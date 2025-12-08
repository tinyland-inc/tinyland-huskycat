"""
Parallel tool executor with intelligent dependency graph management.

Executes validation tools in parallel while respecting dependencies,
maximizing throughput by running independent tools concurrently.
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import networkx as nx


class ToolStatus(Enum):
    """Status of tool execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass
class ToolResult:
    """Result from a tool execution."""

    tool_name: str
    success: bool
    duration: float
    errors: int = 0
    warnings: int = 0
    output: str = ""
    status: ToolStatus = ToolStatus.SUCCESS
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Ensure status matches success flag."""
        if not self.success and self.status == ToolStatus.SUCCESS:
            self.status = ToolStatus.FAILED


# Default tool dependency graph
# Tools with no dependencies can run immediately and in parallel
# Tools with dependencies must wait for their prerequisites to complete
TOOL_DEPENDENCIES: Dict[str, List[str]] = {
    # Python tools
    "black": [],  # Formatter - no dependencies, can run first
    "isort": [],  # Import sorter - independent of black
    "autoflake": [],  # Remove unused imports - independent
    "ruff": [],  # Fast linter - independent
    "mypy": ["black", "isort"],  # Type checker - better after formatting
    "flake8": ["black", "isort"],  # Style checker - better after formatting
    "bandit": ["black"],  # Security scanner - analyze after formatting
    # YAML/Config tools
    "yamllint": [],  # YAML validation - independent
    "taplo": [],  # TOML formatter - independent
    "gitlab-ci": ["yamllint"],  # GitLab CI validator - needs valid YAML
    # Shell/Docker tools
    "shellcheck": [],  # Shell script linter - independent
    "hadolint": [],  # Dockerfile linter - independent
    # Infrastructure tools
    "ansible-lint": ["yamllint"],  # Ansible playbook linter - needs valid YAML
    "helm-lint": ["yamllint"],  # Helm chart linter - needs valid YAML
    # Chapel tools (if applicable)
    "chapel-format": [],  # Chapel formatter - independent
}


class ParallelExecutor:
    """
    Execute validation tools in parallel respecting dependency constraints.

    Uses a directed acyclic graph (DAG) to determine execution order
    and runs independent tools concurrently using ThreadPoolExecutor.
    """

    def __init__(
        self,
        tool_dependencies: Optional[Dict[str, List[str]]] = None,
        max_workers: Optional[int] = None,
        timeout_per_tool: float = 30.0,
        fail_fast: bool = False,
    ) -> None:
        """
        Initialize the parallel executor.

        Args:
            tool_dependencies: Dict mapping tool names to their dependencies
            max_workers: Maximum parallel workers (default: CPU count - 1)
            timeout_per_tool: Maximum seconds per tool execution
            fail_fast: Stop on first critical failure if True
        """
        self.dependencies = tool_dependencies or TOOL_DEPENDENCIES
        self.max_workers = max_workers or max(1, os.cpu_count() - 1)
        self.timeout_per_tool = timeout_per_tool
        self.fail_fast = fail_fast
        self.graph = self._build_graph()

    def _build_graph(self) -> nx.DiGraph:
        """
        Build directed acyclic graph from tool dependencies.

        Returns:
            NetworkX directed graph representing dependencies

        Raises:
            ValueError: If circular dependencies detected
        """
        graph = nx.DiGraph()

        # Add all tools as nodes
        for tool in self.dependencies:
            graph.add_node(tool)

        # Add edges from dependencies to tools
        for tool, deps in self.dependencies.items():
            for dep in deps:
                if dep not in self.dependencies:
                    raise ValueError(
                        f"Tool '{tool}' depends on unknown tool '{dep}'"
                    )
                graph.add_edge(dep, tool)  # dep must run before tool

        # Verify no circular dependencies
        if not nx.is_directed_acyclic_graph(graph):
            cycles = list(nx.simple_cycles(graph))
            raise ValueError(f"Circular dependencies detected: {cycles}")

        return graph

    def _get_execution_order(self) -> List[List[str]]:
        """
        Get tools grouped by execution level using topological sort.

        Tools in the same level have no dependencies on each other
        and can be executed in parallel.

        Returns:
            List of lists, where each inner list contains tools
            that can run in parallel.

            Example: [
                ['black', 'ruff', 'isort'],      # Level 0: no deps
                ['mypy', 'flake8', 'bandit'],    # Level 1: depend on level 0
            ]
        """
        levels: List[List[str]] = []
        remaining_tools = set(self.dependencies.keys())
        completed_tools: Set[str] = set()

        while remaining_tools:
            # Find all tools whose dependencies are satisfied
            current_level = []
            for tool in remaining_tools:
                deps = self.dependencies[tool]
                if all(dep in completed_tools for dep in deps):
                    current_level.append(tool)

            if not current_level:
                # Should never happen with valid DAG, but catch it
                raise ValueError(
                    f"Cannot satisfy dependencies for remaining tools: {remaining_tools}"
                )

            levels.append(current_level)
            completed_tools.update(current_level)
            remaining_tools -= set(current_level)

        return levels

    def _execute_tool_with_timeout(
        self,
        tool_name: str,
        tool_callable: Callable[[], Any],
        progress_callback: Optional[Callable[[str, str], None]] = None,
    ) -> ToolResult:
        """
        Execute a single tool with timeout handling.

        Args:
            tool_name: Name of the tool
            tool_callable: Callable that executes the tool
            progress_callback: Optional callback(tool_name, status)

        Returns:
            ToolResult with execution details
        """
        if progress_callback:
            progress_callback(tool_name, "running")

        start_time = time.time()

        try:
            # Execute tool (tool_callable should handle its own validation)
            result = tool_callable()
            duration = time.time() - start_time

            # Convert result to ToolResult if not already
            if isinstance(result, ToolResult):
                tool_result = result
                tool_result.duration = duration
            else:
                # Assume callable returns success boolean or dict
                if isinstance(result, dict):
                    tool_result = ToolResult(
                        tool_name=tool_name,
                        success=result.get("success", True),
                        duration=duration,
                        errors=result.get("errors", 0),
                        warnings=result.get("warnings", 0),
                        output=result.get("output", ""),
                        metadata=result.get("metadata", {}),
                    )
                else:
                    tool_result = ToolResult(
                        tool_name=tool_name,
                        success=bool(result),
                        duration=duration,
                    )

            if progress_callback:
                status = "success" if tool_result.success else "failed"
                progress_callback(tool_name, status)

            return tool_result

        except TimeoutError:
            duration = time.time() - start_time
            if progress_callback:
                progress_callback(tool_name, "timeout")

            return ToolResult(
                tool_name=tool_name,
                success=False,
                duration=duration,
                status=ToolStatus.TIMEOUT,
                error_message=f"Tool exceeded timeout of {self.timeout_per_tool}s",
            )

        except Exception as e:
            duration = time.time() - start_time
            if progress_callback:
                progress_callback(tool_name, "failed")

            return ToolResult(
                tool_name=tool_name,
                success=False,
                duration=duration,
                status=ToolStatus.FAILED,
                error_message=str(e),
            )

    def _execute_level(
        self,
        tool_names: List[str],
        tools: Dict[str, Callable[[], Any]],
        progress_callback: Optional[Callable[[str, str], None]] = None,
    ) -> List[ToolResult]:
        """
        Execute a level of tools in parallel.

        Args:
            tool_names: List of tool names to execute
            tools: Dict mapping tool names to callables
            progress_callback: Optional callback for progress updates

        Returns:
            List of ToolResult for each tool in this level
        """
        results: List[ToolResult] = []

        # Filter to only tools that exist in the tools dict
        available_tools = [t for t in tool_names if t in tools]

        if not available_tools:
            # No tools to run at this level
            return results

        # Execute tools in parallel using ThreadPoolExecutor
        workers = min(len(available_tools), self.max_workers)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit all tools in this level
            future_to_tool = {
                executor.submit(
                    self._execute_tool_with_timeout,
                    tool_name,
                    tools[tool_name],
                    progress_callback,
                ): tool_name
                for tool_name in available_tools
            }

            # Collect results as they complete
            for future in as_completed(future_to_tool):
                tool_name = future_to_tool[future]
                try:
                    result = future.result(timeout=self.timeout_per_tool)
                    results.append(result)
                except TimeoutError:
                    results.append(
                        ToolResult(
                            tool_name=tool_name,
                            success=False,
                            duration=self.timeout_per_tool,
                            status=ToolStatus.TIMEOUT,
                            error_message=f"Tool exceeded timeout of {self.timeout_per_tool}s",
                        )
                    )
                except Exception as e:
                    results.append(
                        ToolResult(
                            tool_name=tool_name,
                            success=False,
                            duration=0.0,
                            status=ToolStatus.FAILED,
                            error_message=f"Executor error: {e!s}",
                        )
                    )

        return results

    def execute_tools(
        self,
        tools: Dict[str, Callable[[], Any]],
        progress_callback: Optional[Callable[[str, str], None]] = None,
    ) -> List[ToolResult]:
        """
        Execute tools in parallel respecting dependencies.

        Args:
            tools: Dict mapping tool names to callables
            progress_callback: Optional callback(tool_name, status) for progress

        Returns:
            List of ToolResult for each tool executed

        Example:
            >>> tools = {
            ...     "black": lambda: validate_black(),
            ...     "mypy": lambda: validate_mypy(),
            ... }
            >>> executor = ParallelExecutor()
            >>> results = executor.execute_tools(tools)
        """
        # Get execution levels from topological sort
        levels = self._get_execution_order()

        all_results: List[ToolResult] = []
        failed_tools: Set[str] = set()

        # Execute each level in sequence
        for level_idx, level in enumerate(levels):
            # Skip tools whose dependencies failed
            tools_to_run = [
                tool
                for tool in level
                if not any(dep in failed_tools for dep in self.dependencies[tool])
            ]

            # Mark skipped tools
            skipped_tools = set(level) - set(tools_to_run)
            for tool in skipped_tools:
                all_results.append(
                    ToolResult(
                        tool_name=tool,
                        success=False,
                        duration=0.0,
                        status=ToolStatus.SKIPPED,
                        error_message="Skipped due to failed dependencies",
                    )
                )

            # Execute tools within level in parallel
            level_results = self._execute_level(
                tools_to_run, tools, progress_callback
            )
            all_results.extend(level_results)

            # Track failures for dependency skipping
            failed_tools.update(
                result.tool_name for result in level_results if not result.success
            )

            # Fast-fail if requested and critical failure occurred
            if self.fail_fast and failed_tools:
                # Mark remaining tools as skipped
                remaining_tools = [
                    tool for level in levels[level_idx + 1 :] for tool in level
                ]
                for tool in remaining_tools:
                    all_results.append(
                        ToolResult(
                            tool_name=tool,
                            success=False,
                            duration=0.0,
                            status=ToolStatus.SKIPPED,
                            error_message="Skipped due to fail-fast mode",
                        )
                    )
                break

        return all_results

    def get_execution_plan(self) -> List[Tuple[int, List[str]]]:
        """
        Get the execution plan without running tools.

        Returns:
            List of (level_number, tool_names) tuples showing
            parallel execution groups

        Example:
            >>> executor = ParallelExecutor()
            >>> plan = executor.get_execution_plan()
            >>> for level, tools in plan:
            ...     print(f"Level {level}: {', '.join(tools)}")
        """
        levels = self._get_execution_order()
        return list(enumerate(levels))

    def visualize_dependencies(self) -> str:
        """
        Generate a text visualization of the dependency graph.

        Returns:
            String representation of the dependency structure
        """
        levels = self._get_execution_order()
        lines = ["Tool Dependency Execution Plan:", "=" * 50]

        for level_idx, level_tools in enumerate(levels):
            lines.append(f"\nLevel {level_idx} (parallel execution):")
            for tool in sorted(level_tools):
                deps = self.dependencies[tool]
                if deps:
                    deps_str = ", ".join(sorted(deps))
                    lines.append(f"  - {tool} (depends on: {deps_str})")
                else:
                    lines.append(f"  - {tool} (no dependencies)")

        lines.append("\n" + "=" * 50)
        return "\n".join(lines)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the execution plan.

        Returns:
            Dict with execution statistics
        """
        levels = self._get_execution_order()

        return {
            "total_tools": len(self.dependencies),
            "total_levels": len(levels),
            "max_parallelism": max(len(level) for level in levels) if levels else 0,
            "avg_parallelism": (
                sum(len(level) for level in levels) / len(levels) if levels else 0
            ),
            "sequential_time_estimate": len(self.dependencies) * self.timeout_per_tool,
            "parallel_time_estimate": len(levels) * self.timeout_per_tool,
            "speedup_factor": (
                len(self.dependencies) / len(levels) if levels else 1.0
            ),
        }
