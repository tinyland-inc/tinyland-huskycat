# SPDX-License-Identifier: Apache-2.0
"""
History command for viewing validation run history.

Provides CLI access to validation history, matching MCP tool parity:
- get_last_run
- get_run_history
- get_run_results
"""

import json
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

from ..core.base import BaseCommand, CommandResult, CommandStatus
from ..core.process_manager import ProcessManager, ValidationRun


class HistoryCommand(BaseCommand):
    """Command for viewing validation run history."""

    name = "history"
    description = "Show validation run history"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.process_manager = ProcessManager()

    def execute(
        self,
        last: bool = False,
        run_id: Optional[str] = None,
        limit: int = 10,
        **kwargs,
    ) -> CommandResult:
        """
        Execute history command.

        Args:
            last: Show only the most recent run
            run_id: Show details for a specific run ID
            limit: Maximum number of runs to show

        Returns:
            CommandResult with history data
        """
        # Show specific run by ID
        if run_id:
            return self._show_run_details(run_id)

        # Show last run only
        if last:
            return self._show_last_run()

        # Show run history
        return self._show_history(limit)

    def _show_last_run(self) -> CommandResult:
        """Show the most recent validation run."""
        # First check the last_run file
        run = None
        last_run_file = self.process_manager.last_run_file
        if last_run_file.exists():
            try:
                data = json.loads(last_run_file.read_text())
                run = ValidationRun(**data)
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

        # If no last run, check history
        if run is None:
            history = self.process_manager.get_run_history(limit=1)
            if history:
                run = history[0]

        if run is None:
            return CommandResult(
                status=CommandStatus.SUCCESS,
                message="No validation runs found",
                output="No validation runs found. Run 'huskycat validate' to create a validation record.",
                data={"found": False},
            )

        # Load detailed results if available
        run_data = self._load_run_details(run)

        # Format output
        output_lines = [
            f"Last Run: {run.run_id}",
            f"  Status: {'PASS' if run.success else 'FAIL'}",
            f"  Started: {run.start_time}",
            f"  Completed: {run.end_time or 'in progress'}",
            f"  Tool: {run.tool_name}",
            f"  Errors: {run.error_count}",
            f"  Warnings: {run.warning_count}",
        ]

        if run_data.get("log_content"):
            output_lines.append("\nLog Output (last 50 lines):")
            log_lines = run_data["log_content"].split("\n")
            output_lines.extend(f"  {line}" for line in log_lines[-50:])

        return CommandResult(
            status=CommandStatus.SUCCESS if run.success else CommandStatus.WARNING,
            message=f"Last run: {run.run_id}",
            output="\n".join(output_lines),
            data=run_data,
        )

    def _show_history(self, limit: int) -> CommandResult:
        """Show validation run history."""
        limit = min(max(1, limit), 100)
        runs = self.process_manager.get_run_history(limit=limit)

        if not runs:
            return CommandResult(
                status=CommandStatus.SUCCESS,
                message="No validation runs found",
                output="No validation runs found. Run 'huskycat validate' to create a validation record.",
                data={"count": 0, "runs": []},
            )

        # Format output
        output_lines = [f"Validation History (showing {len(runs)} of {limit} max):"]
        output_lines.append("-" * 70)
        output_lines.append(f"{'Run ID':<30} {'Status':<8} {'Errors':<8} {'Tool':<20}")
        output_lines.append("-" * 70)

        for run in runs:
            status = "PASS" if run.success else "FAIL"
            output_lines.append(
                f"{run.run_id:<30} {status:<8} {run.error_count:<8} {run.tool_name:<20}"
            )

        output_lines.append("-" * 70)
        output_lines.append(f"Total: {len(runs)} runs")

        return CommandResult(
            status=CommandStatus.SUCCESS,
            message=f"Found {len(runs)} validation runs",
            output="\n".join(output_lines),
            data={
                "count": len(runs),
                "limit": limit,
                "runs": [asdict(r) for r in runs],
            },
        )

    def _show_run_details(self, run_id: str) -> CommandResult:
        """Show details for a specific run."""
        # Look for the run file
        run_file = self.process_manager.cache_dir / f"{run_id}.json"
        if not run_file.exists():
            return CommandResult(
                status=CommandStatus.FAILED,
                message=f"Run not found: {run_id}",
                output=f"No validation run found with ID: {run_id}",
                errors=[f"Run ID '{run_id}' not found"],
                data={"found": False, "run_id": run_id},
            )

        try:
            run_data = json.loads(run_file.read_text())
            run = ValidationRun(**run_data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                message=f"Could not parse run file: {e}",
                errors=[str(e)],
            )

        # Load detailed results
        run_details = self._load_run_details(run)

        # Format output
        output_lines = [
            f"Run Details: {run.run_id}",
            "=" * 50,
            f"  Status: {'PASS' if run.success else 'FAIL'}",
            f"  Started: {run.start_time}",
            f"  Completed: {run.end_time or 'in progress'}",
            f"  Tool: {run.tool_name}",
            f"  PID: {run.pid}",
            f"  Errors: {run.error_count}",
            f"  Warnings: {run.warning_count}",
        ]

        if run_details.get("detailed_results"):
            output_lines.append("\nDetailed Results:")
            for filepath, results in run_details["detailed_results"].items():
                output_lines.append(f"\n  {filepath}:")
                if isinstance(results, list):
                    for result in results[:10]:  # Limit to 10 per file
                        if isinstance(result, dict):
                            line = result.get("line", "?")
                            msg = result.get("message", str(result))
                            output_lines.append(f"    Line {line}: {msg}")

        if run_details.get("log_content"):
            output_lines.append("\nLog Output:")
            log_lines = run_details["log_content"].split("\n")
            output_lines.extend(f"  {line}" for line in log_lines[-100:])

        return CommandResult(
            status=CommandStatus.SUCCESS if run.success else CommandStatus.WARNING,
            message=f"Run details: {run.run_id}",
            output="\n".join(output_lines),
            data=run_details,
        )

    def _load_run_details(self, run: ValidationRun) -> dict:
        """Load detailed results and logs for a run."""
        result = {
            "found": True,
            "run": asdict(run),
            "detailed_results": None,
            "log_content": None,
        }

        # Load detailed results if available
        results_file = self.process_manager.cache_dir / f"{run.run_id}_results.json"
        if results_file.exists():
            try:
                result["detailed_results"] = json.loads(results_file.read_text())
            except Exception:
                pass

        # Load log file content if available
        log_file = self.process_manager.logs_dir / f"{run.run_id}.log"
        if log_file.exists():
            try:
                log_content = log_file.read_text()
                # Truncate if too long
                if len(log_content) > 10000:
                    log_content = log_content[-10000:] + "\n... [truncated]"
                result["log_content"] = log_content
            except Exception:
                pass

        return result
