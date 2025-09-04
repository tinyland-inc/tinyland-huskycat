#!/usr/bin/env python3
"""
Binary build script for HuskyCat
Handles PyInstaller configuration and builds standalone executable
"""

import sys
from pathlib import Path
import PyInstaller.__main__

def main():
    """Build HuskyCat binary with proper configuration"""
    
    # Get project root
    project_root = Path(__file__).parent
    src_dir = project_root / "src"
    
    # PyInstaller arguments
    args = [
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
    
    print(f"Building HuskyCat binary with args: {args}")
    
    # Run PyInstaller
    PyInstaller.__main__.run(args)
    
    print("✅ Binary build complete!")

if __name__ == "__main__":
    main()