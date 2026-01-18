# Git-Tracked Husky-Style Hooks with UV Venv Integration

**Status: IMPLEMENTED**

## Summary

HuskyCat now uses **git-tracked hooks** in `.githooks/` that leverage UV's virtual environment for tool execution. This replaces the previous runtime-generated hooks with version-controlled scripts.

## Design Principles

1. **UV-Only Execution**: No binary fallback, no container fallback. Forces "eat your own dogfood" paradigm.
2. **Git-Tracked**: All hooks are version-controlled, changes reviewed like code.
3. **Interactive Auto-Fix**: Prompts for fixes when issues found, with auto-approve mode for CI.
4. **Zero NPM Dependencies**: Removed husky and lint-staged - pure shell + UV.

## Architecture

### Directory Structure

```
.githooks/                          # Git-tracked hooks
├── README.md                       # Developer documentation
├── _/
│   └── common.sh                   # Shared utilities (logging, prompts, helpers)
├── pre-commit                      # Staged file validation with auto-fix
├── pre-push                        # Full codebase validation
└── commit-msg                      # Conventional commit format validation

src/huskycat/commands/hooks.py      # Minimal: just sets core.hooksPath
```

### Hook Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           git commit -m "..."                           │
│                                  │                                      │
│                                  ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                        PRE-COMMIT HOOK                            │  │
│  │                                                                   │  │
│  │   1. Verify UV venv active                                        │  │
│  │   2. Get staged Python files                                      │  │
│  │   3. Run Black (format check)                                     │  │
│  │      └── If fail: prompt auto-fix? → apply & re-stage             │  │
│  │   4. Run Ruff (lint check)                                        │  │
│  │      └── If fail: prompt auto-fix? → apply & re-stage             │  │
│  │   5. Run Flake8 (additional lint - no auto-fix)                   │  │
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
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              git push                                   │
│                                  │                                      │
│                                  ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                         PRE-PUSH HOOK                             │  │
│  │                                                                   │  │
│  │   1. Full Black check on src/ tests/                              │  │
│  │   2. Full Ruff check on src/ tests/                               │  │
│  │   3. Full Flake8 check on src/ tests/                             │  │
│  │   4. GitLab CI validation (if glab available)                     │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Setup

### Automatic (on npm install)

```json
{
  "scripts": {
    "postinstall": "git config core.hooksPath .githooks || true"
  }
}
```

### Manual

```bash
git config core.hooksPath .githooks
```

### Via HuskyCat

```bash
npm run hooks:install
# or
uv run python3 -m src.huskycat setup-hooks
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SKIP_HOOKS` | `0` | Skip all hooks |
| `HUSKYCAT_SKIP_HOOKS` | `0` | Alternative skip variable |
| `HUSKYCAT_AUTO_APPROVE` | `0` | Auto-approve all fixes (for CI/scripts) |
| `AUTO_FIX` | `0` | Alternative auto-approve variable |

## Key Files

### `.githooks/_/common.sh`

Shared utilities providing:
- Color output (`log_info`, `log_warn`, `log_error`, `log_step`)
- Environment detection (`is_ci`, `is_interactive`, `is_auto_approve`)
- UV verification (`verify_uv_environment`, `uv_run`)
- Git utilities (`staged_files`, `tracked_files`, `has_staged_files`)
- Interactive prompts (`ask_yes_no`)
- Auto-fix runner (`run_with_autofix`)

### `.githooks/pre-commit`

- Validates staged Python files
- Runs Black, Ruff, Flake8 in sequence
- Interactive auto-fix prompts for Black and Ruff
- Re-stages fixed files automatically

### `.githooks/pre-push`

- Full codebase validation (not just staged files)
- Black, Ruff, Flake8 on `src/` and `tests/`
- GitLab CI configuration validation via `glab`

### `.githooks/commit-msg`

- Validates conventional commit format
- Skips merge/revert/fixup commits
- Clear error messages with examples

### `src/huskycat/commands/hooks.py`

Minimal command that:
- Verifies `.githooks/` directory exists
- Sets `git config core.hooksPath .githooks`
- Validates UV and venv availability
- Reports available hooks

## Developer Requirements

**UV virtual environment MUST be active for development in this repository.**

```bash
# First-time setup
uv sync --dev
npm install  # Configures core.hooksPath automatically

# Verify
uv run black --version
uv run ruff --version
```

## Migration from Previous Hooks

The previous system had:
- Runtime-generated hooks embedded in Python code
- Binary-first, container fallback execution
- Legacy husky v8 files in `.git/hooks/_/`

The new system:
- Git-tracked hooks in `.githooks/`
- UV-only execution
- No external dependencies (removed husky/lint-staged)

### Cleanup

```bash
# Remove legacy husky files
rm -rf .git/hooks/_/

# Remove old runtime-generated hooks (optional, superseded by core.hooksPath)
rm -f .git/hooks/pre-commit .git/hooks/pre-push .git/hooks/commit-msg
```

## Benefits

| Aspect | Previous | New |
|--------|----------|-----|
| Version Control | Runtime-generated | Git-tracked |
| Team Sync | Manual setup-hooks | Automatic via postinstall |
| Customization | Edit Python code | Edit shell scripts |
| Dependencies | Python + optional binary | Just bash + UV |
| Auto-Fix | Complex mode detection | Simple interactive prompts |
| NPM deps | husky + lint-staged | None |
