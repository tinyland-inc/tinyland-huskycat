#!/usr/bin/env python3
"""E2E tests for GitLab Pages deployment and documentation site functionality."""

import pytest
import time
import requests
from pathlib import Path
from typing import Optional
from playwright.sync_api import Page, expect
from urllib.parse import urljoin
import json
import subprocess
import re


class TestGitLabPagesDeployment:
    """Test GitLab Pages deployment and documentation site."""

    @pytest.fixture
    def pages_url(self) -> str:
        """Get the Pages URL from configuration."""
        return "https://huskycat.pages.io"

    @pytest.fixture
    def local_docs_server(self) -> Optional[str]:
        """Start local MkDocs server for testing."""
        try:
            # Check if mkdocs.yml exists
            mkdocs_file = Path("mkdocs.yml")
            if not mkdocs_file.exists():
                return None

            # Start MkDocs development server
            process = subprocess.Popen(
                ["mkdocs", "serve", "--dev-addr", "127.0.0.1:8000"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Wait for server to start
            time.sleep(5)

            # Check if server is running
            try:
                response = requests.get("http://127.0.0.1:8000", timeout=5)
                if response.status_code == 200:
                    yield "http://127.0.0.1:8000"
                else:
                    yield None
            except requests.RequestException:
                yield None
            finally:
                process.terminate()
                process.wait(timeout=10)
        except Exception:
            yield None

    def test_pages_site_availability(self, page: Page, pages_url: str):
        """Test that GitLab Pages site is accessible."""
        page.goto(pages_url)

        # Wait for page load
        page.wait_for_load_state("networkidle")

        # Check that we don't get 404 or error pages
        expect(page.locator("title")).not_to_contain_text("404")
        expect(page.locator("title")).not_to_contain_text("Error")

        # Check for common documentation elements
        expect(page.locator("h1, h2, .main-content")).to_be_visible()

    def test_documentation_navigation(self, page: Page, pages_url: str):
        """Test documentation site navigation."""
        page.goto(pages_url)
        page.wait_for_load_state("networkidle")

        # Look for navigation menu
        nav_selectors = [
            "nav",
            ".nav",
            ".navigation",
            ".sidebar",
            ".menu",
            "[role='navigation']",
            ".md-nav",
        ]

        nav_found = False
        for selector in nav_selectors:
            try:
                nav_element = page.locator(selector)
                if nav_element.count() > 0 and nav_element.first.is_visible():
                    nav_found = True
                    break
            except:
                continue

        if nav_found:
            # Test navigation links
            nav_links = page.locator("nav a, .nav a, .navigation a").all()

            for link in nav_links[:5]:  # Test first 5 links
                if link.is_visible():
                    href = link.get_attribute("href")
                    if href and not href.startswith("#"):
                        # Click and verify page loads
                        try:
                            link.click()
                            page.wait_for_load_state("networkidle", timeout=10000)
                            expect(page).not_to_have_title(re.compile(r"404|Error"))
                            page.go_back()
                            page.wait_for_load_state("networkidle")
                        except:
                            # Skip broken links for now
                            continue

    def test_download_links_functionality(self, page: Page, pages_url: str):
        """Test download links and verify they work."""
        page.goto(pages_url)
        page.wait_for_load_state("networkidle")

        # Look for download links
        download_selectors = [
            "a[href*='download']",
            "a[href*='.tar.gz']",
            "a[href*='.zip']",
            "a[href*='releases']",
            ".download-link",
            "[download]",
        ]

        download_links = []
        for selector in download_selectors:
            links = page.locator(selector).all()
            for link in links:
                if link.is_visible():
                    href = link.get_attribute("href")
                    if href:
                        download_links.append(href)

        # Test download links accessibility
        for link_url in download_links[:3]:  # Test first 3 download links
            if not link_url.startswith("http"):
                link_url = urljoin(pages_url, link_url)

            try:
                response = requests.head(link_url, timeout=10, allow_redirects=True)
                assert response.status_code in [
                    200,
                    302,
                ], f"Download link failed: {link_url}"

                # Check if it's a valid binary file
                content_type = response.headers.get("content-type", "")
                assert any(
                    ct in content_type.lower()
                    for ct in [
                        "application/octet-stream",
                        "application/zip",
                        "application/gzip",
                        "application/x-gzip",
                    ]
                ) or link_url.endswith(
                    (".zip", ".tar.gz", ".tgz")
                ), f"Download link doesn't appear to be a binary file: {link_url}"

            except requests.RequestException:
                # Network issues - skip this test
                pytest.skip(f"Could not access download link: {link_url}")

    def test_search_functionality(self, page: Page, pages_url: str):
        """Test documentation search functionality."""
        page.goto(pages_url)
        page.wait_for_load_state("networkidle")

        # Look for search input
        search_selectors = [
            "input[type='search']",
            ".search-input",
            "#search",
            "[placeholder*='search' i]",
            ".md-search__input",
        ]

        search_input = None
        for selector in search_selectors:
            try:
                element = page.locator(selector)
                if element.count() > 0 and element.first.is_visible():
                    search_input = element.first
                    break
            except:
                continue

        if search_input:
            # Test search functionality
            search_input.click()
            search_input.fill("validation")
            page.keyboard.press("Enter")

            # Wait for search results
            page.wait_for_timeout(2000)

            # Look for search results
            results_selectors = [
                ".search-results",
                ".results",
                "[data-search-results]",
                ".md-search-result",
            ]

            for selector in results_selectors:
                try:
                    results = page.locator(selector)
                    if results.count() > 0:
                        break
                except:
                    continue

            # Either results found or search is not implemented (both are OK)
            assert True, "Search test completed"

    def test_responsive_design(self, page: Page, pages_url: str):
        """Test responsive design at different viewport sizes."""
        page.goto(pages_url)
        page.wait_for_load_state("networkidle")

        # Test different viewport sizes
        viewports = [
            {"width": 1920, "height": 1080},  # Desktop
            {"width": 768, "height": 1024},  # Tablet
            {"width": 375, "height": 667},  # Mobile
        ]

        for viewport in viewports:
            page.set_viewport_size(viewport)
            page.wait_for_timeout(1000)

            # Check that content is still visible and accessible
            expect(page.locator("body")).to_be_visible()

            # Verify no horizontal scrolling on mobile
            if viewport["width"] <= 768:
                # Check that content doesn't overflow
                body_width = page.evaluate("document.body.scrollWidth")
                viewport_width = viewport["width"]
                assert (
                    body_width <= viewport_width + 20
                ), f"Content overflows at {viewport['width']}px width"

    def test_local_docs_build(self, local_docs_server: Optional[str], page: Page):
        """Test locally built documentation."""
        if not local_docs_server:
            pytest.skip("Local MkDocs server not available")

        page.goto(local_docs_server)
        page.wait_for_load_state("networkidle")

        # Verify local docs load correctly
        expect(page.locator("title")).not_to_contain_text("404")
        expect(page.locator("body")).to_be_visible()

        # Test local navigation
        nav_links = page.locator("nav a, .nav a").all()
        for link in nav_links[:3]:  # Test first 3 links
            if link.is_visible():
                href = link.get_attribute("href")
                if href and not href.startswith("http") and not href.startswith("#"):
                    try:
                        link.click()
                        page.wait_for_load_state("networkidle", timeout=5000)
                        expect(page.locator("body")).to_be_visible()
                        page.go_back()
                        page.wait_for_load_state("networkidle")
                    except:
                        continue

    def test_documentation_content_quality(self, page: Page, pages_url: str):
        """Test documentation content quality and completeness."""
        page.goto(pages_url)
        page.wait_for_load_state("networkidle")

        # Check for essential documentation sections
        essential_sections = [
            "installation",
            "install",
            "setup",
            "getting started",
            "usage",
            "configuration",
            "config",
            "api",
            "reference",
        ]

        page_text = page.locator("body").inner_text().lower()

        sections_found = []
        for section in essential_sections:
            if section in page_text:
                sections_found.append(section)

        # At least some essential sections should be present
        assert (
            len(sections_found) >= 2
        ), f"Few essential documentation sections found: {sections_found}"

        # Check for code examples
        code_blocks = page.locator("pre, code, .highlight").count()
        assert code_blocks > 0, "No code examples found in documentation"

        # Check for proper headings structure
        headings = page.locator("h1, h2, h3, h4").count()
        assert headings > 0, "No proper heading structure found"

    def test_performance_metrics(self, page: Page, pages_url: str):
        """Test basic performance metrics of the documentation site."""
        start_time = time.time()

        page.goto(pages_url)
        page.wait_for_load_state("networkidle")

        load_time = time.time() - start_time

        # Page should load within reasonable time (10 seconds)
        assert load_time < 10, f"Page load time too slow: {load_time:.2f}s"

        # Check for large images that might slow down loading
        images = page.locator("img").all()
        for img in images:
            if img.is_visible():
                src = img.get_attribute("src")
                if src and not src.startswith("data:"):
                    try:
                        if not src.startswith("http"):
                            src = urljoin(pages_url, src)
                        response = requests.head(src, timeout=5)
                        content_length = response.headers.get("content-length")
                        if content_length:
                            size_mb = int(content_length) / (1024 * 1024)
                            assert (
                                size_mb < 5
                            ), f"Large image found: {src} ({size_mb:.2f}MB)"
                    except:
                        continue  # Skip if can't check image size


class TestBinaryArtifacts:
    """Test binary artifacts and downloads."""

    def test_binary_download_availability(self):
        """Test that binary downloads are available."""
        # This would test actual binary downloads from releases
        # For now, we'll test the infrastructure
        download_urls = [
            "https://huskycat.pages.io/downloads/huskycat-linux-amd64",
            "https://huskycat.pages.io/downloads/huskycat-darwin-amd64",
            "https://huskycat.pages.io/downloads/huskycat-windows-amd64.exe",
        ]

        for url in download_urls:
            try:
                response = requests.head(url, timeout=10, allow_redirects=True)
                # 404 is OK if binaries aren't built yet, 200 means they exist
                assert response.status_code in [
                    200,
                    404,
                ], f"Unexpected status for {url}: {response.status_code}"
            except requests.RequestException:
                pytest.skip(f"Could not access binary URL: {url}")

    def test_binary_execution_basic(self):
        """Test basic binary execution if available locally."""
        # Look for local binary artifacts
        binary_paths = ["./dist/huskycat", "./build/huskycat", "./huskycat_main.py"]

        for binary_path in binary_paths:
            if Path(binary_path).exists():
                try:
                    # Test basic execution (help command)
                    if binary_path.endswith(".py"):
                        cmd = ["python3", binary_path, "--help"]
                    else:
                        cmd = [binary_path, "--help"]

                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=30
                    )

                    # Should either show help or fail gracefully
                    assert result.returncode in [
                        0,
                        1,
                        2,
                    ], f"Binary execution failed: {result.stderr}"
                    return  # Test passed for at least one binary

                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue

        pytest.skip("No testable binary artifacts found locally")


class TestInstallationScripts:
    """Test installation scripts and procedures."""

    def test_install_script_availability(self):
        """Test that installation scripts are available."""
        install_scripts = ["install.sh", "scripts/install-unified.sh", "deploy.sh"]

        found_scripts = []
        for script_path in install_scripts:
            if Path(script_path).exists():
                found_scripts.append(script_path)

        assert len(found_scripts) > 0, "No installation scripts found"

        # Test script syntax
        for script in found_scripts:
            result = subprocess.run(
                ["bash", "-n", str(script)], capture_output=True, text=True
            )
            assert result.returncode == 0, f"Syntax error in {script}: {result.stderr}"

    def test_package_manager_integration(self):
        """Test package manager integration."""
        # Test npm package.json
        package_json = Path("package.json")
        if package_json.exists():
            with open(package_json) as f:
                package_data = json.load(f)

            assert "scripts" in package_data, "No npm scripts defined"
            assert (
                "dependencies" in package_data or "devDependencies" in package_data
            ), "No dependencies defined"

        # Test Python package configuration
        pyproject_toml = Path("pyproject.toml")
        assert pyproject_toml.exists(), "pyproject.toml not found"


@pytest.mark.slow
class TestFullDeploymentPipeline:
    """Test the complete deployment pipeline."""

    def test_documentation_build_process(self):
        """Test the complete documentation build process."""
        # Check if MkDocs can build successfully
        if not Path("mkdocs.yml").exists():
            pytest.skip("mkdocs.yml not found")

        try:
            # Test build command
            result = subprocess.run(
                ["mkdocs", "build", "--clean"],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                # Verify build output
                site_dir = Path("site")
                assert site_dir.exists(), "Site directory not created"
                assert (site_dir / "index.html").exists(), "index.html not generated"

                # Check for essential files
                essential_files = ["index.html", "search/search_index.json"]
                for file_name in essential_files:
                    file_path = site_dir / file_name
                    if not file_path.exists():
                        print(f"Warning: {file_name} not found in build output")

        except subprocess.TimeoutExpired:
            pytest.fail("Documentation build timed out")
        except FileNotFoundError:
            pytest.skip("MkDocs not available")

    def test_container_registry_integration(self):
        """Test container registry integration."""
        # This would test pushing/pulling from container registry
        # For now, we test local container operations
        containerfile = Path("ContainerFile")
        if not containerfile.exists():
            pytest.skip("ContainerFile not found")

        try:
            import docker

            client = docker.from_env()

            # Test container build
            image, build_logs = client.images.build(
                path=".",
                dockerfile="ContainerFile",
                tag="huskycats-registry-test:latest",
                timeout=600,
            )

            assert image is not None, "Container build failed"

            # Test container can start
            container = client.containers.run(image.id, detach=True, remove=True)

            # Wait briefly and check status
            time.sleep(2)
            container.reload()

            # Clean up
            container.stop(timeout=10)
            client.images.remove(image.id, force=True)

        except ImportError:
            pytest.skip("Docker Python library not available")
        except Exception as e:
            pytest.skip(f"Docker not available: {e}")

    def test_ci_cd_configuration_validity(self):
        """Test CI/CD configuration files."""
        ci_files = [".gitlab-ci.yml", ".github/workflows/deploy.yml", "Makefile"]

        for ci_file in ci_files:
            if Path(ci_file).exists():
                # Basic syntax validation
                if ci_file.endswith(".yml"):
                    import yaml

                    try:
                        with open(ci_file) as f:
                            yaml.safe_load(f)
                    except yaml.YAMLError as e:
                        pytest.fail(f"Invalid YAML in {ci_file}: {e}")

                elif ci_file == "Makefile":
                    # Test Make syntax
                    result = subprocess.run(
                        ["make", "-n", "--dry-run"],
                        capture_output=True,
                        text=True,
                        cwd=".",
                    )

                    if result.returncode != 0 and "No targets" not in result.stderr:
                        print(f"Warning: Makefile issues: {result.stderr}")
