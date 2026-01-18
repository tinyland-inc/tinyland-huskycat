#!/bin/bash
# HuskyCat One-Line Installer v2
# Usage: curl -fsSL https://tinyland.gitlab.io/ai/huskycat/install.sh | bash
# Options: HUSKYCAT_WITH_CLAUDE=1 HUSKYCAT_SCOPE=user

set -euo pipefail

# Configuration
GITLAB_PROJECT="tinyland/ai/huskycat"
VERSION="${HUSKYCAT_VERSION:-latest}"
WITH_CLAUDE="${HUSKYCAT_WITH_CLAUDE:-0}"
SCOPE="${HUSKYCAT_SCOPE:-user}"
TMP_DIR=$(mktemp -d)
trap "rm -rf $TMP_DIR" EXIT

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Platform detection
detect_platform() {
    PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64) ARCH="amd64" ;;
        aarch64|arm64) ARCH="arm64" ;;
        *) log_error "Unsupported architecture: $ARCH" ;;
    esac
}

# Verify checksum if available
verify_checksum() {
    local binary_path="$1"
    local checksum_url="$2"

    # Try to download checksum
    if curl -fsSL "$checksum_url" -o "${TMP_DIR}/checksum.txt" 2>/dev/null; then
        log_info "Verifying checksum..."
        local expected_checksum
        expected_checksum=$(cat "${TMP_DIR}/checksum.txt")

        if command -v sha256sum &> /dev/null; then
            local actual_checksum
            actual_checksum=$(sha256sum "$binary_path" | awk '{print $1}')
            if [ "$expected_checksum" = "$actual_checksum" ]; then
                log_success "Checksum verified"
                return 0
            else
                log_error "Checksum verification failed! Expected: $expected_checksum, Got: $actual_checksum"
            fi
        elif command -v shasum &> /dev/null; then
            local actual_checksum
            actual_checksum=$(shasum -a 256 "$binary_path" | awk '{print $1}')
            if [ "$expected_checksum" = "$actual_checksum" ]; then
                log_success "Checksum verified"
                return 0
            else
                log_error "Checksum verification failed! Expected: $expected_checksum, Got: $actual_checksum"
            fi
        else
            log_warn "No sha256sum or shasum available - skipping verification"
        fi
    else
        log_warn "Checksum not available - skipping verification"
    fi
    return 0
}

# Download binary with checksum verification
download_binary() {
    log_info "Downloading HuskyCat ${VERSION} for ${PLATFORM}-${ARCH}..."

    if [ "$VERSION" = "latest" ]; then
        BINARY_URL="https://gitlab.com/${GITLAB_PROJECT}/-/releases/permalink/latest/downloads/huskycat-${PLATFORM}-${ARCH}"
    else
        BINARY_URL="https://gitlab.com/${GITLAB_PROJECT}/-/releases/${VERSION}/downloads/huskycat-${PLATFORM}-${ARCH}"
    fi

    BINARY_PATH="${TMP_DIR}/huskycat"

    # Download binary
    if command -v curl &> /dev/null; then
        curl -fsSL "$BINARY_URL" -o "$BINARY_PATH" || {
            log_info "Release not found, trying artifacts from main branch..."
            case "${PLATFORM}-${ARCH}" in
                linux-amd64) JOB="build:binary:linux-amd64" ;;
                linux-arm64) JOB="build:binary:linux-arm64" ;;
                darwin-arm64) JOB="build:binary:darwin-arm64" ;;
                darwin-amd64)
                    log_error "macOS Intel (darwin-amd64) binary not available. Intel Mac users: Use Rosetta 2 to run ARM64 binary, or use container execution."
                    ;;
                *) log_error "Unsupported platform: ${PLATFORM}-${ARCH}" ;;
            esac
            curl -fsSL "https://gitlab.com/${GITLAB_PROJECT}/-/jobs/artifacts/main/raw/dist/bin/huskycat-${PLATFORM}-${ARCH}?job=${JOB}" -o "$BINARY_PATH" || log_error "Failed to download binary"
        }
    elif command -v wget &> /dev/null; then
        wget -q "$BINARY_URL" -O "$BINARY_PATH" || log_error "Failed to download binary"
    else
        log_error "Neither curl nor wget found"
    fi

    # Verify checksum (if available)
    CHECKSUM_URL="${BINARY_URL}.sha256"
    verify_checksum "$BINARY_PATH" "$CHECKSUM_URL"

    chmod +x "$BINARY_PATH"
    log_success "Binary downloaded"
}

# Run self-installer
run_install() {
    log_info "Running self-installer..."

    INSTALL_ARGS="install"
    if [ "$WITH_CLAUDE" = "1" ]; then
        INSTALL_ARGS="$INSTALL_ARGS --with-claude --scope $SCOPE"
    fi

    "$BINARY_PATH" $INSTALL_ARGS
    log_success "Installation complete"
}

# Show usage
show_usage() {
    echo ""
    echo "==============================================="
    echo -e "${GREEN}HuskyCat installed successfully!${NC}"
    echo "==============================================="
    echo ""
    echo "Usage:"
    echo "  huskycat validate           # Validate current directory"
    echo "  huskycat validate --staged  # Validate staged files"
    echo "  huskycat setup-hooks        # Setup git hooks"
    echo "  huskycat mcp-server         # Start MCP server"
    echo ""

    if [ "$WITH_CLAUDE" = "1" ]; then
        echo -e "${GREEN}Claude Code integration enabled!${NC}"
        echo "  The huskycat MCP server is now available in Claude Code."
        echo ""
    else
        echo "Claude Code integration:"
        echo '  claude mcp add huskycat -- huskycat mcp-server'
        echo ""
        echo "Or reinstall with auto-registration:"
        echo '  HUSKYCAT_WITH_CLAUDE=1 curl -fsSL https://tinyland.gitlab.io/ai/huskycat/install.sh | bash'
        echo ""
    fi
}

# Main
main() {
    echo -e "${BLUE}HuskyCat Installer${NC}"
    echo "=================="

    detect_platform
    log_info "Platform: ${PLATFORM}-${ARCH}"

    download_binary
    run_install
    show_usage
}

main "$@"
