# CLI Reference

Complete command-line interface reference for HuskyCat.

## Synopsis

```bash
huskycat [OPTIONS] COMMAND [ARGS]
```

## Global Options

| Option | Description |
|--------|-------------|
| `-h`, `--help` | Show help message and exit |
| `--version` | Show version and exit |
| `--verbose`, `-v` | Enable verbose output (repeat for more verbosity) |
| `--config-dir PATH` | Override config directory (default: `.huskycat`) |
| `--mode MODE` | Override product mode detection (see [Product Modes](#product-modes)) |
| `--json` | Force JSON output (equivalent to `--mode pipeline`) |

## Product Modes

HuskyCat automatically detects the execution context, but you can override:

| Mode | Description | Output Format | Use Case |
|------|-------------|---------------|----------|
| `git_hooks` | Git hooks mode | Minimal, errors only | Pre-commit/pre-push validation |
| `ci` | CI/CD mode | JUnit XML | GitLab CI, GitHub Actions |
| `cli` | Interactive CLI | Rich terminal output | Developer usage |
| `pipeline` | Pipeline integration | JSON | Scripting, automation |
| `mcp` | MCP server | JSON-RPC 2.0 | Claude Code integration |

**Examples:**

```bash
# Force CI mode with JUnit XML output
huskycat --mode ci validate --all

# Force JSON output for scripting
huskycat --json status

# Verbose CLI output
huskycat -vv validate src/
```

## Commands

### validate

Validate files or directories with all applicable validators.

**Usage:**
```bash
huskycat validate [OPTIONS] [FILES...]
```

**Arguments:**
- `FILES` - Files or directories to validate (default: current directory)

**Options:**

| Option | Description |
|--------|-------------|
| `--staged` | Validate only staged git files |
| `--all` | Validate all files in repository |
| `--fix` | Auto-fix issues where possible |
| `--interactive` | Prompt for auto-fix decisions |
| `--allow-warnings` | Allow warnings to pass (don't fail) |

**Examples:**

```bash
# Validate current directory
huskycat validate

# Validate specific files
huskycat validate src/main.py tests/test_api.py

# Validate all Python files in src/
huskycat validate src/**/*.py

# Validate staged files (pre-commit)
huskycat validate --staged

# Validate and auto-fix
huskycat validate --fix

# Interactive auto-fix with prompts
huskycat validate --fix --interactive

# Validate all files in repository
huskycat validate --all
```

**Exit Codes:**
- `0` - All validations passed
- `1` - Validation failures found
- `2` - Error during execution

---

### auto-fix

Auto-fix issues using all available validators.

**Usage:**
```bash
huskycat auto-fix [OPTIONS] [FILES...]
```

**Arguments:**
- `FILES` - Files or directories to auto-fix (default: current directory)

**Options:**

| Option | Description |
|--------|-------------|
| `--staged` | Auto-fix only staged git files |
| `--interactive` | Prompt before applying fixes |

**Examples:**

```bash
# Auto-fix current directory
huskycat auto-fix

# Auto-fix staged files
huskycat auto-fix --staged

# Interactive auto-fix with confirmation
huskycat auto-fix --interactive src/
```

---

### setup-hooks

Install git hooks for automatic validation.

**Usage:**
```bash
huskycat setup-hooks [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--force` | Overwrite existing hooks |

**Examples:**

```bash
# Install git hooks
huskycat setup-hooks

# Force reinstall (overwrite existing)
huskycat setup-hooks --force
```

**Installed Hooks:**
- `pre-commit` - Validates staged files before commit
- `pre-push` - Validates CI configuration before push
- `commit-msg` - Validates commit message format

**Configuration:**

Hooks respect `.huskycat/config.json` settings. To skip hooks temporarily:

```bash
# Skip hooks for one commit
SKIP_HOOKS=1 git commit -m "message"

# Skip validation on push
git push --no-verify
```

---

### ci-validate

Validate CI configuration files.

**Usage:**
```bash
huskycat ci-validate [FILES...]
```

**Arguments:**
- `FILES` - CI configuration files (default: `.gitlab-ci.yml`)

**Examples:**

```bash
# Validate GitLab CI
huskycat ci-validate .gitlab-ci.yml

# Validate multiple CI files
huskycat ci-validate .gitlab-ci.yml .github/workflows/*.yml
```

**Supported CI Configs:**
- GitLab CI (`.gitlab-ci.yml`)
- GitHub Actions (`.github/workflows/*.yml`)

---

### auto-devops

Validate Auto-DevOps Helm charts and Kubernetes manifests.

**Usage:**
```bash
huskycat auto-devops [PATH]
```

**Arguments:**
- `PATH` - Path to Helm charts or K8s manifests (default: `.`)

**Examples:**

```bash
# Validate Auto-DevOps configuration
huskycat auto-devops

# Validate specific Helm chart
huskycat auto-devops charts/myapp/
```

---

### mcp-server

Start MCP server for Claude Code integration (stdio mode).

**Usage:**
```bash
huskycat mcp-server
```

**Notes:**
- Uses stdin/stdout for JSON-RPC 2.0 communication
- No HTTP server or port configuration
- Designed for Claude Code MCP integration

**Examples:**

```bash
# Start MCP server (normally called by Claude Code)
huskycat mcp-server

# Test MCP server manually
echo '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}' | huskycat mcp-server
```

See [MCP Server Guide](features/mcp-server.md) for integration details.

---

### bootstrap

Automatically configure Claude Code MCP integration.

**Usage:**
```bash
huskycat bootstrap [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--force` | Overwrite existing MCP configuration |

**Examples:**

```bash
# Configure Claude Code MCP integration
huskycat bootstrap

# Force reconfiguration
huskycat bootstrap --force
```

**What it does:**
1. Creates MCP configuration file
2. Configures HuskyCat binary path
3. Sets up stdio transport

---

### update-schemas

Update validation schemas from official sources.

**Usage:**
```bash
huskycat update-schemas
```

**Examples:**

```bash
# Update all validation schemas
huskycat update-schemas
```

**Updated Schemas:**
- GitLab CI schema
- JSON schemas for configuration files
- Validation rule definitions

---

### clean

Clean cache and temporary files.

**Usage:**
```bash
huskycat clean [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--all` | Clean all cached data including schemas |

**Examples:**

```bash
# Clean cache and temporary files
huskycat clean

# Clean everything including schemas
huskycat clean --all
```

**Cleaned Directories:**
- `.huskycat/cache/` - Validation cache
- `.huskycat/temp/` - Temporary files
- With `--all`: `.huskycat/schemas/` - Downloaded schemas

---

### status

Show HuskyCat configuration and system status.

**Usage:**
```bash
huskycat status
```

**Examples:**

```bash
# Show status
huskycat status

# JSON output for scripting
huskycat --json status
```

**Status Information:**
- HuskyCat version
- Product mode (detected)
- Container runtime (podman/docker)
- Installed validators
- Git hooks status
- Configuration directory
- Cache size

---

### install

Install HuskyCat binary and dependencies (for development).

**Usage:**
```bash
huskycat install
```

**Examples:**

```bash
# Install HuskyCat
huskycat install
```

**Note:** Most users should use [pre-built binaries](binary-downloads.md) instead.

---

## Environment Variables

HuskyCat respects these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `HUSKYCAT_MODE` | Override product mode detection | Auto-detect |
| `HUSKYCAT_LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO |
| `HUSKYCAT_CONFIG_DIR` | Configuration directory | `.huskycat` |
| `SKIP_HOOKS` | Skip git hooks (set to `1`) | Not set |
| `CI` | Detected CI environment | Not set |
| `GITLAB_CI` | GitLab CI detection | Not set |
| `GITHUB_ACTIONS` | GitHub Actions detection | Not set |

**Examples:**

```bash
# Enable debug logging
HUSKYCAT_LOG_LEVEL=DEBUG huskycat validate

# Override product mode
HUSKYCAT_MODE=ci huskycat validate --all

# Skip git hooks temporarily
SKIP_HOOKS=1 git commit -m "message"
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success - all validations passed |
| `1` | Validation failures found |
| `2` | Execution error (invalid arguments, missing dependencies, etc.) |

---

## Configuration Files

### Project Configuration

**Location:** `.huskycat/config.json`

```json
{
  "validators": {
    "python-black": {"enabled": true},
    "mypy": {"enabled": true},
    "flake8": {"enabled": true},
    "ruff": {"enabled": true}
  },
  "auto_fix": {
    "enabled": true,
    "interactive": false
  }
}
```

### Tool-Specific Configuration

HuskyCat respects standard configuration files:

- **Black:** `pyproject.toml` ([tool.black])
- **Flake8:** `.flake8`, `setup.cfg`
- **MyPy:** `mypy.ini`, `pyproject.toml`
- **Ruff:** `ruff.toml`, `pyproject.toml`
- **ESLint:** `.eslintrc.json`, `.eslintrc.js`
- **Prettier:** `.prettierrc`, `prettier.config.js`

---

## Validators

HuskyCat includes these validators:

### Python

| Validator | Tool | Purpose | Auto-Fix |
|-----------|------|---------|----------|
| `python-black` | Black | Code formatting |  Yes |
| `autoflake` | Autoflake | Remove unused imports |  Yes |
| `flake8` | Flake8 | Linting |  No |
| `mypy` | MyPy | Type checking |  No |
| `ruff` | Ruff | Fast linting |  Partial |
| `bandit` | Bandit | Security scanning |  No |

### JavaScript/TypeScript

| Validator | Tool | Purpose | Auto-Fix |
|-----------|------|---------|----------|
| `js-eslint` | ESLint | Linting |  Partial |
| `js-prettier` | Prettier | Code formatting |  Yes |

### Chapel

| Validator | Tool | Purpose | Auto-Fix |
|-----------|------|---------|----------|
| `chapel` | ChapelFormatter | Code formatting |  Yes |

**Note**: Chapel formatter is a lightweight, custom implementation that provides whitespace cleanup and basic syntax formatting without requiring the Chapel compiler. It uses regex-based pattern matching for safe, deterministic formatting.

**Supported features**:
-  Whitespace normalization (trailing spaces, tabs, final newline)
-  Operator spacing (=, +, -, *, /, ==, !=, <, >, &&, ||)
-  Keyword spacing (if, for, while, proc)
-  Brace and comma spacing
-  Type annotation formatting (var x: int)
-  2-space indentation (brace-based)

**Limitations**:
-  No semantic analysis (type checking)
-  No import sorting
-  Basic indentation (complex nested expressions may need manual adjustment)

**Example**:
```bash
# Format Chapel files
huskycat validate --fix src/**/*.chpl

# Check Chapel formatting without fixing
huskycat validate src/**/*.chpl
```

### Configuration Files

| Validator | Tool | Purpose | Auto-Fix |
|-----------|------|---------|----------|
| `yamllint` | yamllint | YAML linting |  Partial |
| `gitlab-ci` | GitLab CI Lint | CI validation |  No |

### Containers & Scripts

| Validator | Tool | Purpose | Auto-Fix |
|-----------|------|---------|----------|
| `hadolint` | hadolint | Dockerfile linting |  No |
| `shellcheck` | shellcheck | Shell script linting |  No |

---

## Examples

### Common Workflows

**Pre-commit validation:**
```bash
# Validate staged files before commit
huskycat validate --staged --fix
```

**CI/CD integration:**
```bash
# Validate in CI with JUnit XML output
huskycat --mode ci validate --all
```

**Interactive development:**
```bash
# Validate and interactively fix issues
huskycat validate --fix --interactive src/
```

**Scripting/Automation:**
```bash
# Get JSON output for parsing
huskycat --json validate src/ > results.json
```

---

## Troubleshooting

### Common Issues

**"No container runtime available"**

Install Podman or Docker:
```bash
# macOS
brew install podman

# Rocky Linux
sudo dnf install podman
```

**"Permission denied" on macOS**

Allow binary execution:
```bash
xattr -d com.apple.quarantine ~/.local/bin/huskycat
```

**Git hooks not running**

Check hooks installation:
```bash
huskycat status
ls -la .git/hooks/
```

Reinstall if needed:
```bash
huskycat setup-hooks --force
```

---

For detailed installation instructions, see [Installation Guide](installation.md).

For binary downloads, see [Binary Downloads](binary-downloads.md).

For troubleshooting, see [Troubleshooting Guide](troubleshooting.md).
