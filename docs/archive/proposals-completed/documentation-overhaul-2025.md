# Documentation Overhaul Proposal (December 2025)

**Status**: Draft
**Author**: Claude + John Sullivan
**Date**: 2025-12-05
**Related**: Pipeline success with Rocky Linux 10, macOS signing, binary builds

## Executive Summary

Following successful CI/CD pipeline implementation with Rocky Linux 10 builds and macOS code signing, comprehensive documentation research revealed critical gaps and inaccuracies. This proposal outlines a systematic documentation update to:

1. Fix critical inaccuracies (outdated MCP architecture, wrong CLI flags)
2. Add missing binary download/installation guides
3. Create comprehensive CLI reference
4. Update CI/CD documentation with Rocky Linux 10 details
5. Reorganize MkDocs navigation for better UX

**Impact**: Without these updates, users will encounter incorrect setup instructions, broken download links, and confusion about actual vs. documented capabilities.

---

## Research Findings Summary

### Documentation Audit Results

- **Total Documentation**: 15 markdown files, 6,222 lines
- **Quality Score**: 63% (needs significant improvement)
- **Critical Issues**: 5 major gaps identified
- **Missing Sections**: 6 new documents needed

### Critical Issues Identified

| Issue | Severity | Files Affected | Impact |
|-------|----------|---------------|--------|
| MCP Architecture completely outdated | CRITICAL | `docs/mcp-architecture.md` | Misleads users about actual implementation |
| Binary downloads not documented | HIGH | `docs/installation.md` | Users can't easily download pre-built binaries |
| CLI flags documented don't exist | HIGH | `docs/features/mcp-server.md`, `docs/installation.md` | Setup instructions fail |
| Container registry paths outdated | MEDIUM | `docs/gitlab-ci-cd.md`, `docs/gitlab-auto-devops-complete.md` | CI examples broken |
| Git hooks not in MkDocs nav | MEDIUM | `.githooks/README.md` | Good docs hidden |

---

## Proposed Documentation Structure

### New MkDocs Navigation

```yaml
nav:
  - Home: index.md
  - Getting Started:
      - Quick Start: quickstart.md (NEW)
      - Installation: installation.md (UPDATED)
      - Configuration: configuration.md
  - User Guides:
      - CLI Reference: cli-reference.md (NEW)
      - Git Hooks: git-hooks.md (NEW - from .githooks/README.md)
      - Binary Downloads: binary-downloads.md (NEW)
  - Features:
      - MCP Server: features/mcp-server.md (UPDATED)
      - Auto-Fix: features/auto-fix.md (NEW)
  - API Reference:
      - MCP Tools: api/mcp-tools.md (UPDATED)
      - CLI API: api/cli-api.md (NEW)
  - CI/CD:
      - GitLab CI/CD: gitlab-ci-cd.md (UPDATED)
      - GitHub Actions: github-actions.md (NEW)
      - Auto-DevOps: gitlab-auto-devops-complete.md
      - Code Signing: macos-code-signing.md (UPDATED)
  - Architecture:
      - Overview: architecture/overview.md (NEW)
      - Product Modes: architecture/product-modes.md (NEW)
      - MCP Protocol: architecture/mcp-protocol.md (REWRITE of mcp-architecture.md)
  - Troubleshooting: troubleshooting.md (NEW)
```

---

## Priority 1: Critical Fixes (Immediate)

### 1.1 Delete/Rewrite `docs/mcp-architecture.md`

**Current State**:
- Document claims HTTP server, Kubernetes pods, TypeScript execution
- Actual: Simple stdio Python JSON-RPC server

**Action**:
```bash
# Option A: Delete (recommended for now)
rm docs/mcp-architecture.md
# Update mkdocs.yml to remove reference

# Option B: Rewrite as architecture/mcp-protocol.md
# Document actual stdio-based implementation
```

**New Content** (`architecture/mcp-protocol.md`):
```markdown
# MCP Protocol Implementation

HuskyCat implements the Model Context Protocol (MCP) using stdio-based JSON-RPC 2.0.

## Architecture

```
┌──────────────┐                    ┌─────────────────┐
│ Claude Code  │ ◄──── stdio ─────► │ HuskyCat MCP    │
│              │   JSON-RPC 2.0     │ Server          │
└──────────────┘                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ Validation      │
                                    │ Engine          │
                                    └─────────────────┘
```

## Implementation Details

- **Protocol**: JSON-RPC 2.0 over stdin/stdout
- **Transport**: stdio (no HTTP, no ports)
- **File**: `src/huskycat/mcp_server.py`
- **Tools**: Dynamically generated from validator registry
```

**Effort**: 2-3 hours
**Files**: Delete 1, create 1, update mkdocs.yml

---

### 1.2 Fix MCP `--port` Flag References

**Problem**: Documentation claims `mcp-server --port 8080` but flag doesn't exist

**Affected Files**:
-  `docs/installation.md:90-95`
- `docs/features/mcp-server.md:35-38`

**Changes**:
```diff
- ./dist/huskycat mcp-server --port 8080
+ ./dist/huskycat mcp-server  # stdio only, no ports needed
```

**Verification**:
```bash
# Confirm no --port flag exists
uv run python -m src.huskycat mcp-server --help | grep -i port
# Should return nothing
```

**Effort**: 30 minutes
**Files**: 2 updates

---

### 1.3 Document Container Fallback Behavior

**Problem**: Docs claim "container-only" but code has fallback to local execution

**Affected Files**:
- `docs/index.md:6-7`
- `docs/installation.md:127-141`
- `docs/features/mcp-server.md:193-209`

**Changes**:
```diff
- HuskyCat is a **container-only** validation platform
+ HuskyCat uses **containerized validation** when available, with automatic fallback to local execution
```

**Add Section** (`docs/index.md`):
```markdown
## Execution Modes

### Container Mode (Recommended)
- Complete toolchain isolation
- Consistent environment
- Requires Docker/Podman

### Local Fallback Mode
- Automatically activates when containers unavailable
- Uses locally installed tools
- Best-effort validation
```

**Effort**: 1 hour
**Files**: 3 updates

---

## Priority 2: Binary Distribution Documentation

### 2.1 Create `docs/binary-downloads.md`

**Purpose**: Document how to download and install pre-built binaries

**Content Structure**:
```markdown
# Binary Downloads

HuskyCat provides pre-built binaries for all major platforms.

## Supported Platforms

| Platform | Architecture | Binary | Status |
|----------|-------------|--------|--------|
| macOS | Apple Silicon (ARM64) | `huskycat-darwin-arm64` |  Ad-hoc signed |
| Linux | AMD64 (x86_64) | `huskycat-linux-amd64` |  Rocky Linux 10 |
| Linux | ARM64 (aarch64) | `huskycat-linux-arm64` |  Rocky Linux 10 |

## Quick Install

### macOS (Apple Silicon)
```bash
curl -L https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-darwin-arm64 -o huskycat
chmod +x huskycat
sudo mv huskycat /usr/local/bin/
```

### Linux (AMD64)
```bash
curl -L https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-amd64 -o huskycat
chmod +x huskycat
sudo mv huskycat /usr/local/bin/
```

### Linux (ARM64)
```bash
curl -L https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-arm64 -o huskycat
chmod +x huskycat
sudo mv huskycat /usr/local/bin/
```

## Verify Installation

```bash
huskycat --version
huskycat status
```

## Binary Details

### Build Information

- **Linux Binaries**: Built on Rocky Linux 10 (RHEL-compatible)
- **macOS Binary**: Built on macOS 14 (Sonoma), Apple Silicon native
- **Compression**: UPX compressed (Linux only)
- **Signing**: macOS ad-hoc signed (development use)

### Architecture Requirements

**Linux**:
- Rocky Linux 10 requires **x86-64-v3** (modern CPUs only)
- Older CPUs (x86-64-v2) not supported
- glibc-based (compatible with RHEL, Fedora, CentOS, Rocky, Alma)

**macOS**:
- Requires macOS 14+ (Sonoma or newer)
- Apple Silicon only (M1/M2/M3 chips)
- Intel Macs not supported (no Intel runners available)

## SHA256 Checksums

Download checksums from release artifacts:
```bash
curl -L https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-darwin-arm64-signed.sha256
curl -L https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-amd64.sha256
curl -L https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-arm64.sha256
```

Verify:
```bash
shasum -a 256 huskycat  # Should match downloaded .sha256 file
```

## CI/CD Usage

### GitLab CI
```yaml
validate:
  stage: test
  image: rockylinux/rockylinux:10
  before_script:
    - curl -L https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-amd64 -o /usr/local/bin/huskycat
    - chmod +x /usr/local/bin/huskycat
  script:
    - huskycat validate --all
```

### GitHub Actions
```yaml
- name: Install HuskyCat
  run: |
    curl -L https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-amd64 -o huskycat
    chmod +x huskycat
    sudo mv huskycat /usr/local/bin/

- name: Validate
  run: huskycat validate --all
```

## Troubleshooting

### "exec format error"
**Problem**: Downloaded wrong architecture binary

**Solution**:
```bash
# Check your architecture
uname -m

# x86_64 = AMD64 (use huskycat-linux-amd64)
# aarch64 or arm64 = ARM64 (use huskycat-linux-arm64 or huskycat-darwin-arm64)
```

### "command not found"
**Problem**: Binary not in PATH

**Solution**:
```bash
# Option 1: Install to /usr/local/bin (requires sudo)
sudo mv huskycat /usr/local/bin/

# Option 2: Add current directory to PATH
export PATH="$PATH:$(pwd)"

# Option 3: Use full path
./huskycat validate
```

### macOS "cannot be opened because the developer cannot be verified"
**Problem**: macOS Gatekeeper blocking unsigned binary

**Solution**:
```bash
# Remove quarantine attribute
xattr -d com.apple.quarantine huskycat

# Or allow in System Preferences > Security & Privacy
```

---

**Effort**: 3-4 hours
**Files**: 1 new file, update mkdocs.yml

---

### 2.2 Update `docs/installation.md`

**Add Section**: "Quick Install (Binary)"

```markdown
## Quick Install (Recommended)

The fastest way to get started is downloading a pre-built binary:

👉 **See [Binary Downloads](binary-downloads.md) for platform-specific instructions**

### Verify Installation
```bash
huskycat --version
huskycat status
```

## Alternative: Build from Source

(existing content...)
```

**Effort**: 30 minutes
**Files**: 1 update

---

## Priority 3: CLI Reference Documentation

### 3.1 Create `docs/cli-reference.md`

**Purpose**: Comprehensive CLI command reference

**Content Outline**:

```markdown
# CLI Reference

Complete reference for HuskyCat command-line interface.

## Global Options

```bash
huskycat [OPTIONS] COMMAND [ARGS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--version` | Show version and exit | - |
| `--verbose, -v` | Enable verbose output | Off |
| `--config-dir DIR` | Configuration directory | `~/.huskycat` |
| `--mode MODE` | Override product mode | Auto-detect |
| `--json` | Force JSON output | Off |

## Product Modes

HuskyCat auto-detects execution mode based on environment:

| Mode | When Used | Output Format | Interactive |
|------|-----------|---------------|-------------|
| `git_hooks` | Git hooks running | Minimal | Yes (TTY) |
| `ci` | CI/CD pipeline | JUnit XML | No |
| `cli` | Manual execution | Rich terminal | Yes |
| `pipeline` | Pipe composition | JSON | No |
| `mcp` | MCP server | JSON-RPC | No |

Override with `--mode`:
```bash
huskycat --mode ci validate --all  # Force CI mode
```

## Commands

### `validate`

Run validation on Python files.

```bash
huskycat validate [OPTIONS] [FILES...]
```

**Options**:
| Option | Description |
|--------|-------------|
| `--staged` | Validate only staged git files |
| `--all` | Validate all files in repository |
| `--fix` | Auto-fix issues where possible |
| `--interactive` | Prompt for auto-fix decisions |
| `--allow-warnings` | Allow warnings to pass |

**Examples**:
```bash
# Validate staged files (default)
huskycat validate --staged

# Validate specific files
huskycat validate src/main.py tests/test_foo.py

# Validate and auto-fix
huskycat validate --fix

# Validate everything
huskycat validate --all
```

**Exit Codes**:
- `0`: All validations passed
- `1`: Validation failures found
- `2`: Command error or exception

### `setup-hooks`

Install git hooks for automatic validation.

```bash
huskycat setup-hooks [OPTIONS]
```

**Options**:
| Option | Description |
|--------|-------------|
| `--force` | Overwrite existing hooks |

**What Gets Installed**:
- `pre-commit`: Validates staged files
- `pre-push`: Validates CI configuration
- `commit-msg`: Validates commit message format

**Examples**:
```bash
# Install hooks
huskycat setup-hooks

# Force reinstall
huskycat setup-hooks --force
```

### `ci-validate`

Validate CI configuration files.

```bash
huskycat ci-validate [FILES...]
```

**Examples**:
```bash
# Validate GitLab CI
huskycat ci-validate .gitlab-ci.yml

# Validate multiple files
huskycat ci-validate .gitlab-ci.yml .github/workflows/*.yml
```

### `mcp-server`

Start MCP server for Claude Code integration (stdio mode).

```bash
huskycat mcp-server
```

**No options** - stdio only, no ports or configuration.

**Usage**:
```json
// Claude Code MCP config
{
  "huskycat": {
    "command": "huskycat",
    "args": ["mcp-server"]
  }
}
```

### `status`

Show HuskyCat configuration and environment status.

```bash
huskycat status
```

**Output Example**:
```
HuskyCat Status
===============

Version: 1.0.0
Config Directory: /Users/username/.huskycat
Product Mode: cli

Environment:
  Container Runtime: docker (available)
  Git Repository: /Users/username/my-project
  Python Version: 3.11.5
  UV Version: 0.5.8

Tools Available:
  ✓ black
  ✓ ruff
  ✓ mypy
  ✓ flake8
```

### `clean`

Clean cache and temporary files.

```bash
huskycat clean [OPTIONS]
```

**Options**:
| Option | Description |
|--------|-------------|
| `--all` | Remove all cache including schemas |

**Examples**:
```bash
# Clean temporary files
huskycat clean

# Clean everything including schemas
huskycat clean --all
```

### `update-schemas`

Update validation schemas from official sources.

```bash
huskycat update-schemas [OPTIONS]
```

**Options**:
| Option | Description |
|--------|-------------|
| `--force` | Force re-download even if cached |

**Examples**:
```bash
# Update schemas
huskycat update-schemas

# Force update
huskycat update-schemas --force
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HUSKYCAT_MODE` | Override product mode detection | Auto-detect |
| `HUSKYCAT_CONFIG_DIR` | Configuration directory | `~/.huskycat` |
| `SKIP_HOOKS` | Skip git hook validation | Not set |
| `CI` | CI environment indicator | Not set |

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Validation failures |
| `2` | Command error |
| `3` | Configuration error |

## Performance Tips

### Git Hooks Mode
- Validates **only staged files** by default (fast)
- Use `SKIP_HOOKS=1 git commit` to bypass temporarily

### CI Mode
- Use `--all` for comprehensive validation
- Cache `~/.huskycat` directory for faster schema loading

### Container Mode
- First run downloads images (slow)
- Subsequent runs use cached images (fast)
- Use `--json` for machine-readable output
```

**Effort**: 4-5 hours
**Files**: 1 new file, update mkdocs.yml

---

## Priority 4: Update CI/CD Documentation

### 4.1 Update `docs/gitlab-ci-cd.md`

**Add Rocky Linux 10 Section**:

```markdown
## Rocky Linux 10 Builds

HuskyCat binaries are built on Rocky Linux 10 for long-term enterprise support.

### Why Rocky Linux 10?

- **Support**: Through May 2035 (10-year lifecycle)
- **Compatibility**: RHEL-compatible, glibc-based
- **Modern**: x86-64-v3 architecture requirement
- **Enterprise-Ready**: Suitable for production deployments

### Binary Build Example

```yaml
binary:build:linux:
  stage: package
  image: rockylinux/rockylinux:10
  before_script:
    - dnf install -y epel-release
    - dnf install -y git curl gcc python3 python3-pip zlib-devel
    - dnf install -y upx || echo "UPX not available"
  script:
    - uv run pyinstaller --onefile huskycat_main.py
    - upx --best --lzma dist/huskycat || true
```

### macOS Code Signing

Binaries are ad-hoc signed for development use:

```yaml
sign:darwin-arm64:
  stage: sign
  extends: .macos_saas_runners
  script:
    - codesign --force --sign - dist/huskycat-darwin-arm64
    - codesign --verify --verbose dist/huskycat-darwin-arm64
```

**For production signing**, configure these CI/CD variables:
- `APPLE_CERTIFICATE_BASE64` - Developer ID Application cert
- `APPLE_CERTIFICATE_PASSWORD` - Certificate password
- `APPLE_DEVELOPER_ID_CA_G2` - Intermediate certificate
- `APPLE_DEVELOPER_ID_APPLICATION` - Certificate name

See [macOS Code Signing](macos-code-signing.md) for details.
```

**Update Container Registry References**:

```diff
- image: registry.gitlab.com/bates-ils/projects/.../husky-lint:latest
+ image: registry.gitlab.com/tinyland/ai/huskycat/validator:latest
```

**Effort**: 2-3 hours
**Files**: 1 update

---

### 4.2 Create `docs/github-actions.md`

**Purpose**: Document GitHub Actions integration

**Content Structure**:
```markdown
# GitHub Actions Integration

Use HuskyCat in GitHub Actions workflows.

## Quick Start

```yaml
name: Validate

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install HuskyCat
        run: |
          curl -L https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-amd64 -o huskycat
          chmod +x huskycat
          sudo mv huskycat /usr/local/bin/

      - name: Validate Code
        run: huskycat validate --all
```

## Advanced Examples

### Validate Pull Requests Only
(examples...)

### Matrix Builds
(examples...)

### Cache Binary Downloads
(examples...)
```

**Effort**: 2-3 hours
**Files**: 1 new file, update mkdocs.yml

---

## Priority 5: MkDocs Navigation Reorganization

### Update `mkdocs.yml`

**Current Problems**:
- Git hooks documentation not linked
- No CLI reference
- No troubleshooting guide
- Architecture section fragmented

**Proposed Changes**:
```yaml
nav:
  - Home: index.md
  - Getting Started:
      - Quick Start: quickstart.md
      - Installation: installation.md
      - Configuration: configuration.md
  - User Guides:
      - CLI Reference: cli-reference.md
      - Git Hooks: git-hooks.md
      - Binary Downloads: binary-downloads.md
  - Features:
      - MCP Server: features/mcp-server.md
      - Auto-Fix: features/auto-fix.md (if implemented)
  - API Reference:
      - MCP Tools: api/mcp-tools.md
      - CLI API: api/cli-api.md
  - CI/CD:
      - GitLab CI/CD: gitlab-ci-cd.md
      - GitHub Actions: github-actions.md
      - Auto-DevOps: gitlab-auto-devops-complete.md
      - Code Signing: macos-code-signing.md
  - Architecture:
      - Overview: architecture/overview.md
      - Product Modes: architecture/product-modes.md
      - MCP Protocol: architecture/mcp-protocol.md
  - Troubleshooting: troubleshooting.md
```

**Effort**: 1 hour
**Files**: mkdocs.yml update

---

## Implementation Plan

### Phase 1: Critical Fixes (Week 1)
- [ ] Delete/archive `docs/mcp-architecture.md`
- [ ] Fix `--port` flag references (2 files)
- [ ] Document container fallback (3 files)
- [ ] Update container registry paths (2 files)

**Deliverable**: No broken/misleading documentation

### Phase 2: Binary Documentation (Week 1-2)
- [ ] Create `docs/binary-downloads.md`
- [ ] Update `docs/installation.md` with binary quick start
- [ ] Test all download links and installation instructions
- [ ] Verify checksums work correctly

**Deliverable**: Users can easily download and install binaries

### Phase 3: CLI Reference (Week 2)
- [ ] Create `docs/cli-reference.md`
- [ ] Document all commands with examples
- [ ] Verify CLI help output matches documentation
- [ ] Add troubleshooting for common CLI issues

**Deliverable**: Complete CLI documentation

### Phase 4: CI/CD Updates (Week 2-3)
- [ ] Update `docs/gitlab-ci-cd.md` with Rocky Linux 10
- [ ] Create `docs/github-actions.md`
- [ ] Update signing documentation
- [ ] Add CI/CD troubleshooting section

**Deliverable**: Accurate CI/CD integration docs

### Phase 5: Navigation & Polish (Week 3)
- [ ] Reorganize mkdocs.yml navigation
- [ ] Create `docs/troubleshooting.md`
- [ ] Add cross-references between docs
- [ ] Review all docs for consistency

**Deliverable**: Professional documentation site

---

## Testing & Verification

### Before Merging
- [ ] Test all download links work
- [ ] Verify all code examples execute correctly
- [ ] Check all internal doc links resolve
- [ ] Build mkdocs locally and review
- [ ] Spell check all new/updated docs

### User Acceptance
- [ ] Can a new user download binary in <5 min?
- [ ] Can a new user set up git hooks in <10 min?
- [ ] Are all CLI commands documented accurately?
- [ ] Do CI/CD examples work in actual pipelines?

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Documentation accuracy | 60% | 95% |
| Critical inaccuracies | 5 | 0 |
| Missing sections | 6 | 0 |
| User setup time | Unknown | <10 min |
| CI/CD example success rate | Unknown | 100% |

---

## Open Questions

1. **Binary Distribution**:
   - Should we also publish to GitHub Releases for wider distribution?
   - Do we need Windows binaries (WSL support)?

2. **Documentation Hosting**:
   - Is GitLab Pages working correctly?
   - Should we mirror docs on GitHub?

3. **CLI Stability**:
   - Are all CLI commands finalized or might they change?
   - Should we version the CLI API?

4. **MCP Server**:
   - What are the actual tool names generated by the validator registry?
   - Should we stabilize tool names or document dynamic generation?

---

## Approval Required

This proposal requires approval for:
1. Deletion of `docs/mcp-architecture.md` (outdated)
2. Creation of 6 new documentation files
3. Updates to 8 existing files
4. MkDocs navigation reorganization

**Estimated Total Effort**: 20-25 hours over 3 weeks

**Next Steps**:
1. Review and approve this proposal
2. Prioritize which phases to implement
3. Begin Phase 1 (critical fixes)

---

**Proposal Status**: Awaiting Review
**Last Updated**: 2025-12-05
