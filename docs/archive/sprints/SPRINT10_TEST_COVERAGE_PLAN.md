# Sprint 10: Test Coverage Improvement Plan

**Status**: Action Required
**Priority**: HIGH (Blocking Production Release)
**Current Coverage**: 22.6% (918/4064 statements)
**Target Coverage**: 80%
**Gap**: 57.4%

## Current Coverage Analysis

### Sprint 10 Components Coverage

| Component | Lines | Covered | Coverage | Target | Gap |
|-----------|-------|---------|----------|--------|-----|
| **git_hooks_nonblocking.py** | 94 | 50 | 53.2% | 80% | -26.8% |
| **process_manager.py** | 252 | 129 | 51.2% | 80% | -28.8% |
| **parallel_executor.py** | 147 | 105 | 71.4% | 80% | -8.6% |
| **tui.py** | 147 | 58 | 39.5% | 80% | -40.5% |
| **unified_validation.py** | 838 | 185 | 22.1% | 80% | -57.9% |
| **config.py** | 219 | ~50 | ~23% | 80% | -57% |
| **tool_extractor.py** | 229 | ~30 | ~13% | 80% | -67% |

**Total Sprint 10 Components**: ~1,926 lines
**Estimated Coverage Needed**: ~1,540 lines (80%)
**Current Coverage**: ~607 lines
**Lines to Cover**: ~933 lines

## Priority Areas

### Priority 1: Critical Path Coverage (Days 1-2)

#### 1.1 Non-Blocking Adapter (git_hooks_nonblocking.py)
**Current**: 53.2% | **Target**: 80% | **Effort**: 1 day

**Missing Coverage**:
```python
# Line 61-75: ProcessManager initialization with cache_dir
# Line 85-110: Tool loading from validators
# Line 126-140: Fork validation call
# Line 150-180: Child validation execution
# Line 200-220: Error recovery paths
```

**Tests to Add**:
```python
# tests/test_nonblocking_adapter_extended.py

def test_adapter_cache_dir_configuration():
    """Test custom cache directory"""
    adapter = NonBlockingGitHooksAdapter(cache_dir=Path("/custom"))
    assert adapter.process_manager.cache_dir == Path("/custom")

def test_adapter_tool_loading_all_types():
    """Test loading tools for different file types"""
    files = ["file.py", "file.js", "file.sh", "file.yaml"]
    tools = adapter._get_all_tools(files)
    assert "python-black" in tools
    assert "js-eslint" in tools
    assert "shellcheck" in tools
    assert "yamllint" in tools

def test_fork_validation_error_handling():
    """Test fork failure scenarios"""
    with mock.patch('os.fork', side_effect=OSError):
        result = adapter.execute("validate", ["file.py"])
        assert not result.success
        assert "fork failed" in result.message

def test_child_validation_exception_handling():
    """Test child process error recovery"""
    # Mock tool that raises exception
    # Verify child logs error and exits with code 1

def test_previous_failure_user_prompt():
    """Test user prompt for previous failures"""
    # Create previous failed run
    # Mock TTY and user input
    # Verify prompt shown and response handled
```

#### 1.2 Process Manager (process_manager.py)
**Current**: 51.2% | **Target**: 80% | **Effort**: 1 day

**Missing Coverage**:
```python
# Line 80-100: Fork failure handling
# Line 120-150: Child process I/O redirection
# Line 180-200: Stale PID cleanup edge cases
# Line 220-240: Concurrent validation detection
# Line 260-280: Zombie process cleanup
```

**Tests to Add**:
```python
# tests/test_process_manager_extended.py

def test_fork_failure_handling():
    """Test fork failure scenarios"""
    manager = ProcessManager()
    with mock.patch('os.fork', side_effect=OSError("Resource unavailable")):
        pid = manager.fork_validation(["file.py"], "cmd", [])
        assert pid == -1

def test_child_io_redirection():
    """Test child process stdout/stderr redirection"""
    # Verify log files created
    # Verify stdout/stderr captured

def test_stale_pid_cleanup_nonexistent_process():
    """Test cleanup of PIDs for dead processes"""
    # Create PID file for fake process
    # Run cleanup
    # Verify PID file removed

def test_concurrent_validation_detection():
    """Test detection of overlapping validations"""
    # Start validation on files A, B
    # Try to start validation on files B, C
    # Verify second validation blocked

def test_zombie_process_cleanup_multiple():
    """Test reaping multiple completed children"""
    # Fork multiple processes
    # Complete them
    # Run cleanup
    # Verify all reaped
```

### Priority 2: User-Facing Components (Days 3-4)

#### 2.1 TUI Framework (tui.py)
**Current**: 39.5% | **Target**: 80% | **Effort**: 1 day

**Missing Coverage**:
```python
# Line 50-80: Tool status updates from multiple threads
# Line 100-130: Render method variations
# Line 150-180: Context manager error handling
# Line 200-230: Non-TTY fallback
```

**Tests to Add**:
```python
# tests/test_tui_extended.py

def test_concurrent_tool_updates():
    """Test thread-safe updates from multiple threads"""
    tui = ValidationTUI()
    tui.start(["tool1", "tool2", "tool3"])

    def update_tool(name, status):
        for i in range(100):
            tui.update_tool(name, status)

    threads = [
        threading.Thread(target=update_tool, args=("tool1", "running"))
        for _ in range(10)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Verify no race conditions, all updates processed

def test_render_with_various_states():
    """Test rendering with different tool states"""
    # Test all combinations of tool states
    # Verify table format correct

def test_context_manager_error_handling():
    """Test context manager cleanup on exception"""
    with pytest.raises(Exception):
        with validation_tui() as tui:
            raise Exception("Test error")
    # Verify TUI stopped and cleaned up

def test_non_tty_fallback():
    """Test graceful degradation in non-TTY"""
    with mock.patch('sys.stdout.isatty', return_value=False):
        tui = ValidationTUI()
        # Verify silent operation, no crashes
```

#### 2.2 Tool Extractor (tool_extractor.py)
**Current**: ~13% | **Target**: 80% | **Effort**: 1 day

**Missing Coverage**:
```python
# Line 40-70: Version checking and comparison
# Line 80-110: Tool extraction from bundle
# Line 120-150: Permission setting
# Line 160-190: PATH setup
```

**Tests to Add**:
```python
# tests/test_tool_extractor_extended.py

def test_version_mismatch_triggers_extraction():
    """Test that version change triggers re-extraction"""
    # Extract tools with version 1.0
    # Change bundled version to 2.0
    # Re-run extraction
    # Verify tools re-extracted

def test_extraction_permission_errors():
    """Test handling of permission errors during extraction"""
    with mock.patch('os.chmod', side_effect=PermissionError):
        # Verify appropriate error handling

def test_partial_extraction_cleanup():
    """Test cleanup of partial extraction on error"""
    # Start extraction
    # Simulate error mid-extraction
    # Verify partial files cleaned up

def test_path_setup_multiple_calls():
    """Test PATH setup is idempotent"""
    # Call setup_path() multiple times
    # Verify PATH only modified once
```

### Priority 3: Core Refactors (Days 5-6)

#### 3.1 Unified Validation (unified_validation.py)
**Current**: 22.1% | **Target**: 80% | **Effort**: 2 days

**Missing Coverage**:
```python
# Line 100-150: Execution mode detection
# Line 180-230: Tool path resolution
# Line 260-300: Bundled tool execution
# Line 320-360: Container fallback
# Line 400-450: Validator delegation
```

**Tests to Add**:
```python
# tests/test_unified_validation_extended.py

def test_execution_mode_detection_bundled():
    """Test detection of bundled mode"""
    with mock.patch('sys.frozen', True, create=True):
        with mock.patch('pathlib.Path.exists', return_value=True):
            mode = validator._get_execution_mode()
            assert mode == "bundled"

def test_tool_path_resolution_priority():
    """Test tool resolution follows priority order"""
    # Create bundled, local, and container tools
    # Verify bundled chosen first

def test_bundled_tool_execution_success():
    """Test successful execution of bundled tool"""
    # Mock bundled tool
    # Execute validator
    # Verify correct tool path used

def test_container_fallback_behavior():
    """Test fallback to container when no local tools"""
    # Remove local tools
    # Mock container runtime exists
    # Execute validator
    # Verify container used with warning logged

def test_validator_delegation_error_handling():
    """Test error handling in validator delegation"""
    # Mock validator that raises exception
    # Verify error caught and logged
```

#### 3.2 Config System (config.py)
**Current**: ~23% | **Target**: 80% | **Effort**: 1 day

**Tests to Add**:
```python
# tests/test_config_extended.py

def test_config_file_loading_yaml():
    """Test loading config from YAML file"""

def test_config_file_loading_json():
    """Test loading config from JSON file"""

def test_environment_variable_overrides():
    """Test env vars override config file"""

def test_feature_flag_cascading():
    """Test feature flag inheritance"""

def test_invalid_config_handling():
    """Test handling of malformed config"""
```

## Test Organization Strategy

### Test File Structure

```
tests/
├── test_sprint10_integration.py     (18 tests) ✅ Complete
├── test_sprint10_e2e.py              (14 tests) ✅ Complete
├── test_sprint10_performance.py     (15 tests) ✅ Complete
├── test_sprint10_regression.py      (30 tests) ✅ Complete
│
├── test_nonblocking_adapter.py      (10 tests) ✅ Complete
├── test_nonblocking_adapter_extended.py  (NEW - 15 tests)
│
├── test_process_manager.py          (17 tests) ✅ Complete
├── test_process_manager_extended.py     (NEW - 15 tests)
│
├── test_tui.py                      (26 tests) ✅ Complete
├── test_tui_extended.py                 (NEW - 15 tests)
│
├── test_parallel_executor.py        (18 tests) ✅ Complete
├── test_parallel_executor_extended.py   (NEW - 10 tests)
│
├── test_tool_extractor.py          (0 tests) ❌ Missing
├── test_tool_extractor_extended.py     (NEW - 20 tests)
│
├── test_execution_modes.py          (22 tests) ✅ Complete
├── test_execution_modes_extended.py    (NEW - 25 tests)
│
└── test_config_extended.py             (NEW - 15 tests)
```

**New Tests**: ~130 tests across 7 new files

## Coverage Improvement Roadmap

### Week 1: Critical Path

**Day 1**: Non-Blocking Adapter Extended Tests
- File: `test_nonblocking_adapter_extended.py`
- Tests: 15
- Coverage gain: +15%
- Target: git_hooks_nonblocking.py to 70%

**Day 2**: Process Manager Extended Tests
- File: `test_process_manager_extended.py`
- Tests: 15
- Coverage gain: +15%
- Target: process_manager.py to 70%

**Day 3**: TUI Extended Tests
- File: `test_tui_extended.py`
- Tests: 15
- Coverage gain: +20%
- Target: tui.py to 60%

**Day 4**: Tool Extractor Complete Tests
- File: `test_tool_extractor_extended.py`
- Tests: 20
- Coverage gain: +40%
- Target: tool_extractor.py to 60%

**Day 5**: Execution Modes Extended Tests
- File: `test_execution_modes_extended.py`
- Tests: 25
- Coverage gain: +30%
- Target: unified_validation.py to 55%

**Day 6**: Config System Tests
- File: `test_config_extended.py`
- Tests: 15
- Coverage gain: +35%
- Target: config.py to 60%

**Day 7**: Final Coverage Push
- Fill remaining gaps
- Target: All components to 80%+

### Expected Final Coverage

| Component | Current | Week 1 Target | Final Target |
|-----------|---------|---------------|--------------|
| git_hooks_nonblocking.py | 53.2% | 70% | 80%+ |
| process_manager.py | 51.2% | 70% | 80%+ |
| parallel_executor.py | 71.4% | 75% | 85%+ |
| tui.py | 39.5% | 60% | 80%+ |
| unified_validation.py | 22.1% | 55% | 80%+ |
| config.py | 23% | 60% | 80%+ |
| tool_extractor.py | 13% | 60% | 80%+ |
| **Overall** | **22.6%** | **60%+** | **80%+** |

## Test Quality Guidelines

### 1. Test Independence
- Each test must be fully independent
- Use fixtures for setup/teardown
- No shared state between tests

### 2. Mock Appropriately
- Mock external dependencies (filesystem, network, processes)
- Don't mock code under test
- Use `unittest.mock` or `pytest-mock`

### 3. Test Names
- Descriptive: `test_fork_failure_handling()`
- Not: `test_fork()`

### 4. Assertions
- Multiple assertions per test are OK
- Test one behavior per test
- Use descriptive assertion messages

### 5. Edge Cases
- Always test: success, failure, edge cases
- Consider: empty input, null, invalid types
- Test concurrent execution

### 6. Performance Tests
- Separate from unit tests
- Use `pytest-benchmark` for consistent results
- Set clear performance thresholds

## CI Integration

### Update `.gitlab-ci.yml`

```yaml
test:coverage:
  stage: test
  script:
    - uv run pytest --cov=src.huskycat --cov-report=term --cov-report=html --cov-report=json
    - |
      COVERAGE=$(python3 -c "import json; print(json.load(open('coverage.json'))['totals']['percent_covered'])")
      if (( $(echo "$COVERAGE < 80" | bc -l) )); then
        echo "Coverage $COVERAGE% is below 80% threshold"
        exit 1
      fi
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
    paths:
      - htmlcov/
      - coverage.json
```

## Success Criteria

✅ **Done When**:
1. Overall coverage ≥ 80%
2. All Sprint 10 components ≥ 80%
3. All new tests passing
4. CI coverage gate enforced
5. Coverage report in MR artifacts

## Effort Estimation

- **Total Effort**: 7 days (1 full sprint)
- **Tests to Write**: ~130 new tests
- **Lines of Test Code**: ~3,000 lines
- **Coverage Gain**: +57.4%

## Next Steps

1. Create issue: "Sprint 10: Test Coverage Improvement"
2. Assign to: Testing specialist
3. Set milestone: Sprint 10 Cleanup
4. Priority: HIGH
5. Start: Immediately after Sprint 10 merge
