# SPDX-License-Identifier: Apache-2.0
"""
RemoteJuggler integration for HuskyCat.

RemoteJuggler provides git identity management with:
- Multi-provider identity (GitLab/GitHub/Bitbucket)
- SSH host alias switching
- GPG/SSH signing configuration
- macOS Keychain integration
- MCP server with 8 tools

This module provides:
1. CLI wrapper for RemoteJuggler commands
2. MCP tool proxying for unified tool exposure
3. Pre-commit hook identity detection

Configuration:
    ~/.huskycat/integrations/remote-juggler.yaml

Example:
    integration = RemoteJugglerIntegration()
    if integration.is_available():
        identity = integration.detect_identity("/path/to/repo")
"""

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Default configuration path
CONFIG_DIR = Path.home() / ".huskycat" / "integrations"
CONFIG_FILE = CONFIG_DIR / "remote-juggler.yaml"


@dataclass
class IdentityResult:
    """Result of identity detection."""

    provider: str  # gitlab, github, bitbucket
    username: str
    email: str
    signing_key: Optional[str] = None
    ssh_host: Optional[str] = None
    confidence: float = 1.0
    matched_by: str = "explicit"  # explicit, remote, config


@dataclass
class RemoteJugglerConfig:
    """Configuration for RemoteJuggler integration."""

    enabled: bool = True
    binary_path: Optional[str] = None
    integration_mode: str = "cli"  # cli, mcp, config
    auto_detect_identity: bool = True
    warn_on_mismatch: bool = True
    auto_switch: bool = False
    validate_gpg: bool = True
    validate_credentials: bool = True
    proxy_mcp_tools: bool = True
    tool_prefix: str = "juggler_"

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "RemoteJugglerConfig":
        """Load configuration from YAML file."""
        config_path = path or CONFIG_FILE
        if config_path.exists():
            try:
                data = yaml.safe_load(config_path.read_text())
                # Extract nested configuration
                hooks = data.get("hooks", {})
                pre_commit = hooks.get("pre_commit", {})
                pre_push = hooks.get("pre_push", {})
                mcp = data.get("mcp", {})

                return cls(
                    enabled=data.get("enabled", True),
                    binary_path=data.get("binary_path"),
                    integration_mode=data.get("integration_mode", "cli"),
                    auto_detect_identity=pre_commit.get("detect_identity", True),
                    warn_on_mismatch=pre_commit.get("warn_on_mismatch", True),
                    auto_switch=pre_commit.get("auto_switch", False),
                    validate_gpg=pre_push.get("validate_gpg", True),
                    validate_credentials=pre_push.get("validate_credentials", True),
                    proxy_mcp_tools=mcp.get("proxy_tools", True),
                    tool_prefix=mcp.get("tool_prefix", "juggler_"),
                )
            except Exception:
                pass
        return cls()

    def save(self, path: Optional[Path] = None) -> None:
        """Save configuration to YAML file."""
        config_path = path or CONFIG_FILE
        config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0",
            "enabled": self.enabled,
            "binary_path": self.binary_path,
            "integration_mode": self.integration_mode,
            "hooks": {
                "pre_commit": {
                    "detect_identity": self.auto_detect_identity,
                    "warn_on_mismatch": self.warn_on_mismatch,
                    "auto_switch": self.auto_switch,
                },
                "pre_push": {
                    "validate_gpg": self.validate_gpg,
                    "validate_credentials": self.validate_credentials,
                },
            },
            "mcp": {
                "proxy_tools": self.proxy_mcp_tools,
                "tool_prefix": self.tool_prefix,
            },
        }
        config_path.write_text(yaml.safe_dump(data, default_flow_style=False))


def is_remote_juggler_available() -> bool:
    """Check if RemoteJuggler binary is available."""
    return shutil.which("remote-juggler") is not None


class RemoteJugglerIntegration:
    """Integration layer for RemoteJuggler."""

    # RemoteJuggler MCP tools that can be proxied
    MCP_TOOLS = [
        "juggler_list_identities",
        "juggler_detect_identity",
        "juggler_switch",
        "juggler_status",
        "juggler_validate",
        "juggler_store_token",
        "juggler_sync_config",
        "juggler_gpg_status",
    ]

    def __init__(self, config: Optional[RemoteJugglerConfig] = None):
        """Initialize the integration."""
        self.config = config or RemoteJugglerConfig.load()
        self._binary_path: Optional[str] = None

    def is_available(self) -> bool:
        """Check if RemoteJuggler is available and enabled."""
        if not self.config.enabled:
            return False
        return self._find_binary() is not None

    def _find_binary(self) -> Optional[str]:
        """Find the RemoteJuggler binary path."""
        if self._binary_path:
            return self._binary_path

        # Check configured path first
        if self.config.binary_path:
            path = Path(self.config.binary_path).expanduser()
            if path.exists():
                self._binary_path = str(path)
                return self._binary_path

        # Check PATH
        binary = shutil.which("remote-juggler")
        if binary:
            self._binary_path = binary
            return self._binary_path

        # Check common locations
        common_paths = [
            Path.home() / ".local" / "bin" / "remote-juggler",
            Path("/usr/local/bin/remote-juggler"),
            Path("/opt/homebrew/bin/remote-juggler"),
        ]
        for path in common_paths:
            if path.exists():
                self._binary_path = str(path)
                return self._binary_path

        return None

    def _run_command(
        self,
        args: List[str],
        capture_output: bool = True,
        json_output: bool = False,
    ) -> subprocess.CompletedProcess:
        """Run a RemoteJuggler command."""
        binary = self._find_binary()
        if not binary:
            raise RuntimeError("RemoteJuggler binary not found")

        cmd = [binary] + args
        if json_output:
            cmd.append("--json")

        return subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            timeout=30,
        )

    def detect_identity(self, repo_path: str = ".") -> Optional[IdentityResult]:
        """Detect the appropriate identity for a repository."""
        if not self.is_available():
            return None

        try:
            result = self._run_command(
                ["detect", repo_path],
                json_output=True,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return IdentityResult(
                    provider=data.get("provider", "unknown"),
                    username=data.get("username", ""),
                    email=data.get("email", ""),
                    signing_key=data.get("signing_key"),
                    ssh_host=data.get("ssh_host"),
                    confidence=data.get("confidence", 1.0),
                    matched_by=data.get("matched_by", "explicit"),
                )
        except Exception:
            pass
        return None

    def list_identities(self) -> List[Dict[str, Any]]:
        """List all configured identities."""
        if not self.is_available():
            return []

        try:
            result = self._run_command(["list"], json_output=True)
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception:
            pass
        return []

    def switch_identity(self, identity_name: str) -> bool:
        """Switch to a different identity."""
        if not self.is_available():
            return False

        try:
            result = self._run_command(["switch", identity_name])
            return result.returncode == 0
        except Exception:
            return False

    def get_status(self) -> Optional[Dict[str, Any]]:
        """Get current identity status."""
        if not self.is_available():
            return None

        try:
            result = self._run_command(["status"], json_output=True)
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception:
            pass
        return None

    def validate_credentials(self) -> Dict[str, bool]:
        """Validate SSH/API credentials for current identity."""
        if not self.is_available():
            return {"available": False}

        try:
            result = self._run_command(["validate"], json_output=True)
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception:
            pass
        return {"valid": False}

    def get_gpg_status(self) -> Optional[Dict[str, Any]]:
        """Get GPG signing status."""
        if not self.is_available():
            return None

        try:
            result = self._run_command(["gpg-status"], json_output=True)
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception:
            pass
        return None

    # MCP Tool Proxying

    def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Get MCP tool definitions for proxying."""
        if not self.config.proxy_mcp_tools or not self.is_available():
            return []

        prefix = self.config.tool_prefix
        return [
            {
                "name": f"{prefix}list_identities",
                "description": "List all configured git identities",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": f"{prefix}detect_identity",
                "description": "Detect the appropriate identity for a repository",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repo_path": {
                            "type": "string",
                            "description": "Path to repository (default: current directory)",
                        }
                    },
                },
            },
            {
                "name": f"{prefix}switch",
                "description": "Switch to a different git identity",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "identity": {
                            "type": "string",
                            "description": "Identity name to switch to",
                        }
                    },
                    "required": ["identity"],
                },
            },
            {
                "name": f"{prefix}status",
                "description": "Get current git identity status",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": f"{prefix}validate",
                "description": "Validate SSH/API credentials for current identity",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": f"{prefix}gpg_status",
                "description": "Get GPG signing status for current identity",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

    def handle_mcp_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle an MCP tool call by proxying to RemoteJuggler."""
        prefix = self.config.tool_prefix

        if tool_name == f"{prefix}list_identities":
            identities = self.list_identities()
            return {"identities": identities}

        elif tool_name == f"{prefix}detect_identity":
            repo_path = arguments.get("repo_path", ".")
            result = self.detect_identity(repo_path)
            if result:
                return {
                    "provider": result.provider,
                    "username": result.username,
                    "email": result.email,
                    "signing_key": result.signing_key,
                    "ssh_host": result.ssh_host,
                    "confidence": result.confidence,
                    "matched_by": result.matched_by,
                }
            return {"error": "Could not detect identity"}

        elif tool_name == f"{prefix}switch":
            identity = arguments.get("identity", "")
            success = self.switch_identity(identity)
            return {"success": success, "identity": identity}

        elif tool_name == f"{prefix}status":
            status = self.get_status()
            return status or {"error": "Could not get status"}

        elif tool_name == f"{prefix}validate":
            result = self.validate_credentials()
            return result

        elif tool_name == f"{prefix}gpg_status":
            status = self.get_gpg_status()
            return status or {"error": "Could not get GPG status"}

        return {"error": f"Unknown tool: {tool_name}"}

    # Hook Integration

    def pre_commit_check(self, repo_path: str = ".") -> Dict[str, Any]:
        """
        Pre-commit hook check for identity mismatch.

        Returns dict with:
        - ok: bool - whether to proceed with commit
        - warning: Optional[str] - warning message if mismatch
        - detected: Optional[IdentityResult] - detected identity
        - current: Optional[dict] - current git config identity
        """
        if not self.config.auto_detect_identity:
            return {"ok": True}

        detected = self.detect_identity(repo_path)
        if not detected:
            return {"ok": True, "warning": "Could not detect identity"}

        # Get current git config
        try:
            name_result = subprocess.run(
                ["git", "config", "user.name"],
                capture_output=True,
                text=True,
                cwd=repo_path,
            )
            email_result = subprocess.run(
                ["git", "config", "user.email"],
                capture_output=True,
                text=True,
                cwd=repo_path,
            )
            current = {
                "name": name_result.stdout.strip(),
                "email": email_result.stdout.strip(),
            }
        except Exception:
            return {"ok": True, "warning": "Could not read git config"}

        # Check for mismatch
        if current["email"] != detected.email:
            warning = (
                f"Identity mismatch: git config has {current['email']} "
                f"but repository expects {detected.email} ({detected.provider})"
            )

            if self.config.auto_switch:
                # Attempt to switch
                # This would require knowing the identity name
                pass

            if self.config.warn_on_mismatch:
                return {
                    "ok": True,  # Allow commit but warn
                    "warning": warning,
                    "detected": detected,
                    "current": current,
                }

        return {"ok": True, "detected": detected, "current": current}

    def pre_push_check(self, repo_path: str = ".") -> Dict[str, Any]:
        """
        Pre-push hook check for GPG and credentials.

        Returns dict with:
        - ok: bool - whether to proceed with push
        - errors: List[str] - blocking errors
        - warnings: List[str] - non-blocking warnings
        """
        errors = []
        warnings = []

        if self.config.validate_gpg:
            gpg_status = self.get_gpg_status()
            if gpg_status and not gpg_status.get("ready", True):
                warnings.append(
                    f"GPG signing not ready: {gpg_status.get('message', 'unknown')}"
                )

        if self.config.validate_credentials:
            cred_status = self.validate_credentials()
            if not cred_status.get("valid", True):
                errors.append(
                    f"Credentials invalid: {cred_status.get('message', 'unknown')}"
                )

        return {
            "ok": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }


def create_default_config() -> None:
    """Create default configuration file if it doesn't exist."""
    if not CONFIG_FILE.exists():
        config = RemoteJugglerConfig()
        config.save()
