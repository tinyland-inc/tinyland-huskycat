"""
CI validation command for validating CI/CD configuration files.
"""

from pathlib import Path
from typing import List, Optional

from ..core.base import BaseCommand, CommandResult, CommandStatus
from ..compose_validator import ComposeSchemaValidator
from ..github_actions_validator import GitHubActionsSchemaValidator
from ..gitlab_ci_validator import GitLabCISchemaValidator


class CIValidateCommand(BaseCommand):
    """Command to validate CI/CD configuration files."""

    @property
    def name(self) -> str:
        return "ci-validate"

    @property
    def description(self) -> str:
        return "Validate CI/CD configuration files"

    def execute(self, files: Optional[List[str]] = None) -> CommandResult:
        """
        Validate CI configuration files.

        Args:
            files: Specific CI files to validate, or auto-detect if None

        Returns:
            CommandResult with validation status
        """
        # Auto-detect CI files if not specified
        if not files:
            files = self._detect_ci_files()

        if not files:
            return CommandResult(
                status=CommandStatus.SUCCESS, message="No CI configuration files found"
            )

        all_errors = []
        all_warnings = []
        validated_count = 0

        for file_path in files:
            path = Path(file_path)
            if not path.exists():
                all_errors.append(f"{file_path}: File not found")
                continue

            # Determine CI type and validate
            if path.name == ".gitlab-ci.yml" or path.suffix == ".gitlab-ci.yml":
                result = self._validate_gitlab_ci(path)
            elif path.name == ".github" or "workflow" in str(path):
                result = self._validate_github_actions(path)
            elif "podman-compose" in path.name or "compose" in path.name:
                result = self._validate_compose(path)
            else:
                all_warnings.append(f"{file_path}: Unknown CI file type")
                continue

            validated_count += 1

            if result.status == CommandStatus.FAILED:
                all_errors.extend(result.errors)
            if result.warnings:
                all_warnings.extend(result.warnings)

        # Determine overall status
        if all_errors:
            status = CommandStatus.FAILED
            message = f"CI validation failed: {len(all_errors)} error(s)"
        elif all_warnings:
            status = CommandStatus.WARNING
            message = f"CI validation passed with {len(all_warnings)} warning(s)"
        else:
            status = CommandStatus.SUCCESS
            message = f"All CI files validated successfully ({validated_count} files)"

        return CommandResult(
            status=status,
            message=message,
            errors=all_errors,
            warnings=all_warnings,
            data={
                "files_validated": validated_count,
                "total_errors": len(all_errors),
                "total_warnings": len(all_warnings),
            },
        )

    def _detect_ci_files(self) -> List[str]:
        """Auto-detect CI configuration files in the repository."""
        ci_files = []

        # GitLab CI
        for pattern in [".gitlab-ci.yml", ".gitlab-ci.yaml", ".gitlab/*.yml"]:
            for path in Path(".").glob(pattern):
                ci_files.append(str(path))

        # GitHub Actions
        workflows_dir = Path(".github/workflows")
        if workflows_dir.exists():
            for workflow in workflows_dir.glob("*.yml"):
                ci_files.append(str(workflow))
            for workflow in workflows_dir.glob("*.yaml"):
                ci_files.append(str(workflow))

        # Podman Compose
        for pattern in [
            "podman-compose.yml",
            "podman-compose.yaml",
            "compose.yml",
            "compose.yaml",
        ]:
            if Path(pattern).exists():
                ci_files.append(pattern)

        return ci_files

    def _validate_gitlab_ci(self, path: Path) -> CommandResult:
        """Validate GitLab CI configuration."""
        try:
            validator = GitLabCISchemaValidator()
            is_valid, errors, warnings = validator.validate_file(str(path))

            if is_valid:
                return CommandResult(
                    status=CommandStatus.SUCCESS,
                    message=f"{path}: Valid GitLab CI configuration",
                    warnings=[f"{path}: {w}" for w in warnings],
                )
            else:
                return CommandResult(
                    status=CommandStatus.FAILED,
                    message=f"{path}: Invalid GitLab CI configuration",
                    errors=[f"{path}: {e}" for e in errors],
                    warnings=[f"{path}: {w}" for w in warnings],
                )
        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                message=f"{path}: Failed to validate",
                errors=[f"{path}: {str(e)}"],
            )

    def _validate_github_actions(self, path: Path) -> CommandResult:
        """Validate GitHub Actions workflow file."""
        try:
            validator = GitHubActionsSchemaValidator()
            is_valid, errors, warnings = validator.validate_file(str(path))

            if is_valid:
                return CommandResult(
                    status=CommandStatus.SUCCESS,
                    message=f"{path}: Valid GitHub Actions workflow",
                    warnings=[f"{path}: {w}" for w in warnings],
                )
            else:
                return CommandResult(
                    status=CommandStatus.FAILED,
                    message=f"{path}: Invalid GitHub Actions workflow",
                    errors=[f"{path}: {e}" for e in errors],
                    warnings=[f"{path}: {w}" for w in warnings],
                )
        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                message=f"{path}: Failed to validate",
                errors=[f"{path}: {str(e)}"],
            )

    def _validate_compose(self, path: Path) -> CommandResult:
        """Validate Compose configuration (Docker/Podman Compose)."""
        try:
            validator = ComposeSchemaValidator()
            is_valid, errors, warnings = validator.validate_file(str(path))

            if is_valid:
                return CommandResult(
                    status=CommandStatus.SUCCESS,
                    message=f"{path}: Valid Compose configuration",
                    warnings=[f"{path}: {w}" for w in warnings],
                )
            else:
                return CommandResult(
                    status=CommandStatus.FAILED,
                    message=f"{path}: Invalid Compose configuration",
                    errors=[f"{path}: {e}" for e in errors],
                    warnings=[f"{path}: {w}" for w in warnings],
                )
        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                message=f"{path}: Failed to validate",
                errors=[f"{path}: {str(e)}"],
            )
