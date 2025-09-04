"""
Command factory pattern for HuskyCat validation platform.
"""

from pathlib import Path
from typing import Dict, List, Optional, Type, Any
from importlib import import_module

from .base import BaseCommand, CommandResult, CommandStatus


class HuskyCatFactory:
    """Factory for creating and managing validation commands."""

    def __init__(self, config_dir: Optional[Path] = None, verbose: bool = False):
        """
        Initialize the factory.

        Args:
            config_dir: Directory containing configuration files
            verbose: Enable verbose output
        """
        self.config_dir = config_dir or Path.home() / ".huskycat"
        self.verbose = verbose
        self._commands: Dict[str, Type[BaseCommand]] = {}
        self._register_commands()

    def _register_commands(self) -> None:
        """Register all available commands."""
        # Get the base package name (handle both src.huskycat and huskycat)
        base_package = __package__.replace(".core", "")

        command_modules = {
            "validate": f"{base_package}.commands.validate.ValidateCommand",
            "install": f"{base_package}.commands.install.InstallCommand",
            "setup-hooks": f"{base_package}.commands.hooks.SetupHooksCommand",
            "update-schemas": f"{base_package}.commands.schemas.UpdateSchemasCommand",
            "ci-validate": f"{base_package}.commands.ci.CIValidateCommand",
            "auto-devops": f"{base_package}.commands.autodevops.AutoDevOpsCommand",
            "mcp-server": f"{base_package}.commands.mcp.MCPServerCommand",
            "clean": f"{base_package}.commands.clean.CleanCommand",
            "status": f"{base_package}.commands.status.StatusCommand",
        }

        for name, class_path in command_modules.items():
            try:
                module_path, class_name = class_path.rsplit(".", 1)
                module = import_module(module_path)
                command_class = getattr(module, class_name)
                self._commands[name] = command_class
            except (ImportError, AttributeError) as e:
                if self.verbose:
                    print(f"Warning: Could not load command {name}: {e}")

    def create_command(self, command_name: str) -> Optional[BaseCommand]:
        """
        Create a command instance.

        Args:
            command_name: Name of the command to create

        Returns:
            Command instance or None if not found
        """
        command_class = self._commands.get(command_name)
        if not command_class:
            return None

        return command_class(config_dir=self.config_dir, verbose=self.verbose)

    def execute_command(self, command_name: str, *args: Any, **kwargs: Any) -> CommandResult:
        """
        Execute a command by name.

        Args:
            command_name: Name of the command to execute
            **kwargs: Keyword arguments for the command

        Returns:
            CommandResult from the execution
        """
        command = self.create_command(command_name)
        if not command:
            return CommandResult(
                status=CommandStatus.FAILED,
                message=f"Unknown command: {command_name}",
                errors=[f"Command '{command_name}' not found"],
            )

        # Check prerequisites
        prereq_result = command.validate_prerequisites()
        if prereq_result.status != CommandStatus.SUCCESS:
            return prereq_result

        # Execute the command
        try:
            return command.execute(*args, **kwargs)
        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                message=f"Command execution failed: {str(e)}",
                errors=[str(e)],
            )

    def list_commands(self) -> List[str]:
        """Get list of available command names."""
        return list(self._commands.keys())

    def get_command_info(self, command_name: str) -> Optional[Dict[str, str]]:
        """
        Get information about a command.

        Args:
            command_name: Name of the command

        Returns:
            Dictionary with command info or None if not found
        """
        command = self.create_command(command_name)
        if not command:
            return None

        return {
            "name": command.name,
            "description": command.description,
            "module": command.__class__.__module__,
            "class": command.__class__.__name__,
        }
