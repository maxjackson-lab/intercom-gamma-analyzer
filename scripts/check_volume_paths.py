#!/usr/bin/env python3
"""
Ensure volume paths (/mnt/persistent, /app/outputs) are accessed only through approved helpers.

Direct string references to these paths caused past incidents where code bypassed
the centralized OutputManager/ExecutionStateManager logic and broke on Railway.
This check scans all source files (Python + Dockerfile) and fails if any
non-allowlisted file hardcodes those paths.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PATTERNS = ("/mnt/persistent", "/app/outputs")

# Files that are allowed to reference the raw paths because they implement the helpers.
ALLOWLIST = {
    Path("Dockerfile"),
    Path("deploy/railway_web.py"),
    Path("deploy/web/routes_execution.py"),
    Path("scripts/railway_mcp_helper.py"),
    Path("scripts/check_volume_paths.py"),  # self-reference for patterns
    Path("scripts/run_all_checks.sh"),
    Path("src/services/execution_state_manager.py"),
    Path("src/services/execution_monitor.py"),
    Path("src/utils/output_manager.py"),
}

CODE_SUFFIXES = {".py", ".sh", ".ts", ".tsx"}


def is_code_file(path: Path) -> bool:
    if path.name == "Dockerfile":
        return True
    return path.suffix in CODE_SUFFIXES


def main() -> int:
    violations: list[str] = []

    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel_path = path.relative_to(PROJECT_ROOT)
        if rel_path.parts and rel_path.parts[0].startswith("."):  # skip hidden dirs like .git
            continue
        if not is_code_file(rel_path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern in text for pattern in PATTERNS) and rel_path not in ALLOWLIST:
            for pattern in PATTERNS:
                if pattern in text:
                    violations.append(f"{rel_path}: references {pattern}")

    if violations:
        print("❌ Volume path enforcement failed:\n")
        for entry in sorted(set(violations)):
            print(f" - {entry}")
        print(
            "\nUse src.utils.output_manager or ExecutionStateManager to access "
            "/app/outputs and conditionally mount /mnt/persistent."
        )
        return 1

    print("✅ Volume path enforcement check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

