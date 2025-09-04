# HuskyCat Architecture Analysis & Simplification Roadmap

## Current State Analysis

### Core Requirements (from prompt.txt)
1. **Primary Goal**: Robust analysis container for ALL git hooks
2. **Secondary Goal**: Simple stdio MCP server for Claude Code
3. **Installation**: One-line curl install for any repo
4. **Philosophy**: Run ALL tools by default (avoid feature paralysis)
5. **Deployment**: Prebuilt container from GitLab registry

### Current Architecture

#### File Count & Complexity
- **Core Python**: ~2,330 lines across 7 files
- **Scripts**: 18 shell scripts (many redundant)
- **Documentation**: 35 markdown files (excessive duplication)
- **Tests**: Multiple test frameworks and approaches

#### Key Components
1. **huskycat/cli.py** (877 lines) - Main CLI interface
2. **huskycat/container.py** (310 lines) - Container management
3. **huskycat/validators.py** (411 lines) - Validation logic
4. **src/validation_engine.py** (361 lines) - Unified validation
5. **src/mcp-stdio-server.py** (354 lines) - MCP server

## Identified Issues & Redundancies

### 1. Multiple Entry Points
- `huskycat.py`
- `huskycat_main.py` 
- `huskycat/__main__.py`
- `build.py`
- `setup.py`

**Solution**: Single entry point through `huskycat/__main__.py`

### 2. Duplicate Validation Logic
- `huskycat/validators.py` (411 lines)
- `src/validation_engine.py` (361 lines)
- Container-based validation in `huskycat/container.py`

**Solution**: Consolidate into single `validation_engine.py`

### 3. Excessive Scripts
- 18 shell scripts with overlapping functionality
- Multiple validation scripts doing similar tasks
- Redundant build and install scripts

**Solution**: Reduce to 3 essential scripts:
- `install.sh` - One-line installer
- `validate.sh` - Run validation
- `clean.sh` - Complete removal

### 4. Documentation Sprawl
- 35 markdown files with significant overlap
- Multiple installation guides
- Redundant MCP documentation

**Solution**: Consolidate to 5 core docs:
- `README.md` - Overview and quick start
- `INSTALL.md` - Installation guide
- `MCP.md` - MCP server setup
- `DEVELOPMENT.md` - Developer guide
- `API.md` - Tool API reference

## Simplified Architecture Proposal

### Unified Binary Distribution

#### Single Distributable Package
```
huskycat-<version>-<platform>-<arch>
├── huskycat (binary)
├── container.tar.gz (embedded container image)
└── install.sh (bootstrap script)
```

#### Components
1. **Binary**: Self-contained executable with:
   - Git hooks integration
   - Container runtime detection
   - MCP stdio server
   - Validation engine

2. **Embedded Container**: Compressed container image that:
   - Auto-extracts on first run
   - Links with local runtime (podman/docker)
   - Contains all validation tools

3. **Bootstrap**: Simple installer that:
   - Detects platform
   - Sets up git hooks
   - Configures MCP server
   - Links container

### UPX Role
- **Purpose**: Compress binary for smaller downloads
- **Target**: Reduce from ~16MB to ~4-5MB
- **Platform-specific**:
  - Linux: Maximum compression
  - macOS: Limited due to signing requirements
  - Windows: Standard compression

### Delivery Methods

#### Method 1: Repository Installation
```bash
curl -fsSL https://huskycat.io/install | bash
```
- Downloads appropriate binary
- Sets up git hooks
- Links prebuilt container from registry

#### Method 2: MCP Server Installation
```bash
claude mcp add huskycat https://huskycat.io/mcp
```
- Installs MCP stdio server
- Uses same validation engine
- Shares container with git hooks

### Simplified Codebase Structure
```
huskycat/
├── src/
│   ├── __main__.py          # Single entry point
│   ├── validation.py         # Unified validation engine
│   ├── container.py          # Container management
│   └── mcp.py               # MCP stdio server
├── scripts/
│   ├── install.sh           # One-line installer
│   └── clean.sh             # Complete removal
├── build/
│   └── Containerfile        # Single container definition
├── tests/
│   └── test_validation.py   # PBT with hypothesis
└── docs/
    ├── README.md
    └── MCP.md
```

## Implementation Plan

### Phase 1: Consolidation (Immediate)
1. Merge validation logic into single module
2. Remove duplicate entry points
3. Consolidate scripts to essential 3
4. Unify container definitions

### Phase 2: Binary Packaging (Next)
1. Fix PyInstaller configuration
2. Implement container embedding
3. Add platform-specific signing
4. Create unified installer

### Phase 3: Distribution (Final)
1. Set up GitLab CI/CD for multi-platform builds
2. Publish to container registry
3. Create download site with platform detection
4. Implement MCP server registration

## Benefits of Simplification

### Code Reduction
- **Current**: ~2,330 lines of Python + 18 scripts
- **Target**: ~1,000 lines of Python + 2 scripts
- **Reduction**: 60% less code to maintain

### Installation Simplification
- **Current**: Multiple installation methods and configs
- **Target**: Single binary + embedded container
- **Result**: True one-line installation

### Testing Simplification
- **Current**: Multiple test frameworks and approaches
- **Target**: Single PBT suite with hypothesis
- **Result**: Comprehensive coverage with less code

### Documentation Simplification
- **Current**: 35 scattered markdown files
- **Target**: 5 focused documents
- **Result**: Clear, maintainable documentation

## Technical Decisions

### Why Embed the Container?
- Eliminates network dependency during installation
- Ensures version compatibility
- Simplifies air-gapped deployments
- Single file distribution

### Why UPX?
- Reduces download size significantly
- Maintains functionality
- Standard practice for Go/Rust CLIs
- User expectation for CLI tools

### Why Unified Binary?
- Single artifact to test and sign
- Simplified CI/CD pipeline
- Better user experience
- Easier troubleshooting

## Next Steps

1. **Immediate**: Consolidate validation logic
2. **Today**: Remove redundant files and scripts
3. **Tomorrow**: Fix PyInstaller build for all platforms
4. **This Week**: Implement container embedding
5. **Next Week**: Set up multi-platform CI/CD

## Conclusion

The current codebase has grown organically with significant redundancy. By consolidating to a single binary with embedded container, we can achieve:

- **60% code reduction**
- **True one-line installation**
- **Unified distribution across platforms**
- **Simplified maintenance and testing**

This aligns perfectly with the core requirement: a robust analysis container that ALL git hooks integrate with, installable with one line in any repo.