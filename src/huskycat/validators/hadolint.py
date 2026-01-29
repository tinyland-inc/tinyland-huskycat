#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Hadolint Validator - Dockerfile/ContainerFile linter

Uses Hadolint for comprehensive Dockerfile linting.
License: GPL-3.0 (requires container/sidecar in FAST mode)
"""

import time
from pathlib import Path
from typing import Set

from huskycat.validators.base import ValidationResult, Validator


class HadolintValidator(Validator):
    """Dockerfile/ContainerFile linter"""

    @property
    def name(self) -> str:
        return "hadolint"

    @property
    def command(self) -> str:
        """Command to execute - hadolint binary"""
        return "hadolint"

    @property
    def extensions(self) -> Set[str]:
        # Handle both extensions and specific filenames
        return {".dockerfile"}

    def can_handle(self, filepath: Path) -> bool:
        """Check if this validator can handle the given file"""
        return filepath.suffix in self.extensions or filepath.name in [
            "Dockerfile",
            "ContainerFile",
        ]

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()
        cmd = [self.command, str(filepath)]

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
                    messages=["Container file is valid"],
                    duration_ms=duration_ms,
                )
            else:
                errors = []
                warnings = []

                for line in result.stdout.splitlines():
                    if "DL" in line:  # Hadolint error codes
                        if "error" in line.lower():
                            errors.append(line)
                        else:
                            warnings.append(line)

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
