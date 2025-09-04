#!/bin/bash
set -euo pipefail

# HuskyCats MCP Server - Podman Desktop Installation Script
# One-command installation and setup for Podman Desktop integration

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# ASCII Art Header
cat << "EOF"
 _   _           _          ____      _       
| | | |_   _ ___| | ___   _/ ___|__ _| |_ ___ 
| |_| | | | / __| |/ / | | | |   / _` | __/ __|
|  _  | |_| \__ \   <| |_| | |__| (_| | |_\__ \
|_| |_|\__,_|___/_|\_\\__, |\____\__,_|\__|___/
                      |___/  MCP Server v2.0.0
EOF

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Podman Desktop Installation & Setup             ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo ""

# Detect OS
OS="unknown"
ARCH="unknown"

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    ARCH=$(uname -m)
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    ARCH=$(uname -m)
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
    ARCH="amd64"
fi

echo -e "${CYAN}System detected: $OS ($ARCH)${NC}"
echo ""

# Check if running as root (not recommended)
if [ "$EUID" -eq 0 ]; then 
   echo -e "${YELLOW}⚠️  Warning: Running as root is not recommended${NC}"
   read -p "Continue anyway? (y/N): " -n 1 -r
   echo
   if [[ ! $REPLY =~ ^[Yy]$ ]]; then
       exit 1
   fi
fi

# Function to check if command exists
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 is installed"
        return 0
    else
        echo -e "${RED}✗${NC} $1 is not installed"
        return 1
    fi
}

# Function to install Podman
install_podman() {
    echo -e "${BLUE}📦 Installing Podman...${NC}"
    
    case $OS in
        linux)
            if command -v apt-get &> /dev/null; then
                # Debian/Ubuntu
                sudo apt-get update
                sudo apt-get install -y podman
            elif command -v dnf &> /dev/null; then
                # Fedora/RHEL/Rocky
                sudo dnf install -y podman
            elif command -v yum &> /dev/null; then
                # CentOS/RHEL 7
                sudo yum install -y podman
            elif command -v pacman &> /dev/null; then
                # Arch Linux
                sudo pacman -S podman
            else
                echo -e "${RED}Unsupported Linux distribution${NC}"
                echo "Please install Podman manually: https://podman.io/getting-started/installation"
                exit 1
            fi
            ;;
        macos)
            if command -v brew &> /dev/null; then
                brew install podman
                # Initialize and start Podman machine
                podman machine init
                podman machine start
            else
                echo -e "${YELLOW}Homebrew not found. Installing...${NC}"
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                brew install podman
                podman machine init
                podman machine start
            fi
            ;;
        windows)
            echo -e "${YELLOW}Please install Podman Desktop from:${NC}"
            echo "https://podman-desktop.io/downloads"
            echo ""
            echo "After installation, run this script again."
            exit 1
            ;;
    esac
}

# Function to install Podman Desktop
install_podman_desktop() {
    echo -e "${BLUE}🖥️  Installing Podman Desktop...${NC}"
    
    case $OS in
        linux)
            # Download Podman Desktop AppImage or Flatpak
            if command -v flatpak &> /dev/null; then
                flatpak install -y flathub io.podman_desktop.PodmanDesktop
            else
                # Download AppImage
                DOWNLOAD_URL="https://github.com/containers/podman-desktop/releases/latest/download/podman-desktop-linux-x64.AppImage"
                wget -O ~/Applications/PodmanDesktop.AppImage "$DOWNLOAD_URL"
                chmod +x ~/Applications/PodmanDesktop.AppImage
                echo -e "${GREEN}✅ Podman Desktop AppImage installed to ~/Applications/${NC}"
            fi
            ;;
        macos)
            if command -v brew &> /dev/null; then
                brew install --cask podman-desktop
            else
                echo -e "${YELLOW}Downloading Podman Desktop...${NC}"
                DOWNLOAD_URL="https://github.com/containers/podman-desktop/releases/latest/download/podman-desktop-darwin-universal.dmg"
                curl -LO "$DOWNLOAD_URL"
                echo -e "${YELLOW}Please install the downloaded DMG file${NC}"
            fi
            ;;
    esac
}

# Check prerequisites
echo -e "${BLUE}🔍 Checking prerequisites...${NC}"
echo ""

PODMAN_INSTALLED=false
PODMAN_DESKTOP_INSTALLED=false

# Check Podman
if check_command podman; then
    PODMAN_INSTALLED=true
    PODMAN_VERSION=$(podman --version | cut -d' ' -f3)
    echo -e "  Version: $PODMAN_VERSION"
fi

# Check Podman Desktop (harder to detect programmatically)
if [[ "$OS" == "macos" ]]; then
    if [ -d "/Applications/Podman Desktop.app" ]; then
        PODMAN_DESKTOP_INSTALLED=true
        echo -e "${GREEN}✓${NC} Podman Desktop is installed"
    else
        echo -e "${RED}✗${NC} Podman Desktop is not installed"
    fi
elif [[ "$OS" == "linux" ]]; then
    if command -v podman-desktop &> /dev/null || [ -f ~/Applications/PodmanDesktop.AppImage ]; then
        PODMAN_DESKTOP_INSTALLED=true
        echo -e "${GREEN}✓${NC} Podman Desktop is installed"
    else
        echo -e "${RED}✗${NC} Podman Desktop is not installed"
    fi
fi

# Check Git
check_command git
check_command curl
check_command jq || echo -e "${YELLOW}  jq is optional but recommended${NC}"

echo ""

# Install missing components
if [ "$PODMAN_INSTALLED" = false ]; then
    read -p "Podman is not installed. Install now? (Y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        install_podman
    else
        echo -e "${RED}Podman is required. Exiting.${NC}"
        exit 1
    fi
fi

if [ "$PODMAN_DESKTOP_INSTALLED" = false ]; then
    read -p "Podman Desktop is not installed. Install now? (Y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        install_podman_desktop
    fi
fi

# Check Podman machine status (macOS/Windows)
if [[ "$OS" == "macos" ]] || [[ "$OS" == "windows" ]]; then
    echo -e "${BLUE}🔧 Checking Podman machine...${NC}"
    
    MACHINE_STATUS=$(podman machine info --format json 2>/dev/null | jq -r '.Host.MachineState' || echo "unknown")
    
    if [[ "$MACHINE_STATUS" != "Running" ]]; then
        echo -e "${YELLOW}Starting Podman machine...${NC}"
        podman machine start || {
            echo -e "${YELLOW}Creating new Podman machine...${NC}"
            podman machine init --cpus 2 --memory 4096 --disk-size 20
            podman machine start
        }
    else
        echo -e "${GREEN}✅ Podman machine is running${NC}"
    fi
fi

# Clone or update repository
echo ""
echo -e "${BLUE}📥 Setting up HuskyCats MCP Server...${NC}"

INSTALL_DIR="$HOME/huskycats-mcp"

if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Directory exists. Updating...${NC}"
    cd "$INSTALL_DIR"
    git pull origin main
else
    echo -e "${BLUE}Cloning repository...${NC}"
    git clone https://github.com/huskycats/huskycats-bates.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Navigate to MCP server directory
cd mcp-server

# Install dependencies
echo -e "${BLUE}📦 Installing dependencies...${NC}"
if command -v npm &> /dev/null; then
    npm install
else
    echo -e "${YELLOW}npm not found. Installing Node.js...${NC}"
    if [[ "$OS" == "macos" ]]; then
        brew install node
    elif [[ "$OS" == "linux" ]]; then
        curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
        sudo apt-get install -y nodejs
    fi
    npm install
fi

# Build the project
echo -e "${BLUE}🔨 Building project...${NC}"
npm run build

# Deploy with Podman
echo -e "${BLUE}🚀 Deploying with Podman...${NC}"
./deploy-podman.sh

# Generate authentication token
AUTH_TOKEN=$(openssl rand -hex 32 2>/dev/null || echo "dev-token-$(date +%s)")

# Create .mcp.json configuration
echo -e "${BLUE}📝 Creating MCP configuration...${NC}"

MCP_CONFIG="$HOME/.config/claude/mcp.json"
mkdir -p "$(dirname "$MCP_CONFIG")"

cat > "$MCP_CONFIG" << EOF
{
  "mcpServers": {
    "huskycats-mcp": {
      "url": "http://localhost:8080/rpc",
      "type": "http",
      "authentication": {
        "type": "bearer",
        "token": "$AUTH_TOKEN"
      }
    }
  }
}
EOF

echo -e "${GREEN}✅ MCP configuration created${NC}"

# Test the deployment
echo ""
echo -e "${BLUE}🧪 Testing deployment...${NC}"

# Wait for server to be ready
sleep 5

# Test health endpoint
if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${RED}❌ Health check failed${NC}"
fi

# Test MCP RPC endpoint
RESPONSE=$(curl -sf -X POST http://localhost:8080/rpc \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -d '{
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "install-test",
                "version": "1.0.0"
            }
        }
    }' 2>/dev/null)

if echo "$RESPONSE" | jq -e '.result.capabilities' > /dev/null 2>&1; then
    echo -e "${GREEN}✅ MCP protocol working${NC}"
else
    echo -e "${RED}❌ MCP protocol test failed${NC}"
fi

# Create desktop shortcut (Linux)
if [[ "$OS" == "linux" ]]; then
    DESKTOP_FILE="$HOME/.local/share/applications/huskycats-mcp.desktop"
    mkdir -p "$(dirname "$DESKTOP_FILE")"
    
    cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=HuskyCats MCP Server
Comment=Code validation MCP server
Exec=bash -c "cd $INSTALL_DIR/mcp-server && ./deploy-podman.sh"
Icon=$INSTALL_DIR/docs/assets/icon.png
Terminal=true
Type=Application
Categories=Development;
EOF
    
    chmod +x "$DESKTOP_FILE"
    echo -e "${GREEN}✅ Desktop shortcut created${NC}"
fi

# Create launch script
LAUNCH_SCRIPT="$HOME/.local/bin/huskycats-mcp"
mkdir -p "$(dirname "$LAUNCH_SCRIPT")"

cat > "$LAUNCH_SCRIPT" << EOF
#!/bin/bash
cd "$INSTALL_DIR/mcp-server"
./deploy-podman.sh
EOF

chmod +x "$LAUNCH_SCRIPT"

# Add to PATH if not already there
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc 2>/dev/null || true
fi

# Print summary
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   ✅ Installation Complete!                       ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}📍 Installation directory:${NC} $INSTALL_DIR"
echo -e "${CYAN}📄 MCP configuration:${NC} $MCP_CONFIG"
echo -e "${CYAN}🔑 Authentication token:${NC} $AUTH_TOKEN"
echo ""
echo -e "${BLUE}Available endpoints:${NC}"
echo "  • MCP RPC:      http://localhost:8080/rpc"
echo "  • Health:       http://localhost:8080/health"
echo "  • Tools:        http://localhost:8080/tools"
echo "  • Metrics:      http://localhost:8080/metrics"
echo ""
echo -e "${BLUE}Quick commands:${NC}"
echo "  • Start server:    huskycats-mcp"
echo "  • View logs:       podman logs -f huskycats-mcp-server"
echo "  • Stop server:     podman stop huskycats-mcp-server"
echo "  • View in Podman:  podman-desktop"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Open Podman Desktop to view the running container"
echo "2. Configure your IDE with the MCP server URL"
echo "3. Test validation tools with your codebase"
echo ""
echo -e "${CYAN}Documentation:${NC} $INSTALL_DIR/docs/mcp-tool-api.md"
echo ""

# Open Podman Desktop if installed
read -p "Open Podman Desktop now? (Y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
    if [[ "$OS" == "macos" ]]; then
        open "/Applications/Podman Desktop.app" 2>/dev/null || echo "Please open Podman Desktop manually"
    elif [[ "$OS" == "linux" ]]; then
        podman-desktop 2>/dev/null || flatpak run io.podman_desktop.PodmanDesktop 2>/dev/null || echo "Please open Podman Desktop manually"
    fi
fi

echo -e "${GREEN}🎉 Setup complete! Happy coding!${NC}"