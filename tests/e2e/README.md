# End-to-End (E2E) Testing Framework

This directory contains comprehensive E2E tests for the HuskyCat platform, covering the entire deployment pipeline from code validation to production deployment.

## 🎯 Test Coverage

### 1. GitLab Pages Deployment (`test_pages_deployment.py`)
- **Site Availability**: Tests that the documentation site is accessible
- **Navigation Testing**: Validates documentation site navigation and links
- **Download Functionality**: Verifies download links for binaries and packages
- **Search Functionality**: Tests documentation search capabilities
- **Responsive Design**: Validates site behavior across different viewport sizes
- **Performance Metrics**: Measures page load times and resource usage
- **Content Quality**: Ensures essential documentation sections are present

### 2. MCP Server Integration (`test_mcp_integration.py`)
- **Server Startup**: Tests MCP server initialization and health checks
- **STDIO Communication**: Validates JSON-RPC protocol communication
- **Code Validation**: Tests Python code validation through MCP endpoints
- **Security Scanning**: Verifies security issue detection capabilities
- **YAML Validation**: Tests YAML configuration validation
- **Performance Testing**: Measures validation performance under load
- **Container Deployment**: Tests MCP server container deployment

### 3. CI/CD Pipeline Validation (`test_ci_cd_pipeline.py`)
- **Configuration Syntax**: Validates GitLab CI, GitHub Actions, and Makefile syntax
- **Lint Stage Execution**: Tests code linting and formatting checks
- **Security Scanning**: Validates security scanning integration
- **Unit Test Execution**: Tests unit test pipeline stages
- **Build Process**: Validates Python packaging and container builds
- **Deployment Readiness**: Checks production deployment preparedness
- **Rollback Mechanisms**: Tests rollback and recovery procedures

## 🚀 Quick Start

### Prerequisites

```bash
# Install dependencies
pip install -e ".[dev]"

# Install Playwright browsers
playwright install chromium firefox
```

### Running Tests

```bash
# Run all E2E tests
python tests/e2e/run_e2e_tests.py --suite=all

# Run specific test suites
python tests/e2e/run_e2e_tests.py --suite=playwright --browser=chromium
python tests/e2e/run_e2e_tests.py --suite=mcp
python tests/e2e/run_e2e_tests.py --suite=cicd

# Run with visible browser (headed mode)
python tests/e2e/run_e2e_tests.py --suite=playwright --headed

# Skip slow tests
python tests/e2e/run_e2e_tests.py --suite=all --skip-slow
```

### Using pytest directly

```bash
# Run specific test file
pytest tests/e2e/test_pages_deployment.py -v

# Run with specific markers
pytest tests/e2e/ -m "playwright" -v
pytest tests/e2e/ -m "not slow" -v

# Generate reports
pytest tests/e2e/ --html=reports/e2e-report.html --self-contained-html
```

## 🛠️ Test Configuration

### Playwright Configuration (`playwright.config.py`)
- Browser settings (Chromium, Firefox, WebKit)
- Viewport configurations for desktop/mobile/tablet
- Screenshot and video recording settings
- Performance monitoring utilities
- Accessibility testing with axe-core

### Pytest Configuration (`pytest-e2e.ini`)
- Test discovery and execution settings
- Markers for test categorization
- Timeout and retry configurations
- Reporting and coverage settings
- Logging configuration

## 🏗️ Test Architecture

### Test Fixtures (`fixtures.py`)
- **MockGitLabPagesServer**: Simulates GitLab Pages for local testing
- **MockMCPServer**: Mock MCP server for integration testing
- **MockContainerRegistry**: Container registry simulation
- **TempGitRepository**: Temporary Git repositories for testing
- **Performance Monitoring**: Built-in performance measurement tools
- **Accessibility Testing**: Automated accessibility compliance checks

### Test Categories

#### Unit-level E2E Tests
- Fast execution (<5 seconds)
- Mock external dependencies
- Focus on component integration

#### Integration E2E Tests  
- Medium execution time (5-30 seconds)
- Real service interactions
- Cross-component validation

#### Full System E2E Tests
- Slow execution (>30 seconds) 
- End-to-end user journeys
- Production-like environment testing

## 📊 Test Reporting

### Generated Reports
- **HTML Reports**: Comprehensive test results with screenshots
- **JUnit XML**: CI/CD integration format
- **Coverage Reports**: Code coverage from E2E tests
- **Performance Metrics**: Load times, resource usage
- **Accessibility Reports**: WCAG compliance results

### Report Locations
```
reports/
├── e2e-report.html           # Main E2E test report
├── playwright-report/        # Playwright-specific reports
├── coverage-e2e/            # E2E test coverage
├── e2e-summary.json         # JSON summary for CI/CD
└── e2e-test.log             # Detailed test execution log
```

## 🔧 CI/CD Integration

### GitLab CI Integration
The E2E tests are integrated into the GitLab CI pipeline with multiple stages:

```yaml
test:e2e:comprehensive:
  stage: test
  image: mcr.microsoft.com/playwright/python:v1.40.0-focal
  script:
    - uv run python tests/e2e/run_e2e_tests.py --suite=all --skip-slow --headless
  artifacts:
    reports:
      junit: reports/e2e-full-junit.xml
```

### Local Development
```bash
# Quick validation during development
make test-e2e-quick

# Full E2E test suite (CI equivalent)
make test-e2e-full

# Performance benchmarking
make test-e2e-performance
```

## 🎭 Browser Testing

### Supported Browsers
- **Chromium**: Primary browser for CI/CD
- **Firefox**: Cross-browser compatibility
- **WebKit**: Safari compatibility testing

### Device Emulation
- Desktop (1920x1080)
- Tablet (768x1024)  
- Mobile (375x667)
- Custom viewport sizes

### Network Conditions
- Fast 3G simulation
- Slow 3G simulation
- Offline mode testing

## 🔒 Security Testing

### Automated Security Checks
- **Content Security Policy**: Validates CSP headers
- **HTTPS Enforcement**: Tests secure connection requirements
- **Authentication Testing**: Validates auth flows
- **Input Sanitization**: Tests XSS prevention
- **Dependency Scanning**: Checks for vulnerable packages

## ⚡ Performance Testing

### Metrics Collected
- **Page Load Time**: Time to interactive
- **Resource Loading**: Size and count of resources
- **Memory Usage**: Heap size and garbage collection
- **CPU Utilization**: Processing time for operations
- **Network Requests**: Request count and response times

### Performance Thresholds
- Page load: <10 seconds
- Resource size: <5MB per image
- Memory growth: <50MB per test
- Response time: <2 seconds for API calls

## 🧪 Writing E2E Tests

### Test Structure
```python
class TestFeatureName:
    """Test suite for specific feature."""
    
    def test_feature_functionality(self, page: Page):
        """Test description with clear expected behavior."""
        # Arrange
        page.goto("https://example.com")
        
        # Act
        page.click("button[data-testid='submit']")
        
        # Assert
        expect(page.locator(".success-message")).to_be_visible()
```

### Best Practices
1. **Clear Test Names**: Use descriptive test method names
2. **Proper Assertions**: Use Playwright's expect API
3. **Wait Strategies**: Use explicit waits for dynamic content
4. **Error Handling**: Include proper error scenarios
5. **Test Isolation**: Each test should be independent
6. **Resource Cleanup**: Clean up test data and resources

### Common Patterns
```python
# Page object pattern
class DocumentationPage:
    def __init__(self, page: Page):
        self.page = page
        self.search_input = page.locator("input[type='search']")
        self.nav_menu = page.locator("nav")
    
    def search(self, query: str):
        self.search_input.fill(query)
        self.search_input.press("Enter")

# Fixture usage
def test_with_mock_server(mock_mcp_server, page: Page):
    """Test using mock server fixture."""
    page.goto(f"http://localhost:{mock_mcp_server.port}")
    # Test implementation
```

## 🚨 Troubleshooting

### Common Issues
1. **Browser Installation**: Run `playwright install` if browsers are missing
2. **Permission Errors**: Ensure proper file permissions for test artifacts
3. **Network Timeouts**: Increase timeout values for slow networks
4. **Container Issues**: Verify Docker/Podman is running and accessible

### Debug Mode
```bash
# Enable debug logging
PLAYWRIGHT_DEBUG=1 python tests/e2e/run_e2e_tests.py --suite=playwright --headed

# Generate traces for failed tests
pytest tests/e2e/ --tracing=on --video=retain-on-failure
```

### CI/CD Debugging
- Check GitLab CI job logs for detailed error messages
- Download test artifacts from failed pipeline runs
- Use `--headed` mode in development for visual debugging

## 📈 Metrics and Monitoring

### Success Criteria
- **Test Pass Rate**: >95% for critical user journeys
- **Test Execution Time**: <10 minutes for full suite
- **Coverage**: >80% of critical application paths
- **Performance**: All pages load within defined thresholds

### Monitoring Integration
- Test results integrated with GitLab CI/CD metrics
- Performance data collected for trend analysis
- Failure notifications for critical test failures
- Regular test health reports

## 🤝 Contributing

### Adding New E2E Tests
1. Create test file in appropriate category directory
2. Use existing fixtures and patterns
3. Add proper test markers and documentation
4. Update CI/CD pipeline if needed
5. Verify tests pass in both local and CI environments

### Test Maintenance
- Regular review of test reliability
- Update selectors when UI changes
- Maintain mock services and fixtures
- Keep dependencies up to date
- Monitor test execution performance

For more information, see the main project documentation and CI/CD pipeline configuration.