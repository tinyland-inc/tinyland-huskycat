# Container Migration Analysis: Docker to ContainerFile/Podman

## Current Container Landscape

### Existing Docker Files
1. **`mcp-server/Dockerfile`** (57 lines)
   - **Base**: `node:20-alpine`
   - **Purpose**: Main MCP server with production optimization
   - **Features**: Multi-stage build, non-root user, health check
   - **Size**: ~200MB estimated

2. **`mcp-server/Dockerfile.rocky10`** (254 lines)
   - **Base**: `rockylinux:9` 
   - **Purpose**: Security-hardened enterprise container
   - **Features**: fail2ban, firewalld, SSH hardening, systemd
   - **Size**: ~1.2GB estimated
   - **Complexity**: Over-engineered for validation tools

3. **`ContainerFile.huskycat`** 
   - **Purpose**: Binary distribution container
   - **Focus**: UPX-compressed executable distribution

4. **`mcp-server/ContainerFile`**
   - **Purpose**: Podman-specific build (existing)

5. **`mcp-server/ContainerFile.rocky`**
   - **Purpose**: Rocky Linux variant for Podman

## Migration Strategy: Docker → ContainerFile/Podman

### Phase 1: ContainerFile Standardization

#### 1.1 Single Unified ContainerFile
**Target**: `ContainerFile.huskycat-unified`
```dockerfile
# Unified HuskyCats Validation Container
FROM alpine:3.19

# Install ALL validation tools in single layer
RUN apk add --no-cache \
    # Core runtime
    nodejs npm python3 py3-pip bash \
    # Python tools
    py3-black py3-flake8 py3-mypy bandit \
    # JavaScript tools  
    && npm install -g eslint prettier \
    # System tools
    && apk add --no-cache shellcheck hadolint yamllint \
    # Cleanup
    && rm -rf /var/cache/apk/*

# Copy validation scripts and MCP server
COPY dist/ /opt/huskycat/
COPY scripts/ /opt/huskycat/scripts/

# Single entrypoint for all functionality
ENTRYPOINT ["/opt/huskycat/huskycat"]
```

#### 1.2 Migration Mapping
| Current File | New ContainerFile | Action |
|--------------|------------------|---------|
| `mcp-server/Dockerfile` | `ContainerFile.huskycat` | MERGE + SIMPLIFY |
| `mcp-server/Dockerfile.rocky10` | `ContainerFile.huskycat` | ELIMINATE (over-engineered) |
| `ContainerFile.huskycat` | `ContainerFile.huskycat` | ENHANCE |
| `mcp-server/ContainerFile` | `ContainerFile.huskycat` | MERGE |
| `mcp-server/ContainerFile.rocky` | `ContainerFile.huskycat` | ELIMINATE |

### Phase 2: Podman-Compose Integration

#### 2.1 Current docker-compose.yml Analysis
**Status**: No docker-compose.yml found in repository
**Recommendation**: Create podman-compose.yml for development

#### 2.2 New podman-compose.yml Structure
```yaml
version: '3.8'
services:
  huskycat:
    build:
      context: .
      dockerfile: ContainerFile.huskycat
    container_name: huskycat-validator
    volumes:
      - .:/workspace:Z  # SELinux label for Podman
      - /var/run/podman/podman.sock:/var/run/podman/podman.sock:ro
    working_dir: /workspace
    environment:
      - NODE_ENV=production
      - MCP_MODE=stdio
    command: ["mcp-server", "--stdio"]
```

### Phase 3: Build System Migration

#### 3.1 Current Build Commands
```bash
# Current Docker builds
npm run docker:build  # podman build -t huskycats-mcp .
npm run docker:run    # podman run -p 3000:3000 huskycats-mcp
```

#### 3.2 New Podman Build Commands
```bash
# New Podman builds
npm run container:build    # podman build -f ContainerFile.huskycat -t huskycat:latest .
npm run container:run      # podman run --rm -v $(pwd):/workspace:Z huskycat:latest
npm run container:dev      # podman-compose up --build
npm run container:stdio    # podman run --rm -i huskycat:latest --stdio
```

## Simplified Architecture Design

### Core Container Features (Unified)
1. **Base**: Alpine Linux 3.19 (minimal, secure, fast)
2. **Size Target**: <150MB (vs current 200MB-1.2GB range)
3. **All Tools Included**: No runtime tool installation
4. **Single Binary**: `/opt/huskycat/huskycat` handles everything
5. **MCP Integration**: Built-in stdio transport

### Removed Complexity
- ❌ Multi-stage builds (unnecessary for tools)
- ❌ Security hardening (fail2ban, firewalld, SSH)
- ❌ SystemD integration (not needed for containers)
- ❌ Multiple base images (Rocky Linux, Alpine variants)
- ❌ Authentication layers (stdio is direct)
- ❌ Syncthing networking (being removed)

### Container Tool Matrix
| Tool Category | Current Status | New Container |
|---------------|----------------|---------------|
| **Python** | Runtime install | Pre-installed |
| black | ✓ | ✓ |
| flake8 | ✓ | ✓ |
| mypy | ✓ | ✓ |
| bandit | ✓ | ✓ |
| **JavaScript** | Runtime install | Pre-installed |
| eslint | ✓ | ✓ |
| prettier | ✓ | ✓ |
| **System** | Runtime install | Pre-installed |
| shellcheck | ✓ | ✓ |
| hadolint | ✓ | ✓ |
| yamllint | ✓ | ✓ |
| **GitLab CI** | Python script | Built-in |

## GitLab Container Registry Integration

### Current Registry Structure
```
registry.gitlab.com/jsullivan2_bates/pubcontainers/
├── husky-lint:latest        # Current main image
├── husky-lint:test          # Test builds  
├── husky-lint:local         # Local builds
└── huskycats:local          # Local variant
```

### Proposed Registry Structure
```
registry.gitlab.com/jsullivan2_bates/pubcontainers/
├── huskycat:latest          # Unified image
├── huskycat:v2.0.0          # Version tags
├── huskycat:alpine          # Explicit base (alias to latest)
└── huskycat:dev             # Development builds
```

### Registry Migration Strategy
1. **Build New Image**: `huskycat:v2.0.0` with unified ContainerFile
2. **Parallel Deployment**: Keep old images during transition
3. **Update References**: Change all scripts to use new image name
4. **Deprecation**: Mark old images as deprecated
5. **Cleanup**: Remove old images after 30 days

## Pre-commit Hook Simplification

### Current Hook Complexity (104 lines)
```bash
# Complex container detection logic (26 lines)
for image in "${LOCAL_IMAGES[@]}"; do
    if $CONTAINER_TOOL image inspect "$image" &>/dev/null; then
        CONTAINER_IMAGE="$image"
        break
    fi
done
```

### Simplified Hook (15 lines)
```bash
#!/usr/bin/env sh
# Simple unified huskycat hook

CONTAINER_IMAGE="registry.gitlab.com/jsullivan2_bates/pubcontainers/huskycat:latest"

# Ensure container is available
if ! podman image exists "$CONTAINER_IMAGE"; then
    podman pull "$CONTAINER_IMAGE"
fi

# Run validation
podman run --rm -v "$(pwd):/workspace:Z" "$CONTAINER_IMAGE" validate --staged
```

## Migration Benefits

### Development Experience
- **Single Command**: `podman run huskycat validate`
- **No Container Selection**: Always use the same image
- **Faster Startup**: No HTTP server, direct stdio
- **Offline Capable**: All tools pre-installed

### CI/CD Simplification
- **Faster Builds**: Single-stage, Alpine-based
- **Smaller Images**: <150MB vs 200MB-1.2GB
- **Predictable Behavior**: No runtime tool installation
- **Reduced Complexity**: 5 container files → 1 container file

### Maintenance Reduction
- **Single Dockerfile**: 1 ContainerFile vs 5 Docker files
- **No Multi-platform**: Focus on amd64 initially
- **Simplified CI**: Fewer build matrix combinations
- **Easier Updates**: Single image to maintain

## Implementation Roadmap

### Week 1: Container Unification
- [ ] Create `ContainerFile.huskycat` with all tools
- [ ] Test tool availability and functionality
- [ ] Build and push to registry as `huskycat:dev`

### Week 2: Script Migration  
- [ ] Update pre-commit hook to use new image
- [ ] Modify build scripts for ContainerFile
- [ ] Create podman-compose.yml

### Week 3: CI/CD Update
- [ ] Update `.gitlab-ci.yml` for new container
- [ ] Test build and deployment pipeline
- [ ] Update documentation

### Week 4: Rollout and Cleanup
- [ ] Deploy `huskycat:latest` to registry
- [ ] Update all references to new image
- [ ] Remove old Dockerfiles
- [ ] Clean up unused registry images

This migration eliminates the complexity of multiple container files while ensuring all validation tools are available by default - achieving the "everything works out of the box" goal.