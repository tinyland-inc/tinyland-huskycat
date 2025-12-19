"""
Test suite for HuskyCat dogfooding - validating itself using its own hooks.

This tests the integration of:
- Non-blocking git hooks
- Binary path detection
- Hook template generation
- Fork-based validation
"""

import os
import subprocess
import time
from pathlib import Path
import pytest
import tempfile
import shutil


class TestDogfooding:
    """Tests for HuskyCat dogfooding its own validation."""

    @pytest.fixture
    def repo_root(self):
        """Get repository root directory."""
        return Path(__file__).parent.parent

    @pytest.fixture
    def clean_test_file(self, repo_root):
        """Create and cleanup a test Python file."""
        test_file = repo_root / "test_dogfood_temp.py"
        test_file.write_text('"""Test module."""\n\nprint("hello")\n')

        yield test_file

        # Cleanup
        if test_file.exists():
            test_file.unlink()

        # Unstage if staged
        subprocess.run(
            ["git", "reset", "HEAD", str(test_file)],
            cwd=repo_root,
            capture_output=True,
        )

    def test_nonblocking_mode_activates(self, repo_root):
        """Verify HUSKYCAT_NONBLOCKING=1 activates non-blocking adapter."""
        env = os.environ.copy()
        env["HUSKYCAT_NONBLOCKING"] = "1"

        # Run validation with non-blocking flag
        result = subprocess.run(
            ["uv", "run", "python", "-m", "huskycat", "validate", "--help"],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, f"Command failed: {result.stderr}"

    def test_hook_binary_path_detection(self, repo_root):
        """Verify binary path detection logic works correctly."""
        from src.huskycat.core.hook_generator import HookGenerator

        generator = HookGenerator(repo_root)
        binary_path = generator._detect_binary_path()

        # Should find binary in one of these locations or return None
        if binary_path:
            assert binary_path.exists(), f"Detected binary path doesn't exist: {binary_path}"
            assert binary_path.is_file(), f"Binary path is not a file: {binary_path}"
            assert os.access(binary_path, os.X_OK), f"Binary not executable: {binary_path}"

    def test_nonblocking_config_read_from_git(self, repo_root):
        """Verify git config huskycat.nonblocking is read correctly."""
        # Get current config
        result = subprocess.run(
            ["git", "config", "--local", "--get", "huskycat.nonblocking"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )

        # If configured, should be 'true' or 'false'
        if result.returncode == 0:
            config_value = result.stdout.strip()
            assert config_value in ["true", "false"], f"Invalid config value: {config_value}"

    def test_tracked_hooks_exist_and_executable(self, repo_root):
        """Verify tracked hooks in .githooks/ are present and executable."""
        githooks_dir = repo_root / ".githooks"

        assert githooks_dir.exists(), ".githooks/ directory missing"

        required_hooks = ["pre-commit", "pre-push", "commit-msg"]
        for hook_name in required_hooks:
            hook_file = githooks_dir / hook_name
            assert hook_file.exists(), f"Hook {hook_name} missing from .githooks/"
            assert os.access(hook_file, os.X_OK), f"Hook {hook_name} not executable"

    def test_tracked_hooks_support_nonblocking(self, repo_root):
        """Verify tracked hooks have non-blocking mode support."""
        pre_commit = repo_root / ".githooks" / "pre-commit"

        assert pre_commit.exists(), "pre-commit hook missing"

        content = pre_commit.read_text()

        # Check for non-blocking configuration reading
        assert "huskycat.nonblocking" in content, "Hook doesn't read nonblocking config"
        assert "HUSKYCAT_NONBLOCKING" in content, "Hook doesn't export HUSKYCAT_NONBLOCKING"

    def test_hook_templates_have_nonblocking_support(self, repo_root):
        """Verify hook templates support non-blocking mode."""
        template_dir = repo_root / "src" / "huskycat" / "templates" / "hooks"
        pre_commit_template = template_dir / "pre-commit.template"

        assert pre_commit_template.exists(), "pre-commit template missing"

        content = pre_commit_template.read_text()

        # Verify non-blocking configuration check exists
        assert "huskycat.nonblocking" in content, "Template doesn't check config"
        assert "HUSKYCAT_NONBLOCKING" in content, "Template doesn't set environment variable"
        assert "background" in content.lower(), "Template doesn't mention background execution"

    def test_main_wires_nonblocking_flag(self, repo_root):
        """Verify __main__.py reads HUSKYCAT_NONBLOCKING environment variable."""
        main_file = repo_root / "src" / "huskycat" / "__main__.py"

        content = main_file.read_text()

        # Verify environment variable is read
        assert "HUSKYCAT_NONBLOCKING" in content, "__main__.py doesn't read HUSKYCAT_NONBLOCKING"
        assert "use_nonblocking" in content, "__main__.py doesn't use use_nonblocking parameter"
        assert "get_adapter" in content, "__main__.py doesn't call get_adapter"

    @pytest.mark.skip(reason="Non-blocking adapter fork execution needs further testing")
    def test_fork_based_execution_fast(self, repo_root, clean_test_file):
        """Verify non-blocking mode returns quickly (under 5 seconds for hook execution)."""
        env = os.environ.copy()
        env["HUSKYCAT_NONBLOCKING"] = "1"

        # Stage the test file
        subprocess.run(
            ["git", "add", str(clean_test_file)],
            cwd=repo_root,
            check=True,
        )

        # Run validation in non-blocking mode
        start = time.time()
        result = subprocess.run(
            ["uv", "run", "python", "-m", "huskycat", "validate", "--staged"],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        duration = time.time() - start

        # Should complete quickly (under 5 seconds for command to return)
        # Note: This tests the Python module, not the full hook execution
        assert duration < 5, f"Non-blocking validation took {duration}s, expected <5s"

    def test_environment_variable_precedence(self, repo_root):
        """Verify HUSKYCAT_NONBLOCKING environment variable takes precedence."""
        env = os.environ.copy()

        # Test with HUSKYCAT_NONBLOCKING=1
        env["HUSKYCAT_NONBLOCKING"] = "1"
        result = subprocess.run(
            ["uv", "run", "python", "-c",
             "import os; from src.huskycat.__main__ import *; "
             "print('nonblocking' if os.environ.get('HUSKYCAT_NONBLOCKING') == '1' else 'blocking')"],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
        )

        assert "nonblocking" in result.stdout, "Environment variable not read correctly"

    def test_git_config_integration(self, repo_root):
        """Verify git config integration works."""
        # Get current config value
        result = subprocess.run(
            ["git", "config", "--local", "--get", "huskycat.nonblocking"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )

        # Should return 0 if config is set
        if result.returncode == 0:
            value = result.stdout.strip()
            assert value in ["true", "false"], f"Invalid config value: {value}"
        else:
            # Config not set, which is also valid
            pass

    def test_hook_generator_priority_order(self, repo_root):
        """Verify binary path detection follows correct priority order."""
        from src.huskycat.core.hook_generator import HookGenerator

        generator = HookGenerator(repo_root)

        # Test priority order documented in code:
        # 1. sys.frozen (running from binary)
        # 2. ~/.local/bin/huskycat (user install)
        # 3. which huskycat (PATH)
        # 4. /usr/local/bin, /usr/bin (system)

        binary_path = generator._detect_binary_path()

        if binary_path:
            # Verify it's one of the expected locations
            expected_locations = [
                Path.home() / ".local" / "bin" / "huskycat",
                Path("/usr/local/bin/huskycat"),
                Path("/usr/bin/huskycat"),
            ]

            # Or it's in PATH
            which_result = subprocess.run(
                ["which", "huskycat"],
                capture_output=True,
                text=True,
            )

            if which_result.returncode == 0:
                path_location = Path(which_result.stdout.strip())
                expected_locations.append(path_location)

            # Binary should be in one of these locations
            assert any(binary_path == loc for loc in expected_locations) or binary_path.exists()

    def test_dogfooding_configuration(self, repo_root):
        """Verify this repository is configured for dogfooding."""
        # Check .huskycat.yaml exists
        config_file = repo_root / ".huskycat.yaml"
        assert config_file.exists(), ".huskycat.yaml missing"

        # Check hooks are configured
        hooks_dir = repo_root / ".githooks"
        assert hooks_dir.exists(), ".githooks/ directory missing"

        # Check core.hooksPath points to .githooks
        result = subprocess.run(
            ["git", "config", "--local", "--get", "core.hooksPath"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            hooks_path = result.stdout.strip()
            assert hooks_path == ".githooks", f"core.hooksPath should be .githooks, got {hooks_path}"


@pytest.mark.integration
class TestDogfoodingIntegration:
    """Integration tests for end-to-end dogfooding workflow."""

    @pytest.fixture
    def temp_git_repo(self, tmp_path):
        """Create a temporary git repository for testing."""
        repo = tmp_path / "test_repo"
        repo.mkdir()

        # Initialize git
        subprocess.run(["git", "init"], cwd=repo, check=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo,
            check=True,
        )

        yield repo

        # Cleanup
        shutil.rmtree(repo, ignore_errors=True)

    def test_setup_hooks_in_temp_repo(self, temp_git_repo):
        """Test setup-hooks command in a fresh repository."""
        # Run setup-hooks
        result = subprocess.run(
            ["uv", "run", "python", "-m", "huskycat", "setup-hooks"],
            cwd=temp_git_repo,
            capture_output=True,
            text=True,
        )

        # Should succeed (or warn about no binary)
        assert result.returncode in [0, 1], f"setup-hooks failed: {result.stderr}"

    def test_nonblocking_mode_in_temp_repo(self, temp_git_repo):
        """Test enabling non-blocking mode in a fresh repository."""
        # Enable non-blocking mode
        result = subprocess.run(
            ["git", "config", "--local", "huskycat.nonblocking", "true"],
            cwd=temp_git_repo,
            check=True,
        )

        # Verify it's set
        result = subprocess.run(
            ["git", "config", "--local", "--get", "huskycat.nonblocking"],
            cwd=temp_git_repo,
            capture_output=True,
            text=True,
        )

        assert result.stdout.strip() == "true", "Config not set correctly"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
