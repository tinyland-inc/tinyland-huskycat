# MCP Server Hooks Integration for Claude

This document describes how the MCP server integrates with Claude hooks for comprehensive code validation.

## Overview

The MCP server provides HTTP API endpoints for validation tools. Claude hooks use these endpoints to validate files before and after editing, ensuring code quality throughout the development workflow.

## Architecture

```
┌─────────────┐     HTTP API      ┌──────────────┐
│   Claude    │ ◄──────────────► │  MCP Server  │
│    Hooks    │                   │  Port 8080   │
└─────────────┘                   └──────────────┘
      │                                   │
      │                                   ▼
      ▼                           ┌──────────────┐
┌─────────────┐                   │  Validation  │
│ Git Hooks   │                   │    Tools     │
│ Pre-commit  │                   │ Black, ESLint│
└─────────────┘                   └──────────────┘
```

## Claude Hooks

### Pre-File-Edit Hook

Located at `.claude/hooks/pre-file-edit`, this hook:

1. **Detects file type** being edited
2. **Validates current state** before Claude makes changes
3. **Warns about existing issues** that need fixing

Supported file types:
- `.gitlab-ci.yml` and `.gitlab/**/*.yml` - GitLab CI validation
- `values*.yml` - Helm values validation
- `*.py` - Notes for post-edit formatting
- `Dockerfile`/`ContainerFile` - Container validation

### Post-File-Edit Hook

Located at `.claude/hooks/post-file-edit`, this hook:

1. **Auto-formats code** using appropriate formatters
2. **Validates the changes** made by Claude
3. **Reports any remaining issues** that need manual fixing

Actions by file type:
- **Python**: Black formatting + Flake8 validation
- **JavaScript/TypeScript**: Prettier formatting + ESLint
- **GitLab CI**: Schema validation
- **Dockerfiles**: Hadolint validation
- **YAML**: yamllint validation

## MCP Server Integration

### Session Management

Each hook interaction creates a new session:

```bash
# Initialize session
curl -X POST http://localhost:8080/rpc \
  -H "X-Session-ID: unique-session-id" \
  -d '{
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {"protocolVersion": "2024-11-05"},
    "id": 1
  }'
```

### Tool Execution

Validation tools are called via the MCP protocol:

```bash
# Example: Validate GitLab CI file
curl -X POST http://localhost:8080/rpc \
  -H "X-Session-ID: session-id" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "gitlab-ci-validate",
      "arguments": {"files": [".gitlab-ci.yml"]}
    },
    "id": 2
  }'
```

## GitLab CI/CD Integration

### Auto DevOps Validation

The hooks specifically validate:
- `.gitlab-ci.yml` schema compliance
- `.gitlab/**/*.yml` CI templates
- `values*.yml` Helm chart values
- Kubernetes manifests in `k8s/` directories

### Pre-Push Validation

Before pushing to GitLab:
1. All CI files are validated against GitLab schema
2. Helm values are checked for YAML syntax
3. Container files are linted with Hadolint
4. Security scanning identifies exposed secrets

## Usage Examples

### 1. Editing GitLab CI File

When Claude edits `.gitlab-ci.yml`:
```
Pre-edit: Validates current file, warns about issues
Edit: Claude makes changes
Post-edit: Re-validates, reports any new issues
```

### 2. Creating Auto DevOps Pipeline

```yaml
# Claude creates this file
# Post-edit hook validates it automatically
include:
  - template: Auto-DevOps.gitlab-ci.yml

variables:
  POSTGRES_ENABLED: "true"
```

### 3. Python Development

```python
# Claude writes Python code
# Post-edit hook auto-formats with Black
# Then validates with Flake8
def process_data(input_data):
    return input_data.strip().lower()
```

## Benefits

1. **Immediate Feedback** - Issues caught during editing
2. **Auto-Formatting** - Consistent code style
3. **GitLab CI Safety** - No broken pipelines
4. **Security** - Secrets detected before commit
5. **AI-Assisted Fixes** - Claude can fix issues immediately

## Configuration

### Environment Variables

- `MCP_SERVER_URL` - MCP server endpoint (default: http://localhost:8080)
- `ENABLE_HOOKS` - Enable/disable hooks (default: true)

### Hook Installation

```bash
# Make hooks executable
chmod +x .claude/hooks/*

# Test hooks
.claude/hooks/pre-file-edit .gitlab-ci.yml
.claude/hooks/post-file-edit .gitlab-ci.yml
```

## Troubleshooting

### MCP Server Not Available

If the MCP server is down, hooks gracefully degrade:
- Exit with code 0 (success)
- Don't block Claude's operations
- Log warnings for manual review

### Session Issues

Each hook creates a new session to avoid conflicts:
- Sessions are short-lived
- No state carried between edits
- Clean initialization each time

### Validation Failures

When validation fails:
- Pre-edit: Shows warnings but allows editing
- Post-edit: Shows errors that need fixing
- Never blocks Claude from saving files

## Summary

The MCP server integration with Claude hooks provides:
- ✅ Automatic validation during AI-assisted development
- ✅ GitLab CI/CD pipeline safety
- ✅ Consistent code formatting
- ✅ Security scanning
- ✅ Immediate feedback loop

This ensures high-quality code whether edited by humans or AI assistants.