"""Configuration: API key storage, Chromium install, playwright driver path resolution."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

console = Console()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def _config_dir() -> Path:
    """Return the platform-appropriate config directory."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
    else:
        base = os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
    path = Path(base) / "auto-playwright"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _config_file() -> Path:
    return _config_dir() / "config.json"


def _load_config() -> dict:
    f = _config_file()
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_config(data: dict) -> None:
    _config_file().write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Playwright driver resolution
# ---------------------------------------------------------------------------

def _get_playwright_exe() -> tuple[Path, Path]:
    """Return (node_exe, cli_js) for the bundled playwright driver.

    Works both in development (site-packages) and when frozen by PyInstaller
    (sys._MEIPASS).
    """
    if getattr(sys, "frozen", False):
        # Frozen: PyInstaller extracts everything to sys._MEIPASS
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        import playwright as _pw
        # site-packages/playwright/__init__.py → site-packages/
        base = Path(_pw.__file__).parent.parent

    if sys.platform == "win32":
        node_name = "node.exe"
    else:
        node_name = "node"

    node_exe = base / "playwright" / "driver" / node_name
    cli_js = base / "playwright" / "driver" / "package" / "cli.js"

    if not node_exe.exists():
        raise FileNotFoundError(
            f"Playwright node executable not found at: {node_exe}\n"
            "Try reinstalling playwright: pip install playwright==1.44.0"
        )
    if not cli_js.exists():
        raise FileNotFoundError(
            f"Playwright CLI not found at: {cli_js}\n"
            "Try reinstalling playwright: pip install playwright==1.44.0"
        )

    return node_exe, cli_js


# ---------------------------------------------------------------------------
# Chromium installation
# ---------------------------------------------------------------------------

def ensure_chromium_installed() -> None:
    """Check for Chromium; download (~130 MB) on first run."""
    node_exe, cli_js = _get_playwright_exe()

    # Quick check: does the chromium marker exist?
    if sys.platform == "win32":
        ms_playwright = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"
    else:
        ms_playwright = Path.home() / ".cache" / "ms-playwright"

    chromium_dirs = list(ms_playwright.glob("chromium-*")) if ms_playwright.exists() else []

    if chromium_dirs:
        return  # Already installed

    console.print(
        "[yellow]Chromium not found. Downloading (~130 MB) — this happens only once...[/yellow]"
    )
    result = subprocess.run(
        [str(node_exe), str(cli_js), "install", "chromium"],
        check=False,
    )
    if result.returncode != 0:
        console.print(
            "[red]Failed to install Chromium. "
            "You can try manually: playwright install chromium[/red]"
        )
        sys.exit(1)
    console.print("[green]Chromium installed successfully.[/green]")


# ---------------------------------------------------------------------------
# API key management
# ---------------------------------------------------------------------------

def ensure_api_key(reset: bool = False) -> str:
    """Return Anthropic API key; prompt and persist if not yet stored."""
    config = _load_config()

    if reset:
        config.pop("api_key", None)
        _save_config(config)
        console.print("[yellow]API key cleared.[/yellow]")

    # Check environment variable first
    env_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if env_key:
        return env_key

    # Check stored config
    stored = config.get("api_key", "")
    if stored:
        return stored

    # Prompt user
    console.print(
        "\n[bold]Anthropic API key required.[/bold] "
        "Get one at https://console.anthropic.com/\n"
    )
    api_key = Prompt.ask("Enter your Anthropic API key", password=True).strip()
    if not api_key:
        console.print("[red]No API key provided. Exiting.[/red]")
        sys.exit(1)

    config["api_key"] = api_key
    _save_config(config)
    console.print(f"[green]API key saved to {_config_file()}[/green]\n")
    return api_key
