# MCP Server Integration Guide

This guide covers how to integrate the HuskyCat MCP Server with AI assistants and development workflows.

## Overview

The HuskyCat MCP Server exposes validation and linting tools through the Model Context Protocol (MCP), allowing AI assistants like Claude to directly run code quality checks and CI validation.

## Architecture

The MCP server provides:
- Stdio transport with JSON-RPC 2.0 protocol
- GitLab CI validation tools
- Direct integration with validation commands
- Schema updating and caching
- Git hooks integration

## Installation Methods

### 1. Using HuskyCat Binary

```bash
# Start MCP server via HuskyCat binary
./dist/huskycat mcp-server

# Start on specific port (default is stdio)
./dist/huskycat mcp-server --port 8080
```

### 2. Via NPM Scripts

```bash
# Using development mode
npm run mcp:server

# Test MCP server
npm run mcp:test
```

### 3. Container Integration

```bash
# Build container with MCP support
npm run container:build

# Run MCP server in container
podman run --rm -p 8080:8080 huskycat:local mcp-server --port 8080
```

## Claude Code Integration

### Basic Configuration

Add to Claude Code MCP configuration:

```json
{
  "mcpServers": {
    "huskycat": {
      "command": "/path/to/huskycat",
      "args": ["mcp-server", "--port=0"],
      "description": "HuskyCat validation platform"
    }
  }
}
```

### With Authentication

For production deployments:

```json
{
  "mcpServers": {
    "huskycats": {
      "url": "https://mcp.example.com/rpc",
      "type": "http",
      "headers": {
        "Authorization": "Bearer ${MCP_AUTH_TOKEN}"
      }
    }
  }
}
```

## Available Tools

### Python Tools
- `python-black` - Format Python code
- `python-flake8` - Lint for style and errors
- `python-mypy` - Type checking
- `python-bandit` - Security analysis

### JavaScript/TypeScript
- `js-eslint` - Lint JavaScript/TypeScript
- `js-prettier` - Format code

### Infrastructure
- `shell-shellcheck` - Lint shell scripts
- `docker-hadolint` - Lint Dockerfiles
- `yaml-yamllint` - Lint YAML files
- `ansible-lint` - Lint Ansible playbooks
- `gitlab-ci-validate` - Validate GitLab CI

## Usage Examples

### From Claude

Once configured, Claude can use commands like:

```
"Use the python-black tool to format all Python files in the src directory"
"Check this Dockerfile for best practices using docker-hadolint"
"Validate the .gitlab-ci.yml file"
```

### Direct API Usage

#### Initialize Connection
```bash
curl -X POST http://localhost:8080/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {}
  }'
```

#### List Tools
```bash
curl -X POST http://localhost:8080/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
  }'
```

#### Run a Tool
```bash
curl -X POST http://localhost:8080/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "python-black",
      "arguments": {
        "files": ["app.py"],
        "fix": true
      }
    }
  }'
```

## Security Configuration

### Environment Variables
- `MCP_AUTH_TOKEN` - Bearer token for authentication
- `CORS_ORIGIN` - Allowed CORS origin
- `NODE_ENV` - Set to "production" for security

### Kubernetes Secrets
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mcp-server-auth
type: Opaque
data:
  token: <base64-encoded-token>
```

### Network Policies
The server only exposes port 8080. In Kubernetes:
- No SSH access
- fail2ban configured
- firewalld active
- Read-only root filesystem

## Monitoring

### Health Endpoint
```bash
curl http://localhost:8080/health
```

Returns:
```json
{
  "status": "ready",
  "uptime": 3600,
  "memoryUsage": {
    "used": 50331648,
    "total": 134217728,
    "percentage": 37.5
  },
  "toolCount": 11,
  "dependencies": {
    "python": true,
    "node": true,
    "git": true
  }
}
```

### Prometheus Metrics
```bash
curl http://localhost:8080/metrics
```

## Troubleshooting

### Connection Issues
1. Check server is running: `curl http://localhost:8080/health`
2. Verify `.mcp.json` configuration
3. Check firewall rules

### Tool Execution Errors
1. Ensure tools are installed in container
2. Check file paths are correct
3. Verify workspace volume is mounted

### Authentication Failures
1. Set `MCP_AUTH_TOKEN` environment variable
2. Include Bearer token in requests
3. Check token matches server configuration

## Advanced Usage

### Custom Tool Configuration

Tools are defined in `src/tools/index.ts`. To add a new tool:

```typescript
{
  name: 'custom-tool',
  description: 'Description for AI',
  category: 'linter',
  command: 'custom-command',
  args: ['--flag'],
  filePatterns: ['*.ext'],
  llmUsage: 'Use this to...'
}
```

### Scaling Considerations

- HPA scales 2-10 pods based on CPU/memory
- Each pod handles ~50 concurrent requests
- Use Redis for shared state if needed
- Consider CDN for static tool descriptions

## Integration Patterns

### CI/CD Pipeline
```yaml
validate:
  image: curlimages/curl:latest
  script:
    - |
      curl -X POST $MCP_SERVER_URL/rpc \
        -H "Authorization: Bearer $MCP_TOKEN" \
        -d '{
          "jsonrpc": "2.0",
          "method": "tools/call",
          "params": {
            "name": "gitlab-ci-validate",
            "arguments": {"files": [".gitlab-ci.yml"]}
          }
        }'
```

### Pre-commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-commit
curl -X POST http://localhost:8080/rpc \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"python-black","arguments":{"files":["*.py"],"fix":true}}}'
```

## Best Practices

1. **Security**: Always use HTTPS in production
2. **Authentication**: Enable bearer tokens for public endpoints
3. **Monitoring**: Set up alerts for health endpoint
4. **Scaling**: Use HPA for automatic scaling
5. **Updates**: Regularly update tool versions in container

## Support

- GitHub Issues: [Report bugs or request features]
- Documentation: [Full API documentation]
- Examples: See `examples/` directory