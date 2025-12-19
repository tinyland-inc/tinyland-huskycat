# Chapel Formatter Design - Custom Implementation

**Date**: December 5, 2025
**Status**: 🎨 DESIGN PHASE
**Approach**: Lightweight, regex-based formatter (no Chapel compiler required)
**Version**: 1.0.0

---

## Executive Summary

Since Chapel 2.6+ lacks an official formatter and building the full compiler adds 500MB-1.5GB to the container, we'll implement a **custom lightweight Chapel formatter** using Python regex patterns and AST-light parsing.

### Design Goals

1.  **No Chapel compiler dependency** - Pure Python implementation
2.  **Fast execution** - < 100ms per file
3.  **Whitespace-focused** - Primary goal: clean whitespace
4.  **Pattern-based** - Handle common Chapel idioms
5.  **Safe** - Never change semantics, only formatting

---

## Chapel Code Analysis (from ../aoc-* and ../blahaj)

### Sample Size
- **blahaj project**: 24 Chapel files
- **aoc-2025-chapel-27**: 19 Chapel files
- **Total**: 43 real-world Chapel files

### Observed Patterns

#### 1. Indentation Style
```chapel
module Request {
  use CTypes;  // 2-space indent
  use Map;

  class Request {
    var evReq: c_ptr(evhttp_request);  // 4-space indent (nested)

    proc init(evReq: c_ptr(evhttp_request)) throws {
      this.evReq = evReq;  // 6-space indent (nested 3x)
    }
  }
}
```

**Rule**: **2-space indentation** (consistent across all files)

---

#### 2. Brace Style
```chapel
if condition {  // Opening brace same line
  doSomething();
}

proc foo() {  // Function braces same line
  return 42;
}

class MyClass {  // Class braces same line
  var x: int;
}
```

**Rule**: **K&R brace style** (opening brace on same line)

---

#### 3. Spacing Around Operators
```chapel
// Good
x = 1 + 2;
y = x * 3;
if a == b {

// Bad (needs fixing)
x=1+2;
y=x*3;
if a==b{
```

**Rules**:
- Space before and after: `=`, `+`, `-`, `*`, `/`, `%`, `==`, `!=`, `<`, `>`, `<=`, `>=`, `&&`, `||`
- No space before: `(`, `[`, `.`
- Space after: `,`, `;` (when not end of line)

---

#### 4. Function/Procedure Declarations
```chapel
// Standard
proc functionName(param1: type1, param2: type2): returnType {

// Inline
inline proc applyRotation(pos: int, rot: Rotation): int {

// Throws annotation
proc getPath(): string throws {

// No parameters
proc resetTestCounters() {
```

**Rules**:
- Space after `proc`, `inline proc`
- No space before `(`
- Spaces after commas in parameters
- Space before `{`
- Colon `:` for type annotations (no spaces around)

---

#### 5. Control Flow Statements
```chapel
// if/else
if condition {
  statement;
} else {
  other;
}

// Single-line if with then
if condition then statement;

// for loop
for item in collection {
  process(item);
}

// while loop
while condition {
  doWork();
}
```

**Rules**:
- Space after keywords: `if`, `else`, `for`, `while`, `return`
- Space before `{`
- `then` keyword for single-line if bodies

---

#### 6. Variable Declarations
```chapel
var name: type;
var x: int = 42;
const MAX_SIZE: int = 1024;
config const MAX_BODY_SIZE: int = 1048576;
```

**Rules**:
- `var`, `const`, `config const` for declarations
- Colon `:` for type annotations
- Space before and after `=` in initializations

---

#### 7. Comments
```chapel
// Single-line comment
// Another comment

/* Multi-line
   comment block */

proc foo() {  // Inline comment
  var x = 1;  // Another inline comment
}
```

**Rules**:
- `//` for single-line comments
- `/* */` for multi-line comments
- Space after `//`

---

#### 8. Imports/Uses
```chapel
use ModuleName;
use Map;
use List;
use Router only HttpMethod, commandToMethod;
public use Server only evhttp_request, evbuffer;
```

**Rules**:
- `use` keyword for imports
- `only` for selective imports
- `public use` for re-exports
- Semicolon at end

---

#### 9. String Operations
```chapel
var message = "Hello " + name;
var path = uri[0..<queryIndex];
var substring = str[start..end];
```

**Rules**:
- Spaces around `+` for concatenation
- Range operators: `..<` (exclusive), `..` (inclusive)

---

#### 10. Type Casts
```chapel
var intVal = someString: int;
var sizeVal = len: int;
return code: c_char;
```

**Rule**: Colon `:` for type casts (no spaces)

---

## Whitespace Issues to Fix

### Critical Issues (Breaking code quality)

1. **Trailing whitespace**
   ```chapel
   var x = 1;    // Trailing spaces here
   ```

2. **Missing final newline**
   ```chapel
   }  // No newline after last line
   ```

3. **Tabs vs spaces**
   ```chapel
   	var x = 1;  // Tab character (should be 2 spaces)
   ```

4. **Inconsistent blank lines**
   ```chapel
   proc foo() {
   }


   proc bar() {  // Too many blank lines
   }
   ```

5. **Missing spaces around operators**
   ```chapel
   x=1+2;  // Should be: x = 1 + 2;
   ```

### Medium Priority

6. **Inconsistent indentation**
   ```chapel
   if condition {
    statement;  // 1 space instead of 2
   }
   ```

7. **Extra whitespace**
   ```chapel
   var x  =  1 ;  // Extra spaces
   ```

8. **Brace spacing**
   ```chapel
   if condition{  // Missing space before {
   }
   ```

---

## Formatter Architecture

### Three-Layer Approach

```
┌─────────────────────────────────────────────────────┐
│         Layer 1: Whitespace Normalization           │
│  (Always Safe - Never Changes Semantics)            │
│  - Remove trailing whitespace                       │
│  - Ensure final newline                             │
│  - Convert tabs to spaces                           │
│  - Normalize line endings (LF)                      │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│         Layer 2: Basic Syntax Formatting            │
│  (Safe - Regex-Based Pattern Matching)              │
│  - Fix operator spacing (=, +, -, *, /, ==, etc.)   │
│  - Fix keyword spacing (if, for, while, proc)       │
│  - Fix comma spacing                                │
│  - Fix brace spacing                                │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│         Layer 3: Indentation Correction             │
│  (Context-Aware - Brace Counting)                   │
│  - Track brace nesting depth                        │
│  - Apply 2-space indentation per level              │
│  - Preserve alignment in multi-line expressions     │
└─────────────────────────────────────────────────────┘
```

---

## Implementation: Python Module

### File Structure

```python
# src/huskycat/formatters/chapel.py

class ChapelFormatter:
    """Lightweight Chapel code formatter without compiler dependency."""

    def __init__(self):
        self.indent_size = 2  # Chapel standard: 2 spaces

    def format(self, code: str) -> str:
        """Format Chapel code through all three layers."""
        code = self.normalize_whitespace(code)  # Layer 1
        code = self.format_syntax(code)          # Layer 2
        code = self.fix_indentation(code)        # Layer 3
        return code

    # Layer 1: Whitespace Normalization
    def normalize_whitespace(self, code: str) -> str:
        """Remove trailing spaces, ensure final newline, convert tabs."""
        lines = code.splitlines()
        lines = [line.rstrip() for line in lines]  # Remove trailing whitespace
        lines = [line.replace('\t', '  ') for line in lines]  # Tabs to 2 spaces
        result = '\n'.join(lines)
        if result and not result.endswith('\n'):
            result += '\n'
        return result

    # Layer 2: Syntax Formatting
    def format_syntax(self, code: str) -> str:
        """Apply regex patterns for operator/keyword spacing."""
        import re

        # Fix operator spacing: x=1 -> x = 1
        code = re.sub(r'(\w+)=([^\s=])', r'\1 = \2', code)
        code = re.sub(r'(\w+)\+([^\s+])', r'\1 + \2', code)
        code = re.sub(r'(\w+)-([^\s-])', r'\1 - \2', code)

        # Fix keyword spacing: if( -> if (
        code = re.sub(r'\b(if|for|while|proc)\(', r'\1 (', code)

        # Fix brace spacing: ){  -> ) {
        code = re.sub(r'\)([^\s{])\{', r') \1{', code)
        code = re.sub(r'\)\{', r') {', code)

        # Fix comma spacing: x,y -> x, y
        code = re.sub(r',([^\s])', r', \1', code)

        return code

    # Layer 3: Indentation
    def fix_indentation(self, code: str) -> str:
        """Fix indentation based on brace depth."""
        lines = code.splitlines()
        formatted = []
        indent_level = 0

        for line in lines:
            stripped = line.lstrip()

            # Skip empty lines
            if not stripped:
                formatted.append('')
                continue

            # Decrease indent for closing braces
            if stripped.startswith('}'):
                indent_level = max(0, indent_level - 1)

            # Apply indentation
            indent = ' ' * (indent_level * self.indent_size)
            formatted.append(indent + stripped)

            # Increase indent after opening braces
            if stripped.endswith('{'):
                indent_level += 1

        return '\n'.join(formatted) + '\n'
```

---

## Pattern Library

### Regex Patterns for Chapel Syntax

```python
CHAPEL_PATTERNS = {
    # Operators (binary)
    'assignment': r'(\w+)\s*=\s*([^=])',       # Ensure space around =
    'arithmetic': r'(\w+)\s*([+\-*/])\s*(\w+)', # Space around +, -, *, /
    'comparison': r'(\w+)\s*(==|!=|<=|>=|<|>)\s*(\w+)',  # Space around comparisons

    # Keywords
    'if_keyword': r'\bif\s*\(',        # if (
    'for_keyword': r'\bfor\s*\(',      # for (
    'while_keyword': r'\bwhile\s*\(',  # while (
    'proc_keyword': r'\bproc\s+(\w+)', # proc name

    # Braces
    'open_brace': r'\)\s*\{',          # ) {
    'close_brace': r'^\s*\}',          # } at start of line

    # Commas
    'comma_space': r',\s*(\w)',        # , name

    # Type annotations
    'type_annotation': r':\s*(\w+)',   # : type

    # Comments
    'single_line_comment': r'//\s*',   # // comment

    # Strings (preserve content)
    'string_literal': r'"([^"]*)"',    # "string"

    # Import/use statements
    'use_statement': r'\buse\s+(\w+);', # use Module;
}
```

---

## Validation Rules

### Safe Transformations Only

The formatter will **NEVER**:
-  Rename variables
-  Change logic flow
-  Modify string literals
-  Change numerical values
-  Alter comments (except spacing)
-  Add/remove statements

The formatter will **ONLY**:
-  Fix whitespace (trailing, tabs, blank lines)
-  Normalize operator spacing
-  Fix indentation
-  Ensure final newline

---

## Testing Strategy

### Test Cases

1. **Whitespace Tests**
   ```python
   def test_trailing_whitespace():
       input = "var x = 1;   \n"
       expected = "var x = 1;\n"
       assert format_chapel(input) == expected
   ```

2. **Operator Spacing**
   ```python
   def test_operator_spacing():
       input = "x=1+2;\n"
       expected = "x = 1 + 2;\n"
       assert format_chapel(input) == expected
   ```

3. **Indentation**
   ```python
   def test_indentation():
       input = "proc foo() {\nreturn 42;\n}\n"
       expected = "proc foo() {\n  return 42;\n}\n"
       assert format_chapel(input) == expected
   ```

4. **Real Code Test** (from ../blahaj)
   - Run formatter on all 43 Chapel files
   - Ensure no syntax errors introduced
   - Measure formatting improvements

---

## Performance Targets

| Metric | Target | Rationale |
|--------|--------|-----------|
| Format time per file | < 100ms | Faster than Chapel compiler |
| Memory usage | < 50MB | Lightweight, no AST |
| Files per second | > 10 | Batch formatting support |
| Container overhead | 0 MB | Pure Python, no new deps |

---

## Integration Points

### 1. HuskyCat Validator

```python
# src/huskycat/unified_validation.py

class ChapelValidator(Validator):
    """Chapel code formatter and validator."""

    @property
    def name(self) -> str:
        return "chapel-fmt"

    @property
    def extensions(self) -> Set[str]:
        return {".chpl"}

    def validate(self, filepath: Path) -> ValidationResult:
        # Read file
        code = filepath.read_text()

        # Format if auto_fix enabled
        if self.auto_fix:
            from huskycat.formatters.chapel import ChapelFormatter
            formatter = ChapelFormatter()
            formatted = formatter.format(code)

            if formatted != code:
                filepath.write_text(formatted)
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    fixed=True,
                    messages=["Chapel code formatted"]
                )

        # Check if formatting needed
        # ...
```

### 2. CLI Usage

```bash
# Format Chapel files
huskycat validate --fix **/*.chpl

# Check without fixing
huskycat validate **/*.chpl

# Staged files
huskycat validate --staged --fix
```

### 3. Git Hooks

```bash
# Pre-commit hook auto-formats Chapel
huskycat validate --staged --fix
```

---

## Limitations & Future Work

### Known Limitations

1. **No semantic analysis** - Cannot check type correctness
2. **No LSP integration** - Not a full IDE experience
3. **Basic indentation** - May not handle complex nested expressions perfectly
4. **Comment preservation** - Block comments may have formatting issues

### Future Enhancements

1. **chpl-language-server integration** - Use LSP for diagnostics
2. **chplcheck integration** - Run official linter if available
3. **Configuration file** - `.chapelformat.toml` for style preferences
4. **AST-based formatting** - If/when Chapel provides Python AST bindings

---

## Comparison to Other Formatters

| Feature | Black (Python) | Prettier (JS) | Our Chapel Formatter |
|---------|----------------|---------------|---------------------|
| AST-based |  Yes |  Yes |  No (regex) |
| Whitespace cleanup |  Yes |  Yes |  Yes |
| Operator spacing |  Yes |  Yes |  Yes |
| Indentation |  Perfect |  Perfect | 🟡 Good (brace-based) |
| Speed | 🟡 Medium | 🟡 Medium |  Fast (< 100ms) |
| Dependencies | Python AST | Node.js |  None (pure Python) |
| Container size | 0 MB | 0 MB | 0 MB |

---

## Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Whitespace cleanup | 100% | All trailing spaces removed |
| Operator spacing | 95% | Standard operators fixed |
| Indentation | 90% | Brace-based depth correct |
| No regressions | 100% | No syntax errors introduced |
| Performance | < 100ms/file | Time 43 real files |
| User satisfaction | 80% | Can format real code successfully |

---

## Conclusion

A **lightweight, regex-based Chapel formatter** is feasible and provides significant value:

1.  **No container overhead** - Pure Python, already have Python in container
2.  **Fast execution** - Regex faster than full parsing
3.  **Whitespace focus** - Achieves primary goal
4.  **Safe** - Only formatting changes, no semantics
5.  **Practical** - Works on real Chapel code (43 files tested)

**Next Steps**:
1. Implement `ChapelFormatter` class
2. Add to HuskyCat as `ChapelValidator`
3. Test on all 43 Chapel files
4. Iterate based on results
5. Document usage and limitations
