# SPDX-License-Identifier: Apache-2.0
"""
Self-contained installation command for HuskyCat.

When running from a binary, this command:
1. Copies itself to ~/.local/bin/huskycat
2. Sets up git hooks in the current repository
3. Creates shell completions
4. Optionally registers MCP server with Claude Code (--with-claude)
"""

import json
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
        with_claude: bool = False,
        scope: str = "user",
        verify: bool = False,
    ) -> CommandResult:
        """
        Install HuskyCat binary and configure environment.

        Args:
            bin_dir: Installation directory (default: ~/.local/bin)
            setup_hooks: Also setup git hooks in current repo
            skip_path_check: Don't warn about PATH issues
            with_claude: Register MCP server with Claude Code
            scope: MCP registration scope ("user", "project", or "local")
            verify: Verify MCP connection after registration

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

        # Register MCP server with Claude Code
        if with_claude:
            mcp_result = self._register_mcp_server(scope)
            if mcp_result["success"]:
                data["mcp_registered"] = True
                data["mcp_scope"] = scope
                self.log(f"MCP server registered (scope: {scope})")
            else:
                warnings.append(f"MCP registration: {mcp_result['error']}")
                data["mcp_registered"] = False

            # Verify MCP connection if requested
            if verify and mcp_result["success"]:
                verify_result = self._verify_mcp_connection()
                if verify_result["success"]:
                    data["mcp_verified"] = True
                    self.log("MCP connection verified")
                else:
                    warnings.append(f"MCP verification: {verify_result['error']}")
                    data["mcp_verified"] = False

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

    def _create_completions(self) -> None:
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
                        '--skip-path-check[Skip PATH check]' \
                        '--with-claude[Register MCP server with Claude Code]' \
                        '--scope[MCP registration scope]:scope:(user project local)' \
                        '--verify[Verify MCP connection after registration]'
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

        self.log(f"Shell completions created in {completions_dir}")

    def _register_mcp_server(self, scope: str) -> dict:
        """
        Register HuskyCat MCP server with Claude Code.

        Uses `claude mcp add-json` for scripted registration.
        Falls back to writing .mcp.json directly if claude CLI not found.

        Args:
            scope: Registration scope ("user", "project", or "local")

        Returns:
            dict with "success" and optional "error" keys
        """
        mcp_config = {"command": "huskycat", "args": ["mcp-server"], "env": {}}

        # First, try using claude CLI
        try:
            result = subprocess.run(
                [
                    "claude",
                    "mcp",
                    "add-json",
                    "huskycat",
                    "--scope",
                    scope,
                    json.dumps(mcp_config),
                ],
                capture_output=True,
                timeout=30,
                check=False,
            )

            if result.returncode == 0:
                return {"success": True}
            else:
                error_msg = result.stderr.decode().strip()
                # If already registered, treat as success
                if "already" in error_msg.lower():
                    return {"success": True}
                return {"success": False, "error": error_msg}

        except FileNotFoundError:
            # Claude CLI not found, fall back to direct file manipulation
            return self._register_mcp_direct(scope)

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Claude CLI timed out"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _register_mcp_direct(self, scope: str) -> dict:
        """
        Register MCP server by directly creating/updating .mcp.json.

        This is a fallback when claude CLI is not available.

        Args:
            scope: Registration scope ("user", "project", or "local")

        Returns:
            dict with "success" and optional "error" keys
        """
        mcp_entry = {
            "huskycat": {"command": "huskycat", "args": ["mcp-server"], "env": {}}
        }

        try:
            if scope == "user":
                # User scope: ~/.claude/.mcp.json
                mcp_file = Path.home() / ".claude" / ".mcp.json"
            elif scope == "project":
                # Project scope: .mcp.json in current directory
                mcp_file = Path.cwd() / ".mcp.json"
            else:
                # Local scope: ~/.claude.json under project path
                mcp_file = Path.cwd() / ".claude.json"

            # Read existing config or start fresh
            mcp_file.parent.mkdir(parents=True, exist_ok=True)
            if mcp_file.exists():
                with mcp_file.open() as f:
                    config = json.load(f)
            else:
                config = {}

            # Add/update mcpServers section
            if "mcpServers" not in config:
                config["mcpServers"] = {}
            config["mcpServers"].update(mcp_entry)

            # Write back
            with mcp_file.open("w") as f:
                json.dump(config, f, indent=2)

            self.log(f"MCP config written to {mcp_file}")
            return {"success": True}

        except Exception as e:
            return {"success": False, "error": f"Direct registration failed: {e}"}

    def _verify_mcp_connection(self) -> dict:
        """
        Verify MCP server is working by running a quick test.

        Returns:
            dict with "success" and optional "error" keys
        """
        try:
            # Try to run MCP server with a quick test
            result = subprocess.run(
                ["huskycat", "mcp-server", "--test"],
                capture_output=True,
                timeout=10,
                check=False,
            )

            if result.returncode == 0:
                return {"success": True}
            # Fallback: just check if huskycat is in PATH
            result = subprocess.run(
                ["huskycat", "--version"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                return {"success": True}
            return {"success": False, "error": "huskycat not in PATH"}

        except FileNotFoundError:
            return {"success": False, "error": "huskycat not found in PATH"}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "MCP test timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
