#!/usr/bin/env bash
# HuskyCat Universal Code Validation Platform
# One-liner installation script for all platforms
# Usage: curl -sSL https://huskycat.pages.io/install.sh | bash

set -euo pipefail

# Configuration
GITLAB_REPO="jsullivan2_bates/huskycat"
GITLAB_PAGES_URL="https://jsullivan2_bates.gitlab.io/huskycat"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
TEMP_DIR=$(mktemp -d)
VERSION="${VERSION:-latest}"

# Platform detection
ARCH=$(uname -m)
OS=$(uname -s)

case $OS in
    Linux*)     PLATFORM="linux";;
    Darwin*)    PLATFORM="darwin";;
    CYGWIN*|MINGW*|MSYS*) PLATFORM="windows";;
    *)          echo "Error: Unsupported operating system: $OS"; exit 1;;
esac

case $ARCH in
    x86_64|amd64)   ARCH_SUFFIX="x64";;
    aarch64|arm64)  ARCH_SUFFIX="arm64";;
    armv7l)         ARCH_SUFFIX="armv7";;
    *)              echo "Error: Unsupported architecture: $ARCH"; exit 1;;
esac

# Colors and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check for required commands
    for cmd in curl grep chmod mkdir; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            log_error "Required command '$cmd' not found"
            exit 1
        fi
    done
    
    # Check Python for MCP server functionality
    if command -v python3 >/dev/null 2>&1; then
        log_success "Python3 found: $(python3 --version)"
    elif command -v python >/dev/null 2>&1; then
        log_success "Python found: $(python --version)"
    else
        log_warning "Python not found. MCP server functionality will not be available."
    fi
}

# Install UV package manager
install_uv() {
    if command -v uv >/dev/null 2>&1; then
        log_info "UV already installed: $(uv --version)"
        return 0
    fi
    
    log_info "Installing UV package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Add to PATH if not already there
    if [[ ":$PATH:" != *":$HOME/.cargo/bin:"* ]]; then
        export PATH="$HOME/.cargo/bin:$PATH"
        echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> "$HOME/.bashrc" 2>/dev/null || true
        echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> "$HOME/.zshrc" 2>/dev/null || true
    fi
    
    source "$HOME/.cargo/env" 2>/dev/null || true
    log_success "UV installed successfully"
}

# Download and install binary
install_binary() {
    log_info "Installing HuskyCat binary..."
    
    # Create install directory
    mkdir -p "$INSTALL_DIR"
    
    # Determine download URL
    if [ "$VERSION" = "latest" ]; then
        DOWNLOAD_URL="https://gitlab.com/${GITLAB_REPO}/-/jobs/artifacts/main/raw/dist/bin/huskycat-${PLATFORM}-${ARCH_SUFFIX}?job=package:binary"
    else
        DOWNLOAD_URL="https://gitlab.com/${GITLAB_REPO}/-/jobs/artifacts/v${VERSION}/raw/dist/bin/huskycat-${PLATFORM}-${ARCH_SUFFIX}?job=package:binary"
    fi
    
    # Download binary
    log_info "Downloading from: $DOWNLOAD_URL"
    if curl -fsSL "$DOWNLOAD_URL" -o "$TEMP_DIR/huskycat"; then
        chmod +x "$TEMP_DIR/huskycat"
        mv "$TEMP_DIR/huskycat" "$INSTALL_DIR/huskycat"
        log_success "Binary installed to: $INSTALL_DIR/huskycat"
        return 0
    else
        log_warning "Binary download failed, falling back to Python installation..."
        return 1
    fi
}

# Install Python package using UV
install_python_package() {
    log_info "Installing HuskyCat Python package..."
    
    if ! command -v uv >/dev/null 2>&1; then
        install_uv
    fi
    
    # Install from GitLab registry or PyPI
    if uv tool install --from "git+https://gitlab.com/${GITLAB_REPO}.git" huskycat; then
        log_success "Python package installed via UV"
        return 0
    else
        log_error "Failed to install Python package"
        return 1
    fi
}

# Add to PATH
add_to_path() {
    # Check if already in PATH
    if command -v huskycat >/dev/null 2>&1; then
        log_success "HuskyCat is already in PATH"
        return 0
    fi
    
    # Add install directory to PATH in shell profiles
    for profile in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
        if [ -f "$profile" ]; then
            if ! grep -q "$INSTALL_DIR" "$profile"; then
                echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$profile"
                log_info "Added $INSTALL_DIR to PATH in $profile"
            fi
        fi
    done
    
    # Add to current session
    export PATH="$INSTALL_DIR:$PATH"
    log_success "HuskyCat added to PATH"
}

# Verify installation
verify_installation() {
    log_info "Verifying installation..."
    
    if command -v huskycat >/dev/null 2>&1; then
        local version_output=$(huskycat --version 2>/dev/null || echo "HuskyCat installed")
        log_success "Installation verified: $version_output"
        
        # Test MCP server capability
        if huskycat mcp --help >/dev/null 2>&1; then
            log_success "MCP server functionality available"
        else
            log_warning "MCP server functionality may be limited"
        fi
        return 0
    else
        log_error "Installation verification failed"
        return 1
    fi
}

# Setup git hooks (optional)
setup_git_hooks() {
    if [ -d ".git" ]; then
        read -p "Setup HuskyCat git hooks in current repository? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            huskycat init
            log_success "Git hooks configured"
        fi
    fi
}

# Setup MCP for Claude Code (optional)
setup_mcp() {
    if command -v claude >/dev/null 2>&1; then
        read -p "Setup HuskyCat MCP server for Claude Code? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            claude mcp add huskycat "huskycat mcp --stdio"
            log_success "MCP server configured for Claude Code"
        fi
    else
        log_info "Claude Code not found. To setup MCP later, run:"
        log_info "  claude mcp add huskycat \"huskycat mcp --stdio\""
    fi
}

# Main installation process
main() {
    echo -e "${GREEN}HuskyCat Universal Code Validation Platform${NC}"
    echo -e "${GREEN}===========================================${NC}"
    echo
    
    check_prerequisites
    
    # Try binary installation first, fallback to Python
    if ! install_binary; then
        if ! install_python_package; then
            log_error "Both binary and Python package installation failed"
            exit 1
        fi
    fi
    
    add_to_path
    
    if ! verify_installation; then
        exit 1
    fi
    
    echo
    echo -e "${GREEN}🎉 Installation complete!${NC}"
    echo
    echo "Next steps:"
    echo "1. Restart your terminal or run: source ~/.bashrc"
    echo "2. Test the installation: huskycat --version"
    echo "3. Initialize in a git repository: huskycat init"
    echo "4. Setup MCP for Claude Code: claude mcp add huskycat \"huskycat mcp --stdio\""
    echo
    echo "Documentation: https://huskycat.pages.io"
    echo "Support: https://gitlab.com/${GITLAB_REPO}/-/issues"
    
    # Optional interactive setup
    setup_git_hooks
    setup_mcp
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "HuskyCat Installation Script"
        echo
        echo "Usage: $0 [OPTIONS]"
        echo
        echo "Options:"
        echo "  --help, -h        Show this help message"
        echo "  --version, -v     Show version information"
        echo
        echo "Environment variables:"
        echo "  VERSION              Version to install (default: latest)"
        echo "  INSTALL_DIR          Installation directory (default: $HOME/.local/bin)"
        exit 0
        ;;
    --version|-v)
        echo "HuskyCat Installer v2.0.0"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac