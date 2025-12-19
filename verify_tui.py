#!/usr/bin/env python3
"""
Verification script for TUI framework implementation.

Checks that all required components are in place and functional.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def check_imports():
    """Verify all TUI components can be imported."""
    print("Checking imports...")
    try:
        from huskycat.core.tui import (
            ToolState,
            ToolStatus,
            ValidationTUI,
            create_simple_spinner,
            is_tty_available,
            validation_tui,
        )
        print("  ✓ All imports successful")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False


def check_interface():
    """Verify interface matches requirements."""
    print("\nChecking interface...")
    try:
        from huskycat.core.tui import ToolState, ToolStatus, ValidationTUI

        # Check ToolState enum
        required_states = ["PENDING", "RUNNING", "SUCCESS", "FAILED"]
        for state in required_states:
            assert hasattr(ToolState, state), f"Missing state: {state}"

        # Check ToolStatus dataclass
        tool = ToolStatus(name="test")
        required_fields = ["name", "state", "duration", "errors", "warnings"]
        for field in required_fields:
            assert hasattr(tool, field), f"Missing field: {field}"

        # Check ValidationTUI class
        tui = ValidationTUI()
        required_methods = ["start", "update_tool", "render", "stop"]
        for method in required_methods:
            assert hasattr(tui, method), f"Missing method: {method}"

        print("  ✓ Interface matches requirements")
        return True
    except (AssertionError, Exception) as e:
        print(f"  ✗ Interface check failed: {e}")
        return False


def check_tests():
    """Verify tests exist and pass."""
    print("\nChecking tests...")
    import subprocess

    result = subprocess.run(
        ["uv", "run", "pytest", "tests/test_tui.py", "-v", "--tb=short"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        # Count passed tests
        passed = result.stdout.count("PASSED")
        print(f"  ✓ All {passed} tests passing")
        return True
    else:
        print(f"  ✗ Tests failed")
        print(result.stdout)
        return False


def check_documentation():
    """Verify documentation exists."""
    print("\nChecking documentation...")
    docs_dir = Path(__file__).parent / "docs"

    required_docs = [
        "TUI_INTEGRATION.md",
    ]

    all_exist = True
    for doc in required_docs:
        doc_path = docs_dir / doc
        if doc_path.exists():
            size = doc_path.stat().st_size
            print(f"  ✓ {doc} ({size:,} bytes)")
        else:
            print(f"  ✗ {doc} missing")
            all_exist = False

    return all_exist


def check_examples():
    """Verify example scripts exist."""
    print("\nChecking examples...")
    examples_dir = Path(__file__).parent / "examples"

    required_examples = [
        "demo_tui.py",
        "tui_with_process_manager.py",
    ]

    all_exist = True
    for example in required_examples:
        example_path = examples_dir / example
        if example_path.exists():
            size = example_path.stat().st_size
            executable = example_path.stat().st_mode & 0o111
            exec_str = "executable" if executable else "not executable"
            print(f"  ✓ {example} ({size:,} bytes, {exec_str})")
        else:
            print(f"  ✗ {example} missing")
            all_exist = False

    return all_exist


def check_features():
    """Verify key features work."""
    print("\nChecking features...")
    try:
        from huskycat.core.tui import ToolState, ToolStatus, ValidationTUI

        # Test tool status lifecycle
        tool = ToolStatus(name="test")
        tool.start()
        assert tool.state == ToolState.RUNNING
        tool.complete(success=True, errors=0, warnings=1)
        assert tool.state == ToolState.SUCCESS
        assert tool.warnings == 1
        print("  ✓ Tool status lifecycle")

        # Test TUI initialization
        tui = ValidationTUI()
        tui.start(["black", "mypy"])
        # Can't test full functionality without TTY, but verify no exceptions
        print("  ✓ TUI initialization")

        # Test graceful degradation
        from unittest.mock import patch

        with patch("sys.stdout.isatty", return_value=False):
            tui2 = ValidationTUI()
            tui2.start(["test"])
            tui2.update_tool("test", ToolState.SUCCESS)
            tui2.stop()
        print("  ✓ Graceful degradation (non-TTY)")

        # Test thread safety
        import threading

        threads = []
        for i in range(5):
            t = threading.Thread(
                target=lambda: tui.update_tool("black", ToolState.RUNNING)
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()
        print("  ✓ Thread-safe updates")

        tui.stop()

        return True
    except Exception as e:
        print(f"  ✗ Feature check failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all verification checks."""
    print("=" * 70)
    print("TUI Framework Verification")
    print("=" * 70)

    checks = [
        ("Imports", check_imports),
        ("Interface", check_interface),
        ("Tests", check_tests),
        ("Documentation", check_documentation),
        ("Examples", check_examples),
        ("Features", check_features),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} check raised exception: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {name}")

    print("\n" + "=" * 70)
    if passed == total:
        print(f"All {total} checks passed!")
        print("=" * 70)
        print("\nTUI framework is fully implemented and ready for use.")
        return 0
    else:
        print(f"{passed}/{total} checks passed")
        print("=" * 70)
        print(f"\n{total - passed} check(s) failed. See output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
