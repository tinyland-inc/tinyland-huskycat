"""
Git hooks setup command - configures git hooks for HuskyCat.

This command supports two modes:

1. **Tracked Hooks Mode** (.githooks/ directory):
   - For HuskyCat development (dogfooding)
   - Uses UV venv for execution
   - Hooks tracked in version control

2. **Binary-Managed Hooks Mode** (generated hooks):
   - For external users with binary installation
   - Auto-generates hooks to .git/hooks/
   - Binary-first execution with UV fallback
   - Auto-detects GitOps repositories

The mode is auto-selected based on whether .githooks/ directory exists.
"""

import logging
import subprocess
from pathlib import Path
from typing import Any

from ..core.base import BaseCommand, CommandResult, CommandStatus
from ..core.hook_generator import HookGenerator

logger = logging.getLogger(__name__)


class SetupHooksCommand(BaseCommand):
    """Configure git hooks for HuskyCat (tracked or binary-managed)."""

    @property
    def name(self) -> str:
        return "setup-hooks"

    @property
    def description(self) -> str:
        return "Configure git hooks for HuskyCat validation"

    def execute(self, **kwargs: Any) -> CommandResult:
        """
        Set up git hooks using appropriate mode.

        Modes:
        - Tracked hooks (.githooks/): If .githooks/ directory exists
        - Binary-managed hooks: Otherwise (generates to .git/hooks/)

        Args:
            **kwargs: Command arguments (force, regenerate, etc.)

        Returns:
            CommandResult with setup status
        """
        force = kwargs.get("force", False)
        regenerate = kwargs.get("regenerate", False)
        repo_path = Path.cwd()

        # Verify we're in a git repository
        if not (repo_path / ".git").exists():
            return CommandResult(
                status=CommandStatus.FAILED,
                message="Not in a git repository",
                errors=["Current directory is not a git repository"],
            )

        # Determine mode based on .githooks/ existence
        tracked_hooks_dir = repo_path / ".githooks"
        use_tracked_mode = tracked_hooks_dir.exists()

        if use_tracked_mode:
            logger.info("Using tracked hooks mode (.githooks/ directory)")
            return self._setup_tracked_hooks(repo_path, force)
        else:
            logger.info("Using binary-managed hooks mode (.git/hooks/ directory)")
            return self._setup_binary_hooks(repo_path, force or regenerate)

    def _setup_tracked_hooks(self, repo_path: Path, force: bool) -> CommandResult:
        """Set up tracked hooks in .githooks/ directory (original behavior).

        Args:
            repo_path: Path to repository
            force: Force reconfiguration

        Returns:
            CommandResult
        """
        hooks_dir = repo_path / ".githooks"
        git_dir = repo_path / ".git"

        # Check for required hook files
        required_hooks = ["pre-commit", "pre-push", "commit-msg"]
        missing_hooks = [h for h in required_hooks if not (hooks_dir / h).exists()]
        if missing_hooks:
            return CommandResult(
                status=CommandStatus.WARNING,
                message="Some hook files are missing",
                warnings=[f"Missing hook: .githooks/{h}" for h in missing_hooks],
            )

        # Check for common.sh utility
        common_sh = hooks_dir / "_" / "common.sh"
        if not common_sh.exists():
            return CommandResult(
                status=CommandStatus.FAILED,
                message="Shared utilities not found",
                errors=[
                    ".githooks/_/common.sh not found",
                    "This file is required for hooks to function",
                ],
            )

        # Set core.hooksPath to use tracked hooks
        try:
            subprocess.run(
                ["git", "config", "core.hooksPath", ".githooks"],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                message=f"Failed to configure git: {e}",
                errors=[str(e)],
            )

        # Verify hooks are executable
        non_executable = []
        for hook in required_hooks:
            hook_path = hooks_dir / hook
            if hook_path.exists() and not hook_path.stat().st_mode & 0o111:
                non_executable.append(hook)

        warnings = []
        if non_executable:
            warnings.append(
                f"Some hooks may not be executable: {', '.join(non_executable)}",
            )
            warnings.append("Run: chmod +x .githooks/*")

        # Check UV availability
        try:
            subprocess.run(
                ["uv", "--version"],
                check=True,
                capture_output=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            warnings.append("UV not found - required for hook execution")
            warnings.append("Install: curl -LsSf https://astral.sh/uv/install.sh | sh")
            warnings.append("Then run: uv sync --dev")

        # Check venv exists
        if not Path(".venv").exists():
            warnings.append("Virtual environment not found")
            warnings.append("Run: uv sync --dev")

        # Build available hooks list
        available_hooks = [
            f.name
            for f in hooks_dir.iterdir()
            if f.is_file() and not f.name.startswith(".") and f.name != "README.md"
        ]

        status = CommandStatus.WARNING if warnings else CommandStatus.SUCCESS

        return CommandResult(
            status=status,
            message="Git hooks configured to use .githooks/",
            warnings=warnings if warnings else None,
            data={
                "hooks_path": ".githooks",
                "git_dir": str(git_dir),
                "hooks_available": available_hooks,
                "requirements": [
                    "UV package manager must be installed",
                    "Virtual environment must be active (uv sync --dev)",
                    "See .githooks/README.md for full documentation",
                ],
                "mode": "tracked",
            },
        )

    def _setup_binary_hooks(self, repo_path: Path, force: bool) -> CommandResult:
        """Set up binary-managed hooks in .git/hooks/ directory.

        Args:
            repo_path: Path to repository
            force: Force overwrite existing hooks

        Returns:
            CommandResult
        """
        # Initialize hook generator
        generator = HookGenerator(repo_path)

        # Detect repository type
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

        logger.info("Repository analysis:")
        if features:
            logger.info(f"  Detected: {', '.join(features)}")
        else:
            logger.info("  No special features detected (standard code repo)")

        if is_gitops:
            logger.info("  🎯 GitOps repository - enabling IaC validation!")

        # Install hooks
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

        # Build warnings
        warnings = []
        if not generator.binary_path:
            warnings.append("Binary not detected - hooks will use UV fallback")
            warnings.append("For best performance, install binary: huskycat install")
        else:
            logger.info(f"Hooks will use binary: {generator.binary_path}")

        status = CommandStatus.WARNING if warnings else CommandStatus.SUCCESS

        return CommandResult(
            status=status,
            message=f"Git hooks installed successfully ({count} hooks)",
            warnings=warnings if warnings else None,
            data={
                "hooks_installed": count,
                "binary_path": (
                    str(generator.binary_path) if generator.binary_path else None
                ),
                "version": generator.version,
                "gitops_enabled": is_gitops,
                "features_detected": features,
                "mode": "binary-managed",
            },
        )
