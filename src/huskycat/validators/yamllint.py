#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
YAMLLint Validator - YAML linter

Uses yamllint to check YAML files for syntax and style issues.
License: GPL-3.0 (requires container/sidecar in FAST mode)
"""

import logging
import time
from pathlib import Path
from typing import Set

from huskycat.validators.base import ValidationResult, Validator

logger = logging.getLogger(__name__)


class YamlLintValidator(Validator):
    """YAML linter with auto-fix for trailing spaces and newlines"""

    @property
    def name(self) -> str:
        return "yamllint"

    @property
    def extensions(self) -> Set[str]:
        return {".yaml", ".yml"}

    def _auto_fix_yaml(self, filepath: Path) -> bool:
        """Auto-fix common YAML issues like trailing spaces and missing newlines"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Fix trailing spaces
            lines = content.splitlines()
            lines = [line.rstrip() for line in lines]

            # Ensure file ends with newline
            content = "\n".join(lines)
            if content and not content.endswith("\n"):
                content += "\n"

            # Write back if changed
            if content != original_content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                return True

            return False
        except Exception as e:
            logger.warning(f"Failed to auto-fix {filepath}: {e}")
            return False

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()

        # If auto-fix is enabled, try to fix common issues first
        fixed = False
        if self.auto_fix:
            fixed = self._auto_fix_yaml(filepath)

        cmd = [self.command, "-f", "parsable", str(filepath)]

        try:
            result = self._execute_command(
                cmd, capture_output=True, text=True, timeout=30
            )
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["YAML is valid"],
                    fixed=fixed,
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
