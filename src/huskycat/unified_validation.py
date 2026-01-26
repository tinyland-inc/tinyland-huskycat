#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
HuskyCat Unified Validation Engine

Single source of truth for all validation logic.
Supports both CLI and MCP server modes.

This module serves as the facade for the validators package.
Validators are now split into individual modules under huskycat.validators.
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from huskycat.core.tool_selector import (
    LintingMode,
    get_mode_from_env,
    is_tool_bundled,
)

# Import all validators from the validators package
from huskycat.validators import (
    # Base classes
    ValidationResult,
    Validator,
    # Utility functions
    get_gpl_sidecar,
    is_gpl_tool,
    # Python validators
    BlackValidator,
    AutoflakeValidator,
    Flake8Validator,
    MypyValidator,
    RuffValidator,
    IsortValidator,
    BanditValidator,
    # TOML validator
    TaploValidator,
    # Terraform validator
    TerraformValidator,
    # JavaScript/TypeScript validators
    ESLintValidator,
    PrettierValidator,
    # Chapel validator
    ChapelValidator,
    # Ansible validator
    AnsibleLintValidator,
    # YAML validator
    YamlLintValidator,
    # Container validators
    HadolintValidator,
    # Shell validator
    ShellcheckValidator,
    # GitLab CI validator
    GitLabCIValidator,
)

# Configure logging
logging.basicConfig(
    level=os.getenv("HUSKYCAT_LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Re-export for backwards compatibility
__all__ = [
    # Base classes
    "ValidationResult",
    "Validator",
    # Utility functions
    "get_gpl_sidecar",
    "is_gpl_tool",
    # Python validators
    "BlackValidator",
    "AutoflakeValidator",
    "Flake8Validator",
    "MypyValidator",
    "RuffValidator",
    "IsortValidator",
    "BanditValidator",
    # TOML validator
    "TaploValidator",
    # Terraform validator
    "TerraformValidator",
    # JavaScript/TypeScript validators
    "ESLintValidator",
    "PrettierValidator",
    # Chapel validator
    "ChapelValidator",
    # Ansible validator
    "AnsibleLintValidator",
    # YAML validator
    "YamlLintValidator",
    # Container validators
    "HadolintValidator",
    # Shell validator
    "ShellcheckValidator",
    # GitLab CI validator
    "GitLabCIValidator",
    # Engine
    "ValidationEngine",
]


class ValidationEngine:
    """Main validation engine that orchestrates all validators"""

    def __init__(
        self,
        auto_fix: bool = False,
        interactive: bool = False,
        allow_warnings: bool = False,
        use_container: bool = False,
        adapter: Optional[Any] = None,
        linting_mode: Optional[LintingMode] = None,
    ):
        self.auto_fix = auto_fix
        self.interactive = interactive
        self.allow_warnings = allow_warnings
        self.use_container = use_container
        self.adapter = adapter
        self.linting_mode = linting_mode or get_mode_from_env()
        logger.info(f"ValidationEngine initialized with linting_mode={self.linting_mode.value}")
        self.validators = self._initialize_validators()
        self._extension_map = self._build_extension_map()

    def _load_dockerlint_validator(self):
        """Dynamically load DockerLintValidator if available"""
        try:
            from huskycat.linters.dockerlint_validator import DockerLintValidator  # type: ignore
            return DockerLintValidator
        except ImportError:
            logger.debug("DockerLintValidator not available")
            return None

    def _should_tool_auto_fix(self, tool_name: str) -> bool:
        """
        Check if a specific tool should auto-fix based on adapter rules.

        Uses adapter's should_auto_fix_tool() if available, otherwise
        falls back to global auto_fix setting.

        Args:
            tool_name: Name of the validation tool

        Returns:
            True if tool should auto-fix
        """
        if self.adapter is not None and hasattr(self.adapter, "should_auto_fix_tool"):
            return self.adapter.should_auto_fix_tool(tool_name, self.auto_fix)
        return self.auto_fix

    def _should_use_tool(self, tool_name: str) -> bool:
        """
        Check if tool should be used based on linting mode and license.

        In FAST mode, only bundled Apache/MIT tools are used.
        In COMPREHENSIVE mode, all tools including GPL are used.

        Args:
            tool_name: Name of the validation tool

        Returns:
            True if tool should be used in current linting mode
        """
        if self.linting_mode == LintingMode.COMPREHENSIVE:
            return True  # Use all tools in comprehensive mode

        # In FAST mode, only use bundled (non-GPL) tools
        try:
            return is_tool_bundled(tool_name)
        except KeyError:
            # Tool not in registry - allow it (backward compatibility)
            logger.warning(f"Tool {tool_name} not in tool registry, allowing by default")
            return True

    def _initialize_validators(self) -> List[Validator]:
        """Initialize all available validators with per-tool auto-fix decisions."""
        # Create validators with per-tool auto-fix based on adapter rules
        validators = [
            BlackValidator(self._should_tool_auto_fix("python-black")),
            AutoflakeValidator(self._should_tool_auto_fix("autoflake")),
            Flake8Validator(False),  # No auto-fix support
            MypyValidator(False),  # No auto-fix support
            RuffValidator(self._should_tool_auto_fix("ruff")),
            IsortValidator(self._should_tool_auto_fix("isort")),
            TaploValidator(self._should_tool_auto_fix("taplo")),
            TerraformValidator(self._should_tool_auto_fix("terraform")),
            BanditValidator(False),  # No auto-fix support
            ESLintValidator(self._should_tool_auto_fix("js-eslint")),
            PrettierValidator(self._should_tool_auto_fix("js-prettier")),
            ChapelValidator(self._should_tool_auto_fix("chapel")),
            AnsibleLintValidator(self._should_tool_auto_fix("ansible-lint")),
            YamlLintValidator(self._should_tool_auto_fix("yamllint")),
            HadolintValidator(False),  # No auto-fix support (GPL licensed, being replaced)
            ShellcheckValidator(False),  # No auto-fix support
            GitLabCIValidator(False),  # No auto-fix support
        ]

        # Dynamically add DockerLintValidator if available
        DockerLintValidatorClass = self._load_dockerlint_validator()
        if DockerLintValidatorClass is not None:
            validators.append(DockerLintValidatorClass(False))  # No auto-fix support

        # Filter to only available validators, respecting linting mode
        available = []
        for v in validators:
            # Check if tool should be used based on linting mode
            if not self._should_use_tool(v.name):
                logger.info(f"Skipping {v.name} in {self.linting_mode.value} mode (GPL or not bundled)")
                continue

            if v.is_available():
                available.append(v)
                logger.info(f"Validator {v.name} is available (auto_fix={v.auto_fix}, mode={self.linting_mode.value})")
            else:
                logger.warning(f"Validator {v.name} is not available")

        return available

    def _build_extension_map(self) -> Dict[str, List[Validator]]:
        """Build a map of file extensions to validators"""
        ext_map: Dict[str, List[Validator]] = {}
        for validator in self.validators:
            for ext in validator.extensions:
                if ext not in ext_map:
                    ext_map[ext] = []
                ext_map[ext].append(validator)
        return ext_map

    def get_validators_for_file(self, filepath: Path) -> List[Validator]:
        """Get applicable validators for a file (for testing compatibility)"""
        validators = self._extension_map.get(filepath.suffix, [])

        # Also check validators with custom can_handle logic
        for v in self.validators:
            if v.can_handle(filepath) and v not in validators:
                validators.append(v)

        return validators

    def validate_file(
        self,
        filepath: Path,
        fix: Optional[bool] = None,
        tools: Optional[List[str]] = None,
    ) -> List[ValidationResult]:
        """Validate a single file with all applicable validators"""
        results: List[ValidationResult] = []

        # Find applicable validators
        if tools:
            # Filter validators by specified tool names
            validators = []
            for tool_name in tools:
                found_validator = None
                for v in self.validators:
                    if v.name == tool_name and v.can_handle(filepath):
                        found_validator = v
                        break

                if found_validator:
                    validators.append(found_validator)
                else:
                    # Create error result for unknown tool
                    result = ValidationResult(
                        tool=tool_name,
                        filepath=str(filepath),
                        success=False,
                        messages=[f"Unknown tool: {tool_name}"],
                        errors=[f"Unknown tool: {tool_name}"],
                    )
                    results.append(result)
        else:
            # Use all applicable validators
            validators = self._extension_map.get(filepath.suffix, [])

            # Also check validators with custom can_handle logic
            for v in self.validators:
                if v.can_handle(filepath) and v not in validators:
                    validators.append(v)

        if not validators and not tools:
            logger.warning(f"No validators found for {filepath}")
            return results

        # Run each validator
        for validator in validators:
            logger.info(f"Running {validator.name} on {filepath}")
            result = validator.validate(filepath)
            results.append(result)

        return results

    def validate_directory(
        self,
        directory: Path,
        recursive: bool = True,
        exclude_patterns: Optional[List[str]] = None,
    ) -> Dict[str, List[ValidationResult]]:
        """Validate all files in a directory"""
        results = {}

        pattern = "**/*" if recursive else "*"
        exclude_patterns = exclude_patterns or []

        for filepath in directory.glob(pattern):
            if filepath.is_file() and not filepath.name.startswith("."):
                # Check if file should be excluded
                should_exclude = False
                for exclude_pattern in exclude_patterns:
                    if exclude_pattern in str(filepath):
                        should_exclude = True
                        break

                if not should_exclude:
                    file_results = self.validate_file(filepath)
                    if file_results:
                        results[str(filepath)] = file_results

        return results

    def validate_staged_files(self) -> Dict[str, List[ValidationResult]]:
        """Validate files staged for git commit with interactive auto-fix prompt"""
        try:
            # Get staged files
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                logger.error("Failed to get staged files")
                return {}

            # First pass - validate without auto-fix
            results = {}
            for filename in result.stdout.splitlines():
                filepath = Path(filename)
                if filepath.exists():
                    file_results = self.validate_file(filepath)
                    if file_results:
                        results[filename] = file_results

            # Check if we have fixable issues and prompt for auto-fix
            if self.interactive and not self.auto_fix:
                fixable_issues = self._count_fixable_issues(results)
                if fixable_issues > 0:
                    print(f"\nFound {fixable_issues} auto-fixable issues.")
                    response = input("Attempt auto-fix? [y/N]: ").strip().lower()
                    if response in ["y", "yes"]:
                        print("Applying auto-fixes...")
                        # Re-run with auto-fix enabled, preserving linting mode
                        auto_fix_engine = ValidationEngine(
                            auto_fix=True,
                            linting_mode=self.linting_mode
                        )
                        results = {}
                        for filename in result.stdout.splitlines():
                            filepath = Path(filename)
                            if filepath.exists():
                                file_results = auto_fix_engine.validate_file(filepath)
                                if file_results:
                                    results[filename] = file_results

            return results

        except Exception as e:
            logger.error(f"Error validating staged files: {e}")
            return {}

    def _count_fixable_issues(self, results: Dict[str, List[ValidationResult]]) -> int:
        """Count how many issues could potentially be auto-fixed"""
        fixable_tools = {
            "black",
            "autoflake",
            "ruff",
            "isort",
            "taplo",
            "terraform",
            "yamllint",
            "eslint",
            "js-prettier",
            "chapel",
        }
        count = 0

        for filepath, file_results in results.items():
            for result in file_results:
                if not result.success and result.tool in fixable_tools:
                    count += result.error_count

        return count

    def get_summary(self, results: Dict[str, List[ValidationResult]]) -> Dict[str, Any]:
        """Generate a summary of validation results"""
        total_files = len(results)
        total_errors = 0
        total_warnings = 0
        failed_files = []
        fixed_files = []

        for filepath, file_results in results.items():
            has_error = False
            has_fixes = False
            for result in file_results:
                total_errors += result.error_count
                total_warnings += result.warning_count
                if not result.success:
                    has_error = True
                if result.fixed:
                    has_fixes = True

            if has_error:
                failed_files.append(filepath)
            if has_fixes:
                fixed_files.append(filepath)

        return {
            "total_files": total_files,
            "passed_files": total_files - len(failed_files),
            "failed_files": len(failed_files),
            "fixed_files": len(fixed_files),
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "failed_file_list": failed_files,
            "fixed_file_list": fixed_files,
            "success": len(failed_files) == 0,
        }


# CLI Interface
def main() -> None:
    """Main entry point for CLI usage"""
    import argparse

    parser = argparse.ArgumentParser(description="HuskyCat Unified Validation Engine")
    parser.add_argument(
        "path", nargs="?", default=".", help="File or directory to validate"
    )
    parser.add_argument(
        "--fix", action="store_true", help="Auto-fix issues where possible"
    )
    parser.add_argument(
        "--staged", action="store_true", help="Validate only staged files"
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument(
        "--container", action="store_true", help="Run validation in container"
    )
    parser.add_argument(
        "--linting-mode",
        choices=["fast", "comprehensive"],
        help="Linting mode: fast (bundled tools only) or comprehensive (all tools including GPL)",
    )

    args = parser.parse_args()

    # Initialize engine with interactive mode for git hooks
    interactive_mode = (
        not args.fix and args.staged
    )  # Interactive only for staged files when --fix not specified

    # Note: --container flag is now ignored as container is the only execution mode
    if args.container:
        print("Note: --container flag is now default behavior (container-only mode)")

    # Parse linting mode from args or environment
    linting_mode = None
    if args.linting_mode:
        linting_mode = LintingMode.FAST if args.linting_mode == "fast" else LintingMode.COMPREHENSIVE

    engine = ValidationEngine(
        auto_fix=args.fix,
        interactive=interactive_mode,
        linting_mode=linting_mode
    )

    # Run validation
    if args.staged:
        results = engine.validate_staged_files()
    else:
        path = Path(args.path)
        if path.is_file():
            file_results = engine.validate_file(path)
            results = {str(path): file_results} if file_results else {}
        else:
            results = engine.validate_directory(path)

    # Generate summary
    summary = engine.get_summary(results)

    # Output results
    if args.json:
        output = {
            "summary": summary,
            "results": {
                filepath: [r.to_dict() for r in file_results]
                for filepath, file_results in results.items()
            },
        }
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        print(f"\n{'='*60}")
        print("VALIDATION SUMMARY")
        print(f"{'='*60}")
        print(f"Files Scanned: {summary['total_files']}")
        print(f"Files Passed:  {summary['passed_files']}")
        print(f"Files Failed:  {summary['failed_files']}")
        if summary.get("fixed_files", 0) > 0:
            print(f"Files Fixed:   {summary['fixed_files']}")
        print(f"Total Errors:  {summary['total_errors']}")
        print(f"Total Warnings: {summary['total_warnings']}")

        if summary["failed_file_list"]:
            print(f"\n{'='*60}")
            print("FAILED FILES:")
            print(f"{'='*60}")
            for filepath in summary["failed_file_list"]:
                print(f"  - {filepath}")
                for result in results[filepath]:
                    if not result.success:
                        print(
                            f"    [{result.tool}] {result.error_count} errors, {result.warning_count} warnings"
                        )

        print(f"\n{'='*60}")
        if summary["success"]:
            print("ALL VALIDATIONS PASSED")
        else:
            print("VALIDATION FAILED")
        print(f"{'='*60}\n")

    # Exit with appropriate code
    sys.exit(0 if summary["success"] else 1)


if __name__ == "__main__":
    main()
