#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Taplo Validator - TOML file formatter

Uses Taplo (https://github.com/tamasfe/taplo) for TOML formatting.
License: MIT
"""

import time
from pathlib import Path
from typing import Set

from huskycat.validators.base import ValidationResult, Validator


class TaploValidator(Validator):
    """TOML file formatter using taplo"""

    @property
    def name(self) -> str:
        return "taplo"

    @property
    def extensions(self) -> Set[str]:
        return {".toml"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()

        # First check what taplo would format (dry run with --check)
        check_cmd = [
            self.command,
            "fmt",
            "--check",
            str(filepath),
        ]

        try:
            result = self._execute_command(
                check_cmd, capture_output=True, text=True, timeout=30
            )
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                # File is already formatted
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["TOML file is properly formatted"],
                    duration_ms=duration_ms,
                )
            else:
                # File needs formatting
                if self.auto_fix:
                    # Apply formatting
                    fix_cmd = [
                        self.command,
                        "fmt",
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
                            messages=["Formatted TOML file"],
                            fixed=True,
                            duration_ms=duration_ms,
                        )
                    else:
                        # Formatting failed
                        error_output = (
                            fix_result.stderr
                            if fix_result.stderr
                            else fix_result.stdout
                        )
                        errors = (
                            [
                                line.strip()
                                for line in error_output.splitlines()
                                if line.strip()
                            ]
                            if error_output
                            else ["Failed to format TOML file"]
                        )
                        return ValidationResult(
                            tool=self.name,
                            filepath=str(filepath),
                            success=False,
                            errors=errors[:10],  # Limit to first 10 errors
                            messages=["Failed to format TOML file"],
                            duration_ms=duration_ms,
                        )
                else:
                    # Just report that formatting is needed
                    output = result.stdout if result.stdout else result.stderr
                    messages = []
                    if output:
                        # taplo --check shows which files need formatting
                        messages = [
                            line.strip() for line in output.splitlines() if line.strip()
                        ][:5]

                    if not messages:
                        messages = [
                            "TOML file needs formatting. Run with --fix to format."
                        ]

                    return ValidationResult(
                        tool=self.name,
                        filepath=str(filepath),
                        success=False,
                        errors=["TOML file is not properly formatted"],
                        messages=messages,
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
