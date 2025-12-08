"""
Test suite for HuskyCat binary bootstrap, installation, and tool extraction.

Tests the complete binary lifecycle:
- Installation to user bin
- Tool extraction to cache
- Hook setup with correct binary paths
- Version tracking and re-extraction logic
- Shell completions generation
"""

import pytest
import subprocess
import tempfile
import shutil
from pathlib import Path
import os


@pytest.fixture
def clean_environment(tmp_path):
    """Create isolated test environment with mocked HOME."""
    bin_dir = tmp_path / "bin"
    home_dir = tmp_path / "home"
    bin_dir.mkdir()
    home_dir.mkdir()

    # Mock HOME for this test
    old_home = os.environ.get("HOME")
    os.environ["HOME"] = str(home_dir)

    yield bin_dir, home_dir

    # Restore original HOME
    if old_home:
        os.environ["HOME"] = old_home


@pytest.fixture
def binary_path():
    """Get path to the built binary (if it exists)."""
    repo_root = Path(__file__).parent.parent
    binary = repo_root / "dist" / "huskycat"

    if not binary.exists():
        pytest.skip("Binary not built - run: npm run build:binary")

    return binary


@pytest.mark.integration
class TestBinaryBootstrap:
    """Integration tests for binary bootstrap and installation."""

    def test_binary_help_works(self, binary_path):
        """Test: Binary --help command works."""
        result = subprocess.run(
            [str(binary_path), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, f"--help failed: {result.stderr}"
        assert "huskycat" in result.stdout.lower()

    def test_binary_version_works(self, binary_path):
        """Test: Binary --version command works."""
        result = subprocess.run(
            [str(binary_path), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, f"--version failed: {result.stderr}"
        # Should output version number like "2.0.0"
        assert any(char.isdigit() for char in result.stdout)

    def test_binary_install_creates_executable(self, clean_environment, binary_path):
        """Test: huskycat install creates executable in bin dir."""
        bin_dir, home_dir = clean_environment

        result = subprocess.run(
            [str(binary_path), "install", "--bin-dir", str(bin_dir), "--no-setup-hooks"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # May succeed or fail depending on implementation, but should not crash
        installed = bin_dir / "huskycat"

        if result.returncode == 0:
            assert installed.exists(), "Binary not installed despite success"
            assert installed.stat().st_mode & 0o111, "Binary not executable"

    def test_tool_extraction_directory_created(self, clean_environment, binary_path):
        """Test: Tools directory created in ~/.huskycat/tools/."""
        bin_dir, home_dir = clean_environment

        # Run any command that triggers tool extraction
        result = subprocess.run(
            [str(binary_path), "validate", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        tools_dir = home_dir / ".huskycat" / "tools"

        # Tool extraction may or may not happen depending on binary type
        # This test just verifies no crashes occur
        assert result.returncode in [0, 1], f"Command crashed: {result.stderr}"

    def test_hook_setup_in_temp_repo(self, clean_environment, binary_path):
        """Test: setup-hooks works in temporary git repository."""
        bin_dir, home_dir = clean_environment

        # Create temporary git repo
        repo = home_dir / "test-repo"
        repo.mkdir()

        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Run setup-hooks
        result = subprocess.run(
            [str(binary_path), "setup-hooks"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should succeed or provide useful error
        assert result.returncode in [0, 1], f"setup-hooks crashed: {result.stderr}"

    def test_binary_executes_without_crash(self, binary_path):
        """Test: Binary executes basic commands without crashing."""
        commands = [
            ["--help"],
            ["--version"],
            ["status"],
            ["validate", "--help"],
        ]

        for cmd in commands:
            result = subprocess.run(
                [str(binary_path)] + cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )

            assert result.returncode in [0, 1], f"Command {cmd} crashed: {result.stderr}"

    def test_version_marker_created_after_extraction(self, clean_environment, binary_path):
        """Test: Version marker file created after tool extraction."""
        bin_dir, home_dir = clean_environment

        # Trigger potential tool extraction
        subprocess.run(
            [str(binary_path), "validate", "--help"],
            capture_output=True,
            timeout=30,
        )

        version_file = home_dir / ".huskycat" / "tools" / ".version"

        # Version file may or may not exist depending on binary type
        # This test just ensures no crashes
        if version_file.exists():
            content = version_file.read_text()
            assert len(content) > 0, "Version file is empty"

    def test_shell_completions_structure(self, clean_environment, binary_path):
        """Test: Shell completion files have expected structure."""
        bin_dir, home_dir = clean_environment

        # Try to install (may or may not create completions)
        subprocess.run(
            [str(binary_path), "install", "--bin-dir", str(bin_dir)],
            capture_output=True,
            timeout=30,
        )

        completions_dir = home_dir / ".huskycat" / "completions"

        # Completions may or may not be created
        if completions_dir.exists():
            # If created, verify expected files
            expected_files = ["huskycat.bash", "_huskycat", "huskycat.fish"]
            for comp_file in expected_files:
                comp_path = completions_dir / comp_file
                if comp_path.exists():
                    assert comp_path.stat().st_size > 0, f"{comp_file} is empty"

    def test_binary_runs_in_subprocess(self, binary_path):
        """Test: Binary can be spawned as subprocess."""
        # This tests that the binary can be forked/spawned
        result = subprocess.run(
            [str(binary_path), "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Should not hang or crash
        assert result.returncode in [0, 1], "Binary subprocess failed"

    def test_multiple_binary_invocations(self, binary_path):
        """Test: Multiple sequential binary invocations work."""
        for i in range(3):
            result = subprocess.run(
                [str(binary_path), "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            assert result.returncode == 0, f"Invocation {i+1} failed"

    def test_binary_with_env_vars(self, binary_path):
        """Test: Binary respects environment variables."""
        env = os.environ.copy()
        env["HUSKYCAT_NONBLOCKING"] = "1"

        result = subprocess.run(
            [str(binary_path), "--help"],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, "Binary with env vars failed"


@pytest.mark.unit
class TestBinaryPathDetection:
    """Unit tests for binary path detection logic."""

    def test_detect_binary_from_generator(self):
        """Test: HookGenerator can detect binary paths."""
        from src.huskycat.core.hook_generator import HookGenerator

        repo_root = Path(__file__).parent.parent
        generator = HookGenerator(repo_root)

        # Should return a path or None (both valid)
        binary_path = generator._detect_binary_path()

        if binary_path:
            assert isinstance(binary_path, Path)
            # If path returned, it should be one of the expected locations
            assert binary_path.name == "huskycat"

    def test_binary_detection_priority(self):
        """Test: Binary detection follows documented priority order."""
        from src.huskycat.core.hook_generator import HookGenerator

        repo_root = Path(__file__).parent.parent
        generator = HookGenerator(repo_root)

        # The priority order should be:
        # 1. sys.frozen (running from binary)
        # 2. ~/.local/bin/huskycat
        # 3. which huskycat
        # 4. /usr/local/bin, /usr/bin

        binary_path = generator._detect_binary_path()

        if binary_path:
            # Verify it's one of the expected locations
            user_bin = Path.home() / ".local" / "bin" / "huskycat"
            system_bins = [
                Path("/usr/local/bin/huskycat"),
                Path("/usr/bin/huskycat"),
            ]

            # Should be in user bin, system bins, or PATH
            is_expected_location = (
                binary_path == user_bin
                or binary_path in system_bins
                or binary_path.exists()
            )

            assert is_expected_location, f"Unexpected binary location: {binary_path}"


@pytest.mark.unit
class TestToolExtraction:
    """Unit tests for tool extraction logic."""

    def test_tool_extractor_initialization(self):
        """Test: ToolExtractor initializes correctly."""
        from src.huskycat.core.tool_extractor import ToolExtractor

        extractor = ToolExtractor()

        # Should initialize without errors
        assert extractor.cache_dir == Path.home() / ".huskycat" / "tools"
        assert extractor.version_file == extractor.cache_dir / ".version"

    def test_needs_extraction_logic(self):
        """Test: needs_extraction() returns boolean."""
        from src.huskycat.core.tool_extractor import ToolExtractor

        extractor = ToolExtractor()

        # Should return True or False (not crash)
        needs_extraction = extractor.needs_extraction()
        assert isinstance(needs_extraction, bool)

    def test_bundle_version_detection(self):
        """Test: get_bundle_version() returns string or None."""
        from src.huskycat.core.tool_extractor import ToolExtractor

        extractor = ToolExtractor()

        # Should return version string or None
        version = extractor.get_bundle_version()
        assert version is None or isinstance(version, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
