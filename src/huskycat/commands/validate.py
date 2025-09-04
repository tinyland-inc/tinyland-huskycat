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
    
    def execute(self, 
                files: Optional[List[str]] = None, 
                staged: bool = False,
                all_files: bool = False) -> CommandResult:
        """
        Execute validation on files.
        
        Args:
            files: List of file paths to validate
            staged: Validate only staged git files
            all_files: Validate all files in repository
            
        Returns:
            CommandResult with validation status
        """
        # Determine which files to validate
        files_to_validate = self._get_files_to_validate(files, staged, all_files)
        
        if not files_to_validate:
            return CommandResult(
                status=CommandStatus.SUCCESS,
                message="No files to validate"
            )
        
        # Create validation engine and run validation
        engine = ValidationEngine(auto_fix=False)
        
        total_errors = 0
        total_warnings = 0
        all_errors = []
        all_warnings = []
        
        for file_path in files_to_validate:
            path = Path(file_path)
            if not path.exists():
                continue
                
            results = engine.validate_file(path)
            
            for result in results:
                if not result.success:
                    total_errors += result.error_count
                    all_errors.extend([f"{file_path} ({result.tool}): {e}" for e in result.errors])
                
                if result.warnings:
                    total_warnings += result.warning_count
                    all_warnings.extend([f"{file_path} ({result.tool}): {w}" for w in result.warnings])
        
        # Determine overall status
        if total_errors > 0:
            status = CommandStatus.FAILED
            message = f"Validation failed: {total_errors} error(s), {total_warnings} warning(s)"
        elif total_warnings > 0:
            status = CommandStatus.WARNING
            message = f"Validation passed with {total_warnings} warning(s)"
        else:
            status = CommandStatus.SUCCESS
            message = "All validations passed"
        
        return CommandResult(
            status=status,
            message=message,
            errors=all_errors,
            warnings=all_warnings,
            data={
                "files_validated": len(files_to_validate),
                "total_errors": total_errors,
                "total_warnings": total_warnings
            }
        )
    
    def _get_files_to_validate(self, 
                               files: Optional[List[str]], 
                               staged: bool, 
                               all_files: bool) -> List[str]:
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
                    check=True
                )
                return result.stdout.strip().split("\n") if result.stdout.strip() else []
            except subprocess.CalledProcessError:
                return []
        
        if all_files:
            # Get all tracked files from git
            try:
                result = subprocess.run(
                    ["git", "ls-files"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                return result.stdout.strip().split("\n") if result.stdout.strip() else []
            except subprocess.CalledProcessError:
                return []
        
        return []