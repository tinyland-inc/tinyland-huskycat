# SPDX-License-Identifier: Apache-2.0
"""
YAML Lint Validator - Integration with HuskyCat validation engine.

This validator wraps the clean-room yaml_lint module and integrates it
with HuskyCat's unified validation framework.
"""

import time
from pathlib import Path
from typing import Set

from huskycat.linters.yaml_lint import YamlLintConfig, lint_yaml_file
from huskycat.unified_validation import ValidationResult, Validator


class YamlLintValidator(Validator):
    """Validator for YAML files using clean-room yaml_lint implementation.

    This validator does NOT depend on GPL yamllint.
    It uses a clean-room implementation based on YAML 1.2 specification.
    """

    def __init__(self, auto_fix: bool = False, config: dict = None):
        """Initialize YAML validator.

        Args:
            auto_fix: Whether to automatically fix issues (not implemented for YAML)
            config: Optional YAML lint configuration dictionary
        """
        super().__init__(auto_fix=auto_fix)
        self.lint_config = YamlLintConfig.from_dict(config)

    @property
    def name(self) -> str:
        """Validator name."""
        return "yaml-lint"

    @property
    def extensions(self) -> Set[str]:
        """File extensions this validator handles."""
        return {".yaml", ".yml"}

    @property
    def command(self) -> str:
        """Command to check availability (not applicable for Python-native linter)."""
        # This is a Python-native linter, no external command needed
        return "python"

    def is_available(self) -> bool:
        """Check if validator is available.

        Since this is a Python-native implementation, it's always available
        as long as PyYAML is installed.
        """
        try:
            import yaml  # noqa: F401

            return True
        except ImportError:
            return False

    def validate(self, filepath: Path) -> ValidationResult:
        """Validate a YAML file.

        Args:
            filepath: Path to YAML file to validate

        Returns:
            ValidationResult with linting results
        """
        start_time = time.time()

        try:
            # Lint the YAML file
            issues = lint_yaml_file(filepath, config=self.lint_config.__dict__)
            duration_ms = int((time.time() - start_time) * 1000)

            # Separate errors and warnings
            errors = []
            warnings = []
            messages = []

            for issue in issues:
                issue_str = str(issue)
                if issue.severity == "error":
                    errors.append(issue_str)
                elif issue.severity == "warning":
                    warnings.append(issue_str)
                messages.append(issue_str)

            # Determine success - file is valid if no errors
            success = len(errors) == 0

            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=success,
                messages=messages,
                errors=errors,
                warnings=warnings,
                fixed=False,  # Auto-fix not implemented for YAML
                duration_ms=duration_ms,
            )

        except FileNotFoundError:
            duration_ms = int((time.time() - start_time) * 1000)
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[f"File not found: {filepath}"],
                duration_ms=duration_ms,
            )

        except PermissionError:
            duration_ms = int((time.time() - start_time) * 1000)
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[f"Permission denied: {filepath}"],
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[f"Validation error: {str(e)}"],
                duration_ms=duration_ms,
            )


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python yaml_lint_validator.py <yaml_file>")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    validator = YamlLintValidator()

    if not validator.is_available():
        print("ERROR: PyYAML is not installed")
        print("Install with: pip install pyyaml")
        sys.exit(1)

    result = validator.validate(filepath)

    print(f"\n{'='*60}")
    print(f"YAML Lint Results: {filepath}")
    print(f"{'='*60}")
    print(f"Tool: {result.tool}")
    print(f"Success: {result.success}")
    print(f"Duration: {result.duration_ms}ms")

    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for error in result.errors:
            print(f"  {error}")

    if result.warnings:
        print(f"\nWarnings ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"  {warning}")

    if result.messages and not result.errors and not result.warnings:
        print("\n✓ No issues found")

    sys.exit(0 if result.success else 1)
