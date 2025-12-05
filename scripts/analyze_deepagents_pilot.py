#!/usr/bin/env python3
"""
Analyze DeepAgents Pilot Results - Phase 5 Decision Support

Aggregates metrics from multiple pilot runs stored in `outputs/deepagents_pilot/`
and generates a decision report evaluating against adoption thresholds.

Usage:
    python scripts/analyze_deepagents_pilot.py
    python scripts/analyze_deepagents_pilot.py --min-runs 5
    python scripts/analyze_deepagents_pilot.py --strict  # Fail if thresholds not met
"""

import argparse
import json
import statistics
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Adoption thresholds per Phase 5 specification
CRITIC_SCORE_IMPROVEMENT_TARGET = 20.0  # ≥20% improvement required
RUNTIME_PENALTY_MAX = 25.0  # ≤25% penalty acceptable
MIN_SUCCESS_RATE = 95.0  # ≥95% success rate required

CRITIC_DIMENSIONS = [
    'specificity_score',
    'metric_density_score',
    'repetition_score',
    'distinctness_score',
    'actionability_score',
]


@dataclass
class OrchestratorMetrics:
    """Aggregated metrics for a single orchestrator."""
    name: str
    runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    
    # Critic scores
    composite_scores: List[float] = field(default_factory=list)
    dimension_scores: Dict[str, List[float]] = field(default_factory=dict)
    
    # Performance
    durations: List[float] = field(default_factory=list)
    total_tokens: List[int] = field(default_factory=list)
    
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.runs == 0:
            return 0.0
        return (self.successful_runs / self.runs) * 100

    def mean_composite_score(self) -> Optional[float]:
        """Calculate mean composite critic score."""
        if not self.composite_scores:
            return None
        return statistics.mean(self.composite_scores)

    def mean_duration(self) -> Optional[float]:
        """Calculate mean runtime in seconds."""
        if not self.durations:
            return None
        return statistics.mean(self.durations)

    def mean_tokens(self) -> Optional[float]:
        """Calculate mean token usage."""
        if not self.total_tokens:
            return None
        return statistics.mean(self.total_tokens)


@dataclass
class PilotRun:
    """Parsed data from a single pilot comparison."""
    timestamp: str
    config: Dict[str, Any]
    legacy: Dict[str, Any]
    deep: Dict[str, Any]


def find_comparison_files(base_dir: Path) -> List[Path]:
    """Recursively find all comparison.json files under base_dir."""
    if not base_dir.exists():
        return []
    return sorted(base_dir.rglob("comparison.json"))


def parse_comparison_file(filepath: Path) -> Optional[PilotRun]:
    """Parse a comparison.json file into a PilotRun."""
    try:
        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)
        return PilotRun(
            timestamp=data.get('timestamp', ''),
            config=data.get('inputs', {}),
            legacy=data.get('legacy', {}),
            deep=data.get('deep', {}),
        )
    except Exception as exc:
        print(f"Warning: Failed to parse {filepath}: {exc}")
        return None


def extract_orchestrator_data(run_data: Dict[str, Any], metrics: OrchestratorMetrics) -> None:
    """Extract metrics from a single orchestrator run into the metrics object."""
    metrics.runs += 1
    
    status = run_data.get('status', 'unknown')
    if status == 'completed':
        metrics.successful_runs += 1
    else:
        metrics.failed_runs += 1
    
    # Duration
    duration = run_data.get('duration_seconds')
    if isinstance(duration, (int, float)):
        metrics.durations.append(float(duration))
    
    # Metrics from scan
    run_metrics = run_data.get('metrics', {})
    
    # Composite critic score
    critic_composite = run_metrics.get('critic_composite')
    if isinstance(critic_composite, (int, float)):
        metrics.composite_scores.append(float(critic_composite))
    
    # Dimension scores
    critic_dims = run_metrics.get('critic_dimensions', {})
    for dim in CRITIC_DIMENSIONS:
        score = critic_dims.get(dim)
        if isinstance(score, (int, float)):
            if dim not in metrics.dimension_scores:
                metrics.dimension_scores[dim] = []
            metrics.dimension_scores[dim].append(float(score))
    
    # Token usage
    token_usage = run_metrics.get('token_usage', {})
    if isinstance(token_usage, dict):
        total = token_usage.get('total_tokens')
        if isinstance(total, (int, float)):
            metrics.total_tokens.append(int(total))


def calculate_statistics(values: List[float]) -> Dict[str, float]:
    """Calculate mean, median, stdev for a list of values."""
    if not values:
        return {'mean': 0.0, 'median': 0.0, 'stdev': 0.0, 'min': 0.0, 'max': 0.0, 'count': 0}
    return {
        'mean': statistics.mean(values),
        'median': statistics.median(values),
        'stdev': statistics.stdev(values) if len(values) > 1 else 0.0,
        'min': min(values),
        'max': max(values),
        'count': len(values),
    }


def generate_histogram(scores: List[float], bins: int = 10, width: int = 30) -> str:
    """Generate ASCII histogram of score distribution."""
    if not scores:
        return "No data"
    
    min_val, max_val = 0.0, 1.0
    bin_width = (max_val - min_val) / bins
    histogram = [0] * bins
    
    for score in scores:
        clamped = max(min_val, min(score, max_val - 0.001))
        index = int((clamped - min_val) / bin_width)
        histogram[index] += 1
    
    max_count = max(histogram) or 1
    lines = []
    for i, count in enumerate(histogram):
        bin_start = min_val + i * bin_width
        bin_end = bin_start + bin_width
        bar = '█' * int((count / max_count) * width)
        lines.append(f"{bin_start:.2f}-{bin_end:.2f}: {bar} ({count})")
    
    return "\n".join(lines)


def evaluate_thresholds(
    legacy: OrchestratorMetrics,
    deep: OrchestratorMetrics
) -> Dict[str, Dict[str, Any]]:
    """Evaluate adoption thresholds and return pass/fail status."""
    results = {}
    
    # Critic score improvement
    legacy_mean = legacy.mean_composite_score() or 0.0
    deep_mean = deep.mean_composite_score() or 0.0
    if legacy_mean > 0:
        critic_improvement = ((deep_mean - legacy_mean) / legacy_mean) * 100
    else:
        critic_improvement = 0.0 if deep_mean == 0 else 100.0
    
    results['critic_score_improvement'] = {
        'value': critic_improvement,
        'target': f"≥{CRITIC_SCORE_IMPROVEMENT_TARGET}%",
        'met': critic_improvement >= CRITIC_SCORE_IMPROVEMENT_TARGET,
        'legacy_mean': legacy_mean,
        'deep_mean': deep_mean,
    }
    
    # Runtime penalty
    legacy_runtime = legacy.mean_duration() or 0.0
    deep_runtime = deep.mean_duration() or 0.0
    if legacy_runtime > 0:
        runtime_penalty = ((deep_runtime - legacy_runtime) / legacy_runtime) * 100
    else:
        runtime_penalty = 0.0
    
    results['runtime_penalty'] = {
        'value': runtime_penalty,
        'target': f"≤{RUNTIME_PENALTY_MAX}%",
        'met': runtime_penalty <= RUNTIME_PENALTY_MAX,
        'legacy_mean': legacy_runtime,
        'deep_mean': deep_runtime,
    }
    
    # Token efficiency
    legacy_tokens = legacy.mean_tokens() or 0.0
    deep_tokens = deep.mean_tokens() or 0.0
    if legacy_tokens > 0:
        token_delta = ((deep_tokens - legacy_tokens) / legacy_tokens) * 100
    else:
        token_delta = 0.0
    
    results['token_efficiency'] = {
        'value': token_delta,
        'target': "maintained or improved (≤0%)",
        'met': token_delta <= 0,
        'legacy_mean': legacy_tokens,
        'deep_mean': deep_tokens,
    }
    
    # Success rates
    legacy_success = legacy.success_rate()
    deep_success = deep.success_rate()
    
    results['legacy_success_rate'] = {
        'value': legacy_success,
        'target': f"≥{MIN_SUCCESS_RATE}%",
        'met': legacy_success >= MIN_SUCCESS_RATE,
    }
    
    results['deep_success_rate'] = {
        'value': deep_success,
        'target': f"≥{MIN_SUCCESS_RATE}%",
        'met': deep_success >= MIN_SUCCESS_RATE,
    }
    
    return results


def determine_recommendation(thresholds: Dict[str, Dict[str, Any]], min_runs: int, actual_runs: int) -> str:
    """Determine ADOPT/DEFER/REJECT recommendation based on thresholds."""
    if actual_runs < min_runs:
        return "DEFER"
    
    critical_checks = [
        thresholds['critic_score_improvement']['met'],
        thresholds['runtime_penalty']['met'],
        thresholds['legacy_success_rate']['met'],
        thresholds['deep_success_rate']['met'],
    ]
    
    if all(critical_checks):
        return "ADOPT"
    elif any(critical_checks):
        return "DEFER"
    else:
        return "REJECT"


def generate_markdown_report(
    legacy: OrchestratorMetrics,
    deep: OrchestratorMetrics,
    thresholds: Dict[str, Dict[str, Any]],
    recommendation: str,
    runs: List[PilotRun],
    output_path: Path
) -> None:
    """Generate the Phase 5 decision analysis markdown report."""
    lines = [
        "# Phase 5: DeepAgents Pilot Decision Analysis",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Recommendation:** **{recommendation}**",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        "| Orchestrator | Runs | Success Rate | Mean Critic Score | Mean Runtime (s) | Mean Tokens |",
        "|--------------|------|--------------|-------------------|------------------|-------------|",
    ]
    
    # Legacy row
    legacy_critic = legacy.mean_composite_score()
    legacy_runtime = legacy.mean_duration()
    legacy_tokens = legacy.mean_tokens()
    legacy_critic_str = f"{legacy_critic:.3f}" if legacy_critic is not None else "N/A"
    legacy_runtime_str = f"{legacy_runtime:.2f}" if legacy_runtime is not None else "N/A"
    legacy_tokens_str = f"{int(legacy_tokens)}" if legacy_tokens is not None else "N/A"
    lines.append(
        f"| Legacy | {legacy.runs} | {legacy.success_rate():.1f}% | "
        f"{legacy_critic_str} | {legacy_runtime_str} | {legacy_tokens_str} |"
    )
     
    # Deep row
    deep_critic = deep.mean_composite_score()
    deep_runtime = deep.mean_duration()
    deep_tokens = deep.mean_tokens()
    deep_critic_str = f"{deep_critic:.3f}" if deep_critic is not None else "N/A"
    deep_runtime_str = f"{deep_runtime:.2f}" if deep_runtime is not None else "N/A"
    deep_tokens_str = f"{int(deep_tokens)}" if deep_tokens is not None else "N/A"
    lines.append(
        f"| Deep | {deep.runs} | {deep.success_rate():.1f}% | "
        f"{deep_critic_str} | {deep_runtime_str} | {deep_tokens_str} |"
    )
    
    # Threshold evaluation
    lines.extend([
        "",
        "## Threshold Evaluation",
        "",
    ])
    
    for key, data in thresholds.items():
        status = "✅" if data['met'] else "❌"
        value = data['value']
        target = data['target']
        if isinstance(value, float):
            value_str = f"{value:+.1f}%" if 'rate' not in key else f"{value:.1f}%"
        else:
            value_str = str(value)
        lines.append(f"- {status} **{key.replace('_', ' ').title()}**: {value_str} (Target: {target})")
    
    # Detailed statistics
    lines.extend([
        "",
        "## Detailed Statistics",
        "",
        "### Composite Critic Scores",
        "",
    ])
    
    if legacy.composite_scores:
        stats = calculate_statistics(legacy.composite_scores)
        lines.extend([
            "**Legacy:**",
            f"- Mean: {stats['mean']:.3f}",
            f"- Median: {stats['median']:.3f}",
            f"- Std Dev: {stats['stdev']:.3f}",
            f"- Range: [{stats['min']:.3f}, {stats['max']:.3f}]",
            "",
            "```",
            generate_histogram(legacy.composite_scores),
            "```",
            "",
        ])
    
    if deep.composite_scores:
        stats = calculate_statistics(deep.composite_scores)
        lines.extend([
            "**Deep:**",
            f"- Mean: {stats['mean']:.3f}",
            f"- Median: {stats['median']:.3f}",
            f"- Std Dev: {stats['stdev']:.3f}",
            f"- Range: [{stats['min']:.3f}, {stats['max']:.3f}]",
            "",
            "```",
            generate_histogram(deep.composite_scores),
            "```",
            "",
        ])
    
    # Per-dimension scores
    lines.extend([
        "### Per-Dimension Critic Scores",
        "",
        "| Dimension | Legacy Mean | Deep Mean | Δ |",
        "|-----------|-------------|-----------|---|",
    ])
    
    for dim in CRITIC_DIMENSIONS:
        legacy_vals = legacy.dimension_scores.get(dim, [])
        deep_vals = deep.dimension_scores.get(dim, [])
        legacy_mean = statistics.mean(legacy_vals) if legacy_vals else 0.0
        deep_mean = statistics.mean(deep_vals) if deep_vals else 0.0
        delta = deep_mean - legacy_mean
        lines.append(f"| {dim.replace('_', ' ').title()} | {legacy_mean:.3f} | {deep_mean:.3f} | {delta:+.3f} |")
    
    # Pilot runs table
    lines.extend([
        "",
        "## Pilot Runs",
        "",
        "| Timestamp | Configuration | Legacy Status | Deep Status |",
        "|-----------|---------------|---------------|-------------|",
    ])
    
    for run in runs:
        config_str = f"{run.config.get('analysis_type', 'N/A')}, {run.config.get('count', 'N/A')} convs"
        if run.config.get('test_mode'):
            config_str += " (test)"
        lines.append(
            f"| {run.timestamp} | {config_str} | "
            f"{run.legacy.get('status', 'N/A')} | {run.deep.get('status', 'N/A')} |"
        )
    
    # Recommendation rationale
    lines.extend([
        "",
        "## Recommendation Rationale",
        "",
    ])
    
    if recommendation == "ADOPT":
        lines.extend([
            "The DeepAgents orchestrator **meets all adoption criteria**:",
            "",
            f"- Critic score improvement exceeds {CRITIC_SCORE_IMPROVEMENT_TARGET}% threshold",
            f"- Runtime penalty is within acceptable {RUNTIME_PENALTY_MAX}% limit",
            "- Both orchestrators maintain high success rates",
            "",
            "**Proceed to rollout** per `docs/PHASE_5_ROLLOUT_CHECKLIST.md`.",
        ])
    elif recommendation == "DEFER":
        lines.extend([
            "The analysis shows **mixed results** that do not clearly support adoption:",
            "",
        ])
        for key, data in thresholds.items():
            if not data['met']:
                lines.append(f"- ❌ {key.replace('_', ' ').title()} missed target")
        lines.extend([
            "",
            "**Re-evaluate after**:",
            "- Collecting additional pilot runs (current sample may be insufficient)",
            "- Addressing identified performance gaps",
            "- Upgrading deepagents dependency if newer version improves metrics",
        ])
    else:  # REJECT
        lines.extend([
            "The DeepAgents orchestrator **fails to meet adoption criteria**:",
            "",
        ])
        for key, data in thresholds.items():
            if not data['met']:
                lines.append(f"- ❌ {key.replace('_', ' ').title()}: {data['value']:.1f}% (target: {data['target']})")
        lines.extend([
            "",
            "**Alternative approaches**:",
            "- Continue with legacy orchestrator as default",
            "- Investigate root causes of quality/performance gaps",
            "- Consider alternative orchestration frameworks",
        ])
    
    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding='utf-8')
    print(f"✅ Decision analysis saved to {output_path}")


def generate_json_summary(
    legacy: OrchestratorMetrics,
    deep: OrchestratorMetrics,
    thresholds: Dict[str, Dict[str, Any]],
    recommendation: str,
    output_path: Path
) -> None:
    """Generate structured JSON summary for programmatic access."""
    summary = {
        'generated_at': datetime.now().isoformat(),
        'recommendation': recommendation,
        'thresholds': thresholds,
        'orchestrators': {
            'legacy': {
                'runs': legacy.runs,
                'successful_runs': legacy.successful_runs,
                'success_rate': legacy.success_rate(),
                'composite_score': calculate_statistics(legacy.composite_scores),
                'duration': calculate_statistics(legacy.durations),
                'tokens': calculate_statistics([float(t) for t in legacy.total_tokens]),
                'dimension_scores': {
                    dim: calculate_statistics(scores)
                    for dim, scores in legacy.dimension_scores.items()
                },
            },
            'deep': {
                'runs': deep.runs,
                'successful_runs': deep.successful_runs,
                'success_rate': deep.success_rate(),
                'composite_score': calculate_statistics(deep.composite_scores),
                'duration': calculate_statistics(deep.durations),
                'tokens': calculate_statistics([float(t) for t in deep.total_tokens]),
                'dimension_scores': {
                    dim: calculate_statistics(scores)
                    for dim, scores in deep.dimension_scores.items()
                },
            },
        },
    }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"✅ Metrics summary saved to {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze DeepAgents pilot results and generate decision report"
    )
    parser.add_argument(
        '--pilot-dir',
        type=Path,
        default=Path('outputs/deepagents_pilot'),
        help="Base directory containing pilot run outputs"
    )
    parser.add_argument(
        '--min-runs',
        type=int,
        default=3,
        help="Minimum runs per orchestrator before generating recommendation (default: 3)"
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help="Exit with error code if thresholds are not met"
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=None,
        help="Output directory for reports (default: same as pilot-dir)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = args.output_dir or args.pilot_dir
    
    print(f"Scanning for pilot data in {args.pilot_dir}...")
    comparison_files = find_comparison_files(args.pilot_dir)
    
    if not comparison_files:
        print(f"❌ No comparison.json files found in {args.pilot_dir}")
        print("   Run `python scripts/run_pilot_suite.py` to generate pilot data first.")
        sys.exit(1)
    
    print(f"Found {len(comparison_files)} pilot runs")
    
    # Parse all runs
    runs: List[PilotRun] = []
    for filepath in comparison_files:
        run = parse_comparison_file(filepath)
        if run:
            runs.append(run)
    
    if not runs:
        print("❌ No valid pilot runs could be parsed")
        sys.exit(1)
    
    # Aggregate metrics
    legacy = OrchestratorMetrics(name='legacy')
    deep = OrchestratorMetrics(name='deep')
    
    for run in runs:
        extract_orchestrator_data(run.legacy, legacy)
        extract_orchestrator_data(run.deep, deep)
    
    print(f"\nAggregated: {legacy.runs} legacy runs, {deep.runs} deep runs")
    
    # Check minimum runs
    min_runs_met = legacy.successful_runs >= args.min_runs and deep.successful_runs >= args.min_runs
    if not min_runs_met:
        print(f"\n⚠️  Insufficient data: need ≥{args.min_runs} successful runs per orchestrator")
        print(f"   Legacy: {legacy.successful_runs} successful, Deep: {deep.successful_runs} successful")
    
    # Evaluate thresholds
    thresholds = evaluate_thresholds(legacy, deep)
    recommendation = determine_recommendation(thresholds, args.min_runs, min(legacy.successful_runs, deep.successful_runs))
    
    # Generate reports
    report_path = output_dir / 'phase5_decision_analysis.md'
    json_path = output_dir / 'phase5_metrics_summary.json'
    
    generate_markdown_report(legacy, deep, thresholds, recommendation, runs, report_path)
    generate_json_summary(legacy, deep, thresholds, recommendation, json_path)
    
    # Print summary
    print("\n" + "=" * 60)
    print("PHASE 5 DECISION ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"\nRecommendation: {recommendation}")
    print("\nThreshold Evaluation:")
    for key, data in thresholds.items():
        status = "✅" if data['met'] else "❌"
        value = data['value']
        if isinstance(value, float):
            value_str = f"{value:+.1f}%" if 'rate' not in key else f"{value:.1f}%"
        else:
            value_str = str(value)
        print(f"  {status} {key.replace('_', ' ').title()}: {value_str}")
    print("=" * 60)
    
    # Exit code for strict mode
    if args.strict:
        all_met = all(data['met'] for data in thresholds.values())
        if not all_met or recommendation != "ADOPT":
            print("\n❌ Strict mode: thresholds not met")
            sys.exit(1)
    
    print("\n✅ Analysis complete")


if __name__ == '__main__':
    main()
