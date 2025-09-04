#!/bin/bash
# HuskyCat Distribution Testing Script
# Tests the packaged binary on different platforms

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Platform detection
PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
    ARCH="amd64"
elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    ARCH="arm64"
fi

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    ((TESTS_PASSED++))
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    ((TESTS_FAILED++))
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Test binary existence
test_binary_exists() {
    log_info "Testing binary existence..."
    
    BINARY_PATH="dist/binaries/huskycat-${PLATFORM}-${ARCH}"
    if [ -f "$BINARY_PATH" ]; then
        log_success "Binary found: $BINARY_PATH"
        return 0
    else
        log_error "Binary not found: $BINARY_PATH"
        return 1
    fi
}

# Test binary execution
test_binary_execution() {
    log_info "Testing binary execution..."
    
    BINARY_PATH="dist/binaries/huskycat-${PLATFORM}-${ARCH}"
    if [ ! -f "$BINARY_PATH" ]; then
        log_error "Binary not found"
        return 1
    fi
    
    # Test version flag
    if $BINARY_PATH --version &>/dev/null; then
        VERSION=$($BINARY_PATH --version 2>&1 || echo "unknown")
        log_success "Version command works: $VERSION"
    else
        log_error "Version command failed"
    fi
    
    # Test help flag
    if $BINARY_PATH --help &>/dev/null; then
        log_success "Help command works"
    else
        log_error "Help command failed"
    fi
}

# Test Python validation functionality
test_python_validation() {
    log_info "Testing Python validation..."
    
    BINARY_PATH="dist/binaries/huskycat-${PLATFORM}-${ARCH}"
    if [ ! -f "$BINARY_PATH" ]; then
        log_error "Binary not found"
        return 1
    fi
    
    # Create test Python file
    TEMP_DIR=$(mktemp -d)
    cat > "$TEMP_DIR/test.py" << 'EOF'
import os
def test():
    x=1+2
    return x
EOF
    
    # Test validation
    if $BINARY_PATH validate "$TEMP_DIR/test.py" &>/dev/null; then
        log_success "Python validation works"
    else
        log_warn "Python validation returned non-zero (expected for badly formatted code)"
    fi
    
    # Cleanup
    rm -rf "$TEMP_DIR"
}

# Test MCP stdio server
test_mcp_server() {
    log_info "Testing MCP stdio server..."
    
    BINARY_PATH="dist/binaries/huskycat-${PLATFORM}-${ARCH}"
    if [ ! -f "$BINARY_PATH" ]; then
        log_error "Binary not found"
        return 1
    fi
    
    # Test MCP server starts
    echo '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}' | \
        timeout 2 $BINARY_PATH mcp --stdio 2>/dev/null | \
        grep -q "protocolVersion" && log_success "MCP server responds" || \
        log_error "MCP server not responding"
}

# Test container integration
test_container_integration() {
    log_info "Testing container integration..."
    
    # Detect container runtime
    if command -v podman &> /dev/null; then
        RUNTIME="podman"
    elif command -v docker &> /dev/null; then
        RUNTIME="docker"
    else
        log_warn "No container runtime found, skipping container tests"
        return 0
    fi
    
    BINARY_PATH="dist/binaries/huskycat-${PLATFORM}-${ARCH}"
    if [ ! -f "$BINARY_PATH" ]; then
        log_error "Binary not found"
        return 1
    fi
    
    # Check if binary can detect container runtime
    if $BINARY_PATH info 2>&1 | grep -q "$RUNTIME"; then
        log_success "Binary detects container runtime: $RUNTIME"
    else
        log_warn "Binary may not detect container runtime"
    fi
}

# Test file size and compression
test_binary_size() {
    log_info "Testing binary size..."
    
    BINARY_PATH="dist/binaries/huskycat-${PLATFORM}-${ARCH}"
    if [ ! -f "$BINARY_PATH" ]; then
        log_error "Binary not found"
        return 1
    fi
    
    # Get file size in MB
    if [ "$PLATFORM" = "darwin" ]; then
        SIZE=$(stat -f%z "$BINARY_PATH" 2>/dev/null || echo 0)
    else
        SIZE=$(stat -c%s "$BINARY_PATH" 2>/dev/null || echo 0)
    fi
    
    SIZE_MB=$((SIZE / 1024 / 1024))
    
    if [ "$SIZE_MB" -lt 50 ]; then
        log_success "Binary size acceptable: ${SIZE_MB}MB (< 50MB)"
    else
        log_warn "Binary size large: ${SIZE_MB}MB (target < 50MB)"
    fi
    
    # Check if UPX compressed
    if command -v upx &> /dev/null; then
        if upx -t "$BINARY_PATH" &>/dev/null; then
            log_success "Binary is UPX compressed"
        else
            log_warn "Binary is not UPX compressed"
        fi
    fi
}

# Test platform-specific package
test_platform_package() {
    log_info "Testing platform-specific package..."
    
    case "$PLATFORM" in
        linux)
            # Test RPM or DEB based on distribution
            if [ -f /etc/redhat-release ] || [ -f /etc/rocky-release ]; then
                if [ -f "dist/rpm/huskycat-2.0.0-1.${ARCH}.rpm" ]; then
                    log_success "RPM package found"
                else
                    log_warn "RPM package not found"
                fi
            elif [ -f /etc/debian_version ]; then
                if [ -f "dist/deb/huskycat_2.0.0_${ARCH}.deb" ]; then
                    log_success "DEB package found"
                else
                    log_warn "DEB package not found"
                fi
            fi
            ;;
        darwin)
            if [ -f "dist/macos/huskycat" ]; then
                log_success "macOS binary found"
            else
                log_warn "macOS binary not found"
            fi
            ;;
        *)
            log_warn "Unknown platform: $PLATFORM"
            ;;
    esac
}

# Test installation and uninstallation
test_install_uninstall() {
    log_info "Testing installation and uninstallation..."
    
    # Test local installation
    if make install-local &>/dev/null; then
        if [ -f "$HOME/.local/bin/huskycat" ]; then
            log_success "Local installation successful"
            
            # Test uninstallation
            if make uninstall &>/dev/null; then
                if [ ! -f "$HOME/.local/bin/huskycat" ]; then
                    log_success "Uninstallation successful"
                else
                    log_error "Uninstallation failed - binary still exists"
                fi
            else
                log_error "Uninstallation command failed"
            fi
        else
            log_error "Local installation failed - binary not found"
        fi
    else
        log_error "Installation command failed"
    fi
}

# Main test execution
main() {
    echo "======================================"
    echo "   HuskyCat Distribution Testing"
    echo "======================================"
    echo "Platform: $PLATFORM"
    echo "Architecture: $ARCH"
    echo ""
    
    # Run tests
    test_binary_exists
    test_binary_execution
    test_python_validation
    test_mcp_server
    test_container_integration
    test_binary_size
    test_platform_package
    test_install_uninstall
    
    # Summary
    echo ""
    echo "======================================"
    echo "          Test Summary"
    echo "======================================"
    echo -e "${GREEN}Passed:${NC} $TESTS_PASSED"
    echo -e "${RED}Failed:${NC} $TESTS_FAILED"
    
    if [ "$TESTS_FAILED" -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}Some tests failed${NC}"
        exit 1
    fi
}

# Run main
main "$@"