"""
Mode Adapters for HuskyCat.

Each adapter configures behavior for a specific product mode.
"""

from .base import ModeAdapter, OutputFormat
from .git_hooks import GitHooksAdapter
from .ci import CIAdapter
from .cli import CLIAdapter
from .pipeline import PipelineAdapter
from .mcp import MCPAdapter

__all__ = [
    "ModeAdapter",
    "OutputFormat",
    "GitHooksAdapter",
    "CIAdapter",
    "CLIAdapter",
    "PipelineAdapter",
    "MCPAdapter",
]
