"""
Extended Tests for NonBlockingGitHooksAdapter.

This test suite increases coverage from 53.2% to 70%+ by testing:
- Adapter configuration with custom cache directories
- Tool loading for various file types
- Fork validation error handling
- Child process validation execution
- Error recovery paths
- Previous failure handling
- Multiple concurrent scenarios

Coverage targets:
- Line 61-75: ProcessManager initialization with cache_dir
- Line 85-110: Tool loading from validators
- Line 126-140: Fork validation call
- Line 150-180: Child validation execution
- Line 200-220: Error recovery paths
"""

import os
import sys
import time
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from huskycat.core.adapters.git_hooks_nonblocking import NonBlockingGitHooksAdapter
from huskycat.core.parallel_executor import ToolResult, ToolStatus
from huskycat.core.process_manager import ValidationRun
from huskycat.core.tui import ToolState


class TestAdapterConfiguration:
    """Test adapter initialization and configuration scenarios."""

    def test_adapter_default_cache_dir(self):
        """Test adapter initializes with default cache directory."""
        adapter = NonBlockingGitHooksAdapter()

        assert adapter.process_manager is not None
        # Default cache dir is .huskycat/runs from current working directory
        expected_cache = Path.cwd() / ".huskycat" / "runs"
        assert adapter.process_manager.cache_dir == expected_cache

    def test_adapter_custom_cache_dir(self):
        """Test adapter initialization with custom cache directory."""
        custom_cache = Path("/tmp/test_cache_huskycat")
        adapter = NonBlockingGitHooksAdapter(cache_dir=custom_cache)

        assert adapter.process_manager.cache_dir == custom_cache

    def test_adapter_initialization_components(self):
        """Test all components initialized correctly."""
        adapter = NonBlockingGitHooksAdapter()

        # Verify ProcessManager created
        assert adapter.process_manager is not None
        assert hasattr(adapter.process_manager, "cache_dir")
        assert hasattr(adapter.process_manager, "fork_validation")

        # Verify TUI created
        assert adapter.tui is not None
        assert hasattr(adapter.tui, "start")
        assert hasattr(adapter.tui, "stop")
        assert hasattr(adapter.tui, "update_tool")

        # Verify ParallelExecutor created
        assert adapter.executor is not None
        assert hasattr(adapter.executor, "execute_tools")
        assert adapter.executor.max_workers == 8
        assert adapter.executor.fail_fast is False

    def test_adapter_name_property(self):
        """Test adapter name is correct."""
        adapter = NonBlockingGitHooksAdapter()
        assert adapter.name == "git_hooks_nonblocking"

    def test_adapter_config_properties(self):
        """Test adapter config returns correct AdapterConfig."""
        adapter = NonBlockingGitHooksAdapter()
        config = adapter.config

        # Verify all config properties
        assert config.output_format.value == "minimal"
        assert config.fail_fast is False
        assert config.progress is True
        assert config.tools == "all"
        # Interactive depends on TTY
        assert isinstance(config.interactive, bool)
        # Color depends on TTY
        assert isinstance(config.color, bool)


class TestToolLoading:
    """Test tool loading based on file types."""

    def test_tool_loading_python_files(self):
        """Test loading Python tools for .py files."""
        adapter = NonBlockingGitHooksAdapter()
        files = ["test.py", "module.py"]

        tools = adapter.get_all_validation_tools(files)

        # Expected Python tools
        assert "black" in tools
        assert "ruff" in tools
        assert "mypy" in tools
        assert "flake8" in tools
        assert "isort" in tools
        assert "bandit" in tools

        # Verify tools are callables
        assert callable(tools["black"])
        assert callable(tools["ruff"])

    def test_tool_loading_javascript_files(self):
        """Test loading JS tools for .js files (not implemented yet)."""
        adapter = NonBlockingGitHooksAdapter()
        files = ["app.js", "index.js"]

        tools = adapter.get_all_validation_tools(files)

        # JavaScript tools not yet implemented in adapter
        # This test documents expected future behavior
        # Currently returns empty dict for JS files
        assert isinstance(tools, dict)

    def test_tool_loading_shell_files(self):
        """Test loading shell tools for .sh files."""
        adapter = NonBlockingGitHooksAdapter()
        files = ["deploy.sh", "install.bash"]

        tools = adapter.get_all_validation_tools(files)

        # Expected shell tools
        assert "shellcheck" in tools
        assert callable(tools["shellcheck"])

    def test_tool_loading_yaml_files(self):
        """Test loading YAML tools for .yaml/.yml files."""
        adapter = NonBlockingGitHooksAdapter()
        files = ["config.yaml", ".gitlab-ci.yml"]

        tools = adapter.get_all_validation_tools(files)

        # Expected YAML tools
        assert "yamllint" in tools
        assert "gitlab-ci" in tools
        assert callable(tools["yamllint"])

    def test_tool_loading_toml_files(self):
        """Test loading TOML tools for .toml files."""
        adapter = NonBlockingGitHooksAdapter()
        files = ["pyproject.toml", "Cargo.toml"]

        tools = adapter.get_all_validation_tools(files)

        # Expected TOML tools
        assert "taplo" in tools
        assert callable(tools["taplo"])

    def test_tool_loading_dockerfile(self):
        """Test loading Docker tools for Dockerfile."""
        adapter = NonBlockingGitHooksAdapter()
        files = ["Dockerfile", "app.dockerfile"]

        tools = adapter.get_all_validation_tools(files)

        # Expected Docker tools
        assert "hadolint" in tools
        assert callable(tools["hadolint"])

    def test_tool_loading_chapel_files(self):
        """Test loading Chapel tools for .chpl files."""
        adapter = NonBlockingGitHooksAdapter()
        files = ["program.chpl", "module.chpl"]

        tools = adapter.get_all_validation_tools(files)

        # Expected Chapel tools
        assert "chapel-format" in tools
        assert callable(tools["chapel-format"])

    def test_tool_loading_mixed_types(self):
        """Test loading tools for mixed file types."""
        adapter = NonBlockingGitHooksAdapter()
        files = [
            "test.py",
            "config.yaml",
            "deploy.sh",
            "pyproject.toml",
        ]

        tools = adapter.get_all_validation_tools(files)

        # Verify all appropriate tools loaded
        assert "black" in tools  # Python
        assert "mypy" in tools  # Python
        assert "yamllint" in tools  # YAML
        assert "shellcheck" in tools  # Shell
        assert "taplo" in tools  # TOML

        # All should be callables
        for tool_name, tool_func in tools.items():
            assert callable(tool_func), f"Tool {tool_name} is not callable"

    def test_tool_loading_unknown_type(self):
        """Test handling of files with no validators."""
        adapter = NonBlockingGitHooksAdapter()
        files = ["file.unknown", "data.dat"]

        tools = adapter.get_all_validation_tools(files)

        # Should return empty dict for unknown types
        assert tools == {}

    def test_tool_loading_empty_files_list(self):
        """Test handling of empty files list."""
        adapter = NonBlockingGitHooksAdapter()
        files = []

        tools = adapter.get_all_validation_tools(files)

        # Should return empty dict
        assert tools == {}


class TestForkValidation:
    """Test fork validation workflow."""

    @patch("huskycat.core.adapters.git_hooks_nonblocking.should_proceed_with_commit")
    @patch.object(NonBlockingGitHooksAdapter, "_run_validation_child_wrapper")
    def test_fork_validation_success(self, mock_child, mock_proceed):
        """Test successful fork validation call."""
        # No previous failure
        mock_proceed.return_value = True

        adapter = NonBlockingGitHooksAdapter()

        # Mock ProcessManager.fork_validation
        with patch.object(adapter.process_manager, "fork_validation") as mock_fork:
            mock_fork.return_value = 12345  # Simulated PID

            # Mock cleanup_zombies
            with patch.object(adapter.process_manager, "cleanup_zombies"):
                files = ["test.py"]
                tools = {"black": MagicMock()}

                pid = adapter.execute_validation(files, tools)

                # Verify fork_validation was called
                mock_fork.assert_called_once()
                # Verify returned PID
                assert pid == 12345

    @patch("sys.exit")
    @patch("huskycat.core.adapters.git_hooks_nonblocking.should_proceed_with_commit")
    def test_fork_validation_with_previous_failure(self, mock_proceed, mock_exit):
        """Test fork when previous validation failed."""
        # Simulate previous failure
        mock_proceed.return_value = False

        adapter = NonBlockingGitHooksAdapter()

        # Mock to avoid actual forking
        with patch.object(adapter.process_manager, "fork_validation"):
            files = ["test.py"]
            tools = {"black": MagicMock()}

            adapter.execute_validation(files, tools)

            # Should call sys.exit(1) when previous failure detected
            mock_exit.assert_called_once_with(1)

    @patch("huskycat.core.adapters.git_hooks_nonblocking.should_proceed_with_commit")
    def test_fork_validation_cleanup_zombies_called(self, mock_proceed):
        """Test that zombie cleanup is called before forking."""
        # No previous failure
        mock_proceed.return_value = True

        adapter = NonBlockingGitHooksAdapter()

        # Mock ProcessManager methods
        with patch.object(adapter.process_manager, "fork_validation") as mock_fork:
            with patch.object(adapter.process_manager, "cleanup_zombies") as mock_cleanup:
                mock_fork.return_value = 12345

                files = ["test.py"]
                tools = {"black": MagicMock()}

                adapter.execute_validation(files, tools)

                # Verify cleanup_zombies was called
                mock_cleanup.assert_called_once()

    @patch("huskycat.core.adapters.git_hooks_nonblocking.should_proceed_with_commit")
    def test_fork_validation_passes_correct_args(self, mock_proceed):
        """Test that fork_validation receives correct arguments."""
        # No previous failure
        mock_proceed.return_value = True

        adapter = NonBlockingGitHooksAdapter()

        # Mock ProcessManager methods
        with patch.object(adapter.process_manager, "fork_validation") as mock_fork:
            with patch.object(adapter.process_manager, "cleanup_zombies"):
                mock_fork.return_value = 12345

                files = ["test.py", "module.py"]
                tools = {
                    "black": MagicMock(),
                    "ruff": MagicMock(),
                }

                adapter.execute_validation(files, tools)

                # Verify fork_validation called with correct args
                mock_fork.assert_called_once()
                call_kwargs = mock_fork.call_args[1]
                assert call_kwargs["files"] == files
                assert len(call_kwargs["validation_args"]) == 2
                assert call_kwargs["validation_args"][0] == files
                assert call_kwargs["validation_args"][1] == tools


class TestChildValidation:
    """Test child process validation execution."""

    @patch("sys.exit")
    @patch.object(NonBlockingGitHooksAdapter, "_run_validation_child")
    def test_child_validation_wrapper_calls_method(self, mock_child, mock_exit):
        """Test child wrapper calls the actual validation method."""
        adapter = NonBlockingGitHooksAdapter()

        files = ["test.py"]
        tools = {"black": MagicMock()}

        adapter._run_validation_child_wrapper(files, tools)

        # Verify _run_validation_child was called
        mock_child.assert_called_once_with(files, tools)

    @patch("sys.exit")
    def test_child_validation_execution_flow(self, mock_exit):
        """Test child process validation flow."""
        adapter = NonBlockingGitHooksAdapter()

        # Create mock tool that returns success
        def mock_tool():
            return ToolResult(
                tool_name="black",
                success=True,
                duration=0.1,
                errors=0,
                warnings=0,
            )

        tools = {"black": mock_tool}
        files = ["test.py"]

        # Mock TUI methods
        with patch.object(adapter.tui, "start") as mock_start:
            with patch.object(adapter.tui, "stop") as mock_stop:
                with patch.object(adapter.tui, "update_tool"):
                    with patch.object(adapter.executor, "execute_tools") as mock_execute:
                        # Mock successful execution
                        mock_execute.return_value = [
                            ToolResult(
                                tool_name="black",
                                success=True,
                                duration=0.5,
                                errors=0,
                                warnings=0,
                            )
                        ]

                        # Mock save_run
                        with patch.object(adapter.process_manager, "save_run"):
                            adapter._run_validation_child(files, tools)

                        # Verify TUI lifecycle
                        mock_start.assert_called_once_with(["black"])
                        mock_stop.assert_called_once()

                        # Verify exit with success
                        mock_exit.assert_called_once_with(0)

    def test_child_validation_exception_handling(self):
        """Test child handles exceptions gracefully."""
        adapter = NonBlockingGitHooksAdapter()

        tools = {"black": MagicMock()}
        files = ["test.py"]

        # Mock sys.exit to raise SystemExit (so execution actually stops)
        with patch("sys.exit") as mock_exit:
            mock_exit.side_effect = SystemExit

            # Mock executor to raise exception
            with patch.object(adapter.executor, "execute_tools") as mock_execute:
                mock_execute.side_effect = Exception("Tool execution failed")

                with patch.object(adapter.tui, "start"):
                    with patch.object(adapter.tui, "stop") as mock_stop:
                        # Call should raise SystemExit due to mock
                        with pytest.raises(SystemExit):
                            adapter._run_validation_child(files, tools)

                        # Verify TUI stopped even on exception
                        # (exception handler calls tui.stop() before sys.exit)
                        mock_stop.assert_called_once()

                        # Verify exit with failure code was attempted
                        # (exception handler calls sys.exit(1))
                        mock_exit.assert_called_once_with(1)

    @patch("sys.exit")
    def test_child_validation_saves_run_results(self, mock_exit):
        """Test child saves validation run results."""
        adapter = NonBlockingGitHooksAdapter()

        tools = {"black": MagicMock(), "ruff": MagicMock()}
        files = ["test.py", "module.py"]

        # Mock execution results
        with patch.object(adapter.executor, "execute_tools") as mock_execute:
            mock_execute.return_value = [
                ToolResult("black", True, 0.5, 0, 1),
                ToolResult("ruff", False, 0.3, 2, 0),
            ]

            with patch.object(adapter.tui, "start"):
                with patch.object(adapter.tui, "stop"):
                    with patch.object(adapter.tui, "update_tool"):
                        with patch.object(adapter.process_manager, "save_run") as mock_save:
                            adapter._run_validation_child(files, tools)

                            # Verify save_run was called
                            mock_save.assert_called_once()

                            # Verify run data
                            saved_run = mock_save.call_args[0][0]
                            assert isinstance(saved_run, ValidationRun)
                            assert saved_run.files == files
                            assert saved_run.success is False  # ruff failed
                            assert saved_run.errors == 2
                            assert saved_run.warnings == 1
                            assert saved_run.exit_code == 1

    @patch("sys.exit")
    def test_child_validation_progress_callback(self, mock_exit):
        """Test progress callback updates TUI correctly."""
        adapter = NonBlockingGitHooksAdapter()

        tools = {"black": MagicMock()}
        files = ["test.py"]

        captured_callback = None

        def capture_callback(*args, **kwargs):
            nonlocal captured_callback
            captured_callback = kwargs.get("progress_callback")
            return [ToolResult("black", True, 0.5, 0, 0)]

        with patch.object(adapter.executor, "execute_tools") as mock_execute:
            mock_execute.side_effect = capture_callback

            with patch.object(adapter.tui, "start"):
                with patch.object(adapter.tui, "stop"):
                    with patch.object(adapter.tui, "update_tool") as mock_update:
                        with patch.object(adapter.process_manager, "save_run"):
                            adapter._run_validation_child(files, tools)

                            # Verify callback was passed
                            assert captured_callback is not None

                            # Test the callback
                            captured_callback("black", "success", errors=1, warnings=2)

                            # Verify TUI update was called
                            mock_update.assert_called()
                            call_args = mock_update.call_args
                            assert call_args[1]["tool_name"] == "black"
                            assert call_args[1]["state"] == ToolState.SUCCESS
                            assert call_args[1]["errors"] == 1
                            assert call_args[1]["warnings"] == 2


class TestErrorRecovery:
    """Test error recovery and resilience."""

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
        assert "Validated 2 files" in result.output

    @patch("sys.exit")
    def test_child_validation_all_tools_fail(self, mock_exit):
        """Test handling when all tools fail."""
        adapter = NonBlockingGitHooksAdapter()

        tools = {
            "black": MagicMock(),
            "ruff": MagicMock(),
            "mypy": MagicMock(),
        }
        files = ["test.py"]

        # Mock all tools failing
        with patch.object(adapter.executor, "execute_tools") as mock_execute:
            mock_execute.return_value = [
                ToolResult("black", False, 0.5, 5, 0),
                ToolResult("ruff", False, 0.3, 3, 1),
                ToolResult("mypy", False, 1.0, 10, 2),
            ]

            with patch.object(adapter.tui, "start"):
                with patch.object(adapter.tui, "stop"):
                    with patch.object(adapter.tui, "update_tool"):
                        with patch.object(adapter.process_manager, "save_run") as mock_save:
                            adapter._run_validation_child(files, tools)

                            # Verify failure recorded
                            saved_run = mock_save.call_args[0][0]
                            assert saved_run.success is False
                            assert saved_run.errors == 18  # 5 + 3 + 10
                            assert saved_run.warnings == 3  # 0 + 1 + 2
                            assert saved_run.exit_code == 1

                            # Verify exit with failure
                            mock_exit.assert_called_once_with(1)

    @patch("sys.exit")
    def test_child_validation_partial_success(self, mock_exit):
        """Test handling when some tools succeed and some fail."""
        adapter = NonBlockingGitHooksAdapter()

        tools = {
            "black": MagicMock(),
            "ruff": MagicMock(),
        }
        files = ["test.py"]

        # Mock mixed results
        with patch.object(adapter.executor, "execute_tools") as mock_execute:
            mock_execute.return_value = [
                ToolResult("black", True, 0.5, 0, 0),
                ToolResult("ruff", False, 0.3, 2, 1),
            ]

            with patch.object(adapter.tui, "start"):
                with patch.object(adapter.tui, "stop"):
                    with patch.object(adapter.tui, "update_tool"):
                        with patch.object(adapter.process_manager, "save_run") as mock_save:
                            adapter._run_validation_child(files, tools)

                            # Verify overall failure due to ruff
                            saved_run = mock_save.call_args[0][0]
                            assert saved_run.success is False
                            assert saved_run.exit_code == 1

                            mock_exit.assert_called_once_with(1)


class TestOutputFormatting:
    """Test output formatting methods."""

    def test_format_output_returns_empty(self):
        """Test that format_output returns empty string."""
        adapter = NonBlockingGitHooksAdapter()

        # Non-blocking adapter doesn't format output (handled by child)
        output = adapter.format_output({}, {})
        assert output == ""

    def test_format_output_with_various_inputs(self):
        """Test format_output always returns empty regardless of input."""
        adapter = NonBlockingGitHooksAdapter()

        # Various inputs should all return empty
        assert adapter.format_output({"file": "data"}, {}) == ""
        assert adapter.format_output({}, {"summary": "data"}) == ""
        assert adapter.format_output({"a": 1, "b": 2}, {"x": 10}) == ""


class TestProgressCallbackMapping:
    """Test progress callback status mapping."""

    @patch("sys.exit")
    def test_progress_callback_status_mapping(self, mock_exit):
        """Test that status strings map correctly to ToolState enum."""
        adapter = NonBlockingGitHooksAdapter()

        tools = {"black": MagicMock()}
        files = ["test.py"]

        captured_callback = None

        def capture_callback(*args, **kwargs):
            nonlocal captured_callback
            captured_callback = kwargs.get("progress_callback")
            return [ToolResult("black", True, 0.5, 0, 0)]

        with patch.object(adapter.executor, "execute_tools") as mock_execute:
            mock_execute.side_effect = capture_callback

            with patch.object(adapter.tui, "start"):
                with patch.object(adapter.tui, "stop"):
                    with patch.object(adapter.tui, "update_tool") as mock_update:
                        with patch.object(adapter.process_manager, "save_run"):
                            adapter._run_validation_child(files, tools)

                            # Test all status mappings
                            status_tests = [
                                ("pending", ToolState.PENDING),
                                ("running", ToolState.RUNNING),
                                ("success", ToolState.SUCCESS),
                                ("failed", ToolState.FAILED),
                                ("skipped", ToolState.SKIPPED),
                            ]

                            for status_str, expected_state in status_tests:
                                mock_update.reset_mock()
                                captured_callback("test-tool", status_str)

                                # Verify correct state passed to TUI
                                assert mock_update.called
                                call_kwargs = mock_update.call_args[1]
                                assert call_kwargs["state"] == expected_state

    @patch("sys.exit")
    def test_progress_callback_unknown_status(self, mock_exit):
        """Test handling of unknown status in progress callback."""
        adapter = NonBlockingGitHooksAdapter()

        tools = {"black": MagicMock()}
        files = ["test.py"]

        captured_callback = None

        def capture_callback(*args, **kwargs):
            nonlocal captured_callback
            captured_callback = kwargs.get("progress_callback")
            return [ToolResult("black", True, 0.5, 0, 0)]

        with patch.object(adapter.executor, "execute_tools") as mock_execute:
            mock_execute.side_effect = capture_callback

            with patch.object(adapter.tui, "start"):
                with patch.object(adapter.tui, "stop"):
                    with patch.object(adapter.tui, "update_tool") as mock_update:
                        with patch.object(adapter.process_manager, "save_run"):
                            adapter._run_validation_child(files, tools)

                            # Test unknown status defaults to RUNNING
                            mock_update.reset_mock()
                            captured_callback("test-tool", "unknown_status")

                            # Should default to RUNNING
                            assert mock_update.called
                            call_kwargs = mock_update.call_args[1]
                            assert call_kwargs["state"] == ToolState.RUNNING


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
