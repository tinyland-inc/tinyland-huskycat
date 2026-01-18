# Auto-Format Implementation Plan - Sprint 8

**Date**: December 5, 2025
**Status**:  READY FOR IMPLEMENTATION
**Target Sprint**: Sprint 8 (Phases 8A-8D)
**Version**: 1.0.0

---

## Overview

This document provides detailed implementation steps for enabling comprehensive auto-formatting across all requested languages. The work is divided into 4 phases that can be completed sequentially in Sprint 8.

---

## Phase 1: Enable Existing Formatters (Sprint 8A)

**Duration**: 2-3 days
**Complexity**: LOW
**Impact**: HIGH
**Priority**: 🔴 CRITICAL

### Goals

Enable auto-fix for Ruff and Prettier - both already installed in container but not used for fixing.

### Tasks

#### Task 1.1: Enable Ruff Auto-Fix

**File**: `src/huskycat/core/validators/python.py` (lines 450-510)

**Current Code**:
```python
class RuffValidator(BaseValidator):
    def check_file(self, file: Path) -> ValidationResult:
        # Only uses: ruff check --output-format=json
        # Does NOT use: ruff check --fix
```

**Changes Required**:

1. Add fix logic to RuffValidator:

```python
class RuffValidator(BaseValidator):
    # ... existing code ...

    def fix_file(self, file: Path) -> FixResult:
        """Apply Ruff auto-fixes to a file."""
        if not self.auto_fix:
            return FixResult(fixed=False, message="Auto-fix not enabled")

        # Run ruff check with --fix flag
        cmd = [
            "ruff",
            "check",
            "--fix",
            "--output-format=json",
            str(file)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.project_root
        )

        if result.returncode == 0:
            return FixResult(
                fixed=True,
                message=f"Applied Ruff fixes to {file.name}",
                tool="ruff"
            )
        else:
            # Parse JSON to see what couldn't be fixed
            try:
                data = json.loads(result.stdout)
                return FixResult(
                    fixed=False,
                    message=f"Some issues couldn't be auto-fixed: {len(data)} remaining",
                    unfixable_count=len(data)
                )
            except json.JSONDecodeError:
                return FixResult(fixed=False, message="Ruff fix failed")

    def check_file(self, file: Path) -> ValidationResult:
        # Existing check logic...

        # If auto_fix enabled, attempt fix first
        if self.auto_fix:
            fix_result = self.fix_file(file)
            if fix_result.fixed:
                # Re-check after fixing
                return self.check_file(file)

        # ... rest of existing check logic
```

2. Update `unified_validation.py` fixable_tools list (line 1271):

```python
# Before:
fixable_tools = {"black", "autoflake", "yamllint", "eslint"}

# After:
fixable_tools = {"black", "autoflake", "ruff", "yamllint", "eslint", "prettier"}
```

**Testing**:

```bash
# Create test file with fixable issues
cat > test_ruff.py << 'EOF'
import sys
import os  # Unused import
x=1+2  # Missing spaces around operators
EOF

# Run with fix
huskycat validate --fix test_ruff.py

# Verify fixes applied
cat test_ruff.py
# Expected: import removed, spaces added
```

---

#### Task 1.2: Enable Prettier Auto-Fix

**File**: `src/huskycat/core/validators/javascript.py` (lines 664-719)

**Current Code**:
```python
class PrettierValidator(BaseValidator):
    def check_file(self, file: Path) -> ValidationResult:
        # Only uses: prettier --check
        # Does NOT use: prettier --write
```

**Changes Required**:

1. Add fix logic to PrettierValidator:

```python
class PrettierValidator(BaseValidator):
    # ... existing code ...

    def fix_file(self, file: Path) -> FixResult:
        """Apply Prettier formatting to a file."""
        if not self.auto_fix:
            return FixResult(fixed=False, message="Auto-fix not enabled")

        cmd = [
            "prettier",
            "--write",
            str(file)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.project_root
        )

        if result.returncode == 0:
            return FixResult(
                fixed=True,
                message=f"Formatted {file.name} with Prettier",
                tool="prettier"
            )
        else:
            return FixResult(
                fixed=False,
                message=f"Prettier formatting failed: {result.stderr}"
            )

    def check_file(self, file: Path) -> ValidationResult:
        # If auto_fix enabled, attempt fix first
        if self.auto_fix:
            fix_result = self.fix_file(file)
            if fix_result.fixed:
                # File now formatted, validation will pass
                return ValidationResult(
                    passed=True,
                    file=file,
                    tool="prettier",
                    message="Formatted successfully",
                    fixed=True
                )

        # ... rest of existing check logic (prettier --check)
```

**Testing**:

```bash
# Create test file with formatting issues
cat > test_prettier.js << 'EOF'
const   x  =  1 ;
function foo( a,b ){return a+b}
EOF

# Run with fix
huskycat validate --fix test_prettier.js

# Verify formatting
cat test_prettier.js
# Expected: proper spacing, semicolons, etc.
```

---

#### Task 1.3: Update Documentation

**Files to update**:
- `docs/cli-reference.md` - Add Ruff and Prettier to auto-fix examples
- `docs/proposals/auto-format-comprehensive-review.md` - Update status

**Changes**:

```markdown
### Auto-Fix Examples

**Python (Ruff)**:
```bash
# Fix import order, unused variables, style issues
huskycat validate --fix src/**/*.py
```

**JavaScript/TypeScript (Prettier)**:
```bash
# Format JS, TS, JSON, Markdown
huskycat validate --fix src/**/*.{js,ts,json,md}
```
```

---

### Phase 1 Acceptance Criteria

- [ ] Ruff auto-fix working: `huskycat validate --fix` applies Ruff fixes
- [ ] Prettier auto-fix working: `huskycat validate --fix` formats JS/TS
- [ ] `fixable_tools` list updated
- [ ] All existing tests pass
- [ ] New tests added for Ruff and Prettier auto-fix
- [ ] Documentation updated

### Phase 1 Deliverables

- Modified: `src/huskycat/core/validators/python.py`
- Modified: `src/huskycat/core/validators/javascript.py`
- Modified: `src/huskycat/unified_validation.py`
- Modified: `docs/cli-reference.md`
- Added: `tests/test_validators/test_ruff_autofix.py`
- Added: `tests/test_validators/test_prettier_autofix.py`

---

## Phase 2: Add IsSort Support (Sprint 8B)

**Duration**: 2-3 days
**Complexity**: MEDIUM
**Impact**: MEDIUM
**Priority**: 🟡 HIGH

### Goals

Implement IsSort validator for Python import sorting.

### Tasks

#### Task 2.1: Add IsSort to Container

**File**: `ContainerFile`

**Changes**:

```dockerfile
# Line ~33 - Add to Python tools installation
RUN pip3 install --no-cache-dir --break-system-packages \
    black \
    flake8 \
    autoflake \
    mypy \
    pylint \
    bandit \
    ruff \
    isort \      # ADD THIS LINE
    yamllint \
    # ... rest
```

**Rebuild container**:

```bash
npm run container:build
```

---

#### Task 2.2: Implement IsortValidator

**File**: `src/huskycat/core/validators/python.py` (append to file)

**Implementation**:

```python
class IsortValidator(BaseValidator):
    """IsSort validator for Python import sorting."""

    def __init__(self, project_root: Path = None, auto_fix: bool = False):
        super().__init__(project_root, auto_fix)
        self.name = "isort"
        self.tool_name = "isort"
        self.confidence = FixConfidence.SAFE  # Import sorting is safe

    def can_handle(self, file: Path) -> bool:
        """Check if file is a Python file."""
        return file.suffix in [".py", ".pyi"]

    def get_extensions(self) -> list[str]:
        """Get supported file extensions."""
        return [".py", ".pyi"]

    def check_file(self, file: Path) -> ValidationResult:
        """Check if imports are sorted correctly."""
        if not self.can_handle(file):
            return ValidationResult(
                passed=True,
                file=file,
                tool=self.name,
                message="Skipped (not a Python file)"
            )

        # If auto_fix enabled, attempt fix first
        if self.auto_fix:
            fix_result = self.fix_file(file)
            if fix_result.fixed:
                return ValidationResult(
                    passed=True,
                    file=file,
                    tool=self.name,
                    message="Imports sorted",
                    fixed=True
                )

        # Check import order
        cmd = [
            "isort",
            "--check-only",
            "--diff",
            str(file)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.project_root
        )

        if result.returncode == 0:
            # Imports already sorted
            return ValidationResult(
                passed=True,
                file=file,
                tool=self.name,
                message="Imports correctly sorted"
            )
        else:
            # Imports need sorting
            return ValidationResult(
                passed=False,
                file=file,
                tool=self.name,
                message="Imports not sorted",
                details=result.stdout,  # Show diff
                fixable=True
            )

    def fix_file(self, file: Path) -> FixResult:
        """Sort imports in file."""
        if not self.auto_fix:
            return FixResult(fixed=False, message="Auto-fix not enabled")

        cmd = [
            "isort",
            str(file)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.project_root
        )

        if result.returncode == 0:
            return FixResult(
                fixed=True,
                message=f"Sorted imports in {file.name}",
                tool="isort"
            )
        else:
            return FixResult(
                fixed=False,
                message=f"IsSort failed: {result.stderr}"
            )
```

---

#### Task 2.3: Register IsortValidator

**File**: `src/huskycat/core/validators/__init__.py`

**Changes**:

```python
from .python import (
    BlackValidator,
    Flake8Validator,
    MypyValidator,
    AutoflakeValidator,
    RuffValidator,
    IsortValidator,  # ADD THIS
)

__all__ = [
    # ... existing ...
    "IsortValidator",  # ADD THIS
]
```

**File**: `src/huskycat/unified_validation.py`

**Changes** (around line 1100):

```python
# Add IsortValidator to validator list
from src.huskycat.core.validators import (
    # ... existing ...
    IsortValidator,  # ADD THIS
)

# In ValidationEngine.__init__ or validator registration:
self.validators = [
    # ... existing validators ...
    IsortValidator(project_root=self.project_root, auto_fix=auto_fix),
]
```

---

#### Task 2.4: Update Configuration

**File**: `.huskycat.yaml`

**Changes**:

```json
{
  "tools": {
    "python": {
      "enabled": true,
      "tools": ["black", "flake8", "mypy", "ruff", "isort"],  // ADD isort
      "file_patterns": ["*.py", "*.pyi"]
    }
  }
}
```

---

#### Task 2.5: Update Documentation

**File**: `docs/cli-reference.md`

**Add section**:

```markdown
### IsSort (Python Import Sorting)

Automatically sort Python imports according to PEP 8 and configured style.

**Auto-fix**:  Enabled by default with `--fix`

**Example**:
```bash
# Sort imports in all Python files
huskycat validate --fix src/**/*.py
```

**Configuration**: Respects `pyproject.toml` [tool.isort] section.
```

---

### Phase 2 Acceptance Criteria

- [ ] IsSort installed in container
- [ ] IsortValidator implemented and registered
- [ ] Import sorting detection working
- [ ] `huskycat validate --fix` sorts imports
- [ ] Configuration via `pyproject.toml` respected
- [ ] Tests added
- [ ] Documentation updated

### Phase 2 Deliverables

- Modified: `ContainerFile`
- Modified: `src/huskycat/core/validators/python.py`
- Modified: `src/huskycat/core/validators/__init__.py`
- Modified: `src/huskycat/unified_validation.py`
- Modified: `.huskycat.yaml`
- Modified: `docs/cli-reference.md`
- Added: `tests/test_validators/test_isort.py`

---

## Phase 3: Add TOML Support (Sprint 8C)

**Duration**: 2-3 days
**Complexity**: MEDIUM
**Impact**: MEDIUM
**Priority**: 🟡 HIGH

### Goals

Add TOML file validation and formatting using taplo.

### Tasks

#### Task 3.1: Add Taplo to Container

**File**: `ContainerFile`

**Changes**:

```dockerfile
# After line 73 (after hadolint installation)

# Install taplo (TOML formatter)
RUN curl -fsSL https://github.com/tamasfe/taplo/releases/latest/download/taplo-linux-x86_64.gz | \
    gunzip > /usr/local/bin/taplo && \
    chmod +x /usr/local/bin/taplo
```

**Verify installation**:

```bash
# Build container
npm run container:build

# Test taplo
docker run --rm huskycat-validator:latest taplo --version
```

---

#### Task 3.2: Create TOML Validator

**File**: `src/huskycat/core/validators/toml.py` (NEW FILE)

**Implementation**:

```python
"""TOML validation and formatting using taplo."""

import subprocess
from pathlib import Path
from typing import List

from src.huskycat.core.adapters.base import FixConfidence
from .base import BaseValidator, ValidationResult, FixResult


class TaploValidator(BaseValidator):
    """Taplo validator for TOML files."""

    def __init__(self, project_root: Path = None, auto_fix: bool = False):
        super().__init__(project_root, auto_fix)
        self.name = "taplo"
        self.tool_name = "taplo"
        self.confidence = FixConfidence.SAFE  # Formatting only

    def can_handle(self, file: Path) -> bool:
        """Check if file is a TOML file."""
        return file.suffix == ".toml"

    def get_extensions(self) -> List[str]:
        """Get supported file extensions."""
        return [".toml"]

    def check_file(self, file: Path) -> ValidationResult:
        """Check TOML file formatting."""
        if not self.can_handle(file):
            return ValidationResult(
                passed=True,
                file=file,
                tool=self.name,
                message="Skipped (not a TOML file)"
            )

        # If auto_fix enabled, format first
        if self.auto_fix:
            fix_result = self.fix_file(file)
            if fix_result.fixed:
                return ValidationResult(
                    passed=True,
                    file=file,
                    tool=self.name,
                    message="Formatted with taplo",
                    fixed=True
                )

        # Check formatting
        cmd = [
            "taplo",
            "format",
            "--check",
            str(file)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.project_root
        )

        if result.returncode == 0:
            return ValidationResult(
                passed=True,
                file=file,
                tool=self.name,
                message="TOML formatting correct"
            )
        else:
            return ValidationResult(
                passed=False,
                file=file,
                tool=self.name,
                message="TOML formatting issues detected",
                details=result.stderr,
                fixable=True
            )

    def fix_file(self, file: Path) -> FixResult:
        """Format TOML file with taplo."""
        if not self.auto_fix:
            return FixResult(fixed=False, message="Auto-fix not enabled")

        cmd = [
            "taplo",
            "format",
            str(file)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.project_root
        )

        if result.returncode == 0:
            return FixResult(
                fixed=True,
                message=f"Formatted {file.name} with taplo",
                tool="taplo"
            )
        else:
            return FixResult(
                fixed=False,
                message=f"Taplo formatting failed: {result.stderr}"
            )
```

---

#### Task 3.3: Register TOML Validator

**File**: `src/huskycat/core/validators/__init__.py`

**Changes**:

```python
from .toml import TaploValidator  # ADD THIS

__all__ = [
    # ... existing ...
    "TaploValidator",  # ADD THIS
]
```

**File**: `src/huskycat/unified_validation.py`

**Changes**:

```python
from src.huskycat.core.validators import (
    # ... existing ...
    TaploValidator,  # ADD THIS
)

# Register validator
self.validators = [
    # ... existing validators ...
    TaploValidator(project_root=self.project_root, auto_fix=auto_fix),
]
```

---

#### Task 3.4: Update Configuration

**File**: `.huskycat.yaml`

**Changes**:

```json
{
  "tools": {
    // ... existing tools ...
    "toml": {
      "enabled": true,
      "tools": ["taplo"],
      "file_patterns": ["*.toml"]
    }
  }
}
```

---

#### Task 3.5: Update Documentation

**File**: `docs/cli-reference.md`

**Add section**:

```markdown
### Taplo (TOML Formatting)

Format TOML configuration files (pyproject.toml, Cargo.toml, etc.).

**Auto-fix**:  Enabled by default with `--fix`

**Example**:
```bash
# Format pyproject.toml
huskycat validate --fix pyproject.toml

# Format all TOML files
huskycat validate --fix **/*.toml
```

**Features**:
- Consistent indentation
- Sorted keys (optional)
- Whitespace cleanup
- Proper newlines
```

---

### Phase 3 Acceptance Criteria

- [ ] Taplo installed in container
- [ ] TaploValidator implemented and registered
- [ ] TOML formatting detection working
- [ ] `huskycat validate --fix` formats TOML files
- [ ] pyproject.toml can be formatted
- [ ] Tests added
- [ ] Documentation updated

### Phase 3 Deliverables

- Modified: `ContainerFile`
- Added: `src/huskycat/core/validators/toml.py`
- Modified: `src/huskycat/core/validators/__init__.py`
- Modified: `src/huskycat/unified_validation.py`
- Modified: `.huskycat.yaml`
- Modified: `docs/cli-reference.md`
- Added: `tests/test_validators/test_toml.py`

---

## Phase 4: Add Terraform Support (Sprint 8D)

**Duration**: 2-3 days
**Complexity**: MEDIUM
**Impact**: MEDIUM
**Priority**: 🟡 HIGH

### Goals

Add Terraform validation and formatting support.

### Tasks

#### Task 4.1: Add Terraform to Container

**File**: `ContainerFile`

**Changes**:

```dockerfile
# Line ~79 - Add to runtime dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    nodejs \
    git \
    bash \
    libstdc++ \
    libgcc \
    terraform      # ADD THIS LINE
```

**Verify installation**:

```bash
# Build container
npm run container:build

# Test terraform
docker run --rm huskycat-validator:latest terraform --version
```

---

#### Task 4.2: Create Terraform Validator

**File**: `src/huskycat/core/validators/terraform.py` (NEW FILE)

**Implementation**:

```python
"""Terraform validation and formatting."""

import subprocess
from pathlib import Path
from typing import List

from src.huskycat.core.adapters.base import FixConfidence
from .base import BaseValidator, ValidationResult, FixResult


class TerraformValidator(BaseValidator):
    """Terraform validator for .tf files."""

    def __init__(self, project_root: Path = None, auto_fix: bool = False):
        super().__init__(project_root, auto_fix)
        self.name = "terraform"
        self.tool_name = "terraform"
        self.confidence = FixConfidence.SAFE  # Formatting only

    def can_handle(self, file: Path) -> bool:
        """Check if file is a Terraform file."""
        return file.suffix in [".tf", ".tfvars"]

    def get_extensions(self) -> List[str]:
        """Get supported file extensions."""
        return [".tf", ".tfvars"]

    def check_file(self, file: Path) -> ValidationResult:
        """Check Terraform file formatting."""
        if not self.can_handle(file):
            return ValidationResult(
                passed=True,
                file=file,
                tool=self.name,
                message="Skipped (not a Terraform file)"
            )

        # If auto_fix enabled, format first
        if self.auto_fix:
            fix_result = self.fix_file(file)
            if fix_result.fixed:
                return ValidationResult(
                    passed=True,
                    file=file,
                    tool=self.name,
                    message="Formatted with terraform fmt",
                    fixed=True
                )

        # Check formatting
        cmd = [
            "terraform",
            "fmt",
            "-check",
            "-diff",
            str(file)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.project_root
        )

        if result.returncode == 0:
            return ValidationResult(
                passed=True,
                file=file,
                tool=self.name,
                message="Terraform formatting correct"
            )
        else:
            return ValidationResult(
                passed=False,
                file=file,
                tool=self.name,
                message="Terraform formatting issues detected",
                details=result.stdout,  # Show diff
                fixable=True
            )

    def fix_file(self, file: Path) -> FixResult:
        """Format Terraform file."""
        if not self.auto_fix:
            return FixResult(fixed=False, message="Auto-fix not enabled")

        cmd = [
            "terraform",
            "fmt",
            str(file)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.project_root
        )

        if result.returncode == 0:
            return FixResult(
                fixed=True,
                message=f"Formatted {file.name} with terraform fmt",
                tool="terraform"
            )
        else:
            return FixResult(
                fixed=False,
                message=f"Terraform fmt failed: {result.stderr}"
            )
```

---

#### Task 4.3: Register Terraform Validator

**File**: `src/huskycat/core/validators/__init__.py`

**Changes**:

```python
from .terraform import TerraformValidator  # ADD THIS

__all__ = [
    # ... existing ...
    "TerraformValidator",  # ADD THIS
]
```

**File**: `src/huskycat/unified_validation.py`

**Changes**:

```python
from src.huskycat.core.validators import (
    # ... existing ...
    TerraformValidator,  # ADD THIS
)

# Register validator
self.validators = [
    # ... existing validators ...
    TerraformValidator(project_root=self.project_root, auto_fix=auto_fix),
]
```

---

#### Task 4.4: Update Configuration

**File**: `.huskycat.yaml`

**Changes**:

```json
{
  "tools": {
    // ... existing tools ...
    "terraform": {
      "enabled": true,
      "tools": ["terraform"],
      "file_patterns": ["*.tf", "*.tfvars"]
    }
  }
}
```

---

#### Task 4.5: Update Documentation

**File**: `docs/cli-reference.md`

**Add section**:

```markdown
### Terraform (Infrastructure Formatting)

Format Terraform infrastructure-as-code files.

**Auto-fix**:  Enabled by default with `--fix`

**Example**:
```bash
# Format all Terraform files
huskycat validate --fix **/*.tf

# Format specific file
huskycat validate --fix main.tf
```

**Features**:
- Canonical formatting
- Consistent indentation
- Attribute alignment
- Whitespace cleanup
```

---

### Phase 4 Acceptance Criteria

- [ ] Terraform installed in container
- [ ] TerraformValidator implemented and registered
- [ ] Terraform formatting detection working
- [ ] `huskycat validate --fix` formats .tf files
- [ ] Tests added
- [ ] Documentation updated

### Phase 4 Deliverables

- Modified: `ContainerFile`
- Added: `src/huskycat/core/validators/terraform.py`
- Modified: `src/huskycat/core/validators/__init__.py`
- Modified: `src/huskycat/unified_validation.py`
- Modified: `.huskycat.yaml`
- Modified: `docs/cli-reference.md`
- Added: `tests/test_validators/test_terraform.py`

---

## Testing Strategy

### Unit Tests

Each phase requires comprehensive unit tests:

```python
# tests/test_validators/test_ruff_autofix.py
def test_ruff_detects_fixable_issues():
    """Test Ruff detects issues that can be auto-fixed."""
    # Create file with fixable issues
    # Run validator
    # Assert issues detected

def test_ruff_applies_fixes():
    """Test Ruff auto-fix applies corrections."""
    # Create file with issues
    # Run validator with auto_fix=True
    # Assert fixes applied
    # Assert file now passes validation

def test_ruff_reports_unfixable_issues():
    """Test Ruff reports issues it cannot fix."""
    # Create file with unfixable issues
    # Run validator with auto_fix=True
    # Assert issues still reported
```

### Integration Tests

End-to-end workflow tests:

```bash
# tests/integration/test_auto_fix_workflow.sh

# Test 1: Multi-language auto-fix
create_test_files() {
    echo "x=1" > test.py  # Ruff will fix
    echo "const x  =  1" > test.js  # Prettier will fix
    echo "name=\"test\"" > test.toml  # Taplo will fix
}

test_auto_fix_all() {
    huskycat validate --fix test.py test.js test.toml
    assert_all_files_formatted
}

# Test 2: Git hook with auto-fix
test_git_hook_auto_fix() {
    git add test.py test.js
    huskycat validate --staged --fix
    assert_staged_files_formatted
}

# Test 3: CI mode (report only)
test_ci_mode_no_fix() {
    huskycat --mode ci validate --fix test.py
    assert_json_output_generated
    assert_no_files_modified  # CI mode doesn't write
}
```

---

## Rollout Plan

### Week 1: Phase 1 (Enable Existing Formatters)

**Mon-Tue**: Implement Ruff and Prettier auto-fix
**Wed**: Testing and documentation
**Thu**: Code review and merge
**Fri**: Deploy updated container

### Week 2: Phases 2-3 (IsSort, TOML)

**Mon-Tue**: Implement IsSort validator
**Wed**: Implement TOML/taplo validator
**Thu**: Testing and documentation
**Fri**: Code review and merge

### Week 3: Phase 4 (Terraform)

**Mon-Tue**: Implement Terraform validator
**Wed**: Comprehensive testing
**Thu**: Documentation and examples
**Fri**: Final review and deployment

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Formatters enabled | 8/8 | All formatters have auto-fix |
| Language coverage | 6/6 | Python, JS/TS, YAML, TOML, TF supported |
| Whitespace cleanup | 100% | All file types handle whitespace |
| Test coverage | >80% | pytest --cov |
| CI integration | Working | GitLab CI runs auto-fix |
| Git hook integration | Working | Pre-commit applies fixes |

---

## Risks and Mitigation

### Risk 1: Container Size Growth

**Mitigation**:
- Use multi-stage builds (already in place)
- Measure size increase per phase
- Target: <500MB total container size

### Risk 2: Breaking Existing Workflows

**Mitigation**:
- Auto-fix requires explicit `--fix` flag
- Default behavior unchanged (validate only)
- Comprehensive changelog

### Risk 3: Performance Impact

**Mitigation**:
- Run formatters in parallel where possible
- Cache formatted results
- Skip files that haven't changed

---

## Chapel Language Support (Future - Sprint 9)

**Status**: 🔬 Research Phase

**Required before implementation**:
1. Confirm Chapel 2.6+ has official formatter
2. Test Chapel installation in Alpine Linux
3. Evaluate container size impact
4. Confirm user demand

**If implemented, follow same pattern**:
- Add to ContainerFile
- Create ChapelValidator
- Register validator
- Update configuration
- Document

**Defer until**: Phases 1-4 complete and validated

---

## Summary

This implementation plan provides a **clear, phased approach** to adding comprehensive auto-formatting support to HuskyCat:

- **Phase 1** (Critical): Enable Ruff and Prettier - unblocks JavaScript/TypeScript
- **Phase 2** (High): Add IsSort - improves Python code organization
- **Phase 3** (High): Add TOML - critical for modern Python projects
- **Phase 4** (High): Add Terraform - supports infrastructure-as-code

Each phase is **independent**, **testable**, and **deliverable** within 2-3 days.

Total estimated duration: **2-3 weeks** for Phases 1-4.

Upon completion, HuskyCat will have **best-in-class auto-formatting** across all major languages with **simple flag-based control** suitable for git hooks, CI/CD, and interactive development.
