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
from unified_validation import ValidationEngine, ValidationResult


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
                    assert hasattr(result, "line")
                    assert hasattr(result, "column")
                    assert hasattr(result, "message")
                    assert hasattr(result, "severity")
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
                line=i, column=0, message=msg, severity="warning", tool="test"
            )
            results[f"file_{i}.py"] = [mock_result]

        summary = engine.get_summary(results)

        # Properties that should always hold
        assert "total_files" in summary
        assert "files_with_issues" in summary
        assert "total_issues" in summary
        assert "by_severity" in summary
        assert "by_tool" in summary

        # Consistency checks
        assert summary["total_files"] == len(results)
        assert summary["files_with_issues"] <= summary["total_files"]
        assert summary["total_issues"] >= 0

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
                    line=i, column=0, message=msg, severity="warning", tool="test"
                )
                for i, msg in enumerate(issues)
            ]

        summary = engine.get_summary(results)

        # Calculate expected values
        expected_total_files = len(results)
        expected_files_with_issues = sum(1 for v in results.values() if v)
        expected_total_issues = sum(len(v) for v in results.values())

        # Assert consistency
        assert summary["total_files"] == expected_total_files
        assert summary["files_with_issues"] == expected_files_with_issues
        assert summary["total_issues"] == expected_total_issues


class TestValidationResultProperties:
    """Property-based tests for ValidationResult"""

    @given(
        st.integers(),
        st.integers(),
        st.text(min_size=1),
        st.sampled_from(["error", "warning", "info"]),
        st.text(min_size=1),
    )
    def test_validation_result_creation(self, line, column, message, severity, tool):
        """Test that ValidationResult can be created with any valid inputs"""
        result = ValidationResult(
            line=line, column=column, message=message, severity=severity, tool=tool
        )

        assert result.line == line
        assert result.column == column
        assert result.message == message
        assert result.severity == severity
        assert result.tool == tool

    @given(
        st.integers(),
        st.integers(),
        st.text(min_size=1),
        st.sampled_from(["error", "warning", "info"]),
        st.text(min_size=1),
    )
    def test_validation_result_to_dict(self, line, column, message, severity, tool):
        """Test that to_dict method produces consistent output"""
        result = ValidationResult(
            line=line, column=column, message=message, severity=severity, tool=tool
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["line"] == line
        assert result_dict["column"] == column
        assert result_dict["message"] == message
        assert result_dict["severity"] == severity
        assert result_dict["tool"] == tool
        assert set(result_dict.keys()) == {
            "line",
            "column",
            "message",
            "severity",
            "tool",
        }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
