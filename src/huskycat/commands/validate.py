"""
Validation command for running all configured validators.

Uses the mode adapter to determine which tools to run based on the
current product mode (git_hooks, ci, cli, pipeline, mcp).
"""

from pathlib import Path
from typing import List, Optional
import subprocess

from ..core.base import BaseCommand, CommandResult, CommandStatus
from ..unified_validation import ValidationEngine


class ValidateCommand(BaseCommand):
    """Command to validate files using all configured validators."""

    @property
    def name(self) -> str:
        return "validate"

    @property
    def description(self) -> str:
        return "Run validation on specified files or staged changes"

    def execute(
        self,
        files: Optional[List[str]] = None,
        staged: bool = False,
        all_files: bool = False,
        fix: bool = False,
        interactive: bool = False,
        allow_warnings: bool = False,
    ) -> CommandResult:
        """
        Execute validation on files.

        Args:
            files: List of file paths to validate
            staged: Validate only staged git files
            all_files: Validate all files in repository
            fix: Auto-fix issues where possible
            interactive: Prompt user for auto-fix decisions

        Returns:
            CommandResult with validation status
        """
        # Determine which files to validate
        files_to_validate = self._get_files_to_validate(files, staged, all_files)

        if not files_to_validate:
            return CommandResult(
                status=CommandStatus.SUCCESS, message="No files to validate"
            )

        # Get mode-specific settings from adapter if available
        adapter_config = self.adapter.config if self.adapter else None
        tool_selection = self.adapter.get_tool_selection() if self.adapter else ["all"]

        # Override interactive based on adapter if not explicitly set
        effective_interactive = interactive
        if adapter_config and not interactive:
            effective_interactive = adapter_config.interactive and staged

        # Create validation engine with mode-aware settings
        engine = ValidationEngine(
            auto_fix=fix,
            interactive=effective_interactive,
            allow_warnings=allow_warnings,
        )

        # Convert tool selection to filter list (None means all tools)
        tools_filter = None if "all" in tool_selection else tool_selection

        # Log tool selection in verbose mode
        if self.verbose:
            mode_name = self.adapter.name if self.adapter else "default"
            print(f"[TOOLS] Mode '{mode_name}' using: {tool_selection}")

        # Use the appropriate validation method
        if staged:
            results = engine.validate_staged_files()
        else:
            results = {}
            for file_path in files_to_validate:
                path = Path(file_path)
                if path.exists():
                    file_results = engine.validate_file(path, tools=tools_filter)
                    if file_results:
                        results[file_path] = file_results

        # Generate summary
        summary = engine.get_summary(results)

        # Prepare detailed messages
        all_errors = []
        all_warnings = []

        for filepath, file_results in results.items():
            for result in file_results:
                if result.errors:
                    all_errors.extend(
                        [f"{filepath} ({result.tool}): {e}" for e in result.errors]
                    )
                if result.warnings:
                    all_warnings.extend(
                        [f"{filepath} ({result.tool}): {w}" for w in result.warnings]
                    )

        # Determine overall status based on summary and allow_warnings flag
        if summary["total_errors"] > 0:
            status = CommandStatus.FAILED
            message = f"Validation failed: {summary['total_errors']} error(s), {summary['total_warnings']} warning(s)"
        elif summary["total_warnings"] > 0:
            if allow_warnings:
                status = CommandStatus.SUCCESS
                message = f"Validation passed with {summary['total_warnings']} warning(s) (warnings allowed)"
            else:
                status = CommandStatus.WARNING
                message = (
                    f"Validation passed with {summary['total_warnings']} warning(s)"
                )
        else:
            status = CommandStatus.SUCCESS
            message = "All validations passed"

        # Include auto-fix information in message
        if summary.get("fixed_files", 0) > 0:
            message += f" ({summary['fixed_files']} files auto-fixed)"

        # Prepare data for structured output (JSON, JUnit, etc.)
        data = {
            **summary,
            "mode": self.adapter.name if self.adapter else "cli",
            "tools_used": tool_selection,
            "files_checked": len(files_to_validate),
            "results": {
                filepath: [r.to_dict() for r in file_results]
                for filepath, file_results in results.items()
            },
        }

        return CommandResult(
            status=status,
            message=message,
            errors=all_errors,
            warnings=all_warnings,
            data=data,
        )

    def _get_files_to_validate(
        self, files: Optional[List[str]], staged: bool, all_files: bool
    ) -> List[str]:
        """Get list of files to validate based on options."""
        if files:
            return files

        if staged:
            # Get staged files from git
            try:
                result = subprocess.run(
                    ["git", "diff", "--cached", "--name-only"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                return (
                    result.stdout.strip().split("\n") if result.stdout.strip() else []
                )
            except subprocess.CalledProcessError:
                return []

        if all_files:
            # Get all tracked files from git
            try:
                result = subprocess.run(
                    ["git", "ls-files"], capture_output=True, text=True, check=True
                )
                return (
                    result.stdout.strip().split("\n") if result.stdout.strip() else []
                )
            except subprocess.CalledProcessError:
                return []

        return []
