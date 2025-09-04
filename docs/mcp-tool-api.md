# HuskyCats MCP Server - Tool API Documentation

## Overview

The HuskyCats MCP Server provides a comprehensive set of validation and code quality tools accessible via the Model Context Protocol (MCP). This document details all available tools, their parameters, and usage examples for IDE and agent integration.

## Connection Configuration

### Stdio Mode (Local)
```json
{
  "mcpServers": {
    "huskycats-validator": {
      "command": "node",
      "args": ["mcp-server/dist/index.js"],
      "type": "stdio",
      "env": {
        "NODE_ENV": "production",
        "MCP_PORT": "8080"
      }
    }
  }
}
```

### HTTP Mode (Remote)
```json
{
  "mcpServers": {
    "huskycats-http": {
      "url": "http://localhost:8080/rpc",
      "type": "http",
      "authentication": {
        "type": "bearer",
        "token": "YOUR_AUTH_TOKEN"
      }
    }
  }
}
```

## MCP Protocol Methods

### 1. Initialize Session
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {
      "name": "your-client",
      "version": "1.0.0"
    }
  }
}
```

### 2. List Available Tools
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list"
}
```

### 3. Call a Tool
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "tool-name",
    "arguments": {
      // Tool-specific arguments
    }
  }
}
```

## Available Tools

### Python Validation Tools

#### python-black
Format Python code using Black formatter.

**Parameters:**
- `files` (array, required): Python files to format
- `fix` (boolean, optional): Apply fixes automatically (default: false)

**Example:**
```json
{
  "name": "python-black",
  "arguments": {
    "files": ["src/main.py", "src/utils.py"],
    "fix": true
  }
}
```

#### python-flake8
Lint Python code for style and errors.

**Parameters:**
- `files` (array, required): Python files to lint

**Example:**
```json
{
  "name": "python-flake8",
  "arguments": {
    "files": ["src/**/*.py"]
  }
}
```

#### python-mypy
Type check Python code.

**Parameters:**
- `files` (array, required): Python files to type check

**Example:**
```json
{
  "name": "python-mypy",
  "arguments": {
    "files": ["src/models.py"]
  }
}
```

#### python-bandit
Security linter for Python.

**Parameters:**
- `files` (array, required): Python files to scan for security issues

**Example:**
```json
{
  "name": "python-bandit",
  "arguments": {
    "files": ["src/**/*.py"]
  }
}
```

### JavaScript/TypeScript Tools

#### js-eslint
Lint JavaScript/TypeScript code.

**Parameters:**
- `files` (array, required): JS/TS files to lint
- `fix` (boolean, optional): Apply fixes automatically (default: false)

**Example:**
```json
{
  "name": "js-eslint",
  "arguments": {
    "files": ["src/**/*.ts", "src/**/*.tsx"],
    "fix": true
  }
}
```

#### js-prettier
Format JavaScript/TypeScript code.

**Parameters:**
- `files` (array, required): JS/TS files to format
- `fix` (boolean, optional): Apply formatting automatically (default: false)

**Example:**
```json
{
  "name": "js-prettier",
  "arguments": {
    "files": ["src/**/*.js"],
    "fix": true
  }
}
```

### Shell Script Tools

#### shell-shellcheck
Lint shell scripts.

**Parameters:**
- `files` (array, required): Shell scripts to lint

**Example:**
```json
{
  "name": "shell-shellcheck",
  "arguments": {
    "files": ["scripts/*.sh"]
  }
}
```

### Docker Tools

#### docker-hadolint
Lint Dockerfiles.

**Parameters:**
- `files` (array, required): Dockerfiles to lint

**Example:**
```json
{
  "name": "docker-hadolint",
  "arguments": {
    "files": ["Dockerfile", "ContainerFile"]
  }
}
```

### YAML Tools

#### yaml-yamllint
Lint YAML files.

**Parameters:**
- `files` (array, required): YAML files to lint

**Example:**
```json
{
  "name": "yaml-yamllint",
  "arguments": {
    "files": ["**/*.yml", "**/*.yaml"]
  }
}
```

### GitLab CI Tools

#### gitlab-ci-validate
Validate GitLab CI configuration.

**Parameters:**
- `files` (array, required): GitLab CI files to validate

**Example:**
```json
{
  "name": "gitlab-ci-validate",
  "arguments": {
    "files": [".gitlab-ci.yml"]
  }
}
```

### Project-Wide Tools

#### validate_project
Validate entire project with all applicable tools.

**Parameters:**
- `directory` (string, optional): Project directory to validate (default: ".")
- `exclude` (array, optional): Patterns to exclude (default: ["node_modules/**", ".git/**", "dist/**"])
- `parallel` (boolean, optional): Run validations in parallel (default: true)
- `fixIssues` (boolean, optional): Automatically fix issues where possible (default: false)

**Example:**
```json
{
  "name": "validate_project",
  "arguments": {
    "directory": ".",
    "exclude": ["node_modules/**", "build/**"],
    "parallel": true,
    "fixIssues": false
  }
}
```

#### batch_validate
Validate multiple files with specified tools.

**Parameters:**
- `files` (array, required): Files to validate
- `tools` (array, required): Tools to use for validation
- `parallel` (boolean, optional): Run in parallel (default: true)

**Example:**
```json
{
  "name": "batch_validate",
  "arguments": {
    "files": ["src/**/*.py", "src/**/*.js"],
    "tools": ["python-black", "js-prettier"],
    "parallel": true
  }
}
```

### Security Tools

#### security_secrets_scan
Scan for exposed secrets and credentials.

**Parameters:**
- `directory` (string, optional): Directory to scan (default: ".")
- `exclude` (array, optional): Patterns to exclude

**Example:**
```json
{
  "name": "security_secrets_scan",
  "arguments": {
    "directory": ".",
    "exclude": [".git/**", "node_modules/**"]
  }
}
```

#### security_dependency_audit
Audit dependencies for vulnerabilities.

**Parameters:**
- `packageFile` (string, required): Package file to audit (package.json, requirements.txt, etc.)

**Example:**
```json
{
  "name": "security_dependency_audit",
  "arguments": {
    "packageFile": "package.json"
  }
}
```

### Validation Queue Tools

#### queue_validation
Queue repository for validation.

**Parameters:**
- `repository` (string, required): Repository URL
- `branch` (string, optional): Branch to validate (default: "main")
- `tools` (array, optional): Tools to use

**Example:**
```json
{
  "name": "queue_validation",
  "arguments": {
    "repository": "https://github.com/user/repo",
    "branch": "develop",
    "tools": ["python-black", "python-flake8"]
  }
}
```

#### queue_status
Get validation queue status.

**Parameters:**
- `jobId` (string, optional): Specific job ID to check

**Example:**
```json
{
  "name": "queue_status",
  "arguments": {
    "jobId": "job-123456"
  }
}
```

### Syncthing Integration Tools

#### syncthing_list_repos
List synchronized repositories.

**Parameters:** None

**Example:**
```json
{
  "name": "syncthing_list_repos",
  "arguments": {}
}
```

#### syncthing_add_repo
Add repository for synchronization.

**Parameters:**
- `repository` (string, required): Repository name
- `path` (string, required): Local path for repository

**Example:**
```json
{
  "name": "syncthing_add_repo",
  "arguments": {
    "repository": "my-project",
    "path": "/workspace/my-project"
  }
}
```

#### syncthing_sync_status
Get synchronization status.

**Parameters:**
- `repository` (string, optional): Repository to check

**Example:**
```json
{
  "name": "syncthing_sync_status",
  "arguments": {
    "repository": "my-project"
  }
}
```

### Container Management Tools

#### container_list
List all containers managed by Podman.

**Parameters:**
- `all` (boolean, optional): Include stopped containers (default: false)

**Example:**
```json
{
  "name": "container_list",
  "arguments": {
    "all": true
  }
}
```

#### container_inspect
Get detailed information about a specific container.

**Parameters:**
- `container` (string, required): Container ID or name

**Example:**
```json
{
  "name": "container_inspect",
  "arguments": {
    "container": "huskycats-mcp-server"
  }
}
```

#### container_logs
Get container logs.

**Parameters:**
- `container` (string, required): Container ID or name
- `tail` (number, optional): Number of lines to show (default: 100)

**Example:**
```json
{
  "name": "container_logs",
  "arguments": {
    "container": "huskycats-mcp-server",
    "tail": 50
  }
}
```

## Resources

The MCP server provides access to various resources:

### List Resources
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "resources/list"
}
```

### Read Resource
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "resources/read",
  "params": {
    "uri": "validation://report/latest"
  }
}
```

### Available Resources

1. **validation://report/latest** - Latest validation report
2. **validation://queue/status** - Current validation queue status
3. **validation://tools/available** - List of all available validation tools
4. **container://logs/mcp-server** - MCP server container logs
5. **syncthing://status** - Syncthing synchronization status

## Prompts

Pre-configured prompts for common tasks:

### List Prompts
```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "method": "prompts/list"
}
```

### Get Prompt
```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "prompts/get",
  "params": {
    "name": "validate_codebase",
    "arguments": {
      "directory": "/path/to/project"
    }
  }
}
```

### Available Prompts

1. **validate_codebase** - Validate an entire codebase
2. **fix_python_issues** - Fix Python code issues automatically
3. **security_audit** - Perform security audit

## Batch Operations

The server supports batch requests for improved performance:

```json
[
  {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  },
  {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "resources/list"
  },
  {
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "python-black",
      "arguments": {
        "files": ["test.py"]
      }
    }
  }
]
```

## Error Handling

All errors follow the JSON-RPC 2.0 error format:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32601,
    "message": "Method not found",
    "data": {
      "method": "unknown/method"
    }
  }
}
```

### Error Codes
- `-32700`: Parse error
- `-32600`: Invalid request
- `-32601`: Method not found
- `-32602`: Invalid params
- `-32603`: Internal error

## Authentication

For HTTP mode, include the Bearer token in the Authorization header:

```http
POST /rpc HTTP/1.1
Host: localhost:8080
Content-Type: application/json
Authorization: Bearer YOUR_AUTH_TOKEN

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

## IDE Integration Examples

### Visual Studio Code Extension
```typescript
import { MCPClient } from '@modelcontextprotocol/sdk';

const client = new MCPClient({
  url: 'http://localhost:8080/rpc',
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN'
  }
});

// Initialize
await client.initialize({
  protocolVersion: '2024-11-05',
  capabilities: {},
  clientInfo: {
    name: 'vscode-huskycat',
    version: '1.0.0'
  }
});

// List tools
const tools = await client.listTools();

// Call a tool
const result = await client.callTool({
  name: 'python-black',
  arguments: {
    files: ['main.py'],
    fix: true
  }
});
```

### IntelliJ IDEA Plugin
```java
import com.modelcontextprotocol.MCPClient;

MCPClient client = new MCPClient("http://localhost:8080/rpc");
client.setAuthToken("YOUR_TOKEN");

// Initialize
InitializeResponse response = client.initialize(
    "2024-11-05",
    new ClientInfo("intellij-huskycat", "1.0.0")
);

// List tools
ToolsResponse tools = client.listTools();

// Call a tool
ToolResult result = client.callTool(
    "python-black",
    Map.of("files", List.of("main.py"), "fix", true)
);
```

### Python Client
```python
import requests

class MCPClient:
    def __init__(self, url, token):
        self.url = url
        self.token = token
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        self.request_id = 0
    
    def call(self, method, params=None):
        self.request_id += 1
        payload = {
            'jsonrpc': '2.0',
            'id': self.request_id,
            'method': method,
            'params': params or {}
        }
        response = requests.post(self.url, json=payload, headers=self.headers)
        return response.json()

# Usage
client = MCPClient('http://localhost:8080/rpc', 'YOUR_TOKEN')

# Initialize
client.call('initialize', {
    'protocolVersion': '2024-11-05',
    'capabilities': {},
    'clientInfo': {
        'name': 'python-client',
        'version': '1.0.0'
    }
})

# List tools
tools = client.call('tools/list')

# Call a tool
result = client.call('tools/call', {
    'name': 'python-black',
    'arguments': {
        'files': ['main.py'],
        'fix': True
    }
})
```

## Performance Considerations

1. **Batch Operations**: Use batch requests when calling multiple tools
2. **Parallel Execution**: Enable `parallel: true` for project-wide validations
3. **Resource Caching**: Resources are cached for 5 minutes by default
4. **Connection Pooling**: Reuse HTTP connections for multiple requests
5. **Timeout Configuration**: Default timeout is 30 seconds per tool

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Verify Bearer token is correct
   - Check token is properly configured in environment

2. **Tool Not Found**
   - Ensure tool name is spelled correctly
   - Check tool is installed in container

3. **File Not Found**
   - Use absolute paths or paths relative to workspace
   - Verify file exists before calling tool

4. **Timeout Errors**
   - Increase timeout for large files
   - Use batch operations for better performance

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=debug
export MCP_DEBUG=true
```

### Health Check

Check server health:
```bash
curl http://localhost:8080/health
```

## Support

- GitHub Issues: https://github.com/huskycats/huskycats-bates/issues
- Documentation: https://github.com/huskycats/huskycats-bates/docs
- MCP Specification: https://modelcontextprotocol.org