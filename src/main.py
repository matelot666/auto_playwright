"""auto-playwright CLI entry point."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Ensure src/ is on sys.path when running directly (not frozen)
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).parent))

from config import ensure_api_key, ensure_chromium_installed
from enhancer import enhance_test
from project_writer import write_project
from recorder import record_test

console = Console()


def _sanitize_name(name: str) -> str:
    """Convert name to a safe directory/file name."""
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9_-]", "-", name)
    name = re.sub(r"-{2,}", "-", name)
    return name.strip("-") or "my-test"


def _default_name_from_url(url: str) -> str:
    """Derive a sensible default test name from a URL."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    host = parsed.hostname or "test"
    # Strip www.
    host = re.sub(r"^www\.", "", host)
    # Use first path segment if it's meaningful
    parts = [p for p in parsed.path.split("/") if p]
    if parts:
        return _sanitize_name(f"{host}-{parts[0]}")
    return _sanitize_name(host)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("url")
@click.option("--name", "-n", default=None, help="Test name (used for folder and file names)")
@click.option(
    "--output",
    "-o",
    default=".",
    type=click.Path(file_okay=False),
    help="Output directory for the generated project (default: current directory)",
)
@click.option("--no-enhance", is_flag=True, default=False, help="Skip Claude enhancement step")
@click.option("--reset-key", is_flag=True, default=False, help="Clear stored Anthropic API key")
def main(url: str, name: str | None, output: str, no_enhance: bool, reset_key: bool) -> None:
    """Record a Playwright test and optionally enhance it with Claude assertions.

    \b
    URL   The starting URL for playwright codegen (e.g. https://example.com)

    \b
    Example:
      auto-playwright https://example.com --name checkout-flow -o ./tests
    """
    console.print(
        Panel(
            Text("auto-playwright", style="bold cyan", justify="center"),
            subtitle="Playwright test recorder + Claude enhancer",
        )
    )

    # --reset-key: clear stored key (may also continue if URL provided)
    if reset_key:
        ensure_api_key(reset=True)
        if not url or url == "__reset__":
            return

    # Resolve test name
    test_name = _sanitize_name(name) if name else _default_name_from_url(url)
    console.print(f"Test name: [bold]{test_name}[/bold]")
    console.print(f"Output dir: [bold]{Path(output).resolve()}[/bold]\n")

    # Step 1: Ensure Chromium is installed
    console.print("[bold]Step 1/4:[/bold] Checking Chromium installation...")
    ensure_chromium_installed()

    # Step 2: Optionally get API key (skip if --no-enhance)
    api_key: str | None = None
    if not no_enhance:
        console.print("[bold]Step 2/4:[/bold] Checking Anthropic API key...")
        api_key = ensure_api_key(reset=False)
    else:
        console.print("[bold]Step 2/4:[/bold] Skipping Claude enhancement (--no-enhance)")

    # Step 3: Record
    console.print("[bold]Step 3/4:[/bold] Recording test...")
    raw_content = record_test(url)

    # Step 4: Enhance
    if no_enhance or api_key is None:
        console.print("[bold]Step 4/4:[/bold] Skipping enhancement — using raw recording.")
        final_content = raw_content
    else:
        console.print("[bold]Step 4/4:[/bold] Enhancing with Claude...")
        final_content = enhance_test(raw_content, api_key)

    # Write output project
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    project_root = write_project(test_name, final_content, output_path)

    # Print next steps
    console.print(
        Panel(
            f"[bold green]Done![/bold green] Next steps:\n\n"
            f"  [cyan]cd {project_root.resolve()}[/cyan]\n"
            f"  [cyan]npm install[/cyan]\n"
            f"  [cyan]npx playwright test[/cyan]\n\n"
            f"[dim](Node.js must be installed on this machine to run the test)[/dim]",
            title="[bold]Success[/bold]",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()
