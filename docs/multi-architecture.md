# Multi-Architecture Docker Images

HuskyCats Bates supports multi-architecture Docker images to ensure compatibility across different platforms, including Apple Silicon Macs (arm64) and traditional x86_64 systems used by most CI/CD runners.

## 🎯 Why Multi-Architecture?

The "exec format error" occurs when a Docker image built for one CPU architecture (e.g., arm64 on Apple Silicon) is run on a different architecture (e.g., amd64/x86_64 on GitLab runners). Multi-architecture images solve this problem by containing binaries for multiple platforms in a single image tag.

## 🚀 Building Multi-Architecture Images

### Automatic Multi-Arch Build (Recommended)

The `publish.sh` script now automatically builds multi-architecture images when using Docker:

```bash
# Set credentials
export CI_REGISTRY_USER="your-username"
export CI_REGISTRY_PASSWORD="your-token"

# Build and publish multi-arch image
./publish.sh v1.0.0
```

This will build for both `linux/amd64` and `linux/arm64` platforms.

### Manual Multi-Arch Build

Use the dedicated script for more control:

```bash
# Build multi-arch image with custom tag
./scripts/build-multiarch.sh v1.0.0

# The script will:
# 1. Setup Docker buildx
# 2. Build for linux/amd64 and linux/arm64
# 3. Push to the registry
```

### Using Docker Buildx Directly

```bash
# Create and use a buildx builder
docker buildx create --name husky-multiarch --use

# Build and push multi-arch image
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -f ContainerFile \
  -t registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest \
  --push \
  .
```

## 🔍 Verifying Multi-Architecture Images

Check which architectures an image supports:

```bash
# Using docker buildx
docker buildx imagetools inspect registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest

# Using docker manifest
docker manifest inspect registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest
```

## 📋 Prerequisites

### For Building Multi-Arch Images

1. **Docker Desktop** (recommended) or Docker CE with buildx plugin
2. **Enable experimental features** (if using older Docker versions):
   ```json
   # ~/.docker/config.json
   {
     "experimental": "enabled"
   }
   ```

### For Podman Users

Podman supports multi-architecture builds natively:

```bash
podman build --platform linux/amd64,linux/arm64 -f ContainerFile -t husky-lint:latest .
```

## 🚨 Troubleshooting

### "exec format error" in GitLab CI

This means the image was built for a different architecture. Solution:
1. Rebuild the image using multi-architecture support
2. Push the new image to the registry
3. Re-run the GitLab pipeline

### Docker buildx not found

Install or update Docker Desktop, or manually install buildx:
```bash
# Manual installation
docker buildx version || \
  wget https://github.com/docker/buildx/releases/download/v0.11.2/buildx-v0.11.2.linux-amd64 -O ~/.docker/cli-plugins/docker-buildx && \
  chmod +x ~/.docker/cli-plugins/docker-buildx
```

### Build takes too long

Multi-architecture builds can be slower because they build for multiple platforms. To speed up:
- Use a more powerful machine
- Build only for required architectures
- Use Docker Hub's automated builds

## 🏗️ Architecture-Specific Considerations

The ContainerFile has been updated to handle architecture-specific downloads:

1. **hadolint**: Downloads the correct binary for arm64 or x86_64
2. **kubectl**: Downloads the correct binary for the build architecture
3. **helm**: The installer script automatically detects architecture

## 📚 References

- [Docker Buildx Documentation](https://docs.docker.com/buildx/working-with-buildx/)
- [Docker Multi-platform Images](https://docs.docker.com/build/building/multi-platform/)
- [Podman Multi-arch Builds](https://docs.podman.io/en/latest/markdown/podman-build.1.html#platform-os-arch-variant)