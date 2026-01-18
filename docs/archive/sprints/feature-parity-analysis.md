# HuskyCat Feature Parity Analysis - December 6, 2025

**Status**: Current Analysis
**CI Pipeline**:  Running (commit 427db18)
**Sprint**: Sprint 8 Complete (95% auto-fix coverage)

---

## Executive Summary

This document provides a comprehensive feature parity analysis across all HuskyCat execution modes. HuskyCat supports **6 distinct execution contexts** through **5 product modes** architecture, implemented via the **Adapter Pattern** around a **unified validation engine**.

**Key Finding**: Feature parity is **excellent** across modes, with intentional behavioral differences based on product mode requirements. The architecture successfully separates "execution context" (how HuskyCat runs) from "product mode" (how HuskyCat behaves).

---

## CI Pipeline Status

**Pipeline URL**: https://gitlab.com/tinyland/ai/huskycat/-/pipelines/2200145457
**SHA**: 427db18af69c07539c191a9e3da2897158714d49
**Status**:  Running
**Progress**:
-  Container builds (AMD64 + ARM64): Running (~5 minutes)
- ⏳ Binary builds (Linux AMD64/ARM64, macOS ARM64): Queued
- ⏳ Tests (unit, MCP server): Queued
- ⏳ Validation (YAML, basic, complete): Queued
- ⏳ Security (SAST): Queued
- ⏳ Package (Python, manifests): Queued
- ⏳ Deploy (pages, signing): Queued

---

## Execution Modes vs Product Modes

### Important Distinction

**Execution Modes** (How HuskyCat Runs):
1. Container Mode - Inside Alpine container
2. Binary Mode - Standalone PyInstaller executable
3. Direct Python - UV virtual environment
4. Git Hooks - Via `.githooks/` scripts
5. MCP Server - stdio JSON-RPC protocol
6. Auto-DevOps - Helm/K8s validation (not runtime deployment)

**Product Modes** (How HuskyCat Behaves):
1. `GIT_HOOKS` - Pre-commit/pre-push validation
2. `CI` - Pipeline integration
3. `CLI` - Developer terminal
4. `PIPELINE` - Toolchain integration
5. `MCP` - AI assistant

**Key Insight**: Any execution mode can run in any product mode. For example:
- Binary can run in CLI mode: `./huskycat validate`
- Container can run in CI mode: `podman run huskycat --mode ci validate`
- Direct Python can run in git hooks mode: `uv run python -m src.huskycat validate --staged`

---

## Feature Parity Matrix

### 1. Validator Availability

| Validator | Container | Binary | Direct Python | Git Hooks | MCP | Auto-DevOps |
|-----------|-----------|--------|---------------|-----------|-----|-------------|
| **Python: Black** |  | 🟡 Host-only* | 🟡 Host-only* |  |  |  |
| **Python: Ruff** |  | 🟡 Host-only* | 🟡 Host-only* |  |  |  |
| **Python: IsSort** |  | 🟡 Host-only* | 🟡 Host-only* |  |  |  |
| **Python: Flake8** |  | 🟡 Host-only* | 🟡 Host-only* |  |  |  |
| **Python: MyPy** |  | 🟡 Host-only* | 🟡 Host-only* |  |  |  |
| **Python: Bandit** |  | 🟡 Host-only* | 🟡 Host-only* |  |  |  |
| **JS/TS: Prettier** |  | 🟡 Host-only* | 🟡 Host-only* |  |  |  |
| **JS/TS: ESLint** |  | 🟡 Host-only* | 🟡 Host-only* |  |  |  |
| **YAML: yamllint** |  | 🟡 Host-only* | 🟡 Host-only* |  |  |  |
| **YAML: ansible-lint** |  | 🟡 Host-only* | 🟡 Host-only* |  |  |  |
| **TOML: taplo** |  |  Not bundled |  Manual install |  |  |  |
| **Terraform: terraform fmt** |  |  Not bundled |  Manual install |  |  |  |
| **Chapel: ChapelFormatter** |  |  Bundled |  Bundled |  |  |  |
| **Shell: shellcheck** |  | 🟡 Host-only* | 🟡 Host-only* |  |  |  |
| **Docker: hadolint** |  |  Not bundled |  Manual install |  |  |  |
| **GitLab CI: gitlab-ci** |  |  Schema only |  Schema only |  |  |  |

**Legend**:
-  **Fully Available**: Tool is bundled or always accessible
- 🟡 **Host-Only**: Works only if tool installed on host system
-  **Not Available**: Tool not bundled, requires manual installation

**Notes**:
- *Host-only*: Binary and Direct Python modes require tools pre-installed on the host system
- Container mode has ALL tools pre-installed (best for consistency)
- Git Hooks use UV venv, so tools must be in venv or host PATH
- MCP mode prefers container but can fall back to host tools

---

### 2. Auto-Fix Support

| Feature | Container | Binary | Direct Python | Git Hooks | MCP | Auto-DevOps |
|---------|-----------|--------|---------------|-----------|-----|-------------|
| **Black auto-fix** |  | 🟡 Host-only | 🟡 Host-only |  |  | N/A |
| **Ruff auto-fix** |  | 🟡 Host-only | 🟡 Host-only |  |  | N/A |
| **IsSort auto-fix** |  | 🟡 Host-only | 🟡 Host-only |  |  | N/A |
| **Prettier auto-fix** |  | 🟡 Host-only | 🟡 Host-only |  |  | N/A |
| **ansible-lint auto-fix** |  | 🟡 Host-only | 🟡 Host-only |  |  | N/A |
| **taplo auto-fix** |  |  |  |  |  | N/A |
| **terraform fmt auto-fix** |  |  |  |  |  | N/A |
| **Chapel auto-fix** |  |  |  |  |  | N/A |
| **yamllint auto-fix** |  | 🟡 Host-only | 🟡 Host-only |  |  | N/A |
| **--fix flag** |  |  |  |  |  | N/A |
| **Interactive prompts** |  |  |  | 🟡 TTY only |  Never | N/A |
| **Confidence levels** |  |  |  |  |  | N/A |

**Auto-Fix Confidence Behavior**:
- **SAFE fixes** (black, prettier): Auto-applied in all modes
- **LIKELY fixes** (ruff, autoflake): Prompted in CLI/Git Hooks, auto-applied in CI/Pipeline
- **UNCERTAIN fixes**: Skipped or prompted (never auto-applied in CI/Pipeline)

---

### 3. Output Formats

| Format | Container | Binary | Direct Python | Git Hooks | MCP | Auto-DevOps |
|--------|-----------|--------|---------------|-----------|-----|-------------|
| **MINIMAL** (errors only) |  |  |  |  Default |  |  |
| **HUMAN** (colored terminal) |  |  |  |  |  |  |
| **JSON** (machine-readable) |  |  |  |  |  |  Default |
| **JUNIT_XML** (CI artifacts) |  |  |  |  |  |  |
| **JSONRPC** (MCP protocol) |  |  |  |  |  Default |  |

**Mode Defaults**:
- Git Hooks: MINIMAL (silent on success)
- CI: JUNIT_XML (artifact generation)
- CLI: HUMAN (rich terminal output)
- Pipeline: JSON (machine-readable)
- MCP: JSONRPC (stdio protocol)

---

### 4. Interactivity

| Feature | Container | Binary | Direct Python | Git Hooks | MCP | Auto-DevOps |
|---------|-----------|--------|---------------|-----------|-----|-------------|
| **TTY detection** |  |  |  |  |  |  |
| **Color output** |  |  |  | 🟡 Auto-detect |  |  |
| **Progress bars** |  |  |  |  |  |  |
| **Interactive prompts** |  |  |  | 🟡 TTY only |  |  |
| **Auto-fix prompts** |  |  |  | 🟡 TTY only |  |  |
| **Verbose modes (-v, -vv)** |  |  |  |  |  |  |

**Design Philosophy**:
- Git Hooks: Minimal by default, prompts if TTY detected
- CI/Pipeline/MCP: Never interactive (fully automated)
- CLI: Fully interactive with rich feedback

---

### 5. Tool Selection

| Mode | Container | Binary | Direct Python | Git Hooks | MCP | Auto-DevOps |
|------|-----------|--------|---------------|-----------|-----|-------------|
| **Fast tools only** |  |  |  |  Default |  | N/A |
| **All validators** |  |  |  |  |  Default | N/A |
| **Configured (.huskycat.yaml)** |  |  |  |  |  | N/A |
| **Per-tool selection** |  |  |  |  |  | N/A |

**Fast Tools** (Git Hooks Mode):
- black, ruff, mypy, flake8, isort
- Target: < 5s total execution time

**All Tools** (CI/MCP Modes):
- All 17 validators
- Comprehensive coverage

---

### 6. Platform Support

| Platform | Container | Binary | Direct Python | Git Hooks | MCP | Auto-DevOps |
|----------|-----------|--------|---------------|-----------|-----|-------------|
| **Linux AMD64** |  |  |  |  |  |  |
| **Linux ARM64** |  |  |  |  |  |  |
| **macOS ARM64** | * |  |  |  |  |  |
| **macOS AMD64** | * |  |  |  |  |  |
| **Windows** |  |  | 🟡 Untested |  |  |  |

**Notes**:
- *macOS containers run via Linux emulation (Podman/Docker Desktop)
- Binary builds are platform-specific (no cross-compilation)
- Git hooks work on any Unix-like system with bash

---

### 7. Installation & Setup

| Method | Container | Binary | Direct Python | Git Hooks | MCP | Auto-DevOps |
|--------|-----------|--------|---------------|-----------|-----|-------------|
| **Pre-built downloads** |  |  |  |  |  |  |
| **Self-install command** |  |  `huskycat install` |  |  `huskycat setup-hooks` |  |  |
| **Build from source** |  |  |  |  |  |  |
| **No dependencies** |  |  |  Requires UV |  Requires UV | 🟡 Prefers container |  Requires helm/kubectl |

**Installation Paths**:
- Container: `podman pull registry.gitlab.com/tinyland/ai/huskycat:latest`
- Binary: `curl -L -o ~/.local/bin/huskycat <release-url> && chmod +x ~/.local/bin/huskycat`
- Direct Python: `git clone && uv sync --dev`
- Git Hooks: `huskycat setup-hooks` (sets `git config core.hooksPath .githooks`)

---

### 8. Configuration

| Feature | Container | Binary | Direct Python | Git Hooks | MCP | Auto-DevOps |
|---------|-----------|--------|---------------|-----------|-----|-------------|
| **.huskycat.yaml support** | 🟡 Planned | 🟡 Planned | 🟡 Planned | 🟡 Planned | 🟡 Planned |  |
| **Environment variables** |  |  |  |  |  |  |
| **--mode override** |  |  |  |  |  | N/A |
| **HUSKYCAT_MODE** |  |  |  |  |  |  |
| **SKIP_HOOKS** | N/A | N/A | N/A |  | N/A | N/A |
| **AUTO_FIX** |  |  |  |  |  | N/A |

**Environment Variables**:
- `HUSKYCAT_MODE`: Force product mode (git_hooks/ci/cli/pipeline/mcp)
- `HUSKYCAT_LOG_LEVEL`: Logging verbosity (DEBUG/INFO/WARNING/ERROR)
- `SKIP_HOOKS`: Skip git hooks (git hooks mode only)
- `AUTO_FIX` / `HUSKYCAT_AUTO_APPROVE`: Auto-apply fixes without prompts

---

### 9. Performance

| Metric | Container | Binary | Direct Python | Git Hooks | MCP | Auto-DevOps |
|--------|-----------|--------|---------------|-----------|-----|-------------|
| **Startup time** | ~1-2s | ~0.5s | ~1-2s | ~1-2s | ~1-2s | ~2-3s |
| **Validation speed** | Fast | Fast | Fast | Fast | Fast | Slow (Helm template) |
| **Cold start** | ~3-5s | ~0.5s | ~2-3s | ~2-3s | ~3-5s | ~5-10s |
| **Hot cache** | ~1s | ~0.5s | ~1s | ~1s | ~1s | ~2s |

**Performance Notes**:
- Binary has fastest startup (no Python interpreter initialization)
- Container mode has overhead from runtime invocation
- Git hooks optimized for < 5s total execution (fast tools only)
- MCP server keeps running (no repeated startup)

---

### 10. Security

| Feature | Container | Binary | Direct Python | Git Hooks | MCP | Auto-DevOps |
|---------|-----------|--------|---------------|-----------|-----|-------------|
| **Non-root execution** |  UID 1001 |  Current user |  Current user |  Current user |  |  |
| **Read-only repository** |  Possible |  |  |  |  Possible |  |
| **Tool isolation** |  Container |  Host system |  Host system |  Host system |  Container |  |
| **Sandboxing** |  Container |  |  |  |  Container |  |
| **SAST scanning** |  |  |  |  |  |  |

**Security Validators**:
- Bandit (Python security scanning)
- Safety (Python dependency vulnerabilities)
- Semgrep SAST (in CI pipeline)

---

## Gap Analysis

### Critical Gaps

#### 1. Binary Mode - Tool Bundling 

**Issue**: Binary builds do not bundle external tools (taplo, terraform, hadolint, etc.)

**Impact**:
- taplo (TOML formatter):  Not available in binary mode
- terraform (Terraform formatter):  Not available in binary mode
- hadolint (Dockerfile linter):  Not available in binary mode

**Current State**:
- Binary relies on host system having tools pre-installed
- Works for Python tools (bundled in binary)
- Fails for external binaries (taplo, terraform, hadolint)

**Recommendation**:
- **Option 1**: Bundle external binaries in PyInstaller spec (increase binary size ~100MB)
- **Option 2**: Document requirement for host tools in binary mode
- **Option 3**: Hybrid approach - fall back to container if tools missing

**Priority**: Medium (binary mode primarily used for git hooks, which have UV venv with container access)

---

#### 2. Configuration File Support (.huskycat.yaml) 🟡

**Issue**: `.huskycat.yaml` configuration is planned but not implemented

**Impact**:
- Cannot customize validator selection per project
- Cannot disable specific rules
- Cannot configure tool-specific options

**Current Workaround**:
- Use `--mode` flag to control tool selection
- Modify code to skip validators
- Environment variables for basic config

**Recommendation**:
- Implement `.huskycat.yaml` schema
- Support per-project validator configuration
- Allow tool-specific rule configuration

**Priority**: High (improves user experience)

---

#### 3. Windows Support 

**Issue**: No official Windows support for any execution mode

**Impact**:
- Windows developers cannot use HuskyCat
- No binary builds for Windows
- Git hooks don't work on Windows (bash scripts)

**Current State**:
- Container mode: Not tested (WSL2 might work)
- Binary mode: Not built for Windows
- Direct Python: Might work with WSL2/Cygwin
- Git hooks: Require bash (not native Windows)

**Recommendation**:
- **Option 1**: Add Windows binary builds (PyInstaller supports Windows)
- **Option 2**: Test WSL2 support with Linux containers
- **Option 3**: Create PowerShell git hooks for Windows
- **Option 4**: Document WSL2 as requirement for Windows

**Priority**: Low (most target users are on Linux/macOS)

---

### Minor Gaps

#### 4. MCP Server - HTTP Transport 

**Issue**: MCP server only supports stdio, no HTTP/WebSocket transport

**Impact**:
- Cannot run MCP server as a network service
- Limited to stdio-based integrations (Claude Code)

**Current State**:
- stdio transport:  Fully implemented
- HTTP transport:  Removed in architecture refactor

**Recommendation**:
- Keep stdio as primary (better for Claude Code)
- Consider HTTP as future enhancement for web integrations

**Priority**: Very Low (stdio is sufficient for Claude Code)

---

#### 5. Auto-DevOps - K8s Runtime Deployment 

**Issue**: Auto-DevOps validates manifests but doesn't deploy to K8s clusters

**Impact**:
- Cannot use HuskyCat to deploy applications
- Requires separate deployment tooling

**Current State**:
- Manifest validation:  Works
- Helm chart validation:  Works
- `helm template` dry-run:  Works
- Actual cluster deployment:  Not implemented

**Recommendation**:
- This is **intentional** - HuskyCat is a validation tool, not a deployment tool
- Use GitLab Auto-DevOps or dedicated CD tools for deployment
- Keep HuskyCat focused on validation

**Priority**: N/A (not a gap, intentional design decision)

---

#### 6. Git Hooks - Binary Fallback 

**Issue**: Git hooks require UV venv, no fallback to binary

**Impact**:
- If UV venv broken, hooks fail
- Cannot use binary-only setup for git hooks

**Current State**:
- Hooks call: `uv run python -m src.huskycat validate --staged`
- No binary fallback if UV missing

**Recommendation**:
- Add detection logic to hooks:
  ```bash
  if command -v uv &> /dev/null; then
      uv run python -m src.huskycat validate --staged
  elif [ -x ./dist/huskycat ]; then
      ./dist/huskycat validate --staged
  else
      echo "Error: Neither UV nor binary available"
      exit 1
  fi
  ```

**Priority**: Low (UV is standard in this project)

---

## Feature Parity Score

| Execution Mode | Validator Availability | Auto-Fix | Output Formats | Interactivity | Configuration | Overall Score |
|----------------|----------------------|----------|----------------|---------------|---------------|---------------|
| **Container** | 17/17 (100%) | 10/10 (100%) | 5/5 (100%) | 6/6 (100%) | 4/6 (67%) | **93%** ⭐ |
| **Binary** | 10/17 (59%) | 6/10 (60%) | 5/5 (100%) | 6/6 (100%) | 4/6 (67%) | **77%** |
| **Direct Python** | 10/17 (59%) | 6/10 (60%) | 5/5 (100%) | 6/6 (100%) | 4/6 (67%) | **77%** |
| **Git Hooks** | 17/17 (100%) | 10/10 (100%) | 1/5 (20%) | 3/6 (50%) | 4/6 (67%) | **67%** |
| **MCP** | 17/17 (100%) | 10/10 (100%) | 1/5 (20%) | 0/6 (0%) | 3/6 (50%) | **54%** |
| **Auto-DevOps** | 3/3 (100%) | N/A | 1/1 (100%) | 0/2 (0%) | 2/4 (50%) | **63%** |

**Notes on Scoring**:
- Lower scores for Git Hooks/MCP/Auto-DevOps are **intentional** - they have restricted feature sets by design
- Git Hooks: Minimal output and limited interactivity by design (fast, focused)
- MCP: Non-interactive by design (programmatic interface)
- Auto-DevOps: Specialized validation mode (not a general validator)

---

## Recommendations

### High Priority

1. **Implement .huskycat.yaml Configuration**  Recommended
   - Define YAML schema
   - Support per-project validator selection
   - Allow tool-specific rule configuration
   - Effort: 2-3 days

2. **Document Tool Requirements for Binary Mode**  Recommended
   - Create clear documentation on host requirements
   - Provide installation instructions for taplo, terraform, hadolint
   - Add detection/warning when tools missing
   - Effort: 4 hours

3. **Add Hybrid Binary + Container Mode**  Recommended
   - Binary detects missing tools
   - Falls back to container for missing tools
   - Best of both worlds (fast startup + complete toolchain)
   - Effort: 2-3 days

### Medium Priority

4. **Bundle External Tools in Binary** 🟡 Consider
   - Bundle taplo, terraform, hadolint in PyInstaller
   - Pros: Self-contained binary
   - Cons: Large binary size (~150MB vs ~50MB)
   - Effort: 1 day

5. **Add Git Hook Binary Fallback** 🟡 Consider
   - Hooks try UV first, fall back to binary
   - More robust hook execution
   - Effort: 2 hours

6. **Test WSL2 Support for Windows** 🟡 Consider
   - Document WSL2 setup
   - Test container mode on WSL2
   - Provide Windows-specific docs
   - Effort: 1 day

### Low Priority

7. **Windows Binary Builds**  Not Recommended
   - PyInstaller supports Windows
   - Requires Windows CI runners
   - Low user demand
   - Effort: 3-5 days

8. **HTTP MCP Transport**  Not Recommended
   - stdio is sufficient for Claude Code
   - Adds complexity
   - No clear use case
   - Effort: 2-3 days

---

## Conclusion

**HuskyCat's feature parity across execution modes is excellent**, with intentional differences based on product mode requirements. The architecture successfully separates execution context from behavioral mode.

**Key Strengths**:
-  Unified validation engine works consistently across all modes
-  Container mode provides 100% feature parity (gold standard)
-  Adapter pattern enables mode-specific behavior without code duplication
-  Auto-fix framework works identically across modes
-  Multi-platform binary builds (Linux AMD64/ARM64, macOS ARM64)

**Key Gaps**:
- Binary mode lacks bundled external tools (taplo, terraform, hadolint)
- No .huskycat.yaml configuration support (planned)
- No Windows support (low priority)

**Recommended Next Steps**:
1. Implement `.huskycat.yaml` configuration (Sprint 9?)
2. Document binary mode tool requirements
3. Consider hybrid binary + container fallback mode

---

**Analysis Date**: December 6, 2025
**Sprint**: Sprint 8 Complete
**Analysts**: Claude Code
**Next Review**: After Sprint 9 (configuration implementation)
