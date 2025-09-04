# MCP Server Installation Guide for Claude Desktop

This guide walks you through setting up the HuskyCat MCP server for use with Claude Desktop and other AI assistants.

## Prerequisites

- Podman Desktop or Docker Desktop installed
- Claude Desktop (or other MCP-compatible AI assistant)
- 4GB RAM minimum
- 10GB disk space

## Quick Start

### 1. Deploy MCP Server

```bash
# Clone the repository
git clone https://github.com/yourusername/huskycats-bates.git
cd huskycats-bates/mcp-server

# Start the server
podman-compose up -d

# Verify it's running
curl http://localhost:8080/health
```

### 2. Configure Claude Desktop

Add to your Claude Desktop configuration file:

**macOS/Linux:** `~/.claude/mcp_settings.json`
**Windows:** `%APPDATA%\Claude\mcp_settings.json`

```json
{
  "mcpServers": {
    "huskycats": {
      "url": "http://localhost:8080/rpc",
      "type": "http",
      "authentication": {
        "type": "bearer",
        "token": "dev-token-for-testing"
      },
      "headers": {
        "X-Repo-Path": "/path/to/your/default/repo"
      }
    }
  }
}
```

### 3. Restart Claude Desktop

After saving the configuration, restart Claude Desktop to load the MCP server.

## Detailed Setup

### Building from Source

If you want to customize or develop:

```bash
cd huskycats-bates/mcp-server

# Install dependencies
npm install

# Build TypeScript
npm run build

# Run development server
npm run dev
```

### Production Deployment

For a production-ready setup with authentication:

```bash
# Generate secure token
export MCP_AUTH_TOKEN=$(openssl rand -hex 32)
echo "Save this token: $MCP_AUTH_TOKEN"

# Create .env file
cat > .env << EOF
NODE_ENV=production
MCP_PORT=8080
MCP_HOST=0.0.0.0
BEARER_TOKEN=$MCP_AUTH_TOKEN
ENABLE_SYNCTHING=true
LOG_LEVEL=info
EOF

# Deploy with docker-compose
docker-compose up -d
```

Update Claude configuration with your token:

```json
{
  "mcpServers": {
    "huskycats": {
      "url": "http://localhost:8080/rpc",
      "type": "http",
      "authentication": {
        "type": "bearer",
        "token": "YOUR_GENERATED_TOKEN_HERE"
      }
    }
  }
}
```

## Using with Claude

Once configured, you can ask Claude to:

### Validate Code
```
"Claude, please validate the Python files in my project"
"Check this file for style issues: src/main.py"
"Run security scanning on my codebase"
```

### Fix Issues
```
"Fix the formatting issues in my Python files"
"Update my code to pass flake8 checks"
"Make my JavaScript comply with ESLint rules"
```

### Multi-Repository Support
```
"Validate the code in /path/to/project-a"
"Compare code quality between project-a and project-b"
"Run security scan on all my repositories"
```

## Claude Code Hooks Integration

For automatic validation during coding sessions:

### 1. Install Claude Code Hooks

```bash
# Create hooks directory
mkdir -p ~/.claude/hooks

# Install HuskyCat hooks
cd huskycats-bates
cp -r claude-hooks/* ~/.claude/hooks/
chmod +x ~/.claude/hooks/*
```

### 2. Configure Auto-Validation

Create `~/.claude/settings.json`:

```json
{
  "hooks": {
    "pre-file-edit": "~/.claude/hooks/huskycat-pre-edit.sh",
    "post-file-edit": "~/.claude/hooks/huskycat-post-edit.sh"
  },
  "validation": {
    "autoValidate": true,
    "autoFix": false,
    "showInline": true
  }
}
```

### 3. Hook Scripts

The hooks automatically validate files before and after Claude edits them:

**`huskycat-pre-edit.sh`:**
```bash
#!/bin/bash
# Validates file before Claude edits
FILE_PATH="$1"
REPO_PATH="$(git -C $(dirname "$FILE_PATH") rev-parse --show-toplevel 2>/dev/null || pwd)"

curl -s -X POST http://localhost:8080/rpc \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $HUSKYCAT_TOKEN" \
  -H "X-Repo-Path: $REPO_PATH" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"method\": \"tools/call\",
    \"params\": {
      \"name\": \"validate-file\",
      \"arguments\": {\"file\": \"$FILE_PATH\"}
    },
    \"id\": 1
  }"
```

## Advanced Features

### Syncthing Integration

For distributed validation across multiple machines:

```bash
# Enable syncthing in .env
ENABLE_SYNCTHING=true
SYNCTHING_API_KEY=your-syncthing-api-key

# Access Syncthing UI
open http://localhost:8384
```

### Custom Validation Rules

Create custom validation profiles:

```bash
# Add to mcp-server/config/profiles/
cat > mcp-server/config/profiles/strict-python.yaml << EOF
name: strict-python
tools:
  - python-black
  - python-flake8
  - python-mypy
  - python-bandit
  - python-pylint
options:
  black:
    line-length: 79
  flake8:
    max-line-length: 79
    ignore: []
  mypy:
    strict: true
EOF
```

### Monitoring and Metrics

```bash
# Enable metrics
ENABLE_METRICS=true

# View metrics
curl http://localhost:8080/metrics

# Prometheus scrape config
scrape_configs:
  - job_name: 'huskycat-mcp'
    static_configs:
      - targets: ['localhost:8080']
```

## Troubleshooting

### Server Not Responding

```bash
# Check if running
podman ps | grep huskycat

# View logs
podman logs huskycats-mcp

# Restart
podman-compose restart
```

### Claude Can't Connect

1. Check Claude logs: `~/.claude/logs/`
2. Test connection:
```bash
curl -X POST http://localhost:8080/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```
3. Verify token in both .env and Claude config

### Performance Issues

```bash
# Increase resources in docker-compose.yml
services:
  mcp-server:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

## Security Considerations

### Network Security

For production use:

```bash
# Use TLS (add to docker-compose.yml)
services:
  mcp-server:
    environment:
      - ENABLE_TLS=true
      - TLS_CERT_FILE=/certs/server.crt
      - TLS_KEY_FILE=/certs/server.key
    volumes:
      - ./certs:/certs:ro
```

### Token Rotation

Regularly rotate authentication tokens:

```bash
# Generate new token
NEW_TOKEN=$(openssl rand -hex 32)

# Update .env
sed -i "s/BEARER_TOKEN=.*/BEARER_TOKEN=$NEW_TOKEN/" .env

# Restart server
podman-compose restart

# Update Claude config with new token
```

## Next Steps

- [Configure validation rules](mcp-config.md)
- [Set up team deployment](mcp-team-setup.md)
- [Integrate with CI/CD](mcp-cicd.md)
- [Production deployment guide](install-production.md)