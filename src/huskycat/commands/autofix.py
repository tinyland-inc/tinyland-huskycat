"""
Auto-fix command for applying all available validators' auto-fix capabilities.
"""

from pathlib import Path
from typing import List, Optional

from ..core.base import BaseCommand, CommandResult, CommandStatus
from ..unified_validation import ValidationEngine


class AutoFixCommand(BaseCommand):
    """Command to auto-fix issues across all supported validators."""

    @property
    def name(self) -> str:
        return "auto-fix"

    @property
    def description(self) -> str:
        return "Auto-fix issues using all available validators"

    def execute(
        self,
        files: Optional[List[str]] = None,
        staged: bool = False,
        all_files: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """
        Execute auto-fix on files.

        Args:
            files: List of file paths to fix
            staged: Fix only staged git files
            all_files: Fix all files in repository
            dry_run: Show what would be fixed without making changes

        Returns:
            CommandResult with fix status
        """
        # Create validation engine with auto-fix enabled
        engine = ValidationEngine(auto_fix=not dry_run, interactive=False)

        # Run validation/fixes
        if staged:
            results = engine.validate_staged_files()
        elif files:
            results = {}
            for file_path in files:
                path = Path(file_path)
                if path.exists():
                    file_results = engine.validate_file(path)
                    if file_results:
                        results[file_path] = file_results
        elif all_files:
            # Get all tracked files from git
            import subprocess

            try:
                result = subprocess.run(
                    ["git", "ls-files"], capture_output=True, text=True, check=True
                )
                file_list = (
                    result.stdout.strip().split("\n") if result.stdout.strip() else []
                )
                results = {}
                for file_path in file_list:
                    path = Path(file_path)
                    if path.exists():
                        file_results = engine.validate_file(path)
                        if file_results:
                            results[file_path] = file_results
            except subprocess.CalledProcessError:
                return CommandResult(
                    status=CommandStatus.FAILED,
                    message="Failed to get tracked files from git",
                    errors=["Not in a git repository or git command failed"],
                )
        else:
            return CommandResult(
                status=CommandStatus.FAILED,
                message="Must specify files, --staged, or --all",
                errors=["No files specified for auto-fix"],
            )

        # Generate summary
        summary = engine.get_summary(results)

        # Prepare status message
        if dry_run:
            if summary["total_errors"] > 0:
                message = f"Would fix {summary['total_errors']} issue(s) across {summary['total_files']} file(s)"
                status = CommandStatus.SUCCESS
            else:
                message = "No fixable issues found"
                status = CommandStatus.SUCCESS
        else:
            if summary.get("fixed_files", 0) > 0:
                message = f"Auto-fixed {summary['fixed_files']} file(s)"
                if summary["total_errors"] > 0:
                    message += f", {summary['total_errors']} issue(s) remain"
                    status = CommandStatus.WARNING
                else:
                    status = CommandStatus.SUCCESS
            elif summary["total_errors"] > 0:
                message = f"Found {summary['total_errors']} issue(s) but none could be auto-fixed"
                status = CommandStatus.WARNING
            else:
                message = "No issues found"
                status = CommandStatus.SUCCESS

        # Collect detailed messages
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

        return CommandResult(
            status=status,
            message=message,
            errors=all_errors,
            warnings=all_warnings,
            data=summary,
        )
