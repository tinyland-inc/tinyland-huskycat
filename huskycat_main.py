#!/usr/bin/env python3
"""
HuskyCat - Universal Code Validation Platform
Main entry point for PyInstaller binary
"""

import sys
from pathlib import Path

# Add the src directory to Python path for imports
if hasattr(sys, "_MEIPASS"):
    # Running from PyInstaller bundle
    base_path = Path(sys._MEIPASS)
    src_path = base_path / "src"
else:
    # Running from source
    base_path = Path(__file__).parent
    src_path = base_path / "src"

sys.path.insert(0, str(src_path))

# Import and run main
from src.huskycat.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
