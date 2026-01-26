#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Ruff Validator - Python fast linter

Uses Ruff (https://github.com/astral-sh/ruff) for fast Python linting.
License: MIT
"""

import json
import time
from pathlib import Path
from typing import Set

from huskycat.validators.base import ValidationResult, Validator


class RuffValidator(Validator):
    """Python fast linter"""

    @property
    def name(self) -> str:
        return "ruff"

    @property
    def extensions(self) -> Set[str]:
        return {".py", ".pyi"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()
        cmd = [self.command, "check", str(filepath), "--output-format=json"]

        # Add --fix flag if auto-fixing is enabled
        if self.auto_fix:
            cmd.insert(2, "--fix")

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

            # Parse JSON output
            messages = []
            errors = []
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    for issue in data:
                        msg = f"Line {issue.get('location', {}).get('row', '?')}: {issue.get('message', 'Unknown error')}"
                        messages.append(msg)
                        errors.append(msg)
                except json.JSONDecodeError:
                    errors = [result.stdout.strip()]
                    messages = [result.stdout.strip()]

            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                messages=messages,
                errors=errors,
                fixed=self.auto_fix and result.returncode == 0,
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
