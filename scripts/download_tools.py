#!/usr/bin/env python3
"""Download platform-specific validation tool binaries.

This script downloads pre-compiled binaries for all HuskyCat validation tools,
organizing them by platform and architecture for embedding in fat binaries.

Usage:
    python scripts/download_tools.py --platform linux-amd64
    python scripts/download_tools.py --all
    python scripts/download_tools.py --clean
"""

import argparse
import gzip
import hashlib
import os
import platform
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path
from typing import Dict, Optional

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


# Tool download URLs by platform
# Format: tool_name -> { platform_key -> (url, extract_path) }
TOOL_URLS: Dict[str, Dict[str, tuple]] = {
    "shellcheck": {
        "linux-amd64": (
            "https://github.com/koalaman/shellcheck/releases/download/v0.10.0/shellcheck-v0.10.0.linux.x86_64.tar.xz",
            "shellcheck-v0.10.0/shellcheck",
        ),
        "linux-arm64": (
            "https://github.com/koalaman/shellcheck/releases/download/v0.10.0/shellcheck-v0.10.0.linux.aarch64.tar.xz",
            "shellcheck-v0.10.0/shellcheck",
        ),
        "darwin-amd64": (
            "https://github.com/koalaman/shellcheck/releases/download/v0.10.0/shellcheck-v0.10.0.darwin.x86_64.tar.xz",
            "shellcheck-v0.10.0/shellcheck",
        ),
        "darwin-arm64": (
            "https://github.com/koalaman/shellcheck/releases/download/v0.10.0/shellcheck-v0.10.0.darwin.aarch64.tar.xz",
            "shellcheck-v0.10.0/shellcheck",
        ),
    },
    "hadolint": {
        "linux-amd64": (
            "https://github.com/hadolint/hadolint/releases/download/v2.12.0/hadolint-Linux-x86_64",
            None,  # Direct binary, no extraction needed
        ),
        "linux-arm64": (
            "https://github.com/hadolint/hadolint/releases/download/v2.12.0/hadolint-Linux-arm64",
            None,
        ),
        "darwin-amd64": (
            "https://github.com/hadolint/hadolint/releases/download/v2.12.0/hadolint-Darwin-x86_64",
            None,
        ),
        "darwin-arm64": (
            # No native ARM64 build in v2.12.0, use x86_64 (runs via Rosetta 2)
            "https://github.com/hadolint/hadolint/releases/download/v2.12.0/hadolint-Darwin-x86_64",
            None,
        ),
    },
    "taplo": {
        "linux-amd64": (
            "https://github.com/tamasfe/taplo/releases/download/0.9.3/taplo-linux-x86_64.gz",
            None,  # Gzipped, extract inline
        ),
        "linux-arm64": (
            "https://github.com/tamasfe/taplo/releases/download/0.9.3/taplo-linux-aarch64.gz",
            None,
        ),
        "darwin-amd64": (
            "https://github.com/tamasfe/taplo/releases/download/0.9.3/taplo-darwin-x86_64.gz",
            None,
        ),
        "darwin-arm64": (
            "https://github.com/tamasfe/taplo/releases/download/0.9.3/taplo-darwin-aarch64.gz",
            None,
        ),
    },
}

# Version markers for tool bundles
TOOL_VERSIONS = {
    "shellcheck": "0.10.0",
    "hadolint": "2.12.0",
    "taplo": "0.9.3",
    "bundle_version": "1.0.0",  # HuskyCat tool bundle version
}


class ToolDownloader:
    """Download and manage validation tool binaries."""

    def __init__(self, target_dir: Path, verbose: bool = True):
        """Initialize downloader.

        Args:
            target_dir: Directory to store downloaded tools
            verbose: Print progress messages
        """
        self.target_dir = target_dir
        self.verbose = verbose
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def log(self, message: str) -> None:
        """Print message if verbose mode enabled."""
        if self.verbose:
            print(message)

    def download_file(self, url: str, dest_path: Path) -> None:
        """Download file with progress reporting.

        Args:
            url: URL to download from
            dest_path: Destination file path
        """
        self.log(f"Downloading {url}")
        self.log(f"  -> {dest_path}")

        # Download with progress
        with urllib.request.urlopen(url) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0

            with open(dest_path, "wb") as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    if self.verbose and total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(
                            f"\r  Progress: {percent:.1f}% ({downloaded}/{total_size} bytes)",
                            end="",
                        )

        if self.verbose and total_size > 0:
            print()  # Newline after progress

    def extract_tarxz(self, archive_path: Path, extract_file: str, dest_path: Path) -> None:
        """Extract specific file from .tar.xz archive.

        Args:
            archive_path: Path to .tar.xz file
            extract_file: Relative path of file to extract from archive
            dest_path: Destination path for extracted file
        """
        self.log(f"Extracting {extract_file} from {archive_path.name}")

        with tarfile.open(archive_path, "r:xz") as tar:
            member = tar.getmember(extract_file)
            with tar.extractfile(member) as src:
                with open(dest_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)

        # Make executable
        dest_path.chmod(0o755)

    def extract_gzip(self, gz_path: Path, dest_path: Path) -> None:
        """Extract .gz file.

        Args:
            gz_path: Path to .gz file
            dest_path: Destination path for extracted file
        """
        self.log(f"Extracting {gz_path.name}")

        with gzip.open(gz_path, "rb") as src:
            with open(dest_path, "wb") as dst:
                shutil.copyfileobj(src, dst)

        # Make executable
        dest_path.chmod(0o755)

    def download_tool(self, tool_name: str, platform_key: str) -> Optional[Path]:
        """Download a specific tool for a platform.

        Args:
            tool_name: Name of tool (e.g., 'shellcheck')
            platform_key: Platform identifier (e.g., 'linux-amd64')

        Returns:
            Path to downloaded binary, or None if not available
        """
        if tool_name not in TOOL_URLS:
            self.log(f"Warning: Unknown tool '{tool_name}'")
            return None

        platforms = TOOL_URLS[tool_name]
        if platform_key not in platforms:
            self.log(f"Warning: {tool_name} not available for {platform_key}")
            return None

        url, extract_path = platforms[platform_key]

        # Create platform-specific directory
        platform_dir = self.target_dir / platform_key
        platform_dir.mkdir(parents=True, exist_ok=True)

        # Determine final binary path
        final_binary = platform_dir / tool_name

        # Skip if already downloaded
        if final_binary.exists():
            self.log(f"Tool {tool_name} already exists at {final_binary}")
            return final_binary

        # Download to temp location
        temp_dir = self.target_dir / "tmp"
        temp_dir.mkdir(exist_ok=True)
        download_path = temp_dir / Path(url).name

        try:
            self.download_file(url, download_path)

            # Extract based on file type
            if url.endswith(".tar.xz"):
                self.extract_tarxz(download_path, extract_path, final_binary)
            elif url.endswith(".gz"):
                self.extract_gzip(download_path, final_binary)
            else:
                # Direct binary - just move and make executable
                shutil.move(str(download_path), str(final_binary))
                final_binary.chmod(0o755)

            self.log(f"Successfully downloaded {tool_name} to {final_binary}")
            return final_binary

        except Exception as e:
            self.log(f"Error downloading {tool_name}: {e}")
            return None

        finally:
            # Cleanup temp file
            if download_path.exists():
                download_path.unlink()

    def download_all_tools(self, platform_key: str) -> Dict[str, Path]:
        """Download all tools for a platform.

        Args:
            platform_key: Platform identifier (e.g., 'linux-amd64')

        Returns:
            Dictionary mapping tool names to binary paths
        """
        self.log(f"\nDownloading tools for {platform_key}")
        self.log("=" * 60)

        results = {}
        for tool_name in TOOL_URLS.keys():
            binary_path = self.download_tool(tool_name, platform_key)
            if binary_path:
                results[tool_name] = binary_path

        self.log("\nDownload Summary:")
        self.log(f"  Platform: {platform_key}")
        self.log(f"  Tools downloaded: {len(results)}/{len(TOOL_URLS)}")
        for tool_name, path in results.items():
            size_mb = path.stat().st_size / (1024 * 1024)
            self.log(f"    {tool_name}: {size_mb:.2f}MB")

        # Write version manifest
        self.write_version_manifest(platform_key, results)

        return results

    def write_version_manifest(self, platform_key: str, tools: Dict[str, Path]) -> None:
        """Write version information for downloaded tools.

        Args:
            platform_key: Platform identifier
            tools: Dictionary of tool names to paths
        """
        manifest_path = self.target_dir / platform_key / "versions.txt"

        with open(manifest_path, "w") as f:
            f.write(f"HuskyCat Tool Bundle\n")
            f.write(f"Platform: {platform_key}\n")
            f.write(f"Bundle Version: {TOOL_VERSIONS['bundle_version']}\n")
            f.write("\nTool Versions:\n")

            for tool_name in sorted(tools.keys()):
                version = TOOL_VERSIONS.get(tool_name, "unknown")
                f.write(f"  {tool_name}: {version}\n")

        self.log(f"Wrote version manifest to {manifest_path}")

    def verify_binary(self, binary_path: Path) -> bool:
        """Verify binary is executable and valid.

        Args:
            binary_path: Path to binary

        Returns:
            True if binary is valid
        """
        if not binary_path.exists():
            return False

        # Check if executable bit is set
        if not os.access(binary_path, os.X_OK):
            return False

        # Check if file is not empty
        if binary_path.stat().st_size == 0:
            return False

        return True

    def clean_downloads(self) -> None:
        """Remove all downloaded tools."""
        if self.target_dir.exists():
            self.log(f"Cleaning {self.target_dir}")
            shutil.rmtree(self.target_dir)
            self.log("Clean complete")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Download HuskyCat validation tool binaries"
    )
    parser.add_argument(
        "--platform",
        choices=["linux-amd64", "linux-arm64", "darwin-amd64", "darwin-arm64", "auto"],
        default="auto",
        help="Target platform (default: auto-detect)",
    )
    parser.add_argument(
        "--tool",
        choices=list(TOOL_URLS.keys()),
        help="Download specific tool only (for checkpoint resume)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download tools for all platforms",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dist/tools"),
        help="Output directory (default: dist/tools)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove all downloaded tools",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output messages",
    )

    args = parser.parse_args()

    downloader = ToolDownloader(args.output_dir, verbose=not args.quiet)

    if args.clean:
        downloader.clean_downloads()
        return 0

    if args.all:
        platforms = ["linux-amd64", "linux-arm64", "darwin-amd64", "darwin-arm64"]
    else:
        platform_key = get_current_platform() if args.platform == "auto" else args.platform
        platforms = [platform_key]

    # Download for each platform
    total_tools = 0
    for platform_key in platforms:
        if args.tool:
            # Download specific tool only (checkpoint mode)
            print(f"\nCheckpoint mode: Downloading {args.tool} for {platform_key}")
            binary_path = downloader.download_tool(args.tool, platform_key)
            if binary_path:
                total_tools += 1
                # Write manifest for single tool
                results = {args.tool: binary_path}
                downloader.write_version_manifest(platform_key, results)
        else:
            # Download all tools
            results = downloader.download_all_tools(platform_key)
            total_tools += len(results)

    print(f"\n✓ Downloaded {total_tools} tool binaries across {len(platforms)} platform(s)")
    print(f"✓ Tools stored in: {args.output_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
