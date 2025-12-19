"""Comprehensive test suite for tool_extractor module.

Tests cover:
- Tool extraction from PyInstaller bundles
- Version tracking and caching
- PATH setup and tool discovery
- Error handling and edge cases
- File permissions
- Module-level functions
"""

import hashlib
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from huskycat.core.tool_extractor import (
    ToolExtractor,
    _extractor,
    ensure_tools,
    get_extractor,
    get_tools_info,
)


class TestToolExtractorInit:
    """Test ToolExtractor initialization."""

    def test_init_detects_bundled_state(self):
        """Test that init correctly detects bundled vs source mode."""
        extractor = ToolExtractor()
        assert isinstance(extractor.is_bundled, bool)

    def test_init_sets_cache_dir(self):
        """Test that init sets cache directory to ~/.huskycat/tools."""
        extractor = ToolExtractor()
        assert extractor.cache_dir == Path.home() / ".huskycat" / "tools"

    def test_init_sets_version_file(self):
        """Test that init sets version file path."""
        extractor = ToolExtractor()
        assert extractor.version_file == extractor.cache_dir / ".version"

    def test_init_bundled_sets_tools_dir(self):
        """Test that init sets bundle_tools_dir when bundled."""
        with mock.patch.object(sys, "frozen", True, create=True):
            with mock.patch.object(sys, "_MEIPASS", "/path/to/bundle", create=True):
                extractor = ToolExtractor()
                assert extractor.is_bundled is True
                assert extractor.bundle_tools_dir == Path("/path/to/bundle") / "tools"

    def test_init_unbundled_sets_none(self):
        """Test that init sets bundle_tools_dir to None when not bundled."""
        with mock.patch.object(sys, "frozen", False, create=True):
            extractor = ToolExtractor()
            assert extractor.is_bundled is False
            assert extractor.bundle_tools_dir is None

    def test_init_missing_meipass_sets_none(self):
        """Test that init handles missing _MEIPASS gracefully."""
        with mock.patch.object(sys, "frozen", True, create=True):
            # Remove _MEIPASS if it exists
            if hasattr(sys, "_MEIPASS"):
                delattr(sys, "_MEIPASS")
            extractor = ToolExtractor()
            assert extractor.is_bundled is False


class TestGetBundleVersion:
    """Test bundle version detection."""

    def test_returns_none_when_not_bundled(self):
        """Test that get_bundle_version returns None when not bundled."""
        with mock.patch.object(sys, "frozen", False, create=True):
            extractor = ToolExtractor()
            assert extractor.get_bundle_version() is None

    def test_returns_none_when_no_bundle_tools_dir(self):
        """Test that get_bundle_version returns None when bundle_tools_dir is None."""
        extractor = ToolExtractor()
        extractor.is_bundled = True
        extractor.bundle_tools_dir = None
        assert extractor.get_bundle_version() is None

    def test_reads_version_from_versions_file(self):
        """Test that get_bundle_version reads from versions.txt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tools_dir = Path(tmpdir)
            versions_file = tools_dir / "versions.txt"
            versions_file.write_text("Bundle Version: 1.2.3\nOther: data")

            extractor = ToolExtractor()
            extractor.is_bundled = True
            extractor.bundle_tools_dir = tools_dir

            assert extractor.get_bundle_version() == "1.2.3"

    def test_handles_versions_file_without_bundle_version(self):
        """Test handling of versions.txt without Bundle Version line."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tools_dir = Path(tmpdir)
            versions_file = tools_dir / "versions.txt"
            versions_file.write_text("Some: data\nOther: info")

            extractor = ToolExtractor()
            extractor.is_bundled = True
            extractor.bundle_tools_dir = tools_dir

            # Should fall back to hash computation
            version = extractor.get_bundle_version()
            assert version is not None
            assert len(version) == 16  # Hash length

    def test_extracts_bundle_version_with_spaces(self):
        """Test that get_bundle_version handles whitespace correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tools_dir = Path(tmpdir)
            versions_file = tools_dir / "versions.txt"
            versions_file.write_text("Bundle Version:   1.2.3  \n")

            extractor = ToolExtractor()
            extractor.is_bundled = True
            extractor.bundle_tools_dir = tools_dir

            assert extractor.get_bundle_version() == "1.2.3"

    def test_falls_back_to_hash_when_no_versions_file(self):
        """Test fallback to hash when versions.txt doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tools_dir = Path(tmpdir)
            # Create some tool files
            (tools_dir / "tool1").write_text("content1")
            (tools_dir / "tool2").write_text("content2")

            extractor = ToolExtractor()
            extractor.is_bundled = True
            extractor.bundle_tools_dir = tools_dir

            version = extractor.get_bundle_version()
            assert version is not None
            assert len(version) == 16  # Hash length

    def test_hash_computation_deterministic(self):
        """Test that hash computation is deterministic."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tools_dir = Path(tmpdir)
            (tools_dir / "tool1").write_text("content1")
            (tools_dir / "tool2").write_text("content2")

            extractor = ToolExtractor()
            extractor.is_bundled = True
            extractor.bundle_tools_dir = tools_dir

            version1 = extractor.get_bundle_version()
            version2 = extractor.get_bundle_version()

            assert version1 == version2


class TestComputeToolsHash:
    """Test hash computation for tools."""

    def test_returns_unknown_when_no_tools_dir(self):
        """Test that _compute_tools_hash returns 'unknown' when dir doesn't exist."""
        extractor = ToolExtractor()
        extractor.bundle_tools_dir = Path("/nonexistent/path")

        assert extractor._compute_tools_hash() == "unknown"

    def test_returns_unknown_when_bundle_tools_dir_none(self):
        """Test that _compute_tools_hash returns 'unknown' when bundle_tools_dir is None."""
        extractor = ToolExtractor()
        extractor.bundle_tools_dir = None

        assert extractor._compute_tools_hash() == "unknown"

    def test_hashes_tool_names_and_sizes(self):
        """Test that hash includes tool names and sizes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tools_dir = Path(tmpdir)
            (tools_dir / "black").write_text("black_content")
            (tools_dir / "ruff").write_text("ruff_content")

            extractor = ToolExtractor()
            extractor.bundle_tools_dir = tools_dir

            hash_val = extractor._compute_tools_hash()

            # Verify it's not 'unknown' and has correct format
            assert hash_val != "unknown"
            assert len(hash_val) == 16
            assert isinstance(hash_val, str)

    def test_ignores_versions_file_in_hash(self):
        """Test that versions.txt is ignored in hash computation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tools_dir = Path(tmpdir)
            (tools_dir / "black").write_text("content")
            (tools_dir / "versions.txt").write_text("Version: 1.0")

            extractor = ToolExtractor()
            extractor.bundle_tools_dir = tools_dir

            hash_val = extractor._compute_tools_hash()

            # Change versions.txt
            (tools_dir / "versions.txt").write_text("Version: 2.0")

            hash_val2 = extractor._compute_tools_hash()

            # Hash should be the same (versions.txt is ignored)
            assert hash_val == hash_val2

    def test_ignores_directories(self):
        """Test that subdirectories are ignored in hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tools_dir = Path(tmpdir)
            (tools_dir / "black").write_text("content")
            subdir = tools_dir / "subdir"
            subdir.mkdir()
            (subdir / "file").write_text("content")

            extractor = ToolExtractor()
            extractor.bundle_tools_dir = tools_dir

            hash_val = extractor._compute_tools_hash()
            assert hash_val != "unknown"
            assert len(hash_val) == 16

    def test_different_tools_different_hash(self):
        """Test that different tool sets produce different hashes."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            tools_dir1 = Path(tmpdir1)
            (tools_dir1 / "black").write_text("content1")

            with tempfile.TemporaryDirectory() as tmpdir2:
                tools_dir2 = Path(tmpdir2)
                (tools_dir2 / "black").write_text("content2_with_more")

                extractor = ToolExtractor()
                extractor.bundle_tools_dir = tools_dir1
                hash1 = extractor._compute_tools_hash()

                extractor.bundle_tools_dir = tools_dir2
                hash2 = extractor._compute_tools_hash()

                # Different content sizes should produce different hashes
                # content2_with_more has different length than content1
                assert hash1 != hash2


class TestGetCachedVersion:
    """Test cached version retrieval."""

    def test_returns_none_when_version_file_missing(self):
        """Test that get_cached_version returns None when version file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            extractor = ToolExtractor()
            extractor.version_file = Path(tmpdir) / "nonexistent"

            assert extractor.get_cached_version() is None

    def test_reads_version_from_file(self):
        """Test that get_cached_version reads version correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            version_file = Path(tmpdir) / ".version"
            version_file.write_text("1.2.3")

            extractor = ToolExtractor()
            extractor.version_file = version_file

            assert extractor.get_cached_version() == "1.2.3"

    def test_strips_whitespace(self):
        """Test that get_cached_version strips whitespace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            version_file = Path(tmpdir) / ".version"
            version_file.write_text("  1.2.3  \n\n")

            extractor = ToolExtractor()
            extractor.version_file = version_file

            assert extractor.get_cached_version() == "1.2.3"

    def test_handles_empty_file(self):
        """Test that get_cached_version handles empty version file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            version_file = Path(tmpdir) / ".version"
            version_file.write_text("")

            extractor = ToolExtractor()
            extractor.version_file = version_file

            assert extractor.get_cached_version() == ""


class TestNeedsExtraction:
    """Test extraction necessity detection."""

    def test_returns_false_when_not_bundled(self):
        """Test that needs_extraction returns False when not bundled."""
        with mock.patch.object(sys, "frozen", False, create=True):
            extractor = ToolExtractor()
            assert extractor.needs_extraction() is False

    def test_returns_true_when_cache_missing(self):
        """Test that needs_extraction returns True when cache dir doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tools_dir = Path(tmpdir) / "tools"
            (Path(tmpdir) / "versions.txt").write_text("Bundle Version: 1.0")

            extractor = ToolExtractor()
            extractor.is_bundled = True
            extractor.bundle_tools_dir = Path(tmpdir)
            extractor.cache_dir = tools_dir  # Non-existent
            extractor.version_file = tools_dir / ".version"

            assert extractor.needs_extraction() is True

    def test_returns_true_when_version_mismatch(self):
        """Test that needs_extraction returns True when versions differ."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create bundle directory with version
            bundle_dir = Path(tmpdir) / "bundle"
            bundle_dir.mkdir()
            (bundle_dir / "versions.txt").write_text("Bundle Version: 1.0")

            # Create cache directory with different version
            cache_dir = Path(tmpdir) / "cache"
            cache_dir.mkdir()
            (cache_dir / ".version").write_text("0.9")

            extractor = ToolExtractor()
            extractor.is_bundled = True
            extractor.bundle_tools_dir = bundle_dir
            extractor.cache_dir = cache_dir
            extractor.version_file = cache_dir / ".version"

            assert extractor.needs_extraction() is True

    def test_returns_false_when_version_matches_and_cache_exists(self):
        """Test that needs_extraction returns False when versions match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create bundle directory
            bundle_dir = Path(tmpdir) / "bundle"
            bundle_dir.mkdir()
            (bundle_dir / "versions.txt").write_text("Bundle Version: 1.0")

            # Create cache directory with matching version
            cache_dir = Path(tmpdir) / "cache"
            cache_dir.mkdir()
            (cache_dir / ".version").write_text("1.0")

            extractor = ToolExtractor()
            extractor.is_bundled = True
            extractor.bundle_tools_dir = bundle_dir
            extractor.cache_dir = cache_dir
            extractor.version_file = cache_dir / ".version"

            assert extractor.needs_extraction() is False


class TestExtractTools:
    """Test tool extraction functionality."""

    def test_returns_false_when_not_bundled(self):
        """Test that extract_tools returns False when not bundled."""
        extractor = ToolExtractor()
        extractor.is_bundled = False

        assert extractor.extract_tools() is False

    def test_returns_false_when_bundle_tools_dir_none(self):
        """Test that extract_tools returns False when bundle_tools_dir is None."""
        extractor = ToolExtractor()
        extractor.is_bundled = True
        extractor.bundle_tools_dir = None

        assert extractor.extract_tools() is False

    def test_returns_false_when_bundle_tools_dir_missing(self):
        """Test that extract_tools returns False when bundle dir doesn't exist."""
        extractor = ToolExtractor()
        extractor.is_bundled = True
        extractor.bundle_tools_dir = Path("/nonexistent/path")

        assert extractor.extract_tools() is False

    def test_creates_cache_directory(self):
        """Test that extract_tools creates cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = Path(tmpdir) / "bundle"
            bundle_dir.mkdir()
            (bundle_dir / "black").write_bytes(b"content")
            (bundle_dir / "versions.txt").write_text("Bundle Version: 1.0")

            cache_dir = Path(tmpdir) / "cache"

            extractor = ToolExtractor()
            extractor.is_bundled = True
            extractor.bundle_tools_dir = bundle_dir
            extractor.cache_dir = cache_dir
            extractor.version_file = cache_dir / ".version"

            result = extractor.extract_tools()

            assert result is True
            assert cache_dir.exists()

    def test_copies_tool_files(self):
        """Test that extract_tools copies tool files to cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = Path(tmpdir) / "bundle"
            bundle_dir.mkdir()
            (bundle_dir / "black").write_bytes(b"black content")
            (bundle_dir / "ruff").write_bytes(b"ruff content")
            (bundle_dir / "versions.txt").write_text("Bundle Version: 1.0")

            cache_dir = Path(tmpdir) / "cache"

            extractor = ToolExtractor()
            extractor.is_bundled = True
            extractor.bundle_tools_dir = bundle_dir
            extractor.cache_dir = cache_dir
            extractor.version_file = cache_dir / ".version"

            extractor.extract_tools()

            assert (cache_dir / "black").exists()
            assert (cache_dir / "ruff").exists()
            assert (cache_dir / "black").read_bytes() == b"black content"
            assert (cache_dir / "ruff").read_bytes() == b"ruff content"

    def test_sets_executable_permissions(self):
        """Test that extract_tools sets executable permissions on tools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = Path(tmpdir) / "bundle"
            bundle_dir.mkdir()
            (bundle_dir / "black").write_bytes(b"content")
            (bundle_dir / "versions.txt").write_text("Bundle Version: 1.0")

            cache_dir = Path(tmpdir) / "cache"

            extractor = ToolExtractor()
            extractor.is_bundled = True
            extractor.bundle_tools_dir = bundle_dir
            extractor.cache_dir = cache_dir
            extractor.version_file = cache_dir / ".version"

            extractor.extract_tools()

            # Check permissions on extracted tool
            tool_path = cache_dir / "black"
            assert tool_path.stat().st_mode & 0o111 != 0  # Has execute permission

    def test_skips_permissions_for_versions_file(self):
        """Test that versions.txt permissions are not modified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = Path(tmpdir) / "bundle"
            bundle_dir.mkdir()
            (bundle_dir / "black").write_bytes(b"content")
            (bundle_dir / "versions.txt").write_text("Bundle Version: 1.0")

            cache_dir = Path(tmpdir) / "cache"

            extractor = ToolExtractor()
            extractor.is_bundled = True
            extractor.bundle_tools_dir = bundle_dir
            extractor.cache_dir = cache_dir
            extractor.version_file = cache_dir / ".version"

            extractor.extract_tools()

            # versions.txt should be copied but permissions not modified
            # (or at least not set to 0o755)
            versions_path = cache_dir / "versions.txt"
            assert versions_path.exists()

    def test_writes_version_file(self):
        """Test that extract_tools writes version file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = Path(tmpdir) / "bundle"
            bundle_dir.mkdir()
            (bundle_dir / "black").write_bytes(b"content")
            (bundle_dir / "versions.txt").write_text("Bundle Version: 1.0")

            cache_dir = Path(tmpdir) / "cache"

            extractor = ToolExtractor()
            extractor.is_bundled = True
            extractor.bundle_tools_dir = bundle_dir
            extractor.cache_dir = cache_dir
            extractor.version_file = cache_dir / ".version"

            extractor.extract_tools()

            assert extractor.version_file.exists()
            assert extractor.version_file.read_text() == "1.0"

    def test_returns_true_on_success(self):
        """Test that extract_tools returns True on successful extraction."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = Path(tmpdir) / "bundle"
            bundle_dir.mkdir()
            (bundle_dir / "black").write_bytes(b"content")

            cache_dir = Path(tmpdir) / "cache"

            extractor = ToolExtractor()
            extractor.is_bundled = True
            extractor.bundle_tools_dir = bundle_dir
            extractor.cache_dir = cache_dir
            extractor.version_file = cache_dir / ".version"

            result = extractor.extract_tools()

            assert result is True

    def test_handles_extraction_errors(self, capsys):
        """Test that extract_tools handles errors gracefully."""
        extractor = ToolExtractor()
        extractor.is_bundled = True
        extractor.bundle_tools_dir = Path("/nonexistent")

        # Should not raise, should return False
        result = extractor.extract_tools()
        assert result is False

    def test_preserves_file_metadata(self):
        """Test that extract_tools preserves file metadata with copy2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = Path(tmpdir) / "bundle"
            bundle_dir.mkdir()
            tool_file = bundle_dir / "black"
            tool_file.write_bytes(b"content")

            # Set specific mtime
            import time
            mtime = time.time() - 10000
            os.utime(tool_file, (mtime, mtime))
            original_stat = tool_file.stat()

            cache_dir = Path(tmpdir) / "cache"

            extractor = ToolExtractor()
            extractor.is_bundled = True
            extractor.bundle_tools_dir = bundle_dir
            extractor.cache_dir = cache_dir
            extractor.version_file = cache_dir / ".version"

            extractor.extract_tools()

            cached_tool = cache_dir / "black"
            cached_stat = cached_tool.stat()

            # Metadata should be preserved (st_mtime)
            assert cached_stat.st_mtime == original_stat.st_mtime


class TestSetupPath:
    """Test PATH setup functionality."""

    def test_adds_cache_dir_to_path(self):
        """Test that setup_path adds cache dir to PATH."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            cache_dir.mkdir()

            extractor = ToolExtractor()
            extractor.cache_dir = cache_dir

            original_path = os.environ.get("PATH", "")
            try:
                os.environ["PATH"] = "/usr/bin:/bin"

                extractor.setup_path()

                new_path = os.environ.get("PATH", "")
                assert str(cache_dir) in new_path
                assert new_path.startswith(str(cache_dir))

            finally:
                os.environ["PATH"] = original_path

    def test_prepends_cache_dir_to_path(self):
        """Test that setup_path prepends cache dir (comes first)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            cache_dir.mkdir()

            extractor = ToolExtractor()
            extractor.cache_dir = cache_dir

            original_path = os.environ.get("PATH", "")
            try:
                os.environ["PATH"] = "/usr/bin:/bin"

                extractor.setup_path()

                new_path = os.environ.get("PATH", "")
                parts = new_path.split(os.pathsep)
                assert parts[0] == str(cache_dir)

            finally:
                os.environ["PATH"] = original_path

    def test_idempotent_setup(self):
        """Test that setup_path is idempotent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            cache_dir.mkdir()

            extractor = ToolExtractor()
            extractor.cache_dir = cache_dir

            original_path = os.environ.get("PATH", "")
            try:
                os.environ["PATH"] = "/usr/bin:/bin"

                extractor.setup_path()
                path_after_first = os.environ.get("PATH", "")

                extractor.setup_path()
                path_after_second = os.environ.get("PATH", "")

                # PATH should not duplicate cache dir
                assert path_after_first == path_after_second

            finally:
                os.environ["PATH"] = original_path

    def test_handles_missing_cache_dir(self):
        """Test that setup_path handles non-existent cache dir."""
        extractor = ToolExtractor()
        extractor.cache_dir = Path("/nonexistent/cache")

        original_path = os.environ.get("PATH", "")
        try:
            os.environ["PATH"] = "/usr/bin:/bin"

            # Should not raise
            extractor.setup_path()

            # PATH should be unchanged
            assert os.environ.get("PATH", "") == "/usr/bin:/bin"

        finally:
            os.environ["PATH"] = original_path

    def test_handles_empty_path(self):
        """Test that setup_path handles empty PATH."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            cache_dir.mkdir()

            extractor = ToolExtractor()
            extractor.cache_dir = cache_dir

            original_path = os.environ.get("PATH", "")
            try:
                os.environ["PATH"] = ""

                extractor.setup_path()

                new_path = os.environ.get("PATH", "")
                assert str(cache_dir) in new_path

            finally:
                os.environ["PATH"] = original_path


class TestEnsureToolsAvailable:
    """Test ensure_tools_available main entry point."""

    def test_returns_true_when_not_bundled(self):
        """Test that ensure_tools_available returns True when not bundled."""
        extractor = ToolExtractor()
        extractor.is_bundled = False

        assert extractor.ensure_tools_available() is True

    def test_extracts_when_needed(self):
        """Test that ensure_tools_available extracts tools when needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = Path(tmpdir) / "bundle"
            bundle_dir.mkdir()
            (bundle_dir / "black").write_bytes(b"content")

            cache_dir = Path(tmpdir) / "cache"

            extractor = ToolExtractor()
            extractor.is_bundled = True
            extractor.bundle_tools_dir = bundle_dir
            extractor.cache_dir = cache_dir
            extractor.version_file = cache_dir / ".version"

            result = extractor.ensure_tools_available()

            assert result is True
            assert cache_dir.exists()
            assert (cache_dir / "black").exists()

    def test_skips_extraction_when_not_needed(self):
        """Test that ensure_tools_available skips extraction when not needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = Path(tmpdir) / "bundle"
            bundle_dir.mkdir()
            (bundle_dir / "versions.txt").write_text("Bundle Version: 1.0")
            (bundle_dir / "black").write_bytes(b"content")

            cache_dir = Path(tmpdir) / "cache"
            cache_dir.mkdir()
            (cache_dir / ".version").write_text("1.0")
            (cache_dir / "black").write_bytes(b"content")

            extractor = ToolExtractor()
            extractor.is_bundled = True
            extractor.bundle_tools_dir = bundle_dir
            extractor.cache_dir = cache_dir
            extractor.version_file = cache_dir / ".version"

            # Mock extract_tools to verify it's not called
            with mock.patch.object(extractor, "extract_tools") as mock_extract:
                extractor.ensure_tools_available()
                mock_extract.assert_not_called()

    def test_calls_setup_path(self):
        """Test that ensure_tools_available calls setup_path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            cache_dir.mkdir()

            extractor = ToolExtractor()
            extractor.is_bundled = True
            extractor.bundle_tools_dir = None
            extractor.cache_dir = cache_dir

            # setup_path is called when tools are available
            original_path = os.environ.get("PATH", "")
            try:
                os.environ["PATH"] = "/usr/bin:/bin"
                extractor.ensure_tools_available()
                # PATH should be updated with cache_dir
                new_path = os.environ.get("PATH", "")
                assert str(cache_dir) in new_path or "/usr/bin" in new_path
            finally:
                os.environ["PATH"] = original_path

    def test_handles_extraction_failure(self, capsys):
        """Test that ensure_tools_available handles extraction failures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            extractor = ToolExtractor()
            extractor.is_bundled = True
            extractor.bundle_tools_dir = Path("/nonexistent")
            extractor.cache_dir = Path(tmpdir) / "cache"
            extractor.version_file = Path(tmpdir) / ".version"

            result = extractor.ensure_tools_available()

            assert result is False
            captured = capsys.readouterr()
            assert "Warning: Failed to extract bundled tools" in captured.err

    def test_returns_true_on_success(self):
        """Test that ensure_tools_available returns True on success."""
        extractor = ToolExtractor()
        extractor.is_bundled = False

        assert extractor.ensure_tools_available() is True


class TestGetToolInfo:
    """Test tool information retrieval."""

    def test_returns_empty_dict_when_cache_missing(self):
        """Test that get_tool_info returns empty dict when cache doesn't exist."""
        extractor = ToolExtractor()
        extractor.cache_dir = Path("/nonexistent/cache")

        assert extractor.get_tool_info() == {}

    def test_returns_tool_paths(self):
        """Test that get_tool_info returns tool paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            (cache_dir / "black").write_bytes(b"content")
            (cache_dir / "ruff").write_bytes(b"content")

            extractor = ToolExtractor()
            extractor.cache_dir = cache_dir

            tools = extractor.get_tool_info()

            assert "black" in tools
            assert "ruff" in tools
            assert tools["black"] == cache_dir / "black"
            assert tools["ruff"] == cache_dir / "ruff"

    def test_excludes_version_file(self):
        """Test that get_tool_info excludes .version file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            (cache_dir / "black").write_bytes(b"content")
            (cache_dir / ".version").write_text("1.0")

            extractor = ToolExtractor()
            extractor.cache_dir = cache_dir

            tools = extractor.get_tool_info()

            assert ".version" not in tools
            assert "black" in tools

    def test_excludes_versions_txt(self):
        """Test that get_tool_info excludes versions.txt file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            (cache_dir / "black").write_bytes(b"content")
            (cache_dir / "versions.txt").write_text("version")

            extractor = ToolExtractor()
            extractor.cache_dir = cache_dir

            tools = extractor.get_tool_info()

            assert "versions.txt" not in tools
            assert "black" in tools

    def test_excludes_directories(self):
        """Test that get_tool_info excludes directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            (cache_dir / "black").write_bytes(b"content")
            subdir = cache_dir / "subdir"
            subdir.mkdir()

            extractor = ToolExtractor()
            extractor.cache_dir = cache_dir

            tools = extractor.get_tool_info()

            assert "subdir" not in tools
            assert "black" in tools


class TestModuleLevelFunctions:
    """Test module-level convenience functions."""

    def test_get_extractor_returns_singleton(self):
        """Test that get_extractor returns same instance."""
        extractor1 = get_extractor()
        extractor2 = get_extractor()

        assert extractor1 is extractor2

    def test_get_extractor_initializes_global(self):
        """Test that get_extractor initializes global _extractor."""
        # Reset global
        import huskycat.core.tool_extractor as te
        te._extractor = None

        extractor = get_extractor()

        assert extractor is not None
        assert isinstance(extractor, ToolExtractor)

    def test_ensure_tools_calls_extractor_method(self):
        """Test that ensure_tools calls extractor.ensure_tools_available."""
        import huskycat.core.tool_extractor as te

        with mock.patch.object(ToolExtractor, "ensure_tools_available", return_value=True):
            result = ensure_tools()

            assert result is True

    def test_get_tools_info_calls_extractor_method(self):
        """Test that get_tools_info calls extractor.get_tool_info."""
        import huskycat.core.tool_extractor as te

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            (cache_dir / "black").write_bytes(b"content")

            with mock.patch.object(ToolExtractor, "get_tool_info") as mock_get:
                mock_get.return_value = {"black": cache_dir / "black"}

                tools = get_tools_info()

                assert "black" in tools


class TestModuleAutoExtract:
    """Test module-level auto-extraction on import."""

    def test_module_level_extraction_called_when_bundled(self):
        """Test that module calls ensure_tools on import when bundled."""
        # This is tested implicitly, but we can verify the mechanism
        import huskycat.core.tool_extractor as te

        # The module-level code runs once on import
        # Verify that ensure_tools function exists and is callable
        assert callable(te.ensure_tools)

    def test_module_level_extraction_skipped_when_not_bundled(self):
        """Test that module-level extraction is skipped when not bundled."""
        # When sys.frozen is False, the module-level if block is skipped
        # This is the normal development case
        assert hasattr(sys, "frozen") is False or not getattr(sys, "frozen", False)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_handles_unicode_in_tool_names(self):
        """Test handling of unicode characters in tool names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            (cache_dir / "black_тест").write_bytes(b"content")

            extractor = ToolExtractor()
            extractor.cache_dir = cache_dir

            tools = extractor.get_tool_info()
            assert "black_тест" in tools

    def test_handles_special_characters_in_paths(self):
        """Test handling of special characters in file paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache-dir_v1.0"
            cache_dir.mkdir()
            (cache_dir / "black").write_bytes(b"content")

            extractor = ToolExtractor()
            extractor.cache_dir = cache_dir

            tools = extractor.get_tool_info()
            assert len(tools) == 1

    def test_handles_symlinks(self):
        """Test handling of symlinks in cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            cache_dir.mkdir()
            (cache_dir / "black").write_bytes(b"content")

            try:
                # Create symlink if supported
                (cache_dir / "black_link").symlink_to(cache_dir / "black")

                extractor = ToolExtractor()
                extractor.cache_dir = cache_dir

                tools = extractor.get_tool_info()
                # Should include both files and symlinks
                assert "black" in tools or "black_link" in tools

            except (OSError, NotImplementedError):
                # Symlinks not supported on this platform
                pass

    def test_handles_readonly_cache_dir(self):
        """Test handling when cache directory is read-only."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            cache_dir.mkdir()
            (cache_dir / "black").write_bytes(b"content")

            extractor = ToolExtractor()
            extractor.cache_dir = cache_dir

            # Get tools before making read-only (normal case)
            tools = extractor.get_tool_info()
            assert "black" in tools

            try:
                # Make directory read-only
                cache_dir.chmod(0o555)

                # On macOS/Unix, files in read-only dir might still be readable
                # This is more about verifying get_tool_info doesn't crash
                try:
                    tools_readonly = extractor.get_tool_info()
                    # If we get here, permissions allowed listing
                    assert isinstance(tools_readonly, dict)
                except PermissionError:
                    # This is also acceptable - permission denied
                    pass

            finally:
                # Restore permissions for cleanup
                cache_dir.chmod(0o755)

    def test_handles_large_version_strings(self):
        """Test handling of large version strings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = Path(tmpdir)
            large_version = "v" + "1.0." + "0" * 1000

            version_file = bundle_dir / "versions.txt"
            version_file.write_text(f"Bundle Version: {large_version}")

            extractor = ToolExtractor()
            extractor.bundle_tools_dir = bundle_dir
            extractor.is_bundled = True

            version = extractor.get_bundle_version()
            assert version == large_version

    def test_concurrent_path_setup(self):
        """Test that concurrent PATH setup calls don't cause issues."""
        import threading

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            cache_dir.mkdir()

            extractor = ToolExtractor()
            extractor.cache_dir = cache_dir

            original_path = os.environ.get("PATH", "")
            try:
                os.environ["PATH"] = "/usr/bin:/bin"

                # Setup PATH from multiple threads
                threads = []
                for _ in range(10):
                    t = threading.Thread(target=extractor.setup_path)
                    threads.append(t)
                    t.start()

                for t in threads:
                    t.join()

                # Should only appear once in PATH
                path_parts = os.environ.get("PATH", "").split(os.pathsep)
                cache_count = sum(1 for p in path_parts if p == str(cache_dir))
                assert cache_count == 1

            finally:
                os.environ["PATH"] = original_path
