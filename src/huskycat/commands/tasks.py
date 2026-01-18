# SPDX-License-Identifier: Apache-2.0
"""
Tasks command for managing async validation tasks.

Provides CLI access to async task management, matching MCP tool parity:
- list_async_tasks
- get_task_status
- cancel_async_task
"""

from typing import Optional

from ..core.base import BaseCommand, CommandResult, CommandStatus
from ..core.task_manager import TaskManager, TaskStatus as TaskState, get_task_manager


class TasksCommand(BaseCommand):
    """Command for managing async validation tasks."""

    name = "tasks"
    description = "Manage async validation tasks"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.task_manager = get_task_manager()

    def execute(
        self,
        status: Optional[str] = None,
        cancel: Optional[str] = None,
        limit: int = 20,
        **kwargs,
    ) -> CommandResult:
        """
        Execute tasks command.

        Args:
            status: Filter tasks by status (pending, running, completed, failed, cancelled)
            cancel: Task ID to cancel
            limit: Maximum number of tasks to show

        Returns:
            CommandResult with task data
        """
        # Cancel a specific task
        if cancel:
            return self._cancel_task(cancel)

        # List tasks (optionally filtered by status)
        return self._list_tasks(status, limit)

    def _list_tasks(self, status_filter: Optional[str], limit: int) -> CommandResult:
        """List async validation tasks."""
        limit = min(max(1, limit), 100)

        # Convert status string to enum if provided
        status_enum = None
        if status_filter:
            try:
                status_enum = TaskState(status_filter)
            except ValueError:
                return CommandResult(
                    status=CommandStatus.FAILED,
                    message=f"Invalid status filter: {status_filter}",
                    errors=[
                        f"Valid values: pending, running, completed, failed, cancelled"
                    ],
                )

        tasks = self.task_manager.list_tasks(status=status_enum, limit=limit)

        if not tasks:
            msg = "No async tasks found"
            if status_filter:
                msg += f" with status '{status_filter}'"
            return CommandResult(
                status=CommandStatus.SUCCESS,
                message=msg,
                output=msg,
                data={"count": 0, "tasks": []},
            )

        # Format output
        output_lines = [
            f"Async Tasks (showing {len(tasks)} of {limit} max):"
        ]
        if status_filter:
            output_lines[0] += f" [filter: {status_filter}]"

        output_lines.append("-" * 80)
        output_lines.append(
            f"{'Task ID':<20} {'Status':<12} {'Progress':<10} {'Tool':<15} {'Message':<20}"
        )
        output_lines.append("-" * 80)

        for task in tasks:
            progress = f"{task.progress_percent:.0f}%" if task.total > 0 else "N/A"
            message = task.message[:17] + "..." if len(task.message) > 20 else task.message
            output_lines.append(
                f"{task.task_id[:18]:<20} {task.status.value:<12} {progress:<10} "
                f"{task.tool_name:<15} {message:<20}"
            )

        output_lines.append("-" * 80)
        output_lines.append(f"Total: {len(tasks)} tasks")

        # Summary by status
        status_counts = {}
        for task in tasks:
            s = task.status.value
            status_counts[s] = status_counts.get(s, 0) + 1

        if status_counts:
            output_lines.append(
                "Status: " + ", ".join(f"{k}: {v}" for k, v in status_counts.items())
            )

        return CommandResult(
            status=CommandStatus.SUCCESS,
            message=f"Found {len(tasks)} async tasks",
            output="\n".join(output_lines),
            data={
                "count": len(tasks),
                "filter": status_filter,
                "limit": limit,
                "tasks": [task.to_dict() for task in tasks],
            },
        )

    def _cancel_task(self, task_id: str) -> CommandResult:
        """Cancel a specific async task."""
        task = self.task_manager.get_task(task_id)

        if task is None:
            return CommandResult(
                status=CommandStatus.FAILED,
                message=f"Task not found: {task_id}",
                output=f"No task found with ID: {task_id}",
                errors=[f"Task ID '{task_id}' not found"],
                data={"success": False, "task_id": task_id},
            )

        if task.is_complete:
            return CommandResult(
                status=CommandStatus.WARNING,
                message=f"Task already {task.status.value}",
                output=f"Task {task_id} is already {task.status.value}, cannot cancel",
                warnings=[f"Task is already {task.status.value}"],
                data={
                    "success": False,
                    "task_id": task_id,
                    "status": task.status.value,
                },
            )

        # Cancel the task
        cancelled = self.task_manager.cancel_task(task_id, reason="Cancelled via CLI")

        if cancelled:
            return CommandResult(
                status=CommandStatus.SUCCESS,
                message=f"Task {task_id} cancelled",
                output=f"Successfully cancelled task: {task_id}",
                data={
                    "success": True,
                    "task_id": task_id,
                    "status": "cancelled",
                },
            )
        else:
            return CommandResult(
                status=CommandStatus.FAILED,
                message=f"Failed to cancel task: {task_id}",
                output=f"Could not cancel task: {task_id}",
                errors=["Failed to cancel task - it may have completed"],
                data={
                    "success": False,
                    "task_id": task_id,
                },
            )
