# Claude Code Instructions for HuskyCat Project

## Sprint Plan Reference

See `docs/SPRINT_PLAN.md` for comprehensive development roadmap covering:
- **Product Mode Architecture**: 5 distinct modes (Git Hooks, CI, CLI, Pipeline, MCP)
- **Execution Modes**: Container vs Binary
- **Auto-Fix Framework**: Confidence tiers, mode-specific behavior
- **Sprint 0-8**: From architecture foundation to auto-fix implementation

## License

HuskyCat is licensed under **Apache-2.0** for libre sales compatibility.

GPL tools (shellcheck, hadolint, yamllint) are isolated in a separate
`gpl-sidecar/` component that communicates via IPC.

## CRITICAL: Git Commit Rules

**Prefer using validation hooks, but `--no-verify` is acceptable during development.**

HuskyCat IS a verification and validation project. We should use our own validation tools, but strict MyPy errors may require bypassing hooks temporarily.

### Preferred approach:
```bash
git commit -m "message"  # Let hooks run
```

### During development with validation issues:
```bash
git commit --no-verify -m "message"  # Acceptable when MyPy blocks commits
git push --no-verify  # Acceptable when validation is too strict
```

## Product Mode Architecture

HuskyCat operates in **5 distinct product modes**, each with different requirements:

```
HUSKYCAT PRODUCT MODES

GIT HOOKS     CI        CLI       PIPELINE
  MODE       MODE      MODE        MODE
    v          v         v           v
            MCP SERVER MODE
        (AI assistant integration)
                v
    UNIFIED VALIDATION ENGINE
    (shared validation logic, tool execution)
```

### Mode 1: Git Hooks Mode
**Purpose**: Pre-commit/pre-push validation
- **Speed**: Fast tools only (black, ruff, mypy)
- **Output**: Minimal (errors only), silent on success
- **Interactive**: Auto-detect TTY for prompts
- **Exit codes**: 0=pass, 1=fail (blocks commit)

### Mode 2: CI Mode
**Purpose**: Pipeline integration for MR/PR checks
- **Tools**: ALL validators (comprehensive)
- **Output**: JUnit XML for CI artifacts
- **Interactive**: Never (fully automated)
- **Exit codes**: 0=pass, non-zero=fail

### Mode 3: CLI Mode
**Purpose**: Developer running validation manually
- **Tools**: Configured per .huskycat.yaml
- **Output**: Rich colored terminal output
- **Interactive**: Prompts enabled, progress bars
- **Verbose options**: -v, -vv, -vvv

### Mode 4: Pipeline Mode
**Purpose**: Part of larger build/lint toolchain
- **Tools**: All available
- **Output**: Machine-readable JSON
- **Interactive**: Never (scriptable)
- **stdin/stdout**: Composable with pipes

### Mode 5: MCP Server Mode
**Purpose**: AI assistant integration (Claude Code)
- **Protocol**: JSON-RPC 2.0 over stdio
- **Tools**: All validators exposed as MCP tools
- **Interactive**: Never
- **Transport**: stdin/stdout

### Mode Detection

Mode is auto-detected based on environment:

```python
# Priority order:
1. --mode flag (explicit override)
2. HUSKYCAT_MODE environment variable
3. MCP server command detection (mcp-server in argv)
4. Git hooks env vars (GIT_AUTHOR_NAME, GIT_INDEX_FILE)
5. CI env vars (CI, GITLAB_CI, GITHUB_ACTIONS, etc.)
6. TTY detection (no TTY = pipeline mode)
7. Default: CLI mode
```

### Critical Files & Responsibilities
- **`src/huskycat/__main__.py`** → CLI interface with mode detection
- **`src/huskycat/core/mode_detector.py`** → ProductMode enum and detect_mode()
- **`src/huskycat/core/adapters/`** → Mode-specific adapters (5 files)
- **`src/huskycat/core/factory.py`** → Command factory pattern
- **`src/huskycat/unified_validation.py`** → Validation engine
- **`src/huskycat/mcp_server.py`** → MCP stdio protocol
- **`src/huskycat/integrations/`** → External tool integrations (RemoteJuggler)
- **`huskycat_main.py`** → Binary entry point wrapper

## Tool Architecture

### Bundled Tools (Apache-2.0 compatible)
- ruff (MIT) - Python linting + formatting
- mypy (MIT) - Type checking
- bandit (Apache) - Security scanning
- dockerlint (MIT) - Dockerfile linting
- yaml_lint (Apache) - YAML linting (5 rules, clean-room)
- taplo (MIT) - TOML formatting

### GPL Tools (Container/Sidecar only)
- shellcheck (GPL-3.0) - Shell script analysis
- hadolint (GPL-3.0) - Comprehensive Dockerfile linting
- yamllint (GPL-3.0) - Comprehensive YAML linting

### Linting Modes
- `FAST`: Binary-only, Apache/MIT tools (git hooks, quick validation)
- `COMPREHENSIVE`: Includes GPL tools via sidecar (CI, thorough validation)

Set via: `--mode fast` or `HUSKYCAT_LINTING_MODE=comprehensive`

## Build System: Multi-Modal Command Interface

HuskyCat supports multiple execution modes optimized for different use cases:

### 1. Binary Execution (Preferred for Git Hooks)
```bash
# Fast binary execution - single file, no Python env needed
./dist/huskycat validate --staged
./dist/huskycat setup-hooks
./dist/huskycat install  # Self-installs to ~/.local/bin
./dist/huskycat status
```

### 2. NPM-Mediated Development Commands
```bash
# Development
npm run dev                    # Run HuskyCat CLI
npm run validate              # Validate current directory
npm run validate:ci           # Validate CI configuration
npm run hooks:install         # Install git hooks
npm run mcp:server           # Start MCP server
npm run clean                # Clean cache
npm run status               # Show HuskyCat status

# Building & Testing
npm run container:build       # Build validation container
npm run container:test        # Test container
npm run build:binary         # Create PyInstaller binary
npm run test:unit            # Run unit tests

# Documentation
npm run docs:build          # Build MkDocs
npm run docs:serve          # Serve docs locally
```

### 3. Direct UV Commands
```bash
uv run python -m src.huskycat --help  # Direct CLI access
uv run python -m src.huskycat validate  # Run validation
uv run python -m src.huskycat --mode cli status  # Force CLI mode
uv run python -m src.huskycat --json validate .  # Force JSON output
```

## CLI Commands Reference

```bash
# Core validation
huskycat validate                # Validate current directory
huskycat validate --staged       # Validate staged files only
huskycat validate --all          # Validate all files
huskycat validate --fix          # Auto-fix issues
huskycat validate --json         # Force JSON output

# Mode override
huskycat --mode ci validate      # Force CI mode (JUnit XML)
huskycat --mode pipeline validate  # Force pipeline mode (JSON)
huskycat --mode git_hooks validate  # Force git hooks mode

# Setup
huskycat install                 # Self-install binary to ~/.local/bin
huskycat setup-hooks             # Install git hooks
huskycat update-schemas          # Update validation schemas

# Advanced
huskycat mcp-server              # Start MCP server (stdio)
huskycat ci-validate             # Validate CI configuration
huskycat auto-devops             # Validate Helm/K8s manifests
huskycat status                  # Show configuration status
huskycat clean                   # Clean cache
```

## Execution Models

See [docs/architecture/execution-models.md](docs/architecture/execution-models.md) for complete details.

### Container Architecture

- `ContainerFile.wrapper` - Thin ~20MB container with fat binary
- `ContainerFile.gpl-sidecar` - GPL tools container (~50MB)
- Original `ContainerFile` - Legacy fat container (deprecated)

### Three Execution Models:

1. **Binary Execution** (`huskycat_main.py:1-27`)
   - PyInstaller single-file executable
   - Optional container delegation when runtime available
   - Fast startup (~100ms)
   - Implementation: `unified_validation.py:85-170`

2. **Container Execution** (`ContainerFile.wrapper:1-153`)
   - Thin wrapper container with fat binary (~20MB)
   - Multi-arch support (amd64, arm64)
   - Container runtime required (podman or docker)
   - Implementation: `.gitlab-ci.yml:158-218`

3. **UV Development Mode** (`package.json:8-38`)
   - npm scripts + UV package manager
   - Local Python environment
   - Development and testing
   - Optional container delegation

### Execution Routing Logic

```python
# unified_validation.py:85-170
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

## MCP Server Integration

### HuskyCat MCP Server

HuskyCat exposes validation tools via MCP protocol for Claude Code:

```bash
# Start MCP server (stdio mode)
huskycat mcp-server

# Add to Claude Code
claude mcp add huskycat -- huskycat mcp-server
```

**MCP Tools Exposed** (28 total):
- `validate` - Validate files/directories
- `validate_staged` - Validate git staged files
- `validate_black`, `validate_mypy`, etc. - Individual tool validators
- `juggler_*` - Git identity tools (when RemoteJuggler available)

### Global MCP Ecosystem (from crush-dots)

HuskyCat's MCP server is part of a broader MCP ecosystem deployed by the `crush-dots` Ansible infrastructure.

**Source of Truth**: `../crush-dots/vars/mcp_registry.yml`

**Production MCP Servers** (enabled):
- **perplexity-pro**: Sonar Pro web search (200k context, requires PERPLEXITY_API_KEY)
- **perplexity-reasoning**: Sonar Reasoning Pro for complex tasks
- **chrome-devtools**: Browser automation via DevTools Protocol
- **wikipedia**: Wikipedia article lookup (Docker-based)
- **duckduckgo**: Privacy-focused web search (Docker-based)
- **arxiv**: Academic paper search (Docker-based)
- **filesystem**: Project file access (~/ crush-projects)

**Configuration**: Ansible role `roles/claude-code/` generates `~/.config/mcp/mcp.json` from registry.

**Disabled Servers** (not deployed):
- flow-nexus (cloud-based, not needed locally)
- claude-flow stable (outdated, superseded by alpha)
- agentic-payments (not needed for development)

### RemoteJuggler Integration

HuskyCat integrates with [RemoteJuggler](https://gitlab.com/tinyland/ai/gitlab-switcher) for git identity management. When RemoteJuggler is available, HuskyCat exposes 6 additional MCP tools for identity switching.

**Integration Location**: `src/huskycat/integrations/remote_juggler.py`

**RemoteJuggler MCP Tools** (exposed as `juggler_*`):
- `juggler_list_identities` - List all configured git identities
- `juggler_detect_identity` - Detect the appropriate identity for a repository
- `juggler_switch` - Switch to a different git identity
- `juggler_status` - Get current git identity status
- `juggler_validate` - Validate SSH/API credentials for current identity
- `juggler_gpg_status` - Get GPG signing status for current identity

**Configuration**: `~/.huskycat/integrations/remote-juggler.yaml`

```yaml
version: "1.0"
enabled: true
binary_path: "~/.local/bin/remote-juggler"  # or auto-detect
integration_mode: "cli"  # cli | mcp | config

hooks:
  pre_commit:
    detect_identity: true
    warn_on_mismatch: true
    auto_switch: false
  pre_push:
    validate_gpg: true
    validate_credentials: true

mcp:
  proxy_tools: true
  tool_prefix: "juggler_"
```

**Git Hooks Integration**:
- Pre-commit: Detects expected identity and warns on mismatch
- Pre-push: Validates GPG signing and credentials

**Total MCP Tools**: 28 (22 HuskyCat + 6 RemoteJuggler)

## Repository Standards

- Python code uses UV package manager
- All code must pass Black, Flake8, MyPy, and Ruff checks
- GitLab CI must validate with `npm run validate:ci`
- Tests use pytest with hypothesis for property-based testing
- Documentation in MkDocs format
- Container builds with Podman/Docker using ContainerFile

## Quick Reference: Working Commands

**Verified working commands:**

```bash
# Basic operations
npm run dev -- --help            # Show help
npm run dev -- status            # Show status
npm run validate                 # Validate current directory
npm run validate:ci              # Validate .gitlab-ci.yml

# Mode-specific output
npm run dev -- --mode cli status       # Rich terminal output
npm run dev -- --mode pipeline status  # JSON output
npm run dev -- --json validate         # Shorthand for pipeline mode

# Build and test
npm run build:binary             # Build PyInstaller binary
npm run container:build          # Build validation container
npm run test:unit                # Run unit tests
uv run pytest tests/test_mode_detection.py -v  # Run mode tests

# Documentation
npm run docs:build               # Build MkDocs
npm run docs:serve               # Serve locally
```

## Architecture Deep Dive

See [docs/architecture/](docs/architecture/) for comprehensive documentation:
- [Execution Models](docs/architecture/execution-models.md) - Binary, Container, UV modes
- [Product Modes](docs/architecture/product-modes.md) - 5 modes with code references

### Adapter Pattern

Five mode-specific adapters in `src/huskycat/core/adapters/`:
- `git_hooks.py` - Fast subset, minimal output, fail-fast
- `ci.py` - JUnit XML, comprehensive tools, never interactive
- `cli.py` - Interactive, colored output, progress bars
- `pipeline.py` - JSON output, machine-readable, scriptable
- `mcp.py` - JSON-RPC 2.0, AI integration, stdio transport

Factory pattern routes commands: `factory.py:1-200` → adapter selection

### Mode Detection Priority

```python
# mode_detector.py:30-82
def detect_mode() -> ProductMode:
    """Priority: flag → env → command → git → CI → TTY → default"""
    if "--mode" in sys.argv:
        return ProductMode(parse_flag())
    if env_mode := os.getenv("HUSKYCAT_MODE"):
        return ProductMode(env_mode)
    if "mcp-server" in sys.argv:
        return ProductMode.MCP
    git_env_count = sum(1 for k in os.environ if k.startswith("GIT_"))
    if git_env_count >= 2:
        return ProductMode.GIT_HOOKS
    # ... continues for CI, Pipeline, default CLI
```

## Current Status

- **Execution Models**: Binary, Container, UV Development all operational
- **Product Modes**: All 5 modes implemented with adapters (Sprint 0 complete)
- **Multi-Arch Support**: amd64 and arm64 container builds passing
- **Test Suite**: Unit tests passing, E2E tests operational
- **CI Pipeline**: 22/22 jobs passing
- **MCP Tools**: 28 tools (22 validators + 6 RemoteJuggler identity tools)
- **Desktop Integration**: Icons and .desktop files created in `assets/`

## Remember

This project is about code quality and validation. We must demonstrate best practices by using our own tools consistently.

**For Future Agents**: The **5 product modes** architecture is now implemented (Sprint 0). Each mode has distinct output format, interactivity, and tool selection. Use mode detection, don't hardcode behaviors!
