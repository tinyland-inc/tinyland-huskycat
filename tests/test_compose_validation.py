#!/usr/bin/env python3
"""
Unit tests for Docker/Podman Compose validation.

Tests the ComposeSchemaValidator class and CI command integration.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from huskycat.commands.ci import CIValidateCommand
from huskycat.compose_validator import ComposeSchemaValidator
from huskycat.core.base import CommandStatus


class TestComposeSchemaValidator:
    """Test the ComposeSchemaValidator class."""

    def test_validator_initializes(self):
        """Validator should initialize without errors."""
        validator = ComposeSchemaValidator()
        assert validator.schema is not None
        assert validator.validator is not None

    def test_validator_has_schema_info(self):
        """Validator should provide schema info."""
        validator = ComposeSchemaValidator()
        info = validator.get_schema_info()

        assert "schema_loaded" in info
        assert info["schema_loaded"] is True
        assert "cache_location" in info

    def test_validate_valid_compose(self):
        """Validator should pass valid compose files."""
        validator = ComposeSchemaValidator()

        valid_compose = """
services:
  web:
    image: nginx:1.25
    ports:
      - "80:80"
"""
        is_valid, errors, warnings = validator.validate_content(valid_compose)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_compose_with_version(self):
        """Validator should warn about deprecated version field."""
        validator = ComposeSchemaValidator()

        compose_with_version = """
version: "3.8"

services:
  web:
    image: nginx:1.25
"""
        is_valid, errors, warnings = validator.validate_content(compose_with_version)

        # Should pass but warn about version
        warning_messages = " ".join(warnings)
        assert "version" in warning_messages.lower() or "obsolete" in warning_messages.lower()

    def test_validate_service_missing_image_and_build(self):
        """Validator should warn when service has neither image nor build."""
        validator = ComposeSchemaValidator()

        compose_no_image = """
services:
  web:
    ports:
      - "80:80"
"""
        is_valid, errors, warnings = validator.validate_content(compose_no_image)

        warning_messages = " ".join(warnings)
        assert "image" in warning_messages.lower() or "build" in warning_messages.lower()

    def test_validate_service_with_build(self):
        """Validator should pass service with build instead of image."""
        validator = ComposeSchemaValidator()

        compose_with_build = """
services:
  web:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "80:80"
"""
        is_valid, errors, warnings = validator.validate_content(compose_with_build)

        # Should not warn about missing image since build is present
        assert is_valid is True
        warning_messages = " ".join(warnings)
        assert "missing 'image' or 'build'" not in warning_messages

    def test_validate_invalid_depends_on_reference(self):
        """Validator should warn about invalid depends_on references."""
        validator = ComposeSchemaValidator()

        compose_bad_depends = """
services:
  web:
    image: nginx:1.25
    depends_on:
      - nonexistent_service
"""
        is_valid, errors, warnings = validator.validate_content(compose_bad_depends)

        warning_messages = " ".join(warnings)
        assert "nonexistent" in warning_messages.lower() or "depends" in warning_messages.lower()

    def test_validate_depends_on_dict_format(self):
        """Validator should handle depends_on in dictionary format."""
        validator = ComposeSchemaValidator()

        compose_depends_dict = """
services:
  db:
    image: postgres:15

  web:
    image: nginx:1.25
    depends_on:
      db:
        condition: service_healthy
"""
        is_valid, errors, warnings = validator.validate_content(compose_depends_dict)

        # Should pass - db exists
        assert is_valid is True

    def test_validate_undefined_network_reference(self):
        """Validator should warn about undefined network references."""
        validator = ComposeSchemaValidator()

        compose_bad_network = """
services:
  web:
    image: nginx:1.25
    networks:
      - undefined_network

networks:
  my_network:
    driver: bridge
"""
        is_valid, errors, warnings = validator.validate_content(compose_bad_network)

        warning_messages = " ".join(warnings)
        assert "undefined" in warning_messages.lower() or "network" in warning_messages.lower()

    def test_validate_default_network_allowed(self):
        """Validator should not warn about 'default' network."""
        validator = ComposeSchemaValidator()

        compose_default_network = """
services:
  web:
    image: nginx:1.25
    networks:
      - default
"""
        is_valid, errors, warnings = validator.validate_content(compose_default_network)

        # 'default' is a special network that doesn't need to be defined
        warning_messages = " ".join(warnings)
        assert "undefined network 'default'" not in warning_messages.lower()

    def test_validate_undefined_volume_reference(self):
        """Validator should warn about undefined named volume references."""
        validator = ComposeSchemaValidator()

        compose_bad_volume = """
services:
  web:
    image: nginx:1.25
    volumes:
      - undefined_volume:/data

volumes:
  my_volume:
"""
        is_valid, errors, warnings = validator.validate_content(compose_bad_volume)

        warning_messages = " ".join(warnings)
        assert "undefined" in warning_messages.lower() or "volume" in warning_messages.lower()

    def test_validate_bind_mount_not_warned(self):
        """Validator should not warn about bind mounts (paths starting with . or /)."""
        validator = ComposeSchemaValidator()

        compose_bind_mount = """
services:
  web:
    image: nginx:1.25
    volumes:
      - ./config:/etc/nginx
      - /var/log:/var/log
"""
        is_valid, errors, warnings = validator.validate_content(compose_bind_mount)

        # Bind mounts shouldn't trigger undefined volume warning
        assert is_valid is True

    def test_validate_privileged_mode_warning(self):
        """Validator should warn about privileged mode."""
        validator = ComposeSchemaValidator()

        compose_privileged = """
services:
  web:
    image: nginx:1.25
    privileged: true
"""
        is_valid, errors, warnings = validator.validate_content(compose_privileged)

        warning_messages = " ".join(warnings)
        assert "privileged" in warning_messages.lower()

    def test_validate_latest_tag_warning(self):
        """Validator should warn about :latest or missing tag."""
        validator = ComposeSchemaValidator()

        compose_latest = """
services:
  web:
    image: nginx:latest
"""
        is_valid, errors, warnings = validator.validate_content(compose_latest)

        warning_messages = " ".join(warnings)
        assert "tag" in warning_messages.lower() or "pin" in warning_messages.lower()

    def test_validate_no_tag_warning(self):
        """Validator should warn about images without any tag."""
        validator = ComposeSchemaValidator()

        compose_no_tag = """
services:
  web:
    image: nginx
"""
        is_valid, errors, warnings = validator.validate_content(compose_no_tag)

        warning_messages = " ".join(warnings)
        assert "tag" in warning_messages.lower() or "pin" in warning_messages.lower()

    def test_validate_invalid_yaml(self):
        """Validator should handle invalid YAML gracefully."""
        validator = ComposeSchemaValidator()

        # Use clearly invalid YAML syntax that will fail parsing
        invalid_yaml = """
services:
  web: [
    this is not valid
    yaml: at: all
"""
        is_valid, errors, warnings = validator.validate_content(invalid_yaml)

        assert is_valid is False
        assert len(errors) > 0
        assert "yaml" in errors[0].lower() or "parsing" in errors[0].lower()

    def test_validate_empty_content(self):
        """Validator should handle empty content."""
        validator = ComposeSchemaValidator()

        is_valid, errors, warnings = validator.validate_content("")

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_no_services(self):
        """Validator should warn when no services are defined."""
        validator = ComposeSchemaValidator()

        compose_no_services = """
networks:
  my_network:
    driver: bridge
"""
        is_valid, errors, warnings = validator.validate_content(compose_no_services)

        warning_messages = " ".join(warnings)
        assert "no services" in warning_messages.lower()

    def test_validate_file(self):
        """Validator should validate files from disk."""
        validator = ComposeSchemaValidator()

        valid_compose = """
services:
  web:
    image: nginx:1.25
    ports:
      - "80:80"
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as f:
            f.write(valid_compose)
            f.flush()

            try:
                is_valid, errors, warnings = validator.validate_file(f.name)
                assert is_valid is True
                assert len(errors) == 0
            finally:
                os.unlink(f.name)

    def test_validate_file_not_found(self):
        """Validator should handle missing files."""
        validator = ComposeSchemaValidator()

        is_valid, errors, warnings = validator.validate_file("/nonexistent/compose.yml")

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_complex_compose(self):
        """Validator should handle complex real-world compose files."""
        validator = ComposeSchemaValidator()

        complex_compose = """
services:
  web:
    image: nginx:1.25-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - static_files:/usr/share/nginx/html:ro
    networks:
      - frontend
    depends_on:
      app:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost"]
      interval: 30s
      timeout: 10s
      retries: 3

  app:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        - NODE_ENV=production
    environment:
      - DATABASE_URL=postgres://db:5432/app
    env_file:
      - .env
    networks:
      - frontend
      - backend
    depends_on:
      - db
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  db:
    image: postgres:15-alpine
    volumes:
      - db_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: user
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets:
      - db_password
    networks:
      - backend
    restart: always

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - backend

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true

volumes:
  static_files:
  db_data:
  redis_data:

secrets:
  db_password:
    file: ./secrets/db_password.txt
"""
        is_valid, errors, warnings = validator.validate_content(complex_compose)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_volume_long_syntax(self):
        """Validator should handle volume long syntax."""
        validator = ComposeSchemaValidator()

        compose_long_volume = """
services:
  web:
    image: nginx:1.25
    volumes:
      - type: volume
        source: my_volume
        target: /data
        read_only: true

volumes:
  my_volume:
"""
        is_valid, errors, warnings = validator.validate_content(compose_long_volume)

        assert is_valid is True

    def test_minimal_schema_fallback(self):
        """Validator should have a working minimal schema fallback."""
        validator = ComposeSchemaValidator()
        minimal_schema = validator._get_minimal_schema()

        assert "$schema" in minimal_schema
        assert "properties" in minimal_schema
        assert "services" in minimal_schema["properties"]


class TestCIValidateCommandCompose:
    """Test CI validation command with Compose files."""

    def test_ci_command_detects_compose_files(self):
        """CI command should detect compose files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            compose_file = Path(tmpdir) / "compose.yml"
            compose_file.write_text("""
services:
  web:
    image: nginx:1.25
""")

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                command = CIValidateCommand()
                detected = command._detect_ci_files()

                assert any("compose.yml" in f for f in detected)
            finally:
                os.chdir(original_cwd)

    def test_ci_command_detects_podman_compose(self):
        """CI command should detect podman-compose files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            compose_file = Path(tmpdir) / "podman-compose.yml"
            compose_file.write_text("""
services:
  web:
    image: nginx:1.25
""")

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                command = CIValidateCommand()
                detected = command._detect_ci_files()

                assert any("podman-compose.yml" in f for f in detected)
            finally:
                os.chdir(original_cwd)

    def test_ci_command_validates_compose(self):
        """CI command should validate compose files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            compose_file = Path(tmpdir) / "compose.yml"
            compose_file.write_text("""
services:
  web:
    image: nginx:1.25
    ports:
      - "80:80"
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

    def test_ci_command_validates_invalid_compose(self):
        """CI command should catch invalid compose files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            compose_file = Path(tmpdir) / "compose.yml"
            compose_file.write_text("""
services:
  web:
    # Missing image and build
    depends_on:
      - nonexistent
""")

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                command = CIValidateCommand()
                result = command.execute()

                # Should have warnings
                assert result.status in (
                    CommandStatus.SUCCESS,  # Still valid YAML
                    CommandStatus.WARNING,
                    CommandStatus.FAILED,
                )
                # Should have warnings about missing image/build and nonexistent dependency
                all_messages = " ".join(result.warnings or [])
                assert (
                    "image" in all_messages.lower()
                    or "nonexistent" in all_messages.lower()
                )
            finally:
                os.chdir(original_cwd)


class TestComposeSemanticValidation:
    """Test semantic validation rules for Compose files."""

    def test_secrets_reference_validation(self):
        """Should warn about undefined secret references."""
        validator = ComposeSchemaValidator()

        compose = """
services:
  web:
    image: nginx:1.25
    secrets:
      - undefined_secret

secrets:
  my_secret:
    file: ./secret.txt
"""
        is_valid, errors, warnings = validator.validate_content(compose)

        warning_messages = " ".join(warnings)
        assert "undefined" in warning_messages.lower() or "secret" in warning_messages.lower()

    def test_configs_reference_validation(self):
        """Should warn about undefined config references."""
        validator = ComposeSchemaValidator()

        compose = """
services:
  web:
    image: nginx:1.25
    configs:
      - undefined_config

configs:
  my_config:
    file: ./config.txt
"""
        is_valid, errors, warnings = validator.validate_content(compose)

        warning_messages = " ".join(warnings)
        assert "undefined" in warning_messages.lower() or "config" in warning_messages.lower()

    def test_valid_secret_reference(self):
        """Should not warn about valid secret references."""
        validator = ComposeSchemaValidator()

        compose = """
services:
  web:
    image: nginx:1.25
    secrets:
      - my_secret

secrets:
  my_secret:
    file: ./secret.txt
"""
        is_valid, errors, warnings = validator.validate_content(compose)

        warning_messages = " ".join(warnings)
        assert "undefined secret 'my_secret'" not in warning_messages.lower()

    def test_multiple_services_dependencies(self):
        """Should validate dependency chain across services."""
        validator = ComposeSchemaValidator()

        compose = """
services:
  web:
    image: nginx:1.25
    depends_on:
      - app

  app:
    image: node:18
    depends_on:
      - db

  db:
    image: postgres:15
"""
        is_valid, errors, warnings = validator.validate_content(compose)

        # All dependencies exist
        assert is_valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
