#!/usr/bin/env bash
# Docker wrapper for lint-staged
# This script runs linting tools through the Docker container

set -euo pipefail

# Check if we're in a Git repository
if [ ! -d .git ]; then
    echo "Error: Not in a Git repository"
    exit 1
fi

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "Warning: Docker not found. Skipping linting."
    exit 0
fi

# Check if the image exists locally
if ! docker images | grep -q "husky-lint.*local"; then
    echo "Warning: husky-lint:local image not found. Skipping linting."
    echo "To build: docker build -t husky-lint:local ."
    exit 0
fi

# Get staged files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

if [ -z "$STAGED_FILES" ]; then
    echo "No staged files to lint"
    exit 0
fi

echo "Running linters on staged files through Docker..."

# Run lint-staged inside the container
docker run --rm \
    -v "$(pwd):/workspace" \
    -w /workspace \
    -e "STAGED_FILES=$STAGED_FILES" \
    husky-lint:local \
    npx lint-staged

echo "Linting complete!"