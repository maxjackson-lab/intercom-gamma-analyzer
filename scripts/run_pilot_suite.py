#!/usr/bin/env python3
"""
Run Pilot Suite - Execute Multiple DeepAgents Pilot Configurations

Runs `run_deepagents_pilot.py` with varied configurations to ensure
robust comparison data for Phase 5 adoption decision.

Usage:
    python scripts/run_pilot_suite.py --quick   # Test-mode only (fast)
    python scripts/run_pilot_suite.py --full    # All configurations including real data
    python scripts/run_pilot_suite.py           # Default: quick mode
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

try:
    from rich.console import Console
    from rich.table import Table
    console = Console()
except ImportError:
    # Fallback if rich not installed
    class Console:
        def print(self, *args, **kwargs):
            text = args[0] if args else ""
            # Strip rich markup
            import re
            text = re.sub(r'\[.*?\]', '', str(text))
            print(text)
    console = Console()


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class PilotConfig:
    """Configuration for a single pilot run."""
    name: str
    time_period: str
    periods_back: int
    count: int
    test_mode: bool
    ai_model: str
    analysis_type: str = "topic-based"
    include_trends: bool = False
    llm_topic_detection: bool = False
    digest_mode: bool = False
    detail_level: str = "standard"


# Configuration matrix for pilot runs
QUICK_CONFIGS = [
    PilotConfig(
        name="test-mode-50-openai",
        time_period="week",
        periods_back=1,
        count=50,
        test_mode=True,
        ai_model="openai",
    ),
    PilotConfig(
        name="test-mode-100-openai",
        time_period="week",
        periods_back=1,
        count=100,
        test_mode=True,
        ai_model="openai",
    ),
    PilotConfig(
        name="test-mode-50-openai-trends",
        time_period="week",
        periods_back=1,
        count=50,
        test_mode=True,
        ai_model="openai",
        include_trends=True,
    ),
]

FULL_CONFIGS = QUICK_CONFIGS + [
    PilotConfig(
        name="real-data-last-week",
        time_period="week",
        periods_back=1,
        count=0,  # Not used for real data
        test_mode=False,
        ai_model="openai",
    ),
    PilotConfig(
        name="real-data-2-weeks",
        time_period="week",
        periods_back=2,
        count=0,
        test_mode=False,
        ai_model="openai",
        digest_mode=True,
    ),
    PilotConfig(
        name="test-mode-100-comprehensive",
        time_period="week",
        periods_back=1,
        count=100,
        test_mode=True,
        ai_model="openai",
        analysis_type="complete",
        detail_level="comprehensive",
    ),
]


@dataclass
class PilotResult:
    """Result of a single pilot run."""
    config: PilotConfig
    success: bool
    output_dir: Optional[Path]
    error: Optional[str]
    duration_seconds: float


def build_pilot_command(config: PilotConfig, output_dir: Path) -> List[str]:
    """Build the command line arguments for run_deepagents_pilot.py."""
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "run_deepagents_pilot.py"),
        "--time-period", config.time_period,
        "--periods-back", str(config.periods_back),
        "--ai-model", config.ai_model,
        "--analysis-type", config.analysis_type,
        "--detail-level", config.detail_level,
        "--output-dir", str(output_dir),
    ]
    
    if config.test_mode:
        cmd.extend(["--test-mode", "--count", str(config.count)])
    
    if config.include_trends:
        cmd.append("--include-trends")
    
    if config.llm_topic_detection:
        cmd.append("--llm-topic-detection")
    
    if config.digest_mode:
        cmd.append("--digest-mode")
    
    return cmd


async def run_single_pilot(config: PilotConfig, output_dir: Path) -> PilotResult:
    """Execute a single pilot configuration."""
    cmd = build_pilot_command(config, output_dir)
    start_time = datetime.now()
    
    console.print(f"\n[cyan]Running: {config.name}[/cyan]")
    console.print(f"[dim]Command: {' '.join(cmd)}[/dim]")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minute timeout per run
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        if result.returncode == 0:
            # Find the output directory created by the pilot
            pilot_dirs = sorted(output_dir.glob("*"))
            latest_dir = pilot_dirs[-1] if pilot_dirs else None
            
            console.print(f"[green]✅ {config.name} completed in {duration:.1f}s[/green]")
            return PilotResult(
                config=config,
                success=True,
                output_dir=latest_dir,
                error=None,
                duration_seconds=duration,
            )
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            console.print(f"[red]❌ {config.name} failed: {error_msg[:200]}[/red]")
            return PilotResult(
                config=config,
                success=False,
                output_dir=None,
                error=error_msg,
                duration_seconds=duration,
            )
    
    except subprocess.TimeoutExpired:
        duration = (datetime.now() - start_time).total_seconds()
        console.print(f"[red]❌ {config.name} timed out after {duration:.1f}s[/red]")
        return PilotResult(
            config=config,
            success=False,
            output_dir=None,
            error="Timeout after 30 minutes",
            duration_seconds=duration,
        )
    
    except Exception as exc:
        duration = (datetime.now() - start_time).total_seconds()
        console.print(f"[red]❌ {config.name} error: {exc}[/red]")
        return PilotResult(
            config=config,
            success=False,
            output_dir=None,
            error=str(exc),
            duration_seconds=duration,
        )


def print_summary(results: List[PilotResult]) -> None:
    """Print summary table of all pilot runs."""
    console.print("\n" + "=" * 70)
    console.print("[bold]PILOT SUITE SUMMARY[/bold]")
    console.print("=" * 70 + "\n")
    
    success_count = sum(1 for r in results if r.success)
    fail_count = len(results) - success_count
    
    try:
        table = Table(title="Pilot Run Results")
        table.add_column("Configuration", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Duration", style="yellow")
        table.add_column("Output Directory")
        
        for r in results:
            status = "✅ Success" if r.success else "❌ Failed"
            duration = f"{r.duration_seconds:.1f}s"
            output = str(r.output_dir.name) if r.output_dir else r.error or "N/A"
            table.add_row(r.config.name, status, duration, output[:40])
        
        console.print(table)
    except Exception:
        # Fallback if Table not available
        for r in results:
            status = "✅" if r.success else "❌"
            console.print(f"  {status} {r.config.name}: {r.duration_seconds:.1f}s")
    
    console.print(f"\n[bold]Total:[/bold] {success_count} succeeded, {fail_count} failed")
    
    if success_count > 0:
        console.print("\n[bold]Next Steps:[/bold]")
        console.print("  1. Review pilot outputs in outputs/deepagents_pilot/")
        console.print("  2. Run analysis: python scripts/analyze_deepagents_pilot.py")
        console.print("  3. Review decision report: outputs/deepagents_pilot/phase5_decision_analysis.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run DeepAgents pilot suite with multiple configurations"
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--quick',
        action='store_true',
        help="Run only test-mode configurations (fast validation)"
    )
    mode_group.add_argument(
        '--full',
        action='store_true',
        help="Run all configurations including real data"
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('outputs/deepagents_pilot'),
        help="Base output directory for pilot runs"
    )
    parser.add_argument(
        '--continue-on-error',
        action='store_true',
        default=False,
        help="Continue running remaining configs if one fails (default: stop on first failure)"
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    
    # Select configuration set
    if args.full:
        configs = FULL_CONFIGS
        mode = "Full Suite"
    else:
        configs = QUICK_CONFIGS
        mode = "Quick Suite"
    
    console.print(f"\n[bold cyan]DeepAgents Pilot Suite - {mode}[/bold cyan]")
    console.print(f"Running {len(configs)} configurations...")
    console.print(f"Output directory: {args.output_dir}")
    
    # Ensure output directory exists
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Run each configuration sequentially
    results: List[PilotResult] = []
    
    for i, config in enumerate(configs, 1):
        console.print(f"\n[bold]Configuration {i}/{len(configs)}[/bold]")
        result = await run_single_pilot(config, args.output_dir)
        results.append(result)
        
        if not result.success and not args.continue_on_error:
            console.print("[red]Stopping due to failure (use --continue-on-error to continue)[/red]")
            break
    
    # Print summary
    print_summary(results)
    
    # Exit with appropriate code
    if all(r.success for r in results):
        console.print("\n[green]✅ All pilot runs completed successfully![/green]")
        sys.exit(0)
    else:
        fail_count = sum(1 for r in results if not r.success)
        console.print(f"\n[yellow]⚠️  {fail_count} pilot run(s) failed[/yellow]")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
