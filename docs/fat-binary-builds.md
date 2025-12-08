# Fat Binary Builds with Embedded Toolchains

HuskyCat builds platform-specific "fat binaries" that include embedded validation tool binaries (shellcheck, hadolint, taplo). This approach eliminates runtime dependencies and ensures consistent tool versions across environments.

## Overview

Traditional HuskyCat binaries require external validation tools to be installed on the system. Fat binaries bundle these tools directly into the executable, providing:

- **Zero dependencies**: No need to install shellcheck, hadolint, or taplo separately
- **Version consistency**: Embedded tools match tested versions exactly
- **Portability**: Single binary works across different environments
- **Simplified deployment**: One file to download and run

## Architecture

```
HuskyCat Fat Binary (250MB target)
├── Python runtime (PyInstaller bundle)
├── HuskyCat source code
└── Embedded tools/
    ├── shellcheck (10-15MB)
    ├── hadolint (5-8MB)
    └── taplo (3-5MB)
```

## Build Pipeline Flow

The CI/CD pipeline uses a multi-stage approach to download tools and build fat binaries:

```
Stage: validate
├── container:build:amd64
└── container:build:arm64

Stage: build (Tool Downloads)
├── download:tools:linux-amd64
├── download:tools:linux-arm64
├── download:tools:darwin-amd64
└── download:tools:darwin-arm64
    ↓ artifacts (1 day expiry)

Stage: test
├── verify:tools:all-platforms
└── test:unit

Stage: package (Binary Builds)
├── build:binary:linux-amd64 ← depends on download:tools:linux-amd64
├── build:binary:linux-arm64 ← depends on download:tools:linux-arm64
├── build:binary:darwin-arm64 ← depends on download:tools:darwin-arm64
├── verify:binary-size
└── checksums:generate
    ↓ artifacts (1 month expiry)

Stage: sign
└── sign:darwin-arm64 ← depends on build:binary:darwin-arm64

Stage: deploy
└── release:create (on tags only)
```

## Pipeline Stages

### Stage 1: Build (Tool Downloads)

**Job**: `download:tools:<platform>`

Downloads platform-specific pre-compiled validation tool binaries from GitHub releases.

**Platforms**:
- `linux-amd64` - Linux x86_64
- `linux-arm64` - Linux ARM64/aarch64
- `darwin-amd64` - macOS Intel (Intel Macs)
- `darwin-arm64` - macOS ARM64 (Apple Silicon)

**Tools Downloaded**:
- shellcheck v0.10.0
- hadolint v2.12.0
- taplo v0.9.3

**Artifacts**: `dist/tools/<platform>/`
- Tool binaries (shellcheck, hadolint, taplo)
- versions.txt manifest
- Cached for 1 day

**Example**:
```yaml
download:tools:linux-amd64:
  stage: build
  image: python:3.11-slim
  script:
    - python3 scripts/download_tools.py --platform linux-amd64 --output-dir dist/tools/linux-amd64
  artifacts:
    paths:
      - dist/tools/linux-amd64/
    expire_in: 1 day
```

### Stage 2: Test (Verification)

**Job**: `verify:tools:all-platforms`

Verifies all tool downloads completed successfully and binaries are executable.

**Checks**:
- Tool directories exist for all platforms
- Required tools (shellcheck, hadolint, taplo) are present
- Binaries are executable
- versions.txt manifest exists

Fails the pipeline if any verification fails.

### Stage 3: Package (Fat Binary Builds)

**Job**: `build:binary:<platform>`

Builds HuskyCat fat binaries with embedded tools using PyInstaller.

**Build Process**:
1. Download tools artifact from build stage
2. Install build dependencies (uv, PyInstaller, gcc)
3. Run PyInstaller with `--add-binary` for each tool:
   ```bash
   pyinstaller --onefile \
     --name huskycat-linux-amd64 \
     --add-binary "dist/tools/linux-amd64/shellcheck:tools/" \
     --add-binary "dist/tools/linux-amd64/hadolint:tools/" \
     --add-binary "dist/tools/linux-amd64/taplo:tools/" \
     huskycat_main.py
   ```
4. Optional UPX compression (Linux only, saves ~30%)
5. Verify binary executes and reports version

**Binary Size Targets**:
- Target: ≤250MB per binary
- Warning if exceeds target
- Fails pipeline if >300MB (reserved for future enforcement)

**Platforms**:
- `linux-amd64` - Rocky Linux 10 runner
- `linux-arm64` - Rocky Linux 10 ARM64 runner (saas-linux-medium-arm64)
- `darwin-arm64` - macOS 14 runner (saas-macos-medium-m1)

**Artifacts**: `dist/bin/huskycat-<platform>`
- Fat binary with embedded tools
- Expires in 1 month

### Stage 4: Verification

**Job**: `verify:binary-size`

Validates all built binaries meet size and format requirements.

**Checks**:
- Binary files exist
- Size ≤250MB (warning if exceeded)
- Executable permission set
- Valid ELF (Linux) or Mach-O (macOS) format

**Job**: `checksums:generate`

Generates SHA256 checksums for all binaries.

**Output**: `dist/bin/SHA256SUMS.txt`
```
a1b2c3... huskycat-linux-amd64
d4e5f6... huskycat-linux-arm64
g7h8i9... huskycat-darwin-arm64
```

### Stage 5: Sign (macOS only)

**Job**: `sign:darwin-arm64`

Signs and notarizes the macOS binary (if credentials available).

**Process**:
1. Create temporary keychain
2. Import Developer ID certificate
3. Sign binary with codesign
4. Notarize with Apple (if credentials set)
5. Archive signed binary

Requires CI/CD variables:
- `APPLE_CERTIFICATE_BASE64`
- `APPLE_CERTIFICATE_PASSWORD`
- `APPLE_DEVELOPER_ID_APPLICATION`
- `APPLE_ID` (for notarization)
- `APPLE_NOTARIZE_PASSWORD`
- `APPLE_TEAM_ID`

Falls back to ad-hoc signing if not configured.

### Stage 6: Deploy (Tags only)

**Job**: `release:create`

Creates GitLab release with download links for all binaries.

**Release Assets**:
- Linux AMD64 Binary (Fat)
- Linux ARM64 Binary (Fat)
- macOS ARM64 Binary (Apple Silicon - Signed, Fat)
- SHA256 Checksums
- Python Wheel Package
- Container Image
- Documentation

Only runs on Git tags (e.g., `v2.0.0`).

## Tool Download Script

**Location**: `scripts/download_tools.py`

Python script that downloads platform-specific validation tool binaries from GitHub releases.

**Usage**:
```bash
# Download tools for specific platform
python scripts/download_tools.py --platform linux-amd64 --output-dir dist/tools/linux-amd64

# Download tools for all platforms
python scripts/download_tools.py --all

# List available tools
python scripts/download_tools.py --list-tools

# Clean downloads
python scripts/download_tools.py --clean
```

**Tool Configuration**:
```python
TOOLS: Dict[str, Dict[str, str]] = {
    "shellcheck": {
        "version": "0.10.0",
        "urls": {
            "linux-amd64": "https://github.com/koalaman/shellcheck/releases/...",
            # ...
        },
    },
    # ...
}
```

Tool versions should be updated periodically to match pyproject.toml dependencies.

## Binary Size Analysis

Typical fat binary sizes (post-UPX):

| Platform | Binary Size | Breakdown |
|----------|-------------|-----------|
| linux-amd64 | ~180MB | PyInstaller bundle (150MB) + Tools (30MB) |
| linux-arm64 | ~175MB | PyInstaller bundle (145MB) + Tools (30MB) |
| darwin-arm64 | ~200MB | PyInstaller bundle (165MB) + Tools (35MB) |

**Size Optimization**:
- UPX compression (Linux): ~30% reduction
- PyInstaller bytecode optimization
- Exclude unnecessary Python stdlib modules
- Strip debug symbols from tool binaries

**Not Used**:
- UPX on macOS (causes code signing issues)
- Strip on macOS (breaks notarization)

## Estimated Build Times

Per-platform build times on GitLab SaaS runners:

| Stage | Job | Time | Notes |
|-------|-----|------|-------|
| build | download:tools:linux-amd64 | ~2 min | Parallel with other platforms |
| build | download:tools:linux-arm64 | ~2 min | Parallel with other platforms |
| build | download:tools:darwin-arm64 | ~2 min | Parallel with other platforms |
| test | verify:tools:all-platforms | ~30 sec | Waits for all downloads |
| package | build:binary:linux-amd64 | ~8 min | PyInstaller + UPX |
| package | build:binary:linux-arm64 | ~10 min | PyInstaller + UPX (ARM slower) |
| package | build:binary:darwin-arm64 | ~6 min | PyInstaller (no UPX) |
| package | verify:binary-size | ~30 sec | Waits for all builds |
| package | checksums:generate | ~15 sec | SHA256 computation |
| sign | sign:darwin-arm64 | ~5 min | Notarization can take 2-3 min |

**Total Pipeline Time**: ~18-22 minutes for full multi-platform build

**Parallelization**:
- Tool downloads run in parallel (4 jobs)
- Binary builds run in parallel (3 jobs)
- Critical path: download → verify → build → sign

## Artifact Management

**Tool Download Artifacts** (build stage):
- Path: `dist/tools/<platform>/`
- Size: ~50MB per platform
- Expiry: 1 day
- Cache: Yes (key: `tools-<platform>`)
- Purpose: Consumed by binary build jobs

**Binary Artifacts** (package stage):
- Path: `dist/bin/huskycat-<platform>`
- Size: 150-200MB per platform
- Expiry: 1 month
- Cache: No
- Purpose: Release assets

**Signed Binary Artifacts** (sign stage):
- Path: `huskycat-darwin-arm64-signed.tar.gz`
- Size: 200MB
- Expiry: 1 month
- Cache: No
- Purpose: Final macOS release asset

## Local Development

Build fat binaries locally:

```bash
# Download tools for current platform
python scripts/download_tools.py --platform auto

# Or download for specific platform
python scripts/download_tools.py --platform linux-amd64

# Build fat binary with PyInstaller
uv sync --extra build
uv run pyinstaller --onefile \
  --name huskycat \
  --add-binary "dist/tools/linux-amd64/shellcheck:tools/" \
  --add-binary "dist/tools/linux-amd64/hadolint:tools/" \
  --add-binary "dist/tools/linux-amd64/taplo:tools/" \
  huskycat_main.py

# Test binary
./dist/huskycat --version
./dist/huskycat validate
```

## Troubleshooting

### "Tool directory not found" error in binary build

**Cause**: download:tools job didn't complete or artifacts expired

**Solution**:
- Re-run pipeline from failed stage
- Check download:tools job logs for download failures
- Verify artifact paths in build job dependencies

### "Binary size exceeds 250MB" warning

**Cause**: Tools or PyInstaller bundle too large

**Solution**:
- Review PyInstaller spec file for unnecessary includes
- Consider excluding unused Python stdlib modules
- Verify UPX compression is working (Linux)
- Check tool binary sizes in dist/tools/

### macOS binary not executable / "damaged" error

**Cause**: Code signing failed or binary not notarized

**Solution**:
- Check sign:darwin-arm64 job logs
- Verify APPLE_* CI variables are set
- Allow ad-hoc signed binaries: `xattr -d com.apple.quarantine ./huskycat`
- Re-run notarization (can timeout on Apple servers)

### ARM64 builds timing out

**Cause**: ARM64 runners slower than x86_64

**Solution**:
- Increase job timeout (currently 2h max on GitLab SaaS)
- Optimize PyInstaller build (exclude unnecessary modules)
- Use build cache effectively
- Consider cross-compilation (requires testing)

## Future Enhancements

### Tool Auto-Update

Automatically detect new tool versions from GitHub releases and update TOOLS configuration.

### Cross-Compilation

Build macOS AMD64 binaries on Linux with osxcross (GitLab SaaS only has ARM64 macOS runners).

### Binary Compression

Explore alternative compression beyond UPX:
- LZMA compression in PyInstaller
- Brotli compressed archives
- Split binaries (base + tools as separate downloads)

### Tool Selection

Allow users to build custom binaries with subset of tools:
```bash
python build_binary.py --tools shellcheck,hadolint
```

### Thin Binaries

Provide both fat and thin binary builds:
- Fat: All tools embedded (current)
- Thin: Tools downloaded on first run

## References

- [PyInstaller Documentation](https://pyinstaller.org/)
- [UPX Compression](https://upx.github.io/)
- [GitLab CI Artifacts](https://docs.gitlab.com/ee/ci/pipelines/job_artifacts.html)
- [macOS Code Signing Guide](macos-code-signing.md)

## Related Documentation

- [Binary Downloads](binary-downloads.md) - User guide for downloading and installing binaries
- [GitLab CI/CD](gitlab-ci-cd.md) - Complete CI/CD pipeline documentation
- [macOS Code Signing](macos-code-signing.md) - Detailed signing and notarization guide
