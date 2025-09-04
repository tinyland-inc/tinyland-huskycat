#!/usr/bin/env python3
"""
HuskyCat Unified Validation Engine
Single source of truth for all validation logic
Supports both CLI and MCP server modes
"""

import json
import logging
import os
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Configure logging
logging.basicConfig(
    level=os.getenv("HUSKYCAT_LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Unified result of a validation operation"""

    tool: str
    filepath: str
    success: bool
    messages: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    fixed: bool = False
    duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "tool": self.tool,
            "filepath": self.filepath,
            "success": self.success,
            "messages": self.messages,
            "errors": self.errors,
            "warnings": self.warnings,
            "fixed": self.fixed,
            "duration_ms": self.duration_ms,
        }

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)


class Validator(ABC):
    """Abstract base class for all validators"""

    def __init__(self, auto_fix: bool = False):
        self.auto_fix = auto_fix

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this validator"""
        pass

    @property
    @abstractmethod
    def extensions(self) -> Set[str]:
        """File extensions this validator handles"""
        pass

    @property
    def command(self) -> str:
        """Command to check if tool is available"""
        return self.name

    def is_available(self) -> bool:
        """Check if the validator tool is available"""
        try:
            result = subprocess.run(
                [self.command, "--version"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    @abstractmethod
    def validate(self, filepath: Path) -> ValidationResult:
        """Validate a single file"""
        pass

    def can_handle(self, filepath: Path) -> bool:
        """Check if this validator can handle the given file"""
        return filepath.suffix in self.extensions


# Python Validators


class BlackValidator(Validator):
    """Python code formatter"""

    @property
    def name(self) -> str:
        return "black"

    @property
    def extensions(self) -> Set[str]:
        return {".py", ".pyi"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()
        cmd = [self.command, "--check", str(filepath)]

        if self.auto_fix:
            cmd.remove("--check")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["File is properly formatted"],
                    fixed=self.auto_fix,
                    duration_ms=duration_ms,
                )
            else:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=False,
                    errors=["File needs formatting"],
                    messages=result.stdout.splitlines() if result.stdout else [],
                    duration_ms=duration_ms,
                )
        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )


class Flake8Validator(Validator):
    """Python linter"""

    @property
    def name(self) -> str:
        return "flake8"

    @property
    def extensions(self) -> Set[str]:
        return {".py", ".pyi"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()
        cmd = [self.command, str(filepath), "--format=json"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["No issues found"],
                    duration_ms=duration_ms,
                )
            else:
                errors = []
                warnings = []

                # Parse flake8 output
                for line in result.stdout.splitlines():
                    if ":" in line:
                        parts = line.split(":", 3)
                        if len(parts) >= 4:
                            msg = parts[3].strip()
                            if any(code in msg for code in ["E", "F"]):
                                errors.append(msg)
                            else:
                                warnings.append(msg)

                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=False,
                    errors=errors,
                    warnings=warnings,
                    duration_ms=duration_ms,
                )
        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )


class MypyValidator(Validator):
    """Python type checker"""

    @property
    def name(self) -> str:
        return "mypy"

    @property
    def extensions(self) -> Set[str]:
        return {".py", ".pyi"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()
        cmd = [self.command, str(filepath), "--no-error-summary"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["Type checking passed"],
                    duration_ms=duration_ms,
                )
            else:
                errors = []
                warnings = []

                for line in result.stdout.splitlines():
                    if "error:" in line:
                        errors.append(line)
                    elif "warning:" in line or "note:" in line:
                        warnings.append(line)

                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=False,
                    errors=errors,
                    warnings=warnings,
                    duration_ms=duration_ms,
                )
        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )


# JavaScript/TypeScript Validators


class ESLintValidator(Validator):
    """JavaScript/TypeScript linter"""

    @property
    def name(self) -> str:
        return "eslint"

    @property
    def extensions(self) -> Set[str]:
        return {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()
        cmd = [self.command, str(filepath), "--format=json"]

        if self.auto_fix:
            cmd.insert(1, "--fix")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            duration_ms = int((time.time() - start_time) * 1000)

            try:
                data = json.loads(result.stdout) if result.stdout else []
                file_result = data[0] if data else {}

                errors = [
                    msg
                    for msg in file_result.get("messages", [])
                    if msg.get("severity") == 2
                ]
                warnings = [
                    msg
                    for msg in file_result.get("messages", [])
                    if msg.get("severity") == 1
                ]

                if not errors:
                    return ValidationResult(
                        tool=self.name,
                        filepath=str(filepath),
                        success=True,
                        warnings=[w.get("message", "") for w in warnings],
                        fixed=self.auto_fix,
                        duration_ms=duration_ms,
                    )
                else:
                    return ValidationResult(
                        tool=self.name,
                        filepath=str(filepath),
                        success=False,
                        errors=[e.get("message", "") for e in errors],
                        warnings=[w.get("message", "") for w in warnings],
                        duration_ms=duration_ms,
                    )
            except json.JSONDecodeError:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=result.returncode == 0,
                    messages=result.stdout.splitlines() if result.stdout else [],
                    duration_ms=duration_ms,
                )
        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )


# YAML Validator


class YamlLintValidator(Validator):
    """YAML linter"""

    @property
    def name(self) -> str:
        return "yamllint"

    @property
    def extensions(self) -> Set[str]:
        return {".yaml", ".yml"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()
        cmd = [self.command, "-f", "parsable", str(filepath)]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["YAML is valid"],
                    duration_ms=duration_ms,
                )
            else:
                errors = []
                warnings = []

                for line in result.stdout.splitlines():
                    if "[error]" in line:
                        errors.append(line)
                    elif "[warning]" in line:
                        warnings.append(line)

                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=False,
                    errors=errors,
                    warnings=warnings,
                    duration_ms=duration_ms,
                )
        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )


# Container Validator


class HadolintValidator(Validator):
    """Dockerfile/ContainerFile linter"""

    @property
    def name(self) -> str:
        return "hadolint"

    @property
    def extensions(self) -> Set[str]:
        # Handle both extensions and specific filenames
        return {".dockerfile"}

    def can_handle(self, filepath: Path) -> bool:
        """Check if this validator can handle the given file"""
        return filepath.suffix in self.extensions or filepath.name in [
            "Dockerfile",
            "ContainerFile",
        ]

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()
        cmd = [self.command, str(filepath)]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["Container file is valid"],
                    duration_ms=duration_ms,
                )
            else:
                errors = []
                warnings = []

                for line in result.stdout.splitlines():
                    if "DL" in line:  # Hadolint error codes
                        if "error" in line.lower():
                            errors.append(line)
                        else:
                            warnings.append(line)

                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=False,
                    errors=errors,
                    warnings=warnings,
                    duration_ms=duration_ms,
                )
        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )


# Shell Script Validator


class ShellcheckValidator(Validator):
    """Shell script linter"""

    @property
    def name(self) -> str:
        return "shellcheck"

    @property
    def extensions(self) -> Set[str]:
        return {".sh", ".bash", ".zsh", ".ksh"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()
        cmd = [self.command, "-f", "json", str(filepath)]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["Shell script is valid"],
                    duration_ms=duration_ms,
                )
            else:
                errors = []
                warnings = []

                try:
                    issues = json.loads(result.stdout) if result.stdout else []
                    for issue in issues:
                        msg = f"Line {issue.get('line')}: {issue.get('message')}"
                        if issue.get("level") == "error":
                            errors.append(msg)
                        else:
                            warnings.append(msg)
                except json.JSONDecodeError:
                    errors = result.stdout.splitlines() if result.stdout else []

                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=False,
                    errors=errors,
                    warnings=warnings,
                    duration_ms=duration_ms,
                )
        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )


class GitLabCIValidator(Validator):
    """Validator for GitLab CI YAML files using official schema"""

    @property
    def name(self) -> str:
        return "gitlab-ci"

    @property
    def extensions(self) -> List[str]:
        return [".yml", ".yaml"]

    def is_available(self) -> bool:
        """Check if GitLab CI validator is available"""
        try:
            from gitlab_ci_validator import GitLabCISchemaValidator
            return True
        except ImportError:
            return False

    def can_handle(self, filepath: Path) -> bool:
        """Check if this file is a GitLab CI file"""
        # Check for .gitlab-ci.yml or files in .gitlab/ci/
        name = filepath.name
        return (
            name == ".gitlab-ci.yml" or 
            name.startswith(".gitlab-ci") or
            ".gitlab/ci/" in str(filepath) or
            ".gitlab-ci" in str(filepath)
        )

    def validate(self, filepath: Path) -> ValidationResult:
        """Validate GitLab CI YAML file against official schema"""
        start_time = time.time()
        
        try:
            # Lazy load the validator
            from gitlab_ci_validator import GitLabCISchemaValidator
            validator = GitLabCISchemaValidator()

            # Validate the file
            is_valid, errors, warnings = validator.validate_file(str(filepath))
            
            duration_ms = int((time.time() - start_time) * 1000)

            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=is_valid,
                errors=errors,
                warnings=warnings,
                duration_ms=duration_ms,
            )

        except ImportError:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=["GitLab CI validator not installed. Install with: pip install jsonschema pyyaml requests"],
                duration_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[f"Validation error: {str(e)}"],
                duration_ms=int((time.time() - start_time) * 1000),
            )


class ValidationEngine:
    """Main validation engine that orchestrates all validators"""

    def __init__(self, auto_fix: bool = False, use_container: bool = False):
        self.auto_fix = auto_fix
        self.use_container = use_container
        self.validators = self._initialize_validators()
        self._extension_map = self._build_extension_map()

    def _initialize_validators(self) -> List[Validator]:
        """Initialize all available validators"""
        validators = [
            BlackValidator(self.auto_fix),
            Flake8Validator(self.auto_fix),
            MypyValidator(self.auto_fix),
            ESLintValidator(self.auto_fix),
            YamlLintValidator(self.auto_fix),
            HadolintValidator(self.auto_fix),
            ShellcheckValidator(self.auto_fix),
            GitLabCIValidator(self.auto_fix),  # Added GitLab CI validator
        ]

        # Filter to only available validators
        available = []
        for v in validators:
            if v.is_available():
                available.append(v)
                logger.info(f"Validator {v.name} is available")
            else:
                logger.warning(f"Validator {v.name} is not available")

        return available

    def _build_extension_map(self) -> Dict[str, List[Validator]]:
        """Build a map of file extensions to validators"""
        ext_map = {}
        for validator in self.validators:
            for ext in validator.extensions:
                if ext not in ext_map:
                    ext_map[ext] = []
                ext_map[ext].append(validator)
        return ext_map

    def validate_file(self, filepath: Path) -> List[ValidationResult]:
        """Validate a single file with all applicable validators"""
        results = []

        # Find applicable validators
        validators = self._extension_map.get(filepath.suffix, [])

        # Also check validators with custom can_handle logic
        for v in self.validators:
            if v.can_handle(filepath) and v not in validators:
                validators.append(v)

        if not validators:
            logger.warning(f"No validators found for {filepath}")
            return results

        # Run each validator
        for validator in validators:
            logger.info(f"Running {validator.name} on {filepath}")
            result = validator.validate(filepath)
            results.append(result)

        return results

    def validate_directory(
        self, directory: Path, recursive: bool = True
    ) -> Dict[str, List[ValidationResult]]:
        """Validate all files in a directory"""
        results = {}

        pattern = "**/*" if recursive else "*"
        for filepath in directory.glob(pattern):
            if filepath.is_file() and not filepath.name.startswith("."):
                file_results = self.validate_file(filepath)
                if file_results:
                    results[str(filepath)] = file_results

        return results

    def validate_staged_files(self) -> Dict[str, List[ValidationResult]]:
        """Validate files staged for git commit"""
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

            results = {}
            for filename in result.stdout.splitlines():
                filepath = Path(filename)
                if filepath.exists():
                    file_results = self.validate_file(filepath)
                    if file_results:
                        results[filename] = file_results

            return results

        except Exception as e:
            logger.error(f"Error validating staged files: {e}")
            return {}

    def get_summary(self, results: Dict[str, List[ValidationResult]]) -> Dict[str, Any]:
        """Generate a summary of validation results"""
        total_files = len(results)
        total_errors = 0
        total_warnings = 0
        failed_files = []

        for filepath, file_results in results.items():
            has_error = False
            for result in file_results:
                total_errors += result.error_count
                total_warnings += result.warning_count
                if not result.success:
                    has_error = True

            if has_error:
                failed_files.append(filepath)

        return {
            "total_files": total_files,
            "passed_files": total_files - len(failed_files),
            "failed_files": len(failed_files),
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "failed_file_list": failed_files,
            "success": len(failed_files) == 0,
        }


# CLI Interface
def main():
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

    args = parser.parse_args()

    # Initialize engine
    engine = ValidationEngine(auto_fix=args.fix, use_container=args.container)

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
            print("✅ ALL VALIDATIONS PASSED")
        else:
            print("❌ VALIDATION FAILED")
        print(f"{'='*60}\n")

    # Exit with appropriate code
    sys.exit(0 if summary["success"] else 1)


if __name__ == "__main__":
    main()
