# HuskyCats Testing Suite

## Overview

This comprehensive testing suite implements a multi-layered testing strategy for the HuskyCats project, emphasizing quality, reliability, and maintainability through systematic validation at all levels.

## Testing Philosophy

- **No Mocks in Implementation**: Test against real services when possible
- **Inline Assertions**: Validate throughout execution, not just at the end
- **Continuous Validation**: Active testing during development
- **Property-Based Testing**: Use Hypothesis for comprehensive input validation
- **Active Debugging**: Compilation errors are opportunities, not roadblocks

## Test Structure

```
tests/
├── conftest.py                    # Pytest configuration and fixtures
├── pytest.ini                    # Pytest settings and markers
├── run_tests.py                   # Intelligent test runner
├── test_sample.py                 # Sample test (existing)
├── e2e-mcp-server.test.js         # MCP server E2E tests (existing)
├── test_property_based.py         # Property-based tests with Hypothesis
├── test_git_hooks.py             # Git hooks validation tests
├── test_e2e_deployment.py        # End-to-end deployment tests
├── test_strategy.md              # Comprehensive testing strategy
├── quality_checklist.md          # Quality gates and checklists
└── test-reports/                 # Generated test reports
```

## Quick Start

### Prerequisites

Install required dependencies:

```bash
pip install pytest hypothesis pytest-cov pytest-html requests docker
```

### Running Tests

Use the intelligent test runner for different scenarios:

```bash
# Fast development tests (< 30 seconds)
./tests/run_tests.py fast

# Full unit test suite with coverage
./tests/run_tests.py unit

# Property-based tests with Hypothesis
./tests/run_tests.py property

# Integration tests
./tests/run_tests.py integration

# Security-focused tests
./tests/run_tests.py security

# End-to-end tests (requires services)
./tests/run_tests.py e2e

# Container tests (requires Docker)
./tests/run_tests.py container

# Performance benchmarks
./tests/run_tests.py performance

# Complete test suite
./tests/run_tests.py all

# CI/CD optimized test sequence
./tests/run_tests.py ci

# Validate test environment
./tests/run_tests.py validate
```

### Direct Pytest Usage

For advanced usage, run pytest directly:

```bash
# Run specific test file
pytest tests/test_property_based.py -v

# Run tests with specific markers
pytest -m "unit and not slow" -v

# Run with coverage
pytest --cov=src --cov-report=html tests/

# Run specific test pattern
pytest -k "test_calculate_sum" -v
```

## Test Categories and Markers

### Test Markers

- `unit`: Fast, isolated unit tests
- `integration`: Tests component interactions
- `e2e`: End-to-end workflow tests
- `security`: Security-focused validations
- `performance`: Performance and benchmarking tests
- `property`: Property-based tests with Hypothesis
- `container`: Container-related tests
- `slow`: Long-running tests (> 5 seconds)
- `network`: Tests requiring network access
- `docker`: Tests requiring Docker
- `git`: Git operation tests
- `mcp`: MCP server tests
- `hooks`: Git hooks tests
- `deployment`: Deployment tests

### Test Selection Examples

```bash
# Run only fast tests
pytest -m "not slow and not e2e"

# Run security and unit tests
pytest -m "security or unit"

# Exclude container tests
pytest -m "not container"

# Run property-based tests only
pytest -m "property"
```

## Key Testing Components

### 1. Property-Based Testing (`test_property_based.py`)

Uses Hypothesis to generate diverse test inputs and validate properties:

- **Mathematical Properties**: Commutativity, associativity, identity
- **Data Processing**: Input validation, output consistency
- **Error Handling**: Graceful failure on invalid inputs
- **Performance Properties**: Linear scaling, bounded execution time

```python
@given(st.lists(st.integers()))
def test_sum_equals_builtin(numbers: List[int]):
    """Property: Our sum should equal Python's builtin sum."""
    result = calculate_sum(numbers)
    expected = sum(numbers)
    assert result == expected
```

### 2. Git Hooks Testing (`test_git_hooks.py`)

Validates Git hook functionality:

- **Hook Installation**: Proper permissions and structure
- **Hook Execution**: Performance and error handling
- **MCP Integration**: Server connectivity and validation
- **Workflow Testing**: Complete commit workflows

### 3. E2E Deployment Testing (`test_e2e_deployment.py`)

Tests complete deployment scenarios:

- **Installation Testing**: Script-based and package installations
- **Container Deployment**: Build, startup, and health checks
- **Configuration Deployment**: Config validation and rollback
- **Service Integration**: Multi-service deployments

### 4. MCP Server Testing (`e2e-mcp-server.test.js`)

Comprehensive API and functionality testing:

- **HTTP Endpoints**: Health, tools, metrics
- **RPC Methods**: Initialization, tool execution
- **Validation Tools**: Python linting and security
- **Error Handling**: Graceful failure modes

## Configuration

### Pytest Configuration (`pytest.ini`)

Key settings:
- Test discovery patterns
- Coverage reporting (HTML, XML, terminal)
- JUnit XML for CI integration
- Custom markers and strict validation
- Performance timing

### Test Fixtures (`conftest.py`)

Provides reusable test components:
- Temporary directories and isolated environments
- Sample code (good and bad examples)
- Configuration objects
- Git repository setup
- Hypothesis strategies

## Quality Gates

### Pre-commit Gates (< 30 seconds)
- [ ] Syntax validation
- [ ] Basic linting
- [ ] Critical security checks
- [ ] Fast unit tests

### CI Gates (< 10 minutes)
- [ ] Full test suite (80%+ coverage)
- [ ] Security scanning
- [ ] Container build validation
- [ ] Performance benchmarks

### Release Gates (< 2 hours)
- [ ] E2E integration tests
- [ ] Cross-platform validation
- [ ] Load testing
- [ ] Security penetration testing

## Reporting and Metrics

### Generated Reports

Test execution generates comprehensive reports:

```
test-reports/
├── coverage-html/              # Interactive coverage report
├── coverage.xml                # Coverage XML for CI
├── junit.xml                   # JUnit format for CI
├── report.html                 # Comprehensive HTML report
├── benchmark.json              # Performance benchmarks
└── ci-summary.json            # CI execution summary
```

### Coverage Targets

- **Minimum**: 80% statement coverage
- **Target**: 90% statement coverage
- **Ideal**: 95% statement coverage with 85% branch coverage

### Performance Benchmarks

- API responses: < 200ms for simple operations
- Complex operations: < 2s
- Pre-commit hooks: < 30s
- Container builds: < 15 minutes

## Development Workflow

### Test-Driven Development

1. **Red**: Write failing test for new functionality
2. **Green**: Write minimal code to pass the test
3. **Refactor**: Improve code while maintaining tests
4. **Repeat**: Continue with next functionality

### Continuous Testing

```bash
# Watch mode for development
pytest --looponfail tests/

# Fast feedback loop
./tests/run_tests.py fast

# Pre-commit validation
git add . && git commit -m "test commit"
```

### Debugging Failed Tests

```bash
# Verbose output with full tracebacks
pytest -vvv --tb=long

# Stop on first failure
pytest -x

# Drop into debugger on failure
pytest --pdb

# Show local variables in traceback
pytest --tb=long --showlocals
```

## Integration with CI/CD

### GitLab CI Integration

```yaml
test:
  stage: test
  script:
    - ./tests/run_tests.py ci
  artifacts:
    reports:
      junit: tests/test-reports/junit.xml
      coverage: tests/test-reports/coverage.xml
    paths:
      - tests/test-reports/
```

### GitHub Actions Integration

```yaml
- name: Run Tests
  run: ./tests/run_tests.py ci
  
- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: tests/test-reports/coverage.xml
```

## Advanced Features

### Parallel Test Execution

```bash
# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Specific number of workers
pytest -n 4
```

### Test Data Management

- **Fixtures**: Reusable test data and setup
- **Factories**: Generate test objects consistently
- **Property-based generation**: Diverse inputs via Hypothesis
- **Snapshot testing**: Capture and compare expected outputs

### Custom Assertions

The test suite includes custom assertions for domain-specific validation:

```python
assert_valid_python_code(code)
assert_no_security_issues(code)
assert_follows_style(code, max_line_length=88)
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure PYTHONPATH includes project root
2. **Docker Tests Fail**: Verify Docker is running and accessible
3. **Network Tests Timeout**: Check network connectivity and firewall
4. **Permission Errors**: Ensure test files have proper permissions

### Environment Setup

```bash
# Validate test environment
./tests/run_tests.py validate

# Install missing dependencies
pip install -r requirements-dev.txt

# Check Docker availability
docker --version && docker info
```

## Contributing

### Adding New Tests

1. Follow existing patterns in test files
2. Use appropriate markers for categorization
3. Include both positive and negative test cases
4. Add property-based tests for algorithmic functions
5. Update this documentation for new test categories

### Test Naming Conventions

- Test files: `test_*.py`
- Test functions: `test_*`
- Test classes: `Test*`
- Descriptive names: `test_calculate_sum_with_empty_list`

### Code Coverage Guidelines

- New code must have > 90% coverage
- Critical paths must have 100% coverage
- Property-based tests for algorithmic code
- Integration tests for component interactions

---

For more detailed information, see:
- [Test Strategy](test_strategy.md) - Comprehensive testing approach
- [Quality Checklist](quality_checklist.md) - Quality gates and validation
- [Pytest Documentation](https://docs.pytest.org/) - Pytest reference
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/) - Property-based testing