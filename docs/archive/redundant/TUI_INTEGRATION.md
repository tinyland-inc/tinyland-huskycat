# TUI Framework Integration Guide

## Overview

The HuskyCat TUI (Terminal User Interface) framework provides real-time validation progress display using the Rich library. It's designed for non-blocking operation with thread-safe updates, making it ideal for displaying validation progress during git hooks or CLI operations.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Validation Process                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Tool 1    │  │   Tool 2    │  │   Tool 3    │    │
│  │  (Thread)   │  │  (Thread)   │  │  (Thread)   │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
│         │                │                │             │
│         └────────────────┼────────────────┘             │
│                          │                              │
│                     Thread-Safe                         │
│                    Update Queue                         │
│                          │                              │
│                          ▼                              │
│                ┌──────────────────┐                     │
│                │  ValidationTUI   │                     │
│                │   (RLock sync)   │                     │
│                └────────┬─────────┘                     │
│                         │                               │
│                         ▼                               │
│                  ┌─────────────┐                        │
│                  │  Rich Live  │                        │
│                  │   Display   │                        │
│                  └─────────────┘                        │
│                         │                               │
└─────────────────────────┼───────────────────────────────┘
                          ▼
                    Terminal Output
```

## Core Components

### 1. ToolState Enum

Defines the possible states for validation tools:

```python
from huskycat.core.tui import ToolState

ToolState.PENDING   # Tool hasn't started yet
ToolState.RUNNING   # Tool is currently executing
ToolState.SUCCESS   # Tool completed successfully
ToolState.FAILED    # Tool completed with errors
ToolState.SKIPPED   # Tool was skipped
```

### 2. ToolStatus Dataclass

Tracks the status of a single validation tool:

```python
from huskycat.core.tui import ToolStatus

tool = ToolStatus(name="mypy")
tool.start()                      # Mark as running
tool.complete(                    # Mark as complete
    success=True,
    errors=0,
    warnings=2
)
```

**Attributes:**
- `name: str` - Tool identifier
- `state: ToolState` - Current execution state
- `duration: float` - Time elapsed in seconds
- `errors: int` - Count of errors found
- `warnings: int` - Count of warnings found
- `files_processed: int` - Number of files processed
- `start_time: Optional[float]` - Unix timestamp when started

### 3. ValidationTUI Class

Main TUI controller for real-time progress display:

```python
from huskycat.core.tui import ValidationTUI, ToolState

# Create TUI instance
tui = ValidationTUI(refresh_rate=0.1)

# Initialize with tool list
tui.start(["black", "mypy", "ruff", "flake8"])

# Update tool status (thread-safe)
tui.update_tool("black", ToolState.RUNNING)
tui.update_tool("black", ToolState.SUCCESS, errors=0, warnings=0)

# Clean shutdown
tui.stop()
```

**Methods:**
- `start(tool_names)` - Initialize TUI with list of tools
- `update_tool(name, state, errors, warnings, files_processed)` - Update tool status
- `render()` - Generate Rich Table for display
- `stop()` - Clean stop of TUI

**Features:**
- Thread-safe updates using RLock
- Automatic TTY detection
- Graceful degradation for non-TTY environments
- Configurable refresh rate
- Dynamic tool addition

## Usage Patterns

### Pattern 1: Context Manager (Recommended)

The cleanest way to use the TUI with automatic cleanup:

```python
from huskycat.core.tui import validation_tui, ToolState

tools = ["black", "mypy", "ruff"]

with validation_tui(tools) as tui:
    for tool_name in tools:
        tui.update_tool(tool_name, ToolState.RUNNING)

        # Run validation
        result = run_tool(tool_name)

        # Update with results
        state = ToolState.SUCCESS if result.passed else ToolState.FAILED
        tui.update_tool(
            tool_name,
            state,
            errors=result.errors,
            warnings=result.warnings,
            files_processed=result.files_count
        )

# TUI automatically stopped here
```

### Pattern 2: Manual Lifecycle

For more control over TUI lifecycle:

```python
from huskycat.core.tui import ValidationTUI, ToolState

tui = ValidationTUI(refresh_rate=0.1)

try:
    tui.start(["black", "mypy", "ruff"])

    # Your validation logic here
    tui.update_tool("black", ToolState.RUNNING)
    # ...

finally:
    tui.stop()
```

### Pattern 3: Thread Pool Integration

For concurrent tool execution:

```python
from concurrent.futures import ThreadPoolExecutor
from huskycat.core.tui import validation_tui, ToolState

def run_tool_with_tui(tool_name, tui):
    """Run tool and update TUI."""
    tui.update_tool(tool_name, ToolState.RUNNING)

    try:
        result = execute_tool(tool_name)
        state = ToolState.SUCCESS if result.passed else ToolState.FAILED
        tui.update_tool(
            tool_name,
            state,
            errors=result.errors,
            warnings=result.warnings
        )
    except Exception as e:
        tui.update_tool(tool_name, ToolState.FAILED, errors=1)

tools = ["black", "mypy", "ruff", "flake8"]

with validation_tui(tools) as tui:
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(run_tool_with_tui, tool, tui)
            for tool in tools
        ]

        # Wait for all tools to complete
        for future in futures:
            future.result()
```

## Integration with ProcessManager

The TUI is designed to work seamlessly with HuskyCat's ProcessManager for non-blocking git hooks:

```python
from pathlib import Path
from huskycat.core.process_manager import ProcessManager
from huskycat.core.tui import validation_tui, ToolState

def git_hook_with_tui(files):
    """Git hook with TUI display."""
    manager = ProcessManager()

    # Check if we should proceed
    if not manager.should_proceed_with_commit():
        return False

    tools = ["black", "mypy", "ruff"]

    with validation_tui(tools) as tui:
        # Run validation in background process
        pid = manager.fork_validation(
            files=files,
            validation_cmd="huskycat",
            validation_args=["validate", "--staged"]
        )

        if pid > 0:
            # Parent process: Show initial status
            print(f"Validation running in background (PID {pid})")
            return True  # Allow commit to proceed

    return False
```

## Display Format

The TUI generates a clean, informative display:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        HuskyCat Validation (Non-Blocking Mode)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tool            Status       Time    Errors  Warnings  Files
──────────────────────────────────────────────────────────────
Overall Progress  ████████░░ 80%  5.2s        4/5

black             ✓ Done     0.3s    0       0         25
ruff              ✓ Done     0.5s    0       2         25
mypy              ⠋ Running  2.1s    -       -         15
flake8            • Pending   -      -       -          -
pytest            • Pending   -      -       -          -
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Features:**
- Overall progress bar with percentage
- Individual tool status with icons
- Real-time duration updates
- Error and warning counts
- Files processed counter
- Color-coded states:
  - Green: Success
  - Red: Failed
  - Cyan: Running
  - Dim: Pending/Skipped

## TTY Detection and Graceful Degradation

The TUI automatically detects terminal capabilities:

```python
from huskycat.core.tui import is_tty_available, create_simple_spinner

if is_tty_available():
    # Full TUI with rich display
    with validation_tui(tools) as tui:
        # ... full TUI logic
else:
    # Fallback to simple spinner or no UI
    with create_simple_spinner("Validating..."):
        # ... validation logic without TUI
```

**Detection logic:**
1. Check `sys.stdout.isatty()`
2. If not TTY, gracefully skip TUI initialization
3. All `update_tool()` calls become no-ops
4. No errors or exceptions raised

## Thread Safety

The TUI is fully thread-safe for concurrent updates:

```python
import threading
from huskycat.core.tui import validation_tui, ToolState

def worker(tool_name, tui):
    """Worker thread updates TUI."""
    tui.update_tool(tool_name, ToolState.RUNNING)
    # ... do work ...
    tui.update_tool(tool_name, ToolState.SUCCESS)

tools = ["tool1", "tool2", "tool3"]

with validation_tui(tools) as tui:
    threads = [
        threading.Thread(target=worker, args=(tool, tui))
        for tool in tools
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()
```

**Thread safety features:**
- `threading.RLock` for reentrant locking
- Atomic updates to tool status
- Safe concurrent rendering
- No race conditions on state changes

## Performance Considerations

### Refresh Rate

Control how often the display updates:

```python
# Fast updates (10 FPS) - good for quick tools
tui = ValidationTUI(refresh_rate=0.1)

# Moderate updates (5 FPS) - balanced
tui = ValidationTUI(refresh_rate=0.2)

# Slow updates (2 FPS) - reduce CPU usage
tui = ValidationTUI(refresh_rate=0.5)
```

**Guidelines:**
- Fast tools (< 1s): 0.1s refresh
- Medium tools (1-10s): 0.2s refresh
- Long tools (> 10s): 0.5s refresh

### Memory Usage

TUI maintains minimal state:
- ~100 bytes per tool status
- ~500 bytes for TUI instance
- No accumulation over time
- Clean cleanup on stop()

### CPU Usage

- Negligible when not updating
- ~0.1% CPU during active updates
- Uses Rich's efficient rendering
- No busy-waiting or polling

## Error Handling

The TUI handles errors gracefully:

```python
from huskycat.core.tui import validation_tui, ToolState

with validation_tui(["black", "mypy"]) as tui:
    for tool in ["black", "mypy"]:
        try:
            tui.update_tool(tool, ToolState.RUNNING)
            result = run_tool(tool)
            tui.update_tool(tool, ToolState.SUCCESS)
        except Exception as e:
            # Mark tool as failed
            tui.update_tool(tool, ToolState.FAILED, errors=1)
            # TUI continues displaying other tools
```

**Error scenarios handled:**
- TTY not available → graceful skip
- Invalid tool names → dynamic addition
- Render exceptions → logged, not raised
- Stop during updates → clean shutdown

## Testing

Comprehensive test suite in `tests/test_tui.py`:

```bash
# Run all TUI tests
pytest tests/test_tui.py -v

# Run specific test class
pytest tests/test_tui.py::TestThreadSafety -v

# Run with coverage
pytest tests/test_tui.py --cov=src/huskycat/core/tui
```

**Test coverage:**
- Tool status lifecycle
- Thread-safe concurrent updates
- TTY detection and degradation
- Progress calculation
- Time formatting
- Context manager behavior
- Progress bar rendering

## Demo

Run the demo to see TUI in action:

```bash
python examples/demo_tui.py
```

This demonstrates:
- Real-time progress updates
- Multiple tool execution
- Error and warning display
- Files processed counter
- Overall progress tracking

## Best Practices

### 1. Always Use Context Manager

Ensures proper cleanup even on exceptions:

```python
# Good
with validation_tui(tools) as tui:
    # ... validation logic

# Avoid
tui = ValidationTUI()
tui.start(tools)
# ... if exception occurs, stop() might not be called
```

### 2. Update Tools Promptly

Don't let tools sit in RUNNING state:

```python
# Good
tui.update_tool("mypy", ToolState.RUNNING)
result = run_mypy()
tui.update_tool("mypy", ToolState.SUCCESS)

# Avoid long gaps
tui.update_tool("mypy", ToolState.RUNNING)
time.sleep(10)  # No updates for 10 seconds
```

### 3. Provide Accurate Counts

Help users understand validation progress:

```python
# Good
tui.update_tool(
    "black",
    ToolState.SUCCESS,
    errors=0,
    warnings=2,
    files_processed=25
)

# Avoid leaving counts at default
tui.update_tool("black", ToolState.SUCCESS)
```

### 4. Check TTY Before Fancy Features

```python
from huskycat.core.tui import is_tty_available

if is_tty_available():
    # Full TUI experience
    with validation_tui(tools) as tui:
        # ...
else:
    # Simple text output
    print("Running validation...")
    # ...
```

### 5. Handle Tool Failures Gracefully

```python
for tool in tools:
    tui.update_tool(tool, ToolState.RUNNING)
    try:
        result = run_tool(tool)
        state = ToolState.SUCCESS if result.passed else ToolState.FAILED
        tui.update_tool(tool, state, errors=result.errors)
    except Exception:
        tui.update_tool(tool, ToolState.FAILED, errors=1)
        # Continue with other tools
```

## Troubleshooting

### TUI Not Displaying

**Symptom:** No TUI appears, validation runs silently

**Cause:** Not running in a TTY

**Solution:**
```python
from huskycat.core.tui import is_tty_available

if not is_tty_available():
    print("TUI requires interactive terminal")
```

### Garbled Output

**Symptom:** Display looks corrupted

**Cause:** Terminal doesn't support Unicode or colors

**Solution:**
```bash
# Set terminal encoding
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# Or use ASCII-only mode (feature to be added)
```

### Updates Not Showing

**Symptom:** Tool status doesn't update in real-time

**Cause:** Updates too fast or slow refresh rate

**Solution:**
```python
# Adjust refresh rate
tui = ValidationTUI(refresh_rate=0.05)  # 20 FPS
```

### Memory Leak Concerns

**Symptom:** Worried about long-running processes

**Solution:** TUI has fixed memory footprint, no leaks

```python
# Memory is constant regardless of runtime
with validation_tui(tools, refresh_rate=0.2) as tui:
    # Even if this runs for hours, memory usage is constant
    for i in range(1000000):
        tui.update_tool("tool", ToolState.RUNNING, files_processed=i)
```

## API Reference

### ValidationTUI

```python
class ValidationTUI:
    def __init__(self, refresh_rate: float = 0.1)
    def start(self, tool_names: List[str]) -> None
    def update_tool(
        self,
        tool_name: str,
        state: ToolState,
        errors: int = 0,
        warnings: int = 0,
        files_processed: int = 0,
    ) -> None
    def render(self) -> Table
    def stop(self) -> None
```

### ToolStatus

```python
@dataclass
class ToolStatus:
    name: str
    state: ToolState = ToolState.PENDING
    duration: float = 0.0
    errors: int = 0
    warnings: int = 0
    files_processed: int = 0
    start_time: Optional[float] = None

    def start(self) -> None
    def complete(self, success: bool, errors: int = 0, warnings: int = 0) -> None
    def update_duration(self) -> None
```

### ToolState

```python
class ToolState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
```

### Utility Functions

```python
def validation_tui(
    tool_names: List[str],
    refresh_rate: float = 0.1
) -> ContextManager[ValidationTUI]

def is_tty_available() -> bool

def create_simple_spinner(message: str = "Validating...") -> Live
```

## Future Enhancements

Potential improvements for future versions:

1. **Streaming logs** - Show tool output inline
2. **Progress bars per tool** - Individual progress tracking
3. **ASCII-only mode** - For terminals without Unicode
4. **Summary statistics** - Total errors/warnings at bottom
5. **Color schemes** - Configurable themes
6. **JSON output mode** - Machine-readable progress
7. **WebSocket updates** - Remote monitoring
8. **Notification integration** - Desktop notifications on completion

## Related Documentation

- [Process Manager Guide](./PROCESS_MANAGER.md) - Non-blocking execution
- [Sprint Plan](./SPRINT_PLAN.md) - Development roadmap
- [API Documentation](./API.md) - Full API reference
- [Testing Guide](./TESTING.md) - Test suite documentation

## Support

For issues or questions:
- GitHub Issues: https://github.com/huskycat/issues
- Documentation: https://huskycat.pages.io
- Tests: `tests/test_tui.py`
