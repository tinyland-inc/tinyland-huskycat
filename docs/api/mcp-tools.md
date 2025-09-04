# MCP Tools API Reference

This document provides detailed API specifications for all MCP tools exposed by HuskyCat's MCP server.

## Tool Discovery

The MCP server exposes tools through the standard `tools/list` method.

### Request
```json
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "id": 1
}
```

### Response
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "validate",
        "description": "Validate code files with appropriate linters",
        "inputSchema": {
          "type": "object",
          "properties": {
            "path": {
              "type": "string",
              "description": "File or directory path to validate"
            },
            "fix": {
              "type": "boolean",
              "description": "Auto-fix issues where possible",
              "default": false
            }
          },
          "required": ["path"]
        }
      }
      // ... other tools
    ]
  }
}
```

## Core Tools

### `validate`

Universal validation tool that runs all applicable validators on the specified path.

#### Input Schema
```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "File or directory path to validate"
    },
    "fix": {
      "type": "boolean",
      "description": "Auto-fix issues where possible",
      "default": false
    }
  },
  "required": ["path"]
}
```

#### Example Request
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "validate",
    "arguments": {
      "path": "src/",
      "fix": true
    }
  },
  "id": 2
}
```

#### Example Response
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\n  \"summary\": {\n    \"total_files\": 5,\n    \"passed_files\": 4,\n    \"failed_files\": 1,\n    \"total_errors\": 2,\n    \"total_warnings\": 1,\n    \"failed_file_list\": [\"src/main.py\"],\n    \"success\": false\n  },\n  \"results\": {\n    \"src/main.py\": [\n      {\n        \"tool\": \"black\",\n        \"filepath\": \"src/main.py\",\n        \"success\": false,\n        \"messages\": [\"reformatted src/main.py\"],\n        \"errors\": [],\n        \"warnings\": [],\n        \"fixed\": true,\n        \"duration_ms\": 45\n      }\n    ]\n  }\n}"
      }
    ]
  }
}
```

### `validate_staged`

Validates files that are staged for Git commit.

#### Input Schema
```json
{
  "type": "object",
  "properties": {
    "fix": {
      "type": "boolean",
      "description": "Auto-fix issues where possible",
      "default": false
    }
  }
}
```

#### Example Request
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "validate_staged",
    "arguments": {
      "fix": false
    }
  },
  "id": 3
}
```

## Individual Validator Tools

Each validator is exposed as a separate tool for targeted validation.

### `validate_black`

Python code formatter using Black.

#### Input Schema
```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Python file path to format"
    },
    "fix": {
      "type": "boolean",
      "description": "Apply Black formatting",
      "default": false
    }
  },
  "required": ["path"]
}
```

### `validate_flake8`

Python linter using Flake8.

#### Input Schema
```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Python file path to lint"
    },
    "fix": {
      "type": "boolean",
      "description": "Auto-fix issues where possible",
      "default": false
    }
  },
  "required": ["path"]
}
```

### `validate_mypy`

Python type checker using MyPy.

#### Input Schema
```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Python file path to type check"
    },
    "fix": {
      "type": "boolean",
      "description": "Auto-fix issues where possible",
      "default": false
    }
  },
  "required": ["path"]
}
```

### `validate_eslint`

JavaScript/TypeScript linter using ESLint.

#### Input Schema
```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "JavaScript/TypeScript file path to lint"
    },
    "fix": {
      "type": "boolean",
      "description": "Apply ESLint fixes",
      "default": false
    }
  },
  "required": ["path"]
}
```

### `validate_yamllint`

YAML validator using yamllint.

#### Input Schema
```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "YAML file path to validate"
    },
    "fix": {
      "type": "boolean",
      "description": "Auto-fix issues where possible",
      "default": false
    }
  },
  "required": ["path"]
}
```

### `validate_hadolint`

Dockerfile/ContainerFile linter using hadolint.

#### Input Schema
```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Dockerfile path to validate"
    },
    "fix": {
      "type": "boolean",
      "description": "Auto-fix issues where possible",
      "default": false
    }
  },
  "required": ["path"]
}
```

### `validate_shellcheck`

Shell script validator using shellcheck.

#### Input Schema
```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Shell script path to validate"
    },
    "fix": {
      "type": "boolean",
      "description": "Auto-fix issues where possible",
      "default": false
    }
  },
  "required": ["path"]
}
```

## Response Format

All tools return responses in the same format:

### Success Response
```json
{
  "jsonrpc": "2.0",
  "id": "<request_id>",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "<JSON_formatted_results>"
      }
    ]
  }
}
```

### Error Response
```json
{
  "jsonrpc": "2.0",
  "id": "<request_id>",
  "error": {
    "code": -32603,
    "message": "Internal error: <error_description>"
  }
}
```

## Result Objects

### ValidationResult

Individual validation results are returned as `ValidationResult` objects:

```json
{
  "tool": "black",
  "filepath": "src/main.py",
  "success": true,
  "messages": ["File is properly formatted"],
  "errors": [],
  "warnings": [],
  "fixed": false,
  "duration_ms": 42
}
```

#### Fields

- `tool`: Name of the validator that produced this result
- `filepath`: Path to the validated file
- `success`: Whether validation passed (no errors)
- `messages`: General messages from the validator
- `errors`: List of error messages (validation failures)
- `warnings`: List of warning messages (non-blocking issues)
- `fixed`: Whether auto-fixes were applied
- `duration_ms`: Time taken for validation in milliseconds

### Summary Object

Aggregate summary of all validation results:

```json
{
  "total_files": 5,
  "passed_files": 4,
  "failed_files": 1,
  "total_errors": 2,
  "total_warnings": 1,
  "failed_file_list": ["src/main.py"],
  "success": false
}
```

#### Fields

- `total_files`: Total number of files validated
- `passed_files`: Number of files that passed all validators
- `failed_files`: Number of files with at least one validation error
- `total_errors`: Total count of all errors across all files
- `total_warnings`: Total count of all warnings across all files
- `failed_file_list`: List of file paths that have validation errors
- `success`: Overall validation status (true if no files failed)

## Error Codes

The MCP server uses standard JSON-RPC error codes:

| Code | Meaning | Description |
|------|---------|-------------|
| -32700 | Parse error | Invalid JSON was received |
| -32600 | Invalid Request | The JSON sent is not a valid Request object |
| -32601 | Method not found | The method does not exist / is not available |
| -32602 | Invalid params | Invalid method parameter(s) |
| -32603 | Internal error | Internal JSON-RPC error |

## Rate Limiting

The MCP server does not implement rate limiting, but individual validators may have their own performance characteristics:

- **Fast validators** (< 100ms): Black, yamllint, shellcheck
- **Medium validators** (100-500ms): Flake8, ESLint
- **Slow validators** (> 500ms): MyPy (especially on large codebases)

## Debugging

### Enable Debug Logging

Set the environment variable before starting the MCP server:

```bash
HUSKYCAT_LOG_LEVEL=DEBUG huskycat mcp-server
```

### Manual Testing

You can test the MCP server manually using stdin/stdout:

```bash
# Start the server
huskycat mcp-server

# Send initialization request
echo '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}'

# List tools
echo '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":2}'

# Call a tool
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"validate","arguments":{"path":"."}},"id":3}'
```

---

For more information about MCP integration, see the [MCP Server Guide](../features/mcp-server.md).