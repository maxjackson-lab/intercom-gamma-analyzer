#!/usr/bin/env python3
"""
Run sample-mode to collect baseline VoC metrics for Phase 0 validation.

Workflow:
1. Execute: python src/main.py sample-mode --count 50 --save-to-file
2. Parse latest log + JSON artifacts in outputs/
3. Extract:
   - Stage metrics (Post-Fetch → Pre-Formatting)
   - InsightAgent and OutputFormatterAgent telemetry
   - Execution metadata (tokens, duration)
4. Persist snapshot to outputs/baseline_metrics/sample_mode_baseline_<timestamp>.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.utils.output_manager import get_output_file_path


DEFAULT_BASELINE_DIR = Path("outputs") / "baseline_metrics"
STAGE_NAMES = ["Post-Fetch", "Post-Segmentation", "Post-TopicDetection", "Post-Insights", "Pre-Formatting"]


@dataclass
class SampleArtifacts:
    log_file: Optional[Path] = None
    json_file: Optional[Path] = None
    markdown_file: Optional[Path] = None

    def latest_path(self) -> Optional[Path]:
        candidates = [p for p in [self.log_file, self.json_file, self.markdown_file] if p and p.exists()]
        if not candidates:
            return None
        return max(candidates, key=lambda path: path.stat().st_mtime)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Phase 0 metrics via sample-mode execution.")
    parser.add_argument(
        "--count",
        type=int,
        default=50,
        help="Conversation count for sample-mode (default: 50)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_BASELINE_DIR),
        help="Directory for saving baseline metric snapshots",
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Skip running sample-mode and only parse latest artifacts",
    )
    return parser.parse_args()


def run_sample_mode(count: int) -> subprocess.CompletedProcess[str]:
    cmd = ["python", "src/main.py", "sample-mode", "--count", str(count), "--save-to-file"]
    print(f"🚀 Running sample-mode: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ Sample-mode failed")
        print(result.stderr)
    else:
        print("✅ Sample-mode completed")
    return result


def find_latest_artifacts(outputs_dir: Path) -> SampleArtifacts:
    if not outputs_dir.exists():
        return SampleArtifacts()
    log_files = sorted(outputs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime)
    json_files = sorted(outputs_dir.glob("sample_mode_*.json"), key=lambda p: p.stat().st_mtime)
    markdown_files = sorted(outputs_dir.glob("*.md"), key=lambda p: p.stat().st_mtime)
    latest = SampleArtifacts(
        log_file=log_files[-1] if log_files else None,
        json_file=json_files[-1] if json_files else None,
        markdown_file=markdown_files[-1] if markdown_files else None,
    )
    return latest


def parse_stage_metrics(log_content: str) -> Dict[str, int]:
    metrics: Dict[str, int] = {}
    for stage in STAGE_NAMES:
        pattern = re.compile(rf"{re.escape(stage)}.*?(\d+)")
        for line in log_content.splitlines():
            if stage in line:
                match = pattern.search(line)
                if match:
                    metrics[stage] = int(match.group(1))
                    break
    return metrics


def parse_agent_metrics(log_content: str) -> Dict[str, Dict[str, float]]:
    insight_pattern = re.compile(
        r"InsightAgent metrics:\s*duplicate_ratio=([\d\.]+),\s*metric_refs=(\d+),\s*tokens=~?(\d+)",
        re.IGNORECASE,
    )
    formatter_pattern = re.compile(
        r"OutputFormatterAgent metrics:\s*topic_fallbacks=(\d+),\s*placeholders=(\d+),\s*tokens=~?(\d+)",
        re.IGNORECASE,
    )
    metrics: Dict[str, Dict[str, float]] = {}
    for line in log_content.splitlines():
        insight_match = insight_pattern.search(line)
        if insight_match:
            metrics["InsightAgent"] = {
                "duplicate_ratio": float(insight_match.group(1)),
                "metric_references_count": int(insight_match.group(2)),
                "token_count": int(insight_match.group(3)),
            }
        formatter_match = formatter_pattern.search(line)
        if formatter_match:
            metrics["OutputFormatterAgent"] = {
                "topic_fallback_used": int(formatter_match.group(1)),
                "placeholder_volume": int(formatter_match.group(2)),
                "token_count": int(formatter_match.group(3)),
            }
    return metrics


def load_json_metrics(json_path: Optional[Path]) -> Dict[str, Any]:
    if not json_path or not json_path.exists():
        return {}
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    agent_results = payload.get("agent_results", {})
    return {
        "conversation_count": payload.get("conversation_count") or len(payload.get("conversations", [])),
        "agent_results": agent_results,
    }


def evaluate_thresholds(agent_metrics: Dict[str, Dict[str, float]]) -> List[str]:
    warnings: List[str] = []
    insight = agent_metrics.get("InsightAgent", {})
    formatter = agent_metrics.get("OutputFormatterAgent", {})
    if insight.get("duplicate_ratio", 0) > 0.4:
        warnings.append(f"InsightAgent duplicate ratio high ({insight['duplicate_ratio']:.2f})")
    if insight.get("metric_references_count", 0) < 2:
        warnings.append("InsightAgent metric references below target (<2)")
    if formatter.get("topic_fallback_used", 0) > 2:
        warnings.append(f"OutputFormatterAgent fallback usage high ({formatter['topic_fallback_used']})")
    if formatter.get("placeholder_volume", 0) > 3:
        warnings.append(f"OutputFormatterAgent placeholder volume high ({formatter['placeholder_volume']})")
    return warnings


def build_baseline_payload(
    stage_metrics: Dict[str, int],
    agent_metrics: Dict[str, Dict[str, float]],
    json_metrics: Dict[str, Any],
    artifacts: SampleArtifacts,
    count: int,
    missing_stage_metrics: Optional[List[str]] = None,
) -> Dict[str, Any]:
    timestamp = datetime.now(timezone.utc).isoformat()
    baseline = {
        "timestamp": timestamp,
        "run_type": "sample-mode",
        "conversation_count": json_metrics.get("conversation_count", count),
        "stage_metrics": stage_metrics,
        "missing_stage_metrics": missing_stage_metrics or [],
        "agent_metrics": agent_metrics,
        "artifacts": {
            "log_file": str(artifacts.log_file) if artifacts.log_file else None,
            "json_file": str(artifacts.json_file) if artifacts.json_file else None,
        },
    }
    return baseline


def save_baseline(payload: Dict[str, Any], output_dir: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"sample_mode_baseline_{timestamp}.json"
    output_path = get_output_file_path(filename, base_dir=output_dir)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def main() -> None:
    args = parse_args()
    outputs_dir = Path("outputs")
    if not args.skip_run:
        run_sample_mode(args.count)
    artifacts = find_latest_artifacts(outputs_dir)
    if not artifacts.log_file or not artifacts.log_file.exists():
        raise SystemExit("No log file found in outputs/. Run sample-mode first.")
    log_content = artifacts.log_file.read_text(encoding="utf-8")
    stage_metrics = parse_stage_metrics(log_content)
    missing_stage_metrics = [stage for stage in STAGE_NAMES if stage not in stage_metrics]
    if missing_stage_metrics:
        print(f"⚠️ Missing stage metrics for: {', '.join(missing_stage_metrics)}")
    agent_metrics = parse_agent_metrics(log_content)
    json_metrics = load_json_metrics(artifacts.json_file)
    baseline_payload = build_baseline_payload(
        stage_metrics=stage_metrics,
        agent_metrics=agent_metrics,
        json_metrics=json_metrics,
        artifacts=artifacts,
        count=args.count,
        missing_stage_metrics=missing_stage_metrics,
    )
    warnings = evaluate_thresholds(agent_metrics)
    output_path = save_baseline(baseline_payload, Path(args.output_dir))
    print(f"📊 Baseline metrics saved to {output_path}")
    if warnings:
        print("⚠️ Validation warnings:")
        for warning in warnings:
            print(f" - {warning}")
    else:
        print("✅ Metrics within expected thresholds")


if __name__ == "__main__":
    main()

