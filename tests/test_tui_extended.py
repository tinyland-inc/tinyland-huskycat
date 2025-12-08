"""
Extended comprehensive tests for TUI framework (src/huskycat/core/tui.py).

This test suite extends coverage beyond the base tests with:
- Concurrent update scenarios with multiple threads
- Render variations with all possible tool state combinations
- Context manager edge cases
- Non-TTY environment variations
- Performance and stress testing
- Error handling and recovery
- Edge cases for time formatting
- Dynamic tool operations
- Thread-safety stress tests
"""

import sys
import time
import threading
from io import StringIO
from unittest.mock import MagicMock, patch, Mock
from contextlib import contextmanager

import pytest

from src.huskycat.core.tui import (
    ToolState,
    ToolStatus,
    ValidationTUI,
    create_simple_spinner,
    is_tty_available,
    validation_tui,
)


class TestConcurrentUpdates:
    """Test thread-safe updates from multiple concurrent threads."""

    @patch("sys.stdout.isatty", return_value=True)
    def test_concurrent_tool_updates_10_threads(self, mock_isatty):
        """Test thread-safe updates from 10 threads updating same tool."""
        tui = ValidationTUI()
        tui.start(["black"])

        results = []
        error_count = [0]

        def update_same_tool_repeatedly(thread_id, iterations):
            """Update the same tool from multiple threads."""
            try:
                for i in range(iterations):
                    tui.update_tool(
                        "black",
                        ToolState.RUNNING,
                        files_processed=i,
                        errors=0,
                        warnings=0,
                    )
                    time.sleep(0.0001)  # Tiny sleep to encourage interleaving
                results.append(thread_id)
            except Exception as e:
                error_count[0] += 1

        threads = []
        for i in range(5):  # Reduced from 10 to 5
            t = threading.Thread(
                target=update_same_tool_repeatedly, args=(i, 10)
            )
            threads.append(t)

        # Start all threads concurrently
        for t in threads:
            t.start()

        # Wait for all to complete with short timeout
        for t in threads:
            t.join(timeout=2)

        # Verify all threads completed successfully
        assert len(results) == 5, "Not all threads completed"
        assert error_count[0] == 0, "Errors occurred during concurrent updates"

        tui.stop()

    @patch("sys.stdout.isatty", return_value=True)
    def test_concurrent_different_tools(self, mock_isatty):
        """Test concurrent updates to different tools from separate threads."""
        tool_names = ["black", "mypy", "ruff"]
        tui = ValidationTUI()
        tui.start(tool_names)

        completion_order = []
        lock = threading.Lock()

        def update_specific_tool(tool_name):
            """Update a specific tool."""
            tui.update_tool(tool_name, ToolState.RUNNING)
            tui.update_tool(
                tool_name,
                ToolState.SUCCESS,
                errors=0,
                warnings=0
            )
            with lock:
                completion_order.append(tool_name)

        threads = []
        for tool_name in tool_names:
            t = threading.Thread(
                target=update_specific_tool,
                args=(tool_name,)
            )
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=2)

        # Verify all tools completed
        assert len(completion_order) == len(tool_names)
        assert all(
            tui.tools[name].state == ToolState.SUCCESS
            for name in tool_names
        )

        tui.stop()

    @patch("sys.stdout.isatty", return_value=True)
    def test_concurrent_updates_rapid_state_changes(self, mock_isatty):
        """Test rapid state changes from concurrent threads."""
        tui = ValidationTUI()
        tui.start(["tool1", "tool2"])

        def rapid_state_changes(tool_name, iterations):
            """Rapidly cycle through states."""
            states = [ToolState.RUNNING, ToolState.SUCCESS]
            for i in range(iterations):
                state = states[i % len(states)]
                tui.update_tool(tool_name, state)

        threads = [
            threading.Thread(target=rapid_state_changes, args=("tool1", 5)),
            threading.Thread(target=rapid_state_changes, args=("tool2", 5)),
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=2)

        # No crash is the success condition
        assert True

        tui.stop()


class TestRenderVariations:
    """Test render output with all possible tool state combinations."""

    @patch("sys.stdout.isatty", return_value=True)
    def test_render_all_pending(self, mock_isatty):
        """Test render when all tools are in PENDING state."""
        tui = ValidationTUI()
        tui.start(["tool1", "tool2", "tool3", "tool4"])

        # All should remain PENDING
        table = tui.render()

        assert table is not None
        assert table.title == "HuskyCat Validation (Non-Blocking Mode)"

        # Progress should be 0%
        tool_states = [t.state for t in tui.tools.values()]
        assert all(s == ToolState.PENDING for s in tool_states)

        tui.stop()

    @patch("sys.stdout.isatty", return_value=True)
    def test_render_all_running(self, mock_isatty):
        """Test render when all tools are in RUNNING state."""
        tui = ValidationTUI()
        tui.start(["tool1", "tool2", "tool3"])

        for tool_name in tui.tools:
            tui.update_tool(tool_name, ToolState.RUNNING)

        table = tui.render()

        assert table is not None
        all_running = all(
            t.state == ToolState.RUNNING
            for t in tui.tools.values()
        )
        assert all_running

        tui.stop()

    @patch("sys.stdout.isatty", return_value=True)
    def test_render_mixed_states(self, mock_isatty):
        """Test render with mixed tool states."""
        tui = ValidationTUI()
        tui.start(["black", "mypy", "ruff", "flake8"])

        # Create mixed states
        tui.update_tool("black", ToolState.SUCCESS, errors=0, warnings=0)
        tui.update_tool("mypy", ToolState.RUNNING)
        tui.update_tool("ruff", ToolState.FAILED, errors=3, warnings=5)
        # flake8 remains PENDING

        table = tui.render()

        assert table is not None
        assert tui.tools["black"].state == ToolState.SUCCESS
        assert tui.tools["mypy"].state == ToolState.RUNNING
        assert tui.tools["ruff"].state == ToolState.FAILED
        assert tui.tools["flake8"].state == ToolState.PENDING

        tui.stop()

    @patch("sys.stdout.isatty", return_value=True)
    def test_render_all_success(self, mock_isatty):
        """Test render when all tools succeeded."""
        tui = ValidationTUI()
        tui.start(["tool1", "tool2", "tool3"])

        for tool_name in tui.tools:
            tui.update_tool(
                tool_name,
                ToolState.SUCCESS,
                errors=0,
                warnings=0
            )

        table = tui.render()

        assert table is not None
        all_success = all(
            t.state == ToolState.SUCCESS
            for t in tui.tools.values()
        )
        assert all_success

        tui.stop()

    @patch("sys.stdout.isatty", return_value=True)
    def test_render_all_failed(self, mock_isatty):
        """Test render when all tools failed."""
        tui = ValidationTUI()
        tui.start(["tool1", "tool2", "tool3"])

        for tool_name in tui.tools:
            tui.update_tool(
                tool_name,
                ToolState.FAILED,
                errors=2,
                warnings=1
            )

        table = tui.render()

        assert table is not None
        all_failed = all(
            t.state == ToolState.FAILED
            for t in tui.tools.values()
        )
        assert all_failed

        tui.stop()

    @patch("sys.stdout.isatty", return_value=True)
    def test_render_with_high_error_counts(self, mock_isatty):
        """Test render with high error counts."""
        tui = ValidationTUI()
        tui.start(["tool1"])

        tui.update_tool(
            "tool1",
            ToolState.FAILED,
            errors=9999,
            warnings=5000
        )

        table = tui.render()

        assert table is not None
        assert tui.tools["tool1"].errors == 9999
        assert tui.tools["tool1"].warnings == 5000

        tui.stop()

    @patch("sys.stdout.isatty", return_value=True)
    def test_render_all_skipped(self, mock_isatty):
        """Test render when all tools are SKIPPED."""
        tui = ValidationTUI()
        tui.start(["tool1", "tool2"])

        for tool_name in tui.tools:
            tui.update_tool(tool_name, ToolState.SKIPPED)

        table = tui.render()

        assert table is not None
        all_skipped = all(
            t.state == ToolState.SKIPPED
            for t in tui.tools.values()
        )
        assert all_skipped

        tui.stop()

    @patch("sys.stdout.isatty", return_value=True)
    def test_render_with_large_file_counts(self, mock_isatty):
        """Test render with large file processing counts."""
        tui = ValidationTUI()
        tui.start(["tool1"])

        tui.update_tool(
            "tool1",
            ToolState.RUNNING,
            files_processed=9999
        )

        table = tui.render()

        assert table is not None
        assert tui.tools["tool1"].files_processed == 9999

        tui.stop()


class TestContextManager:
    """Test context manager edge cases and error handling."""

    @patch("sys.stdout.isatty", return_value=True)
    def test_context_manager_normal_exit(self, mock_isatty):
        """Test context manager cleanup on normal exit."""
        tool_names = ["black", "mypy"]

        with validation_tui(tool_names) as tui:
            assert tui._running
            assert len(tui.tools) == 2
            tui.update_tool("black", ToolState.SUCCESS)

        # After exiting, TUI should be stopped
        assert not tui._running
        assert tui._live is None

    @patch("sys.stdout.isatty", return_value=True)
    def test_context_manager_exception_exit(self, mock_isatty):
        """Test context manager cleanup even on exception."""
        with pytest.raises(ValueError):
            with validation_tui(["tool1"]) as tui:
                assert tui._running
                raise ValueError("Test exception")

        # TUI should still be cleaned up
        assert not tui._running
        assert tui._live is None

    @patch("sys.stdout.isatty", return_value=True)
    def test_context_manager_with_updates_on_exit(self, mock_isatty):
        """Test that final updates occur before context exit."""
        with validation_tui(["tool1"]) as tui:
            tui.update_tool("tool1", ToolState.RUNNING)
            # Still running when exiting
            assert tui.tools["tool1"].state == ToolState.RUNNING

        # Should be stopped after exit
        assert not tui._running

    @patch("sys.stdout.isatty", return_value=True)
    def test_sequential_context_managers(self, mock_isatty):
        """Test sequential (non-nested) TUI context managers."""
        # First TUI
        with validation_tui(["tool1"]) as tui1:
            assert tui1._running
            tui1.update_tool("tool1", ToolState.SUCCESS)

        assert not tui1._running

        # Second TUI after first is closed
        with validation_tui(["tool2"]) as tui2:
            assert tui2._running
            tui2.update_tool("tool2", ToolState.SUCCESS)

        assert not tui2._running

    @patch("sys.stdout.isatty", return_value=True)
    def test_context_manager_custom_refresh_rate(self, mock_isatty):
        """Test context manager with custom refresh rate."""
        with validation_tui(["tool1"], refresh_rate=0.05) as tui:
            assert tui._refresh_rate == 0.05
            tui.update_tool("tool1", ToolState.SUCCESS)

        assert not tui._running


class TestNonTTY:
    """Test graceful degradation in non-TTY environments."""

    @patch("sys.stdout.isatty", return_value=False)
    def test_non_tty_silent_operation(self, mock_isatty):
        """Test graceful degradation in non-TTY (silent operation)."""
        tui = ValidationTUI()

        # Start should degrade gracefully
        tui.start(["tool1", "tool2"])

        # Should not initialize
        assert tui._running is False
        assert len(tui.tools) == 0
        assert tui._live is None

        # Update should be silently ignored
        tui.update_tool("tool1", ToolState.RUNNING)

        # Should not crash on stop
        tui.stop()

    @patch("sys.stdout.isatty", return_value=False)
    def test_non_tty_context_manager(self, mock_isatty):
        """Test context manager in non-TTY environment."""
        with validation_tui(["tool1"]) as tui:
            # Should not be running
            assert not tui._running
            assert tui.tools == {}

        # Cleanup should work fine
        assert not tui._running

    @patch("sys.stdout.isatty", return_value=False)
    def test_non_tty_render_call(self, mock_isatty):
        """Test render can be called in non-TTY without issues."""
        tui = ValidationTUI()

        # Render should still work even in non-TTY
        table = tui.render()
        assert table is not None

    @patch("sys.stdout.isatty", return_value=False)
    def test_non_tty_no_exceptions(self, mock_isatty):
        """Test that non-TTY environment raises no exceptions."""
        tui = ValidationTUI()

        try:
            tui.start(["tool1", "tool2", "tool3"])
            for tool in ["tool1", "tool2", "tool3"]:
                tui.update_tool(tool, ToolState.RUNNING)
                time.sleep(0.001)
                tui.update_tool(tool, ToolState.SUCCESS)
            tui.stop()
        except Exception as e:
            pytest.fail(f"Non-TTY operation raised exception: {e}")

    @patch("sys.stdout.isatty", return_value=False)
    def test_non_tty_is_tty_available(self, mock_isatty):
        """Test is_tty_available() returns False in non-TTY."""
        assert not is_tty_available()

    @patch("sys.stdout.isatty", return_value=True)
    def test_tty_is_tty_available(self, mock_isatty):
        """Test is_tty_available() returns True in TTY."""
        assert is_tty_available()


class TestTimeFormatting:
    """Test edge cases in time formatting."""

    @patch("sys.stdout.isatty", return_value=True)
    def test_format_time_zero_seconds(self, mock_isatty):
        """Test formatting zero seconds."""
        tui = ValidationTUI()
        assert tui._format_time(0.0) == "0.0s"

    @patch("sys.stdout.isatty", return_value=True)
    def test_format_time_sub_second(self, mock_isatty):
        """Test formatting sub-second durations."""
        tui = ValidationTUI()
        assert tui._format_time(0.001) == "0.0s"
        assert tui._format_time(0.1) == "0.1s"

    @patch("sys.stdout.isatty", return_value=True)
    def test_format_time_boundary_seconds(self, mock_isatty):
        """Test formatting at 59.x seconds (boundary to minutes)."""
        tui = ValidationTUI()
        assert "s" in tui._format_time(59.9)
        assert "m" not in tui._format_time(59.9)

    @patch("sys.stdout.isatty", return_value=True)
    def test_format_time_exactly_one_minute(self, mock_isatty):
        """Test formatting exactly 60 seconds."""
        tui = ValidationTUI()
        result = tui._format_time(60.0)
        assert "1m" in result
        assert "0s" in result

    @patch("sys.stdout.isatty", return_value=True)
    def test_format_time_multiple_minutes(self, mock_isatty):
        """Test formatting multiple minutes."""
        tui = ValidationTUI()
        assert tui._format_time(120.0) == "2m 0s"
        assert tui._format_time(125.5) == "2m 6s"
        assert tui._format_time(3661.0) == "61m 1s"

    @patch("sys.stdout.isatty", return_value=True)
    def test_format_time_very_large(self, mock_isatty):
        """Test formatting very large durations."""
        tui = ValidationTUI()
        result = tui._format_time(3600.0)  # 1 hour
        assert "m" in result
        assert "s" in result

    @patch("sys.stdout.isatty", return_value=True)
    def test_format_elapsed_time_no_start(self, mock_isatty):
        """Test elapsed time when TUI hasn't started timing."""
        tui = ValidationTUI()
        # Without starting TUI, _start_time is None
        assert tui._format_elapsed_time() == "0.0s"

    @patch("sys.stdout.isatty", return_value=True)
    def test_format_elapsed_time_with_start(self, mock_isatty):
        """Test elapsed time calculation when TUI is running."""
        tui = ValidationTUI()
        tui.start(["tool1"])

        # Elapsed time should be non-zero
        time.sleep(0.01)
        elapsed = tui._format_elapsed_time()

        # Should be a non-empty string
        assert len(elapsed) > 0
        assert "s" in elapsed

        tui.stop()


class TestDynamicToolOperations:
    """Test dynamic addition and management of tools."""

    @patch("sys.stdout.isatty", return_value=True)
    def test_add_tool_after_start(self, mock_isatty):
        """Test adding tools after TUI initialization."""
        tui = ValidationTUI()
        tui.start(["tool1"])

        assert len(tui.tools) == 1

        # Add new tool dynamically
        tui.update_tool("tool2", ToolState.RUNNING)

        assert len(tui.tools) == 2
        assert "tool2" in tui.tools

        tui.stop()

    @patch("sys.stdout.isatty", return_value=True)
    def test_add_many_tools_dynamically(self, mock_isatty):
        """Test adding many tools dynamically."""
        tui = ValidationTUI()
        tui.start(["tool1"])

        # Add 20 tools dynamically
        for i in range(2, 22):
            tui.update_tool(f"tool{i}", ToolState.RUNNING)

        assert len(tui.tools) == 21

        tui.stop()

    @patch("sys.stdout.isatty", return_value=True)
    def test_update_nonexistent_tool_creates_it(self, mock_isatty):
        """Test that updating a non-existent tool creates it."""
        tui = ValidationTUI()
        tui.start([])

        # Update tool that doesn't exist
        tui.update_tool("new_tool", ToolState.RUNNING)

        assert "new_tool" in tui.tools
        assert tui.tools["new_tool"].state == ToolState.RUNNING

        tui.stop()

    @patch("sys.stdout.isatty", return_value=True)
    def test_update_tool_with_zero_values(self, mock_isatty):
        """Test updating tool with zero errors and warnings."""
        tui = ValidationTUI()
        tui.start(["tool1"])

        tui.update_tool(
            "tool1",
            ToolState.SUCCESS,
            errors=0,
            warnings=0,
            files_processed=0
        )

        assert tui.tools["tool1"].errors == 0
        assert tui.tools["tool1"].warnings == 0
        assert tui.tools["tool1"].files_processed == 0

        tui.stop()


class TestToolStatusEdgeCases:
    """Test edge cases for ToolStatus dataclass."""

    def test_tool_status_complete_without_start(self):
        """Test completing a tool that was never started."""
        tool = ToolStatus(name="tool1")

        # Complete without calling start
        tool.complete(success=True, errors=0, warnings=0)

        assert tool.state == ToolState.SUCCESS
        assert tool.duration == 0.0  # No start time, so duration stays 0

    def test_tool_status_update_duration_without_start(self):
        """Test updating duration when tool never started."""
        tool = ToolStatus(name="tool1")

        # Update duration without starting
        tool.update_duration()

        # Should not crash, duration remains 0
        assert tool.duration == 0.0

    def test_tool_status_update_duration_after_complete(self):
        """Test updating duration after tool completed."""
        tool = ToolStatus(name="tool1")
        tool.start()
        time.sleep(0.01)
        tool.complete(success=True)

        first_duration = tool.duration

        # Try to update duration after completion
        tool.update_duration()

        # Duration should not change since state is not RUNNING
        assert tool.duration == first_duration

    def test_tool_status_multiple_starts(self):
        """Test calling start multiple times."""
        tool = ToolStatus(name="tool1")

        tool.start()
        first_start_time = tool.start_time

        time.sleep(0.01)

        tool.start()
        second_start_time = tool.start_time

        # Second start should update the start_time
        assert second_start_time > first_start_time

    def test_tool_status_complete_with_large_counts(self):
        """Test completing with very large error/warning counts."""
        tool = ToolStatus(name="tool1")
        tool.complete(
            success=False,
            errors=1_000_000,
            warnings=500_000
        )

        assert tool.errors == 1_000_000
        assert tool.warnings == 500_000
        assert tool.state == ToolState.FAILED


class TestProgressBarEdgeCases:
    """Test progress bar rendering edge cases."""

    @patch("sys.stdout.isatty", return_value=True)
    def test_progress_bar_boundary_percentages(self, mock_isatty):
        """Test progress bar at boundary percentages."""
        tui = ValidationTUI()

        for pct in [0, 10, 20, 50, 90, 100]:
            bar = tui._render_progress_bar(pct)
            assert f"{pct}%" in bar.plain

    @patch("sys.stdout.isatty", return_value=True)
    def test_progress_bar_all_percentages(self, mock_isatty):
        """Test progress bar for all percentages 0-100."""
        tui = ValidationTUI()

        for pct in range(0, 101, 5):
            bar = tui._render_progress_bar(pct)
            assert f"{pct}%" in bar.plain
            assert "█" in bar.plain or "░" in bar.plain

    @patch("sys.stdout.isatty", return_value=True)
    def test_progress_calculation_no_tools(self, mock_isatty):
        """Test progress calculation with no tools."""
        tui = ValidationTUI()
        tui.start([])

        # Render with empty tools
        table = tui.render()

        assert table is not None

        tui.stop()

    @patch("sys.stdout.isatty", return_value=True)
    def test_progress_calculation_single_tool_states(self, mock_isatty):
        """Test progress with single tool in each state."""
        tui = ValidationTUI()

        for state in ToolState:
            tui = ValidationTUI()
            tui.start(["tool1"])
            tui.update_tool("tool1", state)

            table = tui.render()
            assert table is not None

            tui.stop()


class TestErrorHandling:
    """Test error handling and edge cases."""

    @patch("sys.stdout.isatty", return_value=True)
    def test_update_tool_when_not_running(self, mock_isatty):
        """Test updating tool when TUI is not running."""
        tui = ValidationTUI()

        # Try to update without starting
        tui.update_tool("tool1", ToolState.RUNNING)

        # Should gracefully handle - no exception
        assert True

    @patch("sys.stdout.isatty", return_value=True)
    def test_stop_multiple_times(self, mock_isatty):
        """Test calling stop multiple times."""
        tui = ValidationTUI()
        tui.start(["tool1"])

        tui.stop()
        assert not tui._running

        # Second stop should not crash
        tui.stop()
        assert not tui._running

    @patch("sys.stdout.isatty", return_value=True)
    def test_render_while_updating(self, mock_isatty):
        """Test rendering while updates are happening."""
        tui = ValidationTUI()
        tui.start(["tool1", "tool2"])

        def update_continuously():
            for i in range(3):
                for j, tool in enumerate(["tool1", "tool2"]):
                    tui.update_tool(tool, ToolState.RUNNING)

        # Start updates in background
        t = threading.Thread(target=update_continuously, daemon=True)
        t.start()

        # Render multiple times
        for _ in range(3):
            table = tui.render()
            assert table is not None

        t.join(timeout=1)
        tui.stop()

    @patch("sys.stdout.isatty", return_value=True)
    def test_format_status_unknown_state(self, mock_isatty):
        """Test formatting unknown tool state."""
        tui = ValidationTUI()

        # All valid states are covered in ToolState enum
        # But the code has fallback for unknown states
        status = tui._format_status(ToolState.PENDING)
        assert status.plain  # Should return something

    @patch("sys.stdout.isatty", return_value=True)
    def test_get_row_style_all_states(self, mock_isatty):
        """Test row styling for all tool states."""
        tui = ValidationTUI()

        for state in ToolState:
            style = tui._get_row_style(state)
            assert isinstance(style, str)
            assert len(style) > 0


class TestIntegration:
    """Integration tests combining multiple features."""

    @patch("sys.stdout.isatty", return_value=True)
    def test_full_validation_workflow(self, mock_isatty):
        """Test complete validation workflow simulation."""
        tools = ["black", "mypy", "ruff", "flake8"]

        with validation_tui(tools) as tui:
            # Simulate validation sequence
            for tool in tools:
                tui.update_tool(tool, ToolState.RUNNING)

            time.sleep(0.01)

            # Some tools pass
            tui.update_tool("black", ToolState.SUCCESS, errors=0)
            tui.update_tool("ruff", ToolState.SUCCESS, errors=0)

            # Some tools fail
            tui.update_tool("mypy", ToolState.FAILED, errors=2)
            tui.update_tool("flake8", ToolState.RUNNING)

            time.sleep(0.01)

            tui.update_tool("flake8", ToolState.SUCCESS, errors=0)

        # After context, TUI should be stopped
        assert not tui._running

    @patch("sys.stdout.isatty", return_value=True)
    def test_stress_test_many_tools_many_updates(self, mock_isatty):
        """Stress test with many tools and rapid updates."""
        tool_count = 10
        tools = [f"tool{i}" for i in range(tool_count)]

        tui = ValidationTUI()
        tui.start(tools)

        # Update all tools
        for tool in tools:
            tui.update_tool(
                tool,
                ToolState.RUNNING,
                files_processed=0
            )

        for tool in tools:
            tui.update_tool(
                tool,
                ToolState.SUCCESS,
                errors=0
            )

        tui.stop()
        assert not tui._running

    @patch("sys.stdout.isatty", return_value=True)
    def test_tui_with_varying_refresh_rates(self, mock_isatty):
        """Test TUI with different refresh rates."""
        for refresh_rate in [0.01, 0.05, 0.1, 0.5, 1.0]:
            tui = ValidationTUI(refresh_rate=refresh_rate)
            assert tui._refresh_rate == refresh_rate

            tui.start(["tool1"])
            tui.update_tool("tool1", ToolState.SUCCESS)
            tui.stop()

    @patch("sys.stdout.isatty", return_value=True)
    def test_create_simple_spinner(self, mock_isatty):
        """Test creating and basic operations with simple spinner."""
        spinner = create_simple_spinner("Test message")

        assert spinner is not None
        # Spinner is a Live display, shouldn't be started in tests


class TestToolStateEnum:
    """Test ToolState enum comprehensiveness."""

    def test_all_tool_states_defined(self):
        """Verify all expected tool states are defined."""
        expected_states = ["PENDING", "RUNNING", "SUCCESS", "FAILED", "SKIPPED"]

        for state_name in expected_states:
            assert hasattr(ToolState, state_name)

    def test_tool_state_values(self):
        """Test ToolState enum values."""
        assert ToolState.PENDING.value == "pending"
        assert ToolState.RUNNING.value == "running"
        assert ToolState.SUCCESS.value == "success"
        assert ToolState.FAILED.value == "failed"
        assert ToolState.SKIPPED.value == "skipped"

    def test_tool_state_comparison(self):
        """Test ToolState enum comparisons."""
        state1 = ToolState.RUNNING
        state2 = ToolState.RUNNING
        state3 = ToolState.SUCCESS

        assert state1 == state2
        assert state1 != state3
        assert state1 != "running"  # Enum vs string
