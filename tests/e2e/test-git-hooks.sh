#!/bin/bash
# E2E Test for Git Hooks
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# Test directory
TEST_DIR="/tmp/huskycat-e2e-$$"
LOG_DIR="logs"
mkdir -p "$LOG_DIR"

# Log file with timestamp
LOG_FILE="$LOG_DIR/e2e-git-hooks-$(date +%Y%m%d-%H%M%S).log"

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

# Setup test environment
setup_test_repo() {
    log "Setting up test repository at $TEST_DIR"
    mkdir -p "$TEST_DIR"
    cd "$TEST_DIR"
    git init
    
    # Install huskycat hooks
    if [ -f "$OLDPWD/scripts/install.sh" ]; then
        cp "$OLDPWD/scripts/install.sh" .
        bash install.sh || log_error "Failed to install huskycat"
    else
        log_error "install.sh not found"
    fi
}

# Test pre-commit hook with Python file
test_pre_commit_python() {
    log "Testing pre-commit hook with Python file..."
    
    # Create badly formatted Python file
    cat > test.py << 'EOF'
import os,sys
def   bad_function (  ):
    x=1+2
    return x
EOF
    
    git add test.py
    
    # Try to commit - should fail due to formatting
    if git commit -m "test commit" 2>&1 | tee -a "$LOG_FILE" | grep -q "validation failed\|black\|format"; then
        log_success "Pre-commit hook correctly blocked badly formatted code"
    else
        log_error "Pre-commit hook failed to block bad code"
    fi
    
    # Fix the file
    cat > test.py << 'EOF'
import os
import sys


def good_function():
    x = 1 + 2
    return x
EOF
    
    git add test.py
    
    # Should succeed now
    if git commit -m "test: fixed formatting" 2>&1 | tee -a "$LOG_FILE"; then
        log_success "Pre-commit hook allowed properly formatted code"
    else
        log_error "Pre-commit hook incorrectly blocked good code"
    fi
}

# Test commit-msg hook
test_commit_msg() {
    log "Testing commit-msg hook..."
    
    # Create a file
    echo "test content" > test.txt
    git add test.txt
    
    # Bad commit message
    if ! git commit -m "bad message" 2>&1 | tee -a "$LOG_FILE" | grep -q "commit.*message"; then
        log_success "Commit-msg hook correctly blocked non-conventional commit"
    else
        log_error "Commit-msg hook failed to block bad message"
    fi
    
    # Good commit message
    if git commit -m "feat: add test file" 2>&1 | tee -a "$LOG_FILE"; then
        log_success "Commit-msg hook allowed conventional commit"
    else
        log_error "Commit-msg hook incorrectly blocked good message"
    fi
}

# Test with JavaScript file
test_pre_commit_javascript() {
    log "Testing pre-commit hook with JavaScript file..."
    
    # Create badly formatted JS file
    cat > test.js << 'EOF'
const x=1+2;function bad(){console.log("test")}
EOF
    
    git add test.js
    
    # Should trigger validation
    if git commit -m "feat: add js file" 2>&1 | tee -a "$LOG_FILE" | grep -q "prettier\|eslint\|validation"; then
        log_success "Pre-commit hook validated JavaScript file"
    else
        log "Warning: JavaScript validation may not be configured"
    fi
}

# Test YAML validation
test_pre_commit_yaml() {
    log "Testing pre-commit hook with YAML file..."
    
    # Create invalid YAML
    cat > test.yaml << 'EOF'
invalid yaml content:
  - no proper structure
    bad indentation
EOF
    
    git add test.yaml
    
    if ! git commit -m "feat: add yaml" 2>&1 | tee -a "$LOG_FILE"; then
        log_success "Pre-commit hook caught invalid YAML"
    else
        log "Warning: YAML validation may not be configured"
    fi
    
    # Fix YAML
    cat > test.yaml << 'EOF'
valid:
  structure:
    - item1
    - item2
EOF
    
    git add test.yaml
    
    if git commit -m "feat: add valid yaml" 2>&1 | tee -a "$LOG_FILE"; then
        log_success "Pre-commit hook allowed valid YAML"
    else
        log_error "Pre-commit hook incorrectly blocked valid YAML"
    fi
}

# Cleanup
cleanup() {
    cd /
    rm -rf "$TEST_DIR"
    log "Cleaned up test directory"
}

# Main test execution
main() {
    log "======================================"
    log "HuskyCat Git Hooks E2E Test"
    log "======================================"
    log "Log file: $LOG_FILE"
    
    # Run tests
    setup_test_repo
    test_pre_commit_python
    test_commit_msg
    test_pre_commit_javascript
    test_pre_commit_yaml
    
    # Cleanup
    cleanup
    
    log "======================================"
    log_success "All tests completed successfully!"
    log "======================================"
}

# Run with error handling
trap cleanup EXIT
main "$@"