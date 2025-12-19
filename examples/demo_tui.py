#!/usr/bin/env python3
"""
Demo script showing ValidationTUI in action.

This demonstrates the real-time progress display for validation tools.
Run this script to see the TUI with simulated tool execution.

Usage:
    python examples/demo_tui.py
"""

import sys
import time
from pathlib import Path

# Add src to path for demo
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from huskycat.core.tui import ValidationTUI, ToolState


def simulate_tool_validation(
    tui: ValidationTUI, tool_name: str, duration: float, errors: int = 0, warnings: int = 0
):
    """
    Simulate a tool validation with gradual progress updates.

    Args:
        tui: ValidationTUI instance
        tool_name: Name of the tool to simulate
        duration: How long the validation should take
        errors: Number of errors to report
        warnings: Number of warnings to report
    """
    # Start the tool
    tui.update_tool(tool_name, ToolState.RUNNING)

    # Simulate processing files with updates
    steps = 5
    step_duration = duration / steps
    for i in range(steps):
        time.sleep(step_duration)
        tui.update_tool(
            tool_name,
            ToolState.RUNNING,
            files_processed=(i + 1) * 10,
        )

    # Complete with results
    success = errors == 0
    final_state = ToolState.SUCCESS if success else ToolState.FAILED
    tui.update_tool(
        tool_name,
        final_state,
        errors=errors,
        warnings=warnings,
        files_processed=50,
    )


def main():
    """Run TUI demonstration."""
    print("\nValidationTUI Demonstration")
    print("=" * 60)
    print("\nSimulating validation of multiple tools...")
    print("Watch the real-time progress display below:\n")

    # Define tools to simulate
    tools = [
        ("black", 0.8, 0, 0),  # name, duration, errors, warnings
        ("ruff", 1.2, 0, 3),
        ("mypy", 2.5, 0, 1),
        ("flake8", 1.0, 0, 2),
        ("pytest", 3.0, 2, 0),  # This one will fail
        ("yamllint", 0.5, 0, 0),
    ]

    # Create and start TUI
    tui = ValidationTUI(refresh_rate=0.1)
    tui.start([tool[0] for tool in tools])

    try:
        # Give user time to see initial state
        time.sleep(0.5)

        # Simulate each tool (they run sequentially in this demo)
        for tool_name, duration, errors, warnings in tools:
            simulate_tool_validation(tui, tool_name, duration, errors, warnings)
            time.sleep(0.2)  # Brief pause between tools

        # Let user see final state
        time.sleep(2)

    finally:
        # Clean stop
        tui.stop()

    print("\n" + "=" * 60)
    print("Demo completed!")
    print("\nKey features demonstrated:")
    print("  - Real-time progress updates")
    print("  - Individual tool status tracking")
    print("  - Error and warning counts")
    print("  - Elapsed time per tool")
    print("  - Files processed counter")
    print("  - Overall progress percentage")
    print("  - Thread-safe updates")
    print("  - Clean terminal cleanup\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        sys.exit(0)
