"""
Status command to show HuskyCat configuration and state.
"""

import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Union, List

from ..core.base import BaseCommand, CommandResult, CommandStatus


class StatusCommand(BaseCommand):
    """Command to display HuskyCat status and configuration."""

    @property
    def name(self) -> str:
        return "status"

    @property
    def description(self) -> str:
        return "Show HuskyCat status and configuration"

    def execute(self) -> CommandResult:
        """
        Show current status.

        Returns:
            CommandResult with status information
        """
        status_info: Dict[str, Union[str, bool, List[str]]] = {}

        # Check git repository
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                check=True,
            )
            git_dir = Path(result.stdout.strip())
            status_info["git_repository"] = "Yes"

            # Check for hooks
            hooks_dir = git_dir / "hooks"
            hooks = []
            for hook_name in ["pre-commit", "pre-push", "commit-msg"]:
                if (hooks_dir / hook_name).exists():
                    hooks.append(hook_name)
            status_info["git_hooks"] = hooks if hooks else ["None installed"]

        except subprocess.CalledProcessError:
            status_info["git_repository"] = "No"
            status_info["git_hooks"] = ["N/A"]

        # Check cache directory
        cache_dir = Path.home() / ".cache" / "huskycats"
        if cache_dir.exists():
            schemas = []
            for schema_file in cache_dir.glob("*.json"):
                mtime = datetime.fromtimestamp(schema_file.stat().st_mtime)
                age_days = (datetime.now() - mtime).days
                schemas.append(f"{schema_file.stem} (updated {age_days} days ago)")
            status_info["cached_schemas"] = schemas if schemas else ["None"]
        else:
            status_info["cached_schemas"] = ["Cache directory not found"]

        # Check configuration
        status_info["config_dir"] = str(self.config_dir)
        status_info["config_exists"] = self.config_dir.exists()

        # Format output
        output_lines = [
            "HuskyCat Status",
            "=" * 40,
            f"Configuration Directory: {status_info['config_dir']}",
            f"Git Repository: {status_info['git_repository']}",
            f"Git Hooks: {', '.join(status_info['git_hooks'])}",
            "",
            "Cached Schemas:",
        ]
        for schema in status_info["cached_schemas"]:
            output_lines.append(f"  • {schema}")

        return CommandResult(
            status=CommandStatus.SUCCESS,
            message="\n".join(output_lines),
            data=status_info,
        )
