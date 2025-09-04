# HuskyCats Local Installation Guide

This guide covers building and installing HuskyCats locally with full container support.

## Prerequisites

- **Podman** or Docker installed and running
- **Python 3.8+** for building the executable
- **Git** for cloning the repository
- **Linux/macOS** (Windows WSL2 supported)

## Step 1: Clone and Build

```bash
# Clone the repository
git clone https://github.com/yourusername/huskycats-bates.git
cd huskycats-bates

# Verify podman is working
podman --version

# Build the container and executable
python3 build.py
```

This will:
1. Build the optimized huskycat container image with all linting tools
2. Export and compress the container image
3. Create a single executable with the embedded container

## Step 2: Test the Build

```bash
# Test the built executable
./dist/huskycat --version

# Run a quick validation test
echo "print('test')" > test.py
./dist/huskycat lint test.py
rm test.py
```

## Step 3: Install System-wide (Optional)

```bash
# Install to /usr/local/bin
sudo cp dist/huskycat /usr/local/bin/

# Now you can use huskycat from anywhere
huskycat --help
```

## Step 4: Initialize in Your Project

```bash
# Navigate to your git repository
cd /path/to/your/project

# Initialize huskycat
huskycat setup-hooks

# This will:
# - Install git hooks (.git/hooks/)
# - Create .huskycat/ directory with configs
# - Set up package.json scripts (if applicable)
```

## Step 5: Test the Hooks

```bash
# Create a test file with issues
cat > bad_code.py << 'EOF'
import os
def bad_function( ):
    x=1
    return x
EOF

# Try to commit (should fail)
git add bad_code.py
git commit -m "test commit"

# Fix with auto-formatting
huskycat lint --fix bad_code.py

# Now commit should work
git add bad_code.py
git commit -m "test commit"
```

## Container Details

The embedded container includes:

### Python Tools
- **black** - Code formatter
- **flake8** - Style guide enforcement
- **mypy** - Static type checker
- **pylint** - Code analysis
- **bandit** - Security linter
- **safety** - Dependency scanner

### JavaScript/TypeScript Tools
- **eslint** - JavaScript linter
- **prettier** - Code formatter
- **typescript-eslint** - TypeScript support

### Other Tools
- **shellcheck** - Shell script analysis
- **hadolint** - Dockerfile linter
- **yamllint** - YAML linter
- **jsonschema** - JSON schema validation
- **ansible-lint** - Ansible playbook linter

## MCP Server Integration

To use the MCP server for advanced validation:

```bash
# Start the MCP server
cd mcp-server
npm install
npm run dev

# The server provides:
# - Hook system for validation workflows
# - Tool orchestration API
# - Session management
# - Real-time validation feedback
```

## Troubleshooting

### Podman Not Found
```bash
# Install podman
sudo apt-get install podman  # Debian/Ubuntu
sudo dnf install podman      # Fedora
brew install podman          # macOS
```

### Build Fails
```bash
# Clean and retry
rm -rf build/ dist/
podman rmi huskycat:latest
python3 build.py
```

### Permission Issues
```bash
# For rootless podman
podman unshare chown -R $USER:$USER ~/.local/share/containers
```

## Architecture Support

HuskyCats supports both AMD64 and ARM64 architectures. The build script automatically detects your architecture and builds the appropriate container.

## Next Steps

- Configure linting rules in `.huskycat/configs/`
- Customize git hooks in `.git/hooks/`
- Set up CI/CD integration (see `docs/gitlab-ci-cd.md`)
- Deploy MCP server for team collaboration