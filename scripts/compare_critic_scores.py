#!/usr/bin/env python3
"""
Compare Critic Scores - Phase 1 Validation

Analyzes critic scores from sample-mode runs and generates comparison reports.

Usage:
    python scripts/compare_critic_scores.py --baseline outputs/baseline_metrics/ --current outputs/critic_scores/
"""

import argparse
import json
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


DIMENSIONS = [
    'specificity_score',
    'metric_density_score',
    'repetition_score',
    'distinctness_score',
    'actionability_score',
    'composite_score'
]


@dataclass
class ScoreEntry:
    file: str
    timestamp: str
    scores: Dict[str, float]


def load_critic_scores(directory: Path) -> List[ScoreEntry]:
    """Load all critic score JSON files from directory."""
    scores: List[ScoreEntry] = []
    for json_file in sorted(directory.glob('*.json')):
        try:
            with open(json_file, encoding='utf-8') as f:
                data = json.load(f)
            critic_scores = data.get('critic_scores')
            if isinstance(critic_scores, dict):
                scores.append(
                    ScoreEntry(
                        file=json_file.name,
                        timestamp=data.get('timestamp', ''),
                        scores=critic_scores
                    )
                )
        except Exception as exc:
            print(f"Warning: Failed to load {json_file}: {exc}")
    return scores


def calculate_statistics(entries: List[ScoreEntry]) -> Dict[str, Dict[str, float]]:
    """Calculate mean, median, std dev for each dimension."""
    stats: Dict[str, Dict[str, float]] = {}
    for dim in DIMENSIONS:
        values = [entry.scores.get(dim) for entry in entries if entry.scores.get(dim) is not None]
        if values:
            stats[dim] = {
                'mean': statistics.mean(values),
                'median': statistics.median(values),
                'stdev': statistics.stdev(values) if len(values) > 1 else 0.0,
                'min': min(values),
                'max': max(values),
                'count': len(values),
            }
    return stats


def generate_histogram(scores: List[float], bins: int = 10) -> str:
    """Generate ASCII histogram of score distribution."""
    if not scores:
        return "No data"

    min_val, max_val = 0.0, 1.0
    bin_width = (max_val - min_val) / bins
    histogram = [0] * bins

    for score in scores:
        index = min(int((score - min_val) / bin_width), bins - 1)
        histogram[index] += 1

    max_count = max(histogram) or 1
    lines = []
    for i, count in enumerate(histogram):
        bin_start = min_val + i * bin_width
        bin_end = bin_start + bin_width
        bar = '█' * int((count / max_count) * 40)
        lines.append(f"{bin_start:.2f}-{bin_end:.2f}: {bar} ({count})")

    return "\n".join(lines)


def compare_distributions(
    baseline_stats: Dict[str, Dict[str, float]],
    current_stats: Dict[str, Dict[str, float]]
) -> Dict[str, Dict[str, float]]:
    """Compare baseline vs current statistics and calculate improvements."""
    comparison: Dict[str, Dict[str, float]] = {}
    for dim, baseline in baseline_stats.items():
        current = current_stats.get(dim)
        if not current:
            continue
        baseline_mean = baseline.get('mean', 0.0)
        current_mean = current.get('mean', 0.0)
        improvement = ((current_mean - baseline_mean) / baseline_mean * 100) if baseline_mean > 0 else 0.0
        comparison[dim] = {
            'baseline_mean': baseline_mean,
            'current_mean': current_mean,
            'improvement_pct': improvement,
            'meets_target': improvement >= 20.0
        }
    return comparison


def generate_report(
    baseline_stats: Dict[str, Dict[str, float]],
    current_stats: Dict[str, Dict[str, float]],
    comparison: Dict[str, Dict[str, float]],
    output_path: Path
) -> None:
    """Generate markdown comparison report."""
    lines = [
        "# Phase 1 Critic Score Comparison Report",
        "",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Summary Statistics",
        "",
        "| Dimension | Baseline Mean | Current Mean | Improvement | Target Met? |",
        "|-----------|---------------|--------------|-------------|-------------|"
    ]

    for dim in DIMENSIONS:
        dim_comp = comparison.get(dim)
        if not dim_comp:
            continue
        target_met = "✅" if dim_comp['meets_target'] else "❌"
        lines.append(
            f"| {dim.replace('_', ' ').title()} | "
            f"{dim_comp['baseline_mean']:.3f} | "
            f"{dim_comp['current_mean']:.3f} | "
            f"{dim_comp['improvement_pct']:+.1f}% | "
            f"{target_met} |"
        )

    lines.extend(["", "## Validation Criteria", ""])
    composite_improvement = comparison.get('composite_score', {}).get('improvement_pct', 0.0)
    current_composite = current_stats.get('composite_score', {}).get('mean', 0.0)
    criteria = [
        ("Mean composite score improves ≥20%", composite_improvement >= 20.0),
        ("Current mean composite ≥0.60", current_composite >= 0.60),
    ]
    for label, met in criteria:
        status = "✅" if met else "❌"
        lines.append(f"- {status} {label}")

    lines.extend(["", "## Detailed Statistics", ""])
    for dim in DIMENSIONS:
        base = baseline_stats.get(dim)
        current = current_stats.get(dim)
        if not base or not current:
            continue
        lines.extend([
            f"### {dim.replace('_', ' ').title()}",
            "",
            "**Baseline:**",
            f"- Mean: {base['mean']:.3f}",
            f"- Median: {base['median']:.3f}",
            f"- Std Dev: {base['stdev']:.3f}",
            f"- Range: [{base['min']:.3f}, {base['max']:.3f}]",
            "",
            "**Current:**",
            f"- Mean: {current['mean']:.3f}",
            f"- Median: {current['median']:.3f}",
            f"- Std Dev: {current['stdev']:.3f}",
            f"- Range: [{current['min']:.3f}, {current['max']:.3f}]",
            "",
        ])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding='utf-8')
    print(f"✅ Report saved to {output_path}")


def summarize_histograms(entries: List[ScoreEntry], label: str) -> None:
    """Print histograms for debugging."""
    print(f"\n--- {label} Score Distributions ---")
    for dim in DIMENSIONS:
        values = [entry.scores.get(dim, 0.0) for entry in entries]
        if values:
            print(f"\n{dim.replace('_', ' ').title()}:")
            print(generate_histogram(values))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare critic score distributions")
    parser.add_argument('--baseline', type=Path, required=True, help="Baseline metrics directory")
    parser.add_argument('--current', type=Path, required=True, help="Current metrics directory")
    parser.add_argument('--output', type=Path, default=Path('outputs/critic_scores/comparison_report.md'),
                        help="Output report path")
    parser.add_argument('--show-histograms', action='store_true', help="Print ASCII histograms to console")
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.baseline.exists():
        print(f"Error: Baseline directory not found: {args.baseline}")
        return
    if not args.current.exists():
        print(f"Error: Current directory not found: {args.current}")
        return

    print("Loading baseline scores...")
    baseline_entries = load_critic_scores(args.baseline)
    print(f"Loaded {len(baseline_entries)} baseline runs")

    print("Loading current scores...")
    current_entries = load_critic_scores(args.current)
    print(f"Loaded {len(current_entries)} current runs")

    if not baseline_entries or not current_entries:
        print("Error: Need scores from both baseline and current runs")
        return

    if args.show_histograms:
        summarize_histograms(baseline_entries, "Baseline")
        summarize_histograms(current_entries, "Current")

    print("Calculating statistics...")
    baseline_stats = calculate_statistics(baseline_entries)
    current_stats = calculate_statistics(current_entries)

    print("Comparing distributions...")
    comparison = compare_distributions(baseline_stats, current_stats)

    print("Generating report...")
    generate_report(baseline_stats, current_stats, comparison, args.output)

    print("\n" + "=" * 60)
    print("PHASE 1 VALIDATION SUMMARY")
    print("=" * 60)
    composite_improvement = comparison.get('composite_score', {}).get('improvement_pct', 0.0)
    print(f"Composite Score Improvement: {composite_improvement:+.1f}%")
    print(f"Target (≥20%): {'✅ MET' if composite_improvement >= 20.0 else '❌ NOT MET'}")
    print("=" * 60)


if __name__ == '__main__':
    main()

