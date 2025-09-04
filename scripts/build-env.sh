#!/bin/bash
# Build HuskyCat in a virtual environment

set -e

echo "🐱 Setting up build environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "build_venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv build_venv
fi

# Activate virtual environment
source build_venv/bin/activate

# Install requirements
echo "📦 Installing build dependencies..."
pip install --upgrade pip
pip install pyinstaller

# Run the build
echo "🔨 Building HuskyCat..."
python3 build.py

echo "✨ Build complete!"
echo ""
echo "Executable location: dist/huskycat"
echo "Lightweight version: dist/huskycat_light"