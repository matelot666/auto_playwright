"""Sends recorded Playwright test to Claude API to add sensible assertions."""

from __future__ import annotations

import re
import sys

import anthropic
from rich.console import Console
from rich.status import Status

console = Console()

MODEL = "claude-sonnet-4-5-20250929"

SYSTEM_PROMPT = """\
You are an expert Playwright TypeScript test engineer.
Your task is to enhance a raw Playwright test recording by adding sensible assertions.

Rules:
- Preserve ALL existing actions exactly as written (clicks, fills, navigations, etc.)
- Add assertions using ONLY these Playwright matchers:
    expect(page).toHaveURL(...)
    expect(page).toHaveTitle(...)
    expect(locator).toBeVisible()
    expect(locator).toHaveText(...)
    expect(locator).toHaveValue(...)
- Place assertions AFTER the action that triggers the state being asserted
- Use await for all assertions
- Return ONLY valid TypeScript — no explanations, no markdown, no code fences
- Do NOT add comments explaining what you changed
- Do NOT add new imports; the existing imports are sufficient
- Do NOT change test names, describe blocks, or file structure
"""

USER_PROMPT_TEMPLATE = """\
Enhance this Playwright test recording by adding sensible assertions.

Do NOT:
- Add assertions that check implementation details (CSS classes, data-testid values)
- Add more than 2-3 assertions per logical step
- Assert on dynamic content that may change between runs (timestamps, random IDs)
- Wrap the output in code fences (``` or similar)
- Add any text before or after the TypeScript code

Raw recording:
{recording}
"""


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences if Claude wrapped the output anyway."""
    # Remove opening fence: ```typescript, ```ts, ```javascript, or just ```
    text = re.sub(r"^```(?:typescript|ts|javascript|js)?\s*\n", "", text, flags=re.MULTILINE)
    # Remove closing fence
    text = re.sub(r"\n```\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


def _looks_like_typescript(text: str) -> bool:
    """Heuristic: valid output should contain 'test(' or 'import'."""
    return "test(" in text or "import " in text


def enhance_test(content: str, api_key: str) -> str:
    """Send *content* to Claude and return enhanced TypeScript test.

    Falls back to the original *content* if the response looks wrong.
    """
    client = anthropic.Anthropic(api_key=api_key)

    user_prompt = USER_PROMPT_TEMPLATE.format(recording=content)

    with Status("[bold blue]Enhancing test with Claude...[/bold blue]", console=console):
        try:
            message = client.messages.create(
                model=MODEL,
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.AuthenticationError:
            console.print(
                "[red]Invalid Anthropic API key. "
                "Run with --reset-key to enter a new one.[/red]"
            )
            sys.exit(1)
        except anthropic.APIConnectionError as e:
            console.print(f"[red]Connection error contacting Claude API: {e}[/red]")
            sys.exit(1)
        except anthropic.RateLimitError:
            console.print(
                "[red]Claude API rate limit hit. Please wait a moment and try again.[/red]"
            )
            sys.exit(1)
        except anthropic.APIStatusError as e:
            console.print(f"[red]Claude API error ({e.status_code}): {e.message}[/red]")
            sys.exit(1)

    response_text = message.content[0].text if message.content else ""

    # Fallback: strip code fences if Claude included them
    cleaned = _strip_code_fences(response_text)

    if not _looks_like_typescript(cleaned):
        console.print(
            "[yellow]Warning: Claude response did not look like TypeScript. "
            "Using original recording as fallback.[/yellow]"
        )
        return content

    console.print("[green]Test enhanced with assertions.[/green]\n")
    return cleaned
