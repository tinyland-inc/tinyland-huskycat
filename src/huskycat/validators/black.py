#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Black Validator - Python code formatter

Uses Black (https://github.com/psf/black) to check and format Python code.
License: MIT
"""

import time
from pathlib import Path
from typing import Set

from huskycat.validators.base import ValidationResult, Validator


class BlackValidator(Validator):
    """Python code formatter"""

    @property
    def name(self) -> str:
        return "python-black"

    @property
    def extensions(self) -> Set[str]:
        return {".py", ".pyi"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()
        cmd = [self.command, "--check", str(filepath)]

        if self.auto_fix:
            cmd.remove("--check")

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
