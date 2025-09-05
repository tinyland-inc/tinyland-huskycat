#!/usr/bin/env python3
"""Run E2E tests with proper setup and reporting."""

import os
import sys
import subprocess
import argparse
import json
import time
from pathlib import Path
from typing import Dict, Any


class E2ETestRunner:
    """E2E test execution orchestrator."""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.reports_dir = self.project_root / "reports"
        self.test_results_dir = self.project_root / "test-results"
        self.setup_directories()

    def setup_directories(self):
        """Create necessary directories for test execution."""
        self.reports_dir.mkdir(exist_ok=True)
        self.test_results_dir.mkdir(exist_ok=True)

        # Create subdirectories
        for subdir in ["coverage", "screenshots", "videos", "traces"]:
            (self.test_results_dir / subdir).mkdir(exist_ok=True)

    def install_dependencies(self) -> bool:
        """Install E2E testing dependencies."""
        print("Installing E2E testing dependencies...")

        try:
            # Install Python dependencies
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
                cwd=self.project_root,
                check=True,
                capture_output=True,
            )

            # Install Playwright browsers
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                cwd=self.project_root,
                check=True,
                capture_output=True,
            )

            print("✓ Dependencies installed successfully")
            return True

        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install dependencies: {e}")
            return False

    def run_playwright_tests(
        self,
        test_pattern: str = "test_pages_deployment.py",
        browser: str = "chromium",
        headless: bool = True,
    ) -> Dict[str, Any]:
        """Run Playwright-based E2E tests."""
        print(f"Running Playwright tests: {test_pattern}")

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            f"tests/e2e/{test_pattern}",
            "-v",
            "--html=reports/playwright-report.html",
            "--self-contained-html",
            "--junit-xml=reports/playwright-junit.xml",
            f"--browser={browser}",
        ]

        if headless:
            cmd.append("--headless")

        env = os.environ.copy()
        env.update(
            {
                "PLAYWRIGHT_HEADLESS": str(headless).lower(),
                "PLAYWRIGHT_BROWSER": browser,
            }
        )

        start_time = time.time()
        result = subprocess.run(
            cmd, cwd=self.project_root, capture_output=True, text=True, env=env
        )
        duration = time.time() - start_time

        return {
            "success": result.returncode == 0,
            "duration": duration,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    def run_mcp_integration_tests(self) -> Dict[str, Any]:
        """Run MCP server integration tests."""
        print("Running MCP integration tests...")

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/e2e/test_mcp_integration.py",
            "-v",
            "-m",
            "not slow",
            "--html=reports/mcp-integration-report.html",
            "--self-contained-html",
            "--junit-xml=reports/mcp-integration-junit.xml",
        ]

        start_time = time.time()
        result = subprocess.run(
            cmd, cwd=self.project_root, capture_output=True, text=True
        )
        duration = time.time() - start_time

        return {
            "success": result.returncode == 0,
            "duration": duration,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    def run_ci_cd_tests(self) -> Dict[str, Any]:
        """Run CI/CD pipeline tests."""
        print("Running CI/CD pipeline tests...")

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/e2e/test_ci_cd_pipeline.py",
            "-v",
            "--html=reports/cicd-report.html",
            "--self-contained-html",
            "--junit-xml=reports/cicd-junit.xml",
        ]

        start_time = time.time()
        result = subprocess.run(
            cmd, cwd=self.project_root, capture_output=True, text=True
        )
        duration = time.time() - start_time

        return {
            "success": result.returncode == 0,
            "duration": duration,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance benchmarking tests."""
        print("Running performance tests...")

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/e2e/",
            "-v",
            "-m",
            "performance",
            "--html=reports/performance-report.html",
            "--self-contained-html",
            "--junit-xml=reports/performance-junit.xml",
            "--durations=0",
        ]

        start_time = time.time()
        result = subprocess.run(
            cmd, cwd=self.project_root, capture_output=True, text=True
        )
        duration = time.time() - start_time

        return {
            "success": result.returncode == 0,
            "duration": duration,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    def run_all_e2e_tests(
        self, skip_slow: bool = False, browser: str = "chromium", headless: bool = True
    ) -> Dict[str, Any]:
        """Run all E2E tests."""
        print("Running complete E2E test suite...")

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/e2e/",
            "-v",
            "--html=reports/e2e-full-report.html",
            "--self-contained-html",
            "--junit-xml=reports/e2e-full-junit.xml",
            "--cov=src",
            "--cov-report=html:reports/coverage-e2e",
            "--cov-report=xml:reports/coverage-e2e.xml",
            f"--browser={browser}",
            "--timeout=600",
        ]

        if skip_slow:
            cmd.extend(["-m", "not slow"])

        if headless:
            cmd.append("--headless")

        env = os.environ.copy()
        env.update(
            {
                "PLAYWRIGHT_HEADLESS": str(headless).lower(),
                "PLAYWRIGHT_BROWSER": browser,
            }
        )

        start_time = time.time()
        result = subprocess.run(
            cmd, cwd=self.project_root, capture_output=True, text=True, env=env
        )
        duration = time.time() - start_time

        return {
            "success": result.returncode == 0,
            "duration": duration,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    def generate_summary_report(
        self, results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate summary report of all test results."""
        summary = {
            "total_suites": len(results),
            "passed_suites": sum(1 for r in results.values() if r["success"]),
            "failed_suites": sum(1 for r in results.values() if not r["success"]),
            "total_duration": sum(r["duration"] for r in results.values()),
            "results": results,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Save summary to file
        summary_file = self.reports_dir / "e2e-summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        return summary

    def print_results_summary(self, results: Dict[str, Dict[str, Any]]):
        """Print formatted test results summary."""
        print("\n" + "=" * 60)
        print("E2E TEST RESULTS SUMMARY")
        print("=" * 60)

        total_duration = sum(r["duration"] for r in results.values())
        passed = sum(1 for r in results.values() if r["success"])
        failed = len(results) - passed

        print(f"Total Test Suites: {len(results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Total Duration: {total_duration:.2f}s")
        print()

        for suite_name, result in results.items():
            status = "PASS" if result["success"] else "FAIL"
            duration = result["duration"]
            print(f"{suite_name:25} {status:4} ({duration:6.2f}s)")

        print("\n" + "=" * 60)

        if failed > 0:
            print("FAILED SUITE DETAILS:")
            print("=" * 60)
            for suite_name, result in results.items():
                if not result["success"]:
                    print(f"\n{suite_name}:")
                    if result.get("stderr"):
                        print("STDERR:")
                        print(
                            result["stderr"][:500] + "..."
                            if len(result["stderr"]) > 500
                            else result["stderr"]
                        )

        return passed == len(results)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Run HuskyCat E2E tests")

    parser.add_argument(
        "--suite",
        choices=["all", "playwright", "mcp", "cicd", "performance"],
        default="all",
        help="Test suite to run",
    )

    parser.add_argument(
        "--browser",
        choices=["chromium", "firefox", "webkit"],
        default="chromium",
        help="Browser for Playwright tests",
    )

    parser.add_argument(
        "--headed", action="store_true", help="Run browser tests in headed mode"
    )

    parser.add_argument(
        "--skip-slow", action="store_true", help="Skip slow-running tests"
    )

    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install dependencies before running tests",
    )

    parser.add_argument("--project-root", type=Path, help="Project root directory")

    args = parser.parse_args()

    runner = E2ETestRunner(args.project_root)

    # Install dependencies if requested
    if args.install_deps:
        if not runner.install_dependencies():
            sys.exit(1)

    headless = not args.headed
    results = {}

    try:
        if args.suite == "all":
            results["full_suite"] = runner.run_all_e2e_tests(
                skip_slow=args.skip_slow, browser=args.browser, headless=headless
            )

        elif args.suite == "playwright":
            results["playwright"] = runner.run_playwright_tests(
                browser=args.browser, headless=headless
            )

        elif args.suite == "mcp":
            results["mcp_integration"] = runner.run_mcp_integration_tests()

        elif args.suite == "cicd":
            results["cicd_pipeline"] = runner.run_ci_cd_tests()

        elif args.suite == "performance":
            results["performance"] = runner.run_performance_tests()

        # Generate and print summary
        runner.generate_summary_report(results)
        all_passed = runner.print_results_summary(results)

        # Exit with appropriate code
        sys.exit(0 if all_passed else 1)

    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
