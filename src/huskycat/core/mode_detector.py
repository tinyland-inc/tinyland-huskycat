"""
Product Mode Detection for HuskyCat.

HuskyCat operates in 5 distinct product modes, each with different:
- Performance requirements
- Output formats
- Interactivity expectations
- Error handling strategies
- Tool availability assumptions

This module provides automatic mode detection and explicit override support.
"""

import os
import sys
from enum import Enum
from typing import Optional


class ProductMode(Enum):
    """The five product modes HuskyCat operates in."""

    GIT_HOOKS = "git_hooks"  # Pre-commit/pre-push validation
    CI = "ci"  # Pipeline integration for MR/PR checks
    CLI = "cli"  # Developer running validation manually
    PIPELINE = "pipeline"  # Part of larger toolchain (stdin/stdout)
    MCP = "mcp"  # AI assistant integration (Claude Code)


def detect_mode(override: Optional[str] = None) -> ProductMode:
    """
    Auto-detect product mode from environment.

    Detection priority:
    1. Explicit override parameter
    2. HUSKYCAT_MODE environment variable
    3. MCP server command detection
    4. Git hooks environment variables
    5. CI environment variables
    6. TTY/pipe detection for Pipeline mode
    7. Default to CLI mode

    Args:
        override: Explicit mode override (takes priority)

    Returns:
        ProductMode enum value
    """
    # 1. Explicit override parameter
    if override:
        try:
            return ProductMode(override.lower())
        except ValueError:
            pass

    # 2. Environment variable override
    env_mode = os.environ.get("HUSKYCAT_MODE", "").lower()
    if env_mode:
        try:
            return ProductMode(env_mode)
        except ValueError:
            pass

    # 3. MCP mode: invoked with mcp-server command
    if _is_mcp_invocation():
        return ProductMode.MCP

    # 4. Git hooks: GIT_* environment variables present
    if _is_git_hooks_context():
        return ProductMode.GIT_HOOKS

    # 5. CI mode: CI environment variables
    if _is_ci_context():
        return ProductMode.CI

    # 6. Pipeline mode: no TTY or piped input
    if _is_pipeline_context():
        return ProductMode.PIPELINE

    # 7. Default: CLI mode (interactive terminal)
    return ProductMode.CLI


def _is_mcp_invocation() -> bool:
    """Check if invoked as MCP server."""
    return any(arg in sys.argv for arg in ["mcp-server", "mcp", "--mcp"])


def _is_git_hooks_context() -> bool:
    """Check if running in git hooks context."""
    git_env_vars = [
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
        "GIT_INDEX_FILE",
        "GIT_DIR",
        "GIT_EXEC_PATH",
    ]
    # Need at least 2 GIT_ variables to be confident
    git_vars_present = sum(1 for var in git_env_vars if os.environ.get(var))
    return git_vars_present >= 2


def _is_ci_context() -> bool:
    """Check if running in CI environment."""
    ci_env_vars = [
        "CI",
        "GITLAB_CI",
        "GITHUB_ACTIONS",
        "JENKINS_URL",
        "TRAVIS",
        "CIRCLECI",
        "BITBUCKET_PIPELINES",
        "AZURE_PIPELINES",
        "TEAMCITY_VERSION",
        "BUILDKITE",
    ]
    return any(os.environ.get(var) for var in ci_env_vars)


def _is_pipeline_context() -> bool:
    """Check if running in pipeline/scripted context."""
    # Not a TTY means likely piped/scripted
    stdin_is_pipe = not sys.stdin.isatty()
    stdout_is_pipe = not sys.stdout.isatty()

    # If both stdin and stdout are pipes, definitely pipeline mode
    if stdin_is_pipe and stdout_is_pipe:
        return True

    # If output is being piped (e.g., huskycat validate | jq)
    if stdout_is_pipe and not stdin_is_pipe:
        return True

    return False


def get_mode_description(mode: ProductMode) -> str:
    """Get human-readable description of a mode."""
    descriptions = {
        ProductMode.GIT_HOOKS: "Git Hooks - Pre-commit/pre-push validation with fast feedback",
        ProductMode.CI: "CI - Pipeline integration with structured reports (JUnit XML, JSON)",
        ProductMode.CLI: "CLI - Interactive terminal with rich colored output",
        ProductMode.PIPELINE: "Pipeline - Machine-readable JSON output for toolchain integration",
        ProductMode.MCP: "MCP - AI assistant integration via JSON-RPC stdio protocol",
    }
    return descriptions.get(mode, f"Unknown mode: {mode}")


def get_adapter(mode: ProductMode, use_nonblocking: bool = False) -> "ModeAdapter":
    """
    Get the adapter instance for a given mode.

    Args:
        mode: The ProductMode to get an adapter for
        use_nonblocking: Use non-blocking adapter for git hooks (feature flag)

    Returns:
        ModeAdapter instance configured for the mode
    """
    from .adapters import (
        GitHooksAdapter,
        CIAdapter,
        CLIAdapter,
        PipelineAdapter,
        MCPAdapter,
    )

    # Check for non-blocking git hooks feature flag
    if mode == ProductMode.GIT_HOOKS and use_nonblocking:
        from .adapters.git_hooks_nonblocking import NonBlockingGitHooksAdapter

        return NonBlockingGitHooksAdapter()

    adapters = {
        ProductMode.GIT_HOOKS: GitHooksAdapter,
        ProductMode.CI: CIAdapter,
        ProductMode.CLI: CLIAdapter,
        ProductMode.PIPELINE: PipelineAdapter,
        ProductMode.MCP: MCPAdapter,
    }

    adapter_class = adapters.get(mode, CLIAdapter)
    return adapter_class()


# For quick debugging
if __name__ == "__main__":
    detected = detect_mode()
    print(f"Detected mode: {detected.value}")
    print(f"Description: {get_mode_description(detected)}")
    print(f"\nEnvironment hints:")
    print(f"  stdin.isatty(): {sys.stdin.isatty()}")
    print(f"  stdout.isatty(): {sys.stdout.isatty()}")
    print(f"  CI env: {_is_ci_context()}")
    print(f"  Git hooks env: {_is_git_hooks_context()}")
    print(f"  sys.argv: {sys.argv}")
