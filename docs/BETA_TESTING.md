# HuskyCat Beta Testing Guide

Welcome beta testers! Thank you for helping test HuskyCat before the public release.

## What is HuskyCat?

HuskyCat is a universal code validation platform with:
- **Fat binary distribution** - No dependencies, runs standalone
- **Non-blocking git hooks** - Commits complete in <100ms
- **15+ validation tools** - Black, MyPy, Flake8, shellcheck, hadolint, and more
- **AI integration** - MCP server for Claude Code
- **Auto-fix support** - Interactive prompts to fix issues automatically

## Prerequisites

- Git repository (any language - Python, Shell, YAML, TOML, etc.)
- macOS (ARM64 recommended) or Linux (amd64/ARM64)
- Terminal with bash/zsh/fish
- 5 minutes of your time

## Quick Install (2 minutes)

### Option A: One-Line Install (Recommended)

```bash
curl -fsSL https://tinyland.gitlab.io/ai/huskycat/install.sh | bash
```

This will:
1. Detect your platform automatically
2. Download the correct binary
3. Install to `~/.local/bin/huskycat`
4. Extract validation tools to `~/.huskycat/tools/`
5. Create shell completions

### Option B: Manual Install

**Linux (amd64):**
```bash
curl -L 'https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/bin/huskycat-linux-amd64?job=build:binary:linux-amd64' -o huskycat
chmod +x huskycat
./huskycat install
```

**Linux (ARM64):**
```bash
curl -L 'https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/bin/huskycat-linux-arm64?job=build:binary:linux-arm64' -o huskycat
chmod +x huskycat
./huskycat install
```

**macOS (ARM64 - M1/M2/M3/M4):**
```bash
curl -L 'https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/bin/huskycat-darwin-arm64?job=build:binary:darwin-arm64' -o huskycat
chmod +x huskycat
xattr -d com.apple.quarantine huskycat  # Remove macOS quarantine
./huskycat install
```

**macOS (Intel):**
```bash
# Download ARM64 binary and run with Rosetta 2
curl -L 'https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/bin/huskycat-darwin-arm64?job=build:binary:darwin-arm64' -o huskycat
chmod +x huskycat
xattr -d com.apple.quarantine huskycat
arch -x86_64 ./huskycat install
```

## Verify Installation

```bash
huskycat --version
# Expected: huskycat 2.0.0

huskycat status
# Expected output:
# HuskyCat Status
# ===============
# Installation:  ~/.local/bin/huskycat
# Tools:         ~/.huskycat/tools/ (3 tools)
# Mode:          CLI
```

## Setup Git Hooks in Your Repo

Navigate to any git repository and run:

```bash
cd /path/to/your/repo
huskycat setup-hooks
```

Expected output:
```
Installing git hooks to .git/hooks/...
✓ pre-commit hook installed
✓ pre-push hook installed
✓ commit-msg hook installed
```

## Enable Non-Blocking Mode (Recommended)

For super-fast commits that don't block on validation:

```bash
git config --local huskycat.nonblocking true
```

## Test It Works

Make a test commit:

```bash
echo "# test" >> README.md
git add README.md
git commit -m "test: verify huskycat hooks work"
```

**Expected output (with non-blocking mode):**
```
⚡ Non-blocking validation mode enabled
🚀 Launching background validation...
   Validation running in background (PID 12345)
[main abc1234] test: verify huskycat hooks work
 1 file changed, 1 insertion(+)
```

The commit completes immediately while validation runs in the background!

**Expected output (without non-blocking mode):**
```
🚀 Running HuskyCat validation...
✓ black: 1 file passed
✓ mypy: 1 file passed
[main abc1234] test: verify huskycat hooks work
 1 file changed, 1 insertion(+)
```

The commit waits for validation to complete (blocking mode).

## What to Test

Please test these scenarios and report your findings:

### ✅ Core Functionality
- [ ] Binary downloads successfully for your platform
- [ ] Installation to `~/.local/bin/` works
- [ ] Tools extract to `~/.huskycat/tools/` (check with `ls ~/.huskycat/tools/`)
- [ ] Git hooks install in your repo
- [ ] Pre-commit hook runs when you commit
- [ ] Non-blocking mode works (commit completes in <100ms)
- [ ] Validation runs in background

### ✅ Different File Types
- [ ] Python files (`.py`) - uses Black, MyPy, Flake8, Ruff
- [ ] Shell scripts (`.sh`) - uses shellcheck
- [ ] YAML files (`.yaml`, `.yml`) - uses yamllint
- [ ] TOML files (`.toml`) - uses taplo
- [ ] Dockerfiles - uses hadolint

### ✅ Edge Cases
- [ ] Works with no Python files (should skip)
- [ ] Works with large commits (10+ files)
- [ ] Error messages are clear when validation fails
- [ ] `git commit --no-verify` skips hooks
- [ ] `SKIP_HOOKS=1 git commit` works
- [ ] Hooks work after reboot (paths preserved)
- [ ] Multiple commits in succession

### ✅ Performance
- [ ] First commit (tool extraction) takes <30 seconds
- [ ] Subsequent commits with non-blocking take <100ms
- [ ] Validation completes within reasonable time (30s for 10 files)
- [ ] No noticeable lag or freezing

### ✅ Platform-Specific
- [ ] **macOS**: Binary runs without "unverified developer" error (after xattr command)
- [ ] **macOS Intel**: Rosetta 2 execution works
- [ ] **Linux**: Binary has executable permissions
- [ ] PATH is correctly configured
- [ ] Shell completions work (try `huskycat <TAB>`)

## Troubleshooting

### "huskycat: command not found"

**Cause**: `~/.local/bin` not in PATH

**Fix**:
```bash
# Bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Zsh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Fish
fish_add_path ~/.local/bin
```

### macOS: "cannot be opened because the developer cannot be verified"

**Cause**: macOS Gatekeeper quarantine

**Fix**:
```bash
xattr -d com.apple.quarantine ~/.local/bin/huskycat
# Or if already moved:
xattr -d com.apple.quarantine /path/to/downloaded/huskycat
```

### Hooks not running

**Cause**: Hooks not installed or wrong path

**Fix**:
```bash
# Verify hooks installed
ls -la .git/hooks/pre-commit
cat .git/hooks/pre-commit | head -20

# Reinstall hooks
huskycat setup-hooks --force
```

### Tools not found

**Cause**: Tool extraction failed

**Fix**:
```bash
# Check extraction
ls -la ~/.huskycat/tools/
# Should show: shellcheck, hadolint, taplo, versions.txt

# Force re-extraction
rm -rf ~/.huskycat/tools
huskycat validate --help  # Triggers extraction

# Verify
ls -la ~/.huskycat/tools/
```

### Validation fails with "command not found"

**Cause**: Binary tools not in PATH or not executable

**Fix**:
```bash
# Make tools executable
chmod +x ~/.huskycat/tools/*

# Check tools work
~/.huskycat/tools/shellcheck --version
~/.huskycat/tools/hadolint --version
~/.huskycat/tools/taplo --version
```

### Non-blocking mode not working

**Cause**: Git config not set or environment variable missing

**Fix**:
```bash
# Check git config
git config --local --get huskycat.nonblocking
# Should output: true

# Set if missing
git config --local huskycat.nonblocking true

# Verify in hook
cat .git/hooks/pre-commit | grep NONBLOCKING
```

## Reporting Issues

When reporting issues, please include:

### Required Information
1. **Platform & Architecture**: macOS ARM64, Linux amd64, etc.
2. **Command**: Exact command that failed
3. **Full Output**: Complete terminal output (copy/paste)
4. **Binary Version**: Output of `huskycat --version`
5. **Installation Method**: One-line installer or manual
6. **Git Config**: Output of `git config --local --list | grep huskycat`

### Optional but Helpful
- Repository type (public/private, language)
- Number of files in commit
- Git hooks configuration
- Screenshot if UI-related

### Where to Report

**GitLab Issues**: https://gitlab.com/jsullivan2/huskycats-bates/-/issues

**Template**:
```
**Platform**: macOS ARM64 / Linux amd64 / etc.
**Binary Version**: 2.0.0
**Installation Method**: One-line / Manual

**Issue**: Describe what went wrong

**Steps to Reproduce**:
1. Step one
2. Step two
3. etc.

**Expected**: What should happen
**Actual**: What actually happened

**Full Output**:
```
[paste full terminal output here]
```

**Additional Context**: Any other relevant information
```

## Beta Testing Checklist

After testing, please submit this checklist:

### Installation
- [ ] Platform tested: ________________
- [ ] One-line install worked: ✓ / ✗
- [ ] Manual install worked: ✓ / ✗
- [ ] Binary is in PATH: ✓ / ✗
- [ ] Tools extracted successfully: ✓ / ✗

### Git Hooks
- [ ] Hooks setup worked: ✓ / ✗
- [ ] Pre-commit hook runs: ✓ / ✗
- [ ] Non-blocking mode works: ✓ / ✗
- [ ] Validation completes: ✓ / ✗
- [ ] Error messages are clear: ✓ / ✗

### Performance
- [ ] First commit < 30s: ✓ / ✗
- [ ] Non-blocking commits < 100ms: ✓ / ✗
- [ ] Validation reasonable speed: ✓ / ✗
- [ ] No lag or freezing: ✓ / ✗

### Documentation
- [ ] Installation instructions clear: ✓ / ✗
- [ ] Troubleshooting helpful: ✓ / ✗
- [ ] Usage examples work: ✓ / ✗

### Overall Experience
- [ ] Would recommend to colleagues: ✓ / ✗
- [ ] Would use in production: ✓ / ✗

**Rating**: ⭐⭐⭐⭐⭐ (1-5 stars)

**What worked well**:
```
[Your feedback here]
```

**What needs improvement**:
```
[Your feedback here]
```

**Feature requests**:
```
[Your ideas here]
```

## Next Steps

After beta testing:

1. **Submit your checklist** as a GitLab issue or email
2. **Join the discussion** in GitLab issues
3. **Watch for updates** - we'll fix reported issues quickly
4. **Recommend to colleagues** - help us grow!

## Thank You!

Your feedback is invaluable in making HuskyCat production-ready. We truly appreciate you taking the time to test and report issues.

**Questions?** Open an issue: https://gitlab.com/jsullivan2/huskycats-bates/-/issues

**Success story?** Share it! We'd love to hear how HuskyCat improved your workflow.

---

**Beta Testing Period**: December 2025 - January 2026
**Expected Public Release**: February 2026
**Version Tested**: 2.0.0 (Sprint 11 - Fat Binary Bootstrap)
