# Chapel Formatter Future Enhancements

**Date**: December 5, 2025
**Status**:  PLANNING
**Phase**: Post-Sprint 8B
**Version**: 2.0.0 (future)

---

## Overview

This document outlines potential future enhancements for the Chapel formatter integration in HuskyCat. The current implementation (v1.0.0) provides lightweight, regex-based formatting without Chapel compiler dependency. Future versions could add more advanced features.

---

## Enhancement Categories

### Phase 1: Core Improvements (Low Effort, High Value)

#### 1.1 Import Sorting

**Status**:  Planned
**Effort**: 2-3 days
**Value**: Medium

**Description**:
Add automatic sorting and organization of `use` statements.

**Implementation**:
```python
def sort_imports(code: str) -> str:
    """Sort Chapel use statements alphabetically."""
    # Extract use statements
    # Group by:
    #   1. Standard library (use CTypes, use Map)
    #   2. Public imports (public use Server)
    #   3. Selective imports (use Router only ...)
    # Sort within groups
    # Preserve comments
```

**Example**:
```chapel
# Before:
use Router;
use Map;
public use Server;
use CTypes;

# After:
use CTypes;
use Map;
use Router;

public use Server;
```

**Benefits**:
- Consistent import organization
- Easier to find imports
- Follows Python/JavaScript formatter conventions

---

#### 1.2 Configuration File Support

**Status**:  Planned
**Effort**: 3-5 days
**Value**: High

**Description**:
Add `.chapelformat.toml` configuration file for customizing formatting behavior.

**Implementation**:
```toml
# .chapelformat.toml

[formatting]
indent_size = 2  # Number of spaces per indentation level
max_line_length = 100  # Maximum line length (warning only)
brace_style = "K&R"  # K&R (same line) or Allman (new line)

[whitespace]
trailing_whitespace = "remove"  # remove, warn, or ignore
final_newline = "ensure"  # ensure, remove, or ignore
tabs_to_spaces = true  # Convert tabs to spaces

[syntax]
operator_spacing = true  # Space around operators
keyword_spacing = true  # Space after keywords
comma_spacing = true  # Space after commas

[imports]
sort_imports = false  # Sort use statements
group_imports = false  # Group imports by type
```

**Benefits**:
- Project-specific formatting rules
- Team can agree on standards
- Gradual adoption (override defaults)

---

#### 1.3 Multi-Line Statement Handling

**Status**:  Planned
**Effort**: 5-7 days
**Value**: Medium

**Description**:
Improve handling of multi-line function calls, array literals, and complex expressions.

**Example**:
```chapel
# Before:
proc longFunction(veryLongParameterName: int,
anotherLongParameter: string,
yetAnotherOne: bool) {
}

# After (aligned):
proc longFunction(
  veryLongParameterName: int,
  anotherLongParameter: string,
  yetAnotherOne: bool
) {
}
```

**Implementation**:
- Detect multi-line constructs
- Apply consistent indentation
- Align parameters/arguments
- Handle trailing commas

---

### Phase 2: Advanced Features (Medium Effort)

#### 2.1 Comment Preservation and Formatting

**Status**: 💭 Concept
**Effort**: 5-7 days
**Value**: Medium

**Description**:
Improve handling of comments, including:
- Block comment alignment
- Inline comment spacing
- Doc comment formatting (if Chapel adds them)

**Example**:
```chapel
// Before:
var x = 1;     // Comment
var longer = 2;// Another

// After (aligned):
var x = 1;      // Comment
var longer = 2; // Another
```

**Implementation**:
- Track comment positions
- Align inline comments to column
- Preserve multi-line comment indentation

---

#### 2.2 LSP Integration

**Status**: 💭 Concept
**Effort**: 10-15 days
**Value**: High (if Chapel LSP becomes available)

**Description**:
Integrate with `chpl-language-server` for:
- Real-time formatting in IDEs
- Semantic-aware formatting
- Type-based alignment

**Requirements**:
- Chapel LSP server availability
- LSP formatting protocol support
- Python LSP client library

**Benefits**:
- IDE integration (VS Code, Vim, Emacs)
- Real-time feedback
- Semantic formatting (type-aware)

---

#### 2.3 chplcheck Integration

**Status**: 💭 Concept
**Effort**: 3-5 days
**Value**: Medium (if chplcheck improves)

**Description**:
Integrate with Chapel's official linter when it supports more checks.

**Current State**:
- chplcheck has limited checks
- Requires `@fixit` decorator annotations
- Not suitable for general formatting

**Future Integration**:
```python
class ChplcheckValidator(Validator):
    """Chapel linter using official chplcheck."""

    @property
    def name(self) -> str:
        return "chplcheck"

    def validate(self, filepath: Path) -> ValidationResult:
        # Run chplcheck on file
        # Parse output
        # Report issues
```

**Benefits**:
- Official Chapel linting
- More comprehensive checks
- Better error messages

---

### Phase 3: Enterprise Features (High Effort)

#### 3.1 AST-Based Formatting

**Status**: 🔮 Future
**Effort**: 20-30 days
**Value**: Very High

**Description**:
Implement full AST-based formatting using Chapel compiler's parser.

**Requirements**:
- Chapel compiler Python bindings
- AST traversal and reconstruction
- Semantic analysis support

**Benefits**:
- Perfect indentation
- Complex expression formatting
- Semantic-aware transformations
- Handles all Chapel syntax

**Challenges**:
- Chapel compiler dependency (500MB-1.5GB)
- Build complexity
- Performance overhead
- Maintenance burden

---

#### 3.2 Performance Optimization

**Status**:  Planned
**Effort**: 5-10 days
**Value**: Low (current performance is good)

**Description**:
Optimize formatter for large files and batch operations.

**Techniques**:
- Parallel file processing
- Incremental formatting (only changed regions)
- Compiled regex patterns (already done)
- Caching formatted results

**Target**:
- Current: ~50ms per file
- Optimized: < 10ms per file
- Batch: 100+ files per second

---

#### 3.3 Format-on-Save Integration

**Status**: 💭 Concept
**Effort**: 3-5 days per IDE
**Value**: High (for Chapel developers)

**Description**:
Integrate formatter into popular IDEs:
- VS Code extension
- Vim/Neovim plugin
- Emacs mode
- Sublime Text plugin

**Implementation**:
```javascript
// VS Code extension
{
  "name": "chapel-format",
  "displayName": "Chapel Formatter",
  "description": "Format Chapel code using HuskyCat",
  "version": "1.0.0",
  "publisher": "huskycat",
  "engines": {
    "vscode": "^1.75.0"
  },
  "activationEvents": [
    "onLanguage:chapel"
  ],
  "main": "./out/extension.js",
  "contributes": {
    "languages": [
      {
        "id": "chapel",
        "extensions": [".chpl"]
      }
    ]
  }
}
```

---

## Priority Roadmap

### Q1 2026 (High Priority)

1. **Configuration File Support** - Enable customization
2. **Import Sorting** - Basic import organization
3. **Multi-Line Handling** - Improve complex expressions

### Q2 2026 (Medium Priority)

4. **Comment Formatting** - Better comment preservation
5. **chplcheck Integration** - If official linter improves
6. **Performance Optimization** - Optimize for large codebases

### Q3 2026 (Future Consideration)

7. **LSP Integration** - If Chapel LSP server becomes available
8. **AST-Based Formatting** - If Chapel provides Python bindings
9. **IDE Extensions** - VS Code, Vim, Emacs plugins

---

## Rejected / Deferred Ideas

### Automatic Code Refactoring

**Reason**: Out of scope for formatter
**Description**: Renaming variables, extracting functions, etc.
**Status**:  Rejected

**Why**:
- Formatter should only format, not refactor
- Requires semantic analysis
- Too complex for lightweight tool

---

### Chapel-Specific Style Checks

**Reason**: Use chplcheck instead
**Description**: Chapel idiom enforcement (e.g., prefer `forall` over `for`)
**Status**:  Rejected

**Why**:
- Belongs in linter, not formatter
- chplcheck should handle this
- Opinionated beyond formatting

---

### Automatic Import Addition

**Reason**: IDE feature, not formatter
**Description**: Auto-import missing symbols
**Status**:  Rejected

**Why**:
- Requires semantic analysis
- IDE responsibility
- Beyond formatter scope

---

## Community Feedback

### Requested Features

*(To be filled in as users provide feedback)*

1. **TBD**: User feature requests will be documented here
2. **TBD**: Prioritized based on demand
3. **TBD**: Evaluated for feasibility

### Known Issues

*(To be filled in as issues are reported)*

1. **TBD**: Known bugs and limitations
2. **TBD**: Workarounds if available
3. **TBD**: Fix timeline

---

## Implementation Notes

### Technical Debt

1. **Result serialization**: Fix "unknown" tool name in validation results
2. **CLI argument parsing**: Improve --check flag position handling
3. **Error messages**: More specific feedback on formatting changes
4. **Test coverage**: Add more edge case tests

### Code Quality

1. **Type hints**: Add comprehensive type annotations
2. **Documentation**: Add inline documentation for complex regex patterns
3. **Performance**: Profile regex patterns for bottlenecks
4. **Maintainability**: Extract pattern library to separate module

---

## Success Metrics

### Phase 1 Goals (Q1 2026)

| Metric | Current | Target |
|--------|---------|--------|
| Configuration support |  None |  .chapelformat.toml |
| Import sorting |  No |  Yes |
| Multi-line handling | 🟡 Basic |  Good |
| User satisfaction | TBD | 85% |

### Phase 2 Goals (Q2 2026)

| Metric | Current | Target |
|--------|---------|--------|
| Comment formatting | 🟡 Basic |  Good |
| LSP integration |  No |  Yes (if available) |
| Performance | ~50ms | < 10ms |
| Test coverage | 55 tests | 100+ tests |

### Phase 3 Goals (Q3 2026)

| Metric | Current | Target |
|--------|---------|--------|
| AST-based formatting |  No |  Yes (if feasible) |
| IDE extensions |  None |  VS Code + Vim |
| Chapel community adoption | 0% | 20% |

---

## Contributing

If you're interested in implementing any of these features:

1. **Open an issue** on GitHub to discuss the enhancement
2. **Review the design document** (`docs/proposals/chapel-formatter-design.md`)
3. **Check existing code** (`src/huskycat/formatters/chapel.py`)
4. **Write tests first** (TDD approach recommended)
5. **Submit PR** with comprehensive tests and documentation

---

## Conclusion

The Chapel formatter has a solid foundation with v1.0.0, providing:
-  Whitespace cleanup
-  Basic syntax formatting
-  2-space indentation
-  Zero dependencies

Future enhancements will focus on:
1. **Configuration** - Customizable formatting rules
2. **Import sorting** - Organized use statements
3. **Multi-line handling** - Better complex expressions
4. **LSP integration** - IDE support (when available)
5. **AST-based formatting** - Perfect formatting (if feasible)

**Next steps**:
1. Gather user feedback
2. Prioritize based on demand
3. Implement Phase 1 features (Q1 2026)

---

**Document Version**: 1.0.0
**Last Updated**: December 5, 2025
**Status**: Living document (will be updated based on feedback)
