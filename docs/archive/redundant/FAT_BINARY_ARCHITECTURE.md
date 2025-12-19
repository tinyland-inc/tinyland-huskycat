# HuskyCat Fat Binary Architecture

## Overview

HuskyCat fat binaries are self-contained executables that include all validation tools and dependencies in a single file. This document describes the architecture, build process, and runtime behavior.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     HuskyCat Fat Binary                         │
│                          (150-200MB)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              Python Runtime Bundle                        │ │
│  │  - Python 3.9+ interpreter                     (~40MB)    │ │
│  │  - Standard library modules                               │ │
│  │  - Core dependencies (PyYAML, jsonschema, etc.)          │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              HuskyCat Application Code                    │ │
│  │  - Core validation engine                      (~5MB)     │ │
│  │  - Mode detection and adapters                            │ │
│  │  - MCP server implementation                              │ │
│  │  - CLI interface                                          │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              Embedded Validation Tools                    │ │
│  │  - shellcheck (bash/sh validation)           (~100-150MB) │ │
│  │  - hadolint (Dockerfile linting)                          │ │
│  │  - taplo (TOML formatting)                                │ │
│  │  - versions.txt (tool version manifest)                   │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              Embedded Formatters                          │ │
│  │  - Chapel formatter (Python implementation)    (~5MB)     │ │
│  │  - Configuration schemas                                  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Runtime Extraction

On first run, the binary extracts embedded tools to the user's cache:

```
1. Binary starts
2. tool_extractor detects PyInstaller bundle
3. Check ~/.huskycat/tools/.version
4. Compare with bundle version
5. Extract tools if needed (one-time)
6. Add ~/.huskycat/tools/ to PATH
7. Continue normal execution
```

### Tool Cache Structure

```
~/.huskycat/
└── tools/
    ├── .version              # Bundle version marker
    ├── shellcheck            # Extracted binaries
    ├── hadolint
    ├── taplo
    └── versions.txt          # Tool version manifest
```

## Build Process

### Phase 1: Tool Download

```bash
python scripts/download_tools.py --all
```

Downloads platform-specific binaries:

```
dist/tools/
├── darwin-arm64/
│   ├── shellcheck      (from GitHub releases)
│   ├── hadolint        (from GitHub releases)
│   ├── taplo           (from GitHub releases)
│   └── versions.txt    (generated manifest)
├── darwin-amd64/
├── linux-arm64/
└── linux-amd64/
```

**Tool Sources:**
- shellcheck: GitHub releases (tar.xz archives)
- hadolint: GitHub releases (direct binaries)
- taplo: GitHub releases (gzipped binaries)

**Current Versions:**
- shellcheck: 0.10.0
- hadolint: 2.12.0
- taplo: 0.9.3

### Phase 2: PyInstaller Bundle

```bash
python build_fat_binary.py
```

Creates PyInstaller spec and builds binary:

1. **Generate spec file** with embedded tools
2. **Run PyInstaller** with bundle configuration
3. **Verify binary** size and execution
4. **Generate checksums** (SHA256)
5. **Output artifacts** to dist/{platform}/

### Phase 3: Verification

```bash
./dist/darwin-arm64/huskycat --help
./dist/darwin-arm64/huskycat status
```

Verifies:
- Binary executes successfully
- Size is under 250MB target
- Tools extract correctly
- Validation works end-to-end

## Component Responsibilities

### 1. scripts/download_tools.py

**Purpose:** Download platform-specific validation tool binaries

**Features:**
- Auto-detect current platform
- Download from GitHub releases
- Extract archives (tar.xz, gzip)
- Verify binary integrity
- Generate version manifests
- Support multiple platforms

**Usage:**
```bash
# Current platform
python scripts/download_tools.py

# Specific platform
python scripts/download_tools.py --platform linux-amd64

# All platforms
python scripts/download_tools.py --all

# Clean downloads
python scripts/download_tools.py --clean
```

### 2. build_fat_binary.py

**Purpose:** Build fat binary with embedded toolchain

**Features:**
- Auto-detect or specify platform
- Download tools (or skip)
- Generate PyInstaller spec
- Build with PyInstaller
- Verify binary size and execution
- Generate SHA256 checksums
- Support multi-platform builds

**Usage:**
```bash
# Current platform
python build_fat_binary.py

# Specific platform
python build_fat_binary.py --platform linux-amd64

# All platforms
python build_fat_binary.py --all-platforms

# Skip download (use existing)
python build_fat_binary.py --skip-download
```

### 3. src/huskycat/core/tool_extractor.py

**Purpose:** Runtime tool extraction and PATH management

**Features:**
- Detect PyInstaller bundle
- Version-aware extraction
- One-time extraction per version
- Automatic PATH setup
- Tool information queries

**API:**
```python
from huskycat.core.tool_extractor import (
    ensure_tools,      # Ensure tools available
    get_tools_info,    # Get tool paths
    get_extractor,     # Get extractor instance
)

# Auto-extract on import (bundled mode)
ensure_tools()

# Get tool information
tools = get_tools_info()
# {'shellcheck': Path('...'), 'hadolint': Path('...'), ...}
```

### 4. src/huskycat/__main__.py

**Purpose:** Main CLI entry point with tool extraction

**Changes:**
```python
def main() -> int:
    # Ensure embedded tools are available (for fat binary)
    from .core.tool_extractor import ensure_tools
    ensure_tools()

    # ... rest of CLI logic
```

## NPM Scripts

Added to package.json:

```json
{
  "scripts": {
    "build:fat": "uv run python build_fat_binary.py",
    "build:fat:all": "uv run python build_fat_binary.py --all-platforms",
    "tools:download": "uv run python scripts/download_tools.py",
    "tools:download:all": "uv run python scripts/download_tools.py --all",
    "tools:clean": "uv run python scripts/download_tools.py --clean"
  }
}
```

## Platform Support

| Platform | Binary Name | Size Target | Status |
|----------|-------------|-------------|--------|
| darwin-arm64 | huskycat | ~180MB | Supported |
| darwin-amd64 | huskycat | ~190MB | Supported |
| linux-arm64 | huskycat | ~170MB | Supported |
| linux-amd64 | huskycat | ~175MB | Supported |

## Size Optimization

Current optimizations:

1. **Excluded modules** (PyInstaller)
   - tkinter (GUI framework)
   - PIL/Pillow (image processing)
   - matplotlib (plotting)
   - numpy (numerical computing)
   - pandas (data analysis)
   - scipy (scientific computing)
   - IPython (interactive shell)

2. **UPX compression** (optional)
   - Can reduce size by 30-50%
   - May cause issues on macOS (code signing)
   - Use `npm run build:upx` if needed

3. **Tool selection**
   - Only include essential validation tools
   - Python tools use embedded runtime (no duplication)
   - Native tools are compact binaries

## Distribution Strategy

### Release Artifacts

For each release, build and distribute:

1. **Platform-specific binaries**
   - `huskycat-v2.0.0-darwin-arm64.tar.gz`
   - `huskycat-v2.0.0-darwin-amd64.tar.gz`
   - `huskycat-v2.0.0-linux-arm64.tar.gz`
   - `huskycat-v2.0.0-linux-amd64.tar.gz`

2. **All-in-one package**
   - `huskycat-v2.0.0-all-platforms.tar.gz`

3. **Checksums**
   - `huskycat-v2.0.0.sha256sums.txt`

### Installation

Users can download and install:

```bash
# Download platform binary
curl -L https://huskycat.pages.io/downloads/huskycat-darwin-arm64 -o huskycat
chmod +x huskycat

# Move to PATH
sudo mv huskycat /usr/local/bin/

# Verify
huskycat --version
huskycat status
```

## CI/CD Integration

### GitLab CI

```yaml
build:fat-binaries:
  stage: build
  parallel:
    matrix:
      - PLATFORM: ["linux-amd64", "darwin-arm64", "darwin-amd64", "linux-arm64"]
  script:
    - python scripts/download_tools.py --platform $PLATFORM
    - python build_fat_binary.py --platform $PLATFORM --skip-download
  artifacts:
    paths:
      - dist/${PLATFORM}/huskycat*
```

### GitHub Actions

```yaml
- name: Build Fat Binary
  run: |
    python scripts/download_tools.py --platform ${{ matrix.platform }}
    python build_fat_binary.py --platform ${{ matrix.platform }} --skip-download
  strategy:
    matrix:
      platform: [linux-amd64, darwin-arm64, darwin-amd64, linux-arm64]
```

## Security Considerations

1. **Tool Verification**
   - Download from official GitHub releases only
   - Verify checksums (future enhancement)
   - Use HTTPS for all downloads

2. **Binary Signing**
   - macOS: Code signing with Developer ID
   - Linux: GPG signatures on releases
   - Windows: Authenticode signing (future)

3. **Tool Isolation**
   - Tools extracted to user cache only
   - No system-wide installation
   - No elevated privileges required

## Future Enhancements

### Short Term

1. **Checksum verification** for downloaded tools
2. **Progress bars** for long downloads
3. **Parallel downloads** for multi-platform builds
4. **Binary compression** options (UPX, etc.)

### Long Term

1. **Python tool bundling** (black, ruff, mypy as single binary)
2. **Node.js tool bundling** (eslint, prettier via pkg)
3. **Auto-update mechanism** for fat binaries
4. **Plugin system** for custom tools
5. **Windows support** (exe binaries)

## Troubleshooting

### Binary Too Large

If binary exceeds 250MB:

1. Remove more Python modules (see build_fat_binary.py)
2. Use UPX compression (macOS may need unsigned)
3. Strip debug symbols from tools
4. Consider tool subset for specific use cases

### Extraction Fails

If tool extraction fails at runtime:

1. Check `~/.huskycat/tools/` permissions
2. Verify disk space availability
3. Check `.version` file for corruption
4. Clean cache and retry: `rm -rf ~/.huskycat/tools/`

### Cross-Platform Builds

PyInstaller only builds for current platform:

1. Use CI with multiple runners (Linux, macOS)
2. Or use Docker/VMs for each platform
3. Or distribute source for user builds

## References

- PyInstaller: https://pyinstaller.org/
- shellcheck: https://github.com/koalaman/shellcheck
- hadolint: https://github.com/hadolint/hadolint
- taplo: https://github.com/tamasfe/taplo
- StaticX (Linux): https://github.com/JonathonReinhart/staticx
