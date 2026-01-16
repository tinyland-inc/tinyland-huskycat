# SPDX-License-Identifier: Apache-2.0
"""
Clean-room YAML linter implementation based on YAML 1.2 specification.

This implementation does NOT use GPL code. It is based on:
- YAML 1.2 specification (public domain specification)
- PyYAML (MIT license) for parsing
- Original rule implementations

Rules implemented:
1. Trailing whitespace detection
2. Line length enforcement (configurable, default 120)
3. Indentation consistency (tabs vs spaces)
4. Duplicate key detection
5. Empty value validation
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


@dataclass
class YamlIssue:
    """Represents a single YAML linting issue."""

    line: int
    column: int
    rule: str
    message: str
    severity: str = "warning"

    def __str__(self) -> str:
        """Format issue as human-readable string."""
        return f"{self.line}:{self.column}: [{self.severity}] {self.rule}: {self.message}"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "line": self.line,
            "column": self.column,
            "rule": self.rule,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass
class YamlLintConfig:
    """Configuration for YAML linting."""

    max_line_length: int = 120
    allow_tabs: bool = False
    allow_trailing_whitespace: bool = False
    allow_empty_values: bool = True
    allow_duplicate_keys: bool = False
    disabled_rules: Set[str] = field(default_factory=set)

    @classmethod
    def from_dict(cls, config: Optional[dict]) -> "YamlLintConfig":
        """Create config from dictionary."""
        if not config:
            return cls()

        return cls(
            max_line_length=config.get("max_line_length", 120),
            allow_tabs=config.get("allow_tabs", False),
            allow_trailing_whitespace=config.get("allow_trailing_whitespace", False),
            allow_empty_values=config.get("allow_empty_values", True),
            allow_duplicate_keys=config.get("allow_duplicate_keys", False),
            disabled_rules=set(config.get("disabled_rules", [])),
        )


class YamlLinter:
    """YAML linter implementing clean-room validation rules."""

    def __init__(self, config: Optional[YamlLintConfig] = None):
        """Initialize linter with configuration.

        Args:
            config: Linting configuration, uses defaults if None
        """
        self.config = config or YamlLintConfig()
        self.issues: List[YamlIssue] = []

    def lint(self, content: str) -> List[YamlIssue]:
        """Lint YAML content for common issues.

        Args:
            content: YAML content as string

        Returns:
            List of YamlIssue objects found
        """
        self.issues = []
        lines = content.splitlines(keepends=True)

        # Run line-based checks
        self._check_trailing_whitespace(lines)
        self._check_line_length(lines)
        self._check_indentation(lines)

        # Run parsing-based checks (requires PyYAML)
        if yaml is not None:
            self._check_duplicate_keys(content)
            self._check_empty_values(content, lines)

        return sorted(self.issues, key=lambda i: (i.line, i.column))

    def _check_trailing_whitespace(self, lines: List[str]) -> None:
        """Check for trailing whitespace on lines.

        Based on YAML 1.2 spec: trailing whitespace is allowed but often unintended.
        """
        if "trailing-whitespace" in self.config.disabled_rules:
            return

        if self.config.allow_trailing_whitespace:
            return

        for line_num, line in enumerate(lines, start=1):
            # Skip empty lines (common in YAML documents)
            if not line.strip():
                continue

            # Check if line has trailing whitespace before newline
            stripped = line.rstrip("\r\n")
            if stripped and stripped[-1] in (" ", "\t"):
                column = len(stripped)
                self.issues.append(
                    YamlIssue(
                        line=line_num,
                        column=column,
                        rule="trailing-whitespace",
                        message="Trailing whitespace found",
                        severity="warning",
                    )
                )

    def _check_line_length(self, lines: List[str]) -> None:
        """Check for lines exceeding maximum length.

        Based on common practice and readability guidelines.
        """
        if "line-length" in self.config.disabled_rules:
            return

        for line_num, line in enumerate(lines, start=1):
            # Remove newline for accurate length
            line_content = line.rstrip("\r\n")
            if len(line_content) > self.config.max_line_length:
                self.issues.append(
                    YamlIssue(
                        line=line_num,
                        column=self.config.max_line_length + 1,
                        rule="line-length",
                        message=f"Line exceeds maximum length of {self.config.max_line_length} characters ({len(line_content)} > {self.config.max_line_length})",
                        severity="warning",
                    )
                )

    def _check_indentation(self, lines: List[str]) -> None:
        """Check for consistent indentation (tabs vs spaces).

        Based on YAML 1.2 spec section 6.2: Indentation Spaces
        YAML allows only space characters for indentation, not tabs.
        """
        if "indentation" in self.config.disabled_rules:
            return

        # Track indentation type (spaces or tabs) from first indented line
        uses_spaces = False
        uses_tabs = False

        for line_num, line in enumerate(lines, start=1):
            # Skip empty lines and non-indented lines
            if not line or line[0] not in (" ", "\t"):
                continue

            # Extract leading whitespace
            leading_ws = re.match(r"^[\s]*", line)
            if not leading_ws:
                continue

            whitespace = leading_ws.group(0)

            # Check for tabs
            if "\t" in whitespace:
                uses_tabs = True
                if not self.config.allow_tabs:
                    self.issues.append(
                        YamlIssue(
                            line=line_num,
                            column=whitespace.index("\t") + 1,
                            rule="indentation",
                            message="Tab character found in indentation (YAML spec requires spaces)",
                            severity="error",
                        )
                    )

            # Check for spaces
            if " " in whitespace:
                uses_spaces = True

        # Warn about mixed indentation
        if uses_spaces and uses_tabs:
            self.issues.append(
                YamlIssue(
                    line=1,
                    column=1,
                    rule="indentation",
                    message="Mixed tabs and spaces in indentation",
                    severity="warning",
                )
            )

    def _check_duplicate_keys(self, content: str) -> None:
        """Check for duplicate keys in YAML mappings.

        Based on YAML 1.2 spec section 3.2.1.2: Keys are unique within a mapping.
        """
        if "duplicate-keys" in self.config.disabled_rules:
            return

        if self.config.allow_duplicate_keys:
            return

        try:
            # Use custom constructor to track duplicate keys
            class DuplicateKeyLoader(yaml.SafeLoader):
                pass

            def check_duplicates(loader, node):
                """Constructor that checks for duplicate keys."""
                mapping = {}
                for key_node, value_node in node.value:
                    key = loader.construct_object(key_node)
                    if key in mapping:
                        # Found duplicate key
                        self.issues.append(
                            YamlIssue(
                                line=key_node.start_mark.line + 1,
                                column=key_node.start_mark.column + 1,
                                rule="duplicate-keys",
                                message=f"Duplicate key '{key}' found in mapping",
                                severity="error",
                            )
                        )
                    mapping[key] = loader.construct_object(value_node)
                return mapping

            DuplicateKeyLoader.add_constructor(
                yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, check_duplicates
            )

            # Parse YAML with duplicate key detection
            yaml.load(content, Loader=DuplicateKeyLoader)

        except yaml.YAMLError as e:
            # If parsing fails, add as a parse error
            if hasattr(e, "problem_mark"):
                mark = e.problem_mark
                self.issues.append(
                    YamlIssue(
                        line=mark.line + 1,
                        column=mark.column + 1,
                        rule="parse-error",
                        message=f"YAML parsing error: {e.problem}",
                        severity="error",
                    )
                )
            else:
                self.issues.append(
                    YamlIssue(
                        line=1,
                        column=1,
                        rule="parse-error",
                        message=f"YAML parsing error: {str(e)}",
                        severity="error",
                    )
                )

    def _check_empty_values(self, content: str, lines: List[str]) -> None:
        """Check for empty values in key-value pairs.

        Based on YAML 1.2 spec: empty values are valid but often unintended.
        """
        if "empty-values" in self.config.disabled_rules:
            return

        if self.config.allow_empty_values:
            return

        # Pattern to match key-value pairs with empty values
        # Examples: "key:", "key: ", "key:\n"
        empty_value_pattern = re.compile(r"^\s*[\w\-]+:\s*(?:#.*)?$")

        for line_num, line in enumerate(lines, start=1):
            # Skip comments and empty lines
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Check for empty value pattern
            if empty_value_pattern.match(line):
                # Extract the key for better error message
                key_match = re.match(r"^\s*([\w\-]+):", line)
                if key_match:
                    key = key_match.group(1)
                    self.issues.append(
                        YamlIssue(
                            line=line_num,
                            column=len(line.rstrip("\r\n")),
                            rule="empty-values",
                            message=f"Empty value for key '{key}'",
                            severity="warning",
                        )
                    )


def lint_yaml(content: str, config: Optional[dict] = None) -> List[YamlIssue]:
    """Lint YAML content for common issues.

    Args:
        content: YAML content as string
        config: Optional configuration dictionary

    Returns:
        List of YamlIssue objects found

    Example:
        >>> issues = lint_yaml("key:  \\n  value: test")
        >>> for issue in issues:
        ...     print(issue)
    """
    lint_config = YamlLintConfig.from_dict(config)
    linter = YamlLinter(lint_config)
    return linter.lint(content)


def lint_yaml_file(path: Path, config: Optional[dict] = None) -> List[YamlIssue]:
    """Lint a YAML file.

    Args:
        path: Path to YAML file
        config: Optional configuration dictionary

    Returns:
        List of YamlIssue objects found

    Raises:
        FileNotFoundError: If file does not exist
        PermissionError: If file cannot be read
    """
    content = path.read_text(encoding="utf-8")
    return lint_yaml(content, config)
