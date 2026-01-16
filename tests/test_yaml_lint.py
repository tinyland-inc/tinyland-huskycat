# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for clean-room YAML linter implementation.
"""

import tempfile
from pathlib import Path

import pytest

from huskycat.linters.yaml_lint import (
    YamlIssue,
    YamlLintConfig,
    YamlLinter,
    lint_yaml,
    lint_yaml_file,
)


class TestYamlIssue:
    """Tests for YamlIssue dataclass."""

    def test_issue_str_representation(self):
        """Test string representation of issue."""
        issue = YamlIssue(
            line=10, column=5, rule="test-rule", message="Test message", severity="warning"
        )
        assert str(issue) == "10:5: [warning] test-rule: Test message"

    def test_issue_to_dict(self):
        """Test dictionary conversion."""
        issue = YamlIssue(
            line=10, column=5, rule="test-rule", message="Test message", severity="error"
        )
        result = issue.to_dict()
        assert result == {
            "line": 10,
            "column": 5,
            "rule": "test-rule",
            "message": "Test message",
            "severity": "error",
        }


class TestYamlLintConfig:
    """Tests for YamlLintConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = YamlLintConfig()
        assert config.max_line_length == 120
        assert config.allow_tabs is False
        assert config.allow_trailing_whitespace is False
        assert config.allow_empty_values is True
        assert config.allow_duplicate_keys is False
        assert len(config.disabled_rules) == 0

    def test_from_dict(self):
        """Test configuration from dictionary."""
        config_dict = {
            "max_line_length": 100,
            "allow_tabs": True,
            "disabled_rules": ["trailing-whitespace"],
        }
        config = YamlLintConfig.from_dict(config_dict)
        assert config.max_line_length == 100
        assert config.allow_tabs is True
        assert "trailing-whitespace" in config.disabled_rules

    def test_from_dict_none(self):
        """Test configuration from None returns defaults."""
        config = YamlLintConfig.from_dict(None)
        assert config.max_line_length == 120


class TestYamlLinter:
    """Tests for YamlLinter class."""

    def test_trailing_whitespace_detection(self):
        """Test detection of trailing whitespace."""
        content = "key: value  \nanother_key: value\n"
        linter = YamlLinter()
        issues = linter.lint(content)

        trailing_issues = [i for i in issues if i.rule == "trailing-whitespace"]
        assert len(trailing_issues) == 1
        assert trailing_issues[0].line == 1

    def test_trailing_whitespace_allowed(self):
        """Test that trailing whitespace is ignored when allowed."""
        content = "key: value  \nanother_key: value\n"
        config = YamlLintConfig(allow_trailing_whitespace=True)
        linter = YamlLinter(config)
        issues = linter.lint(content)

        trailing_issues = [i for i in issues if i.rule == "trailing-whitespace"]
        assert len(trailing_issues) == 0

    def test_line_length_detection(self):
        """Test detection of lines exceeding max length."""
        long_line = "x" * 121
        content = f"key: {long_line}\n"
        linter = YamlLinter()
        issues = linter.lint(content)

        length_issues = [i for i in issues if i.rule == "line-length"]
        assert len(length_issues) == 1
        assert "exceeds maximum length" in length_issues[0].message

    def test_line_length_custom_limit(self):
        """Test line length with custom limit."""
        content = "x" * 51 + "\n"
        config = YamlLintConfig(max_line_length=50)
        linter = YamlLinter(config)
        issues = linter.lint(content)

        length_issues = [i for i in issues if i.rule == "line-length"]
        assert len(length_issues) == 1

    def test_tab_indentation_detection(self):
        """Test detection of tabs in indentation."""
        content = "key:\n\tvalue: test\n"
        linter = YamlLinter()
        issues = linter.lint(content)

        tab_issues = [i for i in issues if i.rule == "indentation" and "Tab character" in i.message]
        assert len(tab_issues) >= 1
        assert tab_issues[0].severity == "error"

    def test_tab_indentation_allowed(self):
        """Test that tabs are allowed when configured."""
        content = "key:\n\tvalue: test\n"
        config = YamlLintConfig(allow_tabs=True)
        linter = YamlLinter(config)
        issues = linter.lint(content)

        # Should still warn about mixed indentation but not error on tabs
        tab_errors = [
            i
            for i in issues
            if i.rule == "indentation" and i.severity == "error" and "Tab character" in i.message
        ]
        assert len(tab_errors) == 0

    def test_duplicate_keys_detection(self):
        """Test detection of duplicate keys."""
        content = """
config:
  key1: value1
  key2: value2
  key1: duplicate
"""
        linter = YamlLinter()
        issues = linter.lint(content)

        dup_issues = [i for i in issues if i.rule == "duplicate-keys"]
        assert len(dup_issues) >= 1
        assert "Duplicate key" in dup_issues[0].message
        assert dup_issues[0].severity == "error"

    def test_empty_values_detection(self):
        """Test detection of empty values."""
        content = "database:\n  host: localhost\n  port:\n  username: admin\n"
        config = YamlLintConfig(allow_empty_values=False)
        linter = YamlLinter(config)
        issues = linter.lint(content)

        empty_issues = [i for i in issues if i.rule == "empty-values"]
        assert len(empty_issues) >= 1
        assert "Empty value" in empty_issues[0].message

    def test_empty_values_allowed(self):
        """Test that empty values are ignored when allowed."""
        content = "database:\n  host: localhost\n  port:\n"
        config = YamlLintConfig(allow_empty_values=True)
        linter = YamlLinter(config)
        issues = linter.lint(content)

        empty_issues = [i for i in issues if i.rule == "empty-values"]
        assert len(empty_issues) == 0

    def test_disabled_rules(self):
        """Test disabling specific rules."""
        content = "key: value  \nlong: " + ("x" * 101) + "\n"
        config = YamlLintConfig(disabled_rules={"trailing-whitespace", "line-length"})
        linter = YamlLinter(config)
        issues = linter.lint(content)

        # Should have no trailing-whitespace or line-length issues
        disabled_issues = [
            i for i in issues if i.rule in ("trailing-whitespace", "line-length")
        ]
        assert len(disabled_issues) == 0

    def test_valid_yaml(self):
        """Test that valid YAML produces no issues."""
        content = """
name: test-project
version: 1.0.0
config:
  key1: value1
  key2: value2
"""
        linter = YamlLinter()
        issues = linter.lint(content)
        assert len(issues) == 0

    def test_parse_error_handling(self):
        """Test handling of YAML parse errors."""
        content = "key: [invalid\n"
        linter = YamlLinter()
        issues = linter.lint(content)

        parse_issues = [i for i in issues if i.rule == "parse-error"]
        assert len(parse_issues) >= 1
        assert parse_issues[0].severity == "error"


class TestLintFunctions:
    """Tests for module-level lint functions."""

    def test_lint_yaml(self):
        """Test lint_yaml function."""
        content = "key: value  \n"
        issues = lint_yaml(content)
        assert len(issues) >= 1

    def test_lint_yaml_with_config(self):
        """Test lint_yaml with configuration."""
        content = "key: value  \n"
        config = {"allow_trailing_whitespace": True}
        issues = lint_yaml(content, config)

        trailing_issues = [i for i in issues if i.rule == "trailing-whitespace"]
        assert len(trailing_issues) == 0

    def test_lint_yaml_file(self):
        """Test lint_yaml_file function."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("key: value\n")
            f.flush()
            filepath = Path(f.name)

        try:
            issues = lint_yaml_file(filepath)
            assert isinstance(issues, list)
        finally:
            filepath.unlink()

    def test_lint_yaml_file_not_found(self):
        """Test lint_yaml_file with non-existent file."""
        with pytest.raises(FileNotFoundError):
            lint_yaml_file(Path("/nonexistent/file.yaml"))


class TestComplexYamlScenarios:
    """Tests for complex YAML scenarios."""

    def test_nested_duplicate_keys(self):
        """Test duplicate keys in nested structures."""
        content = """
root:
  level1:
    key: value1
    key: value2
"""
        linter = YamlLinter()
        issues = linter.lint(content)

        dup_issues = [i for i in issues if i.rule == "duplicate-keys"]
        assert len(dup_issues) >= 1

    def test_multiple_issues_single_file(self):
        """Test detection of multiple different issues."""
        content = (
            "key: value  \n"  # trailing whitespace
            + "\tindented: value\n"  # tab indentation
            + ("x" * 121) + "\n"  # line length
        )
        linter = YamlLinter()
        issues = linter.lint(content)

        assert len(issues) >= 3
        rules = {issue.rule for issue in issues}
        assert "trailing-whitespace" in rules
        assert "indentation" in rules
        assert "line-length" in rules

    def test_comments_ignored(self):
        """Test that comments are handled correctly."""
        content = "# This is a comment\nkey: value  \n# Another comment\n"
        linter = YamlLinter()
        issues = linter.lint(content)

        # Should detect trailing whitespace on content line (line 2)
        trailing_issues = [i for i in issues if i.rule == "trailing-whitespace"]
        assert len(trailing_issues) >= 1
        assert any(i.line == 2 for i in trailing_issues)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
