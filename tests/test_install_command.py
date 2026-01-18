"""
Unit tests for HuskyCat install command.

Tests:
- Binary installation
- MCP server registration (--with-claude)
- MCP scope selection (--scope)
- MCP verification (--verify)
- Shell completions creation
- Git hooks setup
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from huskycat.commands.install import InstallCommand
from huskycat.core.base import CommandStatus


class TestInstallCommand:
    """Test the InstallCommand class."""

    def test_install_command_name(self):
        """Install command should have correct name."""
        cmd = InstallCommand()
        assert cmd.name == "install"

    def test_install_command_description(self):
        """Install command should have description."""
        cmd = InstallCommand()
        assert "install" in cmd.description.lower()
        assert "huskycat" in cmd.description.lower()

    def test_install_from_source_skips_binary(self, tmp_path):
        """When running from source, should skip binary installation."""
        cmd = InstallCommand(config_dir=tmp_path)

        # Mock _get_executable_path to return None (running from source)
        with patch.object(cmd, "_get_executable_path", return_value=None):
            with patch.object(cmd, "_is_git_repo", return_value=False):
                result = cmd.execute(
                    bin_dir=str(tmp_path / "bin"),
                    setup_hooks=False,
                    skip_path_check=True,
                )

        assert result.status in (CommandStatus.SUCCESS, CommandStatus.WARNING)
        assert result.data.get("running_from_source") is True

    def test_install_creates_completions_directory(self, tmp_path):
        """Install should create shell completions directory."""
        config_dir = tmp_path / "config"
        cmd = InstallCommand(config_dir=config_dir)

        with patch.object(cmd, "_get_executable_path", return_value=None):
            with patch.object(cmd, "_is_git_repo", return_value=False):
                result = cmd.execute(
                    bin_dir=str(tmp_path / "bin"),
                    setup_hooks=False,
                    skip_path_check=True,
                )

        completions_dir = config_dir / "completions"
        assert completions_dir.exists()
        assert (completions_dir / "huskycat.bash").exists()
        assert (completions_dir / "_huskycat").exists()
        assert (completions_dir / "huskycat.fish").exists()

    def test_install_completions_contain_new_flags(self, tmp_path):
        """Shell completions should include --with-claude flag."""
        config_dir = tmp_path / "config"
        cmd = InstallCommand(config_dir=config_dir)

        with patch.object(cmd, "_get_executable_path", return_value=None):
            with patch.object(cmd, "_is_git_repo", return_value=False):
                cmd.execute(
                    bin_dir=str(tmp_path / "bin"),
                    setup_hooks=False,
                    skip_path_check=True,
                )

        # Check zsh completion has --with-claude
        zsh_completion = (config_dir / "completions" / "_huskycat").read_text()
        assert "--with-claude" in zsh_completion
        assert "--scope" in zsh_completion
        assert "--verify" in zsh_completion


class TestMCPRegistration:
    """Test MCP server registration functionality."""

    def test_register_mcp_using_claude_cli(self, tmp_path):
        """Should use claude mcp add-json when available."""
        cmd = InstallCommand(config_dir=tmp_path)

        # Mock successful claude CLI call
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = cmd._register_mcp_server("user")

        assert result["success"] is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "claude" in call_args
        assert "mcp" in call_args
        assert "add-json" in call_args
        assert "huskycat" in call_args

    def test_register_mcp_falls_back_to_direct(self, tmp_path):
        """Should fall back to direct file manipulation if claude not found."""
        cmd = InstallCommand(config_dir=tmp_path)

        # Mock FileNotFoundError for claude CLI
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("claude not found")
            with patch.object(cmd, "_register_mcp_direct") as mock_direct:
                mock_direct.return_value = {"success": True}
                result = cmd._register_mcp_server("user")

        assert result["success"] is True
        mock_direct.assert_called_once_with("user")

    def test_register_mcp_direct_user_scope(self, tmp_path):
        """Direct registration should write to ~/.claude/.mcp.json for user scope."""
        cmd = InstallCommand(config_dir=tmp_path)

        with patch.object(Path, "home", return_value=tmp_path):
            result = cmd._register_mcp_direct("user")

        assert result["success"] is True
        mcp_file = tmp_path / ".claude" / ".mcp.json"
        assert mcp_file.exists()

        config = json.loads(mcp_file.read_text())
        assert "mcpServers" in config
        assert "huskycat" in config["mcpServers"]
        assert config["mcpServers"]["huskycat"]["command"] == "huskycat"
        assert config["mcpServers"]["huskycat"]["args"] == ["mcp-server"]

    def test_register_mcp_direct_project_scope(self, tmp_path):
        """Direct registration should write to .mcp.json for project scope."""
        cmd = InstallCommand(config_dir=tmp_path)

        with patch.object(Path, "cwd", return_value=tmp_path):
            result = cmd._register_mcp_direct("project")

        assert result["success"] is True
        mcp_file = tmp_path / ".mcp.json"
        assert mcp_file.exists()

        config = json.loads(mcp_file.read_text())
        assert "mcpServers" in config
        assert "huskycat" in config["mcpServers"]

    def test_register_mcp_merges_with_existing(self, tmp_path):
        """Direct registration should merge with existing MCP config."""
        cmd = InstallCommand(config_dir=tmp_path)

        # Create existing config
        mcp_file = tmp_path / ".mcp.json"
        existing_config = {
            "mcpServers": {"other-server": {"command": "other", "args": []}}
        }
        mcp_file.write_text(json.dumps(existing_config))

        with patch.object(Path, "cwd", return_value=tmp_path):
            result = cmd._register_mcp_direct("project")

        assert result["success"] is True
        config = json.loads(mcp_file.read_text())
        assert "other-server" in config["mcpServers"]
        assert "huskycat" in config["mcpServers"]


class TestMCPVerification:
    """Test MCP connection verification."""

    def test_verify_mcp_success(self, tmp_path):
        """Should verify MCP connection when huskycat is in PATH."""
        cmd = InstallCommand(config_dir=tmp_path)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = cmd._verify_mcp_connection()

        assert result["success"] is True

    def test_verify_mcp_not_in_path(self, tmp_path):
        """Should fail verification when huskycat not in PATH."""
        cmd = InstallCommand(config_dir=tmp_path)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("huskycat not found")
            result = cmd._verify_mcp_connection()

        assert result["success"] is False
        assert "not found" in result["error"].lower()


class TestInstallWithClaudeIntegration:
    """Test the full --with-claude integration flow."""

    def test_install_with_claude_flag(self, tmp_path):
        """Install with --with-claude should register MCP server."""
        cmd = InstallCommand(config_dir=tmp_path)

        with patch.object(cmd, "_get_executable_path", return_value=None):
            with patch.object(cmd, "_is_git_repo", return_value=False):
                with patch.object(
                    cmd, "_register_mcp_server", return_value={"success": True}
                ) as mock_register:
                    result = cmd.execute(
                        bin_dir=str(tmp_path / "bin"),
                        setup_hooks=False,
                        skip_path_check=True,
                        with_claude=True,
                        scope="user",
                    )

        mock_register.assert_called_once_with("user")
        assert result.data.get("mcp_registered") is True
        assert result.data.get("mcp_scope") == "user"

    def test_install_with_claude_and_verify(self, tmp_path):
        """Install with --with-claude --verify should verify connection."""
        cmd = InstallCommand(config_dir=tmp_path)

        with patch.object(cmd, "_get_executable_path", return_value=None):
            with patch.object(cmd, "_is_git_repo", return_value=False):
                with patch.object(
                    cmd, "_register_mcp_server", return_value={"success": True}
                ):
                    with patch.object(
                        cmd, "_verify_mcp_connection", return_value={"success": True}
                    ) as mock_verify:
                        result = cmd.execute(
                            bin_dir=str(tmp_path / "bin"),
                            setup_hooks=False,
                            skip_path_check=True,
                            with_claude=True,
                            verify=True,
                        )

        mock_verify.assert_called_once()
        assert result.data.get("mcp_verified") is True

    def test_install_with_claude_registration_failure(self, tmp_path):
        """Should warn when MCP registration fails."""
        cmd = InstallCommand(config_dir=tmp_path)

        with patch.object(cmd, "_get_executable_path", return_value=None):
            with patch.object(cmd, "_is_git_repo", return_value=False):
                with patch.object(
                    cmd,
                    "_register_mcp_server",
                    return_value={"success": False, "error": "test error"},
                ):
                    result = cmd.execute(
                        bin_dir=str(tmp_path / "bin"),
                        setup_hooks=False,
                        skip_path_check=True,
                        with_claude=True,
                    )

        assert result.data.get("mcp_registered") is False
        assert any("mcp" in w.lower() for w in (result.warnings or []))

    def test_install_project_scope(self, tmp_path):
        """Install with project scope should pass scope to registration."""
        cmd = InstallCommand(config_dir=tmp_path)

        with patch.object(cmd, "_get_executable_path", return_value=None):
            with patch.object(cmd, "_is_git_repo", return_value=False):
                with patch.object(
                    cmd, "_register_mcp_server", return_value={"success": True}
                ) as mock_register:
                    result = cmd.execute(
                        bin_dir=str(tmp_path / "bin"),
                        setup_hooks=False,
                        skip_path_check=True,
                        with_claude=True,
                        scope="project",
                    )

        mock_register.assert_called_once_with("project")
        assert result.data.get("mcp_scope") == "project"


class TestPathInstructions:
    """Test PATH instruction generation."""

    def test_path_instructions_zsh(self, tmp_path):
        """Should generate zsh-specific PATH instructions."""
        cmd = InstallCommand(config_dir=tmp_path)

        with patch.dict("os.environ", {"SHELL": "/bin/zsh"}):
            instructions = cmd._get_path_instructions(Path("/usr/local/bin"))

        assert "zshrc" in instructions
        assert "/usr/local/bin" in instructions

    def test_path_instructions_bash(self, tmp_path):
        """Should generate bash-specific PATH instructions."""
        cmd = InstallCommand(config_dir=tmp_path)

        with patch.dict("os.environ", {"SHELL": "/bin/bash"}):
            instructions = cmd._get_path_instructions(Path("/usr/local/bin"))

        assert "bashrc" in instructions
        assert "/usr/local/bin" in instructions

    def test_path_instructions_fish(self, tmp_path):
        """Should generate fish-specific PATH instructions."""
        cmd = InstallCommand(config_dir=tmp_path)

        with patch.dict("os.environ", {"SHELL": "/usr/bin/fish"}):
            instructions = cmd._get_path_instructions(Path("/usr/local/bin"))

        assert "fish_add_path" in instructions
        assert "/usr/local/bin" in instructions


class TestGitRepoDetection:
    """Test git repository detection."""

    def test_is_git_repo_returns_true(self, tmp_path):
        """Should detect git repository."""
        cmd = InstallCommand(config_dir=tmp_path)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = cmd._is_git_repo()

        assert result is True

    def test_is_git_repo_returns_false(self, tmp_path):
        """Should return false when not in git repo."""
        cmd = InstallCommand(config_dir=tmp_path)

        with patch("subprocess.run") as mock_run:
            from subprocess import CalledProcessError

            mock_run.side_effect = CalledProcessError(128, "git")
            result = cmd._is_git_repo()

        assert result is False
