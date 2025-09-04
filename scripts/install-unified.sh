#!/bin/bash
# HuskyCat Universal Installer
# One-line installation: curl -fsSL https://huskycat.io/install | bash

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
GITLAB_REGISTRY="registry.gitlab.com/tinyland/ai/huskycat"
INSTALL_DIR="$HOME/.huskycat"
BIN_DIR="$HOME/.local/bin"
VERSION="${HUSKYCAT_VERSION:-latest}"

# Platform detection
PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
    ARCH="amd64"
elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    ARCH="arm64"
fi

# Container runtime detection
detect_runtime() {
    if command -v podman &> /dev/null; then
        echo "podman"
    elif command -v docker &> /dev/null; then
        echo "docker"
    else
        echo ""
    fi
}

# Log functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Main installation
main() {
    echo -e "${BLUE}HuskyCat Universal Installer${NC}"
    echo "================================"
    
    # Check container runtime
    RUNTIME=$(detect_runtime)
    if [ -z "$RUNTIME" ]; then
        log_error "No container runtime found. Please install podman or docker."
    fi
    log_success "Container runtime: $RUNTIME"
    
    # Create directories
    log_info "Creating directories..."
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$BIN_DIR"
    
    # Download binary
    log_info "Downloading HuskyCat binary..."
    BINARY_URL="https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-${PLATFORM}-${ARCH}"
    
    if command -v curl &> /dev/null; then
        curl -fsSL "$BINARY_URL" -o "$BIN_DIR/huskycat" || {
            log_error "Failed to download binary"
        }
    elif command -v wget &> /dev/null; then
        wget -q "$BINARY_URL" -O "$BIN_DIR/huskycat" || {
            log_error "Failed to download binary"
        }
    else
        log_error "Neither curl nor wget found"
    fi
    
    chmod +x "$BIN_DIR/huskycat"
    log_success "Binary installed to $BIN_DIR/huskycat"
    
    # Pull container image
    log_info "Pulling HuskyCat container..."
    $RUNTIME pull "$GITLAB_REGISTRY:$VERSION" || {
        log_error "Failed to pull container image"
    }
    log_success "Container image pulled"
    
    # Create configuration
    log_info "Creating configuration..."
    cat > "$INSTALL_DIR/config.yaml" << EOF
version: 2.0.0
runtime: $RUNTIME
container:
  image: $GITLAB_REGISTRY:$VERSION
  auto_update: true
tools:
  python:
    - black
    - flake8
    - mypy
    - ruff
  javascript:
    - eslint
    - prettier
  yaml:
    - yamllint
  container:
    - hadolint
  shell:
    - shellcheck
EOF
    log_success "Configuration created"
    
    # Setup git hooks if in repository
    if [ -d .git ]; then
        log_info "Setting up git hooks..."
        "$BIN_DIR/huskycat" init
        log_success "Git hooks installed"
    fi
    
    # Check PATH
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        echo ""
        echo -e "${YELLOW}[WARNING]${NC} $BIN_DIR is not in your PATH"
        echo "Add the following to your shell configuration:"
        echo ""
        echo "  export PATH=\"\$PATH:$BIN_DIR\""
        echo ""
    fi
    
    # MCP setup instructions
    echo ""
    echo "================================"
    echo -e "${GREEN}Installation Complete!${NC}"
    echo "================================"
    echo ""
    echo "To use HuskyCat:"
    echo "  huskycat validate           # Validate current directory"
    echo "  huskycat validate --staged  # Validate staged files"
    echo "  huskycat init              # Initialize in repository"
    echo ""
    echo "To use with Claude Code:"
    echo "  claude mcp add huskycat \"$BIN_DIR/huskycat mcp --stdio\""
    echo ""
    
    # Test installation
    if "$BIN_DIR/huskycat" info &> /dev/null; then
        log_success "Installation verified"
    else
        log_error "Installation verification failed"
    fi
}

# Run main
main "$@"