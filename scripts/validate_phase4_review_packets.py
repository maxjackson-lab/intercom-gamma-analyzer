import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
HELPER_ANALYSIS_ID = "phase4_validation"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


def generate_degraded_sample() -> Dict[str, Any]:
    """Create degraded payload to simulate KPI failures."""
    return {
        "critic_scores": {
            "composite_score": 0.42,
            "duplicate_ratio": 0.25,
            "metric_references_count": 2,
            "issues_found": ["Generic phrasing", "Low metric density"],
        },
        "formatter_metrics": {
            "topic_percentage_total": 86.0,
            "topic_fallback_used": 3,
            "csat_coverage_pct": None,
            "fin_deflection_rate": None,
            "churn_risk_count": None,
        },
    }


def run_voice_of_customer_with_forced_failure() -> tuple[subprocess.CompletedProcess[str], float]:
    """Execute a VoC run that forces review packet generation."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    env["FORCE_REVIEW_PACKET_FAILURE"] = "1"
    env.setdefault("ENABLE_METRICS_MONITORING", "1")
    cmd = [
        sys.executable,
        "src/main.py",
        "voice-of-customer",
        "--time-period",
        "week",
        "--test-mode",
        "--test-data-count",
        "50",
        "--digest-mode",
    ]
    start_time = time.time()
    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result, start_time


def find_new_files(pattern: str, start_time: float) -> List[Path]:
    """Locate files created after start_time matching glob pattern."""
    if not OUTPUTS_DIR.exists():
        return []
    matches = []
    for path in OUTPUTS_DIR.rglob(pattern):
        try:
            if path.stat().st_mtime >= start_time:
                matches.append(path)
        except FileNotFoundError:
            continue
    matches.sort(key=lambda p: p.stat().st_mtime)
    return matches


def validate_review_packet(packet_path: Path) -> bool:
    """Validate structure of the review packet at packet_path."""
    if not packet_path.exists():
        print(f"❌ Review packet missing: {packet_path}")
        return False

    content = packet_path.read_text(encoding="utf-8")
    required_sections = [
        "# Quality Review Packet",
        "## Executive Summary",
        "## Failed KPIs",
        "## Detailed Findings",
        "## Artifacts",
        "## Recommended Actions",
    ]
    for section in required_sections:
        if section not in content:
            print(f"❌ Missing section in review packet: {section}")
            return False

    print(f"✅ Review packet validated: {packet_path}")
    return True


def extract_review_event(log_text: str) -> Optional[Dict[str, Any]]:
    """Parse the last review_required event from log output."""
    pattern = re.compile(r"SSE_EVENT\s+(\{[^\n]+\})")
    matches = pattern.findall(log_text)
    for candidate in reversed(matches):
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if payload.get("type") == "review_required":
            return payload
    return None


def find_latest_log(start_time: float) -> Optional[Path]:
    """Locate the newest log file associated with the run."""
    logs = find_new_files("*.log", start_time)
    if logs:
        return logs[-1]
    return None


def review_packet_relative_path(packet: Path) -> str:
    """Convert packet path to outputs-relative string."""
    try:
        return str(packet.relative_to(OUTPUTS_DIR))
    except ValueError:
        return packet.name


def generate_review_packet_from_degraded(degraded: Dict[str, Any]) -> Optional[Path]:
    """Generate a review packet directly from degraded metrics."""
    from src.utils.output_manager import get_output_directory
    from src.utils.review_packet_generator import ReviewPacketGenerator

    class DummyContext:
        def __init__(self):
            self.analysis_id = HELPER_ANALYSIS_ID
            self.metadata = {"analysis_id": HELPER_ANALYSIS_ID}
            self.previous_results = {}

    ctx = DummyContext()
    output_dir = get_output_directory()
    evaluation = ReviewPacketGenerator.evaluate_kpis(
        degraded.get("critic_scores", {}),
        degraded.get("formatter_metrics", {}),
        ctx,
    )
    packet_path = ReviewPacketGenerator.generate_review_packet(evaluation, ctx, output_dir)
    return Path(packet_path) if packet_path else None


def extract_analysis_id(packet_path: Path) -> Optional[str]:
    """Read the analysis ID from the review packet."""
    try:
        text = packet_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    match = re.search(r"\*\*Analysis ID\*\*:\s*(.+)", text)
    if match:
        return match.group(1).strip()
    return None


def locate_primary_review_packet(start_time: float) -> Path:
    """Locate review packet generated by the orchestrated VoC run (excludes helper packets)."""
    candidates = find_new_files("review_packet_*.md", start_time)
    for candidate in reversed(candidates):
        if HELPER_ANALYSIS_ID in candidate.name:
            continue
        analysis_id = extract_analysis_id(candidate)
        if analysis_id and analysis_id != HELPER_ANALYSIS_ID:
            return candidate
    raise SystemExit("❌ Orchestrated VoC run did not generate a review packet")


def ensure_stdout_mentions_review(stdout_text: str):
    """Ensure the CLI output mentioned review packet generation."""
    if "Review packet generated" not in stdout_text and "Quality KPIs missed" not in stdout_text:
        raise SystemExit("❌ CLI output did not mention review packet generation (Quality KPIs)")


def main():
    degraded = generate_degraded_sample()
    print("Generated degraded sample:", json.dumps(degraded, indent=2))

    run_result, start_time = run_voice_of_customer_with_forced_failure()
    if run_result.returncode != 0:
        raise SystemExit("Voice of Customer validation run failed")

    ensure_stdout_mentions_review(run_result.stdout)

    latest_packet = locate_primary_review_packet(start_time)

    packet_valid = validate_review_packet(latest_packet)

    latest_log = find_latest_log(start_time)
    if latest_log is None:
        raise SystemExit("❌ Unable to locate log file for review packet run")
    log_text = latest_log.read_text(encoding="utf-8")
    event_payload = extract_review_event(log_text)
    if not event_payload:
        raise SystemExit("❌ review_required event not found in log output")

    relative_packet_path = review_packet_relative_path(latest_packet)
    event_data = event_payload.get("data", {})
    event_packet_path = event_data.get("web_path") or event_data.get("packet_path")
    if event_packet_path and event_packet_path != relative_packet_path:
        raise SystemExit(
            f"❌ Packet path mismatch (event: {event_packet_path}, file: {relative_packet_path})"
        )

    helper_packet = generate_review_packet_from_degraded(degraded)
    helper_valid = helper_packet is not None and helper_packet.exists()
    if helper_valid and helper_packet:
        helper_valid = validate_review_packet(helper_packet)
    else:
        print("❌ Helper degradation test failed to persist packet")

    if not packet_valid:
        raise SystemExit("❌ Phase 4 validation failed (primary VoC run)")
    if not helper_valid:
        raise SystemExit("❌ ReviewPacketGenerator helper test failed")

    print("✅ Phase 4 validation: PASSED")


if __name__ == "__main__":
    main()

