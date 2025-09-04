#!/bin/bash
# Service management script for HuskyCat

set -e

# Configuration
LOG_DIR="logs"
SERVICE_NAME="huskycat-mcp"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Functions
show_status() {
    echo -e "${BLUE}HuskyCat Service Status${NC}"
    echo "========================"
    
    # Check MCP server
    if [ -f "${LOG_DIR}/${SERVICE_NAME}.pid" ]; then
        PID=$(cat "${LOG_DIR}/${SERVICE_NAME}.pid")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ MCP Server: Running (PID: $PID)${NC}"
            
            # Show recent log entries
            if [ -f "$(ls -t ${LOG_DIR}/${SERVICE_NAME}_*.log 2>/dev/null | head -1)" ]; then
                LATEST_LOG=$(ls -t ${LOG_DIR}/${SERVICE_NAME}_*.log | head -1)
                echo "   Latest log: $LATEST_LOG"
            fi
        else
            echo -e "${RED}❌ MCP Server: Not running (stale PID: $PID)${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  MCP Server: Not deployed${NC}"
    fi
    
    # Check validation service
    if [ -f "${LOG_DIR}/validation.pid" ]; then
        PID=$(cat "${LOG_DIR}/validation.pid")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Validation Service: Running (PID: $PID)${NC}"
        else
            echo -e "${RED}❌ Validation Service: Not running (stale PID: $PID)${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Validation Service: Not deployed${NC}"
    fi
    
    echo ""
    echo "Active HuskyCat processes:"
    ps aux | grep huskycat | grep -v grep | grep -v manage.sh || echo "  None"
}

start_service() {
    echo -e "${GREEN}Starting HuskyCat services...${NC}"
    ./deploy.sh
}

stop_service() {
    echo -e "${YELLOW}Stopping HuskyCat services...${NC}"
    
    # Stop MCP server
    if [ -f "${LOG_DIR}/${SERVICE_NAME}.pid" ]; then
        PID=$(cat "${LOG_DIR}/${SERVICE_NAME}.pid")
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID"
            echo "Stopped MCP Server (PID: $PID)"
        fi
        rm "${LOG_DIR}/${SERVICE_NAME}.pid"
    fi
    
    # Stop validation service
    if [ -f "${LOG_DIR}/validation.pid" ]; then
        PID=$(cat "${LOG_DIR}/validation.pid")
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID"
            echo "Stopped Validation Service (PID: $PID)"
        fi
        rm "${LOG_DIR}/validation.pid"
    fi
    
    # Kill any remaining processes
    pkill -f "huskycat" || true
    
    echo -e "${GREEN}✅ All services stopped${NC}"
}

restart_service() {
    echo -e "${BLUE}Restarting HuskyCat services...${NC}"
    stop_service
    sleep 2
    start_service
}

show_logs() {
    if [ -z "$1" ]; then
        # Show latest log
        LATEST_LOG=$(ls -t ${LOG_DIR}/*.log 2>/dev/null | head -1)
        if [ -n "$LATEST_LOG" ]; then
            echo "Showing latest log: $LATEST_LOG"
            echo "Press Ctrl+C to exit"
            tail -f "$LATEST_LOG"
        else
            echo -e "${RED}No log files found${NC}"
        fi
    else
        # Show specific log
        if [ -f "${LOG_DIR}/$1" ]; then
            tail -f "${LOG_DIR}/$1"
        else
            echo -e "${RED}Log file not found: ${LOG_DIR}/$1${NC}"
        fi
    fi
}

clean_logs() {
    echo "This will delete all log files older than 7 days."
    echo "Continue? (y/n)"
    read -r response
    if [[ "$response" == "y" ]]; then
        find "${LOG_DIR}" -name "*.log" -mtime +7 -delete
        echo -e "${GREEN}✅ Old logs cleaned${NC}"
    fi
}

test_service() {
    echo -e "${BLUE}Testing HuskyCat MCP Server...${NC}"
    
    # Test with a simple request
    RESPONSE=$(echo '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' | ./dist/huskycat mcp --stdio 2>/dev/null || echo "")
    
    if echo "$RESPONSE" | grep -q '"jsonrpc"'; then
        echo -e "${GREEN}✅ MCP Server is responding correctly${NC}"
        echo "Response preview:"
        echo "$RESPONSE" | python3 -m json.tool | head -20
    else
        echo -e "${RED}❌ MCP Server test failed${NC}"
    fi
}

# Main menu
case "${1:-}" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "${2:-}"
        ;;
    clean)
        clean_logs
        ;;
    test)
        test_service
        ;;
    *)
        echo "HuskyCat Service Manager"
        echo "========================"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs|clean|test}"
        echo ""
        echo "Commands:"
        echo "  start    - Start all services"
        echo "  stop     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  status   - Show service status"
        echo "  logs     - Show latest logs (tail -f)"
        echo "  clean    - Clean old log files"
        echo "  test     - Test MCP server"
        echo ""
        echo "Examples:"
        echo "  $0 status        # Show current status"
        echo "  $0 start         # Start services"
        echo "  $0 logs          # Show latest log"
        echo "  $0 test          # Test MCP server"
        exit 1
        ;;
esac