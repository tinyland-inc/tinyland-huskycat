# Embedded Tool Execution Architecture

## Overview

HuskyCat now supports **standalone fat binaries** with embedded validation tools, eliminating container runtime dependencies for binary distributions.

This document describes the refactored execution architecture in `src/huskycat/unified_validation.py` that enables three execution modes with intelligent tool resolution.

---

## Execution Modes

### 1. Bundled Mode (Fat Binary)

**When**: Running from PyInstaller bundle with extracted tools

**Detection**:
- `sys.frozen == True` (PyInstaller bundle)
- `~/.huskycat/tools/` directory exists

**Tool Resolution**:
- Tools are extracted from bundle to `~/.huskycat/tools/` on first run
- Tools are version-tracked and re-extracted only when bundle version changes
- Direct execution using absolute paths (no PATH lookup needed)

**Advantages**:
- No external dependencies (no container runtime required)
- Fast startup (no container overhead)
- Portable across machines
- Deterministic tool versions

**Example**:
```bash
# Download fat binary
./dist/huskycat validate --staged

# Tools automatically extracted to ~/.huskycat/tools/
# Runs: ~/.huskycat/tools/python-black --check file.py
```

---

### 2. Local Mode (Development)

**When**: Running from source code with tools in system PATH

**Detection**:
- Not in container
- Not frozen (not PyInstaller bundle)
- Tools available via `which`

**Tool Resolution**:
- Uses system PATH to locate tools
- Relies on user-installed tool versions
- No container overhead

**Advantages**:
- Fast development iteration
- Uses local tool installations
- No extraction overhead

**Example**:
```bash
# Running from source
uv run python -m src.huskycat validate .

# Runs: python-black --check file.py (from PATH)
```

---

### 3. Container Mode

**When**: Running inside a container (Docker/Podman)

**Detection**:
- `/.dockerenv` exists (Docker)
- `/run/.containerenv` exists (Podman)
- `container` environment variable set

**Tool Resolution**:
- Tools pre-installed in container image
- Direct execution from container PATH

**Advantages**:
- Isolated environment
- Consistent tool versions across CI/CD
- Pre-configured dependencies

**Example**:
```bash
# Inside container
huskycat validate /workspace

# Runs: python-black --check file.py (from container)
```

---

### 4. Container Fallback (Legacy)

**When**: No local tools available, container runtime exists

**Detection**:
- Not in container
- Not bundled
- Tools not in PATH
- Podman or Docker available

**Tool Resolution**:
- Delegates to container runtime
- Mounts current directory as `/workspace`
- Runs tools inside `huskycat:local` container

**Warnings**:
- Logs warning about container fallback
- Slower than direct execution
- Requires container image built

**Example**:
```bash
# No local tools, but docker available
huskycat validate .

# Warning logged
# Runs: docker run --rm -v $PWD:/workspace huskycat:local python-black --check file.py
```

---

## Priority Order

Tool execution follows strict priority:

```
1. Bundled tools      (~/.huskycat/tools/)
2. Local tools        (system PATH)
3. Container tools    (if already in container)
4. Container runtime  (fallback, with warning)
```

**Rationale**:
- **Bundled first**: Most portable, no dependencies
- **Local second**: Fastest for development
- **Container third**: Already inside, use what's available
- **Fallback last**: Requires container runtime, slowest

---

## Implementation Details

### Execution Mode Detection

```python
def _get_execution_mode(self) -> str:
    """Detect execution mode

    Returns:
        - "bundled": Running from PyInstaller bundle with embedded tools
        - "local": Running from source with tools in PATH
        - "container": Running inside container
    """
    if self._is_running_in_container():
        return "container"

    if getattr(sys, 'frozen', False):
        bundled_path = Path.home() / ".huskycat" / "tools"
        if bundled_path.exists():
            return "bundled"

    return "local"
```

### Tool Availability Check

```python
def is_available(self) -> bool:
    """Check if validator is available in current execution context

    Priority order:
    1. Bundled tools (from fat binary)
    2. Local tools (in PATH)
    3. Container runtime (fallback only)
    """
    mode = self._get_execution_mode()

    if mode == "bundled":
        tool_path = self._get_bundled_tool_path()
        return tool_path is not None and tool_path.exists() and os.access(tool_path, os.X_OK)

    if mode == "local":
        return shutil.which(self.command) is not None

    if mode == "container":
        result = subprocess.run(
            ["which", self.command],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0

    # Fallback: check for container runtime
    return self._container_runtime_exists()
```

### Command Execution

```python
def _execute_command(self, cmd: List[str], **kwargs: Any) -> subprocess.CompletedProcess:
    """Execute command with mode-aware execution"""
    mode = self._get_execution_mode()

    if mode == "bundled":
        self._log_execution_mode(mode)
        return self._execute_bundled(cmd, **kwargs)

    if mode == "local":
        self._log_execution_mode(mode)
        return self._execute_local(cmd, **kwargs)

    if mode == "container":
        self._log_execution_mode(mode)
        return subprocess.run(cmd, **kwargs)

    # Fallback: delegate to container
    logger.warning(f"Falling back to container execution for {self.command}")
    container_cmd = self._build_container_command(cmd)
    return subprocess.run(container_cmd, **kwargs)
```

### Bundled Tool Execution

```python
def _execute_bundled(self, cmd: List[str], **kwargs: Any) -> subprocess.CompletedProcess:
    """Execute using bundled tools

    Replaces tool name with absolute path to extracted tool.
    """
    tool_path = self._get_bundled_tool_path()

    if not tool_path:
        raise RuntimeError(f"Bundled tool {self.command} not found")

    # Replace tool name with full path
    bundled_cmd = [str(tool_path)] + cmd[1:]

    return subprocess.run(bundled_cmd, **kwargs)
```

---

## Tool Extraction Process

### Phase 1: Bundle Creation

```bash
# Download tools
python scripts/download_tools.py

# Bundle with PyInstaller
python build_fat_binary.py

# Result: dist/huskycat (with embedded tools/)
```

### Phase 2: First Run Extraction

```python
# In __main__.py
from .core.tool_extractor import ensure_tools
ensure_tools()

# Extracts to:
# ~/.huskycat/tools/python-black
# ~/.huskycat/tools/ruff
# ~/.huskycat/tools/mypy
# ~/.huskycat/tools/.version
```

### Phase 3: Version Tracking

```python
# Check if re-extraction needed
def needs_extraction(self) -> bool:
    bundle_version = self.get_bundle_version()  # From bundle manifest
    cached_version = self.get_cached_version()  # From ~/.huskycat/tools/.version

    return bundle_version != cached_version or not self.cache_dir.exists()
```

---

## Configuration Options

### Future Configuration Support

While not yet implemented, the architecture supports:

```yaml
# ~/.huskycat/config.yaml
execution:
  prefer_bundled: true       # Prefer bundled tools over local
  allow_container_fallback: true  # Allow container fallback if no tools
  container_image: "huskycat:local"  # Container image for fallback
```

---

## Logging and Diagnostics

### Debug Logging

Enable verbose logging to see execution mode decisions:

```bash
export HUSKYCAT_LOG_LEVEL=DEBUG
huskycat validate .
```

**Output**:
```
DEBUG - Tool execution mode: bundled (tool=python-black)
DEBUG - Using bundled tools from: /Users/user/.huskycat/tools
DEBUG - Tool execution mode: bundled (tool=ruff)
DEBUG - Using bundled tools from: /Users/user/.huskycat/tools
```

### Container Fallback Warning

When falling back to container (no local tools):

```
WARNING - Falling back to container execution for python-black
```

---

## Testing Recommendations

### Unit Tests

```python
def test_execution_mode_detection():
    """Test mode detection logic"""
    validator = BlackValidator()

    # Test bundled mode
    with mock.patch('sys.frozen', True):
        with mock.patch.object(Path, 'exists', return_value=True):
            assert validator._get_execution_mode() == "bundled"

    # Test container mode
    with mock.patch('os.path.exists', side_effect=lambda p: p == '/.dockerenv'):
        assert validator._get_execution_mode() == "container"

    # Test local mode
    with mock.patch('sys.frozen', False):
        with mock.patch('os.path.exists', return_value=False):
            assert validator._get_execution_mode() == "local"

def test_bundled_tool_execution():
    """Test bundled tool path resolution"""
    validator = BlackValidator()

    with mock.patch.object(validator, '_get_execution_mode', return_value='bundled'):
        tool_path = validator._get_bundled_tool_path()
        assert tool_path is not None
        assert 'python-black' in str(tool_path)

def test_tool_availability():
    """Test tool availability across modes"""
    validator = BlackValidator()

    # Should find bundled tools
    with mock.patch.object(validator, '_get_execution_mode', return_value='bundled'):
        with mock.patch.object(Path, 'exists', return_value=True):
            assert validator.is_available() is True

    # Should find local tools
    with mock.patch.object(validator, '_get_execution_mode', return_value='local'):
        with mock.patch('shutil.which', return_value='/usr/bin/python-black'):
            assert validator.is_available() is True
```

### Integration Tests

```bash
# Test bundled binary execution
./dist/huskycat validate tests/fixtures/sample.py
# Should use ~/.huskycat/tools/python-black

# Test local execution
uv run python -m src.huskycat validate tests/fixtures/sample.py
# Should use system PATH python-black

# Test container execution
podman run -it --rm -v $PWD:/workspace huskycat:local huskycat validate /workspace/tests/fixtures/sample.py
# Should use container python-black
```

### Performance Benchmarks

```bash
# Benchmark bundled vs local vs container
time ./dist/huskycat validate --staged  # Bundled
time huskycat validate --staged         # Local
time podman run ... validate --staged   # Container

# Expected results:
# Bundled:  < 500ms (no container overhead)
# Local:    < 300ms (fastest)
# Container: 1-2s (container startup overhead)
```

---

## Migration Guide

### For Existing Users

**No changes required!** The refactor is backward compatible:

1. **Container users**: Continue working as before (container mode auto-detected)
2. **Local users**: Continue working as before (local mode auto-detected)
3. **New binary users**: Get automatic bundled tool extraction

### For Developers

**Update your code** if you:

1. **Call `_execute_command` directly**: Now mode-aware, no changes needed
2. **Override `is_available`**: Update to match new signature
3. **Build container images**: No changes needed

### For CI/CD Pipelines

**Choose your execution mode**:

```yaml
# Option 1: Use fat binary (no container runtime needed)
- name: Validate
  run: |
    curl -L -o huskycat https://github.com/.../huskycat-linux-amd64
    chmod +x huskycat
    ./huskycat validate --staged

# Option 2: Use container (deterministic environment)
- name: Validate
  run: |
    docker run --rm -v $PWD:/workspace huskycat:local validate /workspace

# Option 3: Use local tools (fastest)
- name: Install tools
  run: |
    pip install black ruff mypy
- name: Validate
  run: huskycat validate --staged
```

---

## Troubleshooting

### Issue: "Bundled tool not found"

**Symptoms**:
```
RuntimeError: Bundled tool python-black not found
```

**Solutions**:
1. Check if tools were extracted: `ls ~/.huskycat/tools/`
2. Re-extract tools: `rm -rf ~/.huskycat/tools/`
3. Verify binary was built with tools: `unzip -l dist/huskycat | grep tools/`

### Issue: "Container fallback used unexpectedly"

**Symptoms**:
```
WARNING - Falling back to container execution for python-black
```

**Solutions**:
1. Install tools locally: `pip install black ruff mypy`
2. Use fat binary: Download from releases
3. Build container: `npm run container:build`

### Issue: "Tool execution is slow"

**Symptoms**:
- Validation takes >2 seconds for small files

**Diagnosis**:
```bash
export HUSKYCAT_LOG_LEVEL=DEBUG
huskycat validate file.py
```

**Solutions**:
- If using container fallback: Install tools locally or use fat binary
- If using bundled: Check tool extraction: `ls ~/.huskycat/tools/`
- If using local: Verify tools in PATH: `which python-black`

---

## Benefits of This Architecture

### 1. Portability

- Fat binary runs anywhere (no dependencies)
- No container runtime required
- Cross-platform support (macOS, Linux, Windows)

### 2. Performance

- No container startup overhead
- Direct tool execution
- Fast validation in git hooks

### 3. Developer Experience

- Local development uses system tools (fast)
- CI/CD uses containers (reproducible)
- Binaries use embedded tools (portable)

### 4. Flexibility

- Mode auto-detection (no manual configuration)
- Graceful fallbacks (container as last resort)
- Compatible with existing workflows

---

## Future Enhancements

### 1. Tool Update Mechanism

```bash
# Update bundled tools to latest versions
huskycat update-tools

# Downloads latest versions to ~/.huskycat/tools/
```

### 2. Configuration-Driven Mode Selection

```yaml
# Force specific execution mode
execution:
  mode: bundled  # bundled, local, container, auto
```

### 3. Parallel Tool Execution

```python
# Execute multiple validators in parallel
results = engine.validate_file_parallel(filepath)
```

### 4. Tool Version Reporting

```bash
# Show which tools are available and their versions
huskycat tools list

# Output:
# python-black v24.4.2 (bundled)
# ruff v0.4.4 (bundled)
# mypy v1.10.0 (local)
```

---

## Summary

The embedded tool execution refactor enables:

- **Standalone fat binaries** with no container dependency
- **Intelligent tool resolution** across 3 execution modes
- **Backward compatibility** with existing workflows
- **Performance improvements** (no container overhead)
- **Graceful fallbacks** (container as last resort)

The architecture prioritizes bundled tools for portability, local tools for speed, and containers for consistency, while maintaining a clean abstraction that's transparent to end users.

**Result**: HuskyCat can now be distributed as a single binary that "just works" anywhere, without requiring Docker, Podman, or even Python installation.
