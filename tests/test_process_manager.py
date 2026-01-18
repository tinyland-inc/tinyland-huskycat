"""
Unit tests for ProcessManager.

Tests fork-based validation, result caching, PID management,
and previous failure handling.
"""

import json
import os
import pytest
import time
from datetime import datetime, timedelta
from pathlib import Path

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


def test_validation_run_dataclass():
    """Test ValidationRun dataclass initialization."""
    run = ValidationRun(
        run_id="test_run_001",
        started="2025-12-07T10:00:00",
        files=["file1.py", "file2.py"],
        tools_run=["black", "ruff"],
        errors=0,
        warnings=2,
    )

    assert run.run_id == "test_run_001"
    assert len(run.files) == 2
    assert len(run.tools_run) == 2
    assert run.errors == 0
    assert run.warnings == 2
    assert run.success is False  # Default
    assert run.completed is None


def test_validation_run_post_init():
    """Test ValidationRun post_init defaults."""
    run = ValidationRun(run_id="test_run", started="2025-12-07T10:00:00")

    assert run.files == []
    assert run.tools_run == []


def test_process_manager_init(process_manager, temp_cache_dir):
    """Test ProcessManager initialization."""
    assert process_manager.cache_dir == temp_cache_dir
    assert process_manager.cache_dir.exists()
    assert process_manager.pids_dir.exists()
    assert process_manager.logs_dir.exists()


def test_save_and_load_run(process_manager):
    """Test saving and loading validation runs."""
    run = ValidationRun(
        run_id="test_save_001",
        started=datetime.now().isoformat(),
        completed=datetime.now().isoformat(),
        files=["test.py"],
        success=True,
        tools_run=["black"],
        errors=0,
        warnings=0,
        exit_code=0,
    )

    # Save run
    process_manager.save_run(run)

    # Verify file exists
    run_file = process_manager.cache_dir / f"{run.run_id}.json"
    assert run_file.exists()

    # Verify last_run updated
    assert process_manager.last_run_file.exists()

    # Load and verify
    loaded_data = json.loads(run_file.read_text())
    loaded_run = ValidationRun(**loaded_data)

    assert loaded_run.run_id == run.run_id
    assert loaded_run.success == run.success
    assert loaded_run.errors == run.errors


def test_check_previous_run_no_failure(process_manager):
    """Test check_previous_run returns None when no previous failure."""
    # No runs yet
    assert process_manager.check_previous_run() is None

    # Successful run
    run = ValidationRun(
        run_id="success_run",
        started=datetime.now().isoformat(),
        completed=datetime.now().isoformat(),
        success=True,
        errors=0,
    )
    process_manager.save_run(run)

    # Should return None for successful run
    assert process_manager.check_previous_run() is None


def test_check_previous_run_with_failure(process_manager):
    """Test check_previous_run returns failed run."""
    # Failed run
    run = ValidationRun(
        run_id="failed_run",
        started=datetime.now().isoformat(),
        completed=datetime.now().isoformat(),
        success=False,
        errors=5,
        warnings=2,
        exit_code=1,
        tools_run=["black", "ruff", "mypy"],
    )
    process_manager.save_run(run)

    # Should return the failed run
    previous = process_manager.check_previous_run()
    assert previous is not None
    assert previous.run_id == run.run_id
    assert previous.success is False
    assert previous.errors == 5


def test_save_and_remove_pid(process_manager):
    """Test PID file management."""
    pid = 12345
    run_id = "test_pid_run"
    files = ["test.py"]

    # Save PID
    process_manager._save_pid(pid, run_id, files)

    pid_file = process_manager.pids_dir / f"{pid}.json"
    assert pid_file.exists()

    # Load and verify
    data = json.loads(pid_file.read_text())
    assert data["pid"] == pid
    assert data["run_id"] == run_id
    assert data["files"] == files

    # Remove PID
    process_manager._remove_pid(pid)
    assert not pid_file.exists()


def test_get_running_validations_empty(process_manager):
    """Test get_running_validations with no running processes."""
    running = process_manager.get_running_validations()
    assert running == []


def test_get_running_validations_with_stale_pids(process_manager):
    """Test get_running_validations cleans up stale PIDs."""
    # Create a PID for a process that doesn't exist
    fake_pid = 999999
    process_manager._save_pid(fake_pid, "stale_run", ["test.py"])

    # Should clean up the stale PID
    running = process_manager.get_running_validations()
    assert running == []

    # PID file should be removed
    pid_file = process_manager.pids_dir / f"{fake_pid}.json"
    assert not pid_file.exists()


def test_is_running_false(process_manager):
    """Test _is_running returns False when no validations running."""
    assert process_manager._is_running(["test.py"]) is False


def test_is_process_alive(process_manager):
    """Test _is_process_alive for current and non-existent processes."""
    # Current process should be alive
    assert process_manager._is_process_alive(os.getpid()) is True

    # Non-existent PID should not be alive
    assert process_manager._is_process_alive(999999) is False


def test_format_elapsed_time(process_manager):
    """Test _format_elapsed_time produces readable strings."""
    # Seconds
    elapsed = timedelta(seconds=30)
    assert "30 seconds ago" == process_manager._format_elapsed_time(elapsed)

    # Minutes
    elapsed = timedelta(minutes=5)
    assert "5 minutes ago" == process_manager._format_elapsed_time(elapsed)

    # Hours
    elapsed = timedelta(hours=2)
    assert "2 hours ago" == process_manager._format_elapsed_time(elapsed)

    # Days
    elapsed = timedelta(days=3)
    assert "3 days ago" == process_manager._format_elapsed_time(elapsed)


def test_get_run_history(process_manager):
    """Test get_run_history returns recent runs."""
    # Create several runs
    for i in range(5):
        run = ValidationRun(
            run_id=f"history_run_{i:03d}",
            started=datetime.now().isoformat(),
            completed=datetime.now().isoformat(),
            success=(i % 2 == 0),
            errors=i,
        )
        process_manager.save_run(run)
        time.sleep(0.01)  # Ensure different mtimes

    # Get history
    history = process_manager.get_run_history(limit=3)

    # Should have at least 2 runs (last_run.json might be filtered out)
    assert len(history) >= 2
    # Should be most recent first
    assert history[0].run_id == "history_run_004"


def test_cleanup_old_runs(process_manager):
    """Test cleanup_old_runs removes old files."""
    # Create an old run by manipulating file mtime
    old_run = ValidationRun(
        run_id="old_run_001",
        started=datetime.now().isoformat(),
        completed=datetime.now().isoformat(),
        success=True,
    )
    process_manager.save_run(old_run)

    run_file = process_manager.cache_dir / f"{old_run.run_id}.json"

    # Set mtime to 10 days ago
    old_time = time.time() - (10 * 86400)
    os.utime(run_file, (old_time, old_time))

    # Create a recent run
    recent_run = ValidationRun(
        run_id="recent_run_001",
        started=datetime.now().isoformat(),
        completed=datetime.now().isoformat(),
        success=True,
    )
    process_manager.save_run(recent_run)

    # Cleanup runs older than 7 days
    process_manager.cleanup_old_runs(max_age_days=7)

    # Old run should be removed
    assert not run_file.exists()

    # Recent run should still exist
    recent_file = process_manager.cache_dir / f"{recent_run.run_id}.json"
    assert recent_file.exists()


def test_clear_last_run(process_manager):
    """Test _clear_last_run removes last_run.json."""
    # Create a run
    run = ValidationRun(
        run_id="clear_test", started=datetime.now().isoformat(), success=False, errors=1
    )
    process_manager.save_run(run)

    assert process_manager.last_run_file.exists()

    # Clear it
    process_manager._clear_last_run()

    assert not process_manager.last_run_file.exists()


def test_should_proceed_with_commit_no_failure(temp_cache_dir):
    """Test should_proceed_with_commit with no previous failure."""
    # No previous runs - should proceed
    assert should_proceed_with_commit(temp_cache_dir) is True

    # Successful previous run - should proceed
    manager = ProcessManager(temp_cache_dir)
    run = ValidationRun(
        run_id="success_commit",
        started=datetime.now().isoformat(),
        completed=datetime.now().isoformat(),
        success=True,
        errors=0,
    )
    manager.save_run(run)

    assert should_proceed_with_commit(temp_cache_dir) is True


# Note: Testing handle_previous_failure with user input is tricky
# in unit tests. Would require mocking stdin/stdout or using
# integration tests with expect/pexpect.


def test_validation_run_serialization(process_manager):
    """Test ValidationRun can be serialized and deserialized."""
    run = ValidationRun(
        run_id="serialize_test",
        started="2025-12-07T10:00:00",
        completed="2025-12-07T10:05:00",
        files=["test1.py", "test2.py"],
        success=True,
        tools_run=["black", "ruff"],
        errors=0,
        warnings=1,
        exit_code=0,
        pid=12345,
    )

    # Serialize
    from dataclasses import asdict

    data = asdict(run)
    json_str = json.dumps(data)

    # Deserialize
    loaded_data = json.loads(json_str)
    loaded_run = ValidationRun(**loaded_data)

    assert loaded_run.run_id == run.run_id
    assert loaded_run.files == run.files
    assert loaded_run.tools_run == run.tools_run
    assert loaded_run.success == run.success
    assert loaded_run.exit_code == run.exit_code


def test_validation_run_with_error_details():
    """Test ValidationRun with error_details and warning_details fields."""
    error_details = [
        {
            "file": "test.py",
            "line": 10,
            "tool": "ruff",
            "message": "Unused import",
            "severity": "error",
        },
        {
            "file": "test2.py",
            "line": 25,
            "tool": "mypy",
            "message": "Incompatible types",
            "severity": "error",
            "column": 5,
        },
    ]
    warning_details = [
        {
            "file": "test.py",
            "line": 15,
            "tool": "flake8",
            "message": "Line too long",
            "severity": "warning",
        },
    ]

    run = ValidationRun(
        run_id="details_test",
        started="2025-12-07T10:00:00",
        files=["test.py", "test2.py"],
        tools_run=["ruff", "mypy", "flake8"],
        errors=2,
        warnings=1,
        error_details=error_details,
        warning_details=warning_details,
    )

    assert len(run.error_details) == 2
    assert len(run.warning_details) == 1
    assert run.error_details[0]["tool"] == "ruff"
    assert run.error_details[1]["line"] == 25
    assert run.warning_details[0]["severity"] == "warning"


def test_validation_run_error_details_default():
    """Test ValidationRun error_details defaults to empty list."""
    run = ValidationRun(run_id="default_test", started="2025-12-07T10:00:00")

    assert run.error_details == []
    assert run.warning_details == []


def test_process_manager_results_dir(process_manager):
    """Test ProcessManager creates results directory."""
    assert process_manager.results_dir.exists()
    # Results dir should be at .huskycat/results (sibling of runs)
    assert process_manager.results_dir.parent == process_manager.cache_dir.parent


def test_save_and_get_detailed_results(process_manager):
    """Test saving and retrieving detailed validation results."""
    run_id = "detailed_test_001"
    results = [
        {
            "tool_name": "black",
            "success": True,
            "duration": 0.5,
            "errors": 0,
            "warnings": 0,
            "output": "",
            "status": "success",
        },
        {
            "tool_name": "ruff",
            "success": False,
            "duration": 0.3,
            "errors": 2,
            "warnings": 1,
            "output": "test.py:10:5: E501 Line too long",
            "error_message": "Found 2 errors",
            "status": "failed",
        },
    ]

    # Save detailed results
    process_manager.save_detailed_results(run_id, [], tool_results=results)

    # Verify file exists
    results_file = process_manager.results_dir / f"{run_id}_results.json"
    assert results_file.exists()

    # Retrieve and verify
    loaded_results = process_manager.get_detailed_results(run_id)
    assert len(loaded_results) == 2
    assert loaded_results[0]["tool_name"] == "black"
    assert loaded_results[0]["success"] is True
    assert loaded_results[1]["tool_name"] == "ruff"
    assert loaded_results[1]["errors"] == 2


def test_get_latest_results(process_manager):
    """Test get_latest_results returns most recent results."""
    # Save multiple runs
    for i in range(3):
        run_id = f"latest_test_{i:03d}"
        results = [
            {
                "tool_name": f"tool_{i}",
                "success": True,
                "duration": 0.1,
                "errors": i,
                "warnings": 0,
                "output": "",
                "status": "success",
            }
        ]
        process_manager.save_detailed_results(run_id, [], tool_results=results)
        time.sleep(0.01)  # Ensure different mtimes

    # Get latest should return last one
    latest = process_manager.get_latest_results()
    assert len(latest) == 1
    assert latest[0]["tool_name"] == "tool_2"
    assert latest[0]["errors"] == 2


def test_get_detailed_results_not_found(process_manager):
    """Test get_detailed_results returns empty list for non-existent run."""
    results = process_manager.get_detailed_results("nonexistent_run_id")
    assert results == []


def test_validation_run_with_error_details_serialization(process_manager):
    """Test ValidationRun with error_details serializes correctly."""
    error_details = [
        {
            "file": "test.py",
            "line": 10,
            "tool": "ruff",
            "message": "Unused import",
            "severity": "error",
        },
    ]

    run = ValidationRun(
        run_id="serialize_details_test",
        started=datetime.now().isoformat(),
        completed=datetime.now().isoformat(),
        files=["test.py"],
        success=False,
        tools_run=["ruff"],
        errors=1,
        warnings=0,
        error_details=error_details,
        warning_details=[],
        exit_code=1,
    )

    # Save run
    process_manager.save_run(run)

    # Verify file exists and load
    run_file = process_manager.cache_dir / f"{run.run_id}.json"
    assert run_file.exists()

    # Load and verify error_details preserved
    loaded_data = json.loads(run_file.read_text())
    loaded_run = ValidationRun(**loaded_data)

    assert len(loaded_run.error_details) == 1
    assert loaded_run.error_details[0]["file"] == "test.py"
    assert loaded_run.error_details[0]["line"] == 10
    assert loaded_run.error_details[0]["tool"] == "ruff"
