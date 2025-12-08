#!/usr/bin/env python3
"""
Integration example: TUI with ProcessManager for non-blocking git hooks.

This demonstrates how ValidationTUI integrates with ProcessManager to provide
real-time progress display during background validation.

Usage:
    python examples/tui_with_process_manager.py
"""

import sys
import time
from pathlib import Path

# Add src to path for demo
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from huskycat.core.process_manager import ProcessManager
from huskycat.core.tui import ValidationTUI, ToolState


def simulate_validation_with_tui():
    """
    Simulate git hook validation with TUI display.

    This shows how the TUI would work in a real git hook scenario:
    1. Check for previous failed runs
    2. Fork validation to background process
    3. Display real-time progress in child process
    4. Parent returns immediately
    """
    print("\n" + "=" * 70)
    print("TUI + ProcessManager Integration Demo")
    print("=" * 70)

    # Simulated file list from git
    staged_files = [
        "src/huskycat/core/tui.py",
        "src/huskycat/core/process_manager.py",
        "tests/test_tui.py",
        "tests/test_process_manager.py",
    ]

    print(f"\nStaged files ({len(staged_files)}):")
    for f in staged_files:
        print(f"  - {f}")

    # Initialize process manager
    manager = ProcessManager()

    # Check for previous failure
    print("\nChecking previous validation runs...")
    previous_run = manager.check_previous_run()

    if previous_run:
        print("  Previous run FAILED")
        if not manager.handle_previous_failure(previous_run):
            print("  User chose to abort. Exiting.")
            return False
    else:
        print("  No previous failures found")

    # Simulate what would happen in real git hook
    print("\n" + "-" * 70)
    print("Simulating git hook behavior:")
    print("-" * 70)

    print("\nPARENT PROCESS:")
    print("  Starting background validation...")

    # In real hook, this would fork and parent would exit immediately
    # For demo, we simulate the child process behavior here
    print("  Forked child process (PID: simulated)")
    print("  Parent returning to git (commit proceeds)")
    print("  Log file: .huskycat/runs/logs/demo.log")

    print("\n" + "-" * 70)
    print("CHILD PROCESS (background):")
    print("-" * 70)
    print("\nStarting ValidationTUI display...\n")

    # Define validation tools
    tools = [
        ("black", 1.0, 0, 0),  # name, duration, errors, warnings
        ("ruff", 1.5, 0, 2),
        ("mypy", 2.0, 0, 1),
        ("flake8", 1.2, 0, 0),
    ]

    # Create TUI and run validation
    tui = ValidationTUI(refresh_rate=0.1)
    tui.start([tool[0] for tool in tools])

    try:
        # Give initial display time to render
        time.sleep(0.3)

        # Simulate each tool execution
        for tool_name, duration, errors, warnings in tools:
            # Start tool
            tui.update_tool(tool_name, ToolState.RUNNING)

            # Simulate processing with progress updates
            steps = 5
            for i in range(steps):
                time.sleep(duration / steps)
                tui.update_tool(
                    tool_name,
                    ToolState.RUNNING,
                    files_processed=(i + 1) * len(staged_files) // steps,
                )

            # Complete tool
            success = errors == 0
            final_state = ToolState.SUCCESS if success else ToolState.FAILED
            tui.update_tool(
                tool_name,
                final_state,
                errors=errors,
                warnings=warnings,
                files_processed=len(staged_files),
            )

            time.sleep(0.2)

        # Show final state
        time.sleep(1.5)

    finally:
        tui.stop()

    # Summary
    print("\n" + "-" * 70)
    print("Background validation completed!")
    print("-" * 70)
    print("\nResults saved to: .huskycat/runs/demo.json")
    print("Next git operation will check these results")
    print("\nKey benefits demonstrated:")
    print("  1. Git commit returns immediately (<100ms)")
    print("  2. Validation runs in background with progress display")
    print("  3. Results cached for next operation")
    print("  4. User sees real-time progress if they wait")
    print("  5. Clean terminal cleanup on completion")

    return True


def demonstrate_tty_detection():
    """Show TTY detection and graceful degradation."""
    print("\n\n" + "=" * 70)
    print("TTY Detection Demo")
    print("=" * 70)

    from huskycat.core.tui import is_tty_available

    if is_tty_available():
        print("\nCurrent environment: TTY available")
        print("  - Full TUI with Rich display enabled")
        print("  - Real-time progress updates")
        print("  - Color-coded status indicators")
    else:
        print("\nCurrent environment: No TTY")
        print("  - TUI disabled (graceful degradation)")
        print("  - Simple text output only")
        print("  - No terminal control sequences")

    print("\nTo test non-TTY mode:")
    print("  python examples/tui_with_process_manager.py | cat")
    print("  # or")
    print("  python examples/tui_with_process_manager.py > output.txt")


def demonstrate_thread_safety():
    """Show thread-safe concurrent updates."""
    print("\n\n" + "=" * 70)
    print("Thread Safety Demo")
    print("=" * 70)

    import threading

    print("\nSimulating concurrent tool execution...")
    print("Multiple threads updating TUI simultaneously\n")

    tools = ["black", "mypy", "ruff", "flake8"]
    tui = ValidationTUI(refresh_rate=0.1)
    tui.start(tools)

    def worker(tool_name, duration):
        """Worker thread simulates tool execution."""
        tui.update_tool(tool_name, ToolState.RUNNING)

        # Simulate work with multiple updates
        steps = 8
        for i in range(steps):
            time.sleep(duration / steps)
            tui.update_tool(
                tool_name,
                ToolState.RUNNING,
                files_processed=(i + 1) * 5,
            )

        tui.update_tool(tool_name, ToolState.SUCCESS, files_processed=40)

    try:
        # Create threads for concurrent execution
        threads = [
            threading.Thread(target=worker, args=(tool, 1.0 + i * 0.2))
            for i, tool in enumerate(tools)
        ]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        time.sleep(1)

    finally:
        tui.stop()

    print("\n" + "-" * 70)
    print("Thread-safe updates completed successfully!")
    print("-" * 70)
    print("\nNo race conditions or corrupted display")
    print("All updates processed correctly with RLock synchronization")


def main():
    """Run all demonstrations."""
    try:
        # Main integration demo
        simulate_validation_with_tui()

        # TTY detection
        demonstrate_tty_detection()

        # Thread safety
        demonstrate_thread_safety()

        print("\n\n" + "=" * 70)
        print("All demonstrations completed!")
        print("=" * 70)
        print("\nFor production use:")
        print("  1. Git hooks call ProcessManager.fork_validation()")
        print("  2. Child process uses ValidationTUI for display")
        print("  3. Parent returns immediately to git")
        print("  4. User sees progress if watching, or can continue work")
        print("\nSee docs/TUI_INTEGRATION.md for full integration guide")
        print()

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
