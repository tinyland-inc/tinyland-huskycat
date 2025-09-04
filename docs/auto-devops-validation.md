# GitLab Auto DevOps Validation

HuskyCats Bates now includes comprehensive GitLab Auto DevOps validation to ensure your CI/CD configurations, Helm charts, and Kubernetes manifests are valid before committing.

## 🚀 Features

- **GitLab CI Validation**: Checks `.gitlab-ci.yml` for Auto DevOps compatibility
- **Helm Chart Validation**: Validates Helm values files and simulates template generation
- **Kubernetes Manifest Validation**: Ensures K8s manifests are syntactically correct
- **Auto Deploy Simulation**: Simulates the Auto DevOps Helm deployment process
- **Pre-commit Integration**: Automatically validates when relevant files are changed

## 📋 Prerequisites

The validation tools are pre-installed in the HuskyCats Bates Docker container:
- Helm 3
- kubectl
- GitLab Auto Deploy Image charts (automatically downloaded)

## 🔧 Usage

### Manual Validation

Run the validation script directly:

```bash
# Basic validation
./scripts/auto-devops-validation.sh

# Verbose output
./scripts/auto-devops-validation.sh --verbose
```

### Via Docker Container

```bash
docker run --rm -v "$(pwd):/workspace" -w /workspace \
  registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest \
  /workspace/scripts/auto-devops-validation.sh
```

### Automatic Pre-commit Validation

The validation runs automatically when you commit changes to:
- `.gitlab-ci.yml`
- `values.yaml` or `values-*.yaml`
- Files in `.helm/`, `k8s/`, `kubernetes/`, or `manifests/` directories

## 📁 File Structure

Auto DevOps validation looks for these files:

```
project/
├── .gitlab-ci.yml          # GitLab CI configuration
├── values.yaml             # Helm values (optional)
├── values-production.yaml  # Environment-specific values (optional)
├── .helm/                  # Helm chart overrides (optional)
│   └── values.yaml
├── k8s/                    # Kubernetes manifests (optional)
│   ├── deployment.yaml
│   └── service.yaml
└── kubernetes/             # Alternative K8s directory (optional)
```

## 🔍 What Gets Validated

### 1. GitLab CI Configuration
- Checks if Auto DevOps template is included
- Validates required variables (`CI_APPLICATION_REPOSITORY`, `CI_APPLICATION_TAG`)
- Suggests improvements for Auto DevOps compatibility

### 2. Helm Values Files
- YAML syntax validation
- Checks for common Auto DevOps values structure
- Validates against Auto Deploy App chart schema

### 3. Kubernetes Manifests
- Validates YAML syntax
- Ensures manifests can be applied (`kubectl apply --dry-run`)
- Checks for required Kubernetes resources

### 4. Auto Deploy Simulation
- Downloads the official GitLab Auto Deploy Image chart
- Simulates `helm template` with your configuration
- Validates the generated Kubernetes manifests

## 🎯 Environment Variables

Configure validation behavior with these environment variables:

```bash
# Auto Deploy Image version (default: v2.48.0)
export AUTO_DEPLOY_IMAGE_VERSION=v2.48.0

# Enable verbose output
export VERBOSE=true

# Common Auto DevOps variables
export CI_APPLICATION_REPOSITORY=registry.gitlab.com/my-group/my-project
export CI_APPLICATION_TAG=latest
export KUBE_NAMESPACE=production
export POSTGRES_ENABLED=false
```

## 📝 Example .gitlab-ci.yml

Here's a minimal Auto DevOps-compatible configuration:

```yaml
variables:
  CI_APPLICATION_REPOSITORY: $CI_REGISTRY_IMAGE
  CI_APPLICATION_TAG: $CI_COMMIT_SHA
  
  # Disable unnecessary features
  TEST_DISABLED: 1
  CODE_QUALITY_DISABLED: 1
  CONTAINER_SCANNING_DISABLED: 1

include:
  - template: Auto-DevOps.gitlab-ci.yml

# Override build stage if needed
build:
  stage: build
  script:
    - docker build -t "$CI_APPLICATION_REPOSITORY:$CI_APPLICATION_TAG" .
    - docker push "$CI_APPLICATION_REPOSITORY:$CI_APPLICATION_TAG"
```

## 🚨 Common Issues

### "Helm template generation failed"
- Ensure your values files have valid YAML syntax
- Check that all referenced secrets and configmaps exist
- Verify image repository and tag variables are set

### "Auto Deploy Image chart not found"
- The script will automatically download the chart on first run
- Ensure you have internet connectivity
- Check `~/.cache/huskycats/auto-deploy-image` directory

### "kubectl not found"
- Run the validation inside the HuskyCats Bates Docker container
- Or install kubectl locally: `curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"`

## 🔗 Integration with Comprehensive Linting

Auto DevOps validation is integrated into the comprehensive linting workflow:

```bash
# Run all linting including Auto DevOps validation
./scripts/comprehensive-lint.sh --all

# Only lint staged files (including Auto DevOps files)
./scripts/comprehensive-lint.sh --staged
```

## 📚 References

- [GitLab Auto DevOps Documentation](https://docs.gitlab.com/ee/topics/autodevops/)
- [Auto Deploy Image Repository](https://gitlab.com/gitlab-org/cluster-integration/auto-deploy-image)
- [Helm Documentation](https://helm.sh/docs/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

## 💡 Tips

1. **Use the Alias**: Add this to your shell profile:
   ```bash
   alias adhd="helm template --debug ~/git/auto-deploy-image/assets/auto-deploy-app"
   ```

2. **Test Locally**: Before committing, test your Helm values:
   ```bash
   helm template my-app ~/.cache/huskycats/auto-deploy-image/assets/auto-deploy-app \
     -f values.yaml \
     --set application.repository=$CI_APPLICATION_REPOSITORY \
     --set application.tag=$CI_APPLICATION_TAG
   ```

3. **Environment-Specific Values**: Use different values files for different environments:
   ```bash
   values.yaml              # Base configuration
   values-staging.yaml      # Staging overrides
   values-production.yaml   # Production overrides
   ```

4. **Custom Kubernetes Resources**: Place additional manifests in `k8s/` directory:
   ```yaml
   # k8s/configmap.yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: my-app-config
   data:
     config.yaml: |
       setting: value
   ```