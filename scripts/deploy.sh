#!/bin/bash
# Deployment script for HuskyCat with nohup and dated logs

set -e

# Configuration
SERVICE_NAME="huskycat-mcp"
LOG_DIR="logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/${SERVICE_NAME}_${TIMESTAMP}.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}HuskyCat Deployment Script${NC}"
echo "========================================="

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Check if already running
if pgrep -f "huskycat mcp --stdio" > /dev/null; then
    echo -e "${YELLOW}Warning: HuskyCat MCP server is already running${NC}"
    echo "Do you want to stop it and restart? (y/n)"
    read -r response
    if [[ "$response" == "y" ]]; then
        echo "Stopping existing service..."
        pkill -f "huskycat mcp --stdio" || true
        sleep 2
    else
        echo "Deployment cancelled"
        exit 1
    fi
fi

# Build the binary if needed
if [ ! -f "dist/huskycat" ]; then
    echo -e "${YELLOW}Binary not found. Building...${NC}"
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    fi
    pyinstaller build/specs/huskycat.spec --clean
fi

# Verify binary exists
if [ ! -f "dist/huskycat" ]; then
    echo -e "${RED}Error: Binary build failed${NC}"
    exit 1
fi

# Deploy MCP server
echo -e "${GREEN}Starting HuskyCat MCP Server${NC}"
echo "Log file: $LOG_FILE"

# Start with nohup
nohup ./dist/huskycat mcp --stdio > "$LOG_FILE" 2>&1 &
MCP_PID=$!

echo "MCP Server started with PID: $MCP_PID"

# Save PID for later management
echo "$MCP_PID" > "${LOG_DIR}/${SERVICE_NAME}.pid"

# Wait a moment and check if it's running
sleep 2

if ps -p $MCP_PID > /dev/null; then
    echo -e "${GREEN}✅ MCP Server successfully deployed${NC}"
    echo ""
    echo "Service Information:"
    echo "-------------------"
    echo "PID: $MCP_PID"
    echo "Log: $LOG_FILE"
    echo ""
    echo "To monitor logs:"
    echo "  tail -f $LOG_FILE"
    echo ""
    echo "To stop the service:"
    echo "  kill $MCP_PID"
    echo ""
    echo "To test the service:"
    echo "  echo '{\"jsonrpc\": \"2.0\", \"method\": \"tools/list\", \"id\": 1}' | ./dist/huskycat mcp --stdio"
else
    echo -e "${RED}❌ Failed to start MCP Server${NC}"
    echo "Check the log file for errors: $LOG_FILE"
    tail -n 20 "$LOG_FILE"
    exit 1
fi

# Optional: Start validation service in background
echo ""
echo "Do you want to start the validation service? (y/n)"
read -r response
if [[ "$response" == "y" ]]; then
    VALIDATION_LOG="${LOG_DIR}/validation_${TIMESTAMP}.log"
    echo "Starting validation service..."
    nohup ./dist/huskycat validate --watch . > "$VALIDATION_LOG" 2>&1 &
    VALIDATION_PID=$!
    echo "$VALIDATION_PID" > "${LOG_DIR}/validation.pid"
    echo -e "${GREEN}✅ Validation service started (PID: $VALIDATION_PID)${NC}"
    echo "Log: $VALIDATION_LOG"
fi

echo ""
echo -e "${GREEN}Deployment complete!${NC}"
echo ""
echo "Active services:"
ps aux | grep huskycat | grep -v grep || echo "No services running"