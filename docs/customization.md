# Customization Guide

This guide shows how to customize the linting setup for your specific needs.

## Adding New Languages

### Example: Adding Ruby Support

1. **Install Ruby linting tools**:
```bash
gem install rubocop rubocop-performance rubocop-rails
```

2. **Create Ruby configuration** (`.rubocop.yml`):
```yaml
AllCops:
  NewCops: enable
  TargetRubyVersion: 3.0
  Exclude:
    - 'vendor/**/*'
    - 'node_modules/**/*'

Style/Documentation:
  Enabled: false

Metrics/MethodLength:
  Max: 20
```

3. **Update `.lintstagedrc.json`**:
```json
{
  "*.rb": [
    "rubocop --auto-correct --fail-level E",
    "prettier --write"
  ]
}
```

4. **Update `comprehensive-lint.sh`**:
```bash
# Add to the script
detect_ruby_files() {
    local scope="${1:-all}"
    
    if [[ "$scope" == "staged" ]]; then
        git diff --cached --name-only --diff-filter=ACM | grep -E '\.rb$' || true
    else
        find . -name "*.rb" -type f \
            -not -path "./vendor/*" \
            -not -path "./node_modules/*" | sort
    fi
}

lint_ruby() {
    local files=("$@")
    
    if [[ ${#files[@]} -eq 0 ]]; then
        log_info "No Ruby files to lint"
        return 0
    fi
    
    log_info "Linting ${#files[@]} Ruby files..."
    
    if command_exists rubocop; then
        if [[ "$AUTO_FIX" == "true" ]]; then
            rubocop --auto-correct "${files[@]}"
        else
            rubocop "${files[@]}"
        fi
    fi
}
```

### Example: Adding Java Support

1. **Install tools**:
```bash
# Install checkstyle
wget https://github.com/checkstyle/checkstyle/releases/download/checkstyle-10.12.0/checkstyle-10.12.0-all.jar
```

2. **Create configuration** (`checkstyle.xml`):
```xml
<?xml version="1.0"?>
<!DOCTYPE module PUBLIC
    "-//Checkstyle//DTD Checkstyle Configuration 1.3//EN"
    "https://checkstyle.org/dtds/configuration_1_3.dtd">
<module name="Checker">
    <module name="TreeWalker">
        <module name="JavadocMethod"/>
        <module name="ConstantName"/>
        <module name="LocalVariableName"/>
    </module>
</module>
```

3. **Add to lint-staged**:
```json
{
  "*.java": [
    "java -jar checkstyle.jar -c checkstyle.xml"
  ]
}
```

## Customizing Existing Linters

### Python Customization

#### Stricter Black Configuration

In `pyproject.toml`:
```toml
[tool.black]
line-length = 79  # PEP 8 strict
target-version = ['py39', 'py310', 'py311']
preview = true  # Enable preview features
```

#### Custom Flake8 Plugins

Install plugins:
```bash
pip install flake8-docstrings flake8-annotations flake8-black
```

Update `.flake8`:
```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503
# Docstring checks
docstring-convention = google
# Type annotation checks
annotation-style = pep484
```

#### Ruff as Fast Alternative

Replace flake8 with ruff:
```bash
# In comprehensive-lint.sh
LINT_PYTHON_FLAKE8=false
LINT_PYTHON_RUFF=true
```

### Ansible Customization

#### Project-Specific Rules

Create custom Ansible-lint rules in `.ansible-lint-rules/`:
```python
# .ansible-lint-rules/custom_naming.py
from ansiblelint.rules import AnsibleLintRule

class TaskNameRule(AnsibleLintRule):
    id = 'custom-task-name'
    description = 'Task names must start with uppercase'
    tags = ['formatting']
    
    def matchtask(self, task, file=None):
        name = task.get('name', '')
        if name and not name[0].isupper():
            return True
        return False
```

Update `.ansible-lint`:
```yaml
rulesdir:
  - .ansible-lint-rules/
```

### JavaScript/TypeScript Customization

#### ESLint Configuration

Create `.eslintrc.js`:
```javascript
module.exports = {
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'prettier'
  ],
  rules: {
    'no-console': 'warn',
    '@typescript-eslint/explicit-function-return-type': 'error'
  }
};
```

Update `.lintstagedrc.json`:
```json
{
  "*.{ts,tsx}": [
    "eslint --fix --max-warnings 0",
    "prettier --write"
  ]
}
```

## Hook Customization

### Custom Pre-commit Checks

Add to `.husky/pre-commit`:
```bash
# Custom check: No TODOs in production code
if echo "$STAGED_FILES" | grep -v test | xargs grep -n "TODO" 2>/dev/null; then
    log_error "TODO comments found in production code!"
    FAILED=true
fi

# Custom check: File size limit
MAX_SIZE=1048576  # 1MB
for file in $STAGED_FILES; do
    if [ -f "$file" ] && [ $(stat -f%z "$file" 2>/dev/null || stat -c%s "$file") -gt $MAX_SIZE ]; then
        log_error "File $file exceeds size limit (1MB)"
        FAILED=true
    fi
done
```

### Skip Hooks Temporarily

```bash
# Skip all hooks
HUSKY=0 git commit

# Skip specific hook
git commit --no-verify

# Skip with environment variable
SKIP_LINT=1 git commit
```

### Conditional Hook Execution

```bash
# In pre-commit hook
if [ "$CI" = "true" ]; then
    log_info "Running in CI, skipping interactive checks"
    exit 0
fi

# Branch-specific rules
BRANCH=$(git symbolic-ref HEAD 2>/dev/null | cut -d"/" -f 3)
if [ "$BRANCH" = "main" ]; then
    # Stricter checks for main branch
    LINT_LEVEL="error"
else
    LINT_LEVEL="warning"
fi
```

## Performance Optimization

### Parallel Execution

Update `comprehensive-lint.sh`:
```bash
# Enable parallel processing
lint_files_parallel() {
    local files=("$@")
    local num_cores=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
    
    printf '%s\n' "${files[@]}" | \
        xargs -P "$num_cores" -I {} bash -c 'lint_single_file "$@"' _ {}
}
```

### Incremental Linting

Cache previous results:
```bash
# Create cache directory
mkdir -p .lint-cache

# Hash file content and cache result
cache_lint_result() {
    local file=$1
    local hash=$(sha256sum "$file" | cut -d' ' -f1)
    local cache_file=".lint-cache/${hash}"
    
    if [ -f "$cache_file" ]; then
        return 0  # Already linted
    fi
    
    # Run linting
    if lint_file "$file"; then
        touch "$cache_file"
        return 0
    fi
    return 1
}
```

### Selective Linting

Based on file patterns:
```bash
# Only lint if substantive changes
if git diff --cached "$file" | grep -E '^\+' | grep -qv '^\+\s*(#|//|/\*)'; then
    # File has non-comment changes
    lint_file "$file"
fi
```

## CI/CD Customization

### Matrix Testing

```yaml
lint:python:
  stage: lint
  image: python:$PYTHON_VERSION
  parallel:
    matrix:
      - PYTHON_VERSION: ['3.8', '3.9', '3.10', '3.11']
  script:
    - pip install -r requirements-dev.txt
    - black --check .
    - flake8 .
```

### Conditional Jobs

```yaml
lint:ansible:
  stage: lint
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
      when: always
    - changes:
        - "**/*.yml"
        - "**/*.yaml"
      when: always
    - when: manual
  script:
    - ansible-lint
```

## Project-Specific Configuration

### Monorepo Support

For monorepos, customize paths:
```bash
# In comprehensive-lint.sh
PACKAGES=("frontend" "backend" "shared")

for package in "${PACKAGES[@]}"; do
    log_info "Linting $package..."
    (cd "$package" && lint_package)
done
```

### Language-Specific Directories

```bash
# Python in specific directories
PYTHON_DIRS=("src" "tests" "scripts")
for dir in "${PYTHON_DIRS[@]}"; do
    find "$dir" -name "*.py" | xargs black
done
```

## IDE Integration

### Custom VS Code Tasks

`.vscode/tasks.json`:
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Lint Current File",
      "type": "shell",
      "command": "./scripts/comprehensive-lint.sh",
      "args": ["--file", "${file}"],
      "problemMatcher": "$eslint-stylish"
    }
  ]
}
```

### Git Hooks in IDEs

Ensure IDEs respect Git hooks:
- **VS Code**: Uses system Git by default
- **IntelliJ**: Settings → Version Control → Git → Use native Git
- **SourceTree**: Preferences → Git → Use System Git