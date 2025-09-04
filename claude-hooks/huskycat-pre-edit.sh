#!/bin/bash
# HuskyCat Pre-Edit Hook for Claude Code
# Validates files before Claude makes edits

# Get file path from Claude
FILE_PATH="$1"

# Skip if no file provided
if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Get repository root
REPO_ROOT="$(git -C "$(dirname "$FILE_PATH")" rev-parse --show-toplevel 2>/dev/null || pwd)"

# Check if HuskyCat MCP is available
MCP_URL="${HUSKYCAT_MCP_URL:-http://localhost:8080}"
MCP_TOKEN="${HUSKYCAT_TOKEN:-dev-token-for-testing}"

# Quick health check
if ! curl -s "$MCP_URL/health" > /dev/null 2>&1; then
    # MCP not available, skip validation
    exit 0
fi

# Get file extension to determine tool
FILE_EXT="${FILE_PATH##*.}"
TOOL=""

case "$FILE_EXT" in
    py) TOOL="python-black" ;;
    js|jsx) TOOL="javascript-eslint" ;;
    ts|tsx) TOOL="typescript-eslint" ;;
    sh|bash) TOOL="shell-shellcheck" ;;
    yml|yaml) TOOL="yaml-yamllint" ;;
    *) exit 0 ;; # Skip unknown file types
esac

# Run validation
RESPONSE=$(curl -s -X POST "$MCP_URL/rpc" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $MCP_TOKEN" \
    -H "X-Repo-Path: $REPO_ROOT" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"tools/call\",
        \"params\": {
            \"name\": \"$TOOL\",
            \"arguments\": {
                \"files\": [\"$FILE_PATH\"],
                \"fix\": false
            }
        },
        \"id\": 1
    }")

# Check if validation passed
if echo "$RESPONSE" | jq -e '.result.success' > /dev/null 2>&1; then
    # Validation passed
    exit 0
else
    # Extract error message
    ERROR=$(echo "$RESPONSE" | jq -r '.result.error // .error.message // "Validation failed"' 2>/dev/null)
    
    # Show validation issues to Claude
    echo "⚠️ HuskyCat Pre-Edit Validation:"
    echo "$ERROR" | head -20
    echo ""
    echo "Claude will see these issues and can fix them."
fi

# Always allow edit to proceed
exit 0