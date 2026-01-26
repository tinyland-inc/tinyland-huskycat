#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Flake8 Validator - Python linter

Uses Flake8 to check Python code for style and programming errors.
License: MIT
"""

import time
from pathlib import Path
from typing import Set

from huskycat.validators.base import ValidationResult, Validator


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
            result = self._execute_command(
                cmd, capture_output=True, text=True, timeout=30
            )
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
