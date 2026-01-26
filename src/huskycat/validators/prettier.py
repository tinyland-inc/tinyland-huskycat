#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Prettier Validator - JavaScript/TypeScript code formatter

Uses Prettier to check and format JavaScript, TypeScript, and other files.
License: MIT
"""

import time
from pathlib import Path
from typing import Set

from huskycat.validators.base import ValidationResult, Validator


class PrettierValidator(Validator):
    """JavaScript/TypeScript code formatter"""

    @property
    def name(self) -> str:
        return "js-prettier"

    @property
    def extensions(self) -> Set[str]:
        return {".js", ".jsx", ".ts", ".tsx", ".json", ".css", ".scss", ".html", ".md"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()

        # Use --write for auto-fix, --check for validation only
        if self.auto_fix:
            cmd = [self.command, "--write", str(filepath)]
        else:
            cmd = [self.command, "--check", str(filepath)]

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
                    fixed=self.auto_fix,
                    duration_ms=duration_ms,
                )

            # Prettier returns non-zero if files need formatting
            messages = []
            errors = []
            if result.stdout:
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if line.strip():
                        msg = f"Code formatting: {line}"
                        messages.append(msg)
                        errors.append(msg)

            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                messages=messages,
                errors=errors,
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
