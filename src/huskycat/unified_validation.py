#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
HuskyCat Unified Validation Engine
Single source of truth for all validation logic
Supports both CLI and MCP server modes
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from huskycat.core.tool_selector import (
    LintingMode,
    get_mode_from_env,
    get_tool_info,
    is_tool_bundled,
)

# Configure logging
logging.basicConfig(
    level=os.getenv("HUSKYCAT_LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
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
        1. Bundled tools (from fat binary)
        2. Local tools (in PATH)
        3. Container runtime (fallback only)
        """
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
        1. Bundled tools (direct execution)
        2. Local tools (direct execution)
        3. Container tools (already in container)
        4. Container runtime (fallback delegation)
        """
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


# Python Validators


class BlackValidator(Validator):
    """Python code formatter"""

    @property
    def name(self) -> str:
        return "python-black"

    @property
    def extensions(self) -> Set[str]:
        return {".py", ".pyi"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()
        cmd = [self.command, "--check", str(filepath)]

        if self.auto_fix:
            cmd.remove("--check")

        try:
            result = self._execute_command(
                cmd, capture_output=True, text=True, timeout=30
            )
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["File is properly formatted"],
                    fixed=self.auto_fix,
                    duration_ms=duration_ms,
                )
            else:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=False,
                    errors=["File needs formatting"],
                    messages=result.stdout.splitlines() if result.stdout else [],
                    duration_ms=duration_ms,
                )
        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )


class AutoflakeValidator(Validator):
    """Python import and unused variable cleaner"""

    @property
    def name(self) -> str:
        return "autoflake"

    @property
    def extensions(self) -> Set[str]:
        return {".py", ".pyi"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()

        # First check what autoflake would fix (dry run)
        check_cmd = [
            self.command,
            "--check",
            "--remove-all-unused-imports",
            "--remove-unused-variables",
            str(filepath),
        ]

        try:
            result = self._execute_command(
                check_cmd, capture_output=True, text=True, timeout=30
            )
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                # No changes needed
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["No unused imports or variables found"],
                    duration_ms=duration_ms,
                )
            else:
                # File needs fixing
                if self.auto_fix:
                    # Apply fixes
                    fix_cmd = [
                        self.command,
                        "--in-place",
                        "--remove-all-unused-imports",
                        "--remove-unused-variables",
                        str(filepath),
                    ]
                    fix_result = self._execute_command(
                        fix_cmd, capture_output=True, text=True, timeout=30
                    )

                    if fix_result.returncode == 0:
                        return ValidationResult(
                            tool=self.name,
                            filepath=str(filepath),
                            success=True,
                            messages=["Fixed unused imports and variables"],
                            fixed=True,
                            duration_ms=duration_ms,
                        )
                    else:
                        return ValidationResult(
                            tool=self.name,
                            filepath=str(filepath),
                            success=False,
                            errors=["Failed to apply autoflake fixes"],
                            messages=(
                                fix_result.stderr.splitlines()
                                if fix_result.stderr
                                else []
                            ),
                            duration_ms=duration_ms,
                        )
                else:
                    # Just report issues without fixing
                    return ValidationResult(
                        tool=self.name,
                        filepath=str(filepath),
                        success=False,
                        errors=["File has unused imports or variables"],
                        messages=["Run with --fix to automatically clean up"],
                        duration_ms=duration_ms,
                    )
        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )


class Flake8Validator(Validator):
    """Python linter"""

    @property
    def name(self) -> str:
        return "flake8"

    @property
    def extensions(self) -> Set[str]:
        return {".py", ".pyi"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()
        cmd = [self.command, str(filepath), "--format=json"]

        try:
            result = self._execute_command(
                cmd, capture_output=True, text=True, timeout=30
            )
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["No issues found"],
                    duration_ms=duration_ms,
                )
            else:
                errors = []
                warnings = []

                # Parse flake8 output
                for line in result.stdout.splitlines():
                    if ":" in line:
                        parts = line.split(":", 3)
                        if len(parts) >= 4:
                            msg = parts[3].strip()
                            if any(code in msg for code in ["E", "F"]):
                                errors.append(msg)
                            else:
                                warnings.append(msg)

                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=False,
                    errors=errors,
                    warnings=warnings,
                    duration_ms=duration_ms,
                )
        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )


class MypyValidator(Validator):
    """Python type checker"""

    @property
    def name(self) -> str:
        return "mypy"

    @property
    def extensions(self) -> Set[str]:
        return {".py", ".pyi"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()
        cmd = [self.command, str(filepath), "--no-error-summary"]

        try:
            result = self._execute_command(
                cmd, capture_output=True, text=True, timeout=30
            )
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["Type checking passed"],
                    duration_ms=duration_ms,
                )
            else:
                errors = []
                warnings = []

                for line in result.stdout.splitlines():
                    if "error:" in line:
                        errors.append(line)
                    elif "warning:" in line or "note:" in line:
                        warnings.append(line)

                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=False,
                    errors=errors,
                    warnings=warnings,
                    duration_ms=duration_ms,
                )
        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )


class RuffValidator(Validator):
    """Python fast linter"""

    @property
    def name(self) -> str:
        return "ruff"

    @property
    def extensions(self) -> Set[str]:
        return {".py", ".pyi"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()
        cmd = [self.command, "check", str(filepath), "--output-format=json"]

        # Add --fix flag if auto-fixing is enabled
        if self.auto_fix:
            cmd.insert(2, "--fix")

        try:
            result = self._execute_command(
                cmd, capture_output=True, text=True, timeout=30
            )

            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    fixed=self.auto_fix,
                    duration_ms=duration_ms,
                )

            # Parse JSON output
            messages = []
            errors = []
            if result.stdout:
                try:
                    import json

                    data = json.loads(result.stdout)
                    for issue in data:
                        msg = f"Line {issue.get('location', {}).get('row', '?')}: {issue.get('message', 'Unknown error')}"
                        messages.append(msg)
                        errors.append(msg)
                except json.JSONDecodeError:
                    errors = [result.stdout.strip()]
                    messages = [result.stdout.strip()]

            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                messages=messages,
                errors=errors,
                fixed=self.auto_fix and result.returncode == 0,
                duration_ms=duration_ms,
            )

        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )


class IsortValidator(Validator):
    """Python import sorting and organization"""

    @property
    def name(self) -> str:
        return "isort"

    @property
    def extensions(self) -> Set[str]:
        return {".py", ".pyi"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()

        # First check what isort would fix (dry run)
        check_cmd = [
            self.command,
            "--check-only",
            "--diff",
            str(filepath),
        ]

        try:
            result = self._execute_command(
                check_cmd, capture_output=True, text=True, timeout=30
            )
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                # Imports are already sorted
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["Imports are properly sorted"],
                    duration_ms=duration_ms,
                )
            else:
                # Imports need sorting
                if self.auto_fix:
                    # Apply fixes (isort modifies in-place by default)
                    fix_cmd = [
                        self.command,
                        str(filepath),
                    ]
                    fix_result = self._execute_command(
                        fix_cmd, capture_output=True, text=True, timeout=30
                    )

                    if fix_result.returncode == 0:
                        return ValidationResult(
                            tool=self.name,
                            filepath=str(filepath),
                            success=True,
                            messages=["Sorted and organized imports"],
                            fixed=True,
                            duration_ms=duration_ms,
                        )
                    else:
                        return ValidationResult(
                            tool=self.name,
                            filepath=str(filepath),
                            success=False,
                            errors=["Failed to sort imports"],
                            messages=(
                                fix_result.stderr.splitlines()
                                if fix_result.stderr
                                else []
                            ),
                            duration_ms=duration_ms,
                        )
                else:
                    # Just report issues without fixing
                    diff_lines = result.stdout.splitlines() if result.stdout else []
                    return ValidationResult(
                        tool=self.name,
                        filepath=str(filepath),
                        success=False,
                        errors=["Imports are not properly sorted"],
                        messages=(
                            diff_lines[:10]
                            if diff_lines
                            else ["Run with --fix to sort imports"]
                        ),
                        duration_ms=duration_ms,
                    )
        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )


# TOML Formatter


class TaploValidator(Validator):
    """TOML file formatter using taplo"""

    @property
    def name(self) -> str:
        return "taplo"

    @property
    def extensions(self) -> Set[str]:
        return {".toml"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()

        # First check what taplo would format (dry run with --check)
        check_cmd = [
            self.command,
            "fmt",
            "--check",
            str(filepath),
        ]

        try:
            result = self._execute_command(
                check_cmd, capture_output=True, text=True, timeout=30
            )
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                # File is already formatted
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["TOML file is properly formatted"],
                    duration_ms=duration_ms,
                )
            else:
                # File needs formatting
                if self.auto_fix:
                    # Apply formatting
                    fix_cmd = [
                        self.command,
                        "fmt",
                        str(filepath),
                    ]
                    fix_result = self._execute_command(
                        fix_cmd, capture_output=True, text=True, timeout=30
                    )

                    if fix_result.returncode == 0:
                        return ValidationResult(
                            tool=self.name,
                            filepath=str(filepath),
                            success=True,
                            messages=["Formatted TOML file"],
                            fixed=True,
                            duration_ms=duration_ms,
                        )
                    else:
                        # Formatting failed
                        error_output = (
                            fix_result.stderr
                            if fix_result.stderr
                            else fix_result.stdout
                        )
                        errors = (
                            [
                                line.strip()
                                for line in error_output.splitlines()
                                if line.strip()
                            ]
                            if error_output
                            else ["Failed to format TOML file"]
                        )
                        return ValidationResult(
                            tool=self.name,
                            filepath=str(filepath),
                            success=False,
                            errors=errors[:10],  # Limit to first 10 errors
                            messages=["Failed to format TOML file"],
                            duration_ms=duration_ms,
                        )
                else:
                    # Just report that formatting is needed
                    output = result.stdout if result.stdout else result.stderr
                    messages = []
                    if output:
                        # taplo --check shows which files need formatting
                        messages = [
                            line.strip() for line in output.splitlines() if line.strip()
                        ][:5]

                    if not messages:
                        messages = [
                            "TOML file needs formatting. Run with --fix to format."
                        ]

                    return ValidationResult(
                        tool=self.name,
                        filepath=str(filepath),
                        success=False,
                        errors=["TOML file is not properly formatted"],
                        messages=messages,
                        duration_ms=duration_ms,
                    )

        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )


# Terraform Formatter


class TerraformValidator(Validator):
    """Terraform configuration file formatter using terraform fmt"""

    @property
    def name(self) -> str:
        return "terraform"

    @property
    def extensions(self) -> Set[str]:
        return {".tf", ".tfvars"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()

        # First check what terraform would format (dry run with -check)
        check_cmd = [
            self.command,
            "fmt",
            "-check",
            str(filepath),
        ]

        try:
            result = self._execute_command(
                check_cmd, capture_output=True, text=True, timeout=30
            )
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                # File is already formatted
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["Terraform file is properly formatted"],
                    duration_ms=duration_ms,
                )
            else:
                # File needs formatting
                if self.auto_fix:
                    # Apply formatting
                    fix_cmd = [
                        self.command,
                        "fmt",
                        str(filepath),
                    ]
                    fix_result = self._execute_command(
                        fix_cmd, capture_output=True, text=True, timeout=30
                    )

                    if fix_result.returncode == 0:
                        return ValidationResult(
                            tool=self.name,
                            filepath=str(filepath),
                            success=True,
                            messages=["Formatted Terraform file"],
                            fixed=True,
                            duration_ms=duration_ms,
                        )
                    else:
                        # Formatting failed
                        error_output = (
                            fix_result.stderr
                            if fix_result.stderr
                            else fix_result.stdout
                        )
                        errors = (
                            [
                                line.strip()
                                for line in error_output.splitlines()
                                if line.strip()
                            ]
                            if error_output
                            else ["Failed to format Terraform file"]
                        )
                        return ValidationResult(
                            tool=self.name,
                            filepath=str(filepath),
                            success=False,
                            errors=errors[:10],  # Limit to first 10 errors
                            messages=["Failed to format Terraform file"],
                            duration_ms=duration_ms,
                        )
                else:
                    # Just report that formatting is needed
                    # terraform fmt -check outputs the filename if it needs formatting
                    output = result.stdout if result.stdout else result.stderr
                    messages = []
                    if output:
                        messages = [
                            line.strip() for line in output.splitlines() if line.strip()
                        ][:5]

                    if not messages:
                        messages = [
                            "Terraform file needs formatting. Run with --fix to format."
                        ]

                    return ValidationResult(
                        tool=self.name,
                        filepath=str(filepath),
                        success=False,
                        errors=["Terraform file is not properly formatted"],
                        messages=messages,
                        duration_ms=duration_ms,
                    )

        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )


class BanditValidator(Validator):
    """Python security vulnerability scanner"""

    @property
    def name(self) -> str:
        return "bandit"

    @property
    def extensions(self) -> Set[str]:
        return {".py", ".pyi"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()
        cmd = [self.command, "-f", "json", str(filepath)]

        try:
            result = self._execute_command(
                cmd, capture_output=True, text=True, timeout=30
            )

            duration_ms = int((time.time() - start_time) * 1000)

            # Bandit returns 0 for no issues, 1 for issues found
            if result.returncode == 0:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    duration_ms=duration_ms,
                )

            # Parse JSON output
            messages = []
            errors = []
            warnings = []
            if result.stdout:
                try:
                    import json

                    data = json.loads(result.stdout)
                    results = data.get("results", [])
                    for issue in results:
                        msg = f"Line {issue.get('line_number', '?')}: {issue.get('test_name', 'Unknown')} - {issue.get('issue_text', 'Security issue')}"
                        messages.append(msg)

                        severity = issue.get("issue_severity", "MEDIUM")
                        if severity in ["HIGH", "CRITICAL"]:
                            errors.append(msg)
                        else:
                            warnings.append(msg)

                except json.JSONDecodeError:
                    errors = [result.stdout.strip()]
                    messages = [result.stdout.strip()]

            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                messages=messages,
                errors=errors,
                warnings=warnings,
                duration_ms=duration_ms,
            )

        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )


# JavaScript/TypeScript Validators


class ESLintValidator(Validator):
    """JavaScript/TypeScript linter"""

    @property
    def name(self) -> str:
        return "js-eslint"

    @property
    def extensions(self) -> Set[str]:
        return {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()
        cmd = [self.command, str(filepath), "--format=json"]

        if self.auto_fix:
            cmd.insert(1, "--fix")

        try:
            result = self._execute_command(
                cmd, capture_output=True, text=True, timeout=30
            )
            duration_ms = int((time.time() - start_time) * 1000)

            try:
                data = json.loads(result.stdout) if result.stdout else []
                file_result = data[0] if data else {}

                errors = [
                    msg
                    for msg in file_result.get("messages", [])
                    if msg.get("severity") == 2
                ]
                warnings = [
                    msg
                    for msg in file_result.get("messages", [])
                    if msg.get("severity") == 1
                ]

                if not errors:
                    return ValidationResult(
                        tool=self.name,
                        filepath=str(filepath),
                        success=True,
                        warnings=[w.get("message", "") for w in warnings],
                        fixed=self.auto_fix,
                        duration_ms=duration_ms,
                    )
                else:
                    return ValidationResult(
                        tool=self.name,
                        filepath=str(filepath),
                        success=False,
                        errors=[e.get("message", "") for e in errors],
                        warnings=[w.get("message", "") for w in warnings],
                        duration_ms=duration_ms,
                    )
            except json.JSONDecodeError:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=result.returncode == 0,
                    messages=result.stdout.splitlines() if result.stdout else [],
                    duration_ms=duration_ms,
                )
        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )


class PrettierValidator(Validator):
    """JavaScript/TypeScript code formatter"""

    @property
    def name(self) -> str:
        return "js-prettier"

    @property
    def extensions(self) -> Set[str]:
        return {".js", ".jsx", ".ts", ".tsx", ".json", ".css", ".scss", ".html", ".md"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()

        # Use --write for auto-fix, --check for validation only
        if self.auto_fix:
            cmd = [self.command, "--write", str(filepath)]
        else:
            cmd = [self.command, "--check", str(filepath)]

        try:
            result = self._execute_command(
                cmd, capture_output=True, text=True, timeout=30
            )

            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    fixed=self.auto_fix,
                    duration_ms=duration_ms,
                )

            # Prettier returns non-zero if files need formatting
            messages = []
            errors = []
            if result.stdout:
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if line.strip():
                        msg = f"Code formatting: {line}"
                        messages.append(msg)
                        errors.append(msg)

            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                messages=messages,
                errors=errors,
                duration_ms=duration_ms,
            )

        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )


# Chapel Validator


class ChapelValidator(Validator):
    """Chapel code formatter (custom implementation, no compiler required)"""

    @property
    def name(self) -> str:
        return "chapel"

    @property
    def extensions(self) -> Set[str]:
        return {".chpl"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()

        try:
            # Import Chapel formatter
            from huskycat.formatters.chapel import ChapelFormatter

            # Read file
            with open(filepath, "r", encoding="utf-8") as f:
                original_code = f.read()

            # Format code
            formatter = ChapelFormatter()
            formatted_code = formatter.format(original_code)

            duration_ms = int((time.time() - start_time) * 1000)

            # Check if formatting changed anything
            if formatted_code == original_code:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    duration_ms=duration_ms,
                )

            # If auto-fix enabled, write the formatted code
            if self.auto_fix:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(formatted_code)

                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    fixed=True,
                    messages=["Chapel code formatted"],
                    duration_ms=duration_ms,
                )
            else:
                # Report formatting issues without fixing
                issues = formatter.check_formatting(original_code)
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=False,
                    errors=issues,
                    messages=[f"Chapel formatting issues found: {len(issues)}"],
                    duration_ms=duration_ms,
                )

        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[f"Chapel validation error: {str(e)}"],
                duration_ms=int((time.time() - start_time) * 1000),
            )


# Ansible Validator


class AnsibleLintValidator(Validator):
    """Ansible playbook and role linter with auto-fix support"""

    @property
    def name(self) -> str:
        return "ansible-lint"

    @property
    def extensions(self) -> Set[str]:
        # Return empty set - use can_handle() method to detect Ansible files
        return set()

    def can_handle(self, filepath: Path) -> bool:
        """Check if file is an Ansible file (playbook, role, task, etc.)"""
        # Only handle files in ansible-specific directories or with ansible patterns
        path_str = str(filepath).lower()
        ansible_indicators = [
            "/playbooks/",
            "/roles/",
            "/tasks/",
            "/handlers/",
            "/vars/",
            "/defaults/",
            "/meta/",
            "playbook",
            "site.yml",
            "site.yaml",
        ]
        return any(indicator in path_str for indicator in ansible_indicators)

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()

        # ansible-lint command
        check_cmd = [
            self.command,
            "--nocolor",
            "--parseable",
            str(filepath),
        ]

        try:
            result = self._execute_command(
                check_cmd, capture_output=True, text=True, timeout=60
            )
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                # No issues found
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["Ansible playbook/role passed all checks"],
                    duration_ms=duration_ms,
                )
            else:
                # Parse ansible-lint output (ansible-lint writes to stderr)
                issues = []
                output = result.stderr if result.stderr else result.stdout
                if output:
                    # Filter to only the actual lint violations (lines with file:line:col format)
                    issues = [
                        line.strip()
                        for line in output.splitlines()
                        if line.strip()
                        and not line.startswith("WARNING")
                        and not line.startswith("#")
                        and not line.startswith("Read")
                        and not line.startswith("Failed:")
                        and ":" in line
                    ]

                if self.auto_fix:
                    # Try to fix issues
                    fix_cmd = [
                        self.command,
                        "--fix",
                        "--nocolor",
                        str(filepath),
                    ]
                    fix_result = self._execute_command(
                        fix_cmd, capture_output=True, text=True, timeout=60
                    )

                    if fix_result.returncode == 0:
                        return ValidationResult(
                            tool=self.name,
                            filepath=str(filepath),
                            success=True,
                            messages=["Fixed Ansible lint issues"],
                            fixed=True,
                            duration_ms=duration_ms,
                        )
                    else:
                        # Some issues couldn't be fixed
                        remaining_issues = []
                        fix_output = (
                            fix_result.stderr
                            if fix_result.stderr
                            else fix_result.stdout
                        )
                        if fix_output:
                            # Filter to only the actual lint violations
                            remaining_issues = [
                                line.strip()
                                for line in fix_output.splitlines()
                                if line.strip()
                                and not line.startswith("WARNING")
                                and not line.startswith("#")
                                and not line.startswith("Read")
                                and not line.startswith("Failed:")
                                and ":" in line
                            ]

                        return ValidationResult(
                            tool=self.name,
                            filepath=str(filepath),
                            success=False,
                            errors=remaining_issues or issues,
                            messages=["Some issues could not be auto-fixed"],
                            fixed=len(remaining_issues) < len(issues),
                            duration_ms=duration_ms,
                        )
                else:
                    # Just report issues
                    return ValidationResult(
                        tool=self.name,
                        filepath=str(filepath),
                        success=False,
                        errors=issues[:20],  # Limit to first 20 issues
                        messages=[
                            f"Found {len(issues)} Ansible lint issues. Run with --fix to auto-fix."
                        ],
                        duration_ms=duration_ms,
                    )

        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )


# YAML Validator


class YamlLintValidator(Validator):
    """YAML linter with auto-fix for trailing spaces and newlines"""

    @property
    def name(self) -> str:
        return "yamllint"

    @property
    def extensions(self) -> Set[str]:
        return {".yaml", ".yml"}

    def _auto_fix_yaml(self, filepath: Path) -> bool:
        """Auto-fix common YAML issues like trailing spaces and missing newlines"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Fix trailing spaces
            lines = content.splitlines()
            lines = [line.rstrip() for line in lines]

            # Ensure file ends with newline
            content = "\n".join(lines)
            if content and not content.endswith("\n"):
                content += "\n"

            # Write back if changed
            if content != original_content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                return True

            return False
        except Exception as e:
            logger.warning(f"Failed to auto-fix {filepath}: {e}")
            return False

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()

        # If auto-fix is enabled, try to fix common issues first
        fixed = False
        if self.auto_fix:
            fixed = self._auto_fix_yaml(filepath)

        cmd = [self.command, "-f", "parsable", str(filepath)]

        try:
            result = self._execute_command(
                cmd, capture_output=True, text=True, timeout=30
            )
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["YAML is valid"],
                    fixed=fixed,
                    duration_ms=duration_ms,
                )
            else:
                errors = []
                warnings = []

                for line in result.stdout.splitlines():
                    if "[error]" in line:
                        errors.append(line)
                    elif "[warning]" in line:
                        warnings.append(line)

                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=False,
                    errors=errors,
                    warnings=warnings,
                    duration_ms=duration_ms,
                )
        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )


# Container Validator


class HadolintValidator(Validator):
    """Dockerfile/ContainerFile linter"""

    @property
    def name(self) -> str:
        return "docker-hadolint"

    @property
    def extensions(self) -> Set[str]:
        # Handle both extensions and specific filenames
        return {".dockerfile"}

    def can_handle(self, filepath: Path) -> bool:
        """Check if this validator can handle the given file"""
        return filepath.suffix in self.extensions or filepath.name in [
            "Dockerfile",
            "ContainerFile",
        ]

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()
        cmd = [self.command, str(filepath)]

        try:
            result = self._execute_command(
                cmd, capture_output=True, text=True, timeout=30
            )
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["Container file is valid"],
                    duration_ms=duration_ms,
                )
            else:
                errors = []
                warnings = []

                for line in result.stdout.splitlines():
                    if "DL" in line:  # Hadolint error codes
                        if "error" in line.lower():
                            errors.append(line)
                        else:
                            warnings.append(line)

                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=False,
                    errors=errors,
                    warnings=warnings,
                    duration_ms=duration_ms,
                )
        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )


# Shell Script Validator


class ShellcheckValidator(Validator):
    """Shell script linter"""

    @property
    def name(self) -> str:
        return "shellcheck"

    @property
    def extensions(self) -> Set[str]:
        return {".sh", ".bash", ".zsh", ".ksh"}

    def validate(self, filepath: Path) -> ValidationResult:
        start_time = time.time()
        cmd = [self.command, "-f", "json", str(filepath)]

        try:
            result = self._execute_command(
                cmd, capture_output=True, text=True, timeout=30
            )
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["Shell script is valid"],
                    duration_ms=duration_ms,
                )
            else:
                errors = []
                warnings = []

                try:
                    issues = json.loads(result.stdout) if result.stdout else []
                    for issue in issues:
                        msg = f"Line {issue.get('line')}: {issue.get('message')}"
                        if issue.get("level") == "error":
                            errors.append(msg)
                        else:
                            warnings.append(msg)
                except json.JSONDecodeError:
                    errors = result.stdout.splitlines() if result.stdout else []

                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=False,
                    errors=errors,
                    warnings=warnings,
                    duration_ms=duration_ms,
                )
        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )


class GitLabCIValidator(Validator):
    """Validator for GitLab CI YAML files using official schema"""

    @property
    def name(self) -> str:
        return "gitlab-ci"

    @property
    def extensions(self) -> Set[str]:
        return set()  # Use can_handle method instead of extension-based matching

    def is_available(self) -> bool:
        """Check if GitLab CI validator is available"""
        try:
            pass

            return True
        except ImportError:
            return False

    def can_handle(self, filepath: Path) -> bool:
        """Check if this file is a GitLab CI file"""
        name = filepath.name
        parent_path = str(filepath.parent)

        # Specific GitLab CI files
        if name == ".gitlab-ci.yml" or name.startswith(".gitlab-ci"):
            return True

        # Files in .gitlab/ci/ directory that are YAML files
        if (".gitlab/ci" in parent_path or parent_path.endswith(".gitlab/ci")) and (
            name.endswith(".yml") or name.endswith(".yaml")
        ):
            return True

        return False

    def validate(self, filepath: Path) -> ValidationResult:
        """Validate GitLab CI YAML file against official schema"""
        start_time = time.time()

        # Try to import the GitLab CI validator
        GitLabCISchemaValidator = None

        # Multiple import strategies
        import sys
        import os

        # Try path-based import first since it works when called directly
        current_dir = os.path.dirname(__file__)
        try:
            sys.path.insert(0, current_dir)
            import gitlab_ci_validator  # type: ignore

            GitLabCISchemaValidator = gitlab_ci_validator.GitLabCISchemaValidator
            sys.path.pop(0)
        except Exception:
            # Try other import strategies
            for import_strategy in [
                lambda: __import__(
                    "huskycat.gitlab_ci_validator", fromlist=["GitLabCISchemaValidator"]
                ).GitLabCISchemaValidator,
                lambda: __import__(
                    "src.huskycat.gitlab_ci_validator",
                    fromlist=["GitLabCISchemaValidator"],
                ).GitLabCISchemaValidator,
                lambda: getattr(
                    __import__("gitlab_ci_validator"), "GitLabCISchemaValidator"
                ),
            ]:
                try:
                    GitLabCISchemaValidator = import_strategy()
                    break
                except (ImportError, ModuleNotFoundError, AttributeError):
                    continue

        if GitLabCISchemaValidator is None:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[
                    "GitLab CI validator not installed. Install with: pip install jsonschema pyyaml requests"
                ],
                duration_ms=int((time.time() - start_time) * 1000),
            )

        try:
            validator = GitLabCISchemaValidator()

            # Validate the file
            is_valid, errors, warnings = validator.validate_file(str(filepath))

            duration_ms = int((time.time() - start_time) * 1000)

            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=is_valid,
                errors=errors,
                warnings=warnings,
                duration_ms=duration_ms,
            )

        except Exception:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[
                    "GitLab CI validator not installed. Install with: pip install jsonschema pyyaml requests"
                ],
                duration_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[f"Validation error: {str(e)}"],
                duration_ms=int((time.time() - start_time) * 1000),
            )


class ValidationEngine:
    """Main validation engine that orchestrates all validators"""

    def __init__(
        self,
        auto_fix: bool = False,
        interactive: bool = False,
        allow_warnings: bool = False,
        use_container: bool = False,
        adapter: Optional[Any] = None,
        linting_mode: Optional[LintingMode] = None,
    ):
        self.auto_fix = auto_fix
        self.interactive = interactive
        self.allow_warnings = allow_warnings
        self.use_container = use_container
        self.adapter = adapter
        self.linting_mode = linting_mode or get_mode_from_env()
        logger.info(f"ValidationEngine initialized with linting_mode={self.linting_mode.value}")
        self.validators = self._initialize_validators()
        self._extension_map = self._build_extension_map()

    def _load_dockerlint_validator(self):
        """Dynamically load DockerLintValidator if available"""
        try:
            from huskycat.linters.dockerlint_validator import DockerLintValidator  # type: ignore
            return DockerLintValidator
        except ImportError:
            logger.debug("DockerLintValidator not available")
            return None

    def _should_tool_auto_fix(self, tool_name: str) -> bool:
        """
        Check if a specific tool should auto-fix based on adapter rules.

        Uses adapter's should_auto_fix_tool() if available, otherwise
        falls back to global auto_fix setting.

        Args:
            tool_name: Name of the validation tool

        Returns:
            True if tool should auto-fix
        """
        if self.adapter is not None and hasattr(self.adapter, "should_auto_fix_tool"):
            return self.adapter.should_auto_fix_tool(tool_name, self.auto_fix)
        return self.auto_fix

    def _should_use_tool(self, tool_name: str) -> bool:
        """
        Check if tool should be used based on linting mode and license.

        In FAST mode, only bundled Apache/MIT tools are used.
        In COMPREHENSIVE mode, all tools including GPL are used.

        Args:
            tool_name: Name of the validation tool

        Returns:
            True if tool should be used in current linting mode
        """
        if self.linting_mode == LintingMode.COMPREHENSIVE:
            return True  # Use all tools in comprehensive mode

        # In FAST mode, only use bundled (non-GPL) tools
        try:
            return is_tool_bundled(tool_name)
        except KeyError:
            # Tool not in registry - allow it (backward compatibility)
            logger.warning(f"Tool {tool_name} not in tool registry, allowing by default")
            return True

    def _initialize_validators(self) -> List[Validator]:
        """Initialize all available validators with per-tool auto-fix decisions."""
        # Create validators with per-tool auto-fix based on adapter rules
        validators = [
            BlackValidator(self._should_tool_auto_fix("python-black")),
            AutoflakeValidator(self._should_tool_auto_fix("autoflake")),
            Flake8Validator(False),  # No auto-fix support
            MypyValidator(False),  # No auto-fix support
            RuffValidator(self._should_tool_auto_fix("ruff")),
            IsortValidator(self._should_tool_auto_fix("isort")),
            TaploValidator(self._should_tool_auto_fix("taplo")),
            TerraformValidator(self._should_tool_auto_fix("terraform")),
            BanditValidator(False),  # No auto-fix support
            ESLintValidator(self._should_tool_auto_fix("js-eslint")),
            PrettierValidator(self._should_tool_auto_fix("js-prettier")),
            ChapelValidator(self._should_tool_auto_fix("chapel")),
            AnsibleLintValidator(self._should_tool_auto_fix("ansible-lint")),
            YamlLintValidator(self._should_tool_auto_fix("yamllint")),
            HadolintValidator(False),  # No auto-fix support (GPL licensed, being replaced)
            ShellcheckValidator(False),  # No auto-fix support
            GitLabCIValidator(False),  # No auto-fix support
        ]

        # Dynamically add DockerLintValidator if available
        DockerLintValidatorClass = self._load_dockerlint_validator()
        if DockerLintValidatorClass is not None:
            validators.append(DockerLintValidatorClass(False))  # No auto-fix support

        # Filter to only available validators, respecting linting mode
        available = []
        for v in validators:
            # Check if tool should be used based on linting mode
            if not self._should_use_tool(v.name):
                logger.info(f"Skipping {v.name} in {self.linting_mode.value} mode (GPL or not bundled)")
                continue

            if v.is_available():
                available.append(v)
                logger.info(f"Validator {v.name} is available (auto_fix={v.auto_fix}, mode={self.linting_mode.value})")
            else:
                logger.warning(f"Validator {v.name} is not available")

        return available

    def _build_extension_map(self) -> Dict[str, List[Validator]]:
        """Build a map of file extensions to validators"""
        ext_map: Dict[str, List[Validator]] = {}
        for validator in self.validators:
            for ext in validator.extensions:
                if ext not in ext_map:
                    ext_map[ext] = []
                ext_map[ext].append(validator)
        return ext_map

    def get_validators_for_file(self, filepath: Path) -> List[Validator]:
        """Get applicable validators for a file (for testing compatibility)"""
        validators = self._extension_map.get(filepath.suffix, [])

        # Also check validators with custom can_handle logic
        for v in self.validators:
            if v.can_handle(filepath) and v not in validators:
                validators.append(v)

        return validators

    def validate_file(
        self,
        filepath: Path,
        fix: Optional[bool] = None,
        tools: Optional[List[str]] = None,
    ) -> List[ValidationResult]:
        """Validate a single file with all applicable validators"""
        results: List[ValidationResult] = []

        # Find applicable validators
        if tools:
            # Filter validators by specified tool names
            validators = []
            for tool_name in tools:
                found_validator = None
                for v in self.validators:
                    if v.name == tool_name and v.can_handle(filepath):
                        found_validator = v
                        break

                if found_validator:
                    validators.append(found_validator)
                else:
                    # Create error result for unknown tool
                    result = ValidationResult(
                        tool=tool_name,
                        filepath=str(filepath),
                        success=False,
                        messages=[f"Unknown tool: {tool_name}"],
                        errors=[f"Unknown tool: {tool_name}"],
                    )
                    results.append(result)
        else:
            # Use all applicable validators
            validators = self._extension_map.get(filepath.suffix, [])

            # Also check validators with custom can_handle logic
            for v in self.validators:
                if v.can_handle(filepath) and v not in validators:
                    validators.append(v)

        if not validators and not tools:
            logger.warning(f"No validators found for {filepath}")
            return results

        # Run each validator
        for validator in validators:
            logger.info(f"Running {validator.name} on {filepath}")
            result = validator.validate(filepath)
            results.append(result)

        return results

    def validate_directory(
        self,
        directory: Path,
        recursive: bool = True,
        exclude_patterns: Optional[List[str]] = None,
    ) -> Dict[str, List[ValidationResult]]:
        """Validate all files in a directory"""
        results = {}

        pattern = "**/*" if recursive else "*"
        exclude_patterns = exclude_patterns or []

        for filepath in directory.glob(pattern):
            if filepath.is_file() and not filepath.name.startswith("."):
                # Check if file should be excluded
                should_exclude = False
                for exclude_pattern in exclude_patterns:
                    if exclude_pattern in str(filepath):
                        should_exclude = True
                        break

                if not should_exclude:
                    file_results = self.validate_file(filepath)
                    if file_results:
                        results[str(filepath)] = file_results

        return results

    def validate_staged_files(self) -> Dict[str, List[ValidationResult]]:
        """Validate files staged for git commit with interactive auto-fix prompt"""
        try:
            # Get staged files
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                logger.error("Failed to get staged files")
                return {}

            # First pass - validate without auto-fix
            results = {}
            for filename in result.stdout.splitlines():
                filepath = Path(filename)
                if filepath.exists():
                    file_results = self.validate_file(filepath)
                    if file_results:
                        results[filename] = file_results

            # Check if we have fixable issues and prompt for auto-fix
            if self.interactive and not self.auto_fix:
                fixable_issues = self._count_fixable_issues(results)
                if fixable_issues > 0:
                    print(f"\nFound {fixable_issues} auto-fixable issues.")
                    response = input("Attempt auto-fix? [y/N]: ").strip().lower()
                    if response in ["y", "yes"]:
                        print("Applying auto-fixes...")
                        # Re-run with auto-fix enabled, preserving linting mode
                        auto_fix_engine = ValidationEngine(
                            auto_fix=True,
                            linting_mode=self.linting_mode
                        )
                        results = {}
                        for filename in result.stdout.splitlines():
                            filepath = Path(filename)
                            if filepath.exists():
                                file_results = auto_fix_engine.validate_file(filepath)
                                if file_results:
                                    results[filename] = file_results

            return results

        except Exception as e:
            logger.error(f"Error validating staged files: {e}")
            return {}

    def _count_fixable_issues(self, results: Dict[str, List[ValidationResult]]) -> int:
        """Count how many issues could potentially be auto-fixed"""
        fixable_tools = {
            "black",
            "autoflake",
            "ruff",
            "isort",
            "taplo",
            "terraform",
            "yamllint",
            "eslint",
            "js-prettier",
            "chapel",
        }
        count = 0

        for filepath, file_results in results.items():
            for result in file_results:
                if not result.success and result.tool in fixable_tools:
                    count += result.error_count

        return count

    def get_summary(self, results: Dict[str, List[ValidationResult]]) -> Dict[str, Any]:
        """Generate a summary of validation results"""
        total_files = len(results)
        total_errors = 0
        total_warnings = 0
        failed_files = []
        fixed_files = []

        for filepath, file_results in results.items():
            has_error = False
            has_fixes = False
            for result in file_results:
                total_errors += result.error_count
                total_warnings += result.warning_count
                if not result.success:
                    has_error = True
                if result.fixed:
                    has_fixes = True

            if has_error:
                failed_files.append(filepath)
            if has_fixes:
                fixed_files.append(filepath)

        return {
            "total_files": total_files,
            "passed_files": total_files - len(failed_files),
            "failed_files": len(failed_files),
            "fixed_files": len(fixed_files),
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "failed_file_list": failed_files,
            "fixed_file_list": fixed_files,
            "success": len(failed_files) == 0,
        }


# CLI Interface
def main() -> None:
    """Main entry point for CLI usage"""
    import argparse

    parser = argparse.ArgumentParser(description="HuskyCat Unified Validation Engine")
    parser.add_argument(
        "path", nargs="?", default=".", help="File or directory to validate"
    )
    parser.add_argument(
        "--fix", action="store_true", help="Auto-fix issues where possible"
    )
    parser.add_argument(
        "--staged", action="store_true", help="Validate only staged files"
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument(
        "--container", action="store_true", help="Run validation in container"
    )
    parser.add_argument(
        "--linting-mode",
        choices=["fast", "comprehensive"],
        help="Linting mode: fast (bundled tools only) or comprehensive (all tools including GPL)",
    )

    args = parser.parse_args()

    # Initialize engine with interactive mode for git hooks
    interactive_mode = (
        not args.fix and args.staged
    )  # Interactive only for staged files when --fix not specified

    # Note: --container flag is now ignored as container is the only execution mode
    if args.container:
        print("Note: --container flag is now default behavior (container-only mode)")

    # Parse linting mode from args or environment
    linting_mode = None
    if args.linting_mode:
        linting_mode = LintingMode.FAST if args.linting_mode == "fast" else LintingMode.COMPREHENSIVE

    engine = ValidationEngine(
        auto_fix=args.fix,
        interactive=interactive_mode,
        linting_mode=linting_mode
    )

    # Run validation
    if args.staged:
        results = engine.validate_staged_files()
    else:
        path = Path(args.path)
        if path.is_file():
            file_results = engine.validate_file(path)
            results = {str(path): file_results} if file_results else {}
        else:
            results = engine.validate_directory(path)

    # Generate summary
    summary = engine.get_summary(results)

    # Output results
    if args.json:
        output = {
            "summary": summary,
            "results": {
                filepath: [r.to_dict() for r in file_results]
                for filepath, file_results in results.items()
            },
        }
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        print(f"\n{'='*60}")
        print("VALIDATION SUMMARY")
        print(f"{'='*60}")
        print(f"Files Scanned: {summary['total_files']}")
        print(f"Files Passed:  {summary['passed_files']}")
        print(f"Files Failed:  {summary['failed_files']}")
        if summary.get("fixed_files", 0) > 0:
            print(f"Files Fixed:   {summary['fixed_files']}")
        print(f"Total Errors:  {summary['total_errors']}")
        print(f"Total Warnings: {summary['total_warnings']}")

        if summary["failed_file_list"]:
            print(f"\n{'='*60}")
            print("FAILED FILES:")
            print(f"{'='*60}")
            for filepath in summary["failed_file_list"]:
                print(f"  - {filepath}")
                for result in results[filepath]:
                    if not result.success:
                        print(
                            f"    [{result.tool}] {result.error_count} errors, {result.warning_count} warnings"
                        )

        print(f"\n{'='*60}")
        if summary["success"]:
            print("✅ ALL VALIDATIONS PASSED")
        else:
            print("❌ VALIDATION FAILED")
        print(f"{'='*60}\n")

    # Exit with appropriate code
    sys.exit(0 if summary["success"] else 1)


if __name__ == "__main__":
    main()
