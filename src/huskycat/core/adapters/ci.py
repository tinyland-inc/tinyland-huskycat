# SPDX-License-Identifier: Apache-2.0
"""
CI Mode Adapter.

Optimized for pipeline integration:
- Comprehensive validation (all tools)
- Structured output (JUnit XML, JSON)
- No interactivity
- Artifact generation
- Result persistence for MCP access
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..process_manager import ProcessManager, ValidationRun
from .base import AdapterConfig, ModeAdapter, OutputFormat

logger = logging.getLogger(__name__)


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
    - Result persistence: Save to .huskycat/results/ for MCP access
    """

    def __init__(self) -> None:
        """Initialize CI adapter with ProcessManager for result storage."""
        super().__init__()
        self.process_manager = ProcessManager()

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

    def format_output(
        self, results: dict[str, Any], summary: dict[str, Any]
    ) -> str:
        """
        CI mode: JUnit XML for pipeline artifacts.
        Also outputs human-readable summary to stderr.
        Saves results to shared store for MCP access.
        """
        # Save to shared result store FIRST (before stdout output)
        self._save_to_result_store(results, summary)

        # Human summary to stderr (for CI logs)
        total_errors = summary.get("total_errors", 0)
        total_warnings = summary.get("total_warnings", 0)
        files_checked = summary.get("files_checked", 0)

        sys.stderr.write(f"HuskyCat CI Validation: {files_checked} files\n")
        sys.stderr.write(f"  Errors: {total_errors}\n")
        sys.stderr.write(f"  Warnings: {total_warnings}\n")
        sys.stderr.write("  Results saved to .huskycat/results/\n")
        sys.stderr.flush()

        # JUnit XML to stdout (for pipeline artifacts)
        return super()._format_junit_xml(results, summary)

    def _save_to_result_store(
        self, results: dict[str, Any], summary: dict[str, Any]
    ) -> None:
        """
        Save CI results to shared result store for MCP access.

        Creates timestamped result files and a 'latest.json' for easy access.
        Also stores metadata via ProcessManager for run history.

        Args:
            results: Per-file validation results
            summary: Aggregated summary statistics
        """
        now = datetime.now(tz=timezone.utc)
        run_id = now.strftime("%Y%m%d_%H%M%S_%f")

        # Create results directory (separate from runs for clarity)
        results_dir = Path.cwd() / ".huskycat" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)

        # Collect detailed errors/warnings
        error_details = self._extract_issues(results, "errors", "error")
        warning_details = self._extract_issues(results, "warnings", "warning")

        # Build detailed results structure
        detailed_results = {
            "run_id": run_id,
            "mode": "ci",
            "timestamp": now.isoformat(),
            "summary": summary,
            "error_details": error_details,
            "warning_details": warning_details,
            "results": self._serialize_results(results),
        }

        # Write timestamped results file
        results_file = results_dir / f"{run_id}_results.json"
        try:
            results_file.write_text(json.dumps(detailed_results, indent=2))
            logger.debug("Saved CI results to %s", results_file)
        except OSError:
            logger.exception("Failed to save results file")

        # Update latest.json for easy access
        latest_file = results_dir / "latest.json"
        try:
            latest_file.write_text(json.dumps(detailed_results, indent=2))
            logger.debug("Updated latest results at %s", latest_file)
        except OSError:
            logger.exception("Failed to update latest results")

        # Also save run metadata via ProcessManager for run history
        tools_run = self._extract_tools_run(results)
        run = ValidationRun(
            run_id=run_id,
            started=now.isoformat(),
            completed=now.isoformat(),
            files=list(results.keys()),
            success=summary.get("total_errors", 0) == 0,
            tools_run=tools_run,
            errors=summary.get("total_errors", 0),
            warnings=summary.get("total_warnings", 0),
            exit_code=0 if summary.get("total_errors", 0) == 0 else 1,
        )
        self.process_manager.save_run(run)

    def _extract_issues(
        self,
        results: dict[str, Any],
        attr_name: str,
        severity: str,
    ) -> list[dict[str, Any]]:
        """
        Extract error or warning details from results.

        Args:
            results: Per-file validation results
            attr_name: Attribute to extract ("errors" or "warnings")
            severity: Severity label for the issues

        Returns:
            List of issue detail dictionaries
        """
        details: list[dict[str, Any]] = []
        for filepath, file_results in results.items():
            for result in file_results:
                tool = self._get_tool_name(result)
                if isinstance(result, dict):
                    issues = result.get(attr_name, [])
                elif hasattr(result, attr_name):
                    issues = getattr(result, attr_name, [])
                else:
                    issues = []

                for issue in issues:
                    details.append({
                        "file": filepath,
                        "tool": tool,
                        "message": str(issue),
                        "severity": severity,
                    })
        return details

    def _get_tool_name(self, result: Any) -> str:
        """Extract tool name from a result object or dict."""
        if isinstance(result, dict):
            return result.get("tool", "unknown")
        return getattr(result, "tool", "unknown")

    def _serialize_results(
        self, results: dict[str, Any]
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Serialize results to JSON-compatible format.

        Args:
            results: Per-file validation results

        Returns:
            Serialized results dictionary
        """
        serialized: dict[str, list[dict[str, Any]]] = {}
        for filepath, file_results in results.items():
            serialized[filepath] = []
            for result in file_results:
                if isinstance(result, dict):
                    serialized[filepath].append(result)
                elif hasattr(result, "to_dict"):
                    serialized[filepath].append(result.to_dict())
                else:
                    # Fallback serialization
                    serialized[filepath].append({
                        "tool": getattr(result, "tool", "unknown"),
                        "success": getattr(result, "success", True),
                        "errors": getattr(result, "errors", []),
                        "warnings": getattr(result, "warnings", []),
                    })
        return serialized

    def _extract_tools_run(self, results: dict[str, Any]) -> list[str]:
        """
        Extract unique list of tools that were run.

        Args:
            results: Per-file validation results

        Returns:
            List of unique tool names
        """
        tools = set()
        for file_results in results.values():
            for result in file_results:
                tools.add(self._get_tool_name(result))
        return list(tools)

    def get_tool_selection(self) -> list[str]:
        """CI runs all tools for comprehensive coverage."""
        return ["all"]
