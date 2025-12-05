"""
Unit tests for HuskyCat mode detection and adapters.

Tests the 5 product modes:
- Git Hooks: Pre-commit/pre-push validation
- CI: Pipeline integration
- CLI: Interactive terminal
- Pipeline: Machine-readable output
- MCP: AI assistant integration
"""

import os
import sys
from unittest.mock import patch

import pytest

from huskycat.core.adapters import (
    TOOL_FIX_CONFIDENCE,
    CIAdapter,
    CLIAdapter,
    FixConfidence,
    GitHooksAdapter,
    MCPAdapter,
    OutputFormat,
    PipelineAdapter,
)
from huskycat.core.mode_detector import (
    ProductMode,
    _is_ci_context,
    _is_git_hooks_context,
    _is_mcp_invocation,
    _is_pipeline_context,
    detect_mode,
    get_adapter,
    get_mode_description,
)


class TestProductModeEnum:
    """Test ProductMode enum values."""

    def test_all_modes_exist(self):
        """All 5 product modes should exist."""
        assert ProductMode.GIT_HOOKS.value == "git_hooks"
        assert ProductMode.CI.value == "ci"
        assert ProductMode.CLI.value == "cli"
        assert ProductMode.PIPELINE.value == "pipeline"
        assert ProductMode.MCP.value == "mcp"

    def test_mode_from_string(self):
        """Can create mode from string value."""
        assert ProductMode("git_hooks") == ProductMode.GIT_HOOKS
        assert ProductMode("ci") == ProductMode.CI
        assert ProductMode("cli") == ProductMode.CLI
        assert ProductMode("pipeline") == ProductMode.PIPELINE
        assert ProductMode("mcp") == ProductMode.MCP


class TestModeDetection:
    """Test automatic mode detection."""

    def test_explicit_override_takes_priority(self):
        """Explicit override parameter should take priority."""
        assert detect_mode(override="ci") == ProductMode.CI
        assert detect_mode(override="git_hooks") == ProductMode.GIT_HOOKS
        assert detect_mode(override="pipeline") == ProductMode.PIPELINE

    def test_env_var_override(self):
        """HUSKYCAT_MODE env var should work."""
        with patch.dict(os.environ, {"HUSKYCAT_MODE": "ci"}):
            # Need to clear any cached detection
            assert detect_mode() == ProductMode.CI

    def test_mcp_invocation_detection(self):
        """MCP mode detected from command line args."""
        with patch.object(sys, "argv", ["huskycat", "mcp-server"]):
            assert _is_mcp_invocation() is True

        with patch.object(sys, "argv", ["huskycat", "validate"]):
            assert _is_mcp_invocation() is False

    def test_ci_context_detection(self):
        """CI mode detected from CI env vars."""
        # GitLab CI
        with patch.dict(os.environ, {"GITLAB_CI": "true"}, clear=True):
            assert _is_ci_context() is True

        # GitHub Actions
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=True):
            assert _is_ci_context() is True

        # Generic CI
        with patch.dict(os.environ, {"CI": "true"}, clear=True):
            assert _is_ci_context() is True

        # No CI
        with patch.dict(os.environ, {}, clear=True):
            assert _is_ci_context() is False

    def test_git_hooks_context_detection(self):
        """Git hooks mode detected from GIT_* env vars."""
        # Multiple GIT vars = git hooks
        with patch.dict(
            os.environ,
            {"GIT_AUTHOR_NAME": "test", "GIT_INDEX_FILE": ".git/index"},
            clear=True,
        ):
            assert _is_git_hooks_context() is True

        # Single GIT var = not enough confidence
        with patch.dict(os.environ, {"GIT_DIR": ".git"}, clear=True):
            assert _is_git_hooks_context() is False


class TestAdapters:
    """Test mode adapters."""

    def test_get_adapter_returns_correct_type(self):
        """get_adapter should return the correct adapter type."""
        assert isinstance(get_adapter(ProductMode.GIT_HOOKS), GitHooksAdapter)
        assert isinstance(get_adapter(ProductMode.CI), CIAdapter)
        assert isinstance(get_adapter(ProductMode.CLI), CLIAdapter)
        assert isinstance(get_adapter(ProductMode.PIPELINE), PipelineAdapter)
        assert isinstance(get_adapter(ProductMode.MCP), MCPAdapter)

    def test_git_hooks_adapter_config(self):
        """Git hooks adapter should have correct config."""
        adapter = GitHooksAdapter()
        config = adapter.config

        assert config.output_format == OutputFormat.MINIMAL
        assert config.fail_fast is True
        assert config.tools == "fast"
        assert config.progress is False

    def test_ci_adapter_config(self):
        """CI adapter should have correct config."""
        adapter = CIAdapter()
        config = adapter.config

        assert config.output_format == OutputFormat.JUNIT_XML
        assert config.interactive is False
        assert config.fail_fast is False
        assert config.tools == "all"
        assert config.color is False

    def test_cli_adapter_config(self):
        """CLI adapter should have correct config."""
        adapter = CLIAdapter()
        config = adapter.config

        assert config.output_format == OutputFormat.HUMAN
        assert config.interactive is True
        assert config.fail_fast is False
        assert config.tools == "configured"

    def test_pipeline_adapter_config(self):
        """Pipeline adapter should have correct config."""
        adapter = PipelineAdapter()
        config = adapter.config

        assert config.output_format == OutputFormat.JSON
        assert config.interactive is False
        assert config.stdin_mode is True
        assert config.color is False

    def test_mcp_adapter_config(self):
        """MCP adapter should have correct config."""
        adapter = MCPAdapter()
        config = adapter.config

        assert config.output_format == OutputFormat.JSONRPC
        assert config.interactive is False
        assert config.transport == "stdio"


class TestAdapterOutputFormatting:
    """Test adapter output formatting."""

    def test_minimal_format_only_shows_errors(self):
        """Minimal format should only show errors."""
        adapter = GitHooksAdapter()

        results = {
            "test.py": [
                MockResult(
                    tool="ruff",
                    errors=["E501 line too long"],
                    warnings=["W123 warning"],
                ),
            ]
        }
        summary = {"total_errors": 1, "total_warnings": 1}

        output = adapter._format_minimal(results, summary)
        assert "E501" in output
        assert "W123" not in output  # No warnings in minimal

    def test_json_format_structure(self):
        """JSON format should have correct structure."""
        adapter = PipelineAdapter()

        results = {
            "test.py": [
                MockResult(tool="black", errors=[], warnings=[]),
            ]
        }
        summary = {"total_errors": 0, "total_warnings": 0, "files_checked": 1}

        import json

        output = adapter._format_json(results, summary)
        data = json.loads(output)

        assert "summary" in data
        assert "results" in data
        assert "test.py" in data["results"]

    def test_junit_xml_format(self):
        """JUnit XML format should be valid XML."""
        adapter = CIAdapter()

        results = {
            "test.py": [
                MockResult(tool="mypy", errors=["error: Type mismatch"], warnings=[]),
            ]
        }
        summary = {"total_errors": 1, "files_checked": 1}

        output = adapter._format_junit_xml(results, summary)

        assert '<?xml version="1.0"' in output
        assert "<testsuites" in output
        assert "<testsuite" in output
        assert "<failure" in output


class TestModeDescriptions:
    """Test mode description strings."""

    def test_all_modes_have_descriptions(self):
        """All modes should have descriptions."""
        for mode in ProductMode:
            desc = get_mode_description(mode)
            assert desc is not None
            assert len(desc) > 0
            assert (
                mode.value in desc.lower()
                or mode.name.lower().replace("_", " ") in desc.lower()
            )


class TestAdapterToolSelection:
    """Test adapter tool selection for different modes."""

    def test_git_hooks_selects_fast_tools(self):
        """Git hooks mode should only use fast tools."""
        adapter = GitHooksAdapter()
        tools = adapter.get_tool_selection()

        # Should be fast tools only (names match unified_validation.py)
        assert "python-black" in tools
        assert "ruff" in tools
        assert "mypy" in tools
        assert "flake8" in tools
        # Should NOT include slower tools
        assert "bandit" not in tools
        assert "shellcheck" not in tools

    def test_ci_mode_selects_all_tools(self):
        """CI mode should use all tools for comprehensive validation."""
        adapter = CIAdapter()
        tools = adapter.get_tool_selection()

        # Should return ["all"] for all tools
        assert tools == ["all"]

    def test_cli_mode_uses_configured_tools(self):
        """CLI mode should use configured tools (defaults to all)."""
        adapter = CLIAdapter()
        tools = adapter.get_tool_selection()

        # Should default to all tools
        assert tools == ["all"]

    def test_pipeline_mode_uses_all_tools(self):
        """Pipeline mode should use all tools."""
        adapter = PipelineAdapter()
        tools = adapter.get_tool_selection()

        assert tools == ["all"]

    def test_mcp_mode_uses_all_tools(self):
        """MCP mode should use all tools."""
        adapter = MCPAdapter()
        tools = adapter.get_tool_selection()

        assert tools == ["all"]


class TestValidateCommandWithAdapter:
    """Test ValidateCommand integration with adapters."""

    def test_validate_command_receives_adapter(self):
        """ValidateCommand should receive adapter from factory."""
        from huskycat.commands.validate import ValidateCommand
        from huskycat.core.factory import HuskyCatFactory

        adapter = GitHooksAdapter()
        factory = HuskyCatFactory(adapter=adapter)

        command = factory.create_command("validate")
        assert command is not None
        assert command.adapter is adapter

    def test_validate_command_uses_adapter_tool_selection(self):
        """ValidateCommand should use adapter's tool selection."""
        from huskycat.commands.validate import ValidateCommand

        adapter = GitHooksAdapter()
        command = ValidateCommand(adapter=adapter)

        # Verify adapter is set
        assert command.adapter is adapter

        # Verify tool selection would use fast tools (names match unified_validation.py)
        tools = command.adapter.get_tool_selection()
        assert tools == ["python-black", "ruff", "mypy", "flake8"]


class TestAutoFixConfidenceTiers:
    """Test auto-fix confidence tier system."""

    def test_fix_confidence_enum_values(self):
        """FixConfidence enum should have correct values."""
        assert FixConfidence.SAFE.value == "safe"
        assert FixConfidence.LIKELY.value == "likely"
        assert FixConfidence.UNCERTAIN.value == "uncertain"

    def test_tool_confidence_mapping(self):
        """Tools should have correct confidence mappings."""
        # Formatting tools are SAFE
        assert TOOL_FIX_CONFIDENCE["python-black"] == FixConfidence.SAFE
        assert TOOL_FIX_CONFIDENCE["js-prettier"] == FixConfidence.SAFE
        assert TOOL_FIX_CONFIDENCE["yamllint"] == FixConfidence.SAFE

        # Style tools are LIKELY
        assert TOOL_FIX_CONFIDENCE["autoflake"] == FixConfidence.LIKELY
        assert TOOL_FIX_CONFIDENCE["ruff"] == FixConfidence.LIKELY
        assert TOOL_FIX_CONFIDENCE["js-eslint"] == FixConfidence.LIKELY

    def test_unknown_tool_returns_uncertain(self):
        """Unknown tools should default to UNCERTAIN confidence."""
        adapter = CLIAdapter()
        confidence = adapter.get_fix_confidence("unknown-tool")
        assert confidence == FixConfidence.UNCERTAIN

    def test_git_hooks_only_auto_fixes_safe(self):
        """Git hooks mode should only auto-fix SAFE confidence."""
        adapter = GitHooksAdapter()

        # SAFE should auto-fix
        assert adapter.should_auto_fix(FixConfidence.SAFE) is True

        # LIKELY and UNCERTAIN should NOT auto-fix in fail-fast mode
        assert adapter.should_auto_fix(FixConfidence.LIKELY) is False
        assert adapter.should_auto_fix(FixConfidence.UNCERTAIN) is False

    def test_cli_auto_fixes_safe_and_likely(self):
        """CLI mode should auto-fix SAFE and LIKELY confidence."""
        adapter = CLIAdapter()

        # SAFE and LIKELY should auto-fix
        assert adapter.should_auto_fix(FixConfidence.SAFE) is True
        assert adapter.should_auto_fix(FixConfidence.LIKELY) is True

        # UNCERTAIN should NOT auto-fix
        assert adapter.should_auto_fix(FixConfidence.UNCERTAIN) is False

    def test_ci_never_auto_fixes(self):
        """CI mode should never auto-fix (read-only)."""
        adapter = CIAdapter()

        # Nothing should auto-fix in CI
        assert adapter.should_auto_fix(FixConfidence.SAFE) is False
        assert adapter.should_auto_fix(FixConfidence.LIKELY) is False
        assert adapter.should_auto_fix(FixConfidence.UNCERTAIN) is False

    def test_pipeline_never_auto_fixes(self):
        """Pipeline mode should never auto-fix (read-only)."""
        adapter = PipelineAdapter()

        assert adapter.should_auto_fix(FixConfidence.SAFE) is False
        assert adapter.should_auto_fix(FixConfidence.LIKELY) is False
        assert adapter.should_auto_fix(FixConfidence.UNCERTAIN) is False

    def test_mcp_never_auto_fixes(self):
        """MCP mode should never auto-fix (read-only)."""
        adapter = MCPAdapter()

        assert adapter.should_auto_fix(FixConfidence.SAFE) is False
        assert adapter.should_auto_fix(FixConfidence.LIKELY) is False
        assert adapter.should_auto_fix(FixConfidence.UNCERTAIN) is False

    def test_cli_prompts_for_uncertain(self):
        """CLI mode should prompt for UNCERTAIN fixes."""
        adapter = CLIAdapter()

        # Should prompt for UNCERTAIN
        assert adapter.should_prompt_for_fix(FixConfidence.UNCERTAIN) is True

        # Should NOT prompt for SAFE or LIKELY (auto-applied)
        assert adapter.should_prompt_for_fix(FixConfidence.SAFE) is False
        assert adapter.should_prompt_for_fix(FixConfidence.LIKELY) is False

    def test_ci_never_prompts(self):
        """CI mode should never prompt (non-interactive)."""
        adapter = CIAdapter()

        assert adapter.should_prompt_for_fix(FixConfidence.SAFE) is False
        assert adapter.should_prompt_for_fix(FixConfidence.LIKELY) is False
        assert adapter.should_prompt_for_fix(FixConfidence.UNCERTAIN) is False


# Mock classes for testing


class MockResult:
    """Mock validation result for testing."""

    def __init__(self, tool: str, errors: list = None, warnings: list = None):
        self.tool = tool
        self.errors = errors or []
        self.warnings = warnings or []
        self.success = len(self.errors) == 0

    def to_dict(self):
        return {
            "tool": self.tool,
            "errors": self.errors,
            "warnings": self.warnings,
            "success": self.success,
        }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
