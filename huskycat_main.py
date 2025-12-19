#!/usr/bin/env python3
"""
HuskyCat - Universal Code Validation Platform
Main entry point for PyInstaller binary
"""

import sys
import os
from pathlib import Path

# PyInstaller frozen mode detection
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    # Running from PyInstaller bundle
    bundle_dir = Path(sys._MEIPASS)
    src_dir = bundle_dir / "src"

    # Verify bundle structure
    if not src_dir.exists():
        print(f"Error: Bundle structure invalid - src not found in {bundle_dir}", file=sys.stderr)
        sys.exit(1)

    sys.path.insert(0, str(src_dir))

    # Set environment marker for frozen mode
    os.environ["HUSKYCAT_FROZEN"] = "1"
else:
    # Running from source
    repo_dir = Path(__file__).parent
    src_dir = repo_dir / "src"

    if not src_dir.exists():
        print(f"Error: Source directory not found: {src_dir}", file=sys.stderr)
        sys.exit(1)

    sys.path.insert(0, str(src_dir))

# Import must be after path setup
from src.huskycat.__main__ import main

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
