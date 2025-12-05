#!/usr/bin/env python3
"""
Parse historical production run artifacts to generate baseline telemetry.

Inputs:
- reference_data/voice-of-customer_Last-Week_dec-*/audit_trail_*.md
- reference_data/voice-of-customer_Last-Week_dec-*/voc_topic_based_*.md

Outputs:
- Structured JSON telemetry persisted to outputs/baseline_metrics/production_run_analysis.json
- Console summary for quick inspection

Collected Metrics:
- Phase durations and success flags from audit trails
- Per-topic volume, duplicate ratios, and metric reference counts
- Repetitive phrases detected via n-gram analysis
- Quality warnings (duplicate ratio, low metrics, fallback usage)
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.utils.output_manager import get_output_file_path


logger = logging.getLogger("parse_production_runs")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


DUPLICATE_NGRAM_RANGE = range(3, 6)
RUN_GLOB_PATTERN = "voice-of-customer_Last-Week_dec-*"


@dataclass
class TopicStats:
    name: str
    volume: Optional[int] = None
    percentage: Optional[float] = None
    detection_method: Optional[str] = None
    sentiment: Optional[str] = None
    insight_text: str = ""
    duplicate_ratio: float = 0.0
    duplicate_phrases: List[Tuple[str, int]] = field(default_factory=list)
    metric_references: int = 0
    fallback_flag: bool = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse production run markdown artifacts for telemetry")
    parser.add_argument(
        "--reference-root",
        type=str,
        default="reference_data",
        help="Root directory that contains voice-of-customer_Last-Week_dec-* folders",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(Path("outputs") / "baseline_metrics"),
        help="Directory for storing parsed telemetry JSON",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit of production run folders to parse",
    )
    return parser.parse_args()


def discover_runs(reference_root: Path, limit: Optional[int] = None) -> List[Path]:
    if not reference_root.exists():
        logger.warning("Reference root not found: %s", reference_root)
        return []
    runs = sorted(reference_root.glob(RUN_GLOB_PATTERN))
    if limit:
        runs = runs[:limit]
    return runs


def read_file_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("File missing: %s", path)
    except Exception as exc:
        logger.warning("Failed reading %s: %s", path, exc)
    return ""


def parse_audit_trail(content: str) -> Dict[str, Any]:
    if not content:
        return {}
    total_duration = None
    phase_details: Dict[str, Dict[str, Any]] = {}
    data_quality_flags: List[str] = []
    conversation_counts: Dict[str, int] = {}
    duration_pattern = re.compile(r"Total Duration:\s*([\d\.]+)\s*(seconds|minutes|min)", re.IGNORECASE)
    phase_pattern = re.compile(
        r"Phase\s+([\d\.]+\s*[^:]+):\s*([\d\.]+)\s*(?:s|sec|seconds|minutes|min)?\s*(?:\(([^)]+)\))?",
        re.IGNORECASE,
    )
    count_pattern = re.compile(r"([\d,]+)\s+conversations", re.IGNORECASE)
    csat_pattern = re.compile(r"CSAT|quality|data quality", re.IGNORECASE)
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        duration_match = duration_pattern.search(stripped)
        if duration_match and total_duration is None:
            duration_value = float(duration_match.group(1))
            unit = duration_match.group(2).lower()
            if unit.startswith("min"):
                duration_value *= 60
            total_duration = round(duration_value, 2)
        phase_match = phase_pattern.search(stripped)
        if phase_match:
            phase_name = phase_match.group(1).strip()
            duration_value = float(phase_match.group(2))
            status = (phase_match.group(3) or "unknown").lower()
            phase_details[phase_name] = {
                "duration_seconds": duration_value,
                "status": status,
            }
        if "conversations" in stripped.lower():
            count_match = count_pattern.search(stripped)
            if count_match:
                value = int(count_match.group(1).replace(",", ""))
                key = "total"
                if "paid" in stripped.lower():
                    key = "paid"
                elif "free" in stripped.lower():
                    key = "free"
                conversation_counts[key] = value
        if csat_pattern.search(stripped):
            data_quality_flags.append(stripped)
    return {
        "total_duration_seconds": total_duration,
        "phases": phase_details,
        "conversation_counts": conversation_counts,
        "data_quality_notes": data_quality_flags,
    }


def split_topic_blocks(content: str) -> List[Tuple[str, List[str]]]:
    blocks: List[Tuple[str, List[str]]] = []
    current_name: Optional[str] = None
    current_lines: List[str] = []
    heading_pattern = re.compile(r"^#{2,3}\s+(.*)")
    ignore_keywords = {"voice of customer", "prioritized actions", "fin ai performance", "bpo snapshot"}
    for line in content.splitlines():
        heading_match = heading_pattern.match(line.strip())
        if heading_match:
            heading = heading_match.group(1).strip()
            heading_lower = heading.lower()
            if any(keyword in heading_lower for keyword in ignore_keywords):
                continue
            if current_name and current_lines:
                blocks.append((current_name, current_lines))
            current_name = heading
            current_lines = []
            continue
        if current_name:
            current_lines.append(line)
    if current_name and current_lines:
        blocks.append((current_name, current_lines))
    return blocks


def tokenize(text: str) -> List[str]:
    return [token for token in re.findall(r"[a-z0-9%]+", text.lower()) if token]


def calculate_duplicate_ratio(chunks: Sequence[str]) -> Tuple[float, List[Tuple[str, int]]]:
    joined = " ".join(chunk for chunk in chunks if chunk)
    tokens = tokenize(joined)
    if len(tokens) < min(DUPLICATE_NGRAM_RANGE):
        return 0.0, []
    counts: Counter[str] = Counter()
    for n in DUPLICATE_NGRAM_RANGE:
        for idx in range(len(tokens) - n + 1):
            phrase = " ".join(tokens[idx : idx + n])
            counts[phrase] += 1
    if not counts:
        return 0.0, []
    total_unique = len(counts)
    duplicates = sum(1 for count in counts.values() if count > 1)
    ratio = duplicates / total_unique if total_unique else 0.0
    top_phrases = [(phrase, count) for phrase, count in counts.most_common() if count > 1][:5]
    return round(min(max(ratio, 0.0), 1.0), 4), top_phrases


def count_metric_references(chunks: Sequence[str]) -> int:
    text = " ".join(chunk for chunk in chunks if chunk)
    if not text:
        return 0
    patterns = [
        re.compile(r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b"),
        re.compile(r"\b\d+\.?\d*\s?%\b"),
        re.compile(r"\b\d+\.?\d*\s?(?:tickets|cases|conversations|agents|minutes|hours|days)\b", re.IGNORECASE),
        re.compile(r"\b\d+\.?\d*\s?(?:rate|count|average|avg|ratio)\b", re.IGNORECASE),
    ]
    matches = set()
    for pattern in patterns:
        for match in pattern.findall(text):
            normalized = match if isinstance(match, str) else " ".join(match)
            normalized = normalized.strip().lower()
            if normalized:
                matches.add(normalized)
    return len(matches)


def parse_topic_markdown(content: str) -> List[TopicStats]:
    topics: List[TopicStats] = []
    for name, lines in split_topic_blocks(content):
        stats = TopicStats(name=name)
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            if "**sentiment**" in line.lower():
                stats.sentiment = line.split(":", 1)[-1].strip()
            if "detection method" in line.lower():
                stats.detection_method = line.split(":", 1)[-1].strip()
                if "fallback" in line.lower():
                    stats.fallback_flag = True
            volume_match = re.search(
                r"(\d[\d,]*)\s+(?:tickets|conversations).+?([\d\.]+)%", line, re.IGNORECASE
            )
            if volume_match:
                stats.volume = int(volume_match.group(1).replace(",", ""))
                stats.percentage = float(volume_match.group(2))
            stats.insight_text += f"{line}\n"
        text_chunks = stats.insight_text.splitlines()
        stats.duplicate_ratio, stats.duplicate_phrases = calculate_duplicate_ratio(text_chunks)
        stats.metric_references = count_metric_references(text_chunks)
        topics.append(stats)
    return topics


def parse_markdown_outputs(run_dir: Path) -> List[TopicStats]:
    topics: List[TopicStats] = []
    for md_file in run_dir.glob("voc_topic_based_*.md"):
        content = read_file_safe(md_file)
        if not content:
            continue
        topics.extend(parse_topic_markdown(content))
    return topics


def summarize_runs(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    all_topics = [topic for run in runs for topic in run.get("topics", [])]
    duplicate_values = [topic["duplicate_ratio"] for topic in all_topics if topic.get("duplicate_ratio") is not None]
    metric_values = [topic["metric_references"] for topic in all_topics if topic.get("metric_references") is not None]
    avg_duplicate = round(sum(duplicate_values) / len(duplicate_values), 4) if duplicate_values else 0.0
    avg_metrics = round(sum(metric_values) / len(metric_values), 2) if metric_values else 0.0
    repetitive_phrases: Counter[str] = Counter()
    for topic in all_topics:
        for phrase, count in topic.get("duplicate_phrases", []):
            repetitive_phrases[phrase] += count
    repetitive_summary = [(phrase, count) for phrase, count in repetitive_phrases.most_common(10)]
    total_topics = len(all_topics)
    fallback_topics = sum(1 for topic in all_topics if topic.get("fallback_flag"))
    return {
        "total_runs": len(runs),
        "total_topics": total_topics,
        "average_duplicate_ratio": avg_duplicate,
        "average_metric_references": avg_metrics,
        "fallback_topic_count": fallback_topics,
        "repetitive_phrases": repetitive_summary,
    }


def collect_run_payload(run_dir: Path) -> Dict[str, Any]:
    audit_payloads = [parse_audit_trail(read_file_safe(path)) for path in run_dir.glob("audit_trail_*.md")]
    merged_audit: Dict[str, Any] = {
        "total_duration_seconds": None,
        "phases": {},
        "conversation_counts": {},
        "data_quality_notes": [],
    }
    for payload in audit_payloads:
        if not payload:
            continue
        if payload.get("total_duration_seconds"):
            merged_audit["total_duration_seconds"] = payload["total_duration_seconds"]
        merged_audit["phases"].update(payload.get("phases", {}))
        merged_audit["conversation_counts"].update(payload.get("conversation_counts", {}))
        merged_audit["data_quality_notes"].extend(payload.get("data_quality_notes", []))
    topics = parse_markdown_outputs(run_dir)
    issues: List[str] = []
    for topic in topics:
        if topic.duplicate_ratio > 0.35:
            issues.append(f"{topic.name}: duplicate ratio {topic.duplicate_ratio:.2f}")
        if topic.metric_references < 1:
            issues.append(f"{topic.name}: lacks metric references")
        if topic.fallback_flag:
            issues.append(f"{topic.name}: fallback detection reported")
    return {
        "run_id": run_dir.name,
        "audit": merged_audit,
        "topics": [
            {
                "name": topic.name,
                "volume": topic.volume,
                "percentage": topic.percentage,
                "detection_method": topic.detection_method,
                "sentiment": topic.sentiment,
                "duplicate_ratio": topic.duplicate_ratio,
                "duplicate_phrases": topic.duplicate_phrases,
                "metric_references": topic.metric_references,
                "fallback_flag": topic.fallback_flag,
            }
            for topic in topics
        ],
        "issues": issues,
    }


def write_output(payload: Dict[str, Any], output_dir: Path) -> Path:
    output_path = get_output_file_path("production_run_analysis.json", base_dir=output_dir)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def main() -> None:
    args = parse_args()
    reference_root = Path(args.reference_root)
    output_dir = Path(args.output_dir)
    runs = discover_runs(reference_root, args.limit)
    if not runs:
        logger.error("No production runs matched pattern %s under %s", RUN_GLOB_PATTERN, reference_root)
        return
    logger.info("Parsing %d production run folders", len(runs))
    run_payloads = [collect_run_payload(run_dir) for run_dir in runs]
    summary = summarize_runs(run_payloads)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reference_root": str(reference_root),
        "runs": run_payloads,
        "summary": summary,
    }
    output_path = write_output(payload, output_dir)
    logger.info("Baseline metrics saved to %s", output_path)
    logger.info(
        "Runs=%d topics=%d avg duplicate=%.3f avg metrics=%.2f fallback_topics=%d",
        len(run_payloads),
        summary.get("total_topics"),
        summary.get("average_duplicate_ratio"),
        summary.get("average_metric_references"),
        summary.get("fallback_topic_count"),
    )


if __name__ == "__main__":
    main()

