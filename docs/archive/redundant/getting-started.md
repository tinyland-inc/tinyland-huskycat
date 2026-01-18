# Getting Started with HuskyCat

## Quick Start Guide (Sprint 10)

This guide gets you up and running with HuskyCat's latest non-blocking git hooks and fat binary features in under 5 minutes.

## Installation

### Option 1: Fat Binary (Recommended)

Download the platform-specific binary for instant validation without dependencies:

```bash
# macOS ARM64 (M1/M2/M3)
curl -L https://huskycat.pages.io/downloads/huskycat-darwin-arm64 -o huskycat
chmod +x huskycat
sudo mv huskycat /usr/local/bin/

# macOS Intel
curl -L https://huskycat.pages.io/downloads/huskycat-darwin-amd64 -o huskycat
chmod +x huskycat
sudo mv huskycat /usr/local/bin/

# Linux ARM64
curl -L https://huskycat.pages.io/downloads/huskycat-linux-arm64 -o huskycat
chmod +x huskycat
sudo mv huskycat /usr/local/bin/

# Linux AMD64
curl -L https://huskycat.pages.io/downloads/huskycat-linux-amd64 -o huskycat
chmod +x huskycat
sudo mv huskycat /usr/local/bin/

# Verify installation
huskycat --version
```

### Option 2: From Source

For development or contribution:

```bash
git clone https://github.com/tinyland/huskycat.git
cd huskycat
npm install
uv sync --dev
npm run build:binary
```

## Basic Configuration

Create `.huskycat.yaml` in your project root:

```yaml
version: "1.0"

# Enable Sprint 10 features
feature_flags:
  nonblocking_hooks: true      # Git operations return in <100ms
  parallel_execution: true     # 7.5x faster validation
  tui_progress: true           # Real-time progress display
  cache_results: true          # Cache validation results

# Tool configuration (all tools enabled by default)
tools:
  python:
    enabled: true
    tools: [black, ruff, mypy, flake8, isort, bandit, autoflake]

  yaml:
    enabled: true
    tools: [yamllint, gitlab-ci, ansible-lint, helm-lint]

  shell:
    enabled: true
    tools: [shellcheck]

  docker:
    enabled: true
    tools: [hadolint]

  toml:
    enabled: true
    tools: [taplo]
```

## Setup Git Hooks

Install non-blocking git hooks:

```bash
# Navigate to your git repository
cd /path/to/your/repo

# Install hooks
huskycat setup-hooks

# Verify installation
cat .git/hooks/pre-commit
```

## Your First Validation

### 1. Manual Validation

```bash
# Validate current directory
huskycat validate .

# Validate specific files
huskycat validate src/module.py tests/test_module.py

# Validate staged files only
huskycat validate --staged

# Auto-fix issues
huskycat validate --fix src/
```

### 2. Git Hooks Validation

```bash
# Make changes
echo "def hello(): print('world')" > src/hello.py
git add src/hello.py

# Commit (returns immediately with non-blocking hooks)
git commit -m "feat: add hello function"

# Output:
# Validation running in background (PID 12345)
# View progress: tail -f .huskycat/runs/latest.log
# [main abc1234] feat: add hello function
```

### 3. Watch Real-Time Progress

```bash
# In a separate terminal, watch validation progress
tail -f .huskycat/runs/latest.log
```

You'll see a rich TUI:

```
┌─────────────────────────────────────────┐
│ HuskyCat Validation (Non-Blocking Mode) │
├──────────┬─────────┬──────┬────────┬────┤
│ Tool     │ Status  │ Time │ Errors │    │
├──────────┼─────────┼──────┼────────┼────┤
│ Overall  │ ████░░  │ 5.2s │        │    │
├──────────┼─────────┼──────┼────────┼────┤
│ black    │ ✓ Done  │ 0.3s │ 0      │    │
│ ruff     │ ✓ Done  │ 0.5s │ 0      │    │
│ mypy     │ ⠋ Run   │ 3.2s │ -      │    │
│ flake8   │ • Pend  │ -    │ -      │    │
└──────────┴─────────┴──────┴────────┴────┘
```

## Common Workflows

### Development Workflow

```bash
# 1. Make changes
vim src/module.py

# 2. Stage files
git add src/module.py

# 3. Commit (returns immediately)
git commit -m "feat: add new feature"

# 4. Continue working
# Validation runs in background

# 5. Check validation status
huskycat status
```

### Auto-Fix Workflow

```bash
# Fix formatting issues automatically
huskycat validate --fix src/

# Or use git alias for pre-staging fixes
git addf src/module.py  # Auto-fix then stage
```

### CI/CD Workflow

```yaml
# .gitlab-ci.yml
validate:
  stage: test
  script:
    # Use fat binary (no container needed)
    - curl -L -o huskycat https://huskycat.pages.io/huskycat-linux-amd64
    - chmod +x huskycat
    - ./huskycat validate --all src/
  artifacts:
    reports:
      junit: test-results.xml
```

## Check Validation Status

### View Recent Runs

```bash
huskycat status
```

Output:

```
Recent Validation Runs:
┌─────────────────┬─────────┬────────┬──────────┐
│ Time            │ Status  │ Errors │ Warnings │
├─────────────────┼─────────┼────────┼──────────┤
│ 2 minutes ago   │ PASS    │ 0      │ 3        │
│ 15 minutes ago  │ FAIL    │ 5      │ 12       │
│ 1 hour ago      │ PASS    │ 0      │ 1        │
└─────────────────┴─────────┴────────┴──────────┘
```

### View Detailed Results

```bash
# Latest run
cat .huskycat/runs/last_run.json

# Specific run
cat .huskycat/runs/20240315_142530.json
```

## Understanding Previous Failure Detection

If validation fails, the next commit will prompt you:

```bash
$ git commit -m "fix: quick fix"

  Previous validation FAILED (2 minutes ago)
    Errors:   5
    Warnings: 12
    Tools:    black, mypy, flake8

  Proceed with commit anyway? [y/N] _
```

**Options:**
- **N** (default): Abort commit, fix issues first
- **y**: Proceed anyway (clears failure flag)
- **--no-verify**: Bypass hook entirely

## Cleanup Old Runs

```bash
# Clean runs older than 7 days
huskycat clean --max-age 7d

# Clean zombie processes
huskycat clean --zombies

# Clean all validation cache
huskycat clean --all
```

## Performance Tips

### Optimize for Speed

```yaml
# .huskycat.yaml
feature_flags:
  max_workers: 8               # Match CPU cores
  timeout_per_tool: 30.0       # Shorter timeout for faster feedback
  parallel_execution: true     # Enable parallelization
```

### Optimize for Resource Usage

```yaml
# .huskycat.yaml
feature_flags:
  max_workers: 4               # Reduce concurrent workers
  timeout_per_tool: 120.0      # Allow more time per tool
  parallel_execution: false    # Disable parallelization
```

### Optimize Tool Selection

```yaml
# .huskycat.yaml
tools:
  python:
    enabled: true
    tools: [black, ruff, mypy]  # Skip flake8 if ruff covers it
```

## Next Steps

- **Advanced Configuration**: See [Configuration Reference](../configuration.md)
- **Migration Guide**: Upgrading from blocking hooks? See [Migration Guide](../migration/to-nonblocking.md)
- **Performance Tuning**: Optimize for your needs in [Performance Guide](../performance.md)
- **Troubleshooting**: Issues? Check [Troubleshooting Guide](../troubleshooting.md)
- **Architecture**: Understand internals in [Architecture Docs](../architecture/)

## Getting Help

- **Documentation**: https://huskycat.pages.io/
- **Issues**: https://github.com/tinyland/huskycat/issues
- **Discussions**: https://github.com/tinyland/huskycat/discussions
- **Slack**: #huskycat on TinyLand workspace

## Example Projects

See HuskyCat in action:

- **Python Project**: https://github.com/tinyland/huskycat-example-python
- **Multi-Language**: https://github.com/tinyland/huskycat-example-multi
- **CI/CD Integration**: https://github.com/tinyland/huskycat-example-ci

---

**Congratulations!** You're now ready to use HuskyCat's revolutionary non-blocking git hooks with comprehensive validation.

**Key Takeaways:**
- Git commits return in <100ms (300x faster)
- All 15+ tools validated in background (3.75x more comprehensive)
- Real-time TUI progress display
- 7.5x faster with parallel execution
- 4.5x faster with embedded tools

Happy validating!
