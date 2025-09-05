"""
Property-Based Testing for HuskyCat Validation Engine
Using Hypothesis for comprehensive testing
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
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
    # Generate various Python constructs
    constructs = [
        "x = 42",
        "def foo(): pass",
        "class Bar: pass",
        "import os",
        "if True: print('hello')",
        "for i in range(10): pass",
        "try: pass\nexcept: pass",
        "[x for x in range(10)]",
        "{k: v for k, v in enumerate(range(5))}",
        "lambda x: x * 2",
    ]

    num_lines = draw(st.integers(min_value=1, max_value=20))
    lines = [draw(st.sampled_from(constructs)) for _ in range(num_lines)]
    return "\n".join(lines)


@st.composite
def javascript_code(draw):
    """Generate valid JavaScript code for testing"""
    constructs = [
        "const x = 42;",
        "let y = 'hello';",
        "function foo() { return 42; }",
        "const bar = () => 42;",
        "class Baz { constructor() {} }",
        "if (true) { console.log('hello'); }",
        "for (let i = 0; i < 10; i++) {}",
        "try { } catch(e) { }",
        "[1, 2, 3].map(x => x * 2);",
        "const obj = { key: 'value' };",
    ]

    num_lines = draw(st.integers(min_value=1, max_value=20))
    lines = [draw(st.sampled_from(constructs)) for _ in range(num_lines)]
    return "\n".join(lines)


@st.composite
def yaml_content(draw):
    """Generate valid YAML content for testing"""
    # Simple YAML structures
    keys = draw(st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=10))
    values = draw(
        st.lists(
            st.one_of(st.integers(), st.text(), st.booleans()), min_size=1, max_size=10
        )
    )

    lines = []
    for k, v in zip(keys, values[: len(keys)]):
        if isinstance(v, bool):
            v = str(v).lower()
        elif isinstance(v, str):
            v = f'"{v}"' if " " in v or ":" in v else v
        lines.append(f"{k}: {v}")

    return "\n".join(lines)


@st.composite
def dockerfile_content(draw):
    """Generate valid Dockerfile content for testing"""
    base_images = ["alpine:3.19", "ubuntu:22.04", "python:3.11", "node:18"]
    base = draw(st.sampled_from(base_images))

    instructions = [
        f"FROM {base}",
        "WORKDIR /app",
        draw(
            st.one_of(
                st.just("RUN apt-get update"),
                st.just("RUN apk add --no-cache python3"),
                st.just("COPY . /app"),
                st.just("ENV FOO=bar"),
                st.just("EXPOSE 8080"),
                st.just('CMD ["python3", "app.py"]'),
            )
        ),
    ]

    num_instructions = draw(st.integers(min_value=2, max_value=10))
    for _ in range(num_instructions - 2):
        instructions.append(
            draw(
                st.sampled_from(
                    [
                        "RUN echo 'hello'",
                        "COPY src/ /app/src/",
                        "ENV KEY=value",
                        "USER nobody",
                        "VOLUME /data",
                    ]
                )
            )
        )

    return "\n".join(instructions)


class TestValidationEngineProperties:
    """Property-based tests for the validation engine"""

    @given(python_code())
    @settings(max_examples=50)
    def test_python_validation_never_crashes(self, code):
        """Python validation should never crash regardless of input"""
        engine = ValidationEngine()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            filepath = Path(f.name)

        try:
            results = engine.validate_file(filepath)

            # Properties to check
            assert isinstance(results, list)
            for result in results:
                assert isinstance(result, ValidationResult)
                assert result.tool in [
                    "python-black",
                    "python-flake8",
                    "python-mypy",
                    "python-bandit",
                    "python-ruff",
                ]
                assert isinstance(result.success, bool)
                assert isinstance(result.messages, list)
                assert result.filepath == str(filepath)
        finally:
            filepath.unlink()

    @given(javascript_code())
    @settings(max_examples=50)
    def test_javascript_validation_never_crashes(self, code):
        """JavaScript validation should never crash regardless of input"""
        engine = ValidationEngine()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(code)
            f.flush()
            filepath = Path(f.name)

        try:
            results = engine.validate_file(filepath)

            assert isinstance(results, list)
            for result in results:
                assert isinstance(result, ValidationResult)
                assert result.tool in ["js-eslint", "js-prettier"]
                assert isinstance(result.success, bool)
        finally:
            filepath.unlink()

    @given(yaml_content())
    @settings(max_examples=50)
    def test_yaml_validation_properties(self, content):
        """YAML validation should handle various content correctly"""
        engine = ValidationEngine()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(content)
            f.flush()
            filepath = Path(f.name)

        try:
            results = engine.validate_file(filepath)

            assert isinstance(results, list)
            if results:  # May have no YAML validator installed
                for result in results:
                    assert result.tool == "yaml-yamllint"
                    assert hasattr(result, "duration_ms")
                    assert result.duration_ms >= 0
        finally:
            filepath.unlink()

    @given(dockerfile_content())
    @settings(max_examples=30)
    def test_dockerfile_validation_properties(self, content):
        """Dockerfile validation should handle various content"""
        engine = ValidationEngine()

        with tempfile.NamedTemporaryFile(
            mode="w", prefix="Dockerfile", delete=False
        ) as f:
            f.write(content)
            f.flush()
            filepath = Path(f.name)

        try:
            results = engine.validate_file(filepath)

            assert isinstance(results, list)
            # Dockerfile validation is optional (hadolint might not be installed)
            for result in results:
                if result.tool == "docker-hadolint":
                    assert isinstance(result.success, bool)
                    assert isinstance(result.messages, list)
        finally:
            filepath.unlink()

    @given(
        st.lists(
            st.tuples(
                st.text(min_size=1, max_size=20),  # filename
                st.sampled_from([".py", ".js", ".yaml", ".sh"]),  # extension
            ),
            min_size=1,
            max_size=10,
        )
    )
    def test_batch_validation_properties(self, file_specs):
        """Batch validation should handle multiple files correctly"""
        engine = ValidationEngine()

        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)
        created_files = []

        try:
            # Create test files
            for name, ext in file_specs:
                # Sanitize filename
                safe_name = "".join(c for c in name if c.isalnum() or c in "_-")
                if not safe_name:
                    safe_name = "test"

                filepath = temp_path / f"{safe_name}{ext}"
                filepath.write_text(
                    "# Test content\nprint('hello')" if ext == ".py" else "test content"
                )
                created_files.append(filepath)

            # Validate directory
            results = engine.validate_directory(temp_path, recursive=False)

            # Properties to check
            assert isinstance(results, dict)
            for filepath_str, file_results in results.items():
                assert isinstance(file_results, list)
                for result in file_results:
                    assert isinstance(result, ValidationResult)
                    assert result.filepath == filepath_str

            # All created files should be validated (if validators available)
            for filepath in created_files:
                validators = engine.get_validators_for_file(filepath)
                if validators:  # Only check if we have validators for this file type
                    assert str(filepath) in results or not validators

        finally:
            # Cleanup
            import shutil

            shutil.rmtree(temp_dir)

    @given(st.booleans())
    def test_fix_mode_properties(self, fix_mode):
        """Fix mode should properly indicate when fixes are applied"""
        engine = ValidationEngine()

        # Create a file with formatting issues
        code = "x=1+2\ny=3+4\n"  # Spacing issues for Black

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            filepath = Path(f.name)

        try:
            results = engine.validate_file(filepath, fix=fix_mode)

            for result in results:
                if result.tool == "python-black" and fix_mode:
                    # Black should report if it fixed the file
                    assert isinstance(result.fixed, bool)
                else:
                    # Non-fix mode or other tools shouldn't claim fixes
                    assert result.fixed == False or (result.fixed and fix_mode)
        finally:
            filepath.unlink()

    @given(
        st.lists(
            st.sampled_from(["__pycache__", ".git", "node_modules", ".venv", "test"]),
            min_size=0,
            max_size=5,
        )
    )
    def test_exclusion_patterns(self, exclude_patterns):
        """Exclusion patterns should properly filter files"""
        engine = ValidationEngine()

        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)

        try:
            # Create files in excluded directories
            for pattern in exclude_patterns:
                excluded_dir = temp_path / pattern
                excluded_dir.mkdir(exist_ok=True)
                (excluded_dir / "test.py").write_text("print('excluded')")

            # Create a file that should be validated
            (temp_path / "included.py").write_text("print('included')")

            # Validate with exclusions
            results = engine.validate_directory(
                temp_path, recursive=True, exclude_patterns=exclude_patterns
            )

            # Check that excluded files are not in results
            for pattern in exclude_patterns:
                excluded_file = str(temp_path / pattern / "test.py")
                assert excluded_file not in results

            # Check that included file is validated (if validators available)
            included_file = str(temp_path / "included.py")
            validators = engine.get_validators_for_file(Path(included_file))
            if validators:
                assert included_file in results

        finally:
            import shutil

            shutil.rmtree(temp_dir)


class TestValidationResultProperties:
    """Property-based tests for ValidationResult"""

    @given(
        tool=st.text(min_size=1, max_size=50),
        filepath=st.text(min_size=1, max_size=200),
        success=st.booleans(),
        messages=st.lists(st.text(), max_size=100),
        fixed=st.booleans(),
        duration_ms=st.integers(min_value=0, max_value=60000),
    )
    def test_validation_result_serialization(
        self, tool, filepath, success, messages, fixed, duration_ms
    ):
        """ValidationResult should serialize correctly"""
        result = ValidationResult(
            tool=tool,
            filepath=filepath,
            success=success,
            messages=messages,
            fixed=fixed,
            duration_ms=duration_ms,
        )

        # Test to_dict
        data = result.to_dict()
        assert data["tool"] == tool
        assert data["filepath"] == filepath
        assert data["success"] == success
        assert data["messages"] == messages
        assert data["fixed"] == fixed
        assert data["duration_ms"] == duration_ms

        # Test that it's JSON serializable
        import json

        json_str = json.dumps(data)
        restored = json.loads(json_str)
        assert restored == data


class TestEngineInvariants:
    """Test invariants that should always hold"""

    @given(st.data())
    def test_validator_discovery_deterministic(self, data):
        """Validator discovery should be deterministic"""
        engine1 = ValidationEngine()
        engine2 = ValidationEngine()

        # Same validators should be discovered
        assert set(engine1.validators.keys()) == set(engine2.validators.keys())

        # Extension map should be the same
        assert engine1._extension_map.keys() == engine2._extension_map.keys()

    @given(
        st.sampled_from(
            [
                Path("test.py"),
                Path("test.js"),
                Path("test.yaml"),
                Path("Dockerfile"),
                Path("test.sh"),
                Path("unknown.xyz"),
            ]
        )
    )
    def test_get_validators_idempotent(self, filepath):
        """Getting validators for a file should be idempotent"""
        engine = ValidationEngine()

        validators1 = engine.get_validators_for_file(filepath)
        validators2 = engine.get_validators_for_file(filepath)

        # Should return the same validators in the same order
        assert [v.name for v in validators1] == [v.name for v in validators2]

    @given(st.text(min_size=1, max_size=100))
    def test_unknown_tool_handling(self, tool_name):
        """Unknown tools should be handled gracefully"""
        assume(
            tool_name not in ["python-black", "python-flake8", "js-eslint"]
        )  # Skip known tools

        engine = ValidationEngine()

        with tempfile.NamedTemporaryFile(suffix=".py") as f:
            results = engine.validate_file(Path(f.name), tools=[tool_name])

            assert len(results) == 1
            assert results[0].tool == tool_name
            assert results[0].success == False
            assert "Unknown tool" in str(results[0].messages)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
