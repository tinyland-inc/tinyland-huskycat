# SPDX-License-Identifier: Apache-2.0
"""Tests for RemoteJuggler integration."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess
import json

from src.huskycat.integrations.remote_juggler import (
    RemoteJugglerIntegration,
    RemoteJugglerConfig,
    IdentityResult,
    is_remote_juggler_available,
    CONFIG_FILE,
)


class TestRemoteJugglerConfig:
    """Test RemoteJugglerConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RemoteJugglerConfig()
        assert config.enabled is True
        assert config.binary_path is None
        assert config.integration_mode == "cli"
        assert config.auto_detect_identity is True
        assert config.warn_on_mismatch is True
        assert config.auto_switch is False
        assert config.validate_gpg is True
        assert config.validate_credentials is True
        assert config.proxy_mcp_tools is True
        assert config.tool_prefix == "juggler_"

    def test_config_load_nonexistent(self, tmp_path):
        """Test loading config from nonexistent file returns defaults."""
        nonexistent = tmp_path / "nonexistent.yaml"
        config = RemoteJugglerConfig.load(nonexistent)
        assert config.enabled is True

    def test_config_save_and_load(self, tmp_path):
        """Test saving and loading configuration."""
        config_file = tmp_path / "config.yaml"

        # Create custom config
        config = RemoteJugglerConfig(
            enabled=True,
            binary_path="/custom/path",
            integration_mode="mcp",
            auto_switch=True,
        )
        config.save(config_file)

        # Load and verify
        loaded = RemoteJugglerConfig.load(config_file)
        assert loaded.enabled is True
        assert loaded.binary_path == "/custom/path"
        assert loaded.integration_mode == "mcp"
        assert loaded.auto_switch is True


class TestIdentityResult:
    """Test IdentityResult dataclass."""

    def test_identity_result_defaults(self):
        """Test IdentityResult with default values."""
        result = IdentityResult(
            provider="gitlab",
            username="test",
            email="test@example.com",
        )
        assert result.provider == "gitlab"
        assert result.username == "test"
        assert result.email == "test@example.com"
        assert result.signing_key is None
        assert result.ssh_host is None
        assert result.confidence == 1.0
        assert result.matched_by == "explicit"

    def test_identity_result_full(self):
        """Test IdentityResult with all values."""
        result = IdentityResult(
            provider="github",
            username="octocat",
            email="octocat@github.com",
            signing_key="ABC123",
            ssh_host="github.com-personal",
            confidence=0.95,
            matched_by="remote",
        )
        assert result.signing_key == "ABC123"
        assert result.confidence == 0.95


class TestRemoteJugglerIntegration:
    """Test RemoteJugglerIntegration class."""

    def test_is_available_when_disabled(self):
        """Test is_available returns False when disabled."""
        config = RemoteJugglerConfig(enabled=False)
        integration = RemoteJugglerIntegration(config)
        assert integration.is_available() is False

    @patch("shutil.which")
    def test_is_available_when_binary_found(self, mock_which):
        """Test is_available returns True when binary found."""
        mock_which.return_value = "/usr/local/bin/remote-juggler"
        config = RemoteJugglerConfig(enabled=True)
        integration = RemoteJugglerIntegration(config)
        assert integration.is_available() is True

    @patch("src.huskycat.integrations.remote_juggler.shutil.which")
    def test_is_available_when_binary_not_found(self, mock_which):
        """Test is_available returns False when binary not found."""
        mock_which.return_value = None
        config = RemoteJugglerConfig(enabled=True, binary_path=None)
        integration = RemoteJugglerIntegration(config)
        # Clear any cached path
        integration._binary_path = None
        # Need to patch the Path.exists check for common paths too
        with patch.object(Path, "exists", return_value=False):
            assert integration.is_available() is False

    def test_find_binary_uses_config_path(self, tmp_path):
        """Test _find_binary prefers configured path."""
        # Create a fake binary
        fake_binary = tmp_path / "remote-juggler"
        fake_binary.touch()
        fake_binary.chmod(0o755)

        config = RemoteJugglerConfig(binary_path=str(fake_binary))
        integration = RemoteJugglerIntegration(config)

        assert integration._find_binary() == str(fake_binary)

    def test_get_mcp_tools_when_disabled(self):
        """Test get_mcp_tools returns empty when disabled."""
        config = RemoteJugglerConfig(proxy_mcp_tools=False)
        integration = RemoteJugglerIntegration(config)
        assert integration.get_mcp_tools() == []

    @patch.object(RemoteJugglerIntegration, "is_available", return_value=True)
    def test_get_mcp_tools_returns_tools(self, mock_available):
        """Test get_mcp_tools returns tool definitions."""
        config = RemoteJugglerConfig(tool_prefix="test_")
        integration = RemoteJugglerIntegration(config)

        tools = integration.get_mcp_tools()

        assert len(tools) == 6
        tool_names = [t["name"] for t in tools]
        assert "test_list_identities" in tool_names
        assert "test_detect_identity" in tool_names
        assert "test_switch" in tool_names
        assert "test_status" in tool_names
        assert "test_validate" in tool_names
        assert "test_gpg_status" in tool_names

    @patch.object(RemoteJugglerIntegration, "list_identities")
    @patch.object(RemoteJugglerIntegration, "is_available", return_value=True)
    def test_handle_mcp_tool_list_identities(self, mock_available, mock_list):
        """Test handling list_identities MCP tool."""
        mock_list.return_value = [
            {"name": "work", "email": "work@example.com"},
            {"name": "personal", "email": "personal@example.com"},
        ]

        config = RemoteJugglerConfig(tool_prefix="juggler_")
        integration = RemoteJugglerIntegration(config)

        result = integration.handle_mcp_tool("juggler_list_identities", {})

        assert "identities" in result
        assert len(result["identities"]) == 2

    @patch.object(RemoteJugglerIntegration, "detect_identity")
    @patch.object(RemoteJugglerIntegration, "is_available", return_value=True)
    def test_handle_mcp_tool_detect_identity(self, mock_available, mock_detect):
        """Test handling detect_identity MCP tool."""
        mock_detect.return_value = IdentityResult(
            provider="gitlab",
            username="test",
            email="test@example.com",
        )

        config = RemoteJugglerConfig(tool_prefix="juggler_")
        integration = RemoteJugglerIntegration(config)

        result = integration.handle_mcp_tool(
            "juggler_detect_identity",
            {"repo_path": "/some/repo"}
        )

        assert result["provider"] == "gitlab"
        assert result["email"] == "test@example.com"

    def test_handle_mcp_tool_unknown(self):
        """Test handling unknown MCP tool."""
        config = RemoteJugglerConfig(tool_prefix="juggler_")
        integration = RemoteJugglerIntegration(config)

        result = integration.handle_mcp_tool("unknown_tool", {})

        assert "error" in result


class TestPreCommitCheck:
    """Test pre-commit hook integration."""

    def test_pre_commit_check_disabled(self):
        """Test pre_commit_check when detection disabled."""
        config = RemoteJugglerConfig(auto_detect_identity=False)
        integration = RemoteJugglerIntegration(config)

        result = integration.pre_commit_check()

        assert result["ok"] is True

    @patch.object(RemoteJugglerIntegration, "detect_identity")
    @patch.object(RemoteJugglerIntegration, "is_available", return_value=True)
    def test_pre_commit_check_no_identity(self, mock_available, mock_detect):
        """Test pre_commit_check when no identity detected."""
        mock_detect.return_value = None

        config = RemoteJugglerConfig()
        integration = RemoteJugglerIntegration(config)

        result = integration.pre_commit_check()

        assert result["ok"] is True
        assert "warning" in result


class TestPrePushCheck:
    """Test pre-push hook integration."""

    @patch.object(RemoteJugglerIntegration, "validate_credentials")
    @patch.object(RemoteJugglerIntegration, "get_gpg_status")
    @patch.object(RemoteJugglerIntegration, "is_available", return_value=True)
    def test_pre_push_check_all_valid(self, mock_available, mock_gpg, mock_cred):
        """Test pre_push_check when all checks pass."""
        mock_gpg.return_value = {"ready": True}
        mock_cred.return_value = {"valid": True}

        config = RemoteJugglerConfig()
        integration = RemoteJugglerIntegration(config)

        result = integration.pre_push_check()

        assert result["ok"] is True
        assert result["errors"] == []

    @patch.object(RemoteJugglerIntegration, "validate_credentials")
    @patch.object(RemoteJugglerIntegration, "get_gpg_status")
    @patch.object(RemoteJugglerIntegration, "is_available", return_value=True)
    def test_pre_push_check_invalid_credentials(self, mock_available, mock_gpg, mock_cred):
        """Test pre_push_check with invalid credentials."""
        mock_gpg.return_value = {"ready": True}
        mock_cred.return_value = {"valid": False, "message": "Token expired"}

        config = RemoteJugglerConfig()
        integration = RemoteJugglerIntegration(config)

        result = integration.pre_push_check()

        assert result["ok"] is False
        assert len(result["errors"]) == 1
        assert "Token expired" in result["errors"][0]


class TestIsRemoteJugglerAvailable:
    """Test module-level availability function."""

    @patch("shutil.which")
    def test_available_when_in_path(self, mock_which):
        """Test returns True when binary in PATH."""
        mock_which.return_value = "/usr/local/bin/remote-juggler"
        assert is_remote_juggler_available() is True

    @patch("shutil.which")
    def test_not_available_when_not_in_path(self, mock_which):
        """Test returns False when binary not in PATH."""
        mock_which.return_value = None
        assert is_remote_juggler_available() is False
