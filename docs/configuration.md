# Configuration Reference

This document details all configuration options for HuskyCat's multi-modal validation platform.

## Linting Configuration Files

### `.ansible-lint`

Ansible-lint configuration with production-grade settings:

```yaml
# Profile settings
profile: production  # Enforces strict rules

# Paths to exclude
exclude_paths:
  - .cache/
  - node_modules/
  - vendor/

# Behavior
progressive: true   # Return non-zero on warnings
strict: true       # Enable strict mode

# Rule configuration
enable_list:       # Explicitly enabled rules
  - args
  - command-instead-of-module
  - fqcn
  - no-log-password
  # ... more rules

skip_list:         # Rules to skip
  - experimental   # Skip experimental rules
```

### `pyproject.toml`

Python tooling configuration:

```toml
[tool.black]
line-length = 88              # Line length limit
target-version = ['py38']     # Python versions
extend-exclude = '''          # Paths to exclude
  /(
    \.git
    | node_modules
    | vendor
  )/
'''

[tool.isort]
profile = "black"             # Compatible with Black
line_length = 88

[tool.mypy]
python_version = "3.8"
warn_return_any = true
disallow_untyped_defs = true

[tool.ruff]
select = ["E", "F", "I", ...]  # Rule sets to enable
line-length = 88
target-version = "py38"
```

### `.flake8`

Flake8 configuration:

```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503, E501  # Black compatibility
exclude = 
    .git,
    __pycache__,
    node_modules,
    vendor
per-file-ignores = 
    __init__.py:F401              # Allow unused imports
    test_*.py:F401,F811           # Test-specific ignores
```

### `.lintstagedrc.json`

File-specific linting rules:

```json
{
  "*.{ts,tsx,js,jsx}": [
    "eslint --fix",
    "prettier --write"
  ],
  "*.py": [
    "black",
    "flake8"
  ],
  "*.{yml,yaml}": [
    "prettier --write",
    "ansible-lint check (conditional)"
  ]
}
```

## Script Configuration

### HuskyCat Execution Configuration

**Multi-Modal Execution**: HuskyCat supports three execution models - Binary (embedded tools), Container (delegated), and UV Development mode. See [Execution Models](architecture/execution-models.md) for details.

Environment variables:
```bash
# Container configuration
HUSKYCAT_CONTAINER_RUNTIME=podman  # or docker
HUSKYCAT_LOG_LEVEL=INFO            # DEBUG, INFO, WARNING, ERROR
HUSKYCAT_CONFIG_DIR=~/.huskycat    # Config storage location

# Validation behavior
HUSKYCAT_AUTO_FIX=false            # Enable auto-fix by default
HUSKYCAT_USE_CACHE=true            # Enable validation caching
```

Command-line options:
```bash
--fix          # Enable auto-fix
--all          # Validate all files
--staged       # Validate only staged files (default)
--verbose, -v  # Verbose output
--mode MODE    # Override auto-detected product mode
--json         # Force JSON output (sets pipeline mode)
```

## Product Modes

HuskyCat operates in 5 distinct product modes, each optimized for different use cases:

### Mode Overview

| Mode | Output Format | Interactive | Auto-Fix | Tools | Use Case |
|------|--------------|-------------|----------|-------|----------|
| `git_hooks` | Minimal | No | SAFE only | Fast subset | Pre-commit/pre-push |
| `ci` | JUnit XML | No | Never | All | Pipeline integration |
| `cli` | Human/Colored | Yes | SAFE+LIKELY | Configured | Interactive terminal |
| `pipeline` | JSON | No | Never | All | Machine-readable |
| `mcp` | JSON-RPC | No | Never | All | AI assistant integration |

### Mode Detection

HuskyCat automatically detects the appropriate mode:

1. **Explicit override**: `--mode git_hooks` or `HUSKYCAT_MODE=ci`
2. **MCP invocation**: `mcp-server` command
3. **CI environment**: `CI=true`, `GITLAB_CI`, `GITHUB_ACTIONS`
4. **Git hooks**: Multiple `GIT_*` environment variables
5. **Pipeline context**: Non-interactive stdin
6. **Default**: CLI mode (interactive terminal)

### Mode-Specific Behavior

#### Git Hooks Mode (`--mode git_hooks`)
- **Output**: Minimal (errors only)
- **Fail-fast**: Yes (stop on first error)
- **Tools**: Fast subset (`python-black`, `ruff`, `mypy`, `flake8`)
- **Auto-fix**: Only SAFE fixes (formatting)

#### CI Mode (`--mode ci`)
- **Output**: JUnit XML for CI artifacts
- **Fail-fast**: No (run all validators)
- **Tools**: All available
- **Auto-fix**: Never (read-only)

#### CLI Mode (`--mode cli`)
- **Output**: Human-readable with colors
- **Interactive**: Yes (prompts for uncertain fixes)
- **Tools**: Configured via `.huskycat.yaml`
- **Auto-fix**: SAFE and LIKELY fixes

#### Pipeline Mode (`--mode pipeline` or `--json`)
- **Output**: JSON for toolchain integration
- **Interactive**: No
- **Tools**: All available
- **Auto-fix**: Never (read-only)

#### MCP Mode (`--mode mcp`)
- **Output**: JSON-RPC 2.0
- **Transport**: stdio (stdin/stdout)
- **Tools**: All available via MCP tools
- **Auto-fix**: Never (Claude decides)

### Auto-Fix Confidence Tiers

HuskyCat uses a three-tier confidence system for auto-fix decisions:

| Tier | Behavior | Example Tools |
|------|----------|---------------|
| **SAFE** | Always safe, formatting only | `python-black`, `js-prettier`, `yamllint` |
| **LIKELY** | Usually safe, style fixes | `autoflake`, `ruff`, `js-eslint` |
| **UNCERTAIN** | Needs human review | Semantic changes |

**Mode-specific auto-fix behavior**:
- **Git Hooks**: Only apply SAFE fixes automatically
- **CLI**: Apply SAFE and LIKELY; prompt for UNCERTAIN
- **CI/Pipeline/MCP**: Never auto-fix (report only)

**File references**:
- Mode detection: `src/huskycat/core/mode_detector.py`
- Adapters: `src/huskycat/core/adapters/*.py`
- FixConfidence: `src/huskycat/core/adapters/base.py:27-51`

### Git Hook Configuration

#### Pre-commit Hook

Container-only validation runs:
1. Staged file validation
2. Auto-fix when requested
3. Complete toolchain in isolated container
4. Repository read-only mounting

**Generated by**: `./dist/huskycat setup-hooks` (do not edit manually)

Customization:
```bash
# Temporary bypass (development only)
git commit --no-verify -m "message"
```

#### Commit-msg Hook

Validates commit format:
```
<type>(<scope>): <subject>

Types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert
```

Configuration:
```bash
# Skip issue check
SKIP_ISSUE_CHECK=true git commit
```

#### Pre-push Hook

Runs before push:
- Full linting (all files)
- Affected tests
- Large file detection
- Security scanning

#### Post-merge Hook

Automatic actions after merge:
- Update dependencies
- Run linting on changed files
- Rebuild affected projects

## GitLab CI Configuration

### Basic Structure

```yaml
stages:
  - validate
  - lint
  - test

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"
  npm_config_cache: "$CI_PROJECT_DIR/.cache/npm"

cache:
  paths:
    - .cache/pip
    - .cache/npm
    - node_modules/
    - .venv/
```

### Job Templates

Python linting job:
```yaml
lint:python:
  stage: lint
  image: python:3.11
  before_script:
    - pip install black flake8 mypy
  script:
    - black --check .
    - flake8 .
    - mypy .
```

## Container Toolchain

### Available Tools in Container

**Python Tools**:
- black, flake8, mypy, ruff
- bandit, safety (security)
- autoflake, isort (formatting)

**Shell Tools**:
- shellcheck, yamllint, hadolint
- gitlab-ci-local (CI validation)

**JavaScript Tools**:
- eslint, prettier

**All tools** are pre-installed in the container - no local installation needed.

### Adding Custom Validators

Extend the ValidationEngine in `unified_validation.py`:
```python
class CustomValidator(Validator):
    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix == '.custom'
    
    def validate(self, file_path: Path) -> ValidationResult:
        # Container execution is automatic
        return self._execute_command(['custom-tool', str(file_path)])
```

### Disabling Specific Checks

Per-file basis:
```python
# flake8: noqa
# mypy: ignore-errors
# pylint: disable=all
```

Project-wide:
- Update respective config files
- Modify `skip_list` or `ignore` sections

### Performance & Caching

Container execution optimizations:

1. **Binary-first execution**: Fast startup (~100ms)
2. **Container caching**: Images cached locally
3. **Validation caching**: Results cached in `~/.huskycat/cache`

```bash
# Clean caches
./dist/huskycat clean --all

# Rebuild container
npm run container:build

# Status and performance info
./dist/huskycat status
```
