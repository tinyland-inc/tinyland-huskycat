#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Demo script showing HuskyCat YAML linter capabilities.
"""

import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from huskycat.linters.yaml_lint import YamlLintConfig, lint_yaml
from huskycat.linters.yaml_lint_validator import YamlLintValidator


def demo_basic_linting():
    """Demonstrate basic YAML linting."""
    print("=" * 60)
    print("Basic YAML Linting Demo")
    print("=" * 60)

    # Example with issues
    yaml_with_issues = """
name: test-project
version: 1.0.0

config:
  key1: value1
  key1: duplicate

database:
  host: localhost
  port:
  username: admin
""".strip()

    print("\nYAML Content:")
    print(yaml_with_issues)
    print("\nLinting results:")

    issues = lint_yaml(yaml_with_issues)

    if issues:
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  ✓ No issues found")


def demo_custom_config():
    """Demonstrate custom configuration."""
    print("\n" + "=" * 60)
    print("Custom Configuration Demo")
    print("=" * 60)

    content = "key: value  \n" + ("x" * 130) + "\n"

    # Default config - strict
    print("\n1. Default configuration (strict):")
    issues = lint_yaml(content)
    print(f"   Found {len(issues)} issues:")
    for issue in issues:
        print(f"     {issue}")

    # Relaxed config
    print("\n2. Relaxed configuration:")
    config = {
        "allow_trailing_whitespace": True,
        "max_line_length": 200,
    }
    issues = lint_yaml(content, config=config)
    print(f"   Found {len(issues)} issues")

    # Disabled rules
    print("\n3. With disabled rules:")
    config = {"disabled_rules": ["trailing-whitespace", "line-length"]}
    issues = lint_yaml(content, config=config)
    print(f"   Found {len(issues)} issues")


def demo_validator_integration():
    """Demonstrate integration with HuskyCat validator."""
    print("\n" + "=" * 60)
    print("Validator Integration Demo")
    print("=" * 60)

    # Create a temporary test file
    test_file = Path("demo_test.yaml")
    test_content = """
name: demo
config:
  setting1: value1
  setting2: value2
"""
    test_file.write_text(test_content.strip())

    try:
        validator = YamlLintValidator()

        print(f"\nValidating: {test_file}")
        result = validator.validate(test_file)

        print(f"  Tool: {result.tool}")
        print(f"  Success: {result.success}")
        print(f"  Duration: {result.duration_ms}ms")
        print(f"  Errors: {result.error_count}")
        print(f"  Warnings: {result.warning_count}")

        if result.errors:
            print("\n  Errors:")
            for error in result.errors:
                print(f"    {error}")

        if result.warnings:
            print("\n  Warnings:")
            for warning in result.warnings:
                print(f"    {warning}")

    finally:
        test_file.unlink()


def demo_all_rules():
    """Demonstrate all validation rules."""
    print("\n" + "=" * 60)
    print("All Validation Rules Demo")
    print("=" * 60)

    examples = [
        (
            "1. Trailing whitespace",
            "key: value  \n",
            "trailing-whitespace",
        ),
        (
            "2. Line length",
            "key: " + ("x" * 120) + "\n",
            "line-length",
        ),
        (
            "3. Tab indentation",
            "key:\n\tvalue: test\n",
            "indentation",
        ),
        (
            "4. Duplicate keys",
            "config:\n  key: value1\n  key: value2\n",
            "duplicate-keys",
        ),
        (
            "5. Empty values",
            "database:\n  host:\n  port: 5432\n",
            "empty-values",
        ),
    ]

    for title, content, expected_rule in examples:
        print(f"\n{title}:")
        print(f"  Content: {repr(content[:40])}...")

        # Use strict config to catch all issues
        config = {"allow_empty_values": False} if expected_rule == "empty-values" else None

        issues = lint_yaml(content, config=config)
        matching = [i for i in issues if i.rule == expected_rule]

        if matching:
            print(f"  ✓ Detected: {matching[0].message}")
        else:
            print(f"  ✗ Not detected (found {len(issues)} other issues)")


if __name__ == "__main__":
    print("\n🔍 HuskyCat YAML Linter Demo\n")
    print("Clean-room implementation (Apache 2.0 license)")
    print("Based on YAML 1.2 specification\n")

    demo_basic_linting()
    demo_custom_config()
    demo_validator_integration()
    demo_all_rules()

    print("\n" + "=" * 60)
    print("Demo completed!")
    print("=" * 60)
    print("\nFor more information, see src/huskycat/linters/README.md")
