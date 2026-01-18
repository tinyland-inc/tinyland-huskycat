#!/bin/bash
# HuskyCat MCP Server wrapper for Claude Code
# This script runs the MCP server using UV from the project directory

set -e

# Get the directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Suppress UV warnings and run MCP server
# Redirect all stderr to /dev/null except critical errors, as MCP uses stdout for JSON-RPC
export VIRTUAL_ENV=""
export HUSKYCAT_LOG_LEVEL="ERROR"
exec uv run --quiet python -m src.huskycat mcp-server "$@" 2>/dev/null
