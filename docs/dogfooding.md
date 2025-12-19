# Dogfooding: HuskyCat Validating Itself

## Philosophy

This repository dogfoods HuskyCat's own validation - we test what users will actually use. By using HuskyCat to validate itself, we ensure:

- Real-world testing of all features
- Early detection of regressions
- Confidence in the user experience
- Alignment between development and production behavior

## Current Configuration

### Hook System
- **Mode**: Tracked hooks (`.githooks/` directory)
- **Git Config**: `core.hooksPath = .githooks`
- **Execution**: UV-based Python module (`uv run python -m huskycat`)
- **Non-Blocking**: Enabled via `git config --local huskycat.nonblocking true`

### Why Tracked Hooks?

For HuskyCat development, we use tracked hooks because:
1. **Development Workflow**: Iterating on hook logic requires no regeneration
2. **Git History**: Changes to hooks are version controlled
3. **UV Integration**: Direct Python module execution for rapid iteration
4. **Team Consistency**: All developers use identical hook logic

For external users, we recommend binary-managed hooks (`.git/hooks/`) for:
- No UV dependency
- Faster execution
- Self-contained installation

## Setup for Contributors

### Prerequisites
- UV package manager installed
- Git 2.9+ (for `core.hooksPath` support)
- Python 3.13+

### Initial Setup

```bash
# 1. Clone repository
git clone https://gitlab.com/jsullivan2/huskycats-bates.git
cd huskycats-bates

# 2. Install dependencies
uv sync --dev

# 3. Verify hooks are configured
git config --local --get core.hooksPath
# Should output: .githooks

# 4. Enable non-blocking mode (optional, recommended)
git config --local huskycat.nonblocking true

# 5. Test with a commit
echo "# test" >> README.md
git add README.md
git commit -m "test: verify hooks work"
```

### Expected Behavior

**With non-blocking mode enabled** (`huskycat.nonblocking = true`):
```
HuskyCat Pre-Commit Hook
⚡ Non-blocking validation mode enabled
Validating 1 Python file(s) with HuskyCat...
Running: uv run python -m huskycat validate --staged
🚀 Launching background validation...
   Validation running in background (PID 12345)
   Check results with: uv run python -m huskycat status

Pre-Commit Passed
All validations passed!
[main abc1234] test: verify hooks work
```

**Without non-blocking mode** (default blocking behavior):
```
HuskyCat Pre-Commit Hook
Validating 1 Python file(s) with HuskyCat...
Running: uv run python -m huskycat validate --staged
🚀 Running HuskyCat validation...
✓ black: 1 file passed
✓ mypy: 1 file passed
✓ flake8: 1 file passed

Pre-Commit Passed
All validations passed!
[main abc1234] test: verify hooks work
```

## Configuration Options

### Enable Non-Blocking Mode

```bash
git config --local huskycat.nonblocking true
```

**Benefits**:
- Commits complete immediately (<100ms)
- Validation runs in background
- Real-time TUI progress display (in separate terminal)
- No blocking on commit

**Tradeoffs**:
- Can't see validation results immediately in commit output
- Must check results separately with `huskycat status`
- Background process may continue after commit

### Disable Non-Blocking Mode

```bash
git config --local huskycat.nonblocking false
# OR
git config --local --unset huskycat.nonblocking
```

**Benefits**:
- See validation results before commit completes
- Commit blocked if validation fails
- Traditional git hook behavior

### Skip Hooks Temporarily

```bash
# Skip all hooks for one commit
SKIP_HOOKS=1 git commit -m "message"

# OR use git's built-in flag
git commit --no-verify -m "message"
```

### Auto-Fix Mode

```bash
# Enable auto-fix for one commit
HUSKYCAT_AUTO_APPROVE=1 git commit -m "message"

# OR
AUTO_FIX=1 git commit -m "message"
```

## Switching Execution Modes

### Current Mode: Tracked Hooks (UV-based)

This is the current setup for HuskyCat development.

**Advantages**:
- Fast iteration
- Version-controlled hooks
- No binary rebuilds needed

**Disadvantages**:
- Requires UV
- Slower than binary execution
- Not dogfooding the binary path

### Alternative: Binary-Managed Hooks

To test the binary execution path (recommended for pre-release testing):

```bash
# 1. Build the binary
npm run build:binary

# 2. Install binary locally
./dist/huskycat install --setup-hooks

# 3. Unset tracked hooks path
git config --local --unset core.hooksPath

# 4. Verify binary hooks installed
ls -la .git/hooks/pre-commit
head -20 .git/hooks/pre-commit  # Check binary path

# 5. Test with commit
git commit -m "test: verify binary hooks"
```

**To switch back to tracked hooks**:
```bash
git config --local core.hooksPath .githooks
```

## Troubleshooting

### Hooks Not Running

**Symptom**: Commits succeed without validation

**Solutions**:
```bash
# Check hooks path configuration
git config --local --get core.hooksPath

# Should be .githooks for tracked mode
# Should be unset for binary mode

# Verify hooks are executable
ls -la .githooks/pre-commit

# Should show -rwxr-xr-x (executable)
```

### Non-Blocking Mode Not Activating

**Symptom**: Validation runs synchronously despite config

**Solutions**:
```bash
# 1. Check git config
git config --local --get huskycat.nonblocking
# Should output: true

# 2. Verify hook reads config
grep -n "huskycat.nonblocking" .githooks/pre-commit
# Should find lines reading the config

# 3. Check environment variable manually
export HUSKYCAT_NONBLOCKING=1
uv run python -m huskycat validate --staged
# Should fork immediately
```

### UV Environment Issues

**Symptom**: `UV environment not ready`

**Solutions**:
```bash
# 1. Sync dependencies
uv sync --dev

# 2. Verify venv exists
ls -la .venv/

# 3. Check UV installation
which uv
uv --version
```

### Background Validation Never Completes

**Symptom**: Forked validation process hangs

**Solutions**:
```bash
# 1. Check for zombie processes
ps aux | grep huskycat

# 2. Kill hanging processes
pkill -f "huskycat validate"

# 3. Disable non-blocking mode temporarily
git config --local huskycat.nonblocking false

# 4. Run validation manually to see errors
uv run python -m huskycat validate --staged --verbose
```

### Tools Not Found

**Symptom**: `black not found` or similar

**Solutions**:
```bash
# 1. Ensure all dev dependencies installed
uv sync --dev

# 2. Verify tools in venv
ls .venv/bin/ | grep -E "black|mypy|flake8|ruff"

# 3. Reinstall dependencies
uv sync --dev --reinstall
```

## Testing

### Run Dogfooding Tests

```bash
# Run all dogfooding tests
uv run pytest tests/test_dogfooding.py -v

# Run specific test
uv run pytest tests/test_dogfooding.py::TestDogfooding::test_nonblocking_mode_activates -v

# Run integration tests
uv run pytest tests/test_dogfooding.py::TestDogfoodingIntegration -v
```

### Manual Validation Test

```bash
# 1. Create test file
echo 'print("test")' > test_validation.py

# 2. Stage it
git add test_validation.py

# 3. Run validation
uv run python -m huskycat validate --staged

# 4. Cleanup
git reset HEAD test_validation.py
rm test_validation.py
```

## Best Practices

### During Development

1. **Use tracked hooks** (`.githooks/`) for rapid iteration
2. **Enable non-blocking mode** for faster commits
3. **Run tests frequently**: `uv run pytest`
4. **Validate manually** before pushing: `uv run python -m huskycat validate --all`

### Before Release

1. **Test binary hooks**: Switch to binary-managed hooks
2. **Disable non-blocking mode** temporarily to verify blocking behavior
3. **Run full test suite**: `uv run pytest`
4. **Test on clean system**: Use container or VM

### For Production

1. **Use binary hooks** (`.git/hooks/`) for end users
2. **Document non-blocking mode** as optional feature
3. **Provide UV fallback** in hook templates
4. **Version check** to warn about outdated hooks

## Architecture

### Hook Execution Flow

```
┌─────────────────────────────────────┐
│ User: git commit -m "message"       │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│ Git: Runs .githooks/pre-commit      │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│ Hook: Read git config               │
│   huskycat.nonblocking = true?      │
└─────────────┬───────────────────────┘
              │
              ├─── YES ──────────────────┐
              │                          │
              │                          ▼
              │              ┌────────────────────────┐
              │              │ Export                 │
              │              │ HUSKYCAT_NONBLOCKING=1 │
              │              └───────────┬────────────┘
              │                          │
              │                          ▼
              │              ┌────────────────────────┐
              │              │ Fork validation &      │
              │              │ return immediately     │
              │              └────────────────────────┘
              │
              └─── NO ───────────────────┐
                                         │
                                         ▼
                             ┌────────────────────────┐
                             │ Run validation         │
                             │ synchronously (blocking)│
                             └───────────┬────────────┘
                                         │
                                         ▼
                             ┌────────────────────────┐
                             │ Exit with status       │
                             │ (0=pass, 1=fail)       │
                             └────────────────────────┘
```

### Non-Blocking Adapter Flow

```python
# __main__.py
mode = detect_mode()
use_nonblocking = os.environ.get('HUSKYCAT_NONBLOCKING') == '1'
adapter = get_adapter(mode, use_nonblocking=use_nonblocking)

# mode_detector.py
if mode == ProductMode.GIT_HOOKS and use_nonblocking:
    return NonBlockingGitHooksAdapter()

# git_hooks_nonblocking.py
def execute(self, command, files):
    if not should_proceed_with_commit():
        return fail_result

    pid = self.process_manager.fork_validation(files)
    if pid > 0:
        # Parent returns immediately
        return success_result
```

## References

- [Sprint 11 Plan](SPRINT11_DOGFOODING_BINARY_BOOTSTRAP.md)
- [Architecture: Product Modes](architecture/product-modes.md)
- [Git Hooks Adapter](../src/huskycat/core/adapters/git_hooks.py)
- [Non-Blocking Adapter](../src/huskycat/core/adapters/git_hooks_nonblocking.py)
- [Hook Generator](../src/huskycat/core/hook_generator.py)
