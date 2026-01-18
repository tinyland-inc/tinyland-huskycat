# GitHub Actions Integration

Integrate HuskyCat validation into your GitHub Actions workflows for automated code quality checks.

## Quick Start

Add this workflow to `.github/workflows/validate.yml`:

```yaml
name: HuskyCat Validation

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Download HuskyCat
        run: |
          curl -L -o huskycat https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-amd64
          chmod +x huskycat
          sudo mv huskycat /usr/local/bin/

      - name: Install Podman
        run: |
          sudo apt-get update
          sudo apt-get install -y podman

      - name: Validate Code
        run: huskycat validate --all
```

##  Workflow Templates

### Basic Validation

Validate all files on push and pull requests:

```yaml
name: Code Validation

on: [push, pull_request]

jobs:
  validate:
    name: Validate Code Quality
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup HuskyCat
        run: |
          curl -L -o /usr/local/bin/huskycat \
            https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-amd64
          chmod +x /usr/local/bin/huskycat

      - name: Install Podman
        run: sudo apt-get update && sudo apt-get install -y podman

      - name: Run Validation
        run: huskycat --mode ci validate --all
```

### Python Project Validation

Focused validation for Python projects:

```yaml
name: Python Validation

on:
  push:
    paths:
      - '**.py'
      - 'pyproject.toml'
      - 'setup.py'
      - 'requirements*.txt'

jobs:
  python-validate:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup HuskyCat
        run: |
          curl -L -o /usr/local/bin/huskycat \
            https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-amd64
          chmod +x /usr/local/bin/huskycat

      - name: Install Podman
        run: sudo apt-get install -y podman

      - name: Validate Python Code
        run: |
          huskycat validate --all
          # Validators used: black, flake8, mypy, ruff, bandit
```

### Multi-Platform Validation

Test on multiple platforms:

```yaml
name: Multi-Platform Validation

on: [push, pull_request]

jobs:
  validate:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
        include:
          - os: ubuntu-latest
            binary: huskycat-linux-amd64
            container: podman
          - os: macos-latest
            binary: huskycat-darwin-arm64
            container: podman

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4

      - name: Download HuskyCat
        run: |
          curl -L -o huskycat \
            https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/${{ matrix.binary }}
          chmod +x huskycat
          sudo mv huskycat /usr/local/bin/

      - name: Install Container Runtime
        run: |
          if [ "$RUNNER_OS" == "Linux" ]; then
            sudo apt-get update && sudo apt-get install -y podman
          elif [ "$RUNNER_OS" == "macOS" ]; then
            brew install podman
            podman machine init
            podman machine start
          fi

      - name: Validate
        run: huskycat validate --all
```

### Pull Request Validation with Comments

Validate PR changes and comment on results:

```yaml
name: PR Validation

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  validate-pr:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for better diff analysis

      - name: Setup HuskyCat
        run: |
          curl -L -o /usr/local/bin/huskycat \
            https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-amd64
          chmod +x /usr/local/bin/huskycat

      - name: Install Podman
        run: sudo apt-get install -y podman

      - name: Validate Changed Files
        id: validate
        run: |
          huskycat --json validate --all > validation-results.json
          echo "results<<EOF" >> $GITHUB_OUTPUT
          cat validation-results.json >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT
        continue-on-error: true

      - name: Comment PR
        uses: actions/github-script@v7
        if: always()
        with:
          script: |
            const results = ${{ steps.validate.outputs.results }};
            const comment = `## HuskyCat Validation Results

            ${results.success ? ' All validations passed!' : ' Validation failures found'}

            **Files validated:** ${results.summary.total_files}
            **Errors:** ${results.summary.total_errors}
            **Warnings:** ${results.summary.total_warnings}
            `;

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
```

### Scheduled Validation

Run periodic validation checks:

```yaml
name: Scheduled Validation

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday at midnight
  workflow_dispatch:  # Manual trigger

jobs:
  scheduled-validate:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup HuskyCat
        run: |
          curl -L -o /usr/local/bin/huskycat \
            https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-amd64
          chmod +x /usr/local/bin/huskycat

      - name: Install Podman
        run: sudo apt-get install -y podman

      - name: Full Repository Validation
        run: huskycat validate --all --verbose

      - name: Upload Results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: validation-results
          path: |
            .huskycat/cache/
            validation-results.json
```

##  Configuration

### Environment Variables

Set these in workflow or repository secrets:

```yaml
env:
  HUSKYCAT_MODE: ci
  HUSKYCAT_LOG_LEVEL: INFO
```

### Secrets Configuration

For private registries or custom setups:

```yaml
env:
  CONTAINER_REGISTRY_TOKEN: ${{ secrets.CONTAINER_REGISTRY_TOKEN }}
```

##  Status Checks

### Required Status Checks

Add HuskyCat as a required status check:

1. Go to **Settings** → **Branches** → **Branch protection rules**
2. Select your branch (e.g., `main`)
3. Enable **Require status checks to pass before merging**
4. Search for and select **HuskyCat Validation**

### Status Badge

Add a badge to your README:

```markdown
[![HuskyCat Validation](https://github.com/your-org/your-repo/workflows/HuskyCat%20Validation/badge.svg)](https://github.com/your-org/your-repo/actions)
```

##  Advanced Usage

### Matrix Strategy for Multiple Validators

Run specific validators in parallel:

```yaml
jobs:
  validate:
    strategy:
      matrix:
        validator: [python-black, mypy, flake8, ruff]

    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
      - name: Setup HuskyCat
        run: # ... (setup steps)

      - name: Run ${{ matrix.validator }}
        run: huskycat validate --validator ${{ matrix.validator }} --all
```

### Caching

Speed up workflows with caching:

```yaml
- name: Cache HuskyCat Binary
  uses: actions/cache@v4
  with:
    path: /usr/local/bin/huskycat
    key: huskycat-${{ runner.os }}-${{ hashFiles('**/huskycat-version.txt') }}

- name: Cache Validation Schemas
  uses: actions/cache@v4
  with:
    path: .huskycat/schemas/
    key: huskycat-schemas-${{ hashFiles('.huskycat/schemas/**') }}
```

### Auto-Fix and Commit

Automatically fix issues and commit changes:

```yaml
- name: Validate and Auto-Fix
  run: huskycat validate --all --fix

- name: Commit Fixes
  uses: stefanzweifel/git-auto-commit-action@v5
  with:
    commit_message: "fix: auto-fix validation issues [skip ci]"
    file_pattern: "*.py *.js *.ts *.yaml"
```

** Warning:** Only use auto-commit on trusted branches or in draft PRs to avoid security risks.

##  Container-Based Workflow

Use HuskyCat's validation container directly:

```yaml
jobs:
  validate:
    runs-on: ubuntu-latest
    container:
      image: registry.gitlab.com/tinyland/ai/huskycat/validator:latest

    steps:
      - uses: actions/checkout@v4

      - name: Validate
        run: huskycat validate --all
```

## 🔗 Integration with Other Actions

### Combine with Code Coverage

```yaml
- name: Run Tests with Coverage
  run: pytest --cov --cov-report=xml

- name: Validate Code Quality
  run: huskycat validate --all

- name: Upload Coverage
  uses: codecov/codecov-action@v4
```

### Combine with Security Scanning

```yaml
- name: HuskyCat Validation
  run: huskycat validate --all

- name: Run Trivy Security Scan
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'fs'
```

##  Performance Tips

1. **Cache Binaries** - Use actions/cache to avoid re-downloading
2. **Parallel Jobs** - Use matrix strategy for independent validations
3. **Conditional Execution** - Use `paths` filter to run only when needed
4. **Container Runtime** - Podman is faster than Docker in most cases

##  Troubleshooting

### Binary Download Fails

```yaml
- name: Download HuskyCat with Retry
  uses: nick-fields/retry@v2
  with:
    timeout_minutes: 5
    max_attempts: 3
    command: |
      curl -L -o /usr/local/bin/huskycat \
        https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-amd64
      chmod +x /usr/local/bin/huskycat
```

### Podman Installation Issues

```yaml
- name: Install Podman (Fallback to Docker)
  run: |
    if ! command -v podman &> /dev/null; then
      if ! command -v docker &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y podman
      fi
    fi
```

### Permission Issues on macOS

```yaml
- name: Allow Binary Execution (macOS)
  if: runner.os == 'macOS'
  run: |
    xattr -d com.apple.quarantine /usr/local/bin/huskycat || true
```

## 🔐 Security Considerations

1. **Pin Binary Versions** - Use specific tags instead of `latest`
2. **Verify Checksums** - Download and verify SHA256 checksums
3. **Limit Permissions** - Use minimal required workflow permissions
4. **Review Auto-Commits** - Don't auto-commit on public PRs

Example with version pinning:

```yaml
- name: Download HuskyCat (Pinned Version)
  run: |
    VERSION="v2.0.0"
    curl -L -o /usr/local/bin/huskycat \
      "https://gitlab.com/tinyland/ai/huskycat/-/jobs/artifacts/${VERSION}/raw/dist/bin/huskycat-linux-amd64?job=binary:build:linux"
    chmod +x /usr/local/bin/huskycat
```

## 📚 Examples

Complete workflow examples are available in the [HuskyCat repository](https://gitlab.com/tinyland/ai/huskycat/-/tree/main/.github/workflows).

---

For GitLab CI integration, see [GitLab CI/CD Guide](ci-cd/gitlab.md).

For CLI usage, see [CLI Reference](cli-reference.md).

For binary downloads, see [Binary Downloads](binary-downloads.md).
