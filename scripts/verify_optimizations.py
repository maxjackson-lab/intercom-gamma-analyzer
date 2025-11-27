"""
Comprehensive verification runner for system optimizations.

This utility orchestrates automated validation across:
- Pytest suite execution
- Sample-mode real data analysis
- Log parsing and JSON/presentation validation
- Multi-language keyword detection checks
- Markdown report generation summarizing all results
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.config.taxonomy import TaxonomyManager
from src.agents.topic_detection_agent import TopicDetectionAgent


console = Console(record=True)


@dataclass
class SectionResult:
    name: str
    success: bool
    details: List[str] = field(default_factory=list)

    def as_markdown(self) -> str:
        status = "✅ PASS" if self.success else "❌ FAIL"
        body = "\n".join(f"- {line}" for line in self.details) or "- No details captured."
        return f"### {self.name}\n**{status}**\n{body}\n"


@dataclass
class VerificationReport:
    sections: List[SectionResult] = field(default_factory=list)

    def overall_success(self) -> bool:
        return all(section.success for section in self.sections)

    def render_console_summary(self) -> None:
        table = Table(title="Optimization Verification Summary")
        table.add_column("Section", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Highlights", style="white")
        for section in self.sections:
            status = "[green]PASS[/green]" if section.success else "[red]FAIL[/red]"
            highlight = section.details[0] if section.details else "No details"
            table.add_row(section.name, status, highlight)
        console.print(table)

    def save_markdown(self, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = output_dir / f"verification_report_{timestamp}.md"
        with path.open("w", encoding="utf-8") as f:
            f.write("# System Optimization Verification Report\n\n")
            f.write(f"_Generated: {datetime.utcnow().isoformat()}Z_\n\n")
            for section in self.sections:
                f.write(section.as_markdown())
                f.write("\n")
            f.write(f"## Overall Status: {'PASS' if self.overall_success() else 'FAIL'}\n")
        return path


def run_subprocess(command: List[str], cwd: Optional[Path] = None) -> Tuple[bool, str]:
    console.log(f"Running command: {' '.join(command)}")
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            check=False,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        return False, f"Command failed: {exc}"

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    if stdout:
        console.log(stdout)
    if stderr:
        console.log(f"[red]{stderr}[/red]")
    success = result.returncode == 0
    return success, stdout if stdout else stderr


def run_pytest_suite(pytest_path: str) -> SectionResult:
    success, output = run_subprocess(["pytest", pytest_path, "-v"])
    details = [
        "Executed pytest suite.",
        "Refer to console output for full trace.",
        "Command: pytest tests/test_prompt_optimization.py -v",
    ]
    if output:
        details.append(output.splitlines()[-1][:160])
    return SectionResult(
        name="Test Suite Verification",
        success=success,
        details=details,
    )


def discover_latest_output(outputs_dir: Path) -> Optional[Path]:
    if not outputs_dir.exists():
        return None
    
    # Look for sample_mode_*.json files first (new format)
    json_files = list(outputs_dir.glob("sample_mode_*.json"))
    if json_files:
        return max(json_files, key=lambda p: p.stat().st_mtime)
    
    candidate_dirs = [
        path for path in outputs_dir.iterdir()
        if path.is_dir()
    ]
    if not candidate_dirs:
        return None
    return max(candidate_dirs, key=lambda p: p.stat().st_mtime)


def run_sample_mode(count: int) -> SectionResult:
    command = [
        sys.executable, "src/main.py", "sample-mode", "--count", str(count), "--save-to-file"
    ]
    success, output = run_subprocess(command)
    details = [
        f"Triggered sample-mode with count={count}",
        "Artifacts saved under outputs/sample_mode_<timestamp>/",
        "Inspect latest outputs directory for JSON, log, and presentation files.",
    ]
    if output:
        details.append(output.splitlines()[-1][:160])
    return SectionResult(
        name="Sample Mode Execution",
        success=success,
        details=details,
    )


def parse_log_file(log_path: Path) -> Dict[str, float]:
    metrics = {
        "high_confidence_skip_count": 0,
        "llm_calls": 0,
        "optimization_rate": 0.0,
        "sentiment_quality_mentions": 0,
    }
    patterns = {
        "skip": re.compile(r"Skipped LLM for (\d+)(?:/(\d+))? conversations"),
        "llm_calls": re.compile(r"Confidence Routing Metrics: (\d+) skips .*?, (\d+) LLM calls"),
        "optimization": re.compile(r"Optimization Efficiency:\s*([\d.]+)"),
        "sentiment": re.compile(r"Sentiment Quality:\s*Score=([\d.]+)"),
    }
    if not log_path.exists():
        return metrics
    with log_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if match := patterns["skip"].search(line):
                metrics["high_confidence_skip_count"] = max(
                    metrics["high_confidence_skip_count"],
                    int(match.group(1)),
                )
            if match := patterns["llm_calls"].search(line):
                # match.group(1) is skips, match.group(2) is llm_calls
                metrics["high_confidence_skip_count"] = max(metrics["high_confidence_skip_count"], int(match.group(1)))
                metrics["llm_calls"] = max(metrics["llm_calls"], int(match.group(2)))
            if match := patterns["optimization"].search(line):
                metrics["optimization_rate"] = max(metrics["optimization_rate"], float(match.group(1)))
            if patterns["sentiment"].search(line):
                metrics["sentiment_quality_mentions"] += 1
    return metrics


def validate_json_output(json_path: Path) -> Tuple[bool, List[str]]:
    if not json_path.exists():
        return False, [f"JSON file missing: {json_path}"]

    with json_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    details = []
    success = True

    topics = data.get("topics") or data.get("results")
    if not topics:
        # Try sample-mode nested structure
        topics = data.get("analysis", {}).get("hierarchy_debug", {}).get("topics", [])
    
    if topics and isinstance(topics, list) and len(topics) > 0:
        first = topics[0]
        if isinstance(first, str):
            # Try to recover if it's just topic names? No, we need fields.
            success = False
            details.append(f"Topics found but are strings, expected dicts. First: {first}")
            return success, details

    fallback_metrics = data.get("fallback_metrics") or data.get("metadata", {}).get("fallback_metrics")
    if not fallback_metrics:
        # Try sample-mode nested structure
        fallback_metrics = data.get("analysis", {}).get("hierarchy_debug", {}).get("fallback_metrics")

    if not topics:
        success = False
        details.append("No topics detected in JSON output.")
    else:
        inspected = 0
        for topic in topics:
            if inspected >= 3:
                break
            detection_tag = topic.get("detection_method") or topic.get("detection_method_tag")
            sentiment = topic.get("sentiment_insight")
            subtopics = topic.get("subtopics") or []
            if not detection_tag:
                success = False
                details.append(f"Missing detection_method or detection_method_tag for topic {topic.get('topic')}")
            
            # Conditional sentiment check: only if sentiment is present
            if sentiment and "sentiment" in sentiment.lower():
                success = False
                details.append(f"Sentiment insight appears generic for topic {topic.get('topic')}")
            
            for subtopic in subtopics:
                if "percentage" not in subtopic:
                    success = False
                    details.append(f"Subtopic missing percentage for topic {topic.get('topic')}")
                    break
            inspected += 1

    if not fallback_metrics:
        success = False
        details.append("fallback_metrics missing from JSON output.")
    else:
        # optimization_rate is optional if we can calculate it
        required_keys = {"total_conversations", "llm_calls", "high_confidence_skip_count"}
        missing = sorted(required_keys - set(fallback_metrics.keys()))
        if missing:
            success = False
            details.append(f"fallback_metrics missing keys: {', '.join(missing)}")
        else:
            opt_rate = fallback_metrics.get('optimization_rate')
            if opt_rate is None and fallback_metrics.get('total_conversations', 0) > 0:
                 opt_rate = (fallback_metrics.get('high_confidence_skip_count', 0) / fallback_metrics.get('total_conversations')) * 100.0
            
            details.append(
                f"fallback_metrics present with optimization_rate={opt_rate}"
            )

    if not details:
        details.append("JSON output validated successfully.")

    return success, details


def validate_presentation(markdown_path: Path) -> Tuple[bool, List[str]]:
    if not markdown_path.exists():
        return False, [f"Presentation file missing: {markdown_path}"]

    with markdown_path.open("r", encoding="utf-8") as handle:
        content = handle.read()

    success = True
    details = []

    if "Methodology Appendix" not in content:
        success = False
        details.append("Methodology appendix missing.")
    if "Optimization Metrics" not in content:
        success = False
        details.append("Optimization metrics table missing.")
    if "Sentiment Breakdown" not in content:
        success = False
        details.append("Sentiment breakdown section missing.")
    if re.search(r"\bpositive sentiment\b|\bnegative sentiment\b|\bmixed sentiment\b", content, re.IGNORECASE):
        success = False
        details.append("Found generic sentiment labels in presentation.")
    if not re.search(r"\(\d+%?\)", content):
        success = False
        details.append("Subtopic percentages missing (pattern '(XX%)').")

    if success:
        details.append("Presentation markdown contains required sections.")

    return success, details


def run_multi_language_probe(verbose: bool = False) -> SectionResult:
    taxonomy = TaxonomyManager()
    agent = TopicDetectionAgent(llm_first=False)

    samples = [
        ("Account", "Я не могу войти в свой аккаунт. Забыл пароль."),
        ("Billing", "Хочу получить возврат денег за подписку."),
        ("Bug", "У меня ошибка при экспорте файла."),
        ("Account", "계정에 로그인할 수 없습니다. 비밀번호를 잊어버렸어요."),
        ("Billing", "구독 환불을 원합니다."),
        ("Bug", "파일 내보내기 오류가 있습니다."),
    ]

    failures = []
    for expected_topic, text in samples:
        conversation = {
            "id": f"test-{expected_topic.lower()}",
            "source": {"author": {"name": "Test User"}},
            "conversation_parts": {"conversation_parts": []},
            "custom_attributes": {},
            "body": text,
        }
        classifications = taxonomy.classify_conversation(conversation)
        taxonomy_match = classifications[0]["category"] if classifications else None

        keyword_topics = asyncio.run(agent._fallback_to_keywords(conversation))
        agent_topic = keyword_topics[0]["topic"] if keyword_topics else None

        if taxonomy_match != expected_topic or agent_topic != expected_topic:
            failures.append(
                f"{text[:30]}... expected {expected_topic}, got taxonomy={taxonomy_match}, agent={agent_topic}"
            )

    success = len(failures) == 0
    details = ["Russian/Korean keywords validated via TaxonomyManager and TopicDetectionAgent."]
    if failures:
        details.extend(failures)
    if verbose:
        console.print(Panel("\n".join(details), title="Multi-language Debug"))
    return SectionResult(
        name="Multi-Language Keyword Coverage",
        success=success,
        details=details,
    )


def analyze_outputs(outputs_dir: Path) -> List[SectionResult]:
    sections: List[SectionResult] = []
    latest = discover_latest_output(outputs_dir)
    if not latest:
        return [
            SectionResult(
                name="Output Discovery",
                success=False,
                details=[f"No directories found in {outputs_dir}"],
            )
        ]

    if latest.is_file():
        json_path = latest
        log_path = latest.with_suffix(".log")
        presentation_path = latest.parent / "presentation.md"
        if not presentation_path.exists():
            presentation_path = None
    else:
        json_path = next((p for p in latest.glob("*.json")), None)
        log_path = next((p for p in latest.glob("*.log")), None)
        presentation_path = next((p for p in latest.glob("*.md")), None)

    log_metrics = parse_log_file(log_path) if log_path else {}
    sections.append(
        SectionResult(
            name="Log Analysis",
            success=bool(log_path),
            details=[
                f"Log file: {log_path}" if log_path else "Log file missing.",
                f"High-confidence skips: {log_metrics.get('high_confidence_skip_count', 'N/A')}",
                f"LLM calls: {log_metrics.get('llm_calls', 'N/A')}",
                f"Optimization rate: {log_metrics.get('optimization_rate', 'N/A')}%",
                f"Sentiment quality mentions: {log_metrics.get('sentiment_quality_mentions', 'N/A')}",
            ],
        )
    )

    json_success, json_details = validate_json_output(json_path) if json_path else (False, ["JSON file missing."])
    sections.append(
        SectionResult(
            name="JSON Output Validation",
            success=json_success,
            details=json_details,
        )
    )

    if presentation_path and presentation_path.exists():
        pres_success, pres_details = validate_presentation(presentation_path)
        sections.append(
            SectionResult(
                name="Presentation Validation",
                success=pres_success,
                details=pres_details,
            )
        )
    else:
        sections.append(
            SectionResult(
                name="Presentation Validation",
                success=True,
                details=["Presentation file not generated (optional for sample-mode)."],
            )
        )

    return sections


def generate_final_report(args: argparse.Namespace) -> VerificationReport:
    report = VerificationReport()

    if args.test_suite:
        report.sections.append(run_pytest_suite("tests/test_prompt_optimization.py"))

    if args.sample_mode:
        report.sections.append(run_sample_mode(args.sample_count))
        report.sections.extend(analyze_outputs(Path("outputs")))

    if args.multi_language:
        report.sections.append(run_multi_language_probe(verbose=args.verbose))

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify system optimizations end-to-end.")
    parser.add_argument("--test-suite", dest="test_suite", action="store_true", default=True, help="Run pytest suite (enabled by default).")
    parser.add_argument("--skip-test-suite", dest="test_suite", action="store_false", help="Disable pytest suite execution.")
    parser.add_argument("--sample-mode", dest="sample_mode", action="store_true", default=True, help="Execute sample-mode workflow (enabled by default).")
    parser.add_argument("--skip-sample-mode", dest="sample_mode", action="store_false", help="Disable sample-mode verification.")
    parser.add_argument("--multi-language", dest="multi_language", action="store_true", default=True, help="Validate Russian/Korean keyword support.")
    parser.add_argument("--skip-multi-language", dest="multi_language", action="store_false", help="Disable multi-language tests.")
    parser.add_argument("--sample-count", type=int, default=50, help="Conversation count for sample mode.")
    parser.add_argument("--output-dir", type=Path, default=Path("./verification_outputs"), help="Directory for verification artifacts.")
    parser.add_argument("--verbose", action="store_true", default=False, help="Enable verbose logging.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = generate_final_report(args)
    report.render_console_summary()
    report_path = report.save_markdown(args.output_dir)
    console.print(f"[bold]Report saved to {report_path}[/bold]")
    sys.exit(0 if report.overall_success() else 1)


if __name__ == "__main__":
    main()

