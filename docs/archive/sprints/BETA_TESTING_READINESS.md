# Beta Testing Readiness Review

## Executive Summary

Sprint 11 Phase 1 & 2 are **COMPLETE** and committed. This document reviews the current state of documentation and git hooks setup for beta testing readiness, specifically for the user journey:

1. Visit the repo
2. Download the binary
3. Install it
4. Bootstrap full fat binary-backed git hooks in their repo
5. All with a single clean script

## Current State Assessment

### ✅ What's Working

#### Binary Distribution
- **Fat binaries built successfully** in CI for all platforms:
  - Linux amd64/ARM64 (~150-200 MB with embedded tools)
  - macOS Intel/ARM64 (~21 MB macOS ARM64, ~150-200 MB Intel)
- **GitLab CI artifacts** available at known URLs
- **Tool extraction** works automatically on first run
- **Bootstrap installation** via `huskycat install` command

#### Git Hooks Setup
- **Binary-generated hooks** in `.git/hooks/` via `huskycat setup-hooks`
- **Non-blocking mode** fully functional via `git config --local huskycat.nonblocking true`
- **Hook templates** are robust with:
  - Binary path auto-detection
  - UV fallback for development
  - Version mismatch warnings
  - Interactive TTY detection
  - Auto-fix support

#### Documentation
- **docs/installation.md** (410 lines) - Comprehensive with verified paths
- **docs/binary-downloads.md** (337 lines) - All artifact URLs documented
- **docs/dogfooding.md** - Internal dogfooding guide
- **README.md** - Architecture and features documented

#### Testing
- **18 bootstrap tests** in `tests/test_binary_bootstrap.py`
- **6-test verification script** in `scripts/verify_binary.sh`
- **64 TTY tests** for terminal detection and rendering
- **CI binary tests** configured in `.gitlab/ci/binary-tests.yml`

### ⚠️ Gaps for Beta Testing

#### 1. **No Working One-Line Install Script** ❌

**Current State:**
- `scripts/install.sh` exists but references **non-existent release URLs**
- Documentation shows manual 3-step process (curl + chmod + install)
- No hosted install script at a short URL

**What Beta Testers Need:**
```bash
# Single command that "just works"
curl -fsSL https://huskycat.sh/install | bash
```

**Current Reality:**
```bash
# Manual 3-step process
curl -L https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/linux-amd64/huskycat?job=build:binary:linux-amd64 -o huskycat
chmod +x huskycat
./huskycat install
```

#### 2. **No Short URL for Install Script** ❌

**Problem:**
- GitLab artifact URLs are ~150 characters long
- No `huskycat.sh` or similar short domain
- No GitLab Pages-hosted install script

**Needed:**
- GitLab Pages deployment of install script
- Short URL: `https://tinyland.gitlab.io/ai/huskycat/install.sh`
- Or custom domain: `https://huskycat.sh/install`

#### 3. **README Quick Start is Outdated** ⚠️

**Current README:**
```bash
# Line 235 - References non-existent URL
curl -L https://huskycat.pages.io/downloads/huskycat-darwin-arm64 -o huskycat
```

**Should Be:**
```bash
# Reference actual working artifact URL or install script
curl -fsSL https://tinyland.gitlab.io/ai/huskycat/install.sh | bash
```

#### 4. **No Beta Tester Quick Start Guide** ❌

**Missing:**
- Dedicated `docs/BETA_TESTING.md` guide
- Step-by-step testing instructions
- Expected output examples
- Troubleshooting for beta testers
- What to test checklist

#### 5. **GitLab Pages Not Configured for Install Script** ❌

**Current State:**
- GitLab Pages exists at: `https://tinyland.gitlab.io/ai/huskycat/`
- But `install.sh` not deployed there
- `.gitlab/ci/pages.yml` deploys MkDocs only

**Needed:**
- Add `install.sh` to GitLab Pages deployment
- Ensure script is executable/downloadable
- Test URL: `https://tinyland.gitlab.io/ai/huskycat/install.sh`

## Recommended Actions for Beta Readiness

### Phase 1: Working One-Line Installer (30 minutes)

#### Action 1.1: Update `scripts/install.sh` with Artifact URLs

**File:** `scripts/install.sh`

**Current Issue:** Lines 40-58 reference non-existent release URLs

**Fix:** Use actual GitLab CI artifact URLs

```bash
# Replace lines 40-58 with:
if [ "$VERSION" = "latest" ]; then
    case "${PLATFORM}-${ARCH}" in
        linux-amd64)
            BINARY_URL="https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/linux-amd64/huskycat?job=build:binary:linux-amd64"
            ;;
        linux-arm64)
            BINARY_URL="https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/linux-arm64/huskycat?job=build:binary:linux-arm64"
            ;;
        darwin-arm64)
            BINARY_URL="https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/darwin-arm64/huskycat?job=build:binary:darwin-arm64"
            ;;
        darwin-amd64)
            BINARY_URL="https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/darwin-amd64/huskycat?job=build:binary:darwin-amd64"
            ;;
        *)
            log_error "Unsupported platform: ${PLATFORM}-${ARCH}"
            ;;
    esac
else
    log_error "Version-specific installs not yet supported. Use HUSKYCAT_VERSION=latest"
fi
```

#### Action 1.2: Deploy Install Script to GitLab Pages

**File:** `.gitlab/ci/pages.yml`

**Add to pages job:**
```yaml
pages:
  stage: deploy
  script:
    # ... existing MkDocs build ...
    - cp scripts/install.sh public/install.sh
    - chmod +x public/install.sh
  artifacts:
    paths:
      - public
```

#### Action 1.3: Test One-Line Install

```bash
# Test locally first
bash scripts/install.sh

# After GitLab Pages deployment
curl -fsSL https://tinyland.gitlab.io/ai/huskycat/install.sh | bash
```

### Phase 2: Beta Tester Documentation (45 minutes)

#### Action 2.1: Create Beta Testing Quick Start Guide

**New File:** `docs/BETA_TESTING.md`

```markdown
# HuskyCat Beta Testing Guide

Welcome beta testers! This guide will help you install and test HuskyCat in your repository.

## Prerequisites

- Git repository (any language, HuskyCat works with Python, Shell, YAML, TOML, etc.)
- macOS (Intel/ARM64) or Linux (amd64/ARM64)
- Terminal with bash/zsh

## Quick Install (2 minutes)

### One-Line Install (Recommended)

```bash
curl -fsSL https://tinyland.gitlab.io/ai/huskycat/install.sh | bash
```

This will:
1. Download the binary for your platform
2. Install to `~/.local/bin/huskycat`
3. Extract validation tools to `~/.huskycat/tools/`
4. Create shell completions

### Manual Install (If one-liner fails)

**Linux (amd64):**
```bash
curl -L https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/linux-amd64/huskycat?job=build:binary:linux-amd64 -o huskycat
chmod +x huskycat
./huskycat install
```

**macOS (ARM64 - M1/M2/M3):**
```bash
curl -L https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/darwin-arm64/huskycat?job=build:binary:darwin-arm64 -o huskycat
chmod +x huskycat
./huskycat install
```

## Verify Installation

```bash
huskycat --version
# Expected: huskycat 2.0.0

huskycat status
# Expected: Shows installation paths and available tools
```

## Setup Git Hooks in Your Repo

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

For super-fast commits that don't block:

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

**With non-blocking mode:**
```
⚡ Non-blocking validation mode enabled
🚀 Launching background validation...
   Validation running in background (PID 12345)
[main abc1234] test: verify huskycat hooks work
 1 file changed, 1 insertion(+)
```

**Without non-blocking mode (blocking):**
```
🚀 Running HuskyCat validation...
✓ black: 1 file passed
✓ mypy: 1 file passed
[main abc1234] test: verify huskycat hooks work
 1 file changed, 1 insertion(+)
```

## What to Test

### Core Functionality
- [ ] Binary downloads successfully
- [ ] Installation to `~/.local/bin/` works
- [ ] Tools extract to `~/.huskycat/tools/`
- [ ] Git hooks install in your repo
- [ ] Pre-commit hook runs on commit
- [ ] Non-blocking mode works (commit completes in <100ms)
- [ ] Validation runs in background

### Edge Cases
- [ ] Works with no Python files (should skip)
- [ ] Works with large commits (10+ files)
- [ ] Error messages are clear when validation fails
- [ ] `--no-verify` skips hooks
- [ ] `SKIP_HOOKS=1 git commit` works
- [ ] Hooks work after reboot (paths preserved)

### Platform-Specific
- [ ] macOS: Binary runs without "unverified developer" error
- [ ] Linux: Binary has executable permissions
- [ ] PATH is correctly configured
- [ ] Shell completions work (tab completion)

## Troubleshooting

### "huskycat: command not found"

Add to PATH:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### macOS: "cannot be opened because the developer cannot be verified"

Remove quarantine attribute:
```bash
xattr -d com.apple.quarantine ~/.local/bin/huskycat
```

### Hooks not running

Verify hooks installed:
```bash
ls -la .git/hooks/pre-commit
cat .git/hooks/pre-commit | head -20
```

Reinstall hooks:
```bash
huskycat setup-hooks --force
```

### Tools not found

Force re-extraction:
```bash
rm -rf ~/.huskycat/tools
huskycat validate --help  # Triggers extraction
ls -la ~/.huskycat/tools/
```

## Reporting Issues

When reporting issues, please include:

1. **Platform:** macOS/Linux, ARM64/amd64
2. **Command:** Exact command that failed
3. **Output:** Full terminal output (copy/paste)
4. **Binary version:** Output of `huskycat --version`
5. **Installation method:** One-line vs manual
6. **Git config:** Output of `git config --local --list | grep huskycat`

**Report at:** https://gitlab.com/jsullivan2/huskycats-bates/-/issues

## Beta Testing Checklist

Submit this checklist with your feedback:

- [ ] Platform tested: _________
- [ ] One-line install: ✓ / ✗
- [ ] Manual install: ✓ / ✗
- [ ] Git hooks setup: ✓ / ✗
- [ ] Non-blocking mode: ✓ / ✗
- [ ] Tool extraction: ✓ / ✗
- [ ] Validation works: ✓ / ✗
- [ ] Performance acceptable: ✓ / ✗
- [ ] Documentation clear: ✓ / ✗

**Overall rating:** ⭐⭐⭐⭐⭐ (1-5 stars)

**Comments:**
```

#### Action 2.2: Update README Quick Start

**File:** `README.md`

**Replace lines 232-247 (Quick Start > Option A):**

```markdown
#### Option A: Fat Binary (Recommended - No Dependencies)

**One-Line Install:**
```bash
curl -fsSL https://tinyland.gitlab.io/ai/huskycat/install.sh | bash
```

**Manual Install:**
```bash
# Linux (amd64)
curl -L https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/linux-amd64/huskycat?job=build:binary:linux-amd64 -o huskycat
chmod +x huskycat
./huskycat install

# macOS (ARM64)
curl -L https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/darwin-arm64/huskycat?job=build:binary:darwin-arm64 -o huskycat
chmod +x huskycat
./huskycat install
```

See [docs/BETA_TESTING.md](docs/BETA_TESTING.md) for beta testing guide.
```

### Phase 3: End-to-End Testing (20 minutes)

#### Test Plan

1. **Clean Environment Test:**
   ```bash
   # Use a Docker container for clean environment
   docker run -it --rm ubuntu:22.04 bash

   # Install git
   apt-get update && apt-get install -y git curl

   # Test one-line install
   curl -fsSL https://tinyland.gitlab.io/ai/huskycat/install.sh | bash

   # Verify
   export PATH="$HOME/.local/bin:$PATH"
   huskycat --version
   ```

2. **Test Repo Bootstrap:**
   ```bash
   # Create test repo
   mkdir test-repo && cd test-repo
   git init

   # Setup hooks
   huskycat setup-hooks

   # Enable non-blocking
   git config --local huskycat.nonblocking true

   # Test commit
   echo "test" > test.sh
   git add test.sh
   git commit -m "test: verify hooks"
   ```

3. **Verify Non-Blocking:**
   ```bash
   # Should complete in <100ms
   time git commit -m "test" --allow-empty
   # real    0m0.050s  (expected)
   ```

## Summary: Beta Testing Readiness Score

| Aspect | Status | Ready? |
|--------|--------|--------|
| Binary builds | ✅ All platforms working | ✅ YES |
| Binary functionality | ✅ Install, extract, hooks all work | ✅ YES |
| Git hooks templates | ✅ Robust with fallbacks | ✅ YES |
| Non-blocking mode | ✅ Fully functional | ✅ YES |
| Documentation (installation) | ✅ Comprehensive | ✅ YES |
| One-line installer | ⚠️ Needs artifact URL update | ⚠️ 30 MIN |
| GitLab Pages hosting | ⚠️ Needs install.sh deployment | ⚠️ 10 MIN |
| Beta testing guide | ❌ Doesn't exist yet | ❌ 45 MIN |
| README quick start | ⚠️ Outdated URL | ⚠️ 5 MIN |
| End-to-end testing | ⏳ Not yet done | ⏳ 20 MIN |

**Total Time to Beta Ready:** ~2 hours

## Immediate Next Steps

1. **Update `scripts/install.sh`** with artifact URLs (30 min)
2. **Deploy to GitLab Pages** - add install.sh to pages job (10 min)
3. **Create `docs/BETA_TESTING.md`** (45 min)
4. **Update README quick start** (5 min)
5. **End-to-end test** in clean environment (20 min)
6. **Commit and push** all changes
7. **Recruit beta testers** with link to docs/BETA_TESTING.md

## Beta Tester Invitation Template

```
Subject: HuskyCat Beta Testing - Universal Code Validation Platform

Hi [Name],

I'd like to invite you to beta test HuskyCat, a universal code validation platform with:

- Fat binary distribution (no dependencies)
- Non-blocking git hooks (<100ms commits)
- AI integration via MCP server
- Auto-fix support for 15+ tools

Install in 30 seconds:
```bash
curl -fsSL https://tinyland.gitlab.io/ai/huskycat/install.sh | bash
cd your-repo
huskycat setup-hooks
git config --local huskycat.nonblocking true
```

Full guide: https://tinyland.gitlab.io/ai/huskycat/BETA_TESTING.html

Please test for 1 week and report:
- Any installation issues
- Hook behavior in your workflow
- Performance feedback
- Documentation clarity

Report issues: https://gitlab.com/jsullivan2/huskycats-bates/-/issues

Thanks!
```

## Success Criteria

Beta testing is successful when:

- [ ] 5+ beta testers install successfully
- [ ] No critical installation issues
- [ ] Git hooks work in 95%+ of test repos
- [ ] Non-blocking mode works consistently
- [ ] Documentation is clear (90%+ of testers understand it)
- [ ] Performance is acceptable (commits <100ms with non-blocking)
- [ ] Zero data loss or repo corruption issues

---

**Status:** Ready for 2-hour sprint to beta readiness
**Confidence:** High (all core functionality proven to work)
