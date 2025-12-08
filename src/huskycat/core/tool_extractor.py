#!/usr/bin/env python3
"""Runtime tool extraction for fat binaries.

When running from a PyInstaller bundle, this module extracts embedded
validation tools to ~/.huskycat/tools/ on first run and sets up PATH
to use them.

The extraction is version-aware and only re-extracts when the bundle
version changes.
"""

import hashlib
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, Optional


class ToolExtractor:
    """Extract and manage embedded validation tools."""

    def __init__(self):
        """Initialize extractor."""
        # Detect if running from PyInstaller bundle
        self.is_bundled = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")

        if self.is_bundled:
            # Running from bundle - tools are in _MEIPASS/tools
            self.bundle_tools_dir = Path(sys._MEIPASS) / "tools"
        else:
            # Running from source - tools might be in dist/tools/{platform}
            self.bundle_tools_dir = None

        # User's tool cache directory
        self.cache_dir = Path.home() / ".huskycat" / "tools"
        self.version_file = self.cache_dir / ".version"

    def get_bundle_version(self) -> Optional[str]:
        """Get version identifier for bundled tools.

        Returns:
            Version string, or None if not bundled
        """
        if not self.is_bundled or not self.bundle_tools_dir:
            return None

        # Check for versions.txt in bundle
        version_file = self.bundle_tools_dir / "versions.txt"
        if version_file.exists():
            with open(version_file) as f:
                for line in f:
                    if line.startswith("Bundle Version:"):
                        return line.split(":", 1)[1].strip()

        # Fallback: compute hash of tool directory
        return self._compute_tools_hash()

    def _compute_tools_hash(self) -> str:
        """Compute hash of all bundled tools for version tracking.

        Returns:
            Hash string
        """
        if not self.bundle_tools_dir or not self.bundle_tools_dir.exists():
            return "unknown"

        hasher = hashlib.sha256()

        for tool_file in sorted(self.bundle_tools_dir.glob("*")):
            if tool_file.is_file() and tool_file.name != "versions.txt":
                hasher.update(tool_file.name.encode())
                hasher.update(str(tool_file.stat().st_size).encode())

        return hasher.hexdigest()[:16]

    def get_cached_version(self) -> Optional[str]:
        """Get version of currently cached tools.

        Returns:
            Version string, or None if not cached
        """
        if not self.version_file.exists():
            return None

        with open(self.version_file) as f:
            return f.read().strip()

    def needs_extraction(self) -> bool:
        """Check if tools need to be extracted.

        Returns:
            True if extraction is needed
        """
        if not self.is_bundled:
            return False

        bundle_version = self.get_bundle_version()
        cached_version = self.get_cached_version()

        # Extract if versions don't match or cache doesn't exist
        return bundle_version != cached_version or not self.cache_dir.exists()

    def extract_tools(self) -> bool:
        """Extract embedded tools to cache directory.

        Returns:
            True if successful
        """
        if not self.is_bundled or not self.bundle_tools_dir:
            return False

        if not self.bundle_tools_dir.exists():
            return False

        try:
            # Create cache directory
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            # Copy each tool
            for tool_file in self.bundle_tools_dir.glob("*"):
                if tool_file.is_file():
                    dest = self.cache_dir / tool_file.name
                    shutil.copy2(tool_file, dest)

                    # Ensure executable (Unix)
                    if tool_file.name != "versions.txt":
                        dest.chmod(0o755)

            # Write version marker
            bundle_version = self.get_bundle_version()
            with open(self.version_file, "w") as f:
                f.write(bundle_version or "unknown")

            return True

        except Exception as e:
            print(f"Warning: Failed to extract tools: {e}", file=sys.stderr)
            return False

    def setup_path(self) -> None:
        """Add cache directory to PATH for tool discovery."""
        if self.cache_dir.exists():
            # Prepend cache directory to PATH
            path_var = os.environ.get("PATH", "")
            cache_str = str(self.cache_dir)

            if cache_str not in path_var:
                os.environ["PATH"] = f"{cache_str}{os.pathsep}{path_var}"

    def ensure_tools_available(self) -> bool:
        """Ensure tools are extracted and available.

        This is the main entry point - call this before running validation.

        Returns:
            True if tools are available
        """
        # If not bundled, tools should be found via normal PATH
        if not self.is_bundled:
            return True

        # Check if extraction needed
        if self.needs_extraction():
            if not self.extract_tools():
                print("Warning: Failed to extract bundled tools", file=sys.stderr)
                return False

        # Setup PATH
        self.setup_path()

        return True

    def get_tool_info(self) -> Dict[str, Path]:
        """Get information about available tools.

        Returns:
            Dictionary mapping tool names to paths
        """
        tools = {}

        if not self.cache_dir.exists():
            return tools

        for tool_file in self.cache_dir.glob("*"):
            if tool_file.is_file() and tool_file.name not in (".version", "versions.txt"):
                tools[tool_file.name] = tool_file

        return tools


# Global extractor instance
_extractor: Optional[ToolExtractor] = None


def get_extractor() -> ToolExtractor:
    """Get global ToolExtractor instance.

    Returns:
        ToolExtractor instance
    """
    global _extractor
    if _extractor is None:
        _extractor = ToolExtractor()
    return _extractor


def ensure_tools() -> bool:
    """Convenience function to ensure tools are available.

    Returns:
        True if tools are available
    """
    return get_extractor().ensure_tools_available()


def get_tools_info() -> Dict[str, Path]:
    """Convenience function to get tool information.

    Returns:
        Dictionary of tool names to paths
    """
    return get_extractor().get_tool_info()


# Auto-extract on module import for bundled executables
if getattr(sys, "frozen", False):
    # Running from bundle - ensure tools on startup
    ensure_tools()
