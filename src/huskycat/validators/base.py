#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
HuskyCat Validators Base Module

Contains the base classes for all validators:
- ValidationResult: Dataclass for validation results
- Validator: Abstract base class for all validators
"""

import logging
import os
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Unified result of a validation operation"""

    tool: str
    filepath: str
    success: bool
    messages: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    fixed: bool = False
    duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "tool": self.tool,
            "filepath": self.filepath,
            "success": self.success,
            "messages": self.messages,
            "errors": self.errors,
            "warnings": self.warnings,
            "fixed": self.fixed,
            "duration_ms": self.duration_ms,
        }

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)


class Validator(ABC):
    """Abstract base class for all validators"""

    def __init__(self, auto_fix: bool = False):
        self.auto_fix = auto_fix

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this validator"""

    @property
    @abstractmethod
    def extensions(self) -> Set[str]:
        """File extensions this validator handles"""

    @property
    def command(self) -> str:
        """Command to check if tool is available"""
        return self.name

    def is_available(self) -> bool:
        """Check if validator is available in current execution context

        Priority order:
        1. GPL sidecar (for GPL tools when sidecar is running)
        2. Bundled tools (from fat binary)
        3. Local tools (in PATH)
        4. Container runtime (fallback only)
        """
        # Import here to avoid circular imports
        from huskycat.validators._utils import is_gpl_tool, get_gpl_sidecar

        # Check if this is a GPL tool and sidecar is available
        if is_gpl_tool(self.name):
            sidecar = get_gpl_sidecar()
            if sidecar is not None:
                logger.debug(f"GPL tool {self.name} available via sidecar")
                return True
            # Fall through to check local availability

        mode = self._get_execution_mode()

        if mode == "bundled":
            # Check extracted tools directory
            tool_path = self._get_bundled_tool_path()
            return (
                tool_path is not None
                and tool_path.exists()
                and os.access(tool_path, os.X_OK)
            )

        if mode == "local":
            # Check PATH for local tools
            return shutil.which(self.command) is not None

        if mode == "container":
            # Already in container - check tool in PATH
            try:
                result = subprocess.run(
                    ["which", self.command], capture_output=True, text=True, timeout=5
                )
                return result.returncode == 0
            except (subprocess.SubprocessError, FileNotFoundError):
                return False

        # Fallback: check for container runtime (legacy behavior)
        return self._container_runtime_exists()

    def _get_execution_mode(self) -> str:
        """Detect execution mode

        Returns:
            - "bundled": Running from PyInstaller bundle with embedded tools
            - "local": Running from source with tools in PATH
            - "container": Running inside container
        """
        # Check if running inside container first
        if self._is_running_in_container():
            return "container"

        # Check if running from PyInstaller bundle
        if getattr(sys, "frozen", False):
            # PyInstaller bundle - check if tools were extracted
            bundled_path = Path.home() / ".huskycat" / "tools"
            if bundled_path.exists():
                return "bundled"

        # Default to local mode (running from source or no bundled tools)
        return "local"

    def _is_running_in_container(self) -> bool:
        """Detect if we're running inside a container"""
        # Check for container-specific environment indicators
        return (
            os.path.exists("/.dockerenv")  # Docker
            or bool(os.environ.get("container"))  # Podman
            or os.path.exists("/run/.containerenv")  # Podman
        )

    def _get_bundled_tool_path(self) -> Optional[Path]:
        """Get path to bundled tool if available

        Returns:
            Path to tool, or None if not bundled
        """
        bundled_dir = Path.home() / ".huskycat" / "tools"
        if not bundled_dir.exists():
            return None

        tool_path = bundled_dir / self.command
        if tool_path.exists():
            return tool_path

        return None

    def _container_runtime_exists(self) -> bool:
        """Check if a container runtime is available

        Returns:
            True if podman or docker is available
        """
        for runtime in ["podman", "docker"]:
            try:
                result = subprocess.run(
                    [runtime, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    return True
            except (subprocess.SubprocessError, FileNotFoundError):
                continue
        return False

    def _execute_command(
        self, cmd: List[str], **kwargs: Any
    ) -> subprocess.CompletedProcess:
        """Execute command with mode-aware execution

        Priority order:
        1. GPL sidecar (for GPL tools when sidecar is running)
        2. Bundled tools (direct execution)
        3. Local tools (direct execution)
        4. Container tools (already in container)
        5. Container runtime (fallback delegation)
        """
        # Import here to avoid circular imports
        from huskycat.validators._utils import is_gpl_tool, get_gpl_sidecar

        # Check if this is a GPL tool and sidecar is available
        if is_gpl_tool(self.name):
            sidecar = get_gpl_sidecar()
            if sidecar is not None:
                return self._execute_via_sidecar(sidecar, cmd, **kwargs)

        mode = self._get_execution_mode()

        if mode == "bundled":
            # Use bundled tools directly
            self._log_execution_mode(mode)
            return self._execute_bundled(cmd, **kwargs)

        if mode == "local":
            # Use local tools directly
            self._log_execution_mode(mode)
            return self._execute_local(cmd, **kwargs)

        if mode == "container":
            # Already in container - direct execution
            self._log_execution_mode(mode)
            return subprocess.run(cmd, **kwargs)

        # Fallback: delegate to container (legacy behavior)
        logger.warning(f"Falling back to container execution for {self.command}")
        container_cmd = self._build_container_command(cmd)
        return subprocess.run(container_cmd, **kwargs)

    def _execute_via_sidecar(
        self, sidecar: Any, cmd: List[str], **kwargs: Any
    ) -> subprocess.CompletedProcess:
        """Execute GPL tool via IPC sidecar.

        Args:
            sidecar: GPL sidecar client
            cmd: Command list where first element is tool name
            **kwargs: Additional arguments (timeout extracted if present)

        Returns:
            subprocess.CompletedProcess-like object with stdout, stderr, returncode
        """
        from huskycat.core.gpl_client import GPLSidecarError

        self._log_execution_mode("gpl_sidecar")

        # Extract tool name and args from command
        tool = cmd[0]
        args = cmd[1:] if len(cmd) > 1 else []

        # Get timeout from kwargs (convert to ms)
        timeout_s = kwargs.get("timeout", 30)
        timeout_ms = int(timeout_s * 1000)

        # Get working directory
        cwd = kwargs.get("cwd", os.getcwd())

        logger.debug(f"Executing {tool} via GPL sidecar: {args}")

        try:
            result = sidecar.execute(tool, args, cwd=str(cwd), timeout_ms=timeout_ms)

            # Convert GPLToolResult to subprocess.CompletedProcess
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=result.exit_code,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        except GPLSidecarError as e:
            logger.error(f"GPL sidecar execution failed: {e}")
            # Return error result
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=1,
                stdout="",
                stderr=str(e),
            )

    def _execute_bundled(
        self, cmd: List[str], **kwargs: Any
    ) -> subprocess.CompletedProcess:
        """Execute using bundled tools

        Args:
            cmd: Command list where first element is tool name
            **kwargs: Additional subprocess arguments

        Returns:
            CompletedProcess result
        """
        tool_path = self._get_bundled_tool_path()

        if not tool_path:
            raise RuntimeError(f"Bundled tool {self.command} not found")

        # Replace tool name with full path
        bundled_cmd = [str(tool_path)] + cmd[1:]

        return subprocess.run(bundled_cmd, **kwargs)

    def _execute_local(
        self, cmd: List[str], **kwargs: Any
    ) -> subprocess.CompletedProcess:
        """Execute using local tools in PATH

        Args:
            cmd: Command list
            **kwargs: Additional subprocess arguments

        Returns:
            CompletedProcess result
        """
        # Direct execution using PATH lookup
        return subprocess.run(cmd, **kwargs)

    def _log_execution_mode(self, mode: str) -> None:
        """Log which execution mode is being used

        Args:
            mode: Execution mode (bundled/local/container)
        """
        logger.debug(f"Tool execution mode: {mode} (tool={self.command})")

        if mode == "bundled":
            tools_dir = Path.home() / ".huskycat" / "tools"
            logger.debug(f"Using bundled tools from: {tools_dir}")

    def _build_container_command(self, cmd: List[str]) -> List[str]:
        """Build container command for tool execution"""
        container_runtime = self._get_available_container_runtime()

        # Build container command that bypasses the ENTRYPOINT to run tools directly
        # Mount current directory as workspace and execute the validation command
        container_cmd = [
            container_runtime,
            "run",
            "--rm",
            "--entrypoint=",  # Override the entrypoint to run commands directly
            "-v",
            f"{Path.cwd()}:/workspace",
            "-w",
            "/workspace",
            "huskycat:local",
        ] + cmd

        return container_cmd

    def _get_available_container_runtime(self) -> str:
        """Get available container runtime (podman or docker)

        Returns:
            Name of available runtime

        Raises:
            RuntimeError: If no container runtime is available
        """
        for runtime in ["podman", "docker"]:
            try:
                result = subprocess.run(
                    [runtime, "--version"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    return runtime
            except (subprocess.SubprocessError, FileNotFoundError):
                continue

        # No container runtime available
        raise RuntimeError(
            f"No container runtime available for tool {self.command}.\n"
            "Options:\n"
            "1. Install tools locally (recommended)\n"
            "2. Use fat binary with embedded tools\n"
            "3. Install container runtime:\n"
            "   - Podman: https://podman.io/getting-started/installation\n"
            "   - Docker: https://docs.docker.com/get-docker/"
        )

    @abstractmethod
    def validate(self, filepath: Path) -> ValidationResult:
        """Validate a single file"""

    def can_handle(self, filepath: Path) -> bool:
        """Check if this validator can handle the given file"""
        return filepath.suffix in self.extensions
