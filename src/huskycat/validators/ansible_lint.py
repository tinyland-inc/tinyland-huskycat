#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Ansible Lint Validator - Ansible playbook and role linter

Uses ansible-lint to check Ansible playbooks and roles.
License: MIT
"""

import time
from pathlib import Path
from typing import Set

from huskycat.validators.base import ValidationResult, Validator


class AnsibleLintValidator(Validator):
    """Ansible playbook and role linter with auto-fix support"""

    @property
    def name(self) -> str:
        return "ansible-lint"

    @property
    def extensions(self) -> Set[str]:
        # Return empty set - use can_handle() method to detect Ansible files
        return set()

    def can_handle(self, filepath: Path) -> bool:
        """Check if file is an Ansible file (playbook, role, task, etc.)"""
        # Only handle files in ansible-specific directories or with ansible patterns
        path_str = str(filepath).lower()
        ansible_indicators = [
            "/playbooks/",
            "/roles/",
            "/tasks/",
            "/handlers/",
            "/vars/",
            "/defaults/",
            "/meta/",
            "playbook",
            "site.yml",
            "site.yaml",
        ]
        return any(indicator in path_str for indicator in ansible_indicators)

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()

        # ansible-lint command
        check_cmd = [
            self.command,
            "--nocolor",
            "--parseable",
            str(filepath),
        ]

        try:
            result = self._execute_command(
                check_cmd, capture_output=True, text=True, timeout=60
            )
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                # No issues found
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["Ansible playbook/role passed all checks"],
                    duration_ms=duration_ms,
                )
            else:
                # Parse ansible-lint output (ansible-lint writes to stderr)
                issues = []
                output = result.stderr if result.stderr else result.stdout
                if output:
                    # Filter to only the actual lint violations (lines with file:line:col format)
                    issues = [
                        line.strip()
                        for line in output.splitlines()
                        if line.strip()
                        and not line.startswith("WARNING")
                        and not line.startswith("#")
                        and not line.startswith("Read")
                        and not line.startswith("Failed:")
                        and ":" in line
                    ]

                if self.auto_fix:
                    # Try to fix issues
                    fix_cmd = [
                        self.command,
                        "--fix",
                        "--nocolor",
                        str(filepath),
                    ]
                    fix_result = self._execute_command(
                        fix_cmd, capture_output=True, text=True, timeout=60
                    )

                    if fix_result.returncode == 0:
                        return ValidationResult(
                            tool=self.name,
                            filepath=str(filepath),
                            success=True,
                            messages=["Fixed Ansible lint issues"],
                            fixed=True,
                            duration_ms=duration_ms,
                        )
                    else:
                        # Some issues couldn't be fixed
                        remaining_issues = []
                        fix_output = (
                            fix_result.stderr
                            if fix_result.stderr
                            else fix_result.stdout
                        )
                        if fix_output:
                            # Filter to only the actual lint violations
                            remaining_issues = [
                                line.strip()
                                for line in fix_output.splitlines()
                                if line.strip()
                                and not line.startswith("WARNING")
                                and not line.startswith("#")
                                and not line.startswith("Read")
                                and not line.startswith("Failed:")
                                and ":" in line
                            ]

                        return ValidationResult(
                            tool=self.name,
                            filepath=str(filepath),
                            success=False,
                            errors=remaining_issues or issues,
                            messages=["Some issues could not be auto-fixed"],
                            fixed=len(remaining_issues) < len(issues),
                            duration_ms=duration_ms,
                        )
                else:
                    # Just report issues
                    return ValidationResult(
                        tool=self.name,
                        filepath=str(filepath),
                        success=False,
                        errors=issues[:20],  # Limit to first 20 issues
                        messages=[
                            f"Found {len(issues)} Ansible lint issues. Run with --fix to auto-fix."
                        ],
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
