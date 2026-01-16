# SPDX-License-Identifier: Apache-2.0
"""
Mode Adapters for HuskyCat.

Each adapter configures behavior for a specific product mode.
"""

from .base import (
    ModeAdapter,
    OutputFormat,
    FixConfidence,
    TOOL_FIX_CONFIDENCE,
    AdapterConfig,
)
from .git_hooks import GitHooksAdapter
from .git_hooks_nonblocking import NonBlockingGitHooksAdapter
from .ci import CIAdapter
from .cli import CLIAdapter
from .pipeline import PipelineAdapter
from .mcp import MCPAdapter

__all__ = [
    "ModeAdapter",
    "OutputFormat",
    "FixConfidence",
    "TOOL_FIX_CONFIDENCE",
    "AdapterConfig",
    "GitHooksAdapter",
    "NonBlockingGitHooksAdapter",
    "CIAdapter",
    "CLIAdapter",
    "PipelineAdapter",
    "MCPAdapter",
]
