"""
Validation command for running all configured validators.
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

        # Create validation engine (container-only mode)
        engine = ValidationEngine(
            auto_fix=fix,
            interactive=interactive and staged,
        )

        # Use the appropriate validation method
        if staged:
            results = engine.validate_staged_files()
        else:
            results = {}
            for file_path in files_to_validate:
                path = Path(file_path)
                if path.exists():
                    file_results = engine.validate_file(path)
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

        # Determine overall status based on summary
        if summary["total_errors"] > 0:
            status = CommandStatus.FAILED
            message = f"Validation failed: {summary['total_errors']} error(s), {summary['total_warnings']} warning(s)"
        elif summary["total_warnings"] > 0:
            status = CommandStatus.WARNING
            message = f"Validation passed with {summary['total_warnings']} warning(s)"
        else:
            status = CommandStatus.SUCCESS
            message = "All validations passed"

        # Include auto-fix information in message
        if summary.get("fixed_files", 0) > 0:
            message += f" ({summary['fixed_files']} files auto-fixed)"

        return CommandResult(
            status=status,
            message=message,
            errors=all_errors,
            warnings=all_warnings,
            data=summary,
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
