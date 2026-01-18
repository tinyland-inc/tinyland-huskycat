"""
Async Task Manager for HuskyCat MCP Server

Provides async validation support with task tracking and polling capability.
Long-running validations (mypy: 10-30s, CI schema: 5-15s) can be started
asynchronously and polled for results.

Usage:
    task_manager = TaskManager()
    task_id = task_manager.create_task()

    # In background thread:
    task_manager.update_progress(task_id, 25, 100, "Running mypy...")
    task_manager.complete_task(task_id, {"success": True, "results": [...]})

    # Polling:
    task = task_manager.get_task(task_id)
    if task.status == TaskStatus.COMPLETED:
        return task.result
"""

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class TaskStatus(Enum):
    """Status of an async task"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AsyncTask:
    """Represents an async validation task"""

    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    total: int = 100
    message: str = ""
    started: Optional[str] = None
    completed: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    # Additional metadata
    tool_name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for JSON serialization"""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "progress": self.progress,
            "total": self.total,
            "message": self.message,
            "started": self.started,
            "completed": self.completed,
            "result": self.result,
            "error": self.error,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
        }

    @property
    def is_complete(self) -> bool:
        """Check if task has finished (completed or failed)"""
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)

    @property
    def progress_percent(self) -> float:
        """Get progress as percentage"""
        if self.total == 0:
            return 0.0
        return (self.progress / self.total) * 100


class TaskManager:
    """
    Thread-safe task manager for async validation operations.

    Manages async tasks with:
    - Task creation and tracking
    - Progress updates
    - Result storage
    - Task persistence to disk for completed/failed tasks
    """

    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        """
        Initialize task manager.

        Args:
            cache_dir: Directory for persisting completed tasks.
                       Defaults to .huskycat/tasks in current working directory.
        """
        self.tasks: Dict[str, AsyncTask] = {}
        self._lock = threading.RLock()
        self.cache_dir = cache_dir or Path.cwd() / ".huskycat" / "tasks"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Load any persisted tasks from disk
        self._load_persisted_tasks()

    def _load_persisted_tasks(self) -> None:
        """Load completed/failed tasks from disk cache"""
        try:
            for task_file in self.cache_dir.glob("*.json"):
                try:
                    task_data = json.loads(task_file.read_text())
                    task = AsyncTask(
                        task_id=task_data["task_id"],
                        status=TaskStatus(task_data["status"]),
                        progress=task_data.get("progress", 100),
                        total=task_data.get("total", 100),
                        message=task_data.get("message", ""),
                        started=task_data.get("started"),
                        completed=task_data.get("completed"),
                        result=task_data.get("result"),
                        error=task_data.get("error"),
                        tool_name=task_data.get("tool_name"),
                        arguments=task_data.get("arguments"),
                    )
                    self.tasks[task.task_id] = task
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    # Skip invalid task files
                    continue
        except Exception:
            # Silently handle any errors during load
            pass

    def create_task(
        self,
        tool_name: Optional[str] = None,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new task and return its ID.

        Args:
            tool_name: Name of the validation tool being run
            arguments: Arguments passed to the tool

        Returns:
            task_id: Unique 8-character task identifier
        """
        task_id = str(uuid.uuid4())[:8]
        task = AsyncTask(
            task_id=task_id,
            started=datetime.now().isoformat(),
            tool_name=tool_name,
            arguments=arguments,
        )

        with self._lock:
            self.tasks[task_id] = task

        return task_id

    def update_progress(
        self,
        task_id: str,
        progress: int,
        total: int,
        message: str,
    ) -> bool:
        """
        Update task progress.

        Args:
            task_id: Task identifier
            progress: Current progress value
            total: Total progress value (for percentage calculation)
            message: Human-readable progress message

        Returns:
            True if task was updated, False if task not found
        """
        with self._lock:
            if task_id not in self.tasks:
                return False

            task = self.tasks[task_id]
            task.progress = progress
            task.total = total
            task.message = message
            task.status = TaskStatus.RUNNING

        return True

    def complete_task(self, task_id: str, result: Dict[str, Any]) -> bool:
        """
        Mark task as completed with result.

        Args:
            task_id: Task identifier
            result: Validation result dictionary

        Returns:
            True if task was completed, False if task not found
        """
        with self._lock:
            if task_id not in self.tasks:
                return False

            task = self.tasks[task_id]
            task.status = TaskStatus.COMPLETED
            task.completed = datetime.now().isoformat()
            task.result = result
            task.progress = task.total
            task.message = "Validation completed"

            self._persist_task(task)

        return True

    def fail_task(self, task_id: str, error: str) -> bool:
        """
        Mark task as failed with error message.

        Args:
            task_id: Task identifier
            error: Error message describing the failure

        Returns:
            True if task was updated, False if task not found
        """
        with self._lock:
            if task_id not in self.tasks:
                return False

            task = self.tasks[task_id]
            task.status = TaskStatus.FAILED
            task.completed = datetime.now().isoformat()
            task.error = error
            task.message = f"Failed: {error}"

            self._persist_task(task)

        return True

    def cancel_task(self, task_id: str, reason: str = "Cancelled by user") -> bool:
        """
        Cancel a running task.

        Args:
            task_id: Task identifier
            reason: Reason for cancellation

        Returns:
            True if task was cancelled, False if task not found or already complete
        """
        with self._lock:
            if task_id not in self.tasks:
                return False

            task = self.tasks[task_id]
            if task.is_complete:
                return False

            task.status = TaskStatus.CANCELLED
            task.completed = datetime.now().isoformat()
            task.error = reason
            task.message = f"Cancelled: {reason}"

            self._persist_task(task)

        return True

    def get_task(self, task_id: str) -> Optional[AsyncTask]:
        """
        Get task by ID.

        Args:
            task_id: Task identifier

        Returns:
            AsyncTask if found, None otherwise
        """
        with self._lock:
            return self.tasks.get(task_id)

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 50,
    ) -> List[AsyncTask]:
        """
        List tasks, optionally filtered by status.

        Args:
            status: Filter by task status (None for all)
            limit: Maximum number of tasks to return

        Returns:
            List of tasks, most recent first
        """
        with self._lock:
            tasks = list(self.tasks.values())

        # Filter by status if specified
        if status is not None:
            tasks = [t for t in tasks if t.status == status]

        # Sort by started time, most recent first
        tasks.sort(key=lambda t: t.started or "", reverse=True)

        return tasks[:limit]

    def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """
        Remove completed/failed tasks older than max_age_hours.

        Args:
            max_age_hours: Maximum age in hours for tasks to keep

        Returns:
            Number of tasks removed
        """
        cutoff = datetime.now()
        removed = 0

        with self._lock:
            to_remove = []
            for task_id, task in self.tasks.items():
                if task.is_complete and task.completed:
                    try:
                        completed_time = datetime.fromisoformat(task.completed)
                        age_hours = (cutoff - completed_time).total_seconds() / 3600
                        if age_hours > max_age_hours:
                            to_remove.append(task_id)
                    except ValueError:
                        continue

            for task_id in to_remove:
                del self.tasks[task_id]
                # Also remove persisted file
                task_file = self.cache_dir / f"{task_id}.json"
                if task_file.exists():
                    task_file.unlink()
                removed += 1

        return removed

    def _persist_task(self, task: AsyncTask) -> None:
        """
        Save completed/failed task to disk.

        Args:
            task: Task to persist
        """
        try:
            task_file = self.cache_dir / f"{task.task_id}.json"
            task_file.write_text(json.dumps(task.to_dict(), indent=2, default=str))
        except Exception:
            # Silently handle persistence errors
            pass


# Singleton instance for global access
_task_manager: Optional[TaskManager] = None
_task_manager_lock = threading.Lock()


def get_task_manager(cache_dir: Optional[Path] = None) -> TaskManager:
    """
    Get or create the global TaskManager instance.

    Args:
        cache_dir: Directory for task persistence (only used on first call)

    Returns:
        Global TaskManager instance
    """
    global _task_manager

    with _task_manager_lock:
        if _task_manager is None:
            _task_manager = TaskManager(cache_dir=cache_dir)
        return _task_manager
