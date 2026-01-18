# HuskyCat Linters

Clean-room implementations of code quality linters with permissive licensing.

## YAML Linter

### License Compliance

This YAML linter is a **clean-room implementation** that does NOT use any GPL code:

- **License**: Apache 2.0 (SPDX: Apache-2.0)
- **Based on**: YAML 1.2 specification (public domain specification)
- **Dependencies**: PyYAML (MIT license) for parsing only
- **Original implementation**: All validation rules written from scratch

### Features

The YAML linter implements 5 core validation rules:

1. **Trailing Whitespace Detection**
   - Detects trailing spaces/tabs at end of lines
   - Configurable: `allow_trailing_whitespace: bool`

2. **Line Length Enforcement**
   - Enforces maximum line length (default: 120 characters)
   - Configurable: `max_line_length: int`

3. **Indentation Consistency**
   - Enforces YAML 1.2 spec requirement for space-only indentation
   - Detects tabs in indentation (error)
   - Detects mixed tabs/spaces (warning)
   - Configurable: `allow_tabs: bool`

4. **Duplicate Key Detection**
   - Detects duplicate keys within YAML mappings
   - Per YAML 1.2 spec section 3.2.1.2
   - Configurable: `allow_duplicate_keys: bool`

5. **Empty Value Validation**
   - Detects empty values in key-value pairs
   - Often indicates unintended configuration
   - Configurable: `allow_empty_values: bool`

### Usage

#### Standalone Usage

```python
from pathlib import Path
from huskycat.linters.yaml_lint import lint_yaml, lint_yaml_file

# Lint YAML content
content = "key: value\n"
issues = lint_yaml(content)

# Lint YAML file
filepath = Path("config.yaml")
issues = lint_yaml_file(filepath)

# Print issues
for issue in issues:
    print(issue)  # "10:5: [warning] trailing-whitespace: Trailing whitespace found"
```

#### With Configuration

```python
from huskycat.linters.yaml_lint import lint_yaml

config = {
    "max_line_length": 100,
    "allow_tabs": False,
    "allow_trailing_whitespace": False,
    "allow_empty_values": True,
    "allow_duplicate_keys": False,
    "disabled_rules": ["line-length"],  # Disable specific rules
}

issues = lint_yaml(content, config=config)
```

#### Integration with HuskyCat Validator

```python
from pathlib import Path
from huskycat.linters.yaml_lint_validator import YamlLintValidator

validator = YamlLintValidator()

# Check availability
if validator.is_available():
    result = validator.validate(Path("config.yaml"))

    print(f"Success: {result.success}")
    print(f"Errors: {len(result.errors)}")
    print(f"Warnings: {len(result.warnings)}")
```

#### Command-Line Usage

```bash
# Validate a YAML file
python -m huskycat.linters.yaml_lint_validator config.yaml

# Exit code: 0 if valid, 1 if errors found
```

### Configuration Reference

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `max_line_length` | int | 120 | Maximum line length |
| `allow_tabs` | bool | False | Allow tabs in indentation |
| `allow_trailing_whitespace` | bool | False | Allow trailing whitespace |
| `allow_empty_values` | bool | True | Allow empty values in key-value pairs |
| `allow_duplicate_keys` | bool | False | Allow duplicate keys in mappings |
| `disabled_rules` | set[str] | {} | Rules to disable |

#### Available Rules

- `trailing-whitespace` - Trailing whitespace detection
- `line-length` - Line length enforcement
- `indentation` - Indentation consistency
- `duplicate-keys` - Duplicate key detection
- `empty-values` - Empty value validation

### Implementation Details

#### Architecture

```
yaml_lint.py
├── YamlIssue - Issue representation
├── YamlLintConfig - Configuration
├── YamlLinter - Core linter class
├── lint_yaml() - Convenience function
└── lint_yaml_file() - File wrapper

yaml_lint_validator.py
└── YamlLintValidator - HuskyCat integration
    ├── extends Validator base class
    ├── implements validate() method
    └── returns ValidationResult
```

#### Rule Implementation

All rules are implemented from scratch based on:

1. **YAML 1.2 Specification** (yaml.org/spec/1.2/)
   - Section 6.2: Indentation Spaces (tabs not allowed)
   - Section 3.2.1.2: Mapping keys must be unique

2. **Common Best Practices**
   - Line length limits for readability
   - Trailing whitespace detection
   - Empty value warnings

3. **PyYAML Parser** (MIT license)
   - Used only for parsing, not validation logic
   - Custom loader for duplicate key detection

### Testing

Comprehensive test suite with 24 test cases:

```bash
# Run tests
python -m pytest tests/test_yaml_lint.py -v

# Test coverage
python -m pytest tests/test_yaml_lint.py --cov=huskycat.linters.yaml_lint
```

Test coverage includes:
- Basic rule detection
- Configuration options
- Edge cases (comments, nested structures, parse errors)
- Integration with validator framework

### Comparison with yamllint

| Feature | HuskyCat yaml-lint | yamllint |
|---------|-------------------|----------|
| License | Apache 2.0 | GPL 3.0 |
| Dependencies | PyYAML (MIT) | PyYAML (MIT) |
| Implementation | Clean-room | GPL |
| Rules | 5 core rules | 40+ rules |
| Performance | Fast (Python-native) | Fast |
| Extensibility | Easy to extend | Plugin system |

**Why this implementation?**

HuskyCat requires permissive licensing (Apache 2.0) for:
- Commercial use without restrictions
- Integration into proprietary systems
- Redistribution in binary form

GPL yamllint would require all HuskyCat code to be GPL-licensed.

### Adding New Rules

To add a new validation rule:

1. Add rule method to `YamlLinter` class:

```python
def _check_my_rule(self, lines: List[str]) -> None:
    """Check for my custom rule."""
    if "my-rule" in self.config.disabled_rules:
        return

    for line_num, line in enumerate(lines, start=1):
        if condition:
            self.issues.append(
                YamlIssue(
                    line=line_num,
                    column=column,
                    rule="my-rule",
                    message="Issue description",
                    severity="warning",
                )
            )
```

2. Call method in `lint()`:

```python
def lint(self, content: str) -> List[YamlIssue]:
    # ... existing checks ...
    self._check_my_rule(lines)
    return sorted(self.issues, key=lambda i: (i.line, i.column))
```

3. Add configuration option to `YamlLintConfig`:

```python
@dataclass
class YamlLintConfig:
    # ... existing options ...
    my_rule_option: bool = True
```

4. Add tests in `tests/test_yaml_lint.py`

### Future Enhancements

Potential rules to add (priority order):

1. **Key ordering** - Detect unsorted keys in mappings
2. **Anchor/alias validation** - Check for undefined references
3. **Value type consistency** - Detect mixed types in arrays
4. **Bracket/brace spacing** - Flow style formatting
5. **Comment formatting** - Comment style consistency

### License

```
SPDX-License-Identifier: Apache-2.0

Copyright 2025 HuskyCat Project

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
