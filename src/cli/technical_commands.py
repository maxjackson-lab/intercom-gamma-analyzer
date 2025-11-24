"""
Technical CLI command implementations extracted from src/main.py during
Phase 1.5 of the CLI refactor.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from src.cli.utils import console, setup_verbose_logging, show_audit_trail_enabled
from src.cli.category_commands import run_technical_troubleshooting_analysis
from src.config.test_data import parse_test_data_count, get_preset_display_name
from src.utils.time_utils import calculate_date_range


async def run_macro_analysis(start_date: datetime, end_date: datetime, min_occurrences: int):
    """Run macro discovery analysis."""
    console.print("[yellow]Macro analysis not yet implemented[/yellow]")
    console.print(
        f"Would analyze {min_occurrences}+ occurrences from {start_date.date()} to {end_date.date()}"
    )


async def run_fin_analysis(start_date: datetime, end_date: datetime, detailed: bool):
    """Run Fin escalation analysis."""
    console.print("[yellow]Fin analysis not yet implemented[/yellow]")
    console.print(f"Would analyze Fin effectiveness from {start_date.date()} to {end_date.date()}")


async def run_tech_analysis_command(
    days: int,
    start_date: Optional[str],
    end_date: Optional[str],
    time_period: Optional[str],
    periods_back: int,
    output_format: str,
    gamma_export: Optional[str],
    output_dir: str,
    test_mode: bool,
    test_data_count: str,
    verbose: bool,
    audit_trail: bool,
    ai_model: Optional[str],
    filter_category: Optional[str],
    max_pages: Optional[int],
):
    """Shared implementation for the `tech-analysis` CLI command."""
    # Deprecation warning for --days
    if days != 30 or (not time_period and not start_date and not end_date):
        console.print(
            "[yellow]⚠️  Warning: --days is deprecated. Please use --time-period and --periods-back instead.[/yellow]"
        )
        console.print(
            "[yellow]   Example: --time-period month --periods-back 1 (for last 30 days)[/yellow]"
        )

    console.print("[bold green]Technical Troubleshooting Analysis[/bold green]")

    # Set AI model if specified
    if ai_model:
        os.environ['AI_MODEL'] = ai_model
        console.print(f"[cyan]🤖 AI Model: {ai_model.upper()}[/cyan]")

    # Enable verbose logging if requested
    if verbose:
        setup_verbose_logging()

    # Audit trail indication
    if audit_trail:
        show_audit_trail_enabled()

    # Parse test data count
    try:
        test_count, preset_name = parse_test_data_count(test_data_count)
        preset_display = get_preset_display_name(test_count, preset_name)
    except ValueError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        return

    # Test mode indication
    if test_mode:
        console.print(f"[yellow]🧪 Test Mode: ENABLED ({preset_display})[/yellow]")

    # Calculate date range using shared utility
    try:
        start_dt, end_dt = calculate_date_range(
            time_period=time_period,
            periods_back=periods_back,
            start_date=start_date,
            end_date=end_date,
            end_is_yesterday=True,
        )
        console.print(f"Analyzing: {start_dt.date()} to {end_dt.date()}")
    except ValueError as exc:
        # Fallback to --days if time range not specified
        if not time_period and not (start_date and end_date):
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=days)
            console.print(f"Analyzing last {days} days of conversations")
        else:
            console.print(f"[red]Error: {exc}[/red]")
            return

    taxonomy_target = (filter_category or 'Bug').strip() or 'Bug'
    generate_gamma = output_format == 'gamma'

    if output_format not in ['markdown', 'gamma']:
        console.print(
            "[yellow]⚠️  Technical troubleshooting now outputs Narrative V2 markdown (JSON/Excel unsupported).[/yellow]"
        )
        console.print(
            "        Use --output-format markdown (default) or --output-format gamma for deck output.\n"
        )

    if max_pages:
        console.print(
            "[dim]ℹ️  max-pages is ignored in the new multi-agent pipeline (kept for backward compatibility).[/dim]"
        )

    console.print(f"[cyan]Applying taxonomy filter: {taxonomy_target}[/cyan]\n")

    await run_technical_troubleshooting_analysis(
        start_dt,
        end_dt,
        taxonomy_filter=taxonomy_target,
        generate_gamma=generate_gamma,
        audit_trail=audit_trail,
    )


__all__ = ['run_macro_analysis', 'run_fin_analysis', 'run_tech_analysis_command']

