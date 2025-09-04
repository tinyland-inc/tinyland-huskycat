# Quick Install Guide

## 🚀 The One-Line Installer

HuskyCats can be installed with a single command that works on all architectures and uses SSH authentication by default for better security:

```bash
# Ensure SSH access to GitLab
ssh -T git@gitlab.com

# Install with SSH authentication (default)
curl -fsSL https://gitlab.com/jsullivan2_bates/pubcontainers/-/raw/main/install.sh | bash

# Or use HTTPS mode if SSH is not available
curl -fsSL https://gitlab.com/jsullivan2_bates/pubcontainers/-/raw/main/install.sh | bash -s -- --no-ssh
```

## How It Works

The installer automatically:
1. **Detects your CPU architecture** (ARM64 or AMD64)
2. **Uses the correct Docker platform flag** to avoid "exec format error"
3. **Pulls the right image** from GitLab Container Registry
4. **Sets up everything** in your project

## Supported Architectures

| Architecture | Systems | Auto-Detected |
|-------------|---------|---------------|
| **AMD64** (x86_64) | Most servers, cloud instances, GitLab CI runners, Intel/AMD desktops | ✅ Yes |
| **ARM64** (aarch64) | Apple Silicon Macs (M1/M2/M3), AWS Graviton, Raspberry Pi 4+ | ✅ Yes |

## Manual Architecture Override

If needed, you can specify the architecture:

```bash
# Force AMD64 (for CI/CD compatibility testing)
docker run --rm --platform linux/amd64 -v "$(pwd):/workspace" \
  registry.gitlab.com/jsullivan2_bates/pubcontainers/husky-lint:latest

# Force ARM64 (for Apple Silicon)
docker run --rm --platform linux/arm64 -v "$(pwd):/workspace" \
  registry.gitlab.com/jsullivan2_bates/pubcontainers/husky-lint:latest
```

## Troubleshooting

### "exec format error"

This error means the Docker image doesn't match your CPU architecture. The one-line installer prevents this by auto-detecting your architecture.

### Check Your Architecture

```bash
# See your system architecture
uname -m

# Check Docker image architecture
docker inspect registry.gitlab.com/jsullivan2_bates/pubcontainers/husky-lint:latest | grep Architecture
```

### GitLab CI Integration

GitLab CI runners typically use AMD64. The image is built for both architectures, so it will work automatically:

```yaml
image: registry.gitlab.com/jsullivan2_bates/pubcontainers/husky-lint:latest

validate:
  script:
    - cd /workspace
    - cp -r ${CI_PROJECT_DIR}/* /workspace/
    - ./scripts/comprehensive-lint.sh
```

## Requirements

- Docker or Podman
- Git repository
- Internet connection (to download the installer)

That's it! No other dependencies needed.