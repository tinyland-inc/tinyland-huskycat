"""
Tests for parallel tool executor with dependency graph.
"""

import time
from typing import Any, Dict

import pytest

from src.huskycat.core.parallel_executor import (
    TOOL_DEPENDENCIES,
    ParallelExecutor,
    ToolResult,
    ToolStatus,
)


class TestDependencyGraph:
    """Test dependency graph construction and validation."""

    def test_build_graph_no_cycles(self):
        """Verify default dependencies form valid DAG."""
        executor = ParallelExecutor()
        assert executor.graph is not None
        assert len(executor.graph.nodes) == len(TOOL_DEPENDENCIES)

    def test_circular_dependency_detection(self):
        """Verify circular dependencies are detected."""
        circular_deps = {
            "tool_a": ["tool_b"],
            "tool_b": ["tool_c"],
            "tool_c": ["tool_a"],  # Creates cycle
        }

        with pytest.raises(ValueError, match="Circular dependencies"):
            ParallelExecutor(tool_dependencies=circular_deps)

    def test_unknown_dependency_detection(self):
        """Verify unknown dependencies are detected."""
        bad_deps = {
            "tool_a": ["unknown_tool"],
        }

        with pytest.raises(ValueError, match="unknown tool"):
            ParallelExecutor(tool_dependencies=bad_deps)

    def test_execution_order_levels(self):
        """Verify tools are grouped into correct execution levels."""
        simple_deps = {
            "formatter": [],
            "linter": ["formatter"],
            "type_checker": ["formatter"],
            "final": ["linter", "type_checker"],
        }

        executor = ParallelExecutor(tool_dependencies=simple_deps)
        levels = executor._get_execution_order()

        # Level 0: formatter only
        assert levels[0] == ["formatter"]

        # Level 1: linter and type_checker (parallel)
        assert set(levels[1]) == {"linter", "type_checker"}

        # Level 2: final
        assert levels[2] == ["final"]

    def test_default_dependencies_structure(self):
        """Verify default tool dependencies are well-structured."""
        executor = ParallelExecutor()
        levels = executor._get_execution_order()

        # Level 0 should contain tools with no dependencies
        level_0_tools = set(levels[0])
        for tool in level_0_tools:
            assert TOOL_DEPENDENCIES[tool] == []

        # All tools should be included
        all_tools_in_levels = {tool for level in levels for tool in level}
        assert all_tools_in_levels == set(TOOL_DEPENDENCIES.keys())


class TestParallelExecution:
    """Test parallel tool execution."""

    def test_execute_simple_tools(self):
        """Test execution of tools with no dependencies."""
        call_count = {"a": 0, "b": 0, "c": 0}

        def make_tool(name: str):
            def tool():
                call_count[name] += 1
                return ToolResult(
                    tool_name=name, success=True, duration=0.01, errors=0, warnings=0
                )

            return tool

        deps = {
            "a": [],
            "b": [],
            "c": [],
        }

        executor = ParallelExecutor(tool_dependencies=deps)
        tools = {
            "a": make_tool("a"),
            "b": make_tool("b"),
            "c": make_tool("c"),
        }

        results = executor.execute_tools(tools)

        # All tools should execute
        assert len(results) == 3
        assert all(r.success for r in results)
        assert call_count == {"a": 1, "b": 1, "c": 1}

    def test_execute_with_dependencies(self):
        """Test execution respects dependencies."""
        execution_order = []

        def make_tool(name: str, sleep_time: float = 0.01):
            def tool():
                execution_order.append(name)
                time.sleep(sleep_time)
                return ToolResult(
                    tool_name=name, success=True, duration=sleep_time, errors=0
                )

            return tool

        deps = {
            "first": [],
            "second": ["first"],
            "third": ["second"],
        }

        executor = ParallelExecutor(tool_dependencies=deps)
        tools = {
            "first": make_tool("first"),
            "second": make_tool("second"),
            "third": make_tool("third"),
        }

        results = executor.execute_tools(tools)

        # Verify execution order
        assert execution_order.index("first") < execution_order.index("second")
        assert execution_order.index("second") < execution_order.index("third")
        assert all(r.success for r in results)

    def test_parallel_execution_performance(self):
        """Verify parallel execution is faster than sequential."""

        def slow_tool():
            time.sleep(0.1)
            return ToolResult(tool_name="tool", success=True, duration=0.1)

        # Three independent tools
        deps = {
            "tool_a": [],
            "tool_b": [],
            "tool_c": [],
        }

        executor = ParallelExecutor(tool_dependencies=deps, max_workers=3)
        tools = {
            "tool_a": slow_tool,
            "tool_b": slow_tool,
            "tool_c": slow_tool,
        }

        start = time.time()
        results = executor.execute_tools(tools)
        duration = time.time() - start

        # Should take ~0.1s (parallel), not ~0.3s (sequential)
        assert duration < 0.25  # Some overhead allowed
        assert all(r.success for r in results)

    def test_progress_callback(self):
        """Verify progress callback is invoked."""
        progress_updates = []

        def callback(tool_name: str, status: str):
            progress_updates.append((tool_name, status))

        deps = {"tool_a": [], "tool_b": []}

        executor = ParallelExecutor(tool_dependencies=deps)
        tools = {
            "tool_a": lambda: ToolResult(
                tool_name="tool_a", success=True, duration=0.01
            ),
            "tool_b": lambda: ToolResult(
                tool_name="tool_b", success=True, duration=0.01
            ),
        }

        executor.execute_tools(tools, progress_callback=callback)

        # Should have running and success/failed for each tool
        tool_names = {update[0] for update in progress_updates}
        assert "tool_a" in tool_names
        assert "tool_b" in tool_names

        # Each tool should have at least a running status
        statuses = [update[1] for update in progress_updates]
        assert "running" in statuses


class TestFailureHandling:
    """Test failure scenarios and error handling."""

    def test_failed_tool_result(self):
        """Test handling of failed tool execution."""

        def failing_tool():
            return ToolResult(
                tool_name="fail_tool",
                success=False,
                duration=0.01,
                errors=5,
                error_message="Validation failed",
            )

        deps = {"fail_tool": []}
        executor = ParallelExecutor(tool_dependencies=deps)
        tools = {"fail_tool": failing_tool}

        results = executor.execute_tools(tools)

        assert len(results) == 1
        assert not results[0].success
        assert results[0].errors == 5

    def test_dependency_skip_on_failure(self):
        """Test dependent tools are skipped when dependency fails."""

        def failing_tool():
            return ToolResult(
                tool_name="base",
                success=False,
                duration=0.01,
                error_message="Failed",
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

        # Base should fail, dependent should be skipped
        base_result = next(r for r in results if r.tool_name == "base")
        dependent_result = next(r for r in results if r.tool_name == "dependent")

        assert not base_result.success
        assert dependent_result.status == ToolStatus.SKIPPED

    def test_fail_fast_mode(self):
        """Test fail-fast mode stops on first failure."""
        execution_count = {"count": 0}

        def counting_tool(name: str, should_fail: bool = False):
            def tool():
                execution_count["count"] += 1
                return ToolResult(
                    tool_name=name, success=not should_fail, duration=0.01
                )

            return tool

        deps = {
            "level0_fail": [],
            "level0_success": [],
            "level1_a": ["level0_fail"],
            "level1_b": ["level0_success"],
        }

        executor = ParallelExecutor(tool_dependencies=deps, fail_fast=True)
        tools = {
            "level0_fail": counting_tool("level0_fail", should_fail=True),
            "level0_success": counting_tool("level0_success"),
            "level1_a": counting_tool("level1_a"),
            "level1_b": counting_tool("level1_b"),
        }

        results = executor.execute_tools(tools)

        # Should execute level 0 but stop before level 1
        assert execution_count["count"] == 2  # Only level 0 tools
        assert any(r.status == ToolStatus.SKIPPED for r in results)

    def test_exception_handling(self):
        """Test handling of exceptions during tool execution."""

        def exception_tool():
            raise RuntimeError("Tool crashed")

        deps = {"crash_tool": []}
        executor = ParallelExecutor(tool_dependencies=deps)
        tools = {"crash_tool": exception_tool}

        results = executor.execute_tools(tools)

        assert len(results) == 1
        assert not results[0].success
        assert results[0].status == ToolStatus.FAILED
        assert "Tool crashed" in results[0].error_message


class TestExecutionPlan:
    """Test execution plan generation and visualization."""

    def test_get_execution_plan(self):
        """Test execution plan generation."""
        deps = {
            "a": [],
            "b": [],
            "c": ["a", "b"],
        }

        executor = ParallelExecutor(tool_dependencies=deps)
        plan = executor.get_execution_plan()

        assert len(plan) == 2
        # Level 0 should have a and b (order doesn't matter)
        assert plan[0][0] == 0
        assert set(plan[0][1]) == {"a", "b"}
        # Level 1 should have c
        assert plan[1] == (1, ["c"])

    def test_visualize_dependencies(self):
        """Test dependency visualization."""
        deps = {
            "formatter": [],
            "linter": ["formatter"],
        }

        executor = ParallelExecutor(tool_dependencies=deps)
        viz = executor.visualize_dependencies()

        assert "formatter" in viz
        assert "linter" in viz
        assert "Level 0" in viz
        assert "Level 1" in viz

    def test_get_statistics(self):
        """Test execution statistics."""
        deps = {
            "a": [],
            "b": [],
            "c": ["a", "b"],
            "d": ["c"],
        }

        executor = ParallelExecutor(tool_dependencies=deps)
        stats = executor.get_statistics()

        assert stats["total_tools"] == 4
        assert stats["total_levels"] == 3
        assert stats["max_parallelism"] == 2
        assert stats["speedup_factor"] > 1.0


class TestRealWorldScenario:
    """Test realistic validation scenarios."""

    def test_python_validation_pipeline(self):
        """Test typical Python validation pipeline."""
        results_map: Dict[str, ToolResult] = {}

        def make_validator(name: str, error_count: int = 0):
            def validator():
                result = ToolResult(
                    tool_name=name,
                    success=error_count == 0,
                    duration=0.01,
                    errors=error_count,
                )
                results_map[name] = result
                return result

            return validator

        deps = {
            "black": [],
            "isort": [],
            "ruff": [],
            "mypy": ["black", "isort"],
            "flake8": ["black", "isort"],
        }

        executor = ParallelExecutor(tool_dependencies=deps)
        tools = {
            "black": make_validator("black"),
            "isort": make_validator("isort"),
            "ruff": make_validator("ruff"),
            "mypy": make_validator("mypy"),
            "flake8": make_validator("flake8"),
        }

        results = executor.execute_tools(tools)

        # Verify execution order
        assert all(r.success for r in results)

        # Verify formatters ran before type checkers
        levels = executor._get_execution_order()
        assert "black" in levels[0]
        assert "isort" in levels[0]
        assert "mypy" in levels[1]
        assert "flake8" in levels[1]

    def test_full_huskycat_pipeline(self):
        """Test execution plan for full HuskyCat tool suite."""
        executor = ParallelExecutor()  # Use default dependencies

        plan = executor.get_execution_plan()
        stats = executor.get_statistics()

        # Should have multiple levels for parallelism
        assert stats["total_levels"] >= 2

        # Should achieve significant parallelism
        assert stats["speedup_factor"] > 1.5

        # Verify critical tools are in correct order
        levels = executor._get_execution_order()
        level_map = {tool: idx for idx, level in enumerate(levels) for tool in level}

        # mypy should run after black
        if "mypy" in level_map and "black" in level_map:
            assert level_map["black"] < level_map["mypy"]

        # flake8 should run after black
        if "flake8" in level_map and "black" in level_map:
            assert level_map["black"] < level_map["flake8"]
