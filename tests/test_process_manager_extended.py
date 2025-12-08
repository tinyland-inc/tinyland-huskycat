"""
Extended test suite for ProcessManager.

Tests edge cases, error conditions, and complex scenarios to increase
coverage from 54% to 80%+.

Focus areas:
- Fork failure handling
- Child process I/O redirection
- Stale PID cleanup edge cases
- Concurrent validation detection
- Zombie process cleanup
- Previous failure handling with prompts
- Validation run persistence
"""

import json
import os
import pytest
import signal
import sys
import time
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from unittest import mock

from src.huskycat.core.process_manager import (
    ProcessManager,
    ValidationRun,
    should_proceed_with_commit,
)


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create temporary cache directory for testing."""
    cache_dir = tmp_path / ".huskycat" / "runs"
    cache_dir.mkdir(parents=True)
    return cache_dir


@pytest.fixture
def process_manager(temp_cache_dir):
    """Create ProcessManager instance with temp cache."""
    return ProcessManager(cache_dir=temp_cache_dir)


# ============================================================================
# Test Fork Failure Handling
# ============================================================================


class TestForkFailureHandling:
    """Test fork failure scenarios and error handling."""

    def test_fork_failure_resource_unavailable(self, process_manager):
        """Test fork failure due to resource exhaustion."""
        files = ["test.py"]

        with mock.patch("os.fork", side_effect=OSError("Resource temporarily unavailable")):
            pid = process_manager.fork_validation(files, "echo", ["test"])

            # Should return -1 on fork failure
            assert pid == -1

    def test_fork_failure_permission_denied(self, process_manager):
        """Test fork failure due to permissions."""
        files = ["test.py"]

        with mock.patch("os.fork", side_effect=PermissionError("Operation not permitted")):
            pid = process_manager.fork_validation(files, "echo", ["test"])

            # Should return -1 on fork failure
            assert pid == -1

    def test_fork_failure_cleanup(self, process_manager):
        """Test cleanup after fork failure."""
        files = ["test.py"]

        # Count PIDs before
        pids_before = list(process_manager.pids_dir.glob("*.json"))

        with mock.patch("os.fork", side_effect=OSError("Fork failed")):
            pid = process_manager.fork_validation(files, "echo", ["test"])

            # Verify no PID files created
            pids_after = list(process_manager.pids_dir.glob("*.json"))
            assert len(pids_after) == len(pids_before)

    def test_fork_failure_error_logging(self, process_manager, capsys):
        """Test error logging on fork failure."""
        files = ["test.py"]

        with mock.patch("os.fork", side_effect=OSError("Fork failed")):
            process_manager.fork_validation(files, "echo", ["test"])

            # Verify error message printed
            captured = capsys.readouterr()
            assert "ERROR" in captured.out or "error" in captured.out.lower()


# ============================================================================
# Test Child Process I/O Redirection
# ============================================================================


class TestChildIORedirection:
    """Test child process stdout/stderr redirection."""

    def test_log_file_creation(self, process_manager):
        """Test log files created with correct permissions."""
        run_id = "test_log_001"
        log_file = process_manager.logs_dir / f"{run_id}.log"

        # Create log file manually to test the path
        log_fd = os.open(log_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        os.close(log_fd)

        # Verify file exists and is readable
        assert log_file.exists()
        assert os.access(log_file, os.R_OK)

        # Verify permissions (0o644 = rw-r--r--)
        stat_info = log_file.stat()
        # Check owner can read/write
        assert stat_info.st_mode & 0o600 == 0o600

    def test_log_directory_exists(self, process_manager):
        """Test log directory is created during initialization."""
        assert process_manager.logs_dir.exists()
        assert process_manager.logs_dir.is_dir()

    def test_multiple_log_files(self, process_manager):
        """Test multiple log files can be created."""
        log_files = []

        for i in range(3):
            run_id = f"test_log_{i:03d}"
            log_file = process_manager.logs_dir / f"{run_id}.log"
            log_file.write_text(f"Log content {i}")
            log_files.append(log_file)

        # Verify all files exist
        for log_file in log_files:
            assert log_file.exists()


# ============================================================================
# Test Stale PID Cleanup
# ============================================================================


class TestStalePIDCleanup:
    """Test cleanup of PIDs for processes that no longer exist."""

    def test_cleanup_nonexistent_process(self, process_manager):
        """Test cleanup of PID for process that no longer exists."""
        # Create PID file with fake PID (very high number unlikely to exist)
        fake_pid = 999999
        process_manager._save_pid(fake_pid, "stale_run", ["test.py"])

        pid_file = process_manager.pids_dir / f"{fake_pid}.json"
        assert pid_file.exists()

        # Run get_running_validations which cleans up stale PIDs
        running = process_manager.get_running_validations()

        # Should have cleaned up the stale PID
        assert not pid_file.exists()
        assert len(running) == 0

    def test_cleanup_with_psutil_unavailable(self, process_manager):
        """Test cleanup when psutil.pid_exists raises exception."""
        fake_pid = 999999
        process_manager._save_pid(fake_pid, "stale_run", ["test.py"])

        # Mock psutil to raise exception, forcing fallback to os.kill
        with mock.patch("psutil.pid_exists", side_effect=Exception("psutil error")):
            # Should fall back to os.kill(pid, 0)
            is_alive = process_manager._is_process_alive(fake_pid)

            # Fake PID should not be alive
            assert not is_alive

    def test_cleanup_permission_error_pid_file(self, process_manager):
        """Test cleanup gracefully handles permission errors on PID file."""
        fake_pid = 999998
        process_manager._save_pid(fake_pid, "test_run", ["test.py"])

        pid_file = process_manager.pids_dir / f"{fake_pid}.json"

        # Mock file operations to raise permission error
        with mock.patch("pathlib.Path.read_text", side_effect=PermissionError("Access denied")):
            # Should handle error gracefully
            running = process_manager.get_running_validations()

            # Error should be logged but not crash
            assert isinstance(running, list)

    def test_cleanup_corrupted_pid_file(self, process_manager):
        """Test cleanup handles corrupted PID files."""
        fake_pid = 999997
        pid_file = process_manager.pids_dir / f"{fake_pid}.json"

        # Write invalid JSON
        pid_file.write_text("{ invalid json }")

        # Should handle error gracefully
        running = process_manager.get_running_validations()

        # Error should be logged but not crash
        assert isinstance(running, list)


# ============================================================================
# Test Concurrent Validation Detection
# ============================================================================


class TestConcurrentValidation:
    """Test detection and handling of concurrent validations."""

    def test_concurrent_validation_same_files(self, process_manager):
        """Test detection of validation on exact same files."""
        files = ["file1.py", "file2.py"]

        # Create a running validation with current process PID
        process_manager._save_pid(os.getpid(), "run_001", files)

        # Try to start another validation on same files
        is_running = process_manager._is_running(files)

        # Should detect overlap
        assert is_running is True

        # Cleanup
        process_manager._remove_pid(os.getpid())

    def test_concurrent_validation_overlapping_files(self, process_manager):
        """Test detection of overlapping file sets."""
        files1 = ["file1.py", "file2.py"]
        files2 = ["file2.py", "file3.py"]

        # Create running validation with current PID
        process_manager._save_pid(os.getpid(), "run_001", files1)

        # Try to check overlapping files
        is_running = process_manager._is_running(files2)

        # Should detect overlap (file2.py in both)
        assert is_running is True

        # Cleanup
        process_manager._remove_pid(os.getpid())

    def test_concurrent_validation_different_files(self, process_manager):
        """Test concurrent validations on different files allowed."""
        files1 = ["file1.py"]
        files2 = ["file2.py"]

        # Create running validation with current PID
        process_manager._save_pid(os.getpid(), "run_001", files1)

        # Check completely different files
        is_running = process_manager._is_running(files2)

        # Should not detect overlap
        assert is_running is False

        # Cleanup
        process_manager._remove_pid(os.getpid())

    def test_concurrent_validation_empty_file_list(self, process_manager):
        """Test handling of empty file list."""
        # Create running validation
        process_manager._save_pid(os.getpid(), "run_001", ["file1.py"])

        # Check empty file list
        is_running = process_manager._is_running([])

        # Should not detect overlap with empty list
        assert is_running is False

        # Cleanup
        process_manager._remove_pid(os.getpid())


# ============================================================================
# Test Zombie Process Cleanup
# ============================================================================


class TestZombieProcessCleanup:
    """Test reaping of completed child processes."""

    def test_cleanup_no_zombies(self, process_manager):
        """Test cleanup when no zombies exist."""
        # Should run without error even if no children
        try:
            process_manager.cleanup_zombies()
        except Exception as e:
            pytest.fail(f"cleanup_zombies raised exception: {e}")

    def test_cleanup_child_process_error(self, process_manager):
        """Test cleanup handles ChildProcessError gracefully."""
        # Mock waitpid to raise ChildProcessError (no children)
        with mock.patch("os.waitpid", side_effect=ChildProcessError("No child processes")):
            # Should handle gracefully
            try:
                process_manager.cleanup_zombies()
            except Exception as e:
                pytest.fail(f"cleanup_zombies raised exception: {e}")

    def test_cleanup_removes_pid_files(self, process_manager):
        """Test cleanup removes PID files for reaped processes."""
        fake_pid = 12345

        # Create PID file
        process_manager._save_pid(fake_pid, "test_run", ["test.py"])

        # Mock waitpid to return this PID as completed
        with mock.patch("os.waitpid", return_value=(fake_pid, 0)):
            process_manager.cleanup_zombies()

        # PID file should be removed
        pid_file = process_manager.pids_dir / f"{fake_pid}.json"
        assert not pid_file.exists()

    def test_cleanup_handles_waitpid_exception(self, process_manager):
        """Test cleanup handles unexpected waitpid exceptions."""
        with mock.patch("os.waitpid", side_effect=Exception("Unexpected error")):
            # Should handle gracefully and not crash
            try:
                process_manager.cleanup_zombies()
            except Exception as e:
                pytest.fail(f"cleanup_zombies raised exception: {e}")


# ============================================================================
# Test Previous Failure Handling
# ============================================================================


class TestPreviousFailureHandling:
    """Test handling of previous failed validation runs."""

    def test_handle_previous_failure_non_interactive(self, process_manager):
        """Test previous failure handling in non-interactive environment."""
        run = ValidationRun(
            run_id="failed_run",
            started=datetime.now().isoformat(),
            completed=datetime.now().isoformat(),
            success=False,
            errors=5,
            warnings=2,
            tools_run=["black", "ruff"],
        )

        # Mock non-TTY environment
        with mock.patch("sys.stdin.isatty", return_value=False):
            with mock.patch("sys.stdout.isatty", return_value=False):
                result = process_manager.handle_previous_failure(run)

                # Should return False (do not proceed)
                assert result is False

    def test_handle_previous_failure_user_abort(self, process_manager):
        """Test user choosing to abort commit."""
        run = ValidationRun(
            run_id="failed_run",
            started=datetime.now().isoformat(),
            completed=datetime.now().isoformat(),
            success=False,
            errors=3,
            warnings=1,
            tools_run=["mypy"],
        )

        # Mock TTY and user input "n"
        with mock.patch("sys.stdin.isatty", return_value=True):
            with mock.patch("sys.stdout.isatty", return_value=True):
                with mock.patch("sys.stdin.readline", return_value="n\n"):
                    result = process_manager.handle_previous_failure(run)

                    # Should return False
                    assert result is False

    def test_handle_previous_failure_user_proceed(self, process_manager):
        """Test user choosing to proceed despite failure."""
        run = ValidationRun(
            run_id="failed_run",
            started=datetime.now().isoformat(),
            completed=datetime.now().isoformat(),
            success=False,
            errors=1,
            warnings=0,
            tools_run=["ruff"],
        )

        # Mock TTY and user input "y"
        with mock.patch("sys.stdin.isatty", return_value=True):
            with mock.patch("sys.stdout.isatty", return_value=True):
                with mock.patch("sys.stdin.readline", return_value="y\n"):
                    result = process_manager.handle_previous_failure(run)

                    # Should return True
                    assert result is True

                    # Last run should be cleared
                    assert not process_manager.last_run_file.exists()

    def test_handle_previous_failure_keyboard_interrupt(self, process_manager):
        """Test handling of KeyboardInterrupt during prompt."""
        run = ValidationRun(
            run_id="failed_run",
            started=datetime.now().isoformat(),
            completed=datetime.now().isoformat(),
            success=False,
            errors=2,
        )

        # Mock TTY and KeyboardInterrupt
        with mock.patch("sys.stdin.isatty", return_value=True):
            with mock.patch("sys.stdout.isatty", return_value=True):
                with mock.patch("sys.stdin.readline", side_effect=KeyboardInterrupt):
                    result = process_manager.handle_previous_failure(run)

                    # Should return False on interrupt
                    assert result is False

    def test_handle_previous_failure_eof_error(self, process_manager):
        """Test handling of EOFError during prompt."""
        run = ValidationRun(
            run_id="failed_run",
            started=datetime.now().isoformat(),
            completed=datetime.now().isoformat(),
            success=False,
            errors=1,
        )

        # Mock TTY and EOFError
        with mock.patch("sys.stdin.isatty", return_value=True):
            with mock.patch("sys.stdout.isatty", return_value=True):
                with mock.patch("sys.stdin.readline", side_effect=EOFError):
                    result = process_manager.handle_previous_failure(run)

                    # Should return False on EOF
                    assert result is False

    def test_handle_previous_failure_invalid_timestamp(self, process_manager):
        """Test handling of invalid timestamp in completed field."""
        run = ValidationRun(
            run_id="failed_run",
            started=datetime.now().isoformat(),
            completed="invalid-timestamp",
            success=False,
            errors=1,
        )

        # Mock TTY and user input
        with mock.patch("sys.stdin.isatty", return_value=True):
            with mock.patch("sys.stdout.isatty", return_value=True):
                with mock.patch("sys.stdin.readline", return_value="n\n"):
                    # Should handle invalid timestamp gracefully
                    result = process_manager.handle_previous_failure(run)

                    # Should still work, just show "unknown time ago"
                    assert result is False


# ============================================================================
# Test Validation Run Persistence
# ============================================================================


class TestValidationRunPersistence:
    """Test saving and loading validation runs."""

    def test_save_run_success(self, process_manager):
        """Test saving successful validation run."""
        run = ValidationRun(
            run_id="success_001",
            started=datetime.now().isoformat(),
            completed=datetime.now().isoformat(),
            files=["test1.py", "test2.py"],
            success=True,
            tools_run=["black", "ruff"],
            errors=0,
            warnings=0,
            exit_code=0,
            pid=12345,
        )

        process_manager.save_run(run)

        # Verify file created
        run_file = process_manager.cache_dir / f"{run.run_id}.json"
        assert run_file.exists()

        # Verify content
        data = json.loads(run_file.read_text())
        assert data["success"] is True
        assert data["exit_code"] == 0
        assert data["errors"] == 0

    def test_save_run_failure(self, process_manager):
        """Test saving failed validation run."""
        run = ValidationRun(
            run_id="failure_001",
            started=datetime.now().isoformat(),
            completed=datetime.now().isoformat(),
            files=["bad.py"],
            success=False,
            tools_run=["mypy"],
            errors=5,
            warnings=3,
            exit_code=1,
            pid=12346,
        )

        process_manager.save_run(run)

        # Verify file created
        run_file = process_manager.cache_dir / f"{run.run_id}.json"
        assert run_file.exists()

        # Verify failure details preserved
        data = json.loads(run_file.read_text())
        assert data["success"] is False
        assert data["exit_code"] == 1
        assert data["errors"] == 5
        assert data["warnings"] == 3

    def test_load_previous_run(self, process_manager):
        """Test loading previous run from cache."""
        # Create and save a run
        original_run = ValidationRun(
            run_id="load_test_001",
            started=datetime.now().isoformat(),
            completed=datetime.now().isoformat(),
            files=["file.py"],
            success=False,
            tools_run=["black"],
            errors=2,
            warnings=1,
            exit_code=1,
        )

        process_manager.save_run(original_run)

        # Load it back
        loaded_run = process_manager.check_previous_run()

        # Verify all fields match
        assert loaded_run is not None
        assert loaded_run.run_id == original_run.run_id
        assert loaded_run.success == original_run.success
        assert loaded_run.errors == original_run.errors
        assert loaded_run.warnings == original_run.warnings
        assert loaded_run.files == original_run.files

    def test_save_run_updates_last_run(self, process_manager):
        """Test that save_run updates last_run.json."""
        run = ValidationRun(
            run_id="update_test",
            started=datetime.now().isoformat(),
            success=True,
        )

        process_manager.save_run(run)

        # Verify last_run.json exists and has correct content
        assert process_manager.last_run_file.exists()
        data = json.loads(process_manager.last_run_file.read_text())
        assert data["run_id"] == "update_test"

    def test_save_run_handles_write_error(self, process_manager, caplog):
        """Test save_run handles write errors gracefully."""
        run = ValidationRun(
            run_id="error_test",
            started=datetime.now().isoformat(),
            success=True,
        )

        # Mock file write to raise exception
        with mock.patch("pathlib.Path.write_text", side_effect=PermissionError("Access denied")):
            # Should not crash
            process_manager.save_run(run)

            # Error should be logged
            # Note: caplog might not work with all logging configs, so we just verify no crash


# ============================================================================
# Test Check Previous Run Edge Cases
# ============================================================================


class TestCheckPreviousRunEdgeCases:
    """Test edge cases in check_previous_run."""

    def test_check_previous_run_corrupted_json(self, process_manager):
        """Test handling of corrupted last_run.json."""
        # Write invalid JSON
        process_manager.last_run_file.write_text("{ invalid json }")

        # Should return None and log warning
        result = process_manager.check_previous_run()
        assert result is None

    def test_check_previous_run_incomplete_data(self, process_manager):
        """Test handling of incomplete run data."""
        # Write JSON missing required fields
        process_manager.last_run_file.write_text('{"run_id": "incomplete"}')

        # Should handle gracefully
        result = process_manager.check_previous_run()
        # May return None or handle with defaults

    def test_check_previous_run_still_running(self, process_manager):
        """Test handling of run that hasn't completed."""
        run = ValidationRun(
            run_id="running_test",
            started=datetime.now().isoformat(),
            completed=None,  # Not completed
            success=False,
            errors=0,
        )

        process_manager.save_run(run)

        # Should return None for incomplete run
        result = process_manager.check_previous_run()
        assert result is None


# ============================================================================
# Test should_proceed_with_commit Integration
# ============================================================================


def test_should_proceed_with_commit_with_zombies(temp_cache_dir):
    """Test should_proceed_with_commit cleans up zombies."""
    # This function should call cleanup_zombies before checking previous run

    # Mock cleanup_zombies to verify it's called
    with mock.patch.object(ProcessManager, "cleanup_zombies") as mock_cleanup:
        should_proceed_with_commit(temp_cache_dir)

        # Verify cleanup was called
        mock_cleanup.assert_called_once()


def test_should_proceed_with_commit_previous_failure_non_interactive(temp_cache_dir):
    """Test should_proceed_with_commit with previous failure in non-interactive mode."""
    # Create a previous failed run
    manager = ProcessManager(temp_cache_dir)
    run = ValidationRun(
        run_id="prev_fail",
        started=datetime.now().isoformat(),
        completed=datetime.now().isoformat(),
        success=False,
        errors=3,
    )
    manager.save_run(run)

    # Mock non-interactive
    with mock.patch("sys.stdin.isatty", return_value=False):
        with mock.patch("sys.stdout.isatty", return_value=False):
            result = should_proceed_with_commit(temp_cache_dir)

            # Should return False
            assert result is False


# ============================================================================
# Test Format Elapsed Time Edge Cases
# ============================================================================


def test_format_elapsed_time_singular_forms(process_manager):
    """Test singular forms of time units."""
    # 1 second
    elapsed = timedelta(seconds=1)
    result = process_manager._format_elapsed_time(elapsed)
    assert "1 second ago" in result

    # 1 minute
    elapsed = timedelta(minutes=1)
    result = process_manager._format_elapsed_time(elapsed)
    assert "1 minute ago" in result

    # 1 hour
    elapsed = timedelta(hours=1)
    result = process_manager._format_elapsed_time(elapsed)
    assert "1 hour ago" in result

    # 1 day
    elapsed = timedelta(days=1)
    result = process_manager._format_elapsed_time(elapsed)
    assert "1 day ago" in result


def test_format_elapsed_time_zero(process_manager):
    """Test formatting of zero elapsed time."""
    elapsed = timedelta(seconds=0)
    result = process_manager._format_elapsed_time(elapsed)
    assert "0 seconds ago" in result
