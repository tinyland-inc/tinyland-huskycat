#!/usr/bin/env python3
"""Tests for embedded tool execution modes.

This test suite validates the refactored unified_validation.py
execution mode detection and tool resolution logic.
"""

import os
import sys
from pathlib import Path
from unittest import mock

import pytest

from src.huskycat.unified_validation import BlackValidator, Validator


class TestExecutionModeDetection:
    """Test execution mode detection logic."""

    def test_container_mode_detection_dockerenv(self):
        """Test container mode detection via /.dockerenv."""
        validator = BlackValidator()

        with mock.patch("os.path.exists") as mock_exists:
            mock_exists.side_effect = lambda p: p == "/.dockerenv"

            mode = validator._get_execution_mode()
            assert mode == "container"

    def test_container_mode_detection_podman(self):
        """Test container mode detection via /run/.containerenv."""
        validator = BlackValidator()

        with mock.patch("os.path.exists") as mock_exists:
            mock_exists.side_effect = lambda p: p == "/run/.containerenv"

            mode = validator._get_execution_mode()
            assert mode == "container"

    def test_container_mode_detection_env_var(self):
        """Test container mode detection via environment variable."""
        validator = BlackValidator()

        with mock.patch.dict(os.environ, {"container": "podman"}):
            with mock.patch("os.path.exists", return_value=True):
                mode = validator._get_execution_mode()
                assert mode == "container"

    def test_bundled_mode_detection(self):
        """Test bundled mode detection (PyInstaller)."""
        validator = BlackValidator()

        # Mock sys.frozen and Path.exists properly
        bundled_dir = Path.home() / ".huskycat" / "tools"

        with mock.patch.object(sys, "frozen", True, create=True):
            with mock.patch.object(Path, "exists") as mock_exists:
                # Return True for bundled tools directory
                mock_exists.return_value = True

                mode = validator._get_execution_mode()
                assert mode == "bundled"

    def test_local_mode_detection(self):
        """Test local mode detection (development)."""
        validator = BlackValidator()

        # Mock both container check and bundled check to be false
        with mock.patch("os.path.exists", return_value=False):
            # No sys.frozen attribute (running from source)
            if hasattr(sys, 'frozen'):
                delattr(sys, 'frozen')

            mode = validator._get_execution_mode()
            assert mode == "local"


class TestToolAvailability:
    """Test tool availability checks across modes."""

    def test_bundled_tool_available(self):
        """Test tool availability in bundled mode."""
        validator = BlackValidator()

        bundled_path = Path.home() / ".huskycat" / "tools" / "python-black"

        with mock.patch.object(validator, "_get_execution_mode", return_value="bundled"):
            with mock.patch.object(Path, "exists", return_value=True):
                with mock.patch("os.access", return_value=True):
                    assert validator.is_available() is True

    def test_bundled_tool_not_executable(self):
        """Test tool unavailable if not executable."""
        validator = BlackValidator()

        with mock.patch.object(validator, "_get_execution_mode", return_value="bundled"):
            with mock.patch.object(Path, "exists", return_value=True):
                with mock.patch("os.access", return_value=False):
                    assert validator.is_available() is False

    def test_local_tool_available(self):
        """Test tool availability in local mode."""
        validator = BlackValidator()

        with mock.patch.object(validator, "_get_execution_mode", return_value="local"):
            with mock.patch("shutil.which", return_value="/usr/bin/python-black"):
                assert validator.is_available() is True

    def test_local_tool_not_in_path(self):
        """Test tool unavailable if not in PATH."""
        validator = BlackValidator()

        with mock.patch.object(validator, "_get_execution_mode", return_value="local"):
            with mock.patch("shutil.which", return_value=None):
                assert validator.is_available() is False

    def test_container_tool_available(self):
        """Test tool availability in container mode."""
        validator = BlackValidator()

        with mock.patch.object(validator, "_get_execution_mode", return_value="container"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                assert validator.is_available() is True

    def test_container_fallback_not_available(self):
        """Test container runtime fallback when tool not in PATH."""
        validator = BlackValidator()

        with mock.patch.object(validator, "_get_execution_mode", return_value="local"):
            with mock.patch("shutil.which", return_value=None):
                with mock.patch.object(
                    validator, "_container_runtime_exists", return_value=False
                ):
                    # No local tool, no container runtime
                    assert validator.is_available() is False


class TestBundledToolPathResolution:
    """Test bundled tool path resolution."""

    def test_get_bundled_tool_path_exists(self):
        """Test resolving bundled tool path when it exists."""
        validator = BlackValidator()

        bundled_dir = Path.home() / ".huskycat" / "tools"
        tool_path = bundled_dir / "python-black"

        with mock.patch.object(Path, "exists", side_effect=lambda: True):
            result = validator._get_bundled_tool_path()
            # Should return path to bundled tool
            assert result is not None
            assert "python-black" in str(result)

    def test_get_bundled_tool_path_not_exists(self):
        """Test resolving bundled tool path when directory doesn't exist."""
        validator = BlackValidator()

        with mock.patch.object(Path, "exists", return_value=False):
            result = validator._get_bundled_tool_path()
            assert result is None


class TestCommandExecution:
    """Test command execution across modes."""

    def test_execute_bundled_mode(self):
        """Test command execution in bundled mode."""
        validator = BlackValidator()

        bundled_path = Path.home() / ".huskycat" / "tools" / "python-black"

        with mock.patch.object(validator, "_get_execution_mode", return_value="bundled"):
            with mock.patch.object(
                validator, "_get_bundled_tool_path", return_value=bundled_path
            ):
                with mock.patch("subprocess.run") as mock_run:
                    mock_run.return_value.returncode = 0

                    cmd = ["python-black", "--check", "file.py"]
                    validator._execute_command(cmd, capture_output=True)

                    # Should call with full path to bundled tool
                    mock_run.assert_called_once()
                    called_cmd = mock_run.call_args[0][0]
                    assert str(bundled_path) in called_cmd[0]
                    assert "--check" in called_cmd
                    assert "file.py" in called_cmd

    def test_execute_local_mode(self):
        """Test command execution in local mode."""
        validator = BlackValidator()

        with mock.patch.object(validator, "_get_execution_mode", return_value="local"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0

                cmd = ["python-black", "--check", "file.py"]
                validator._execute_command(cmd, capture_output=True)

                # Should call with original command (PATH lookup)
                mock_run.assert_called_once()
                called_cmd = mock_run.call_args[0][0]
                assert called_cmd == cmd

    def test_execute_container_mode(self):
        """Test command execution in container mode."""
        validator = BlackValidator()

        with mock.patch.object(validator, "_get_execution_mode", return_value="container"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0

                cmd = ["python-black", "--check", "file.py"]
                validator._execute_command(cmd, capture_output=True)

                # Should call with original command (already in container)
                mock_run.assert_called_once()
                called_cmd = mock_run.call_args[0][0]
                assert called_cmd == cmd


class TestContainerRuntimeDetection:
    """Test container runtime detection."""

    def test_podman_available(self):
        """Test podman runtime detection."""
        validator = BlackValidator()

        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0

            assert validator._container_runtime_exists() is True

    def test_docker_available(self):
        """Test docker runtime detection."""
        validator = BlackValidator()

        def run_side_effect(*args, **kwargs):
            cmd = args[0]
            if "podman" in cmd[0]:
                raise FileNotFoundError()
            elif "docker" in cmd[0]:
                result = mock.Mock()
                result.returncode = 0
                return result
            raise FileNotFoundError()

        with mock.patch("subprocess.run", side_effect=run_side_effect):
            assert validator._container_runtime_exists() is True

    def test_no_container_runtime(self):
        """Test no container runtime available."""
        validator = BlackValidator()

        with mock.patch("subprocess.run", side_effect=FileNotFoundError()):
            assert validator._container_runtime_exists() is False


class TestExecutionModeLogging:
    """Test execution mode logging."""

    def test_log_bundled_mode(self, caplog):
        """Test logging for bundled mode."""
        import logging

        validator = BlackValidator()

        with caplog.at_level(logging.DEBUG):
            validator._log_execution_mode("bundled")

            assert "bundled" in caplog.text
            assert "python-black" in caplog.text

    def test_log_local_mode(self, caplog):
        """Test logging for local mode."""
        import logging

        validator = BlackValidator()

        with caplog.at_level(logging.DEBUG):
            validator._log_execution_mode("local")

            assert "local" in caplog.text

    def test_log_container_mode(self, caplog):
        """Test logging for container mode."""
        import logging

        validator = BlackValidator()

        with caplog.at_level(logging.DEBUG):
            validator._log_execution_mode("container")

            assert "container" in caplog.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
