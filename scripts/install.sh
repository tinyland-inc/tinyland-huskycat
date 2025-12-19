#!/bin/bash
# HuskyCat One-Line Installer
# Usage: curl -fsSL https://tinyland.gitlab.io/ai/huskycat/install.sh | bash

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Platform detection
PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
case "$ARCH" in
    x86_64) ARCH="amd64" ;;
    aarch64|arm64) ARCH="arm64" ;;
    *) log_error "Unsupported architecture: $ARCH" ;;
esac

# Configuration
GITLAB_PROJECT="tinyland/ai/huskycat"
VERSION="${HUSKYCAT_VERSION:-latest}"
TMP_DIR=$(mktemp -d)
trap "rm -rf $TMP_DIR" EXIT

main() {
    echo -e "${BLUE}HuskyCat Installer${NC}"
    echo "=================="
    log_info "Platform: ${PLATFORM}-${ARCH}"

    # Download binary
    log_info "Downloading HuskyCat binary..."

    if [ "$VERSION" = "latest" ]; then
        BINARY_URL="https://gitlab.com/${GITLAB_PROJECT}/-/releases/permalink/latest/downloads/huskycat-${PLATFORM}-${ARCH}"
    else
        BINARY_URL="https://gitlab.com/${GITLAB_PROJECT}/-/releases/${VERSION}/downloads/huskycat-${PLATFORM}-${ARCH}"
    fi

    BINARY_PATH="${TMP_DIR}/huskycat"

    if command -v curl &> /dev/null; then
        curl -fsSL "$BINARY_URL" -o "$BINARY_PATH" || {
            # Fallback to artifact URL if release doesn't exist
            log_info "Release not found, trying artifacts from main branch..."
            case "${PLATFORM}-${ARCH}" in
                linux-amd64) JOB="build:binary:linux-amd64" ;;
                linux-arm64) JOB="build:binary:linux-arm64" ;;
                darwin-arm64) JOB="build:binary:darwin-arm64" ;;
                darwin-amd64)
                    log_error "macOS Intel (darwin-amd64) binary not available. Intel Mac users: Use Rosetta 2 to run ARM64 binary, or use container execution with: podman run -v \$(pwd):/workspace tinyland/huskycat validate"
                    ;;
                *) log_error "Unsupported platform: ${PLATFORM}-${ARCH}" ;;
            esac
            curl -fsSL "https://gitlab.com/${GITLAB_PROJECT}/-/jobs/artifacts/main/raw/dist/bin/huskycat-${PLATFORM}-${ARCH}?job=${JOB}" -o "$BINARY_PATH" || log_error "Failed to download binary for ${PLATFORM}-${ARCH}"
        }
    elif command -v wget &> /dev/null; then
        wget -q "$BINARY_URL" -O "$BINARY_PATH" || log_error "Failed to download binary"
    else
        log_error "Neither curl nor wget found"
    fi

    chmod +x "$BINARY_PATH"
    log_success "Binary downloaded"

    # Run self-installer
    log_info "Running self-installer..."
    "$BINARY_PATH" install

    echo ""
    echo "=================="
    log_success "Installation complete!"
    echo ""
    echo "Usage:"
    echo "  huskycat validate           # Validate current directory"
    echo "  huskycat validate --staged  # Validate staged files"
    echo "  huskycat setup-hooks        # Setup git hooks"
    echo "  huskycat mcp-server         # Start MCP server for Claude"
    echo ""
    echo "Claude Code integration:"
    echo '  claude mcp add huskycat -- huskycat mcp-server --stdio'
}

main "$@"
