#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# FPM post-install script for Linux packages (RPM/DEB)
# Runs after package installation

set -e

echo "HuskyCat Post-Install Setup"
echo "==========================="

# Ensure binary is executable
if [ -f /usr/local/bin/huskycat ]; then
    chmod +x /usr/local/bin/huskycat
    echo "Binary installed: /usr/local/bin/huskycat"
fi

# Update icon cache (for .desktop file)
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true
fi

# Update desktop database (for .desktop file)
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database /usr/share/applications 2>/dev/null || true
fi

# Display completion message
echo ""
echo "HuskyCat installed successfully!"
echo ""
echo "Quick Start:"
echo "  huskycat status        # Check installation"
echo "  huskycat setup-hooks   # Install git hooks"
echo "  huskycat validate      # Validate current directory"
echo ""

exit 0
