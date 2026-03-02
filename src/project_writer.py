"""Writes the output Playwright project folder."""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console

console = Console()

PLAYWRIGHT_CONFIG = """\
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'html',
  use: {
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
"""


def _package_json(test_name: str) -> str:
    data = {
        "name": test_name,
        "version": "1.0.0",
        "description": f"Playwright test: {test_name}",
        "scripts": {
            "test": "playwright test",
            "test:headed": "playwright test --headed",
            "report": "playwright show-report",
        },
        "devDependencies": {
            "@playwright/test": "^1.44.0",
            "@types/node": "^20.0.0",
        },
    }
    return json.dumps(data, indent=2) + "\n"


def write_project(name: str, content: str, output_dir: Path) -> Path:
    """Write the ready-to-run Playwright project and return its root path.

    Creates:
        <output_dir>/<name>/
            playwright.config.ts
            package.json
            tests/<name>.spec.ts
    """
    project_root = output_dir / name
    tests_dir = project_root / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    (project_root / "playwright.config.ts").write_text(PLAYWRIGHT_CONFIG, encoding="utf-8")
    (project_root / "package.json").write_text(_package_json(name), encoding="utf-8")
    (tests_dir / f"{name}.spec.ts").write_text(content + "\n", encoding="utf-8")

    console.print(f"[green]Project written to:[/green] {project_root.resolve()}")
    return project_root
