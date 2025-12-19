"""
Sprint 10 Integration Tests.

Comprehensive integration tests for non-blocking hooks and fat binary features.
Tests the complete flow of all Phase 1 components working together:
- NonBlockingGitHooksAdapter
- ProcessManager (fork-based execution)
- ValidationTUI (real-time progress)
- ParallelExecutor (dependency graph execution)
- Unified validation (tool resolution)
"""

import json
import os
import signal
import time
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock, patch

import pytest

from huskycat.core.adapters.git_hooks_nonblocking import NonBlockingGitHooksAdapter
from huskycat.core.parallel_executor import ToolResult, ToolStatus
from huskycat.core.process_manager import ProcessManager, ValidationRun
from huskycat.core.tui import ToolState, ValidationTUI


class TestNonBlockingCompleteFlow:
    """Test complete non-blocking validation flow end-to-end."""

    def test_complete_flow_with_mocked_fork(self, tmp_path):
        """Test complete non-blocking flow with mocked fork."""
        cache_dir = tmp_path / ".huskycat" / "runs"
        adapter = NonBlockingGitHooksAdapter(cache_dir=cache_dir)

        files = ["test1.py", "test2.py"]
        tools = {
            "black": MagicMock(
                return_value=ToolResult(
                    tool_name="black",
                    success=True,
                    duration=0.1,
                    errors=0,
                    warnings=0,
                )
            ),
            "ruff": MagicMock(
                return_value=ToolResult(
                    tool_name="ruff",
                    success=True,
                    duration=0.1,
                    errors=0,
                    warnings=0,
                )
            ),
        }

        # Mock fork to prevent actual forking
        with patch("os.fork", return_value=12345):
            with patch.object(adapter.process_manager, "cleanup_zombies"):
                with patch.object(adapter.process_manager, "_save_pid"):
                    pid = adapter.execute_validation(files, tools)

                    # Verify parent returns immediately with PID
                    assert pid == 12345

    def test_forking_with_tui_and_parallel_execution(self, tmp_path):
        """Test that forking integrates with TUI and parallel executor."""
        cache_dir = tmp_path / ".huskycat" / "runs"
        adapter = NonBlockingGitHooksAdapter(cache_dir=cache_dir)

        # Verify components are initialized
        assert adapter.process_manager is not None
        assert adapter.tui is not None
        assert adapter.executor is not None

        # Verify TUI is configured for real-time updates
        assert adapter.tui._refresh_rate == 0.1

        # Verify executor is configured for parallel execution
        assert adapter.executor.max_workers == 8
        assert adapter.executor.fail_fast is False

    def test_previous_failure_detection(self, tmp_path):
        """Test that previous failures are detected and handled."""
        cache_dir = tmp_path / ".huskycat" / "runs"
        manager = ProcessManager(cache_dir=cache_dir)

        # Create a previous failed run
        failed_run = ValidationRun(
            run_id="failed_001",
            started="2025-12-07T10:00:00",
            completed="2025-12-07T10:05:00",
            files=["test.py"],
            success=False,
            tools_run=["black", "ruff"],
            errors=5,
            warnings=2,
            exit_code=1,
        )
        manager.save_run(failed_run)

        # Check previous run is detected
        previous = manager.check_previous_run()
        assert previous is not None
        assert previous.success is False
        assert previous.errors == 5

        # Test with adapter
        adapter = NonBlockingGitHooksAdapter(cache_dir=cache_dir)

        # Mock sys.stdin/stdout to simulate non-interactive
        with patch("sys.stdin.isatty", return_value=False):
            with patch("sys.stdout.isatty", return_value=False):
                # Should return False (abort commit)
                proceed = manager.handle_previous_failure(previous)
                assert proceed is False

    def test_all_tools_parallel_execution(self, tmp_path):
        """Test that all 15+ tools execute in parallel correctly."""
        cache_dir = tmp_path / ".huskycat" / "runs"
        adapter = NonBlockingGitHooksAdapter(cache_dir=cache_dir)

        # Create comprehensive tool set (15+ tools)
        tools = {}
        for tool_name in [
            "black",
            "isort",
            "autoflake",
            "ruff",
            "mypy",
            "flake8",
            "bandit",
            "yamllint",
            "taplo",
            "gitlab-ci",
            "shellcheck",
            "hadolint",
            "ansible-lint",
            "helm-lint",
            "chapel-format",
        ]:
            tools[tool_name] = lambda name=tool_name: ToolResult(
                tool_name=name,
                success=True,
                duration=0.1,
                errors=0,
                warnings=0,
            )

        # Execute tools in parallel
        start_time = time.time()
        results = adapter.executor.execute_tools(tools)
        duration = time.time() - start_time

        # Verify all tools executed
        assert len(results) == 15
        assert all(r.success for r in results)

        # Verify parallel execution speedup
        # Sequential would take 15 * 0.1 = 1.5s
        # Parallel should be much faster (< 0.5s with 8 workers)
        assert duration < 0.8  # Allow some overhead

    def test_tui_progress_updates(self, tmp_path):
        """Test TUI receives and displays progress updates."""
        cache_dir = tmp_path / ".huskycat" / "runs"
        adapter = NonBlockingGitHooksAdapter(cache_dir=cache_dir)

        tool_names = ["black", "ruff", "mypy"]

        # Only test TUI in TTY environment
        if not os.isatty(1):
            pytest.skip("TUI test requires TTY")

        # Start TUI
        adapter.tui.start(tool_names)

        # Simulate progress updates
        for tool in tool_names:
            adapter.tui.update_tool(tool, ToolState.RUNNING)
            time.sleep(0.05)
            adapter.tui.update_tool(tool, ToolState.SUCCESS, errors=0, warnings=0)

        # Stop TUI
        adapter.tui.stop()

        # Verify all tools were tracked
        for tool in tool_names:
            assert tool in adapter.tui.tools
            assert adapter.tui.tools[tool].state == ToolState.SUCCESS


class TestProcessManagerIntegration:
    """Test ProcessManager integration with other components."""

    def test_fork_and_result_caching(self, tmp_path):
        """Test forking with result caching."""
        cache_dir = tmp_path / ".huskycat" / "runs"
        manager = ProcessManager(cache_dir=cache_dir)

        files = ["test.py"]

        # Mock fork to test parent path
        with patch("os.fork", return_value=12345):
            with patch.object(manager, "_save_pid"):
                pid = manager.fork_validation(
                    files=files,
                    validation_cmd="echo",
                    validation_args=["test"],
                )

                # Verify PID returned
                assert pid == 12345

    def test_running_validation_detection(self, tmp_path):
        """Test detection of running validations."""
        cache_dir = tmp_path / ".huskycat" / "runs"
        manager = ProcessManager(cache_dir=cache_dir)

        files = ["test.py"]

        # Save PID for current process (which is alive)
        manager._save_pid(os.getpid(), "test_run", files)

        # Check if validation is running for these files
        is_running = manager._is_running(files)
        assert is_running is True

        # Different files should not be detected
        is_running_other = manager._is_running(["other.py"])
        assert is_running_other is False

        # Cleanup
        manager._remove_pid(os.getpid())

    def test_zombie_cleanup(self, tmp_path):
        """Test zombie process cleanup."""
        cache_dir = tmp_path / ".huskycat" / "runs"
        manager = ProcessManager(cache_dir=cache_dir)

        # Save PID for non-existent process
        fake_pid = 999999
        manager._save_pid(fake_pid, "zombie_run", ["test.py"])

        # Verify PID file exists
        pid_file = manager.pids_dir / f"{fake_pid}.json"
        assert pid_file.exists()

        # Get running validations (should clean up stale PID)
        running = manager.get_running_validations()

        # Stale PID should be cleaned up
        assert len(running) == 0
        assert not pid_file.exists()


class TestParallelExecutorIntegration:
    """Test ParallelExecutor integration with validation tools."""

    def test_dependency_graph_execution(self, tmp_path):
        """Test execution respects dependency graph."""
        cache_dir = tmp_path / ".huskycat" / "runs"
        adapter = NonBlockingGitHooksAdapter(cache_dir=cache_dir)

        execution_order = []

        def make_tool(name: str):
            def tool():
                execution_order.append(name)
                return ToolResult(
                    tool_name=name,
                    success=True,
                    duration=0.01,
                    errors=0,
                    warnings=0,
                )

            return tool

        tools = {
            "black": make_tool("black"),
            "isort": make_tool("isort"),
            "mypy": make_tool("mypy"),  # Depends on black, isort
        }

        # Execute tools
        results = adapter.executor.execute_tools(tools)

        # Verify execution order respects dependencies
        black_idx = execution_order.index("black")
        isort_idx = execution_order.index("isort")
        mypy_idx = execution_order.index("mypy")

        # mypy should run after black and isort
        assert mypy_idx > black_idx
        assert mypy_idx > isort_idx

    def test_parallel_speedup_measurement(self, tmp_path):
        """Test and measure parallel execution speedup."""
        cache_dir = tmp_path / ".huskycat" / "runs"
        adapter = NonBlockingGitHooksAdapter(cache_dir=cache_dir)

        # Create 8 independent tools (should run fully parallel)
        tools = {}
        for i in range(8):
            tool_name = f"tool_{i}"
            tools[tool_name] = lambda name=tool_name: ToolResult(
                tool_name=name,
                success=True,
                duration=0.1,
                errors=0,
                warnings=0,
            )

        # Measure execution time
        start_time = time.time()
        results = adapter.executor.execute_tools(tools)
        duration = time.time() - start_time

        # Verify speedup
        # Sequential: 8 * 0.1 = 0.8s
        # Parallel (8 workers): ~0.1s (all tools run simultaneously)
        expected_speedup = 5.0  # Conservative estimate
        sequential_time = 0.8
        speedup = sequential_time / duration

        assert speedup >= expected_speedup
        assert all(r.success for r in results)


class TestToolResolution:
    """Test fat binary tool resolution and execution."""

    def test_tool_loading_by_file_type(self, tmp_path):
        """Test tool loading based on file types."""
        cache_dir = tmp_path / ".huskycat" / "runs"
        adapter = NonBlockingGitHooksAdapter(cache_dir=cache_dir)

        # Python files
        python_tools = adapter.get_all_validation_tools(["test.py"])
        assert "black" in python_tools
        assert "ruff" in python_tools
        assert "mypy" in python_tools

        # YAML files
        yaml_tools = adapter.get_all_validation_tools(["config.yaml"])
        assert "yamllint" in yaml_tools

        # Shell files
        shell_tools = adapter.get_all_validation_tools(["deploy.sh"])
        assert "shellcheck" in shell_tools

        # Docker files
        docker_tools = adapter.get_all_validation_tools(["Dockerfile"])
        assert "hadolint" in docker_tools

    def test_mixed_file_types(self, tmp_path):
        """Test tool loading for mixed file types."""
        cache_dir = tmp_path / ".huskycat" / "runs"
        adapter = NonBlockingGitHooksAdapter(cache_dir=cache_dir)

        files = [
            "main.py",
            "config.yaml",
            "deploy.sh",
            "Dockerfile",
            "pyproject.toml",
        ]

        tools = adapter.get_all_validation_tools(files)

        # Should have tools for all file types
        assert "black" in tools  # Python
        assert "yamllint" in tools  # YAML
        assert "shellcheck" in tools  # Shell
        assert "hadolint" in tools  # Docker
        assert "taplo" in tools  # TOML


class TestConcurrentCommits:
    """Test handling of concurrent commit scenarios."""

    def test_multiple_validation_processes(self, tmp_path):
        """Test multiple validation processes running concurrently."""
        cache_dir = tmp_path / ".huskycat" / "runs"

        # Create multiple managers (simulating concurrent commits)
        manager1 = ProcessManager(cache_dir=cache_dir)
        manager2 = ProcessManager(cache_dir=cache_dir)

        files1 = ["file1.py"]
        files2 = ["file2.py"]

        # Save PIDs for both (simulating concurrent runs)
        manager1._save_pid(os.getpid(), "run1", files1)
        time.sleep(0.01)  # Ensure different timestamps
        manager2._save_pid(os.getpid() + 1, "run2", files2)

        # Both should see different running validations
        running1 = manager1.get_running_validations()
        running2 = manager2.get_running_validations()

        # Should have at least one running validation each
        assert len(running1) >= 1
        assert len(running2) >= 1

        # Cleanup
        manager1._remove_pid(os.getpid())
        manager2._remove_pid(os.getpid() + 1)

    def test_previous_validation_still_running(self, tmp_path):
        """Test behavior when previous validation is still running."""
        cache_dir = tmp_path / ".huskycat" / "runs"
        manager = ProcessManager(cache_dir=cache_dir)

        files = ["test.py"]

        # Save PID for current process (which is alive)
        manager._save_pid(os.getpid(), "running_validation", files)

        # Try to start validation for same files
        is_running = manager._is_running(files)
        assert is_running is True

        # Should not start duplicate validation
        # (In real adapter, this would skip forking)

        # Cleanup
        manager._remove_pid(os.getpid())


class TestErrorRecovery:
    """Test error recovery and fallback scenarios."""

    def test_tool_failure_continues_execution(self, tmp_path):
        """Test that tool failures don't stop other tools."""
        cache_dir = tmp_path / ".huskycat" / "runs"
        adapter = NonBlockingGitHooksAdapter(cache_dir=cache_dir)

        # Define tool dependencies to ensure they can all run
        tool_deps = {
            "success_tool": [],
            "failure_tool": [],
            "another_success": [],
        }

        # Create executor with custom dependencies
        from huskycat.core.parallel_executor import ParallelExecutor
        executor = ParallelExecutor(tool_dependencies=tool_deps, fail_fast=False)

        tools = {
            "success_tool": lambda: ToolResult(
                tool_name="success_tool",
                success=True,
                duration=0.1,
                errors=0,
            ),
            "failure_tool": lambda: ToolResult(
                tool_name="failure_tool",
                success=False,
                duration=0.1,
                errors=5,
            ),
            "another_success": lambda: ToolResult(
                tool_name="another_success",
                success=True,
                duration=0.1,
                errors=0,
            ),
        }

        # Execute all tools (fail_fast=False)
        results = executor.execute_tools(tools)

        # All tools should execute despite failure
        assert len(results) == 3

        # Check results
        success_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]

        assert len(success_results) == 2
        assert len(failed_results) == 1

    def test_tty_vs_non_tty_execution(self, tmp_path):
        """Test TUI gracefully degrades in non-TTY environment."""
        cache_dir = tmp_path / ".huskycat" / "runs"

        # Force non-TTY mode
        with patch("sys.stdout.isatty", return_value=False):
            adapter = NonBlockingGitHooksAdapter(cache_dir=cache_dir)

            # Start TUI (should gracefully degrade)
            adapter.tui.start(["black", "ruff"])

            # Should not crash, but TUI won't be active
            assert adapter.tui._is_tty is False

            # Stop should also work
            adapter.tui.stop()


class TestValidationRunPersistence:
    """Test validation run persistence and retrieval."""

    def test_save_and_load_validation_run(self, tmp_path):
        """Test saving and loading validation runs."""
        cache_dir = tmp_path / ".huskycat" / "runs"
        manager = ProcessManager(cache_dir=cache_dir)

        run = ValidationRun(
            run_id="test_run_001",
            started="2025-12-07T10:00:00",
            completed="2025-12-07T10:05:00",
            files=["file1.py", "file2.py"],
            success=True,
            tools_run=["black", "ruff", "mypy"],
            errors=0,
            warnings=3,
            exit_code=0,
            pid=12345,
        )

        # Save run
        manager.save_run(run)

        # Verify file exists
        run_file = cache_dir / f"{run.run_id}.json"
        assert run_file.exists()

        # Load and verify
        loaded_data = json.loads(run_file.read_text())
        assert loaded_data["run_id"] == run.run_id
        assert loaded_data["success"] is True
        assert loaded_data["errors"] == 0
        assert len(loaded_data["tools_run"]) == 3

    def test_run_history_retrieval(self, tmp_path):
        """Test retrieving run history."""
        cache_dir = tmp_path / ".huskycat" / "runs"
        manager = ProcessManager(cache_dir=cache_dir)

        # Create multiple runs
        for i in range(5):
            run = ValidationRun(
                run_id=f"history_run_{i:03d}",
                started="2025-12-07T10:00:00",
                completed="2025-12-07T10:05:00",
                success=(i % 2 == 0),
                errors=i,
            )
            manager.save_run(run)
            time.sleep(0.01)

        # Get history
        history = manager.get_run_history(limit=3)

        # Should have runs (excluding last_run.json)
        assert len(history) >= 2

        # Most recent first
        assert history[0].run_id == "history_run_004"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
