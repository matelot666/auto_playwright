# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for auto-playwright
# Build with: python build.py  (or: pyinstaller auto_playwright.spec)

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files

# ---------------------------------------------------------------------------
# Data collections
# ---------------------------------------------------------------------------

# playwright: includes driver/node.exe, driver/package/cli.js, and all browser
# launcher scripts needed at runtime.
pw_datas, pw_binaries, pw_hiddenimports = collect_all("playwright")

# anthropic: includes CA certs, JSON schemas, and other data files the SDK needs.
anthropic_datas = collect_data_files("anthropic")

# certifi: prevents SSL verification errors when the anthropic SDK makes HTTPS calls.
import certifi
certifi_datas = [(certifi.where(), "certifi")]

# rich: _unicode_data submodule has version-named files PyInstaller misses without this.
rich_datas, rich_binaries, rich_hiddenimports = collect_all("rich")

# httpx / httpcore are used by the anthropic SDK; collect their data too.
try:
    httpx_datas = collect_data_files("httpx")
except Exception:
    httpx_datas = []

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

a = Analysis(
    ["src/main.py"],
    pathex=["src"],
    binaries=pw_binaries + rich_binaries,
    datas=(
        pw_datas
        + anthropic_datas
        + certifi_datas
        + httpx_datas
        + rich_datas
    ),
    hiddenimports=pw_hiddenimports + rich_hiddenimports + [
        "anthropic",
        "anthropic._models",
        "anthropic.types",
        "anthropic.resources",
        "certifi",
        "httpx",
        "httpcore",
        "click",
        "rich",
        "rich.console",
        "rich.prompt",
        "rich.status",
        "rich.panel",
        "rich.text",
        # src modules
        "config",
        "recorder",
        "enhancer",
        "project_writer",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "PIL",
        "IPython",
        "jupyter",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,          # onedir mode: binaries go into COLLECT
    name="auto-playwright",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,                    # strip=True corrupts Windows PE binaries
    upx=False,                      # UPX triggers Windows Defender false positives
    console=True,                   # keep console window (CLI tool)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="auto-playwright",         # → dist/auto-playwright/
)
