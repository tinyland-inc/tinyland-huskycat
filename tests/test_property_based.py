#!/usr/bin/env python3
"""Property-based tests using Hypothesis for core functionality."""

import pytest
from hypothesis import given, assume, strategies as st, example
from typing import List, Dict, Any
import tempfile
import os
from pathlib import Path

# Import the sample code functions for testing
# In a real implementation, these would be imported from the actual modules
def calculate_sum(numbers: List[int]) -> int:
    """Calculate the sum of a list of numbers."""
    return sum(numbers)

def process_data(data: List[str]) -> List[str]:
    """Process string data by stripping and converting to uppercase."""
    return [item.strip().upper() for item in data if item.strip()]

def validate_python_code(code: str) -> Dict[str, Any]:
    """Validate Python code syntax and return analysis."""
    try:
        compile(code, '<test>', 'exec')
        return {"valid": True, "errors": []}
    except SyntaxError as e:
        return {"valid": False, "errors": [str(e)]}

def format_code_with_black(code: str) -> str:
    """Simulate code formatting with black."""
    # Simplified implementation for testing
    lines = code.split('\n')
    formatted_lines = []
    for line in lines:
        # Remove trailing whitespace
        formatted_line = line.rstrip()
        formatted_lines.append(formatted_line)
    return '\n'.join(formatted_lines)


class TestCalculateSum:
    """Property-based tests for calculate_sum function."""
    
    @given(st.lists(st.integers()))
    def test_sum_equals_builtin(self, numbers: List[int]):
        """Property: Our sum should equal Python's builtin sum."""
        result = calculate_sum(numbers)
        expected = sum(numbers)
        assert result == expected
    
    @given(st.lists(st.integers()))
    def test_sum_is_commutative(self, numbers: List[int]):
        """Property: Sum should be the same regardless of order."""
        result1 = calculate_sum(numbers)
        result2 = calculate_sum(numbers[::-1])  # Reverse order
        assert result1 == result2
    
    @given(st.lists(st.integers(), min_size=1))
    def test_sum_with_zero_is_identity(self, numbers: List[int]):
        """Property: Adding zero should not change the sum."""
        original_sum = calculate_sum(numbers)
        with_zero = numbers + [0]
        new_sum = calculate_sum(with_zero)
        assert original_sum == new_sum
    
    @given(st.integers(), st.lists(st.integers()))
    def test_sum_distributive_property(self, n: int, numbers: List[int]):
        """Property: sum(numbers) + n == sum(numbers + [n])."""
        original_sum = calculate_sum(numbers)
        extended_sum = calculate_sum(numbers + [n])
        assert extended_sum == original_sum + n
    
    @example([])  # Edge case: empty list
    @given(st.lists(st.integers()))
    def test_empty_list_returns_zero(self, numbers: List[int]):
        """Property: Empty list should return 0."""
        if not numbers:
            assert calculate_sum(numbers) == 0


class TestProcessData:
    """Property-based tests for process_data function."""
    
    @given(st.lists(st.text()))
    def test_process_data_never_crashes(self, data: List[str]):
        """Property: Process data should never crash on any input."""
        try:
            result = process_data(data)
            assert isinstance(result, list)
        except Exception as e:
            pytest.fail(f"process_data crashed with input {data}: {e}")
    
    @given(st.lists(st.text(min_size=1).filter(lambda x: x.strip())))
    def test_processed_data_is_uppercase(self, data: List[str]):
        """Property: All processed strings should be uppercase."""
        result = process_data(data)
        for item in result:
            assert item.isupper(), f"Item '{item}' is not uppercase"
    
    @given(st.lists(st.text()))
    def test_no_empty_strings_in_result(self, data: List[str]):
        """Property: Result should contain no empty strings."""
        result = process_data(data)
        for item in result:
            assert item.strip() != "", f"Empty string found in result: {result}"
    
    @given(st.lists(st.text()))
    def test_result_length_bounded(self, data: List[str]):
        """Property: Result length should not exceed input length."""
        result = process_data(data)
        assert len(result) <= len(data)
    
    @given(st.lists(st.text().filter(lambda x: not x.strip())))
    def test_whitespace_only_returns_empty(self, data: List[str]):
        """Property: Whitespace-only strings should result in empty list."""
        result = process_data(data)
        assert result == []


class TestCodeValidation:
    """Property-based tests for code validation functions."""
    
    @given(st.text())
    def test_validate_never_crashes(self, code: str):
        """Property: Code validation should never crash."""
        try:
            result = validate_python_code(code)
            assert isinstance(result, dict)
            assert "valid" in result
            assert "errors" in result
            assert isinstance(result["valid"], bool)
            assert isinstance(result["errors"], list)
        except Exception as e:
            pytest.fail(f"validate_python_code crashed: {e}")
    
    @given(st.text().filter(lambda x: 'def ' in x or 'class ' in x))
    def test_code_with_definitions_analysis(self, code: str):
        """Property: Code with definitions should be analyzable."""
        result = validate_python_code(code)
        # Should not crash and should return structured response
        assert isinstance(result["valid"], bool)
    
    @example("print('hello')")  # Valid Python
    @example("if True")  # Invalid Python
    @given(st.text())
    def test_validation_correctness(self, code: str):
        """Property: Validation should correctly identify syntax errors."""
        result = validate_python_code(code)
        
        # Test against Python's own compiler
        try:
            compile(code, '<test>', 'exec')
            python_valid = True
        except SyntaxError:
            python_valid = False
        
        # Our validator should match Python's compiler
        assert result["valid"] == python_valid


class TestCodeFormatting:
    """Property-based tests for code formatting."""
    
    @given(st.text())
    def test_format_never_crashes(self, code: str):
        """Property: Code formatting should never crash."""
        try:
            result = format_code_with_black(code)
            assert isinstance(result, str)
        except Exception as e:
            pytest.fail(f"format_code_with_black crashed: {e}")
    
    @given(st.text())
    def test_format_removes_trailing_whitespace(self, code: str):
        """Property: Formatting should remove trailing whitespace."""
        result = format_code_with_black(code)
        lines = result.split('\n')
        for line in lines:
            assert not line.endswith(' '), f"Line still has trailing space: '{line}'"
            assert not line.endswith('\t'), f"Line still has trailing tab: '{line}'"
    
    @given(st.text())
    def test_format_idempotency(self, code: str):
        """Property: Formatting should be idempotent."""
        first_format = format_code_with_black(code)
        second_format = format_code_with_black(first_format)
        assert first_format == second_format


class TestFileOperations:
    """Property-based tests for file operations."""
    
    @given(st.text())
    def test_write_and_read_consistency(self, content: str):
        """Property: Writing and reading a file should be consistent."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
            try:
                f.write(content)
                f.flush()
                
                with open(f.name, 'r') as read_f:
                    read_content = read_f.read()
                
                assert read_content == content
            finally:
                os.unlink(f.name)
    
    @given(st.lists(st.text(), min_size=1))
    def test_multiple_file_operations(self, contents: List[str]):
        """Property: Multiple file operations should be consistent."""
        temp_files = []
        try:
            # Write all files
            for i, content in enumerate(contents):
                temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=f'_{i}.txt')
                temp_file.write(content)
                temp_file.close()
                temp_files.append(temp_file.name)
            
            # Read all files and verify
            for i, temp_file in enumerate(temp_files):
                with open(temp_file, 'r') as f:
                    read_content = f.read()
                assert read_content == contents[i]
                
        finally:
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except OSError:
                    pass


class TestConfigurationHandling:
    """Property-based tests for configuration handling."""
    
    @given(st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.one_of(
            st.text(),
            st.integers(),
            st.booleans(),
            st.floats(allow_nan=False, allow_infinity=False)
        ),
        min_size=1
    ))
    def test_config_serialization(self, config: Dict[str, Any]):
        """Property: Configuration should serialize and deserialize correctly."""
        import json
        
        # Serialize to JSON
        json_str = json.dumps(config)
        
        # Deserialize from JSON
        restored_config = json.loads(json_str)
        
        # Should be identical
        assert restored_config == config
    
    @given(st.dictionaries(
        keys=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd", "_"))),
        values=st.one_of(st.text(), st.integers(min_value=0, max_value=1000), st.booleans()),
        min_size=1,
        max_size=10
    ))
    def test_config_validation_structure(self, config: Dict[str, Any]):
        """Property: Configuration should maintain structure invariants."""
        # All keys should be strings
        for key in config.keys():
            assert isinstance(key, str)
            assert len(key) > 0
        
        # All values should be of expected types
        for value in config.values():
            assert isinstance(value, (str, int, bool))


@pytest.mark.slow
class TestPerformanceProperties:
    """Property-based performance tests."""
    
    @given(st.lists(st.integers(), min_size=1000, max_size=10000))
    def test_sum_performance_scales_linearly(self, numbers: List[int]):
        """Property: Sum performance should scale roughly linearly."""
        import time
        
        start_time = time.perf_counter()
        result = calculate_sum(numbers)
        end_time = time.perf_counter()
        
        duration = end_time - start_time
        
        # Should complete within reasonable time (adjust based on hardware)
        max_time = len(numbers) * 0.000001  # 1 microsecond per number
        assert duration < max_time, f"Sum took too long: {duration}s for {len(numbers)} numbers"
        
        # Verify correctness wasn't sacrificed for speed
        assert result == sum(numbers)


# Integration with pytest-benchmark if available
try:
    import pytest_benchmark
    
    class TestBenchmarkProperties:
        """Benchmark-based property tests."""
        
        @given(st.lists(st.integers(), min_size=100, max_size=1000))
        def test_sum_benchmark(self, benchmark, numbers: List[int]):
            """Benchmark sum function with property-based inputs."""
            result = benchmark(calculate_sum, numbers)
            assert result == sum(numbers)
            
except ImportError:
    # pytest-benchmark not available, skip benchmark tests
    pass