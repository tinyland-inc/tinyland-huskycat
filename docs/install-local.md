# HuskyCat Local Installation Guide

This guide covers installing HuskyCat as a local validation tool with git hooks.

## Installation Options

### Option 1: Pre-built Binary (Recommended)

```bash
# Download the latest release
curl -fsSL https://github.com/yourusername/huskycats-bates/releases/latest/download/huskycat -o huskycat
chmod +x huskycat

# Move to PATH (optional)
sudo mv huskycat /usr/local/bin/

# Initialize in your repository
cd /path/to/your/project
huskycat setup-hooks
```

### Option 2: Build from Source

```bash
# Clone the repository
git clone https://github.com/yourusername/huskycats-bates.git
cd huskycats-bates

# Build the executable
python3 build.py

# Use the built executable
./dist/huskycat setup-hooks
```

### Option 3: Python Package

```bash
# Install via pip
python3 -m pip install --user huskycat

# Initialize in your repository
cd /path/to/your/project
huskycat setup-hooks
```

## What Gets Installed

When you run `huskycat setup-hooks`, the following is set up in your repository:

```
your-project/
├── .huskycat.yaml        # Configuration file
├── .huskycat/            # HuskyCat directory
│   ├── cache/           # Validation cache
│   └── logs/            # Validation logs
└── .git/hooks/          # Git hooks
    ├── pre-commit       # Pre-commit validation
    └── commit-msg       # Commit message validation
```

## Configuration

HuskyCat uses `.huskycat.yaml` for configuration. The default configuration is created during `init`:

```yaml
# .huskycat.yaml
version: "1.0"

validation:
  enabled: true
  staged_only: true      # Only validate staged files in pre-commit
  auto_fix: false        # Don't auto-fix by default
  strict: false          # Don't fail on warnings
  max_errors: 50         # Stop after 50 errors

tools:
  python:
    enabled: true
    tools: [black, flake8, mypy]
    file_patterns: ["*.py", "*.pyi"]
    exclude: ["__pycache__", ".venv", "venv"]
  
  javascript:
    enabled: true
    tools: [eslint, prettier]
    file_patterns: ["*.js", "*.jsx", "*.ts", "*.tsx"]
    exclude: ["node_modules", "dist", "build"]

hooks:
  pre_commit:
    enabled: true
    commands:
      - "huskycat validate --staged"
  
  commit_msg:
    enabled: true
    conventional_commits: true
    allowed_types:
      - feat
      - fix
      - docs
      - style
      - refactor
      - perf
      - test
      - build
      - ci
      - chore
      - revert
```

## Usage

### Manual Validation

```bash
# Validate all files
huskycat validate

# Validate only staged files
huskycat validate --staged

# Auto-fix issues
huskycat validate --fix

# Run specific tool
huskycat validate --tool python-black

# Validate specific files
huskycat validate src/main.py tests/*.py
```

### Git Hooks

Git hooks run automatically:

```bash
# Pre-commit: Validates staged files
git add file.py
git commit -m "feat: add new feature"
# HuskyCat validates file.py before allowing commit

# Commit-msg: Validates commit message format
git commit -m "bad message"  # Will fail
git commit -m "feat: good message"  # Will pass
```

## Troubleshooting

### HuskyCat command not found

```bash
# Check if executable is in PATH
which huskycat

# If not, add to PATH or use full path
./huskycat setup-hooks
```

### Container runtime not found

```bash
# Install Podman (recommended)
sudo apt-get install podman  # Debian/Ubuntu
sudo dnf install podman       # Fedora
brew install podman           # macOS

# Or install Docker
# Follow instructions at https://docs.docker.com/get-docker/
```

### Permission denied

```bash
# Make sure the executable has proper permissions
chmod +x huskycat

# For container runtime issues
sudo usermod -aG podman $USER  # or docker
newgrp podman
```

## Uninstalling

To remove HuskyCat from a repository:

```bash
# Option 1: Clean uninstall
huskycat clean

# Option 2: Manual removal
rm -rf .git/hooks/pre-commit .git/hooks/commit-msg
rm -rf .huskycat .huskycat.yaml
```

## Advanced Features

### Custom Validators

Add custom validation commands to `.huskycat.yaml`:

```yaml
custom:
  scripts:
    - name: "security-scan"
      command: "trivy fs ."
      file_patterns: ["*"]
    - name: "license-check"
      command: "license-checker --production"
      file_patterns: ["package.json"]
```

### CI/CD Integration

```bash
# GitHub Actions
- name: Validate Code
  run: |
    curl -fsSL https://github.com/.../huskycat -o huskycat
    chmod +x huskycat
    ./huskycat validate --ci

# GitLab CI
validate:
  script:
    - wget -O huskycat https://github.com/.../huskycat
    - chmod +x huskycat
    - ./huskycat validate --ci
```

## Next Steps

- [Configure validation rules](configuration.md)
- [Set up MCP server for AI assistance](install-mcp.md)
- [Integrate with CI/CD](ci-integration.md)