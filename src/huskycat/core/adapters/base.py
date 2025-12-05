"""
Base Mode Adapter for HuskyCat.

The ModeAdapter pattern encapsulates mode-specific behavior:
- Output formatting
- Interactivity settings
- Tool selection
- Error handling strategies
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class OutputFormat(Enum):
    """Output format options."""

    MINIMAL = "minimal"  # Errors only (git hooks)
    HUMAN = "human"  # Colored, formatted (CLI)
    JSON = "json"  # Machine-readable (pipeline)
    JUNIT_XML = "junit_xml"  # CI artifact format
    JSONRPC = "jsonrpc"  # MCP protocol


class FixConfidence(Enum):
    """Confidence level for auto-fix operations.

    Used to determine whether to apply fixes automatically or prompt user.

    Levels:
    - SAFE: Formatting changes that cannot change semantics (black, prettier)
    - LIKELY: Code style fixes that are usually safe (autoflake import removal)
    - UNCERTAIN: Semantic changes that need human review
    """

    SAFE = "safe"  # Always safe to apply (formatting)
    LIKELY = "likely"  # Usually safe (style fixes)
    UNCERTAIN = "uncertain"  # Needs human review


# Tool confidence mapping - which tools produce which confidence fixes
TOOL_FIX_CONFIDENCE = {
    "python-black": FixConfidence.SAFE,  # Formatting only
    "js-prettier": FixConfidence.SAFE,  # Formatting only
    "autoflake": FixConfidence.LIKELY,  # Import removal
    "ruff": FixConfidence.LIKELY,  # Style fixes
    "yamllint": FixConfidence.SAFE,  # Whitespace fixes
    "js-eslint": FixConfidence.LIKELY,  # Style fixes
}


@dataclass
class AdapterConfig:
    """Configuration container for adapter settings."""

    output_format: OutputFormat
    interactive: bool
    fail_fast: bool
    color: bool
    progress: bool
    tools: str  # "fast", "all", "configured"
    report_path: Optional[str] = None
    stdin_mode: bool = False
    transport: Optional[str] = None  # "stdio" for MCP


class ModeAdapter(ABC):
    """
    Abstract base class for mode-specific adapters.

    Each adapter configures how HuskyCat behaves in a specific mode:
    - Git Hooks: Fast, minimal output, fail-fast
    - CI: Comprehensive, structured reports
    - CLI: Interactive, colored output
    - Pipeline: JSON output, no interactivity
    - MCP: JSON-RPC protocol
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Mode name for logging/debugging."""

    @property
    @abstractmethod
    def config(self) -> AdapterConfig:
        """Get the adapter configuration."""

    def format_output(self, results: Dict[str, Any], summary: Dict[str, Any]) -> str:
        """
        Format validation results for output.

        Args:
            results: Per-file validation results
            summary: Aggregated summary statistics

        Returns:
            Formatted output string
        """
        fmt = self.config.output_format

        if fmt == OutputFormat.MINIMAL:
            return self._format_minimal(results, summary)
        elif fmt == OutputFormat.HUMAN:
            return self._format_human(results, summary)
        elif fmt == OutputFormat.JSON:
            return self._format_json(results, summary)
        elif fmt == OutputFormat.JUNIT_XML:
            return self._format_junit_xml(results, summary)
        elif fmt == OutputFormat.JSONRPC:
            return self._format_jsonrpc(results, summary)
        else:
            return self._format_human(results, summary)

    def _format_minimal(self, results: Dict[str, Any], summary: Dict[str, Any]) -> str:
        """Minimal output - only errors."""
        lines = []
        for filepath, file_results in results.items():
            for result in file_results:
                if hasattr(result, "errors") and result.errors:
                    for error in result.errors:
                        lines.append(f"{filepath}: {error}")
        return "\n".join(lines) if lines else ""

    def _format_human(self, results: Dict[str, Any], summary: Dict[str, Any]) -> str:
        """Human-readable colored output."""
        lines = []

        # Summary header
        total_errors = summary.get("total_errors", 0)
        total_warnings = summary.get("total_warnings", 0)
        files_checked = summary.get("files_checked", 0)

        if self.config.color:
            if total_errors > 0:
                lines.append(f"\033[91m✗ {total_errors} error(s)\033[0m")
            if total_warnings > 0:
                lines.append(f"\033[93m⚠ {total_warnings} warning(s)\033[0m")
            if total_errors == 0 and total_warnings == 0:
                lines.append(f"\033[92m✓ All {files_checked} files passed\033[0m")
        else:
            if total_errors > 0:
                lines.append(f"✗ {total_errors} error(s)")
            if total_warnings > 0:
                lines.append(f"⚠ {total_warnings} warning(s)")
            if total_errors == 0 and total_warnings == 0:
                lines.append(f"✓ All {files_checked} files passed")

        # Details
        for filepath, file_results in results.items():
            for result in file_results:
                if hasattr(result, "errors") and result.errors:
                    lines.append(f"\n{filepath} ({result.tool}):")
                    for error in result.errors:
                        lines.append(f"  • {error}")
                if hasattr(result, "warnings") and result.warnings:
                    lines.append(f"\n{filepath} ({result.tool}):")
                    for warning in result.warnings:
                        lines.append(f"  ⚠ {warning}")

        return "\n".join(lines)

    def _format_json(self, results: Dict[str, Any], summary: Dict[str, Any]) -> str:
        """JSON output for pipeline integration."""
        import json

        output = {
            "summary": summary,
            "results": {},
        }

        for filepath, file_results in results.items():
            output["results"][filepath] = []
            for result in file_results:
                if hasattr(result, "to_dict"):
                    output["results"][filepath].append(result.to_dict())
                else:
                    output["results"][filepath].append(
                        {
                            "tool": getattr(result, "tool", "unknown"),
                            "success": getattr(result, "success", True),
                            "errors": getattr(result, "errors", []),
                            "warnings": getattr(result, "warnings", []),
                        }
                    )

        return json.dumps(output, indent=2)

    def _format_junit_xml(
        self, results: Dict[str, Any], summary: Dict[str, Any]
    ) -> str:
        """JUnit XML format for CI artifacts."""
        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append(
            f'<testsuites tests="{summary.get("files_checked", 0)}" '
            f'failures="{summary.get("total_errors", 0)}">'
        )

        for filepath, file_results in results.items():
            for result in file_results:
                tool = getattr(result, "tool", "huskycat")
                errors = getattr(result, "errors", [])
                success = len(errors) == 0

                lines.append(f'  <testsuite name="{tool}" tests="1">')
                lines.append(f'    <testcase name="{filepath}" classname="{tool}">')

                if not success:
                    for error in errors:
                        escaped_error = (
                            error.replace("&", "&amp;")
                            .replace("<", "&lt;")
                            .replace(">", "&gt;")
                        )
                        lines.append(f'      <failure message="{escaped_error}"/>')

                lines.append("    </testcase>")
                lines.append("  </testsuite>")

        lines.append("</testsuites>")
        return "\n".join(lines)

    def _format_jsonrpc(self, results: Dict[str, Any], summary: Dict[str, Any]) -> str:
        """JSON-RPC format for MCP protocol."""
        import json

        # MCP responses are wrapped in JSON-RPC format elsewhere
        # Here we just prepare the result content
        return json.dumps(
            {
                "summary": summary,
                "results": {
                    filepath: [
                        (
                            result.to_dict()
                            if hasattr(result, "to_dict")
                            else {"tool": getattr(result, "tool", "unknown")}
                        )
                        for result in file_results
                    ]
                    for filepath, file_results in results.items()
                },
            }
        )

    def should_prompt_for_fix(self, confidence: "FixConfidence") -> bool:
        """
        Determine if we should prompt user for a fix at given confidence.

        Args:
            confidence: Fix confidence level (FixConfidence enum)

        Returns:
            True if should prompt, False if should auto-apply or skip
        """
        if not self.config.interactive:
            return False

        # In interactive mode, prompt for uncertain fixes
        return confidence == FixConfidence.UNCERTAIN

    def should_auto_fix(self, confidence: "FixConfidence") -> bool:
        """
        Determine if we should auto-apply a fix at given confidence.

        The decision depends on mode:
        - Git Hooks: Auto-apply SAFE fixes only (fast feedback)
        - CLI: Auto-apply SAFE and LIKELY (user initiated)
        - CI/Pipeline/MCP: Never auto-fix (read-only)

        Args:
            confidence: Fix confidence level (FixConfidence enum)

        Returns:
            True if should auto-apply, False otherwise
        """
        # Non-interactive modes never auto-fix
        if not self.config.interactive and self.config.output_format not in (
            OutputFormat.MINIMAL,  # Git hooks can fix
            OutputFormat.HUMAN,  # CLI can fix
        ):
            return False

        # Fail-fast modes (git_hooks) only apply SAFE fixes
        if self.config.fail_fast:
            return confidence == FixConfidence.SAFE

        # Interactive modes apply SAFE and LIKELY fixes
        return confidence in (FixConfidence.SAFE, FixConfidence.LIKELY)

    def get_fix_confidence(self, tool_name: str) -> "FixConfidence":
        """
        Get the fix confidence level for a tool.

        Args:
            tool_name: Name of the validation tool

        Returns:
            FixConfidence level for the tool's fixes
        """
        return TOOL_FIX_CONFIDENCE.get(tool_name, FixConfidence.UNCERTAIN)

    def get_tool_selection(self) -> List[str]:
        """
        Get list of tools to run based on mode.

        Returns:
            List of tool names or ["all"] for all tools
        """
        tools_config = self.config.tools

        if tools_config == "fast":
            # Fast tools for git hooks - Python formatters and basic linters
            # Names must match validator names in unified_validation.py
            return ["python-black", "ruff", "mypy", "flake8"]
        elif tools_config == "all":
            # All available tools
            return ["all"]
        elif tools_config == "configured":
            # Read from .huskycat.yaml (not implemented yet)
            return ["all"]
        else:
            return ["all"]
