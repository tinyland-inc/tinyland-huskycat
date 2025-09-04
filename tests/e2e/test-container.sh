#!/bin/bash
# E2E Test for Container Validation
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# Configuration
CONTAINER_NAME="huskycat-test-$$"
CONTAINER_IMAGE="${CONTAINER_IMAGE:-huskycat:latest}"
LOG_DIR="logs"
LOG_FILE="$LOG_DIR/e2e-container-$(date +%Y%m%d-%H%M%S).log"

# Create log directory
mkdir -p "$LOG_DIR"

log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

log_success() {
    log "${GREEN}✓${NC} $1"
}

log_error() {
    log "${RED}✗${NC} $1"
    exit 1
}

# Detect container runtime
detect_runtime() {
    if command -v podman &> /dev/null; then
        RUNTIME="podman"
    elif command -v docker &> /dev/null; then
        RUNTIME="docker"
    else
        log_error "No container runtime found (podman/docker)"
    fi
    log "Using container runtime: $RUNTIME"
}

# Build container
build_container() {
    log "Building container from ContainerFile..."
    
    if $RUNTIME build -f ContainerFile -t "$CONTAINER_IMAGE" . >> "$LOG_FILE" 2>&1; then
        log_success "Container built successfully"
    else
        log_error "Failed to build container"
    fi
}

# Test container help
test_container_help() {
    log "Testing container help command..."
    
    if $RUNTIME run --rm "$CONTAINER_IMAGE" --help >> "$LOG_FILE" 2>&1; then
        log_success "Container help command works"
    else
        log_error "Container help command failed"
    fi
}

# Test Python validation in container
test_python_validation() {
    log "Testing Python validation in container..."
    
    # Create test file
    cat > /tmp/test.py << 'EOF'
import os,sys
def bad():
    x=1+2
    return x
EOF
    
    # Run validation
    if $RUNTIME run --rm -v /tmp:/workspace "$CONTAINER_IMAGE" validate test.py 2>&1 | tee -a "$LOG_FILE" | grep -q "black\|format\|validation"; then
        log_success "Python validation detected formatting issues"
    else
        log_error "Python validation failed to detect issues"
    fi
    
    # Cleanup
    rm -f /tmp/test.py
}

# Test JavaScript validation
test_javascript_validation() {
    log "Testing JavaScript validation in container..."
    
    # Create test file
    cat > /tmp/test.js << 'EOF'
const x=1;function bad(){console.log("test")}
EOF
    
    # Run validation
    if $RUNTIME run --rm -v /tmp:/workspace "$CONTAINER_IMAGE" validate test.js >> "$LOG_FILE" 2>&1; then
        log "JavaScript validation completed"
    else
        log "Warning: JavaScript validation may not be configured"
    fi
    
    # Cleanup
    rm -f /tmp/test.js
}

# Test YAML validation
test_yaml_validation() {
    log "Testing YAML validation in container..."
    
    # Create test file
    cat > /tmp/test.yaml << 'EOF'
valid:
  key: value
  list:
    - item1
    - item2
EOF
    
    # Run validation
    if $RUNTIME run --rm -v /tmp:/workspace "$CONTAINER_IMAGE" validate test.yaml >> "$LOG_FILE" 2>&1; then
        log_success "YAML validation passed for valid file"
    else
        log_error "YAML validation failed for valid file"
    fi
    
    # Cleanup
    rm -f /tmp/test.yaml
}

# Test container security
test_container_security() {
    log "Testing container security..."
    
    # Check non-root user
    USER_ID=$($RUNTIME run --rm "$CONTAINER_IMAGE" id -u 2>/dev/null)
    if [ "$USER_ID" != "0" ]; then
        log_success "Container runs as non-root user (UID: $USER_ID)"
    else
        log_error "Container runs as root - security issue!"
    fi
    
    # Check read-only filesystem (should fail to write to /app)
    if ! $RUNTIME run --rm "$CONTAINER_IMAGE" sh -c "touch /app/test 2>/dev/null"; then
        log_success "Container filesystem is properly restricted"
    else
        log_error "Container allows writing to application directory"
    fi
}

# Test health check
test_health_check() {
    log "Testing container health check..."
    
    # Start container
    $RUNTIME run -d --name "$CONTAINER_NAME" "$CONTAINER_IMAGE" sleep 30 >> "$LOG_FILE" 2>&1
    
    # Wait for container to be healthy
    sleep 2
    
    # Check health
    if $RUNTIME exec "$CONTAINER_NAME" python3 -c "import sys; sys.exit(0)" >> "$LOG_FILE" 2>&1; then
        log_success "Container health check passed"
    else
        log_error "Container health check failed"
    fi
    
    # Cleanup
    $RUNTIME stop "$CONTAINER_NAME" >> "$LOG_FILE" 2>&1
    $RUNTIME rm "$CONTAINER_NAME" >> "$LOG_FILE" 2>&1
}

# Test all validators are available
test_all_tools() {
    log "Testing all validation tools are available..."
    
    TOOLS=(
        "black --version"
        "flake8 --version"
        "mypy --version"
        "bandit --version"
        "ruff --version"
        "yamllint --version"
        "shellcheck --version"
        "hadolint --version"
    )
    
    for tool_cmd in "${TOOLS[@]}"; do
        if $RUNTIME run --rm "$CONTAINER_IMAGE" sh -c "$tool_cmd" >> "$LOG_FILE" 2>&1; then
            log_success "Tool available: $tool_cmd"
        else
            log "Warning: Tool not available: $tool_cmd"
        fi
    done
}

# Main test execution
main() {
    log "======================================"
    log "HuskyCat Container E2E Test"
    log "======================================"
    
    detect_runtime
    build_container
    
    test_container_help
    test_python_validation
    test_javascript_validation
    test_yaml_validation
    test_container_security
    test_health_check
    test_all_tools
    
    log "======================================"
    log_success "All container tests completed!"
    log "======================================"
}

# Run tests
main "$@"