# SPDX-License-Identifier: Apache-2.0
"""
Core module for HuskyCat validation platform.
"""

from .base import BaseCommand, CommandResult, CommandStatus
from .factory import HuskyCatFactory
from .mode_detector import ProductMode, detect_mode, get_adapter, get_mode_description
from .task_manager import AsyncTask, TaskManager, TaskStatus, get_task_manager
from .tool_selector import (
    LintingMode,
    ToolInfo,
    ToolLicense,
    detect_file_types,
    get_bundled_tools,
    get_gpl_tools,
    get_mode_from_env,
    get_tool_info,
    get_tools_for_file_type,
    get_tools_for_mode,
    is_tool_bundled,
)

__all__ = [
    "AsyncTask",
    "BaseCommand",
    "CommandResult",
    "CommandStatus",
    "HuskyCatFactory",
    "LintingMode",
    "ProductMode",
    "TaskManager",
    "TaskStatus",
    "ToolInfo",
    "ToolLicense",
    "detect_file_types",
    "detect_mode",
    "get_adapter",
    "get_bundled_tools",
    "get_gpl_tools",
    "get_mode_description",
    "get_mode_from_env",
    "get_task_manager",
    "get_tool_info",
    "get_tools_for_file_type",
    "get_tools_for_mode",
    "is_tool_bundled",
]
