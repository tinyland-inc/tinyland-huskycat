#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Chapel Validator - Chapel code formatter

Custom implementation for Chapel programming language formatting.
No compiler required - pure Python implementation.
"""

import time
from pathlib import Path
from typing import Set

from huskycat.validators.base import ValidationResult, Validator


class ChapelValidator(Validator):
    """Chapel code formatter (custom implementation, no compiler required)"""

    @property
    def name(self) -> str:
        return "chapel"

    @property
    def extensions(self) -> Set[str]:
        return {".chpl"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()

        try:
            # Import Chapel formatter
            from huskycat.formatters.chapel import ChapelFormatter

            # Read file
            with open(filepath, "r", encoding="utf-8") as f:
                original_code = f.read()

            # Format code
            formatter = ChapelFormatter()
            formatted_code = formatter.format(original_code)

            duration_ms = int((time.time() - start_time) * 1000)

            # Check if formatting changed anything
            if formatted_code == original_code:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    duration_ms=duration_ms,
                )

            # If auto-fix enabled, write the formatted code
            if self.auto_fix:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(formatted_code)

                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    fixed=True,
                    messages=["Chapel code formatted"],
                    duration_ms=duration_ms,
                )
            else:
                # Report formatting issues without fixing
                issues = formatter.check_formatting(original_code)
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=False,
                    errors=issues,
                    messages=[f"Chapel formatting issues found: {len(issues)}"],
                    duration_ms=duration_ms,
                )

        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[f"Chapel validation error: {str(e)}"],
                duration_ms=int((time.time() - start_time) * 1000),
            )
