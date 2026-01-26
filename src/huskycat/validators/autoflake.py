#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Autoflake Validator - Python import and unused variable cleaner

Uses Autoflake to remove unused imports and variables from Python code.
License: MIT
"""

import time
from pathlib import Path
from typing import Set

from huskycat.validators.base import ValidationResult, Validator


class AutoflakeValidator(Validator):
    """Python import and unused variable cleaner"""

    @property
    def name(self) -> str:
        return "autoflake"

    @property
    def extensions(self) -> Set[str]:
        return {".py", ".pyi"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()

        # First check what autoflake would fix (dry run)
        check_cmd = [
            self.command,
            "--check",
            "--remove-all-unused-imports",
            "--remove-unused-variables",
            str(filepath),
        ]

        try:
            result = self._execute_command(
                check_cmd, capture_output=True, text=True, timeout=30
            )
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                # No changes needed
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["No unused imports or variables found"],
                    duration_ms=duration_ms,
                )
            else:
                # File needs fixing
                if self.auto_fix:
                    # Apply fixes
                    fix_cmd = [
                        self.command,
                        "--in-place",
                        "--remove-all-unused-imports",
                        "--remove-unused-variables",
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
                            messages=["Fixed unused imports and variables"],
                            fixed=True,
                            duration_ms=duration_ms,
                        )
                    else:
                        return ValidationResult(
                            tool=self.name,
                            filepath=str(filepath),
                            success=False,
                            errors=["Failed to apply autoflake fixes"],
                            messages=(
                                fix_result.stderr.splitlines()
                                if fix_result.stderr
                                else []
                            ),
                            duration_ms=duration_ms,
                        )
                else:
                    # Just report issues without fixing
                    return ValidationResult(
                        tool=self.name,
                        filepath=str(filepath),
                        success=False,
                        errors=["File has unused imports or variables"],
                        messages=["Run with --fix to automatically clean up"],
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
