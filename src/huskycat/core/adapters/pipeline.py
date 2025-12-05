"""
Pipeline Mode Adapter.

Optimized for toolchain integration:
- Machine-readable JSON output
- stdin/stdout friendly
- No interactivity
- Predictable behavior
"""

from .base import AdapterConfig, ModeAdapter, OutputFormat


class PipelineAdapter(ModeAdapter):
    """
    Adapter for Pipeline mode.

    Requirements:
    - Composable: stdin/stdout friendly
    - Machine-readable: JSON output
    - Non-interactive: Never prompt
    - Scriptable: Predictable behavior
    - Exit codes: Semantic (0, 1, 2, etc.)
    - No side effects: Read-only by default
    """

    @property
    def name(self) -> str:
        return "pipeline"

    @property
    def config(self) -> AdapterConfig:
        return AdapterConfig(
            output_format=OutputFormat.JSON,  # Machine-readable
            interactive=False,  # Never prompt
            fail_fast=False,  # Complete run for full report
            color=False,  # No ANSI codes
            progress=False,  # No spinners
            tools="all",  # Complete toolchain
            stdin_mode=True,  # Accept file list from stdin
        )

    def format_output(self, results, summary):
        """
        Pipeline mode: Clean JSON output to stdout.

        Designed to pipe to tools like jq:
            huskycat validate src/ | jq '.summary.total_errors'
        """
        return super()._format_json(results, summary)

    def get_exit_code(self, summary):
        """
        Get semantic exit code for pipeline scripting.

        Exit codes:
        - 0: All validations passed
        - 1: Validation errors found
        - 2: Validation warnings (but no errors)
        - 3: No files to validate
        - 4: Tool/configuration error
        """
        total_errors = summary.get("total_errors", 0)
        total_warnings = summary.get("total_warnings", 0)
        files_checked = summary.get("files_checked", 0)

        if files_checked == 0:
            return 3
        elif total_errors > 0:
            return 1
        elif total_warnings > 0:
            return 2
        else:
            return 0
