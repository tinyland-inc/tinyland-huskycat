# HuskyCat Git Hooks

This directory contains git-tracked hooks for the HuskyCat repository. These hooks enforce code quality standards using **HuskyCat's own validation engine** - true "eat your own dogfood" paradigm.

## Key Principle: Eat Your Own Dogfood

These hooks use `huskycat validate` commands, NOT direct tool invocations like `black` or `ruff`. This ensures:

1. **We test our own code** on every commit/push
2. **Consistency** between hook behavior and HuskyCat's validation
3. **Dogfooding** forces us to fix issues in our validation engine

## Prerequisites

**UV virtual environment MUST be active for development in this repository.**

```bash
# First-time setup
uv sync --dev

# Verify setup
uv run python --version
uv run python -m src.huskycat --help
```

## Setup

Configure git to use these tracked hooks:

```bash
# One-time setup (or run: npm run hooks:install)
git config core.hooksPath .githooks
```

This is also done automatically by `npm install` (via postinstall script).

## Hook Flow Diagram

```
                              GIT WORKFLOW
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           git add <files>                               │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          git commit -m "..."                            │
│                                  │                                      │
│                                  ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                        PRE-COMMIT HOOK                            │  │
│  │                                                                   │  │
│  │   1. Verify UV venv active                                        │  │
│  │   2. Check for staged Python files                                │  │
│  │   3. Run: huskycat validate --staged [--fix|--interactive]        │  │
│  │      └── Uses HuskyCat's validation engine (Black, Ruff, etc.)    │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                  │                                      │
│                                  ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                        COMMIT-MSG HOOK                            │  │
│  │                                                                   │  │
│  │   Validate conventional commit format:                            │  │
│  │   <type>(<scope>): <description>                                  │  │
│  │                                                                   │  │
│  │   Types: feat|fix|docs|style|refactor|test|chore|perf|ci|build    │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                  │                                      │
│                                  ▼                                      │
│                           COMMIT CREATED                                │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              git push                                   │
│                                  │                                      │
│                                  ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    PRE-PUSH HOOK (FAST)                           │  │
│  │                                                                   │  │
│  │   1. Verify UV venv active                                        │  │
│  │   2. Run: huskycat ci-validate .gitlab-ci.yml                     │  │
│  │      └── GitLab CI configuration validation only                  │  │
│  │                                                                   │  │
│  │   NOTE: Full codebase validation happens in CI pipeline           │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                  │                                      │
│                                  ▼                                      │
│                            PUSH TO REMOTE                               │
└─────────────────────────────────────────────────────────────────────────┘
```

## Hooks Overview

| Hook | Trigger | What it does |
|------|---------|--------------|
| `pre-commit` | Before commit is created | `huskycat validate --staged` on Python files |
| `commit-msg` | After commit message entered | Validates conventional commit format |
| `pre-push` | Before push to remote | `huskycat ci-validate` (CI config only - fast!) |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SKIP_HOOKS` | `0` | Set to `1` to skip all hooks |
| `HUSKYCAT_SKIP_HOOKS` | `0` | Alternative skip variable |
| `HUSKYCAT_AUTO_APPROVE` | `0` | Set to `1` to auto-approve all fixes |
| `AUTO_FIX` | `0` | Alternative auto-approve variable |

## Usage Examples

### Normal workflow
```bash
git add src/myfile.py
git commit -m "feat: add new feature"
git push
```

### Skip hooks (emergency only)
```bash
# Skip via environment variable
SKIP_HOOKS=1 git commit -m "wip: work in progress"

# Or use git's built-in flag
git commit --no-verify -m "wip: work in progress"
git push --no-verify
```

### Auto-approve all fixes (CI/scripts)
```bash
HUSKYCAT_AUTO_APPROVE=1 git commit -m "feat: new feature"
```

### Fix issues manually before commit
```bash
# Use HuskyCat to fix issues
uv run python -m src.huskycat validate --staged --fix

# Or run individual tools
uv run black src/ tests/
uv run ruff check --fix src/ tests/

# Then commit
git add -u
git commit -m "style: fix formatting"
```

## HuskyCat Commands Used

The hooks use these HuskyCat commands:

```bash
# Pre-commit (staged files only)
uv run python -m src.huskycat validate --staged
uv run python -m src.huskycat validate --staged --fix           # with auto-fix
uv run python -m src.huskycat validate --staged --interactive   # with prompts

# Pre-push (CI config validation only - FAST)
uv run python -m src.huskycat ci-validate .gitlab-ci.yml

# Full codebase validation (done by CI pipeline, not hooks)
uv run python -m src.huskycat validate --all
```

## File Structure

```
.githooks/
├── README.md           # This file
├── _/
│   └── common.sh       # Shared utilities (colors, logging, helpers)
├── pre-commit          # Staged file validation with HuskyCat
├── pre-push            # Full codebase validation with HuskyCat
└── commit-msg          # Commit message format validation
```

## Troubleshooting

### "UV not found" error
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Then setup venv
uv sync --dev
```

### "Virtual environment not found" error
```bash
# Create venv with dev dependencies
uv sync --dev
```

### Hooks not running
```bash
# Verify hooks path is configured
git config core.hooksPath
# Should output: .githooks

# If not, set it
git config core.hooksPath .githooks
```

### Permission denied on hook
```bash
# Make hooks executable
chmod +x .githooks/*
chmod +x .githooks/_/*
```

### HuskyCat validation errors
```bash
# Run validation manually to see details
uv run python -m src.huskycat validate --staged

# Try with auto-fix
uv run python -m src.huskycat validate --staged --fix
```

## Design Principles

1. **Eat Your Own Dogfood**: Hooks use `huskycat validate`, not direct tool invocations. This tests our validation engine on every commit.

2. **UV-Only Execution**: No binary fallback, no container fallback. UV venv is required.

3. **Git-Tracked**: All hooks are version-controlled. Changes are reviewed like any other code.

4. **Interactive by Default**: Prompts for auto-fix when issues found. Supports non-interactive mode for CI.

5. **Clear Escape Hatches**: `SKIP_HOOKS=1` or `--no-verify` when needed.
