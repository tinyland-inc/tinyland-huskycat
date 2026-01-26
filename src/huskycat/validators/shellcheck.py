#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Shellcheck Validator - Shell script linter

Uses Shellcheck for shell script analysis.
License: GPL-3.0 (requires container/sidecar in FAST mode)
"""

import json
import time
from pathlib import Path
from typing import Set

from huskycat.validators.base import ValidationResult, Validator


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
            result = self._execute_command(
                cmd, capture_output=True, text=True, timeout=30
            )
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
