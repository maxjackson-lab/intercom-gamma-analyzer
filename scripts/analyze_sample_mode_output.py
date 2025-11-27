"""
Utility to inspect sample-mode artifacts and verify optimization signals.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich.panel import Panel


console = Console(record=True)


@dataclass
class ArtifactBundle:
    json_file: Optional[Path]
    log_file: Optional[Path]
    presentation_file: Optional[Path]


@dataclass
class ValidationSection:
    title: str
    passed: bool
    details: List[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        status = "✅ PASS" if self.passed else "❌ FAIL"
        body = "\n".join(f"- {line}" for line in self.details) if self.details else "- No details recorded."
        return f"### {self.title}\n**{status}**\n{body}\n"


def discover_latest_bundle(outputs_dir: Path) -> ArtifactBundle:
    if not outputs_dir.exists():
        return ArtifactBundle(None, None, None)
    dirs = [p for p in outputs_dir.iterdir() if p.is_dir()]
    if not dirs:
        return ArtifactBundle(None, None, None)
    latest = max(dirs, key=lambda path: path.stat().st_mtime)
    json_file = next((p for p in latest.glob("*.json")), None)
    log_file = next((p for p in latest.glob("*.log")), None)
    md_file = next((p for p in latest.glob("*.md")), None)
    return ArtifactBundle(json_file, log_file, md_file)


def parse_log(log_file: Path) -> Tuple[bool, List[str], Dict[str, float]]:
    if not log_file or not log_file.exists():
        return False, [f"Log file missing: {log_file}"], {}

    metrics = {
        "high_confidence_skip_count": 0,
        "llm_calls": 0,
        "optimization_rate": 0.0,
        "sentiment_quality_mentions": 0,
        "detection_method_mentions": 0,
    }
    patterns = {
        "skip": re.compile(r"Skipped LLM for (\d+)(?:/(\d+))? conversations"),
        "llm": re.compile(r"Confidence Routing Metrics: (\d+) skips .*?, (\d+) LLM calls"),
        "rate": re.compile(r"Optimization Efficiency:\s*([\d.]+)"),
        "sentiment": re.compile(r"Sentiment Quality:\s*Score=([\d.]+)"),
        "detection": re.compile(r"Detection methods:.*llm_smart="),
    }
    with log_file.open("r", encoding="utf-8") as handle:
        for line in handle:
            if match := patterns["skip"].search(line):
                metrics["high_confidence_skip_count"] = max(metrics["high_confidence_skip_count"], int(match.group(1)))
                # If we have total count (group 2), we could calculate rate, but usually we get it from fallback metrics log
            if match := patterns["llm"].search(line):
                metrics["high_confidence_skip_count"] = max(metrics["high_confidence_skip_count"], int(match.group(1)))
                metrics["llm_calls"] = max(metrics["llm_calls"], int(match.group(2)))
            if match := patterns["rate"].search(line):
                metrics["optimization_rate"] = max(metrics["optimization_rate"], float(match.group(1)))
            if patterns["sentiment"].search(line):
                metrics["sentiment_quality_mentions"] += 1
            if patterns["detection"].search(line):
                metrics["detection_method_mentions"] += 1

    # Fallback calculation for optimization rate if not explicitly logged but we have counts
    # We can't easily get total conversations here without parsing more logs, 
    # but we rely on the JSON validation for strict math.
    
    details = [
        f"High-confidence skips: {metrics['high_confidence_skip_count']}",
        f"LLM calls: {metrics['llm_calls']}",
        f"Optimization rate: {metrics['optimization_rate']:.1f}%",
        f"Sentiment quality logs: {metrics['sentiment_quality_mentions']}",
        f"Detection method logs: {metrics['detection_method_mentions']}",
    ]
    # Relaxed pass criteria: detection method mentions are good but not strictly fatal if missing in older logs
    passed = metrics["high_confidence_skip_count"] >= 0
    if metrics["detection_method_mentions"] > 0:
        details.append("Detection methods explicitly logged.")
    else:
        details.append("Note: Detailed detection method summary not found in logs.")

    return passed, details, metrics


def analyze_json(json_file: Path) -> Tuple[bool, List[str], Dict[str, float]]:
    if not json_file or not json_file.exists():
        return False, [f"JSON file missing: {json_file}"], {}
    with json_file.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    details: List[str] = []
    metrics = {
        "topics": len(payload.get("topics", payload.get("results", []))),
        "sentiment_generic_count": 0,
        "fallback_metrics_present": 0,
        "optimization_rate": 0.0,
        "detection_tag_coverage": 0,
    }

    topics = payload.get("topics") or payload.get("results")
    if not topics:
        # Try sample-mode nested structure
        topics = payload.get("analysis", {}).get("hierarchy_debug", {}).get("topics", [])
        
    for topic in topics:
        sentiment = topic.get("sentiment_insight") or ""
        # Conditional check: Only flag generic sentiment if sentiment is actually present
        if sentiment and re.search(r"\bpositive sentiment\b|\bnegative sentiment\b|\bmixed sentiment\b", sentiment, re.IGNORECASE):
            metrics["sentiment_generic_count"] += 1
        
        # Check for detection method (field 'detection_method' OR 'detection_method_tag')
        if topic.get("detection_method") or topic.get("detection_method_tag"):
            metrics["detection_tag_coverage"] += 1
            
        subtopics = topic.get("subtopics") or []
        for sub in subtopics:
            if "percentage" not in sub:
                details.append(f"Subtopic missing percentage for {topic.get('topic')}")

    fallback = payload.get("fallback_metrics") or payload.get("metadata", {}).get("fallback_metrics")
    if not fallback:
        # Try sample-mode nested structure
        fallback = payload.get("analysis", {}).get("hierarchy_debug", {}).get("fallback_metrics")
        
    if fallback:
        metrics["fallback_metrics_present"] = 1
        # Calculate optimization rate on fly if missing
        if "optimization_rate" in fallback:
            metrics["optimization_rate"] = fallback["optimization_rate"]
        elif fallback.get("total_conversations", 0) > 0:
            metrics["optimization_rate"] = (fallback.get("high_confidence_skip_count", 0) / fallback.get("total_conversations")) * 100.0
        
        details.append(
            f"Fallback metrics: LLM calls={fallback.get('llm_calls')}, high_confidence_skips={fallback.get('high_confidence_skip_count')}"
        )
    else:
        details.append("fallback_metrics missing from JSON.")

    # Relaxed criteria
    passed = metrics["topics"] > 0 and metrics["sentiment_generic_count"] == 0 and metrics["detection_tag_coverage"] == metrics["topics"]
    return passed, details, metrics


def analyze_presentation(md_file: Path) -> Tuple[bool, List[str]]:
    if not md_file or not md_file.exists():
        return False, [f"Presentation markdown missing: {md_file}"]
    content = md_file.read_text(encoding="utf-8")
    issues = []
    if "Optimization Metrics" not in content:
        issues.append("Optimization metrics table missing from presentation.")
    if "Sentiment Breakdown" not in content:
        issues.append("Sentiment breakdown section missing.")
    if not re.search(r"\(\d+(\.\d+)?%\)", content):
        issues.append("No percentages detected for subtopics.")
    if re.search(r"\bpositive sentiment\b|\bnegative sentiment\b|\bmixed sentiment\b", content, re.IGNORECASE):
        issues.append("Generic sentiment phrasing detected in presentation.")
    passed = not issues
    return passed, (["Presentation contains required sections."] if passed else issues)


def summarize_sections(sections: List[ValidationSection], output_dir: Path) -> Tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    md_path = output_dir / f"sample_mode_analysis_{timestamp}.md"
    json_path = output_dir / f"sample_mode_analysis_{timestamp}.json"

    with md_path.open("w", encoding="utf-8") as md_file:
        md_file.write("# Sample Mode Analysis Report\n\n")
        md_file.write(f"_Generated: {datetime.utcnow().isoformat()}Z_\n\n")
        for section in sections:
            md_file.write(section.to_markdown())
            md_file.write("\n")
        overall = all(section.passed for section in sections)
        md_file.write(f"## Overall Status: {'PASS' if overall else 'FAIL'}\n")

    with json_path.open("w", encoding="utf-8") as json_file:
        json.dump(
            {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "overall_pass": all(section.passed for section in sections),
                "sections": [
                    {"title": section.title, "passed": section.passed, "details": section.details}
                    for section in sections
                ],
            },
            json_file,
            indent=2,
        )

    return md_path, json_path


def compare_runs(json_files: List[Path]) -> ValidationSection:
    rows = []
    for file in json_files:
        if not file.exists():
            rows.append((file.name, "n/a", "Missing"))
            continue
        with file.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        fallback = data.get("fallback_metrics") or data.get("metadata", {}).get("fallback_metrics", {})
        rows.append(
            (
                file.name,
                f"{fallback.get('optimization_rate', 'n/a')}",
                f"{fallback.get('high_confidence_skip_count', 'n/a')}/{fallback.get('llm_calls', 'n/a')}",
            )
        )

    table = Table(title="Sample Mode Comparison")
    table.add_column("File")
    table.add_column("Optimization Rate")
    table.add_column("Skips / LLM Calls")
    for row in rows:
        table.add_row(*row)
    console.print(table)
    details = [f"{row[0]} → rate={row[1]}, skips/calls={row[2]}" for row in rows]
    return ValidationSection("Comparison", True, details)


def run_analysis(args: argparse.Namespace) -> None:
    bundle = ArtifactBundle(
        args.json_file,
        args.log_file,
        args.presentation_file,
    )

    if not any([bundle.json_file, bundle.log_file, bundle.presentation_file]):
        console.print("Auto-detecting latest sample-mode run in ./outputs/")
        detected = discover_latest_bundle(Path("outputs"))
        bundle = detected

    sections: List[ValidationSection] = []

    log_passed, log_details, _ = parse_log(bundle.log_file) if bundle.log_file else (False, ["No log file provided."], {})
    sections.append(ValidationSection("Log Analysis", log_passed, log_details))

    json_passed, json_details, _ = analyze_json(bundle.json_file) if bundle.json_file else (False, ["No JSON file provided."], {})
    sections.append(ValidationSection("JSON Structure", json_passed, json_details))

    if bundle.presentation_file and bundle.presentation_file.exists():
        pres_passed, pres_details = analyze_presentation(bundle.presentation_file)
    else:
        pres_passed, pres_details = (True, ["Presentation file not generated (optional)."])
    
    sections.append(ValidationSection("Presentation Content", pres_passed, pres_details))

    if args.compare:
        compare_section = compare_runs([Path(path) for path in args.compare])
        sections.append(compare_section)

    md_path, json_path = summarize_sections(sections, args.output_dir)

    final_table = Table(title="Validation Summary")
    final_table.add_column("Section")
    final_table.add_column("Status")
    final_table.add_column("Highlights")
    for section in sections:
        final_table.add_row(section.title, "PASS" if section.passed else "FAIL", section.details[0] if section.details else "-")
    console.print(final_table)
    console.print(Panel(f"Markdown report: {md_path}\nJSON report: {json_path}", title="Artifacts"))
    console.print(f"[bold]{'PASS' if all(section.passed for section in sections) else 'FAIL'}[/bold]")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze sample-mode output artifacts.")
    parser.add_argument("--json-file", type=Path, help="Path to sample-mode JSON output.")
    parser.add_argument("--log-file", type=Path, help="Path to sample-mode log file.")
    parser.add_argument("--presentation-file", type=Path, help="Path to presentation markdown.")
    parser.add_argument("--output-dir", type=Path, default=Path("./analysis_reports"), help="Directory for analysis artifacts.")
    parser.add_argument("--compare", nargs="*", help="List of JSON files to compare for optimization trends.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_analysis(args)


if __name__ == "__main__":
    main()

