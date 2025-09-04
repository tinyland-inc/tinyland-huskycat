# HuskyCat Simplification Implementation Plan

## Architecture Overview

### Unified Binary Distribution

We're creating a single distributable that combines:
1. **Binary executable** (Python compiled with PyInstaller)
2. **Container image** (pulled from GitLab registry)
3. **MCP stdio server** (integrated into binary)

### Key Simplifications

#### 1. Single Validation Engine
- **Before**: 3 separate validation implementations (772 lines)
- **After**: 1 unified engine in `src/unified_validation.py` (600 lines)
- **Benefit**: 22% code reduction, single source of truth

#### 2. Unified Entry Point
- **Before**: 5 different entry points
- **After**: Single `src/__main__.py` (250 lines)
- **Commands**:
  - `huskycat validate` - Run validation
  - `huskycat setup-hooks` - Setup git hooks
  - `huskycat mcp-server` - MCP server
  - `huskycat info` - System information

#### 3. Simplified MCP Server
- **Before**: Complex HTTP-based server (354 lines)
- **After**: Simple stdio server in `src/mcp_server.py` (300 lines)
- **Benefit**: Direct integration with Claude Code

#### 4. Container Strategy
- **Approach**: Container pulled from registry, not embedded
- **Reason**: Keeps binary small, allows independent updates
- **Registry**: `registry.gitlab.com/tinyland/ai/huskycat:latest`

## UPX Role and Strategy

### Purpose
UPX compresses the binary for faster downloads:
- **Uncompressed**: ~16MB
- **Target with UPX**: ~5-6MB
- **Benefit**: 66% size reduction

### Platform-Specific Approach

#### Linux
```bash
upx --best --lzma huskycat
# Expected: 70-80% compression
```

#### macOS
```bash
upx --best --force-macos huskycat
# Limited compression due to Mach-O format
# Must sign after compression
codesign -s - huskycat
```

#### Windows
```bash
upx --best --lzma huskycat.exe
# Standard compression
```

## Distribution Strategy

### Single Unified Package

Each platform gets one package containing:
```
huskycat-2.0.0-linux-amd64.tar.gz
├── huskycat              # Binary executable
├── install.sh           # Local installer
└── README.md            # Quick start guide
```

### Installation Methods

#### Method 1: One-Line Install (Repository)
```bash
curl -fsSL https://huskycat.io/install | bash
```
- Downloads appropriate binary for platform
- Pulls container from GitLab registry
- Sets up git hooks automatically
- Configures MCP server

#### Method 2: Package Manager
```bash
# macOS
brew install huskycat

# Debian/Ubuntu
apt install huskycat

# RHEL/Rocky
dnf install huskycat
```

#### Method 3: MCP Direct
```bash
claude mcp add huskycat https://huskycat.io/mcp
```

## Build Pipeline

### Containerized Build System

Create `build/BuildContainer` for cross-platform builds:

```dockerfile
FROM alpine:3.19

# Install build tools
RUN apk add --no-cache \
    python3 py3-pip \
    upx git make \
    gcc musl-dev

# Install PyInstaller
RUN pip install pyinstaller

# Build script
COPY build.sh /build.sh
ENTRYPOINT ["/build.sh"]
```

### GitLab CI Pipeline

```yaml
stages:
  - build
  - package
  - publish

build:linux:
  stage: build
  image: registry.gitlab.com/tinyland/ai/huskycat/builder
  script:
    - make build-binary
    - upx --best dist/huskycat
  artifacts:
    paths:
      - dist/

build:macos:
  stage: build
  tags: [macos]
  script:
    - make build-binary
    - codesign -s - dist/huskycat

package:
  stage: package
  script:
    - make package-all

publish:
  stage: publish
  script:
    - make publish-registry
```

## Implementation Timeline

### Phase 1: Core Consolidation (Today)
- [x] Create unified validation engine
- [x] Create simplified MCP server
- [x] Create single entry point
- [x] Create unified installer
- [ ] Remove old redundant files

### Phase 2: Build System (Tomorrow)
- [ ] Fix PyInstaller configuration
- [ ] Create containerized build system
- [ ] Test UPX compression on all platforms
- [ ] Implement code signing for macOS

### Phase 3: Packaging (This Week)
- [ ] Create platform packages (RPM, DEB, brew)
- [ ] Set up GitLab CI/CD
- [ ] Publish to container registry
- [ ] Create download site

### Phase 4: Testing (Next Week)
- [ ] E2E testing on all platforms
- [ ] MCP integration testing
- [ ] Git hooks testing
- [ ] Performance benchmarking

## Files to Remove

### Redundant Python Files
- `huskycat/validators.py` (replaced by unified_validation.py)
- `huskycat/container.py` (simplified into main)
- `src/validation_engine.py` (replaced by unified_validation.py)
- `src/mcp-stdio-server.py` (replaced by mcp_server.py)
- `huskycat.py`, `huskycat_main.py`, `build.py` (redundant entries)

### Redundant Scripts (keep only 3)
Keep:
- `scripts/install-unified.sh` - Installation
- `scripts/clean-slate.sh` - Complete removal
- `scripts/test-distro.sh` - Testing

Remove all others (15 scripts)

### Redundant Documentation
Consolidate 35 docs into 5:
- `README.md` - Overview
- `INSTALL.md` - Installation guide
- `MCP.md` - MCP setup
- `DEVELOPMENT.md` - Developer guide
- `API.md` - API reference

## Benefits Summary

### Code Reduction
- **Current**: ~2,330 lines Python + 18 scripts
- **After**: ~1,150 lines Python + 3 scripts
- **Reduction**: 51% less code

### Binary Size (with UPX)
- **Linux**: ~5MB (from 16MB)
- **macOS**: ~12MB (limited compression)
- **Windows**: ~5MB

### Installation Simplicity
- **One command**: Works everywhere
- **No dependencies**: Self-contained binary
- **Auto-setup**: Git hooks configured automatically

### Maintenance
- **Single codebase**: Easier to maintain
- **Unified testing**: One test suite
- **Clear architecture**: Simple to understand

## Next Immediate Steps

1. Test the unified validation engine
2. Remove redundant files
3. Fix PyInstaller build
4. Create containerized builder
5. Test on multiple platforms

This simplified architecture achieves the core goal: a robust analysis container that ALL git hooks integrate with, installable with one line in any repo, with a simple MCP server for Claude Code.