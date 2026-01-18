# Comprehensive Auto-Format and Linting Review

**Date**: December 5, 2025
**Status**: 🔍 RESEARCH COMPLETE
**Version**: 1.0.0

---

## Executive Summary

This document provides a comprehensive review of HuskyCat's auto-formatting and auto-fixing capabilities across all supported and requested languages. The review identifies significant gaps in language support and incomplete implementation of existing formatters.

### Key Findings

 **Working**: Black (Python), Autoflake (Python), YAMLLint (limited)
 **Partially Implemented**: ESLint, Prettier, Ruff
 **Missing**: IsSort, TOML formatters, Terraform, Chapel language
 **Critical Gap**: Whitespace cleanup not universally implemented

---

## Language Support Matrix

| Language | Validation | Auto-Fix | Whitespace Cleanup | Status |
|----------|------------|----------|-------------------|--------|
| **Python** |  Full | 🟡 Partial | 🟡 Partial | Needs Ruff fix, IsSort |
| **JavaScript/TypeScript** |  Full | 🟡 Partial |  Missing | Prettier not enabled |
| **YAML** |  Full | 🟡 Limited |  Complete | Only whitespace fixes |
| **TOML** |  None |  None |  None | **MISSING** |
| **Terraform** |  None |  None |  None | **MISSING** |
| **Chapel** |  None |  None |  None | **MISSING** |
| **Shell Scripts** |  Full |  None |  None | Report-only |
| **Docker** |  Full |  None |  None | Report-only |

---

## Current Implementation Analysis

### 1. Python Auto-Formatting

####  Working Tools

**Black** (`src/huskycat/core/validators/python.py:87-149`)
- **Confidence**: SAFE
- **Auto-fix mechanism**: Removes `--check` flag, applies formatting directly
- **Whitespace**: Comprehensive (trailing, indentation, line length)
- **Extensions**: `.py`, `.pyi`
- **Status**:  Complete

**Autoflake** (`src/huskycat/core/validators/python.py:152-231`)
- **Confidence**: LIKELY
- **Auto-fix mechanism**: Two-phase (check, then `--in-place`)
- **Fixes**: Unused imports, unused variables
- **Extensions**: `.py`, `.pyi`
- **Status**:  Complete

####  Incomplete Tools

**Ruff** (`src/huskycat/core/validators/python.py:450-510`)
- **Confidence**: LIKELY (configured in `base.py:48`)
- **Current implementation**: JSON output with `ruff check` only
- **Missing**: Does NOT use `ruff check --fix` even when `auto_fix=True`
- **Impact**: HIGH - Ruff can fix 100+ rule violations automatically
- **Configuration**: `pyproject.toml:227` shows `fixable = ["ALL"]`
- **Status**:  Incomplete - Fix capability exists but not used

####  Missing Tools

**IsSort** (Import sorting)
- **Configuration exists**: `pyproject.toml:123-130`
- **Validator**: Does NOT exist in codebase
- **Confidence**: SAFE (formatting-only)
- **Impact**: MEDIUM - Import organization improves readability
- **Status**:  Missing validator implementation

### 2. JavaScript/TypeScript Auto-Formatting

#### 🟡 Partially Working

**ESLint** (`src/huskycat/core/validators/javascript.py:600-662`)
- **Confidence**: LIKELY
- **Auto-fix mechanism**: Inserts `--fix` flag (line 605)
- **Extensions**: `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, `.cjs`
- **Status**: 🟡 Partial - Fix enabled but status tracking unclear
- **Whitespace**: Depends on ESLint rules configured

**Prettier** (`src/huskycat/core/validators/javascript.py:664-719`)
- **Confidence**: SAFE (configured in `base.py:49`)
- **Current implementation**: Uses `--check` flag only
- **Missing**: No `--write` mode for auto-fix
- **Extensions**: `.js`, `.jsx`, `.ts`, `.tsx`, `.json`, `.css`, `.scss`, `.html`, `.md`
- **Impact**: HIGH - Prettier is the standard formatter for JS/TS
- **Whitespace**: Comprehensive (when enabled)
- **Status**:  Incomplete - Check-only, no fix

### 3. YAML Auto-Formatting

**YAMLLint** (`src/huskycat/core/validators/yaml.py:736-770`)
- **Confidence**: SAFE
- **Auto-fix mechanism**: Custom `_auto_fix_yaml()` method
- **Fixes implemented**:
  - Trailing whitespace removal: 
  - Ensures file ends with newline: 
  - Indentation:  Not implemented
  - Line length:  Not implemented
- **Extensions**: `.yaml`, `.yml`
- **Status**: 🟡 Partial - Only whitespace, not full formatting

### 4. TOML Formatting

**Status**:  Completely missing

**No validator exists for:**
- `.toml` file validation
- `pyproject.toml` formatting
- `Cargo.toml` formatting

**Recommended tools**:
1. **taplo** - Rust-based TOML formatter
   - Fast, comprehensive
   - Supports auto-fix
   - Confidence: SAFE (formatting-only)
2. **Prettier TOML plugin**
   - Integrates with existing Prettier
   - Node.js based

**Current situation**:
- Container: taplo NOT installed
- Prettier TOML plugin: NOT installed
- No configuration in `pyproject.toml` or `.huskycat.yaml`

### 5. Terraform Formatting

**Status**:  Completely missing

**No validator exists for:**
- `.tf` file validation
- `terraform fmt` integration
- `terraform validate` checks

**Recommended tools**:
1. **terraform fmt** - Official formatter
   - Safe, deterministic
   - Confidence: SAFE
2. **tflint** - Terraform linter
   - Additional validation beyond fmt
   - Can detect errors terraform fmt won't catch

**Current situation**:
- Container: terraform NOT installed
- No `.tf` file handling

### 6. Chapel Language Formatting

**Status**:  Completely missing

**No validator exists for:**
- `.chpl` file validation
- Chapel compiler integration
- Chapel formatting

**Chapel language details**:
- Version requested: Chapel 2.6+
- Official formatter: `chplfmt` (if available)
- Chapel compiler: `chpl`

**Research needed**:
1. Does Chapel 2.6+ have an official formatter?
2. What linting tools exist for Chapel?
3. Is Chapel available in Alpine Linux packages?

**Current situation**:
- Container: Chapel NOT installed
- No `.chpl` file handling
- No Chapel documentation

---

## Fix Confidence Framework

### Current Tiers (`src/huskycat/core/adapters/base.py:27-51`)

```python
class FixConfidence(Enum):
    SAFE = "safe"           # Formatting-only, always apply
    LIKELY = "likely"       # Style fixes, usually safe
    UNCERTAIN = "uncertain" # Semantic changes, needs review
```

### Tool Confidence Mapping

```python
TOOL_FIX_CONFIDENCE = {
    "python-black": FixConfidence.SAFE,      #  Implemented
    "js-prettier": FixConfidence.SAFE,       #  Not used for fixing
    "autoflake": FixConfidence.LIKELY,       #  Implemented
    "ruff": FixConfidence.LIKELY,            #  Not used for fixing
    "yamllint": FixConfidence.SAFE,          # 🟡 Limited fixes
    "js-eslint": FixConfidence.LIKELY,       # 🟡 Status unclear
}
```

### Proposed Additions

```python
TOOL_FIX_CONFIDENCE = {
    # ... existing ...
    "isort": FixConfidence.SAFE,        # Import sorting
    "taplo": FixConfidence.SAFE,        # TOML formatting
    "terraform-fmt": FixConfidence.SAFE, # Terraform formatting
    "chplfmt": FixConfidence.SAFE,      # Chapel formatting (if exists)
}
```

---

## Whitespace Cleanup Analysis

### User Requirement
> "automatically remove whitespace, clear up / fail fast on whitespace related formatting"

### Current Whitespace Handling

####  Complete Whitespace Cleanup

1. **Black (Python)**:
   - Trailing whitespace:  Removed
   - Line endings:  Normalized to LF
   - Final newline:  Ensured
   - Indentation:  Spaces (configurable)

2. **YAMLLint**:
   - Trailing whitespace:  Removed (line 759)
   - Final newline:  Ensured (line 761)
   - Indentation:  Only validates, doesn't fix

####  No Whitespace Cleanup

1. **Prettier**: Not enabled for auto-fix (would handle all JS/TS/JSON/Markdown)
2. **TOML**: No formatter at all
3. **Terraform**: No formatter at all
4. **Chapel**: No formatter at all

### Whitespace Issues by File Type

| File Type | Trailing Whitespace | Final Newline | Indentation | Line Endings |
|-----------|---------------------|---------------|-------------|--------------|
| `.py` |  Black |  Black |  Black |  Black |
| `.js/.ts` |  None |  None |  None |  None |
| `.yaml` |  YAMLLint |  YAMLLint |  None |  None |
| `.toml` |  None |  None |  None |  None |
| `.tf` |  None |  None |  None |  None |
| `.chpl` |  None |  None |  None |  None |
| `.md` |  None |  None |  None |  None |
| `.json` |  None |  None |  None |  None |

---

## Git Hook Integration

### Current Pre-Commit Hook (`scripts/pre-commit-hook.sh`)

```bash
# Current implementation validates but doesn't auto-fix by default
huskycat validate --staged
```

### Desired Workflow

```bash
# Auto-fix SAFE changes, prompt for LIKELY changes
huskycat validate --staged --fix --interactive
```

### CI/CD Auto-Fix Workflow

**Publishing bot / agent CI job requirements**:
1. Auto-fix all SAFE changes without prompting
2. Report LIKELY/UNCERTAIN changes without applying
3. Exit with error if unfixable issues remain

```bash
# CI mode: fix SAFE only, report others
huskycat validate --fix --safe-only --mode ci
```

---

## Container Toolchain Gaps

### Current Container Tools (`ContainerFile`)

**Installed Python tools**:
- black 
- flake8 
- autoflake 
- mypy 
- pylint 
- bandit 
- ruff 
- yamllint 

**Installed JavaScript tools**:
- eslint 
- prettier 
- typescript 

**Installed shell/docker tools**:
- shellcheck 
- hadolint 

### Missing Tools for Full Support

**Required additions**:
1. **isort** - Python import sorting
   ```dockerfile
   RUN pip3 install --no-cache-dir --break-system-packages isort
   ```

2. **taplo** - TOML formatting
   ```dockerfile
   RUN curl -fsSL https://github.com/tamasfe/taplo/releases/latest/download/taplo-linux-x86_64.gz | \
       gunzip > /usr/local/bin/taplo && chmod +x /usr/local/bin/taplo
   ```

3. **terraform** - Terraform validation and formatting
   ```dockerfile
   RUN apk add --no-cache terraform
   ```

4. **Chapel compiler** - Chapel language support
   ```dockerfile
   # Research: Chapel installation for Alpine Linux
   # May require building from source or using different base image
   ```

---

## Gap Analysis Summary

### Critical Gaps (Blocking auto-format workflow)

1. **Prettier auto-fix not enabled**
   - Impact: HIGH
   - Effort: LOW
   - Priority: 🔴 Critical
   - Blocks: JavaScript, TypeScript, JSON, Markdown whitespace cleanup

2. **Ruff auto-fix not enabled**
   - Impact: HIGH
   - Effort: LOW
   - Priority: 🔴 Critical
   - Blocks: 100+ Python style fixes

3. **IsSort not implemented**
   - Impact: MEDIUM
   - Effort: MEDIUM
   - Priority: 🟡 High
   - Blocks: Python import organization

### Missing Language Support

4. **TOML formatting**
   - Impact: MEDIUM
   - Effort: MEDIUM
   - Priority: 🟡 High
   - Required for: pyproject.toml, Cargo.toml, config files

5. **Terraform formatting**
   - Impact: MEDIUM
   - Effort: MEDIUM
   - Priority: 🟡 High
   - Required for: .tf infrastructure files

6. **Chapel language support**
   - Impact: LOW (niche language)
   - Effort: HIGH (research needed)
   - Priority: 🟢 Future
   - Required for: .chpl files

### Incomplete Features

7. **YAML full formatting**
   - Current: Only whitespace fixes
   - Missing: Indentation, line length, key ordering
   - Priority: 🟢 Nice-to-have

8. **Dry-run preview mode**
   - Current: Flag exists but no diff output
   - Missing: Show what would be changed
   - Priority: 🟢 Nice-to-have

---

## Proposed Implementation Plan

### Phase 1: Fix Existing Tools (Sprint 8A)

**Goal**: Enable auto-fix for already-installed tools

**Tasks**:
1. **Enable Ruff auto-fix** (`src/huskycat/core/validators/python.py`)
   - Add `ruff check --fix` support
   - Handle `--fix` flag in validator
   - Update `fixable_tools` list

2. **Enable Prettier auto-fix** (`src/huskycat/core/validators/javascript.py`)
   - Replace `--check` with `--write` when `auto_fix=True`
   - Update confidence mapping
   - Add to `fixable_tools` list

3. **Verify ESLint auto-fix** (`src/huskycat/core/validators/javascript.py`)
   - Test fix status tracking
   - Ensure `fixed` property correctly set

**Acceptance Criteria**:
- `huskycat validate --fix` applies Ruff fixes to Python
- `huskycat validate --fix` applies Prettier fixes to JS/TS/JSON
- All existing tests pass
- Container toolchain unchanged (already installed)

**Files Changed**:
- `src/huskycat/core/validators/python.py` (Ruff validator)
- `src/huskycat/core/validators/javascript.py` (Prettier validator)
- `src/huskycat/unified_validation.py` (fixable_tools list)

**Testing**:
```bash
# Create test files with fixable issues
echo "x=1" > test.py  # Missing spaces around =
echo "const x  =  1" > test.js  # Extra spaces

# Run auto-fix
huskycat validate --fix test.py test.js

# Verify fixes applied
cat test.py  # Should show "x = 1"
cat test.js  # Should show "const x = 1;"
```

---

### Phase 2: Add Python Import Sorting (Sprint 8B)

**Goal**: Implement IsSort validator for Python import organization

**Tasks**:
1. **Add IsSort to container** (`ContainerFile`)
   ```dockerfile
   RUN pip3 install --no-cache-dir --break-system-packages isort
   ```

2. **Create IsortValidator** (`src/huskycat/core/validators/python.py`)
   - Implement check phase: `isort --check-only --diff`
   - Implement fix phase: `isort`
   - Confidence: SAFE
   - Extensions: `.py`, `.pyi`

3. **Update configuration**
   - Add to `.huskycat.yaml` Python tools
   - IsSort already configured in `pyproject.toml:123-130`

4. **Update documentation**
   - Add to CLI reference
   - Add to MCP tools

**Acceptance Criteria**:
- `huskycat validate` detects import order issues
- `huskycat validate --fix` sorts imports correctly
- IsSort respects `pyproject.toml` configuration
- Container includes isort binary

**Files Changed**:
- `ContainerFile` (add isort)
- `src/huskycat/core/validators/python.py` (new IsortValidator class)
- `.huskycat.yaml` (add isort to Python tools)
- `docs/cli-reference.md` (document isort)

**Testing**:
```python
# test_imports.py - unsorted imports
import sys
import os
from pathlib import Path
import json

# After isort --fix:
import json
import os
import sys
from pathlib import Path
```

---

### Phase 3: Add TOML Formatting (Sprint 8C)

**Goal**: Add TOML validation and formatting support

**Tasks**:
1. **Add taplo to container** (`ContainerFile`)
   ```dockerfile
   # Install taplo (TOML formatter)
   RUN curl -fsSL https://github.com/tamasfe/taplo/releases/latest/download/taplo-linux-x86_64.gz | \
       gunzip > /usr/local/bin/taplo && \
       chmod +x /usr/local/bin/taplo
   ```

2. **Create TaploValidator** (`src/huskycat/core/validators/toml.py` - NEW FILE)
   - Implement check: `taplo format --check`
   - Implement fix: `taplo format`
   - Confidence: SAFE
   - Extensions: `.toml`

3. **Update configuration**
   - Add TOML section to `.huskycat.yaml`
   - Configure taplo options if needed

4. **Update documentation**
   - Add TOML to supported languages
   - Document taplo options

**Acceptance Criteria**:
- `huskycat validate pyproject.toml` detects formatting issues
- `huskycat validate --fix pyproject.toml` formats correctly
- Whitespace cleanup: trailing spaces, final newline
- Container includes taplo binary

**Files Created**:
- `src/huskycat/core/validators/toml.py` (new)

**Files Changed**:
- `ContainerFile` (add taplo)
- `src/huskycat/core/validators/__init__.py` (export TaploValidator)
- `.huskycat.yaml` (add TOML section)
- `docs/cli-reference.md` (add TOML)

**Testing**:
```toml
# test.toml - bad formatting
[package]
name="mypackage"  # Missing space
version   =   "1.0.0"  # Extra spaces

# After taplo format:
[package]
name = "mypackage"
version = "1.0.0"
```

---

### Phase 4: Add Terraform Support (Sprint 8D)

**Goal**: Add Terraform validation and formatting

**Tasks**:
1. **Add terraform to container** (`ContainerFile`)
   ```dockerfile
   # Install Terraform
   RUN apk add --no-cache terraform
   ```

2. **Create TerraformValidator** (`src/huskycat/core/validators/terraform.py` - NEW FILE)
   - Implement check: `terraform fmt -check -diff`
   - Implement fix: `terraform fmt`
   - Optional: `terraform validate` for syntax
   - Confidence: SAFE (fmt), LIKELY (validate)
   - Extensions: `.tf`, `.tfvars`

3. **Update configuration**
   - Add Terraform section to `.huskycat.yaml`

4. **Update documentation**
   - Add Terraform to supported languages

**Acceptance Criteria**:
- `huskycat validate *.tf` detects formatting issues
- `huskycat validate --fix *.tf` applies terraform fmt
- Container includes terraform binary

**Files Created**:
- `src/huskycat/core/validators/terraform.py` (new)

**Files Changed**:
- `ContainerFile` (add terraform)
- `src/huskycat/core/validators/__init__.py` (export TerraformValidator)
- `.huskycat.yaml` (add Terraform section)
- `docs/cli-reference.md` (add Terraform)

**Testing**:
```hcl
# test.tf - bad formatting
resource "aws_instance" "example" {
ami="ami-12345"  # Missing space
instance_type    =    "t2.micro"  # Extra spaces
}

# After terraform fmt:
resource "aws_instance" "example" {
  ami           = "ami-12345"
  instance_type = "t2.micro"
}
```

---

### Phase 5: Chapel Language Support (Sprint 9 - Future)

**Goal**: Research and implement Chapel language support

**Status**: 🔬 Research required

**Research Questions**:
1. Does Chapel 2.6+ include an official formatter?
2. What linting tools exist for Chapel?
3. How to install Chapel in Alpine Linux container?
4. Chapel compiler size/performance impact?

**Preliminary Tasks**:
1. **Research Chapel tooling**
   - Check Chapel 2.6+ documentation
   - Identify `chplfmt` or equivalent
   - Chapel Language Server Protocol (LSP) support?

2. **Evaluate installation options**
   - Option A: Alpine package (if exists)
   - Option B: Build from source
   - Option C: Different base image (Ubuntu has Chapel packages)

3. **Prototype Chapel validator**
   - If formatter exists, create ChapelValidator
   - Extensions: `.chpl`
   - Confidence: TBD based on formatter behavior

**Acceptance Criteria** (if implemented):
- Container includes Chapel compiler/formatter
- `huskycat validate *.chpl` validates Chapel files
- `huskycat validate --fix *.chpl` formats Chapel code

**Blocking Issues**:
- Chapel tooling maturity unknown
- Container size impact (Chapel compiler may be large)
- Alpine Linux support unclear

**Recommendation**: Defer to Sprint 9 after Phase 1-4 complete

---

## Whitespace Cleanup Implementation

### Universal Whitespace Fixer

**Location**: `src/huskycat/core/validators/whitespace.py` (NEW FILE)

**Purpose**: Universal whitespace cleanup for any file type

```python
class WhitespaceFixer(AutoFixer):
    """Universal whitespace cleanup for all file types."""

    name = "whitespace"
    confidence = FixConfidence.SAFE

    def can_fix(self, file: Path) -> bool:
        """Can fix any text file."""
        # Exclude binary files
        return not self._is_binary(file)

    def fix(self, file: Path, dry_run: bool = False) -> List[FixResult]:
        """Apply whitespace fixes."""
        content = file.read_text()
        fixed = self._fix_whitespace(content)

        if content != fixed:
            if not dry_run:
                file.write_text(fixed)
            return [FixResult(
                file=file,
                original=content,
                fixed=fixed,
                confidence=FixConfidence.SAFE,
                tool="whitespace",
                description="Removed trailing whitespace and ensured final newline"
            )]
        return []

    def _fix_whitespace(self, content: str) -> str:
        """Fix whitespace issues."""
        lines = content.splitlines()

        # Remove trailing whitespace from each line
        lines = [line.rstrip() for line in lines]

        # Rejoin with newlines
        result = '\n'.join(lines)

        # Ensure final newline
        if result and not result.endswith('\n'):
            result += '\n'

        return result
```

**Integration**:
- Run as FIRST fixer before language-specific formatters
- Always SAFE confidence (whitespace-only)
- Applies to ALL file types unless formatter handles it

**Configuration**:
```yaml
# .huskycat.yaml
tools:
  whitespace:
    enabled: true
    file_patterns: ["*"]  # All files
    exclude_patterns: ["*.pyc", "*.jpg", "*.png"]  # Binary files
```

---

## CLI Flag Design

### Current Flags

```bash
huskycat validate --fix              # Auto-fix with default confidence
huskycat validate --staged --fix    # Fix staged files only
```

### Proposed Additional Flags

```bash
# Confidence control
huskycat validate --fix --safe-only        # Only SAFE fixes (black, prettier, whitespace)
huskycat validate --fix --unsafe           # Include UNCERTAIN fixes (prompts in interactive mode)

# Preview mode
huskycat validate --fix --dry-run          # Show what would be fixed
huskycat validate --fix --diff             # Show diffs of changes

# Whitespace-specific
huskycat validate --fix-whitespace         # Only fix whitespace (fast, safe)
huskycat validate --no-fix-whitespace      # Skip whitespace fixes

# CI/CD mode
huskycat validate --fix --ci-mode          # Fix SAFE only, JSON output, no prompts
```

### Git Hook Integration

**Pre-commit hook with auto-fix**:
```bash
#!/usr/bin/env sh
# .git/hooks/pre-commit (installed by huskycat setup-hooks --auto-fix)

huskycat validate --staged --fix --safe-only

# Exit code: 0 if all fixed or clean, 1 if unfixable issues
```

**Interactive pre-commit**:
```bash
#!/usr/bin/env sh
# .git/hooks/pre-commit (installed by huskycat setup-hooks --interactive)

huskycat validate --staged --fix --interactive

# Prompts user for LIKELY fixes, auto-applies SAFE fixes
```

---

## Testing Strategy

### Unit Tests Required

1. **Ruff auto-fix tests** (`tests/test_validators/test_python.py`)
   - Test Ruff detects fixable issues
   - Test `--fix` applies fixes
   - Test fixed files pass validation

2. **Prettier auto-fix tests** (`tests/test_validators/test_javascript.py`)
   - Test Prettier formatting JS/TS
   - Test JSON formatting
   - Test Markdown formatting

3. **IsSort tests** (`tests/test_validators/test_python.py`)
   - Test import ordering detection
   - Test import sorting fixes

4. **TOML formatting tests** (`tests/test_validators/test_toml.py` - NEW)
   - Test taplo formatting
   - Test pyproject.toml fixes

5. **Terraform formatting tests** (`tests/test_validators/test_terraform.py` - NEW)
   - Test terraform fmt
   - Test .tf and .tfvars files

6. **Whitespace fixer tests** (`tests/test_validators/test_whitespace.py` - NEW)
   - Test trailing whitespace removal
   - Test final newline addition
   - Test binary file exclusion

### Integration Tests

1. **End-to-end auto-fix workflow**
   ```bash
   # Create test repository with issues
   # Run huskycat validate --fix
   # Verify all SAFE issues fixed
   # Verify LIKELY issues reported
   ```

2. **Git hook integration**
   ```bash
   # Install hooks with --auto-fix
   # Create commit with fixable issues
   # Verify fixes applied before commit
   ```

3. **CI mode auto-fix**
   ```bash
   # Run in CI with --fix --ci-mode
   # Verify JSON output
   # Verify no prompts
   # Verify SAFE fixes applied
   ```

---

## Documentation Updates Required

### 1. CLI Reference (`docs/cli-reference.md`)

Add sections for:
- `--fix-whitespace` flag
- `--safe-only` flag
- `--dry-run` with diff output
- Auto-fix examples for each language

### 2. Configuration Guide (`docs/configuration.md`)

Add:
- TOML validation configuration
- Terraform validation configuration
- Whitespace fixer configuration
- Fix confidence tier explanation

### 3. Git Hooks Guide (`docs/installation.md`)

Update:
- `setup-hooks --auto-fix` option
- `setup-hooks --interactive` option
- Examples of pre-commit with auto-fix

### 4. Language Support Matrix

Create new doc: `docs/language-support.md`
- Complete matrix of languages, validators, formatters
- Auto-fix capability for each
- Whitespace handling per language

---

## Success Metrics

### Phase 1 Success Criteria

- [ ] Ruff auto-fix enabled and working
- [ ] Prettier auto-fix enabled and working
- [ ] ESLint auto-fix verified
- [ ] All existing tests pass
- [ ] New tests for auto-fix functionality

### Phase 2 Success Criteria

- [ ] IsSort validator implemented
- [ ] Python import sorting works
- [ ] Container includes isort

### Phase 3 Success Criteria

- [ ] TOML formatting works
- [ ] pyproject.toml can be formatted
- [ ] Container includes taplo

### Phase 4 Success Criteria

- [ ] Terraform formatting works
- [ ] .tf files can be formatted
- [ ] Container includes terraform

### Overall Success Metrics

| Metric | Target | Current | Gap |
|--------|--------|---------|-----|
| Languages with auto-fix | 6 | 2 | 4 |
| Formatters enabled | 8 | 3 | 5 |
| Whitespace cleanup coverage | 100% | 40% | 60% |
| CI auto-fix workflow | Working | Partial | Incomplete |
| Git hook auto-fix | Working | Manual | Incomplete |

---

## Risks and Mitigation

### Risk 1: Chapel Tooling Immaturity

**Risk**: Chapel 2.6+ may not have mature formatting tools
**Impact**: HIGH (cannot meet user requirement)
**Mitigation**: Research thoroughly before committing; consider Chapel optional

### Risk 2: Container Size Growth

**Risk**: Adding terraform, Chapel may significantly increase container size
**Impact**: MEDIUM (slower pulls, larger storage)
**Mitigation**:
- Use multi-stage builds
- Only install in "full" variant
- Offer "lite" container without Chapel

### Risk 3: Breaking Changes to Existing Workflows

**Risk**: Enabling auto-fix by default may surprise users
**Impact**: MEDIUM (unexpected commits)
**Mitigation**:
- Auto-fix requires explicit `--fix` flag
- Default behavior unchanged (validate only)
- Clear documentation and changelog

### Risk 4: Fix Confidence Misclassification

**Risk**: Tool marked SAFE actually makes semantic changes
**Impact**: HIGH (code breakage)
**Mitigation**:
- Conservative confidence assignments
- Extensive testing before SAFE classification
- User override: `--unsafe` flag for risky fixes

---

## Recommendations

### Immediate Actions (This Sprint)

1. **Enable Ruff and Prettier auto-fix** (Phase 1)
   - Highest impact, lowest effort
   - Unblocks JavaScript/TypeScript whitespace cleanup
   - Unlocks 100+ Python style fixes

2. **Add IsSort support** (Phase 2)
   - Medium effort, high value
   - Python import organization is common need

### Next Sprint

3. **Implement TOML formatting** (Phase 3)
   - Critical for `pyproject.toml` consistency
   - Growing importance with Python packaging

4. **Add Terraform support** (Phase 4)
   - Infrastructure-as-code becoming standard
   - Many projects have `.tf` files

### Future Consideration

5. **Chapel language support** (Phase 5)
   - Research-heavy, uncertain payoff
   - Defer until user demand confirmed
   - May require specialized container variant

### Optional Enhancements

6. **Universal whitespace fixer**
   - Nice-to-have for comprehensive whitespace cleanup
   - Could be separate tool called before formatters

7. **Dry-run with diff output**
   - Improves user confidence in auto-fix
   - Helps debugging formatting issues

---

## Conclusion

HuskyCat has a **solid foundation** for auto-formatting with clear confidence tiers and mode-aware behavior. However, **critical gaps exist**:

1. **Two major formatters disabled**: Ruff and Prettier auto-fix not enabled despite being installed
2. **Import sorting missing**: IsSort configured but not implemented
3. **Three languages unsupported**: TOML, Terraform, Chapel have no validators
4. **Whitespace cleanup incomplete**: Only Python and YAML (partially) handle whitespace

**Priority 1 recommendation**: Enable Ruff and Prettier auto-fix (Phase 1) - this is LOW EFFORT, HIGH IMPACT and unblocks the user's primary use case of whitespace cleanup for Python and JavaScript/TypeScript.

**Priority 2 recommendation**: Add IsSort, TOML, and Terraform support (Phases 2-4) - these are common file types in modern projects.

**Defer**: Chapel language support (Phase 5) until tooling maturity confirmed and user demand established.

With Phases 1-4 complete, HuskyCat will have **comprehensive auto-formatting** across Python, JavaScript/TypeScript, YAML, TOML, and Terraform with **universal whitespace cleanup** and **simple flag-based control** suitable for git hooks, CI/CD, and interactive use.
