#!/usr/bin/env python3
"""
Demonstration of ParallelExecutor for HuskyCat validation tools.

Shows execution plan, statistics, and simulated tool execution.
"""

import time
from typing import Dict

from huskycat.core.parallel_executor import (
    TOOL_DEPENDENCIES,
    ParallelExecutor,
    ToolResult,
)


def simulate_tool_execution(tool_name: str, fail: bool = False) -> ToolResult:
    """Simulate a tool execution with realistic timing."""
    # Simulate tool execution time
    duration = 0.05 + (hash(tool_name) % 10) * 0.01  # 0.05-0.15s
    time.sleep(duration)

    return ToolResult(
        tool_name=tool_name,
        success=not fail,
        duration=duration,
        errors=5 if fail else 0,
        warnings=2 if not fail else 0,
        output=f"{tool_name} validation output",
    )


def main():
    """Demonstrate parallel executor capabilities."""
    print("=" * 70)
    print("HuskyCat Parallel Executor Demonstration")
    print("=" * 70)
    print()

    # Initialize executor with default HuskyCat tool dependencies
    executor = ParallelExecutor()

    # Show dependency visualization
    print(executor.visualize_dependencies())
    print()

    # Show execution statistics
    stats = executor.get_statistics()
    print("Execution Statistics:")
    print("-" * 70)
    print(f"Total tools:           {stats['total_tools']}")
    print(f"Execution levels:      {stats['total_levels']}")
    print(f"Max parallelism:       {stats['max_parallelism']} tools concurrently")
    print(f"Average parallelism:   {stats['avg_parallelism']:.2f} tools per level")
    print(
        f"Sequential time est:   {stats['sequential_time_estimate']:.1f}s (if run serially)"
    )
    print(
        f"Parallel time est:     {stats['parallel_time_estimate']:.1f}s (with parallelism)"
    )
    print(f"Speedup factor:        {stats['speedup_factor']:.2f}x faster")
    print()

    # Show execution plan
    plan = executor.get_execution_plan()
    print("Execution Plan:")
    print("-" * 70)
    for level_idx, tools in plan:
        tool_count = len(tools)
        print(
            f"Level {level_idx}: {tool_count} tool{'s' if tool_count != 1 else ''} "
            f"(parallel execution)"
        )
        for tool in sorted(tools):
            deps = TOOL_DEPENDENCIES[tool]
            if deps:
                print(f"  - {tool:20s} depends on: {', '.join(deps)}")
            else:
                print(f"  - {tool:20s} (no dependencies)")
        print()

    # Simulate actual execution with progress tracking
    print("Simulating Tool Execution:")
    print("-" * 70)

    progress_updates = []

    def progress_callback(tool_name: str, status: str):
        """Track progress updates."""
        timestamp = time.time()
        progress_updates.append((timestamp, tool_name, status))
        status_icon = {"running": "⚙", "success": "✓", "failed": "✗"}.get(status, "•")
        print(f"  {status_icon} {tool_name:20s} {status}")

    # Create tool callables (all successful for demo)
    tools: Dict[str, callable] = {
        tool_name: lambda tn=tool_name: simulate_tool_execution(tn)
        for tool_name in TOOL_DEPENDENCIES.keys()
    }

    # Execute all tools
    start_time = time.time()
    results = executor.execute_tools(tools, progress_callback=progress_callback)
    total_duration = time.time() - start_time

    print()
    print("Execution Results:")
    print("-" * 70)

    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful
    total_errors = sum(r.errors for r in results)
    total_warnings = sum(r.warnings for r in results)

    print(f"Total tools executed:  {len(results)}")
    print(f"Successful:            {successful}")
    print(f"Failed:                {failed}")
    print(f"Total errors:          {total_errors}")
    print(f"Total warnings:        {total_warnings}")
    print(f"Total execution time:  {total_duration:.2f}s")
    print()

    # Show per-tool results
    print("Per-Tool Results:")
    print("-" * 70)
    print(f"{'Tool':<20} {'Status':<10} {'Duration':<10} {'Errors':<8} {'Warnings':<8}")
    print("-" * 70)

    for result in sorted(results, key=lambda r: r.tool_name):
        status = "SUCCESS" if result.success else "FAILED"
        print(
            f"{result.tool_name:<20} {status:<10} "
            f"{result.duration:.3f}s     {result.errors:<8} {result.warnings:<8}"
        )

    print()
    print("=" * 70)
    print("Demonstration Complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
