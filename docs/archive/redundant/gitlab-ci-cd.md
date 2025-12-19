# GitLab CI/CD Integration

HuskyCats Bates provides comprehensive CI/CD validation using the published container image. The container must be built and published manually using podman or docker on your local machine.

##  Quick Start

### Option 1: Include HuskyCats Template

Add this to your `.gitlab-ci.yml`:

```yaml
include:
  - remote: 'https://gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/-/raw/main/.gitlab/ci/husky-validation.yml'

stages:
  - test

# This will run comprehensive validation
husky:validate:
  stage: test
```

### Option 2: Custom Configuration

```yaml
image: registry.gitlab.com/tinyland/ai/huskycat/validator:latest

stages:
  - validate
  - lint
  - security
  - test

# Run all validations
validate:all:
  stage: validate
  script:
    - cd /workspace
    - cp -r ${CI_PROJECT_DIR}/* /workspace/
    - ./scripts/comprehensive-lint.sh
```

##  Available Jobs

### Validation Jobs

| Job | Description | Runs On |
|-----|-------------|---------|
| `validate:gitlab-ci` | Validates `.gitlab-ci.yml` syntax | CI file changes |
| `validate:auto-devops` | Validates Auto DevOps configuration | K8s/Helm changes |
| `validate:comprehensive` | Runs all linters and validators | All changes |

### Linting Jobs

| Job | Description | Tools Used |
|-----|-------------|------------|
| `lint:python` | Python code quality | Black, Flake8, MyPy, Ruff, Pylint |
| `lint:javascript` | JS/TS code quality | ESLint, Prettier |
| `lint:shell` | Shell script analysis | ShellCheck |
| `lint:docker` | Dockerfile best practices | Hadolint |
| `lint:yaml` | YAML validation | yamllint |
| `lint:ansible` | Ansible playbook linting | ansible-lint |

### Security Jobs

| Job | Description | Checks For |
|-----|-------------|------------|
| `security:secrets` | Secret scanning | Passwords, API keys, tokens |
| `security:python` | Python security | Bandit, Safety |

### Test Jobs

| Job | Description | Output |
|-----|-------------|--------|
| `test:unit` | Run unit tests | JUnit XML, Coverage |
| `quality:report` | Generate quality metrics | Quality report artifact |

##  Configuration

### Environment Variables

```yaml
variables:
  # Disable shallow clone for full repo access
  GIT_DEPTH: 0
  
  # Python settings
  PYTHONUNBUFFERED: "1"
  
  # Node settings
  NODE_ENV: "ci"
  
  # Custom linting options
  LINT_PYTHON_BLACK: "true"
  LINT_PYTHON_FLAKE8: "true"
  AUTO_FIX: "false"
```

### Caching

Speed up CI runs with caching:

```yaml
cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - node_modules/
    - .npm/
    - .cache/
    - .venv/
```

##  Use Cases

### 1. Python Project

```yaml
include:
  - remote: 'https://gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/-/raw/main/.gitlab/ci/husky-validation.yml'

stages:
  - lint
  - test

# Python-specific validation
python:quality:
  extends: husky:python
  stage: lint

# Run tests after linting
test:pytest:
  extends: .husky
  stage: test
  script:
    - python -m pytest
```

### 2. Node.js Project

```yaml
image: registry.gitlab.com/tinyland/ai/huskycat/validator:latest

stages:
  - install
  - lint
  - test

install:deps:
  stage: install
  script:
    - npm ci
  cache:
    key: ${CI_COMMIT_REF_SLUG}
    paths:
      - node_modules/

lint:js:
  stage: lint
  script:
    - npx eslint .
    - npx prettier --check .
  needs: ["install:deps"]
```

### 3. Mixed Language Project

```yaml
image: registry.gitlab.com/tinyland/ai/huskycat/validator:latest

stages:
  - validate

# Run all validations
validate:all:
  stage: validate
  before_script:
    - cd /workspace
    - cp -r ${CI_PROJECT_DIR}/* /workspace/
    - cp -r ${CI_PROJECT_DIR}/.* /workspace/ 2>/dev/null || true
  script:
    - ./scripts/comprehensive-lint.sh
  artifacts:
    paths:
      - lint-results.txt
    expire_in: 1 week
```

### 4. Security-Focused Pipeline

```yaml
include:
  - remote: 'https://gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/-/raw/main/.gitlab/ci/husky-validation.yml'

stages:
  - security

# Fail on security issues
security:scan:
  extends: husky:security
  stage: security
  allow_failure: false
```

##  Artifacts and Reports

### JUnit Test Reports

```yaml
test:results:
  script:
    - python -m pytest --junitxml=test-results.xml
  artifacts:
    reports:
      junit: test-results.xml
```

### Coverage Reports

```yaml
test:coverage:
  script:
    - python -m pytest --cov --cov-report=xml
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

### Quality Reports

```yaml
quality:metrics:
  extends: .husky
  script:
    - ./scripts/comprehensive-lint.sh > quality-report.txt
  artifacts:
    paths:
      - quality-report.txt
    expire_in: 1 month
```

## 🚨 Troubleshooting

### Common Issues

1. **"Docker-in-Docker not available"**
   - Not needed! HuskyCats image includes all tools

2. **"Permission denied" errors**
   - Add execution permissions in before_script:
   ```yaml
   before_script:
     - chmod +x scripts/*.sh
   ```

3. **"Module not found" errors**
   - Install dependencies in the job:
   ```yaml
   script:
     - pip install -r requirements.txt
     - npm install
   ```

### Debugging

Enable verbose output:

```yaml
variables:
  VERBOSE: "true"
  DEBUG: "1"
```

##  Migration Guide

### From Container Building in CI

Before:
```yaml
services:
  - docker:dind

build:
  script:
    - docker build -t myapp .
```

After:
```yaml
# Build locally with podman/docker:
# ./publish.sh v1.0.0

# Then use in CI:
image: registry.gitlab.com/tinyland/ai/huskycat/validator:latest

validate:
  script:
    - hadolint ContainerFile
    - ./scripts/comprehensive-lint.sh
```

### From Multiple Linter Jobs

Before:
```yaml
flake8:
  image: python:3.9
  script: flake8 .

eslint:
  image: node:16
  script: npx eslint .

shellcheck:
  image: koalaman/shellcheck
  script: shellcheck *.sh
```

After:
```yaml
image: registry.gitlab.com/tinyland/ai/huskycat/validator:latest

lint:all:
  script:
    - ./scripts/comprehensive-lint.sh
```

##  Binary Builds

HuskyCat's CI pipeline builds native binaries for multiple platforms using GitLab SaaS runners.

### Supported Platforms

| Platform | Architecture | Base Image | Runner | Status |
|----------|-------------|------------|--------|---------|
| Linux | x86_64 (AMD64) | Rocky Linux 10 | GitLab SaaS AMD64 |  Supported |
| Linux | ARM64 (aarch64) | Rocky Linux 10 | GitLab SaaS ARM64 |  Supported |
| macOS | Apple Silicon (M1/M2/M3) | macOS 14 | GitLab SaaS macOS |  Supported (ad-hoc signed) |
| macOS | Intel (x86_64) | - | - |  Not available |

### Build Configuration

**Linux AMD64:**
```yaml
binary:build:linux:
  stage: package
  image: rockylinux/rockylinux:10
  before_script:
    - dnf install -y epel-release
    - dnf install -y git curl gcc python3 python3-pip zlib-devel upx
    - curl -LsSf https://astral.sh/uv/install.sh | sh
  script:
    - uv sync --extra build
    - uv run pyinstaller --onefile --name huskycat-linux-amd64 huskycat_main.py
    - upx --best --lzma dist/bin/huskycat-linux-amd64
  artifacts:
    paths:
      - dist/bin/huskycat-linux-amd64
```

**Linux ARM64:**
```yaml
binary:build:linux-arm64:
  stage: package
  image: rockylinux/rockylinux:10
  tags:
    - saas-linux-medium-arm64
  before_script:
    - dnf install -y epel-release
    - dnf install -y git curl gcc python3 python3-pip zlib-devel upx
  script:
    - uv sync --extra build
    - uv run pyinstaller --onefile --name huskycat-linux-arm64 huskycat_main.py
```

**macOS ARM64 with Signing:**
```yaml
sign:darwin-arm64:
  extends: .macos_saas_runners
  stage: sign
  script:
    # Create temporary keychain
    - security create-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN_NAME"
    - security import certificate.p12 -k "$KEYCHAIN_NAME"

    # Check certificate type and sign or fallback
    - |
      APP_CERT_COUNT=$(security find-identity -v "$KEYCHAIN_NAME" | grep -c "Developer ID Application" || true)
      if [ "$APP_CERT_COUNT" -eq 0 ]; then
        codesign --force --sign - dist/bin/huskycat-darwin-arm64  # Ad-hoc signing
      else
        codesign --force --options runtime --sign "$APPLE_DEVELOPER_ID_APPLICATION" dist/bin/huskycat-darwin-arm64
      fi
    - codesign --verify --verbose dist/bin/huskycat-darwin-arm64
```

### Key Features

1. **Rocky Linux 10** - Latest RHEL-compatible base (supported through May 2035)
2. **Native Compilation** - No cross-compilation, native runners for each architecture
3. **UPX Compression** - Reduces binary size by ~60%
4. **macOS Code Signing** - Ad-hoc signing with fallback when Developer ID Application cert not available
5. **Automatic Releases** - Binaries attached to GitLab releases on tags

### Download Binaries

Pre-built binaries are available from GitLab releases:

```bash
# Latest release (permalink)
curl -L -o huskycat https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-amd64
chmod +x huskycat
```

See [Binary Downloads Guide](binary-downloads.md) for detailed instructions.

---

## 🎉 Benefits

1. **No Container Building in CI** - Uses pre-published images
2. **All Tools Pre-installed** - No setup needed
3. **Consistent Environment** - Same tools locally and in CI
4. **Fast Execution** - No build step required
5. **Comprehensive Validation** - All languages and configs covered
6. **Manual Publishing** - Full control over image versions

## 📚 Next Steps

- [Installation Guide](installation.md) - Setup and install HuskyCat
- [Configuration](configuration.md) - Configure validation rules
- [Auto DevOps](gitlab-auto-devops-complete.md) - Kubernetes validation