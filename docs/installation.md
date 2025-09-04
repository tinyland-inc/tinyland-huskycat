# Installation Guide

This guide covers installing HuskyCat locally and in development projects.

## Prerequisites

- **Python 3.8+**: Required for the core validation platform
- **UV Package Manager**: Fast Python dependency management (`pip install uv`)
- **Node.js and npm**: For build system and npm scripts
- **Podman or Docker**: For containerized validation (optional)
- **Git Repository**: The project must be a Git repository

## 🚀 Quick Start - HuskyCat Installation

HuskyCat provides multiple installation methods to suit different workflows.

### Method 1: Build from Source (Recommended)

```bash
# Clone and build HuskyCat
git clone <repository>
cd huskycats-bates
npm install
npm run build:binary

# Install Python dependencies
uv sync --dev

# Verify installation
./dist/huskycat --version
./dist/huskycat status
```

### Method 2: Development Mode

```bash
# For active development on HuskyCat itself
npm run dev -- --help             # Show available commands
npm run validate                   # Validate current directory
npm run hooks:install              # Setup git hooks
npm run mcp:server                 # Start MCP server
```

## Using HuskyCat in Your Projects

### 1. Setup Git Hooks

```bash
# Navigate to your project
cd your-project

# Setup HuskyCat git hooks
./path/to/huskycat setup-hooks

# Test the installation
git add .
git commit -m "test: verify hooks"  # Should run validation
```

### 2. Validate Code

```bash
# Validate current directory
./path/to/huskycat validate

# Validate specific files
./path/to/huskycat validate src/main.py

# Validate all files
./path/to/huskycat validate --all

# Validate only staged files
./path/to/huskycat validate --staged
```

## MCP Server Integration

### Setup MCP for Claude Code

```bash
# Start MCP server for Claude Code integration
./path/to/huskycat mcp-server

# Test MCP server
./path/to/huskycat mcp-server --port 8080

# Configure in Claude Code MCP settings:
# Command: /path/to/huskycat
# Args: ["mcp-server", "--port=0"]
```

## Container-based Validation

### Build and Use Container

```bash
# Build HuskyCat container
npm run container:build

# Test container
npm run container:test

# Run validation in container
podman run --rm -v "$(pwd):/workspace" huskycat:local validate --all
```

## What Gets Configured

HuskyCat setup creates:

```
your-project/
├── .git/hooks/               # Git hooks installed by setup-hooks
│   ├── pre-commit           # Validates staged files
│   ├── pre-push             # Validates CI configuration  
│   └── commit-msg           # Validates commit message format
├── .huskycat/               # Configuration and cache
│   ├── config.json         # HuskyCat configuration
│   └── schemas/            # Downloaded validation schemas
└── (existing project files remain unchanged)
```

## Post-Installation

### Verify Installation

```bash
# Check HuskyCat status
./dist/huskycat status

# Test validation
./dist/huskycat validate --all

# Verify git hooks are working
git add .
git commit -m "test: verify hooks"  # Should run validation

# Update validation schemas
./dist/huskycat update-schemas
```

### Using HuskyCat Commands

After installation, you can use these commands:

```bash
# Validate code
./dist/huskycat validate                    # Validate current directory
./dist/huskycat validate --staged          # Validate staged files
./dist/huskycat validate src/main.py       # Validate specific file

# CI/CD validation  
./dist/huskycat ci-validate .gitlab-ci.yml # Validate GitLab CI

# MCP integration
./dist/huskycat mcp-server                  # Start MCP server

# Management
./dist/huskycat clean                       # Clean cache
./dist/huskycat update-schemas              # Update schemas
./dist/huskycat status                      # Show status
```

## Development Configuration

### Configure Your IDE

#### VS Code
Add to `.vscode/settings.json`:
```json
{
  "editor.formatOnSave": true,
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

#### PyCharm
1. Go to Settings → Tools → File Watchers
2. Add watchers for Black and flake8
3. Enable "Reformat on Save"

### Update package.json Scripts

Add these helpful scripts:
```json
{
  "scripts": {
    "lint": "./scripts/comprehensive-lint.sh --all",
    "lint:fix": "./scripts/comprehensive-lint.sh --all --fix",
    "lint:staged": "./scripts/comprehensive-lint.sh --staged",
    "prepare": "husky install"
  }
}
```

## Troubleshooting

### Architecture Issues

1. **"exec format error" when running Docker**
   ```bash
   # This means architecture mismatch. Use the platform flag:
   docker run --rm --platform linux/amd64 -v "$(pwd):/workspace" \
     registry.gitlab.com/jsullivan2_bates/pubcontainers/husky-lint:latest
   
   # Or use the install script which auto-detects:
   curl -fsSL https://gitlab.com/jsullivan2_bates/pubcontainers/-/raw/main/install.sh | bash
   ```

2. **Check your system architecture**
   ```bash
   # See what architecture you're running
   uname -m
   # x86_64 = use linux/amd64
   # arm64 or aarch64 = use linux/arm64
   
   # Check Docker image architecture
   docker inspect registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest | grep Architecture
   ```

### Common Issues

1. **"command not found" errors**
   - Ensure tools are installed and in PATH
   - Try using full paths in scripts

2. **Permission denied**
   - Make scripts executable: `chmod +x <script>`
   - Check file permissions

3. **Python tools not found**
   - Activate virtual environment
   - Install missing tools with pip

4. **Husky hooks not running**
   - Run `npx husky install`
   - Check Git version (needs 2.9+)
   - Ensure core.hooksPath is not set

See [Troubleshooting Guide](troubleshooting.md) for more solutions.