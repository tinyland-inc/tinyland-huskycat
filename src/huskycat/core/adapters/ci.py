"""
CI Mode Adapter.

Optimized for pipeline integration:
- Comprehensive validation (all tools)
- Structured output (JUnit XML, JSON)
- No interactivity
- Artifact generation
"""

from .base import AdapterConfig, ModeAdapter, OutputFormat


class CIAdapter(ModeAdapter):
    """
    Adapter for CI mode.

    Requirements:
    - Comprehensive: Run ALL validators
    - Structured output: JUnit XML, JSON reports
    - Exit codes: 0=pass, non-zero=fail
    - Artifacts: Save reports for pipeline artifacts
    - No interactivity: Fully automated
    - Badge-ready: Status for MR badges
    """

    @property
    def name(self) -> str:
        return "ci"

    @property
    def config(self) -> AdapterConfig:
        return AdapterConfig(
            output_format=OutputFormat.JUNIT_XML,  # CI artifact format
            interactive=False,  # Never prompt in CI
            fail_fast=False,  # Run ALL validators, report everything
            color=False,  # No ANSI codes in CI logs
            progress=False,  # No progress spinners
            tools="all",  # Complete toolchain
            report_path="./reports/",  # Artifact directory
        )

    def format_output(self, results, summary):
        """
        CI mode: JUnit XML for pipeline artifacts.
        Also outputs human-readable summary to stderr.
        """
        import sys

        # Human summary to stderr (for CI logs)
        total_errors = summary.get("total_errors", 0)
        total_warnings = summary.get("total_warnings", 0)
        files_checked = summary.get("files_checked", 0)

        sys.stderr.write(f"HuskyCat CI Validation: {files_checked} files\n")
        sys.stderr.write(f"  Errors: {total_errors}\n")
        sys.stderr.write(f"  Warnings: {total_warnings}\n")
        sys.stderr.flush()

        # JUnit XML to stdout
        return super()._format_junit_xml(results, summary)

    def get_tool_selection(self):
        """CI runs all tools for comprehensive coverage."""
        return ["all"]
