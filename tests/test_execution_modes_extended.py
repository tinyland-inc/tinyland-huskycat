#!/usr/bin/env python3
"""
Extended tests for unified_validation.py execution modes.

Comprehensive test coverage for:
- Bundled tool execution and path resolution
- Container fallback mechanisms
- Mode detection and switching
- Error handling across execution modes
- Performance characteristics
- Concurrent execution scenarios
"""

import logging
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

from src.huskycat.unified_validation import BlackValidator, ValidationResult, Validator


class TestBundledToolExecution:
    """Test bundled tool execution and path resolution."""

    def test_bundled_tool_path_resolution_success(self):
        """Test correct bundled tool path is resolved."""
        validator = BlackValidator()

        with mock.patch.object(Path, "exists", return_value=True):
            result = validator._get_bundled_tool_path()

            assert result is not None
            assert "python-black" in str(result)
            assert ".huskycat" in str(result)

    def test_bundled_tool_path_directory_not_exists(self):
        """Test bundled tool path when directory doesn't exist."""
        validator = BlackValidator()

        with mock.patch.object(Path, "exists", return_value=False):
            result = validator._get_bundled_tool_path()

            assert result is None

    def test_bundled_tool_path_tool_not_exists(self):
        """Test bundled tool path when tool file doesn't exist."""
        validator = BlackValidator()

        # Use a counter object to track call count
        call_counter = {"count": 0}

        def exists_side_effect():
            # First call for directory, second for tool file
            call_counter["count"] += 1

            # Directory exists but tool doesn't
            if call_counter["count"] == 1:
                return True
            return False

        with mock.patch.object(Path, "exists", side_effect=exists_side_effect):
            result = validator._get_bundled_tool_path()

            assert result is None

    def test_bundled_tool_execution_success(self):
        """Test successful execution of bundled tool."""
        validator = BlackValidator()
        bundled_path = Path.home() / ".huskycat" / "tools" / "python-black"

        with mock.patch.object(validator, "_get_bundled_tool_path", return_value=bundled_path):
            with mock.patch("subprocess.run") as mock_run:
                mock_result = mock.Mock()
                mock_result.returncode = 0
                mock_result.stdout = "File formatted"
                mock_run.return_value = mock_result

                result = validator._execute_bundled(
                    ["python-black", "--check", "file.py"],
                    capture_output=True,
                )

                assert result.returncode == 0
                assert result.stdout == "File formatted"

                # Verify command was executed with full path
                mock_run.assert_called_once()
                called_cmd = mock_run.call_args[0][0]
                assert str(bundled_path) in called_cmd[0]

    def test_bundled_tool_execution_tool_not_found(self):
        """Test bundled tool execution when tool doesn't exist."""
        validator = BlackValidator()

        with mock.patch.object(validator, "_get_bundled_tool_path", return_value=None):
            with pytest.raises(RuntimeError, match="Bundled tool"):
                validator._execute_bundled(["python-black", "file.py"])

    def test_bundled_tool_command_format(self):
        """Test that bundled tool command is correctly formatted."""
        validator = BlackValidator()
        bundled_path = Path.home() / ".huskycat" / "tools" / "python-black"

        with mock.patch.object(validator, "_get_bundled_tool_path", return_value=bundled_path):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0

                validator._execute_bundled(
                    ["python-black", "--check", "--line-length", "88", "file.py"],
                    capture_output=True,
                )

                mock_run.assert_called_once()
                called_cmd = mock_run.call_args[0][0]

                # First element should be full path
                assert called_cmd[0] == str(bundled_path)
                # Other elements should be preserved
                assert "--check" in called_cmd
                assert "--line-length" in called_cmd
                assert "88" in called_cmd
                assert "file.py" in called_cmd

    def test_bundled_tool_stderr_capture(self):
        """Test that bundled tool stderr is captured."""
        validator = BlackValidator()
        bundled_path = Path.home() / ".huskycat" / "tools" / "python-black"

        with mock.patch.object(validator, "_get_bundled_tool_path", return_value=bundled_path):
            with mock.patch("subprocess.run") as mock_run:
                mock_result = mock.Mock()
                mock_result.returncode = 1
                mock_result.stderr = "Error: File not found"
                mock_run.return_value = mock_result

                result = validator._execute_bundled(
                    ["python-black", "file.py"],
                    capture_output=True,
                )

                assert result.returncode == 1
                assert result.stderr == "Error: File not found"


class TestContainerFallback:
    """Test container fallback mechanisms."""

    def test_container_fallback_when_no_local_tools(self):
        """Test fallback to container when local tools unavailable."""
        validator = BlackValidator()

        with mock.patch.object(validator, "_get_execution_mode", return_value="local"):
            with mock.patch("shutil.which", return_value=None):
                with mock.patch.object(validator, "_container_runtime_exists", return_value=True):
                    # The validator should fall back to container when local tool not found
                    assert validator.is_available() is False  # No local tool

    def test_container_fallback_execution(self):
        """Test container fallback execution path."""
        validator = BlackValidator()

        with mock.patch.object(validator, "_get_execution_mode", return_value="local"):
            with mock.patch("shutil.which", return_value=None):
                with mock.patch.object(
                    validator, "_container_runtime_exists", return_value=True
                ):
                    with mock.patch("subprocess.run") as mock_run:
                        mock_run.return_value.returncode = 0

                        # When executing with no local tool, should use container
                        cmd = ["python-black", "file.py"]
                        result = validator._execute_command(cmd, capture_output=True)

                        # Verify command was executed
                        assert mock_run.called

    def test_container_fallback_with_podman(self):
        """Test container fallback with podman runtime."""
        validator = BlackValidator()

        with mock.patch("subprocess.run") as mock_run:
            # First call: podman --version succeeds
            def run_side_effect(*args, **kwargs):
                result = mock.Mock()
                result.returncode = 0
                return result

            mock_run.side_effect = run_side_effect

            runtime = validator._get_available_container_runtime()

            assert runtime == "podman"

    def test_container_fallback_with_docker(self):
        """Test container fallback with docker runtime."""
        validator = BlackValidator()

        def run_side_effect(*args, **kwargs):
            cmd = args[0]
            result = mock.Mock()

            if "podman" in cmd[0]:
                raise FileNotFoundError
            if "docker" in cmd[0]:
                result.returncode = 0
                return result

            raise FileNotFoundError

        with mock.patch("subprocess.run", side_effect=run_side_effect):
            runtime = validator._get_available_container_runtime()

            assert runtime == "docker"

    def test_container_fallback_no_runtime_available(self):
        """Test container fallback when no runtime available."""
        validator = BlackValidator()

        with mock.patch("subprocess.run", side_effect=FileNotFoundError()):
            with pytest.raises(RuntimeError):
                validator._get_available_container_runtime()

    def test_container_command_format(self):
        """Test container command is correctly formatted."""
        validator = BlackValidator()

        with mock.patch.object(validator, "_get_available_container_runtime", return_value="podman"):
            cmd = ["python-black", "--check", "file.py"]
            container_cmd = validator._build_container_command(cmd)

            assert container_cmd[0] == "podman"
            assert "run" in container_cmd
            assert "--rm" in container_cmd
            assert "--entrypoint=" in container_cmd
            assert "-v" in container_cmd
            assert "-w" in container_cmd
            assert "/workspace" in container_cmd
            assert cmd[0] in container_cmd

    def test_container_command_mounts_current_directory(self):
        """Test container command mounts current directory."""
        validator = BlackValidator()
        current_dir = Path.cwd()

        with mock.patch.object(validator, "_get_available_container_runtime", return_value="docker"):
            cmd = ["python-black", "file.py"]
            container_cmd = validator._build_container_command(cmd)

            # Find the volume mount
            volume_idx = container_cmd.index("-v")
            volume_mount = container_cmd[volume_idx + 1]

            assert str(current_dir) in volume_mount
            assert "/workspace" in volume_mount


class TestExecutionModeDetection:
    """Test execution mode detection and switching."""

    def test_container_detection_dockerenv(self):
        """Test container detection via /.dockerenv."""
        validator = BlackValidator()

        with mock.patch("os.path.exists") as mock_exists:
            mock_exists.side_effect = lambda p: p == "/.dockerenv"

            assert validator._is_running_in_container() is True

    def test_container_detection_container_env(self):
        """Test container detection via environment variable."""
        validator = BlackValidator()

        with mock.patch.dict(os.environ, {"container": "docker"}):
            with mock.patch("os.path.exists", return_value=False):
                assert validator._is_running_in_container() is True

    def test_container_detection_podmanenv(self):
        """Test container detection via /run/.containerenv."""
        validator = BlackValidator()

        with mock.patch("os.path.exists") as mock_exists:
            mock_exists.side_effect = lambda p: p == "/run/.containerenv"

            assert validator._is_running_in_container() is True

    def test_not_in_container_all_checks_fail(self):
        """Test not in container when all detection checks fail."""
        validator = BlackValidator()

        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("os.path.exists", return_value=False):
                assert validator._is_running_in_container() is False

    def test_mode_detection_priority_container_first(self):
        """Test mode detection prioritizes container check."""
        validator = BlackValidator()

        with mock.patch.object(validator, "_is_running_in_container", return_value=True):
            with mock.patch.object(sys, "frozen", True, create=True):
                mode = validator._get_execution_mode()

                assert mode == "container"

    def test_mode_detection_priority_bundled_second(self):
        """Test mode detection prioritizes bundled after container."""
        validator = BlackValidator()

        with mock.patch.object(validator, "_is_running_in_container", return_value=False):
            with mock.patch.object(sys, "frozen", True, create=True):
                Path.home() / ".huskycat" / "tools"

                with mock.patch.object(Path, "exists", return_value=True):
                    mode = validator._get_execution_mode()

                    assert mode == "bundled"

    def test_mode_detection_defaults_to_local(self):
        """Test mode detection defaults to local."""
        validator = BlackValidator()

        with mock.patch.object(validator, "_is_running_in_container", return_value=False):
            # No sys.frozen
            if hasattr(sys, "frozen"):
                delattr(sys, "frozen")

            with mock.patch("os.path.exists", return_value=False):
                mode = validator._get_execution_mode()

                assert mode == "local"


class TestToolAvailabilityDetection:
    """Test tool availability detection across modes."""

    def test_tool_available_bundled_mode(self):
        """Test tool availability in bundled mode."""
        validator = BlackValidator()

        # Create a mock path object
        mock_path = mock.Mock(spec=Path)
        mock_path.exists.return_value = True

        with mock.patch.object(validator, "_get_execution_mode", return_value="bundled"):
            with mock.patch.object(validator, "_get_bundled_tool_path", return_value=mock_path):
                with mock.patch("os.access", return_value=True):
                    assert validator.is_available() is True

    def test_tool_unavailable_bundled_not_executable(self):
        """Test tool unavailable in bundled mode when not executable."""
        validator = BlackValidator()

        # Create a mock path object
        mock_path = mock.Mock(spec=Path)
        mock_path.exists.return_value = True

        with mock.patch.object(validator, "_get_execution_mode", return_value="bundled"):
            with mock.patch.object(validator, "_get_bundled_tool_path", return_value=mock_path):
                with mock.patch("os.access", return_value=False):
                    assert validator.is_available() is False

    def test_tool_unavailable_bundled_path_none(self):
        """Test tool unavailable in bundled mode when path is None."""
        validator = BlackValidator()

        with mock.patch.object(validator, "_get_execution_mode", return_value="bundled"):
            with mock.patch.object(validator, "_get_bundled_tool_path", return_value=None):
                assert validator.is_available() is False

    def test_tool_available_local_mode(self):
        """Test tool availability in local mode."""
        validator = BlackValidator()

        with mock.patch.object(validator, "_get_execution_mode", return_value="local"):
            with mock.patch("shutil.which", return_value="/usr/bin/python-black"):
                assert validator.is_available() is True

    def test_tool_unavailable_local_mode(self):
        """Test tool unavailable in local mode."""
        validator = BlackValidator()

        with mock.patch.object(validator, "_get_execution_mode", return_value="local"):
            with mock.patch("shutil.which", return_value=None):
                with mock.patch.object(
                    validator, "_container_runtime_exists", return_value=False
                ):
                    assert validator.is_available() is False

    def test_tool_available_container_mode(self):
        """Test tool availability in container mode."""
        validator = BlackValidator()

        with mock.patch.object(validator, "_get_execution_mode", return_value="container"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0

                assert validator.is_available() is True

    def test_tool_unavailable_container_mode_which_fails(self):
        """Test tool unavailable in container mode when which fails."""
        validator = BlackValidator()

        with mock.patch.object(validator, "_get_execution_mode", return_value="container"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 1

                assert validator.is_available() is False

    def test_tool_unavailable_container_mode_exception(self):
        """Test tool unavailable in container mode when subprocess fails."""
        validator = BlackValidator()

        with mock.patch.object(validator, "_get_execution_mode", return_value="container"):
            with mock.patch("subprocess.run", side_effect=subprocess.SubprocessError()):
                assert validator.is_available() is False


class TestContainerRuntimeDetection:
    """Test container runtime detection."""

    def test_podman_runtime_available(self):
        """Test podman runtime detection."""
        validator = BlackValidator()

        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0

            result = validator._container_runtime_exists()

            assert result is True

    def test_docker_runtime_available_after_podman_fails(self):
        """Test docker runtime fallback when podman fails."""
        validator = BlackValidator()

        def run_side_effect(*args, **kwargs):
            cmd = args[0]
            result = mock.Mock()

            if "podman" in cmd[0]:
                raise FileNotFoundError
            if "docker" in cmd[0]:
                result.returncode = 0
                return result

            raise FileNotFoundError

        with mock.patch("subprocess.run", side_effect=run_side_effect):
            result = validator._container_runtime_exists()

            assert result is True

    def test_no_container_runtime_available(self):
        """Test when no container runtime available."""
        validator = BlackValidator()

        with mock.patch("subprocess.run", side_effect=FileNotFoundError()):
            result = validator._container_runtime_exists()

            assert result is False

    def test_runtime_detection_timeout_handled(self):
        """Test that subprocess timeout is handled gracefully."""
        validator = BlackValidator()

        with mock.patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("cmd", 5)

            result = validator._container_runtime_exists()

            assert result is False


class TestExecutionModeLogging:
    """Test execution mode logging."""

    def test_log_bundled_mode(self, caplog):
        """Test logging for bundled mode includes tool name."""
        validator = BlackValidator()

        with caplog.at_level(logging.DEBUG):
            validator._log_execution_mode("bundled")

            assert "bundled" in caplog.text.lower()

    def test_log_local_mode(self, caplog):
        """Test logging for local mode."""
        validator = BlackValidator()

        with caplog.at_level(logging.DEBUG):
            validator._log_execution_mode("local")

            assert "local" in caplog.text.lower()

    def test_log_container_mode(self, caplog):
        """Test logging for container mode."""
        validator = BlackValidator()

        with caplog.at_level(logging.DEBUG):
            validator._log_execution_mode("container")

            assert "container" in caplog.text.lower()

    def test_log_bundled_mode_includes_tools_dir(self, caplog):
        """Test bundled mode logging includes tools directory."""
        validator = BlackValidator()

        with caplog.at_level(logging.DEBUG):
            validator._log_execution_mode("bundled")

            assert ".huskycat" in caplog.text


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_validation_result_to_dict(self):
        """Test ValidationResult serialization to dict."""
        result = ValidationResult(
            tool="black",
            filepath="test.py",
            success=True,
            messages=["File formatted"],
            errors=[],
            warnings=[],
            fixed=True,
            duration_ms=100,
        )

        result_dict = result.to_dict()

        assert result_dict["tool"] == "black"
        assert result_dict["filepath"] == "test.py"
        assert result_dict["success"] is True
        assert result_dict["fixed"] is True
        assert result_dict["duration_ms"] == 100

    def test_validation_result_error_count(self):
        """Test ValidationResult error count property."""
        result = ValidationResult(
            tool="mypy",
            filepath="test.py",
            success=False,
            errors=["Error 1", "Error 2", "Error 3"],
        )

        assert result.error_count == 3

    def test_validation_result_warning_count(self):
        """Test ValidationResult warning count property."""
        result = ValidationResult(
            tool="ruff",
            filepath="test.py",
            success=True,
            warnings=["Warning 1", "Warning 2"],
        )

        assert result.warning_count == 2

    def test_validation_result_empty_errors_and_warnings(self):
        """Test ValidationResult with empty errors and warnings."""
        result = ValidationResult(
            tool="black",
            filepath="test.py",
            success=True,
        )

        assert result.error_count == 0
        assert result.warning_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
