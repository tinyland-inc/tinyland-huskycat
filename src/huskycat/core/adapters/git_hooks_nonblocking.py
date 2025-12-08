"""
Non-Blocking Git Hooks Mode Adapter.

This adapter provides non-blocking validation for git hooks that:
- Returns immediately to git (<100ms) to avoid blocking the commit
- Forks validation to a background process
- Shows real-time progress via TUI in the background
- Runs ALL validation tools (15+), not just fast subset
- Checks previous run results to prevent committing with known failures
- Provides user prompts when previous validation failed

Architecture:
    Parent Process (git hook):
        1. Check previous run status
        2. Fork child process for validation
        3. Return immediately to git (commit proceeds)
        4. Exit 0 (always allows commit unless previous failure)

    Child Process (background):
        1. Initialize TUI with all tools
        2. Execute tools in parallel via ParallelExecutor
        3. Show real-time progress to user
        4. Save results to cache
        5. Exit with validation status

Integration:
    - ProcessManager: Fork/PID management, result caching
    - ValidationTUI: Real-time progress display
    - ParallelExecutor: Parallel tool execution with dependencies
"""

import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

from .base import AdapterConfig, ModeAdapter, OutputFormat
from ..process_manager import ProcessManager, should_proceed_with_commit
from ..tui import ValidationTUI, ToolState
from ..parallel_executor import ParallelExecutor, ToolResult


class NonBlockingGitHooksAdapter(ModeAdapter):
    """
    Adapter for non-blocking git hooks validation.

    Key Features:
    - Parent process returns <100ms
    - Child runs comprehensive validation (15+ tools)
    - Real-time TUI progress display
    - Previous failure handling with user prompts
    - Result caching for subsequent commits
    - Zombie process cleanup

    Performance Targets:
    - Parent return time: <100ms
    - Child startup overhead: <200ms
    - Full validation: 10-30s (15+ tools in parallel)
    - Speedup vs sequential: ~7.5x
    """

    def __init__(self, cache_dir: Path = None):
        """
        Initialize the non-blocking adapter.

        Args:
            cache_dir: Directory for validation run cache (default: .huskycat/runs)
        """
        self.process_manager = ProcessManager(cache_dir)
        self.tui = ValidationTUI(refresh_rate=0.1)
        self.executor = ParallelExecutor(max_workers=8, fail_fast=False)

    @property
    def name(self) -> str:
        return "git_hooks_nonblocking"

    @property
    def config(self) -> AdapterConfig:
        """
        Return adapter configuration.

        Note: Unlike blocking git_hooks adapter, this runs ALL tools
        and shows progress, but does so in a background process.
        """
        is_interactive = sys.stdin.isatty() and sys.stdout.isatty()

        return AdapterConfig(
            output_format=OutputFormat.MINIMAL,  # Parent has minimal output
            interactive=is_interactive,  # For previous failure prompts
            fail_fast=False,  # Run all tools in background
            color=sys.stdout.isatty(),  # Auto-detect color support
            progress=True,  # Enable TUI in child process
            tools="all",  # ALL validation tools, not "fast"
        )

    def execute_validation(self, files: List[str], tools: Dict[str, Callable]) -> int:
        """
        Execute non-blocking validation workflow.

        This is the main entry point for git hooks. It:
        1. Checks previous validation results
        2. Forks to background process
        3. Returns immediately to allow commit

        Args:
            files: List of file paths to validate
            tools: Dict mapping tool names to validation callables

        Returns:
            PID of child process (parent returns this)
            Does not return in child process (calls sys.exit)
        """
        # Step 1: Check previous run status
        if not should_proceed_with_commit(self.process_manager.cache_dir):
            # User declined to proceed with previous failure
            print("Aborting commit due to previous validation failure.")
            print("Fix issues and try again, or override with --no-verify")
            sys.exit(1)

        # Step 2: Cleanup any zombie processes from previous runs
        self.process_manager.cleanup_zombies()

        # Step 3: Fork validation process
        # We pass a lambda that calls our child validation method
        pid = self.process_manager.fork_validation(
            files=files,
            validation_cmd=self._run_validation_child_wrapper,
            validation_args=[files, tools],
        )

        # Step 4: Parent returns immediately
        # The commit proceeds while validation runs in background
        return pid

    def _run_validation_child_wrapper(self, files: List[str], tools: Dict[str, Callable]):
        """
        Wrapper to bridge ProcessManager's string command interface to our method.

        The ProcessManager expects validation_cmd to be a string command,
        but we need to call a Python method. This wrapper handles the transition.

        Args:
            files: List of file paths to validate
            tools: Dict mapping tool names to validation callables
        """
        # This runs in the forked child process
        self._run_validation_child(files, tools)

    def _run_validation_child(self, files: List[str], tools: Dict[str, Callable]):
        """
        Run comprehensive validation in forked child process.

        This method runs in the background and:
        1. Initializes TUI with all tools
        2. Sets up progress callbacks
        3. Executes tools in parallel via ParallelExecutor
        4. Displays real-time progress
        5. Saves results to cache
        6. Exits with appropriate code

        Args:
            files: List of file paths to validate
            tools: Dict mapping tool names to validation callables
        """
        tool_names = list(tools.keys())

        # Start TUI (only if TTY available)
        self.tui.start(tool_names)

        print(f"Starting non-blocking validation of {len(files)} files...")
        print(f"Tools: {', '.join(tool_names)}")
        print("-" * 60)

        # Progress callback for ParallelExecutor
        def on_progress(tool_name: str, status: str, errors: int = 0, warnings: int = 0):
            """Update TUI when tool status changes."""
            # Map status string to ToolState enum
            status_map = {
                "pending": ToolState.PENDING,
                "running": ToolState.RUNNING,
                "success": ToolState.SUCCESS,
                "failed": ToolState.FAILED,
                "skipped": ToolState.SKIPPED,
            }
            tool_state = status_map.get(status, ToolState.RUNNING)

            # Update TUI
            self.tui.update_tool(
                tool_name=tool_name,
                state=tool_state,
                errors=errors,
                warnings=warnings,
            )

            # Also print to log for non-TTY fallback
            if tool_state == ToolState.SUCCESS:
                print(f"  OK  {tool_name}")
            elif tool_state == ToolState.FAILED:
                print(f"  FAIL {tool_name} ({errors} errors, {warnings} warnings)")

        # Execute all tools in parallel with dependency management
        try:
            results: List[ToolResult] = self.executor.execute_tools(
                tools=tools, progress_callback=on_progress
            )
        except Exception as e:
            print(f"FATAL: Validation executor failed: {e}")
            import traceback

            traceback.print_exc()
            self.tui.stop()
            sys.exit(1)

        # Stop TUI
        self.tui.stop()

        # Calculate aggregate results
        total_errors = sum(r.errors for r in results)
        total_warnings = sum(r.warnings for r in results)
        all_success = all(r.success for r in results)
        failed_tools = [r.tool_name for r in results if not r.success]

        print("-" * 60)
        print(f"Validation complete:")
        print(f"  Files:    {len(files)}")
        print(f"  Tools:    {len(results)} / {len(tool_names)}")
        print(f"  Errors:   {total_errors}")
        print(f"  Warnings: {total_warnings}")
        print(f"  Status:   {'PASS' if all_success else 'FAIL'}")

        if failed_tools:
            print(f"  Failed tools: {', '.join(failed_tools)}")

        # Save validation run results
        from datetime import datetime
        from ..process_manager import ValidationRun

        run = ValidationRun(
            run_id=datetime.now().isoformat(),
            started=datetime.now().isoformat(),
            completed=datetime.now().isoformat(),
            files=files,
            success=all_success,
            tools_run=tool_names,
            errors=total_errors,
            warnings=total_warnings,
            exit_code=0 if all_success else 1,
            pid=None,  # Will be set by ProcessManager
        )

        self.process_manager.save_run(run)

        # Exit with appropriate code
        exit_code = 0 if all_success else 1
        print(f"\nExiting with code {exit_code}")
        sys.exit(exit_code)

    def format_output(self, results: Dict[str, Any], summary: Dict[str, Any]) -> str:
        """
        Format validation output for git hooks.

        In non-blocking mode, the parent process has minimal output
        (just the background PID message). The child process handles
        all validation output and logging.

        Args:
            results: Per-file validation results (unused in non-blocking)
            summary: Aggregated summary statistics (unused in non-blocking)

        Returns:
            Empty string (output handled by child process)
        """
        # Parent process output is handled in execute_validation()
        # Child process output is handled in _run_validation_child()
        return ""

    def get_all_validation_tools(self, files: List[str]) -> Dict[str, Callable]:
        """
        Load ALL available validation tools for given files.

        This is a placeholder that should be populated by the
        command implementation. Returns tools based on file types.

        Args:
            files: List of file paths to validate

        Returns:
            Dict mapping tool names to validation callables
        """
        # This will be populated by the validate command
        # based on file extensions and configuration
        tools = {}

        # Python tools
        if any(f.endswith(".py") for f in files):
            tools.update(
                {
                    "black": lambda: self._placeholder_tool("black", files),
                    "ruff": lambda: self._placeholder_tool("ruff", files),
                    "mypy": lambda: self._placeholder_tool("mypy", files),
                    "flake8": lambda: self._placeholder_tool("flake8", files),
                    "isort": lambda: self._placeholder_tool("isort", files),
                    "bandit": lambda: self._placeholder_tool("bandit", files),
                }
            )

        # YAML/Config tools
        yaml_files = [f for f in files if f.endswith((".yml", ".yaml"))]
        if yaml_files:
            tools.update(
                {
                    "yamllint": lambda: self._placeholder_tool("yamllint", yaml_files),
                    "gitlab-ci": lambda: self._placeholder_tool("gitlab-ci", yaml_files),
                }
            )

        # TOML tools
        if any(f.endswith(".toml") for f in files):
            tools["taplo"] = lambda: self._placeholder_tool("taplo", files)

        # Shell tools
        if any(f.endswith((".sh", ".bash")) for f in files):
            tools["shellcheck"] = lambda: self._placeholder_tool("shellcheck", files)

        # Docker tools
        if any("Dockerfile" in f or f.endswith(".dockerfile") for f in files):
            tools["hadolint"] = lambda: self._placeholder_tool("hadolint", files)

        # Chapel tools
        if any(f.endswith(".chpl") for f in files):
            tools["chapel-format"] = lambda: self._placeholder_tool("chapel-format", files)

        return tools

    def _placeholder_tool(self, tool_name: str, files: List[str]) -> ToolResult:
        """
        Placeholder tool implementation for demonstration.

        In production, this would call the actual validation tool.
        The real implementation would be provided by the unified_validation
        module or validate command.

        Args:
            tool_name: Name of the tool
            files: List of files to validate

        Returns:
            ToolResult with validation results
        """
        # Placeholder - actual implementation would call real tools
        import time

        time.sleep(0.5)  # Simulate tool execution

        return ToolResult(
            tool_name=tool_name,
            success=True,
            duration=0.5,
            errors=0,
            warnings=0,
            output=f"Validated {len(files)} files with {tool_name}",
        )
