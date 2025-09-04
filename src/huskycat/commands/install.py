"""
Installation command for setting up HuskyCat.
"""

import subprocess

from ..core.base import BaseCommand, CommandResult, CommandStatus


class InstallCommand(BaseCommand):
    """Command to install HuskyCat and its dependencies."""

    @property
    def name(self) -> str:
        return "install"

    @property
    def description(self) -> str:
        return "Install HuskyCat and all dependencies using uv"

    def execute(self, dev: bool = False, global_install: bool = False) -> CommandResult:
        """
        Execute installation.

        Args:
            dev: Install development dependencies
            global_install: Install globally (not recommended)

        Returns:
            CommandResult with installation status
        """
        errors = []
        warnings = []

        # Check for uv
        try:
            subprocess.run(["uv", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Install uv if not present
            self.log("Installing uv package manager...")
            try:
                subprocess.run(
                    ["curl", "-LsSf", "https://astral.sh/uv/install.sh", "|", "sh"],
                    shell=True,
                    check=True,
                )
            except subprocess.CalledProcessError as e:
                return CommandResult(
                    status=CommandStatus.FAILED,
                    message="Failed to install uv",
                    errors=[str(e)],
                )

        # Install Python dependencies
        self.log("Installing Python dependencies...")
        try:
            cmd = ["uv", "pip", "install", "-e", "."]
            if dev:
                cmd.extend(["-e", ".[dev]"])

            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            errors.append(f"Failed to install Python dependencies: {e}")

        # Install git hooks
        self.log("Setting up git hooks...")
        try:
            from .hooks import SetupHooksCommand

            hooks_cmd = SetupHooksCommand(
                config_dir=self.config_dir, verbose=self.verbose
            )
            hooks_result = hooks_cmd.execute()
            if hooks_result.status != CommandStatus.SUCCESS:
                warnings.append("Git hooks setup had issues")
                warnings.extend(hooks_result.errors)
        except Exception as e:
            warnings.append(f"Could not setup git hooks: {e}")

        # Update schemas
        self.log("Updating validation schemas...")
        try:
            from .schemas import UpdateSchemasCommand

            schemas_cmd = UpdateSchemasCommand(
                config_dir=self.config_dir, verbose=self.verbose
            )
            schemas_result = schemas_cmd.execute()
            if schemas_result.status != CommandStatus.SUCCESS:
                warnings.append("Schema update had issues")
                warnings.extend(schemas_result.warnings)
        except Exception as e:
            warnings.append(f"Could not update schemas: {e}")

        # Create shell completion scripts
        self._create_completions()

        # Determine overall status
        if errors:
            return CommandResult(
                status=CommandStatus.FAILED,
                message="Installation failed",
                errors=errors,
                warnings=warnings,
            )
        elif warnings:
            return CommandResult(
                status=CommandStatus.WARNING,
                message="Installation completed with warnings",
                warnings=warnings,
            )
        else:
            return CommandResult(
                status=CommandStatus.SUCCESS, message="HuskyCat installed successfully"
            )

    def _create_completions(self):
        """Create shell completion scripts."""
        completions_dir = self.config_dir / "completions"
        completions_dir.mkdir(exist_ok=True)

        # Bash completion
        bash_completion = """
_huskycat_completions() {
    local commands="validate install setup-hooks update-schemas ci-validate mcp-server clean status"
    COMPREPLY=($(compgen -W "$commands" -- "${COMP_WORDS[COMP_CWORD]}"))
}
complete -F _huskycat_completions huskycat
"""
        (completions_dir / "huskycat.bash").write_text(bash_completion)

        # Zsh completion
        zsh_completion = """
#compdef huskycat
_huskycat() {
    local commands=(
        'validate:Run validation on files'
        'install:Install HuskyCat and dependencies'
        'setup-hooks:Setup git hooks'
        'update-schemas:Update validation schemas'
        'ci-validate:Validate CI configuration'
        'mcp-server:Start MCP server'
        'clean:Clean cache and temporary files'
        'status:Show HuskyCat status'
    )
    _describe 'command' commands
}
"""
        (completions_dir / "_huskycat").write_text(zsh_completion)

        self.log(f"Shell completions created in {completions_dir}")
