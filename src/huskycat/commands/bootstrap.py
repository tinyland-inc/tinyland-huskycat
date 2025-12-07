"""
Bootstrap command for HuskyCat integration.

Supports two bootstrap modes:
1. Git Hooks Bootstrap: Sets up git hooks for code validation (default)
2. MCP Bootstrap: Sets up Claude Code MCP integration (with --mcp flag)

The command auto-detects repository type and configures appropriate validations.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

from ..core.base import BaseCommand, CommandResult, CommandStatus
from ..core.hook_generator import HookGenerator

logger = logging.getLogger(__name__)


class BootstrapCommand(BaseCommand):
    """Command to bootstrap HuskyCat (Git Hooks or MCP integration)."""

    @property
    def name(self) -> str:
        return "bootstrap"

    @property
    def description(self) -> str:
        return "Bootstrap HuskyCat with git hooks and GitOps validation"

    def execute(
        self,
        force: bool = False,
        mcp: bool = False,
        skip_install: bool = False,
    ) -> CommandResult:
        """
        Bootstrap HuskyCat for repository.

        Args:
            force: Overwrite existing configuration files
            mcp: Bootstrap MCP integration instead of git hooks
            skip_install: Skip binary installation (hooks only)

        Returns:
            CommandResult with bootstrap status
        """
        # Choose bootstrap mode
        if mcp:
            return self._bootstrap_mcp_integration(force)
        else:
            return self._bootstrap_gitops_hooks(force, skip_install)

    def _bootstrap_gitops_hooks(self, force: bool, skip_install: bool) -> CommandResult:
        """Bootstrap git hooks and GitOps validation.

        Args:
            force: Force overwrite existing hooks
            skip_install: Skip binary installation

        Returns:
            CommandResult
        """
        logger.info("🚀 Bootstrapping HuskyCat...")

        repo_path = Path.cwd()

        # Step 1: Check if in git repository
        if not (repo_path / ".git").exists():
            return CommandResult(
                status=CommandStatus.FAILED,
                message="Not a git repository",
                errors=[
                    "Current directory is not a git repository",
                    "Hint: Run 'git init' first",
                ],
            )

        # Step 2: Detect repository type
        logger.info("Step 1: Analyzing repository...")
        generator = HookGenerator(repo_path)
        repo_info = generator.detect_repo_type()
        is_gitops = repo_info["gitops"]

        # Report findings
        features = []
        if repo_info["gitlab_ci"]:
            features.append("GitLab CI")
        if repo_info["github_actions"]:
            features.append("GitHub Actions")
        if repo_info["helm_chart"]:
            features.append("Helm")
        if repo_info["k8s_manifests"]:
            features.append("Kubernetes")
        if repo_info["terraform"]:
            features.append("Terraform")
        if repo_info["ansible"]:
            features.append("Ansible")

        logger.info("Repository type detection:")
        if features:
            logger.info(f"  Detected: {', '.join(features)}")
        else:
            logger.info("  No special features detected (standard code repo)")

        if is_gitops:
            logger.info("  🎯 GitOps repository - enabling IaC validation!")

        # Step 3: Install git hooks
        logger.info("Step 2: Setting up git hooks...")

        try:
            count = generator.install_all_hooks(force=force)
        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                message=f"Failed to install hooks: {e}",
                errors=[str(e)],
            )

        if count == 0:
            return CommandResult(
                status=CommandStatus.WARNING,
                message="No hooks were installed (use --force to overwrite)",
                warnings=["Hooks may already exist - use --force to regenerate"],
            )

        # Step 4: Success message
        logger.info("")
        logger.info("✅ Bootstrap complete!")
        logger.info("")
        logger.info("HuskyCat is now configured for:")

        if repo_info["gitlab_ci"]:
            logger.info("  ✓ GitLab CI validation (pre-push)")
        if is_gitops:
            logger.info("  ✓ Auto-DevOps validation (pre-push)")
            if repo_info["helm_chart"]:
                logger.info("    - Helm chart validation")
            if repo_info["k8s_manifests"]:
                logger.info("    - Kubernetes manifest validation")
        if repo_info["terraform"]:
            logger.info("  ✓ Terraform formatting (pre-commit)")
        if repo_info["ansible"]:
            logger.info("  ✓ Ansible linting (pre-commit)")

        logger.info("")
        logger.info("Try it out:")
        logger.info("  git add . && git commit -m 'test: HuskyCat validation'")

        # Build warnings
        warnings = []
        if not generator.binary_path:
            warnings.append("Binary not detected - hooks will use UV fallback")
            warnings.append("For best performance, install binary: huskycat install")

        status = CommandStatus.WARNING if warnings else CommandStatus.SUCCESS

        return CommandResult(
            status=status,
            message=f"✅ Bootstrap complete ({count} hooks installed)",
            warnings=warnings if warnings else None,
            data={
                "hooks_installed": count,
                "binary_path": (
                    str(generator.binary_path) if generator.binary_path else None
                ),
                "gitops_enabled": is_gitops,
                "features_detected": features,
            },
        )

    def _bootstrap_mcp_integration(self, force: bool) -> CommandResult:
        """Bootstrap MCP integration for Claude Code.

        Args:
            force: Force overwrite existing configuration

        Returns:
            CommandResult
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
                data={"results": results, "mode": "mcp"},
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
