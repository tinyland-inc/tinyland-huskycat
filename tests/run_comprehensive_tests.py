#!/usr/bin/env python3
"""
Comprehensive Test Runner for HuskyCat
Orchestrates all testing phases: unit, integration, E2E, and performance
"""

import sys
import subprocess
import time
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class TestPhase(Enum):
    """Test execution phases."""

    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    SECURITY = "security"
    CONTAINER = "container"


@dataclass
class TestResult:
    """Test execution result."""

    phase: str
    name: str
    command: List[str]
    returncode: int
    duration: float
    stdout: str
    stderr: str
    success: bool
    skipped: bool = False
    skip_reason: str = ""


class TestRunner:
    """Comprehensive test runner."""

    def __init__(self, verbose: bool = False, fail_fast: bool = False):
        self.verbose = verbose
        self.fail_fast = fail_fast
        self.results: List[TestResult] = []
        self.start_time = time.time()

        # Test discovery
        self.project_root = Path(__file__).parent.parent
        self.tests_dir = self.project_root / "tests"
        self.scripts_dir = self.project_root / "scripts"

    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp."""
        if self.verbose or level in ["ERROR", "SUCCESS", "FAILURE"]:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] {level}: {message}")

    def run_command(
        self,
        command: List[str],
        cwd: Optional[Path] = None,
        timeout: Optional[int] = None,
        env: Optional[Dict] = None,
    ) -> Tuple[int, str, str, float]:
        """Run command and return results."""
        start_time = time.time()

        try:
            result = subprocess.run(
                command,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )

            duration = time.time() - start_time
            return result.returncode, result.stdout, result.stderr, duration

        except subprocess.TimeoutExpired as e:
            duration = time.time() - start_time
            return -1, "", f"Command timed out after {timeout}s", duration

        except Exception as e:
            duration = time.time() - start_time
            return -2, "", f"Command failed: {e}", duration

    def execute_test(
        self,
        phase: TestPhase,
        name: str,
        command: List[str],
        cwd: Optional[Path] = None,
        timeout: Optional[int] = None,
        env: Optional[Dict] = None,
    ) -> TestResult:
        """Execute a single test."""
        self.log(f"Running {phase.value} test: {name}")

        returncode, stdout, stderr, duration = self.run_command(
            command, cwd, timeout, env
        )

        success = returncode == 0
        skipped = "SKIPPED" in stdout.upper() or "SKIP" in stderr.upper()
        skip_reason = ""

        if skipped:
            # Extract skip reason
            lines = (stdout + "\n" + stderr).split("\n")
            for line in lines:
                if "skip" in line.lower() and ("reason" in line.lower() or ":" in line):
                    skip_reason = line.strip()
                    break

        result = TestResult(
            phase=phase.value,
            name=name,
            command=command,
            returncode=returncode,
            duration=duration,
            stdout=stdout,
            stderr=stderr,
            success=success,
            skipped=skipped,
            skip_reason=skip_reason,
        )

        self.results.append(result)

        if success:
            self.log(f"✅ {name} passed ({duration:.2f}s)", "SUCCESS")
        elif skipped:
            self.log(f"⏭️  {name} skipped: {skip_reason}", "SKIP")
        else:
            self.log(f"❌ {name} failed ({duration:.2f}s)", "FAILURE")
            if self.verbose:
                self.log(f"STDOUT: {stdout}")
                self.log(f"STDERR: {stderr}")

        if self.fail_fast and not success and not skipped:
            raise SystemExit(f"Test failed: {name}")

        return result

    def run_unit_tests(self) -> List[TestResult]:
        """Run unit tests."""
        self.log("=== Running Unit Tests ===")
        results = []

        # Property-based tests
        pbt_tests = [
            "test_validation_pbt.py",
            "test_unified_validation_pbt.py",
            "test_mcp_server_pbt.py",
        ]

        for test_file in pbt_tests:
            test_path = self.tests_dir / test_file
            if test_path.exists():
                result = self.execute_test(
                    TestPhase.UNIT,
                    f"Property-based: {test_file}",
                    ["python3", "-m", "pytest", str(test_path), "-v"],
                    timeout=300,
                )
                results.append(result)

        # Standard unit tests
        unit_test_files = self.tests_dir.glob("test_*_unit.py")
        for test_file in unit_test_files:
            result = self.execute_test(
                TestPhase.UNIT,
                f"Unit: {test_file.name}",
                ["python3", "-m", "pytest", str(test_file), "-v"],
                timeout=180,
            )
            results.append(result)

        return results

    def run_integration_tests(self) -> List[TestResult]:
        """Run integration tests."""
        self.log("=== Running Integration Tests ===")
        results = []

        # Git hooks integration
        git_hooks_test = self.tests_dir / "test_git_hooks.py"
        if git_hooks_test.exists():
            result = self.execute_test(
                TestPhase.INTEGRATION,
                "Git Hooks Integration",
                [
                    "python3",
                    "-m",
                    "pytest",
                    str(git_hooks_test),
                    "-v",
                    "-m",
                    "integration",
                ],
                timeout=300,
            )
            results.append(result)

        # MCP integration
        mcp_integration_test = self.tests_dir / "test_mcp_integration_comprehensive.py"
        if mcp_integration_test.exists():
            result = self.execute_test(
                TestPhase.INTEGRATION,
                "MCP Server Integration",
                [
                    "python3",
                    "-m",
                    "pytest",
                    str(mcp_integration_test),
                    "-v",
                    "-m",
                    "integration",
                ],
                timeout=300,
            )
            results.append(result)

        # Real validation flow
        real_validation_test = self.tests_dir / "test_real_validation_e2e.py"
        if real_validation_test.exists():
            result = self.execute_test(
                TestPhase.INTEGRATION,
                "Real Validation Flow",
                [
                    "python3",
                    "-m",
                    "pytest",
                    str(real_validation_test),
                    "-v",
                    "-m",
                    "integration",
                ],
                timeout=300,
            )
            results.append(result)

        return results

    def run_e2e_tests(self) -> List[TestResult]:
        """Run end-to-end tests."""
        self.log("=== Running E2E Tests ===")
        results = []

        # Shell-based E2E tests
        e2e_scripts = [
            ("Git Hooks E2E", self.tests_dir / "e2e" / "test-git-hooks.sh"),
            ("Container E2E", self.tests_dir / "e2e" / "test-container.sh"),
        ]

        for name, script_path in e2e_scripts:
            if script_path.exists():
                result = self.execute_test(
                    TestPhase.E2E,
                    name,
                    ["bash", str(script_path)],
                    timeout=600,  # 10 minutes
                )
                results.append(result)

        # Python E2E tests
        e2e_test = self.tests_dir / "test_real_validation_e2e.py"
        if e2e_test.exists():
            result = self.execute_test(
                TestPhase.E2E,
                "Python E2E Validation",
                ["python3", "-m", "pytest", str(e2e_test), "-v", "-m", "e2e"],
                timeout=600,
            )
            results.append(result)

        # Deployment tests
        deployment_test = self.tests_dir / "test_e2e_deployment.py"
        if deployment_test.exists():
            result = self.execute_test(
                TestPhase.E2E,
                "Deployment E2E",
                ["python3", "-m", "pytest", str(deployment_test), "-v", "-m", "e2e"],
                timeout=900,  # 15 minutes
            )
            results.append(result)

        return results

    def run_container_tests(self) -> List[TestResult]:
        """Run container tests."""
        self.log("=== Running Container Tests ===")
        results = []

        # Check if container runtime is available
        has_runtime = False
        for runtime in ["podman", "docker"]:
            try:
                subprocess.run([runtime, "--version"], check=True, capture_output=True)
                has_runtime = True
                break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue

        if not has_runtime:
            result = TestResult(
                phase=TestPhase.CONTAINER.value,
                name="Container Tests",
                command=["echo", "skipped"],
                returncode=0,
                duration=0.0,
                stdout="",
                stderr="",
                success=True,
                skipped=True,
                skip_reason="No container runtime available",
            )
            results.append(result)
            return results

        # Container functionality tests
        container_test = self.tests_dir / "test_container_comprehensive.py"
        if container_test.exists():
            result = self.execute_test(
                TestPhase.CONTAINER,
                "Container Comprehensive",
                [
                    "python3",
                    "-m",
                    "pytest",
                    str(container_test),
                    "-v",
                    "-m",
                    "container",
                ],
                timeout=1200,  # 20 minutes
            )
            results.append(result)

        return results

    def run_performance_tests(self) -> List[TestResult]:
        """Run performance tests."""
        self.log("=== Running Performance Tests ===")
        results = []

        # Performance-specific tests
        perf_tests = [
            self.tests_dir / "test_real_validation_e2e.py",
            self.tests_dir / "test_container_comprehensive.py",
        ]

        for test_file in perf_tests:
            if test_file.exists():
                result = self.execute_test(
                    TestPhase.PERFORMANCE,
                    f"Performance: {test_file.name}",
                    ["python3", "-m", "pytest", str(test_file), "-v", "-m", "slow"],
                    timeout=1800,  # 30 minutes
                )
                results.append(result)

        return results

    def run_security_tests(self) -> List[TestResult]:
        """Run security tests."""
        self.log("=== Running Security Tests ===")
        results = []

        # Security-focused tests
        security_tests = [
            self.tests_dir / "test_container_comprehensive.py",
            self.tests_dir / "test_real_validation_e2e.py",
        ]

        for test_file in security_tests:
            if test_file.exists():
                result = self.execute_test(
                    TestPhase.SECURITY,
                    f"Security: {test_file.name}",
                    ["python3", "-m", "pytest", str(test_file), "-v", "-m", "security"],
                    timeout=600,
                )
                results.append(result)

        return results

    def run_makefile_tests(self) -> List[TestResult]:
        """Run tests defined in Makefile."""
        self.log("=== Running Makefile Tests ===")
        results = []

        makefile = self.project_root / "Makefile"
        if makefile.exists():
            make_targets = [
                ("Makefile Unit Tests", ["make", "test-unit"]),
                ("Makefile Integration Tests", ["make", "test-integration"]),
                ("Makefile Distribution Tests", ["make", "test-distribution"]),
            ]

            for name, command in make_targets:
                result = self.execute_test(
                    TestPhase.INTEGRATION, name, command, timeout=600
                )
                results.append(result)

        return results

    def generate_report(self) -> Dict[str, Any]:
        """Generate test execution report."""
        total_duration = time.time() - self.start_time

        # Group results by phase
        by_phase = {}
        for result in self.results:
            if result.phase not in by_phase:
                by_phase[result.phase] = []
            by_phase[result.phase].append(result)

        # Calculate statistics
        total_tests = len(self.results)
        passed = len([r for r in self.results if r.success and not r.skipped])
        failed = len([r for r in self.results if not r.success and not r.skipped])
        skipped = len([r for r in self.results if r.skipped])

        report = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "success_rate": passed / max(1, total_tests - skipped) * 100,
                "total_duration": total_duration,
            },
            "by_phase": {},
            "failures": [],
        }

        # Phase statistics
        for phase, phase_results in by_phase.items():
            phase_passed = len(
                [r for r in phase_results if r.success and not r.skipped]
            )
            phase_failed = len(
                [r for r in phase_results if not r.success and not r.skipped]
            )
            phase_skipped = len([r for r in phase_results if r.skipped])

            report["by_phase"][phase] = {
                "total": len(phase_results),
                "passed": phase_passed,
                "failed": phase_failed,
                "skipped": phase_skipped,
                "duration": sum(r.duration for r in phase_results),
            }

        # Collect failures
        for result in self.results:
            if not result.success and not result.skipped:
                report["failures"].append(
                    {
                        "phase": result.phase,
                        "name": result.name,
                        "command": " ".join(result.command),
                        "returncode": result.returncode,
                        "stderr": result.stderr[:500],  # Truncate for readability
                    }
                )

        return report

    def print_report(self):
        """Print test execution report."""
        report = self.generate_report()
        summary = report["summary"]

        print("\n" + "=" * 70)
        print("🧪 HUSKYCATS COMPREHENSIVE TEST REPORT")
        print("=" * 70)

        print(f"📊 SUMMARY:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   ✅ Passed: {summary['passed']}")
        print(f"   ❌ Failed: {summary['failed']}")
        print(f"   ⏭️  Skipped: {summary['skipped']}")
        print(f"   🎯 Success Rate: {summary['success_rate']:.1f}%")
        print(f"   ⏱️  Total Duration: {summary['total_duration']:.2f}s")

        print(f"\n📋 BY PHASE:")
        for phase, stats in report["by_phase"].items():
            print(f"   {phase.upper()}:")
            print(
                f"      Tests: {stats['total']} | Passed: {stats['passed']} | Failed: {stats['failed']} | Skipped: {stats['skipped']}"
            )
            print(f"      Duration: {stats['duration']:.2f}s")

        if report["failures"]:
            print(f"\n❌ FAILURES ({len(report['failures'])}):")
            for failure in report["failures"]:
                print(f"   {failure['phase'].upper()}: {failure['name']}")
                print(f"      Command: {failure['command']}")
                print(f"      Exit Code: {failure['returncode']}")
                if failure["stderr"]:
                    print(f"      Error: {failure['stderr'][:200]}...")
                print()

        print("=" * 70)

    def save_report(self, path: Path):
        """Save detailed report to file."""
        report = self.generate_report()
        report["results"] = [asdict(r) for r in self.results]

        with open(path, "w") as f:
            json.dump(report, f, indent=2)

        self.log(f"Detailed report saved to: {path}")

    def run_all_tests(self, phases: Optional[List[TestPhase]] = None):
        """Run all test phases."""
        if phases is None:
            phases = [
                TestPhase.UNIT,
                TestPhase.INTEGRATION,
                TestPhase.E2E,
                TestPhase.CONTAINER,
            ]

        self.log("🚀 Starting HuskyCat Comprehensive Test Suite")
        self.log(f"Phases to run: {[p.value for p in phases]}")

        # Execute test phases
        for phase in phases:
            try:
                if phase == TestPhase.UNIT:
                    self.run_unit_tests()
                elif phase == TestPhase.INTEGRATION:
                    self.run_integration_tests()
                    self.run_makefile_tests()
                elif phase == TestPhase.E2E:
                    self.run_e2e_tests()
                elif phase == TestPhase.CONTAINER:
                    self.run_container_tests()
                elif phase == TestPhase.PERFORMANCE:
                    self.run_performance_tests()
                elif phase == TestPhase.SECURITY:
                    self.run_security_tests()

            except SystemExit:
                if self.fail_fast:
                    break
                else:
                    raise

        # Generate and print report
        self.print_report()

        # Save detailed report
        report_path = self.project_root / f"test_report_{int(time.time())}.json"
        self.save_report(report_path)

        # Return overall success
        failed_tests = [r for r in self.results if not r.success and not r.skipped]
        return len(failed_tests) == 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run comprehensive HuskyCat tests")
    parser.add_argument(
        "--phases",
        nargs="+",
        choices=[p.value for p in TestPhase],
        help="Test phases to run",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--fail-fast", action="store_true", help="Stop on first failure"
    )
    parser.add_argument(
        "--quick", action="store_true", help="Run only unit and integration tests"
    )

    args = parser.parse_args()

    # Determine phases to run
    if args.quick:
        phases = [TestPhase.UNIT, TestPhase.INTEGRATION]
    elif args.phases:
        phases = [TestPhase(phase) for phase in args.phases]
    else:
        phases = None  # Run all

    # Create and run test suite
    runner = TestRunner(verbose=args.verbose, fail_fast=args.fail_fast)
    success = runner.run_all_tests(phases)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
