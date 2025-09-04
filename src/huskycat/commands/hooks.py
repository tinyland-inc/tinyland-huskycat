"""
Git hooks setup command.
"""

import subprocess
from pathlib import Path

from ..core.base import BaseCommand, CommandResult, CommandStatus


class SetupHooksCommand(BaseCommand):
    """Command to setup git hooks for automatic validation."""

    @property
    def name(self) -> str:
        return "setup-hooks"

    @property
    def description(self) -> str:
        return "Setup git hooks for automatic validation"

    def execute(self, force: bool = False) -> CommandResult:
        """
        Setup git hooks.

        Args:
            force: Force overwrite existing hooks

        Returns:
            CommandResult with setup status
        """
        # Find git directory
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                check=True,
            )
            git_dir = Path(result.stdout.strip())
        except subprocess.CalledProcessError:
            return CommandResult(
                status=CommandStatus.FAILED,
                message="Not in a git repository",
                errors=["Current directory is not a git repository"],
            )

        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir(exist_ok=True)

        # Get absolute path to main module
        main_module_path = Path(__file__).parent.parent / "__main__.py"

        # Create pre-commit hook
        pre_commit = hooks_dir / "pre-commit"
        pre_commit_content = f"""#!/bin/bash
# HuskyCat pre-commit hook
# Validates staged files before commit

python3 {main_module_path.absolute()} validate --staged
exit $?
"""

        if pre_commit.exists() and not force:
            return CommandResult(
                status=CommandStatus.WARNING,
                message="Pre-commit hook already exists",
                warnings=["Use --force to overwrite existing hooks"],
            )

        pre_commit.write_text(pre_commit_content)
        pre_commit.chmod(0o755)

        # Create pre-push hook
        pre_push = hooks_dir / "pre-push"
        pre_push_content = f"""#!/bin/bash
# HuskyCat pre-push hook
# Validates all changes before push

python3 {main_module_path.absolute()} ci-validate
exit $?
"""

        pre_push.write_text(pre_push_content)
        pre_push.chmod(0o755)

        # Create commit-msg hook for conventional commits
        commit_msg = hooks_dir / "commit-msg"
        commit_msg_content = f"""#!/bin/bash
# HuskyCat commit-msg hook
# Validates commit message format

python3 {main_module_path.absolute()} validate-commit-msg "$1"
exit $?
"""

        commit_msg.write_text(commit_msg_content)
        commit_msg.chmod(0o755)

        return CommandResult(
            status=CommandStatus.SUCCESS,
            message="Git hooks installed successfully",
            data={
                "hooks_dir": str(hooks_dir),
                "hooks_installed": ["pre-commit", "pre-push", "commit-msg"],
            },
        )
