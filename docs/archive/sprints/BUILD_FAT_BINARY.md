# Building HuskyCat Fat Binaries

This document describes how to build HuskyCat fat binaries with embedded validation toolchains.

## Overview

HuskyCat fat binaries are self-contained executables that include:
- Python runtime and HuskyCat code
- All validation tool binaries (shellcheck, hadolint, taplo)
- Chapel formatter implementation
- Configuration schemas and templates

The resulting binaries require no external dependencies and are suitable for distribution.

## Binary Structure

```
huskycat (150-200MB)
├── Python runtime (~40MB)
├── HuskyCat code (~5MB)
├── Embedded tools (~100-150MB)
│   ├── shellcheck
│   ├── hadolint
│   └── taplo
└── Chapel formatter (~5MB)
```

On first run, the binary extracts tools to `~/.huskycat/tools/` and adds them to PATH.

## Supported Platforms

- `linux-amd64` - Linux x86_64
- `linux-arm64` - Linux ARM64 (aarch64)
- `darwin-amd64` - macOS x86_64 (Intel)
- `darwin-arm64` - macOS ARM64 (Apple Silicon)

## Quick Start

### Build for Current Platform

```bash
# Download tools and build fat binary
npm run build:fat

# Or manually:
python scripts/download_tools.py
python build_fat_binary.py
```

### Build for All Platforms

```bash
# Build fat binaries for all supported platforms
npm run build:fat:all

# Or manually:
python scripts/download_tools.py --all
python build_fat_binary.py --all-platforms
```

### Test the Binary

```bash
# Test current platform binary
./dist/darwin-arm64/huskycat --help
./dist/darwin-arm64/huskycat status
./dist/darwin-arm64/huskycat validate

# Verify embedded tools
./dist/darwin-arm64/huskycat validate --verbose
```

## Build Process

### Step 1: Download Validation Tools

The `scripts/download_tools.py` script downloads platform-specific binaries:

```bash
# Auto-detect platform
python scripts/download_tools.py

# Specific platform
python scripts/download_tools.py --platform linux-amd64

# All platforms
python scripts/download_tools.py --all

# Custom output directory
python scripts/download_tools.py --output-dir /path/to/tools
```

Downloaded tools are stored in `dist/tools/{platform}/`:

```
dist/tools/
├── darwin-arm64/
│   ├── shellcheck
│   ├── hadolint
│   ├── taplo
│   └── versions.txt
├── darwin-amd64/
├── linux-arm64/
└── linux-amd64/
```

### Step 2: Build Fat Binary

The `build_fat_binary.py` script creates PyInstaller bundles with embedded tools:

```bash
# Auto-detect platform
python build_fat_binary.py

# Specific platform
python build_fat_binary.py --platform linux-amd64

# All platforms
python build_fat_binary.py --all-platforms

# Skip tool download (use existing)
python build_fat_binary.py --skip-download
```

Output binaries are stored in `dist/{platform}/`:

```
dist/
├── darwin-arm64/
│   ├── huskycat
│   └── huskycat.sha256
├── darwin-amd64/
├── linux-arm64/
└── linux-amd64/
```

### Step 3: Verify Binary

```bash
# Check binary size
ls -lh dist/darwin-arm64/huskycat

# Verify checksum
shasum -a 256 -c dist/darwin-arm64/huskycat.sha256

# Test execution
./dist/darwin-arm64/huskycat --help
./dist/darwin-arm64/huskycat status
```

## Runtime Tool Extraction

When running from a fat binary, tools are automatically extracted on first run:

1. Binary detects it's running from PyInstaller bundle
2. Checks if tools are already extracted to `~/.huskycat/tools/`
3. Compares bundle version with cached version
4. Extracts tools if needed (one-time operation)
5. Adds `~/.huskycat/tools/` to PATH

Version checking ensures tools are re-extracted when the binary is updated.

### Manual Tool Management

```python
from huskycat.core.tool_extractor import get_extractor

# Get extractor instance
extractor = get_extractor()

# Check if extraction needed
if extractor.needs_extraction():
    print("Tools need extraction")

# Force extraction
extractor.extract_tools()

# Get tool information
tools = extractor.get_tool_info()
for name, path in tools.items():
    print(f"{name}: {path}")
```

## Tool Versions

Current tool versions:

- **shellcheck**: 0.10.0
- **hadolint**: 2.12.0
- **taplo**: 0.9.3

To update tool versions, edit `scripts/download_tools.py` and update the `TOOL_URLS` dictionary.

## Expected Binary Sizes

Target sizes by platform:

| Platform | Size | Components |
|----------|------|------------|
| darwin-arm64 | ~180MB | Python runtime (40MB) + Tools (130MB) + Code (10MB) |
| darwin-amd64 | ~190MB | Similar breakdown |
| linux-arm64 | ~170MB | Smaller Python runtime |
| linux-amd64 | ~175MB | Similar breakdown |

If binaries exceed 250MB, consider:
- Removing unused Python modules (matplotlib, numpy, etc.)
- Using UPX compression (may cause issues on macOS)
- Stripping debug symbols from tools

## CI Integration

### GitLab CI

```yaml
build:fat-binaries:
  stage: build
  image: python:3.11
  script:
    - pip install -r requirements.txt
    - python scripts/download_tools.py --all
    - python build_fat_binary.py --all-platforms
  artifacts:
    paths:
      - dist/*/huskycat*
    expire_in: 30 days
```

### GitHub Actions

```yaml
- name: Build Fat Binaries
  run: |
    pip install -r requirements.txt
    python scripts/download_tools.py --all
    python build_fat_binary.py --all-platforms

- name: Upload Artifacts
  uses: actions/upload-artifact@v3
  with:
    name: huskycat-binaries
    path: dist/*/huskycat*
```

## Distribution

### Release Package

Create a release package with all binaries:

```bash
# Build all platforms
npm run build:fat:all

# Create release tarball
tar -czf huskycat-v2.0.0-all-platforms.tar.gz \
  dist/darwin-arm64/huskycat* \
  dist/darwin-amd64/huskycat* \
  dist/linux-arm64/huskycat* \
  dist/linux-amd64/huskycat*
```

### Platform-Specific Packages

```bash
# macOS ARM64
tar -czf huskycat-v2.0.0-darwin-arm64.tar.gz \
  -C dist/darwin-arm64 huskycat huskycat.sha256

# Linux AMD64
tar -czf huskycat-v2.0.0-linux-amd64.tar.gz \
  -C dist/linux-amd64 huskycat huskycat.sha256
```

## Troubleshooting

### Binary Too Large

If binary exceeds 250MB:

```python
# In build_fat_binary.py, add more exclusions:
excludes=[
    'tkinter',
    'PIL',
    'matplotlib',
    'numpy',
    'pandas',
    'scipy',
    'IPython',
    'jupyter',
    'notebook',
    'sphinx',
]
```

### Tool Extraction Fails

Check permissions and disk space:

```bash
# Check cache directory
ls -la ~/.huskycat/tools/

# Manual extraction test
python -c "from huskycat.core.tool_extractor import ensure_tools; ensure_tools()"

# Clean and retry
rm -rf ~/.huskycat/tools/
./dist/darwin-arm64/huskycat status
```

### Cross-Platform Builds

PyInstaller can only build for the current platform. For multi-platform builds:

1. Use CI with multiple runners (Linux, macOS, Windows)
2. Or use Docker/VMs for each target platform
3. Or distribute source and let users build locally

## Advanced Configuration

### Custom Tool URLs

Edit `scripts/download_tools.py` to use custom tool sources:

```python
TOOL_URLS = {
    "shellcheck": {
        "linux-amd64": (
            "https://internal-mirror.company.com/shellcheck-linux-amd64",
            None,
        ),
    },
}
```

### Binary Signing (macOS)

```bash
# Sign binary for distribution
codesign --sign "Developer ID Application" \
  --entitlements entitlements.plist \
  --options runtime \
  --timestamp \
  dist/darwin-arm64/huskycat

# Verify signature
codesign --verify --deep --strict dist/darwin-arm64/huskycat
```

### Static Linking (Linux)

For truly static binaries on Linux, use StaticX:

```bash
pip install staticx
staticx dist/linux-amd64/huskycat dist/linux-amd64/huskycat-static
```

## References

- [PyInstaller Documentation](https://pyinstaller.org/)
- [shellcheck Releases](https://github.com/koalaman/shellcheck/releases)
- [hadolint Releases](https://github.com/hadolint/hadolint/releases)
- [taplo Releases](https://github.com/tamasfe/taplo/releases)
