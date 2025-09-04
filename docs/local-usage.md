# Local Usage Guide - Container Only

This guide explains how to use HuskyCats Bates locally with containers. All tools run in containers - no local installation required!

## Prerequisites

- **Podman** or **Docker** - That's it!
- Git repository where you want to apply linting

> **Note**: The scripts automatically detect whether you have podman or docker installed and use the appropriate tool.

## Installation

### Using Published Image (Recommended)

```bash
# Navigate to your project
cd /path/to/your/project

# Install HuskyCats Bates
curl -fsSL https://gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/-/raw/main/install.sh | bash

# Or directly with podman/docker
podman run --rm -v "$(pwd):/workspace" \
  registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest
# or: docker run --rm -v "$(pwd):/workspace" registry.gitlab.com/...
```

### Building from Source (For Development)

```bash
# Clone the repository
git clone https://gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates.git
cd huskycats-bates

# Build the container image (auto-detects podman/docker)
./build.sh -t local

# Or manually with podman
podman build -f ContainerFile -t husky-lint:local .

# Or manually with docker
docker build -f ContainerFile -t husky-lint:local .

# Use your local build
cd /path/to/your/project
podman run --rm -v "$(pwd):/workspace" husky-lint:local
```

## Daily Usage

After installation, you have three ways to run linters:

### 1. Using the Convenience Script (Easiest)

```bash
# The installer creates a 'husky-lint' script
./husky-lint lint         # Run all linters
./husky-lint lint-fix     # Auto-fix issues
./husky-lint shell        # Interactive shell
./husky-lint black        # Run specific tool
./husky-lint flake8       # Python linting
./husky-lint shellcheck   # Shell script linting
```

### 2. Using Compose

```bash
# With podman-compose
podman-compose -f podman-compose.husky-lint.yml run --rm lint
podman-compose -f podman-compose.husky-lint.yml run --rm lint-fix
podman-compose -f podman-compose.husky-lint.yml run --rm shell

# With docker-compose
docker-compose -f docker-compose.husky-lint.yml run --rm lint
docker-compose -f docker-compose.husky-lint.yml run --rm lint-fix
docker-compose -f docker-compose.husky-lint.yml run --rm shell
```

### 3. Direct Container Commands

```bash
# Run comprehensive linting with podman
podman run --rm -v "$(pwd):/workspace" \
  --entrypoint /bin/bash \
  registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest \
  /workspace/scripts/comprehensive-lint.sh

# Interactive shell with podman
podman run --rm -it -v "$(pwd):/workspace" \
  --entrypoint /bin/bash \
  registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest

# Same commands work with docker - just replace 'podman' with 'docker'
```

## Running Specific Tools

### Python Linting

```bash
# Using convenience script
./husky-lint black        # Check formatting
./husky-lint flake8       # Lint code
./husky-lint mypy         # Type checking
./husky-lint pylint       # Advanced linting
./husky-lint bandit       # Security scanning

# Direct container command for specific files
podman run --rm -v "$(pwd):/workspace" \
  --entrypoint black \
  registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest \
  --check src/main.py
```

### Shell Script Linting

```bash
# Check all shell scripts
./husky-lint shellcheck

# Check specific script
podman run --rm -v "$(pwd):/workspace" \
  --entrypoint shellcheck \
  registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest \
  scripts/deploy.sh
```

### Dockerfile Linting

```bash
# Check all Dockerfiles
./husky-lint hadolint

# Check specific ContainerFile/Dockerfile
podman run --rm -v "$(pwd):/workspace" \
  --entrypoint hadolint \
  registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest \
  ContainerFile.prod
```

### YAML Validation

```bash
# Validate all YAML files
./husky-lint shell -c "yamllint ."

# Validate GitLab CI
./husky-lint shell -c "python -c 'import yaml; yaml.safe_load(open(\".gitlab-ci.yml\"))'"
```

## Interactive Development

For exploring and debugging, use the interactive shell:

```bash
# Start interactive session
./husky-lint shell

# Now you're inside the container with all tools:
black --check .
flake8 --statistics
mypy --strict src/
pylint src/
ruff check .
bandit -r .
shellcheck scripts/*.sh
hadolint Dockerfile
yamllint .
ansible-lint playbooks/
```

## Git Hooks Behavior

HuskyCats Bates installs container-aware Git hooks that:

1. **Auto-detect podman or docker**
2. **Check for local container images first**
3. **Fall back to registry images if needed**
4. **Show warnings but don't block commits if neither tool is available**

```bash
# Normal commit - hooks run automatically
git add . && git commit -m "feat: new feature"

# Skip hooks if needed
git commit --no-verify -m "WIP: work in progress"

# Manually run pre-commit checks
./husky-lint lint
```

## Customizing Behavior

### Environment Variables

```bash
# Use a different image
export HUSKY_IMAGE=husky-lint:local
./husky-lint lint

# Skip certain checks
export SKIP_PYTHON=true
./husky-lint lint

# Enable verbose output
export VERBOSE=true
./husky-lint lint

# Auto-fix mode
export AUTO_FIX=true
./husky-lint lint
```

### Modifying Configurations

1. **Python formatting** - Edit `pyproject.toml`:
```toml
[tool.black]
line-length = 100  # Change from default 88
```

2. **Python linting** - Edit `.flake8`:
```ini
[flake8]
max-line-length = 100
ignore = E203,W503
```

3. **Lint-staged** - Edit `.lintstagedrc.json`:
```json
{
  "*.py": ["black", "flake8 --max-line-length=100"]
}
```

## Troubleshooting

### Container Runtime Not Running

```bash
# Check podman status
podman info

# Check docker status
docker info

# Start Docker Desktop (macOS)
open -a Docker

# Start Docker service (Linux)
sudo systemctl start docker

# Start Podman service (Linux)
systemctl --user start podman.socket
```

### Permission Issues

```bash
# Run with user mapping (podman handles this automatically)
podman run --rm -v "$(pwd):/workspace" \
  registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest

# For docker, you may need user mapping
docker run --rm -v "$(pwd):/workspace" \
  -u $(id -u):$(id -g) \
  registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest
```

### Image Updates

```bash
# Pull latest image with podman
podman pull registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest

# Remove old images
podman image prune

# Or with docker
docker pull registry.gitlab.com/...
docker image prune
```

### Debugging Tools

```bash
# Verbose output
./husky-lint shell -c "black --verbose --check ."
./husky-lint shell -c "flake8 --show-source --statistics ."
./husky-lint shell -c "mypy --show-error-codes ."

# Check what files will be linted
./husky-lint shell -c "find . -name '*.py' -type f"
./husky-lint shell -c "find . -name '*.sh' -type f"
```

## Performance Tips

### 1. Use Local Images

```bash
# Pull once, use many times
docker pull registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest

# Tag for easier access
podman tag registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest husky:latest
```

### 2. Lint Only Changed Files

```bash
# Lint only staged files
git diff --staged --name-only | grep '\.py$' | xargs ./husky-lint black --check

# Lint files changed in last commit
git diff HEAD~1 --name-only | grep '\.py$' | xargs ./husky-lint flake8
```

### 3. Parallel Execution

```bash
# Run multiple linters in parallel
./husky-lint black &
./husky-lint flake8 &
./husky-lint shellcheck &
wait
```

## IDE Integration

### VS Code

1. Install "Docker" and "Remote - Containers" extensions (works with both podman and docker)
2. Add to `.vscode/settings.json`:
```json
{
  "python.linting.enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "dev.containers.dockerPath": "podman"  // if using podman
}
```

### PyCharm

1. Configure container as Python interpreter
2. Use image: `registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest`
3. Set working directory: `/workspace`
4. For podman: Set Docker executable path to podman in PyCharm settings

## Tips and Tricks

### Shell Aliases

Add to `~/.bashrc` or `~/.zshrc`:

```bash
# Quick access to husky-lint
alias hl='./husky-lint'
alias hll='./husky-lint lint'
alias hlf='./husky-lint lint-fix'
alias hls='./husky-lint shell'

# Direct container commands
alias husky-podman='podman run --rm -v "$(pwd):/workspace" --entrypoint /bin/bash registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest'
alias husky-docker='docker run --rm -v "$(pwd):/workspace" --entrypoint /bin/bash registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest'
```

### Quick Checks

```bash
# Check if your code will pass CI
./husky-lint lint

# Fix everything possible before committing
./husky-lint lint-fix

# Run the same validation as GitLab CI
./husky-lint shell -c "/workspace/scripts/comprehensive-lint.sh"
```

## Next Steps

- [GitLab CI/CD Integration](gitlab-ci-cd.md) - Set up automated validation
- [Configuration Reference](configuration.md) - Customize linting rules
- [Troubleshooting Guide](troubleshooting.md) - Common issues and solutions