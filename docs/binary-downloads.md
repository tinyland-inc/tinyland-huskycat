# Binary Downloads

Pre-built HuskyCat binaries for all supported platforms.

## Latest Release (main branch)

Download the latest binary from the main branch CI artifacts:

| Platform | Architecture | Size | Download Link |
|----------|--------------|------|---------------|
| **Linux** | x86_64 (amd64) | ~150-200 MB | [Download](https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/bin/huskycat-linux-amd64?job=build:binary:linux-amd64) |
| **Linux** | ARM64 | ~150-200 MB | [Download](https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/bin/huskycat-linux-arm64?job=build:binary:linux-arm64) |
| **macOS** | ARM64 (M1/M2/M3/M4) | ~150-200 MB | [Download](https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/bin/huskycat-darwin-arm64?job=build:binary:darwin-arm64) |

> **Note**: macOS Intel (x86_64) binary not currently available due to GitLab SaaS runner limitations. Intel Mac users can use Rosetta 2 or container execution.

## Quick Install

### Linux (amd64)

```bash
curl -L 'https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/bin/huskycat-linux-amd64?job=build:binary:linux-amd64' -o huskycat
chmod +x huskycat
./huskycat install
```

### Linux (ARM64)

```bash
curl -L 'https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/bin/huskycat-linux-arm64?job=build:binary:linux-arm64' -o huskycat
chmod +x huskycat
./huskycat install
```

### macOS (ARM64 - Apple Silicon)

```bash
curl -L 'https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/bin/huskycat-darwin-arm64?job=build:binary:darwin-arm64' -o huskycat
chmod +x huskycat

# Remove quarantine (macOS security)
xattr -d com.apple.quarantine huskycat

./huskycat install
```

### macOS (Intel) - Rosetta 2

Intel Mac users can run the ARM64 binary using Rosetta 2:

```bash
# Download ARM64 binary
curl -L 'https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/bin/huskycat-darwin-arm64?job=build:binary:darwin-arm64' -o huskycat
chmod +x huskycat
xattr -d com.apple.quarantine huskycat

# Run with Rosetta 2
arch -x86_64 ./huskycat install
```

## Verification

### Check SHA256 Checksums

Download checksums from CI artifacts:

```bash
# Linux amd64
curl -L 'https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/linux-amd64/huskycat.sha256?job=build:binary:linux-amd64'

# macOS ARM64
curl -L 'https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/darwin-arm64/huskycat.sha256?job=build:binary:darwin-arm64'
```

Verify checksum:

```bash
# Linux
sha256sum huskycat
# Should match downloaded checksum

# macOS
shasum -a 256 huskycat
# Should match downloaded checksum
```

### Verify Binary Works

```bash
./huskycat --version
./huskycat --help
```

Expected output:
```
$ ./huskycat --version
huskycat 2.0.0

$ ./huskycat --help
huskycat - Universal Code Validation Platform

Usage:
  huskycat [command] [options]

Commands:
  validate          Validate files with configured tools
  setup-hooks       Install git hooks
  install           Install binary to ~/.local/bin
  status            Show HuskyCat configuration
  ...
```

## What's Inside

Each binary includes:

### Core Components
- **HuskyCat Engine** (~5 MB) - Validation orchestration
- **Python Runtime** (~40 MB) - Embedded Python 3.13
- **Python Packages** (~30-50 MB) - Dependencies (pytest, rich, networkx, etc.)

### Embedded Validation Tools
- **shellcheck** v0.10.0 (~3-4 MB) - Shell script linter
- **hadolint** v2.12.0 (~10-15 MB) - Dockerfile linter
- **taplo** v0.9.3 (~15-20 MB) - TOML formatter/validator

### Total Binary Sizes
- **Linux binaries**: ~150-200 MB (all tools embedded)
- **macOS binaries**: ~21-200 MB (varies by build configuration)

## Platform Support

### Linux

**Architectures**:
- x86_64 (amd64) - Most common
- ARM64 (aarch64) - Raspberry Pi, AWS Graviton, etc.

**Requirements**:
- glibc 2.17+ (available on most modern distributions)
- No additional dependencies required

**Tested On**:
- Ubuntu 20.04+
- Debian 11+
- RHEL/CentOS 8+
- Alpine Linux 3.14+
- Fedora 34+

### macOS

**Architectures**:
- ARM64 (Apple Silicon) - M1, M2, M3 chips
- x86_64 (Intel) - Older Macs

**Requirements**:
- macOS 10.13+ (High Sierra or later)
- May require Xcode Command Line Tools for some operations

**Tested On**:
- macOS 14 (Sonoma) - ARM64
- macOS 13 (Ventura) - ARM64
- macOS 12 (Monterey) - ARM64/Intel
- macOS 11 (Big Sur) - ARM64/Intel

### Windows

**Status**: Not yet supported

**Alternatives**:
1. **WSL2** (Recommended):
   ```bash
   # Use Linux binary in WSL2
   curl -L 'https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/main/raw/dist/linux-amd64/huskycat?job=build:binary:linux-amd64' -o huskycat
   chmod +x huskycat
   ./huskycat install
   ```

2. **Docker Desktop**:
   ```bash
   docker pull registry.gitlab.com/jsullivan2/huskycats-bates:latest
   docker run --rm -v "$(pwd):/workspace" huskycat validate --all
   ```

3. **Git Bash** (Limited):
   - May work with Linux binary and Git Bash compatibility layer
   - Not officially supported

## Download from Specific Branch/Tag

Replace `main` with your branch name or tag:

### From Branch

```bash
# Replace 'feature-branch' with your branch name
curl -L 'https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/feature-branch/raw/dist/linux-amd64/huskycat?job=build:binary:linux-amd64' -o huskycat
```

### From Tag

```bash
# Replace 'v2.0.0' with your tag
curl -L 'https://gitlab.com/jsullivan2/huskycats-bates/-/jobs/artifacts/v2.0.0/raw/dist/linux-amd64/huskycat?job=build:binary:linux-amd64' -o huskycat
```

## Troubleshooting Downloads

### SSL Certificate Issues

If you encounter SSL errors:

```bash
# Skip SSL verification (not recommended for production)
curl -L --insecure 'https://...' -o huskycat

# Or install ca-certificates
# Ubuntu/Debian
sudo apt-get install ca-certificates

# RHEL/CentOS
sudo yum install ca-certificates
```

### Download Timeout

For slow connections, increase timeout:

```bash
curl -L --max-time 300 'https://...' -o huskycat
```

### Corrupted Download

Verify and retry:

```bash
# Check file size
ls -lh huskycat
# Should be ~150-200 MB for Linux, ~21 MB for macOS ARM64

# If wrong size, delete and retry
rm huskycat
curl -L 'https://...' -o huskycat
```

### Permission Denied on Download

Ensure write permissions:

```bash
# Download to current directory
curl -L 'https://...' -o ./huskycat

# Or use ~/Downloads
curl -L 'https://...' -o ~/Downloads/huskycat
cd ~/Downloads
chmod +x huskycat
./huskycat install
```

## Manual Download (Browser)

If `curl` is not available:

1. Visit the GitLab CI pipelines page:
   ```
   https://gitlab.com/jsullivan2/huskycats-bates/-/pipelines
   ```

2. Click on the latest successful pipeline (green checkmark)

3. Click "Browse" next to the build job for your platform:
   - `build:binary:linux-amd64`
   - `build:binary:darwin-arm64`
   - etc.

4. Navigate to `dist/<platform>/huskycat`

5. Click "Download" button

6. Move to desired location and make executable:
   ```bash
   chmod +x ~/Downloads/huskycat
   ~/Downloads/huskycat install
   ```

## Building from Source

If binaries don't work for your platform:

```bash
# Clone repository
git clone https://gitlab.com/jsullivan2/huskycats-bates.git
cd huskycats-bates

# Install dependencies
uv sync --dev

# Build binary
npm run build:binary

# Binary will be in dist/huskycat
./dist/huskycat --version
```

See [Development Guide](../CONTRIBUTING.md) for details.

## Release Channels

### Stable (main branch)
- Thoroughly tested
- Recommended for production use
- Download from `main` branch

### Development (feature branches)
- Latest features
- May have bugs
- Download from specific feature branch

### Tagged Releases (v2.0.0, v2.1.0, etc.)
- Semantic versioning
- Production-ready releases
- Download from tagged commits

## Next Steps

After downloading:

1. [Install](installation.md) - Installation guide
2. [Configure](configuration.md) - Set up for your project
3. [Git Hooks](dogfooding.md) - Enable validation on commits
4. [Troubleshooting](troubleshooting.md) - Fix common issues

## Questions?

- **Documentation**: [docs/](.)
- **Issues**: [GitLab Issues](https://gitlab.com/jsullivan2/huskycats-bates/-/issues)
- **CI/CD**: [Pipeline Status](https://gitlab.com/jsullivan2/huskycats-bates/-/pipelines)
