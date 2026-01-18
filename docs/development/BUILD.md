# HuskyCat Build Guide

Reproducible local build instructions for all execution models.

## Prerequisites

| Dependency | Version | Purpose | Install |
|------------|---------|---------|---------|
| Python | >= 3.9 | Runtime | System package manager |
| UV | >= 0.4.0 | Package manager | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | >= 18 | NPM scripts | System package manager |
| Podman/Docker | Any | Container builds | `brew install podman` or system |

## Quick Start

```bash
# Clone repository
git clone https://gitlab.com/tinyland/ai/huskycat.git
cd huskycat

# Install dependencies (deterministic via uv.lock)
uv sync --dev

# Configure git hooks (optional)
npm run hooks:install

# Verify installation
npm run status
```

## Build Pathways

HuskyCat supports 3 execution models. Choose based on your use case.

### 1. UV Development Mode

For development and testing:

```bash
# Install all dependencies
uv sync --dev

# Run HuskyCat
npm run dev -- --help
npm run validate
npm run test:unit

# MCP server
npm run mcp:server
```

### 2. Container Build

For consistent, isolated execution:

```bash
# Build container (Alpine 3.19, multi-arch)
npm run container:build

# Test container
npm run container:test

# Run validation in container
npm run container:validate
```

### 3. Fat Binary Build

For standalone, portable execution:

```bash
# Step 1: Download embedded tools for your platform
npm run tools:download

# Step 2: Build PyInstaller binary
npm run build:binary

# Step 3: Verify binary
npm run verify:binary

# Result: dist/huskycat (single file, ~175MB)
```

#### Platform-Specific Binary Builds

```bash
# Detect platform automatically
python3 scripts/download_tools.py --platform auto

# Or specify explicitly
python3 scripts/download_tools.py --platform linux-amd64
python3 scripts/download_tools.py --platform linux-arm64
python3 scripts/download_tools.py --platform darwin-arm64
```

## Reproducibility

### Lock Files

| File | Purpose | Status |
|------|---------|--------|
| `uv.lock` | Python dependencies | Tracked |
| `package-lock.json` | Node.js dependencies | N/A (no node deps) |

### Verification Commands

```bash
# Verify Python environment matches lock
uv sync --locked

# Verify binary functionality
bash scripts/verify_binary.sh dist/huskycat

# Run full test suite
uv run pytest tests/ -v
```

## CI/CD Pipeline

The GitLab CI pipeline (`.gitlab-ci.yml`) performs:

1. **validate** - Container builds (amd64, arm64)
2. **security** - SAST, dependency scanning
3. **build** - Tool downloads, binary builds
4. **test** - Unit tests, MCP server tests
5. **package** - Fat binaries for 3 platforms
6. **sign** - Binary verification, checksums
7. **deploy** - GitLab Pages documentation

### Local CI Validation

```bash
# Validate CI configuration
npm run validate:ci

# Run same tests as CI
npm run test:all
```

## Directory Structure

```
huskycat/
├── src/huskycat/           # Python source
│   ├── __main__.py         # CLI entry point
│   ├── mcp_server.py       # MCP server
│   └── core/               # Core modules
├── huskycat_main.py        # Binary entry point
├── ContainerFile           # Container definition
├── pyproject.toml          # Python package config
├── package.json            # NPM scripts
├── uv.lock                 # Python lock file
├── scripts/
│   ├── download_tools.py   # Tool downloader
│   ├── verify_binary.sh    # Binary verification
│   └── install.sh          # Installation script
└── dist/                   # Build outputs
    ├── bin/                # Compiled binaries
    └── tools/              # Downloaded tools
```

## Troubleshooting

### UV Sync Fails

```bash
# Clear UV cache and retry
rm -rf ~/.cache/uv
uv sync --dev
```

### Container Build Fails

```bash
# Clean podman cache
podman system prune -af
npm run container:build
```

### Binary Not Executable

```bash
chmod +x dist/huskycat
./dist/huskycat --version
```

### Missing Embedded Tools

```bash
# Re-download tools
npm run tools:clean
npm run tools:download
npm run build:binary
```

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `HUSKYCAT_MODE` | Force product mode | Auto-detect |
| `HUSKYCAT_LOG_LEVEL` | Logging verbosity | INFO |
| `UV_CACHE_DIR` | UV cache location | ~/.cache/uv |

## Next Steps

- [Configuration Reference](docs/configuration.md)
- [Product Modes](docs/architecture/product-modes.md)
- [Execution Models](docs/architecture/execution-models.md)
