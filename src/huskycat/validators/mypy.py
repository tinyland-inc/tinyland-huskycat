#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
MyPy Validator - Python type checker

Uses MyPy to check Python code for type errors.
License: MIT
"""

import time
from pathlib import Path
from typing import Set

from huskycat.validators.base import ValidationResult, Validator


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
            result = self._execute_command(
                cmd, capture_output=True, text=True, timeout=30
            )
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
