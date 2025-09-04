#!/usr/bin/env python3
"""
Comprehensive test runner for HuskyCats project.

This script provides intelligent test execution with different testing strategies:
- Fast feedback for development
- Comprehensive validation for CI/CD
- Targeted testing for specific components
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import json


class TestRunner:
    """Intelligent test runner with multiple execution strategies."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_dir = Path(__file__).parent
        self.reports_dir = self.test_dir / "test-reports"
        self.reports_dir.mkdir(exist_ok=True)
        
    def run_fast_tests(self) -> bool:
        """Run fast tests suitable for development feedback."""
        print("🏃‍♂️ Running fast development tests...")
        
        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir),
            "-m", "not slow and not e2e and not container",
            "--maxfail=3",
            "--tb=short",
            "-q",
            "--durations=5"
        ]
        
        return self._execute_pytest(cmd, "fast")
    
    def run_unit_tests(self) -> bool:
        """Run all unit tests."""
        print("🧪 Running unit tests...")
        
        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir),
            "-m", "unit",
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=html:test-reports/unit-coverage",
            "--junit-xml=test-reports/unit-junit.xml"
        ]
        
        return self._execute_pytest(cmd, "unit")
    
    def run_property_tests(self) -> bool:
        """Run property-based tests with Hypothesis."""
        print("🎲 Running property-based tests...")
        
        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir / "test_property_based.py"),
            "-m", "property",
            "-v",
            "--tb=short"
        ]
        
        return self._execute_pytest(cmd, "property")
    
    def run_integration_tests(self) -> bool:
        """Run integration tests."""
        print("🔗 Running integration tests...")
        
        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir),
            "-m", "integration",
            "-v",
            "--tb=short",
            "--junit-xml=test-reports/integration-junit.xml"
        ]
        
        return self._execute_pytest(cmd, "integration")
    
    def run_security_tests(self) -> bool:
        """Run security-focused tests."""
        print("🔒 Running security tests...")
        
        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir),
            "-m", "security",
            "-v",
            "--tb=short",
            "--junit-xml=test-reports/security-junit.xml"
        ]
        
        return self._execute_pytest(cmd, "security")
    
    def run_e2e_tests(self) -> bool:
        """Run end-to-end tests."""
        print("🎭 Running end-to-end tests...")
        
        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir),
            "-m", "e2e",
            "-v",
            "--tb=long",
            "--junit-xml=test-reports/e2e-junit.xml",
            "--timeout=300"  # 5 minutes timeout for E2E tests
        ]
        
        return self._execute_pytest(cmd, "e2e")
    
    def run_container_tests(self) -> bool:
        """Run container-related tests."""
        print("🐳 Running container tests...")
        
        # Check if Docker is available
        if not self._check_docker():
            print("⚠️  Docker not available, skipping container tests")
            return True
        
        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir),
            "-m", "container",
            "-v",
            "--tb=short",
            "--junit-xml=test-reports/container-junit.xml",
            "--timeout=600"  # 10 minutes timeout for container tests
        ]
        
        return self._execute_pytest(cmd, "container")
    
    def run_performance_tests(self) -> bool:
        """Run performance tests."""
        print("⚡ Running performance tests...")
        
        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir),
            "-m", "performance",
            "-v",
            "--tb=short",
            "--benchmark-only",
            "--benchmark-json=test-reports/benchmark.json"
        ]
        
        return self._execute_pytest(cmd, "performance")
    
    def run_all_tests(self) -> bool:
        """Run comprehensive test suite."""
        print("🎯 Running comprehensive test suite...")
        
        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir),
            "-v",
            "--cov=src",
            "--cov=.",
            "--cov-report=term-missing",
            "--cov-report=html:test-reports/coverage-html",
            "--cov-report=xml:test-reports/coverage.xml",
            "--junit-xml=test-reports/junit.xml",
            "--html=test-reports/report.html",
            "--self-contained-html",
            "--durations=10"
        ]
        
        return self._execute_pytest(cmd, "comprehensive")
    
    def run_ci_tests(self) -> bool:
        """Run CI-appropriate test suite."""
        print("🏗️ Running CI test suite...")
        
        # Run tests in specific order for CI
        test_phases = [
            ("Unit Tests", self.run_unit_tests),
            ("Property Tests", self.run_property_tests),
            ("Security Tests", self.run_security_tests),
            ("Integration Tests", self.run_integration_tests),
        ]
        
        # Add container and E2E tests if environment supports them
        if self._check_docker():
            test_phases.append(("Container Tests", self.run_container_tests))
        
        if os.getenv("RUN_E2E_TESTS", "false").lower() == "true":
            test_phases.append(("E2E Tests", self.run_e2e_tests))
        
        results = []
        for phase_name, test_func in test_phases:
            print(f"\n{'='*60}")
            print(f"🚀 {phase_name}")
            print('='*60)
            
            result = test_func()
            results.append((phase_name, result))
            
            if not result:
                print(f"❌ {phase_name} failed!")
                break
            else:
                print(f"✅ {phase_name} passed!")
        
        # Generate CI summary
        self._generate_ci_summary(results)
        
        return all(result for _, result in results)
    
    def run_specific_tests(self, test_pattern: str) -> bool:
        """Run tests matching specific pattern."""
        print(f"🎯 Running tests matching: {test_pattern}")
        
        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir),
            "-k", test_pattern,
            "-v",
            "--tb=short"
        ]
        
        return self._execute_pytest(cmd, f"specific-{test_pattern}")
    
    def validate_test_environment(self) -> bool:
        """Validate test environment setup."""
        print("🔧 Validating test environment...")
        
        checks = [
            ("Python version", self._check_python_version),
            ("Required packages", self._check_required_packages),
            ("Test directory structure", self._check_test_structure),
            ("Configuration files", self._check_configuration),
        ]
        
        all_passed = True
        for check_name, check_func in checks:
            try:
                result = check_func()
                status = "✅" if result else "❌"
                print(f"  {status} {check_name}")
                if not result:
                    all_passed = False
            except Exception as e:
                print(f"  ❌ {check_name}: {e}")
                all_passed = False
        
        return all_passed
    
    def _execute_pytest(self, cmd: List[str], test_type: str) -> bool:
        """Execute pytest command and handle results."""
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=False,  # Show output in real-time
                text=True
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            success = result.returncode == 0
            
            print(f"\n{'='*50}")
            print(f"Test Type: {test_type}")
            print(f"Duration: {duration:.2f}s")
            print(f"Result: {'PASS' if success else 'FAIL'}")
            print('='*50)
            
            return success
            
        except KeyboardInterrupt:
            print(f"\n⚠️  Tests interrupted by user")
            return False
        except Exception as e:
            print(f"\n❌ Error running {test_type} tests: {e}")
            return False
    
    def _check_docker(self) -> bool:
        """Check if Docker is available."""
        try:
            subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _check_python_version(self) -> bool:
        """Check Python version compatibility."""
        return sys.version_info >= (3, 8)
    
    def _check_required_packages(self) -> bool:
        """Check if required packages are installed."""
        required_packages = [
            "pytest",
            "hypothesis",
            "pytest-cov",
            "pytest-html",
            "requests"
        ]
        
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                print(f"    Missing package: {package}")
                return False
        
        return True
    
    def _check_test_structure(self) -> bool:
        """Check test directory structure."""
        expected_files = [
            "conftest.py",
            "test_property_based.py",
            "test_git_hooks.py",
            "test_e2e_deployment.py"
        ]
        
        for file_name in expected_files:
            if not (self.test_dir / file_name).exists():
                print(f"    Missing test file: {file_name}")
                return False
        
        return True
    
    def _check_configuration(self) -> bool:
        """Check test configuration files."""
        config_files = [
            "pytest.ini",
            "../pyproject.toml",
            "../linting-configs/pyproject.toml"
        ]
        
        for config_file in config_files:
            config_path = self.test_dir / config_file
            if config_path.exists():
                return True
        
        print("    No pytest configuration found")
        return False
    
    def _generate_ci_summary(self, results: List[tuple]) -> None:
        """Generate CI summary report."""
        summary = {
            "timestamp": time.time(),
            "total_phases": len(results),
            "passed_phases": sum(1 for _, result in results if result),
            "failed_phases": sum(1 for _, result in results if not result),
            "results": [{"phase": phase, "passed": result} for phase, result in results]
        }
        
        summary_file = self.reports_dir / "ci-summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n📊 CI Summary saved to: {summary_file}")


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(description="HuskyCats Test Runner")
    
    parser.add_argument(
        "command",
        choices=[
            "fast", "unit", "property", "integration", "security", 
            "e2e", "container", "performance", "all", "ci", "validate"
        ],
        help="Test execution strategy"
    )
    
    parser.add_argument(
        "-k", "--pattern",
        help="Run tests matching specific pattern"
    )
    
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Disable coverage reporting"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Quiet output"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    # Validate environment first (except for validate command)
    if args.command != "validate":
        if not runner.validate_test_environment():
            print("❌ Test environment validation failed!")
            sys.exit(1)
    
    # Execute requested command
    command_map = {
        "fast": runner.run_fast_tests,
        "unit": runner.run_unit_tests,
        "property": runner.run_property_tests,
        "integration": runner.run_integration_tests,
        "security": runner.run_security_tests,
        "e2e": runner.run_e2e_tests,
        "container": runner.run_container_tests,
        "performance": runner.run_performance_tests,
        "all": runner.run_all_tests,
        "ci": runner.run_ci_tests,
        "validate": runner.validate_test_environment
    }
    
    if args.pattern:
        success = runner.run_specific_tests(args.pattern)
    else:
        success = command_map[args.command]()
    
    if success:
        print("\n🎉 Tests completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()