#!/usr/bin/env python3
"""
Performance comparison: Sequential vs Parallel execution.

Demonstrates the performance benefits of parallel execution.
"""

import time
from typing import Callable, Dict

from huskycat.core.parallel_executor import (
    TOOL_DEPENDENCIES,
    ParallelExecutor,
    ToolResult,
)


def simulate_validation_tool(tool_name: str, complexity: float = 1.0) -> ToolResult:
    """
    Simulate a validation tool with realistic timing.

    Args:
        tool_name: Name of the tool
        complexity: Complexity multiplier (1.0 = baseline)
    """
    # Simulate different tool execution times
    base_times = {
        "black": 0.15,
        "isort": 0.12,
        "ruff": 0.08,
        "mypy": 0.25,
        "flake8": 0.18,
        "bandit": 0.14,
        "yamllint": 0.10,
        "taplo": 0.08,
        "shellcheck": 0.09,
        "hadolint": 0.11,
        "gitlab-ci": 0.13,
        "ansible-lint": 0.16,
        "helm-lint": 0.17,
        "autoflake": 0.10,
        "chapel-format": 0.12,
    }

    duration = base_times.get(tool_name, 0.10) * complexity
    time.sleep(duration)

    return ToolResult(
        tool_name=tool_name,
        success=True,
        duration=duration,
        errors=0,
        warnings=2,
    )


def sequential_execution(tools: Dict[str, Callable]) -> tuple[list, float]:
    """Execute tools sequentially (one at a time)."""
    results = []
    start = time.time()

    for tool_name, tool_func in tools.items():
        result = tool_func()
        results.append(result)

    total_time = time.time() - start
    return results, total_time


def parallel_execution(tools: Dict[str, Callable]) -> tuple[list, float]:
    """Execute tools in parallel using ParallelExecutor."""
    executor = ParallelExecutor()
    start = time.time()

    results = executor.execute_tools(tools)

    total_time = time.time() - start
    return results, total_time


def main():
    """Run performance comparison."""
    print("=" * 70)
    print("Performance Comparison: Sequential vs Parallel Execution")
    print("=" * 70)
    print()

    # Create tool callables
    tools: Dict[str, Callable] = {
        tool_name: lambda tn=tool_name: simulate_validation_tool(tn)
        for tool_name in TOOL_DEPENDENCIES.keys()
    }

    print(f"Testing with {len(tools)} validation tools...")
    print()

    # Sequential execution
    print("Running SEQUENTIAL execution...")
    seq_results, seq_time = sequential_execution(tools)
    print(f"  Completed in {seq_time:.2f} seconds")
    print()

    # Parallel execution
    print("Running PARALLEL execution...")
    par_results, par_time = parallel_execution(tools)
    print(f"  Completed in {par_time:.2f} seconds")
    print()

    # Calculate speedup
    speedup = seq_time / par_time

    print("=" * 70)
    print("Results")
    print("=" * 70)
    print()
    print(f"Sequential Execution:  {seq_time:.2f}s")
    print(f"Parallel Execution:    {par_time:.2f}s")
    print(f"Time Saved:            {seq_time - par_time:.2f}s ({(1 - par_time/seq_time) * 100:.1f}%)")
    print(f"Speedup Factor:        {speedup:.2f}x faster")
    print()

    # Tool-by-tool breakdown
    print("Tool Execution Times:")
    print("-" * 70)
    print(f"{'Tool':<20} {'Duration':<12} {'Notes':<30}")
    print("-" * 70)

    for result in sorted(seq_results, key=lambda r: r.duration, reverse=True):
        deps = TOOL_DEPENDENCIES.get(result.tool_name, [])
        note = f"Depends on: {', '.join(deps)}" if deps else "Independent"
        print(f"{result.tool_name:<20} {result.duration:.3f}s       {note}")

    print()

    # Execution plan
    executor = ParallelExecutor()
    stats = executor.get_statistics()

    print("Parallel Execution Strategy:")
    print("-" * 70)
    print(f"Execution Levels:      {stats['total_levels']}")
    print(f"Max Parallelism:       {stats['max_parallelism']} tools concurrently")
    print(f"Average Parallelism:   {stats['avg_parallelism']:.2f} tools per level")
    print()

    # Show execution levels
    levels = executor._get_execution_order()
    for level_idx, level_tools in enumerate(levels):
        print(f"Level {level_idx}: {len(level_tools)} tools (run in parallel)")
        for tool in sorted(level_tools):
            print(f"  - {tool}")
        print()

    print("=" * 70)
    print(f"Conclusion: Parallel execution is {speedup:.2f}x faster!")
    print("=" * 70)


if __name__ == "__main__":
    main()
