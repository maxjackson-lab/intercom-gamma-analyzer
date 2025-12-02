#!/usr/bin/env python3
"""
Scan the codebase for Phase 3 resilience violations:
- Hardcoded semaphores/timeouts
- Missing get_recommended_semaphore usage
- Missing log_stage_metrics checkpoints
- Missing settings entries
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
AGENT_DIR = SRC_DIR / "agents"
SERVICE_DIR = SRC_DIR / "services"
STRATEGY_DIR = SERVICE_DIR / "strategies"
SETTINGS_FILE = SRC_DIR / "config" / "settings.py"
VOC_STRATEGY_FILE = STRATEGY_DIR / "voc_strategy.py"

SEM_REGEX = re.compile(r"asyncio\.Semaphore\(\s*(\d+)\s*\)")
TIMEOUT_REGEX = re.compile(r"timeout\s*=\s*(\d+)")

REQUIRED_SETTINGS = [
    "openai_concurrency",
    "anthropic_concurrency",
    "llm_timeout_default",
    "topic_detection_timeout",
    "output_formatter_timeout",
]


@dataclass
class Violation:
    category: str
    path: Path
    line: int
    snippet: str

    def display(self) -> str:
        rel = self.path.relative_to(PROJECT_ROOT)
        return f"- {rel}:{self.line} → {self.snippet.strip()}"


def iter_python_files(base: Path, exclude: Sequence[str]) -> Iterable[Path]:
    for path in base.rglob("*.py"):
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        if any(ex in rel for ex in exclude):
            continue
        yield path


def find_hardcoded_semaphores(files: Iterable[Path], autofix: bool) -> List[Violation]:
    violations: List[Violation] = []
    for path in files:
        text = path.read_text()
        modified = False
        for match in SEM_REGEX.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            snippet = match.group(0)
            violations.append(Violation("Hardcoded Semaphore", path, line, snippet))

            if (
                autofix
                and "self.llm_semaphore" in snippet
                and "self.llm_semaphore" in text
                and "get_recommended_semaphore" in text
            ):
                # Replace exact assignment where possible
                replacement = "get_recommended_semaphore(self.ai_client)"
                text = text.replace(snippet, replacement, 1)
                modified = True

        if autofix and modified:
            path.write_text(text)

    return violations


def find_hardcoded_timeouts(files: Iterable[Path]) -> List[Violation]:
    violations: List[Violation] = []
    for path in files:
        text = path.read_text()
        for match in TIMEOUT_REGEX.finditer(text):
            snippet = match.group(0)
            if "settings." in snippet:
                continue
            line = text.count("\n", 0, match.start()) + 1
            violations.append(Violation("Hardcoded Timeout", path, line, snippet))
    return violations


def find_missing_semaphore_helpers(agent_files: Iterable[Path]) -> List[Violation]:
    violations: List[Violation] = []
    for path in agent_files:
        text = path.read_text()
        if "llm_semaphore" in text and "get_recommended_semaphore" not in text:
            violations.append(
                Violation(
                    "Missing get_recommended_semaphore",
                    path,
                    1,
                    "llm_semaphore present but helper not imported/used",
                )
            )
    return violations


def find_missing_stage_metrics(strategy_files: Iterable[Path]) -> List[Violation]:
    violations: List[Violation] = []
    for path in strategy_files:
        text = path.read_text()
        if "class" not in text:
            continue
        if "log_stage_metrics" not in text:
            violations.append(
                Violation(
                    "Missing log_stage_metrics",
                    path,
                    1,
                    "strategy must call self.log_stage_metrics() at key stages",
                )
            )
    return violations


def find_missing_settings() -> List[Violation]:
    text = SETTINGS_FILE.read_text()
    missing = [
        setting
        for setting in REQUIRED_SETTINGS
        if setting not in text
    ]
    return [
        Violation("Missing Setting", SETTINGS_FILE, 1, setting)
        for setting in missing
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Phase 3 resilience standards.")
    parser.add_argument(
        "--fix-semaphores",
        action="store_true",
        help="Attempt to auto-replace simple self.llm_semaphore assignments.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print every file scanned.",
    )
    parser.add_argument(
        "--exclude",
        default="",
        help="Comma-separated substrings to exclude (e.g., legacy,experimental).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    excludes = [token.strip() for token in args.exclude.split(",") if token.strip()]

    agent_files = list(iter_python_files(AGENT_DIR, excludes))
    service_files = list(iter_python_files(SERVICE_DIR, excludes))
    strategy_targets: List[Path] = []
    if VOC_STRATEGY_FILE.exists() and VOC_STRATEGY_FILE.is_file():
        strategy_targets.append(VOC_STRATEGY_FILE)

    if args.verbose:
        print("Scanning files:")
        for path in sorted(agent_files + service_files):
            print(f" - {path.relative_to(PROJECT_ROOT)}")
        print()

    print("🔍 Validating Phase 3 Resilience Standards...\n")

    violations: List[Violation] = []
    violations += find_hardcoded_semaphores(agent_files + service_files, args.fix_semaphores)
    violations += find_hardcoded_timeouts(agent_files)
    violations += find_missing_semaphore_helpers(agent_files)
    violations += find_missing_stage_metrics(strategy_targets)
    violations += find_missing_settings()

    if not violations:
        print("✅ No resilience violations detected.\n")
        return 0

    categories = {}
    for violation in violations:
        categories.setdefault(violation.category, []).append(violation)

    print("❌ VIOLATIONS FOUND:\n")
    for category, items in categories.items():
        print(f"{category} ({len(items)}):")
        for item in items:
            print(f"  {item.display()}")
        print()

    total = sum(len(items) for items in categories.values())
    print("📊 SUMMARY:")
    for category, items in categories.items():
        print(f"  - {category}: {len(items)}")
    print(f"  - Total Violations: {total}\n")
    print("Fix the violations above and re-run `python scripts/validate_resilience_standards.py`.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

