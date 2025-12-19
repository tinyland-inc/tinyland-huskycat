"""
Tests for NonBlockingGitHooksAdapter.

Tests the integration of:
- ProcessManager for forking
- ValidationTUI for progress display
- ParallelExecutor for parallel tool execution
"""

import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from huskycat.core.adapters.git_hooks_nonblocking import NonBlockingGitHooksAdapter
from huskycat.core.parallel_executor import ToolResult
from huskycat.core.tui import ToolState


class TestNonBlockingGitHooksAdapter:
    """Test suite for NonBlockingGitHooksAdapter."""

    def test_adapter_initialization(self):
        """Test adapter initializes with correct components."""
        adapter = NonBlockingGitHooksAdapter()

        assert adapter.name == "git_hooks_nonblocking"
        assert adapter.process_manager is not None
        assert adapter.tui is not None
        assert adapter.executor is not None

    def test_adapter_config(self):
        """Test adapter configuration is correct."""
        adapter = NonBlockingGitHooksAdapter()
        config = adapter.config

        # Non-blocking adapter runs ALL tools
        assert config.tools == "all"

        # Enables progress in child process
        assert config.progress is True

        # Uses minimal output format (for parent)
        assert config.output_format.value == "minimal"

        # Does not fail fast (runs all tools)
        assert config.fail_fast is False

    def test_get_all_validation_tools(self):
        """Test tool loading based on file types."""
        adapter = NonBlockingGitHooksAdapter()

        # Test with Python files
        python_files = ["test.py", "module.py"]
        tools = adapter.get_all_validation_tools(python_files)

        assert "black" in tools
        assert "ruff" in tools
        assert "mypy" in tools
        assert "flake8" in tools
        assert "isort" in tools
        assert "bandit" in tools

        # Test with YAML files
        yaml_files = ["config.yaml", ".gitlab-ci.yml"]
        tools = adapter.get_all_validation_tools(yaml_files)

        assert "yamllint" in tools
        assert "gitlab-ci" in tools

        # Test with shell files
        shell_files = ["deploy.sh", "test.bash"]
        tools = adapter.get_all_validation_tools(shell_files)

        assert "shellcheck" in tools

    def test_placeholder_tool_execution(self):
        """Test placeholder tool returns expected result."""
        adapter = NonBlockingGitHooksAdapter()

        result = adapter._placeholder_tool("test-tool", ["file1.py", "file2.py"])

        assert isinstance(result, ToolResult)
        assert result.tool_name == "test-tool"
        assert result.success is True
        assert result.duration > 0
        assert result.errors == 0
        assert result.warnings == 0

    @patch("sys.exit")
    @patch("huskycat.core.adapters.git_hooks_nonblocking.should_proceed_with_commit")
    def test_previous_failure_blocks_commit(self, mock_proceed, mock_exit):
        """Test that previous validation failure blocks commit."""
        # Simulate previous failure
        mock_proceed.return_value = False

        adapter = NonBlockingGitHooksAdapter()

        # Mock the process manager to avoid actual forking
        with patch.object(adapter.process_manager, "fork_validation"):
            adapter.execute_validation(["test.py"], {})

            # Should call sys.exit(1) when previous failure detected
            mock_exit.assert_called_once_with(1)

    @patch("os.fork")
    @patch("huskycat.core.adapters.git_hooks_nonblocking.should_proceed_with_commit")
    def test_fork_returns_pid_to_parent(self, mock_proceed, mock_fork):
        """Test that parent process receives PID and continues."""
        # No previous failure
        mock_proceed.return_value = True

        # Mock fork to return parent process
        mock_fork.return_value = 12345  # Parent process (PID > 0)

        adapter = NonBlockingGitHooksAdapter()

        # Create mock tools
        tools = {"black": MagicMock()}

        # Execute validation
        with patch.object(adapter.process_manager, "_save_pid"):
            with patch.object(adapter.process_manager, "cleanup_zombies"):
                pid = adapter.execute_validation(["test.py"], tools)

                # Parent should receive PID
                assert pid == 12345

    def test_format_output_returns_empty(self):
        """Test that format_output returns empty string."""
        adapter = NonBlockingGitHooksAdapter()

        # Non-blocking adapter doesn't format output (handled by child)
        output = adapter.format_output({}, {})
        assert output == ""

    def test_config_integration(self):
        """Test integration with HuskyCatConfig."""
        from huskycat.core.config import HuskyCatConfig

        # Create temporary config
        config = HuskyCatConfig()

        # Enable non-blocking hooks
        config.set_feature_flag("nonblocking_hooks", True)

        assert config.nonblocking_hooks_enabled is True

    def test_mode_detector_integration(self):
        """Test integration with mode detector."""
        from huskycat.core.mode_detector import ProductMode, get_adapter

        # Get adapter without feature flag (standard blocking)
        adapter_blocking = get_adapter(ProductMode.GIT_HOOKS, use_nonblocking=False)
        assert adapter_blocking.name == "git_hooks"

        # Get adapter with feature flag (non-blocking)
        adapter_nonblocking = get_adapter(ProductMode.GIT_HOOKS, use_nonblocking=True)
        assert adapter_nonblocking.name == "git_hooks_nonblocking"


@pytest.mark.integration
class TestNonBlockingIntegration:
    """Integration tests that require actual execution."""

    def test_parallel_execution_integration(self):
        """Test integration with ParallelExecutor."""
        adapter = NonBlockingGitHooksAdapter()

        # Create mock tools that simulate validation
        def mock_tool(name: str) -> ToolResult:
            time.sleep(0.1)  # Simulate work
            return ToolResult(
                tool_name=name, success=True, duration=0.1, errors=0, warnings=0
            )

        tools = {
            "black": lambda: mock_tool("black"),
            "ruff": lambda: mock_tool("ruff"),
            "mypy": lambda: mock_tool("mypy"),
        }

        # Track progress updates
        progress_updates = []

        def track_progress(tool_name: str, status: str, errors: int = 0, warnings: int = 0):
            progress_updates.append((tool_name, status))

        # Execute tools
        results = adapter.executor.execute_tools(tools, progress_callback=track_progress)

        # Verify results
        assert len(results) == 3
        assert all(r.success for r in results)

        # Verify progress tracking
        assert len(progress_updates) > 0

    def test_tui_updates(self):
        """Test TUI updates during validation."""
        adapter = NonBlockingGitHooksAdapter()

        # Start TUI with test tools
        tool_names = ["black", "ruff", "mypy"]

        # Note: TUI only works in TTY, so this may be skipped in CI
        if not os.isatty(1):
            pytest.skip("TUI requires TTY")

        adapter.tui.start(tool_names)

        # Update tool status
        adapter.tui.update_tool("black", ToolState.RUNNING)
        time.sleep(0.1)
        adapter.tui.update_tool("black", ToolState.SUCCESS, errors=0, warnings=0)

        # Stop TUI
        adapter.tui.stop()

        # Verify tool was tracked
        assert "black" in adapter.tui.tools
        assert adapter.tui.tools["black"].state == ToolState.SUCCESS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
