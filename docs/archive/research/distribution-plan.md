# HuskyCat Distribution & API Unification Plan
**Date**: 2026-01-15
**Status**: DEEP RESEARCH COMPLETE - Ready for Review
**Scope**: Cross-platform packaging, API unification, desktop integration, tray application

---

## Executive Summary

This plan addresses the user's comprehensive requirements:

1. **API Parity Audit**: Ensure all invocation methods (CLI, MCP, UV dev, Git Hooks, CI) have identical feature sets
2. **Execution Model Unification**: Address disparity between binary/container and embedded execution
3. **FPM-based Linux Packaging**: RPM and DEB generation for cross-distro portability
4. **macOS PKG Installer**: Complete code signing, notarization, stapling workflow
5. **Desktop/GUI Installer**: Application launcher with icons and .desktop files
6. **Tray Icon Application**: Darwin and GNOME tray icon for global git profile switching

---

## Part 1: API Parity Audit

### Current API Surface by Invocation Method

| Feature | CLI Binary | UV Dev | Git Hooks | MCP Server | Container | Notes |
|---------|------------|--------|-----------|------------|-----------|-------|
| `validate` | Yes | Yes | Yes | Yes (22 tools) | Yes | Core feature |
| `validate --staged` | Yes | Yes | Yes | Yes | Yes | Staged files |
| `validate --fix` | Yes | Yes | Limited | Yes | Limited | Auto-fix |
| `validate --json` | Yes | Yes | N/A | N/A (native) | Yes | JSON output |
| `validate --mode X` | Yes | Yes | N/A | N/A | Yes | Mode override |
| `auto-fix` | Yes | Yes | N/A | N/A | N/A | **Gap: MCP missing** |
| `install` | Yes | N/A | N/A | N/A | N/A | Self-install |
| `setup-hooks` | Yes | Yes | N/A | N/A | N/A | Hook setup |
| `mcp-server` | Yes | Yes | N/A | N/A | Yes | MCP protocol |
| `ci-validate` | Yes | Yes | N/A | N/A | Yes | CI config |
| `auto-devops` | Yes | Yes | N/A | N/A | Yes | Helm/K8s |
| `status` | Yes | Yes | N/A | N/A | Yes | Status info |
| `clean` | Yes | Yes | N/A | N/A | N/A | Cache clean |
| `bootstrap` | Yes | Yes | N/A | N/A | N/A | Claude setup |
| Async validation | N/A | N/A | N/A | Yes (4 tools) | N/A | **Gap: CLI missing** |
| Result history | N/A | N/A | N/A | Yes (4 tools) | N/A | **Gap: CLI missing** |

### Identified API Gaps

#### Gap 1: MCP Missing `auto-fix` Dedicated Tool
**Current**: MCP has `validate` with `fix` parameter
**Missing**: No dedicated `auto-fix` tool for consistency with CLI

#### Gap 2: CLI Missing Async Validation
**Current**: MCP has `validate_async`, `get_task_status`, `list_async_tasks`, `cancel_async_task`
**Missing**: CLI has no equivalent async/background validation mode

#### Gap 3: CLI Missing Result History
**Current**: MCP has `get_last_run`, `get_run_history`, `get_run_results`, `get_running_validations`
**Missing**: CLI has no `huskycat history` or similar command

#### Gap 4: Git Hooks Limited Auto-Fix
**Current**: Auto-fix happens but files not re-staged
**Missing**: Automatic `git add` after auto-fix in hooks mode

### API Unification Recommendations

```yaml
Phase 1 - CLI Parity (Add to CLI):
  - huskycat history              # Show validation history
  - huskycat history --last       # Last run details
  - huskycat history --run-id X   # Specific run details
  - huskycat validate --async     # Background validation
  - huskycat tasks                # List async tasks
  - huskycat tasks --cancel X     # Cancel task

Phase 2 - MCP Parity (Add to MCP):
  - auto_fix tool                 # Dedicated auto-fix
  - ci_validate tool              # CI config validation
  - auto_devops tool              # Helm/K8s validation
  - status tool                   # System status

Phase 3 - Hooks Parity:
  - Auto re-stage after fix       # git add modified files
  - Result persistence            # Save to .huskycat/runs/
```

---

## Part 2: Execution Model Disparity Resolution

### Current Execution Models

```
                    EXECUTION MODELS

+------------------+     +------------------+     +------------------+
|   FAT BINARY     |     |   UV DEV MODE    |     |   CONTAINER      |
+------------------+     +------------------+     +------------------+
| PyInstaller      |     | uv run python    |     | podman/docker    |
| Embedded tools   |     | -m huskycat      |     | run huskycat     |
| Single file      |     | Source execution |     | Image with tools |
+------------------+     +------------------+     +------------------+
        |                        |                        |
        v                        v                        v
+----------------------------------------------------------------+
|                    UNIFIED VALIDATION ENGINE                    |
|                 (src/huskycat/unified_validation.py)            |
+----------------------------------------------------------------+
        |                        |                        |
        v                        v                        v
+------------------+     +------------------+     +------------------+
|   BUNDLED        |     |   LOCAL          |     |   CONTAINER      |
|   TOOLS          |     |   TOOLS          |     |   TOOLS          |
| ~/.huskycat/     |     | In PATH          |     | /usr/bin/        |
| tools/           |     | (black, ruff)    |     | (all tools)      |
+------------------+     +------------------+     +------------------+
```

### Disparity Analysis

#### Problem Statement (from user)
> "I am concerned there is too much of a disparity between the binary / container attached execution model and the embedded execution model; I worry our embedded pattern foregoes the bulk of the actual application and is likely confusing."

#### Current Implementation

**Fat Binary** (`huskycat_main.py`):
- Full Python runtime embedded
- Validation tools (shellcheck, hadolint, taplo) embedded
- Extracts tools to `~/.huskycat/tools/` on first run
- **FULL API** - all commands available

**UV Dev Mode** (`uv run python -m huskycat`):
- Same Python codebase
- Requires local tools in PATH OR container fallback
- **FULL API** - all commands available

**Container Mode** (`podman run huskycat`):
- Full toolchain bundled in container
- Entry point is `huskycat validate`
- **LIMITED API** - primarily validation, no install/setup commands

**MCP Server** (`huskycat mcp-server`):
- Same codebase, different interface (JSON-RPC)
- 22 tools exposed but different naming convention
- **DIFFERENT API SURFACE** - validates but no setup commands

### Resolution Strategy

#### Strategy A: Single Entry Point, Multiple Interfaces

```python
# Proposed unified architecture

class HuskyCat:
    """Single source of truth for all HuskyCat functionality"""

    def __init__(self, adapter: ModeAdapter):
        self.adapter = adapter
        self.engine = ValidationEngine(adapter=adapter)

    # Core validation API
    def validate(self, paths, fix=False, staged=False) -> ValidationResult: ...
    def auto_fix(self, paths) -> FixResult: ...

    # Configuration API
    def install(self, bin_dir, with_claude=False) -> InstallResult: ...
    def setup_hooks(self, force=False) -> HookResult: ...
    def update_schemas(self) -> SchemaResult: ...

    # Query API
    def status(self) -> StatusResult: ...
    def history(self, limit=10) -> List[RunResult]: ...
    def last_run(self) -> Optional[RunResult]: ...

    # Async API
    def validate_async(self, paths, fix=False) -> TaskHandle: ...
    def get_task(self, task_id) -> TaskStatus: ...
    def list_tasks(self, status=None) -> List[TaskStatus]: ...
    def cancel_task(self, task_id) -> bool: ...
```

#### Strategy B: Interface Adapters

```
CLI Interface        MCP Interface        Container Interface
     |                    |                      |
     v                    v                      v
+--------+          +-----------+          +------------+
| ArgParse|          | JSON-RPC  |          | Entrypoint |
| Handler |          | Handler   |          | Script     |
+--------+          +-----------+          +------------+
     |                    |                      |
     +--------------------+----------------------+
                          |
                          v
              +------------------------+
              |   HuskyCat Core API    |
              | (src/huskycat/api.py)  |
              +------------------------+
                          |
                          v
              +------------------------+
              | Unified Validation     |
              | Engine                 |
              +------------------------+
```

### Recommendation

**Create `src/huskycat/api.py`** as the canonical API surface that:
1. All interfaces (CLI, MCP, Container) call into
2. Exposes identical functionality regardless of interface
3. Handles mode-specific behavior internally via adapters

---

## Part 3: FPM-based Linux Packaging

### FPM Overview

[FPM (Effing Package Management)](https://fpm.readthedocs.io/) creates Linux packages from directories without needing distro-specific tooling.

### Proposed GitLab CI Jobs

```yaml
# .gitlab/ci/fpm-packages.yml

variables:
  FPM_VERSION: "1.15.1"
  PACKAGE_VERSION: $CI_COMMIT_TAG
  PACKAGE_RELEASE: "1"

.fpm_base:
  image: ruby:3.2-slim
  before_script:
    - apt-get update && apt-get install -y rpm rpmbuild
    - gem install fpm -v $FPM_VERSION
    - fpm --version

package:rpm:
  extends: .fpm_base
  stage: package
  needs:
    - build:binary:linux-amd64
    - build:binary:linux-arm64
  script:
    - mkdir -p pkg-root/usr/local/bin
    - mkdir -p pkg-root/usr/share/huskycat
    - mkdir -p pkg-root/etc/huskycat
    - mkdir -p pkg-root/usr/share/applications
    - mkdir -p pkg-root/usr/share/icons/hicolor/256x256/apps

    # Copy binaries for each architecture
    - cp dist/bin/huskycat-linux-amd64 pkg-root/usr/local/bin/huskycat

    # Copy resources
    - cp assets/huskycat.desktop pkg-root/usr/share/applications/
    - cp assets/icons/huskycat-256.png pkg-root/usr/share/icons/hicolor/256x256/apps/huskycat.png
    - cp docs/examples/.huskycat.yaml pkg-root/etc/huskycat/huskycat.yaml.example

    # Create RPM with FPM
    - |
      fpm -s dir -t rpm \
        --name huskycat \
        --version ${PACKAGE_VERSION:-2.0.0} \
        --iteration ${PACKAGE_RELEASE} \
        --architecture x86_64 \
        --description "Universal Code Validation Platform" \
        --url "https://tinyland.gitlab.io/ai/huskycat" \
        --maintainer "Jess Sullivan <jess@tinyland.ai>" \
        --license "MIT" \
        --vendor "Tinyland AI" \
        --category "Development/Tools" \
        --depends "git >= 2.0" \
        --after-install scripts/postinstall.sh \
        --before-remove scripts/preremove.sh \
        --config-files /etc/huskycat \
        -C pkg-root \
        .

    - mkdir -p dist/rpm
    - mv *.rpm dist/rpm/
  artifacts:
    paths:
      - dist/rpm/*.rpm
    expire_in: 1 month
  rules:
    - if: $CI_COMMIT_TAG

package:deb:
  extends: .fpm_base
  stage: package
  needs:
    - build:binary:linux-amd64
    - build:binary:linux-arm64
  script:
    - mkdir -p pkg-root/usr/local/bin
    - mkdir -p pkg-root/usr/share/huskycat
    - mkdir -p pkg-root/etc/huskycat
    - mkdir -p pkg-root/usr/share/applications
    - mkdir -p pkg-root/usr/share/icons/hicolor/256x256/apps

    # Copy binary
    - cp dist/bin/huskycat-linux-amd64 pkg-root/usr/local/bin/huskycat

    # Copy resources
    - cp assets/huskycat.desktop pkg-root/usr/share/applications/
    - cp assets/icons/huskycat-256.png pkg-root/usr/share/icons/hicolor/256x256/apps/huskycat.png
    - cp docs/examples/.huskycat.yaml pkg-root/etc/huskycat/huskycat.yaml.example

    # Create DEB with FPM
    - |
      fpm -s dir -t deb \
        --name huskycat \
        --version ${PACKAGE_VERSION:-2.0.0} \
        --iteration ${PACKAGE_RELEASE} \
        --architecture amd64 \
        --description "Universal Code Validation Platform" \
        --url "https://tinyland.gitlab.io/ai/huskycat" \
        --maintainer "Jess Sullivan <jess@tinyland.ai>" \
        --license "MIT" \
        --vendor "Tinyland AI" \
        --category "devel" \
        --depends "git" \
        --after-install scripts/postinstall.sh \
        --before-remove scripts/preremove.sh \
        --config-files /etc/huskycat \
        -C pkg-root \
        .

    - mkdir -p dist/deb
    - mv *.deb dist/deb/
  artifacts:
    paths:
      - dist/deb/*.deb
    expire_in: 1 month
  rules:
    - if: $CI_COMMIT_TAG
```

### Required Assets

```
assets/
  huskycat.desktop          # .desktop file for Linux
  icons/
    huskycat-16.png       # 16x16 icon
    huskycat-32.png       # 32x32 icon
    huskycat-64.png       # 64x64 icon
    huskycat-128.png      # 128x128 icon
    huskycat-256.png      # 256x256 icon
    huskycat.svg          # Vector source
  scripts/
    postinstall.sh        # FPM post-install script
    preremove.sh          # FPM pre-remove script
```

### Desktop Entry File

```ini
# assets/huskycat.desktop
[Desktop Entry]
Version=1.0
Type=Application
Name=HuskyCat
GenericName=Code Validator
Comment=Universal Code Validation Platform
Exec=huskycat-tray
Icon=huskycat
Categories=Development;IDE;
Terminal=false
StartupNotify=true
Keywords=validation;linting;git;hooks;
```

---

## Part 4: macOS PKG Installer

### Extracted Code Signing Patterns

From `.gitlab-ci.yml:316-511`, the current macOS signing workflow:

```bash
# COMPLETE CODE SIGNING WORKFLOW
# Extracted from existing GitLab CI

# ========================================================================
# STEP 1: TEMPORARY KEYCHAIN SETUP
# ========================================================================
KEYCHAIN_NAME="signing.keychain-db"
KEYCHAIN_PASSWORD="$(openssl rand -base64 32)"

# Create keychain with password (required for security set-key-partition-list)
security create-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN_NAME"

# Configure keychain for CI: no timeout, no auto-lock
security set-keychain-settings "$KEYCHAIN_NAME"

# Unlock keychain
security unlock-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN_NAME"

# Set as default keychain for this session
security default-keychain -s "$KEYCHAIN_NAME"

# Add to search list with SystemRootCertificates for trust chain validation
LOGIN_KEYCHAIN="$HOME/Library/Keychains/login.keychain-db"
security list-keychains -d user -s "$KEYCHAIN_NAME" "$LOGIN_KEYCHAIN" /System/Library/Keychains/SystemRootCertificates.keychain

# ========================================================================
# STEP 2: IMPORT CERTIFICATES
# ========================================================================
# Import ONLY Developer ID Certification Authority G2 intermediate
# DO NOT import Apple WWDR CA - G2 - it chains to the wrong root!
if [ -n "$APPLE_DEVELOPER_ID_CA_G2" ]; then
  echo "$APPLE_DEVELOPER_ID_CA_G2" | base64 -d > DeveloperIDG2CA.cer
  security import DeveloperIDG2CA.cer -k "$KEYCHAIN_NAME" -T /usr/bin/codesign -T /usr/bin/productsign -T /usr/bin/pkgbuild -A
  security import DeveloperIDG2CA.cer -k "$LOGIN_KEYCHAIN" -T /usr/bin/codesign -T /usr/bin/productsign -T /usr/bin/pkgbuild -A
fi

# Import Application certificate from .p12
echo "$APPLE_CERTIFICATE_BASE64" | base64 -d > certificate.p12
security import certificate.p12 -k "$KEYCHAIN_NAME" -P "$APPLE_CERTIFICATE_PASSWORD" -T /usr/bin/codesign -A

# Set partition list to allow command-line access without user interaction
# CRITICAL: The -s flag and password are required for headless CI environments
security set-key-partition-list -S apple-tool:,apple: -s -k "$KEYCHAIN_PASSWORD" "$KEYCHAIN_NAME"

# ========================================================================
# STEP 3: CODE SIGNING
# ========================================================================
codesign --force --options runtime --sign "$APPLE_DEVELOPER_ID_APPLICATION" --keychain "$KEYCHAIN_NAME" dist/bin/huskycat-darwin-arm64
codesign --verify --verbose dist/bin/huskycat-darwin-arm64

# ========================================================================
# STEP 4: NOTARIZATION
# ========================================================================
# Create a zip for notarization
ditto -c -k --keepParent dist/bin/huskycat-darwin-arm64 huskycat-darwin-arm64.zip

# Submit for notarization and wait
SUBMISSION_OUTPUT=$(xcrun notarytool submit huskycat-darwin-arm64.zip \
  --apple-id "$APPLE_ID" \
  --password "$APPLE_NOTARIZE_PASSWORD" \
  --team-id "$APPLE_TEAM_ID" \
  --wait 2>&1)

# Extract submission ID and check status
SUBMISSION_ID=$(echo "$SUBMISSION_OUTPUT" | grep "id:" | head -1 | awk '{print $2}')
if echo "$SUBMISSION_OUTPUT" | grep -q "status: Invalid"; then
  xcrun notarytool log "$SUBMISSION_ID" \
    --apple-id "$APPLE_ID" \
    --password "$APPLE_NOTARIZE_PASSWORD" \
    --team-id "$APPLE_TEAM_ID" \
    notarization-log.json
  cat notarization-log.json
  exit 1
fi

# ========================================================================
# STEP 5: STAPLING (for PKG only)
# ========================================================================
# Staple notarization ticket to PKG
xcrun stapler staple HuskyCat-Installer.pkg
xcrun stapler validate HuskyCat-Installer.pkg
```

### Complete macOS PKG Build Job

```yaml
# .gitlab/ci/macos-pkg.yml

package:macos-pkg:
  extends: .macos_saas_runners
  stage: package
  needs:
    - job: sign:darwin-arm64
      artifacts: true
  variables:
    PKG_VERSION: ${CI_COMMIT_TAG:-2.0.0}
  script:
    # ================================================================
    # CREATE PKG STRUCTURE
    # ================================================================
    - echo "Creating macOS PKG installer structure..."
    - mkdir -p pkg-root/usr/local/bin
    - mkdir -p pkg-root/usr/local/share/huskycat
    - mkdir -p pkg-root/Applications/HuskyCat.app/Contents/MacOS
    - mkdir -p pkg-root/Applications/HuskyCat.app/Contents/Resources

    # Copy binary
    - cp dist/bin/huskycat-darwin-arm64 pkg-root/usr/local/bin/huskycat
    - chmod +x pkg-root/usr/local/bin/huskycat

    # ================================================================
    # BUILD COMPONENT PKG
    # ================================================================
    - |
      pkgbuild \
        --root pkg-root \
        --identifier ai.tinyland.huskycat \
        --version $PKG_VERSION \
        --install-location / \
        --scripts assets/macos/scripts \
        huskycat.pkg

    # ================================================================
    # BUILD PRODUCT PKG (Distribution)
    # ================================================================
    - |
      productbuild \
        --distribution distribution.xml \
        --resources assets/macos/resources \
        --package-path . \
        HuskyCat-$PKG_VERSION-unsigned.pkg

    # ================================================================
    # SIGN PKG WITH DEVELOPER ID INSTALLER
    # ================================================================
    - |
      if [ -n "$APPLE_DEVELOPER_ID_INSTALLER" ]; then
        productsign \
          --sign "$APPLE_DEVELOPER_ID_INSTALLER" \
          --keychain "$KEYCHAIN_NAME" \
          HuskyCat-$PKG_VERSION-unsigned.pkg \
          HuskyCat-$PKG_VERSION.pkg
        pkgutil --check-signature HuskyCat-$PKG_VERSION.pkg
      fi

    # ================================================================
    # NOTARIZE PKG
    # ================================================================
    - |
      if [ -n "$APPLE_ID" ]; then
        xcrun notarytool submit HuskyCat-$PKG_VERSION.pkg \
          --apple-id "$APPLE_ID" \
          --password "$APPLE_NOTARIZE_PASSWORD" \
          --team-id "$APPLE_TEAM_ID" \
          --wait
        xcrun stapler staple HuskyCat-$PKG_VERSION.pkg
        xcrun stapler validate HuskyCat-$PKG_VERSION.pkg
      fi

    - mkdir -p dist/macos
    - mv HuskyCat-$PKG_VERSION.pkg dist/macos/
  artifacts:
    paths:
      - dist/macos/*.pkg
    expire_in: 1 month
  rules:
    - if: $CI_COMMIT_TAG
```

### Required CI/CD Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `APPLE_CERTIFICATE_BASE64` | Application .p12 cert (base64) | Yes for signing |
| `APPLE_INSTALLER_CERTIFICATE_BASE64` | Installer .p12 cert (base64) | Yes for PKG |
| `APPLE_CERTIFICATE_PASSWORD` | Certificate password | Yes |
| `APPLE_DEVELOPER_ID_APPLICATION` | "Developer ID Application: Name (TEAMID)" | Yes |
| `APPLE_DEVELOPER_ID_INSTALLER` | "Developer ID Installer: Name (TEAMID)" | Yes for PKG |
| `APPLE_DEVELOPER_ID_CA_G2` | G2 intermediate cert (base64) | Recommended |
| `APPLE_ID` | Apple ID email | Yes for notarization |
| `APPLE_NOTARIZE_PASSWORD` | App-specific password | Yes for notarization |
| `APPLE_TEAM_ID` | Team ID | Yes for notarization |

---

## Part 5: Desktop/GUI Installer Assets

### Required Assets Structure

```
assets/
  icons/
    huskycat.icns          # macOS icon bundle
    huskycat.ico           # Windows icon
    huskycat.svg           # Vector source (used for Linux)
    huskycat-16.png        # Linux sizes
    huskycat-32.png
    huskycat-64.png
    huskycat-128.png
    huskycat-256.png
    huskycat-512.png

  linux/
    huskycat.desktop       # .desktop entry
    huskycat-tray.desktop  # Tray app autostart
    org.huskycat.tray.service  # Systemd user service

  macos/
    Info.plist             # App bundle Info.plist
    entitlements.plist     # Code signing entitlements
    scripts/
      preinstall         # PKG pre-install script
      postinstall        # PKG post-install script
    resources/
      welcome.html       # Installer welcome page
      conclusion.html    # Installer conclusion
      README.html        # Installer readme
      LICENSE            # License for installer
```

### macOS Info.plist for Tray App

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>HuskyCat-Tray</string>
    <key>CFBundleIdentifier</key>
    <string>ai.tinyland.huskycat.tray</string>
    <key>CFBundleName</key>
    <string>HuskyCat</string>
    <key>CFBundleVersion</key>
    <string>2.0.0</string>
    <key>CFBundleIconFile</key>
    <string>huskycat.icns</string>
    <key>LSUIElement</key>
    <true/><!-- Hide from Dock, show only in menu bar -->
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.developer-tools</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
```

---

## Part 6: Darwin & GNOME Tray Icon Application

### Feature Overview

A cross-platform tray/menu bar application for:
1. **Global Git Profile Switching** - Switch between git identities
2. **Validation Status** - Show last validation status
3. **Quick Actions** - Validate current project, view history
4. **Configuration** - Access HuskyCat settings

### Architecture

```
                    TRAY APPLICATION ARCHITECTURE

+------------------------------------------------------------------+
|                      HuskyCat Tray App                           |
+------------------------------------------------------------------+
        |                    |                    |
        v                    v                    v
+----------------+   +----------------+   +----------------+
| Darwin Menu    |   | GNOME AppInd.  |   | Windows Tray   |
| (NSStatusItem) |   | (AppIndicator3)|   | (Future)       |
+----------------+   +----------------+   +----------------+
        |                    |                    |
        +--------------------+--------------------+
                             |
                             v
+------------------------------------------------------------------+
|                    Tray Controller                               |
|  - Git Profile Manager                                           |
|  - Validation Status Monitor                                     |
|  - IPC with HuskyCat CLI                                         |
+------------------------------------------------------------------+
        |                    |
        v                    v
+------------------+   +------------------+
|  State Manager   |   |  Config Manager  |
| ~/.huskycat/     |   | ~/.huskycat/     |
| state.json       |   | config.yaml      |
+------------------+   +------------------+
```

### Git Profile State Management

```yaml
# ~/.huskycat/profiles.yaml
version: 1
active_profile: work

profiles:
  work:
    name: "John Smith"
    email: "john.smith@company.com"
    signing_key: "ABC123DEF"
    scope: global  # or "repo" for per-repo

  personal:
    name: "JohnnyS"
    email: "johnny@personal.dev"
    signing_key: ""
    scope: global

  opensource:
    name: "JohnSmith"
    email: "jsmith@users.noreply.github.com"
    signing_key: "XYZ789ABC"
    scope: global

# Per-repository overrides
repo_overrides:
  "/Users/john/work/project":
    profile: work
    locked: true  # Prevent automatic switching

  "/Users/john/personal/*":  # Glob pattern
    profile: personal
```

### Singleton Pattern for State

```python
# src/huskycat/tray/state.py

import fcntl
import json
import os
from pathlib import Path
from typing import Optional

class TrayStateManager:
    """Singleton state manager for tray application.

    Uses file locking to ensure only one tray instance runs.
    State is persisted across sessions.
    """

    LOCK_FILE = Path.home() / ".huskycat" / "tray.lock"
    STATE_FILE = Path.home() / ".huskycat" / "tray-state.json"
    PROFILES_FILE = Path.home() / ".huskycat" / "profiles.yaml"

    _instance: Optional["TrayStateManager"] = None
    _lock_fd: Optional[int] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def acquire_lock(self) -> bool:
        """Acquire exclusive lock. Returns False if another instance running."""
        try:
            self.LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
            self._lock_fd = os.open(str(self.LOCK_FILE), os.O_CREAT | os.O_RDWR)
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except (OSError, IOError):
            return False

    def release_lock(self) -> None:
        """Release lock on shutdown."""
        if self._lock_fd is not None:
            fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
            os.close(self._lock_fd)
            self._lock_fd = None

    def switch_profile(self, profile_name: str, scope: str = "global") -> bool:
        """Switch to a different git profile."""
        import subprocess
        import yaml

        profiles = yaml.safe_load(self.PROFILES_FILE.read_text())
        profile = profiles.get("profiles", {}).get(profile_name)

        if not profile:
            return False

        git_scope = ["--global"] if scope == "global" else []

        subprocess.run(["git", "config", *git_scope, "user.name", profile["name"]])
        subprocess.run(["git", "config", *git_scope, "user.email", profile["email"]])

        if profile.get("signing_key"):
            subprocess.run(["git", "config", *git_scope, "user.signingkey", profile["signing_key"]])
            subprocess.run(["git", "config", *git_scope, "commit.gpgsign", "true"])
        else:
            subprocess.run(["git", "config", *git_scope, "--unset", "user.signingkey"], check=False)
            subprocess.run(["git", "config", *git_scope, "commit.gpgsign", "false"])

        return True
```

### Technology Choices

#### macOS: Native NSStatusItem (rumps or PyObjC)
```python
from rumps import App, MenuItem

class HuskyCatTray(App):
    def __init__(self):
        super().__init__("HuskyCat", icon="assets/icons/huskycat-template.png")

    @rumps.clicked("Switch Profile")
    def switch_profile(self, _):
        pass
```

#### Linux GNOME: AppIndicator3 (PyGObject)
```python
import gi
gi.require_version('AppIndicator3', '0.1')
gi.require_version('Gtk', '3.0')
from gi.repository import AppIndicator3, Gtk

class HuskyCatTray:
    def __init__(self):
        self.indicator = AppIndicator3.Indicator.new(
            "huskycat-tray",
            "huskycat",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
```

### Implementation Phases

#### Phase 1: Core State Management
- [ ] Create `~/.huskycat/profiles.yaml` schema
- [ ] Implement singleton state manager
- [ ] Add profile switching logic
- [ ] CLI command: `huskycat profile switch <name>`

#### Phase 2: macOS Tray App
- [ ] Create macOS app bundle structure
- [ ] Implement NSStatusItem menu bar
- [ ] Add profile switching UI
- [ ] Add validation status display
- [ ] Code sign and notarize .app

#### Phase 3: Linux GNOME Tray
- [ ] Create AppIndicator3 implementation
- [ ] Add .desktop autostart file
- [ ] Add systemd user service
- [ ] Package in DEB/RPM

#### Phase 4: Integration
- [ ] IPC between tray and CLI
- [ ] Real-time validation status updates
- [ ] Repository detection and auto-profile

---

## Implementation Timeline

### Milestone 1: API Unification (1 week)
- [ ] Create `src/huskycat/api.py` canonical interface
- [ ] Add CLI history commands
- [ ] Add MCP auto_fix tool
- [ ] Wire Git Hooks auto re-stage

### Milestone 2: Linux Packaging (1 week)
- [ ] Create icon assets
- [ ] Create .desktop file
- [ ] Implement FPM RPM job
- [ ] Implement FPM DEB job
- [ ] Test on Rocky Linux, Ubuntu, Debian

### Milestone 3: macOS PKG (1 week)
- [ ] Create PKG structure
- [ ] Implement component/product build
- [ ] Add PKG code signing
- [ ] Add PKG notarization + stapling
- [ ] Test on macOS 14+

### Milestone 4: Tray App Core (2 weeks)
- [ ] Design profile schema
- [ ] Implement state manager
- [ ] Add CLI profile commands
- [ ] Create macOS tray prototype
- [ ] Create GNOME tray prototype

### Milestone 5: Tray App Polish (2 weeks)
- [ ] macOS app bundle
- [ ] Linux autostart/systemd
- [ ] Validation status integration
- [ ] Repository detection
- [ ] Full testing

---

## Success Criteria

### API Parity
- [ ] All 11 CLI commands accessible via MCP
- [ ] All 22+ MCP tools accessible via CLI
- [ ] Git Hooks auto re-stage working

### Linux Packages
- [ ] RPM installs cleanly on Rocky Linux 9
- [ ] DEB installs cleanly on Ubuntu 22.04/24.04
- [ ] .desktop file appears in application menu

### macOS PKG
- [ ] PKG passes Gatekeeper
- [ ] Notarization succeeds
- [ ] Stapling verified
- [ ] Works on macOS 14 Sonoma and 15

### Tray App
- [ ] Single instance enforcement
- [ ] Profile switching works
- [ ] State persists across restarts
- [ ] Works on macOS and GNOME

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Apple signing complexity | High | High | Extract working patterns from existing CI |
| FPM dependency on Ruby | Medium | Low | Pin specific version, test in CI |
| Tray API differences | Medium | Medium | Abstract platform differences early |
| State file corruption | Low | Medium | Use atomic writes, backups |
| Singleton race conditions | Low | High | Use proper file locking |

---

---

## Part 7: SBOM & Full Fat Binary Architecture

### Research Summary

Four specialized research agents completed deep analysis on December 2025 covering:
1. License compliance audit of all bundled/delegated tools
2. PyInstaller bundling feasibility
3. SBOM generation pipeline
4. Container-free architecture design

### License Compliance Matrix

| Tool | License | Bundling Status | Risk Level |
|------|---------|-----------------|------------|
| **Python Tools** | | | |
| black | MIT | ✅ SAFE | None |
| ruff | MIT | ✅ SAFE | None |
| mypy | MIT | ✅ SAFE | None |
| flake8 | MIT | ✅ SAFE | None |
| autoflake | MIT | ✅ SAFE | None |
| isort | MIT | ✅ SAFE | None |
| bandit | Apache-2.0 | ✅ SAFE | None |
| ansible-lint | MIT | ⚠️ LARGE | 51.6MB deps |
| yamllint | GPL-3.0 | 🚨 CANNOT BUNDLE | Copyleft |
| **Binary Tools** | | | |
| shellcheck | GPL-3.0 | 🚨 CANNOT BUNDLE | Copyleft |
| hadolint | GPL-3.0 | 🚨 CANNOT BUNDLE | Copyleft |
| taplo | MIT | ✅ SAFE | None |
| **JavaScript Tools** | | | |
| eslint | MIT | ✅ SAFE | Needs runtime |
| prettier | MIT | ✅ SAFE | Needs runtime |
| **Infrastructure Tools** | | | |
| terraform | BSL 1.1 | ⚠️ CONDITIONAL | v1.6.0+ restricted |
| kubectl | Apache-2.0 | ✅ SAFE | None |
| helm | Apache-2.0 | ✅ SAFE | None |

### 🚨 CRITICAL: GPL Contamination Risk

**Current Implementation is Non-Compliant**:
The existing fat binary bundles `shellcheck` and `hadolint` which are GPL-3.0 licensed. Bundling GPL code in an MIT-licensed binary **violates the GPL** unless the entire binary is relicensed as GPL.

**Required Remediation**:
1. Remove `shellcheck`, `hadolint`, `yamllint` from fat binary
2. Use container-only execution for GPL tools
3. Implement runtime detection with graceful degradation

### Tiered Bundling Strategy

```
TIER 1: BUNDLED (MIT/Apache - Safe to embed)
┌─────────────────────────────────────────────────────────┐
│  black, ruff, mypy, flake8, isort, autoflake, bandit   │
│  taplo, kubectl, helm                                   │
│  Size: ~107MB combined                                  │
└─────────────────────────────────────────────────────────┘

TIER 2: CONTAINER-ONLY (GPL - Cannot bundle)
┌─────────────────────────────────────────────────────────┐
│  shellcheck, hadolint, yamllint                         │
│  Execution: Container delegation only                   │
│  Fallback: Graceful skip with warning                   │
└─────────────────────────────────────────────────────────┘

TIER 3: RUNTIME DETECTION (JavaScript - Optional)
┌─────────────────────────────────────────────────────────┐
│  eslint, prettier                                       │
│  Detection: Local Node.js → Container → Skip            │
│  Bundling: Optional with Bun runtime (~80MB)            │
└─────────────────────────────────────────────────────────┘

TIER 4: CONDITIONAL (BSL - License dependent)
┌─────────────────────────────────────────────────────────┐
│  terraform (v1.5.x only, BSL after v1.6.0)              │
│  Detection: Version check required                      │
│  Alternative: OpenTofu (MPL-2.0)                        │
└─────────────────────────────────────────────────────────┘
```

### Ruff Consolidation Strategy

Ruff (Rust-based, MIT licensed) can replace 4 Python tools:

| Replaced Tool | Ruff Equivalent | Status |
|---------------|-----------------|--------|
| flake8 | `ruff check` | Full compatibility |
| autoflake | `ruff check --fix` | Full compatibility |
| isort | `ruff check --select I` | Full compatibility |
| black | `ruff format` | Near-full compatibility |

**Impact**: Reduces Python tool count from 7 to 4, saves ~15MB

### Fat Binary Architecture

```
HUSKYCAT FAT BINARY (~220MB total)
┌─────────────────────────────────────────────────────────────────┐
│                        PyInstaller Bundle                        │
├─────────────────────────────────────────────────────────────────┤
│  Python Runtime (python-build-standalone)              ~45MB    │
│  ├── musl-libc statically linked                                │
│  └── Minimal stdlib                                             │
├─────────────────────────────────────────────────────────────────┤
│  HuskyCat Application Code                             ~5MB     │
│  ├── src/huskycat/                                              │
│  ├── Validation engine                                          │
│  └── MCP server                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Bundled Python Packages                               ~60MB    │
│  ├── ruff (replaces flake8, autoflake, isort, black)            │
│  ├── mypy + typeshed                                            │
│  ├── bandit                                                     │
│  └── pyyaml, rich, click, etc.                                  │
├─────────────────────────────────────────────────────────────────┤
│  Bundled Binary Tools (MIT/Apache only)                ~30MB    │
│  ├── taplo (TOML)                                               │
│  ├── kubectl                                                    │
│  └── helm                                                       │
├─────────────────────────────────────────────────────────────────┤
│  Optional: Bun Runtime (JavaScript tools)              ~80MB    │
│  ├── eslint                                                     │
│  └── prettier                                                   │
└─────────────────────────────────────────────────────────────────┘

CONTAINER-ONLY TOOLS (NOT bundled)
┌─────────────────────────────────────────────────────────────────┐
│  shellcheck (GPL-3.0)                                           │
│  hadolint (GPL-3.0)                                             │
│  yamllint (GPL-3.0)                                             │
│  ansible-lint (too large: 51.6MB deps)                          │
│  terraform (BSL restricted)                                     │
└─────────────────────────────────────────────────────────────────┘
```

### SBOM Generation Pipeline

**Recommended Format**: CycloneDX 1.5 (security-focused, OWASP standard)

**Toolchain**:
- **Syft**: SBOM generation from source and binaries
- **Grype**: Vulnerability scanning against SBOM
- **Cosign**: Cryptographic signing with Sigstore

```yaml
# .gitlab/ci/sbom.yml

variables:
  SYFT_VERSION: "1.0.1"
  GRYPE_VERSION: "0.74.0"
  COSIGN_VERSION: "2.2.0"

sbom:generate:
  stage: security
  image: alpine:latest
  before_script:
    # Install Syft
    - wget -qO- https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin v${SYFT_VERSION}
    # Install Grype
    - wget -qO- https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin v${GRYPE_VERSION}
    # Install Cosign
    - wget -qO cosign https://github.com/sigstore/cosign/releases/download/v${COSIGN_VERSION}/cosign-linux-amd64
    - chmod +x cosign && mv cosign /usr/local/bin/
  script:
    # Generate SBOM from source (before PyInstaller)
    - syft dir:. -o cyclonedx-json=sbom-source.json

    # Generate SBOM from Python dependencies
    - syft file:requirements.txt -o cyclonedx-json=sbom-python.json

    # Merge SBOMs
    - |
      python3 -c "
      import json
      with open('sbom-source.json') as f: src = json.load(f)
      with open('sbom-python.json') as f: py = json.load(f)
      src['components'].extend(py.get('components', []))
      with open('sbom-merged.json', 'w') as f: json.dump(src, f, indent=2)
      "

    # Vulnerability scan
    - grype sbom:sbom-merged.json --output json > vulnerabilities.json
    - grype sbom:sbom-merged.json --fail-on high

    # Sign SBOM with Cosign (keyless via Sigstore)
    - cosign sign-blob --yes sbom-merged.json --output-signature sbom-merged.json.sig

    # Verify signature
    - cosign verify-blob sbom-merged.json --signature sbom-merged.json.sig --certificate-identity-regexp ".*" --certificate-oidc-issuer-regexp ".*"
  artifacts:
    paths:
      - sbom-merged.json
      - sbom-merged.json.sig
      - vulnerabilities.json
    reports:
      cyclonedx: sbom-merged.json
  rules:
    - if: $CI_COMMIT_TAG
    - if: $CI_PIPELINE_SOURCE == "schedule"
```

### Unified Execution Mode Logic

```python
# src/huskycat/core/execution_router.py

from enum import Enum
from typing import Optional
import shutil
import subprocess
from pathlib import Path

class ToolLicense(Enum):
    MIT = "mit"
    APACHE = "apache"
    GPL = "gpl"
    BSL = "bsl"

class ExecutionMode(Enum):
    BUNDLED = "bundled"      # Extracted from fat binary
    LOCAL = "local"          # Found in system PATH
    CONTAINER = "container"  # Delegate to container
    UNAVAILABLE = "unavailable"

# License registry - determines bundling eligibility
TOOL_LICENSES = {
    # Tier 1: Safe to bundle
    "ruff": ToolLicense.MIT,
    "mypy": ToolLicense.MIT,
    "bandit": ToolLicense.APACHE,
    "taplo": ToolLicense.MIT,
    "kubectl": ToolLicense.APACHE,
    "helm": ToolLicense.APACHE,

    # Tier 2: GPL - Container only
    "shellcheck": ToolLicense.GPL,
    "hadolint": ToolLicense.GPL,
    "yamllint": ToolLicense.GPL,

    # Tier 3: Conditional
    "terraform": ToolLicense.BSL,
}

class ExecutionRouter:
    """Routes tool execution based on license compliance and availability."""

    def __init__(self):
        self.bundled_path = Path.home() / ".huskycat" / "tools"
        self.container_available = self._check_container_runtime()

    def get_execution_mode(self, tool: str) -> ExecutionMode:
        """Determine best execution mode respecting license compliance."""
        license_type = TOOL_LICENSES.get(tool, ToolLicense.MIT)

        # GPL tools MUST use container - never bundle
        if license_type == ToolLicense.GPL:
            if self.container_available:
                return ExecutionMode.CONTAINER
            return ExecutionMode.UNAVAILABLE

        # BSL tools need version check
        if license_type == ToolLicense.BSL:
            return self._check_bsl_compliance(tool)

        # MIT/Apache: prefer bundled → local → container
        if self._is_bundled(tool):
            return ExecutionMode.BUNDLED

        if self._is_local(tool):
            return ExecutionMode.LOCAL

        if self.container_available:
            return ExecutionMode.CONTAINER

        return ExecutionMode.UNAVAILABLE

    def _is_bundled(self, tool: str) -> bool:
        """Check if tool is available in bundled path."""
        tool_path = self.bundled_path / tool
        return tool_path.exists() and tool_path.is_file()

    def _is_local(self, tool: str) -> bool:
        """Check if tool is available in system PATH."""
        return shutil.which(tool) is not None

    def _check_container_runtime(self) -> bool:
        """Check if podman or docker is available."""
        return shutil.which("podman") or shutil.which("docker")

    def _check_bsl_compliance(self, tool: str) -> ExecutionMode:
        """Check BSL version compliance (terraform < 1.6.0 is MPL)."""
        if tool != "terraform":
            return ExecutionMode.UNAVAILABLE

        # Check local terraform version
        local_path = shutil.which("terraform")
        if local_path:
            try:
                result = subprocess.run(
                    ["terraform", "version", "-json"],
                    capture_output=True, text=True
                )
                import json
                version = json.loads(result.stdout)["terraform_version"]
                major, minor, _ = version.split(".")
                if int(major) == 1 and int(minor) < 6:
                    return ExecutionMode.LOCAL  # MPL version, safe
            except Exception:
                pass

        # Suggest OpenTofu as alternative
        if shutil.which("tofu"):
            return ExecutionMode.LOCAL

        if self.container_available:
            return ExecutionMode.CONTAINER

        return ExecutionMode.UNAVAILABLE
```

### Container Thin Wrapper

With GPL tools removed from fat binary, the container becomes a thin wrapper for GPL-only execution:

```dockerfile
# ContainerFile.gpl-tools
# Minimal container for GPL tools only

FROM alpine:3.19 AS gpl-tools

# Install only GPL-licensed tools
RUN apk add --no-cache \
    shellcheck \
    hadolint \
    yamllint \
    && rm -rf /var/cache/apk/*

# Verify tools
RUN shellcheck --version && \
    hadolint --version && \
    yamllint --version

ENTRYPOINT ["/bin/sh", "-c"]
```

**Container Size**: ~50MB (vs current ~500MB)

### Migration Path

```
PHASE 1: License Remediation (Immediate)
├── Remove shellcheck from fat binary
├── Remove hadolint from fat binary
├── Remove yamllint from fat binary
├── Update execution router to use container for GPL tools
└── Add license compliance checks to CI

PHASE 2: Ruff Consolidation (Short-term)
├── Replace black with ruff format
├── Replace flake8 with ruff check
├── Replace autoflake with ruff check --fix
├── Replace isort with ruff check --select I
└── Remove legacy tool references

PHASE 3: SBOM Pipeline (Medium-term)
├── Add syft SBOM generation
├── Add grype vulnerability scanning
├── Add cosign signing
├── Publish SBOMs with releases
└── Add SBOM verification to install

PHASE 4: Fat Binary Optimization (Long-term)
├── Evaluate python-build-standalone
├── Evaluate Bun for JavaScript tools
├── Implement musl-libc static linking
├── Target ~150MB final binary size
└── Full multi-arch support
```

### Risk Assessment Update

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GPL violation (current) | **CONFIRMED** | Critical | Remove GPL tools from bundle immediately |
| SBOM generation complexity | Medium | Low | Use proven Syft/Grype toolchain |
| Ruff compatibility gaps | Low | Medium | Test extensively before migration |
| Container runtime dependency | Medium | Medium | Clear error messages, graceful degradation |
| Binary size regression | Low | Low | Monitor size in CI, set thresholds |

---

## Part 8: Container Thin Wrapper & Dual Licensing Architecture

### Current Problem Analysis

The existing `ContainerFile` is a **fat container** (~500MB) that bundles:
- Python 3.11 runtime + 20+ packages
- Node.js runtime + eslint/prettier/typescript
- Go toolchain (commented out)
- Rust binaries (taplo)
- GPL tools (shellcheck, hadolint, yamllint)
- Terraform (BSL licensed)
- Full application code

**Issues**:
1. Duplicates functionality of fat binary
2. Bundles GPL tools alongside MIT code
3. Large image size slows CI/CD
4. Container becomes primary execution path, not fallback

### Target Architecture: Thin Wrapper

```
CURRENT (Fat Container)                    TARGET (Thin Wrapper)
┌─────────────────────────┐               ┌─────────────────────────┐
│    FULL TOOLCHAIN       │               │    MINIMAL WRAPPER      │
│  ┌───────────────────┐  │               │  ┌───────────────────┐  │
│  │ Python 3.11       │  │               │  │ Alpine + bash     │  │
│  │ Node.js           │  │               │  │ Container runtime │  │
│  │ 20+ Python pkgs   │  │      →        │  │ IPC client        │  │
│  │ shellcheck (GPL)  │  │               │  └───────────────────┘  │
│  │ hadolint (GPL)    │  │               │         │               │
│  │ yamllint (GPL)    │  │               │         v               │
│  │ taplo, terraform  │  │               │  Delegates to:          │
│  │ HuskyCat app      │  │               │  - Fat binary           │
│  └───────────────────┘  │               │  - GPL sidecar          │
│        ~500MB           │               │  - Tool containers      │
└─────────────────────────┘               │        ~20MB            │
                                          └─────────────────────────┘
```

### Dual Licensing Strategy

#### Option A: FSL-1.1-MIT (Functional Source License)

```
FSL-1.1-MIT License Structure
┌────────────────────────────────────────────────────────────────┐
│  YEAR 0-2: Functional Source License 1.1                       │
│  ├── Source available, not open source                         │
│  ├── Can view, fork, modify for internal use                   │
│  ├── Cannot compete commercially                               │
│  └── Change date: 2 years from release                         │
├────────────────────────────────────────────────────────────────┤
│  YEAR 2+: Automatically converts to MIT                        │
│  ├── Full open source                                          │
│  ├── Commercial use allowed                                    │
│  └── No restrictions                                           │
└────────────────────────────────────────────────────────────────┘
```

**Pros**: Clear path to MIT, used by HashiCorp (BSL), Sentry, others
**Cons**: Not OSI-approved during FSL period

#### Option B: zlib + Apache-2.0 Hybrid

```
zlib/libpng License (Core)
┌────────────────────────────────────────────────────────────────┐
│  HuskyCat Core Application                                     │
│  ├── Permissive, public domain-like                            │
│  ├── No copyleft, no attribution required in binary            │
│  ├── Can be embedded, modified, redistributed                  │
│  └── Very compatible with proprietary use                      │
└────────────────────────────────────────────────────────────────┘

Apache-2.0 (Dependencies)
┌────────────────────────────────────────────────────────────────┐
│  Third-party components, plugins, extensions                   │
│  ├── Patent grant protection                                   │
│  ├── Attribution required                                      │
│  └── OSI-approved, widely accepted                             │
└────────────────────────────────────────────────────────────────┘
```

**Pros**: OSI-approved, clear patent protection
**Cons**: Requires separate license files, more complex

#### Recommended: Dual License (User's Choice)

```
LICENSE
├── SPDX-License-Identifier: (zlib OR Apache-2.0)
├── Users choose which license applies to their use
├── zlib for embedding/modification without attribution
└── Apache-2.0 for patent protection needs
```

### IPC-Based GPL Tool Isolation

#### Architecture Overview

```
HUSKYCAT PROCESS ISOLATION ARCHITECTURE

┌─────────────────────────────────────────────────────────────────────┐
│                     MAIN PROCESS (zlib/Apache-2.0)                  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  HuskyCat Application                                          │  │
│  │  ├── Validation Engine                                         │  │
│  │  ├── MCP Server                                                │  │
│  │  ├── CLI Interface                                             │  │
│  │  └── IPC Client ────────────────────────┐                      │  │
│  └─────────────────────────────────────────│──────────────────────┘  │
│                                            │                         │
│  BUNDLED TOOLS (MIT/Apache)                │                         │
│  ├── ruff, mypy, bandit                    │                         │
│  └── taplo, kubectl, helm                  │                         │
└────────────────────────────────────────────│─────────────────────────┘
                                             │
                    PROCESS BOUNDARY         │  Unix Socket / Named Pipe
                    (License Firewall)       │
                                             │
┌────────────────────────────────────────────│─────────────────────────┐
│                     GPL SIDECAR PROCESS                              │
│  ┌─────────────────────────────────────────v──────────────────────┐  │
│  │  IPC Server (GPL-3.0 licensed wrapper)                         │  │
│  │  ├── JSON-RPC 2.0 protocol                                     │  │
│  │  ├── Request: {"tool": "shellcheck", "args": [...]}            │  │
│  │  └── Response: {"exitCode": 0, "stdout": "...", "stderr": ""} │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  GPL TOOLS                                                           │
│  ├── shellcheck (GPL-3.0)                                           │
│  ├── hadolint (GPL-3.0)                                             │
│  └── yamllint (GPL-3.0)                                             │
└──────────────────────────────────────────────────────────────────────┘
```

#### IPC Protocol Design

```python
# src/huskycat/core/ipc/protocol.py

"""
GPL Tool Isolation Protocol

This module provides IPC communication with GPL-licensed tools
running in a separate process. The process boundary provides
license isolation - the main HuskyCat process (zlib/Apache-2.0)
never links or bundles GPL code.

Protocol: JSON-RPC 2.0 over Unix domain socket
Socket path: /tmp/huskycat-gpl-$UID.sock (or ~/.huskycat/gpl.sock)
"""

from dataclasses import dataclass
from typing import Optional, List
import json


@dataclass
class ToolRequest:
    """Request to execute a GPL tool."""
    jsonrpc: str = "2.0"
    method: str = "execute"
    id: int = 1
    params: dict = None

    def to_json(self) -> str:
        return json.dumps({
            "jsonrpc": self.jsonrpc,
            "method": self.method,
            "id": self.id,
            "params": self.params or {}
        })


@dataclass
class ToolResponse:
    """Response from GPL tool execution."""
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    tool: str

    @classmethod
    def from_json(cls, data: str) -> "ToolResponse":
        obj = json.loads(data)
        result = obj.get("result", {})
        return cls(
            exit_code=result.get("exit_code", 1),
            stdout=result.get("stdout", ""),
            stderr=result.get("stderr", ""),
            duration_ms=result.get("duration_ms", 0),
            tool=result.get("tool", "unknown")
        )


# Example request/response:
#
# Request:
# {
#   "jsonrpc": "2.0",
#   "method": "execute",
#   "id": 1,
#   "params": {
#     "tool": "shellcheck",
#     "args": ["-f", "json", "script.sh"],
#     "stdin": null,
#     "cwd": "/workspace",
#     "timeout_ms": 30000
#   }
# }
#
# Response:
# {
#   "jsonrpc": "2.0",
#   "id": 1,
#   "result": {
#     "tool": "shellcheck",
#     "exit_code": 0,
#     "stdout": "[{\"file\":\"script.sh\",...}]",
#     "stderr": "",
#     "duration_ms": 125.4
#   }
# }
```

#### GPL Sidecar Implementation

```python
#!/usr/bin/env python3
# gpl-sidecar/server.py
# SPDX-License-Identifier: GPL-3.0-only
#
# This file is GPL-3.0 licensed because it bundles/executes GPL tools.
# It runs as a separate process and communicates via IPC only.

"""
GPL Tool Sidecar Server

This server provides IPC access to GPL-licensed validation tools.
It must be distributed separately from the main HuskyCat binary
to maintain license compliance.

Supported tools:
- shellcheck (GPL-3.0) - Shell script analysis
- hadolint (GPL-3.0) - Dockerfile linting
- yamllint (GPL-3.0) - YAML validation
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

SOCKET_PATH = os.environ.get(
    "HUSKYCAT_GPL_SOCKET",
    f"/tmp/huskycat-gpl-{os.getuid()}.sock"
)

ALLOWED_TOOLS = {
    "shellcheck": "/usr/bin/shellcheck",
    "hadolint": "/usr/bin/hadolint",
    "yamllint": "/usr/bin/yamllint",
}


async def handle_request(reader, writer):
    """Handle a single JSON-RPC request."""
    data = await reader.read(65536)
    if not data:
        writer.close()
        return

    try:
        request = json.loads(data.decode())
        params = request.get("params", {})
        tool = params.get("tool")

        if tool not in ALLOWED_TOOLS:
            response = {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {"code": -32602, "message": f"Unknown tool: {tool}"}
            }
        else:
            result = await execute_tool(
                tool=tool,
                args=params.get("args", []),
                cwd=params.get("cwd"),
                stdin=params.get("stdin"),
                timeout=params.get("timeout_ms", 30000) / 1000
            )
            response = {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": result
            }

    except Exception as e:
        response = {
            "jsonrpc": "2.0",
            "id": request.get("id", 0),
            "error": {"code": -32603, "message": str(e)}
        }

    writer.write(json.dumps(response).encode())
    await writer.drain()
    writer.close()


async def execute_tool(tool: str, args: list, cwd: str = None,
                       stdin: str = None, timeout: float = 30) -> dict:
    """Execute a GPL tool and return results."""
    import time
    start = time.monotonic()

    cmd = [ALLOWED_TOOLS[tool]] + args

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE if stdin else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd
    )

    stdout, stderr = await asyncio.wait_for(
        proc.communicate(stdin.encode() if stdin else None),
        timeout=timeout
    )

    return {
        "tool": tool,
        "exit_code": proc.returncode,
        "stdout": stdout.decode(),
        "stderr": stderr.decode(),
        "duration_ms": (time.monotonic() - start) * 1000
    }


async def main():
    """Start the GPL sidecar server."""
    # Remove stale socket
    socket_path = Path(SOCKET_PATH)
    socket_path.unlink(missing_ok=True)

    server = await asyncio.start_unix_server(handle_request, SOCKET_PATH)
    print(f"GPL Sidecar listening on {SOCKET_PATH}", file=sys.stderr)

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
```

### Container Architecture Transformation

#### New ContainerFile: Thin Wrapper

```dockerfile
# ContainerFile.wrapper
# SPDX-License-Identifier: zlib OR Apache-2.0
#
# Thin wrapper container for HuskyCat
# Delegates to fat binary or chained containers

FROM alpine:3.19 AS wrapper

# Minimal runtime only
RUN apk add --no-cache \
    bash \
    curl \
    git \
    && rm -rf /var/cache/apk/*

# Create non-root user
RUN addgroup -g 1001 huskycat && \
    adduser -D -u 1001 -G huskycat huskycat

# Copy ONLY the fat binary (pre-built, signed)
COPY --chown=huskycat:huskycat dist/huskycat /usr/local/bin/huskycat
RUN chmod +x /usr/local/bin/huskycat

# Workspace setup
RUN mkdir -p /workspace && chown huskycat:huskycat /workspace

USER huskycat
WORKDIR /workspace

# Environment
ENV HUSKYCAT_MODE=container
ENV HUSKYCAT_GPL_SOCKET=/tmp/huskycat-gpl.sock

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
    CMD huskycat status --json || exit 1

ENTRYPOINT ["huskycat"]
CMD ["--help"]
```

**Size: ~20MB** (vs current ~500MB)

#### GPL Sidecar Container

```dockerfile
# ContainerFile.gpl-sidecar
# SPDX-License-Identifier: GPL-3.0-only
#
# GPL-licensed tool sidecar
# Runs as separate container/process for license isolation

FROM alpine:3.19

# Install ONLY GPL tools
RUN apk add --no-cache \
    python3 \
    shellcheck \
    && pip3 install --no-cache-dir --break-system-packages yamllint \
    && rm -rf /var/cache/apk/*

# Install hadolint (GPL-3.0)
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then HADOLINT_ARCH="x86_64"; \
    elif [ "$ARCH" = "aarch64" ]; then HADOLINT_ARCH="arm64"; \
    else HADOLINT_ARCH="x86_64"; fi && \
    curl -L "https://github.com/hadolint/hadolint/releases/latest/download/hadolint-Linux-${HADOLINT_ARCH}" \
        -o /usr/bin/hadolint && \
    chmod +x /usr/bin/hadolint

# Copy sidecar server
COPY gpl-sidecar/server.py /usr/local/bin/gpl-sidecar
RUN chmod +x /usr/local/bin/gpl-sidecar

# Create socket directory
RUN mkdir -p /run/huskycat

# Non-root execution
RUN addgroup -g 1001 huskycat && \
    adduser -D -u 1001 -G huskycat huskycat && \
    chown huskycat:huskycat /run/huskycat

USER huskycat

ENV HUSKYCAT_GPL_SOCKET=/run/huskycat/gpl.sock

ENTRYPOINT ["python3", "/usr/local/bin/gpl-sidecar"]
```

**Size: ~50MB**

### Container Chaining Architecture

```yaml
# docker-compose.yml / podman-compose.yml
# HuskyCat with GPL sidecar

version: "3.8"

services:
  huskycat:
    image: ghcr.io/tinyland/huskycat:latest
    volumes:
      - ./:/workspace:ro
      - huskycat-socket:/run/huskycat
    environment:
      HUSKYCAT_GPL_SOCKET: /run/huskycat/gpl.sock
    depends_on:
      - gpl-sidecar

  gpl-sidecar:
    image: ghcr.io/tinyland/huskycat-gpl:latest
    volumes:
      - huskycat-socket:/run/huskycat
    # Separate GPL-licensed container
    # License: GPL-3.0-only

volumes:
  huskycat-socket:
```

### License File Structure

```
LICENSE                          # Primary: zlib OR Apache-2.0
├── LICENSE-ZLIB                 # Full zlib license text
├── LICENSE-APACHE               # Full Apache-2.0 text
└── NOTICE                       # Attribution notices

gpl-sidecar/
├── LICENSE                      # GPL-3.0-only
├── server.py                    # GPL-3.0-only header
└── README.md                    # Explains GPL boundary

SPDX headers in source files:
- Main code: SPDX-License-Identifier: zlib OR Apache-2.0
- GPL sidecar: SPDX-License-Identifier: GPL-3.0-only
```

### Migration Checklist

```
PHASE 1: License Structure (Before Release)
├── [ ] Choose primary license (recommend: zlib OR Apache-2.0)
├── [ ] Create LICENSE files
├── [ ] Add SPDX headers to all source files
├── [ ] Create NOTICE file with attributions
├── [ ] Legal review of GPL isolation architecture

PHASE 2: IPC Implementation
├── [ ] Create src/huskycat/core/ipc/ module
├── [ ] Implement Unix socket client
├── [ ] Implement JSON-RPC 2.0 protocol
├── [ ] Add fallback to direct execution (when tools local)
├── [ ] Integration tests for IPC path

PHASE 3: Container Transformation
├── [ ] Create ContainerFile.wrapper (thin)
├── [ ] Create ContainerFile.gpl-sidecar
├── [ ] Update CI to build both images
├── [ ] Create docker-compose.yml for chained execution
├── [ ] Update documentation

PHASE 4: Fat Binary Update
├── [ ] Remove shellcheck, hadolint from bundle
├── [ ] Add IPC client for GPL tools
├── [ ] Auto-start sidecar when needed
├── [ ] Test all execution paths
```

### Legal Considerations

| Aspect | Current | Target |
|--------|---------|--------|
| Core license | MIT (unpublished) | zlib OR Apache-2.0 |
| GPL tools | Bundled (VIOLATION) | IPC-isolated sidecar |
| Container | Single fat image | Wrapper + GPL sidecar |
| Binary | Contains GPL tools | MIT/Apache only |
| Distribution | Single artifact | Split artifacts |

**Key Legal Points**:
1. GPL tools must never be statically linked or bundled
2. IPC (pipes, sockets) creates process boundary = no license contamination
3. Separate containers with separate licenses = compliant
4. Users who want GPL tools must explicitly pull GPL sidecar
5. Main HuskyCat can be embedded in proprietary software

---

## Part 9: Clean-Room Reimplementation & GPL Elimination Strategy

### Research Summary

Deep research completed on clean-room reimplementation feasibility for GPL tools.

### Feasibility Matrix

| Tool | GPL Replacement | Effort | Risk | Recommendation |
|------|-----------------|--------|------|----------------|
| **hadolint** | `dockerlint` (MIT) | **0** | None | **Use immediately** |
| **yamllint** | Clean-room 5-rule | 1-2 weeks | Low | Optional - build minimal |
| **shellcheck** | Not feasible | 6+ months | High | Keep in container only |

### Key Discovery: dockerlint (MIT)

**hadolint can be completely replaced** with `dockerlint`, an existing MIT-licensed Python library:

```toml
# pyproject.toml
[project.dependencies]
dockerlint = ">=0.3.0"  # MIT license, ~500KB
```

**Capabilities**:
- Parses Dockerfiles using `dockerfile-parse` (BSD)
- Checks best practices (pinned versions, multi-stage, etc.)
- Pure Python, no external binary needed
- MIT license = safe to bundle

### yamllint: Minimal Clean-Room Implementation

**5 Critical Rules** (covers 80% of use cases):

```python
# src/huskycat/linters/yaml_lint.py
# SPDX-License-Identifier: Apache-2.0
"""
Minimal YAML linter - clean-room implementation.
Based on YAML 1.2 specification (NOT yamllint GPL source).
"""

import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import List, Iterator

@dataclass
class YamlIssue:
    line: int
    column: int
    rule: str
    message: str
    severity: str = "warning"

def lint_yaml(content: str, max_line_length: int = 120) -> List[YamlIssue]:
    """Lint YAML content for common issues."""
    issues = []
    lines = content.splitlines(keepends=True)

    for i, line in enumerate(lines, 1):
        # Rule 1: Trailing whitespace
        if line.rstrip('\n\r') != line.rstrip():
            issues.append(YamlIssue(
                line=i, column=len(line.rstrip()) + 1,
                rule="trailing-whitespace",
                message="Trailing whitespace"
            ))

        # Rule 2: Line too long
        if len(line.rstrip()) > max_line_length:
            issues.append(YamlIssue(
                line=i, column=max_line_length + 1,
                rule="line-length",
                message=f"Line too long ({len(line.rstrip())} > {max_line_length})"
            ))

        # Rule 3: Tabs instead of spaces
        if '\t' in line and not line.lstrip().startswith('#'):
            issues.append(YamlIssue(
                line=i, column=line.index('\t') + 1,
                rule="indentation",
                message="Use spaces instead of tabs"
            ))

    # Rule 4: Duplicate keys (parsed)
    try:
        # Custom loader that tracks duplicates
        issues.extend(_check_duplicate_keys(content))
    except yaml.YAMLError as e:
        if hasattr(e, 'problem_mark'):
            issues.append(YamlIssue(
                line=e.problem_mark.line + 1,
                column=e.problem_mark.column + 1,
                rule="syntax-error",
                message=str(e.problem),
                severity="error"
            ))

    # Rule 5: Empty values
    issues.extend(_check_empty_values(content))

    return sorted(issues, key=lambda x: (x.line, x.column))

def _check_duplicate_keys(content: str) -> List[YamlIssue]:
    """Detect duplicate keys in YAML mappings."""
    issues = []
    # Implementation uses PyYAML's event-based parsing
    # to track key positions without evaluating values
    # ... (omitted for brevity)
    return issues

def _check_empty_values(content: str) -> List[YamlIssue]:
    """Detect empty values that may be unintentional."""
    issues = []
    for i, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()
        if stripped.endswith(':') and not stripped.startswith('#'):
            # Key with no value on same line - check next line
            issues.append(YamlIssue(
                line=i, column=len(line.rstrip()),
                rule="empty-value",
                message="Key has no value (may be intentional)",
                severity="info"
            ))
    return issues
```

**Size**: ~200-300 lines, ~15KB
**License**: Apache-2.0 (clean-room, no GPL contact)
**Effort**: 1-2 weeks

### shellcheck: Container-Only (Not Feasible to Replace)

**Why clean-room is not justified**:

1. **Complexity**: 340+ rules (SC1000-SC2253)
2. **Parser required**: bashlex is GPL, must build from scratch
3. **Time**: 6-12 months for meaningful coverage
4. **Maintenance**: Shell evolves, ongoing work needed

**Decision**: Keep shellcheck in container/IPC sidecar for CI mode only.

### Updated Tool Routing Strategy

```
EXECUTION ROUTING BY LICENSE

┌─────────────────────────────────────────────────────────────────────┐
│                    FAT BINARY (Apache-2.0)                          │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  BUNDLED TOOLS                                                 │  │
│  │  ├── ruff (MIT) ─────────── Python linting + formatting       │  │
│  │  ├── mypy (MIT) ─────────── Type checking                     │  │
│  │  ├── bandit (Apache) ────── Security scanning                 │  │
│  │  ├── dockerlint (MIT) ───── Dockerfile linting ← NEW!         │  │
│  │  ├── yaml_lint (Apache) ─── YAML linting (5 rules) ← NEW!     │  │
│  │  └── taplo (MIT) ────────── TOML formatting                   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  Size: ~100MB (reduced from 150MB by removing GPL tools)            │
│  Startup: <100ms                                                     │
│  License: Fully Apache-2.0 compatible                                │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│              CONTAINER/SIDECAR (GPL - Optional Add-on)              │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  GPL TOOLS (Comprehensive)                                     │  │
│  │  ├── shellcheck (GPL-3.0) ── Full shell analysis (340 rules)  │  │
│  │  ├── hadolint (GPL-3.0) ──── Full Dockerfile lint (50 rules)  │  │
│  │  └── yamllint (GPL-3.0) ──── Full YAML lint (30 rules)        │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  When used: CI mode, explicit --comprehensive flag                  │
│  Distribution: Separate container image                              │
│  License: GPL-3.0-only (isolated)                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Mode-Specific Tool Selection

```python
# src/huskycat/core/tool_selector.py

from enum import Enum
from typing import Set

class LintingMode(Enum):
    FAST = "fast"           # Binary-only, Apache-2.0 tools
    COMPREHENSIVE = "comprehensive"  # Include GPL container tools

# Tool sets by license
APACHE_TOOLS = {
    "ruff",        # Python (replaces black, flake8, isort, autoflake)
    "mypy",        # Type checking
    "bandit",      # Security
    "dockerlint",  # Dockerfile (MIT) ← REPLACES hadolint
    "yaml_lint",   # YAML (Apache, 5 rules) ← REPLACES yamllint
    "taplo",       # TOML
}

GPL_TOOLS = {
    "shellcheck",  # Shell scripts (no Apache replacement)
    "hadolint",    # Dockerfile (comprehensive, 50 rules)
    "yamllint",    # YAML (comprehensive, 30 rules)
}

def get_tools_for_mode(mode: LintingMode, file_types: Set[str]) -> Set[str]:
    """Select tools based on linting mode and file types."""
    tools = set()

    # Always use Apache tools from binary
    if "python" in file_types:
        tools.update({"ruff", "mypy", "bandit"})
    if "dockerfile" in file_types:
        tools.add("dockerlint")
    if "yaml" in file_types:
        tools.add("yaml_lint")
    if "toml" in file_types:
        tools.add("taplo")

    # Add GPL tools only in comprehensive mode
    if mode == LintingMode.COMPREHENSIVE:
        if "shell" in file_types:
            tools.add("shellcheck")
        if "dockerfile" in file_types:
            tools.add("hadolint")  # Adds 50 more rules
        if "yaml" in file_types:
            tools.add("yamllint")  # Adds 25 more rules

    return tools
```

### Product Mode Mapping

| Mode | Default Linting | GPL Tools Available |
|------|-----------------|---------------------|
| Git Hooks | FAST (binary only) | No |
| CLI | FAST (--comprehensive for GPL) | Optional |
| CI | COMPREHENSIVE | Yes (container) |
| MCP | FAST (--comprehensive for GPL) | Optional |
| Pipeline | COMPREHENSIVE | Yes (container) |

### Implementation Checklist

```
PHASE 1: MIT/Apache Tool Integration (Week 1)
├── [ ] Add dockerlint to pyproject.toml
├── [ ] Create DockerLintValidator in unified_validation.py
├── [ ] Create yaml_lint.py clean-room implementation
├── [ ] Create YamlLintValidator wrapper
├── [ ] Update tool registry with license metadata
└── [ ] Remove GPL tools from fat binary spec

PHASE 2: Tool Selector Implementation (Week 2)
├── [ ] Create tool_selector.py module
├── [ ] Add --comprehensive flag to CLI
├── [ ] Update mode adapters to use selector
├── [ ] Add HUSKYCAT_LINTING_MODE environment variable
└── [ ] Update MCP tools to support mode parameter

PHASE 3: Documentation & Migration (Week 3)
├── [ ] Document tool coverage differences
├── [ ] Create migration guide for users
├── [ ] Update CLAUDE.md with new architecture
├── [ ] Add license compliance CI check
└── [ ] Release notes with GPL elimination announcement
```

### Libre Sales Compatibility

With Apache-2.0 licensing and GPL elimination from core binary:

```
MONETIZATION OPTIONS (Apache-2.0)

✅ Proprietary Extensions
   └── Sell additional validators, integrations

✅ SaaS Offering
   └── HuskyCat Cloud with hosted validation

✅ Enterprise Features
   └── RBAC, audit logs, compliance reports

✅ Support Contracts
   └── Priority support, custom rules

✅ Dual Licensing
   └── Offer commercial license for OEM embedding

❌ NOT POSSIBLE with GPL in binary
   └── Would contaminate entire distribution
```

---

**Plan Status**: READY FOR APPROVAL

This comprehensive plan addresses all user concerns:
1. API parity across all invocation methods
2. Cross-platform packaging with FPM
3. Complete macOS PKG signing workflow
4. Desktop application assets
5. Tray icon with git profile management
6. SBOM generation and signing pipeline
7. GPL license compliance remediation
8. Fat binary wrapper architecture
9. **Apache-2.0 licensing (libre sales compatible)**
10. **GPL tool elimination via dockerlint + clean-room yaml_lint**
11. **Container-only for shellcheck (comprehensive mode)**
