"""
Git Hooks Mode Adapter.

Optimized for pre-commit/pre-push hooks:
- Fast execution (only essential tools)
- Minimal output (errors only)
- Fail-fast behavior
- Auto-detect TTY for interactive prompts
"""

import sys

from .base import AdapterConfig, ModeAdapter, OutputFormat


class GitHooksAdapter(ModeAdapter):
    """
    Adapter for Git Hooks mode.

    Requirements:
    - Speed: Must complete in <5s for good DX
    - Staged files only: Usually --staged flag
    - Silent success: No output on pass
    - Loud failure: Clear, actionable errors
    - Exit codes: 0=pass, 1=fail (blocks commit)
    """

    @property
    def name(self) -> str:
        return "git_hooks"

    @property
    def config(self) -> AdapterConfig:
        # Auto-detect if we have a TTY for interactive prompts
        is_interactive = sys.stdin.isatty() and sys.stdout.isatty()

        return AdapterConfig(
            output_format=OutputFormat.MINIMAL,
            interactive=is_interactive,  # Auto-detect TTY
            fail_fast=True,  # Stop on first error for speed
            color=sys.stdout.isatty(),  # Auto-detect color support
            progress=False,  # No progress bars in hooks
            tools="fast",  # Only fast tools (black, ruff, mypy)
        )

    def format_output(self, results, summary):
        """
        Git hooks: Silent on success, errors only on failure.
        """
        total_errors = summary.get("total_errors", 0)

        if total_errors == 0:
            # Silent success for git hooks
            return ""

        # Show only errors, no warnings, no summary
        return super()._format_minimal(results, summary)
