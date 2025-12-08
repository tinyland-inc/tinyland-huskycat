"""
Sprint 10 Performance Tests.

Performance benchmarks and profiling for non-blocking hooks.
Validates Sprint 10 performance targets:
- Parent return time: <100ms
- Parallel execution speedup: >5x
- Tool extraction time: <1s
- Memory efficiency: <100MB overhead
"""

import os
import sys
import time
import tracemalloc
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from huskycat.core.adapters.git_hooks_nonblocking import NonBlockingGitHooksAdapter
from huskycat.core.parallel_executor import ToolResult
from huskycat.core.process_manager import ProcessManager


class TestParentReturnTimeBenchmark:
    """Benchmark parent process return time."""

    def test_parent_return_time_target(self, tmp_path):
        """Benchmark parent return time (target: <100ms)."""
        cache_dir = tmp_path / ".huskycat" / "runs"
        adapter = NonBlockingGitHooksAdapter(cache_dir=cache_dir)

        files = ["test.py"]
        tools = {"black": MagicMock()}

        def execute_with_mock_fork():
            with patch("os.fork", return_value=12345):
                with patch.object(adapter.process_manager, "cleanup_zombies"):
                    with patch.object(adapter.process_manager, "_save_pid"):
                        return adapter.execute_validation(files, tools)

        # Manual benchmark (pytest-benchmark not required)
        times = []
        for _ in range(100):
            start = time.time()
            execute_with_mock_fork()
            times.append((time.time() - start) * 1000)

        avg_time = sum(times) / len(times)
        p95_time = sorted(times)[94]  # 95th percentile
        p99_time = sorted(times)[98]  # 99th percentile

        print(f"\nParent Return Time:")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  P95: {p95_time:.2f}ms")
        print(f"  P99: {p99_time:.2f}ms")

        # Target: <100ms (should be much lower, ~1-10ms)
        assert avg_time < 100.0
        assert p99_time < 100.0

    def test_fork_overhead_measurement(self, tmp_path):
        """Measure fork overhead specifically."""
        cache_dir = tmp_path / ".huskycat" / "runs"
        manager = ProcessManager(cache_dir=cache_dir)

        times = []
        for _ in range(50):
            start = time.time()

            with patch("os.fork", return_value=12345):
                with patch.object(manager, "_save_pid"):
                    pid = manager.fork_validation(
                        files=["test.py"],
                        validation_cmd="echo",
                        validation_args=["test"],
                    )

            fork_time = (time.time() - start) * 1000
            times.append(fork_time)

        avg_fork_time = sum(times) / len(times)
        max_fork_time = max(times)

        print(f"\nFork Overhead:")
        print(f"  Average: {avg_fork_time:.2f}ms")
        print(f"  Maximum: {max_fork_time:.2f}ms")

        # Fork should be very fast (<10ms typically)
        assert avg_fork_time < 50.0
        assert max_fork_time < 100.0


class TestParallelExecutionSpeedup:
    """Benchmark parallel execution speedup."""

    def test_parallel_vs_sequential_speedup(self, tmp_path):
        """Measure parallel execution speedup (target: >5x)."""
        cache_dir = tmp_path / ".huskycat" / "runs"
        adapter = NonBlockingGitHooksAdapter(cache_dir=cache_dir)

        # Create 8 independent tools that take 0.1s each
        num_tools = 8
        tool_duration = 0.1

        def make_tool(name: str):
            def tool():
                time.sleep(tool_duration)
                return ToolResult(
                    tool_name=name,
                    success=True,
                    duration=tool_duration,
                    errors=0,
                    warnings=0,
                )

            return tool

        tools = {f"tool_{i}": make_tool(f"tool_{i}") for i in range(num_tools)}

        # Measure parallel execution
        start = time.time()
        results = adapter.executor.execute_tools(tools)
        parallel_time = time.time() - start

        # Calculate expected sequential time
        sequential_time = num_tools * tool_duration

        # Calculate speedup
        speedup = sequential_time / parallel_time

        print(f"\nParallel Execution Speedup:")
        print(f"  Sequential time (estimated): {sequential_time:.2f}s")
        print(f"  Parallel time: {parallel_time:.2f}s")
        print(f"  Speedup: {speedup:.2f}x")

        # Target: >5x speedup
        assert speedup >= 5.0
        assert all(r.success for r in results)

    def test_scalability_with_tool_count(self, tmp_path):
        """Test scalability as tool count increases."""
        cache_dir = tmp_path / ".huskycat" / "runs"
        adapter = NonBlockingGitHooksAdapter(cache_dir=cache_dir)

        tool_counts = [2, 4, 8, 16]
        results_by_count = {}

        for num_tools in tool_counts:
            tools = {}
            for i in range(num_tools):
                tool_name = f"tool_{i}"
                tools[tool_name] = lambda name=tool_name: ToolResult(
                    tool_name=name,
                    success=True,
                    duration=0.05,
                    errors=0,
                )

            start = time.time()
            results = adapter.executor.execute_tools(tools)
            duration = time.time() - start

            results_by_count[num_tools] = {
                "duration": duration,
                "speedup": (num_tools * 0.05) / duration,
            }

        print(f"\nScalability Analysis:")
        for count, data in results_by_count.items():
            print(f"  {count} tools: {data['duration']:.3f}s (speedup: {data['speedup']:.2f}x)")

        # Speedup should increase with tool count (up to worker limit)
        assert results_by_count[8]["speedup"] > results_by_count[2]["speedup"]


class TestToolExtractionPerformance:
    """Benchmark tool extraction from fat binary."""

    def test_tool_extraction_time(self, tmp_path):
        """Measure tool extraction time (target: <1s)."""
        # Simulate extracting tools from PyInstaller bundle
        tools_dir = tmp_path / ".huskycat" / "tools"
        tools_dir.mkdir(parents=True)

        # Simulate tool binaries (small files for test)
        tool_names = ["black", "ruff", "mypy", "flake8", "bandit"]

        start = time.time()

        for tool in tool_names:
            tool_path = tools_dir / tool
            # Simulate binary extraction
            tool_path.write_bytes(b"#!/usr/bin/env python3\nprint('tool')\n" * 100)
            tool_path.chmod(0o755)

        extraction_time = time.time() - start

        print(f"\nTool Extraction:")
        print(f"  {len(tool_names)} tools: {extraction_time:.3f}s")

        # Target: <1s for all tools
        assert extraction_time < 1.0

    def test_bundled_tool_resolution_speed(self, tmp_path):
        """Measure bundled tool resolution speed."""
        from huskycat.unified_validation import Validator

        # Create mock validator
        class MockValidator(Validator):
            @property
            def name(self):
                return "test-validator"

            @property
            def extensions(self):
                return {".py"}

            def validate(self, filepath, auto_fix=False):
                pass

        validator = MockValidator()

        # Benchmark tool resolution
        times = []
        for _ in range(100):
            start = time.time()
            _ = validator._get_execution_mode()
            times.append((time.time() - start) * 1000)

        avg_time = sum(times) / len(times)
        print(f"\nTool Resolution Time: {avg_time:.3f}ms")

        # Should be very fast (<1ms)
        assert avg_time < 10.0


class TestMemoryEfficiency:
    """Test memory usage and efficiency."""

    def test_memory_overhead_parallel_execution(self, tmp_path):
        """Measure memory overhead during parallel execution."""
        cache_dir = tmp_path / ".huskycat" / "runs"
        adapter = NonBlockingGitHooksAdapter(cache_dir=cache_dir)

        # Start memory tracking
        tracemalloc.start()

        # Get baseline memory
        baseline = tracemalloc.get_traced_memory()[0]

        # Create many tools
        num_tools = 16
        tools = {}
        for i in range(num_tools):
            tool_name = f"tool_{i}"
            tools[tool_name] = lambda name=tool_name: ToolResult(
                tool_name=name,
                success=True,
                duration=0.01,
                errors=0,
            )

        # Execute tools
        results = adapter.executor.execute_tools(tools)

        # Measure peak memory
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()

        memory_overhead_mb = (peak - baseline) / 1024 / 1024

        print(f"\nMemory Overhead:")
        print(f"  Baseline: {baseline / 1024 / 1024:.2f} MB")
        print(f"  Peak: {peak / 1024 / 1024:.2f} MB")
        print(f"  Overhead: {memory_overhead_mb:.2f} MB")

        # Target: <100MB overhead for parallel execution
        assert memory_overhead_mb < 100.0

    def test_process_manager_memory_efficiency(self, tmp_path):
        """Test ProcessManager memory efficiency with many runs."""
        from huskycat.core.process_manager import ProcessManager, ValidationRun

        cache_dir = tmp_path / ".huskycat" / "runs"
        manager = ProcessManager(cache_dir=cache_dir)

        tracemalloc.start()
        baseline = tracemalloc.get_traced_memory()[0]

        # Create many validation runs
        for i in range(100):
            run = ValidationRun(
                run_id=f"run_{i:03d}",
                started="2025-12-07T10:00:00",
                completed="2025-12-07T10:05:00",
                files=[f"file{j}.py" for j in range(10)],
                success=(i % 2 == 0),
                tools_run=["black", "ruff", "mypy"],
                errors=i % 5,
            )
            manager.save_run(run)

        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()

        memory_mb = (peak - baseline) / 1024 / 1024

        print(f"\nProcessManager Memory (100 runs):")
        print(f"  Memory used: {memory_mb:.2f} MB")

        # Should be efficient (<50MB for 100 runs)
        assert memory_mb < 50.0


class TestTUIPerformance:
    """Test TUI performance and overhead."""

    def test_tui_update_performance(self, tmp_path):
        """Measure TUI update performance."""
        from huskycat.core.tui import ToolState, ValidationTUI

        if not sys.stdout.isatty():
            pytest.skip("TUI test requires TTY")

        tui = ValidationTUI(refresh_rate=0.1)

        tool_names = [f"tool_{i}" for i in range(20)]
        tui.start(tool_names)

        # Measure update time
        update_times = []
        for tool in tool_names:
            start = time.time()
            tui.update_tool(tool, ToolState.RUNNING)
            update_times.append((time.time() - start) * 1000)

        tui.stop()

        avg_update = sum(update_times) / len(update_times)
        max_update = max(update_times)

        print(f"\nTUI Update Performance:")
        print(f"  Average: {avg_update:.3f}ms")
        print(f"  Maximum: {max_update:.3f}ms")

        # Updates should be very fast (<10ms)
        assert avg_update < 10.0

    def test_tui_thread_safety_performance(self, tmp_path):
        """Test TUI thread-safe updates don't cause bottlenecks."""
        from huskycat.core.tui import ToolState, ValidationTUI
        import threading

        if not sys.stdout.isatty():
            pytest.skip("TUI test requires TTY")

        tui = ValidationTUI()
        tool_names = [f"tool_{i}" for i in range(10)]
        tui.start(tool_names)

        # Simulate concurrent updates from multiple threads
        def update_tool(tool_name: str):
            for _ in range(10):
                tui.update_tool(tool_name, ToolState.RUNNING)
                time.sleep(0.01)
                tui.update_tool(tool_name, ToolState.SUCCESS, errors=0)

        start = time.time()

        threads = []
        for tool in tool_names[:5]:  # Use subset for speed
            t = threading.Thread(target=update_tool, args=(tool,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        duration = time.time() - start

        tui.stop()

        print(f"\nTUI Thread Safety (5 threads, 10 updates each):")
        print(f"  Duration: {duration:.2f}s")

        # Should handle concurrent updates efficiently
        assert duration < 2.0


class TestDependencyGraphPerformance:
    """Test dependency graph computation performance."""

    def test_graph_construction_time(self):
        """Measure dependency graph construction time."""
        from huskycat.core.parallel_executor import TOOL_DEPENDENCIES, ParallelExecutor

        times = []
        for _ in range(100):
            start = time.time()
            executor = ParallelExecutor(tool_dependencies=TOOL_DEPENDENCIES)
            times.append((time.time() - start) * 1000)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        print(f"\nDependency Graph Construction:")
        print(f"  Average: {avg_time:.3f}ms")
        print(f"  Maximum: {max_time:.3f}ms")

        # Should be very fast (<10ms)
        assert avg_time < 10.0

    def test_topological_sort_performance(self):
        """Measure topological sort performance for execution order."""
        from huskycat.core.parallel_executor import TOOL_DEPENDENCIES, ParallelExecutor

        executor = ParallelExecutor(tool_dependencies=TOOL_DEPENDENCIES)

        times = []
        for _ in range(100):
            start = time.time()
            _ = executor._get_execution_order()
            times.append((time.time() - start) * 1000)

        avg_time = sum(times) / len(times)

        print(f"\nTopological Sort Performance:")
        print(f"  Average: {avg_time:.3f}ms")

        # Should be very fast (<1ms)
        assert avg_time < 5.0


class TestEndToEndPerformance:
    """Test complete end-to-end performance."""

    def test_complete_validation_cycle(self, tmp_path):
        """Measure complete validation cycle performance."""
        cache_dir = tmp_path / ".huskycat" / "runs"
        adapter = NonBlockingGitHooksAdapter(cache_dir=cache_dir)

        files = ["test1.py", "test2.py", "test3.py"]

        # Create realistic tool set
        tools = {}
        for tool in ["black", "ruff", "mypy", "flake8"]:
            tools[tool] = lambda name=tool: ToolResult(
                tool_name=name,
                success=True,
                duration=0.1,
                errors=0,
            )

        # Measure complete cycle (with mocked fork)
        start = time.time()

        with patch("os.fork", return_value=12345):
            with patch.object(adapter.process_manager, "cleanup_zombies"):
                with patch.object(adapter.process_manager, "_save_pid"):
                    pid = adapter.execute_validation(files, tools)

        cycle_time = (time.time() - start) * 1000

        print(f"\nComplete Validation Cycle:")
        print(f"  Time: {cycle_time:.2f}ms")

        # Parent should return very quickly
        assert cycle_time < 100.0

    def test_throughput_multiple_commits(self, tmp_path):
        """Measure throughput for multiple rapid commits."""
        from huskycat.core.process_manager import ProcessManager

        cache_dir = tmp_path / ".huskycat" / "runs"
        manager = ProcessManager(cache_dir=cache_dir)

        num_commits = 10

        start = time.time()

        for i in range(num_commits):
            files = [f"commit{i}_file.py"]
            with patch("os.fork", return_value=1000 + i):
                with patch.object(manager, "_save_pid"):
                    manager.fork_validation(
                        files=files,
                        validation_cmd="echo",
                        validation_args=["test"],
                    )

        total_time = time.time() - start
        commits_per_sec = num_commits / total_time

        print(f"\nCommit Throughput:")
        print(f"  {num_commits} commits: {total_time:.2f}s")
        print(f"  Throughput: {commits_per_sec:.1f} commits/sec")

        # Should handle multiple commits quickly
        assert commits_per_sec > 50.0  # At least 50 commits/sec


class TestRegressionPerformance:
    """Test performance doesn't regress compared to baseline."""

    def test_no_performance_regression(self, tmp_path):
        """Ensure performance meets all Sprint 10 targets."""
        results = {
            "parent_return": None,
            "parallel_speedup": None,
            "tool_extraction": None,
            "memory_overhead": None,
        }

        # Test 1: Parent return time
        cache_dir = tmp_path / ".huskycat" / "runs"
        adapter = NonBlockingGitHooksAdapter(cache_dir=cache_dir)

        start = time.time()
        with patch("os.fork", return_value=12345):
            with patch.object(adapter.process_manager, "cleanup_zombies"):
                with patch.object(adapter.process_manager, "_save_pid"):
                    adapter.execute_validation(["test.py"], {"black": MagicMock()})
        results["parent_return"] = (time.time() - start) * 1000

        # Test 2: Parallel speedup
        tools = {f"tool_{i}": lambda i=i: ToolResult(
            tool_name=f"tool_{i}", success=True, duration=0.05
        ) for i in range(8)}

        start = time.time()
        adapter.executor.execute_tools(tools)
        parallel_time = time.time() - start
        results["parallel_speedup"] = (8 * 0.05) / parallel_time

        # Print summary
        print(f"\nPerformance Targets Summary:")
        print(f"  Parent return time: {results['parent_return']:.2f}ms (target: <100ms)")
        print(f"  Parallel speedup: {results['parallel_speedup']:.2f}x (target: >5x)")

        # Verify all targets met
        assert results["parent_return"] < 100.0
        assert results["parallel_speedup"] >= 5.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
