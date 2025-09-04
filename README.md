# HuskyCat - Friendly Code Validation

A comprehensive code validation platform with MCP server integration for automated code quality enforcement, GitLab CI validation, and container-based development workflows.

## Features

- **Universal Validation**: Black, Flake8, MyPy, Ruff, and custom validators
- **GitLab CI Integration**: Automated CI/CD validation and schema checking  
- **MCP Server**: Claude Code integration for AI-powered validation
- **Container-Based**: Isolated validation environment with Podman
- **One-Line Installation**: Automated setup with git hooks and tooling

## Quick Start

```bash
# Build HuskyCat binary
npm run build:binary

# Check status and configuration
./dist/huskycat status

# Validate your code
./dist/huskycat validate

# Or validate all files
./dist/huskycat validate --all

# Setup git hooks for automatic validation
./dist/huskycat setup-hooks

# Validate CI/CD configuration
./dist/huskycat ci-validate .gitlab-ci.yml

# Start MCP server for Claude Code integration
./dist/huskycat mcp-server

# Clean cache and update schemas
./dist/huskycat clean
./dist/huskycat update-schemas
```

## Alternative Usage via NPM Scripts

You can also use the npm scripts instead of the binary directly:

```bash
# Validate code (Python module)
npm run validate

# Setup git hooks (calls setup-hooks)
npm run hooks:install

# Start MCP server (calls mcp-server)
npm run mcp:server

# Validate GitLab CI
npm run validate:ci

# Check status
npm run status

# Build container image
npm run container:build

# Run all tests (may have import issues)
npm run test:all
```

## Available Commands

| Command | Description | Options |
|---------|-------------|---------|
| `validate` | Run validation on files | `--staged`, `--all`, `[files...]` |
| `install` | Install HuskyCat and dependencies | `--dev`, `--global` |
| `setup-hooks` | Setup git hooks for automatic validation | `--force` |
| `update-schemas` | Update validation schemas from official sources | `--force` |
| `ci-validate` | Validate CI configuration files | `[files...]` |
| `auto-devops` | Validate Auto-DevOps Helm charts and Kubernetes | `--no-helm`, `--no-k8s`, `--simulate`, `--strict` |
| `mcp-server` | Start MCP server for AI integration | `--port PORT` |
| `clean` | Clean cache and temporary files | `--all` |
| `status` | Show HuskyCat status and configuration | |

## Requirements

- Python 3.8+
- UV package manager (`pip install uv`)
- Node.js and npm (for build system)
- Podman or Docker (for containerized validation)

## Installation

1. **Clone and build**:
   ```bash
   git clone <repository>
   cd huskycats-bates
   npm install
   npm run build:binary
   ```

2. **Install Python dependencies**:
   ```bash
   uv sync --dev
   ```

3. **Verify installation**:
   ```bash
   ./dist/huskycat --version
   ./dist/huskycat status
   ```

## Usage Notes

- The binary (`./dist/huskycat`) provides the fastest execution
- NPM scripts use the Python module directly and are useful for development
- Git hooks are automatically installed and will run HuskyCat on commits
- Container-based validation provides isolated environments

## Documentation

Visit [huskycat.pages.io](https://huskycat.pages.io) for complete documentation.