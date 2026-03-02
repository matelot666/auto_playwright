"""Build helper — validates environment then runs PyInstaller."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def _check(condition: bool, message: str) -> None:
    if not condition:
        print(f"[ERROR] {message}", file=sys.stderr)
        sys.exit(1)


def validate_environment() -> None:
    """Ensure all required tools and packages are available."""
    print("Validating build environment...")

    # Python version
    _check(sys.version_info >= (3, 9), f"Python 3.9+ required, got {sys.version}")
    print(f"  Python {sys.version.split()[0]} OK")

    # PyInstaller
    _check(shutil.which("pyinstaller") is not None, "PyInstaller not found. Run: pip install pyinstaller")
    result = subprocess.run(["pyinstaller", "--version"], capture_output=True, text=True)
    print(f"  PyInstaller {result.stdout.strip()} OK")

    # playwright
    try:
        import playwright  # noqa: F401
        print("  playwright OK")
    except ImportError:
        _check(False, "playwright not installed. Run: pip install playwright==1.44.0")

    # anthropic
    try:
        import anthropic  # noqa: F401
        print("  anthropic OK")
    except ImportError:
        _check(False, "anthropic not installed. Run: pip install anthropic")

    # certifi
    try:
        import certifi  # noqa: F401
        print("  certifi OK")
    except ImportError:
        _check(False, "certifi not installed. Run: pip install certifi")

    # rich
    try:
        import rich  # noqa: F401
        print("  rich OK")
    except ImportError:
        _check(False, "rich not installed. Run: pip install rich")

    # click
    try:
        import click  # noqa: F401
        print("  click OK")
    except ImportError:
        _check(False, "click not installed. Run: pip install click")

    # spec file
    spec = ROOT / "auto_playwright.spec"
    _check(spec.exists(), f"Spec file not found: {spec}")
    print(f"  Spec file {spec.name} OK")

    print()


def build() -> None:
    """Run PyInstaller with the project spec."""
    spec = ROOT / "auto_playwright.spec"

    print("Running PyInstaller...")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(spec), "--clean", "--noconfirm"],
        cwd=ROOT,
    )

    if result.returncode != 0:
        print("\n[ERROR] PyInstaller build failed.", file=sys.stderr)
        sys.exit(1)

    dist_dir = ROOT / "dist" / "auto-playwright"
    print(f"\nBuild succeeded!")
    print(f"Output directory: {dist_dir.resolve()}")

    if sys.platform == "win32":
        exe = dist_dir / "auto-playwright.exe"
        print(f"Executable: {exe.resolve()}")
        print()
        print("To distribute: zip the entire dist/auto-playwright/ folder.")
        print("Users unzip and run auto-playwright.exe — no Python or Node.js required.")
    else:
        exe = dist_dir / "auto-playwright"
        print(f"Executable: {exe.resolve()}")
        print()
        print("Note: This is a macOS/Linux build. For Windows .exe, build on Windows.")

    print()
    print("Quick smoke test:")
    if sys.platform == "win32":
        print(f"  dist\\auto-playwright\\auto-playwright.exe https://example.com --name smoke-test")
    else:
        print(f"  dist/auto-playwright/auto-playwright https://example.com --name smoke-test")


if __name__ == "__main__":
    validate_environment()
    build()
