#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Bandit Validator - Python security vulnerability scanner

Uses Bandit to scan Python code for common security issues.
License: Apache-2.0
"""

import json
import time
from pathlib import Path
from typing import Set

from huskycat.validators.base import ValidationResult, Validator


class BanditValidator(Validator):
    """Python security vulnerability scanner"""

    @property
    def name(self) -> str:
        return "bandit"

    @property
    def extensions(self) -> Set[str]:
        return {".py", ".pyi"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()
        cmd = [self.command, "-f", "json", str(filepath)]

        try:
            result = self._execute_command(
                cmd, capture_output=True, text=True, timeout=30
            )

            duration_ms = int((time.time() - start_time) * 1000)

            # Bandit returns 0 for no issues, 1 for issues found
            if result.returncode == 0:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    duration_ms=duration_ms,
                )

            # Parse JSON output
            messages = []
            errors = []
            warnings = []
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    results = data.get("results", [])
                    for issue in results:
                        msg = f"Line {issue.get('line_number', '?')}: {issue.get('test_name', 'Unknown')} - {issue.get('issue_text', 'Security issue')}"
                        messages.append(msg)

                        severity = issue.get("issue_severity", "MEDIUM")
                        if severity in ["HIGH", "CRITICAL"]:
                            errors.append(msg)
                        else:
                            warnings.append(msg)

                except json.JSONDecodeError:
                    errors = [result.stdout.strip()]
                    messages = [result.stdout.strip()]

            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                messages=messages,
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
