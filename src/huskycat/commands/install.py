"""
Self-contained installation command for HuskyCat.

When running from a binary, this command:
1. Copies itself to ~/.local/bin/huskycat
2. Sets up git hooks in the current repository
3. Creates shell completions
"""

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from ..core.base import BaseCommand, CommandResult, CommandStatus


class InstallCommand(BaseCommand):
    """Self-contained installer - binary installs itself to PATH."""

    @property
    def name(self) -> str:
        return "install"

    @property
    def description(self) -> str:
        return "Install HuskyCat binary to ~/.local/bin and setup git hooks"

    def execute(
        self,
        bin_dir: str | None = None,
        setup_hooks: bool = True,
        skip_path_check: bool = False,
    ) -> CommandResult:
        """
        Install HuskyCat binary and configure environment.

        Args:
            bin_dir: Installation directory (default: ~/.local/bin)
            setup_hooks: Also setup git hooks in current repo
            skip_path_check: Don't warn about PATH issues

        Returns:
            CommandResult with installation status
        """
        errors = []
        warnings = []
        data = {}

        # Determine installation directory
        install_dir = Path(bin_dir) if bin_dir else Path.home() / ".local" / "bin"
        install_dir.mkdir(parents=True, exist_ok=True)

        # Get the path to the running executable
        executable = self._get_executable_path()
        target = install_dir / "huskycat"

        # Install binary
        if executable:
            try:
                self.log(f"Installing binary to {target}...")

                # Don't copy if we're already running from target location
                if Path(executable).resolve() != target.resolve():
                    shutil.copy2(executable, target)
                    # Ensure executable permissions
                    target.chmod(
                        target.stat().st_mode
                        | stat.S_IXUSR
                        | stat.S_IXGRP
                        | stat.S_IXOTH
                    )
                    data["binary_installed"] = str(target)
                    self.log(f"✓ Binary installed to {target}")
                else:
                    data["binary_installed"] = str(target)
                    self.log(f"✓ Already installed at {target}")

            except (OSError, shutil.Error) as e:
                errors.append(f"Failed to install binary: {e}")
        else:
            # Running from Python source, not a binary
            warnings.append("Running from source - skipping binary installation")
            data["running_from_source"] = True

        # Check PATH
        if not skip_path_check:
            path_dirs = os.environ.get("PATH", "").split(os.pathsep)
            if str(install_dir) not in path_dirs:
                warnings.append(f"{install_dir} is not in PATH")
                data["path_instructions"] = self._get_path_instructions(install_dir)

        # Setup git hooks if in a git repo
        if setup_hooks and self._is_git_repo():
            self.log("Setting up git hooks...")
            try:
                from .hooks import SetupHooksCommand

                hooks_cmd = SetupHooksCommand(
                    config_dir=self.config_dir, verbose=self.verbose
                )
                hooks_result = hooks_cmd.execute()
                if hooks_result.status == CommandStatus.SUCCESS:
                    data["hooks_installed"] = hooks_result.data.get(
                        "hooks_installed", []
                    )
                    self.log("✓ Git hooks installed")
                else:
                    warnings.extend(hooks_result.warnings or [])
            except Exception as e:
                warnings.append(f"Could not setup git hooks: {e}")
        elif setup_hooks:
            data["hooks_skipped"] = "Not in a git repository"

        # Create shell completions
        self._create_completions()
        data["completions_dir"] = str(self.config_dir / "completions")

        # Create config directory
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Summary
        if errors:
            return CommandResult(
                status=CommandStatus.FAILED,
                message="Installation failed",
                errors=errors,
                warnings=warnings,
                data=data,
            )
        elif warnings:
            return CommandResult(
                status=CommandStatus.WARNING,
                message="Installation completed with warnings",
                warnings=warnings,
                data=data,
            )
        else:
            return CommandResult(
                status=CommandStatus.SUCCESS,
                message=f"HuskyCat installed to {target}",
                data=data,
            )

    def _get_executable_path(self) -> str | None:
        """Get path to the running executable (works for PyInstaller binaries)."""
        # PyInstaller sets sys.frozen when running as a bundle
        if getattr(sys, "frozen", False):
            return sys.executable

        # Check if we're running from a binary-like path
        exe = sys.executable
        if exe and not exe.endswith("python") and not exe.endswith("python3"):
            return exe

        return None

    def _is_git_repo(self) -> bool:
        """Check if current directory is a git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                check=True,
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _get_path_instructions(self, install_dir: Path) -> str:
        """Get instructions for adding to PATH based on shell."""
        shell = os.environ.get("SHELL", "")

        if "zsh" in shell:
            return f"echo 'export PATH=\"$PATH:{install_dir}\"' >> ~/.zshrc && source ~/.zshrc"
        elif "bash" in shell:
            return f"echo 'export PATH=\"$PATH:{install_dir}\"' >> ~/.bashrc && source ~/.bashrc"
        elif "fish" in shell:
            return f"fish_add_path {install_dir}"
        else:
            return f'export PATH="$PATH:{install_dir}"'

    def _create_completions(self):
        """Create shell completion scripts."""
        completions_dir = self.config_dir / "completions"
        completions_dir.mkdir(parents=True, exist_ok=True)

        # Bash completion
        bash_completion = """
_huskycat_completions() {
    local commands="validate install setup-hooks update-schemas ci-validate mcp-server clean status autofix"
    local validate_opts="--staged --all --fix --interactive --allow-warnings"

    if [ "${#COMP_WORDS[@]}" -eq 2 ]; then
        COMPREPLY=($(compgen -W "$commands" -- "${COMP_WORDS[COMP_CWORD]}"))
    elif [ "${COMP_WORDS[1]}" = "validate" ]; then
        COMPREPLY=($(compgen -W "$validate_opts" -- "${COMP_WORDS[COMP_CWORD]}"))
    fi
}
complete -F _huskycat_completions huskycat
"""
        (completions_dir / "huskycat.bash").write_text(bash_completion)

        # Zsh completion
        zsh_completion = """#compdef huskycat

_huskycat() {
    local -a commands
    commands=(
        'validate:Run validation on files'
        'install:Install HuskyCat to PATH'
        'setup-hooks:Setup git hooks'
        'update-schemas:Update validation schemas'
        'ci-validate:Validate CI configuration'
        'mcp-server:Start MCP server for Claude'
        'clean:Clean cache and temporary files'
        'status:Show HuskyCat status'
        'autofix:Auto-fix validation issues'
    )

    _arguments -C \
        '1: :->command' \
        '*: :->args'

    case $state in
        command)
            _describe 'command' commands
            ;;
        args)
            case ${words[2]} in
                validate)
                    _arguments \
                        '--staged[Validate staged files only]' \
                        '--all[Validate all files]' \
                        '--fix[Auto-fix issues]' \
                        '--interactive[Interactive mode]' \
                        '--allow-warnings[Allow warnings to pass]' \
                        '*:file:_files'
                    ;;
                install)
                    _arguments \
                        '--bin-dir[Installation directory]:dir:_directories' \
                        '--no-hooks[Skip git hooks setup]' \
                        '--skip-path-check[Skip PATH check]'
                    ;;
            esac
            ;;
    esac
}

_huskycat "$@"
"""
        (completions_dir / "_huskycat").write_text(zsh_completion)

        # Fish completion
        fish_completion = """
complete -c huskycat -n __fish_use_subcommand -a validate -d 'Run validation on files'
complete -c huskycat -n __fish_use_subcommand -a install -d 'Install HuskyCat to PATH'
complete -c huskycat -n __fish_use_subcommand -a setup-hooks -d 'Setup git hooks'
complete -c huskycat -n __fish_use_subcommand -a ci-validate -d 'Validate CI configuration'
complete -c huskycat -n __fish_use_subcommand -a mcp-server -d 'Start MCP server'
complete -c huskycat -n __fish_use_subcommand -a clean -d 'Clean cache'
complete -c huskycat -n __fish_use_subcommand -a status -d 'Show status'

complete -c huskycat -n '__fish_seen_subcommand_from validate' -l staged -d 'Staged files only'
complete -c huskycat -n '__fish_seen_subcommand_from validate' -l all -d 'All files'
complete -c huskycat -n '__fish_seen_subcommand_from validate' -l fix -d 'Auto-fix issues'
"""
        (completions_dir / "huskycat.fish").write_text(fish_completion)

        self.log(f"✓ Shell completions created in {completions_dir}")
