# GitLab CI Pipeline Architecture

**HuskyCat Fat Binary Build Pipeline**

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        GitLab CI Pipeline                        │
│                    Multi-Stage, Multi-Platform                   │
└─────────────────────────────────────────────────────────────────┘

Stage 1: VALIDATE
├── container:build:amd64         (buildah, linux/amd64)
├── container:build:arm64         (buildah, linux/arm64)
└── container:build:manifest      (multi-arch manifest)

Stage 2: SECURITY
├── validate:basic               (black, ruff, mypy)
├── validate:yaml                (yamllint)
├── SAST                         (GitLab security template)
└── Dependency-Scanning          (GitLab security template)

Stage 3: BUILD
├── download:tools:linux-amd64   (shellcheck, hadolint, taplo)
├── download:tools:linux-arm64   (ARM64 validation tools)
├── download:tools:darwin-amd64  (macOS Intel tools)
├── download:tools:darwin-arm64  (macOS ARM64 tools)
└── validate:complete            (comprehensive validation)

Stage 4: TEST
├── verify:tools:all-platforms   (verify downloaded tools)
├── test:unit                    (pytest + hypothesis PBT)
└── test:mcp:server              (MCP protocol tests)

Stage 5: PACKAGE
├── build:binary:linux-amd64     (Fat binary: Python + tools)
├── build:binary:linux-arm64     (Fat binary: Python + tools)
├── build:binary:darwin-arm64    (Fat binary: Python + tools)
├── package:python               (wheel + sdist)
├── verify:binary-size           (check size limits)
└── checksums:generate           (SHA256 for all binaries)

Stage 6: SIGN
└── sign:darwin-arm64            (Apple Developer ID signing)

Stage 7: DEPLOY
├── release:create               (GitLab releases, tags only)
└── pages                        (MkDocs documentation)

Stage 8: SCHEDULED
└── update:dependencies          (weekly dependency updates)
```

## Fat Binary Build Flow

### Tool Download Phase

```
┌────────────────────────────────────────────────────────┐
│           download:tools:linux-amd64                   │
│                                                        │
│  Input:  scripts/download_tools.py                    │
│  Image:  python:3.11-slim                             │
│  Script: python3 scripts/download_tools.py            │
│          --platform linux-amd64                       │
│          --output-dir dist/tools/linux-amd64          │
│                                                        │
│  Downloads from GitHub Releases:                      │
│  • shellcheck v0.10.0  (~15-20MB)                     │
│  • hadolint v2.12.0    (~10-15MB)                     │
│  • taplo v0.9.3        (~8-12MB)                      │
│                                                        │
│  Output: dist/tools/linux-amd64/                      │
│          ├── shellcheck                               │
│          ├── hadolint                                 │
│          ├── taplo                                    │
│          └── versions.txt                             │
│                                                        │
│  Artifacts: expire_in: 1 day                          │
│  Cache: key: tools-linux-amd64                        │
└────────────────────────────────────────────────────────┘
            │
            ├── (Parallel downloads for other platforms)
            │
            ↓
┌────────────────────────────────────────────────────────┐
│           verify:tools:all-platforms                   │
│                                                        │
│  Dependencies: All download:tools:* jobs               │
│  Verifies:                                             │
│  • All tools exist                                     │
│  • All tools are executable                           │
│  • Version manifests present                          │
│  • File sizes reasonable                              │
│                                                        │
│  Fails pipeline if any tool missing or invalid        │
└────────────────────────────────────────────────────────┘
```

### Binary Build Phase

```
┌────────────────────────────────────────────────────────┐
│           build:binary:linux-amd64                     │
│                                                        │
│  Needs:    download:tools:linux-amd64                 │
│  Image:    rockylinux/rockylinux:10                   │
│  Runner:   GitLab SaaS AMD64                          │
│                                                        │
│  Build Process:                                        │
│  1. Install UV + PyInstaller                          │
│  2. Sync dependencies (uv sync --extra build)         │
│  3. Run PyInstaller:                                  │
│                                                        │
│     uv run pyinstaller --onefile \                    │
│       --name huskycat-linux-amd64 \                   │
│       --add-binary "dist/tools/.../shellcheck:tools/" │
│       --add-binary "dist/tools/.../hadolint:tools/"   │
│       --add-binary "dist/tools/.../taplo:tools/"      │
│       huskycat_main.py                                │
│                                                        │
│  4. Move to dist/bin/huskycat-linux-amd64             │
│  5. Optional UPX compression (--best --lzma)          │
│  6. Verify binary (--version test)                    │
│  7. Check size (warn if >250MB)                       │
│                                                        │
│  Output: dist/bin/huskycat-linux-amd64                │
│  Size:   60-100MB (compressed) / 150-200MB (raw)      │
│  Artifacts: expire_in: 1 month                        │
└────────────────────────────────────────────────────────┘
            │
            ├── (Parallel builds for other platforms)
            │
            ↓
┌────────────────────────────────────────────────────────┐
│           verify:binary-size                           │
│                                                        │
│  Dependencies: All build:binary:* jobs                 │
│  Verifies:                                             │
│  • Size <= 250MB (fails if exceeded)                  │
│  • Executable permissions set                         │
│  • Valid ELF/Mach-O format                            │
│  • Binary not empty                                   │
│                                                        │
│  allow_failure: false (blocks pipeline)               │
└────────────────────────────────────────────────────────┘
            │
            ↓
┌────────────────────────────────────────────────────────┐
│           checksums:generate                           │
│                                                        │
│  Input:  dist/bin/huskycat-*                          │
│  Output: dist/bin/SHA256SUMS.txt                      │
│                                                        │
│  Example:                                              │
│  abc123... huskycat-linux-amd64                       │
│  def456... huskycat-linux-arm64                       │
│  789ghi... huskycat-darwin-arm64                      │
└────────────────────────────────────────────────────────┘
```

### Code Signing Phase (macOS only)

```
┌────────────────────────────────────────────────────────┐
│           sign:darwin-arm64                            │
│                                                        │
│  Needs:    build:binary:darwin-arm64                  │
│  Image:    macos-14-xcode-15                          │
│  Runner:   saas-macos-medium-m1                       │
│                                                        │
│  Signing Process:                                      │
│  1. Create temporary keychain                         │
│  2. Import Developer ID Application cert              │
│  3. Import Developer ID CA G2 intermediate            │
│  4. Set partition list for headless CI                │
│  5. Sign binary:                                      │
│                                                        │
│     codesign --force --options runtime \              │
│       --sign "$APPLE_DEVELOPER_ID_APPLICATION" \      │
│       --keychain signing.keychain-db \                │
│       dist/bin/huskycat-darwin-arm64                  │
│                                                        │
│  6. Verify signature                                  │
│  7. Notarize (if credentials available):              │
│                                                        │
│     xcrun notarytool submit \                         │
│       huskycat-darwin-arm64.zip \                     │
│       --apple-id "$APPLE_ID" \                        │
│       --password "$APPLE_NOTARIZE_PASSWORD" \         │
│       --team-id "$APPLE_TEAM_ID" \                    │
│       --wait                                          │
│                                                        │
│  Fallback: Ad-hoc signing (no certificate required)   │
│                                                        │
│  Output: huskycat-darwin-arm64-signed.tar.gz          │
│          huskycat-darwin-arm64-signed.sha256          │
│                                                        │
│  allow_failure: true (don't block if signing fails)   │
└────────────────────────────────────────────────────────┘
```

### Release Phase (Tags only)

```
┌────────────────────────────────────────────────────────┐
│           release:create                               │
│                                                        │
│  Trigger: CI_COMMIT_TAG set (e.g., v1.0.0)            │
│  Needs:   All binary builds + checksums + signing     │
│                                                        │
│  Creates GitLab Release with:                         │
│  • Linux AMD64 Fat Binary                             │
│  • Linux ARM64 Fat Binary                             │
│  • macOS ARM64 Signed Fat Binary                      │
│  • SHA256SUMS.txt                                     │
│  • Python Wheel Package                               │
│  • Container Image (registry.gitlab.com)              │
│  • Documentation Link (Pages)                         │
│                                                        │
│  Release Notes: Auto-generated from commit messages   │
└────────────────────────────────────────────────────────┘
```

## Platform Build Matrix

| Platform | Runner | Tools Size | Binary Size | Build Time | UPX | Signing |
|----------|--------|------------|-------------|------------|-----|---------|
| linux-amd64 | GitLab SaaS AMD64 | ~40MB | 60-100MB | 10-15 min | Yes | N/A |
| linux-arm64 | GitLab SaaS ARM64 | ~40MB | 60-100MB | 12-18 min | Yes | N/A |
| darwin-amd64 | Not available | ~40MB | N/A | N/A | No | N/A |
| darwin-arm64 | GitLab SaaS macOS M1 | ~40MB | 150-200MB | 14-21 min | No | Yes |

**Total Pipeline Time**: ~21 minutes (parallel execution, limited by slowest build)

## Key CI Variables

```yaml
# Container Registry
CONTAINER_REGISTRY: registry.gitlab.com/tinyland/ai/huskycat
CONTAINER_TAG: $CI_COMMIT_SHORT_SHA

# Build Configuration
UV_CACHE_DIR: $CI_PROJECT_DIR/.cache/uv
UV_VERSION: '0.5.8'
BUILDAH_FORMAT: docker
BUILDAH_ISOLATION: chroot

# Apple Code Signing (Optional)
APPLE_CERTIFICATE_BASE64:           Base64 .p12 certificate
APPLE_CERTIFICATE_PASSWORD:         Certificate password
APPLE_DEVELOPER_ID_APPLICATION:     "Developer ID Application: Name (TEAM)"
APPLE_DEVELOPER_ID_CA_G2:           Base64 intermediate CA cert
APPLE_ID:                           Apple ID email
APPLE_NOTARIZE_PASSWORD:            App-specific password
APPLE_TEAM_ID:                      Team ID
```

## Artifact Flow

```
Tool Downloads (1 day expiry, cached)
    ↓
Binary Builds (1 month expiry)
    ↓
Checksums (1 month expiry)
    ↓
Signed Binaries (1 month expiry)
    ↓
GitLab Releases (permanent, tags only)
```

## Quality Gates

### Blocking (Pipeline fails)
1. Container build failures
2. Security scanning critical issues
3. Tool download verification failures
4. Binary size exceeds 250MB
5. Binary format validation failures

### Warning (Pipeline continues)
1. UPX compression failures
2. Code signing failures (falls back to ad-hoc)
3. Binary execution test failures
4. Documentation build warnings

## Optimization Features

### Caching Strategy
- **UV dependencies**: Cached per `pyproject.toml` + `uv.lock` hash
- **Tool downloads**: Cached per platform, 1 day TTL
- **Container layers**: Buildah `--layers` for layer caching

### Parallel Execution
- All platform tool downloads run in parallel (4 jobs)
- All platform binary builds run in parallel (3 jobs)
- Security scans run in parallel with validation

### Artifact Compression
- UPX with `--best --lzma` on Linux (40-60% size reduction)
- Darwin binaries uncompressed (code signing requirement)
- Tar.gz for release artifacts

## Security Considerations

### Tool Provenance
All tools downloaded from official GitHub releases with pinned versions:
- shellcheck: v0.10.0 (github.com/koalaman/shellcheck)
- hadolint: v2.12.0 (github.com/hadolint/hadolint)
- taplo: v0.9.3 (github.com/tamasfe/taplo)

### Binary Integrity
- SHA256 checksums for all binaries
- Code signing for macOS binaries
- Notarization for macOS binaries (when credentials available)

### CI Security
- SAST scanning with GitLab security templates
- Dependency scanning with GitLab security templates
- Secrets passed via CI/CD variables (not in code)
- Temporary keychains for code signing (deleted after use)

## Runner Requirements

### Linux Builds
- GitLab SaaS shared runners (AMD64, ARM64)
- Rocky Linux 10 base image
- Requirements: git, curl, gcc, python3, zlib-devel

### macOS Builds
- GitLab SaaS macOS runners (ARM64 only)
- Tags: `saas-macos-medium-m1`
- Image: `macos-14-xcode-15`
- Requirements: Xcode command line tools

## CI Configuration Files

```
.gitlab-ci.yml                      Main pipeline definition
├── include:
│   ├── .gitlab/ci/download-tools.yml  (Tool download jobs)
│   ├── .gitlab/ci/build.yml           (Binary build jobs)
│   ├── .gitlab/ci/e2e-tests.yml       (End-to-end tests)
│   ├── .gitlab/ci/pages.yml           (Documentation)
│   └── .gitlab/ci/scheduled-updates.yml (Dependency updates)
│
├── scripts/download_tools.py       Tool downloader script
├── build_fat_binary.py             Fat binary builder (not used by CI)
└── huskycat_main.py                Binary entry point
```

## References

- CI Pipeline: `/Users/jsullivan2/git/huskycats-bates/.gitlab-ci.yml`
- Download Tools: `/Users/jsullivan2/git/huskycats-bates/.gitlab/ci/download-tools.yml`
- Build Jobs: `/Users/jsullivan2/git/huskycats-bates/.gitlab/ci/build.yml`
- Tool Downloader: `/Users/jsullivan2/git/huskycats-bates/scripts/download_tools.py`
- Build Script: `/Users/jsullivan2/git/huskycats-bates/build_fat_binary.py`

## Future Enhancements

1. **Use build_fat_binary.py in CI** - Reduce duplication, single source of truth
2. **darwin-amd64 support** - Requires custom Intel macOS runner
3. **Universal macOS binaries** - Combine AMD64 + ARM64 with `lipo`
4. **Binary size optimization** - Target <100MB per binary
5. **Multi-stage container builds** - Smaller container images
6. **Parallel test execution** - Faster test stage
