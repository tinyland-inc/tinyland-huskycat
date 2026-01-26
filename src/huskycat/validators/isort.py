#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Isort Validator - Python import sorting and organization

Uses isort to check and sort Python imports.
License: MIT
"""

import time
from pathlib import Path
from typing import Set

from huskycat.validators.base import ValidationResult, Validator


class IsortValidator(Validator):
    """Python import sorting and organization"""

    @property
    def name(self) -> str:
        return "isort"

    @property
    def extensions(self) -> Set[str]:
        return {".py", ".pyi"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()

        # First check what isort would fix (dry run)
        check_cmd = [
            self.command,
            "--check-only",
            "--diff",
            str(filepath),
        ]

        try:
            result = self._execute_command(
                check_cmd, capture_output=True, text=True, timeout=30
            )
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                # Imports are already sorted
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["Imports are properly sorted"],
                    duration_ms=duration_ms,
                )
            else:
                # Imports need sorting
                if self.auto_fix:
                    # Apply fixes (isort modifies in-place by default)
                    fix_cmd = [
                        self.command,
                        str(filepath),
                    ]
                    fix_result = self._execute_command(
                        fix_cmd, capture_output=True, text=True, timeout=30
                    )

                    if fix_result.returncode == 0:
                        return ValidationResult(
                            tool=self.name,
                            filepath=str(filepath),
                            success=True,
                            messages=["Sorted and organized imports"],
                            fixed=True,
                            duration_ms=duration_ms,
                        )
                    else:
                        return ValidationResult(
                            tool=self.name,
                            filepath=str(filepath),
                            success=False,
                            errors=["Failed to sort imports"],
                            messages=(
                                fix_result.stderr.splitlines()
                                if fix_result.stderr
                                else []
                            ),
                            duration_ms=duration_ms,
                        )
                else:
                    # Just report issues without fixing
                    diff_lines = result.stdout.splitlines() if result.stdout else []
                    return ValidationResult(
                        tool=self.name,
                        filepath=str(filepath),
                        success=False,
                        errors=["Imports are not properly sorted"],
                        messages=(
                            diff_lines[:10]
                            if diff_lines
                            else ["Run with --fix to sort imports"]
                        ),
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
