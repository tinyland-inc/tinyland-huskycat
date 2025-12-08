"""
TUI (Terminal User Interface) Framework for HuskyCat.

Provides real-time validation progress display using the rich library.
Designed for non-blocking operation with thread-safe updates.

Features:
- Real-time progress display with overall completion percentage
- Individual tool status tracking (pending/running/success/failed)
- Error and warning counts per tool
- Elapsed time tracking
- Thread-safe updates from concurrent validation processes
- Clean terminal cleanup on exit
- Graceful degradation for non-TTY environments
"""

import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from rich.console import Console
from rich.live import Live
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text


class ToolState(Enum):
    """Status states for validation tools."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ToolStatus:
    """
    Status tracking for a single validation tool.

    Attributes:
        name: Tool identifier (e.g., "black", "mypy", "ruff")
        state: Current execution state
        duration: Time elapsed in seconds
        errors: Count of errors found
        warnings: Count of warnings found
        files_processed: Number of files processed
        start_time: Unix timestamp when tool started
    """

    name: str
    state: ToolState = ToolState.PENDING
    duration: float = 0.0
    errors: int = 0
    warnings: int = 0
    files_processed: int = 0
    start_time: Optional[float] = None

    def start(self) -> None:
        """Mark tool as running and record start time."""
        self.state = ToolState.RUNNING
        self.start_time = time.time()

    def complete(self, success: bool, errors: int = 0, warnings: int = 0) -> None:
        """
        Mark tool as complete and record results.

        Args:
            success: Whether tool passed validation
            errors: Number of errors found
            warnings: Number of warnings found
        """
        self.state = ToolState.SUCCESS if success else ToolState.FAILED
        self.errors = errors
        self.warnings = warnings
        if self.start_time:
            self.duration = time.time() - self.start_time

    def update_duration(self) -> None:
        """Update duration for running tool."""
        if self.state == ToolState.RUNNING and self.start_time:
            self.duration = time.time() - self.start_time


class ValidationTUI:
    """
    Real-time TUI for validation progress tracking.

    Thread-safe validation progress display that runs in background.
    Updates display without blocking validation processes.

    Usage:
        tui = ValidationTUI()
        tui.start(["black", "mypy", "ruff", "flake8"])
        tui.update_tool("black", ToolState.RUNNING)
        tui.update_tool("black", ToolState.SUCCESS, errors=0, warnings=0)
        tui.stop()
    """

    def __init__(self, refresh_rate: float = 0.1):
        """
        Initialize TUI framework.

        Args:
            refresh_rate: Display refresh interval in seconds (default: 0.1)
        """
        self.console = Console()
        self.tools: Dict[str, ToolStatus] = {}
        self._running = False
        self._lock = threading.RLock()
        self._start_time: Optional[float] = None
        self._live: Optional[Live] = None
        self._refresh_rate = refresh_rate
        self._is_tty = sys.stdout.isatty()
        self._thread: Optional[threading.Thread] = None

    def start(self, tool_names: List[str]) -> None:
        """
        Initialize TUI with list of tools to track.

        Args:
            tool_names: List of tool identifiers to display
        """
        if not self._is_tty:
            # Graceful degradation - no TUI in non-interactive mode
            return

        with self._lock:
            # Initialize tool statuses
            self.tools = {name: ToolStatus(name=name) for name in tool_names}
            self._start_time = time.time()
            self._running = True

            # Start live display
            self._live = Live(
                self.render(),
                console=self.console,
                refresh_per_second=int(1.0 / self._refresh_rate),
                transient=False,
            )
            self._live.start()

    def update_tool(
        self,
        tool_name: str,
        state: ToolState,
        errors: int = 0,
        warnings: int = 0,
        files_processed: int = 0,
    ) -> None:
        """
        Update status of a specific tool (thread-safe).

        Args:
            tool_name: Tool identifier
            state: New state for the tool
            errors: Current error count
            warnings: Current warning count
            files_processed: Number of files processed
        """
        if not self._is_tty or not self._running:
            return

        with self._lock:
            if tool_name not in self.tools:
                # Dynamic tool addition
                self.tools[tool_name] = ToolStatus(name=tool_name)

            tool = self.tools[tool_name]

            if state == ToolState.RUNNING and tool.state == ToolState.PENDING:
                tool.start()
            elif state in (ToolState.SUCCESS, ToolState.FAILED):
                tool.complete(success=(state == ToolState.SUCCESS), errors=errors, warnings=warnings)
            else:
                tool.state = state

            tool.errors = errors
            tool.warnings = warnings
            tool.files_processed = files_processed

            # Update live display
            if self._live:
                self._live.update(self.render())

    def render(self) -> Table:
        """
        Generate rich Table for display.

        Returns:
            Rich Table with current validation status
        """
        with self._lock:
            # Create main table
            table = Table(
                title="HuskyCat Validation (Non-Blocking Mode)",
                title_style="bold cyan",
                show_header=True,
                header_style="bold magenta",
                border_style="blue",
                expand=False,
            )

            # Add columns
            table.add_column("Tool", style="cyan", no_wrap=True, width=20)
            table.add_column("Status", style="white", width=15)
            table.add_column("Time", justify="right", style="yellow", width=8)
            table.add_column("Errors", justify="right", style="red", width=8)
            table.add_column("Warnings", justify="right", style="yellow", width=10)
            table.add_column("Files", justify="right", style="blue", width=8)

            # Calculate overall progress
            total_tools = len(self.tools)
            completed_tools = sum(
                1
                for t in self.tools.values()
                if t.state in (ToolState.SUCCESS, ToolState.FAILED, ToolState.SKIPPED)
            )
            progress_pct = (
                int((completed_tools / total_tools) * 100) if total_tools > 0 else 0
            )

            # Add overall progress row
            progress_bar = self._render_progress_bar(progress_pct)
            table.add_row(
                Text("Overall Progress", style="bold white"),
                progress_bar,
                self._format_elapsed_time(),
                "",
                "",
                f"{completed_tools}/{total_tools}",
                style="bold",
            )

            # Add separator
            table.add_section()

            # Add tool rows
            for tool_name, tool in sorted(self.tools.items()):
                # Update duration for running tools
                if tool.state == ToolState.RUNNING:
                    tool.update_duration()

                status_text = self._format_status(tool.state)
                time_text = self._format_time(tool.duration) if tool.duration > 0 else "-"
                errors_text = str(tool.errors) if tool.state != ToolState.PENDING else "-"
                warnings_text = (
                    str(tool.warnings) if tool.state != ToolState.PENDING else "-"
                )
                files_text = (
                    str(tool.files_processed) if tool.files_processed > 0 else "-"
                )

                # Apply row styling based on state
                style = self._get_row_style(tool.state)

                table.add_row(
                    tool_name,
                    status_text,
                    time_text,
                    errors_text,
                    warnings_text,
                    files_text,
                    style=style,
                )

            return table

    def stop(self) -> None:
        """Clean stop of TUI display."""
        if not self._is_tty:
            return

        with self._lock:
            self._running = False

            if self._live:
                # Final update before stopping
                self._live.update(self.render())
                self._live.stop()
                self._live = None

    def _format_status(self, state: ToolState) -> Text:
        """
        Format tool status with appropriate icon and color.

        Args:
            state: Tool state enum

        Returns:
            Rich Text with styled status
        """
        status_map = {
            ToolState.PENDING: ("• Pending", "dim"),
            ToolState.RUNNING: ("⠋ Running", "cyan"),
            ToolState.SUCCESS: ("✓ Done", "green"),
            ToolState.FAILED: ("✗ Failed", "red"),
            ToolState.SKIPPED: ("⊘ Skipped", "dim"),
        }
        text, style = status_map.get(state, ("? Unknown", "white"))
        return Text(text, style=style)

    def _format_time(self, seconds: float) -> str:
        """
        Format duration in human-readable form.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted string (e.g., "0.3s", "2.1s", "1m 23s")
        """
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"

    def _format_elapsed_time(self) -> str:
        """
        Format total elapsed time since validation started.

        Returns:
            Formatted elapsed time string
        """
        if not self._start_time:
            return "0.0s"
        elapsed = time.time() - self._start_time
        return self._format_time(elapsed)

    def _render_progress_bar(self, percentage: int) -> Text:
        """
        Render ASCII progress bar.

        Args:
            percentage: Progress percentage (0-100)

        Returns:
            Rich Text with progress bar
        """
        filled = int(percentage / 10)  # 10 blocks for 0-100%
        empty = 10 - filled
        bar = "█" * filled + "░" * empty
        return Text(f"{bar} {percentage}%", style="bold cyan")

    def _get_row_style(self, state: ToolState) -> str:
        """
        Get row styling based on tool state.

        Args:
            state: Tool state enum

        Returns:
            Style string for rich Table
        """
        style_map = {
            ToolState.PENDING: "dim",
            ToolState.RUNNING: "cyan",
            ToolState.SUCCESS: "green",
            ToolState.FAILED: "red",
            ToolState.SKIPPED: "dim",
        }
        return style_map.get(state, "")


@contextmanager
def validation_tui(tool_names: List[str], refresh_rate: float = 0.1):
    """
    Context manager for validation TUI.

    Automatically starts and stops TUI display.

    Args:
        tool_names: List of tools to track
        refresh_rate: Display refresh interval in seconds

    Yields:
        ValidationTUI instance

    Example:
        with validation_tui(["black", "mypy", "ruff"]) as tui:
            tui.update_tool("black", ToolState.RUNNING)
            # ... perform validation ...
            tui.update_tool("black", ToolState.SUCCESS)
    """
    tui = ValidationTUI(refresh_rate=refresh_rate)
    try:
        tui.start(tool_names)
        yield tui
    finally:
        tui.stop()


# Utility functions for integration

def is_tty_available() -> bool:
    """
    Check if TUI can be displayed (TTY available).

    Returns:
        True if stdout is a TTY, False otherwise
    """
    return sys.stdout.isatty()


def create_simple_spinner(message: str = "Validating...") -> Live:
    """
    Create a simple spinner for non-TUI fallback.

    Args:
        message: Message to display

    Returns:
        Rich Live display with spinner

    Example:
        with create_simple_spinner("Running validation...") as spinner:
            # ... perform work ...
            pass
    """
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    )
    progress.add_task(description=message, total=None)
    return Live(progress, console=Console(), refresh_per_second=10)
