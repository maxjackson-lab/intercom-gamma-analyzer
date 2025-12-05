#!/usr/bin/env python3
"""
Validate Phase 5 Decision Documentation

Verifies that Phase 5 decision documentation is complete and consistent
before rollout. Checks required artifacts, validates metrics, and ensures
documentation alignment.

Exit Codes:
    0: All validations passed, ready for rollout
    1: Missing required artifacts
    2: Insufficient pilot data
    3: Decision documentation incomplete
    4: Rollout plan missing (if ADOPT)

Usage:
    python scripts/validate_phase5_decision.py
    python scripts/validate_phase5_decision.py --strict  # Fail on warnings
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from rich.console import Console
    from rich.table import Table
    console = Console()
except ImportError:
    class Console:
        def print(self, *args, **kwargs):
            text = args[0] if args else ""
            import re as re_mod
            text = re_mod.sub(r'\[.*?\]', '', str(text))
            print(text)
    console = Console()


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PILOT_DIR = PROJECT_ROOT / "outputs" / "deepagents_pilot"
MIGRATION_DOC = PROJECT_ROOT / "docs" / "LANGCHAIN_ARCHITECTURE_MIGRATION.md"
ROLLOUT_CHECKLIST = PROJECT_ROOT / "docs" / "PHASE_5_ROLLOUT_CHECKLIST.md"
README = PROJECT_ROOT / "README.md"
SETTINGS = PROJECT_ROOT / "src" / "config" / "settings.py"

MIN_RUNS_PER_ORCHESTRATOR = 3


class ValidationResult:
    """Tracks validation results."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed: List[str] = []
        self.decision: Optional[str] = None
    
    def add_error(self, message: str) -> None:
        self.errors.append(message)
    
    def add_warning(self, message: str) -> None:
        self.warnings.append(message)
    
    def add_passed(self, message: str) -> None:
        self.passed.append(message)
    
    def is_valid(self, strict: bool = False) -> bool:
        if self.errors:
            return False
        if strict and self.warnings:
            return False
        return True


def check_pilot_directory(result: ValidationResult) -> bool:
    """Check that pilot directory exists with sufficient data."""
    if not PILOT_DIR.exists():
        result.add_error(f"Pilot directory not found: {PILOT_DIR}")
        return False
    
    result.add_passed(f"Pilot directory exists: {PILOT_DIR}")
    
    # Count comparison.json files
    comparison_files = list(PILOT_DIR.rglob("comparison.json"))
    if not comparison_files:
        result.add_error("No comparison.json files found in pilot directory")
        return False
    
    result.add_passed(f"Found {len(comparison_files)} pilot run(s)")
    
    # Parse and count successful runs per orchestrator
    legacy_success = 0
    deep_success = 0
    
    for filepath in comparison_files:
        try:
            with open(filepath, encoding='utf-8') as f:
                data = json.load(f)
            if data.get('legacy', {}).get('status') == 'completed':
                legacy_success += 1
            if data.get('deep', {}).get('status') == 'completed':
                deep_success += 1
        except Exception:
            continue
    
    if legacy_success < MIN_RUNS_PER_ORCHESTRATOR:
        result.add_error(f"Insufficient legacy runs: {legacy_success} (need ≥{MIN_RUNS_PER_ORCHESTRATOR})")
    else:
        result.add_passed(f"Legacy runs: {legacy_success} successful")
    
    if deep_success < MIN_RUNS_PER_ORCHESTRATOR:
        result.add_error(f"Insufficient deep runs: {deep_success} (need ≥{MIN_RUNS_PER_ORCHESTRATOR})")
    else:
        result.add_passed(f"Deep runs: {deep_success} successful")
    
    return legacy_success >= MIN_RUNS_PER_ORCHESTRATOR and deep_success >= MIN_RUNS_PER_ORCHESTRATOR


def check_analysis_artifacts(result: ValidationResult) -> bool:
    """Check that analysis artifacts exist."""
    analysis_md = PILOT_DIR / "phase5_decision_analysis.md"
    metrics_json = PILOT_DIR / "phase5_metrics_summary.json"
    
    artifacts_ok = True
    
    if not analysis_md.exists():
        result.add_error(f"Decision analysis not found: {analysis_md}")
        result.add_warning("Run `python scripts/analyze_deepagents_pilot.py` to generate")
        artifacts_ok = False
    else:
        result.add_passed(f"Decision analysis exists: {analysis_md}")
    
    if not metrics_json.exists():
        result.add_error(f"Metrics summary not found: {metrics_json}")
        artifacts_ok = False
    else:
        result.add_passed(f"Metrics summary exists: {metrics_json}")
        
        # Validate JSON structure
        try:
            with open(metrics_json, encoding='utf-8') as f:
                data = json.load(f)
            
            required_keys = ['recommendation', 'thresholds', 'orchestrators']
            for key in required_keys:
                if key not in data:
                    result.add_warning(f"Metrics summary missing key: {key}")
            
            result.decision = data.get('recommendation')
            if result.decision:
                result.add_passed(f"Recommendation found: {result.decision}")
            else:
                result.add_warning("No recommendation found in metrics summary")

            # Validate thresholds structure
            thresholds = data.get('thresholds', {})
            expected_thresholds = [
                'critic_score_improvement',
                'runtime_penalty',
                'token_efficiency',
                'legacy_success_rate',
                'deep_success_rate',
            ]
            for key in expected_thresholds:
                if key not in thresholds:
                    result.add_error(f"Threshold missing: {key}")
                    continue
                entry = thresholds.get(key, {})
                for required_field in ('value', 'target', 'met'):
                    if required_field not in entry:
                        result.add_warning(f"Threshold '{key}' missing field: {required_field}")

            # Validate orchestrator data
            orchestrators = data.get('orchestrators', {})
            for orch in ('legacy', 'deep'):
                orch_data = orchestrators.get(orch)
                if not orch_data:
                    result.add_error(f"Orchestrator data missing: {orch}")
                    continue
                runs = orch_data.get('runs', 0)
                success_rate = orch_data.get('success_rate', 0)
                if runs <= 0:
                    result.add_warning(f"{orch.title()} runs not recorded or zero")
                if success_rate <= 0:
                    result.add_warning(f"{orch.title()} success_rate missing or zero")
        
        except json.JSONDecodeError as e:
            result.add_error(f"Invalid JSON in metrics summary: {e}")
            artifacts_ok = False
    
    return artifacts_ok


def check_migration_doc(result: ValidationResult) -> Tuple[bool, Optional[str]]:
    """Check that migration doc has Phase 5 section with decision."""
    if not MIGRATION_DOC.exists():
        result.add_error(f"Migration doc not found: {MIGRATION_DOC}")
        return False, None
    
    result.add_passed(f"Migration doc exists: {MIGRATION_DOC}")
    
    content = MIGRATION_DOC.read_text(encoding='utf-8')
    
    # Check for Phase 5 section
    if "## Phase 5" not in content:
        result.add_error("Phase 5 section not found in migration doc")
        return False, None
    
    result.add_passed("Phase 5 section found in migration doc")
    
    # Extract decision status
    decision_match = re.search(r'Status:\s*\[?(PENDING|ADOPT|DEFER|REJECT)', content, re.IGNORECASE)
    if decision_match:
        decision = decision_match.group(1).upper()
        result.add_passed(f"Decision status found: {decision}")
        return True, decision
    else:
        result.add_warning("Decision status not clearly marked in Phase 5 section")
        return True, None


def check_rollout_checklist(result: ValidationResult, decision: Optional[str]) -> bool:
    """Check rollout checklist exists if decision is ADOPT."""
    if decision != "ADOPT":
        result.add_passed("Rollout checklist not required (decision is not ADOPT)")
        return True
    
    if not ROLLOUT_CHECKLIST.exists():
        result.add_error(f"Rollout checklist not found: {ROLLOUT_CHECKLIST}")
        result.add_warning("Create `docs/PHASE_5_ROLLOUT_CHECKLIST.md` for ADOPT decision")
        return False
    
    result.add_passed(f"Rollout checklist exists: {ROLLOUT_CHECKLIST}")
    
    content = ROLLOUT_CHECKLIST.read_text(encoding='utf-8')
    
    # Check for required sections
    required_sections = [
        "Pre-Rollout Validation",
        "Phase 5.1",
        "Phase 5.2",
        "Phase 5.3",
        "Phase 5.4",
        "Rollback Plan",
    ]
    
    for section in required_sections:
        if section not in content:
            result.add_warning(f"Missing section in rollout checklist: {section}")
    
    return True


def check_readme_docs(result: ValidationResult) -> bool:
    """Check README documents deepagents installation."""
    if not README.exists():
        result.add_warning(f"README not found: {README}")
        return False
    
    content = README.read_text(encoding='utf-8')
    
    if "deepagents" in content.lower():
        result.add_passed("README documents deepagents")
    else:
        result.add_warning("README does not mention deepagents")
    
    if "--orchestrator" in content:
        result.add_passed("README documents --orchestrator flag")
    else:
        result.add_warning("README does not document --orchestrator flag")
    
    return True


def check_settings_flag(result: ValidationResult) -> bool:
    """Check settings.py has enable_deep_orchestrator flag."""
    if not SETTINGS.exists():
        result.add_warning(f"Settings file not found: {SETTINGS}")
        return False
    
    content = SETTINGS.read_text(encoding='utf-8')
    
    if "enable_deep_orchestrator" in content:
        result.add_passed("Settings contains enable_deep_orchestrator flag")
        return True
    else:
        result.add_warning("Settings missing enable_deep_orchestrator flag")
        return False


def generate_validation_report(result: ValidationResult, output_path: Path) -> None:
    """Generate validation report markdown file."""
    lines = [
        "# Phase 5 Validation Report",
        "",
        f"**Generated:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Overall Status:** {'✅ PASSED' if result.is_valid() else '❌ FAILED'}",
        "",
    ]
    
    if result.decision:
        lines.extend([
            f"**Decision:** {result.decision}",
            "",
        ])
    
    lines.extend([
        "## Passed Checks",
        "",
    ])
    for item in result.passed:
        lines.append(f"- ✅ {item}")
    
    if result.warnings:
        lines.extend([
            "",
            "## Warnings",
            "",
        ])
        for item in result.warnings:
            lines.append(f"- ⚠️  {item}")
    
    if result.errors:
        lines.extend([
            "",
            "## Errors",
            "",
        ])
        for item in result.errors:
            lines.append(f"- ❌ {item}")
    
    lines.extend([
        "",
        "## Next Steps",
        "",
    ])
    
    if result.is_valid():
        if result.decision == "ADOPT":
            lines.extend([
                "1. Review rollout checklist: `docs/PHASE_5_ROLLOUT_CHECKLIST.md`",
                "2. Begin Phase 5.1 soft launch",
                "3. Monitor pilot usage in production",
            ])
        elif result.decision == "DEFER":
            lines.extend([
                "1. Review conditions for re-evaluation in migration doc",
                "2. Collect additional pilot data as specified",
                "3. Re-run analysis when conditions are met",
            ])
        else:
            lines.extend([
                "1. Continue with legacy orchestrator",
                "2. Review alternative approaches in migration doc",
            ])
    else:
        lines.extend([
            "1. Fix the errors listed above",
            "2. Re-run validation: `python scripts/validate_phase5_decision.py`",
        ])
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding='utf-8')
    console.print(f"[dim]Validation report saved to {output_path}[/dim]")


def print_results(result: ValidationResult) -> None:
    """Print validation results to console."""
    console.print("\n" + "=" * 60)
    console.print("[bold]PHASE 5 VALIDATION RESULTS[/bold]")
    console.print("=" * 60 + "\n")
    
    console.print("[bold green]Passed Checks:[/bold green]")
    for item in result.passed:
        console.print(f"  ✅ {item}")
    
    if result.warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for item in result.warnings:
            console.print(f"  ⚠️  {item}")
    
    if result.errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for item in result.errors:
            console.print(f"  ❌ {item}")
    
    console.print("\n" + "-" * 60)
    
    if result.is_valid():
        console.print("[bold green]✅ Validation PASSED[/bold green]")
        if result.decision:
            console.print(f"   Decision: {result.decision}")
    else:
        console.print("[bold red]❌ Validation FAILED[/bold red]")
        console.print("   Fix errors before proceeding with rollout")
    
    console.print("=" * 60 + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Phase 5 decision documentation completeness"
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help="Fail on warnings in addition to errors"
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=PILOT_DIR / "phase5_validation_report.md",
        help="Output path for validation report"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    result = ValidationResult()
    
    console.print("\n[bold cyan]Phase 5 Decision Validation[/bold cyan]")
    console.print("Checking required artifacts and documentation...\n")
    
    # Check 1: Pilot directory and data
    console.print("[bold]1. Checking pilot data...[/bold]")
    pilot_ok = check_pilot_directory(result)
    
    # Check 2: Analysis artifacts
    console.print("\n[bold]2. Checking analysis artifacts...[/bold]")
    artifacts_ok = check_analysis_artifacts(result)
    
    # Check 3: Migration doc
    console.print("\n[bold]3. Checking migration documentation...[/bold]")
    doc_ok, doc_decision = check_migration_doc(result)
    
    # Use decision from metrics if not found in doc
    decision = result.decision or doc_decision
    
    # Check 4: Rollout checklist (if ADOPT)
    console.print("\n[bold]4. Checking rollout readiness...[/bold]")
    rollout_ok = check_rollout_checklist(result, decision)
    
    # Check 5: README docs
    console.print("\n[bold]5. Checking README documentation...[/bold]")
    readme_ok = check_readme_docs(result)
    
    # Check 6: Settings flag
    console.print("\n[bold]6. Checking settings configuration...[/bold]")
    settings_ok = check_settings_flag(result)
    
    # Generate report
    generate_validation_report(result, args.output)
    
    # Print results
    print_results(result)
    
    # Determine exit code
    if result.errors:
        # Categorize error type for specific exit codes
        has_missing_artifacts = any("not found" in e for e in result.errors)
        has_insufficient_data = any("Insufficient" in e for e in result.errors)
        has_doc_issues = any("section not found" in e for e in result.errors)
        has_rollout_issues = any("Rollout checklist" in e for e in result.errors)
        
        if has_missing_artifacts:
            sys.exit(1)
        elif has_insufficient_data:
            sys.exit(2)
        elif has_doc_issues:
            sys.exit(3)
        elif has_rollout_issues:
            sys.exit(4)
        else:
            sys.exit(1)
    
    if args.strict and result.warnings:
        console.print("[yellow]Strict mode: failing due to warnings[/yellow]")
        sys.exit(1)
    
    console.print("[green]✅ Phase 5 validation complete[/green]")
    sys.exit(0)


if __name__ == '__main__':
    main()
