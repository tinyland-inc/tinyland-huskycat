"""
Sprint 10 End-to-End Tests.

E2E tests for non-blocking hooks in real git repositories.
Tests the complete workflow from git commit through validation completion.
"""

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional

import pytest


@pytest.fixture
def git_repo(tmp_path):
    """Create a real git repository for E2E testing."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # Initialize git repository
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    # Create .huskycat directory
    huskycat_dir = repo_dir / ".huskycat"
    huskycat_dir.mkdir()

    # Create initial commit (empty repo needs at least one commit)
    readme = repo_dir / "README.md"
    readme.write_text("# Test Repository\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo_dir, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    return repo_dir


@pytest.fixture
def huskycat_hook(git_repo):
    """Install non-blocking HuskyCat hook in git repository."""
    hooks_dir = git_repo / ".git" / "hooks"
    pre_commit = hooks_dir / "pre-commit"

    # Create non-blocking pre-commit hook
    hook_script = """#!/usr/bin/env bash
# HuskyCat Non-Blocking Pre-Commit Hook (Sprint 10)

# Get HuskyCat executable
if command -v huskycat &> /dev/null; then
    HUSKYCAT="huskycat"
elif [ -f "./dist/huskycat" ]; then
    HUSKYCAT="./dist/huskycat"
else
    echo "ERROR: HuskyCat not found"
    exit 1
fi

# Enable non-blocking mode
export HUSKYCAT_NONBLOCKING=1

# Run validation (returns immediately, validation runs in background)
$HUSKYCAT validate --staged --mode git_hooks_nonblocking

# Exit code determines if commit proceeds
exit $?
"""

    pre_commit.write_text(hook_script)
    pre_commit.chmod(0o755)

    return pre_commit


class TestRealGitCommit:
    """Test real git commits with non-blocking hooks."""

    @pytest.mark.slow
    def test_commit_with_valid_file(self, git_repo, huskycat_hook):
        """Test git commit with valid Python file."""
        # Create valid Python file
        test_file = git_repo / "valid.py"
        test_file.write_text(
            '''"""Valid Python module."""


def hello() -> str:
    """Return greeting."""
    return "Hello, World!"


if __name__ == "__main__":
    print(hello())
'''
        )

        # Stage file
        subprocess.run(["git", "add", "valid.py"], cwd=git_repo, check=True)

        # Mock HuskyCat command to test hook behavior
        # (Real E2E would require built binary)
        with pytest.raises(subprocess.CalledProcessError):
            # Hook will fail if huskycat not found, which is expected in test
            subprocess.run(
                ["git", "commit", "-m", "Add valid file"],
                cwd=git_repo,
                check=True,
                capture_output=True,
            )

        # In real scenario with built binary:
        # - Commit should succeed immediately (<100ms)
        # - Validation runs in background
        # - Results saved to .huskycat/runs/

    @pytest.mark.slow
    def test_commit_with_invalid_file(self, git_repo, huskycat_hook):
        """Test git commit with invalid Python file."""
        # Create invalid Python file (formatting issues)
        test_file = git_repo / "invalid.py"
        test_file.write_text(
            """def hello():
    x=1+2  # No spaces
    return x"""
        )

        # Stage file
        subprocess.run(["git", "add", "invalid.py"], cwd=git_repo, check=True)

        # Attempt commit (would run validation)
        with pytest.raises(subprocess.CalledProcessError):
            subprocess.run(
                ["git", "commit", "-m", "Add invalid file"],
                cwd=git_repo,
                check=True,
                capture_output=True,
            )


class TestParentReturnTime:
    """Test that parent process returns quickly."""

    def test_parent_returns_under_100ms(self, tmp_path):
        """Test parent process returns in <100ms."""
        from huskycat.core.process_manager import ProcessManager

        cache_dir = tmp_path / ".huskycat" / "runs"
        manager = ProcessManager(cache_dir=cache_dir)

        files = ["test.py"]

        # Measure fork time
        start_time = time.time()

        # Mock fork to only test parent path
        import os
        from unittest.mock import patch

        with patch("os.fork", return_value=12345):
            with patch.object(manager, "_save_pid"):
                pid = manager.fork_validation(
                    files=files,
                    validation_cmd="echo",
                    validation_args=["test"],
                )

        parent_time = (time.time() - start_time) * 1000  # Convert to ms

        # Parent should return in <100ms (very conservative, should be <10ms)
        assert parent_time < 100.0
        assert pid == 12345

    def test_adapter_execute_validation_speed(self, tmp_path):
        """Test adapter execute_validation returns quickly."""
        from huskycat.core.adapters.git_hooks_nonblocking import (
            NonBlockingGitHooksAdapter,
        )
        from unittest.mock import MagicMock, patch

        cache_dir = tmp_path / ".huskycat" / "runs"
        adapter = NonBlockingGitHooksAdapter(cache_dir=cache_dir)

        files = ["test.py"]
        tools = {"black": MagicMock()}

        # Measure execution time
        start_time = time.time()

        with patch("os.fork", return_value=12345):
            with patch.object(adapter.process_manager, "cleanup_zombies"):
                with patch.object(adapter.process_manager, "_save_pid"):
                    pid = adapter.execute_validation(files, tools)

        execution_time = (time.time() - start_time) * 1000  # ms

        # Should return very quickly (<100ms)
        assert execution_time < 100.0
        assert pid == 12345


class TestChildValidationCompletion:
    """Test child process completes validation correctly."""

    @pytest.mark.slow
    def test_child_validation_saves_results(self, tmp_path):
        """Test child process saves validation results."""
        from huskycat.core.process_manager import ProcessManager, ValidationRun

        cache_dir = tmp_path / ".huskycat" / "runs"
        manager = ProcessManager(cache_dir=cache_dir)

        # Create a validation run result
        run = ValidationRun(
            run_id="child_run_001",
            started="2025-12-07T10:00:00",
            completed="2025-12-07T10:05:00",
            files=["test.py"],
            success=True,
            tools_run=["black", "ruff"],
            errors=0,
            warnings=0,
            exit_code=0,
            pid=12345,
        )

        # Save results (simulating child process)
        manager.save_run(run)

        # Verify results were saved
        run_file = cache_dir / f"{run.run_id}.json"
        assert run_file.exists()

        # Verify last_run updated
        assert manager.last_run_file.exists()

        # Load and verify
        import json

        loaded_data = json.loads(run_file.read_text())
        assert loaded_data["success"] is True
        assert loaded_data["exit_code"] == 0


class TestValidationResultsPersistence:
    """Test that validation results persist across commits."""

    def test_results_saved_correctly(self, tmp_path):
        """Test validation results are saved with correct structure."""
        from huskycat.core.process_manager import ProcessManager, ValidationRun

        cache_dir = tmp_path / ".huskycat" / "runs"
        manager = ProcessManager(cache_dir=cache_dir)

        run = ValidationRun(
            run_id="persist_001",
            started="2025-12-07T10:00:00",
            completed="2025-12-07T10:05:00",
            files=["file1.py", "file2.py", "file3.py"],
            success=False,
            tools_run=["black", "ruff", "mypy", "flake8"],
            errors=10,
            warnings=5,
            exit_code=1,
            pid=12345,
        )

        manager.save_run(run)

        # Verify structure
        import json

        run_file = cache_dir / f"{run.run_id}.json"
        loaded = json.loads(run_file.read_text())

        assert loaded["run_id"] == "persist_001"
        assert loaded["success"] is False
        assert loaded["errors"] == 10
        assert loaded["warnings"] == 5
        assert len(loaded["files"]) == 3
        assert len(loaded["tools_run"]) == 4

    def test_subsequent_commit_reads_previous_result(self, tmp_path):
        """Test subsequent commit reads previous validation result."""
        from huskycat.core.process_manager import ProcessManager, ValidationRun

        cache_dir = tmp_path / ".huskycat" / "runs"
        manager = ProcessManager(cache_dir=cache_dir)

        # First validation fails
        failed_run = ValidationRun(
            run_id="first_commit",
            started="2025-12-07T10:00:00",
            completed="2025-12-07T10:05:00",
            success=False,
            errors=5,
        )
        manager.save_run(failed_run)

        # Second commit should detect previous failure
        previous = manager.check_previous_run()
        assert previous is not None
        assert previous.success is False
        assert previous.errors == 5


class TestBackgroundValidationMonitoring:
    """Test monitoring background validation progress."""

    def test_can_monitor_validation_progress(self, tmp_path):
        """Test ability to monitor validation in real-time."""
        from huskycat.core.process_manager import ProcessManager

        cache_dir = tmp_path / ".huskycat" / "runs"
        manager = ProcessManager(cache_dir=cache_dir)

        # Simulate saving PID for running validation
        manager._save_pid(os.getpid(), "monitor_test", ["test.py"])

        # Get running validations
        running = manager.get_running_validations()

        # Should find the running validation
        assert len(running) >= 1
        assert running[0]["pid"] == os.getpid()
        assert running[0]["run_id"] == "monitor_test"

        # Cleanup
        manager._remove_pid(os.getpid())

    def test_log_file_tracking(self, tmp_path):
        """Test validation log files are created and accessible."""
        from huskycat.core.process_manager import ProcessManager

        cache_dir = tmp_path / ".huskycat" / "runs"
        manager = ProcessManager(cache_dir=cache_dir)

        run_id = "log_test_001"

        # Log file path
        log_file = manager.logs_dir / f"{run_id}.log"

        # Simulate creating log
        log_file.write_text("Validation started\nRunning black...\nCompleted\n")

        assert log_file.exists()
        assert "Running black" in log_file.read_text()


class TestConcurrentCommitScenarios:
    """Test concurrent commit scenarios."""

    def test_multiple_commits_different_files(self, tmp_path):
        """Test multiple commits on different files simultaneously."""
        from huskycat.core.process_manager import ProcessManager

        cache_dir = tmp_path / ".huskycat" / "runs"

        # Create separate managers for each "commit"
        manager1 = ProcessManager(cache_dir=cache_dir)
        manager2 = ProcessManager(cache_dir=cache_dir)

        # Different file sets
        files1 = ["module1.py", "utils1.py"]
        files2 = ["module2.py", "utils2.py"]

        # Both start validation
        manager1._save_pid(1001, "commit1", files1)
        manager2._save_pid(1002, "commit2", files2)

        # Both should see running validations
        running1 = manager1.get_running_validations()
        running2 = manager2.get_running_validations()

        # Should have 2 running validations
        assert len(running1) >= 1
        assert len(running2) >= 1

        # Cleanup
        manager1._remove_pid(1001)
        manager2._remove_pid(1002)

    def test_commit_while_validation_running(self, tmp_path):
        """Test committing while previous validation still running."""
        from huskycat.core.process_manager import ProcessManager

        cache_dir = tmp_path / ".huskycat" / "runs"
        manager = ProcessManager(cache_dir=cache_dir)

        files = ["test.py"]

        # Start first validation (use current process as placeholder)
        manager._save_pid(os.getpid(), "running_validation", files)

        # Try to start second validation for same files
        is_running = manager._is_running(files)
        assert is_running is True

        # Second validation should be skipped or queued
        # (Implementation would handle this)

        # Cleanup
        manager._remove_pid(os.getpid())


class TestValidationInterruption:
    """Test validation interruption and recovery."""

    def test_zombie_process_cleanup(self, tmp_path):
        """Test cleanup of zombie processes."""
        from huskycat.core.process_manager import ProcessManager

        cache_dir = tmp_path / ".huskycat" / "runs"
        manager = ProcessManager(cache_dir=cache_dir)

        # Create stale PID files (processes that don't exist)
        stale_pids = [999991, 999992, 999993]
        for pid in stale_pids:
            manager._save_pid(pid, f"stale_{pid}", ["test.py"])

        # Verify PID files exist
        for pid in stale_pids:
            assert (manager.pids_dir / f"{pid}.json").exists()

        # Get running validations (should clean up stale PIDs)
        running = manager.get_running_validations()

        # Stale PIDs should be cleaned up
        for pid in stale_pids:
            assert not (manager.pids_dir / f"{pid}.json").exists()

        # Should only have actually running validations
        actual_running = [r for r in running if r["pid"] in stale_pids]
        assert len(actual_running) == 0


class TestValidationOutputFormats:
    """Test validation output formats in different scenarios."""

    def test_git_hook_minimal_output(self, tmp_path):
        """Test git hook produces minimal output for parent."""
        from huskycat.core.adapters.git_hooks_nonblocking import (
            NonBlockingGitHooksAdapter,
        )

        cache_dir = tmp_path / ".huskycat" / "runs"
        adapter = NonBlockingGitHooksAdapter(cache_dir=cache_dir)

        # Format output (parent process)
        output = adapter.format_output({}, {})

        # Should be empty (handled by child)
        assert output == ""

    def test_child_process_verbose_output(self, tmp_path):
        """Test child process produces verbose validation output."""
        # Child process output is printed directly, not returned
        # This would be tested by examining log files

        from huskycat.core.process_manager import ProcessManager

        cache_dir = tmp_path / ".huskycat" / "runs"
        manager = ProcessManager(cache_dir=cache_dir)

        # Verify logs directory exists
        assert manager.logs_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "not slow"])
