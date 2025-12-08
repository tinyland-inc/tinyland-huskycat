#!/usr/bin/env python3
"""
Comprehensive tests for HuskyCat configuration system.

Tests cover:
- YAML and JSON configuration file loading
- Configuration file discovery and fallback
- Environment variable overrides
- Feature flag configuration and cascading
- Runtime configuration updates
- Error handling and recovery
"""

import json
import os
from pathlib import Path
from unittest import mock

import pytest
import yaml

from src.huskycat.core.config import HuskyCatConfig, get_config, reload_config


class TestConfigFileLoading:
    """Test configuration file loading from various formats."""

    def test_load_yaml_config(self, tmp_path):
        """Test loading YAML configuration file."""
        config_file = tmp_path / ".huskycat.yaml"
        config_data = {
            "feature_flags": {
                "nonblocking_hooks": True,
                "parallel_execution": False,
            },
            "tools": {
                "black": {"enabled": True},
                "mypy": {"enabled": False},
            },
        }

        config_file.write_text(yaml.dump(config_data))

        config = HuskyCatConfig(config_file)

        assert config.get("feature_flags.nonblocking_hooks") is True
        assert config.get("feature_flags.parallel_execution") is False
        assert config.get("tools.black.enabled") is True
        assert config.get("tools.mypy.enabled") is False

    def test_load_json_config(self, tmp_path):
        """Test loading JSON configuration file."""
        config_file = tmp_path / ".huskycat.json"
        config_data = {
            "feature_flags": {
                "tui_progress": False,
                "cache_results": True,
            },
            "validation": {"timeout_seconds": 30},
        }

        config_file.write_text(json.dumps(config_data))

        config = HuskyCatConfig(config_file)

        assert config.get("feature_flags.tui_progress") is False
        assert config.get("feature_flags.cache_results") is True
        assert config.get("validation.timeout_seconds") == 30

    def test_load_yaml_with_yml_extension(self, tmp_path):
        """Test loading YAML configuration with .yml extension."""
        config_file = tmp_path / ".huskycat.yml"
        config_data = {"feature_flags": {"nonblocking_hooks": True}}

        config_file.write_text(yaml.dump(config_data))

        config = HuskyCatConfig(config_file)

        assert config.get("feature_flags.nonblocking_hooks") is True

    def test_config_file_not_found(self):
        """Test handling of missing configuration file."""
        nonexistent_path = Path("/nonexistent/path/.huskycat.yaml")

        config = HuskyCatConfig(nonexistent_path)

        assert config._config == {}
        assert config.to_dict() == {}

    def test_config_file_with_invalid_yaml(self, tmp_path):
        """Test handling of invalid YAML configuration."""
        config_file = tmp_path / ".huskycat.yaml"
        # Invalid YAML syntax
        config_file.write_text("invalid: yaml: content: [")

        config = HuskyCatConfig(config_file)

        # Should gracefully fail with empty config
        assert config._config == {}

    def test_config_file_with_invalid_json(self, tmp_path):
        """Test handling of invalid JSON configuration."""
        config_file = tmp_path / ".huskycat.json"
        # Invalid JSON syntax
        config_file.write_text('{"invalid": json}')

        config = HuskyCatConfig(config_file)

        # Should gracefully fail
        assert config._config == {}

    def test_config_discovery_in_current_directory(self, tmp_path, monkeypatch):
        """Test configuration discovery in current directory."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({"discovered": True}))

        monkeypatch.chdir(tmp_path)

        config = HuskyCatConfig()

        assert config.config_file == config_file
        assert config.get("discovered") is True

    def test_config_discovery_in_parent_directory(self, tmp_path, monkeypatch):
        """Test configuration discovery in parent directory."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({"parent": True}))

        subdir = tmp_path / "subdir" / "nested"
        subdir.mkdir(parents=True)

        monkeypatch.chdir(subdir)

        config = HuskyCatConfig()

        assert config.config_file == config_file
        assert config.get("parent") is True

    def test_config_discovery_prefers_yaml_over_json(self, tmp_path, monkeypatch):
        """Test that YAML is preferred over JSON in discovery."""
        yaml_file = tmp_path / ".huskycat.yaml"
        yaml_file.write_text(yaml.dump({"format": "yaml"}))

        json_file = tmp_path / ".huskycat.json"
        json_file.write_text(json.dumps({"format": "json"}))

        monkeypatch.chdir(tmp_path)

        config = HuskyCatConfig()

        assert config.config_file == yaml_file
        assert config.get("format") == "yaml"

    def test_config_discovery_returns_none_when_not_found(self, tmp_path, monkeypatch):
        """Test that config discovery returns None when no config found."""
        monkeypatch.chdir(tmp_path)

        config = HuskyCatConfig()

        assert config.config_file is None
        assert config._config == {}


class TestEnvironmentVariables:
    """Test environment variable configuration overrides."""

    def test_env_var_feature_flag_override(self, tmp_path):
        """Test environment variable overrides YAML feature flag."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(
            yaml.dump({"feature_flags": {"nonblocking_hooks": False}})
        )

        with mock.patch.dict(
            os.environ, {"HUSKYCAT_FEATURE_NONBLOCKING_HOOKS": "true"}
        ):
            config = HuskyCatConfig(config_file)

            assert config.get_feature_flag("nonblocking_hooks") is True

    def test_env_var_multiple_feature_flags(self, tmp_path):
        """Test multiple environment variable feature flag overrides."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({"feature_flags": {}}))

        env_vars = {
            "HUSKYCAT_FEATURE_NONBLOCKING_HOOKS": "true",
            "HUSKYCAT_FEATURE_PARALLEL_EXECUTION": "false",
            "HUSKYCAT_FEATURE_TUI_PROGRESS": "1",
            "HUSKYCAT_FEATURE_CACHE_RESULTS": "yes",
        }

        with mock.patch.dict(os.environ, env_vars):
            config = HuskyCatConfig(config_file)

            assert config.get_feature_flag("nonblocking_hooks") is True
            assert config.get_feature_flag("parallel_execution") is False
            assert config.get_feature_flag("tui_progress") is True
            assert config.get_feature_flag("cache_results") is True

    def test_env_var_feature_flag_case_insensitive(self, tmp_path):
        """Test feature flag env vars are case insensitive."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({}))

        with mock.patch.dict(
            os.environ, {"HUSKYCAT_FEATURE_NONBLOCKING_HOOKS": "TRUE"}
        ):
            config = HuskyCatConfig(config_file)

            assert config.get_feature_flag("nonblocking_hooks") is True

    def test_env_var_feature_flag_false_values(self, tmp_path):
        """Test various false values for feature flags."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({}))

        for false_value in ["false", "False", "0", "no", "off", "anything_else"]:
            with mock.patch.dict(
                os.environ, {"HUSKYCAT_FEATURE_TEST": false_value}
            ):
                config = HuskyCatConfig(config_file)

                assert config.get_feature_flag("test") is False

    def test_env_var_true_values(self, tmp_path):
        """Test various true values for feature flags."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({}))

        for true_value in ["true", "True", "1", "yes", "on"]:
            with mock.patch.dict(
                os.environ, {"HUSKYCAT_FEATURE_TEST": true_value}
            ):
                config = HuskyCatConfig(config_file)

                assert config.get_feature_flag("test") is True

    def test_env_var_creates_feature_flags_section(self, tmp_path):
        """Test that env vars create feature_flags section if missing."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({"other": "value"}))

        with mock.patch.dict(
            os.environ, {"HUSKYCAT_FEATURE_NEW_FLAG": "true"}
        ):
            config = HuskyCatConfig(config_file)

            assert "feature_flags" in config._config
            assert config.get("feature_flags.new_flag") is True

    def test_env_var_non_feature_vars_ignored(self, tmp_path):
        """Test that non-HUSKYCAT_FEATURE vars are ignored."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({}))

        with mock.patch.dict(
            os.environ,
            {
                "OTHER_VAR": "value",
                "HUSKYCAT_OTHER": "value",
                "FEATURE_TEST": "value",
            },
        ):
            config = HuskyCatConfig(config_file)

            assert "feature_flags" not in config._config or len(
                config.get("feature_flags", {})
            ) == 0


class TestFeatureFlags:
    """Test feature flag configuration and properties."""

    def test_feature_flag_nonblocking_hooks_default(self, tmp_path):
        """Test nonblocking_hooks feature flag default value."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({}))

        config = HuskyCatConfig(config_file)

        assert config.nonblocking_hooks_enabled is False

    def test_feature_flag_parallel_execution_default(self, tmp_path):
        """Test parallel_execution feature flag default value."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({}))

        config = HuskyCatConfig(config_file)

        assert config.parallel_execution_enabled is True

    def test_feature_flag_tui_progress_default(self, tmp_path):
        """Test tui_progress feature flag default value."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({}))

        config = HuskyCatConfig(config_file)

        assert config.tui_progress_enabled is True

    def test_feature_flag_cache_results_default(self, tmp_path):
        """Test cache_results feature flag default value."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({}))

        config = HuskyCatConfig(config_file)

        assert config.cache_results_enabled is True

    def test_set_feature_flag_runtime(self, tmp_path):
        """Test setting feature flag at runtime."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({"feature_flags": {"test": False}}))

        config = HuskyCatConfig(config_file)

        assert config.get_feature_flag("test") is False

        config.set_feature_flag("test", True)

        assert config.get_feature_flag("test") is True

    def test_set_feature_flag_creates_section(self, tmp_path):
        """Test setting feature flag creates section if missing."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({}))

        config = HuskyCatConfig(config_file)

        config.set_feature_flag("new_flag", True)

        assert config.get("feature_flags.new_flag") is True

    def test_feature_flag_cascading_from_file_and_env(self, tmp_path):
        """Test feature flag cascading with file and env vars."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "feature_flags": {
                        "flag1": True,
                        "flag2": False,
                        "flag3": True,
                    }
                }
            )
        )

        env_vars = {
            "HUSKYCAT_FEATURE_FLAG2": "true",  # Override file
            "HUSKYCAT_FEATURE_FLAG4": "true",  # New from env
        }

        with mock.patch.dict(os.environ, env_vars):
            config = HuskyCatConfig(config_file)

            assert config.get_feature_flag("flag1") is True  # From file
            assert config.get_feature_flag("flag2") is True  # Overridden by env
            assert config.get_feature_flag("flag3") is True  # From file
            assert config.get_feature_flag("flag4") is True  # From env

    def test_invalid_feature_flag_name_uses_default(self, tmp_path):
        """Test that invalid feature flag names return default."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({}))

        config = HuskyCatConfig(config_file)

        assert config.get_feature_flag("nonexistent_flag", default=False) is False
        assert config.get_feature_flag("nonexistent_flag", default=True) is True


class TestConfigGetMethod:
    """Test configuration value retrieval."""

    def test_get_simple_value(self, tmp_path):
        """Test getting simple configuration value."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({"key": "value"}))

        config = HuskyCatConfig(config_file)

        assert config.get("key") == "value"

    def test_get_nested_value_dot_notation(self, tmp_path):
        """Test getting nested value with dot notation."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(
            yaml.dump({"section": {"subsection": {"key": "value"}}})
        )

        config = HuskyCatConfig(config_file)

        assert config.get("section.subsection.key") == "value"

    def test_get_with_default_value(self, tmp_path):
        """Test getting value with default."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({}))

        config = HuskyCatConfig(config_file)

        assert config.get("nonexistent", "default") == "default"

    def test_get_none_returns_default(self, tmp_path):
        """Test that None value returns default."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({"key": None}))

        config = HuskyCatConfig(config_file)

        assert config.get("key", "default") == "default"

    def test_get_partial_path_returns_default(self, tmp_path):
        """Test getting partial path returns default."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({"section": {"key": "value"}}))

        config = HuskyCatConfig(config_file)

        assert config.get("section.missing.key", "default") == "default"

    def test_get_on_non_dict_returns_default(self, tmp_path):
        """Test getting from non-dict value returns default."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({"key": "value"}))

        config = HuskyCatConfig(config_file)

        # Trying to access "key.subkey" when "key" is a string
        assert config.get("key.subkey", "default") == "default"

    def test_get_empty_key_returns_default(self, tmp_path):
        """Test that empty key returns None (no split behavior)."""
        config_file = tmp_path / ".huskycat.yaml"
        config_data = {"key": "value"}
        config_file.write_text(yaml.dump(config_data))

        config = HuskyCatConfig(config_file)

        # Empty key results in split returning [""], which looks for empty string key
        assert config.get("", "default") == "default"

    def test_get_zero_returns_value(self, tmp_path):
        """Test that 0 value is returned (not treated as None)."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({"count": 0}))

        config = HuskyCatConfig(config_file)

        assert config.get("count") == 0

    def test_get_false_returns_value(self, tmp_path):
        """Test that False value is returned (not treated as None)."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({"enabled": False}))

        config = HuskyCatConfig(config_file)

        assert config.get("enabled") is False


class TestConfigSerialization:
    """Test configuration serialization and conversion."""

    def test_to_dict_returns_copy(self, tmp_path):
        """Test that to_dict returns a copy of config."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({"key": "value"}))

        config = HuskyCatConfig(config_file)
        config_dict = config.to_dict()

        # Modify the returned dict
        config_dict["key"] = "modified"

        # Original config should be unchanged
        assert config.get("key") == "value"

    def test_to_dict_includes_all_config(self, tmp_path):
        """Test that to_dict includes all configuration."""
        config_data = {
            "section1": {"key1": "value1"},
            "section2": {"key2": "value2"},
            "feature_flags": {"flag1": True},
        }
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump(config_data))

        config = HuskyCatConfig(config_file)
        config_dict = config.to_dict()

        assert config_dict == config_data


class TestGlobalConfigInstance:
    """Test global configuration instance management."""

    def test_get_config_returns_singleton(self, tmp_path):
        """Test that get_config returns singleton instance."""
        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({"singleton": True}))

        # Import fresh to reset global state
        import src.huskycat.core.config as config_module  # noqa: F401, E402

        # Reset global
        config_module._global_config = None

        config1 = config_module.get_config(config_file)
        config2 = config_module.get_config()

        assert config1 is config2
        assert config1.get("singleton") is True

    def test_reload_config_creates_new_instance(self, tmp_path):
        """Test that reload_config creates new instance."""
        import src.huskycat.core.config as config_module  # noqa: F401, E402

        config_file = tmp_path / ".huskycat.yaml"
        config_file.write_text(yaml.dump({"version": 1}))

        # Reset global
        config_module._global_config = None

        config1 = config_module.get_config(config_file)

        # Update config file
        config_file.write_text(yaml.dump({"version": 2}))

        config_module.reload_config(config_file)

        # reload_config doesn't return, but updates the global
        config2 = config_module.get_config()

        assert config1 is not config2
        assert config2.get("version") == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
