# Troubleshooting Guide

Common issues and solutions for HuskyCat.

## Sprint 10 Issues

### Non-Blocking Hooks Issues

#### Commit Still Blocks

**Problem:** Git commit waits for validation instead of returning immediately

**Diagnosis:**
```bash
# Check feature flag
grep nonblocking_hooks .huskycat.yaml

# Check hook implementation
cat .git/hooks/pre-commit | grep -A5 fork

# Check version
huskycat --version  # Should be >= 2.0.0
```

**Solutions:**
```bash
# Enable non-blocking mode
echo "feature_flags:" >> .huskycat.yaml
echo "  nonblocking_hooks: true" >> .huskycat.yaml

# Reinstall hooks
huskycat setup-hooks --force

# Verify environment variable not overriding
unset HUSKYCAT_FEATURE_NONBLOCKING_HOOKS
```

#### No TUI Progress Display

**Problem:** Expected real-time TUI but only seeing log file

**Diagnosis:**
```bash
# Check TUI enabled
grep tui_progress .huskycat.yaml

# Check TTY available
tty

# Check Rich library
python -c "import rich; print(rich.__version__)"
```

**Solutions:**
```bash
# Enable TUI progress
echo "  tui_progress: true" >> .huskycat.yaml

# Install Rich library
pip install rich

# Use log file as fallback (non-TTY environments)
tail -f .huskycat/runs/latest.log
```

#### Previous Failure Not Detected

**Problem:** Able to commit even though previous validation failed

**Diagnosis:**
```bash
# Check last run status
cat .huskycat/runs/last_run.json

# Check cache directory
ls -la .huskycat/runs/
```

**Solutions:**
```bash
# Manually clear failure flag
rm .huskycat/runs/last_run.json

# Enable result caching
echo "  cache_results: true" >> .huskycat.yaml

# Fix permissions
chmod 755 ~/.huskycat/runs/
chmod 644 ~/.huskycat/runs/*.json
```

#### Validation Not Running in Background

**Problem:** Commit succeeds but no validation occurs

**Diagnosis:**
```bash
# Check for background processes
ps aux | grep huskycat

# Check PID files
ls -la .huskycat/runs/pids/

# Check fork succeeded
cat .huskycat/runs/latest.log
```

**Solutions:**
```bash
# Check fork support (Windows may not support)
python -c "import os; os.fork()" 2>&1 | grep -q AttributeError && echo "Fork not supported" || echo "Fork supported"

# Verify write permissions
ls -ld ~/.huskycat/
mkdir -p ~/.huskycat/runs/pids/

# Check logs for errors
cat .huskycat/runs/latest.log

# Fallback to blocking mode (Windows)
export HUSKYCAT_FEATURE_NONBLOCKING_HOOKS=false
```

#### Zombie Processes

**Problem:** Multiple orphaned huskycat processes consuming resources

**Diagnosis:**
```bash
# Check for zombies
ps aux | grep huskycat | grep defunct

# Check PID files
ls -la .huskycat/runs/pids/
```

**Solutions:**
```bash
# Clean up zombies
huskycat clean --zombies

# Manual cleanup
ps aux | grep huskycat | grep defunct | awk '{print $2}' | xargs kill -9

# Clean old PID files
find ~/.huskycat/runs/pids/ -mtime +1 -delete
```

### Embedded Tools Issues

#### Tool Extraction Failed

**Problem:** "Bundled tool not found" error

**Diagnosis:**
```bash
# Check extracted tools
ls -la ~/.huskycat/tools/

# Check bundle version
cat ~/.huskycat/tools/.version

# Check disk space
df -h ~/.huskycat/
```

**Solutions:**
```bash
# Re-extract tools
rm -rf ~/.huskycat/tools/
huskycat validate --staged  # Triggers extraction

# Check extraction permissions
chmod 755 ~/.huskycat/
chmod 755 ~/.huskycat/tools/
chmod +x ~/.huskycat/tools/*

# Verify binary built with tools
unzip -l dist/huskycat | grep tools/
```

#### Container Fallback Warning

**Problem:** "Falling back to container execution" messages

**Diagnosis:**
```bash
# Check execution mode
export HUSKYCAT_LOG_LEVEL=DEBUG
huskycat validate file.py | grep "execution mode"

# Check tool availability
which shellcheck hadolint taplo
```

**Solutions:**
```bash
# Install tools locally
brew install shellcheck hadolint taplo  # macOS
apt install shellcheck  # Ubuntu

# Use fat binary instead
curl -L -o huskycat https://huskycat.pages.io/huskycat-darwin-arm64
chmod +x huskycat
./huskycat validate file.py

# Build fat binary from source
npm run build:fat
```

#### Slow Tool Execution

**Problem:** Validation takes >2s per tool (expected <0.5s)

**Diagnosis:**
```bash
# Check execution mode
export HUSKYCAT_LOG_LEVEL=DEBUG
time huskycat validate file.py

# Check for container usage
ps aux | grep -E 'podman|docker'
```

**Solutions:**
```bash
# Verify using embedded tools
ls ~/.huskycat/tools/

# Force bundled mode
export HUSKYCAT_TOOL_MODE=bundled

# Check tool extraction complete
cat ~/.huskycat/tools/.version

# Rebuild fat binary if needed
npm run build:fat
```

### Parallel Execution Issues

#### Poor Parallelism

**Problem:** Speedup <3x (expected 7.5x)

**Diagnosis:**
```bash
# Check worker count
grep max_workers .huskycat.yaml

# Check CPU cores
nproc  # Linux
sysctl -n hw.ncpu  # macOS

# Monitor CPU usage during validation
top -pid $(pgrep huskycat)
```

**Solutions:**
```bash
# Increase worker count
echo "  max_workers: 8" >> .huskycat.yaml

# Enable parallel execution
echo "  parallel_execution: true" >> .huskycat.yaml

# Check dependencies not creating bottleneck
huskycat validate --dry-run --show-plan

# Reduce timeout to prevent hanging tools
echo "  timeout_per_tool: 30.0" >> .huskycat.yaml
```

#### Tools Timing Out

**Problem:** "Tool timed out after Xs" messages

**Diagnosis:**
```bash
# Check timeout configuration
grep timeout_per_tool .huskycat.yaml

# Check which tools timing out
grep "timed out" .huskycat/runs/latest.log
```

**Solutions:**
```bash
# Increase timeout
echo "  timeout_per_tool: 120.0" >> .huskycat.yaml

# Optimize slow tools (mypy incremental mode)
echo "[mypy]" >> mypy.ini
echo "incremental = true" >> mypy.ini

# Reduce files per validation
huskycat validate src/module.py  # Instead of src/

# Disable slow tools temporarily
# Edit .huskycat.yaml and remove slow tools
```

#### High Resource Usage

**Problem:** Validation consuming excessive CPU/memory

**Diagnosis:**
```bash
# Monitor resource usage
top -pid $(pgrep huskycat)

# Check worker count
grep max_workers .huskycat.yaml
```

**Solutions:**
```bash
# Reduce worker count
echo "  max_workers: 4" >> .huskycat.yaml

# Disable parallel execution
echo "  parallel_execution: false" >> .huskycat.yaml

# Increase per-tool timeout
echo "  timeout_per_tool: 120.0" >> .huskycat.yaml

# Use sequential validation
huskycat validate --no-parallel src/
```

---

## Installation Issues

### Binary Download Fails

**Problem:** `curl` command fails or times out

**Solutions:**

```bash
# Use wget instead of curl
wget -O huskycat https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-amd64

# Use verbose mode to see what's failing
curl -v -L -o huskycat https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-amd64

# Check network connectivity
ping gitlab.com
```

### "Permission denied" When Running Binary

**Problem:** Binary downloads but won't execute

**Solutions:**

```bash
# Make binary executable
chmod +x huskycat

# Check file permissions
ls -l huskycat

# Move to a directory with execute permissions
mkdir -p ~/.local/bin
mv huskycat ~/.local/bin/
```

### macOS "Cannot verify developer" Warning

**Problem:** macOS blocks unsigned binary

**Solutions:**

```bash
# Method 1: Remove quarantine attribute
xattr -d com.apple.quarantine huskycat

# Method 2: Allow in System Settings
# 1. Try to run binary: ./huskycat
# 2. Go to System Settings > Privacy & Security
# 3. Click "Allow Anyway" next to the huskycat warning
# 4. Run binary again and click "Open"

# Method 3: Disable Gatekeeper temporarily (not recommended)
sudo spctl --master-disable
./huskycat --version
sudo spctl --master-enable
```

### Binary Not Found After Installation

**Problem:** `huskycat: command not found`

**Solutions:**

```bash
# Check if binary exists
ls -l ~/.local/bin/huskycat

# Check if directory is in PATH
echo $PATH | grep -q "$HOME/.local/bin" && echo "✓ In PATH" || echo "✗ Not in PATH"

# Add to PATH (bash)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Add to PATH (zsh)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Use full path temporarily
~/.local/bin/huskycat --version
```

---

## Container Runtime Issues

### "No container runtime available"

**Problem:** HuskyCat can't find Podman or Docker

**Solutions:**

```bash
# Check if container runtime is installed
which podman || which docker

# Install Podman (recommended)
# macOS:
brew install podman

# Ubuntu/Debian:
sudo apt-get update && sudo apt-get install -y podman

# Rocky Linux/RHEL:
sudo dnf install -y podman

# Verify installation
podman --version
# or
docker --version
```

### Podman Machine Not Started (macOS)

**Problem:** `Error: unable to connect to Podman socket`

**Solutions:**

```bash
# Initialize Podman machine
podman machine init

# Start Podman machine
podman machine start

# Check status
podman machine list

# Restart if needed
podman machine stop
podman machine start
```

### Docker Permission Denied (Linux)

**Problem:** `permission denied while trying to connect to the Docker daemon socket`

**Solutions:**

```bash
# Method 1: Add user to docker group (recommended)
sudo usermod -aG docker $USER
newgrp docker

# Method 2: Use sudo (not recommended for regular use)
sudo huskycat validate

# Method 3: Use Podman instead (rootless)
brew install podman  # or apt/dnf install
```

### Container Build Fails

**Problem:** `npm run container:build` fails

**Solutions:**

```bash
# Check Podman/Docker is working
podman run --rm hello-world
# or
docker run --rm hello-world

# Clean build cache
podman system prune -a
# or
docker system prune -a

# Rebuild with verbose output
podman build -t huskycat-validator:latest -f ContainerFile . --no-cache
```

---

## Validation Issues

### "Tool not found" Errors

**Problem:** Validator reports missing tool

**Solutions:**

```bash
# HuskyCat should run tools in containers - this usually means container runtime issues
# Check container is working
huskycat status

# Rebuild validation container
cd /path/to/huskycats-bates
npm run container:build

# Verify container has tools
podman run --rm huskycat-validator:latest black --version
```

### Validation Hangs or Times Out

**Problem:** Validation never completes

**Solutions:**

```bash
# Run with verbose logging
HUSKYCAT_LOG_LEVEL=DEBUG huskycat validate

# Check which file is causing the hang
huskycat validate --verbose src/

# Skip slow validators temporarily
huskycat validate --skip-validator mypy

# Increase timeout (if configurable)
export HUSKYCAT_TIMEOUT=300
```

### False Positive Errors

**Problem:** Validator reports errors that aren't real issues

**Solutions:**

```bash
# Check tool-specific configuration
cat pyproject.toml  # Black, MyPy, Ruff config
cat .flake8         # Flake8 config
cat .eslintrc.json  # ESLint config

# Disable specific rules
# In pyproject.toml:
# [tool.flake8]
# ignore = E501,W503

# Update validation schemas
huskycat update-schemas

# Report false positives
# File issue: https://gitlab.com/tinyland/ai/huskycat/-/issues
```

---

## Git Hooks Issues

### Hooks Not Running

**Problem:** Git commits don't trigger validation

**Solutions:**

```bash
# Check hooks are installed
ls -la .git/hooks/

# Reinstall hooks
huskycat setup-hooks --force

# Check hook permissions
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/pre-push

# Verify hooks point to correct binary
cat .git/hooks/pre-commit
head -1 .git/hooks/pre-commit  # Should show correct shebang

# Check Git hooks path
git config core.hooksPath  # Should be empty or .git/hooks
```

### Hooks Too Slow

**Problem:** Pre-commit hook takes too long

**Solutions:**

```bash
# Validate only staged files (should be default)
# Check pre-commit hook uses --staged flag
cat .git/hooks/pre-commit | grep -- --staged

# Skip hooks temporarily
SKIP_HOOKS=1 git commit -m "message"

# Or use git commit flag
git commit --no-verify -m "message"

# Reduce validators in git hooks mode
# Edit .huskycat/config.json to disable slow validators for hooks
```

### Hook Fails on Valid Code

**Problem:** Commit blocked but code looks correct

**Solutions:**

```bash
# Run validation manually to see full output
huskycat validate --staged

# Check for tool version mismatches
huskycat status

# Update schemas
huskycat update-schemas

# Skip hooks if urgent (fix later)
git commit --no-verify -m "urgent: [will fix validation]"
```

---

## MCP Server Issues

### Claude Code Can't Connect

**Problem:** HuskyCat MCP tools not available in Claude Code

**Solutions:**

```bash
# Check MCP configuration
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Verify binary path is correct
which huskycat

# Test MCP server manually
echo '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}' | huskycat mcp-server

# Reconfigure with bootstrap
huskycat bootstrap --force

# Check Claude Code logs
# macOS: ~/Library/Logs/Claude/
# Linux: ~/.config/Claude/logs/
```

### MCP Tools Timeout

**Problem:** MCP validation requests time out

**Solutions:**

```bash
# Check container runtime is working
podman ps

# Reduce scope of validation
# Instead of validating whole directory, validate specific files

# Increase Claude Code timeout (if configurable)
# Edit claude_desktop_config.json to add timeout setting
```

### MCP Server Crashes

**Problem:** MCP server stops responding

**Solutions:**

```bash
# Check for errors in Claude Code logs
tail -f ~/Library/Logs/Claude/mcp-server.log

# Run server with debug logging
HUSKYCAT_LOG_LEVEL=DEBUG huskycat mcp-server

# Restart Claude Code completely
# macOS: Cmd+Q then reopen
# Linux: killall claude; claude &
```

---

## CI/CD Issues

### GitLab CI Job Fails

**Problem:** Validation job fails in GitLab CI

**Solutions:**

```yaml
# Add debug output
validate:all:
  script:
    - huskycat --version
    - huskycat status
    - huskycat --verbose validate --all

# Check container runtime in CI
validate:all:
  before_script:
    - which podman || which docker
    - podman --version || docker --version

# Use correct image
validate:all:
  image: registry.gitlab.com/tinyland/ai/huskycat/validator:latest
```

### GitHub Actions Job Fails

**Problem:** Workflow fails to download or run HuskyCat

**Solutions:**

```yaml
# Add retry logic
- name: Download HuskyCat
  uses: nick-fields/retry@v2
  with:
    timeout_minutes: 5
    max_attempts: 3
    command: |
      curl -L -o /usr/local/bin/huskycat https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-amd64
      chmod +x /usr/local/bin/huskycat

# Verify download
- name: Verify HuskyCat
  run: |
    huskycat --version
    huskycat status
```

### CI Validation Different from Local

**Problem:** CI reports errors that don't appear locally

**Solutions:**

```bash
# Force CI mode locally
huskycat --mode ci validate --all

# Check tool versions
huskycat status  # Local
# Compare with CI job output

# Use same container as CI
podman run --rm -v $(pwd):/workspace registry.gitlab.com/tinyland/ai/huskycat/validator:latest validate --all
```

---

## Performance Issues

### Slow Validation

**Problem:** Validation takes too long

**Solutions:**

```bash
# Identify slow validators
huskycat --verbose validate --all

# Skip slow validators for quick checks
huskycat validate --skip-validator mypy --all

# Use specific validators only
huskycat validate --validator black,ruff --all

# Clean cache
huskycat clean

# Validate changed files only
git diff --name-only | xargs huskycat validate
```

### High Memory Usage

**Problem:** HuskyCat uses too much memory

**Solutions:**

```bash
# Validate in batches
find src/ -name "*.py" | xargs -n 10 huskycat validate

# Limit container memory (Podman)
podman run --memory=2g huskycat-validator:latest

# Clean up old containers
podman system prune -a
```

---

## Architecture Issues

### "exec format error"

**Problem:** Binary won't run due to architecture mismatch

**Solutions:**

```bash
# Check your architecture
uname -m
# x86_64 → Use huskycat-linux-amd64
# aarch64/arm64 → Use huskycat-linux-arm64 or huskycat-darwin-arm64

# Download correct binary
# For ARM64 Linux:
curl -L -o huskycat https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-arm64

# For Apple Silicon:
curl -L -o huskycat https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-darwin-arm64

# Verify binary architecture
file huskycat
```

### Rosetta 2 Issues (macOS Intel Binary on Apple Silicon)

**Problem:** Trying to use Intel binary on Apple Silicon

**Solution:**

```bash
# Use native Apple Silicon binary
curl -L -o huskycat https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-darwin-arm64
chmod +x huskycat
```

---

## Configuration Issues

### Config File Not Found

**Problem:** HuskyCat ignores configuration

**Solutions:**

```bash
# Check config location
huskycat status | grep -i config

# Create config directory
mkdir -p .huskycat

# Create default config
cat > .huskycat/config.json <<EOF
{
  "validators": {
    "python-black": {"enabled": true},
    "mypy": {"enabled": true},
    "flake8": {"enabled": true},
    "ruff": {"enabled": true}
  }
}
EOF
```

### Tool-Specific Config Ignored

**Problem:** Black/MyPy/Flake8 config not respected

**Solutions:**

```bash
# HuskyCat respects standard config files
# Ensure they're in the right location

# Black: pyproject.toml
[tool.black]
line-length = 100

# MyPy: myproject.toml or mypy.ini
[tool.mypy]
strict = true

# Flake8: .flake8 or setup.cfg
[flake8]
max-line-length = 100

# ESLint: .eslintrc.json
{
  "extends": "eslint:recommended"
}
```

---

## Getting Help

### Debug Logging

Enable verbose logging to diagnose issues:

```bash
# Level 1: Basic debug info
huskycat -v validate

# Level 2: More detail
huskycat -vv validate

# Level 3: Maximum verbosity
huskycat -vvv validate

# Or use environment variable
HUSKYCAT_LOG_LEVEL=DEBUG huskycat validate
```

### Collect System Information

When reporting issues, include this information:

```bash
# HuskyCat version and status
huskycat --version
huskycat status

# System information
uname -a
python --version || python3 --version

# Container runtime
podman --version || docker --version

# Git version (if hooks issue)
git --version

# Tool versions
black --version
mypy --version
flake8 --version
```

### Report Issues

File issues on GitLab:

**[https://gitlab.com/tinyland/ai/huskycat/-/issues](https://gitlab.com/tinyland/ai/huskycat/-/issues)**

Include:
1. System information (from above)
2. Full error message
3. Steps to reproduce
4. Expected vs actual behavior
5. Relevant configuration files

---

## Quick Reference

### Common Commands

```bash
# Reset everything
huskycat clean --all
huskycat update-schemas
huskycat setup-hooks --force

# Debug validation
HUSKYCAT_LOG_LEVEL=DEBUG huskycat validate

# Skip hooks
SKIP_HOOKS=1 git commit -m "message"
git push --no-verify

# Force mode
huskycat --mode ci validate --all
huskycat --json validate > results.json

# Check status
huskycat status
podman ps || docker ps
```

### Environment Variables

```bash
# Debug logging
export HUSKYCAT_LOG_LEVEL=DEBUG

# Skip hooks
export SKIP_HOOKS=1

# Force mode
export HUSKYCAT_MODE=cli

# Custom config directory
export HUSKYCAT_CONFIG_DIR=/path/to/config
```

---

For installation help, see [Installation Guide](installation.md).

For binary issues, see [Binary Downloads](binary-downloads.md).

For CLI usage, see [CLI Reference](cli-reference.md).
