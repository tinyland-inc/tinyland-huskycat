"""
Unit tests for TUI framework.

Tests cover:
- Tool status tracking
- Thread-safe updates
- Progress calculation
- Display rendering
- TTY detection
- Graceful degradation
"""

import sys
import time
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from src.huskycat.core.tui import (
    ToolState,
    ToolStatus,
    ValidationTUI,
    create_simple_spinner,
    is_tty_available,
    validation_tui,
)


class TestToolStatus:
    """Test ToolStatus dataclass behavior."""

    def test_initial_state(self):
        """Tool should start in PENDING state."""
        tool = ToolStatus(name="black")
        assert tool.state == ToolState.PENDING
        assert tool.duration == 0.0
        assert tool.errors == 0
        assert tool.warnings == 0

    def test_start_tool(self):
        """Starting tool should set RUNNING state and record time."""
        tool = ToolStatus(name="mypy")
        tool.start()
        assert tool.state == ToolState.RUNNING
        assert tool.start_time is not None
        assert tool.start_time > 0

    def test_complete_success(self):
        """Completing successfully should set SUCCESS state."""
        tool = ToolStatus(name="ruff")
        tool.start()
        time.sleep(0.01)  # Small delay to get measurable duration
        tool.complete(success=True, errors=0, warnings=2)
        assert tool.state == ToolState.SUCCESS
        assert tool.errors == 0
        assert tool.warnings == 2
        assert tool.duration > 0

    def test_complete_failure(self):
        """Completing with errors should set FAILED state."""
        tool = ToolStatus(name="flake8")
        tool.start()
        time.sleep(0.01)
        tool.complete(success=False, errors=5, warnings=1)
        assert tool.state == ToolState.FAILED
        assert tool.errors == 5
        assert tool.warnings == 1
        assert tool.duration > 0

    def test_update_duration(self):
        """Duration should update for running tools."""
        tool = ToolStatus(name="black")
        tool.start()
        initial_duration = tool.duration
        time.sleep(0.01)
        tool.update_duration()
        assert tool.duration > initial_duration


class TestValidationTUI:
    """Test ValidationTUI class behavior."""

    @patch("sys.stdout.isatty", return_value=True)
    def test_initialization(self, mock_isatty):
        """TUI should initialize correctly."""
        tui = ValidationTUI()
        assert tui.tools == {}
        assert not tui._running
        assert tui._is_tty

    @patch("sys.stdout.isatty", return_value=False)
    def test_initialization_no_tty(self, mock_isatty):
        """TUI should detect non-TTY environment."""
        tui = ValidationTUI()
        assert not tui._is_tty

    @patch("sys.stdout.isatty", return_value=True)
    def test_start(self, mock_isatty):
        """Starting TUI should initialize tools."""
        tui = ValidationTUI()
        tool_names = ["black", "mypy", "ruff"]
        tui.start(tool_names)

        assert tui._running
        assert len(tui.tools) == 3
        assert all(name in tui.tools for name in tool_names)
        assert all(tool.state == ToolState.PENDING for tool in tui.tools.values())

        # Cleanup
        tui.stop()

    @patch("sys.stdout.isatty", return_value=False)
    def test_start_no_tty_graceful_degradation(self, mock_isatty):
        """TUI should gracefully degrade in non-TTY environment."""
        tui = ValidationTUI()
        tui.start(["black", "mypy"])

        # Should not start in non-TTY mode
        assert not tui._running
        assert tui.tools == {}

    @patch("sys.stdout.isatty", return_value=True)
    def test_update_tool(self, mock_isatty):
        """Updating tool status should work correctly."""
        tui = ValidationTUI()
        tui.start(["black", "mypy"])

        # Update to RUNNING
        tui.update_tool("black", ToolState.RUNNING)
        assert tui.tools["black"].state == ToolState.RUNNING

        # Update to SUCCESS
        tui.update_tool("black", ToolState.SUCCESS, errors=0, warnings=1)
        assert tui.tools["black"].state == ToolState.SUCCESS
        assert tui.tools["black"].errors == 0
        assert tui.tools["black"].warnings == 1

        # Cleanup
        tui.stop()

    @patch("sys.stdout.isatty", return_value=True)
    def test_update_tool_dynamic_addition(self, mock_isatty):
        """TUI should handle dynamically added tools."""
        tui = ValidationTUI()
        tui.start(["black"])

        # Add new tool dynamically
        tui.update_tool("mypy", ToolState.RUNNING)
        assert "mypy" in tui.tools
        assert tui.tools["mypy"].state == ToolState.RUNNING

        # Cleanup
        tui.stop()

    @patch("sys.stdout.isatty", return_value=True)
    def test_render_table(self, mock_isatty):
        """Rendering should produce valid Rich Table."""
        tui = ValidationTUI()
        tui.start(["black", "mypy", "ruff"])

        # Update some tools
        tui.update_tool("black", ToolState.SUCCESS, errors=0, warnings=0)
        tui.update_tool("mypy", ToolState.RUNNING)

        # Render should not raise exception
        table = tui.render()
        assert table is not None
        assert table.title == "HuskyCat Validation (Non-Blocking Mode)"

        # Cleanup
        tui.stop()

    @patch("sys.stdout.isatty", return_value=True)
    def test_progress_calculation(self, mock_isatty):
        """Progress should calculate correctly."""
        tui = ValidationTUI()
        tui.start(["black", "mypy", "ruff", "flake8"])

        # Complete 2 out of 4 tools
        tui.update_tool("black", ToolState.SUCCESS)
        tui.update_tool("mypy", ToolState.FAILED)

        # Progress should be 50%
        completed = sum(
            1
            for t in tui.tools.values()
            if t.state in (ToolState.SUCCESS, ToolState.FAILED, ToolState.SKIPPED)
        )
        total = len(tui.tools)
        progress_pct = int((completed / total) * 100)
        assert progress_pct == 50

        # Cleanup
        tui.stop()

    @patch("sys.stdout.isatty", return_value=True)
    def test_format_time(self, mock_isatty):
        """Time formatting should be human-readable."""
        tui = ValidationTUI()

        # Test seconds
        assert tui._format_time(0.5) == "0.5s"
        assert tui._format_time(5.7) == "5.7s"

        # Test minutes
        assert tui._format_time(65.0) == "1m 5s"
        assert tui._format_time(125.5) == "2m 6s"

    @patch("sys.stdout.isatty", return_value=True)
    def test_format_status(self, mock_isatty):
        """Status formatting should include icons and colors."""
        tui = ValidationTUI()

        status_pending = tui._format_status(ToolState.PENDING)
        assert "Pending" in status_pending.plain

        status_running = tui._format_status(ToolState.RUNNING)
        assert "Running" in status_running.plain

        status_success = tui._format_status(ToolState.SUCCESS)
        assert "Done" in status_success.plain

        status_failed = tui._format_status(ToolState.FAILED)
        assert "Failed" in status_failed.plain

    @patch("sys.stdout.isatty", return_value=True)
    def test_stop_cleanup(self, mock_isatty):
        """Stopping TUI should clean up resources."""
        tui = ValidationTUI()
        tui.start(["black", "mypy"])
        assert tui._running

        tui.stop()
        assert not tui._running
        assert tui._live is None

    @patch("sys.stdout.isatty", return_value=False)
    def test_stop_no_tty(self, mock_isatty):
        """Stopping in non-TTY mode should not raise exceptions."""
        tui = ValidationTUI()
        tui.start(["black"])
        tui.stop()  # Should not raise


class TestContextManager:
    """Test validation_tui context manager."""

    @patch("sys.stdout.isatty", return_value=True)
    def test_context_manager(self, mock_isatty):
        """Context manager should start and stop TUI."""
        tool_names = ["black", "mypy", "ruff"]

        with validation_tui(tool_names) as tui:
            assert isinstance(tui, ValidationTUI)
            assert tui._running
            tui.update_tool("black", ToolState.SUCCESS)

        # TUI should be stopped after context exit
        assert not tui._running

    @patch("sys.stdout.isatty", return_value=True)
    def test_context_manager_exception_handling(self, mock_isatty):
        """Context manager should cleanup even on exception."""
        try:
            with validation_tui(["black"]) as tui:
                assert tui._running
                raise ValueError("Test exception")
        except ValueError:
            pass

        # TUI should still be stopped
        assert not tui._running


class TestUtilityFunctions:
    """Test utility functions."""

    @patch("sys.stdout.isatty", return_value=True)
    def test_is_tty_available_true(self, mock_isatty):
        """Should detect TTY availability."""
        assert is_tty_available()

    @patch("sys.stdout.isatty", return_value=False)
    def test_is_tty_available_false(self, mock_isatty):
        """Should detect non-TTY environment."""
        assert not is_tty_available()

    @patch("sys.stdout.isatty", return_value=True)
    def test_create_simple_spinner(self, mock_isatty):
        """Simple spinner should create valid Live display."""
        spinner = create_simple_spinner("Testing...")
        assert spinner is not None
        # Don't start it to avoid terminal output in tests


class TestThreadSafety:
    """Test thread-safety of TUI updates."""

    @patch("sys.stdout.isatty", return_value=True)
    def test_concurrent_updates(self, mock_isatty):
        """TUI should handle concurrent updates from multiple threads."""
        import threading

        tui = ValidationTUI()
        tui.start(["black", "mypy", "ruff"])

        def update_tool_repeatedly(tool_name, iterations):
            for i in range(iterations):
                tui.update_tool(tool_name, ToolState.RUNNING, files_processed=i)
                time.sleep(0.001)
            tui.update_tool(tool_name, ToolState.SUCCESS)

        # Create threads for concurrent updates
        threads = [
            threading.Thread(target=update_tool_repeatedly, args=("black", 10)),
            threading.Thread(target=update_tool_repeatedly, args=("mypy", 10)),
            threading.Thread(target=update_tool_repeatedly, args=("ruff", 10)),
        ]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify all tools completed successfully
        assert all(t.state == ToolState.SUCCESS for t in tui.tools.values())

        # Cleanup
        tui.stop()


class TestProgressBar:
    """Test progress bar rendering."""

    @patch("sys.stdout.isatty", return_value=True)
    def test_progress_bar_empty(self, mock_isatty):
        """Progress bar at 0% should be all empty blocks."""
        tui = ValidationTUI()
        progress = tui._render_progress_bar(0)
        assert "0%" in progress.plain
        assert "░" in progress.plain

    @patch("sys.stdout.isatty", return_value=True)
    def test_progress_bar_full(self, mock_isatty):
        """Progress bar at 100% should be all filled blocks."""
        tui = ValidationTUI()
        progress = tui._render_progress_bar(100)
        assert "100%" in progress.plain
        assert "█" in progress.plain

    @patch("sys.stdout.isatty", return_value=True)
    def test_progress_bar_partial(self, mock_isatty):
        """Progress bar at 50% should be half filled."""
        tui = ValidationTUI()
        progress = tui._render_progress_bar(50)
        assert "50%" in progress.plain
        assert "█" in progress.plain
        assert "░" in progress.plain
