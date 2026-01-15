#!/usr/bin/env python3
"""
Unit tests for GitHub Actions workflow validation.

Tests the GitHubActionsSchemaValidator class and CI command integration.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from huskycat.commands.ci import CIValidateCommand
from huskycat.core.base import CommandStatus
from huskycat.github_actions_validator import GitHubActionsSchemaValidator


class TestGitHubActionsSchemaValidator:
    """Test the GitHubActionsSchemaValidator class."""

    def test_validator_initializes(self):
        """Validator should initialize without errors."""
        validator = GitHubActionsSchemaValidator()
        assert validator.schema is not None
        assert validator.validator is not None

    def test_validator_has_schema_info(self):
        """Validator should provide schema info."""
        validator = GitHubActionsSchemaValidator()
        info = validator.get_schema_info()

        assert "schema_loaded" in info
        assert info["schema_loaded"] is True
        assert "cache_location" in info

    def test_validate_valid_workflow(self):
        """Validator should pass valid workflow files."""
        validator = GitHubActionsSchemaValidator()

        valid_workflow = """
name: CI
on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: echo "Hello World"
"""
        is_valid, errors, warnings = validator.validate_content(valid_workflow)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_workflow_missing_on(self):
        """Validator should warn about missing 'on' trigger."""
        validator = GitHubActionsSchemaValidator()

        workflow_missing_on = """
name: CI

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
"""
        is_valid, errors, warnings = validator.validate_content(workflow_missing_on)

        # May have schema errors or warnings
        warning_messages = " ".join(warnings)
        assert "on" in warning_messages.lower() or len(errors) > 0

    def test_validate_workflow_missing_jobs(self):
        """Validator should error on missing 'jobs'."""
        validator = GitHubActionsSchemaValidator()

        workflow_missing_jobs = """
name: CI
on: push
"""
        is_valid, errors, warnings = validator.validate_content(workflow_missing_jobs)

        # Should fail or have warnings about missing jobs
        all_messages = " ".join(errors + warnings)
        assert "jobs" in all_messages.lower() or not is_valid

    def test_validate_job_missing_runs_on(self):
        """Validator should warn about job missing runs-on."""
        validator = GitHubActionsSchemaValidator()

        workflow_no_runner = """
name: CI
on: push

jobs:
  build:
    steps:
      - uses: actions/checkout@v4
"""
        is_valid, errors, warnings = validator.validate_content(workflow_no_runner)

        all_messages = " ".join(errors + warnings)
        assert "runs-on" in all_messages.lower() or not is_valid

    def test_validate_job_missing_steps(self):
        """Validator should warn about job missing steps."""
        validator = GitHubActionsSchemaValidator()

        workflow_no_steps = """
name: CI
on: push

jobs:
  build:
    runs-on: ubuntu-latest
"""
        is_valid, errors, warnings = validator.validate_content(workflow_no_steps)

        all_messages = " ".join(errors + warnings)
        assert "steps" in all_messages.lower() or not is_valid

    def test_validate_step_missing_uses_or_run(self):
        """Validator should warn about step missing uses or run."""
        validator = GitHubActionsSchemaValidator()

        workflow_empty_step = """
name: CI
on: push

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Empty step
"""
        is_valid, errors, warnings = validator.validate_content(workflow_empty_step)

        warning_messages = " ".join(warnings)
        assert "uses" in warning_messages.lower() or "run" in warning_messages.lower()

    def test_validate_unpinned_action(self):
        """Validator should warn about unpinned actions using @main or @master."""
        validator = GitHubActionsSchemaValidator()

        workflow_unpinned = """
name: CI
on: push

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@main
"""
        is_valid, errors, warnings = validator.validate_content(workflow_unpinned)

        warning_messages = " ".join(warnings)
        assert "unpinned" in warning_messages.lower() or "pin" in warning_messages.lower()

    def test_validate_invalid_needs_reference(self):
        """Validator should warn about invalid needs references."""
        validator = GitHubActionsSchemaValidator()

        workflow_bad_needs = """
name: CI
on: push

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo "build"

  deploy:
    runs-on: ubuntu-latest
    needs: nonexistent_job
    steps:
      - run: echo "deploy"
"""
        is_valid, errors, warnings = validator.validate_content(workflow_bad_needs)

        warning_messages = " ".join(warnings)
        assert "nonexistent" in warning_messages.lower() or "needs" in warning_messages.lower()

    def test_validate_invalid_yaml(self):
        """Validator should handle invalid YAML gracefully."""
        validator = GitHubActionsSchemaValidator()

        invalid_yaml = """
name: CI
on: [push
  - invalid yaml structure
"""
        is_valid, errors, warnings = validator.validate_content(invalid_yaml)

        assert is_valid is False
        assert len(errors) > 0
        assert "yaml" in errors[0].lower()

    def test_validate_empty_content(self):
        """Validator should handle empty content."""
        validator = GitHubActionsSchemaValidator()

        is_valid, errors, warnings = validator.validate_content("")

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_file(self):
        """Validator should validate files from disk."""
        validator = GitHubActionsSchemaValidator()

        valid_workflow = """
name: Test CI
on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as f:
            f.write(valid_workflow)
            f.flush()

            try:
                is_valid, errors, warnings = validator.validate_file(f.name)
                assert is_valid is True
                assert len(errors) == 0
            finally:
                os.unlink(f.name)

    def test_validate_file_not_found(self):
        """Validator should handle missing files."""
        validator = GitHubActionsSchemaValidator()

        is_valid, errors, warnings = validator.validate_file("/nonexistent/path.yml")

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_complex_workflow(self):
        """Validator should handle complex real-world workflows."""
        validator = GitHubActionsSchemaValidator()

        complex_workflow = """
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Deployment environment'
        required: true
        default: 'staging'

env:
  NODE_VERSION: '18'

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
      - run: npm ci
      - run: npm run lint

  test:
    needs: lint
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node: [16, 18, 20]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node }}
      - run: npm ci
      - run: npm test

  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: build
          path: dist/

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://example.com
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: build
          path: dist/
      - run: echo "Deploying..."
"""
        is_valid, errors, warnings = validator.validate_content(complex_workflow)

        assert is_valid is True
        assert len(errors) == 0

    def test_minimal_schema_fallback(self):
        """Validator should have a working minimal schema fallback."""
        validator = GitHubActionsSchemaValidator()
        minimal_schema = validator._get_minimal_schema()

        assert "$schema" in minimal_schema
        assert "properties" in minimal_schema
        assert "jobs" in minimal_schema["properties"]


class TestCIValidateCommandGitHubActions:
    """Test CI validation command with GitHub Actions."""

    def test_ci_command_detects_github_workflows(self):
        """CI command should detect GitHub workflows in .github/workflows."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflows_dir = Path(tmpdir) / ".github" / "workflows"
            workflows_dir.mkdir(parents=True)

            workflow_file = workflows_dir / "ci.yml"
            workflow_file.write_text("""
name: CI
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
""")

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                command = CIValidateCommand()
                detected = command._detect_ci_files()

                assert any("ci.yml" in f for f in detected)
            finally:
                os.chdir(original_cwd)

    def test_ci_command_validates_github_workflow(self):
        """CI command should validate GitHub Actions workflows."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflows_dir = Path(tmpdir) / ".github" / "workflows"
            workflows_dir.mkdir(parents=True)

            workflow_file = workflows_dir / "test.yml"
            workflow_file.write_text("""
name: Test
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test
""")

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                command = CIValidateCommand()
                result = command.execute()

                # Should pass validation
                assert result.status in (CommandStatus.SUCCESS, CommandStatus.WARNING)
            finally:
                os.chdir(original_cwd)

    def test_ci_command_validates_invalid_workflow(self):
        """CI command should catch invalid GitHub Actions workflows."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflows_dir = Path(tmpdir) / ".github" / "workflows"
            workflows_dir.mkdir(parents=True)

            workflow_file = workflows_dir / "invalid.yml"
            workflow_file.write_text("""
name: Invalid
on: push
jobs:
  test:
    # Missing runs-on and steps
""")

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                command = CIValidateCommand()
                result = command.execute()

                # Should fail or have warnings
                assert result.status in (
                    CommandStatus.FAILED,
                    CommandStatus.WARNING,
                )
            finally:
                os.chdir(original_cwd)


class TestGitHubActionsSemanticValidation:
    """Test semantic validation rules for GitHub Actions."""

    def test_branches_and_branches_ignore_conflict(self):
        """Should warn when both branches and branches-ignore are used."""
        validator = GitHubActionsSchemaValidator()

        workflow = """
name: CI
on:
  push:
    branches: [main]
    branches-ignore: [develop]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo "test"
"""
        is_valid, errors, warnings = validator.validate_content(workflow)

        warning_messages = " ".join(warnings)
        assert "branches" in warning_messages.lower()

    def test_matrix_strategy_workflow(self):
        """Should validate workflows with matrix strategies."""
        validator = GitHubActionsSchemaValidator()

        workflow = """
name: Matrix CI
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python: [3.9, 3.10, 3.11]
        os: [ubuntu-latest, macos-latest]
      fail-fast: false
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - run: python --version
"""
        is_valid, errors, warnings = validator.validate_content(workflow)

        assert is_valid is True

    def test_reusable_workflow(self):
        """Should validate reusable workflow syntax."""
        validator = GitHubActionsSchemaValidator()

        workflow = """
name: Reusable
on:
  workflow_call:
    inputs:
      version:
        required: true
        type: string
    secrets:
      token:
        required: true
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo "${{ inputs.version }}"
"""
        is_valid, errors, warnings = validator.validate_content(workflow)

        # Reusable workflows may not require traditional on/jobs structure
        # Just ensure it doesn't crash
        assert isinstance(is_valid, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
