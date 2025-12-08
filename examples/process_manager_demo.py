"""
Demo: ProcessManager for Git Hook Integration

This example demonstrates how to use ProcessManager for non-blocking
git hook validation with fork-based execution.

Usage scenarios:
1. Pre-commit hook: Fork validation to background
2. Check previous validation results
3. Handle previous failures with user prompts
"""

import sys
from pathlib import Path

# Add src to path for demo
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.huskycat.core.process_manager import ProcessManager, should_proceed_with_commit


def example_1_fork_validation():
    """
    Example 1: Fork validation process (git hook scenario)

    This simulates a pre-commit hook that:
    1. Forks validation to background
    2. Returns immediately to git (<100ms)
    3. Background process runs full validation with TUI
    """
    print("=" * 60)
    print("Example 1: Fork Validation Process")
    print("=" * 60)

    manager = ProcessManager()

    # Simulate staged files
    files = [
        "src/huskycat/core/process_manager.py",
        "src/huskycat/core/mode_detector.py",
        "tests/test_process_manager.py",
    ]

    print(f"\nForking validation for {len(files)} files...")

    # Fork validation (in real scenario, this would run huskycat)
    # For demo, we'll simulate with a simple command
    pid = manager.fork_validation(
        files=files,
        validation_cmd="sleep",
        validation_args=["1"],  # Sleep for 1 second to simulate validation
    )

    if pid > 0:
        print(f"\nParent process: Validation running in background (PID {pid})")
        print("Parent process: Returning to git immediately...")
        print("\nIn real scenario, git would proceed with commit.")
        print("Validation continues in background with TUI.")
    else:
        print("\nERROR: Could not fork validation process")

    print()


def example_2_check_previous_run():
    """
    Example 2: Check previous validation run

    Before starting new validation, check if previous run failed.
    This prevents repeated commits of broken code.
    """
    print("=" * 60)
    print("Example 2: Check Previous Validation Run")
    print("=" * 60)

    manager = ProcessManager()

    # Check for previous failed validation
    previous_run = manager.check_previous_run()

    if previous_run is None:
        print("\nNo previous failed validation found.")
        print("Proceeding with new validation...")
    else:
        print("\nPREVIOUS VALIDATION FAILED:")
        print(f"  Run ID:   {previous_run.run_id}")
        print(f"  Started:  {previous_run.started}")
        print(f"  Errors:   {previous_run.errors}")
        print(f"  Warnings: {previous_run.warnings}")
        print(f"  Tools:    {', '.join(previous_run.tools_run)}")
        print("\nUser would be prompted: 'Proceed anyway? [y/N]'")

    print()


def example_3_should_proceed():
    """
    Example 3: Convenience function for git hooks

    Use should_proceed_with_commit() as a simple entry point
    for git hooks to check previous failures.
    """
    print("=" * 60)
    print("Example 3: Should Proceed with Commit")
    print("=" * 60)

    print("\nChecking if commit should proceed...")

    # This checks for previous failures and prompts user if needed
    # (In non-interactive mode, automatically fails on previous error)
    should_proceed = should_proceed_with_commit()

    if should_proceed:
        print("Commit should proceed.")
    else:
        print("Commit should be aborted (previous validation failed).")

    print()


def example_4_run_management():
    """
    Example 4: Validation run history and cleanup

    View recent validation runs and cleanup old results.
    """
    print("=" * 60)
    print("Example 4: Run History and Cleanup")
    print("=" * 60)

    manager = ProcessManager()

    # Get recent run history
    print("\nRecent validation runs:")
    history = manager.get_run_history(limit=5)

    if not history:
        print("  No validation runs found.")
    else:
        for run in history:
            status = "PASS" if run.success else "FAIL"
            completed = run.completed or "RUNNING"
            print(f"  [{status}] {run.run_id}")
            print(f"      Started:   {run.started}")
            print(f"      Completed: {completed}")
            print(f"      Errors:    {run.errors}")
            print()

    # Check running validations
    running = manager.get_running_validations()
    print(f"Currently running validations: {len(running)}")
    for run in running:
        print(f"  PID {run['pid']}: {run['run_id']}")

    # Cleanup old runs
    print("\nCleaning up validation runs older than 7 days...")
    manager.cleanup_old_runs(max_age_days=7)

    print()


def example_5_git_hook_integration():
    """
    Example 5: Complete Git Hook Integration

    Shows how a pre-commit hook would use ProcessManager.
    """
    print("=" * 60)
    print("Example 5: Git Hook Integration Pattern")
    print("=" * 60)

    print(
        """
Git hook integration pseudo-code:

```bash
#!/bin/bash
# .git/hooks/pre-commit (generated by HuskyCat)

# Get staged files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACMR)

# Check if we should proceed (handles previous failures)
python -c "
from huskycat.core.process_manager import should_proceed_with_commit
import sys
if not should_proceed_with_commit():
    sys.exit(1)  # Abort commit
"

# Fork validation to background
python -c "
from huskycat.core.process_manager import ProcessManager
import sys

manager = ProcessManager()
files = sys.argv[1:]

# Fork validation process
pid = manager.fork_validation(
    files=files,
    validation_cmd='huskycat',
    validation_args=['validate', '--staged']
)

# Parent returns immediately (git proceeds)
# Child runs validation in background
" $STAGED_FILES

exit 0  # Let git proceed (validation runs in background)
```

Key features:
1. Check previous validation (with user prompt if failed)
2. Fork validation to background process
3. Parent returns immediately (<100ms) to git
4. Child process runs full validation with progress UI
5. Results cached for next commit check
"""
    )
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("ProcessManager Demo for Git Hook Integration")
    print("=" * 60)
    print()

    print("This demo shows how ProcessManager enables non-blocking")
    print("git hook validation with background process execution.\n")

    # Run examples
    example_1_fork_validation()
    example_2_check_previous_run()
    example_3_should_proceed()
    example_4_run_management()
    example_5_git_hook_integration()

    print("=" * 60)
    print("Demo complete!")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
