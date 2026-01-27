#!/usr/bin/env bash
# HuskyCat Beta Download Script
# Downloads binaries from GitLab Package Registry using deploy token
#
# Usage:
#   HUSKYCAT_TOKEN=<deploy-token> ./download-beta.sh [version]
#
# Examples:
#   HUSKYCAT_TOKEN=gldt-xxx ./download-beta.sh          # Latest main build
#   HUSKYCAT_TOKEN=gldt-xxx ./download-beta.sh v2.0.0   # Specific version

set -euo pipefail

# Configuration
PROJECT_ID="tinyland%2Fai%2Fhuskycat"  # URL-encoded project path
GITLAB_API="https://gitlab.com/api/v4"
PACKAGE_NAME="huskycat"

# Check for deploy token
if [ -z "${HUSKYCAT_TOKEN:-}" ]; then
    echo "Error: HUSKYCAT_TOKEN environment variable required"
    echo ""
    echo "Usage: HUSKYCAT_TOKEN=<deploy-token> $0 [version]"
    echo ""
    echo "Get your deploy token from the HuskyCat beta program."
    exit 1
fi

# Version (default to latest)
VERSION="${1:-latest}"

# Detect platform
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

case "${OS}" in
    linux)
        BINARY="huskycat-linux-amd64"
        ;;
    darwin)
        BINARY="huskycat-darwin-arm64"
        ;;
    *)
        echo "Error: Unsupported platform: ${OS}"
        exit 1
        ;;
esac

echo "HuskyCat Beta Installer"
echo "======================="
echo "Platform: ${OS}/${ARCH}"
echo "Binary:   ${BINARY}"
echo "Version:  ${VERSION}"
echo ""

# If version is "latest", find the latest package version
if [ "${VERSION}" = "latest" ]; then
    echo "Finding latest version..."
    VERSION=$(curl -sf --header "DEPLOY-TOKEN: ${HUSKYCAT_TOKEN}" \
        "${GITLAB_API}/projects/${PROJECT_ID}/packages?package_name=${PACKAGE_NAME}&order_by=created_at&sort=desc" \
        | grep -o '"version":"[^"]*"' | head -1 | cut -d'"' -f4)

    if [ -z "${VERSION}" ]; then
        echo "Error: Could not find any packages. Check your token or try a specific version."
        exit 1
    fi
    echo "Latest version: ${VERSION}"
fi

# Download URL
DOWNLOAD_URL="${GITLAB_API}/projects/${PROJECT_ID}/packages/generic/${PACKAGE_NAME}/${VERSION}/${BINARY}"

echo ""
echo "Downloading ${BINARY} v${VERSION}..."

# Download binary
if curl -fL --header "DEPLOY-TOKEN: ${HUSKYCAT_TOKEN}" \
    -o "${BINARY}" \
    "${DOWNLOAD_URL}"; then
    chmod +x "${BINARY}"
    echo ""
    echo "Downloaded: ${BINARY}"
    echo ""

    # Verify
    ./"${BINARY}" --version || true

    echo ""
    echo "Installation options:"
    echo "  1. Move to PATH:     sudo mv ${BINARY} /usr/local/bin/huskycat"
    echo "  2. Self-install:     ./${BINARY} install"
    echo ""
    echo "Then run: huskycat setup-hooks"
else
    echo ""
    echo "Error: Download failed"
    echo "Check your deploy token and version."
    exit 1
fi
