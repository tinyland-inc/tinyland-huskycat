# CRUSH - HuskyCat Quick Reference

**Last Updated**: 2025-01-15
**Version**: 2.0.0
**Scope**: HuskyCat validation platform operations

---

## Quick Commands

### Validation

```bash
# Fast validation (binary - preferred)
./dist/huskycat validate .
./dist/huskycat validate src/

# Validate with auto-fix
./dist/huskycat validate --fix src/
npm run validate:fix

# Validate staged files only (git hooks mode)
./dist/huskycat validate --staged
npm run validate:staged

# Validate all files (comprehensive)
./dist/huskycat validate --all
npm run validate:all

# Development mode (allow warnings)
npm run validate:dev

# UV development commands
uv run python3 -m src.huskycat validate .
uv run python3 -m src.huskycat validate --fix src/

# Force specific mode
./dist/huskycat --mode cli validate .       # Rich terminal output
./dist/huskycat --mode pipeline validate .  # JSON output
./dist/huskycat --mode ci validate .        # JUnit XML output
./dist/huskycat --json validate .           # Shorthand for pipeline mode

# Validate CI configuration
npm run validate:ci
./dist/huskycat ci-validate .gitlab-ci.yml
```

### Git Hooks

```bash
# Install hooks (binary - preferred)
./dist/huskycat setup-hooks
./dist/huskycat install  # Self-installs to ~/.local/bin

# Install hooks (development)
npm run hooks:install

# Enable non-blocking mode (fast commits, background validation)
git config --local huskycat.nonblocking true

# Disable non-blocking mode
git config --local huskycat.nonblocking false

# Check hook status
cat .git/hooks/pre-commit
git config --get huskycat.nonblocking

# Bypass hooks (development - when MyPy blocks commits)
git commit --no-verify -m "message"
git push --no-verify
```

### Building

```bash
# Build fat binary (with embedded tools)
npm run build:binary
npm run build:fat
uv run python scripts/build_fat_binary.py

# Build for all platforms
npm run build:fat:all
uv run python scripts/build_fat_binary.py --all-platforms

# Download embedded tools
npm run tools:download
npm run tools:download:all
uv run python scripts/download_tools.py --platform linux-amd64

# Build container
npm run container:build
podman build -f ContainerFile -t huskycat:local .

# Test container
npm run container:test
podman run --rm huskycat:local --version

# Build documentation
npm run docs:build
mkdocs build

# Verify binary
npm run verify:binary
bash scripts/verify_binary.sh dist/bin/huskycat-linux-amd64
```

### Testing

```bash
# All tests (excluding E2E)
npm run test:all
uv run pytest tests/ -v -m 'not e2e'

# Unit tests only
npm run test:unit
uv run pytest tests/ -v -m unit

# Property-based tests (Hypothesis)
uv run pytest tests/test_*pbt.py -v

# Specific test suites
uv run pytest tests/test_mode_detection.py -v    # Mode detection
uv run pytest tests/test_binary_bootstrap.py -v  # Binary bootstrap
uv run pytest tests/test_mcp_server_pbt.py -v    # MCP server

# With coverage
uv run pytest tests/ --cov=src/ --cov-report=html

# With CI Hypothesis profile (shorter timeouts)
HYPOTHESIS_PROFILE=ci uv run pytest tests/test_*pbt.py -v
```

### MCP Server

```bash
# Start HuskyCat MCP server
./dist/huskycat mcp-server
npm run mcp:server
uv run python3 -m src.huskycat mcp-server

# Test MCP server (tools/list)
npm run mcp:test
echo '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' | ./dist/huskycat mcp-server

# Test MCP initialization
echo '{"jsonrpc":"2.0","id":1,"method":"initialize"}' | ./dist/huskycat mcp-server

# Add to Claude Code
claude mcp add huskycat -- ./dist/huskycat mcp-server
```

### Status and Clean

```bash
# Show configuration status
./dist/huskycat status
npm run status

# Clean cache
./dist/huskycat clean
npm run clean
```

---

## Product Modes Architecture

HuskyCat operates in **5 distinct product modes**, each optimized for different contexts.

### Mode Overview

| Mode | Adapter | Output Format | Tools | Speed | Use Case |
|------|---------|---------------|-------|-------|----------|
| Git Hooks (Blocking) | `git_hooks.py` | MINIMAL | Fast (4) | 5-30s | Pre-commit validation |
| Git Hooks (Non-Blocking) | `git_hooks_nonblocking.py` | MINIMAL + TUI | All (15+) | <100ms commit | Background validation |
| CI | `ci.py` | JUNIT_XML | All (15+) | 30s-5min | Pipeline integration |
| CLI | `cli.py` | HUMAN (colored) | Configured | Variable | Developer usage |
| Pipeline | `pipeline.py` | JSON | All (15+) | Variable | Automation/scripting |
| MCP | `mcp.py` | JSONRPC | All (15+) | <1s | AI integration |

### Mode Detection Priority

```python
# src/huskycat/core/mode_detector.py
# Detection priority (highest to lowest):
1. --mode flag (explicit override)
2. HUSKYCAT_MODE environment variable
3. MCP server command detection (mcp-server in argv)
4. Git hooks environment variables (GIT_AUTHOR_NAME, GIT_INDEX_FILE, etc.)
5. CI environment variables (CI, GITLAB_CI, GITHUB_ACTIONS, etc.)
6. TTY/pipe detection (no TTY = pipeline mode)
7. Default: CLI mode
```

### Mode-Specific Behavior

**Git Hooks Mode (Blocking)**:
- Fast tools only: black, ruff, mypy, flake8
- Minimal output (errors only)
- Silent on success
- Exit code: 0=pass, 1=fail (blocks commit)

**Git Hooks Mode (Non-Blocking)**:
- Parent returns in <100ms
- Child runs all 15+ tools in background
- Real-time TUI progress display
- Checks previous run failures before commit

**CI Mode**:
- JUnit XML output for pipeline artifacts
- All validators run comprehensively
- Never interactive
- Coverage reports generated

**CLI Mode**:
- Rich colored terminal output
- Progress bars and spinners
- Interactive prompts enabled
- Verbose options: -v, -vv, -vvv

**Pipeline Mode**:
- Machine-readable JSON output
- Composable with pipes (stdin/stdout)
- Never interactive
- Scriptable

**MCP Mode**:
- JSON-RPC 2.0 protocol over stdio
- All validators exposed as MCP tools
- Never interactive
- Transport: stdin/stdout

### Key Files

| File | Purpose |
|------|---------|
| `src/huskycat/core/mode_detector.py` | Mode detection logic |
| `src/huskycat/core/adapters/git_hooks.py` | Blocking git hooks adapter |
| `src/huskycat/core/adapters/git_hooks_nonblocking.py` | Non-blocking git hooks adapter |
| `src/huskycat/core/adapters/ci.py` | CI mode adapter |
| `src/huskycat/core/adapters/cli.py` | CLI mode adapter |
| `src/huskycat/core/adapters/pipeline.py` | Pipeline mode adapter |
| `src/huskycat/core/adapters/mcp.py` | MCP mode adapter |
| `src/huskycat/core/factory.py` | Adapter factory pattern |

---

## Execution Models

HuskyCat supports **3 execution models** for different deployment scenarios.

### 1. Binary Execution (Preferred)

```bash
# Fast startup (~100ms), no dependencies
./dist/huskycat validate .
./dist/huskycat setup-hooks
./dist/huskycat install  # Self-install to ~/.local/bin
```

**Characteristics**:
- PyInstaller single-file executable
- Embedded tools (shellcheck, hadolint, taplo)
- No Python environment required
- Optional container delegation when runtime available
- ~175-180MB binary size

**Entry Point**: `huskycat_main.py`

### 2. Container Execution (CI/CD)

```bash
# Complete toolchain, consistent environment
podman run --rm -v "$(pwd)":/workspace huskycat:local validate --all
docker run --rm -v "$(pwd)":/workspace $CONTAINER_REGISTRY:latest validate
```

**Characteristics**:
- Alpine 3.19 base image
- Multi-arch (amd64, arm64)
- All 15+ validators bundled
- Consistent environment across systems
- Container runtime required (podman or docker)

**Definition**: `ContainerFile`

### 3. UV Development Mode

```bash
# Fast iteration, local development
uv run python3 -m src.huskycat validate .
npm run dev -- --help
```

**Characteristics**:
- Direct Python module execution
- NPM script integration
- Fast iteration during development
- Optional container delegation

**Scripts**: `package.json`

### Execution Routing Logic

```python
# unified_validation.py
def is_available(self) -> bool:
    """Check validator availability in current context"""
    if self._is_running_in_container():
        # Inside container: check tool directly
        return tool_exists_locally()
    else:
        # On host: check container runtime available
        return container_runtime_exists()

def _execute_command(self, cmd: List[str], **kwargs):
    """Route execution: direct or container-delegated"""
    if self._is_running_in_container():
        # Direct execution inside container
        return subprocess.run(cmd, **kwargs)
    else:
        # Container-delegated execution from host
        container_cmd = self._build_container_command(cmd)
        return subprocess.run(container_cmd, **kwargs)
```

---

## CI/CD Pipeline

### Pipeline Stages

```
.gitlab-ci.yml (main)
  |
  +-- validate stage
  |     +-- container:build:amd64
  |     +-- container:build:arm64 (allow_failure)
  |
  +-- security stage
  |     +-- validate:basic
  |     +-- validate:yaml
  |     +-- SAST/Dependency scanning
  |
  +-- build stage
  |     +-- download:tools:{platform} (4 jobs)
  |     +-- container:build:manifest
  |     +-- validate:complete
  |
  +-- test stage
  |     +-- test:unit
  |     +-- test:mcp:server
  |
  +-- package stage
  |     +-- build:binary:linux-amd64
  |     +-- build:binary:linux-arm64
  |     +-- build:binary:darwin-arm64
  |     +-- verify:binary-size
  |     +-- checksums:generate
  |     +-- package:python (allow_failure)
  |
  +-- sign stage
  |     +-- binary:test:linux-amd64
  |     +-- binary:test:linux-arm64 (allow_failure)
  |     +-- binary:test:darwin-arm64 (allow_failure)
  |     +-- binary:smoke-test
  |     +-- sign:darwin-arm64 (macOS code signing)
  |
  +-- deploy stage
  |     +-- pages (MkDocs documentation)
  |     +-- release:create (on tags)
  |
  +-- scheduled stage
        +-- dependency updates
```

### Modular CI/CD Files

| File | Purpose | Key Jobs |
|------|---------|----------|
| `.gitlab-ci.yml` | Main pipeline | Stages, variables, container builds, tests |
| `.gitlab/ci/download-tools.yml` | Tool downloads | download:tools:{platform} (4 jobs) |
| `.gitlab/ci/build.yml` | Binary builds | build:binary:{platform} (3 jobs), verify:binary-size |
| `.gitlab/ci/binary-tests.yml` | Binary testing | binary:test:{platform}, binary:smoke-test |
| `.gitlab/ci/pages.yml` | Documentation | mkdocs:build, pages deployment |
| `.gitlab/ci/e2e-tests.yml` | E2E testing | (aspirational, not active) |
| `.gitlab/ci/scheduled-updates.yml` | Scheduled jobs | Dependency updates |

### Triggering Pipelines

```bash
# Trigger fresh pipeline
git commit --allow-empty -m "chore: trigger CI"
git push

# Check pipeline status (requires glab CLI)
glab ci status
glab ci view

# Retry failed jobs
glab ci retry <job-id>

# View job logs
glab ci trace container:build:amd64
```

### Key CI/CD Patterns

**Buildah VFS Storage Driver**:
```yaml
.container_build_template:
  variables:
    STORAGE_DRIVER: vfs  # Avoids user namespace requirements
  before_script:
    - buildah --storage-driver vfs login ...
  script:
    - buildah --storage-driver vfs build --platform=$PLATFORM ...
```

**Multi-Arch Container Builds**:
```yaml
container:build:amd64:
  variables:
    PLATFORM: linux/amd64
    ARCH: amd64

container:build:arm64:
  variables:
    PLATFORM: linux/arm64
    ARCH: arm64
  allow_failure: true  # No local ARM64 runner
```

**Allow Failure Strategy**:
```yaml
# Jobs that should not block pipeline
container:build:arm64:
  allow_failure: true  # No ARM64 runner available

package:python:
  allow_failure: true  # psutil build issues shouldn't block binaries

binary:test:linux-arm64:
  allow_failure: true  # ARM64 runners may not be available

binary:test:darwin-arm64:
  allow_failure: true  # macOS runners may not be available
```

---

## MCP Integration

### HuskyCat MCP Server

**Protocol**: JSON-RPC 2.0 over stdio
**File**: `src/huskycat/mcp_server.py`

**Starting the Server**:
```bash
./dist/huskycat mcp-server
npm run mcp:server
uv run python3 -m src.huskycat mcp-server
```

**Claude Code Configuration**:
```json
{
  "mcpServers": {
    "huskycat": {
      "command": "/path/to/huskycat",
      "args": ["mcp-server"],
      "transport": "stdio"
    }
  }
}
```

**Exposed Tools**:

| Tool Name | Description | Arguments |
|-----------|-------------|-----------|
| `validate` | Validate files/directories | `path`, `fix` (optional) |
| `validate_staged` | Validate git staged files | `fix` (optional) |
| `validate_black` | Run black formatter | `path`, `fix` (optional) |
| `validate_ruff` | Run ruff linter | `path`, `fix` (optional) |
| `validate_mypy` | Run mypy type checker | `path` |
| `validate_flake8` | Run flake8 style checker | `path` |
| `validate_shellcheck` | Run shellcheck | `path` |
| `validate_hadolint` | Run hadolint | `path` |
| `validate_yamllint` | Run yamllint | `path` |
| `validate_isort` | Run isort import sorter | `path`, `fix` (optional) |
| `validate_taplo` | Run taplo TOML formatter | `path`, `fix` (optional) |
| `validate_bandit` | Run bandit security linter | `path` |
| `validate_ansible_lint` | Run ansible-lint | `path` |
| `validate_terraform` | Run terraform validate | `path` |
| `validate_gitlab_ci` | Validate GitLab CI config | `path` |

### Global MCP Ecosystem (from crush-dots)

HuskyCat's MCP server is part of a broader MCP ecosystem deployed by the `crush-dots` Ansible infrastructure.

**Source of Truth**: `../crush-dots/vars/mcp_registry.yml`

**Enabled Production MCP Servers**:

| Server | Package | Purpose | API Key |
|--------|---------|---------|---------|
| **perplexity-pro** | @perplexity-ai/mcp-server | Sonar Pro web search (200k context) | Yes (PERPLEXITY_API_KEY) |
| **perplexity-reasoning** | @perplexity-ai/mcp-server | Sonar Reasoning Pro (complex tasks) | Yes (PERPLEXITY_API_KEY) |
| **chrome-devtools** | chrome-devtools-mcp@latest | Browser automation via DevTools Protocol | No (requires Node.js 22+) |
| **wikipedia** | mcp/wikipedia-mcp (Docker) | Wikipedia article lookup | No |
| **fetch** | mcp/fetch (Docker) | Web content retrieval | No |
| **duckduckgo** | mcp/duckduckgo (Docker) | Privacy-focused web search | No |
| **arxiv** | mcp/arxiv-mcp-server (Docker) | Academic paper search | No |
| **filesystem** | @modelcontextprotocol/server-filesystem | Project file access (~/ crush-projects) | No |

**Disabled/Not Used** (explicitly excluded from deployments):
- **flow-nexus**: Cloud-based orchestration, not needed for local deployments
- **claude-flow (stable)**: Outdated v2.0.0, superseded by alpha version
- **agentic-payments**: Payment processing, not needed for development
- **perplexity-ask (community)**: Replaced by official @perplexity-ai servers

**Configuration Locations**:
- Global: `~/.config/mcp/mcp.json` (generated by crush-dots Ansible)
- Project: `.mcp.json` (project-specific overrides)

---

## Troubleshooting

### Binary Issues

**Binary not found**:
```bash
# Build binary
npm run build:binary

# Check binary exists
ls -lah dist/bin/

# Make executable
chmod +x dist/bin/huskycat-*
```

**Binary fails to execute**:
```bash
# Check file type
file dist/bin/huskycat-linux-amd64

# Check for missing libraries (Linux)
ldd dist/bin/huskycat-linux-amd64

# Check macOS signing (Darwin)
codesign -dv dist/bin/huskycat-darwin-arm64
```

**Tools not extracted**:
```bash
# Check extraction directory
ls -lah ~/.huskycat/tools/

# Force re-extraction
rm -rf ~/.huskycat/tools/
./dist/huskycat --version  # Triggers extraction
```

**Binary size verification**:
```bash
# Check size (target: ~175-180MB)
ls -lah dist/bin/huskycat-*

# Verify embedded tools
./dist/huskycat status
```

### Container Issues

**Container not found**:
```bash
# Build container locally
npm run container:build

# Pull from registry
podman pull registry.gitlab.com/tinyland/ai/huskycat:latest-amd64
```

**Container runtime not available**:
```bash
# Check for podman
podman --version

# Check for docker
docker --version

# Install podman (macOS)
brew install podman
podman machine init
podman machine start
```

**Permission errors**:
```bash
# Check file ownership
ls -lah .

# Fix ownership
chown -R $(id -u):$(id -g) .

# Check container user
podman run --rm huskycat:local whoami
```

### Mode Detection Issues

**Wrong mode detected**:
```bash
# Check detected mode
./dist/huskycat status

# Force specific mode
./dist/huskycat --mode cli validate .
./dist/huskycat --mode pipeline validate . > results.json

# Check environment
env | grep -E "(CI|GIT_|HUSKYCAT)"
```

**MCP server not starting**:
```bash
# Check mode detection
./dist/huskycat --mode mcp mcp-server

# Check stdio communication
echo '{"jsonrpc":"2.0","method":"initialize","id":1}' | ./dist/huskycat mcp-server 2>&1

# Check logs (stderr)
./dist/huskycat mcp-server 2> mcp-server.log
cat mcp-server.log
```

### CI/CD Issues

**Buildah user namespace errors**:
```yaml
# Add --storage-driver vfs to all buildah commands
.container_build_template:
  variables:
    STORAGE_DRIVER: vfs
  before_script:
    - buildah --storage-driver vfs login ...
  script:
    - buildah --storage-driver vfs build ...
```

**ARM64 build failures**:
```yaml
# Mark as allow_failure until ARM64 runner available
container:build:arm64:
  allow_failure: true
```

**Binary tests skipped**:
```yaml
# Add rules to binary test jobs
binary:test:linux-amd64:
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
    - if: $CI_COMMIT_TAG
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

**Python packaging blocks pipeline**:
```yaml
# Mark as allow_failure
package:python:
  allow_failure: true
```

**Registry authentication failed**:
```bash
# Verify CI/CD variables are set:
# - CI_REGISTRY_USER
# - CI_REGISTRY_PASSWORD

# Test login manually
buildah --storage-driver vfs login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
```

---

## Pattern Library

### PyInstaller Bundling

**Add embedded tools**:
```bash
uv run pyinstaller --onefile \
  --name huskycat-$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m) \
  --add-data "src:src" \
  --add-binary "dist/tools/linux-amd64/shellcheck:tools/" \
  --add-binary "dist/tools/linux-amd64/hadolint:tools/" \
  --add-binary "dist/tools/linux-amd64/taplo:tools/" \
  huskycat_main.py
```

**Add hidden imports**:
```bash
uv run pyinstaller --onefile \
  --hidden-import=networkx \
  --hidden-import=psutil \
  huskycat_main.py
```

**Optimize binary size**:
```bash
# UPX compression (optional)
upx --best --lzma dist/bin/huskycat-linux-amd64

# Exclude unnecessary modules
uv run pyinstaller --onefile \
  --exclude-module=matplotlib \
  --exclude-module=pandas \
  huskycat_main.py
```

### Multi-Arch Container Builds

**Buildah multi-arch pattern**:
```bash
# Build amd64
buildah --storage-driver vfs build --platform=linux/amd64 --layers \
  -f ContainerFile -t huskycat:amd64 .

# Build arm64
buildah --storage-driver vfs build --platform=linux/arm64 --layers \
  -f ContainerFile -t huskycat:arm64 .

# Create manifest
buildah manifest create huskycat:latest
buildah manifest add huskycat:latest huskycat:amd64
buildah manifest add huskycat:latest huskycat:arm64

# Push manifest
buildah manifest push --all huskycat:latest docker://registry/huskycat:latest
```

### Non-Blocking Hooks

**Enable non-blocking mode**:
```bash
# Per-repository (recommended)
git config --local huskycat.nonblocking true

# Global (all repositories)
git config --global huskycat.nonblocking true

# Verify
git config --get huskycat.nonblocking  # Expected: true
```

**How it works**:
1. Parent process returns in <100ms (commit proceeds immediately)
2. Child process runs comprehensive validation in background (15+ tools)
3. Real-time TUI progress display
4. Results cached in `.huskycat/runs/`
5. Previous failure checking (prompts before commit if last run failed)

**Result caching structure**:
```
.huskycat/runs/
  +-- pids/12345.json          # Running process
  +-- logs/20240315_142530.log # Validation output
  +-- 20240315_142530.json     # Run result
  +-- last_run.json            # Most recent pointer
```

### Parallel Execution

**Dependency graph** (from `src/huskycat/core/parallel_executor.py`):
```python
dependencies = {
    "mypy": ["black", "isort"],
    "flake8": ["black", "isort"],
    "bandit": ["black"],
    "ansible-lint": ["yamllint"],
    "gitlab-ci": ["yamllint"],
    "helm-lint": ["yamllint"],
}

# Execution levels (topological sort)
levels = [
    # Level 0: No dependencies (9 tools)
    ["black", "ruff", "isort", "yamllint", "shellcheck",
     "hadolint", "taplo", "autoflake", "chapel-format"],

    # Level 1: Depends on Level 0 (6 tools)
    ["mypy", "flake8", "bandit", "ansible-lint",
     "gitlab-ci", "helm-lint"],
]
```

**Result**: 7.5x speedup (4s vs 30s for 15 tools)

---

## Infrastructure Reference

### File Structure

```
huskycats-bates/
  +-- src/huskycat/              # Source code
  |     +-- __main__.py          # CLI entry point
  |     +-- mcp_server.py        # MCP server
  |     +-- unified_validation.py # Validation engine
  |     +-- core/                # Core modules
  |           +-- adapters/      # Product mode adapters (6 files)
  |           +-- mode_detector.py # Mode detection
  |           +-- factory.py     # Command factory
  |           +-- process_manager.py # Process management
  |           +-- tool_extractor.py # Tool extraction
  |           +-- parallel_executor.py # Parallel execution
  |           +-- tui.py         # Terminal UI
  |
  +-- huskycat_main.py           # Binary entry point
  +-- ContainerFile              # Container definition
  +-- .gitlab-ci.yml             # Main CI config
  +-- .gitlab/ci/                # Modular CI files (9 files)
  +-- .claude/                   # Claude Code integration
  |     +-- commands/            # Slash commands
  |     +-- agents/              # Agent templates
  |     +-- helpers/             # Shell scripts
  +-- docs/                      # Documentation
  |     +-- SPRINT_PLAN.md       # Sprint planning
  |     +-- architecture/        # Architecture docs
  +-- tests/                     # Test suite (268+ tests)
  +-- scripts/                   # Utility scripts
  |     +-- download_tools.py    # Tool downloads
  |     +-- verify_binary.sh     # Binary verification
  +-- pyproject.toml             # Python package config
  +-- package.json               # NPM scripts
  +-- CLAUDE.md                  # Claude Code instructions
  +-- CRUSH.md                   # This file
```

### Key Files Reference

| File | Purpose | Critical Sections |
|------|---------|------------------|
| `src/huskycat/__main__.py` | CLI entry | Mode detection, argument parsing |
| `src/huskycat/core/mode_detector.py` | Mode detection | Priority order logic |
| `src/huskycat/core/factory.py` | Command factory | Adapter creation |
| `src/huskycat/core/adapters/*.py` | Product modes | Mode-specific behavior |
| `src/huskycat/mcp_server.py` | MCP integration | JSON-RPC handling |
| `src/huskycat/unified_validation.py` | Validation engine | Tool execution routing |
| `huskycat_main.py` | Binary wrapper | PyInstaller entry |
| `ContainerFile` | Container def | Multi-arch toolchain |
| `.gitlab-ci.yml` | Main pipeline | Stages, variables |
| `.gitlab/ci/build.yml` | Binary builds | PyInstaller config |
| `docs/SPRINT_PLAN.md` | Sprint planning | Roadmap, milestones |
| `pyproject.toml` | Python config | Dependencies, metadata |

### Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `HUSKYCAT_MODE` | Force product mode | `export HUSKYCAT_MODE=cli` |
| `UV_CACHE_DIR` | UV cache location | `$CI_PROJECT_DIR/.cache/uv` |
| `PIP_CACHE_DIR` | Pip cache location | `$CI_PROJECT_DIR/.cache/pip` |
| `HYPOTHESIS_PROFILE` | Hypothesis config | `export HYPOTHESIS_PROFILE=ci` |
| `CI` | CI environment | Set by GitLab CI |
| `GITLAB_CI` | GitLab CI | Set by GitLab CI |
| `GITHUB_ACTIONS` | GitHub Actions | Set by GitHub |
| `GIT_*` | Git environment | Set by git hooks |
| `PYTHONPATH` | Python module path | `$CI_PROJECT_DIR/src` |

### Container Registry

**Production Images**:
```
registry.gitlab.com/tinyland/ai/huskycat:latest-amd64
registry.gitlab.com/tinyland/ai/huskycat:latest-arm64
registry.gitlab.com/tinyland/ai/huskycat:latest  # Manifest
registry.gitlab.com/tinyland/ai/huskycat:<commit-sha>-amd64
registry.gitlab.com/tinyland/ai/huskycat:<commit-sha>-arm64
```

**Pull Commands**:
```bash
# Latest (multi-arch manifest)
podman pull registry.gitlab.com/tinyland/ai/huskycat:latest

# Specific architecture
podman pull registry.gitlab.com/tinyland/ai/huskycat:latest-amd64

# Specific commit
podman pull registry.gitlab.com/tinyland/ai/huskycat:528503d-amd64
```

### Binary Artifacts

**Platforms**:
- linux-amd64 (~175MB)
- linux-arm64 (~170MB)
- darwin-arm64 (~180MB)

**Embedded Tools** (all platforms):
- shellcheck
- hadolint
- taplo

**Download Locations**:
- GitLab artifacts (1 month expiry)
- GitLab Releases (on tags)

---

## Performance Reference

### Binary vs Container Execution

| Metric | Binary (Embedded) | Binary (Container) | Container Only |
|--------|-------------------|-------------------|----------------|
| Startup | ~100ms | ~200ms | ~500ms |
| Tool Execution | 0.42s | 1.87s | 1.87s |
| Speedup | 1.0x (baseline) | 4.5x slower | 4.5x slower |
| Dependencies | None | podman/docker | podman/docker |

### Non-Blocking vs Blocking Hooks

| Metric | Blocking | Non-Blocking |
|--------|----------|--------------|
| Commit Time | 5-30s | <100ms |
| Validation Time | 5-30s | 10-30s (background) |
| Tools Run | 4 (fast) | 15+ (all) |
| User Experience | Poor (blocking) | Excellent (immediate) |

### Parallel vs Sequential Execution

| Metric | Sequential | Parallel |
|--------|------------|----------|
| Execution Time | ~30s | ~4s |
| Speedup | 1.0x (baseline) | 7.5x |
| Worker Processes | 1 | 8 |
| Tools Run | 15+ | 15+ |

---

## Integration Protocols

### MCP (Claude Code, OpenCode)

**Current**: Fully implemented
**Protocol**: JSON-RPC 2.0 over stdio
**Tools**: All validators exposed
**File**: `src/huskycat/mcp_server.py`

### ACP (JetBrains) - Future

**Status**: Planned
**Protocol**: ACP (Agent Communication Protocol)
**Use Case**: JetBrains IDE integration

### LSP (All Editors) - Future

**Status**: Planned
**Protocol**: Language Server Protocol
**Use Case**: VS Code, Neovim, Emacs integration

---

## Recent Analysis Findings

### Sprint 10-11 Completion (Merged 4ffe953)

**Features Delivered**:
- Non-blocking git hooks (<100ms commit time)
- Fat binaries with embedded tools (175-180MB, 3 tools)
- Parallel execution engine (7.5x speedup)
- TUI progress display
- 268 comprehensive tests added

### CI/CD Infrastructure (Past 3 Weeks)

**Fixes Applied**:
- Buildah VFS storage driver (commits 528503d, 07c4b37)
- Binary test path corrections (commit 0e835d1)
- ARM64 allow_failure configuration (commit 501a610)
- Python package allow_failure (commit 4446fb6)
- Runner infrastructure optimizations

### Critical Issues Identified

1. **ARM64 Runner Availability**: No local ARM64 runner - jobs marked allow_failure
2. **Python Packaging**: psutil build issues on some platforms - marked allow_failure
3. **macOS Intel**: GitLab SaaS only provides ARM64 runners - no Intel builds

### Recommended Actions

1. **For Developers**:
   - Enable non-blocking hooks: `git config --local huskycat.nonblocking true`
   - Use binary execution when possible (faster, no dependencies)
   - Run `npm run validate` before commits if not using hooks

2. **For CI/CD**:
   - Always use `--storage-driver vfs` with buildah
   - Mark ARM64 and macOS jobs as `allow_failure: true`
   - Use container image for test consistency

3. **For MCP Integration**:
   - Use HuskyCat MCP server for Claude Code validation
   - Configure in `~/.config/mcp/mcp.json` or project `.mcp.json`
   - Leverage perplexity-pro and chrome-devtools from global MCP ecosystem

---

## Validation Tools Reference

### Python Tools

| Tool | Purpose | Auto-Fix | Container | Binary |
|------|---------|----------|-----------|--------|
| black | Code formatter | Yes | Yes | No |
| ruff | Fast linter | Yes | Yes | No |
| flake8 | Style checker | No | Yes | No |
| mypy | Type checker | No | Yes | No |
| pylint | Comprehensive linter | No | Yes | No |
| bandit | Security linter | No | Yes | No |
| isort | Import sorter | Yes | Yes | No |
| autoflake | Remove unused imports | Yes | Yes | No |

### Shell Tools

| Tool | Purpose | Auto-Fix | Container | Binary |
|------|---------|----------|-----------|--------|
| shellcheck | Shell script analysis | No | Yes | **Yes** |

### Docker Tools

| Tool | Purpose | Auto-Fix | Container | Binary |
|------|---------|----------|-----------|--------|
| hadolint | Dockerfile linter | No | Yes | **Yes** |

### Config Tools

| Tool | Purpose | Auto-Fix | Container | Binary |
|------|---------|----------|-----------|--------|
| yamllint | YAML validation | No | Yes | No |
| taplo | TOML formatter | Yes | Yes | **Yes** |

### IaC Tools

| Tool | Purpose | Auto-Fix | Container | Binary |
|------|---------|----------|-----------|--------|
| ansible-lint | Ansible playbook linter | No | Yes | No |
| terraform | Terraform validation | Yes | Yes | No |

### Tool Selection by Mode

| Mode | Tool Set | Count |
|------|----------|-------|
| Git Hooks (Blocking) | black, ruff, mypy, flake8 | 4 |
| Git Hooks (Non-Blocking) | All | 15+ |
| CI | All | 15+ |
| CLI | Configured (.huskycat.yaml) | Variable |
| Pipeline | All | 15+ |
| MCP | All | 15+ |

---

**Last Updated**: 2025-01-15
**Maintainer**: Jess Sullivan <jess@tinyland.ai>
**Repository**: https://gitlab.com/tinyland/ai/huskycat
