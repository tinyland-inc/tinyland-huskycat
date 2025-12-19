# Sprint 10: Architectural Refactor - Non-Blocking Git Hooks & Standalone Binaries

**Status**: Proposal
**Priority**: High
**Complexity**: Very High
**Sprint Duration**: 3-4 weeks
**Dependencies**: Sprint 9B (E2E tests + ARM64 optimization)

## Executive Summary

Transform HuskyCat from a container-dependent, blocking validation platform into a truly standalone, non-blocking git hooks system with full toolchain embedded in binaries.

**Current Pain Points**:
1. Git hooks block user operations for 3-5 seconds
2. "Fast mode" compromises on validation completeness
3. Binaries require container runtime (not truly standalone)
4. Container builds separate from binary builds
5. Poor developer experience during commits

**Proposed Solution**:
1. Non-blocking git hooks with TUI feedback (parallel execution)
2. Remove "fast mode" - full validation always
3. Embed all validation tools in PyInstaller binaries
4. Single build artifact: fat binary with embedded toolchain
5. Continue git operations immediately, validation runs in background

## Problem Analysis

### Current Architecture Issues

#### Issue 1: Blocking Git Hooks (`git_hooks.py:40-44`)
```python
# Current: Blocks git operations
return AdapterConfig(
    fail_fast=True,      # Stops on first error
    tools="fast",        # Only 4 tools (black, ruff, mypy)
    progress=False,      # No feedback during execution
)
```

**Impact**:
- User waits 3-5s for validation to complete
- Cannot proceed with next git operation
- False sense of "fast" (actually just incomplete)
- Poor developer experience

#### Issue 2: Container Dependency (`unified_validation.py:85-170`)
```python
def is_available(self) -> bool:
    if self._is_running_in_container():
        return tool_exists_locally()
    else:
        return container_runtime_exists()  # ❌ Requires runtime
```

**Impact**:
- Binary is NOT standalone (needs podman/docker)
- 50-100MB binary that can't run without external dependencies
- Installation friction: "install binary + container runtime"
- Defeats purpose of single-file distribution

#### Issue 3: Fast Mode Compromise (`git_hooks.py:43`)
```python
tools="fast",  # Only black, ruff, mypy
```

**Tools Excluded in Fast Mode**:
- flake8 (linting)
- isort (import sorting)
- bandit (security)
- yamllint (config validation)
- shellcheck (shell scripts)
- hadolint (Dockerfiles)
- ansible-lint (playbooks)
- gitlab-ci validator

**Impact**: False confidence - passing git hooks doesn't mean CI will pass

#### Issue 4: Separate Build Artifacts
```yaml
# .gitlab-ci.yml: Two independent build paths
container:build:amd64:  # Builds container with tools
binary:build:linux:     # Builds binary without tools
```

**Impact**:
- Duplication of effort
- Binary can't function without container
- 2x CI time for builds
- Complex dependency chain

## Proposed Architecture

### Architecture Vision

```
┌─────────────────────────────────────────────────────────────┐
│                    HuskyCat Fat Binary                      │
│  (Single 150-200MB executable - NO external dependencies)  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Python     │  │   Node.js    │  │   Native     │    │
│  │   Tools      │  │   Tools      │  │   Tools      │    │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤    │
│  │ • black      │  │ • eslint     │  │ • shellcheck │    │
│  │ • ruff       │  │ • prettier   │  │ • hadolint   │    │
│  │ • mypy       │  │ • typescript │  │ • taplo      │    │
│  │ • flake8     │  │              │  │              │    │
│  │ • isort      │  │              │  │              │    │
│  │ • bandit     │  │              │  │              │    │
│  │ • yamllint   │  │              │  │              │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │         Non-Blocking Git Hooks Engine              │  │
│  │                                                     │  │
│  │  1. Fork validation process immediately           │  │
│  │  2. Return control to git operation               │  │
│  │  3. Show TUI with real-time progress             │  │
│  │  4. Write results to .huskycat/last-run.json     │  │
│  │  5. Next git op checks previous results          │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Component 1: Non-Blocking Git Hooks with TUI

**Implementation Strategy**: Fork + TUI feedback

```python
# src/huskycat/core/adapters/git_hooks_nonblocking.py

import os
import sys
import multiprocessing
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.spinner import Spinner

class NonBlockingGitHooksAdapter(ModeAdapter):
    """
    Non-blocking git hooks adapter.

    Flow:
    1. Immediately fork validation process
    2. Return 0 to git (allow operation to proceed)
    3. Show TUI in background terminal
    4. Write results to .huskycat/last-run.json
    5. Next git operation checks previous results
    """

    def execute(self, files):
        # Check if previous run failed
        if self._check_previous_run_failed():
            return self._handle_previous_failure()

        # Fork validation process
        pid = os.fork()

        if pid > 0:
            # Parent: Return immediately to git
            self._write_pid_file(pid)
            return CommandResult(success=True, message="Validation running in background")
        else:
            # Child: Run validation with TUI
            self._run_validation_with_tui(files)
            sys.exit(0)

    def _run_validation_with_tui(self, files):
        """Run validation showing real-time TUI progress"""
        console = Console()

        with Live(self._create_progress_table(), console=console) as live:
            results = []

            # Run ALL tools (no fast mode compromise)
            for tool in self.get_all_tools():
                live.update(self._update_progress(tool, "running"))

                result = self._run_tool_async(tool, files)
                results.append(result)

                status = "✓" if result.success else "✗"
                live.update(self._update_progress(tool, status))

            # Write results for next git operation
            self._write_results_file(results)

            # Show summary
            console.print(self._format_summary(results))

    def _check_previous_run_failed(self) -> bool:
        """Check if previous validation failed"""
        results_file = Path(".huskycat/last-run.json")
        if not results_file.exists():
            return False

        with open(results_file) as f:
            data = json.load(f)
            return data.get("has_errors", False)

    def _handle_previous_failure(self):
        """Handle case where previous run failed"""
        console = Console()
        console.print("[red]Previous validation failed![/red]")
        console.print("Fix issues or use: git commit --no-verify")

        # Show previous results
        with open(".huskycat/last-run.json") as f:
            results = json.load(f)
            console.print(self._format_results(results))

        return CommandResult(success=False, message="Previous validation failed")
```

**TUI Features**:
```python
# Real-time progress display
┌────────────────────────────────────────────────────┐
│ HuskyCat Validation (Background)                  │
├────────────────────────────────────────────────────┤
│ ✓ black           (123ms)  - Formatted            │
│ ✓ ruff            (456ms)  - No issues            │
│ ⟳ mypy            (...)    - Running...           │
│ ⋯ flake8          (...)    - Pending              │
│ ⋯ isort           (...)    - Pending              │
│ ⋯ bandit          (...)    - Pending              │
│ ⋯ yamllint        (...)    - Pending              │
│ ⋯ shellcheck      (...)    - Pending              │
│ ⋯ hadolint        (...)    - Pending              │
│ ⋯ gitlab-ci       (...)    - Pending              │
└────────────────────────────────────────────────────┘
Press Ctrl+C to background, validation continues...
```

**Advantages**:
- ✅ User continues immediately
- ✅ Full validation (no "fast mode" compromise)
- ✅ Real-time feedback via TUI
- ✅ Results cached for next operation
- ✅ Can background the TUI and validation continues

### Component 2: Fat Binary with Embedded Toolchain

**Strategy**: Bundle ALL validation tools in PyInstaller binary

```python
# build_fat_binary.py

def build_fat_binary():
    """Build standalone binary with embedded toolchain"""

    # 1. Collect Python tools (via PyInstaller data collection)
    python_tools = [
        ("black", "bin/black"),
        ("ruff", "bin/ruff"),
        ("mypy", "bin/mypy"),
        ("flake8", "bin/flake8"),
        ("isort", "bin/isort"),
        ("bandit", "bin/bandit"),
        ("yamllint", "bin/yamllint"),
    ]

    # 2. Download and embed native binaries
    native_tools = download_native_tools([
        ("shellcheck", "https://github.com/koalaman/shellcheck/releases/"),
        ("hadolint", "https://github.com/hadolint/hadolint/releases/"),
        ("taplo", "https://github.com/tamasfe/taplo/releases/"),
    ])

    # 3. Embed Node.js + npm packages
    nodejs_bundle = create_nodejs_bundle([
        "eslint",
        "prettier",
        "@typescript-eslint/parser",
    ])

    # 4. Build fat binary
    pyinstaller_args = [
        "--onefile",
        "--name=huskycat",
        f"--add-binary={native_tools}:tools/bin",
        f"--add-data={nodejs_bundle}:tools/node",
        f"--add-data={python_tools}:tools/python",
        "--hidden-import=huskycat",
        "huskycat_main.py",
    ]

    PyInstaller.__main__.run(pyinstaller_args)
```

**Tool Execution** (from embedded binaries):
```python
# src/huskycat/unified_validation.py (refactored)

class Validator(ABC):
    def _execute_tool(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """Execute tool from embedded binary"""

        # Get tool path from embedded resources
        tool_path = self._get_embedded_tool_path(cmd[0])

        # Execute directly (no container needed)
        cmd[0] = str(tool_path)
        return subprocess.run(cmd, **kwargs)

    def _get_embedded_tool_path(self, tool_name: str) -> Path:
        """Get path to embedded tool"""
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller bundle
            base_path = Path(sys._MEIPASS)
            tool_path = base_path / "tools" / "bin" / tool_name
        else:
            # Development mode - use system tools
            tool_path = shutil.which(tool_name)

        if not tool_path or not Path(tool_path).exists():
            raise FileNotFoundError(f"Tool not found: {tool_name}")

        return Path(tool_path)
```

**Binary Size Estimates**:
```
Python tools:        ~30MB (bundled with Python runtime)
Native tools:        ~20MB (shellcheck, hadolint, taplo)
Node.js + packages:  ~50MB (node + eslint + prettier)
HuskyCat code:       ~10MB (Python code + dependencies)
Total:              ~110MB (compressed with UPX: ~60-80MB)
```

**Advantages**:
- ✅ TRUE standalone binary (no external dependencies)
- ✅ No container runtime required
- ✅ Single download, works immediately
- ✅ Consistent tool versions across platforms
- ✅ Faster execution (no container overhead)

### Component 3: Unified Build Pipeline

**New Build Strategy**: Build binary WITH embedded tools, then containerize binary

```yaml
# .gitlab-ci.yml (refactored)

stages:
  - download-tools    # Download native tools for each arch
  - build-fat-binary  # Build binaries with embedded toolchain
  - test-binary       # Test standalone binary
  - containerize      # Optional: Wrap binary in minimal container
  - deploy

download:tools:amd64:
  stage: download-tools
  script:
    - mkdir -p tools/amd64
    - curl -L -o tools/amd64/shellcheck <url>
    - curl -L -o tools/amd64/hadolint <url>
    - curl -L -o tools/amd64/taplo <url>
  artifacts:
    paths:
      - tools/amd64

download:tools:arm64:
  stage: download-tools
  script:
    - mkdir -p tools/arm64
    - curl -L -o tools/arm64/shellcheck <url>
    - curl -L -o tools/arm64/hadolint <url>
    - curl -L -o tools/arm64/taplo <url>
  artifacts:
    paths:
      - tools/arm64

build:fat-binary:linux-amd64:
  stage: build-fat-binary
  dependencies:
    - download:tools:amd64
  script:
    - python build_fat_binary.py --arch amd64 --os linux
  artifacts:
    paths:
      - dist/huskycat-linux-amd64

build:fat-binary:linux-arm64:
  stage: build-fat-binary
  dependencies:
    - download:tools:arm64
  script:
    - python build_fat_binary.py --arch arm64 --os linux
  artifacts:
    paths:
      - dist/huskycat-linux-arm64

test:fat-binary:linux-amd64:
  stage: test-binary
  dependencies:
    - build:fat-binary:linux-amd64
  script:
    # Test binary is truly standalone (no container needed)
    - ./dist/huskycat-linux-amd64 --version
    - ./dist/huskycat-linux-amd64 validate --all
    - ldd ./dist/huskycat-linux-amd64  # Should show minimal dependencies

# Optional: Containerize binary for users who want containers
containerize:fat-binary:amd64:
  stage: containerize
  dependencies:
    - build:fat-binary:linux-amd64
  script:
    - |
      cat > ContainerFile.minimal <<EOF
      FROM alpine:latest
      COPY dist/huskycat-linux-amd64 /usr/local/bin/huskycat
      ENTRYPOINT ["/usr/local/bin/huskycat"]
      EOF
    - podman build -f ContainerFile.minimal -t huskycat:minimal-amd64
```

**Advantages**:
- ✅ Binary is primary artifact (not container)
- ✅ Container is optional wrapper (for those who want it)
- ✅ Single source of truth: fat binary
- ✅ Reduced CI complexity
- ✅ Faster builds (parallel downloads)

## Implementation Sprints

### Sprint 10A: Non-Blocking Git Hooks (Week 1-2)

**Goal**: Implement fork-based non-blocking git hooks with TUI

**Tasks**:

1. **Implement Fork-Based Execution** (`core/adapters/git_hooks_nonblocking.py`)
   - [ ] Create `NonBlockingGitHooksAdapter` class
   - [ ] Implement `os.fork()` for process separation
   - [ ] Add PID file management (`.huskycat/validation.pid`)
   - [ ] Implement result caching (`.huskycat/last-run.json`)
   - [ ] Add previous run checking logic
   - [ ] Handle zombie process cleanup

2. **Build TUI Progress Display** (`core/tui.py`)
   - [ ] Install `rich` library for TUI
   - [ ] Create real-time progress table
   - [ ] Add spinner animations for running tools
   - [ ] Implement status indicators (✓, ✗, ⟳, ⋯)
   - [ ] Add keyboard controls (Ctrl+C to background)
   - [ ] Show timing information per tool
   - [ ] Display summary on completion

3. **Refactor Tool Execution for Parallelism** (`unified_validation.py`)
   - [ ] Add `multiprocessing.Pool` for parallel tool execution
   - [ ] Implement tool dependency graph (mypy needs black to run first)
   - [ ] Add result aggregation from parallel workers
   - [ ] Handle partial failures gracefully
   - [ ] Add timeout handling per tool

4. **Update Git Hook Templates** (`templates/hooks/`)
   - [ ] Update `pre-commit.template` to use non-blocking adapter
   - [ ] Update `pre-push.template` to check previous results
   - [ ] Add clear user messaging
   - [ ] Add `--no-verify` bypass instructions

5. **Testing**
   - [ ] Unit tests for fork behavior
   - [ ] Integration tests for TUI display
   - [ ] E2E tests for full git workflow
   - [ ] Test previous result checking
   - [ ] Test parallel tool execution

**Code References**:
- `src/huskycat/core/adapters/git_hooks.py:16-58` - Current blocking adapter
- `src/huskycat/templates/hooks/pre-commit.template:1-50` - Git hook template
- `src/huskycat/unified_validation.py:60-180` - Validator execution

**Success Criteria**:
- ✅ Git operations return immediately (<100ms)
- ✅ Full validation runs in background
- ✅ TUI shows real-time progress
- ✅ Results cached for next git operation
- ✅ No "fast mode" - all tools run

### Sprint 10B: Fat Binary with Embedded Toolchain (Week 3-4)

**Goal**: Build standalone binary with all tools embedded (no container dependency)

**Tasks**:

1. **Tool Download Script** (`scripts/download_tools.py`)
   - [ ] Implement multi-platform tool downloader
   - [ ] Add version pinning for reproducibility
   - [ ] Support architectures: amd64, arm64, darwin-arm64, darwin-amd64
   - [ ] Download shellcheck from GitHub releases
   - [ ] Download hadolint from GitHub releases
   - [ ] Download taplo from GitHub releases
   - [ ] Verify checksums for security
   - [ ] Handle download failures gracefully

2. **Node.js Bundle Builder** (`scripts/bundle_nodejs.py`)
   - [ ] Create minimal Node.js runtime bundle
   - [ ] Include npm packages: eslint, prettier, typescript
   - [ ] Strip dev dependencies
   - [ ] Compress bundle
   - [ ] Test bundle functionality

3. **Fat Binary Builder** (`build_fat_binary.py`)
   - [ ] Refactor `build_binary.py` to `build_fat_binary.py`
   - [ ] Add `--embed-tools` flag (default: true)
   - [ ] Collect Python tools from UV environment
   - [ ] Embed native tools (shellcheck, hadolint, taplo)
   - [ ] Embed Node.js bundle
   - [ ] Configure PyInstaller data collection
   - [ ] Add resource extraction on first run
   - [ ] Test binary size (<200MB target)

4. **Embedded Tool Execution** (`unified_validation.py`)
   - [ ] Refactor `_execute_command()` to use embedded tools
   - [ ] Implement `_get_embedded_tool_path()`
   - [ ] Handle PyInstaller `_MEIPASS` path
   - [ ] Fall back to system tools in dev mode
   - [ ] Remove container delegation logic
   - [ ] Update `is_available()` to check embedded tools

5. **Remove Container Dependency**
   - [ ] Remove `_is_running_in_container()` checks
   - [ ] Remove `_build_container_command()`
   - [ ] Remove `_get_available_container_runtime()`
   - [ ] Update error messages (no more "install container runtime")
   - [ ] Update documentation

6. **Update Build Pipeline** (`.gitlab-ci.yml`)
   - [ ] Create `download-tools` stage
   - [ ] Create per-arch tool download jobs
   - [ ] Refactor binary build jobs to use downloaded tools
   - [ ] Add binary standalone tests (no container)
   - [ ] Make container builds optional (wrap binary)
   - [ ] Update artifact paths

7. **Testing**
   - [ ] Test fat binary on clean system (no Python, no containers)
   - [ ] Test all tools execute from embedded binaries
   - [ ] Test multi-arch binaries (amd64, arm64, darwin)
   - [ ] Benchmark binary size
   - [ ] Benchmark execution speed vs container
   - [ ] Test resource extraction

**Code References**:
- `build_binary.py:1-100` - Current binary builder
- `unified_validation.py:85-170` - Container delegation logic
- `.gitlab-ci.yml:268-298` - Binary build jobs
- `ContainerFile:1-153` - Current container build

**Success Criteria**:
- ✅ Binary runs on clean system (no Python, no containers)
- ✅ All 15+ tools work from embedded binaries
- ✅ Binary size <200MB (uncompressed)
- ✅ Execution speed matches or beats container mode
- ✅ Multi-arch support maintained

## Migration Strategy

### Phase 1: Parallel Implementation (Week 1-2)
- Implement non-blocking adapter alongside existing blocking adapter
- Add feature flag: `HUSKYCAT_NONBLOCKING_HOOKS=1`
- Beta test with select users
- Gather feedback on TUI experience

### Phase 2: Fat Binary Beta (Week 3-4)
- Build fat binaries for Linux amd64/arm64
- Test on clean systems
- Benchmark performance
- Gather binary size feedback

### Phase 3: Default Switch (Week 5)
- Make non-blocking hooks default
- Make fat binaries default
- Update documentation
- Deprecate container-only mode

### Phase 4: Cleanup (Week 6)
- Remove "fast mode" logic
- Remove container delegation code
- Remove old blocking adapter
- Archive old ContainerFile

## Testing Strategy

### Unit Tests
```python
# tests/test_nonblocking_hooks.py
def test_fork_validation_process():
    """Test that validation process forks correctly"""

def test_previous_results_checking():
    """Test that previous results are checked"""

def test_tui_progress_display():
    """Test TUI renders correctly"""

# tests/test_fat_binary.py
def test_embedded_tool_extraction():
    """Test tools extract from binary"""

def test_embedded_tool_execution():
    """Test tools execute correctly"""

def test_binary_size():
    """Test binary size is within limits"""
```

### Integration Tests
```python
# tests/integration/test_git_workflow.py
def test_nonblocking_commit():
    """Test full non-blocking commit workflow"""
    # 1. Make changes
    # 2. Git add
    # 3. Git commit (returns immediately)
    # 4. Validation runs in background
    # 5. Next commit checks previous results

def test_fat_binary_standalone():
    """Test fat binary runs without Python/containers"""
    # 1. Run binary on clean Docker container
    # 2. Verify all tools work
    # 3. Verify no external dependencies
```

### E2E Tests
```bash
# tests/e2e/test_user_experience.sh

# Test 1: Fast commit flow
git add file.py
time git commit -m "test"  # Should return in <100ms
# Background validation completes
git add file2.py
git commit -m "test2"  # Should check previous results

# Test 2: Standalone binary
./dist/huskycat-linux-amd64 validate --all  # No container needed
ldd ./dist/huskycat-linux-amd64  # Verify minimal deps
```

## Documentation Updates

### Update Files
1. **README.md** - Remove container requirements, emphasize standalone
2. **docs/installation.md** - Simplify to "download binary + run"
3. **docs/architecture/execution-models.md** - Remove container delegation
4. **docs/architecture/product-modes.md** - Remove "fast mode"
5. **CLAUDE.md** - Update architecture instructions
6. **docs/user-guide/git-hooks.md** - Document non-blocking behavior

### New Documents
1. **docs/architecture/non-blocking-hooks.md** - Explain fork strategy
2. **docs/architecture/fat-binary.md** - Explain embedded toolchain
3. **docs/development/building-fat-binary.md** - Build instructions
4. **docs/troubleshooting/tui.md** - TUI issues and solutions

## Risk Analysis

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Binary size exceeds 200MB | High | Medium | Aggressive compression, optional tools |
| Fork() not supported on Windows | High | High | Use threading instead of fork on Windows |
| Tool version conflicts | Medium | Low | Pin versions, test thoroughly |
| TUI doesn't work in all terminals | Medium | Medium | Fall back to simple progress |
| Embedded tools have wrong arch | High | Low | Multi-arch detection, clear errors |

### User Experience Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Users confused by background validation | Medium | Medium | Clear messaging, TUI feedback |
| Previous failure not noticed | High | Low | Prominent error message, block next commit |
| Binary too large to download | Medium | Low | Provide compressed versions |
| Slower than expected | Low | Low | Benchmark and optimize |

## Success Metrics

### Performance Metrics
- Git operation latency: <100ms (currently 3-5s)
- Full validation time: <10s (all tools, not just fast subset)
- Binary size: <200MB uncompressed
- Download size: <100MB compressed
- Tool execution overhead: <5% vs native

### User Experience Metrics
- Time to first commit: <30s (download + install)
- Developer satisfaction: >90% prefer non-blocking
- Installation success rate: >95% on clean systems
- False failure rate: <1% (previous results checking)

### Quality Metrics
- CI pass rate after git hooks pass: >95%
- Tool coverage in binary: 100% (all 15+ tools)
- Multi-arch support: 4 platforms (linux-amd64, linux-arm64, darwin-amd64, darwin-arm64)
- E2E test coverage: >80%

## Rollback Plan

If critical issues discovered:

### Week 1-2 Rollback
- Disable non-blocking adapter via feature flag
- Revert to blocking adapter
- Keep TUI code for future use

### Week 3-4 Rollback
- Provide container-based binary as fallback
- Keep fat binary as beta option
- Document container requirement again

### Full Rollback
- Revert all changes
- Restore Sprint 9B state
- Document lessons learned
- Plan Sprint 10.1 with improvements

## Dependencies & Prerequisites

### External Dependencies
- **rich** library for TUI
- **multiprocessing** for parallelism
- Native tool binaries for each arch
- Node.js runtime bundle

### Internal Prerequisites
- Sprint 9B complete (E2E tests + ARM64 optimization)
- CI pipeline stable
- Documentation up to date
- All adapters implemented (Sprint 0)

## Future Enhancements (Post-Sprint 10)

### Sprint 11: Advanced TUI Features
- Real-time log tailing
- Tool output filtering
- Interactive fixing (press key to auto-fix)
- Validation history viewer

### Sprint 12: Performance Optimization
- Intelligent tool selection (only run relevant tools)
- Incremental validation (only changed files + deps)
- Persistent daemon mode (avoid startup overhead)
- Tool result caching

### Sprint 13: Distribution Improvements
- Auto-update mechanism
- Homebrew formula
- apt/yum packages
- Windows installer

## Conclusion

Sprint 10 represents a fundamental architectural shift:

**From**: Container-dependent, blocking, compromised validation
**To**: Standalone, non-blocking, comprehensive validation

This transformation will:
1. ✅ Eliminate all external dependencies (true standalone)
2. ✅ Improve developer experience (non-blocking)
3. ✅ Increase validation coverage (no "fast mode")
4. ✅ Simplify installation (single binary download)
5. ✅ Reduce CI complexity (single build artifact)

**Estimated Effort**: 3-4 weeks
**Estimated LOC Changed**: ~2,000 lines
**Risk Level**: High (architectural change)
**Value**: Very High (transforms product positioning)

---

**Approval Required From**:
- Technical Lead (architecture review)
- Product Owner (roadmap alignment)
- DevOps (CI pipeline changes)

**Next Steps**:
1. Review and approve proposal
2. Create detailed task breakdown
3. Set up feature branches
4. Begin Sprint 10A (non-blocking hooks)
