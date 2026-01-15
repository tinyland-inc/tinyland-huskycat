"""
Pydantic configuration schema for .huskycat.yaml validation.

This module defines the validated configuration schema for HuskyCat,
ensuring type safety and validation of all configuration options.
"""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Validation bounds constants
MIN_ERRORS = 1
MAX_ERRORS = 10000
MIN_TIMEOUT = 1
MAX_TIMEOUT = 600


class OutputFormat(str, Enum):
    """Output format options for validation results."""

    MINIMAL = "minimal"
    HUMAN = "human"
    JSON = "json"
    JUNIT_XML = "junit_xml"
    JSONRPC = "jsonrpc"


class FeatureFlags(BaseModel):
    """Feature flags for controlling optional/experimental features."""

    model_config = ConfigDict(extra="ignore")

    nonblocking_hooks: bool = Field(
        default=False, description="Enable non-blocking git hooks"
    )
    parallel_execution: bool = Field(
        default=True, description="Enable parallel tool execution"
    )
    tui_progress: bool = Field(default=True, description="Enable TUI progress display")
    cache_results: bool = Field(default=True, description="Cache validation results")


class ValidationConfig(BaseModel):
    """Configuration for validation behavior."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = Field(default=True, description="Enable validation")
    staged_only: bool = Field(
        default=True, description="Only validate staged files in git hooks mode"
    )
    auto_fix: bool = Field(
        default=False, description="Automatically fix issues when possible"
    )
    strict: bool = Field(
        default=False, description="Enable strict mode (treat warnings as errors)"
    )
    max_errors: int = Field(
        default=100, ge=1, le=10000, description="Maximum number of errors to report"
    )

    @field_validator("max_errors")
    @classmethod
    def validate_max_errors(cls, v: int) -> int:
        """Ensure max_errors is within reasonable bounds."""
        if v < MIN_ERRORS:
            return MIN_ERRORS
        if v > MAX_ERRORS:
            return MAX_ERRORS
        return v


class ToolConfig(BaseModel):
    """Configuration for a specific tool or tool category."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = Field(default=True, description="Enable this tool/category")
    auto_fix: bool = Field(
        default=False, description="Enable auto-fix for this tool/category"
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=600,
        description="Timeout in seconds for tool execution",
    )
    tools: List[str] = Field(
        default_factory=list, description="List of tools to run in this category"
    )
    file_patterns: List[str] = Field(
        default_factory=list, description="File patterns to match for this tool"
    )
    exclude: List[str] = Field(
        default_factory=list, description="Patterns to exclude from validation"
    )

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Ensure timeout is within reasonable bounds."""
        if v < MIN_TIMEOUT:
            return MIN_TIMEOUT
        if v > MAX_TIMEOUT:
            return MAX_TIMEOUT
        return v


class HookConfig(BaseModel):
    """Configuration for a git hook."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = Field(default=True, description="Enable this hook")
    commands: List[str] = Field(
        default_factory=list, description="Commands to run for this hook"
    )


class CommitMsgHookConfig(HookConfig):
    """Configuration for the commit-msg hook."""

    conventional_commits: bool = Field(
        default=True, description="Enforce conventional commit format"
    )
    allowed_types: List[str] = Field(
        default_factory=lambda: [
            "feat",
            "fix",
            "docs",
            "style",
            "refactor",
            "perf",
            "test",
            "build",
            "ci",
            "chore",
            "revert",
        ],
        description="Allowed commit types for conventional commits",
    )


class HooksConfig(BaseModel):
    """Configuration for all git hooks."""

    model_config = ConfigDict(extra="ignore")

    pre_commit: HookConfig = Field(default_factory=HookConfig)
    commit_msg: CommitMsgHookConfig = Field(default_factory=CommitMsgHookConfig)
    pre_push: HookConfig = Field(default_factory=HookConfig)


class HuskyCatConfigSchema(BaseModel):
    """
    Validated configuration schema for .huskycat.yaml.

    This is the root configuration model that validates all HuskyCat
    configuration options. Unknown fields are rejected to catch typos.

    Example:
        ```yaml
        version: "1.0"
        validation:
          enabled: true
          staged_only: true
          auto_fix: false
        feature_flags:
          parallel_execution: true
          cache_results: true
        tools:
          python:
            enabled: true
            tools: ["black", "flake8", "mypy"]
            file_patterns: ["*.py"]
        hooks:
          pre_commit:
            enabled: true
            commands: ["huskycat validate --staged"]
        ```
    """

    model_config = ConfigDict(extra="forbid")

    version: str = Field(default="1.0", description="Configuration schema version")
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    feature_flags: FeatureFlags = Field(default_factory=FeatureFlags)
    tools: Dict[str, ToolConfig] = Field(
        default_factory=dict, description="Tool configurations by category"
    )
    hooks: HooksConfig = Field(default_factory=HooksConfig)
    ignore_patterns: List[str] = Field(
        default_factory=list, description="Global patterns to ignore"
    )

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate version string format."""
        valid_versions = ["1.0", "1.1", "2.0"]
        if v not in valid_versions:
            # Allow unknown versions but warn
            pass
        return v

    def get_tool_config(self, tool_name: str) -> Optional[ToolConfig]:
        """
        Get configuration for a specific tool category.

        Args:
            tool_name: Name of the tool category (e.g., "python", "javascript")

        Returns:
            ToolConfig if found, None otherwise
        """
        return self.tools.get(tool_name)

    def is_tool_enabled(self, tool_name: str) -> bool:
        """
        Check if a tool category is enabled.

        Args:
            tool_name: Name of the tool category

        Returns:
            True if enabled, False otherwise
        """
        tool_config = self.get_tool_config(tool_name)
        if tool_config is None:
            return False
        return tool_config.enabled

    def get_file_patterns(self, tool_name: str) -> List[str]:
        """
        Get file patterns for a tool category.

        Args:
            tool_name: Name of the tool category

        Returns:
            List of file patterns
        """
        tool_config = self.get_tool_config(tool_name)
        if tool_config is None:
            return []
        return tool_config.file_patterns

    def get_exclude_patterns(self, tool_name: str) -> List[str]:
        """
        Get exclude patterns for a tool category.

        Args:
            tool_name: Name of the tool category

        Returns:
            List of exclude patterns
        """
        tool_config = self.get_tool_config(tool_name)
        if tool_config is None:
            return []
        return tool_config.exclude

    def model_dump_yaml(self) -> str:
        """
        Export configuration as YAML string.

        Returns:
            YAML-formatted configuration string
        """
        return yaml.dump(self.model_dump(mode="json"), default_flow_style=False)

    @classmethod
    def from_yaml_file(cls, path: str) -> "HuskyCatConfigSchema":
        """
        Load and validate configuration from a YAML file.

        Args:
            path: Path to the YAML configuration file

        Returns:
            Validated HuskyCatConfigSchema instance

        Raises:
            ValidationError: If the configuration is invalid
            FileNotFoundError: If the file doesn't exist
        """
        config_path = Path(path)
        content = config_path.read_text()
        data = yaml.safe_load(content) or {}
        return cls(**data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HuskyCatConfigSchema":
        """
        Create and validate configuration from a dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            Validated HuskyCatConfigSchema instance

        Raises:
            ValidationError: If the configuration is invalid
        """
        return cls(**data)


# Type aliases for convenience
ConfigSchema = HuskyCatConfigSchema


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
