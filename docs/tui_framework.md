# TUI Framework Documentation

## Overview

The HuskyCat TUI (Terminal User Interface) Framework provides real-time validation progress display using the Rich library. It is designed for non-blocking operation with thread-safe updates, making it ideal for concurrent validation processes.

## Features

- Real-time progress display with overall completion percentage
- Individual tool status tracking (pending/running/success/failed)
- Error and warning counts per tool
- Elapsed time tracking with human-readable formatting
- Thread-safe updates from concurrent validation processes
- Clean terminal cleanup on exit
- Graceful degradation for non-TTY environments
- Zero-overhead when not in TTY mode

## Architecture

### Core Components

#### ToolState Enum

Represents the execution state of a validation tool:

```python
class ToolState(Enum):
    PENDING = "pending"    # Tool not yet started
    RUNNING = "running"    # Tool currently executing
    SUCCESS = "success"    # Tool completed without errors
    FAILED = "failed"      # Tool completed with errors
    SKIPPED = "skipped"    # Tool was skipped
```

#### ToolStatus Dataclass

Tracks status information for a single validation tool:

```python
@dataclass
class ToolStatus:
    name: str                          # Tool identifier
    state: ToolState                   # Current execution state
    duration: float                    # Time elapsed in seconds
    errors: int                        # Count of errors found
    warnings: int                      # Count of warnings found
    files_processed: int               # Number of files processed
    start_time: Optional[float]        # Unix timestamp when started
```

#### ValidationTUI Class

Main class for TUI management:

```python
class ValidationTUI:
    def start(self, tool_names: List[str]) -> None
    def update_tool(self, tool_name: str, state: ToolState, ...) -> None
    def render(self) -> Table
    def stop(self) -> None
```

## Usage

### Basic Usage

```python
from huskycat.core.tui import ValidationTUI, ToolState

# Create TUI instance
tui = ValidationTUI()

# Start with list of tools
tui.start(["black", "mypy", "ruff", "flake8"])

# Update tool status as validation progresses
tui.update_tool("black", ToolState.RUNNING)
# ... perform black validation ...
tui.update_tool("black", ToolState.SUCCESS, errors=0, warnings=0)

tui.update_tool("mypy", ToolState.RUNNING)
# ... perform mypy validation ...
tui.update_tool("mypy", ToolState.FAILED, errors=5, warnings=2)

# Clean shutdown
tui.stop()
```

### Context Manager (Recommended)

```python
from huskycat.core.tui import validation_tui, ToolState

with validation_tui(["black", "mypy", "ruff"]) as tui:
    tui.update_tool("black", ToolState.RUNNING)
    # ... perform validation ...
    tui.update_tool("black", ToolState.SUCCESS)
# TUI automatically cleaned up on exit
```

### Parallel Validation

The TUI is thread-safe and supports concurrent tool execution:

```python
import threading
from huskycat.core.tui import validation_tui, ToolState

def validate_with_tool(tui, tool_name):
    tui.update_tool(tool_name, ToolState.RUNNING)
    # ... perform validation ...
    tui.update_tool(tool_name, ToolState.SUCCESS, errors=0, warnings=1)

with validation_tui(["black", "mypy", "ruff"]) as tui:
    threads = [
        threading.Thread(target=validate_with_tool, args=(tui, "black")),
        threading.Thread(target=validate_with_tool, args=(tui, "mypy")),
        threading.Thread(target=validate_with_tool, args=(tui, "ruff")),
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()
```

### Dynamic Tool Addition

Tools can be added dynamically during validation:

```python
with validation_tui(["black"]) as tui:
    # Start with black
    tui.update_tool("black", ToolState.SUCCESS)

    # Dynamically add mypy
    tui.update_tool("mypy", ToolState.RUNNING)
    # ... validation ...
    tui.update_tool("mypy", ToolState.SUCCESS)
```

## Display Format

The TUI displays a real-time table with the following structure:

```
HuskyCat Validation (Non-Blocking Mode)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tool            Status      Time    Errors  Warnings  Files
─────────────────────────────────────────────────────────────
Overall Progress ████████░░ 80%  5.2s                 12/15
─────────────────────────────────────────────────────────────
black           ✓ Done      0.3s    0       0         23
ruff            ✓ Done      0.5s    0       2         23
mypy            ⠋ Running   2.1s    -       -         15
flake8          • Pending   -       -       -         -
pylint          • Pending   -       -       -         -
```

### Status Icons

- `• Pending` - Tool not yet started (dim)
- `⠋ Running` - Tool currently executing (cyan, animated spinner)
- `✓ Done` - Tool completed successfully (green)
- `✗ Failed` - Tool completed with errors (red)
- `⊘ Skipped` - Tool was skipped (dim)

### Time Formatting

- Under 60s: `"0.3s"`, `"5.7s"`
- Over 60s: `"1m 23s"`, `"5m 42s"`

## Integration with Process Manager

The TUI is designed to integrate with `process_manager.py` for shared state:

```python
# process_manager.py integration (example)
class ProcessManager:
    def __init__(self, tui: Optional[ValidationTUI] = None):
        self.tui = tui

    def run_tool(self, tool_name: str):
        if self.tui:
            self.tui.update_tool(tool_name, ToolState.RUNNING)

        # ... run validation ...

        if self.tui:
            self.tui.update_tool(
                tool_name,
                ToolState.SUCCESS if success else ToolState.FAILED,
                errors=error_count,
                warnings=warning_count
            )
```

## TTY Detection and Graceful Degradation

The TUI automatically detects non-TTY environments and gracefully degrades:

```python
# Check TTY availability
from huskycat.core.tui import is_tty_available

if is_tty_available():
    # Use full TUI
    with validation_tui(tools) as tui:
        # ... validation with TUI ...
else:
    # Fallback to simple output
    print("Running validation...")
    # ... validation without TUI ...
```

### Non-TTY Behavior

When running in non-TTY environments (pipes, CI, etc.):

- `start()` becomes a no-op
- `update_tool()` becomes a no-op
- No Rich display is created
- Zero performance overhead

## Performance Considerations

### Refresh Rate

The TUI refresh rate can be configured:

```python
# Default: 10 updates per second (0.1s interval)
tui = ValidationTUI(refresh_rate=0.1)

# High refresh rate for smooth animations
tui = ValidationTUI(refresh_rate=0.05)  # 20 updates/sec

# Low refresh rate to reduce CPU usage
tui = ValidationTUI(refresh_rate=0.2)   # 5 updates/sec
```

### Thread Safety

All TUI methods are protected by `threading.RLock()`:

- Multiple threads can safely call `update_tool()`
- Rendering is atomic and consistent
- No race conditions on shared state

### Memory Usage

- Minimal memory overhead (~1KB per tool)
- No unbounded memory growth
- Clean resource cleanup on `stop()`

## Testing

Comprehensive test coverage in `tests/test_tui.py`:

```bash
# Run TUI tests
pytest tests/test_tui.py -v

# Run with coverage
pytest tests/test_tui.py --cov=src.huskycat.core.tui --cov-report=term-missing
```

### Test Categories

1. **ToolStatus Tests** - State transitions, timing
2. **ValidationTUI Tests** - Initialization, updates, rendering
3. **Context Manager Tests** - Lifecycle management
4. **Thread Safety Tests** - Concurrent updates
5. **TTY Detection Tests** - Graceful degradation
6. **Utility Function Tests** - Helper functions

## Demo

Run the interactive demo to see the TUI in action:

```bash
# Run demo script
python examples/tui_demo.py

# Or with UV
uv run python examples/tui_demo.py
```

The demo showcases:

1. Sequential validation (one tool at a time)
2. Parallel validation (concurrent tools)
3. Dynamic tool addition during validation
4. Various error scenarios

## API Reference

### ValidationTUI

#### `__init__(refresh_rate: float = 0.1)`

Initialize TUI framework.

**Parameters:**
- `refresh_rate` - Display refresh interval in seconds (default: 0.1)

#### `start(tool_names: List[str]) -> None`

Initialize TUI with list of tools to track.

**Parameters:**
- `tool_names` - List of tool identifiers to display

#### `update_tool(tool_name: str, state: ToolState, errors: int = 0, warnings: int = 0, files_processed: int = 0) -> None`

Update status of a specific tool (thread-safe).

**Parameters:**
- `tool_name` - Tool identifier
- `state` - New state for the tool
- `errors` - Current error count (default: 0)
- `warnings` - Current warning count (default: 0)
- `files_processed` - Number of files processed (default: 0)

#### `render() -> Table`

Generate Rich Table for display.

**Returns:**
- Rich Table with current validation status

#### `stop() -> None`

Clean stop of TUI display.

### Context Manager

#### `validation_tui(tool_names: List[str], refresh_rate: float = 0.1)`

Context manager for validation TUI. Automatically starts and stops display.

**Parameters:**
- `tool_names` - List of tools to track
- `refresh_rate` - Display refresh interval in seconds (default: 0.1)

**Yields:**
- ValidationTUI instance

### Utility Functions

#### `is_tty_available() -> bool`

Check if TUI can be displayed (TTY available).

**Returns:**
- True if stdout is a TTY, False otherwise

#### `create_simple_spinner(message: str = "Validating...") -> Live`

Create a simple spinner for non-TUI fallback.

**Parameters:**
- `message` - Message to display (default: "Validating...")

**Returns:**
- Rich Live display with spinner

## Design Decisions

### Why Rich Library?

- Production-ready terminal UI library
- Excellent table rendering and progress bars
- Built-in TTY detection
- Cross-platform compatibility
- Already in project dependencies

### Why Thread-Based Updates?

- Validation tools run in parallel processes
- TUI needs to receive updates from multiple sources
- Thread-safe design prevents race conditions
- Simple integration model for callers

### Why Graceful Degradation?

- CI/Pipeline environments are non-interactive
- TUI should not impact non-TTY use cases
- Zero overhead when TUI is not needed
- Maintains compatibility with all HuskyCat modes

### Why Context Manager Pattern?

- Ensures proper resource cleanup
- Automatic start/stop lifecycle
- Exception-safe design
- Pythonic and intuitive API

## Future Enhancements

Potential future improvements:

1. **Color Themes** - Support for different color schemes
2. **Logging Integration** - Save TUI output to file
3. **Progress Estimation** - ETA based on historical data
4. **Interactive Mode** - Key bindings for pause/resume
5. **Network Status** - Show network tool execution status
6. **Resource Monitoring** - CPU/memory usage per tool

## Troubleshooting

### TUI Not Displaying

**Problem:** TUI does not appear when running validation.

**Solutions:**
- Verify running in a TTY: `python -c "import sys; print(sys.stdout.isatty())"`
- Check TERM environment variable: `echo $TERM`
- Ensure Rich library is installed: `pip show rich`

### Display Flickering

**Problem:** TUI display flickers or updates too fast.

**Solutions:**
- Reduce refresh rate: `ValidationTUI(refresh_rate=0.2)`
- Check terminal emulator compatibility
- Update Rich library to latest version

### Thread Deadlock

**Problem:** TUI stops updating or hangs.

**Solutions:**
- Ensure proper `stop()` call or use context manager
- Check for exceptions in validation threads
- Verify thread cleanup in your integration code

## Contributing

When contributing to the TUI framework:

1. Add tests for new features in `tests/test_tui.py`
2. Update this documentation with API changes
3. Run the demo to verify visual changes
4. Ensure thread-safety for all shared state access
5. Test in both TTY and non-TTY environments

## Related Documentation

- [Mode Detection](./mode_detection.md) - How TUI integrates with product modes
- [CLI Adapter](./adapters_cli.md) - CLI mode integration
- [Process Manager](./process_manager.md) - Validation process coordination
