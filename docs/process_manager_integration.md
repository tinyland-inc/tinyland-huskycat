# ProcessManager Integration Guide

## Overview

The `ProcessManager` class provides robust fork-based process management for non-blocking git hook execution. It enables git hooks to return immediately (<100ms) while validation runs in the background with full progress UI.

## Key Features

### 1. Fork-Based Execution
- Parent process returns immediately to git
- Child process runs full validation with TUI
- Proper signal handling and cleanup
- Zero blocking for developer workflow

### 2. Result Caching and Persistence
- Store validation results in `.huskycat/runs/{run_id}.json`
- Track previous run results
- Fast lookup for "previous run failed" scenario
- Historical run data for analytics

### 3. PID File Management
- Track running validation processes
- Prevent duplicate validations on same files
- Automatic zombie process cleanup
- Robust process lifecycle management

### 4. Previous Failure Handling
- Detect previous failed validations
- Interactive user prompts (TTY aware)
- Non-interactive fail-safe behavior
- Clear last run on user confirmation

## Architecture

```
GIT COMMIT ATTEMPT
       |
       v
Check Previous Run -----> [FAILED?] ---> Prompt User
       |                                      |
       |                                      v
       |                              [Proceed? y/N]
       |                                      |
       v                                      |
Fork Validation Process <-------------------+
       |
       +---> PARENT: Return to Git (0ms)
       |
       +---> CHILD: Run Validation (background)
                   |
                   +---> Save Results
                   |
                   +---> Cleanup PID
                   |
                   v
                  Exit
```

## File Structure

```
.huskycat/
└── runs/
    ├── last_run.json          # Latest validation result
    ├── 20251207_103045.json   # Historical run data
    ├── 20251207_104512.json
    ├── pids/                  # Running process tracking
    │   ├── 12345.json         # PID 12345 running
    │   └── 12346.json         # PID 12346 running
    └── logs/                  # Validation output logs
        ├── 20251207_103045.log
        └── 20251207_104512.log
```

## Core Classes

### ValidationRun

Represents a single validation run with results.

```python
@dataclass
class ValidationRun:
    run_id: str                    # Unique identifier (ISO timestamp)
    started: str                   # ISO timestamp when started
    completed: Optional[str]       # ISO timestamp when completed
    files: List[str]               # Files validated
    success: bool                  # Whether validation passed
    tools_run: List[str]           # Tool names executed
    errors: int                    # Number of errors found
    warnings: int                  # Number of warnings found
    exit_code: Optional[int]       # Process exit code
    pid: Optional[int]             # Process ID
```

### ProcessManager

Manages forked validation processes.

```python
class ProcessManager:
    def __init__(self, cache_dir: Path = None)

    # Core methods
    def check_previous_run(self) -> Optional[ValidationRun]
    def fork_validation(self, files: List[str], validation_cmd: str,
                       validation_args: List[str] = None) -> int
    def save_run(self, run: ValidationRun)
    def get_running_validations(self) -> List[Dict[str, Any]]
    def cleanup_zombies(self)
    def handle_previous_failure(self, run: ValidationRun) -> bool

    # Utility methods
    def get_run_history(self, limit: int = 10) -> List[ValidationRun]
    def cleanup_old_runs(self, max_age_days: int = 7)
```

## Usage Examples

### Example 1: Basic Fork Validation

```python
from huskycat.core.process_manager import ProcessManager

manager = ProcessManager()

# Get staged files
files = ["src/file1.py", "src/file2.py"]

# Fork validation to background
pid = manager.fork_validation(
    files=files,
    validation_cmd="huskycat",
    validation_args=["validate", "--staged"]
)

if pid > 0:
    print(f"Validation running in background (PID {pid})")
    # Parent returns immediately - git proceeds with commit
else:
    print("ERROR: Could not fork validation")
    sys.exit(1)
```

### Example 2: Check Previous Run

```python
from huskycat.core.process_manager import ProcessManager

manager = ProcessManager()

# Check for previous failed validation
previous_run = manager.check_previous_run()

if previous_run:
    print(f"WARNING: Previous validation failed with {previous_run.errors} errors")

    # Handle previous failure (prompts user if TTY)
    if not manager.handle_previous_failure(previous_run):
        print("Aborting commit")
        sys.exit(1)
```

### Example 3: Convenience Function

```python
from huskycat.core.process_manager import should_proceed_with_commit

# Simple one-liner for git hooks
if not should_proceed_with_commit():
    sys.exit(1)  # Abort commit on previous failure
```

### Example 4: Run History and Cleanup

```python
from huskycat.core.process_manager import ProcessManager

manager = ProcessManager()

# Get recent runs
history = manager.get_run_history(limit=10)
for run in history:
    status = "PASS" if run.success else "FAIL"
    print(f"[{status}] {run.run_id} - {run.errors} errors")

# Cleanup old runs (older than 7 days)
manager.cleanup_old_runs(max_age_days=7)

# Cleanup zombie processes
manager.cleanup_zombies()
```

## Git Hook Integration

### Pre-Commit Hook Template

```bash
#!/bin/bash
# .git/hooks/pre-commit
# Auto-generated by huskycat

# Get staged files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACMR)

if [ -z "$STAGED_FILES" ]; then
    exit 0  # No files to validate
fi

# Check previous validation
huskycat --check-previous-run || exit 1

# Fork validation to background
huskycat validate --staged --fork

# Parent returns immediately (validation runs in background)
exit 0
```

### Python Integration in Hooks

```python
#!/usr/bin/env python3
"""Pre-commit hook with ProcessManager integration."""

import sys
import subprocess
from pathlib import Path
from huskycat.core.process_manager import ProcessManager, should_proceed_with_commit

def main():
    # Check previous run (with user prompt if failed)
    if not should_proceed_with_commit():
        print("Fix validation issues before committing")
        return 1

    # Get staged files
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True,
        text=True
    )

    files = result.stdout.strip().split("\n")
    if not files or files == [""]:
        return 0  # No files to validate

    # Fork validation
    manager = ProcessManager()
    pid = manager.fork_validation(
        files=files,
        validation_cmd="huskycat",
        validation_args=["validate", "--staged"]
    )

    if pid <= 0:
        print("ERROR: Could not start validation")
        return 1

    # Parent returns immediately
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## Edge Cases Handled

### 1. Duplicate Validation Prevention
```python
# Checks if validation already running for same files
if manager._is_running(files):
    print("Validation already running for these files")
    return 0
```

### 2. Stale PID Cleanup
```python
# Automatically removes PID files for dead processes
running = manager.get_running_validations()
# Stale PIDs are cleaned up during this call
```

### 3. Non-Interactive Mode
```python
# handle_previous_failure() checks TTY availability
if not sys.stdin.isatty() or not sys.stdout.isatty():
    # Non-interactive: fail safely, don't prompt
    return False
```

### 4. Zombie Process Cleanup
```python
# Reap completed child processes
manager.cleanup_zombies()
```

### 5. Fork Failure Handling
```python
try:
    pid = os.fork()
except OSError as e:
    logger.error(f"Fork failed: {e}")
    return -1  # Indicate failure to caller
```

## Performance Characteristics

- **Parent Return Time**: <100ms (typically <10ms)
- **Child Startup Time**: <200ms to redirect I/O and start validation
- **PID File Operations**: O(1) file writes
- **Previous Run Check**: O(1) single file read
- **Process Check**: O(n) where n = number of running validations (typically 1-2)

## Testing

Run the comprehensive test suite:

```bash
# Run all ProcessManager tests
uv run pytest tests/test_process_manager.py -v

# Run specific test
uv run pytest tests/test_process_manager.py::test_fork_validation -v

# Run with coverage
uv run pytest tests/test_process_manager.py --cov=src.huskycat.core.process_manager
```

## Dependencies

- **psutil** (>=5.9.0): Process management and lifecycle checks
- **Python stdlib**: os, sys, signal, json, pathlib, datetime, dataclasses

## Integration Checklist

When integrating ProcessManager into git hooks:

- [ ] Add `from huskycat.core.process_manager import ProcessManager, should_proceed_with_commit`
- [ ] Call `should_proceed_with_commit()` before starting new validation
- [ ] Use `fork_validation()` to run validation in background
- [ ] Ensure parent process returns quickly (<100ms)
- [ ] Handle fork failures gracefully
- [ ] Set up log file redirection in child process
- [ ] Test with both interactive (TTY) and non-interactive modes
- [ ] Add cleanup_zombies() call to prevent zombie accumulation
- [ ] Configure cleanup_old_runs() for cache maintenance

## Future Enhancements

Potential improvements for future iterations:

1. **Parallel Validation**: Support multiple tool processes running concurrently
2. **Progress Streaming**: Real-time progress updates via named pipes or sockets
3. **Run Aggregation**: Combine multiple partial runs into comprehensive reports
4. **Performance Analytics**: Track validation times and identify slow tools
5. **Smart Caching**: Skip unchanged files based on content hash
6. **Distributed Validation**: Offload validation to remote workers

## Troubleshooting

### Validation Process Not Starting

Check if fork is failing:
```python
pid = manager.fork_validation(...)
if pid < 0:
    print("Fork failed - check system resources")
```

### PID Files Accumulating

Manually cleanup:
```python
manager.cleanup_zombies()
running = manager.get_running_validations()  # Auto-cleans stale PIDs
```

### Previous Run Always Prompting

Clear the last run:
```python
manager._clear_last_run()
```

### Log Files Growing Large

Set up periodic cleanup:
```bash
# Cron job to cleanup old runs
0 2 * * * cd /path/to/repo && huskycat cleanup-old-runs --days 7
```

## See Also

- [Git Hooks Documentation](./git_hooks.md)
- [TUI Integration Guide](./tui_integration.md)
- [Mode Detection](./mode_detection.md)
- [Sprint Plan](./SPRINT_PLAN.md)
