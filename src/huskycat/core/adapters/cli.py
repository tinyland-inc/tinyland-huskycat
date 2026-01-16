# SPDX-License-Identifier: Apache-2.0
"""
CLI Mode Adapter.

Optimized for interactive terminal use:
- Colored output
- Progress indicators
- Interactive prompts
- Verbose options
"""

import sys

from .base import AdapterConfig, ModeAdapter, OutputFormat


class CLIAdapter(ModeAdapter):
    """
    Adapter for CLI mode.

    Requirements:
    - Interactive feedback: Progress indicators
    - Colored output: Rich terminal experience
    - Auto-fix: --fix flag with prompts
    - File selection: Glob patterns, paths
    - Verbose options: -v, -vv, -vvv
    - Help text: Comprehensive --help
    """

    @property
    def name(self) -> str:
        return "cli"

    @property
    def config(self) -> AdapterConfig:
        return AdapterConfig(
            output_format=OutputFormat.HUMAN,  # Colored, formatted
            interactive=True,  # Prompts enabled
            fail_fast=False,  # Show all issues
            color=sys.stdout.isatty(),  # Auto-detect color
            progress=sys.stderr.isatty(),  # Spinners if TTY
            tools="configured",  # Per .huskycat.yaml
        )

    def format_output(self, results, summary):
        """
        CLI mode: Rich colored output with full details.
        """
        lines = []
        total_errors = summary.get("total_errors", 0)
        total_warnings = summary.get("total_warnings", 0)
        files_checked = summary.get("files_checked", 0)
        fixed_files = summary.get("fixed_files", 0)

        # Header
        lines.append("")
        if self.config.color:
            lines.append("\033[1m━━━ HuskyCat Validation Results ━━━\033[0m")
        else:
            lines.append("━━━ HuskyCat Validation Results ━━━")

        # Summary
        lines.append(f"Files checked: {files_checked}")

        if fixed_files > 0:
            if self.config.color:
                lines.append(f"\033[94mFixed: {fixed_files} files\033[0m")
            else:
                lines.append(f"Fixed: {fixed_files} files")

        # Status
        if total_errors > 0:
            if self.config.color:
                lines.append(f"\033[91m✗ Errors: {total_errors}\033[0m")
            else:
                lines.append(f"✗ Errors: {total_errors}")

        if total_warnings > 0:
            if self.config.color:
                lines.append(f"\033[93m⚠ Warnings: {total_warnings}\033[0m")
            else:
                lines.append(f"⚠ Warnings: {total_warnings}")

        if total_errors == 0 and total_warnings == 0:
            if self.config.color:
                lines.append(f"\033[92m✓ All validations passed!\033[0m")
            else:
                lines.append(f"✓ All validations passed!")

        # Details
        if total_errors > 0 or total_warnings > 0:
            lines.append("")
            lines.append("Details:")

            for filepath, file_results in results.items():
                file_has_issues = False

                for result in file_results:
                    errors = getattr(result, "errors", [])
                    warnings = getattr(result, "warnings", [])

                    if errors or warnings:
                        if not file_has_issues:
                            if self.config.color:
                                lines.append(f"\n\033[1m{filepath}\033[0m")
                            else:
                                lines.append(f"\n{filepath}")
                            file_has_issues = True

                        tool = getattr(result, "tool", "validator")

                        for error in errors:
                            if self.config.color:
                                lines.append(f"  \033[91m✗ [{tool}] {error}\033[0m")
                            else:
                                lines.append(f"  ✗ [{tool}] {error}")

                        for warning in warnings:
                            if self.config.color:
                                lines.append(f"  \033[93m⚠ [{tool}] {warning}\033[0m")
                            else:
                                lines.append(f"  ⚠ [{tool}] {warning}")

        lines.append("")
        return "\n".join(lines)
