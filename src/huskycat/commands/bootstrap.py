"""
Bootstrap command for Claude Code integration.
Non-destructively sets up .mcp.json and .claude/ configuration.
"""

import json
from pathlib import Path
from typing import Dict, Any

from ..core.base import BaseCommand, CommandResult, CommandStatus


class BootstrapCommand(BaseCommand):
    """Command to bootstrap Claude Code MCP integration."""

    @property
    def name(self) -> str:
        return "bootstrap"

    @property
    def description(self) -> str:
        return "Bootstrap Claude Code MCP integration"

    def execute(self, force: bool = False) -> CommandResult:
        """
        Bootstrap Claude Code integration files.

        Args:
            force: Overwrite existing configuration files

        Returns:
            CommandResult with bootstrap status
        """
        try:
            results = []
            warnings = []

            # Bootstrap .mcp.json
            mcp_result = self._bootstrap_mcp_json(force)
            results.append(mcp_result)

            # Bootstrap .claude/commands/
            claude_result = self._bootstrap_claude_commands(force)
            results.append(claude_result)

            # Determine overall status
            success_count = sum(1 for r in results if r["success"])
            if success_count == len(results):
                status = CommandStatus.SUCCESS
                message = "Claude Code integration bootstrapped successfully"
            elif success_count > 0:
                status = CommandStatus.WARNING
                message = f"Partial bootstrap success ({success_count}/{len(results)})"
                warnings.extend([r["message"] for r in results if not r["success"]])
            else:
                status = CommandStatus.FAILED
                message = "Bootstrap failed"

            return CommandResult(
                status=status,
                message=message,
                warnings=warnings,
                data={"results": results},
            )

        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                message=f"Bootstrap error: {str(e)}",
                errors=[str(e)],
            )

    def _bootstrap_mcp_json(self, force: bool) -> Dict[str, Any]:
        """Bootstrap .mcp.json configuration for Claude Code."""
        mcp_path = Path(".mcp.json")

        try:
            # Check if file exists
            if mcp_path.exists() and not force:
                # Non-destructive: merge with existing
                with open(mcp_path, "r") as f:
                    existing_config = json.load(f)
            else:
                existing_config = {}

            # Ensure mcpServers section exists
            if "mcpServers" not in existing_config:
                existing_config["mcpServers"] = {}

            # Get binary path (prefer local binary, fallback to PATH)
            binary_path = "./dist/huskycat"
            if not Path(binary_path).exists():
                binary_path = "huskycat"

            # Add HuskyCat MCP server configuration
            huskycat_config = {
                "command": binary_path,
                "args": ["mcp-server"],
                "env": {},
            }

            # Non-destructive update
            if "huskycat" not in existing_config["mcpServers"] or force:
                existing_config["mcpServers"]["huskycat"] = huskycat_config

                # Write updated configuration
                with open(mcp_path, "w") as f:
                    json.dump(existing_config, f, indent=2)

                return {
                    "success": True,
                    "message": f"Updated .mcp.json with HuskyCat server configuration",
                    "file": str(mcp_path),
                }
            else:
                return {
                    "success": True,
                    "message": f"HuskyCat already configured in .mcp.json (use --force to overwrite)",
                    "file": str(mcp_path),
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to bootstrap .mcp.json: {str(e)}",
                "file": str(mcp_path),
            }

    def _bootstrap_claude_commands(self, force: bool) -> Dict[str, Any]:
        """Bootstrap .claude/commands/ directory with HuskyCat validation commands."""
        claude_dir = Path(".claude/commands")

        try:
            # Create directory if it doesn't exist
            claude_dir.mkdir(parents=True, exist_ok=True)

            # Define HuskyCat-specific commands
            commands = self._get_huskycat_commands()
            created_files = []
            skipped_files = []

            for cmd_name, cmd_content in commands.items():
                cmd_file = claude_dir / f"{cmd_name}.md"

                if not cmd_file.exists() or force:
                    with open(cmd_file, "w") as f:
                        f.write(cmd_content)
                    created_files.append(str(cmd_file))
                else:
                    skipped_files.append(str(cmd_file))

            message_parts = []
            if created_files:
                message_parts.append(f"Created {len(created_files)} command files")
            if skipped_files:
                message_parts.append(f"Skipped {len(skipped_files)} existing files")

            return {
                "success": True,
                "message": f"Bootstrapped .claude/commands/: {', '.join(message_parts)}",
                "created": created_files,
                "skipped": skipped_files,
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to bootstrap .claude/commands/: {str(e)}",
            }

    def _get_huskycat_commands(self) -> Dict[str, str]:
        """Get HuskyCat-specific Claude commands."""

        # Get binary path (prefer local binary)
        binary_path = (
            "./dist/huskycat" if Path("./dist/huskycat").exists() else "huskycat"
        )

        return {
            "validate": f"""# HuskyCat Code Validation

Validate code files using HuskyCat's comprehensive validation suite with binary-first, container-extensible execution.

## Usage

Run validation on the specified files or directories:

```bash
{binary_path} validate $ARGUMENTS
```

## Features

- **Binary-first execution**: Fast local validation using available tools
- **Container fallback**: Comprehensive toolchain via container when needed  
- **Multi-language support**: Python, YAML, Shell, Docker, GitLab CI
- **Auto-fix capabilities**: Automatically fix issues where possible

## Examples

- Validate current directory: `validate .`
- Validate specific file: `validate src/main.py` 
- Validate with auto-fix: `validate --fix src/`
- Validate staged files: `validate --staged`

## Available Validators

- **black**: Python code formatter
- **autoflake**: Remove unused imports and variables  
- **flake8**: Python linting (style, complexity, errors)
- **mypy**: Python type checking
- **yamllint**: YAML file validation
- **hadolint**: Dockerfile linting
- **shellcheck**: Shell script analysis
- **gitlab-ci**: GitLab CI/CD configuration validation
""",
            "ci-validate": f"""# HuskyCat CI Configuration Validation

Validate CI/CD configuration files with comprehensive schema checking and pipeline analysis.

## Usage

Validate CI configuration files:

```bash
{binary_path} ci-validate $ARGUMENTS
```

## Supported Formats

- **GitLab CI**: `.gitlab-ci.yml` schema validation and pipeline testing
- **GitHub Actions**: Workflow validation
- **Docker Compose**: Service configuration validation  
- **Kubernetes**: Manifest validation

## Features

- **Schema validation**: Checks against official CI schemas
- **Pipeline testing**: Validates pipeline structure and dependencies
- **Security analysis**: Identifies potential security issues
- **Best practices**: Enforces CI/CD best practices

## Examples

- Validate GitLab CI: `ci-validate .gitlab-ci.yml`
- Validate all CI files: `ci-validate .`
""",
            "setup-hooks": f"""# HuskyCat Git Hooks Setup

Install HuskyCat git hooks for automatic validation on commits and pushes.

## Usage

Setup git hooks with binary-first, container-fallback paradigm:

```bash
{binary_path} setup-hooks
```

## Features

- **Binary-first execution**: Uses local binary when available
- **Container fallback**: Falls back to container for comprehensive validation
- **Universal compatibility**: Works in any directory with proper fallback
- **Non-destructive**: Preserves existing hooks where possible

## Hook Types

- **pre-commit**: Validates staged files before commit
- **pre-push**: Validates all changes before push
- **commit-msg**: Validates commit message format

## Examples

- Install hooks: `setup-hooks`
- Force overwrite: `setup-hooks --force`
""",
            "auto-devops": f"""# HuskyCat Auto-DevOps Validation

Validate Auto-DevOps Helm charts and Kubernetes manifests for GitLab integration.

## Usage

Validate Auto-DevOps configurations:

```bash
{binary_path} auto-devops $ARGUMENTS
```

## Features

- **Helm chart validation**: Validates chart structure and templates
- **Kubernetes manifest validation**: Checks manifest syntax and best practices  
- **Auto-DevOps simulation**: Simulates deployment pipeline
- **Security scanning**: Identifies potential security issues

## Examples

- Validate current project: `auto-devops .`
- Skip Helm validation: `auto-devops --no-helm`
- Simulate deployment: `auto-devops --simulate`
- Strict mode: `auto-devops --strict`
""",
        }
