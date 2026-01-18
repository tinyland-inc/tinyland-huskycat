# E2E and CI Testing Strategy for HuskyCat Git Hook Bootstrap

**Status**: Sprint 9A Phase 1.5
**Focus**: Binary + Git Hooks mode testing for GitOps repositories
**Created**: 2025-12-06

## Executive Summary

This document defines the comprehensive End-to-End (E2E) and Continuous Integration (CI) testing strategy for HuskyCat's git hook bootstrap procedure. The primary challenge is testing a tool that modifies git hooks (a Catch-22 for dogfooding), requiring isolated test environments and GitLab CI examples.

## Testing Philosophy

**Key Principle**: We cannot dogfood binary+hooks mode in HuskyCat's own repo (we use UV+tracked hooks), so we must create:

1. **Isolated test repositories** - Synthetic GitOps repos for E2E testing
2. **Container-based test environments** - Reproducible, clean git repos
3. **GitLab CI job templates** - Reference implementations for users
4. **Automated validation** - Unit, integration, and E2E test suites

---

## 1. Test Scenarios Matrix

### 1.1 Repository Types

| Repo Type | Features | Expected Behavior |
|-----------|----------|-------------------|
| **GitOps Full** | GitLab CI + Helm + K8s + Terraform + Ansible | All features enabled, GitOps mode active |
| **GitLab CI Only** | .gitlab-ci.yml only | CI validation in pre-push, no GitOps mode |
| **Helm Chart** | chart/ directory | GitOps mode, Helm validation in pre-push |
| **Kubernetes** | k8s/ manifests | GitOps mode, K8s validation in pre-push |
| **Terraform** | *.tf files | GitOps mode, TF validation in pre-commit |
| **Mixed Python + IaC** | Python + K8s | Both Python and GitOps validations |
| **Plain Python** | No IaC files | Standard validation only, no GitOps |

### 1.2 Installation Scenarios

| Scenario | Binary Location | Expected Outcome |
|----------|----------------|------------------|
| **Fresh Install** | Binary in ~/.local/bin | Hooks installed with binary path |
| **PATH Install** | Binary in /usr/local/bin | Hooks use `huskycat` from PATH |
| **No Binary** | UV available | Hooks fall back to UV execution |
| **Bootstrap Command** | `huskycat bootstrap` | Auto-detect, install, report features |
| **Manual Setup** | `huskycat setup-hooks` | Same as bootstrap without self-install |

### 1.3 Update Scenarios

| Scenario | Before | After | Expected Behavior |
|----------|--------|-------|-------------------|
| **Binary Update** | v2.0.0 hooks | v2.1.0 binary | Hooks auto-regenerate on next commit |
| **Hook Version Mismatch** | Old hook templates | New binary | User warned, hooks updated |
| **Template Changes** | v2.0.0 | v2.0.1 (template fix) | Hooks regenerated with new logic |
| **Force Regenerate** | Any version | Any version | `--force` regenerates all hooks |

---

## 2. E2E Test Suite Design

### 2.1 Test Environment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  E2E Test Orchestrator                          │
│                  (pytest + Docker/Podman)                       │
└────────────┬────────────────────────────────────────────────────┘
             │
             v
┌─────────────────────────────────────────────────────────────────┐
│              Isolated Test Container                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Test Repository (ephemeral)                             │   │
│  │  - Fresh git init                                        │   │
│  │  - GitOps files (Helm/K8s/Terraform/Ansible)            │   │
│  │  - HuskyCat binary installed                            │   │
│  │  - Git configured (user.name, user.email)               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Test Steps:                                                    │
│  1. huskycat bootstrap                                          │
│  2. Validate hooks installed                                    │
│  3. Simulate git commit/push                                    │
│  4. Assert validations run correctly                            │
│  5. Test binary update scenario                                │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Test Repository Factory

**Location**: `tests/e2e/fixtures/repo_factory.py`

```python
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
import tempfile

class TestRepoFactory:
    """Factory for creating isolated test repositories."""

    @staticmethod
    def create_gitops_repo(
        features: List[str],
        temp_dir: Optional[Path] = None
    ) -> Path:
        """
        Create a test GitOps repository with specified features.

        Args:
            features: List of features to enable
                     ['gitlab_ci', 'helm', 'k8s', 'terraform', 'ansible']
            temp_dir: Optional directory (uses tempfile if None)

        Returns:
            Path to test repository
        """
        repo_path = temp_dir or Path(tempfile.mkdtemp())

        # Initialize git
        subprocess.run(['git', 'init'], cwd=repo_path, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'],
                      cwd=repo_path, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'],
                      cwd=repo_path, check=True)

        # Create feature files based on requested features
        if 'gitlab_ci' in features:
            TestRepoFactory._create_gitlab_ci(repo_path)

        if 'helm' in features:
            TestRepoFactory._create_helm_chart(repo_path)

        if 'k8s' in features:
            TestRepoFactory._create_k8s_manifests(repo_path)

        if 'terraform' in features:
            TestRepoFactory._create_terraform(repo_path)

        if 'ansible' in features:
            TestRepoFactory._create_ansible(repo_path)

        # Initial commit
        subprocess.run(['git', 'add', '.'], cwd=repo_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'],
                      cwd=repo_path, check=True)

        return repo_path

    @staticmethod
    def _create_gitlab_ci(repo_path: Path):
        """Create .gitlab-ci.yml with Auto-DevOps templates."""
        ci_content = """
include:
  - template: Auto-DevOps.gitlab-ci.yml
  - template: Security/SAST.gitlab-ci.yml
  - template: Security/Secret-Detection.gitlab-ci.yml

variables:
  AUTO_DEVOPS_PLATFORM_TARGET: ECS
  POSTGRES_ENABLED: "false"

stages:
  - build
  - test
  - deploy

build:
  stage: build
  script:
    - echo "Building application"
  artifacts:
    paths:
      - dist/

test:
  stage: test
  script:
    - echo "Running tests"
"""
        (repo_path / '.gitlab-ci.yml').write_text(ci_content.strip())

    @staticmethod
    def _create_helm_chart(repo_path: Path):
        """Create Helm chart structure."""
        chart_dir = repo_path / 'chart'
        chart_dir.mkdir(exist_ok=True)

        (chart_dir / 'Chart.yaml').write_text("""
apiVersion: v2
name: test-app
description: Test application Helm chart
type: application
version: 0.1.0
appVersion: "1.0"
""".strip())

        (chart_dir / 'values.yaml').write_text("""
replicaCount: 2
image:
  repository: nginx
  tag: "1.21"
  pullPolicy: IfNotPresent
service:
  type: ClusterIP
  port: 80
""".strip())

    @staticmethod
    def _create_k8s_manifests(repo_path: Path):
        """Create Kubernetes manifest files."""
        k8s_dir = repo_path / 'k8s' / 'deployments'
        k8s_dir.mkdir(parents=True, exist_ok=True)

        (k8s_dir / 'app.yaml').write_text("""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: test-app
  template:
    metadata:
      labels:
        app: test-app
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
        ports:
        - containerPort: 80
""".strip())

    @staticmethod
    def _create_terraform(repo_path: Path):
        """Create Terraform configuration."""
        (repo_path / 'main.tf').write_text("""
terraform {
  required_version = ">= 1.0"
}

resource "null_resource" "test" {
  provisioner "local-exec" {
    command = "echo Test"
  }
}
""".strip())

    @staticmethod
    def _create_ansible(repo_path: Path):
        """Create Ansible playbook."""
        playbooks_dir = repo_path / 'playbooks'
        playbooks_dir.mkdir(exist_ok=True)

        (playbooks_dir / 'deploy.yml').write_text("""
---
- name: Deploy application
  hosts: all
  tasks:
    - name: Test task
      debug:
        msg: "Deploying application"
""".strip())
```

### 2.3 E2E Test Cases

**Location**: `tests/e2e/test_bootstrap_gitops.py`

```python
import pytest
import subprocess
from pathlib import Path
from .fixtures.repo_factory import TestRepoFactory

class TestBootstrapGitOps:
    """E2E tests for HuskyCat bootstrap on GitOps repositories."""

    @pytest.fixture
    def huskycat_binary(self) -> Path:
        """Path to HuskyCat binary (must be built before tests)."""
        binary_path = Path.home() / '.local' / 'bin' / 'huskycat'
        assert binary_path.exists(), "Binary not found - run 'npm run build:binary'"
        return binary_path

    def test_bootstrap_full_gitops_repo(self, huskycat_binary, tmp_path):
        """Test bootstrap on repository with all GitOps features."""
        # Create test repo
        repo = TestRepoFactory.create_gitops_repo(
            features=['gitlab_ci', 'helm', 'k8s', 'terraform', 'ansible'],
            temp_dir=tmp_path
        )

        # Run bootstrap
        result = subprocess.run(
            [str(huskycat_binary), 'bootstrap', '--force'],
            cwd=repo,
            capture_output=True,
            text=True
        )

        # Assert success
        assert result.returncode == 0, f"Bootstrap failed: {result.stderr}"
        assert "GitOps repository" in result.stdout
        assert "3 hooks" in result.stdout

        # Verify hooks installed
        hooks_dir = repo / '.git' / 'hooks'
        assert (hooks_dir / 'pre-commit').exists()
        assert (hooks_dir / 'pre-push').exists()
        assert (hooks_dir / 'commit-msg').exists()

        # Verify hooks are executable
        for hook in ['pre-commit', 'pre-push', 'commit-msg']:
            hook_path = hooks_dir / hook
            assert hook_path.stat().st_mode & 0o111, f"{hook} not executable"

        # Verify GitOps features detected
        assert "GitLab CI" in result.stdout
        assert "Helm" in result.stdout
        assert "Kubernetes" in result.stdout
        assert "Terraform" in result.stdout
        assert "Ansible" in result.stdout

    def test_bootstrap_helm_only_repo(self, huskycat_binary, tmp_path):
        """Test bootstrap on Helm-only repository."""
        repo = TestRepoFactory.create_gitops_repo(
            features=['helm'],
            temp_dir=tmp_path
        )

        result = subprocess.run(
            [str(huskycat_binary), 'bootstrap'],
            cwd=repo,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "GitOps repository" in result.stdout
        assert "Helm" in result.stdout
        assert "Terraform" not in result.stdout  # Should not detect

    def test_bootstrap_plain_python_repo(self, huskycat_binary, tmp_path):
        """Test bootstrap on non-GitOps repository."""
        # Create plain git repo (no GitOps features)
        repo = tmp_path
        subprocess.run(['git', 'init'], cwd=repo, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=repo)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo)

        # Create Python file
        (repo / 'main.py').write_text('print("Hello")')
        subprocess.run(['git', 'add', '.'], cwd=repo, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=repo, check=True)

        result = subprocess.run(
            [str(huskycat_binary), 'bootstrap'],
            cwd=repo,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "3 hooks" in result.stdout
        assert "GitOps" not in result.stdout  # Should not enable GitOps mode

    def test_hook_execution_pre_commit(self, huskycat_binary, tmp_path):
        """Test pre-commit hook executes validation."""
        repo = TestRepoFactory.create_gitops_repo(
            features=['gitlab_ci'],
            temp_dir=tmp_path
        )

        # Bootstrap
        subprocess.run([str(huskycat_binary), 'bootstrap'], cwd=repo, check=True)

        # Create invalid Python file (syntax error)
        (repo / 'bad.py').write_text('def foo(\n')  # Syntax error
        subprocess.run(['git', 'add', 'bad.py'], cwd=repo, check=True)

        # Try to commit (should fail)
        result = subprocess.run(
            ['git', 'commit', '-m', 'Add bad file'],
            cwd=repo,
            capture_output=True,
            text=True
        )

        # Pre-commit hook should block commit
        assert result.returncode != 0, "Hook should have blocked commit"
        assert "SyntaxError" in result.stderr or "invalid syntax" in result.stderr

    def test_hook_execution_pre_push_gitlab_ci(self, huskycat_binary, tmp_path):
        """Test pre-push hook validates GitLab CI."""
        repo = TestRepoFactory.create_gitops_repo(
            features=['gitlab_ci'],
            temp_dir=tmp_path
        )

        subprocess.run([str(huskycat_binary), 'bootstrap'], cwd=repo, check=True)

        # Create invalid .gitlab-ci.yml
        (repo / '.gitlab-ci.yml').write_text("""
invalid yaml syntax here
  - no proper structure
not even valid YAML
""")
        subprocess.run(['git', 'add', '.gitlab-ci.yml'], cwd=repo, check=True)
        subprocess.run(['git', 'commit', '-m', 'Update CI'], cwd=repo, check=True)

        # Setup remote (required for pre-push)
        subprocess.run(['git', 'remote', 'add', 'origin', '/tmp/dummy.git'],
                      cwd=repo, check=True)

        # Try to push (should fail)
        result = subprocess.run(
            ['git', 'push', '--dry-run', 'origin', 'main'],
            cwd=repo,
            capture_output=True,
            text=True
        )

        # Pre-push hook should detect invalid CI config
        # Note: --dry-run may not trigger hooks, so this test may need adjustment
        assert "GitLab CI" in result.stderr or result.returncode != 0

    def test_binary_version_update_regenerates_hooks(self, huskycat_binary, tmp_path):
        """Test hook auto-regeneration on binary version update."""
        repo = TestRepoFactory.create_gitops_repo(
            features=['helm'],
            temp_dir=tmp_path
        )

        # Install hooks with current version
        subprocess.run([str(huskycat_binary), 'bootstrap'], cwd=repo, check=True)

        # Read installed hook
        pre_commit = repo / '.git' / 'hooks' / 'pre-commit'
        original_content = pre_commit.read_text()
        assert 'VERSION="2.0.0"' in original_content or 'VERSION=2.0.0' in original_content

        # Simulate version change (manually edit hook to old version)
        modified_content = original_content.replace('VERSION="2.0.0"', 'VERSION="1.9.0"')
        pre_commit.write_text(modified_content)

        # Run setup-hooks again (should detect version mismatch)
        result = subprocess.run(
            [str(huskycat_binary), 'setup-hooks'],
            cwd=repo,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        # Hook should be regenerated with current version
        new_content = pre_commit.read_text()
        assert 'VERSION="2.0.0"' in new_content or 'VERSION=2.0.0' in new_content
```

---

## 3. GitLab CI Integration Examples

### 3.1 Testing HuskyCat Bootstrap in GitLab CI

**Use Case**: Test that HuskyCat bootstrap works correctly in CI environment

**File**: `.gitlab-ci.yml` (for HuskyCat's own testing pipeline)

```yaml
# Job to test bootstrap procedure in isolated environment
test:bootstrap:binary:
  stage: test
  image: alpine:latest
  before_script:
    # Install dependencies
    - apk add --no-cache git bash python3 py3-pip

    # Download HuskyCat binary (from artifacts or release)
    - wget https://github.com/yourusername/huskycat/releases/download/v2.0.0/huskycat-linux -O huskycat
    - chmod +x huskycat
    - mv huskycat /usr/local/bin/

  script:
    # Create test GitOps repository
    - mkdir -p /tmp/test-gitops
    - cd /tmp/test-gitops
    - git init
    - git config user.name "CI Test"
    - git config user.email "ci@test.com"

    # Create GitOps files
    - mkdir -p chart k8s/deployments
    - |
      cat > chart/Chart.yaml <<EOF
      apiVersion: v2
      name: test-app
      version: 0.1.0
      EOF
    - |
      cat > k8s/deployments/app.yaml <<EOF
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: test-app
      spec:
        replicas: 1
      EOF
    - |
      cat > .gitlab-ci.yml <<EOF
      test:
        script:
          - echo "Test job"
      EOF

    # Commit initial files
    - git add .
    - git commit -m "Initial commit"

    # Run bootstrap
    - huskycat bootstrap --force

    # Verify hooks installed
    - test -f .git/hooks/pre-commit || exit 1
    - test -f .git/hooks/pre-push || exit 1
    - test -f .git/hooks/commit-msg || exit 1

    # Verify hooks are executable
    - test -x .git/hooks/pre-commit || exit 1
    - test -x .git/hooks/pre-push || exit 1
    - test -x .git/hooks/commit-msg || exit 1

    # Test hook execution (create valid Python file)
    - echo 'print("test")' > test.py
    - git add test.py
    - git commit -m "feat: add test file"  # Should pass

    # Test hook blocks invalid commit message
    - echo 'print("test2")' > test2.py
    - git add test2.py
    - |
      if git commit -m "bad commit message"; then
        echo "ERROR: Hook should have blocked invalid commit message"
        exit 1
      else
        echo "✓ Hook correctly blocked invalid commit message"
      fi

  artifacts:
    when: on_failure
    paths:
      - /tmp/test-gitops/.git/hooks/
    expire_in: 1 week
```

### 3.2 User Reference: GitLab CI for Projects Using HuskyCat

**Use Case**: Example CI configuration for users who installed HuskyCat in their GitOps repo

**File**: User's `.gitlab-ci.yml`

```yaml
# Example GitLab CI configuration for projects using HuskyCat
# This shows how to integrate HuskyCat validation in CI pipeline

include:
  - template: Auto-DevOps.gitlab-ci.yml
  - template: Security/SAST.gitlab-ci.yml

variables:
  # Enable Auto-DevOps
  AUTO_DEVOPS_PLATFORM_TARGET: ECS
  POSTGRES_ENABLED: "false"

  # HuskyCat settings (optional - will use defaults if not set)
  HUSKYCAT_MODE: ci
  HUSKYCAT_VERBOSE: "true"

stages:
  - validate
  - build
  - test
  - deploy

# Validate with HuskyCat before building
huskycat:validate:
  stage: validate
  image: alpine:latest
  before_script:
    - apk add --no-cache python3 py3-pip bash git

    # Option 1: Install from PyPI (when released)
    # - pip install huskycat

    # Option 2: Download binary
    - wget https://github.com/yourusername/huskycat/releases/latest/download/huskycat-linux -O /usr/local/bin/huskycat
    - chmod +x /usr/local/bin/huskycat

  script:
    # Run all validations
    - huskycat validate --all

    # Explicitly validate GitLab CI
    - huskycat ci-validate .gitlab-ci.yml

    # Validate Auto-DevOps (if applicable)
    - |
      if [ -d "chart" ] || [ -d "k8s" ]; then
        huskycat auto-devops --fast
      fi

  artifacts:
    when: always
    reports:
      junit: huskycat-results.xml
    paths:
      - huskycat-results.xml
      - .huskycat-cache/
    expire_in: 1 week

  # Only run on merge requests and main branch
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'

# Validate Helm chart specifically (optional separate job)
helm:validate:
  stage: validate
  image: alpine/helm:latest
  script:
    - huskycat auto-devops --validate-helm
  only:
    changes:
      - chart/**/*
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
      changes:
        - chart/**/*

# Validate Kubernetes manifests (optional separate job)
k8s:validate:
  stage: validate
  image: bitnami/kubectl:latest
  script:
    - huskycat auto-devops --validate-k8s
  only:
    changes:
      - k8s/**/*
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
      changes:
        - k8s/**/*
```

### 3.3 Binary Build and Release CI Job

**Use Case**: Build HuskyCat binary in CI and publish as artifact

**File**: `.gitlab-ci.yml` (HuskyCat project)

```yaml
build:binary:linux:
  stage: build
  image: python:3.11-alpine
  before_script:
    - apk add --no-cache git bash gcc musl-dev libffi-dev
    - pip install pyinstaller

  script:
    - npm run build:binary

  artifacts:
    name: "huskycat-binary-linux-$CI_COMMIT_SHORT_SHA"
    paths:
      - dist/huskycat
    expire_in: 30 days

  rules:
    - if: '$CI_COMMIT_TAG'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'

# Release job (creates GitHub/GitLab release with binary)
release:
  stage: deploy
  image: registry.gitlab.com/gitlab-org/release-cli:latest
  needs:
    - build:binary:linux
  script:
    - echo "Creating release $CI_COMMIT_TAG"

  release:
    tag_name: '$CI_COMMIT_TAG'
    description: './CHANGELOG.md'
    assets:
      links:
        - name: 'HuskyCat Binary (Linux)'
          url: '$CI_PROJECT_URL/-/jobs/artifacts/$CI_COMMIT_TAG/raw/dist/huskycat?job=build:binary:linux'

  rules:
    - if: '$CI_COMMIT_TAG'
```

---

## 4. Automated Test Execution

### 4.1 Local E2E Test Execution

**Script**: `scripts/test-bootstrap-e2e.sh`

```bash
#!/bin/bash
# E2E test script for local execution

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== HuskyCat Bootstrap E2E Test ==="
echo ""

# Build binary
echo "Building binary..."
cd "$PROJECT_ROOT"
npm run build:binary

# Run pytest E2E tests
echo ""
echo "Running E2E tests..."
uv run pytest tests/e2e/test_bootstrap_gitops.py -v -s

echo ""
echo "✓ E2E tests complete!"
```

### 4.2 Container-Based Test Environment

**File**: `tests/e2e/ContainerFile`

```dockerfile
# Container for isolated E2E testing
FROM alpine:latest

# Install dependencies
RUN apk add --no-cache \
    git \
    bash \
    python3 \
    py3-pip \
    helm \
    kubectl \
    terraform

# Install HuskyCat binary (copy from build context)
COPY dist/huskycat /usr/local/bin/huskycat
RUN chmod +x /usr/local/bin/huskycat

# Create test workspace
WORKDIR /workspace

# Entry point runs test script
COPY tests/e2e/run-container-tests.sh /run-tests.sh
RUN chmod +x /run-tests.sh

ENTRYPOINT ["/run-tests.sh"]
```

**Test Runner**: `tests/e2e/run-container-tests.sh`

```bash
#!/bin/bash
set -e

echo "=== Running E2E Tests in Container ==="

# Create test repo
mkdir -p /tmp/test-gitops
cd /tmp/test-gitops

git init
git config user.name "Container Test"
git config user.email "test@container"

# Create GitOps files
mkdir -p chart k8s/deployments

cat > chart/Chart.yaml <<EOF
apiVersion: v2
name: test-app
version: 0.1.0
EOF

cat > k8s/deployments/app.yaml <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: test-app
  template:
    metadata:
      labels:
        app: test-app
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
EOF

cat > .gitlab-ci.yml <<EOF
test:
  script:
    - echo "Test"
EOF

git add .
git commit -m "Initial commit"

# Test bootstrap
echo ""
echo "Testing: huskycat bootstrap"
huskycat bootstrap --force

# Verify hooks
echo ""
echo "Verifying hooks installed..."
test -f .git/hooks/pre-commit || { echo "ERROR: pre-commit hook missing"; exit 1; }
test -f .git/hooks/pre-push || { echo "ERROR: pre-push hook missing"; exit 1; }
test -f .git/hooks/commit-msg || { echo "ERROR: commit-msg hook missing"; exit 1; }

test -x .git/hooks/pre-commit || { echo "ERROR: pre-commit not executable"; exit 1; }
test -x .git/hooks/pre-push || { echo "ERROR: pre-push not executable"; exit 1; }
test -x .git/hooks/commit-msg || { echo "ERROR: commit-msg not executable"; exit 1; }

echo "✓ All hooks installed and executable"

# Test pre-commit hook
echo ""
echo "Testing pre-commit hook execution..."
echo 'print("valid python")' > test.py
git add test.py
git commit -m "feat: add test file"
echo "✓ Pre-commit hook passed for valid Python"

# Test commit-msg hook
echo ""
echo "Testing commit-msg hook (should block invalid message)..."
echo 'print("test2")' > test2.py
git add test2.py
if git commit -m "invalid message format"; then
    echo "ERROR: commit-msg hook should have blocked this"
    exit 1
else
    echo "✓ commit-msg hook correctly blocked invalid message"
fi

echo ""
echo "=== All container E2E tests passed! ==="
```

**Build and Run**:

```bash
# Build test container
podman build -f tests/e2e/ContainerFile -t huskycat-e2e-test .

# Run tests
podman run --rm huskycat-e2e-test
```

---

## 5. Test Coverage Metrics

### 5.1 Coverage Goals

| Component | Target Coverage | Current | Priority |
|-----------|----------------|---------|----------|
| `hook_generator.py` | 90% | TBD | High |
| `commands/hooks.py` | 85% | TBD | High |
| `commands/bootstrap.py` | 85% | TBD | High |
| Hook templates | 100% (E2E) | TBD | High |
| GitOps detection | 95% | TBD | Medium |
| Binary execution fallback | 80% | TBD | Medium |

### 5.2 Test Pyramid

```
                    ┌─────────────┐
                    │   E2E (10)  │  Container-based, full workflow
                    └─────────────┘
                 ┌───────────────────┐
                 │  Integration (30)  │  HookGenerator + real git
                 └───────────────────┘
           ┌─────────────────────────────┐
           │     Unit Tests (100+)       │  Functions, methods, edge cases
           └─────────────────────────────┘
```

**Target Distribution**:
- 70% Unit tests (fast, isolated, comprehensive edge cases)
- 20% Integration tests (real git operations, file system)
- 10% E2E tests (full bootstrap workflow, slow but critical)

---

## 6. Continuous Testing in GitLab CI

### 6.1 Test Matrix Job

```yaml
test:bootstrap:matrix:
  stage: test
  image: alpine:latest
  parallel:
    matrix:
      - REPO_TYPE: [gitops-full, gitlab-ci-only, helm-only, k8s-only, plain-python]

  before_script:
    - apk add --no-cache git bash python3 py3-pip
    - pip install pytest
    - wget https://github.com/yourusername/huskycat/releases/latest/download/huskycat-linux -O /usr/local/bin/huskycat
    - chmod +x /usr/local/bin/huskycat

  script:
    - |
      case "$REPO_TYPE" in
        gitops-full)
          export TEST_FEATURES="gitlab_ci,helm,k8s,terraform,ansible"
          ;;
        gitlab-ci-only)
          export TEST_FEATURES="gitlab_ci"
          ;;
        helm-only)
          export TEST_FEATURES="helm"
          ;;
        k8s-only)
          export TEST_FEATURES="k8s"
          ;;
        plain-python)
          export TEST_FEATURES=""
          ;;
      esac

    - uv run pytest tests/e2e/test_bootstrap_gitops.py::TestBootstrapGitOps::test_bootstrap_${REPO_TYPE}_repo -v

  artifacts:
    when: always
    reports:
      junit: pytest-results.xml
```

---

## 7. Documentation for Users

### 7.1 Quick Start Guide

**File**: `docs/installation/binary-gitops-quickstart.md`

```markdown
# Binary Installation Quick Start for GitOps Repositories

## Installation

### Option 1: Download Binary

\`\`\`bash
# Linux
wget https://github.com/yourusername/huskycat/releases/latest/download/huskycat-linux -O ~/.local/bin/huskycat
chmod +x ~/.local/bin/huskycat

# macOS
wget https://github.com/yourusername/huskycat/releases/latest/download/huskycat-macos -O ~/.local/bin/huskycat
chmod +x ~/.local/bin/huskycat

# Add to PATH (if not already)
export PATH="$HOME/.local/bin:$PATH"
\`\`\`

### Option 2: From Package Manager (future)

\`\`\`bash
# Ubuntu/Debian (future)
apt install huskycat

# Fedora/RHEL (future)
dnf install huskycat

# macOS Homebrew (future)
brew install huskycat
\`\`\`

## Bootstrap GitOps Repository

Navigate to your GitOps repository and run:

\`\`\`bash
huskycat bootstrap
\`\`\`

**What this does:**
1. Detects your repository type (GitLab CI, Helm, K8s, Terraform, Ansible)
2. Installs 3 git hooks (pre-commit, pre-push, commit-msg)
3. Configures automatic validation based on detected features
4. Reports what features were enabled

**Expected output:**

\`\`\`
 Bootstrapping HuskyCat...

Repository analysis:
  ✓ GitLab CI detected
  ✓ Helm chart detected
  ✓ Kubernetes manifests detected
   GitOps repository - enabling IaC validation!

Installing git hooks:
  ✓ pre-commit installed
  ✓ pre-push installed
  ✓ commit-msg installed

 Bootstrap complete!
HuskyCat is now configured for:
  ✓ Python code validation (pre-commit)
  ✓ GitLab CI validation (pre-push)
  ✓ Auto-DevOps validation (pre-push)
  ✓ Helm chart linting (pre-push)
  ✓ Kubernetes manifest validation (pre-push)
  ✓ Conventional commit format (commit-msg)

Try making a commit to see validation in action!
\`\`\`

## What Gets Validated

### Pre-Commit (Fast)
- Python code formatting (Black)
- Python linting (Ruff)
- Python type checking (MyPy)
- YAML syntax

### Pre-Push (Comprehensive)
- GitLab CI schema validation
- Helm chart linting
- Kubernetes manifest validation
- Terraform fmt check
- Ansible playbook syntax

### Commit-Msg
- Conventional commit format: `type(scope): subject`
- Valid types: feat, fix, docs, style, refactor, test, chore

## Updating HuskyCat

When you update the binary, hooks will auto-regenerate on next commit:

\`\`\`bash
# Download new version
wget https://github.com/yourusername/huskycat/releases/latest/download/huskycat-linux -O ~/.local/bin/huskycat
chmod +x ~/.local/bin/huskycat

# Hooks will auto-update on next commit, or manually:
huskycat setup-hooks --force
\`\`\`

## Troubleshooting

### Hooks Not Running

\`\`\`bash
# Check hook installation
ls -la .git/hooks/

# Reinstall hooks
huskycat setup-hooks --force

# Check binary is in PATH
which huskycat
\`\`\`

### Bypass Hooks (Emergency)

\`\`\`bash
# Skip pre-commit and commit-msg
git commit --no-verify -m "message"

# Skip pre-push
git push --no-verify
\`\`\`

### View Validation Status

\`\`\`bash
# Check HuskyCat configuration
huskycat status

# Test validation without committing
huskycat validate --all
\`\`\`
\`\`\`

---

## 8. Implementation Checklist

### Phase 1.5: Testing Infrastructure (Current)

- [x] Test repository factory (`TestRepoFactory`)
- [x] E2E test cases for bootstrap
- [x] GitLab CI job for bootstrap testing
- [x] Container-based test environment
- [ ] Test matrix for repository types
- [ ] Coverage reporting integration
- [ ] Performance benchmarks for hook execution

### Phase 2: Fast Mode Implementation

- [ ] Add `fast_mode` parameter to `auto-devops.py`
- [ ] Skip `helm template` in fast mode
- [ ] Skip `kubectl --dry-run` in fast mode
- [ ] Add `--fast` flag to CLI
- [ ] Update hook templates to use `--fast`
- [ ] Test fast mode execution time (<2s target)

### Phase 3: Documentation

- [ ] Quick start guide for binary installation
- [ ] GitOps repository setup guide
- [ ] Troubleshooting guide
- [ ] GitLab CI integration examples
- [ ] Hook customization guide
- [ ] Binary update procedure

---

## 9. Success Criteria

This testing strategy is successful when:

1. **E2E Tests Pass**: All 10 E2E scenarios pass in CI
2. **Coverage Achieved**: >85% coverage on hook generation code
3. **CI Examples Work**: Users can copy-paste GitLab CI examples
4. **Bootstrap Time**: <5 seconds for full GitOps bootstrap
5. **Hook Execution**: <2 seconds for pre-commit, <5 seconds for pre-push (fast mode)
6. **Auto-Update Works**: Binary updates automatically regenerate hooks
7. **Documentation Complete**: Users can bootstrap without reading code

---

## 10. Future Enhancements

- **GitHub Actions examples** (currently GitLab-focused)
- **Windows binary testing** (WSL + native)
- **Pre-commit framework integration** (as alternative to binary hooks)
- **Hook performance profiling** (identify slow validation steps)
- **Remote config validation** (validate production Helm values)
- **Dry-run mode** (show what would be validated without executing)
