#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# FPM pre-remove script for Linux packages (RPM/DEB)
# Runs before package removal

echo "Preparing to remove HuskyCat..."

# Note: We don't remove ~/.huskycat as it contains user configuration
# Users can manually remove it if desired

echo "Configuration at ~/.huskycat will be preserved."
echo "Remove manually if not needed: rm -rf ~/.huskycat"

exit 0
