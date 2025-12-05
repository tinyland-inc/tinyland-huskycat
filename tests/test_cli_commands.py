"""
Unit tests for HuskyCat CLI commands.

Tests each command's execute() method and error handling.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from huskycat.core.adapters import CLIAdapter, GitHooksAdapter
from huskycat.core.base import CommandResult, CommandStatus
from huskycat.core.factory import HuskyCatFactory


class TestHuskyCatFactory:
    """Test the HuskyCatFactory class."""

    def test_factory_creates_with_defaults(self):
        """Factory should create with default config directory."""
        factory = HuskyCatFactory()
        assert factory.config_dir == Path.home() / ".huskycat"
        assert factory.verbose is False
        assert factory.adapter is None

    def test_factory_creates_with_custom_config(self):
        """Factory should accept custom config directory."""
        custom_dir = Path("/tmp/custom-huskycat")
        factory = HuskyCatFactory(config_dir=custom_dir, verbose=True)
        assert factory.config_dir == custom_dir
        assert factory.verbose is True

    def test_factory_accepts_adapter(self):
        """Factory should accept mode adapter."""
        adapter = CLIAdapter()
        factory = HuskyCatFactory(adapter=adapter)
        assert factory.adapter is adapter

    def test_factory_lists_commands(self):
        """Factory should list all registered commands."""
        factory = HuskyCatFactory()
        commands = factory.list_commands()

        expected_commands = [
            "validate",
            "auto-fix",
            "install",
            "setup-hooks",
            "update-schemas",
            "ci-validate",
            "auto-devops",
            "mcp-server",
            "bootstrap",
            "clean",
            "status",
        ]
        for cmd in expected_commands:
            assert cmd in commands, f"Command '{cmd}' not found in factory"

    def test_factory_creates_validate_command(self):
        """Factory should create ValidateCommand."""
        factory = HuskyCatFactory()
        command = factory.create_command("validate")
        assert command is not None
        assert command.name == "validate"

    def test_factory_returns_none_for_unknown_command(self):
        """Factory should return None for unknown commands."""
        factory = HuskyCatFactory()
        command = factory.create_command("nonexistent")
        assert command is None

    def test_factory_execute_unknown_command(self):
        """Factory should return error for unknown command execution."""
        factory = HuskyCatFactory()
        result = factory.execute_command("nonexistent")

        assert result.status == CommandStatus.FAILED
        assert "Unknown command" in result.message

    def test_factory_passes_adapter_to_commands(self):
        """Factory should pass adapter to created commands."""
        adapter = GitHooksAdapter()
        factory = HuskyCatFactory(adapter=adapter)
        command = factory.create_command("validate")

        assert command.adapter is adapter

    def test_factory_get_command_info(self):
        """Factory should return command info."""
        factory = HuskyCatFactory()
        info = factory.get_command_info("validate")

        assert info is not None
        assert info["name"] == "validate"
        assert "description" in info

    def test_factory_get_command_info_unknown(self):
        """Factory should return None for unknown command info."""
        factory = HuskyCatFactory()
        info = factory.get_command_info("nonexistent")
        assert info is None


class TestValidateCommand:
    """Test ValidateCommand."""

    def test_validate_command_has_correct_name(self):
        """ValidateCommand should have correct name."""
        from huskycat.commands.validate import ValidateCommand

        command = ValidateCommand()
        assert command.name == "validate"

    def test_validate_command_accepts_adapter(self):
        """ValidateCommand should accept adapter."""
        from huskycat.commands.validate import ValidateCommand

        adapter = CLIAdapter()
        command = ValidateCommand(adapter=adapter)
        assert command.adapter is adapter

    def test_validate_command_uses_adapter_tool_selection(self):
        """ValidateCommand should use adapter's tool selection."""
        from huskycat.commands.validate import ValidateCommand

        adapter = GitHooksAdapter()
        command = ValidateCommand(adapter=adapter)

        tools = command.adapter.get_tool_selection()
        assert "python-black" in tools
        assert "ruff" in tools


class TestCleanCommand:
    """Test CleanCommand."""

    def test_clean_command_has_correct_name(self):
        """CleanCommand should have correct name."""
        from huskycat.commands.clean import CleanCommand

        command = CleanCommand()
        assert command.name == "clean"

    def test_clean_command_execute_with_temp_dir(self):
        """CleanCommand should execute without errors."""
        from huskycat.commands.clean import CleanCommand

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".huskycat"
            config_dir.mkdir(parents=True)

            # Create some cache files
            cache_dir = config_dir / "cache"
            cache_dir.mkdir()
            (cache_dir / "test.cache").write_text("test")

            command = CleanCommand(config_dir=config_dir)
            result = command.execute()

            # Should succeed or warn (depending on what exists)
            assert result.status in (CommandStatus.SUCCESS, CommandStatus.WARNING)


class TestStatusCommand:
    """Test StatusCommand."""

    def test_status_command_has_correct_name(self):
        """StatusCommand should have correct name."""
        from huskycat.commands.status import StatusCommand

        command = StatusCommand()
        assert command.name == "status"

    def test_status_command_execute(self):
        """StatusCommand should execute and return status info."""
        from huskycat.commands.status import StatusCommand

        with tempfile.TemporaryDirectory() as tmpdir:
            command = StatusCommand(config_dir=Path(tmpdir))
            result = command.execute()

            # Status should always succeed (it's informational)
            assert result.status in (CommandStatus.SUCCESS, CommandStatus.WARNING)


class TestInstallCommand:
    """Test InstallCommand."""

    def test_install_command_has_correct_name(self):
        """InstallCommand should have correct name."""
        from huskycat.commands.install import InstallCommand

        command = InstallCommand()
        assert command.name == "install"
        assert "Install" in command.description

    def test_install_command_creates_completions(self):
        """InstallCommand should create shell completions."""
        from huskycat.commands.install import InstallCommand

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".huskycat"
            command = InstallCommand(config_dir=config_dir)

            # Call the completions method directly
            command._create_completions()

            completions_dir = config_dir / "completions"
            assert completions_dir.exists()
            assert (completions_dir / "huskycat.bash").exists()
            assert (completions_dir / "_huskycat").exists()  # zsh
            assert (completions_dir / "huskycat.fish").exists()

    def test_install_command_get_path_instructions(self):
        """InstallCommand should generate path instructions."""
        from huskycat.commands.install import InstallCommand

        command = InstallCommand()
        install_dir = Path("/usr/local/bin")

        with patch.dict(os.environ, {"SHELL": "/bin/zsh"}):
            instructions = command._get_path_instructions(install_dir)
            assert "zshrc" in instructions

        with patch.dict(os.environ, {"SHELL": "/bin/bash"}):
            instructions = command._get_path_instructions(install_dir)
            assert "bashrc" in instructions


class TestSetupHooksCommand:
    """Test SetupHooksCommand."""

    def test_setup_hooks_has_correct_name(self):
        """SetupHooksCommand should have correct name."""
        from huskycat.commands.hooks import SetupHooksCommand

        command = SetupHooksCommand()
        assert command.name == "setup-hooks"

    def test_setup_hooks_in_non_git_repo(self):
        """SetupHooksCommand should fail in non-git directory."""
        from huskycat.commands.hooks import SetupHooksCommand

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                command = SetupHooksCommand()
                result = command.execute()

                # Should fail or warn - not a git repo
                assert result.status in (CommandStatus.FAILED, CommandStatus.WARNING)
            finally:
                os.chdir(original_cwd)


class TestAutoFixCommand:
    """Test AutoFixCommand."""

    def test_autofix_command_has_correct_name(self):
        """AutoFixCommand should have correct name."""
        from huskycat.commands.autofix import AutoFixCommand

        command = AutoFixCommand()
        assert command.name == "auto-fix"


class TestBootstrapCommand:
    """Test BootstrapCommand."""

    def test_bootstrap_command_has_correct_name(self):
        """BootstrapCommand should have correct name."""
        from huskycat.commands.bootstrap import BootstrapCommand

        command = BootstrapCommand()
        assert command.name == "bootstrap"


class TestCIValidateCommand:
    """Test CIValidateCommand."""

    def test_ci_validate_has_correct_name(self):
        """CIValidateCommand should have correct name."""
        from huskycat.commands.ci import CIValidateCommand

        command = CIValidateCommand()
        assert command.name == "ci-validate"


class TestMCPServerCommand:
    """Test MCPServerCommand."""

    def test_mcp_server_has_correct_name(self):
        """MCPServerCommand should have correct name."""
        from huskycat.commands.mcp import MCPServerCommand

        command = MCPServerCommand()
        assert command.name == "mcp-server"


class TestAutoDevOpsCommand:
    """Test AutoDevOpsCommand."""

    def test_autodevops_has_correct_name(self):
        """AutoDevOpsCommand should have correct name."""
        from huskycat.commands.autodevops import AutoDevOpsCommand

        command = AutoDevOpsCommand()
        assert command.name == "auto-devops"


class TestUpdateSchemasCommand:
    """Test UpdateSchemasCommand."""

    def test_update_schemas_has_correct_name(self):
        """UpdateSchemasCommand should have correct name."""
        from huskycat.commands.schemas import UpdateSchemasCommand

        command = UpdateSchemasCommand()
        assert command.name == "update-schemas"


class TestCLIArgumentParsing:
    """Test CLI argument parsing."""

    def test_create_parser(self):
        """Parser should be created with all subcommands."""
        from huskycat.__main__ import create_parser

        parser = create_parser()

        # Parse help to verify it works
        try:
            parser.parse_args(["--help"])
        except SystemExit:
            pass  # --help exits

    def test_parse_validate_args(self):
        """Parser should parse validate arguments."""
        from huskycat.__main__ import create_parser

        parser = create_parser()

        args = parser.parse_args(["validate", "--staged", "--fix"])
        assert args.command == "validate"
        assert args.staged is True
        assert args.fix is True

    def test_parse_mode_override(self):
        """Parser should parse --mode argument."""
        from huskycat.__main__ import create_parser

        parser = create_parser()

        args = parser.parse_args(["--mode", "ci", "validate"])
        assert args.mode == "ci"
        assert args.command == "validate"

    def test_parse_json_flag(self):
        """Parser should parse --json argument."""
        from huskycat.__main__ import create_parser

        parser = create_parser()

        args = parser.parse_args(["--json", "validate"])
        assert args.json is True

    def test_parse_verbose_flag(self):
        """Parser should parse --verbose argument."""
        from huskycat.__main__ import create_parser

        parser = create_parser()

        args = parser.parse_args(["-v", "status"])
        assert args.verbose is True


class TestCommandResult:
    """Test CommandResult dataclass."""

    def test_command_result_success(self):
        """CommandResult should represent success."""
        result = CommandResult(
            status=CommandStatus.SUCCESS, message="Operation completed"
        )
        assert result.status == CommandStatus.SUCCESS
        # Default values are empty lists, not None
        assert result.errors == []
        assert result.warnings == []

    def test_command_result_failed(self):
        """CommandResult should represent failure with errors."""
        result = CommandResult(
            status=CommandStatus.FAILED,
            message="Operation failed",
            errors=["Error 1", "Error 2"],
        )
        assert result.status == CommandStatus.FAILED
        assert len(result.errors) == 2

    def test_command_result_warning(self):
        """CommandResult should represent warnings."""
        result = CommandResult(
            status=CommandStatus.WARNING,
            message="Completed with warnings",
            warnings=["Warning 1"],
        )
        assert result.status == CommandStatus.WARNING
        assert len(result.warnings) == 1

    def test_command_result_with_data(self):
        """CommandResult should carry arbitrary data."""
        result = CommandResult(
            status=CommandStatus.SUCCESS,
            message="Success",
            data={"files_checked": 10, "errors_found": 0},
        )
        assert result.data["files_checked"] == 10


class TestCommandStatus:
    """Test CommandStatus enum."""

    def test_status_values(self):
        """CommandStatus should have correct values."""
        assert CommandStatus.SUCCESS.value == "success"
        assert CommandStatus.FAILED.value == "failed"
        assert CommandStatus.WARNING.value == "warning"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
