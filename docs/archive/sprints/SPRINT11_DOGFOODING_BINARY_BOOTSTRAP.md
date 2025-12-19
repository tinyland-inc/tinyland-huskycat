# Sprint 11: Git Hooks Dogfooding & Fat Binary Bootstrap

## Executive Summary

This sprint addresses two critical gaps identified in Sprint 10:
1. **Dogfooding**: This repository must properly use its own validation via fat binary
2. **Binary Bootstrap**: Comprehensive testing and validation of installation workflows

## Critical Findings from Exploration

### Dogfooding Issues
- **Binary path hardcoded to wrong repo**: `.git/hooks/pre-commit` references `/Users/jsullivan2/crush-dots/.venv/bin/huskycat`
- **Non-blocking hooks not enabled**: Feature flag implemented but never activated (environment variable not wired)
- **Dual hook systems**: Both `.githooks/` (tracked, UV-based) and `.git/hooks/` (generated, binary-based) exist, creating confusion
- **Not testing binary execution**: Current hooks use UV mode, not fat binary path

### Fat Binary Issues
- Binary builds successfully (~21MB macOS ARM64, ~150-200MB with embedded tools)
- Tool extraction logic implemented but not verified end-to-end
- No automated tests for bootstrap installation flow
- Documentation references unverified paths

## PHASE 1: Fix Dogfooding & Non-Blocking Hooks (3-4 Days)

### Goal
Ensure this repository properly dogfoods HuskyCat validation using non-blocking hooks with fat binary execution.

### Current State
- Git config: `core.hooksPath = .githooks` (using tracked UV-based hooks)
- Binary hooks in `.git/hooks/` are ignored
- Non-blocking adapter fully implemented (`src/huskycat/core/adapters/git_hooks_nonblocking.py:362`)
- Feature flag parameter exists but never set to True

### Deliverable 1.1: Wire Non-Blocking Feature Flag

**File**: `src/huskycat/__main__.py:228-229`

**Problem**: Never checks `HUSKYCAT_NONBLOCKING` environment variable

```python
# Current (BROKEN)
mode = detect_mode(override=mode_override)
adapter = get_adapter(mode)  # use_nonblocking defaults to False!
```

**Fix**:
```python
# After mode detection
use_nonblocking = os.environ.get('HUSKYCAT_NONBLOCKING', '0') == '1'
adapter = get_adapter(mode, use_nonblocking=use_nonblocking)
```

**Verification**:
```bash
export HUSKYCAT_NONBLOCKING=1
uv run python -m huskycat validate --staged
# Should fork and return in <100ms
```

### Deliverable 1.2: Simplify to Single Hook System

**Decision Required**: Choose ONE of:

**Option A: Pure Binary Mode** (Recommended)
- Remove `.githooks/` directory
- Unset `git config core.hooksPath`
- Use binary-generated hooks in `.git/hooks/`
- Test binary execution path (dogfood the fat binary)

**Option B: Pure Tracked Mode**
- Keep `.githooks/` directory
- Update tracked hooks to support non-blocking mode
- Continue using UV execution
- Better for HuskyCat development iteration

**Recommendation**: Option A - Test what users will actually use

**Implementation Steps** (Option A):
```bash
# 1. Build fresh binary
npm run build:binary

# 2. Install binary locally
./dist/huskycat install --setup-hooks

# 3. Verify binary hooks installed
cat .git/hooks/pre-commit | head -20

# 4. Enable non-blocking mode for this repo
git config --local huskycat.nonblocking true

# 5. Remove tracked hooks to avoid confusion
git rm -r .githooks/
git commit -m "refactor: switch to binary-managed hooks for dogfooding"
```

### Deliverable 1.3: Update Hook Templates for Non-Blocking

**File**: `src/huskycat/templates/hooks/pre-commit.template:50`

**Add configuration reading**:
```bash
# Check for non-blocking mode configuration
NONBLOCKING_MODE=$(git config --get huskycat.nonblocking || echo "false")
if [[ "$NONBLOCKING_MODE" == "true" ]]; then
    export HUSKYCAT_NONBLOCKING=1
    echo "⚡ Non-blocking validation mode enabled"
fi
```

**Update validation execution** (lines 65-69):
```bash
if [[ "$HUSKYCAT_NONBLOCKING" == "1" ]]; then
    # Non-blocking: fork and return immediately
    $EXEC_CMD validate $VALIDATE_ARGS &
    VALIDATE_PID=$!
    echo "🚀 Validation running in background (PID $VALIDATE_PID)"
    exit 0
else
    # Blocking: wait for validation
    $EXEC_CMD validate $VALIDATE_ARGS
    exit $?
fi
```

### Deliverable 1.4: Fix Binary Path Auto-Detection

**File**: `src/huskycat/core/hook_generator.py:45-78`

**Current Issue**: Generated hooks hardcode binary path that may be wrong

**Fix Priority Ordering**:
```python
def _detect_binary_path(self) -> Optional[Path]:
    """Detect HuskyCat binary location with priority ordering."""

    # Priority 1: Running from binary right now
    if getattr(sys, "frozen", False):
        return Path(sys.executable)

    # Priority 2: Installed in user's bin
    user_bin = Path.home() / ".local" / "bin" / "huskycat"
    if user_bin.exists():
        return user_bin

    # Priority 3: System PATH
    try:
        result = subprocess.run(
            ["which", "huskycat"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except Exception:
        pass

    # Priority 4: Common system locations
    for location in [Path("/usr/local/bin/huskycat"), Path("/usr/bin/huskycat")]:
        if location.exists():
            return location

    # No binary found - hooks will use UV fallback
    return None
```

### Deliverable 1.5: Create Dogfooding Validation Suite

**New File**: `tests/test_dogfooding.py`

**Test Scenarios**:
```python
def test_hooks_use_binary_not_uv():
    """Verify hooks execute via binary, not UV fallback."""
    hook = Path(".git/hooks/pre-commit")
    content = hook.read_text()
    assert "~/.local/bin/huskycat" in content or "/usr/local/bin/huskycat" in content
    assert 'uv run python' not in content.split('\n')[0:20]  # Not in primary path

def test_nonblocking_mode_activates():
    """Verify HUSKYCAT_NONBLOCKING=1 activates non-blocking adapter."""
    env = os.environ.copy()
    env["HUSKYCAT_NONBLOCKING"] = "1"

    result = subprocess.run(
        ["python", "-c", "from src.huskycat.__main__ import main; main()"],
        env=env,
        capture_output=True,
    )
    # Should use NonBlockingGitHooksAdapter

def test_hook_binary_path_correct():
    """Verify generated hooks reference correct binary path."""
    subprocess.run(["./dist/huskycat", "setup-hooks", "--force"])
    hook = Path(".git/hooks/pre-commit")
    content = hook.read_text()

    # Should reference the actual binary location
    detected_binary = subprocess.run(
        ["which", "huskycat"], capture_output=True, text=True
    ).stdout.strip()

    if detected_binary:
        assert detected_binary in content

def test_fork_returns_under_100ms():
    """Verify non-blocking parent returns in <100ms."""
    import time

    env = os.environ.copy()
    env["HUSKYCAT_NONBLOCKING"] = "1"

    start = time.time()
    subprocess.run(
        ["./dist/huskycat", "validate", "--staged"],
        env=env,
        timeout=1,
    )
    duration = (time.time() - start) * 1000

    assert duration < 100, f"Took {duration}ms, expected <100ms"

def test_background_validation_completes():
    """Verify child process completes validation and caches results."""
    env = os.environ.copy()
    env["HUSKYCAT_NONBLOCKING"] = "1"

    # Start validation
    subprocess.run(["./dist/huskycat", "validate", "--staged"], env=env)

    # Wait for background process
    time.sleep(5)

    # Check for cached results
    cache_dir = Path.home() / ".huskycat" / "runs"
    assert cache_dir.exists()
    assert len(list(cache_dir.glob("*.json"))) > 0

def test_tui_displays_in_background():
    """Verify TUI progress shown in child process."""
    # This requires testing with a TTY
    # Mock with pty module for real TTY testing
    pass
```

### Deliverable 1.6: Documentation Updates

**New File**: `docs/dogfooding.md`

**Content**:
```markdown
# Dogfooding: HuskyCat Validating Itself

## Philosophy

This repository dogfoods HuskyCat's own validation using the fat binary.
We test what users will actually use, not a separate development path.

## Current Configuration

- **Hook Mode**: Binary-managed (`.git/hooks/`)
- **Execution**: Fat binary at `~/.local/bin/huskycat`
- **Non-Blocking**: Enabled via `git config --local huskycat.nonblocking true`
- **Tool Extraction**: Tools extracted to `~/.huskycat/tools/` on first run

## Setup for Contributors

1. Build the binary:
   ```bash
   npm run build:binary
   ```

2. Install locally with hooks:
   ```bash
   ./dist/huskycat install --setup-hooks
   ```

3. Enable non-blocking mode (optional):
   ```bash
   git config --local huskycat.nonblocking true
   ```

4. Test with a commit:
   ```bash
   echo "# test" >> README.md
   git add README.md
   git commit -m "test: verify hooks work"
   ```

Expected output with non-blocking:
```
⚡ Non-blocking validation mode enabled
🚀 Validation running in background (PID 12345)
[main abc1234] test: verify hooks work
```

Expected output without non-blocking:
```
🚀 Running HuskyCat validation...
✓ black: 23 files passed
✓ mypy: 23 files passed
✓ flake8: 23 files passed
[main abc1234] test: verify hooks work
```

## Switching Modes

### Use Binary Execution (Recommended)
```bash
./dist/huskycat setup-hooks --force
```

### Use UV Development Mode
```bash
# Edit .git/hooks/pre-commit
# Change HUSKYCAT_BIN to: "uv run python -m huskycat"
```

### Enable Non-Blocking
```bash
git config --local huskycat.nonblocking true
```

### Disable Non-Blocking
```bash
git config --local huskycat.nonblocking false
```

## Troubleshooting

### Hooks using wrong binary path
```bash
# Check current path
head -20 .git/hooks/pre-commit | grep HUSKYCAT_BIN

# Regenerate
./dist/huskycat setup-hooks --force
```

### Non-blocking mode not activating
```bash
# Check git config
git config --get huskycat.nonblocking

# Set explicitly
git config --local huskycat.nonblocking true

# Verify in hook
grep NONBLOCKING_MODE .git/hooks/pre-commit
```

### Tools not found
```bash
# Check extraction
ls -la ~/.huskycat/tools/

# Force re-extraction
rm -rf ~/.huskycat/tools
./dist/huskycat validate --help
```
```

**File**: `README.md` (update installation section)

Add after line 50:
```markdown
## Development Setup (HuskyCat Contributors)

This repository dogfoods HuskyCat's own validation using the fat binary:

```bash
# 1. Build the binary
npm run build:binary

# 2. Install locally with hooks
./dist/huskycat install --setup-hooks

# 3. Enable non-blocking mode (optional, recommended)
git config --local huskycat.nonblocking true

# 4. Make a commit to test hooks
git add .
git commit -m "test: verify hooks work"
# Should see: ⚡ Non-blocking validation mode enabled
# Should see: 🚀 Validation running in background (PID 12345)
# Commit proceeds immediately, validation runs in background
```

See [docs/dogfooding.md](docs/dogfooding.md) for detailed information.
```

### Phase 1 Success Criteria

- [ ] `HUSKYCAT_NONBLOCKING=1` activates `NonBlockingGitHooksAdapter`
- [ ] Git hooks in this repo execute via fat binary (not UV)
- [ ] Hook binary path auto-detected correctly
- [ ] Pre-commit returns in <100ms with non-blocking enabled
- [ ] Background validation completes and displays TUI
- [ ] All dogfooding tests pass
- [ ] Documentation accurate and verified

---

## PHASE 2: Fat Binary Bootstrap Testing & Validation (3-4 Days)

### Goal
Comprehensively test and validate fat binary installation, tool extraction, and hook bootstrap workflows.

### Current State
- Binary builds successfully (~21MB macOS ARM64)
- Tool extraction logic implemented in `src/huskycat/core/tool_extractor.py`
- Installation command exists in `src/huskycat/commands/install.py`
- No automated tests for binary bootstrap end-to-end

### Deliverable 2.1: Improve Binary Entry Point

**File**: `huskycat_main.py`

**Current**: Works but could be more robust

**Improved Version**:
```python
#!/usr/bin/env python3
"""HuskyCat - Universal Code Validation Platform
Main entry point for PyInstaller binary
"""

import sys
import os
from pathlib import Path

# PyInstaller frozen mode detection
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    # Running from PyInstaller bundle
    bundle_dir = Path(sys._MEIPASS)
    src_dir = bundle_dir / "src"

    # Verify bundle structure
    if not src_dir.exists():
        print(f"Error: Bundle structure invalid - src not found in {bundle_dir}", file=sys.stderr)
        sys.exit(1)

    sys.path.insert(0, str(src_dir))

    # Set environment marker for frozen mode
    os.environ["HUSKYCAT_FROZEN"] = "1"
else:
    # Running from source
    repo_dir = Path(__file__).parent
    src_dir = repo_dir / "src"
    sys.path.insert(0, str(src_dir))

# Import must be after path setup
from src.huskycat.__main__ import main

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
```

### Deliverable 2.2: Create Binary Verification Script

**New File**: `scripts/verify_binary.sh`

```bash
#!/bin/bash
set -e

BINARY="$1"
echo "Testing HuskyCat binary: $BINARY"

# Test 1: Basic execution
echo "Test 1: --help"
$BINARY --help >/dev/null || exit 1

# Test 2: Version command
echo "Test 2: --version"
VERSION=$($BINARY --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
echo "  Version: $VERSION"

# Test 3: Frozen mode detection
echo "Test 3: Check frozen mode"
export HUSKYCAT_FROZEN
if [[ "$HUSKYCAT_FROZEN" != "1" ]]; then
    echo "  Warning: HUSKYCAT_FROZEN not set"
fi

# Test 4: Tool extraction
echo "Test 4: Tool extraction"
rm -rf ~/.huskycat/tools  # Clean slate
$BINARY validate --help >/dev/null  # Trigger extraction
[[ -f ~/.huskycat/tools/shellcheck ]] || { echo "  ERROR: shellcheck not extracted"; exit 1; }
[[ -f ~/.huskycat/tools/hadolint ]] || { echo "  ERROR: hadolint not extracted"; exit 1; }
[[ -f ~/.huskycat/tools/taplo ]] || { echo "  ERROR: taplo not extracted"; exit 1; }
echo "  ✓ All tools extracted"

# Test 5: Tool execution
echo "Test 5: Tool execution"
~/.huskycat/tools/shellcheck --version >/dev/null || { echo "  ERROR: shellcheck not executable"; exit 1; }
~/.huskycat/tools/hadolint --version >/dev/null || { echo "  ERROR: hadolint not executable"; exit 1; }
~/.huskycat/tools/taplo --version >/dev/null || { echo "  ERROR: taplo not executable"; exit 1; }
echo "  ✓ All tools executable"

# Test 6: Validation works
echo "Test 6: Run validation"
echo '#!/bin/bash\necho "test"' > /tmp/test.sh
$BINARY validate /tmp/test.sh >/dev/null || { echo "  ERROR: Validation failed"; exit 1; }
rm /tmp/test.sh
echo "  ✓ Validation works"

echo ""
echo "✅ All binary tests passed!"
```

**Add to package.json**:
```json
{
  "scripts": {
    "verify:binary": "bash scripts/verify_binary.sh dist/huskycat"
  }
}
```

### Deliverable 2.3: Create Bootstrap Installation Tests

**New File**: `tests/test_binary_bootstrap.py`

See full test suite in sprint plan above (8 comprehensive tests covering installation, extraction, hooks, versioning).

**Key Test Coverage**:
- Binary installation creates executable in bin dir
- Tool extraction happens during install
- Generated hooks reference correct binary path
- Version tracking prevents redundant extraction
- Binary validates without prior installation
- Completions generated during install

### Deliverable 2.4: Add Tool Extraction Logging

**File**: `src/huskycat/core/tool_extractor.py:104-139`

**Add progress feedback**:
```python
def extract_tools(self) -> bool:
    """Extract embedded tools to cache directory with progress feedback."""
    if not self.is_bundled or not self.bundle_tools_dir:
        return False

    try:
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Count tools
        tools = [f for f in self.bundle_tools_dir.glob("*") if f.is_file()]

        print(f"Extracting {len(tools)} validation tools to {self.cache_dir}...")

        for tool_file in tools:
            if tool_file.is_file():
                dest = self.cache_dir / tool_file.name

                # Show progress
                if tool_file.name != "versions.txt":
                    size_mb = tool_file.stat().st_size / (1024 * 1024)
                    print(f"  • {tool_file.name} ({size_mb:.1f} MB)")

                shutil.copy2(tool_file, dest)

                if tool_file.name != "versions.txt":
                    dest.chmod(0o755)

        # Write version marker
        bundle_version = self.get_bundle_version()
        with open(self.version_file, "w") as f:
            f.write(bundle_version or "unknown")

        print(f"✓ Tools extracted successfully")
        return True

    except Exception as e:
        print(f"✗ Failed to extract tools: {e}", file=sys.stderr)
        return False
```

### Deliverable 2.5: CI Integration for Binary Testing

**New File**: `.gitlab/ci/binary-tests.yml`

```yaml
binary:test:linux-amd64:
  stage: test
  needs:
    - build:binary:linux-amd64
  script:
    - chmod +x dist/linux-amd64/huskycat
    - bash scripts/verify_binary.sh dist/linux-amd64/huskycat
    - pytest tests/test_binary_bootstrap.py --binary=dist/linux-amd64/huskycat -v
  artifacts:
    when: always
    reports:
      junit: test-reports/binary-bootstrap.xml

binary:test:darwin-arm64:
  stage: test
  tags:
    - macos
    - arm64
  needs:
    - build:binary:darwin-arm64
  script:
    - chmod +x dist/darwin-arm64/huskycat
    - bash scripts/verify_binary.sh dist/darwin-arm64/huskycat
    - pytest tests/test_binary_bootstrap.py --binary=dist/darwin-arm64/huskycat -v
  artifacts:
    when: always
    reports:
      junit: test-reports/binary-bootstrap-macos.xml
```

**Update**: `.gitlab-ci.yml` to include:
```yaml
include:
  - local: '.gitlab/ci/binary-tests.yml'
```

### Deliverable 2.6: Update Documentation with Verified Paths

**File**: `docs/installation.md` (rewrite)

```markdown
# Installation Guide

## Quick Install (Recommended)

Download the latest binary for your platform:

### Linux (amd64)
```bash
curl -L https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/linux-amd64/huskycat?job=build:binary:linux-amd64 -o huskycat
chmod +x huskycat
./huskycat install
```

### Linux (arm64)
```bash
curl -L https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/linux-arm64/huskycat?job=build:binary:linux-arm64 -o huskycat
chmod +x huskycat
./huskycat install
```

### macOS (ARM64)
```bash
curl -L https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/darwin-arm64/huskycat?job=build:binary:darwin-arm64 -o huskycat
chmod +x huskycat
./huskycat install
```

### macOS (Intel)
```bash
curl -L https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/darwin-amd64/huskycat?job=build:binary:darwin-amd64 -o huskycat
chmod +x huskycat
./huskycat install
```

## Verify Installation

```bash
huskycat --version
huskycat --help
```

## What Happens During Installation

1. **Binary copied to** `~/.local/bin/huskycat`
2. **Validation tools extracted to** `~/.huskycat/tools/`:
   - shellcheck (v0.10.0, ~3.4 MB)
   - hadolint (v2.12.0, ~12 MB)
   - taplo (v0.9.3, ~18 MB)
3. **Shell completions created** in `~/.huskycat/completions/`:
   - Bash: `huskycat.bash`
   - Zsh: `_huskycat`
   - Fish: `huskycat.fish`
4. **Git hooks installed** (if in a git repository)

## Enable Git Hooks

```bash
cd your-repo
huskycat setup-hooks

# Optional: Enable non-blocking mode for faster commits
git config --local huskycat.nonblocking true
```

## Verify Hooks Work

```bash
# Make a test commit
echo "# test" >> README.md
git add README.md
git commit -m "test: verify hooks"
```

**With non-blocking mode**:
```
⚡ Non-blocking validation mode enabled
🚀 Validation running in background (PID 12345)
[main abc1234] test: verify hooks
```

**Without non-blocking mode**:
```
🚀 Running HuskyCat validation...
✓ black: 1 file passed
✓ mypy: 1 file passed
[main abc1234] test: verify hooks
```

## Troubleshooting

### Tools not found
```bash
# Check extraction
ls -la ~/.huskycat/tools/

# Force re-extraction
rm -rf ~/.huskycat/tools
huskycat validate --help  # Triggers extraction
```

### Binary not in PATH
```bash
# Check PATH
echo $PATH | grep .local/bin

# Add to shell profile
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify
which huskycat
```

### Hooks not running
```bash
# Verify hooks installed
ls -la .git/hooks/pre-commit

# Check binary path in hook
head -20 .git/hooks/pre-commit | grep HUSKYCAT_BIN

# Regenerate hooks
huskycat setup-hooks --force
```

### Permission denied
```bash
# Make binary executable
chmod +x ~/.local/bin/huskycat

# Make tools executable
chmod +x ~/.huskycat/tools/*
```
```

### Deliverable 2.7: Create Binary Distribution Guide

**New File**: `docs/binary-downloads.md`

```markdown
# Binary Downloads

## Latest Release

Download pre-built binaries for all platforms from GitLab CI artifacts.

## Supported Platforms

| Platform | Architecture | Size | Download |
|----------|--------------|------|----------|
| Linux | x86_64 (amd64) | ~150 MB | [Download](https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/linux-amd64/huskycat?job=build:binary:linux-amd64) |
| Linux | ARM64 | ~150 MB | [Download](https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/linux-arm64/huskycat?job=build:binary:linux-arm64) |
| macOS | ARM64 (M1/M2) | ~21 MB | [Download](https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/darwin-arm64/huskycat?job=build:binary:darwin-arm64) |
| macOS | x86_64 (Intel) | ~150 MB | [Download](https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/darwin-amd64/huskycat?job=build:binary:darwin-amd64) |

## Checksums

Verify downloads with SHA256 checksums:

```bash
# Linux amd64
sha256sum huskycat
# Expected: [checksum from CI artifacts]

# macOS ARM64
shasum -a 256 huskycat
# Expected: [checksum from CI artifacts]
```

## Installation

See [Installation Guide](installation.md) for detailed instructions.

Quick install:
```bash
# 1. Download binary for your platform (see table above)

# 2. Make executable
chmod +x huskycat

# 3. Install
./huskycat install

# 4. Verify
huskycat --version
```

## What's Inside

Each binary includes:
- **HuskyCat Core** (~5 MB): Validation engine, commands, formatters
- **Python Runtime** (~40 MB): Embedded Python 3.13
- **Embedded Tools** (~100-150 MB):
  - shellcheck v0.10.0
  - hadolint v2.12.0
  - taplo v0.9.3
- **Python Packages** (~30-50 MB): Dependencies (argparse, pathlib, etc.)

Total: 150-200 MB per platform (except macOS ARM64 which is ~21 MB with tools extracted separately)

## Verification

After installation, verify the binary works:

```bash
# Check version
huskycat --version

# Verify tools extracted
ls -la ~/.huskycat/tools/
# Should show: shellcheck, hadolint, taplo

# Test validation
echo '#!/bin/bash\necho "test"' > test.sh
huskycat validate test.sh
rm test.sh
```

## Troubleshooting

### macOS: "cannot be opened because the developer cannot be verified"

```bash
# Allow unsigned binary
xattr -d com.apple.quarantine huskycat
```

### Linux: Permission denied

```bash
# Make executable
chmod +x huskycat
```

### Tools not found after installation

```bash
# Check extraction
ls ~/.huskycat/tools/

# Force re-extraction
rm -rf ~/.huskycat/tools
huskycat validate --help
```
```

### Phase 2 Success Criteria

- [ ] Binary builds without errors on all platforms
- [ ] `scripts/verify_binary.sh` passes all tests
- [ ] Bootstrap tests pass (install, extract, setup-hooks)
- [ ] CI runs binary tests on Linux and macOS
- [ ] Tools extract to `~/.huskycat/tools/` correctly
- [ ] Extracted tools are executable and functional
- [ ] Version tracking prevents redundant extraction
- [ ] Hook templates reference correct binary path
- [ ] Documentation reflects actual binary behavior (verified)
- [ ] Installation guide tested step-by-step

---

## Sprint Timeline

### Week 1: Phase 1 (Dogfooding)
- **Day 1**: Wire non-blocking feature flag, update hook templates
- **Day 2**: Fix binary path detection, implement single hook system
- **Day 3**: Create dogfooding test suite, verify all tests pass
- **Day 4**: Documentation updates, end-to-end validation

### Week 2: Phase 2 (Binary Bootstrap)
- **Day 1**: Improve entry point, create verification script
- **Day 2**: Create bootstrap test suite, add tool extraction logging
- **Day 3**: CI integration for binary testing
- **Day 4**: Documentation updates, installation guide verification

**Total Duration**: 7-8 days with comprehensive testing and documentation

---

## Risk Assessment

### High Risk
- **Binary codesign errors on macOS**: May require developer certificate or ad-hoc signing workaround
- **Tool extraction on restricted filesystems**: Some environments may block `~/.huskycat/tools/` writes

### Medium Risk
- **Hook template changes breaking existing installations**: Require careful testing and migration guide
- **Binary size**: 150-200 MB may be too large for some use cases (container images, CI caches)

### Low Risk
- **UV fallback path**: Well-tested, provides safety net if binary path detection fails
- **Version tracking**: Hash-based versioning prevents extraction issues

---

## Success Metrics

### Phase 1
- [ ] Non-blocking hooks return in <100ms (target: 5-10ms)
- [ ] Background validation completes successfully
- [ ] Binary path auto-detected 100% of time when binary installed
- [ ] All dogfooding tests pass (>95% coverage of dogfooding scenarios)

### Phase 2
- [ ] Binary bootstrap tests pass on all platforms (Linux amd64/arm64, macOS amd64/arm64)
- [ ] Tool extraction succeeds 100% of time
- [ ] Installation guide verified step-by-step on clean systems
- [ ] CI binary tests pass consistently (no flaky tests)

---

## Next Steps After Sprint 11

1. **Sprint 12: Performance Optimization**
   - Profile binary startup time
   - Optimize tool extraction (lazy loading?)
   - Reduce binary size if possible

2. **Sprint 13: Auto-Update Mechanism**
   - Self-update command: `huskycat update`
   - Version checking with remote registry
   - Automatic hook regeneration after updates

3. **Sprint 14: Distribution Channels**
   - Homebrew formula
   - APT/YUM packages
   - Docker image with pre-installed binary
