#!/usr/bin/env python3
"""
Verify that all FastAPI web routes use the shared template renderers.

This prevents regressions where deploy/railway_web.py embeds stale HTML directly
inside route handlers (bypassing deploy/web/templates.py). The check enforces:

1. No <html ...> markup is allowed inside deploy/railway_web.py.
2. The / and /files routes must delegate to render_chat_html_v2 / render_files_html.
3. Those template helpers must be imported in deploy/railway_web.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAILWAY_WEB = PROJECT_ROOT / "deploy" / "railway_web.py"


def main() -> int:
    if not RAILWAY_WEB.exists():
        print(f"❌ Expected file not found: {RAILWAY_WEB}")
        return 1

    text = RAILWAY_WEB.read_text()
    lower = text.lower()
    errors: list[str] = []

    # 1. Block inline HTML in the FastAPI entrypoint.
    if "<html" in lower or "<body" in lower:
        errors.append(
            "Inline HTML detected inside deploy/railway_web.py. "
            "All markup must live in deploy/web/templates.py."
        )

    # 2. Ensure template render helpers are imported and referenced.
    required_helpers = {
        "render_chat_html_v2": "root(/)",
        "render_files_html": "/files",
    }
    for helper, route in required_helpers.items():
        if helper not in text:
            errors.append(
                f"{helper} is not referenced in deploy/railway_web.py "
                f"(required for {route} route)."
            )

    # 3. Guard against legacy file reads (e.g., files.html) that bypass templates.
    legacy_markers = ["files.html", "open(static_path"]
    if any(marker in text for marker in legacy_markers):
        errors.append(
            "Legacy file reads detected (files.html/static_path). "
            "Routes must use render_files_html/render_chat_html_v2 instead."
        )

    if errors:
        print("❌ Web template integrity check failed:\n")
        for msg in errors:
            print(f" - {msg}")
        print(
            "\nFix by delegating all HTML rendering to deploy/web/templates.py "
            "and ensuring deploy/railway_web.py only calls those helpers."
        )
        return 1

    print("✅ Web template integrity check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

