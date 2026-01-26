#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
GitLab CI Validator - GitLab CI YAML file validator

Validates GitLab CI YAML files using official schema.
"""

import os
import sys
import time
from pathlib import Path
from typing import Set

from huskycat.validators.base import ValidationResult, Validator


class GitLabCIValidator(Validator):
    """Validator for GitLab CI YAML files using official schema"""

    @property
    def name(self) -> str:
        return "gitlab-ci"

    @property
    def extensions(self) -> Set[str]:
        return set()  # Use can_handle method instead of extension-based matching

    def is_available(self) -> bool:
        """Check if GitLab CI validator is available"""
        try:
            pass

            return True
        except ImportError:
            return False

    def can_handle(self, filepath: Path) -> bool:
        """Check if this file is a GitLab CI file"""
        name = filepath.name
        parent_path = str(filepath.parent)

        # Specific GitLab CI files
        if name == ".gitlab-ci.yml" or name.startswith(".gitlab-ci"):
            return True

        # Files in .gitlab/ci/ directory that are YAML files
        if (".gitlab/ci" in parent_path or parent_path.endswith(".gitlab/ci")) and (
            name.endswith(".yml") or name.endswith(".yaml")
        ):
            return True

        return False

    def validate(self, filepath: Path) -> ValidationResult:
        """Validate GitLab CI YAML file against official schema"""
        start_time = time.time()

        # Try to import the GitLab CI validator
        GitLabCISchemaValidator = None

        # Multiple import strategies
        current_dir = os.path.dirname(os.path.dirname(__file__))  # huskycat dir
        try:
            sys.path.insert(0, current_dir)
            import gitlab_ci_validator  # type: ignore

            GitLabCISchemaValidator = gitlab_ci_validator.GitLabCISchemaValidator
            sys.path.pop(0)
        except Exception:
            # Try other import strategies
            for import_strategy in [
                lambda: __import__(
                    "huskycat.gitlab_ci_validator", fromlist=["GitLabCISchemaValidator"]
                ).GitLabCISchemaValidator,
                lambda: __import__(
                    "src.huskycat.gitlab_ci_validator",
                    fromlist=["GitLabCISchemaValidator"],
                ).GitLabCISchemaValidator,
                lambda: getattr(
                    __import__("gitlab_ci_validator"), "GitLabCISchemaValidator"
                ),
            ]:
                try:
                    GitLabCISchemaValidator = import_strategy()
                    break
                except (ImportError, ModuleNotFoundError, AttributeError):
                    continue

        if GitLabCISchemaValidator is None:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[
                    "GitLab CI validator not installed. Install with: pip install jsonschema pyyaml requests"
                ],
                duration_ms=int((time.time() - start_time) * 1000),
            )

        try:
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

        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[f"Validation error: {str(e)}"],
                duration_ms=int((time.time() - start_time) * 1000),
            )
