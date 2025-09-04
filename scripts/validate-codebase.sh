#!/bin/bash
# Validate HuskyCat codebase using MCP server

set -e

MCP_URL="http://localhost:8080/rpc"
TOKEN="dev-token-for-testing"

echo "🔍 Validating HuskyCat codebase with MCP server..."

# Initialize session
SESSION_ID=$(curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "huskycat-self-validation", "version": "2.0.0"}
    },
    "id": 1
  }' | jq -r '.result.sessionId // empty')

echo "✅ Session initialized"

# Validate entire project
echo "🧪 Running comprehensive project validation..."
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "validate_project",
      "arguments": {
        "directory": ".",
        "exclude": ["node_modules/**", ".git/**", "dist/**", "build/**", "build_venv/**"],
        "fixIssues": false,
        "parallel": true
      }
    },
    "id": 2
  }' | jq .

# Python specific validation
echo -e "\n🐍 Validating Python code..."
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "python-black",
      "arguments": {
        "files": ["huskycat/*.py", "build.py", "setup.py"],
        "fix": false
      }
    },
    "id": 3
  }' | jq .

# Security scan
echo -e "\n🔒 Running security scan..."
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "security_secrets_scan",
      "arguments": {
        "directory": ".",
        "exclude": [".git/**", "node_modules/**", "build/**", "dist/**"],
        "outputFormat": "json"
      }
    },
    "id": 4
  }' | jq .

# YAML validation
echo -e "\n📄 Validating YAML files..."
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "yaml-yamllint",
      "arguments": {
        "files": [".gitlab-ci-autodevops.yml", ".huskycat.yaml", "mcp-server/docker-compose.yml"],
        "fix": false
      }
    },
    "id": 5
  }' | jq .

echo -e "\n✅ Validation complete!"