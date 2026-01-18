#!/usr/bin/env python3
"""Build HuskyCat fat binary with embedded validation tools.

This script creates a standalone executable binary that includes:
- Python runtime and HuskyCat code
- All validation tool binaries (shellcheck, hadolint, taplo)
- Chapel formatter implementation
- Configuration schemas and templates

The resulting binary is self-contained and requires no external dependencies.

Usage:
    python build_fat_binary.py                    # Build for current platform
    python build_fat_binary.py --platform linux-amd64
    python build_fat_binary.py --all-platforms    # Build for all platforms
    python build_fat_binary.py --skip-download    # Use existing tools

Binary Structure:
    huskycat (150-200MB)
    ├── Python runtime (~40MB)
    ├── HuskyCat code (~5MB)
    ├── Embedded tools (~100-150MB)
    │   ├── shellcheck
    │   ├── hadolint
    │   └── taplo
    └── Chapel formatter (~5MB)
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Import our download script (same directory)
sys.path.insert(0, str(Path(__file__).parent))
import download_tools

# Platform detection
SYSTEM_MAP = {
    "Linux": "linux",
    "Darwin": "darwin",
    "Windows": "windows",
}

ARCH_MAP = {
    "x86_64": "amd64",
    "aarch64": "arm64",
    "arm64": "arm64",
    "AMD64": "amd64",
}


def get_current_platform() -> str:
    """Detect current platform string (e.g., 'linux-amd64')."""
    system = SYSTEM_MAP.get(platform.system(), platform.system().lower())
    arch = ARCH_MAP.get(platform.machine(), platform.machine().lower())
    return f"{system}-{arch}"


class FatBinaryBuilder:
    """Build HuskyCat fat binary with embedded toolchain."""

    def __init__(
        self,
        platform_key: str,
        output_dir: Path,
        tools_dir: Path,
        skip_download: bool = False,
        verbose: bool = True,
    ):
        """Initialize builder.

        Args:
            platform_key: Target platform (e.g., 'linux-amd64')
            output_dir: Directory for output binaries
            tools_dir: Directory containing downloaded tools
            skip_download: Skip downloading tools (use existing)
            verbose: Print progress messages
        """
        self.platform_key = platform_key
        self.output_dir = output_dir
        self.tools_dir = tools_dir
        self.skip_download = skip_download
        self.verbose = verbose

        # Paths
        self.project_root = Path(__file__).parent
        self.dist_dir = self.output_dir / self.platform_key
        self.tools_platform_dir = self.tools_dir / self.platform_key

    def log(self, message: str) -> None:
        """Print message if verbose mode enabled."""
        if self.verbose:
            print(message)

    def download_tools(self) -> bool:
        """Download validation tools for target platform.

        Returns:
            True if successful
        """
        if self.skip_download:
            self.log("Skipping tool download (--skip-download)")
            if not self.tools_platform_dir.exists():
                self.log(f"Error: Tools directory not found: {self.tools_platform_dir}")
                return False
            return True

        self.log(f"\nDownloading tools for {self.platform_key}...")
        downloader = download_tools.ToolDownloader(self.tools_dir, verbose=self.verbose)

        results = downloader.download_all_tools(self.platform_key)

        if not results:
            self.log(f"Error: Failed to download tools for {self.platform_key}")
            return False

        self.log(f"✓ Downloaded {len(results)} tools")
        return True

    def verify_tools(self) -> bool:
        """Verify all required tools are present.

        Returns:
            True if all tools exist
        """
        required_tools = ["shellcheck", "hadolint", "taplo"]
        missing = []

        for tool_name in required_tools:
            tool_path = self.tools_platform_dir / tool_name
            if not tool_path.exists():
                missing.append(tool_name)
            else:
                size_mb = tool_path.stat().st_size / (1024 * 1024)
                self.log(f"  ✓ {tool_name}: {size_mb:.2f}MB")

        if missing:
            self.log(f"Error: Missing tools: {', '.join(missing)}")
            return False

        return True

    def create_pyinstaller_spec(self) -> Path:
        """Create PyInstaller spec file with embedded tools.

        Returns:
            Path to spec file
        """
        spec_path = self.project_root / "build" / "specs" / f"huskycat-{self.platform_key}.spec"

        # Get list of tool binaries to embed
        tool_binaries = []
        if self.tools_platform_dir.exists():
            for tool_file in self.tools_platform_dir.glob("*"):
                if tool_file.is_file() and tool_file.name != "versions.txt":
                    tool_binaries.append((str(tool_file), "tools"))

        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for HuskyCat fat binary with embedded tools.

Generated for platform: {self.platform_key}
"""

block_cipher = None

a = Analysis(
    ['huskycat_main.py'],
    pathex=[],
    binaries={tool_binaries!r},
    datas=[
        ('src/huskycat/formatters/chapel.py', 'huskycat/formatters'),
        ('src/huskycat/formatters/__init__.py', 'huskycat/formatters'),
    ],
    hiddenimports=[
        'huskycat',
        'huskycat.__main__',
        'huskycat.core',
        'huskycat.core.mode_detector',
        'huskycat.core.factory',
        'huskycat.core.adapters',
        'huskycat.formatters',
        'huskycat.formatters.chapel',
        'huskycat.unified_validation',
        'huskycat.mcp_server',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'PIL',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='huskycat',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''

        with open(spec_path, "w") as f:
            f.write(spec_content)

        self.log(f"Created PyInstaller spec: {spec_path}")
        return spec_path

    def build_with_pyinstaller(self, spec_path: Path) -> Optional[Path]:
        """Build binary using PyInstaller.

        Args:
            spec_path: Path to PyInstaller spec file

        Returns:
            Path to built binary, or None on failure
        """
        self.log(f"\nBuilding binary with PyInstaller...")
        self.log(f"  Platform: {self.platform_key}")
        self.log(f"  Spec: {spec_path}")

        # Prepare output directory
        self.dist_dir.mkdir(parents=True, exist_ok=True)

        # Run PyInstaller
        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            str(spec_path),
            "--distpath",
            str(self.dist_dir),
            "--workpath",
            str(self.project_root / "build" / self.platform_key),
            "--clean",
            "--noconfirm",
        ]

        self.log(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=not self.verbose,
                text=True,
                check=True,
            )

            # Find the binary
            binary_name = "huskycat.exe" if "windows" in self.platform_key else "huskycat"
            binary_path = self.dist_dir / binary_name

            if not binary_path.exists():
                self.log(f"Error: Binary not found at {binary_path}")
                return None

            # Make executable (Unix)
            if "windows" not in self.platform_key:
                binary_path.chmod(0o755)

            return binary_path

        except subprocess.CalledProcessError as e:
            self.log(f"Error: PyInstaller failed with exit code {e.returncode}")
            if not self.verbose and e.output:
                self.log(f"Output: {e.output}")
            return None

    def verify_binary(self, binary_path: Path) -> bool:
        """Verify the built binary works correctly.

        Args:
            binary_path: Path to binary

        Returns:
            True if binary is valid
        """
        self.log(f"\nVerifying binary: {binary_path}")

        # Check size
        size_mb = binary_path.stat().st_size / (1024 * 1024)
        self.log(f"  Size: {size_mb:.1f}MB")

        if size_mb > 250:
            self.log(f"  Warning: Binary larger than 250MB target")

        # Test execution
        try:
            result = subprocess.run(
                [str(binary_path), "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                self.log("  ✓ Binary executes successfully")
                return True
            else:
                self.log(f"  Error: Binary returned exit code {result.returncode}")
                return False

        except subprocess.TimeoutExpired:
            self.log("  Error: Binary execution timed out")
            return False
        except Exception as e:
            self.log(f"  Error: Failed to execute binary: {e}")
            return False

    def generate_checksums(self, binary_path: Path) -> Path:
        """Generate SHA256 checksums for the binary.

        Args:
            binary_path: Path to binary

        Returns:
            Path to checksum file
        """
        import hashlib

        checksum_path = binary_path.parent / f"{binary_path.name}.sha256"

        sha256 = hashlib.sha256()
        with open(binary_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)

        checksum = sha256.hexdigest()

        with open(checksum_path, "w") as f:
            f.write(f"{checksum}  {binary_path.name}\n")

        self.log(f"  Checksum: {checksum}")
        self.log(f"  Written to: {checksum_path}")

        return checksum_path

    def build(self) -> Optional[Path]:
        """Execute full build process.

        Returns:
            Path to built binary, or None on failure
        """
        self.log("=" * 70)
        self.log(f"Building HuskyCat Fat Binary for {self.platform_key}")
        self.log("=" * 70)

        # Step 1: Download tools
        if not self.download_tools():
            return None

        # Step 2: Verify tools
        self.log("\nVerifying tools...")
        if not self.verify_tools():
            return None

        # Step 3: Create PyInstaller spec
        self.log("\nCreating PyInstaller spec...")
        spec_path = self.create_pyinstaller_spec()

        # Step 4: Build with PyInstaller
        binary_path = self.build_with_pyinstaller(spec_path)
        if not binary_path:
            return None

        # Step 5: Verify binary
        if not self.verify_binary(binary_path):
            return None

        # Step 6: Generate checksums
        self.log("\nGenerating checksums...")
        self.generate_checksums(binary_path)

        # Success!
        self.log("\n" + "=" * 70)
        self.log("Build Complete!")
        self.log("=" * 70)
        self.log(f"Binary: {binary_path}")
        size_mb = binary_path.stat().st_size / (1024 * 1024)
        self.log(f"Size: {size_mb:.1f}MB")
        self.log("\nTo test the binary:")
        self.log(f"  {binary_path} --help")
        self.log(f"  {binary_path} status")
        self.log(f"  {binary_path} validate")

        return binary_path


def build_all_platforms(
    output_dir: Path,
    tools_dir: Path,
    skip_download: bool = False,
    verbose: bool = True,
) -> Dict[str, Optional[Path]]:
    """Build binaries for all supported platforms.

    Args:
        output_dir: Directory for output binaries
        tools_dir: Directory containing downloaded tools
        skip_download: Skip downloading tools
        verbose: Print progress messages

    Returns:
        Dictionary mapping platform keys to binary paths
    """
    platforms = ["linux-amd64", "linux-arm64", "darwin-amd64", "darwin-arm64"]
    results = {}

    for platform_key in platforms:
        print(f"\n{'=' * 70}")
        print(f"Building for {platform_key}")
        print('=' * 70)

        builder = FatBinaryBuilder(
            platform_key=platform_key,
            output_dir=output_dir,
            tools_dir=tools_dir,
            skip_download=skip_download,
            verbose=verbose,
        )

        binary_path = builder.build()
        results[platform_key] = binary_path

        if binary_path:
            print(f"✓ {platform_key}: Success")
        else:
            print(f"✗ {platform_key}: Failed")

    return results


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Build HuskyCat fat binary with embedded tools"
    )
    parser.add_argument(
        "--platform",
        choices=["linux-amd64", "linux-arm64", "darwin-amd64", "darwin-arm64", "auto"],
        default="auto",
        help="Target platform (default: auto-detect)",
    )
    parser.add_argument(
        "--all-platforms",
        action="store_true",
        help="Build for all supported platforms",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dist"),
        help="Output directory (default: dist)",
    )
    parser.add_argument(
        "--tools-dir",
        type=Path,
        default=Path("dist/tools"),
        help="Tools directory (default: dist/tools)",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip downloading tools (use existing)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output messages",
    )

    args = parser.parse_args()

    if args.all_platforms:
        results = build_all_platforms(
            output_dir=args.output_dir,
            tools_dir=args.tools_dir,
            skip_download=args.skip_download,
            verbose=not args.quiet,
        )

        # Summary
        print("\n" + "=" * 70)
        print("Build Summary")
        print("=" * 70)

        success_count = sum(1 for path in results.values() if path is not None)
        total_count = len(results)

        for platform_key, binary_path in results.items():
            if binary_path:
                size_mb = binary_path.stat().st_size / (1024 * 1024)
                print(f"  ✓ {platform_key}: {size_mb:.1f}MB")
            else:
                print(f"  ✗ {platform_key}: Failed")

        print(f"\nSuccess: {success_count}/{total_count} platforms")

        return 0 if success_count == total_count else 1

    else:
        # Build for single platform
        platform_key = (
            get_current_platform() if args.platform == "auto" else args.platform
        )

        builder = FatBinaryBuilder(
            platform_key=platform_key,
            output_dir=args.output_dir,
            tools_dir=args.tools_dir,
            skip_download=args.skip_download,
            verbose=not args.quiet,
        )

        binary_path = builder.build()

        return 0 if binary_path else 1


if __name__ == "__main__":
    sys.exit(main())
