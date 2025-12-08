#!/usr/bin/env python3
"""
Verification script for ParallelExecutor implementation.

Demonstrates all key features and validates correctness.
"""

import sys
import time
from typing import List

from huskycat.core.parallel_executor import (
    TOOL_DEPENDENCIES,
    ParallelExecutor,
    ToolResult,
    ToolStatus,
)


def verify_dependency_graph() -> bool:
    """Verify dependency graph is valid DAG."""
    print("1. Verifying Dependency Graph...")

    try:
        executor = ParallelExecutor()
        print(f"   ✓ Graph built successfully ({len(executor.graph.nodes)} nodes)")

        # Check for cycles
        import networkx as nx

        if not nx.is_directed_acyclic_graph(executor.graph):
            print("   ✗ Graph contains cycles!")
            return False

        print("   ✓ No circular dependencies detected")
        return True

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def verify_execution_order() -> bool:
    """Verify execution order is correct."""
    print("\n2. Verifying Execution Order...")

    executor = ParallelExecutor()
    levels = executor._get_execution_order()

    print(f"   ✓ {len(levels)} execution levels generated")

    # Verify all tools are included
    all_tools = {tool for level in levels for tool in level}
    expected_tools = set(TOOL_DEPENDENCIES.keys())

    if all_tools != expected_tools:
        print(f"   ✗ Missing tools: {expected_tools - all_tools}")
        return False

    print(f"   ✓ All {len(all_tools)} tools scheduled")

    # Verify dependencies are satisfied
    completed = set()
    for level_idx, level in enumerate(levels):
        for tool in level:
            deps = TOOL_DEPENDENCIES[tool]
            if not all(dep in completed for dep in deps):
                unsatisfied = [d for d in deps if d not in completed]
                print(
                    f"   ✗ Tool '{tool}' in level {level_idx} has "
                    f"unsatisfied dependencies: {unsatisfied}"
                )
                return False
        completed.update(level)

    print("   ✓ All dependencies satisfied")
    return True


def verify_parallel_execution() -> bool:
    """Verify tools actually execute in parallel."""
    print("\n3. Verifying Parallel Execution...")

    execution_times = []

    def make_timed_tool(name: str, sleep_time: float = 0.1):
        def tool():
            start = time.time()
            time.sleep(sleep_time)
            duration = time.time() - start
            execution_times.append((name, start, duration))
            return ToolResult(tool_name=name, success=True, duration=duration)

        return tool

    # Three independent tools that should run in parallel
    deps = {"tool_a": [], "tool_b": [], "tool_c": []}
    executor = ParallelExecutor(tool_dependencies=deps, max_workers=3)

    tools = {
        "tool_a": make_timed_tool("tool_a"),
        "tool_b": make_timed_tool("tool_b"),
        "tool_c": make_timed_tool("tool_c"),
    }

    start = time.time()
    results = executor.execute_tools(tools)
    total_duration = time.time() - start

    # Check results
    if len(results) != 3:
        print(f"   ✗ Expected 3 results, got {len(results)}")
        return False

    if not all(r.success for r in results):
        print("   ✗ Some tools failed")
        return False

    # Verify parallel execution (should take ~0.1s, not ~0.3s)
    if total_duration > 0.25:
        print(f"   ✗ Execution too slow: {total_duration:.2f}s (expected <0.25s)")
        return False

    print(f"   ✓ Parallel execution confirmed ({total_duration:.2f}s for 3 tools)")
    return True


def verify_dependency_enforcement() -> bool:
    """Verify dependencies are enforced."""
    print("\n4. Verifying Dependency Enforcement...")

    execution_order: List[str] = []

    def make_ordering_tool(name: str):
        def tool():
            execution_order.append(name)
            time.sleep(0.01)
            return ToolResult(tool_name=name, success=True, duration=0.01)

        return tool

    deps = {
        "first": [],
        "second": ["first"],
        "third": ["second"],
    }

    executor = ParallelExecutor(tool_dependencies=deps)
    tools = {
        "first": make_ordering_tool("first"),
        "second": make_ordering_tool("second"),
        "third": make_ordering_tool("third"),
    }

    results = executor.execute_tools(tools)

    # Verify order
    if execution_order.index("first") > execution_order.index("second"):
        print(f"   ✗ Order violation: {execution_order}")
        return False

    if execution_order.index("second") > execution_order.index("third"):
        print(f"   ✗ Order violation: {execution_order}")
        return False

    print(f"   ✓ Dependencies enforced: {' → '.join(execution_order)}")
    return True


def verify_failure_handling() -> bool:
    """Verify failure handling and skipping."""
    print("\n5. Verifying Failure Handling...")

    def failing_tool():
        return ToolResult(
            tool_name="base", success=False, duration=0.01, error_message="Failed"
        )

    def success_tool():
        return ToolResult(tool_name="dependent", success=True, duration=0.01)

    deps = {
        "base": [],
        "dependent": ["base"],
    }

    executor = ParallelExecutor(tool_dependencies=deps)
    tools = {
        "base": failing_tool,
        "dependent": success_tool,
    }

    results = executor.execute_tools(tools)

    # Find results
    base_result = next(r for r in results if r.tool_name == "base")
    dependent_result = next(r for r in results if r.tool_name == "dependent")

    if base_result.success:
        print("   ✗ Base tool should have failed")
        return False

    if dependent_result.status != ToolStatus.SKIPPED:
        print(f"   ✗ Dependent should be skipped, got: {dependent_result.status}")
        return False

    print("   ✓ Failed dependencies trigger skipping")
    return True


def verify_progress_callbacks() -> bool:
    """Verify progress callbacks work."""
    print("\n6. Verifying Progress Callbacks...")

    progress_updates = []

    def callback(tool_name: str, status: str):
        progress_updates.append((tool_name, status))

    deps = {"tool_a": [], "tool_b": []}
    executor = ParallelExecutor(tool_dependencies=deps)

    tools = {
        "tool_a": lambda: ToolResult(tool_name="tool_a", success=True, duration=0.01),
        "tool_b": lambda: ToolResult(tool_name="tool_b", success=True, duration=0.01),
    }

    executor.execute_tools(tools, progress_callback=callback)

    # Verify callbacks were invoked
    tool_names = {update[0] for update in progress_updates}
    if "tool_a" not in tool_names or "tool_b" not in tool_names:
        print("   ✗ Not all tools reported progress")
        return False

    statuses = {update[1] for update in progress_updates}
    if "running" not in statuses:
        print("   ✗ Missing 'running' status updates")
        return False

    print(f"   ✓ Progress callbacks working ({len(progress_updates)} updates)")
    return True


def verify_statistics() -> bool:
    """Verify statistics generation."""
    print("\n7. Verifying Statistics...")

    executor = ParallelExecutor()
    stats = executor.get_statistics()

    required_keys = [
        "total_tools",
        "total_levels",
        "max_parallelism",
        "avg_parallelism",
        "speedup_factor",
    ]

    for key in required_keys:
        if key not in stats:
            print(f"   ✗ Missing statistic: {key}")
            return False

    if stats["speedup_factor"] < 1.0:
        print(f"   ✗ Invalid speedup factor: {stats['speedup_factor']}")
        return False

    print(f"   ✓ Statistics generated (speedup: {stats['speedup_factor']:.2f}x)")
    return True


def verify_huskycat_tools() -> bool:
    """Verify HuskyCat default tool configuration."""
    print("\n8. Verifying HuskyCat Tool Configuration...")

    executor = ParallelExecutor()

    # Check critical dependencies
    critical_checks = [
        ("mypy", "black", "mypy should depend on black"),
        ("flake8", "black", "flake8 should depend on black"),
        ("gitlab-ci", "yamllint", "gitlab-ci should depend on yamllint"),
    ]

    for tool, dependency, message in critical_checks:
        if tool in TOOL_DEPENDENCIES:
            if dependency not in TOOL_DEPENDENCIES[tool]:
                print(f"   ✗ {message}")
                return False

    stats = executor.get_statistics()

    # Verify reasonable parallelism
    if stats["max_parallelism"] < 5:
        print(f"   ✗ Low parallelism: {stats['max_parallelism']}")
        return False

    if stats["speedup_factor"] < 2.0:
        print(f"   ✗ Low speedup: {stats['speedup_factor']:.2f}x")
        return False

    print(f"   ✓ HuskyCat tools configured correctly")
    print(f"     - {stats['total_tools']} tools")
    print(f"     - {stats['max_parallelism']} max parallel")
    print(f"     - {stats['speedup_factor']:.2f}x speedup")
    return True


def main():
    """Run all verification tests."""
    print("=" * 70)
    print("ParallelExecutor Verification Suite")
    print("=" * 70)

    tests = [
        ("Dependency Graph", verify_dependency_graph),
        ("Execution Order", verify_execution_order),
        ("Parallel Execution", verify_parallel_execution),
        ("Dependency Enforcement", verify_dependency_enforcement),
        ("Failure Handling", verify_failure_handling),
        ("Progress Callbacks", verify_progress_callbacks),
        ("Statistics", verify_statistics),
        ("HuskyCat Tools", verify_huskycat_tools),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n   ✗ Exception: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 70)
    print("Verification Summary")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:10} {name}")

    print("=" * 70)
    print(f"Result: {passed}/{total} tests passed")
    print("=" * 70)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
