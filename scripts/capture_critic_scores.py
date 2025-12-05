#!/usr/bin/env python3
"""
Capture Critic Scores from Sample-Mode Runs

Extracts critic scores from sample-mode output files and saves them in a standardized format.

Usage:
    python scripts/capture_critic_scores.py outputs/sample_mode_*.json
    python scripts/capture_critic_scores.py --input outputs/ --output outputs/critic_scores/
"""

import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List


def extract_critic_scores(sample_output: Dict) -> Optional[Dict]:
    """Extract critic scores from sample-mode output structure."""
    workflow_results = sample_output.get('workflow_results')
    if not workflow_results:
        workflow_results = sample_output.get('agent_results', {})
        if workflow_results:
            print("ℹ️ capture_critic_scores: Falling back to agent_results container")
    if not isinstance(workflow_results, dict):
        workflow_results = {}
    editor_result = workflow_results.get('EditorAgent', {})

    if not isinstance(editor_result, dict):
        return None

    critic_scores = editor_result.get('critic_scores') or {}
    if not critic_scores:
        data_payload = editor_result.get('data')
        if isinstance(data_payload, dict):
            critic_scores = data_payload.get('critic_scores') or {}
    if not critic_scores:
        return None

    rewrite_performed = editor_result.get('rewrite_performed')
    if rewrite_performed is None:
        data_payload = editor_result.get('data')
        if isinstance(data_payload, dict):
            rewrite_performed = data_payload.get('rewrite_performed')
    rewrite_performed = bool(rewrite_performed)

    analytical_insights = workflow_results.get('AnalyticalInsights', {})
    insight_result = analytical_insights.get('InsightAgent', {})
    insight_data = insight_result.get('data', {}) if isinstance(insight_result, dict) else {}

    return {
        'timestamp': sample_output.get('timestamp', datetime.utcnow().isoformat()),
        'run_id': sample_output.get('analysis_id', 'unknown'),
        'conversation_count': sample_output.get('total_conversations', 0),
        'critic_scores': critic_scores,
        'rewrite_performed': rewrite_performed,
        'insight_metrics': {
            'duplicate_ratio': insight_data.get('insight_duplicate_ratio', 0.0),
            'metric_references': insight_data.get('metric_references_count', 0)
        }
    }


def save_critic_scores(scores: Dict, output_dir: Path, run_id: str) -> Path:
    """Save critic scores to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"phase1_critic_scores_{run_id}_{timestamp}.json"
    output_path = output_dir / filename

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(scores, f, indent=2)

    print(f"✅ Saved critic scores to {output_path}")
    return output_path


def process_sample_file(input_path: Path, output_dir: Path) -> bool:
    """Process a single sample-mode output file."""
    try:
        with open(input_path, encoding='utf-8') as f:
            sample_output = json.load(f)

        scores = extract_critic_scores(sample_output)
        if not scores:
            print(f"⚠️ No critic scores found in {input_path.name}")
            return False

        run_id = scores.get('run_id') or input_path.stem
        save_critic_scores(scores, output_dir, run_id)

        composite = scores['critic_scores'].get('composite_score', 0.0)
        rewrite = "Yes" if scores.get('rewrite_performed') else "No"
        print(f"   Composite Score: {composite:.2f}, Rewrite: {rewrite}")
        return True

    except Exception as exc:
        print(f"❌ Error processing {input_path}: {exc}")
        return False


def collect_input_files(explicit_files, input_dir: Optional[Path]) -> List[Path]:
    """Gather input files from explicit arguments and directory scan."""
    files = list(explicit_files)
    if input_dir:
        if not input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")
        files.extend(sorted(input_dir.glob('sample_mode_*.json')))
    return files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract critic scores from sample-mode runs")
    parser.add_argument('files', nargs='*', type=Path, help="Sample-mode JSON files to process")
    parser.add_argument('--input', type=Path, help="Input directory to scan for sample-mode files")
    parser.add_argument('--output', type=Path, default=Path('outputs/critic_scores'),
                        help="Output directory for critic score files")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        input_files = collect_input_files(args.files, args.input)
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return

    if not input_files:
        print("Error: No input files specified")
        print("Usage: python scripts/capture_critic_scores.py outputs/sample_mode_*.json")
        return

    print(f"Processing {len(input_files)} sample-mode files...\n")
    success_count = 0
    for input_file in input_files:
        if not input_file.exists():
            print(f"⚠️ File not found: {input_file}")
            continue
        print(f"Processing {input_file.name}...")
        if process_sample_file(input_file, args.output):
            success_count += 1
        print("")

    print("=" * 60)
    print(f"Processed {success_count}/{len(input_files)} files successfully")
    print(f"Critic scores saved to {args.output}")
    print("=" * 60)
    print("")
    print("Next steps:")
    print("1. Run more sample-mode tests: python src/main.py sample-mode --count 50 --save-to-file")
    print("2. Capture more scores: python scripts/capture_critic_scores.py outputs/sample_mode_*.json")
    print(f"3. Compare distributions: python scripts/compare_critic_scores.py --baseline outputs/baseline_metrics/ --current {args.output}")


if __name__ == '__main__':
    main()

