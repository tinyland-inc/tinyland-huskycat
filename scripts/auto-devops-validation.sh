#!/bin/bash
#
# Auto DevOps Validation Script
#
# This script validates Auto DevOps configurations including:
# - Kubernetes manifests (k8s/, kubernetes/, manifests/)
# - Helm charts and values (.helm/, values*.yaml)
# - Docker/Container configurations
# - GitLab CI Auto DevOps patterns
#
# Environment variables:
#   CI_PROJECT_PATH_SLUG - Project slug for resource naming
#   KUBE_NAMESPACE - Target Kubernetes namespace
#   CI_ENVIRONMENT_SLUG - Environment slug
#   GITLAB_USER_EMAIL - User email for validation context
#
# Exit codes:
#   0: Validation passed
#   1: Validation failed (warnings only)
#   2: Critical validation errors

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  INFO:${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}⚠️  WARN:${NC} $1" >&2
}

log_error() {
    echo -e "${RED}❌ ERROR:${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}✅ SUCCESS:${NC} $1" >&2
}

# Validation counters
WARNINGS=0
ERRORS=0

# Environment defaults
CI_PROJECT_PATH_SLUG="${CI_PROJECT_PATH_SLUG:-$(basename "$PROJECT_ROOT" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g')}"
KUBE_NAMESPACE="${KUBE_NAMESPACE:-default}"
CI_ENVIRONMENT_SLUG="${CI_ENVIRONMENT_SLUG:-production}"

log_info "Starting Auto DevOps validation for project: $CI_PROJECT_PATH_SLUG"
log_info "Target namespace: $KUBE_NAMESPACE"

# Function to validate YAML syntax
validate_yaml_syntax() {
    local file="$1"
    local context="${2:-}"
    
    if ! command -v python3 &>/dev/null; then
        log_warn "Python3 not available, skipping YAML syntax validation for $file"
        return 0
    fi
    
    if ! python3 -c "
import yaml
import sys
try:
    with open('$file', 'r') as f:
        yaml.safe_load(f)
    print('✓ YAML syntax valid: $file')
except yaml.YAMLError as e:
    print(f'✗ YAML syntax error in $file: {e}')
    sys.exit(1)
except Exception as e:
    print(f'✗ Error reading $file: {e}')
    sys.exit(1)
" 2>/dev/null; then
        log_error "YAML syntax validation failed for $file${context:+ ($context)}"
        ((ERRORS++))
        return 1
    fi
    
    return 0
}

# Function to validate Kubernetes manifests
validate_kubernetes_manifests() {
    local manifest_dirs=("k8s" "kubernetes" "manifests")
    local found_manifests=false
    
    log_info "Validating Kubernetes manifests..."
    
    for dir in "${manifest_dirs[@]}"; do
        if [[ -d "$PROJECT_ROOT/$dir" ]]; then
            found_manifests=true
            log_info "Found Kubernetes manifests in: $dir/"
            
            while IFS= read -r -d '' file; do
                log_info "Validating K8s manifest: $file"
                validate_yaml_syntax "$file" "Kubernetes manifest"
                
                # Basic Kubernetes resource validation
                if ! grep -q "apiVersion:" "$file"; then
                    log_error "Missing apiVersion in Kubernetes manifest: $file"
                    ((ERRORS++))
                fi
                
                if ! grep -q "kind:" "$file"; then
                    log_error "Missing kind in Kubernetes manifest: $file"
                    ((ERRORS++))
                fi
                
                if ! grep -q "metadata:" "$file"; then
                    log_error "Missing metadata in Kubernetes manifest: $file"
                    ((ERRORS++))
                fi
                
                # Check for hardcoded namespaces
                if grep -q "namespace:" "$file" && ! grep -q "namespace: $KUBE_NAMESPACE" "$file"; then
                    log_warn "Hardcoded namespace found in $file, should use: $KUBE_NAMESPACE"
                    ((WARNINGS++))
                fi
                
                # Check for resource naming conventions
                if grep -q "name:" "$file"; then
                    if ! grep -qE "name: .*$CI_PROJECT_PATH_SLUG" "$file"; then
                        log_warn "Resource names should include project slug ($CI_PROJECT_PATH_SLUG) in $file"
                        ((WARNINGS++))
                    fi
                fi
                
            done < <(find "$PROJECT_ROOT/$dir" \( -name "*.yml" -o -name "*.yaml" \) -print0)
        fi
    done
    
    if [[ "$found_manifests" == false ]]; then
        log_info "No Kubernetes manifest directories found (k8s/, kubernetes/, manifests/)"
    fi
}

# Function to validate Helm charts
validate_helm_charts() {
    local helm_dirs=(".helm" "helm" "chart")
    local found_helm=false
    
    log_info "Validating Helm configurations..."
    
    # Check for Helm chart directories
    for dir in "${helm_dirs[@]}"; do
        if [[ -d "$PROJECT_ROOT/$dir" ]]; then
            found_helm=true
            log_info "Found Helm chart directory: $dir/"
            
            # Validate Chart.yaml
            if [[ -f "$PROJECT_ROOT/$dir/Chart.yaml" ]]; then
                validate_yaml_syntax "$PROJECT_ROOT/$dir/Chart.yaml" "Helm Chart.yaml"
                
                if ! grep -q "name:" "$PROJECT_ROOT/$dir/Chart.yaml"; then
                    log_error "Missing name in Chart.yaml"
                    ((ERRORS++))
                fi
                
                if ! grep -q "version:" "$PROJECT_ROOT/$dir/Chart.yaml"; then
                    log_error "Missing version in Chart.yaml"
                    ((ERRORS++))
                fi
            else
                log_error "Missing Chart.yaml in Helm chart directory: $dir/"
                ((ERRORS++))
            fi
            
            # Validate templates
            if [[ -d "$PROJECT_ROOT/$dir/templates" ]]; then
                while IFS= read -r -d '' template; do
                    log_info "Validating Helm template: $template"
                    # Basic template validation (check for obvious syntax issues)
                    if grep -q "{{" "$template" && ! grep -q "}}" "$template"; then
                        log_error "Unmatched template braces in $template"
                        ((ERRORS++))
                    fi
                done < <(find "$PROJECT_ROOT/$dir/templates" \( -name "*.yml" -o -name "*.yaml" \) -print0)
            fi
        fi
    done
    
    # Check for values files in project root
    while IFS= read -r -d '' values_file; do
        found_helm=true
        log_info "Validating Helm values file: $values_file"
        validate_yaml_syntax "$values_file" "Helm values"
        
        # Check for common Auto DevOps values
        if [[ "$(basename "$values_file")" == "values.yaml" ]]; then
            if ! grep -q "replicaCount:" "$values_file" && ! grep -q "image:" "$values_file"; then
                log_warn "Standard Helm values not found in $values_file (consider adding replicaCount, image)"
                ((WARNINGS++))
            fi
        fi
        
    done < <(find "$PROJECT_ROOT" -maxdepth 1 -name "values*.yaml" -print0)
    
    if [[ "$found_helm" == false ]]; then
        log_info "No Helm chart configurations found"
    fi
}

# Function to validate Auto DevOps GitLab CI patterns
validate_auto_devops_patterns() {
    log_info "Validating Auto DevOps GitLab CI patterns..."
    
    if [[ -f "$PROJECT_ROOT/.gitlab-ci.yml" ]]; then
        local gitlab_ci="$PROJECT_ROOT/.gitlab-ci.yml"
        
        # Check for Auto DevOps template inclusion
        if grep -q "Auto-DevOps.gitlab-ci.yml" "$gitlab_ci"; then
            log_info "Auto DevOps template detected in .gitlab-ci.yml"
            
            # Check for required variables
            local required_vars=("POSTGRES_ENABLED" "POSTGRES_VERSION" "POSTGRES_DB" "POSTGRES_USER")
            for var in "${required_vars[@]}"; do
                if grep -q "$var:" "$gitlab_ci"; then
                    log_info "Found Auto DevOps variable: $var"
                fi
            done
        fi
        
        # Check for custom deployment stages
        if grep -q "stage: deploy" "$gitlab_ci"; then
            log_info "Custom deployment stage detected"
            
            # Validate environment configurations
            if grep -q "environment:" "$gitlab_ci"; then
                if ! grep -q "name:" "$gitlab_ci"; then
                    log_warn "Environment configuration should include name field"
                    ((WARNINGS++))
                fi
                
                if ! grep -q "url:" "$gitlab_ci"; then
                    log_warn "Environment configuration should include url field"
                    ((WARNINGS++))
                fi
            fi
        fi
        
        # Check for review app configurations
        if grep -q "review:" "$gitlab_ci"; then
            log_info "Review app configuration detected"
            
            if ! grep -q "on_stop:" "$gitlab_ci"; then
                log_warn "Review apps should include on_stop action for cleanup"
                ((WARNINGS++))
            fi
        fi
    fi
}

# Function to validate Docker configurations
validate_docker_configs() {
    log_info "Validating Docker configurations..."
    
    local docker_files=("Dockerfile" "ContainerFile" ".dockerignore")
    
    for file in "${docker_files[@]}"; do
        if [[ -f "$PROJECT_ROOT/$file" ]]; then
            log_info "Found Docker configuration: $file"
            
            if [[ "$file" =~ ^(Dockerfile|ContainerFile)$ ]]; then
                # Basic Dockerfile validation
                if ! grep -q "FROM" "$PROJECT_ROOT/$file"; then
                    log_error "Missing FROM instruction in $file"
                    ((ERRORS++))
                fi
                
                # Security checks
                if grep -q "ADD http" "$PROJECT_ROOT/$file"; then
                    log_warn "Consider using COPY instead of ADD for HTTP URLs in $file"
                    ((WARNINGS++))
                fi
                
                if grep -q "RUN.*sudo" "$PROJECT_ROOT/$file"; then
                    log_warn "Avoid using sudo in Docker containers: $file"
                    ((WARNINGS++))
                fi
                
                if ! grep -q "USER" "$PROJECT_ROOT/$file"; then
                    log_warn "Consider adding non-root USER instruction in $file"
                    ((WARNINGS++))
                fi
            fi
        fi
    done
}

# Function to validate environment-specific configurations
validate_environment_configs() {
    log_info "Validating environment-specific configurations..."
    
    # Check for environment-specific values files
    local env_patterns=("values-*.yaml" "*-values.yaml" "values.*.yaml")
    
    for pattern in "${env_patterns[@]}"; do
        while IFS= read -r -d '' env_file; do
            log_info "Found environment values file: $env_file"
            validate_yaml_syntax "$env_file" "Environment values"
            
            # Check for environment-specific configurations
            if grep -q "ingress:" "$env_file"; then
                if ! grep -q "host:" "$env_file"; then
                    log_warn "Ingress configuration should include host field in $env_file"
                    ((WARNINGS++))
                fi
            fi
            
        done < <(find "$PROJECT_ROOT" -name "$pattern" -print0 2>/dev/null || true)
    done
}

# Function to validate security configurations
validate_security_configs() {
    log_info "Validating security configurations..."
    
    # Check for common security misconfigurations
    local sensitive_files=(".env" ".env.local" ".env.production" "secrets.yaml" "secret.yaml")
    
    for file in "${sensitive_files[@]}"; do
        if [[ -f "$PROJECT_ROOT/$file" ]]; then
            log_error "Sensitive file should not be in version control: $file"
            ((ERRORS++))
        fi
    done
    
    # Check for hardcoded secrets in YAML files
    while IFS= read -r -d '' yaml_file; do
        if grep -qiE "(password|secret|token|key):\s*[\"']?[^\"'\s]{8,}" "$yaml_file"; then
            log_warn "Potential hardcoded secrets found in $yaml_file"
            ((WARNINGS++))
        fi
    done < <(find "$PROJECT_ROOT" \( -name "*.yml" -o -name "*.yaml" \) -print0 2>/dev/null || true)
}

# Main validation function
main() {
    log_info "Auto DevOps validation started"
    
    # Run all validation checks
    validate_kubernetes_manifests
    validate_helm_charts
    validate_auto_devops_patterns
    validate_docker_configs
    validate_environment_configs
    validate_security_configs
    
    # Report results
    echo
    log_info "Auto DevOps validation completed"
    echo "Results:"
    echo "  Errors: $ERRORS"
    echo "  Warnings: $WARNINGS"
    
    if [[ $ERRORS -gt 0 ]]; then
        log_error "Validation failed with $ERRORS errors"
        return 2
    elif [[ $WARNINGS -gt 0 ]]; then
        log_warn "Validation completed with $WARNINGS warnings"
        return 1
    else
        log_success "All validations passed!"
        return 0
    fi
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi