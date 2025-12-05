"""
Pilot script to compare legacy vs DeepAgents orchestrators for VoC.

Runs two back-to-back analyses with identical inputs:
- legacy orchestrator (TopicOrchestratorV2 path)
- deep orchestrator (DeepSupervisor path)

Outputs are stored under outputs/deepagents_pilot/<timestamp>/
with a comparison report summarizing runtime and status.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from rich.console import Console

from src.cli.voc_commands import run_voice_of_customer_analysis


console = Console()


def _maybe_numeric(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return None


def _scan_output_metrics(output_dir: Path) -> Dict[str, Any]:
    """
    Parse JSON outputs to extract critic scores and token usage for pilot comparison.
    """
    metrics: Dict[str, Any] = {}

    def _traverse(obj: Any):
        if isinstance(obj, dict):
            # Structured critic scores
            critic_scores = obj.get("critic_scores") or obj.get("critic_metrics")
            if isinstance(critic_scores, dict) and "critic_dimensions" not in metrics:
                metrics["critic_dimensions"] = critic_scores

            # Composite critic score
            for key in ["critic_score", "composite_score", "critic_composite_score"]:
                if key in obj and "critic_composite" not in metrics:
                    num = _maybe_numeric(obj[key])
                    if num is not None:
                        metrics["critic_composite"] = num
                        break

            # Token usage
            if "token_usage" in obj and "token_usage" not in metrics and isinstance(obj["token_usage"], dict):
                metrics["token_usage"] = obj["token_usage"]

            for key in ["total_tokens", "token_count", "tokens"]:
                if key in obj and "token_usage" not in metrics:
                    num = _maybe_numeric(obj[key])
                    if num is not None:
                        metrics["token_usage"] = {"total_tokens": num}
                        break

            for value in obj.values():
                _traverse(value)

        elif isinstance(obj, list):
            for item in obj:
                _traverse(item)

    for json_file in output_dir.rglob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                _traverse(data)
        except Exception:
            continue  # Best-effort parsing; skip unreadable files

    return metrics


def _build_output_dir(base: Path, orchestrator: str) -> Path:
    target = base / orchestrator
    target.mkdir(parents=True, exist_ok=True)
    return target


async def _run_single(orchestrator: str, args: argparse.Namespace, output_dir: Path) -> Dict[str, Any]:
    """
    Execute a single VoC run with the specified orchestrator.
    """
    start_time = time.perf_counter()
    status = "completed"
    error: str | None = None

    try:
        await run_voice_of_customer_analysis(
            time_period=args.time_period,
            periods_back=args.periods_back,
            start_date=None,
            end_date=None,
            ai_model=args.ai_model,
            enable_fallback=True,
            include_trends=args.include_trends,
            include_canny=False,
            llm_topic_detection=args.llm_topic_detection,
            canny_board_id=None,
            generate_gamma=False,
            test_mode=args.test_mode,
            test_data_count=str(args.count),
            verbose=False,
            analysis_type=args.analysis_type,
            audit_trail=False,
            output_dir=str(output_dir),
            digest_mode=args.digest_mode,
            enable_correlation_analysis=True,
            enable_quality_insights=True,
            enable_churn_detection=True,
            enable_confidence_meta=True,
            enable_subtopic_detection=True,
            enable_topic_sentiment=True,
            enable_topic_examples=True,
            enable_fin_analysis=True,
            enable_bpo_analysis=True,
            enable_trend_analysis=True,
            legacy_mode=False,
            detail_level=args.detail_level,
            orchestrator=orchestrator,
        )
        metrics = _scan_output_metrics(output_dir)
    except Exception as exc:  # pragma: no cover - pilot resilience
        status = "failed"
        error = str(exc)
        console.print(f"[red]❌ {orchestrator} run failed: {exc}[/red]")
        metrics = {}

    duration = time.perf_counter() - start_time
    return {
        "orchestrator": orchestrator,
        "status": status,
        "error": error,
        "duration_seconds": duration,
        "metrics": metrics,
    }


async def main():
    parser = argparse.ArgumentParser(description="Run legacy vs deep orchestrator pilot.")
    parser.add_argument("--time-period", default="week", help="Time period to analyze (default: week)")
    parser.add_argument("--periods-back", type=int, default=1, help="Periods back (default: 1)")
    parser.add_argument("--analysis-type", default="topic-based", choices=["topic-based", "synthesis", "complete"])
    parser.add_argument("--count", type=int, default=100, help="Test data count when --test-mode enabled")
    parser.add_argument("--ai-model", default="openai", choices=["openai", "claude"])
    parser.add_argument("--include-trends", action="store_true", help="Include trend analysis")
    parser.add_argument("--llm-topic-detection", action="store_true", help="Enable LLM-first topic detection")
    parser.add_argument("--digest-mode", action="store_true", help="Enable digest narrative mode where applicable")
    parser.add_argument("--detail-level", default="standard", choices=["standard", "deep", "comprehensive"])
    parser.add_argument("--test-mode", action="store_true", help="Use mock data")
    parser.add_argument(
        "--output-dir",
        default="outputs/deepagents_pilot",
        help="Base output directory for pilot runs",
    )

    args = parser.parse_args()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_dir = Path(args.output_dir) / timestamp
    base_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[cyan]Starting DeepAgents pilot at {timestamp}[/cyan]")
    legacy_dir = _build_output_dir(base_dir, "legacy")
    deep_dir = _build_output_dir(base_dir, "deep")

    legacy_result = await _run_single("legacy", args, legacy_dir)
    deep_result = await _run_single("deep", args, deep_dir)

    comparison = {
        "legacy": legacy_result,
        "deep": deep_result,
        "timestamp": timestamp,
        "inputs": {
            "time_period": args.time_period,
            "periods_back": args.periods_back,
            "analysis_type": args.analysis_type,
            "ai_model": args.ai_model,
            "llm_topic_detection": args.llm_topic_detection,
            "digest_mode": args.digest_mode,
            "detail_level": args.detail_level,
            "test_mode": args.test_mode,
            "count": args.count,
        },
    }

    # Write structured JSON
    json_path = base_dir / "comparison.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)

    # Write quick Markdown summary
    def _format_metric(label: str, legacy_val: Any, deep_val: Any) -> str:
        delta = None
        if isinstance(legacy_val, (int, float)) and isinstance(deep_val, (int, float)):
            delta = deep_val - legacy_val
        delta_str = f" (Δ {delta:+.2f})" if delta is not None else ""
        return f"- {label}: legacy={legacy_val}, deep={deep_val}{delta_str}"

    md_lines = [
        "# DeepAgents Pilot Comparison",
        "",
        f"- Timestamp: {timestamp}",
        f"- Time Period: {args.time_period} (periods back: {args.periods_back})",
        f"- Analysis Type: {args.analysis_type}",
        "",
        "## Results",
        f"- Legacy: {legacy_result['status']} in {legacy_result['duration_seconds']:.2f}s",
        f"- Deep: {deep_result['status']} in {deep_result['duration_seconds']:.2f}s",
    ]
    if legacy_result.get("error"):
        md_lines.append(f"- Legacy error: {legacy_result['error']}")
    if deep_result.get("error"):
        md_lines.append(f"- Deep error: {deep_result['error']}")

    # Metrics comparison (critic score + token usage)
    legacy_metrics = legacy_result.get("metrics") or {}
    deep_metrics = deep_result.get("metrics") or {}
    if legacy_metrics or deep_metrics:
        md_lines.append("")
        md_lines.append("## Metrics")
        legacy_critic = legacy_metrics.get("critic_composite")
        deep_critic = deep_metrics.get("critic_composite")
        if legacy_critic is not None or deep_critic is not None:
            md_lines.append(_format_metric("Composite critic score", legacy_critic, deep_critic))

        legacy_tokens = None
        deep_tokens = None
        if isinstance(legacy_metrics.get("token_usage"), dict):
            legacy_tokens = legacy_metrics["token_usage"].get("total_tokens")
        if isinstance(deep_metrics.get("token_usage"), dict):
            deep_tokens = deep_metrics["token_usage"].get("total_tokens")
        if legacy_tokens is not None or deep_tokens is not None:
            md_lines.append(_format_metric("Total tokens", legacy_tokens, deep_tokens))

    md_path = base_dir / "comparison_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    console.print(f"[green]✅ Pilot complete. Outputs saved to {base_dir}[/green]")
    console.print(f"[dim]JSON: {json_path}[/dim]")
    console.print(f"[dim]Markdown: {md_path}[/dim]")


if __name__ == "__main__":
    asyncio.run(main())

