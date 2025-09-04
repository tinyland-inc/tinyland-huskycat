#!/usr/bin/env python3
"""Playwright configuration for E2E testing."""

import os
from playwright.sync_api import Playwright
from typing import Dict, Any


def playwright_config() -> Dict[str, Any]:
    """Playwright configuration for browser automation."""
    return {
        # Browser configuration
        "browsers": ["chromium", "firefox", "webkit"],
        "headless": os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true",
        "slow_mo": int(os.getenv("PLAYWRIGHT_SLOW_MO", "0")),
        
        # Viewport and device settings
        "viewport": {
            "width": 1280,
            "height": 720
        },
        
        # Screenshots and videos
        "screenshot": "only-on-failure",
        "video": "retain-on-failure",
        "trace": "retain-on-failure",
        
        # Timeouts
        "timeout": 30000,  # 30 seconds
        "navigation_timeout": 30000,
        "expect_timeout": 5000,
        
        # Test directory
        "test_dir": "tests/e2e",
        "output_dir": "test-results",
        
        # Browser context options
        "context_options": {
            "ignore_https_errors": True,
            "viewport": {"width": 1280, "height": 720},
            "locale": "en-US",
            "timezone_id": "America/New_York",
        },
        
        # Mobile device emulation
        "devices": {
            "mobile": {
                "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
                "viewport": {"width": 375, "height": 667},
                "device_scale_factor": 2,
                "is_mobile": True,
                "has_touch": True,
            },
            "tablet": {
                "user_agent": "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
                "viewport": {"width": 768, "height": 1024},
                "device_scale_factor": 2,
                "is_mobile": True,
                "has_touch": True,
            }
        },
        
        # Network conditions
        "network_conditions": {
            "slow_3g": {
                "download_throughput": 500 * 1024 / 8,  # 500kb/s
                "upload_throughput": 500 * 1024 / 8,
                "latency": 2000  # 2s
            },
            "fast_3g": {
                "download_throughput": 1.6 * 1024 * 1024 / 8,  # 1.6mb/s
                "upload_throughput": 750 * 1024 / 8,  # 750kb/s
                "latency": 560
            }
        },
        
        # Test execution
        "workers": int(os.getenv("PLAYWRIGHT_WORKERS", "1")),
        "retry": int(os.getenv("PLAYWRIGHT_RETRIES", "2")),
        "reporter": [
            ["html", {"output_folder": "playwright-report"}],
            ["junit", {"output_file": "reports/playwright-results.xml"}],
            ["json", {"output_file": "reports/playwright-results.json"}]
        ],
        
        # Base URL for testing
        "base_url": os.getenv("PLAYWRIGHT_BASE_URL", "http://localhost:8000"),
        
        # Custom setup
        "global_setup": "tests/e2e/global_setup.py",
        "global_teardown": "tests/e2e/global_teardown.py",
    }


# Global setup and teardown
def global_setup():
    """Global setup before all tests."""
    print("Setting up Playwright environment...")
    
    # Create output directories
    os.makedirs("test-results", exist_ok=True)
    os.makedirs("playwright-report", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    
    # Install browsers if needed
    if os.getenv("CI"):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # Install only Chromium in CI for speed
            p.chromium.launch()


def global_teardown():
    """Global teardown after all tests."""
    print("Cleaning up Playwright environment...")
    
    # Archive test results in CI
    if os.getenv("CI"):
        import shutil
        if os.path.exists("test-results"):
            shutil.make_archive("test-results-archive", "zip", "test-results")


# Pytest integration
def pytest_playwright_configure(config):
    """Configure Playwright for pytest."""
    playwright_cfg = playwright_config()
    
    # Set base URL if not already set
    if hasattr(config.option, 'base_url') and not config.option.base_url:
        config.option.base_url = playwright_cfg["base_url"]
    
    # Set browser if not already set
    if hasattr(config.option, 'browser') and not config.option.browser:
        config.option.browser = ["chromium"]  # Default browser
    
    # Set headless mode
    if hasattr(config.option, 'headless'):
        config.option.headless = playwright_cfg["headless"]


# Custom fixtures for advanced scenarios
def create_authenticated_context(browser):
    """Create browser context with authentication."""
    context = browser.new_context()
    
    # Mock authentication
    context.add_init_script("""
        window.localStorage.setItem('auth_token', 'mock-token');
        window.localStorage.setItem('user_id', 'test-user');
    """)
    
    return context


def create_mobile_context(browser):
    """Create mobile browser context."""
    mobile_config = playwright_config()["devices"]["mobile"]
    return browser.new_context(**mobile_config)


def create_offline_context(browser):
    """Create offline browser context."""
    context = browser.new_context()
    context.set_offline(True)
    return context


# Performance monitoring utilities
class PerformanceMonitor:
    """Monitor page performance during tests."""
    
    def __init__(self, page):
        self.page = page
        self.metrics = {}
    
    def start_monitoring(self):
        """Start performance monitoring."""
        self.page.add_init_script("""
            window.performanceMetrics = {
                startTime: performance.now(),
                resources: [],
                navigation: performance.getEntriesByType('navigation')[0]
            };
            
            // Monitor resource loading
            new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    window.performanceMetrics.resources.push({
                        name: entry.name,
                        duration: entry.duration,
                        size: entry.transferSize
                    });
                }
            }).observe({entryTypes: ['resource']});
        """)
    
    def get_metrics(self):
        """Get performance metrics."""
        return self.page.evaluate("""
            () => {
                const metrics = window.performanceMetrics || {};
                const navigation = performance.getEntriesByType('navigation')[0];
                
                return {
                    loadTime: navigation ? navigation.loadEventEnd - navigation.loadEventStart : 0,
                    domContentLoaded: navigation ? navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart : 0,
                    resourceCount: metrics.resources ? metrics.resources.length : 0,
                    totalResourceSize: metrics.resources ? metrics.resources.reduce((sum, r) => sum + (r.size || 0), 0) : 0
                };
            }
        """)


# Accessibility testing utilities
class AccessibilityTester:
    """Test accessibility compliance."""
    
    def __init__(self, page):
        self.page = page
    
    def inject_axe(self):
        """Inject axe-core for accessibility testing."""
        self.page.add_script_tag(url="https://unpkg.com/axe-core@latest/axe.min.js")
    
    def run_axe_scan(self):
        """Run accessibility scan."""
        return self.page.evaluate("""
            async () => {
                if (typeof axe === 'undefined') {
                    throw new Error('axe-core not loaded');
                }
                
                const results = await axe.run();
                return {
                    violations: results.violations.map(v => ({
                        id: v.id,
                        impact: v.impact,
                        description: v.description,
                        nodes: v.nodes.length
                    })),
                    passes: results.passes.length,
                    incomplete: results.incomplete.length
                };
            }
        """)


if __name__ == "__main__":
    # Print configuration for debugging
    import json
    config = playwright_config()
    print(json.dumps(config, indent=2))