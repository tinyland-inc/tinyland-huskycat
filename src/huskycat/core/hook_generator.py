"""Git hook generation and management for HuskyCat."""

import logging
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class HookGenerator:
    """Generates and manages git hooks for HuskyCat."""

    HOOK_TEMPLATES = {
        "pre-commit": "templates/hooks/pre-commit.template",
        "pre-push": "templates/hooks/pre-push.template",
        "commit-msg": "templates/hooks/commit-msg.template",
    }

    def __init__(self, repo_path: Path, binary_path: Optional[Path] = None):
        """Initialize hook generator.

        Args:
            repo_path: Path to git repository
            binary_path: Path to HuskyCat binary (auto-detected if None)
        """
        self.repo_path = repo_path
        self.binary_path = binary_path or self._detect_binary_path()
        self.hooks_dir = repo_path / ".git" / "hooks"
        self.version = self._get_version()

    def _get_version(self) -> str:
        """Get HuskyCat version."""
        try:
            from .. import __version__

            return __version__
        except ImportError:
            return "2.1.0"

    def _detect_binary_path(self) -> Optional[Path]:
        """Detect HuskyCat binary location with priority ordering.

        Priority:
        1. Running from binary right now (sys.frozen)
        2. Installed in user's bin (~/.local/bin/huskycat)
        3. System PATH (which huskycat)
        4. Common system locations (/usr/local/bin, /usr/bin)

        Returns:
            Path to binary if found, None otherwise
        """
        # Priority 1: Check if running as PyInstaller binary
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            return Path(sys.executable)

        # Priority 2: Check user's bin (most common install location)
        user_bin = Path.home() / ".local" / "bin" / "huskycat"
        if user_bin.exists() and user_bin.is_file():
            return user_bin

        # Priority 3: Check PATH for huskycat command
        try:
            which_result = subprocess.run(
                ["which", "huskycat"], capture_output=True, text=True, check=False, timeout=5
            )
            if which_result.returncode == 0:
                binary_path = Path(which_result.stdout.strip())
                if binary_path.exists() and binary_path.is_file():
                    return binary_path
        except Exception as e:
            logger.debug(f"Error detecting binary in PATH: {e}")

        # Priority 4: Check common system locations
        common_locations = [
            Path("/usr/local/bin/huskycat"),
            Path("/usr/bin/huskycat"),
        ]

        for location in common_locations:
            if location.exists() and location.is_file():
                return location

        # No binary found - hooks will use UV fallback
        return None

    def detect_repo_type(self) -> Dict[str, bool]:
        """Auto-detect repository type and features.

        Returns:
            Dictionary of detected features
        """
        features = {
            "gitlab_ci": (self.repo_path / ".gitlab-ci.yml").exists(),
            "github_actions": (self.repo_path / ".github" / "workflows").is_dir(),
            "helm_chart": any(
                [
                    (self.repo_path / "chart").is_dir(),
                    (self.repo_path / "charts").is_dir(),
                    (self.repo_path / ".helm").is_dir(),
                ]
            ),
            "k8s_manifests": any(
                [
                    (self.repo_path / "k8s").is_dir(),
                    (self.repo_path / "kubernetes").is_dir(),
                    (self.repo_path / "manifests").is_dir(),
                ]
            ),
            "terraform": len(list(self.repo_path.glob("*.tf"))) > 0,
            "ansible": any(
                [
                    (self.repo_path / "playbooks").is_dir(),
                    (self.repo_path / "roles").is_dir(),
                ]
            ),
        }

        # Derived features
        features["gitops"] = self.is_gitops_repo(features)

        return features

    def is_gitops_repo(self, repo_info: Optional[Dict[str, bool]] = None) -> bool:
        """Determine if this is a GitOps repository.

        Args:
            repo_info: Pre-computed repo info (optional)

        Returns:
            True if GitOps repository
        """
        if repo_info is None:
            repo_info = self.detect_repo_type()

        return any(
            [
                repo_info.get("helm_chart", False),
                repo_info.get("k8s_manifests", False),
                repo_info.get("terraform", False),
                repo_info.get("ansible", False),
            ]
        )

    def generate_hook(
        self, hook_name: str, template_vars: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate hook content from template.

        Args:
            hook_name: Name of hook (pre-commit, pre-push, etc.)
            template_vars: Variables to substitute in template

        Returns:
            Generated hook content
        """
        # Find template
        template_relative = self.HOOK_TEMPLATES.get(hook_name)
        if not template_relative:
            raise ValueError(f"Unknown hook: {hook_name}")

        # Template path relative to this file
        template_path = Path(__file__).parent.parent / template_relative

        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        template = template_path.read_text()

        # Default variables
        vars = {
            "VERSION": self.version,
            "BINARY_PATH": str(self.binary_path) if self.binary_path else "",
            "GITOPS_FLAGS": "",
            "GITOPS_AUTODEVOPS": "",
        }

        # Merge user variables
        if template_vars:
            vars.update(template_vars)

        # Simple template substitution
        content = template
        for key, value in vars.items():
            placeholder = "{{" + key + "}}"
            content = content.replace(placeholder, str(value))

        return content

    def install_hook(self, hook_name: str, force: bool = False) -> bool:
        """Install a git hook.

        Args:
            hook_name: Name of hook
            force: Force overwrite if exists

        Returns:
            True if installed, False if skipped
        """
        hook_path = self.hooks_dir / hook_name

        # Check if hook exists
        if hook_path.exists() and not force:
            # Check if it's a HuskyCat-generated hook
            content = hook_path.read_text()
            if "Auto-generated by huskycat" not in content:
                logger.warning(
                    f"Hook {hook_name} already exists (not HuskyCat-generated). "
                    f"Use --force to overwrite."
                )
                return False

        # Detect repo type
        repo_info = self.detect_repo_type()
        is_gitops = repo_info["gitops"]

        # Generate hook content
        template_vars = {}

        # Add GitOps-specific content for pre-push hook
        if hook_name == "pre-push" and is_gitops:
            template_vars["GITOPS_AUTODEVOPS"] = "# GitOps validation enabled"

        content = self.generate_hook(hook_name, template_vars)

        # Ensure hooks directory exists
        self.hooks_dir.mkdir(parents=True, exist_ok=True)

        # Write hook
        hook_path.write_text(content)

        # Make executable
        current_mode = hook_path.stat().st_mode
        hook_path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        logger.info(f"Installed {hook_name} hook")
        return True

    def install_all_hooks(self, force: bool = False) -> int:
        """Install all hooks.

        Args:
            force: Force overwrite existing hooks

        Returns:
            Number of hooks installed
        """
        count = 0
        for hook_name in self.HOOK_TEMPLATES.keys():
            try:
                if self.install_hook(hook_name, force):
                    count += 1
            except Exception as e:
                logger.error(f"Error installing {hook_name}: {e}")

        return count

    def update_hooks(self) -> int:
        """Update existing HuskyCat-generated hooks to latest version.

        Returns:
            Number of hooks updated
        """
        count = 0
        for hook_name in self.HOOK_TEMPLATES.keys():
            hook_path = self.hooks_dir / hook_name

            if not hook_path.exists():
                continue

            # Check if it's a HuskyCat-generated hook
            content = hook_path.read_text()
            if "Auto-generated by huskycat" not in content:
                logger.debug(f"Skipping {hook_name} (not HuskyCat-generated)")
                continue

            # Update it
            try:
                if self.install_hook(hook_name, force=True):
                    count += 1
            except Exception as e:
                logger.error(f"Error updating {hook_name}: {e}")

        return count

    def check_hooks_version(self) -> Optional[str]:
        """Check if hooks need updating.

        Returns:
            Old version string if outdated, None if up-to-date or not found
        """
        hook_path = self.hooks_dir / "pre-commit"

        if not hook_path.exists():
            return None

        content = hook_path.read_text()

        # Check if HuskyCat-generated
        if "Auto-generated by huskycat" not in content:
            return None  # Not our hook

        # Extract version
        match = re.search(r"# Auto-generated by huskycat v([\d.]+)", content)
        if not match:
            return None

        hook_version = match.group(1)

        # Compare versions
        if hook_version != self.version:
            return hook_version  # Outdated

        return None  # Up to date

    def needs_update(self) -> bool:
        """Check if hooks need updating.

        Returns:
            True if hooks are outdated
        """
        return self.check_hooks_version() is not None

    def get_hook_status(self) -> Dict[str, Any]:
        """Get status of all hooks.

        Returns:
            Dictionary with hook status information
        """
        status = {
            "hooks_dir": str(self.hooks_dir),
            "binary_path": str(self.binary_path) if self.binary_path else None,
            "version": self.version,
            "hooks": {},
        }

        for hook_name in self.HOOK_TEMPLATES.keys():
            hook_path = self.hooks_dir / hook_name
            hook_status = {
                "exists": hook_path.exists(),
                "executable": False,
                "huskycat_managed": False,
                "version": None,
            }

            if hook_path.exists():
                # Check executable
                hook_status["executable"] = os.access(hook_path, os.X_OK)

                # Check if HuskyCat-generated
                content = hook_path.read_text()
                if "Auto-generated by huskycat" in content:
                    hook_status["huskycat_managed"] = True

                    # Extract version
                    match = re.search(
                        r"# Auto-generated by huskycat v([\d.]+)", content
                    )
                    if match:
                        hook_status["version"] = match.group(1)

            status["hooks"][hook_name] = hook_status

        return status
