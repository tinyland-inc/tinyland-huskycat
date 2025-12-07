#!/usr/bin/env python3
"""Lightweight Chapel code formatter without compiler dependency.

This formatter focuses on whitespace normalization, operator spacing,
and basic indentation without requiring the full Chapel compiler.

Design:
- Layer 1: Whitespace normalization (always safe)
- Layer 2: Syntax formatting (regex-based patterns)
- Layer 3: Indentation correction (brace counting)

Usage:
    formatter = ChapelFormatter()
    formatted_code = formatter.format(code)
"""

import re
from typing import List, Tuple


class ChapelFormatter:
    """Lightweight Chapel code formatter.

    Formats Chapel code using regex patterns and brace counting,
    without requiring the Chapel compiler or full AST parsing.
    """

    def __init__(self, indent_size: int = 2):
        """Initialize formatter with configuration.

        Args:
            indent_size: Number of spaces per indentation level (default: 2)
        """
        self.indent_size = indent_size
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for performance."""
        # Operator patterns
        self.patterns = {
            # Fix spacing around = (but not ==, !=, <=, >=)
            "assignment": re.compile(r"(\w+)\s*=\s*([^=\s])"),
            "assignment_pre": re.compile(r"(\w+)\s*="),
            # Fix spacing around + (but not ++)
            "plus": re.compile(r"(\w+)\s*\+\s*(\w+)"),
            # Fix spacing around - (but not --)
            "minus": re.compile(r"(\w+)\s*-\s*(\w+)"),
            # Fix spacing around * / %
            "multiply": re.compile(r"(\w+)\s*\*\s*(\w+)"),
            "divide": re.compile(r"(\w+)\s*/\s*(\w+)"),
            "modulo": re.compile(r"(\w+)\s*%\s*(\w+)"),
            # Fix spacing around comparisons
            "equal": re.compile(r"(\w+)\s*==\s*(\w+)"),
            "not_equal": re.compile(r"(\w+)\s*!=\s*(\w+)"),
            "less_equal": re.compile(r"(\w+)\s*<=\s*(\w+)"),
            "greater_equal": re.compile(r"(\w+)\s*>=\s*(\w+)"),
            "less": re.compile(r"(\w+)\s*<\s*([^\s=])"),
            "greater": re.compile(r"(\w+)\s*>\s*([^\s=])"),
            # Fix spacing around logical operators
            "and": re.compile(r"(\w+)\s*&&\s*(\w+)"),
            "or": re.compile(r"(\w+)\s*\|\|\s*(\w+)"),
            # Fix keyword spacing
            "if_keyword": re.compile(r"\bif\s*\("),
            "else_keyword": re.compile(r"\belse\s+"),
            "for_keyword": re.compile(r"\bfor\s*\("),
            "while_keyword": re.compile(r"\bwhile\s*\("),
            "proc_keyword": re.compile(r"\b(inline\s+)?proc\s+"),
            "return_keyword": re.compile(r"\breturn\s+"),
            # Fix brace spacing
            "open_brace_paren": re.compile(r"\)\s*\{"),
            "open_brace_word": re.compile(r"(\w)\s*\{"),
            # Fix comma spacing
            "comma": re.compile(r",\s*([^\s])"),
            # Fix semicolon spacing
            "semicolon": re.compile(r";\s*([^\s\n])"),
            # Fix colon spacing in type annotations (keep no space)
            "type_colon": re.compile(r"(\w+)\s*:\s*(\w+)"),
            # Comment spacing
            "single_comment": re.compile(r"//\s*"),
        }

    def format(self, code: str) -> str:
        """Format Chapel code through all three layers.

        Args:
            code: Chapel source code string

        Returns:
            Formatted Chapel code string
        """
        # Layer 1: Whitespace normalization
        code = self.normalize_whitespace(code)

        # Layer 2: Syntax formatting
        code = self.format_syntax(code)

        # Layer 3: Indentation correction
        code = self.fix_indentation(code)

        return code

    # ========== Layer 1: Whitespace Normalization ==========

    def normalize_whitespace(self, code: str) -> str:
        """Normalize whitespace (always safe transformations).

        - Remove trailing whitespace
        - Convert tabs to spaces
        - Ensure final newline
        - Normalize line endings to LF

        Args:
            code: Chapel source code

        Returns:
            Code with normalized whitespace
        """
        # Normalize line endings to LF
        code = code.replace("\r\n", "\n").replace("\r", "\n")

        # Split into lines
        lines = code.splitlines()

        # Remove trailing whitespace
        lines = [line.rstrip() for line in lines]

        # Convert tabs to spaces (Chapel standard: 2 spaces)
        lines = [line.replace("\t", " " * self.indent_size) for line in lines]

        # Rejoin lines
        result = "\n".join(lines)

        # Ensure final newline
        if result and not result.endswith("\n"):
            result += "\n"

        return result

    # ========== Layer 2: Syntax Formatting ==========

    def format_syntax(self, code: str) -> str:
        """Apply regex patterns for operator/keyword spacing.

        Args:
            code: Chapel code with normalized whitespace

        Returns:
            Code with fixed syntax spacing
        """
        lines = code.splitlines()
        formatted_lines = []

        for line in lines:
            # Skip empty lines and pure comments
            if not line.strip() or line.strip().startswith("//"):
                formatted_lines.append(line)
                continue

            # Preserve string literals (simple approach)
            # Extract strings, format rest, restore strings
            parts, strings = self._extract_strings(line)

            # Format each part (outside strings)
            formatted_parts = []
            for part in parts:
                formatted_part = self._format_line_part(part)
                formatted_parts.append(formatted_part)

            # Restore strings
            result = self._restore_strings(formatted_parts, strings)
            formatted_lines.append(result)

        return "\n".join(formatted_lines) + "\n"

    def _extract_strings(self, line: str) -> Tuple[List[str], List[str]]:
        """Extract string literals to avoid modifying them.

        Args:
            line: Source line

        Returns:
            Tuple of (parts without strings, extracted strings)
        """
        parts = []
        strings = []
        current = ""
        in_string = False
        escape_next = False

        for ch in line:
            if escape_next:
                current += ch
                escape_next = False
                continue

            if ch == "\\":
                escape_next = True
                current += ch
                continue

            if ch == '"':
                if in_string:
                    # End of string
                    strings.append(current + '"')
                    current = ""
                    parts.append(f"__STRING_{len(strings) - 1}__")
                    in_string = False
                else:
                    # Start of string
                    if current:
                        parts.append(current)
                    current = '"'
                    in_string = True
            else:
                current += ch

        # Add remaining
        if current:
            if in_string:
                strings.append(current)
                parts.append(f"__STRING_{len(strings) - 1}__")
            else:
                parts.append(current)

        if not parts:
            parts = [line]

        return (parts, strings)

    def _restore_strings(self, parts: List[str], strings: List[str]) -> str:
        """Restore string literals after formatting.

        Args:
            parts: Formatted parts with placeholders
            strings: Original string literals

        Returns:
            Line with strings restored
        """
        result = "".join(parts)
        for i, string in enumerate(strings):
            placeholder = f"__STRING_{i}__"
            result = result.replace(placeholder, string)
        return result

    def _format_line_part(self, part: str) -> str:
        """Format a line part (outside string literals).

        Args:
            part: Line part to format

        Returns:
            Formatted line part
        """
        # Skip if part is empty or just whitespace
        if not part.strip():
            return part

        # Operators - ensure space around
        part = re.sub(r"(\w+)\s*=\s*([^=])", r"\1 = \2", part)  # assignment
        part = re.sub(r"(\w+)\s*\+\s*(\w+)", r"\1 + \2", part)  # plus
        part = re.sub(r"(\w+)\s*-\s*(\w+)", r"\1 - \2", part)  # minus
        part = re.sub(r"(\w+)\s*\*\s*(\w+)", r"\1 * \2", part)  # multiply
        part = re.sub(r"(\w+)\s*/\s*(\w+)", r"\1 / \2", part)  # divide
        part = re.sub(r"(\w+)\s*%\s*(\w+)", r"\1 % \2", part)  # modulo

        # Comparisons
        part = re.sub(r"(\w+)\s*==\s*(\w+)", r"\1 == \2", part)
        part = re.sub(r"(\w+)\s*!=\s*(\w+)", r"\1 != \2", part)
        part = re.sub(r"(\w+)\s*<=\s*(\w+)", r"\1 <= \2", part)
        part = re.sub(r"(\w+)\s*>=\s*(\w+)", r"\1 >= \2", part)
        part = re.sub(r"(\w+)\s*<\s*([^\s=])", r"\1 < \2", part)
        part = re.sub(r"(\w+)\s*>\s*([^\s=])", r"\1 > \2", part)

        # Logical operators
        part = re.sub(r"(\w+)\s*&&\s*(\w+)", r"\1 && \2", part)
        part = re.sub(r"(\w+)\s*\|\|\s*(\w+)", r"\1 || \2", part)

        # Keywords - ensure space after
        part = re.sub(r"\bif\s*\(", "if (", part)
        part = re.sub(r"\bfor\s*\(", "for (", part)
        part = re.sub(r"\bwhile\s*\(", "while (", part)
        part = re.sub(r"\breturn\s+", "return ", part)

        # Braces - ensure space before {
        part = re.sub(r"\)\s*\{", ") {", part)
        part = re.sub(r"(\w)\s*\{", r"\1 {", part)

        # Commas - ensure space after
        part = re.sub(r",\s*([^\s])", r", \1", part)

        # Semicolons - ensure no space before, space after (if not end of line)
        part = re.sub(r"\s*;", ";", part)
        part = re.sub(r";\s*([^\s])", r"; \1", part)

        # Type annotations - no space around colon
        part = re.sub(r"(\w+)\s*:\s*(\w+)", r"\1: \2", part)

        return part

    # ========== Layer 3: Indentation Correction ==========

    def fix_indentation(self, code: str) -> str:
        """Fix indentation based on brace depth.

        Args:
            code: Code with fixed syntax

        Returns:
            Code with corrected indentation
        """
        lines = code.splitlines()
        formatted = []
        indent_level = 0

        for line in lines:
            stripped = line.lstrip()

            # Skip empty lines (preserve them)
            if not stripped:
                formatted.append("")
                continue

            # Calculate indent adjustment for this line
            # Closing braces decrease indent BEFORE the line
            opens_before_close = stripped.find("}")
            if opens_before_close == 0:
                indent_level = max(0, indent_level - 1)

            # Apply indentation
            indent = " " * (indent_level * self.indent_size)
            formatted_line = indent + stripped

            formatted.append(formatted_line)

            # Count brace changes for next line
            # Opening braces increase indent AFTER the line
            open_count = stripped.count("{")
            close_count = stripped.count("}")

            # Adjust indent for next line
            indent_level += open_count - close_count
            indent_level = max(0, indent_level)  # Never go negative

        # Join lines and ensure final newline
        result = "\n".join(formatted)
        if result and not result.endswith("\n"):
            result += "\n"

        return result

    # ========== Validation Methods ==========

    def check_formatting(self, code: str) -> List[str]:
        """Check if code needs formatting.

        Args:
            code: Chapel source code

        Returns:
            List of formatting issues found
        """
        issues = []

        # Check trailing whitespace
        for i, line in enumerate(code.splitlines(), 1):
            if line != line.rstrip():
                issues.append(f"Line {i}: Trailing whitespace")

        # Check final newline
        if code and not code.endswith("\n"):
            issues.append("Missing final newline")

        # Check tabs
        if "\t" in code:
            issues.append("Contains tab characters (use spaces)")

        # Check if formatting would change code
        formatted = self.format(code)
        if formatted != code:
            issues.append("Code formatting differs from standard")

        return issues


def format_chapel_file(filepath: str, in_place: bool = False) -> str:
    """Format a Chapel file.

    Args:
        filepath: Path to .chpl file
        in_place: If True, write formatted code back to file

    Returns:
        Formatted code
    """
    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()

    formatter = ChapelFormatter()
    formatted = formatter.format(code)

    if in_place and formatted != code:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(formatted)

    return formatted


# CLI entry point for standalone use
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python chapel.py <file.chpl> [--check]")
        sys.exit(1)

    filepath = sys.argv[1]
    check_only = "--check" in sys.argv

    formatter = ChapelFormatter()

    with open(filepath, "r") as f:
        code = f.read()

    if check_only:
        issues = formatter.check_formatting(code)
        if issues:
            print(f"Formatting issues in {filepath}:")
            for issue in issues:
                print(f"  - {issue}")
            sys.exit(1)
        else:
            print(f"{filepath}: OK")
            sys.exit(0)
    else:
        formatted = formatter.format(code)
        if formatted != code:
            with open(filepath, "w") as f:
                f.write(formatted)
            print(f"{filepath}: Formatted")
        else:
            print(f"{filepath}: Already formatted")
        sys.exit(0)
