#!/usr/bin/env python3
"""
Property-Based Testing for Unified Validation Engine
Using Hypothesis for comprehensive testing
"""

import pytest
from hypothesis import given, strategies as st, settings
from pathlib import Path
import tempfile
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from huskycat.unified_validation import ValidationEngine, ValidationResult


# Custom strategies for testing
@st.composite
def python_code(draw):
    """Generate valid Python code for testing"""
    constructs = [
        "x = 42",
        "def foo(): pass",
        "class Bar: pass",
        "import os",
        "if True: print('hello')",
        "for i in range(10): pass",
        "while False: break",
        "try:\n    pass\nexcept:\n    pass",
        "[x for x in range(10)]",
        "{k: v for k, v in enumerate(range(5))}",
    ]
    return draw(st.sampled_from(constructs))


@st.composite
def yaml_content(draw):
    """Generate valid YAML content for testing"""
    yaml_samples = [
        "key: value",
        "list:\n  - item1\n  - item2",
        "nested:\n  key: value\n  another: test",
        "number: 42",
        "boolean: true",
        "null_value: null",
        "multiline: |\n  This is a\n  multiline string",
    ]
    return draw(st.sampled_from(yaml_samples))


@st.composite
def shell_script(draw):
    """Generate valid shell scripts for testing"""
    scripts = [
        "#!/bin/bash\necho 'Hello World'",
        "#!/bin/sh\nexit 0",
        "#!/bin/bash\nfor i in {1..10}; do echo $i; done",
        "#!/bin/bash\nif [ -f file.txt ]; then\n  cat file.txt\nfi",
        "#!/bin/bash\nfunction test() { echo 'test'; }",
    ]
    return draw(st.sampled_from(scripts))


class TestValidationEngineProperties:
    """Property-based tests for ValidationEngine"""

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=50)
    def test_validation_engine_initialization(self, text):
        """Test that ValidationEngine initializes with any boolean flags"""
        engine = ValidationEngine(auto_fix=False, use_container=False)
        assert engine is not None
        assert hasattr(engine, "validate_file")
        assert hasattr(engine, "validate_directory")

    @given(python_code())
    @settings(max_examples=30)
    def test_python_validation_returns_results(self, code):
        """Test that Python validation always returns a list of results"""
        engine = ValidationEngine()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()

            try:
                results = engine.validate_file(Path(f.name))
                # Results should be a list (possibly empty)
                assert isinstance(results, list)
                # Each result should be a ValidationResult
                for result in results:
                    assert isinstance(result, ValidationResult)
                    assert hasattr(result, "messages")
                    assert hasattr(result, "errors")
                    assert hasattr(result, "warnings")
                    assert hasattr(result, "duration_ms")
                    assert hasattr(result, "tool")
            finally:
                os.unlink(f.name)

    @given(yaml_content())
    @settings(max_examples=30)
    def test_yaml_validation_returns_results(self, yaml):
        """Test that YAML validation always returns structured results"""
        engine = ValidationEngine()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml)
            f.flush()

            try:
                results = engine.validate_file(Path(f.name))
                assert isinstance(results, list)
                for result in results:
                    assert isinstance(result, ValidationResult)
                    assert result.tool in ["yamllint", "unknown"]
            finally:
                os.unlink(f.name)

    @given(shell_script())
    @settings(max_examples=30)
    def test_shell_validation_returns_results(self, script):
        """Test that shell script validation works correctly"""
        engine = ValidationEngine()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(script)
            f.flush()
            os.chmod(f.name, 0o755)

            try:
                results = engine.validate_file(Path(f.name))
                assert isinstance(results, list)
                for result in results:
                    assert isinstance(result, ValidationResult)
                    assert result.tool in ["shellcheck", "unknown"]
            finally:
                os.unlink(f.name)

    @given(st.lists(st.text(min_size=1), min_size=0, max_size=10))
    @settings(max_examples=20)
    def test_get_summary_properties(self, messages):
        """Test that get_summary produces consistent output"""
        engine = ValidationEngine()

        # Create mock results
        results = {}
        for i, msg in enumerate(messages):
            mock_result = ValidationResult(
                tool="test", filepath=f"file_{i}.py", success=False, messages=[msg], warnings=[msg]
            )
            results[f"file_{i}.py"] = [mock_result]

        summary = engine.get_summary(results)

        # Properties that should always hold
        assert "total_files" in summary
        assert "failed_files" in summary
        assert "passed_files" in summary
        assert "total_errors" in summary
        assert "total_warnings" in summary
        assert "success" in summary

        # Consistency checks
        assert summary["total_files"] == len(results)
        assert summary["failed_files"] <= summary["total_files"]
        assert summary["total_errors"] >= 0
        assert summary["total_warnings"] >= 0

    @given(st.booleans(), st.booleans())
    @settings(max_examples=10)
    def test_engine_configuration_flags(self, auto_fix, use_container):
        """Test that engine respects configuration flags"""
        engine = ValidationEngine(auto_fix=auto_fix, use_container=use_container)

        assert engine.auto_fix == auto_fix
        assert engine.use_container == use_container

    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=10),
            st.lists(st.text(min_size=1), min_size=0, max_size=5),
            min_size=0,
            max_size=10,
        )
    )
    @settings(max_examples=20)
    def test_summary_calculation_consistency(self, file_issues):
        """Test that summary calculations are internally consistent"""
        engine = ValidationEngine()

        # Create results from dictionary
        results = {}
        for filename, issues in file_issues.items():
            results[filename] = [
                ValidationResult(
                    tool="test", filepath=filename, success=False, messages=[msg], warnings=[msg]
                )
                for i, msg in enumerate(issues)
            ]

        summary = engine.get_summary(results)

        # Calculate expected values
        expected_total_files = len(results)
        expected_failed_files = sum(1 for file_results in results.values() 
                                   if any(not result.success for result in file_results))
        expected_total_errors = sum(result.error_count for file_results in results.values() 
                                  for result in file_results)
        expected_total_warnings = sum(result.warning_count for file_results in results.values() 
                                    for result in file_results)

        # Assert consistency
        assert summary["total_files"] == expected_total_files
        assert summary["failed_files"] == expected_failed_files
        assert summary["total_errors"] == expected_total_errors
        assert summary["total_warnings"] == expected_total_warnings


class TestValidationResultProperties:
    """Property-based tests for ValidationResult"""

    @given(
        st.text(min_size=1),
        st.text(min_size=1),
        st.booleans(),
        st.lists(st.text(), max_size=5),
        st.lists(st.text(), max_size=5),
        st.lists(st.text(), max_size=5),
    )
    def test_validation_result_creation(self, tool, filepath, success, messages, errors, warnings):
        """Test that ValidationResult can be created with any valid inputs"""
        result = ValidationResult(
            tool=tool, filepath=filepath, success=success, messages=messages, errors=errors, warnings=warnings
        )

        assert result.tool == tool
        assert result.filepath == filepath
        assert result.success == success
        assert result.messages == messages
        assert result.errors == errors
        assert result.warnings == warnings

    @given(
        st.text(min_size=1),
        st.text(min_size=1),
        st.booleans(),
        st.lists(st.text(), max_size=5),
        st.lists(st.text(), max_size=5),
        st.lists(st.text(), max_size=5),
    )
    def test_validation_result_to_dict(self, tool, filepath, success, messages, errors, warnings):
        """Test that to_dict method produces consistent output"""
        result = ValidationResult(
            tool=tool, filepath=filepath, success=success, messages=messages, errors=errors, warnings=warnings
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["tool"] == tool
        assert result_dict["filepath"] == filepath
        assert result_dict["success"] == success
        assert result_dict["messages"] == messages
        assert result_dict["errors"] == errors
        assert result_dict["warnings"] == warnings
        assert set(result_dict.keys()) == {
            "tool",
            "filepath",
            "success",
            "messages",
            "errors",
            "warnings",
            "fixed",
            "duration_ms",
        }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
