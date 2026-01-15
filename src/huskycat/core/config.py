"""
Configuration management for HuskyCat.

Handles loading configuration from multiple sources:
1. .huskycat.yaml in project root
2. Environment variables
3. Command-line flags

Feature flags control optional or experimental features.

Configuration is validated using Pydantic schemas to ensure
type safety and catch configuration errors early.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import ValidationError

from .config_schema.schema import HuskyCatConfigSchema

logger = logging.getLogger(__name__)


class HuskyCatConfig:
    """
    HuskyCat configuration with feature flags.

    Feature Flags:
        nonblocking_hooks: Enable non-blocking git hooks (default: False)
        parallel_execution: Enable parallel tool execution (default: True)
        tui_progress: Enable TUI progress display (default: True)
        cache_results: Cache validation results (default: True)
    """

    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize configuration.

        Args:
            config_file: Path to .huskycat.yaml (default: find in project root)
        """
        self.config_file = config_file or self._find_config_file()
        self._config: Dict[str, Any] = {}
        self._validated_config: Optional[HuskyCatConfigSchema] = None
        self._validation_errors: list[str] = []
        self._load_config()

    def _find_config_file(self) -> Optional[Path]:
        """
        Find .huskycat.yaml in current directory or parents.

        Returns:
            Path to config file or None if not found
        """
        current = Path.cwd()

        # Try current directory and all parents
        for parent in [current] + list(current.parents):
            config_path = parent / ".huskycat.yaml"
            if config_path.exists():
                return config_path

            # Also try .huskycat.json
            json_path = parent / ".huskycat.json"
            if json_path.exists():
                return json_path

        return None

    def _load_config(self):
        """Load configuration from file and environment."""
        # Load from file if exists
        if self.config_file and self.config_file.exists():
            try:
                content = self.config_file.read_text()

                # Parse based on extension
                if self.config_file.suffix in [".yaml", ".yml"]:
                    self._config = yaml.safe_load(content) or {}
                elif self.config_file.suffix == ".json":
                    self._config = json.loads(content)
                else:
                    # Try YAML first, then JSON
                    try:
                        self._config = yaml.safe_load(content) or {}
                    except yaml.YAMLError:
                        self._config = json.loads(content)

            except Exception as e:
                # Fail gracefully with empty config
                logger.warning(f"Could not load config from {self.config_file}: {e}")
                self._config = {}
        else:
            self._config = {}

        # Apply environment variable overrides
        self._apply_env_overrides()

        # Validate configuration using Pydantic schema
        self._validate_config()

    def _apply_env_overrides(self):
        """Apply environment variable overrides."""
        # Feature flags can be set via HUSKYCAT_FEATURE_<NAME>=true
        feature_prefix = "HUSKYCAT_FEATURE_"

        for key, value in os.environ.items():
            if key.startswith(feature_prefix):
                feature_name = key[len(feature_prefix) :].lower()
                feature_value = value.lower() in ["true", "1", "yes", "on"]

                # Ensure feature_flags section exists
                if "feature_flags" not in self._config:
                    self._config["feature_flags"] = {}

                self._config["feature_flags"][feature_name] = feature_value

    def _validate_config(self):
        """
        Validate configuration using Pydantic schema.

        If validation fails, logs warnings and uses default configuration.
        The raw config is still accessible for backward compatibility.
        """
        self._validation_errors = []

        try:
            self._validated_config = HuskyCatConfigSchema(**self._config)
        except ValidationError as e:
            # Collect all validation errors
            for error in e.errors():
                field_path = ".".join(str(loc) for loc in error["loc"])
                error_msg = f"{field_path}: {error['msg']}"
                self._validation_errors.append(error_msg)
                logger.warning(f"Config validation error: {error_msg}")

            # Fall back to default configuration
            logger.warning(
                "Using default configuration due to validation errors. "
                f"Found {len(self._validation_errors)} error(s)."
            )
            self._validated_config = HuskyCatConfigSchema()

    @property
    def validated(self) -> HuskyCatConfigSchema:
        """
        Get the validated configuration schema.

        Returns:
            HuskyCatConfigSchema instance (validated or default)
        """
        if self._validated_config is None:
            self._validate_config()
        return self._validated_config  # type: ignore[return-value]

    @property
    def validation_errors(self) -> list[str]:
        """
        Get any validation errors that occurred.

        Returns:
            List of validation error messages
        """
        return self._validation_errors.copy()

    @property
    def is_valid(self) -> bool:
        """
        Check if the configuration is valid.

        Returns:
            True if configuration passed validation, False otherwise
        """
        return len(self._validation_errors) == 0

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key.

        Args:
            key: Dot-separated key path (e.g., "feature_flags.nonblocking_hooks")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default

    def get_feature_flag(self, flag_name: str, default: bool = False) -> bool:
        """
        Get feature flag value.

        Args:
            flag_name: Name of the feature flag
            default: Default value if not set

        Returns:
            Boolean feature flag value
        """
        return bool(self.get(f"feature_flags.{flag_name}", default))

    @property
    def nonblocking_hooks_enabled(self) -> bool:
        """Check if non-blocking git hooks are enabled."""
        return self.get_feature_flag("nonblocking_hooks", default=False)

    @property
    def parallel_execution_enabled(self) -> bool:
        """Check if parallel tool execution is enabled."""
        return self.get_feature_flag("parallel_execution", default=True)

    @property
    def tui_progress_enabled(self) -> bool:
        """Check if TUI progress display is enabled."""
        return self.get_feature_flag("tui_progress", default=True)

    @property
    def cache_results_enabled(self) -> bool:
        """Check if result caching is enabled."""
        return self.get_feature_flag("cache_results", default=True)

    def set_feature_flag(self, flag_name: str, value: bool):
        """
        Set feature flag value (runtime only, not persisted).

        Args:
            flag_name: Name of the feature flag
            value: Boolean value to set
        """
        if "feature_flags" not in self._config:
            self._config["feature_flags"] = {}

        self._config["feature_flags"][flag_name] = value

    def to_dict(self) -> Dict[str, Any]:
        """
        Get full configuration as dictionary.

        Returns:
            Dictionary with all configuration
        """
        return self._config.copy()


# Global config instance (lazy-loaded)
_global_config: Optional[HuskyCatConfig] = None


def get_config(config_file: Optional[Path] = None) -> HuskyCatConfig:
    """
    Get global configuration instance.

    Args:
        config_file: Optional config file path (only used on first call)

    Returns:
        HuskyCatConfig instance
    """
    global _global_config

    if _global_config is None:
        _global_config = HuskyCatConfig(config_file)

    return _global_config


def reload_config(config_file: Optional[Path] = None):
    """
    Reload configuration from file.

    Args:
        config_file: Optional new config file path
    """
    global _global_config
    _global_config = HuskyCatConfig(config_file)
