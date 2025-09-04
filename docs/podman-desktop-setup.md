# Podman Desktop Setup Guide for HuskyCat

## Installation

### macOS
```bash
# Using Homebrew
brew install --cask podman-desktop

# Or download from official site
open https://podman-desktop.io/downloads
```

### Linux
```bash
# Flatpak (recommended)
flatpak install flathub io.podman_desktop.PodmanDesktop

# Or download AppImage
wget https://github.com/containers/podman-desktop/releases/latest/download/podman-desktop-x86_64.AppImage
chmod +x podman-desktop-*.AppImage
./podman-desktop-*.AppImage
```

### Windows
Download installer from: https://podman-desktop.io/downloads

## Post-Installation Setup

1. **Launch Podman Desktop**
2. **Initialize Podman Machine** (macOS/Windows only):
   - Click "Initialize Podman"
   - Accept default settings
   - Wait for machine to start

3. **Verify Installation**:
   ```bash
   podman --version
   podman machine list  # macOS/Windows
   podman ps
   ```

## Running HuskyCat MCP Server

### Using Podman Desktop GUI

1. **Import Container**:
   - Go to Images tab
   - Click "Pull an image"
   - Enter: `localhost/huskycat-mcp:latest`

2. **Create Container**:
   - Click on the image
   - Click "Run"
   - Configure:
     - Name: `huskycats-mcp`
     - Port mapping: `8080:8080`
     - Environment variables:
       - `NODE_ENV=production`
       - `BEARER_TOKEN=dev-token-for-testing`
     - Volume: Mount your workspace to `/workspace`

3. **Start Container**:
   - Go to Containers tab
   - Click play button on `huskycats-mcp`

### Using Podman CLI

```bash
# Build the image
cd mcp-server
podman build -t localhost/huskycat-mcp:latest .

# Run with podman-compose
podman-compose up -d

# Or run directly
podman run -d \
  --name huskycats-mcp \
  -p 8080:8080 \
  -e NODE_ENV=production \
  -e BEARER_TOKEN=dev-token-for-testing \
  -v $(pwd):/workspace:ro \
  localhost/huskycat-mcp:latest
```

## Verifying MCP Server

```bash
# Check health endpoint
curl http://localhost:8080/health

# List available tools
curl -X POST http://localhost:8080/rpc \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-token-for-testing" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1}'
```

## Troubleshooting

### Podman Machine Issues (macOS/Windows)
```bash
# Reset machine
podman machine rm
podman machine init
podman machine start
```

### Permission Issues
```bash
# Linux: Add user to podman group
sudo usermod -aG podman $USER

# macOS: Ensure machine has enough resources
podman machine set --cpus 4 --memory 4096
```

### Network Issues
```bash
# Check if port is already in use
lsof -i :8080  # macOS/Linux
netstat -an | findstr 8080  # Windows

# Use alternative port
podman run -p 8081:8080 ...
```

## Integration with Development Tools

### VS Code Integration
1. Install "Dev Containers" extension
2. Add to `.devcontainer/devcontainer.json`:
   ```json
   {
     "name": "HuskyCat Dev",
     "image": "localhost/huskycat-mcp:latest",
     "forwardPorts": [8080],
     "customizations": {
       "vscode": {
         "extensions": ["ms-python.python"]
       }
     }
   }
   ```

### JetBrains IDEs
1. Go to Settings → Build, Execution, Deployment → Docker
2. Add new Docker configuration
3. Set Connection type to "Podman"
4. Configure path to podman executable

## Resources

- Podman Desktop Documentation: https://podman-desktop.io/docs
- Podman CLI Reference: https://docs.podman.io/en/latest/
- HuskyCat Documentation: https://huskycats.gitlab.io/