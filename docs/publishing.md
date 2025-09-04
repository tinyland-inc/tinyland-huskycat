# Publishing HuskyCats Bates to GitLab Container Registry

This guide explains how to build and publish the HuskyCats Bates container image to the GitLab Container Registry.

## 🚨 Important Note

The HuskyCats Bates project relies on manual publishing. The container image must be built and published locally using podman or docker.

## 📋 Prerequisites

- Podman or Docker installed locally
- GitLab account with push access to the container registry
- GitLab personal access token with `write_registry` scope

## 🔑 Authentication

### Create a Personal Access Token

1. Go to GitLab → Settings → Access Tokens
2. Create a token with `write_registry` scope
3. Save the token securely

### Set Environment Variables

```bash
export CI_REGISTRY_USER="your-gitlab-username"
export CI_REGISTRY_PASSWORD="your-personal-access-token"
```

## 🚀 Publishing Methods

### Method 1: Using publish.sh (Recommended)

The `publish.sh` script handles the entire build and publish process. It automatically detects whether you have podman or docker installed:

```bash
# Publish as latest
./publish.sh

# Publish with specific tag
./publish.sh v1.0.0

# The script will:
# 1. Auto-detect podman or docker
# 2. Build using ContainerFile
# 3. Tag as both specified version and latest
# 4. Push to GitLab registry
```

### Method 2: Using build.sh

The `build.sh` script offers more control and also auto-detects podman/docker:

```bash
# Build and push in one command
./build.sh \
  -r registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates \
  -t v1.0.0 \
  -p

# Build locally first, then push
./build.sh -t v1.0.0
# If using podman:
podman tag husky-lint:v1.0.0 registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:v1.0.0
podman push registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:v1.0.0
# If using docker, replace 'podman' with 'docker'
```

### Method 3: Manual Container Commands

For complete control using podman:

```bash
# 1. Login to GitLab registry
echo "$CI_REGISTRY_PASSWORD" | podman login -u "$CI_REGISTRY_USER" --password-stdin registry.gitlab.com

# 2. Build the image from ContainerFile
podman build -f ContainerFile -t registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest .

# 3. Tag for multiple versions
podman tag registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest \
           registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:v1.0.0

# 4. Push to registry
podman push registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest
podman push registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:v1.0.0

# 5. Logout
podman logout registry.gitlab.com
```

For docker, simply replace `podman` with `docker` in the commands above.

## 📦 Version Tagging Strategy

### Semantic Versioning

Use semantic versioning for releases:
- `v1.0.0` - Major release
- `v1.1.0` - Minor release (new features)
- `v1.1.1` - Patch release (bug fixes)

### Special Tags

- `latest` - Always points to the most recent stable version
- `dev` - Development/unstable version
- `main` - Tracks the main branch

### Example Publishing Workflow

```bash
# For a new release
./publish.sh v1.2.0

# Update latest to point to new release
./publish.sh latest

# For development builds
./publish.sh dev
```

## 🔍 Verifying Publication

After publishing, verify the image is available:

```bash
# List available tags
curl -s -H "Authorization: Bearer $CI_REGISTRY_PASSWORD" \
  https://registry.gitlab.com/v2/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint/tags/list

# Pull and test the image with podman
podman pull registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest
podman run --rm registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest --version

# Or with docker
docker pull registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest
docker run --rm registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest --version
```

## 🛠️ Troubleshooting

### Authentication Errors

```
unauthorized: authentication required
```

**Solution**: Ensure your personal access token has `write_registry` scope and is not expired.

### Push Denied

```
denied: requested access to the resource is denied
```

**Solution**: Verify you have Developer or higher role in the GitLab project.

### Image Not Found

```
manifest unknown: manifest unknown
```

**Solution**: Check the image name and tag are correct. The full path should be:
```
registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:TAG
```

## 🔄 CI/CD Status

The HuskyCats Bates project uses manual publishing exclusively. The GitLab CI/CD pipeline:

1. **Uses the published image** for all validation and testing
2. **Does not build images** in CI/CD
3. **Includes a manual job** that provides publishing instructions
4. **Validates** the project using the latest published image

## 📝 Best Practices

1. **Always test locally** before publishing
   ```bash
   # Build with podman
   podman build -f ContainerFile -t husky-lint:test .
   podman run --rm -v "$(pwd):/workspace" husky-lint:test
   
   # Or with docker
   docker build -f ContainerFile -t husky-lint:test .
   docker run --rm -v "$(pwd):/workspace" husky-lint:test
   ```
