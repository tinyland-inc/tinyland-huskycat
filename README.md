# HuskyCat - Universal Code Validation Platform

[![Pipeline](https://gitlab.com/tinyland/ai/huskycat/badges/main/pipeline.svg)](https://gitlab.com/tinyland/ai/huskycat/-/pipelines)

## Quick Install

One-line install (macOS and Linux):
```bash
curl -fsSL https://huskycat-570fbd.gitlab.io/install.sh | bash
```

With Claude Code MCP integration:
```bash
HUSKYCAT_WITH_CLAUDE=1 curl -fsSL https://huskycat-570fbd.gitlab.io/install.sh | bash
```

Manual downloads: [Binary Downloads](https://huskycat-570fbd.gitlab.io/downloads/)

## Overview

HuskyCat is a code validation platform that provides:

- **Non-Blocking Git Hooks** - Commits complete quickly while validation runs in background
- **Fat Binary Distribution** - Standalone binaries with embedded validation tools
- **20 Validation Tools** - Black, MyPy, Ruff, shellcheck, hadolint, yamllint, and more
- **MCP Server Integration** - Exposes validation as AI-callable tools for Claude Code
- **Multi-Modal Execution** - Binary, Container, or UV development modes
- **Auto-Fix Support** - Automatically fix issues where possible

## Product Modes

HuskyCat operates in 5 distinct modes, each optimized for different use cases:

| Mode | Output | Tools | Interactive | Use Case |
|------|--------|-------|-------------|----------|
| **Git Hooks (Blocking)** | Minimal | Fast subset (4) | TTY-dependent | Traditional pre-commit validation |
| **Git Hooks (Non-Blocking)** | TUI progress | All (20) | Background | Fast commits with comprehensive validation |
| **CI Mode** | JUnit XML | All (20) | Never | GitLab/GitHub pipeline integration |
| **CLI Mode** | Colored terminal | Configured | Yes | Interactive development |
| **Pipeline Mode** | JSON | All (20) | Never | Scriptable automation |
| **MCP Server** | JSON-RPC | All (20) | Never | AI assistant integration |

### Mode Detection Priority

Mode is auto-detected based on environment:

1. `--mode` flag (explicit override)
2. `HUSKYCAT_MODE` environment variable
3. `mcp-server` command detection
4. Git hooks environment variables (`GIT_AUTHOR_NAME`, `GIT_INDEX_FILE`)
5. CI environment variables (`CI`, `GITLAB_CI`, `GITHUB_ACTIONS`)
6. TTY detection (no TTY = pipeline mode)
7. Default: CLI mode

See [docs/architecture/product-modes.md](docs/architecture/product-modes.md) for implementation details.

## Execution Models

HuskyCat supports three execution models with automatic tool discovery:

### 1. Binary Execution

PyInstaller single-file executable with optional embedded tools:

```bash
./huskycat validate --staged    # Direct execution
./huskycat setup-hooks          # Install git hooks
./huskycat install              # Self-install to ~/.local/bin
```

Tool resolution priority:
1. Bundled tools in `~/.huskycat/tools/` (extracted from fat binary)
2. System PATH
3. Container delegation (if runtime available)

### 2. Container Execution

Alpine-based multi-arch images with complete toolchain:

```bash
podman run --rm -v "$(pwd)":/workspace huskycat:local validate --all
```

Supports amd64 and arm64 architectures. Container runtime (podman or docker) required.

### 3. UV Development Mode

For development and testing:

```bash
npm run validate                # Validate current directory
npm run validate:staged         # Validate staged files
uv run python -m src.huskycat   # Direct module invocation
```

### Container Chaining

When running on host without local tools, HuskyCat delegates to containers:

```
Host Binary → Tool Check → Not Found → Container Runtime Check → Delegate to Container
```

This allows the binary to work on systems without validation tools installed, transparently routing execution through containers when needed.

See [docs/architecture/execution-models.md](docs/architecture/execution-models.md) for details.

## CLI Reference

### Core Commands

```bash
# Validation
huskycat validate                  # Validate current directory
huskycat validate --staged         # Validate git staged files
huskycat validate --all            # Validate all files in project
huskycat validate --fix            # Auto-fix issues where possible
huskycat validate --json           # Output JSON (pipeline mode)

# Git Hooks
huskycat setup-hooks               # Install git hooks to .git/hooks/
huskycat install                   # Self-install binary to ~/.local/bin

# CI/CD
huskycat ci-validate FILE          # Validate GitLab CI configuration
huskycat auto-devops               # Validate Helm/K8s manifests

# MCP Server
huskycat mcp-server                # Start MCP server (stdio)

# Utilities
huskycat status                    # Show installation and configuration
huskycat update-schemas            # Update validation schemas
huskycat clean                     # Clean cache
huskycat --version                 # Show version
```

### Mode Override

```bash
huskycat --mode ci validate        # Force CI mode (JUnit XML output)
huskycat --mode pipeline validate  # Force pipeline mode (JSON output)
huskycat --mode git_hooks validate # Force git hooks mode
```

## Git Hooks Installation

### Automatic Setup

```bash
cd /path/to/your/repo
huskycat setup-hooks
```

This installs pre-commit and pre-push hooks to `.git/hooks/`.

### Non-Blocking Mode

Enable non-blocking mode for faster commits:

```bash
git config --local huskycat.nonblocking true
```

With non-blocking mode:
- Commits complete in under 100ms
- Validation runs in background process
- TUI displays real-time progress
- Previous failures are checked before allowing new commits

### Tracked Hooks (Recommended)

For team consistency, use tracked hooks in `.githooks/`:

```bash
# Configure git to use tracked hooks
git config core.hooksPath .githooks

# Add postinstall to package.json
"postinstall": "git config core.hooksPath .githooks || true"
```

## Validation Tools

HuskyCat includes 20 validators across multiple categories:

| Category | Tools |
|----------|-------|
| **Python** | black, ruff, flake8, mypy, pylint, bandit, isort, autoflake |
| **JavaScript** | eslint, prettier |
| **Shell** | shellcheck |
| **Docker** | hadolint |
| **YAML** | yamllint, ansible-lint |
| **TOML** | taplo |
| **IaC** | terraform |
| **Schema** | gitlab-ci-schema, openapi-schema, json-schema |
| **Chapel** | chapel-format |

## MCP Server Integration

HuskyCat exposes validation tools via MCP protocol for AI assistants:

```bash
# Start MCP server
huskycat mcp-server

# Add to Claude Code
claude mcp add huskycat -- huskycat mcp-server
```

MCP tools exposed:
- `validate` - Validate files/directories
- `validate_staged` - Validate git staged files
- `validate_black`, `validate_mypy`, etc. - Individual tool validators

See [docs/features/mcp-server.md](docs/features/mcp-server.md) for details.

## Performance

### Non-Blocking vs Blocking Hooks

| Metric | Blocking Hooks | Non-Blocking Hooks |
|--------|----------------|-------------------|
| **Time to commit** | 5-30s (waits for validation) | Under 100ms (validation runs in background) |
| **Tools run** | Fast subset (4 tools) | All available (20 tools) |
| **Parallel execution** | Sequential | Concurrent with NetworkX DAG |

Note: The "300x faster commits" claim compares commit completion time, not total validation time. Non-blocking mode moves validation to background rather than eliminating it.

### Execution Model Performance

| Model | Startup | Tool Access | Dependencies |
|-------|---------|-------------|--------------|
| **Binary (bundled)** | Fast | Embedded | None |
| **Binary (delegated)** | Fast | Container call | Container runtime |
| **Container** | Container startup | Direct | Container runtime |
| **UV Development** | Python startup | System PATH | Python, uv |

## Configuration

Create `.huskycat.yaml` in your project root:

```yaml
# Tools to run
tools:
  - black
  - ruff
  - mypy
  - shellcheck

# Files to validate
include:
  - "**/*.py"
  - "**/*.sh"

# Files to exclude
exclude:
  - "vendor/**"
  - "node_modules/**"

# Auto-fix settings
fix:
  enabled: true
  confidence_threshold: high
```

## Downloads

| Platform | Architecture | Download |
|----------|-------------|----------|
| Linux | x86_64 (amd64) | [Download](https://gitlab.com/tinyland/ai/huskycat/-/jobs/artifacts/main/raw/dist/bin/huskycat-linux-amd64?job=build:binary:linux-amd64) |
| Linux | ARM64 (aarch64) | [Download](https://gitlab.com/tinyland/ai/huskycat/-/jobs/artifacts/main/raw/dist/bin/huskycat-linux-arm64?job=build:binary:linux-arm64) |
| macOS | ARM64 (M1/M2/M3/M4) | [Download](https://gitlab.com/tinyland/ai/huskycat/-/jobs/artifacts/main/raw/dist/bin/huskycat-darwin-arm64?job=build:binary:darwin-arm64) |

Binary sizes: 150-200MB (includes embedded validation tools)

macOS note: Remove quarantine after download:
```bash
xattr -d com.apple.quarantine huskycat
```

See [docs/binary-downloads.md](docs/binary-downloads.md) for checksums and verification.

## Documentation

- [Installation Guide](docs/installation.md) - Detailed installation for all platforms
- [CLI Reference](docs/cli-reference.md) - Command-line usage
- [Product Modes](docs/architecture/product-modes.md) - 5 modes with code references
- [Execution Models](docs/architecture/execution-models.md) - Binary, Container, UV
- [Non-Blocking Hooks](docs/nonblocking-hooks.md) - Fast commit workflow
- [MCP Server](docs/features/mcp-server.md) - AI integration
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions

## Contributing

HuskyCat uses its own validation tools (dogfooding):

```bash
git clone https://gitlab.com/tinyland/ai/huskycat.git
cd huskycat
uv sync --dev

# Hooks are configured via core.hooksPath = .githooks
git config --local --get core.hooksPath  # Shows: .githooks

# Enable non-blocking mode
git config --local huskycat.nonblocking true

# Run tests
npm run test:unit
```

See [docs/dogfooding.md](docs/dogfooding.md) for details.

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

## Links

- **Repository**: https://gitlab.com/tinyland/ai/huskycat
- **Documentation**: https://huskycat-570fbd.gitlab.io/
- **Downloads**: https://huskycat-570fbd.gitlab.io/downloads/
- **Issues**: https://gitlab.com/tinyland/ai/huskycat/-/issues

---

**Version**: 2.0.0
