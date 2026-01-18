# HuskyCat Binary Installation & GitOps Setup Guide

**Target Audience**: DevOps engineers, SREs, and developers working with GitOps repositories

**Use Case**: Install HuskyCat binary and automatically configure git hooks for GitLab CI, Helm, Kubernetes, Terraform, and Ansible validation

---

## Table of Contents

1. [Quick Start (5 minutes)](#quick-start)
2. [Installation](#installation)
3. [Bootstrap Your Repository](#bootstrap-your-repository)
4. [What Gets Validated](#what-gets-validated)
5. [How It Works](#how-it-works)
6. [Troubleshooting](#troubleshooting)
7. [Performance & Fast Mode](#performance--fast-mode)
8. [Advanced Configuration](#advanced-configuration)
9. [CI Integration](#ci-integration)
10. [FAQ](#faq)

---

## Quick Start

**Goal**: Get HuskyCat running in your GitOps repository in 5 minutes

```bash
# 1. Download binary (one-time setup)
wget https://github.com/yourusername/huskycat/releases/latest/download/huskycat-linux \
  -O ~/.local/bin/huskycat
chmod +x ~/.local/bin/huskycat

# 2. Add to PATH (if not already)
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# 3. Bootstrap your GitOps repository
cd /path/to/your/gitops/repo
huskycat bootstrap

# 4. Done! Try making a commit to see validation in action
```

---

## Installation

### Method 1: Binary Download (Recommended)

**Linux (x86_64)**:
```bash
# Create directory if it doesn't exist
mkdir -p ~/.local/bin

# Download latest release
wget https://github.com/yourusername/huskycat/releases/latest/download/huskycat-linux \
  -O ~/.local/bin/huskycat

# Make executable
chmod +x ~/.local/bin/huskycat

# Verify installation
huskycat --version
```

**macOS (Intel)**:
```bash
mkdir -p ~/.local/bin
wget https://github.com/yourusername/huskycat/releases/latest/download/huskycat-macos-intel \
  -O ~/.local/bin/huskycat
chmod +x ~/.local/bin/huskycat
huskycat --version
```

**macOS (Apple Silicon)**:
```bash
mkdir -p ~/.local/bin
wget https://github.com/yourusername/huskycat/releases/latest/download/huskycat-macos-arm64 \
  -O ~/.local/bin/huskycat
chmod +x ~/.local/bin/huskycat
huskycat --version
```

### Method 2: Package Managers (Future)

```bash
# Ubuntu/Debian (future)
sudo apt install huskycat

# Fedora/RHEL (future)
sudo dnf install huskycat

# macOS Homebrew (future)
brew install huskycat

# Arch Linux (future)
sudo pacman -S huskycat
```

### Add to PATH

If `~/.local/bin` is not in your PATH:

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

**Verify**:
```bash
which huskycat
# Should output: /home/yourusername/.local/bin/huskycat
```

---

## Bootstrap Your Repository

### What is Bootstrap?

The `huskycat bootstrap` command:
1. Analyzes your repository to detect GitOps features
2. Installs 3 git hooks (pre-commit, pre-push, commit-msg)
3. Configures automatic validation based on detected features
4. Reports what features were enabled

### Basic Bootstrap

```bash
cd /path/to/your/repository
huskycat bootstrap
```

**Example Output**:

```
 Bootstrapping HuskyCat...

Repository analysis:
  ✓ GitLab CI detected (.gitlab-ci.yml found)
  ✓ Helm chart detected (chart/ directory)
  ✓ Kubernetes manifests detected (k8s/ directory)
  ✓ Terraform detected (*.tf files)
   GitOps repository - enabling IaC validation!

Installing git hooks:
  ✓ pre-commit installed (.git/hooks/pre-commit)
  ✓ pre-push installed (.git/hooks/pre-push)
  ✓ commit-msg installed (.git/hooks/commit-msg)

 Bootstrap complete!

HuskyCat is now configured for:
  ✓ Python code validation (pre-commit)
  ✓ GitLab CI validation (pre-push)
  ✓ Auto-DevOps validation (pre-push)
  ✓ Helm chart linting (pre-push)
  ✓ Kubernetes manifest validation (pre-push)
  ✓ Terraform validation (pre-commit)
  ✓ Conventional commit format (commit-msg)

Try making a commit to see validation in action!
```

### Repository Types Detected

HuskyCat auto-detects these features:

| Feature | Detection Method | Validation Enabled |
|---------|------------------|-------------------|
| **GitLab CI** | `.gitlab-ci.yml` exists | CI schema validation |
| **Helm Charts** | `chart/` or `charts/` directory | Helm chart linting |
| **Kubernetes** | `k8s/` or `kubernetes/` directory | K8s manifest validation |
| **Terraform** | `*.tf` files in repository | Terraform fmt validation |
| **Ansible** | `playbooks/` or `roles/` directory | Ansible syntax validation |

### Force Re-Bootstrap

If you need to regenerate hooks (e.g., after updating HuskyCat):

```bash
huskycat bootstrap --force
```

This will overwrite existing hooks.

---

## What Gets Validated

### Pre-Commit Hook (Fast - <1 second)

**Triggers**: Before each `git commit`

**Validates**:
-  Python code formatting (Black)
-  Python linting (Ruff)
-  Python type checking (MyPy)
-  YAML syntax (all .yaml/.yml files)
-  Terraform formatting (if .tf files detected)

**Example**:
```bash
$ git add main.py
$ git commit -m "feat: add new feature"

🔍 Validating staged files...
  ✓ main.py: Black formatting OK
  ✓ main.py: Ruff linting OK
  ✓ main.py: MyPy type checking OK
 Pre-commit validation passed
```

### Pre-Push Hook (Fast - <2 seconds)

**Triggers**: Before each `git push`

**Validates**:
-  GitLab CI configuration (`.gitlab-ci.yml` schema)
-  Auto-DevOps compliance (if GitOps repo)
-  Helm chart structure (if Helm detected)
-  Kubernetes manifest YAML (if K8s detected)

**Example**:
```bash
$ git push origin main

🔍 Validating GitLab CI configuration...
  ✓ .gitlab-ci.yml: Valid YAML
  ✓ .gitlab-ci.yml: Schema validation passed
 GitOps repository detected - validating Auto-DevOps/K8s manifests...
  ✓ chart/Chart.yaml: Valid schema
  ✓ k8s/deployments/app.yaml: Valid K8s manifest
 Pre-push validation passed
```

### Commit-Msg Hook (Instant - <100ms)

**Triggers**: After `git commit -m "message"`

**Validates**:
-  Conventional commit format
-  Valid commit type (feat, fix, docs, etc.)
-  Subject line length (<72 chars)

**Example**:
```bash
$ git commit -m "Added new feature"
 Invalid commit message format

Expected format: type(scope): subject
Example: feat(api): add user authentication

Valid types: feat, fix, docs, style, refactor, test, chore
```

**Correct**:
```bash
$ git commit -m "feat: add user authentication"
 Commit message valid
```

---

## How It Works

### Hook Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Developer Workflow                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ├─> git add file.py
                              │
                              ├─> git commit -m "message"
                              │         │
                              │         v
                              │   ┌──────────────────────┐
                              │   │  commit-msg hook     │
                              │   │  Check message format│
                              │   └──────────┬───────────┘
                              │              │
                              │              v
                              │   ┌──────────────────────┐
                              │   │  pre-commit hook     │
                              │   │  Validate staged code│
                              │   │  Black, Ruff, MyPy   │
                              │   └──────────┬───────────┘
                              │              │
                              │              v (if pass)
                              │         Commit created
                              │
                              ├─> git push origin main
                              │         │
                              │         v
                              │   ┌──────────────────────┐
                              │   │  pre-push hook       │
                              │   │  Validate CI & GitOps│
                              │   │  GitLab CI, Helm, K8s│
                              │   └──────────┬───────────┘
                              │              │
                              │              v (if pass)
                              │         Push succeeds
                              │
                              v
                        GitLab CI Pipeline
                     (comprehensive validation)
```

### Binary Execution Modes

HuskyCat hooks use intelligent fallback:

```bash
# Priority 1: Specific binary path (fastest, most reliable)
if [[ -x "/home/user/.local/bin/huskycat" ]]; then
    /home/user/.local/bin/huskycat validate --staged

# Priority 2: Binary in PATH
elif command -v huskycat &> /dev/null; then
    huskycat validate --staged

# Priority 3: UV development mode (fallback for developers)
elif command -v uv &> /dev/null && [[ -d ".venv" ]]; then
    uv run python -m src.huskycat validate --staged

# Priority 4: Error (no installation found)
else
    echo "Error: No HuskyCat installation found"
    exit 1
fi
```

**Why this matters**:
- **Reliability**: Hooks work even if PATH changes
- **Performance**: Direct binary execution is fastest
- **Developer-friendly**: Fallback to UV mode for HuskyCat contributors

### Version Tracking & Auto-Updates

Each hook includes a version marker:

```bash
# HuskyCat Pre-Commit Hook
# Auto-generated by huskycat v2.0.0
# DO NOT EDIT MANUALLY - Regenerate with: huskycat setup-hooks --force
```

**Future enhancement**: When you update the binary, HuskyCat will detect version mismatch and prompt to regenerate hooks.

---

## Troubleshooting

### Hooks Not Running

**Symptom**: Commits succeed without validation

**Check 1**: Verify hooks are installed
```bash
ls -la .git/hooks/ | grep -E 'pre-commit|pre-push|commit-msg'
```

**Expected output**:
```
-rwxr-xr-x  1 user user 1641 Dec  6 12:00 pre-commit
-rwxr-xr-x  1 user user 3207 Dec  6 12:00 pre-push
-rwxr-xr-x  1 user user 1079 Dec  6 12:00 commit-msg
```

**Check 2**: Verify hooks are executable
```bash
test -x .git/hooks/pre-commit && echo "Executable" || echo "Not executable"
```

**Fix**: Re-run bootstrap
```bash
huskycat bootstrap --force
```

### Binary Not Found

**Symptom**: `huskycat: command not found`

**Check**: Verify binary location
```bash
ls -la ~/.local/bin/huskycat
```

**Fix 1**: Add to PATH
```bash
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

**Fix 2**: Re-download binary
```bash
wget https://github.com/yourusername/huskycat/releases/latest/download/huskycat-linux \
  -O ~/.local/bin/huskycat
chmod +x ~/.local/bin/huskycat
```

### Hooks Fail with Permission Denied

**Symptom**: `Permission denied: .git/hooks/pre-commit`

**Fix**: Make hooks executable
```bash
chmod +x .git/hooks/pre-commit .git/hooks/pre-push .git/hooks/commit-msg
```

Or re-run bootstrap:
```bash
huskycat bootstrap --force
```

### Validation Too Slow

**Symptom**: Pre-push hook takes >5 seconds

**Check**: Are you running in fast mode?
```bash
cat .git/hooks/pre-push | grep "auto-devops"
```

**Expected**: Should see `auto-devops --fast`

**Fix**: Update hooks to use fast mode
```bash
huskycat setup-hooks --force
```

**Manual bypass** (if needed):
```bash
# Skip slow validations for this push only
SKIP_GITOPS=1 git push origin main
```

### Bypass Hooks (Emergency)

**Use sparingly** - only when hooks are blocking legitimate work

```bash
# Skip all hooks for this commit
git commit --no-verify -m "emergency fix"

# Skip all hooks for this push
git push --no-verify
```

**Better approach**: Fix the validation issue or use temporary skip:
```bash
# Skip GitOps validation only
SKIP_GITOPS=1 git push

# Skip all hooks for current session
export SKIP_HOOKS=1
git commit -m "message"
git push
unset SKIP_HOOKS
```

---

## Performance & Fast Mode

### Why Fast Mode?

Git hooks should complete in <2 seconds to not disrupt developer flow. HuskyCat uses **fast mode** in pre-push to skip slow operations:

| Operation | Normal Mode | Fast Mode | Time Saved |
|-----------|-------------|-----------|------------|
| Helm template |  Runs | ⏭️ Skipped | ~3s |
| kubectl --dry-run |  Runs | ⏭️ Skipped | ~2s |
| Deployment simulation |  Runs | ⏭️ Skipped | ~5s |
| **Total** | ~7s | ~1.5s | **~5.5s (78%)** |

### What Still Gets Validated

Even in fast mode, you get comprehensive validation:

 **YAML Syntax**: All YAML files parsed
 **Schema Validation**: Helm Chart.yaml, values.yaml checked against schemas
 **Required Fields**: K8s manifests validated for apiVersion, kind
 **GitLab CI**: Full CI configuration schema validation
 **Structure**: Directory structure and file existence

### When Fast Mode is Used

**Automatic**:
- Pre-push hook (always uses `--fast`)
- Pre-commit hook (uses `--fast` for YAML validation)

**Manual**:
```bash
# Use fast mode manually
huskycat auto-devops . --fast

# Full validation (for comprehensive checks)
huskycat auto-devops .
```

### CI Still Runs Full Validation

Your GitLab CI pipeline runs **comprehensive validation** without fast mode:

```yaml
# .gitlab-ci.yml
huskycat:validate:
  stage: validate
  script:
    - huskycat auto-devops  # No --fast flag = full validation
```

This ensures that while hooks are fast, you still get thorough validation before merge.

---

## Advanced Configuration

### Custom Hook Behavior

Create `.huskycat.yaml` in your repository:

```yaml
# .huskycat.yaml
git_hooks:
  pre_commit:
    enabled: true
    tools:
      - black
      - ruff
      - mypy
    # Skip slow tools in hooks
    fast_mode: true

  pre_push:
    enabled: true
    validate_ci: true
    validate_gitops: true
    # Always use fast mode for GitOps validation
    gitops_fast: true

  commit_msg:
    enabled: true
    # Enforce conventional commits
    conventional_commits: true
    # Allow these types
    allowed_types:
      - feat
      - fix
      - docs
      - chore
      - refactor

# Skip validation for specific files
exclude:
  - "*.md"
  - "docs/**"
  - "examples/**"
```

### Environment Variables

Control hook behavior via environment:

```bash
# Skip all hooks (temporary)
export SKIP_HOOKS=1

# Skip only GitOps validation
export SKIP_GITOPS=1

# Enable debug logging
export HUSKYCAT_DEBUG=1

# Force verbose output
export HUSKYCAT_VERBOSE=1
```

### Team Configuration

Share configuration across team:

```bash
# Commit .huskycat.yaml to repo
git add .huskycat.yaml
git commit -m "chore: add HuskyCat configuration"
git push

# Team members run bootstrap
# They automatically get the same configuration
huskycat bootstrap
```

---

## CI Integration

### GitLab CI Example

**Validate in CI pipeline with comprehensive checks**:

```yaml
# .gitlab-ci.yml
include:
  - template: Auto-DevOps.gitlab-ci.yml

stages:
  - validate
  - build
  - test
  - deploy

# Quick validation (fast mode)
validate:quick:
  stage: validate
  image: alpine:latest
  before_script:
    - apk add --no-cache bash curl
    - curl -L https://github.com/yourusername/huskycat/releases/latest/download/huskycat-linux -o /usr/local/bin/huskycat
    - chmod +x /usr/local/bin/huskycat
  script:
    - huskycat auto-devops --fast
  allow_failure: true  # Don't block on quick check

# Comprehensive validation (full mode)
validate:comprehensive:
  stage: validate
  image: alpine:latest
  before_script:
    - apk add --no-cache bash curl helm kubectl
    - curl -L https://github.com/yourusername/huskycat/releases/latest/download/huskycat-linux -o /usr/local/bin/huskycat
    - chmod +x /usr/local/bin/huskycat
  script:
    - huskycat validate --all
    - huskycat ci-validate .gitlab-ci.yml
    - huskycat auto-devops  # Full validation (no --fast)
  artifacts:
    when: always
    reports:
      junit: huskycat-results.xml
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
```

### GitHub Actions Example

```yaml
# .github/workflows/validate.yml
name: HuskyCat Validation

on:
  pull_request:
  push:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install HuskyCat
        run: |
          curl -L https://github.com/yourusername/huskycat/releases/latest/download/huskycat-linux -o /usr/local/bin/huskycat
          chmod +x /usr/local/bin/huskycat

      - name: Validate Code
        run: huskycat validate --all

      - name: Validate GitOps
        run: huskycat auto-devops
```

---

## FAQ

### Q: Do I need to install Python?

**A**: No! The binary is standalone and includes all dependencies.

### Q: Will hooks slow down my commits?

**A**: No. Fast mode ensures hooks complete in <2 seconds.

### Q: What if I don't have kubectl/helm installed locally?

**A**: Fast mode skips those tools. You'll still get YAML and schema validation.

### Q: Can I customize what gets validated?

**A**: Yes! Create `.huskycat.yaml` in your repository (see [Advanced Configuration](#advanced-configuration))

### Q: What happens if hooks fail?

**A**: The commit/push is blocked. Fix the issues or use `--no-verify` to bypass (not recommended).

### Q: How do I update HuskyCat?

**A**: Download the latest binary and re-run bootstrap:
```bash
wget https://github.com/yourusername/huskycat/releases/latest/download/huskycat-linux -O ~/.local/bin/huskycat
chmod +x ~/.local/bin/huskycat
huskycat bootstrap --force
```

### Q: Does this work with pre-commit framework?

**A**: HuskyCat uses direct git hooks for maximum performance. Pre-commit framework integration is planned for future releases.

### Q: What if my repo has .githooks/ directory?

**A**: HuskyCat detects this and uses "tracked hooks mode" instead. Binary mode is only used when no .githooks/ directory exists.

### Q: Can I use HuskyCat in a Docker container?

**A**: Yes! The binary works in Alpine, Ubuntu, and other Linux distributions.

### Q: Is this safe for CI/CD pipelines?

**A**: Yes! HuskyCat is designed for both local development and CI environments.

---

## Next Steps

 **Install HuskyCat** - Download binary and add to PATH
 **Bootstrap Your Repo** - Run `huskycat bootstrap`
 **Test It Out** - Make a commit and see validation in action
 **Add to CI** - Integrate HuskyCat into your GitLab CI pipeline
 **Share with Team** - Commit `.huskycat.yaml` and share installation instructions

**Need Help?**
- 📖 Read the full documentation: https://huskycat.readthedocs.io
- 🐛 Report issues: https://github.com/yourusername/huskycat/issues
- 💬 Ask questions: https://github.com/yourusername/huskycat/discussions

---

**Happy validating! 🐱**
