#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
ESLint Validator - JavaScript/TypeScript linter

Uses ESLint to lint JavaScript and TypeScript code.
License: MIT
"""

import json
import time
from pathlib import Path
from typing import Set

from huskycat.validators.base import ValidationResult, Validator


class ESLintValidator(Validator):
    """JavaScript/TypeScript linter"""

    @property
    def name(self) -> str:
        return "js-eslint"

    @property
    def extensions(self) -> Set[str]:
        return {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()
        cmd = [self.command, str(filepath), "--format=json"]

        if self.auto_fix:
            cmd.insert(1, "--fix")

        try:
            result = self._execute_command(
                cmd, capture_output=True, text=True, timeout=30
            )
            duration_ms = int((time.time() - start_time) * 1000)

            try:
                data = json.loads(result.stdout) if result.stdout else []
                file_result = data[0] if data else {}

                errors = [
                    msg
                    for msg in file_result.get("messages", [])
                    if msg.get("severity") == 2
                ]
                warnings = [
                    msg
                    for msg in file_result.get("messages", [])
                    if msg.get("severity") == 1
                ]

                if not errors:
                    return ValidationResult(
                        tool=self.name,
                        filepath=str(filepath),
                        success=True,
                        warnings=[w.get("message", "") for w in warnings],
                        fixed=self.auto_fix,
                        duration_ms=duration_ms,
                    )
                else:
                    return ValidationResult(
                        tool=self.name,
                        filepath=str(filepath),
                        success=False,
                        errors=[e.get("message", "") for e in errors],
                        warnings=[w.get("message", "") for w in warnings],
                        duration_ms=duration_ms,
                    )
            except json.JSONDecodeError:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=result.returncode == 0,
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
