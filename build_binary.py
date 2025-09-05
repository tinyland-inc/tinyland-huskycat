#!/usr/bin/env python3
"""
Binary build script for HuskyCat
Handles PyInstaller configuration and builds standalone executable with optional macOS code signing
"""

import sys
import os
import platform
import argparse
from pathlib import Path
import PyInstaller.__main__

def main():
    """Build HuskyCat binary with proper configuration"""
    
    parser = argparse.ArgumentParser(description="Build HuskyCat binary")
    parser.add_argument("--codesign-identity", help="macOS code signing identity")
    parser.add_argument("--entitlements-file", help="macOS entitlements file path") 
    parser.add_argument("--skip-upx", action="store_true", help="Skip UPX compression")
    parser.add_argument("--target-arch", help="Target architecture (auto-detected if not specified)")
    args = parser.parse_args()
    
    # Get project root
    project_root = Path(__file__).parent
    src_dir = project_root / "src"
    
    # Base PyInstaller arguments
    pyinstaller_args = [
        "--onefile",
        "--name=huskycat",
        f"--add-data={src_dir}:src",
        "--hidden-import=huskycat.core.factory",
        "--hidden-import=huskycat.core.base", 
        "--hidden-import=huskycat.commands",
        "--hidden-import=huskycat.unified_validation",
        "--hidden-import=huskycat.gitlab_ci_validator",
        "--hidden-import=huskycat.mcp_server",
        "--console",
        "huskycat_main.py"
    ]
    
    # Add macOS-specific options
    if platform.system() == "Darwin":
        print("🍎 Building for macOS with platform-specific optimizations")
        
        # Add target architecture if specified
        if args.target_arch:
            pyinstaller_args.extend(["--target-arch", args.target_arch])
        
        # Add code signing if identity provided
        if args.codesign_identity:
            print(f"🔐 Code signing with identity: {args.codesign_identity}")
            pyinstaller_args.extend(["--codesign-identity", args.codesign_identity])
            
            # Add entitlements file if provided
            if args.entitlements_file:
                entitlements_path = Path(args.entitlements_file)
                if entitlements_path.exists():
                    print(f"📋 Using entitlements file: {entitlements_path}")
                    pyinstaller_args.extend(["--osx-entitlements-file", str(entitlements_path)])
                else:
                    print(f"⚠️  Entitlements file not found: {entitlements_path}")
        else:
            print("ℹ️  No code signing identity provided - binary will be ad-hoc signed")
    
    print(f"Building HuskyCat binary with args: {pyinstaller_args}")
    
    # Run PyInstaller
    PyInstaller.__main__.run(pyinstaller_args)
    
    # Handle UPX compression
    if not args.skip_upx and platform.system() != "Darwin":
        print("🗜️  Attempting UPX compression...")
        try:
            import subprocess
            result = subprocess.run(
                ["upx", "--best", "--lzma", "dist/huskycat"], 
                capture_output=True, text=True
            )
            if result.returncode == 0:
                print("✅ UPX compression successful")
            else:
                print(f"⚠️  UPX compression failed: {result.stderr}")
        except FileNotFoundError:
            print("⚠️  UPX not found, skipping compression")
    elif platform.system() == "Darwin":
        print("ℹ️  Skipping UPX compression on macOS (can cause signing issues)")
    
    print("✅ Binary build complete!")
    
    # Show binary info
    binary_path = Path("dist/huskycat")
    if binary_path.exists():
        size_mb = binary_path.stat().st_size / (1024 * 1024)
        print(f"📦 Binary size: {size_mb:.1f} MB")
        print(f"📍 Binary location: {binary_path.absolute()}")

if __name__ == "__main__":
    main()