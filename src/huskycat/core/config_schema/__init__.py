"""
Configuration schema package for HuskyCat.

This package provides Pydantic-validated configuration schemas
for .huskycat.yaml files.
"""

from .schema import (
    CommitMsgHookConfig,
    ConfigSchema,
    FeatureFlags,
    HookConfig,
    HooksConfig,
    HuskyCatConfigSchema,
    OutputFormat,
    ToolConfig,
    ValidationConfig,
)

__all__ = [
    "CommitMsgHookConfig",
    "ConfigSchema",
    "FeatureFlags",
    "HookConfig",
    "HooksConfig",
    "HuskyCatConfigSchema",
    "OutputFormat",
    "ToolConfig",
    "ValidationConfig",
]
