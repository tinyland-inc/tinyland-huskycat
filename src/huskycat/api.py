# SPDX-License-Identifier: Apache-2.0
"""HuskyCat Canonical API - Single source of truth for all interfaces.

This module provides a unified API for all HuskyCat functionality that works
regardless of execution mode (CLI, MCP, Container, Git Hooks).

All methods return typed result dataclasses for consistency and type safety.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .core.process_manager import ProcessManager, ValidationRun
from .core.task_manager import TaskManager, TaskStatus, get_task_manager
from .unified_validation import ValidationEngine, ValidationResult as EngineResult


# =============================================================================
# Result Types
# =============================================================================


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    success: bool
    issues: List[Dict[str, Any]]
    files_checked: int
    tools_used: List[str]
    duration_ms: float
    errors: int = 0
    warnings: int = 0
    fixed: bool = False
    fixed_files: List[str] = field(default_factory=list)
    failed_files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "issues": self.issues,
            "files_checked": self.files_checked,
            "tools_used": self.tools_used,
            "duration_ms": self.duration_ms,
            "errors": self.errors,
            "warnings": self.warnings,
            "fixed": self.fixed,
            "fixed_files": self.fixed_files,
            "failed_files": self.failed_files,
        }


@dataclass
class FixResult:
    """Result of an auto-fix operation."""

    files_modified: List[str]
    issues_fixed: int
    issues_remaining: int
    success: bool
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "files_modified": self.files_modified,
            "issues_fixed": self.issues_fixed,
            "issues_remaining": self.issues_remaining,
            "success": self.success,
            "errors": self.errors,
        }


@dataclass
class StatusResult:
    """HuskyCat status information."""

    version: str
    mode: str
    tools_available: List[str]
    config_path: Optional[str]
    execution_mode: str
    container_available: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "version": self.version,
            "mode": self.mode,
            "tools_available": self.tools_available,
            "config_path": self.config_path,
            "execution_mode": self.execution_mode,
            "container_available": self.container_available,
        }


@dataclass
class HistoryResult:
    """Validation run history."""

    runs: List[Dict[str, Any]]
    count: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "runs": self.runs,
            "count": self.count,
        }


@dataclass
class TaskResult:
    """Async task information."""

    task_id: str
    status: str
    progress: int
    total: int
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "progress": self.progress,
            "total": self.total,
            "message": self.message,
            "result": self.result,
            "error": self.error,
        }


# =============================================================================
# Canonical API
# =============================================================================


class HuskyCat:
    """Canonical API for HuskyCat validation platform.

    This class provides a unified interface for all HuskyCat functionality
    that works regardless of how HuskyCat is being invoked (CLI, MCP, Container).

    All methods return typed result dataclasses for consistency.

    Example:
        >>> api = HuskyCat()
        >>> result = api.validate([Path("myfile.py")], fix=True)
        >>> if result.success:
        ...     print(f"Validation passed! {result.files_checked} files checked")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize HuskyCat API.

        Args:
            config: Optional configuration dictionary with keys:
                - auto_fix: Enable auto-fix by default
                - interactive: Enable interactive prompts
                - allow_warnings: Treat warnings as success
                - container_mode: Force container execution
        """
        self.config = config or {}
        self.engine = ValidationEngine(
            auto_fix=self.config.get("auto_fix", False),
            interactive=self.config.get("interactive", False),
            allow_warnings=self.config.get("allow_warnings", False),
            use_container=self.config.get("container_mode", False),
        )
        self.process_manager = ProcessManager()
        self.task_manager = get_task_manager()

    # =========================================================================
    # Core Validation
    # =========================================================================

    def validate(
        self,
        paths: List[Path],
        fix: bool = False,
        staged: bool = False,
        tools: Optional[List[str]] = None,
    ) -> ValidationResult:
        """Validate files or directories.

        Args:
            paths: List of file or directory paths to validate
            fix: Enable auto-fix where possible
            staged: Only validate git-staged files (ignores paths)
            tools: Optional list of specific tools to run (e.g., ["black", "ruff"])

        Returns:
            ValidationResult with detailed validation information
        """
        start_time = time.time()

        # Update engine settings
        self.engine.auto_fix = fix

        # Validate
        if staged:
            validation_results = self.engine.validate_staged_files()
        else:
            validation_results = {}
            for path in paths:
                if path.is_file():
                    file_results = self.engine.validate_file(path, fix=fix, tools=tools)
                    if file_results:
                        validation_results[str(path)] = file_results
                elif path.is_dir():
                    dir_results = self.engine.validate_directory(path)
                    validation_results.update(dir_results)

        # Generate summary
        summary = self.engine.get_summary(validation_results)
        duration_ms = (time.time() - start_time) * 1000

        # Collect issues
        issues = []
        tools_used = set()
        for filepath, file_results in validation_results.items():
            for result in file_results:
                tools_used.add(result.tool)
                if not result.success or result.warnings:
                    issues.append(
                        {
                            "filepath": filepath,
                            "tool": result.tool,
                            "success": result.success,
                            "errors": result.errors,
                            "warnings": result.warnings,
                            "fixed": result.fixed,
                        }
                    )

        return ValidationResult(
            success=summary["success"],
            issues=issues,
            files_checked=summary["total_files"],
            tools_used=sorted(tools_used),
            duration_ms=duration_ms,
            errors=summary["total_errors"],
            warnings=summary["total_warnings"],
            fixed=summary.get("fixed_files", 0) > 0,
            fixed_files=summary.get("fixed_file_list", []),
            failed_files=summary.get("failed_file_list", []),
        )

    def auto_fix(self, paths: List[Path]) -> FixResult:
        """Auto-fix issues in files.

        This is a convenience method that runs validate() with fix=True
        and returns a simplified result focused on what was fixed.

        Args:
            paths: List of file or directory paths to fix

        Returns:
            FixResult with information about fixes applied
        """
        # Run validation with auto-fix enabled
        result = self.validate(paths, fix=True)

        # Count issues fixed vs remaining
        issues_fixed = 0
        issues_remaining = 0
        errors = []

        for issue in result.issues:
            if issue.get("fixed"):
                issues_fixed += len(issue.get("errors", []))
            else:
                issues_remaining += len(issue.get("errors", []))
                if issue.get("errors"):
                    errors.extend(issue["errors"])

        return FixResult(
            files_modified=result.fixed_files,
            issues_fixed=issues_fixed,
            issues_remaining=issues_remaining,
            success=result.success,
            errors=errors,
        )

    # =========================================================================
    # Query Operations
    # =========================================================================

    def status(self) -> StatusResult:
        """Get HuskyCat status and configuration.

        Returns:
            StatusResult with system information
        """
        # Get available tools
        tools_available = [v.name for v in self.engine.validators]

        # Detect execution mode
        execution_mode = self.engine.validators[0]._get_execution_mode() if self.engine.validators else "unknown"

        # Check container availability
        container_available = False
        if self.engine.validators:
            container_available = self.engine.validators[0]._container_runtime_exists()

        return StatusResult(
            version="2.0.0",
            mode="api",
            tools_available=tools_available,
            config_path=str(self.config.get("config_path", "~/.huskycat")),
            execution_mode=execution_mode,
            container_available=container_available,
        )

    def history(self, limit: int = 10) -> HistoryResult:
        """Get validation run history.

        Args:
            limit: Maximum number of runs to return (1-100)

        Returns:
            HistoryResult with recent validation runs
        """
        limit = min(max(1, limit), 100)
        runs = self.process_manager.get_run_history(limit=limit)

        return HistoryResult(
            runs=[self._run_to_dict(r) for r in runs],
            count=len(runs),
        )

    def last_run(self) -> Optional[Dict[str, Any]]:
        """Get last validation run.

        Returns:
            Dictionary with run information, or None if no runs found
        """
        # Try to get the most recent run
        run = self.process_manager.check_previous_run()

        # If no failed run, check last_run file
        if run is None:
            last_run_file = self.process_manager.last_run_file
            if last_run_file.exists():
                try:
                    import json

                    data = json.loads(last_run_file.read_text())
                    run = ValidationRun(**data)
                except Exception:
                    pass

        # If still nothing, try history
        if run is None:
            history = self.process_manager.get_run_history(limit=1)
            if history:
                run = history[0]

        if run is None:
            return None

        return self._run_to_dict(run)

    # =========================================================================
    # Async Operations
    # =========================================================================

    def validate_async(
        self,
        paths: List[Path],
        fix: bool = False,
        tools: Optional[List[str]] = None,
    ) -> str:
        """Start async validation, return task ID.

        Use this for long-running validations that should not block.
        Poll with get_task() to check progress and retrieve results.

        Args:
            paths: List of file or directory paths to validate
            fix: Enable auto-fix where possible
            tools: Optional list of specific tools to run

        Returns:
            Task ID string (use with get_task)
        """
        import threading

        # Create task
        task_id = self.task_manager.create_task(
            tool_name="validate",
            arguments={
                "paths": [str(p) for p in paths],
                "fix": fix,
                "tools": tools,
            },
        )

        # Start validation in background thread
        def _run():
            try:
                self.task_manager.update_progress(task_id, 0, 100, "Starting validation...")
                result = self.validate(paths, fix=fix, tools=tools)
                self.task_manager.complete_task(task_id, result.to_dict())
            except Exception as e:
                self.task_manager.fail_task(task_id, str(e))

        thread = threading.Thread(target=_run, daemon=True, name=f"validate-{task_id}")
        thread.start()

        return task_id

    def get_task(self, task_id: str) -> Optional[TaskResult]:
        """Get task status and results.

        Args:
            task_id: Task ID from validate_async()

        Returns:
            TaskResult with status and results, or None if not found
        """
        task = self.task_manager.get_task(task_id)
        if task is None:
            return None

        return TaskResult(
            task_id=task.task_id,
            status=task.status.value,
            progress=task.progress,
            total=task.total,
            message=task.message,
            result=task.result,
            error=task.error,
        )

    def list_tasks(
        self, status: Optional[str] = None, limit: int = 20
    ) -> List[TaskResult]:
        """List all async tasks.

        Args:
            status: Optional status filter (pending, running, completed, failed, cancelled)
            limit: Maximum tasks to return (1-100)

        Returns:
            List of TaskResult objects
        """
        limit = min(max(1, limit), 100)

        # Convert status string to enum if provided
        status_enum = None
        if status:
            try:
                status_enum = TaskStatus(status)
            except ValueError:
                raise ValueError(
                    f"Invalid status: {status}. "
                    "Valid values: pending, running, completed, failed, cancelled"
                )

        tasks = self.task_manager.list_tasks(status=status_enum, limit=limit)

        return [
            TaskResult(
                task_id=t.task_id,
                status=t.status.value,
                progress=t.progress,
                total=t.total,
                message=t.message,
                result=t.result,
                error=t.error,
            )
            for t in tasks
        ]

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running async task.

        Args:
            task_id: Task ID to cancel

        Returns:
            True if cancelled successfully, False otherwise
        """
        return self.task_manager.cancel_task(task_id, reason="Cancelled via API")

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _run_to_dict(self, run: ValidationRun) -> Dict[str, Any]:
        """Convert ValidationRun to dictionary."""
        from dataclasses import asdict

        return asdict(run)


# =============================================================================
# Convenience Functions
# =============================================================================


def validate(
    paths: List[Path],
    fix: bool = False,
    staged: bool = False,
    tools: Optional[List[str]] = None,
) -> ValidationResult:
    """Convenience function for quick validation.

    Example:
        >>> from huskycat.api import validate
        >>> result = validate([Path("myfile.py")])
        >>> print(f"Success: {result.success}")
    """
    api = HuskyCat()
    return api.validate(paths, fix=fix, staged=staged, tools=tools)


def auto_fix(paths: List[Path]) -> FixResult:
    """Convenience function for quick auto-fix.

    Example:
        >>> from huskycat.api import auto_fix
        >>> result = auto_fix([Path("myfile.py")])
        >>> print(f"Fixed {result.issues_fixed} issues")
    """
    api = HuskyCat()
    return api.auto_fix(paths)


def get_status() -> StatusResult:
    """Convenience function to get HuskyCat status.

    Example:
        >>> from huskycat.api import get_status
        >>> status = get_status()
        >>> print(f"Available tools: {status.tools_available}")
    """
    api = HuskyCat()
    return api.status()
