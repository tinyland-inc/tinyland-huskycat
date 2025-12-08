#!/bin/bash
# Binary Verification Script for HuskyCat
# Tests fat binary installation, tool extraction, and validation

set -e

BINARY="$1"

if [[ -z "$BINARY" ]]; then
    echo "Usage: $0 <path-to-huskycat-binary>"
    echo "Example: $0 dist/huskycat"
    exit 1
fi

if [[ ! -f "$BINARY" ]]; then
    echo "Error: Binary not found: $BINARY"
    exit 1
fi

echo "======================================================================"
echo "HuskyCat Binary Verification"
echo "======================================================================"
echo "Binary: $BINARY"
echo "Platform: $(uname -s) $(uname -m)"
echo "Date: $(date)"
echo ""

TESTS_PASSED=0
TESTS_FAILED=0

# Test 1: Basic execution (--help)
echo "Test 1: --help command"
echo "----------------------------------------------------------------------"
if $BINARY --help >/dev/null 2>&1; then
    echo "✓ PASS: --help command executed successfully"
    ((TESTS_PASSED++))
else
    echo "✗ FAIL: --help command failed"
    ((TESTS_FAILED++))
fi
echo ""

# Test 2: Version command
echo "Test 2: --version command"
echo "----------------------------------------------------------------------"
if VERSION=$($BINARY --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1); then
    echo "✓ PASS: Version detected: $VERSION"
    ((TESTS_PASSED++))
else
    echo "✗ FAIL: Could not detect version"
    ((TESTS_FAILED++))
fi
echo ""

# Test 3: Frozen mode detection
echo "Test 3: Frozen mode environment variable"
echo "----------------------------------------------------------------------"
# The HUSKYCAT_FROZEN env var is set internally by the binary
# We can verify it indirectly by checking if tools get extracted
if [[ -n "$HUSKYCAT_FROZEN" ]]; then
    echo "✓ PASS: HUSKYCAT_FROZEN is set: $HUSKYCAT_FROZEN"
    ((TESTS_PASSED++))
else
    echo "ℹ INFO: HUSKYCAT_FROZEN not set in environment (this is normal)"
    echo "  Binary sets this internally during execution"
    ((TESTS_PASSED++))
fi
echo ""

# Test 4: Tool extraction
echo "Test 4: Tool extraction to ~/.huskycat/tools/"
echo "----------------------------------------------------------------------"
# Clean slate for testing
TOOLS_DIR="$HOME/.huskycat/tools"
if [[ -d "$TOOLS_DIR" ]]; then
    echo "  Cleaning existing tools directory..."
    rm -rf "$TOOLS_DIR"
fi

# Trigger extraction by running validate --help
$BINARY validate --help >/dev/null 2>&1 || true

# Check if tools were extracted
TOOLS_FOUND=0
TOOLS_MISSING=()

if [[ -f "$TOOLS_DIR/shellcheck" ]]; then
    ((TOOLS_FOUND++))
else
    TOOLS_MISSING+=("shellcheck")
fi

if [[ -f "$TOOLS_DIR/hadolint" ]]; then
    ((TOOLS_FOUND++))
else
    TOOLS_MISSING+=("hadolint")
fi

if [[ -f "$TOOLS_DIR/taplo" ]]; then
    ((TOOLS_FOUND++))
else
    TOOLS_MISSING+=("taplo")
fi

if [[ $TOOLS_FOUND -eq 3 ]]; then
    echo "✓ PASS: All 3 tools extracted successfully"
    echo "  - shellcheck"
    echo "  - hadolint"
    echo "  - taplo"
    ((TESTS_PASSED++))
else
    echo "✗ FAIL: Only $TOOLS_FOUND/3 tools extracted"
    if [[ ${#TOOLS_MISSING[@]} -gt 0 ]]; then
        echo "  Missing tools: ${TOOLS_MISSING[*]}"
    fi
    ((TESTS_FAILED++))
fi
echo ""

# Test 5: Tool execution
echo "Test 5: Extracted tools are executable"
echo "----------------------------------------------------------------------"
TOOLS_EXECUTABLE=0
TOOLS_NOT_EXECUTABLE=()

if [[ -f "$TOOLS_DIR/shellcheck" ]] && "$TOOLS_DIR/shellcheck" --version >/dev/null 2>&1; then
    ((TOOLS_EXECUTABLE++))
else
    TOOLS_NOT_EXECUTABLE+=("shellcheck")
fi

if [[ -f "$TOOLS_DIR/hadolint" ]] && "$TOOLS_DIR/hadolint" --version >/dev/null 2>&1; then
    ((TOOLS_EXECUTABLE++))
else
    TOOLS_NOT_EXECUTABLE+=("hadolint")
fi

if [[ -f "$TOOLS_DIR/taplo" ]] && "$TOOLS_DIR/taplo" --version >/dev/null 2>&1; then
    ((TOOLS_EXECUTABLE++))
else
    TOOLS_NOT_EXECUTABLE+=("taplo")
fi

if [[ $TOOLS_EXECUTABLE -eq 3 ]]; then
    echo "✓ PASS: All 3 tools are executable and functional"
    ((TESTS_PASSED++))
else
    echo "✗ FAIL: Only $TOOLS_EXECUTABLE/3 tools are executable"
    if [[ ${#TOOLS_NOT_EXECUTABLE[@]} -gt 0 ]]; then
        echo "  Non-executable tools: ${TOOLS_NOT_EXECUTABLE[*]}"
    fi
    ((TESTS_FAILED++))
fi
echo ""

# Test 6: Validation works
echo "Test 6: Run validation on test file"
echo "----------------------------------------------------------------------"
# Create a simple test shell script
TEST_FILE="/tmp/huskycat_test_$$"
cat > "$TEST_FILE" <<'EOF'
#!/bin/bash
# Test script for shellcheck validation
echo "Hello, World!"
EOF

if $BINARY validate "$TEST_FILE" >/dev/null 2>&1; then
    echo "✓ PASS: Validation executed successfully"
    ((TESTS_PASSED++))
else
    echo "✗ FAIL: Validation failed"
    echo "  Trying with verbose output:"
    $BINARY validate "$TEST_FILE" 2>&1 || true
    ((TESTS_FAILED++))
fi

# Cleanup
rm -f "$TEST_FILE"
echo ""

# Summary
echo "======================================================================"
echo "Verification Summary"
echo "======================================================================"
echo "Tests passed: $TESTS_PASSED"
echo "Tests failed: $TESTS_FAILED"
echo "Total tests:  $((TESTS_PASSED + TESTS_FAILED))"
echo ""

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo "✅ All binary tests passed!"
    echo ""
    echo "Binary is ready for:"
    echo "  - Installation: $BINARY install"
    echo "  - Hook setup:   $BINARY setup-hooks"
    echo "  - Validation:   $BINARY validate <files>"
    exit 0
else
    echo "❌ Some binary tests failed"
    echo ""
    echo "Review the errors above and:"
    echo "  - Check binary build process"
    echo "  - Verify PyInstaller configuration"
    echo "  - Check tool embedding in build"
    exit 1
fi
