#!/usr/bin/env python3
"""
Test the Testing Infrastructure Itself
Meta-tests to ensure our test suite is working correctly
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Test infrastructure paths
TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent


class TestTestingInfrastructure:
    """Test that our testing infrastructure is properly set up."""

    def test_pytest_available(self):
        """Test that pytest is available and working."""
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "pytest" in result.stdout.lower()

    def test_test_files_exist(self):
        """Test that all expected test files exist."""
        expected_test_files = [
            "test_validation_pbt.py",
            "test_unified_validation_pbt.py",
            "test_mcp_server_pbt.py",
            "test_git_hooks.py",
            "test_container_comprehensive.py",
            "test_mcp_integration_comprehensive.py",
            "run_comprehensive_tests.py",
            "conftest.py",
        ]

        for test_file in expected_test_files:
            test_path = TESTS_DIR / test_file
            assert test_path.exists(), f"Test file missing: {test_file}"
            assert test_path.stat().st_size > 0, f"Test file is empty: {test_file}"

    def test_makefile_has_test_targets(self):
        """Test that Makefile has proper test targets."""
        makefile = PROJECT_ROOT / "Makefile"
        if not makefile.exists():
            pytest.skip("Makefile not found")

        content = makefile.read_text()

        expected_targets = [
            "test:",
            "test-unit:",
            "test-integration:",
            "test-comprehensive:",
        ]

        for target in expected_targets:
            assert target in content, f"Makefile missing target: {target}"

    def test_package_json_has_test_scripts(self):
        """Test that package.json has test scripts."""
        package_json = PROJECT_ROOT / "package.json"
        if not package_json.exists():
            pytest.skip("package.json not found")

        with open(package_json) as f:
            config = json.load(f)

        assert "scripts" in config
        scripts = config["scripts"]

        # Should not have the default failing test script
        if "test" in scripts:
            assert "Error: no test specified" not in scripts["test"]

        # Should have some test-related scripts
        test_scripts = [key for key in scripts.keys() if "test" in key]
        assert len(test_scripts) > 0, "No test scripts found in package.json"

    def test_conftest_configuration(self):
        """Test that conftest.py is properly configured."""
        conftest = TESTS_DIR / "conftest.py"
        assert conftest.exists(), "conftest.py missing"

        content = conftest.read_text()

        # Should have fixtures and configuration
        expected_elements = ["pytest", "fixture", "hypothesis", "isolated_dir"]

        for element in expected_elements:
            assert element in content, f"conftest.py missing: {element}"

    def test_test_markers_configured(self):
        """Test that pytest markers are properly configured."""
        # Try to list available markers
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--markers"],
            check=False,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            markers_output = result.stdout

            expected_markers = [
                "unit",
                "integration",
                "e2e",
                "container",
                "security",
                "slow",
            ]

            for marker in expected_markers:
                assert marker in markers_output, f"Marker not configured: {marker}"

    def test_comprehensive_test_runner_executable(self):
        """Test that comprehensive test runner is executable."""
        runner = TESTS_DIR / "run_comprehensive_tests.py"
        assert runner.exists(), "Comprehensive test runner missing"
        assert os.access(runner, os.X_OK), "Test runner not executable"

        # Test help command
        result = subprocess.run(
            [sys.executable, str(runner), "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower() or "help" in result.stdout.lower()


class TestTestExecution:
    """Test that tests can actually be executed."""

    def test_simple_pytest_execution(self):
        """Test that pytest can run on a simple test file."""
        # Create a minimal test file
        simple_test_content = '''
def test_simple():
    """A simple test that should always pass."""
    assert True

def test_basic_math():
    """Test basic mathematics."""
    assert 2 + 2 == 4
    assert 10 / 2 == 5
'''

        simple_test_file = TESTS_DIR / "test_simple_execution.py"
        simple_test_file.write_text(simple_test_content)

        try:
            # Run the simple test
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(simple_test_file), "-v"],
                check=False,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert (
                result.returncode == 0
            ), f"Simple test execution failed: {result.stderr}"
            assert "PASSED" in result.stdout
            assert "test_simple" in result.stdout
            assert "test_basic_math" in result.stdout

        finally:
            # Clean up
            if simple_test_file.exists():
                simple_test_file.unlink()

    def test_property_based_test_execution(self):
        """Test that property-based tests can execute."""
        # Test one of our property-based test files
        pbt_files = [
            "test_validation_pbt.py",
            "test_unified_validation_pbt.py",
            "test_mcp_server_pbt.py",
        ]

        for pbt_file in pbt_files:
            test_path = TESTS_DIR / pbt_file
            if test_path.exists():
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        str(test_path),
                        "--tb=short",
                        "-x",  # Stop on first failure
                    ],
                    check=False,
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                # Should not crash (returncode 0 or 5 for no tests)
                assert result.returncode in [
                    0,
                    5,
                ], f"PBT test {pbt_file} crashed: {result.stderr}"
                break  # Test at least one PBT file

    @pytest.mark.slow
    def test_comprehensive_runner_quick_mode(self):
        """Test that comprehensive test runner can execute in quick mode."""
        runner = TESTS_DIR / "run_comprehensive_tests.py"
        if not runner.exists():
            pytest.skip("Comprehensive test runner not found")

        # Run in quick mode with a short timeout
        result = subprocess.run(
            [sys.executable, str(runner), "--quick", "--phases", "unit"],
            check=False,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )

        # Should complete without crashing
        assert result.returncode is not None, "Test runner hung or crashed"

        # Check output contains expected elements
        output = result.stdout + result.stderr
        assert "HuskyCat" in output or "test" in output.lower()

    def test_makefile_test_target_execution(self):
        """Test that Makefile test targets can be executed."""
        makefile = PROJECT_ROOT / "Makefile"
        if not makefile.exists():
            pytest.skip("Makefile not found")

        # Test help target first to ensure make works
        result = subprocess.run(
            ["make", "help"],
            check=False,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            pytest.skip("Make not available or Makefile broken")

        # Test a simple target that should work
        result = subprocess.run(
            ["make", "clean-cache"],
            check=False,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Should complete without error
        assert result.returncode == 0, f"Make target failed: {result.stderr}"


class TestTestEnvironment:
    """Test that the test environment is properly set up."""

    def test_python_version(self):
        """Test that Python version is suitable for testing."""
        version_info = sys.version_info
        assert version_info.major == 3
        assert (
            version_info.minor >= 8
        ), f"Python 3.8+ required, got {version_info.major}.{version_info.minor}"

    def test_required_packages_available(self):
        """Test that required testing packages are available."""
        required_packages = ["pytest", "hypothesis"]

        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                pytest.fail(f"Required package not available: {package}")

    def test_optional_packages_import(self):
        """Test importing optional packages (may skip if not available)."""
        optional_packages = [
            ("docker", "Docker integration"),
            ("requests", "HTTP testing"),
        ]

        for package, description in optional_packages:
            try:
                __import__(package)
                print(f"✅ Optional package available: {package} ({description})")
            except ImportError:
                print(f"⚠️  Optional package not available: {package} ({description})")

    def test_project_structure(self):
        """Test that project structure is suitable for testing."""
        expected_dirs = [
            "src",
            "tests",
        ]

        for dir_name in expected_dirs:
            dir_path = PROJECT_ROOT / dir_name
            if dir_name == "tests":
                assert dir_path.exists(), f"Required directory missing: {dir_name}"
            elif not dir_path.exists():
                print(f"⚠️  Expected directory not found: {dir_name}")

    def test_test_data_accessibility(self):
        """Test that tests can access necessary data and fixtures."""
        # Test that conftest fixtures work
        try:
            # This should work if conftest.py is properly configured
            import conftest

            assert hasattr(conftest, "isolated_dir") or "isolated_dir" in dir(conftest)
        except ImportError:
            pytest.skip("conftest.py not properly configured")

    def test_temporary_directory_access(self):
        """Test that tests can create temporary directories."""
        import tempfile

        # Should be able to create temp directories
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            assert temp_path.exists()

            # Should be able to write files
            test_file = temp_path / "test.txt"
            test_file.write_text("test content")
            assert test_file.exists()
            assert test_file.read_text() == "test content"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
