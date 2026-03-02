"""Records a Playwright test via `playwright codegen` subprocess."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from rich.console import Console

from config import _get_playwright_exe

console = Console()


def record_test(url: str) -> str:
    """Launch playwright codegen for *url* and return the recorded TypeScript.

    Blocks until the user closes the Playwright Inspector / browser window.
    Returns the raw TypeScript source of the recorded test.

    Raises:
        SystemExit: if the recording is empty or codegen fails.
    """
    node_exe, cli_js = _get_playwright_exe()

    with tempfile.NamedTemporaryFile(
        suffix=".spec.ts", delete=False, mode="w", encoding="utf-8"
    ) as tmp:
        tmp_path = Path(tmp.name)

    console.print(
        "\n[bold green]Opening browser for recording...[/bold green]\n"
        "  • Perform your test actions in the browser.\n"
        "  • When finished, [bold]close the browser window[/bold] to continue.\n"
    )

    cmd = [
        str(node_exe),
        str(cli_js),
        "codegen",
        "--target=playwright-test",
        f"--output={tmp_path}",
        url,
    ]

    # IMPORTANT: do NOT use capture_output=True here.
    # playwright codegen is a GUI process; capturing stdout/stderr causes a
    # pipe deadlock that hangs the process indefinitely.
    result = subprocess.run(cmd, check=False)

    if result.returncode != 0:
        console.print(
            f"[red]playwright codegen exited with code {result.returncode}.[/red]"
        )
        _cleanup(tmp_path)
        sys.exit(1)

    if not tmp_path.exists() or tmp_path.stat().st_size == 0:
        console.print(
            "[yellow]No test was recorded (empty output). "
            "Did you close the browser before making any actions?[/yellow]"
        )
        _cleanup(tmp_path)
        sys.exit(0)

    content = tmp_path.read_text(encoding="utf-8").strip()
    _cleanup(tmp_path)

    if not content:
        console.print(
            "[yellow]Recording was empty after reading. Nothing to enhance.[/yellow]"
        )
        sys.exit(0)

    console.print("[green]Recording captured successfully.[/green]\n")
    return content


def _cleanup(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
