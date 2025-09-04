# Configuration Reference

This document details all configuration options for the comprehensive linting setup.

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

### `comprehensive-lint.sh` Options

Environment variables:
```bash
# Enable/disable specific linters
LINT_PYTHON_BLACK=true      # Black formatter
LINT_PYTHON_FLAKE8=true     # Flake8 linter
LINT_PYTHON_RUFF=false      # Ruff linter (faster alternative)
LINT_ANSIBLE=true           # Ansible-lint

# Behavior
AUTO_FIX=true              # Automatically fix issues
VERBOSE=false              # Verbose output
INSTALL_TOOLS=false        # Install missing tools
```

Command-line options:
```bash
--all          # Lint all files
--staged       # Lint only staged files (default)
--fix          # Enable auto-fix
--no-fix       # Disable auto-fix
--install      # Install missing tools
--verbose, -v  # Verbose output
```

### Husky Hook Configuration

#### Pre-commit Hook

The pre-commit hook runs:
1. Enhanced CI validation
2. Comprehensive linting (staged files)
3. lint-staged
4. Secret scanning
5. Language-specific checks

Customization:
```bash
# Skip specific checks
SKIP_CI_VALIDATION=true git commit
SKIP_LINT_STAGED=true git commit
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

## Customization Examples

### Adding a New Language

1. Add to `.lintstagedrc.json`:
```json
{
  "*.rb": [
    "rubocop --auto-correct",
    "prettier --write"
  ]
}
```

2. Update `comprehensive-lint.sh`:
```bash
# Add detection function
detect_ruby_files() {
    find . -name "*.rb" -type f
}

# Add lint function
lint_ruby() {
    rubocop --auto-correct "$@"
}
```

3. Update pre-commit hook:
```bash
if echo "$STAGED_FILES" | grep -q '\.rb$'; then
    log_info "Ruby files detected..."
    # Add Ruby-specific checks
fi
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

### Performance Optimization

For large repositories:

1. Use `--staged` by default
2. Enable parallel processing:
```bash
# In comprehensive-lint.sh
export PARALLEL_JOBS=4
```

3. Cache linter results:
```bash
# Add to .gitignore
.mypy_cache/
.ruff_cache/
.pytest_cache/
```
