"""
Main CLI application for Intercom to Gamma analysis tool.

This is the main entry point for the CLI application. The actual command
implementations have been refactored into modular components in src/cli/
for better maintainability and testability.
"""

import asyncio
import logging
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

# Suppress urllib3 SSL warning
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')

# Suppress Pydantic serializer warnings from Intercom SDK
# The SDK has type mismatches (int vs str) that trigger harmless warnings
warnings.filterwarnings('ignore', category=UserWarning, message='.*Pydantic serializer warnings.*')
warnings.filterwarnings('ignore', category=UserWarning, message='.*Expected.*but got.*serialized value.*')

import click
from rich.panel import Panel

# Note: CLI module exists but implementations are still in this file for now
# TODO: Complete migration to src/cli/ module structure

# Core imports for basic functionality
from src.cli.entry import cli
from src.cli.flags import standard_flags, validate_sample_count
from src.cli.system_commands import (
    run_config_command,
    run_examples_command,
    run_help_command,
    run_interactive_command,
    run_list_commands_command,
    run_show_categories_command,
    run_system_info_command,
    run_test_command,
)
from src.cli.export_commands import (
    run_custom_analysis,
    run_data_export,
    run_general_query,
    save_json_output,
    save_markdown_output,
    generate_gamma_presentation,
)
from src.cli.utils import console, setup_verbose_logging, show_audit_trail_enabled
from src.cli.voc_commands import (
    run_comprehensive_analysis as run_comprehensive_analysis_impl,
    run_voice_of_customer_analysis as run_voice_of_customer_analysis_impl,
)
from src.cli.category_commands import (
    run_api_analysis,
    run_all_categories_analysis_v2,
    run_billing_analysis,
    run_product_analysis,
    run_sites_analysis,
    run_technical_troubleshooting_analysis,
)
from src.cli.agent_commands import (
    run_agent_analysis,
    run_agent_coaching_report,
    run_agent_performance_analysis,
)
from src.cli.technical_commands import (
    run_fin_analysis,
    run_macro_analysis,
    run_tech_analysis_command,
)
from src.cli.canny_commands import run_canny_analysis
from src.cli.gamma_commands import run_gamma_generation, run_bulk_gamma_generation
from src.cli.sample_commands import run_sample_mode_command, run_test_mode_command
from src.cli.chat_commands import run_chat_interface
from src.cli.legacy_category_commands import (
    run_category_analysis,
    run_all_categories_analysis,
    run_synthesis_analysis,
    run_custom_tag_analysis,
    run_escalation_analysis,
    run_pattern_analysis,
)
from src.config.settings import settings
from src.models.analysis_models import AnalysisRequest, AnalysisMode

# ============================================================================
# Phase 1.6: Final CLI Refactor Complete (Canny, Gamma, Sample, Chat, Legacy)
# ============================================================================
# Remaining commands extracted to:
# - src/cli/canny_commands.py (Canny analysis)
# - src/cli/gamma_commands.py (Gamma generation)
# - src/cli/sample_commands.py (Sample/test modes)
# - src/cli/chat_commands.py (Interactive chat)
# - src/cli/legacy_category_commands.py (Deprecated category commands)
#
# Total reduction: ~1,499 lines (from 2,965 to ~1,466)
# ============================================================================

# ============================================================================
# Phase 1.4: VoC & Category Commands (Extracted to src/cli/voc_commands.py
# and src/cli/category_commands.py)
# ============================================================================

# DISABLED: This command uses unfinished CLI refactoring - use 'voice-of-customer' instead
# @cli.command()
# @click.option('--month', type=int, required=True, help='Month (1-12)')
# @click.option('--year', type=int, required=True, help='Year')
# @click.option('--tier1-countries', help='Comma-separated tier 1 countries')
# @click.option('--generate-gamma', is_flag=True, help='Generate Gamma presentation')
# @click.option('--output-format', type=click.Choice(['gamma', 'markdown', 'json']), default='markdown')
# @click.option('--multi-agent', is_flag=True, help='Use multi-agent mode (premium quality, 3-5x cost)')
# @click.option('--analysis-type', type=click.Choice(['standard', 'topic-based', 'synthesis']), default='standard',
#               help='Analysis type: standard (single), topic-based (Hilary format), synthesis (insights)')
# @click.option('--ai-model', type=click.Choice(['openai', 'claude']), default=None,
#               help='AI model to use (openai or claude). Defaults to config setting.')
# def voice(month: int, year: int, tier1_countries: Optional[str], generate_gamma: bool, output_format: str, multi_agent: bool, analysis_type: str, ai_model: Optional[str]):
#     """Generate Voice of Customer analysis for monthly executive reports"""
#
#     # Parse tier1 countries
#     tier1_list = []
#     if tier1_countries:
#         tier1_list = [country.strip() for country in tier1_countries.split(',')]
#     else:
#         tier1_list = settings.default_tier1_countries
#
#     # Use modular command implementation
#     asyncio.run(voice_analysis(
#         month=month,
#         year=year,
#         tier1_countries=tier1_list,
#         generate_gamma=generate_gamma,
#         output_format=output_format,
#         multi_agent=multi_agent,
#         analysis_type=analysis_type,
#         ai_model=ai_model
#     ))


# DISABLED: This command uses unfinished CLI refactoring
# @cli.command()
# @click.option('--start-date', required=True, help='Start date (YYYY-MM-DD)')
# @click.option('--end-date', required=True, help='End date (YYYY-MM-DD)')
# @click.option('--focus-areas', help='Comma-separated focus areas (e.g., billing,product,escalations)')
# @click.option('--custom-prompt', help='Custom analysis instructions')
# @click.option('--generate-gamma', is_flag=True, help='Generate Gamma presentation')
# @click.option('--output-format', type=click.Choice(['gamma', 'markdown', 'json']), default='markdown')
# def trends(start_date: str, end_date: str, focus_areas: Optional[str],
#            custom_prompt: Optional[str], generate_gamma: bool, output_format: str):
#     """Generate general purpose trend analysis for any time period"""
#
#     # Parse focus areas
#     focus_list = []
#     if focus_areas:
#         focus_list = [area.strip() for area in focus_areas.split(',')]
#
#     # Use modular command implementation
#     asyncio.run(trend_analysis(
#         start_date=start_date,
#         end_date=end_date,
#         focus_areas=focus_list,
#         custom_prompt=custom_prompt,
#         generate_gamma=generate_gamma,
#         output_format=output_format
#     ))


@cli.command()
@click.option('--prompt-file', required=True, help='Path to custom prompt file')
@click.option('--start-date', required=True, help='Start date (YYYY-MM-DD)')
@click.option('--end-date', required=True, help='End date (YYYY-MM-DD)')
@click.option('--generate-gamma', is_flag=True, help='Generate Gamma presentation')
@click.option('--output-format', type=click.Choice(['gamma', 'markdown', 'json']), default='markdown')
def custom(prompt_file: str, start_date: str, end_date: str, generate_gamma: bool, output_format: str):
    """Generate analysis with custom prompt"""
    
    # Read custom prompt
    try:
        with open(prompt_file, 'r') as f:
            custom_prompt = f.read()
    except FileNotFoundError:
        console.print(f"[red]Error: Prompt file not found: {prompt_file}[/red]")
        sys.exit(1)
    
    # Parse dates (keep as datetime objects for pipeline compatibility)
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        console.print("[red]Error: Invalid date format. Use YYYY-MM-DD[/red]")
        sys.exit(1)
    
    console.print(f"[bold green]Custom Analysis[/bold green]")
    console.print(f"Date Range: {start_date} to {end_date}")
    console.print(f"Prompt File: {prompt_file}")
    
    # Create analysis request
    request = AnalysisRequest(
        mode=AnalysisMode.CUSTOM,
        start_date=start_dt,
        end_date=end_dt,
        custom_prompt=custom_prompt
    )
    
    # Run analysis
    asyncio.run(run_custom_analysis(request, generate_gamma, output_format))


@cli.command()
def test():
    """Test API connections and configuration"""
    run_test_command()


@cli.command()
def system_info():
    """Show system information for debugging"""
    run_system_info_command()


@cli.command(name='list-snapshots')
@click.option('--type', '-t', 'analysis_type',
              type=click.Choice(['weekly', 'monthly', 'quarterly']),
              help='Filter by snapshot type')
@click.option('--limit', '-l', type=int, default=10,
              help='Maximum number of snapshots to display')
@click.option('--show-reviewed', is_flag=True,
              help='Show only reviewed snapshots')
@click.option('--show-unreviewed', is_flag=True,
              help='Show only unreviewed snapshots')
def list_snapshots_cmd(analysis_type: Optional[str], limit: int, show_reviewed: bool, show_unreviewed: bool):
    """List historical analysis snapshots"""
    from src.cli.snapshot_commands import list_snapshots
    asyncio.run(list_snapshots(analysis_type, limit, show_reviewed, show_unreviewed))


@cli.command(name='export-snapshot-schema')
@click.option('--output', '-o', 'output_file',
              help='Output file path for schema JSON')
@click.option('--type', '-t', 'schema_type',
              type=click.Choice(['snapshot', 'comparison', 'all']),
              default='all',
              help='Schema type to export')
def export_snapshot_schema_cmd(output_file: Optional[str], schema_type: str):
    """Export JSON schema for snapshot data models (API documentation)"""
    from src.cli.snapshot_commands import export_snapshot_schema
    asyncio.run(export_snapshot_schema(output_file, schema_type))


@cli.command(name='compare-snapshots')
@click.option('--current', '-c', 'current_id', required=True,
              help='Snapshot ID for current period (e.g., weekly_20251114)')
@click.option('--prior', '-p', 'prior_id', required=True,
              help='Snapshot ID for prior period (e.g., weekly_20251107)')
@click.option('--show-details', '-d', is_flag=True, default=False,
              help='Show detailed comparison including sentiment and resolution metrics')
def compare_snapshots_cmd(current_id: str, prior_id: str, show_details: bool):
    """Compare two analysis snapshots"""
    from src.cli.snapshot_commands import compare_snapshots
    
    console.print("[bold]Comparing Analysis Snapshots[/bold]")
    console.print(f"Current: {current_id}")
    console.print(f"Prior: {prior_id}")
    console.print("")
    
    result = asyncio.run(compare_snapshots(current_id, prior_id, show_details))
    
    if 'error' in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)
    
    sys.exit(0)


@cli.command()
@click.option('--start-date', required=True, help='Start date (YYYY-MM-DD)')
@click.option('--end-date', required=True, help='End date (YYYY-MM-DD)')
@click.option('--export-format', type=click.Choice(['excel', 'csv', 'json', 'parquet', 'all']), default='excel', help='Export format')
@click.option('--max-pages', type=int, help='Maximum pages to fetch')
@click.option('--include-metrics', is_flag=True, help='Include calculated metrics in export')
def export(start_date: str, end_date: str, export_format: str, max_pages: Optional[int], include_metrics: bool):
    """Export raw conversation data to spreadsheets and other formats"""
    
    # Parse dates (keep as datetime objects for pipeline compatibility)
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        console.print("[red]Error: Invalid date format. Use YYYY-MM-DD[/red]")
        sys.exit(1)
    
    console.print(f"[bold green]Data Export[/bold green]")
    console.print(f"Date Range: {start_date} to {end_date}")
    console.print(f"Export Format: {export_format}")
    
    # Run export
    asyncio.run(run_data_export(start_dt, end_dt, export_format, max_pages, include_metrics))


@cli.command()
@click.option('--query-type', type=click.Choice(['time_based', 'state_based', 'source_based', 'satisfaction_based', 'geographic_based', 'content_based']), help='Type of query to build')
@click.option('--suggestion', help='Specific query suggestion')
@click.option('--custom-query', help='Custom query JSON')
@click.option('--export-format', type=click.Choice(['excel', 'csv', 'json', 'parquet']), default='excel', help='Export format')
@click.option('--max-pages', type=int, help='Maximum pages to fetch')
def query(query_type: Optional[str], suggestion: Optional[str], custom_query: Optional[str], export_format: str, max_pages: Optional[int]):
    """Execute general queries against Intercom data"""
    
    console.print(f"[bold green]General Query System[/bold green]")
    
    # Run query
    asyncio.run(run_general_query(query_type, suggestion, custom_query, export_format, max_pages))


# Help Commands
@cli.command()
def help():
    """Show comprehensive help message"""
    run_help_command()

@cli.command()
def interactive():
    """Start interactive mode with guided prompts"""
    run_interactive_command()

@cli.command()
def list_commands():
    """List all available commands"""
    run_list_commands_command()

@cli.command()
def examples():
    """Show usage examples"""
    run_examples_command()

@cli.command()
def show_categories():
    """List available categories"""
    run_show_categories_command()

# Note: Removed non-functional utility commands (show_tags, show_agents, sync_taxonomy)
# These were stubs without implementation and may be added in future releases if needed

# Primary Commands (Technical Triage)
@cli.command(name='tech-analysis')
@click.option('--days', type=int, default=30, help='[DEPRECATED] Use --time-period instead. Number of days to analyze')
@standard_flags()
@click.option('--max-pages', type=int, help='Maximum pages to fetch (for testing)')
def tech_analysis(
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
    max_pages: Optional[int]
):
    """Analyze technical troubleshooting patterns in Intercom conversations"""
    asyncio.run(
        run_tech_analysis_command(
            days=days,
            start_date=start_date,
            end_date=end_date,
            time_period=time_period,
            periods_back=periods_back,
            output_format=output_format,
            gamma_export=gamma_export,
            output_dir=output_dir,
            test_mode=test_mode,
            test_data_count=test_data_count,
            verbose=verbose,
            audit_trail=audit_trail,
            ai_model=ai_model,
            filter_category=filter_category,
            max_pages=max_pages,
        )
    )

@cli.command(name='find-macros')
@click.option('--min-occurrences', type=int, default=5, help='Minimum occurrences for macro (default: 5)')
@click.option('--days', type=int, default=30, help='[DEPRECATED] Use --time-period instead. Number of days to analyze')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
def find_macros(min_occurrences: int, days: int, start_date: Optional[str], end_date: Optional[str]):
    """Discover macro opportunities from repeated agent responses"""
    
    # Deprecation warning for --days
    if days != 30 or (not start_date and not end_date):
        console.print("[yellow]⚠️  Warning: --days is deprecated. Please use --time-period and --periods-back instead.[/yellow]")
    
    console.print(f"[bold green]Macro Discovery Analysis[/bold green]")
    
    # Calculate date range
    if start_date and end_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        console.print(f"Analyzing from {start_date} to {end_date}")
    else:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)
        console.print(f"Analyzing last {days} days of conversations")
    
    console.print(f"Looking for patterns with {min_occurrences}+ occurrences")
    
    # Run macro analysis
    asyncio.run(run_macro_analysis(start_dt, end_dt, min_occurrences))

@cli.command(name='fin-escalations')
@click.option('--days', type=int, default=30, help='[DEPRECATED] Use --time-period instead. Number of days to analyze')
@standard_flags()
@click.option('--detailed', is_flag=True, help='Generate detailed performance report')
def fin_escalations(
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
    detailed: bool
):
    """Analyze Fin → human handoffs and effectiveness"""
    
    # Deprecation warning for --days
    if days != 30 or (not time_period and not start_date and not end_date):
        console.print("[yellow]⚠️  Warning: --days is deprecated. Please use --time-period and --periods-back instead.[/yellow]")
    from src.utils.time_utils import calculate_date_range
    from src.config.test_data import parse_test_data_count, get_preset_display_name
    
    console.print(f"[bold green]Fin Escalation Analysis[/bold green]")
    
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
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
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
            end_is_yesterday=True
        )
        console.print(f"Analyzing: {start_dt.date()} to {end_dt.date()}")
    except ValueError as e:
        # Fallback to --days if time range not specified
        if not time_period and not (start_date and end_date):
            from datetime import timedelta
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=days)
            console.print(f"Analyzing last {days} days of conversations")
        else:
            console.print(f"[red]Error: {e}[/red]")
            return
    
    # Run Fin analysis
    asyncio.run(run_fin_analysis(start_dt, end_dt, detailed))

# DISABLED: This command uses unfinished CLI refactoring - use 'agent-performance' instead
# @cli.command(name='analyze-agent')
# @click.option('--agent', required=True, help='Agent name to analyze (e.g., "Dae-Ho")')
# @click.option('--days', type=int, default=30, help='Number of days to analyze (default: 30)')
# @click.option('--start-date', help='Start date (YYYY-MM-DD)')
# @click.option('--end-date', help='End date (YYYY-MM-DD)')
# @click.option('--individual-breakdown', is_flag=True, help='Show individual agent breakdown')
# @click.option('--focus-categories', help='Focus on specific categories')
# @click.option('--generate-gamma', is_flag=True, help='Generate Gamma presentation')
# @click.option('--analyze-troubleshooting', is_flag=True, help='Analyze troubleshooting patterns')
# def analyze_agent(agent: str, days: int, start_date: Optional[str], end_date: Optional[str],
#                  individual_breakdown: bool, focus_categories: Optional[str], generate_gamma: bool,
#                  analyze_troubleshooting: bool):
#     """Agent-specific performance analysis"""
#
#     # Calculate date range
#     if start_date and end_date:
#         start_dt = datetime.strptime(start_date, '%Y-%m-%d')
#         end_dt = datetime.strptime(end_date, '%Y-%m-%d')
#     else:
#         end_dt = datetime.now()
#         start_dt = end_dt - timedelta(days=days)
#
#     # Use modular command implementation
#     asyncio.run(agent_performance(
#         agent=agent,
#         individual_breakdown=individual_breakdown,
#         time_period=None,
#         start_date=start_date,
#         end_date=end_date,
#         focus_categories=focus_categories,
#         generate_gamma=generate_gamma,
#         analyze_troubleshooting=analyze_troubleshooting
#     ))


# Secondary Commands (VoC Reports)
@cli.command(name='analyze-category')
@click.option('--category', required=True, help='Category to analyze (e.g., billing, bug)')
@click.option('--days', type=int, default=30, help='Number of days to analyze (default: 30)')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
@click.option('--output-format', type=click.Choice(['csv', 'excel', 'json']), default='csv', help='Output format')
def analyze_category(category: str, days: int, start_date: Optional[str], end_date: Optional[str], output_format: str):
    """Single taxonomy category report"""
    console.print("[yellow]⚠️  Warning: This legacy command is deprecated. Use 'analyze-billing' or other modern variants.[/yellow]")
    console.print(f"[bold green]Category Analysis: {category.title()}[/bold green]")
    
    # Calculate date range
    if start_date and end_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        console.print(f"Analyzing from {start_date} to {end_date}")
    else:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)
        console.print(f"Analyzing last {days} days of conversations")
    
    # Run category analysis
    asyncio.run(run_category_analysis(category, start_dt, end_dt, output_format))

@cli.command(name='analyze-all-categories')
@click.option('--days', type=int, default=30, help='Number of days to analyze (default: 30)')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
@click.option('--parallel', is_flag=True, help='Run analyses in parallel (faster)')
def analyze_all_categories(days: int, start_date: Optional[str], end_date: Optional[str], parallel: bool):
    """All 13 taxonomy reports"""
    console.print("[yellow]⚠️  Warning: This legacy command is deprecated. Use modern multi-category commands instead.[/yellow]")
    console.print(f"[bold green]All Categories Analysis[/bold green]")
    
    # Calculate date range
    if start_date and end_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        console.print(f"Analyzing from {start_date} to {end_date}")
    else:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)
        console.print(f"Analyzing last {days} days of conversations")
    
    # Run all categories analysis
    asyncio.run(run_all_categories_analysis(start_dt, end_dt, parallel))


# Advanced Commands (Synthesis)
@cli.command(name='synthesize')
@click.option('--categories', required=True, help='Comma-separated categories (e.g., "Billing,Bug")')
@click.option('--pattern', help='Specific pattern to analyze (e.g., "refund after bug")')
@click.option('--days', type=int, default=30, help='Number of days to analyze (default: 30)')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
def synthesize(categories: str, pattern: Optional[str], days: int, start_date: Optional[str], end_date: Optional[str]):
    """Cross-category pattern analysis"""
    console.print("[yellow]⚠️  Warning: This command is deprecated. Use 'narrative-v2' or multi-agent workflows instead.[/yellow]")
    console.print(f"[bold green]Synthesis Analysis[/bold green]")
    console.print(f"Categories: {categories}")
    if pattern:
        console.print(f"Pattern: {pattern}")
    
    # Calculate date range
    if start_date and end_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        console.print(f"Analyzing from {start_date} to {end_date}")
    else:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)
        console.print(f"Analyzing last {days} days of conversations")
    
    # Run synthesis analysis
    asyncio.run(run_synthesis_analysis(categories, pattern, start_dt, end_dt))

@cli.command(name='analyze-custom-tag')
@click.option('--tag', required=True, help='Custom tag to analyze (e.g., "DC")')
@click.option('--agent', help='Filter by specific agent')
@click.option('--days', type=int, default=30, help='Number of days to analyze (default: 30)')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
def analyze_custom_tag(tag: str, agent: Optional[str], days: int, start_date: Optional[str], end_date: Optional[str]):
    """Custom tag analysis (e.g., "DC")"""
    console.print("[yellow]⚠️  Warning: Legacy custom-tag analysis is deprecated.[/yellow]")
    console.print(f"[bold green]Custom Tag Analysis: {tag}[/bold green]")
    if agent:
        console.print(f"Agent filter: {agent}")
    
    # Calculate date range
    if start_date and end_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        console.print(f"Analyzing from {start_date} to {end_date}")
    else:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)
        console.print(f"Analyzing last {days} days of conversations")
    
    # Run custom tag analysis
    asyncio.run(run_custom_tag_analysis(tag, agent, start_dt, end_dt))

@cli.command(name='analyze-escalations')
@click.option('--to', help='Escalated to (e.g., "Hilary", "Dae-Ho")')
@click.option('--from', help='Escalated from (agent name)')
@click.option('--days', type=int, default=30, help='Number of days to analyze (default: 30)')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
def analyze_escalations(to: Optional[str], from_agent: Optional[str], days: int, start_date: Optional[str], end_date: Optional[str]):
    """Escalation pattern analysis"""
    console.print("[yellow]⚠️  Warning: Escalation analysis legacy path is deprecated.[/yellow]")
    console.print(f"[bold green]Escalation Analysis[/bold green]")
    if to:
        console.print(f"Escalated to: {to}")
    if from_agent:
        console.print(f"Escalated from: {from_agent}")
    
    # Calculate date range
    if start_date and end_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        console.print(f"Analyzing from {start_date} to {end_date}")
    else:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)
        console.print(f"Analyzing last {days} days of conversations")
    
    # Run escalation analysis
    asyncio.run(run_escalation_analysis(to, from_agent, start_dt, end_dt))

@cli.command(name='analyze-pattern')
@click.option('--pattern', required=True, help='Text pattern to search (e.g., "email change")')
@click.option('--days', type=int, default=30, help='Number of days to analyze (default: 30)')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
@click.option('--case-sensitive', is_flag=True, help='Case sensitive search')
def analyze_pattern(pattern: str, days: int, start_date: Optional[str], end_date: Optional[str], case_sensitive: bool):
    """Text pattern search"""
    console.print("[yellow]⚠️  Warning: Pattern analysis legacy path is deprecated.[/yellow]")
    console.print(f"[bold green]Pattern Analysis: {pattern}[/bold green]")
    if case_sensitive:
        console.print("Case sensitive search enabled")
    
    # Calculate date range
    if start_date and end_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        console.print(f"Analyzing from {start_date} to {end_date}")
    else:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)
        console.print(f"Analyzing last {days} days of conversations")
    
    # Run pattern analysis
    asyncio.run(run_pattern_analysis(pattern, start_dt, end_dt, case_sensitive))


@cli.command(name='query-suggestions')
def query_suggestions():
    """Show available query suggestions"""
    console.print("[bold green]Available Query Suggestions[/bold green]")
    
    suggestions = {
        "time_based": [
            "Last 7 days",
            "Last 30 days", 
            "Last quarter",
            "This month",
            "Last month"
        ],
        "state_based": [
            "Open conversations",
            "Closed conversations",
            "Snoozed conversations"
        ],
        "source_based": [
            "Email conversations",
            "Chat conversations",
            "Phone conversations"
        ],
        "satisfaction_based": [
            "High satisfaction (4.5+)",
            "Low satisfaction (<3.0)",
            "Rated conversations only"
        ],
        "geographic_based": [
            "US customers",
            "European customers",
            "Tier 1 countries"
        ],
        "content_based": [
            "Billing related",
            "Technical issues",
            "Product questions",
            "Account management"
        ]
    }
    
    for category, items in suggestions.items():
        console.print(f"\n[bold cyan]{category.replace('_', ' ').title()}[/bold cyan]")
        for item in items:
            console.print(f"  • {item}")
    
    console.print(f"\n[bold yellow]Usage Examples:[/bold yellow]")
    console.print("python -m src.main query --query-type time_based --suggestion 'Last 30 days'")
    console.print("python -m src.main query --query-type geographic_based --suggestion 'US customers'")
    console.print("python -m src.main query --query-type content_based --suggestion 'Billing related'")


@cli.command()
def config():
    """Show current configuration"""
    run_config_command()


# New Category Analysis Commands
@cli.command(name='analyze-billing')
@click.option('--days', type=int, default=30, help='[DEPRECATED] Use --time-period instead. Number of days to analyze')
@standard_flags()
@click.option('--max-conversations', type=int, help='Maximum conversations to analyze')
def analyze_billing(
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
    max_conversations: Optional[int]
):
    """Analyze billing conversations (refunds, invoices, credits, discounts)."""
    
    # Deprecation warning for --days
    if days != 30 or (not time_period and not start_date and not end_date):
        console.print("[yellow]⚠️  Warning: --days is deprecated. Please use --time-period and --periods-back instead.[/yellow]")
    from src.utils.time_utils import calculate_date_range
    from src.config.test_data import parse_test_data_count, get_preset_display_name
    
    # Set AI model if specified
    if ai_model:
        os.environ['AI_MODEL'] = ai_model
    
    # Enable verbose logging if requested
    if verbose:
        setup_verbose_logging()
    
    # Audit trail indication
    if audit_trail:
        show_audit_trail_enabled()
    
    # Calculate date range using shared utility
    try:
        start_dt, end_dt = calculate_date_range(
            time_period=time_period,
            periods_back=periods_back,
            start_date=start_date,
            end_date=end_date,
            end_is_yesterday=True
        )
    except ValueError as e:
        # Fallback to --days if time range not specified
        if not time_period and not (start_date and end_date):
            from datetime import timedelta
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=days)
        else:
            console.print(f"[red]Error: {e}[/red]")
            return
    
    # Generate gamma flag derived from output format
    generate_gamma = output_format == 'gamma'
    
    asyncio.run(run_billing_analysis(start_dt, end_dt, generate_gamma, max_conversations, audit_trail=audit_trail))


@cli.command(name='analyze-product')
@click.option('--days', type=int, default=30, help='[DEPRECATED] Use --time-period instead. Number of days to analyze')
@standard_flags()
@click.option('--max-conversations', type=int, help='Maximum conversations to analyze')
def analyze_product(
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
    max_conversations: Optional[int]
):
    """Analyze product conversations (export issues, bugs, feature requests)."""
    
    # Deprecation warning for --days
    if days != 30 or (not time_period and not start_date and not end_date):
        console.print("[yellow]⚠️  Warning: --days is deprecated. Please use --time-period and --periods-back instead.[/yellow]")
    from src.utils.time_utils import calculate_date_range
    from datetime import timedelta
    
    # Set AI model if specified
    if ai_model:
        os.environ['AI_MODEL'] = ai_model
    
    # Enable verbose logging if requested
    if verbose:
        setup_verbose_logging()
    
    # Audit trail indication
    if audit_trail:
        show_audit_trail_enabled()
    
    # Calculate date range using shared utility
    try:
        start_dt, end_dt = calculate_date_range(
            time_period=time_period,
            periods_back=periods_back,
            start_date=start_date,
            end_date=end_date,
            end_is_yesterday=True
        )
    except ValueError:
        # Fallback to --days if time range not specified
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)
    
    # Generate gamma flag derived from output format
    generate_gamma = output_format == 'gamma'
    
    asyncio.run(run_product_analysis(start_dt, end_dt, generate_gamma, max_conversations, audit_trail=audit_trail))


@cli.command(name='analyze-sites')
@click.option('--days', type=int, default=30, help='[DEPRECATED] Use --time-period instead. Number of days to analyze')
@standard_flags(include_output=False, include_test=False, include_debug=False, include_analysis=False)
@click.option('--generate-gamma', is_flag=True, help='Generate Gamma presentation')
@click.option('--max-conversations', type=int, help='Maximum conversations to analyze')
@click.option('--verbose', is_flag=True, default=False, help='Enable verbose DEBUG logging')
@click.option('--audit-trail', is_flag=True, default=False, help='Enable audit trail logging')
@click.option('--ai-model', type=click.Choice(['openai', 'claude']), default=None,
              help='AI model to use for analysis (overrides config setting)')
def analyze_sites(
    days: int,
    start_date: Optional[str],
    end_date: Optional[str],
    time_period: Optional[str],
    periods_back: int,
    generate_gamma: bool,
    max_conversations: Optional[int],
    verbose: bool = False,
    audit_trail: bool = False,
    ai_model: Optional[str] = None,
):
    """Analyze sites conversations (domain, publishing, education)."""
    from datetime import timedelta
    from src.utils.time_utils import calculate_date_range

    if days != 30 or (not time_period and not start_date and not end_date):
        console.print("[yellow]⚠️  Warning: --days is deprecated. Please use --time-period and --periods-back instead.[/yellow]")

    if ai_model:
        os.environ['AI_MODEL'] = ai_model

    if verbose:
        setup_verbose_logging()
    if audit_trail:
        show_audit_trail_enabled()
    
    try:
        start_dt, end_dt = calculate_date_range(
            time_period=time_period,
            periods_back=periods_back,
            start_date=start_date,
            end_date=end_date,
            end_is_yesterday=True
        )
    except ValueError:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)
    
    asyncio.run(
        run_sites_analysis(
            start_dt,
            end_dt,
            generate_gamma,
            max_conversations,
            audit_trail=audit_trail,
        )
    )


@cli.command(name='analyze-api')
@click.option('--days', type=int, default=30, help='[DEPRECATED] Use --time-period instead. Number of days to analyze')
@standard_flags()
@click.option('--max-conversations', type=int, help='Maximum conversations to analyze')
def analyze_api(
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
    max_conversations: Optional[int]
):
    """Analyze API conversations (authentication, integration, performance)."""
    
    # Deprecation warning for --days
    if days != 30 or (not time_period and not start_date and not end_date):
        console.print("[yellow]⚠️  Warning: --days is deprecated. Please use --time-period and --periods-back instead.[/yellow]")
    from src.utils.time_utils import calculate_date_range
    from datetime import timedelta
    
    # Set AI model if specified
    if ai_model:
        os.environ['AI_MODEL'] = ai_model
    
    # Enable verbose logging if requested
    if verbose:
        setup_verbose_logging()
    
    # Audit trail indication
    if audit_trail:
        show_audit_trail_enabled()
    
    # Calculate date range using shared utility
    try:
        start_dt, end_dt = calculate_date_range(
            time_period=time_period,
            periods_back=periods_back,
            start_date=start_date,
            end_date=end_date,
            end_is_yesterday=True
        )
    except ValueError:
        # Fallback to --days if time range not specified
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)
    
    # Generate gamma flag derived from output format
    generate_gamma = output_format == 'gamma'
    
    asyncio.run(run_api_analysis(start_dt, end_dt, generate_gamma, max_conversations, audit_trail=audit_trail))


@cli.command(name='analyze-all-categories')
@click.option('--days', type=int, default=30, help='[DEPRECATED] Use --time-period instead. Number of days to analyze')
@standard_flags(include_output=False, include_test=False, include_debug=False, include_analysis=False)
@click.option('--generate-gamma', is_flag=True, help='Generate Gamma presentations')
@click.option('--parallel', is_flag=True, help='Run analyses in parallel')
@click.option('--max-conversations', type=int, help='Maximum conversations per category')
@click.option('--verbose', is_flag=True, default=False, help='Enable verbose DEBUG logging')
@click.option('--audit-trail', is_flag=True, default=False, help='Enable audit trail logging')
@click.option('--ai-model', type=click.Choice(['openai', 'claude']), default=None,
              help='AI model to use for analysis (overrides config setting)')
def analyze_all_categories(
    days: int,
    start_date: Optional[str],
    end_date: Optional[str],
    time_period: Optional[str],
    periods_back: int,
    generate_gamma: bool,
    parallel: bool,
    max_conversations: Optional[int],
    verbose: bool = False,
    audit_trail: bool = False,
    ai_model: Optional[str] = None,
):
    """Analyze all 4 main categories (Billing, Product, Sites, API)."""
    from datetime import timedelta
    from src.utils.time_utils import calculate_date_range

    if days != 30 or (not time_period and not start_date and not end_date):
        console.print("[yellow]⚠️  Warning: --days is deprecated. Please use --time-period and --periods-back instead.[/yellow]")

    if ai_model:
        os.environ['AI_MODEL'] = ai_model

    if verbose:
        setup_verbose_logging()
    if audit_trail:
        show_audit_trail_enabled()
    
    try:
        start_dt, end_dt = calculate_date_range(
            time_period=time_period,
            periods_back=periods_back,
            start_date=start_date,
            end_date=end_date,
            end_is_yesterday=True
        )
    except ValueError:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)

    asyncio.run(
        run_all_categories_analysis_v2(
            start_dt,
            end_dt,
            generate_gamma,
            parallel,
            max_conversations,
        )
    )




@cli.command(name='comprehensive-analysis')
@standard_flags()
@click.option('--max-conversations', default=1000, help='Maximum conversations to analyze')
@click.option('--gamma-style', default='executive', type=click.Choice(['executive', 'detailed', 'training']), help='Gamma presentation style')
@click.option('--export-docs', is_flag=True, help='Generate markdown for Google Docs')
@click.option('--include-fin-analysis', is_flag=True, default=True, help='Include Fin escalation analysis')
@click.option('--include-technical-analysis', is_flag=True, default=True, help='Include technical pattern analysis')
@click.option('--include-macro-analysis', is_flag=True, default=True, help='Include macro opportunity analysis')
def comprehensive_analysis(
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
    max_conversations: int,
    gamma_style: str,
    export_docs: bool,
    include_fin_analysis: bool,
    include_technical_analysis: bool,
    include_macro_analysis: bool
):
    asyncio.run(
        run_comprehensive_analysis_impl(
            start_date=start_date,
            end_date=end_date,
            time_period=time_period,
            periods_back=periods_back,
            output_format=output_format,
            gamma_export=gamma_export,
            output_dir=output_dir,
            test_mode=test_mode,
            test_data_count=test_data_count,
            verbose=verbose,
            audit_trail=audit_trail,
            ai_model=ai_model,
            filter_category=filter_category,
            max_conversations=max_conversations,
            gamma_style=gamma_style,
            export_docs=export_docs,
            include_fin_analysis=include_fin_analysis,
            include_technical_analysis=include_technical_analysis,
            include_macro_analysis=include_macro_analysis,
        )
    )


@cli.command(name='generate-gamma')
@click.option('--analysis-file', required=True, type=click.Path(exists=True), help='Path to analysis JSON file')
@click.option('--style', default='executive', type=click.Choice(['executive', 'detailed', 'training']), help='Presentation style')
@click.option('--export-pdf', is_flag=True, help='Also export as PDF')
@click.option('--export-pptx', is_flag=True, help='Also export as PPTX')
@click.option('--export-docs', is_flag=True, help='Generate markdown for Google Docs')
@click.option('--output-dir', default='outputs', help='Output directory for results')
def generate_gamma(analysis_file, style, export_pdf, export_pptx, export_docs, output_dir):
    """Generate Gamma presentation from existing analysis JSON file."""
    run_gamma_generation(
        analysis_file=analysis_file,
        style=style,
        export_pdf=export_pdf,
        export_pptx=export_pptx,
        export_docs=export_docs,
        output_dir=output_dir,
    )


@cli.command(name='generate-all-gamma')
@click.option('--analysis-file', required=True, type=click.Path(exists=True), help='Path to analysis JSON file')
@click.option('--export-pdf', is_flag=True, help='Also export as PDF')
@click.option('--export-pptx', is_flag=True, help='Also export as PPTX')
@click.option('--export-docs', is_flag=True, help='Generate markdown for Google Docs')
@click.option('--output-dir', default='outputs', help='Output directory for results')
def generate_all_gamma(analysis_file, export_pdf, export_pptx, export_docs, output_dir):
    """Generate all Gamma presentation styles from existing analysis JSON file."""
    run_bulk_gamma_generation(
        analysis_file=analysis_file,
        export_pdf=export_pdf,
        export_pptx=export_pptx,
        export_docs=export_docs,
        output_dir=output_dir,
    )


def run_comprehensive_analysis_wrapper(
    start_date: str,
    end_date: str,
    max_conversations: int = 1000,
    generate_gamma: bool = True,
    gamma_style: str = "executive",
    gamma_export: str = None,
    export_docs: bool = False,
    output_dir: str = "outputs"
) -> dict:
    """
    Serverless wrapper for comprehensive analysis.
    Designed for deployment platforms like Modal, Railway, or AWS Lambda.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        max_conversations: Maximum conversations to analyze
        generate_gamma: Whether to generate Gamma presentation
        gamma_style: Gamma presentation style (executive, detailed, training)
        gamma_export: Export format (pdf, pptx) or None
        export_docs: Whether to generate Google Docs markdown
        output_dir: Output directory for results
        
    Returns:
        Dictionary with analysis results and Gamma URLs
    """
    try:
        # Parse dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Prepare options
        options = {
            'max_conversations': max_conversations,
            'generate_gamma_presentation': generate_gamma,
            'gamma_style': gamma_style,
            'gamma_export': gamma_export,
            'export_docs': export_docs,
            'output_directory': output_dir
        }
        
        # Initialize orchestrator
        orchestrator = AnalysisOrchestrator()
        
        # Run analysis
        results = asyncio.run(orchestrator.run_comprehensive_analysis(
            start_date=start_dt,
            end_date=end_dt,
            options=options
        ))
        
        # Extract key results for serverless response
        response = {
            'success': True,
            'analysis_metadata': results.get('analysis_metadata', {}),
            'validation': results.get('validation', {}),
            'total_conversations': len(results.get('conversations', [])),
            'category_results': results.get('category_results', {}),
            'gamma_presentation': results.get('gamma_presentation', {}),
            'timestamp': datetime.now().isoformat()
        }
        
        # Add Gamma URLs if available
        gamma_result = results.get('gamma_presentation', {})
        if gamma_result and not gamma_result.get('error'):
            response['gamma_url'] = gamma_result.get('gamma_url')
            response['export_url'] = gamma_result.get('export_url')
            response['credits_used'] = gamma_result.get('credits_used')
        
        return response
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


@cli.command(name='voice-of-customer')
@click.option('--time-period', type=click.Choice(['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks']),
              help='Time period for analysis (overrides start/end dates if provided)')
@click.option('--periods-back', type=int, default=1,
              help='Number of periods back to analyze (e.g., --time-period month --periods-back 3)')
@click.option('--start-date', help='Start date (YYYY-MM-DD) - used if no time-period specified')
@click.option('--end-date', help='End date (YYYY-MM-DD) - used if no time-period specified')
@click.option('--enable-fallback/--no-fallback', default=True,
              help='Enable fallback to other AI model if primary fails')
@click.option('--include-trends', is_flag=True, default=False,
              help='Include historical trend analysis')
@click.option('--include-canny', is_flag=True, default=False,
              help='Include Canny feedback in analysis')
@click.option('--canny-board-id', help='Specific Canny board ID for combined analysis')
@click.option('--generate-gamma', is_flag=True, default=False,
              help='Generate Gamma presentation from results')
@click.option('--test-mode', is_flag=True, default=False,
              help='🧪 Use mock test data instead of Intercom API (fast, no API calls)')
@click.option('--test-data-count', type=str, default='100',
              help='Number of test conversations or preset (100, 500, 1000, 5000, 10000, or custom number)')
@click.option('--verbose', is_flag=True, default=False,
              help='Enable verbose DEBUG logging to see detailed agent decision-making')
@click.option('--separate-agent-feedback', is_flag=True, default=True,
              help='Separate feedback by agent type (Finn, Boldr, Horatio, etc.)')
@click.option('--multi-agent', is_flag=True, help='Use multi-agent mode')
@click.option('--analysis-type', type=click.Choice(['standard', 'topic-based', 'synthesis', 'complete']), 
             default='topic-based', help='Analysis type: topic-based (V2 with detailed cards), synthesis, or complete')
@click.option('--ai-model', type=click.Choice(['openai', 'claude']), default=None,
              help='AI model to use (openai or claude). Defaults to config setting.')
@click.option('--audit-trail', is_flag=True, default=False,
              help='Enable audit trail logging for debugging and compliance')
@click.option('--llm-topic-detection', is_flag=True, default=True,
              help='🤖 LLM-first topic detection (DEFAULT: ON for accuracy - use --no-llm-topic-detection to disable)')
@click.option('--output-dir', default='outputs', help='Output directory')
@click.option('--digest-mode', is_flag=True, default=False,
             help='Digest mode: executive summary, topic cards, prioritized actions only')
@click.option('--legacy-mode', is_flag=True, default=False,
              help='Run legacy Hilary V1 multi-agent workflow (topic-based only)')
@click.option('--enable-correlation-analysis', 'enable_correlation_analysis',
              flag_value=True, default=None,
              help='Toggle Phase 4.5 CorrelationAgent (default: enabled)')
@click.option('--disable-correlation-analysis', 'enable_correlation_analysis',
              flag_value=False, default=None,
              help='Toggle Phase 4.5 CorrelationAgent (default: enabled)')
@click.option('--enable-quality-insights', 'enable_quality_insights',
              flag_value=True, default=None,
              help='Toggle Phase 4.5 QualityInsightsAgent (default: enabled)')
@click.option('--disable-quality-insights', 'enable_quality_insights',
              flag_value=False, default=None,
              help='Toggle Phase 4.5 QualityInsightsAgent (default: enabled)')
@click.option('--enable-churn-detection', 'enable_churn_detection',
              flag_value=True, default=None,
              help='Toggle Phase 4.5 ChurnRiskAgent (default: enabled)')
@click.option('--disable-churn-detection', 'enable_churn_detection',
              flag_value=False, default=None,
              help='Toggle Phase 4.5 ChurnRiskAgent (default: enabled)')
@click.option('--enable-confidence-meta', 'enable_confidence_meta',
              flag_value=True, default=None,
              help='Toggle Phase 4.5 ConfidenceMetaAgent (default: enabled)')
@click.option('--disable-confidence-meta', 'enable_confidence_meta',
              flag_value=False, default=None,
              help='Toggle Phase 4.5 ConfidenceMetaAgent (default: enabled)')
def voice_of_customer_analysis(
    time_period: Optional[str],
    periods_back: int,
    start_date: Optional[str],
    end_date: Optional[str],
    ai_model: str,
    enable_fallback: bool,
    include_trends: bool,
    include_canny: bool,
    llm_topic_detection: bool,
    canny_board_id: Optional[str],
    generate_gamma: bool,
    test_mode: bool,
    test_data_count: str,
    verbose: bool,
    separate_agent_feedback: bool,
    multi_agent: bool,
    analysis_type: str,
    audit_trail: bool,
    output_dir: str,
    digest_mode: bool,
    legacy_mode: bool,
    enable_correlation_analysis: Optional[bool],
    enable_quality_insights: Optional[bool],
    enable_churn_detection: Optional[bool],
    enable_confidence_meta: Optional[bool]
):
    asyncio.run(
        run_voice_of_customer_analysis_impl(
            time_period=time_period,
            periods_back=periods_back,
            start_date=start_date,
            end_date=end_date,
            ai_model=ai_model,
            enable_fallback=enable_fallback,
            include_trends=include_trends,
            include_canny=include_canny,
            llm_topic_detection=llm_topic_detection,
            canny_board_id=canny_board_id,
            generate_gamma=generate_gamma,
            test_mode=test_mode,
            test_data_count=test_data_count,
            verbose=verbose,
            analysis_type=analysis_type,
            audit_trail=audit_trail,
            output_dir=output_dir,
            digest_mode=digest_mode,
            enable_correlation_analysis=enable_correlation_analysis,
            enable_quality_insights=enable_quality_insights,
            enable_churn_detection=enable_churn_detection,
            enable_confidence_meta=enable_confidence_meta,
            legacy_mode=legacy_mode,
        )
    )


@cli.command(name='sample-mode')
@click.option('--count', type=int, callback=validate_sample_count, default=None,
              help='Number of conversations to sample (defaults per schema mode)')
@click.option('--time-period', type=click.Choice(['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks']),
              default='week', help='Time period window for sampling')
@click.option('--start-date', help='Custom start date (YYYY-MM-DD)')
@click.option('--end-date', help='Custom end date (YYYY-MM-DD)')
@click.option('--save-to-file', is_flag=True, default=False,
              help='Persist sampled conversations and logs to outputs/')
@click.option('--test-llm', is_flag=True, default=False,
              help='Run production LLM sentiment test across sampled topics')
@click.option('--test-all-agents', is_flag=True, default=False,
              help='Exercise all production agents (longer runtime)')
@click.option('--show-agent-thinking', is_flag=True, default=False,
              help='Capture LLM prompts/responses for debugging')
@click.option('--llm-topic-detection', is_flag=True, default=False,
              help='Use LLM-first topic detection (higher accuracy & cost)')
@click.option('--schema-mode', type=click.Choice(['quick', 'standard', 'deep', 'comprehensive']),
              default='quick', help='Sampling preset (controls volume & diagnostics)')
@click.option('--ai-model', type=click.Choice(['openai', 'claude']), default='openai',
              help='AI provider for diagnostic LLM calls')
@click.option('--include-hierarchy/--no-include-hierarchy', default=True,
              help='Include topic hierarchy debugging block')
@click.option('--no-hierarchy', is_flag=True, default=False,
              help='Alias to disable hierarchy block (legacy flag)')
@click.option('--verbose', is_flag=True, default=False,
              help='Enable verbose DEBUG logging for sampling run')
def sample_mode_cli(
    count: Optional[int],
    time_period: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
    save_to_file: bool,
    test_llm: bool,
    test_all_agents: bool,
    show_agent_thinking: bool,
    llm_topic_detection: bool,
    schema_mode: str,
    ai_model: str,
    include_hierarchy: bool,
    no_hierarchy: bool,
    verbose: bool,
):
    """Pull a real-data sample with ultra-rich logging + diagnostics."""
    asyncio.run(
        run_sample_mode_command(
            count=count,
            start_date=start_date,
            end_date=end_date,
            time_period=time_period or 'week',
            save_to_file=save_to_file,
            test_llm=test_llm,
            test_all_agents=test_all_agents,
            show_agent_thinking=show_agent_thinking,
            llm_topic_detection=llm_topic_detection,
            schema_mode=schema_mode,
            ai_model=ai_model,
            include_hierarchy=include_hierarchy,
            no_hierarchy=no_hierarchy,
            verbose=verbose,
        )
    )


@cli.command(name='voc-v2')
@click.option('--time-period', type=click.Choice(['yesterday', 'week', 'month', 'quarter']),
              help='Time period for analysis (overrides start/end dates if provided)')
@click.option('--periods-back', type=int, default=1,
              help='Number of periods back to analyze (e.g., --time-period month --periods-back 3)')
@click.option('--start-date', help='Start date (YYYY-MM-DD) - used if no time-period specified')
@click.option('--end-date', help='End date (YYYY-MM-DD) - used if no time-period specified')
@click.option('--ai-model', type=click.Choice(['openai', 'claude']), default=None,
              help='AI model to use (openai or claude). Defaults to config setting.')
@click.option('--generate-gamma', is_flag=True, default=False,
              help='Generate Gamma presentation from results')
@click.option('--test-mode', is_flag=True, default=False,
              help='🧪 Use mock test data instead of Intercom API (fast, no API calls)')
@click.option('--test-data-count', type=str, default='100',
              help='Number of test conversations or preset (100, 500, 1000, 5000, 10000, or custom number)')
@click.option('--verbose', is_flag=True, default=False,
              help='Enable verbose DEBUG logging')
@click.option('--audit-trail', is_flag=True, default=False,
              help='Enable audit trail logging for debugging and compliance')
@click.option('--llm-topic-detection', is_flag=True, default=True,
              help='🤖 LLM-first topic detection (DEFAULT: ON for accuracy - use --no-llm-topic-detection to disable)')
@click.option('--digest-mode', is_flag=True, default=False,
              help='Digest mode: short narrative + top actions only')
def voice_of_customer_v2_analysis(
    time_period: Optional[str],
    periods_back: int,
    start_date: Optional[str],
    end_date: Optional[str],
    ai_model: Optional[str],
    generate_gamma: bool,
    test_mode: bool,
    test_data_count: str,
    verbose: bool,
    audit_trail: bool,
    llm_topic_detection: bool,
    digest_mode: bool
):
    """
    VOC-V2: Narrative, BPO-aware Voice of Customer analysis.
    """
    from src.utils.time_utils import calculate_date_range, format_date_range_for_display
    try:
        start_dt, end_dt = calculate_date_range(
            time_period=time_period,
            periods_back=periods_back,
            start_date=start_date,
            end_date=end_date,
            end_is_yesterday=True
        )
        start_date = start_dt.strftime('%Y-%m-%d')
        end_date = end_dt.strftime('%Y-%m-%d')
        label = time_period.capitalize() if time_period else "Custom Range"
        console.print(f"[bold]VOC-V2 Narrative Analysis - {label}[/bold]")
        console.print(f"Date Range: {format_date_range_for_display(start_dt, end_dt)} (Pacific Time)")
    except ValueError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        return

    if verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
        for module in ['agents', 'services', 'src.agents', 'src.services']:
            logging.getLogger(module).setLevel(logging.DEBUG)
        console.print(f"[yellow]🔍 Verbose Logging: ENABLED (DEBUG level)[/yellow]")

    if ai_model:
        os.environ['AI_MODEL'] = ai_model
        console.print(f"[cyan]🤖 AI Model: {ai_model}[/cyan]")

    if llm_topic_detection:
        os.environ['LLM_TOPIC_DETECTION'] = 'true'
        console.print(f"[bold cyan]🤖 LLM-First Topic Detection: ENABLED[/bold cyan]")
        console.print(f"[dim]   Uses GPT-4o-mini to classify every conversation[/dim]")

    preset_counts = {
        'micro': 100,
        'small': 500,
        'medium': 1000,
        'large': 5000,
        'xlarge': 10000,
        'xxlarge': 20000
    }
    parsed_test_count = test_data_count
    try:
        if test_mode:
            if test_data_count.lower() in preset_counts:
                test_data_count_int = preset_counts[test_data_count.lower()]
                preset_label = test_data_count.lower()
            else:
                test_data_count_int = int(test_data_count)
                preset_label = None
            info = f" ({preset_label})" if preset_label else ""
            console.print(f"[yellow]🧪 Test Mode: {test_data_count_int} mock conversations{info}[/yellow]")
            parsed_test_count = str(test_data_count_int)
        else:
            test_data_count_int = int(test_data_count) if test_data_count.isdigit() else 0
    except ValueError:
        console.print(f"[red]Invalid test data count '{test_data_count}'[/red]")
        return

    if verbose:
        console.print()

    from src.agents.topic_orchestrator_v2 import TopicOrchestratorV2

    asyncio.run(run_topic_based_analysis_custom(
        start_dt,
        end_dt,
        generate_gamma,
        test_mode=test_mode,
        test_data_count=parsed_test_count,
        audit_trail=audit_trail,
        digest_mode=digest_mode,
        orchestrator_factory=TopicOrchestratorV2,
        output_prefix="voc_v2",
        output_subdir="voc_v2"
    ))


@cli.command(name='agent-performance')
@click.option('--agent', type=click.Choice(['horatio', 'boldr', 'escalated']), required=True,
              help='Agent to analyze (horatio, boldr, or escalated to senior staff)')
@click.option('--individual-breakdown', is_flag=True,
              help='Show individual agent metrics with taxonomy breakdown (not just team summary)')
@click.option('--time-period', type=click.Choice(['week', 'month', '6-weeks', 'quarter']),
              help='Time period for analysis')
@click.option('--periods-back', type=int, default=1,
              help='Number of periods back to analyze (e.g., --time-period week --periods-back 4 for last 4 weeks)')
@click.option('--start-date', help='Start date (YYYY-MM-DD) - overrides time-period')
@click.option('--end-date', help='End date (YYYY-MM-DD) - overrides time-period')
@click.option('--focus-categories', help='Comma-separated categories to focus on (e.g., "Bug,API")')
@click.option('--filter-category', help='Alias for focus categories (taxonomy filter)')
@click.option('--generate-gamma', is_flag=True, help='Generate Gamma presentation')
@click.option('--output-format', type=click.Choice(['gamma', 'markdown', 'json', 'excel']), default='markdown',
              help='Output format for results')
@click.option('--analyze-troubleshooting', is_flag=True, 
              help='Enable AI-powered troubleshooting analysis (slower, analyzes diagnostic questions and escalation patterns)')
@click.option('--test-mode', is_flag=True, default=False, help='Use mock test data instead of real API calls')
@click.option('--test-data-count', type=str, default='100', 
              help='Data volume: micro(100), small(500), medium(1000), large(5000), xlarge(10000) or custom number')
@click.option('--verbose', is_flag=True, default=False, help='Enable verbose DEBUG logging')
@click.option('--audit-trail', is_flag=True, default=False, help='Enable audit trail logging')
@click.option('--ai-model', type=click.Choice(['openai', 'claude']), default=None,
              help='AI model to use for analysis (overrides config setting)')
def agent_performance(agent: str, individual_breakdown: bool, time_period: Optional[str], periods_back: int,
                     start_date: Optional[str], end_date: Optional[str], focus_categories: Optional[str],
                     filter_category: Optional[str],
                     generate_gamma: bool, output_format: str, analyze_troubleshooting: bool = False, 
                     test_mode: bool = False, test_data_count: str = '100',
                     verbose: bool = False, audit_trail: bool = False, ai_model: Optional[str] = None):
    """Analyze support agent/team performance with operational metrics"""
    from src.utils.time_utils import calculate_date_range, format_date_range_for_display
    
    # Set AI model if specified
    if ai_model:
        os.environ['AI_MODEL'] = ai_model
        console.print(f"[cyan]🤖 AI Model: {ai_model.upper()}[/cyan]")
    
    # Calculate dates using shared utility
    try:
        start_dt, end_dt = calculate_date_range(
            time_period=time_period,
            periods_back=periods_back,
            start_date=start_date,
            end_date=end_date,
            end_is_yesterday=True
        )
        start_date_str = start_dt.strftime('%Y-%m-%d')
        end_date_str = end_dt.strftime('%Y-%m-%d')
        
        if time_period:
            console.print(f"[bold]Agent Performance Analysis - {time_period.capitalize()}[/bold]")
            console.print(f"Period: Last {periods_back} {time_period}(s)")
        else:
            console.print(f"[bold]Agent Performance Analysis - Custom Range[/bold]")
        
        console.print(f"Date Range: {format_date_range_for_display(start_dt, end_dt)} (Pacific Time)")
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return
    
    agent_name = {'horatio': 'Horatio', 'boldr': 'Boldr', 'escalated': 'Senior Staff'}.get(agent, agent)
    
    # Parse test data count (supports presets or custom numbers)
    test_data_presets = {
        'micro': 100,
        'small': 500,
        'medium': 1000,
        'large': 5000,
        'xlarge': 10000
    }
    
    try:
        if test_data_count.lower() in test_data_presets:
            test_data_count_int = test_data_presets[test_data_count.lower()]
            preset_label = test_data_count.lower()
        else:
            test_data_count_int = int(test_data_count)
            preset_label = None
    except ValueError:
        console.print(f"[red]Error: Invalid test data count '{test_data_count}'. Use a number or preset (micro, small, medium, large, xlarge, xxlarge)[/red]")
        return
    
    # Enable verbose logging if requested
    if verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
        for module in ['agents', 'services', 'src.agents', 'src.services']:
            logging.getLogger(module).setLevel(logging.DEBUG)
        console.print(f"[yellow]🔍 Verbose Logging: ENABLED (DEBUG level)[/yellow]")
    
    # Test mode indication
    if test_mode:
        preset_info = f" ({preset_label})" if preset_label else ""
        console.print(f"[yellow]🧪 Test Mode: ENABLED ({test_data_count_int} mock conversations{preset_info})[/yellow]")
        console.print(f"[dim]   No API calls will be made - using generated test data[/dim]")
    
    # Audit trail indication
    if audit_trail:
        console.print("[purple]📋 Audit Trail Mode: ENABLED[/purple]")
    
    if filter_category and not focus_categories:
        focus_categories = filter_category

    console.print(f"[bold green]{agent_name} Performance Analysis[/bold green]")
    console.print(f"Date Range: {start_date_str} to {end_date_str}")
    if individual_breakdown:
        console.print("[cyan]Mode: Individual Agent Breakdown with Taxonomy Analysis[/cyan]")
    if focus_categories:
        console.print(f"Focus: {focus_categories}")
    
    asyncio.run(run_agent_performance_analysis(
        agent, start_dt, end_dt, focus_categories, generate_gamma, individual_breakdown,
        analyze_troubleshooting, test_mode, test_data_count_int, audit_trail
    ))


@cli.command(name='agent-eval')
@click.option('--vendor', type=click.Choice(['horatio', 'boldr', 'escalated']), required=True,
              help='Vendor team to evaluate')
@click.option('--time-period', type=click.Choice(['week', 'month', '6-weeks', 'quarter']),
              help='Time period for analysis')
@click.option('--periods-back', type=int, default=1,
              help='Number of periods back to analyze (e.g., --time-period week --periods-back 4)')
@click.option('--start-date', help='Start date (YYYY-MM-DD) - overrides time-period')
@click.option('--end-date', help='End date (YYYY-MM-DD) - overrides time-period')
@click.option('--focus-categories', help='Comma-separated taxonomy categories to emphasize')
@click.option('--filter-category', help='Alias for focus categories (taxonomy filter)')
@click.option('--generate-gamma', is_flag=True, default=False, help='Generate Gamma presentation output')
@click.option('--test-mode', is_flag=True, default=False, help='Use generated mock data (no API calls)')
@click.option('--test-data-count', type=str, default='100',
              help='Test data count preset (micro, small, medium, large, xlarge, xxlarge) or number')
@click.option('--verbose', is_flag=True, default=False, help='Enable DEBUG logging')
@click.option('--audit-trail', is_flag=True, default=False, help='Generate audit trail artifacts')
@click.option('--ai-model', type=click.Choice(['openai', 'claude']), default=None,
              help='AI model override for analysis')
def agent_eval(
    vendor: str,
    time_period: Optional[str],
    periods_back: int,
    start_date: Optional[str],
    end_date: Optional[str],
    focus_categories: Optional[str],
    filter_category: Optional[str],
    generate_gamma: bool,
    test_mode: bool,
    test_data_count: str,
    verbose: bool,
    audit_trail: bool,
    ai_model: Optional[str]
):
    """Shortcut command for per-agent evaluation with individual breakdown enabled."""
    from src.utils.time_utils import calculate_date_range, format_date_range_for_display

    if ai_model:
        os.environ['AI_MODEL'] = ai_model
        console.print(f"[cyan]🤖 AI Model: {ai_model.upper()}[/cyan]")

    try:
        start_dt, end_dt = calculate_date_range(
            time_period=time_period,
            periods_back=periods_back,
            start_date=start_date,
            end_date=end_date,
            end_is_yesterday=True
        )
        console.print(f"[bold]Agent Evaluation - {vendor.title()}[/bold]")
        console.print(f"Date Range: {format_date_range_for_display(start_dt, end_dt)} (Pacific Time)")
    except ValueError as err:
        console.print(f"[red]Error: {err}[/red]")
        return

    test_data_presets = {
        'micro': 100,
        'small': 500,
        'medium': 1000,
        'large': 5000,
        'xlarge': 10000,
        'xxlarge': 20000
    }
    test_data_count_int = 0
    try:
        if test_mode:
            if test_data_count.lower() in test_data_presets:
                test_data_count_int = test_data_presets[test_data_count.lower()]
                console.print(f"[yellow]🧪 Test Mode: {test_data_count_int} mock conversations ({test_data_count.lower()})[/yellow]")
            else:
                test_data_count_int = int(test_data_count)
                console.print(f"[yellow]🧪 Test Mode: {test_data_count_int} mock conversations[/yellow]")
    except ValueError:
        console.print(f"[red]Invalid test data count '{test_data_count}'. Use a number or preset (micro, small, medium, large, xlarge, xxlarge)[/red]")
        return

    if verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
        for module in ['agents', 'services', 'src.agents', 'src.services']:
            logging.getLogger(module).setLevel(logging.DEBUG)
        console.print(f"[yellow]🔍 Verbose Logging: ENABLED (DEBUG level)[/yellow]")

    if audit_trail:
        console.print("[purple]📋 Audit Trail Mode: ENABLED[/purple]")

    if filter_category and not focus_categories:
        focus_categories = filter_category

    asyncio.run(run_agent_performance_analysis(
        vendor,
        start_dt,
        end_dt,
        focus_categories,
        generate_gamma,
        individual_breakdown=True,
        analyze_troubleshooting=False,
        test_mode=test_mode,
        test_data_count=test_data_count_int,
        audit_trail=audit_trail
    ))

@cli.command(name='agent-coaching-report')
@click.option('--vendor', type=click.Choice(['horatio', 'boldr']), required=True,
              help='Vendor to analyze (horatio or boldr)')
@standard_flags()
@click.option('--top-n', default=3, help='Number of top/bottom performers to highlight')
def agent_coaching_report(
    vendor: str,
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
    top_n: int
):
    """Generate coaching-focused report with individual agent performance and taxonomy breakdown"""
    from src.utils.time_utils import calculate_date_range
    from src.config.test_data import parse_test_data_count, get_preset_display_name
    
    console.print(f"\n📋 [bold cyan]{vendor.title()} Coaching Report[/bold cyan]")
    
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
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return
    
    # Test mode indication
    if test_mode:
        console.print(f"[yellow]🧪 Test Mode: ENABLED ({preset_display})[/yellow]")
    
    # Calculate date range - default to week if not specified
    try:
        start_dt, end_dt = calculate_date_range(
            time_period=time_period or 'week',
            periods_back=periods_back,
            start_date=start_date,
            end_date=end_date,
            end_is_yesterday=True
        )
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return
    
    console.print(f"Period: {start_dt.date()} to {end_dt.date()}")
    console.print(f"Highlighting: Top {top_n} and Bottom {top_n} performers\n")
    
    # Generate gamma flag derived from output format
    generate_gamma = output_format == 'gamma'
    
    asyncio.run(run_agent_coaching_report(
        vendor, start_dt, end_dt, top_n, generate_gamma,
        test_mode=test_mode,
        test_data_count=test_count,
        output_dir=output_dir
    ))


@cli.command()
@click.option('--model', default='gpt-4o-mini', help='AI model to use for chat')
@click.option('--enable-cache', is_flag=True, help='Enable semantic caching')
@click.option('--railway', is_flag=True, help='Enable Railway deployment mode')
def chat(model: str, enable_cache: bool, railway: bool):
    """Start interactive chat interface for natural language command translation"""
    run_chat_interface(model=model, enable_cache=enable_cache, railway=railway)


async def run_topic_based_analysis_custom(
    start_date: datetime, 
    end_date: datetime, 
    generate_gamma: bool,
    test_mode: bool = False,
    test_data_count: str = "100",
    audit_trail: bool = False,
    digest_mode: bool = False,
    orchestrator_factory=None,
    output_prefix: str = "topic_based",
    output_subdir: Optional[str] = None
):
    """Run topic-based analysis with custom date range"""
    try:
        # Import output_manager first (used early for console recording)
        from src.utils.output_manager import get_output_directory
        
        # 🔧 ENABLE CONSOLE RECORDING (capture ALL output to .log file!)
        # This ensures users have complete logs even if SSE disconnects
        console.record = True
        output_base_dir = get_output_directory()
        
        # Comment 3: Add timing logs for heavy imports
        verbose_imports = os.getenv('VERBOSE', '').lower() in ('1', 'true', 'yes')
        if verbose_imports:
            import time as time_module
            import_start = time_module.monotonic()
            console.print(f"[dim]⏱️  Importing TopicOrchestrator and ChunkedFetcher...[/dim]")
        
        from src.agents.topic_orchestrator import TopicOrchestrator
        from src.services.chunked_fetcher import ChunkedFetcher
        
        if verbose_imports:
            import_duration = time_module.monotonic() - import_start
            console.print(f"[dim]✅ Heavy imports completed in {import_duration:.2f}s[/dim]")
        
        from src.services.gamma_generator import GammaGenerator
        from src.services.audit_trail import AuditTrail
        from src.utils.time_utils import detect_period_type
        
        # Initialize audit trail if enabled
        audit = None
        if audit_trail:
            audit = AuditTrail(output_dir=str(get_output_directory()))
            audit.step("Initialization", "Started Voice of Customer Analysis", {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'test_mode': test_mode,
                'generate_gamma': generate_gamma
            })
            console.print("📋 [purple]Audit Trail Mode: ENABLED[/purple] - Generating detailed analysis narration\n")
        
        # Fetch conversations (or generate test data)
        if test_mode:
            console.print(f"🧪 [yellow]TEST MODE: Generating {test_data_count} mock conversations...[/yellow]")
            from src.services.test_data_generator import TestDataGenerator
            generator = TestDataGenerator()
            conversations = generator.generate_conversations(
                count=int(test_data_count),
                start_date=start_date,
                end_date=end_date
            )
            console.print(f"   ✅ Generated {len(conversations)} test conversations\n")
            
            if audit:
                audit.step("Data Generation", f"Generated {len(conversations)} test conversations", {
                    'count': len(conversations),
                    'method': 'TestDataGenerator',
                    'distribution': 'Realistic (tiers, topics, languages)'
                })
        else:
            console.print("📥 Fetching conversations from Intercom...")
            if audit:
                audit.step("Data Fetching", "Started fetching conversations from Intercom API", {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'api': 'Intercom Conversations Search API'
                })
            
            # ChunkedFetcher now uses simple mode - no chunking, no timeouts
            fetcher = ChunkedFetcher()
            conversations = await fetcher.fetch_conversations_chunked(start_date, end_date)
            console.print(f"   ✅ Fetched {len(conversations)} conversations\n")
            
            if audit:
                audit.step("Data Fetching", f"Fetched {len(conversations)} conversations", {
                    'count': len(conversations),
                    'method': 'ChunkedFetcher',
                    'chunking_strategy': 'Daily chunks with preprocessing'
                })
        
        # Detect period type from date range
        period_type, period_label = detect_period_type(start_date, end_date)
        
        if audit:
            audit.decision(
                "What time period does this analysis cover?",
                f"{period_type} ({period_label})",
                f"Based on date range {start_date.date()} to {end_date.date()}",
                {'period_type': period_type, 'period_label': period_label}
            )
        
        # Initialize execution monitor for agent-level tracking
        from src.services.execution_monitor import get_execution_monitor
        monitor = get_execution_monitor()
        
        # Start execution tracking
        await monitor.start_execution(
            command='voice-of-customer',
            args=[],
            date_range={'start': start_date.isoformat(), 'end': end_date.isoformat()},
            conversations_count=len(conversations)
        )
        
        orchestrator_cls = orchestrator_factory or TopicOrchestrator
        orchestrator = orchestrator_cls(audit_trail=audit, execution_monitor=monitor)
        week_id = start_date.strftime('%Y-W%W')
        
        results = await orchestrator.execute_weekly_analysis(
            conversations=conversations,
            week_id=week_id,
            start_date=start_date,
            end_date=end_date,
            period_type=period_type,
            period_label=period_label,
            digest_mode=digest_mode
        )
        
        # Save output
        from src.utils.output_manager import get_output_file_path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{output_prefix}_{week_id}_{timestamp}.md"
        if output_subdir:
            filename = f"{output_subdir}/{filename}"
        report_file = get_output_file_path(filename)
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            f.write(results.get('formatted_report', ''))
        
        # Save audit trail if enabled
        if audit:
            audit.step("Output Generation", "Saved analysis report", {
                'file': str(report_file),
                'format': 'markdown'
            })
            
            audit_md = audit.save_report()
            audit_json = audit.save_json()
            
            console.print(f"\n📋 [purple]Audit Trail Reports Generated:[/purple]")
            console.print(f"   📄 Narrative Report: {audit_md}")
            console.print(f"   📊 JSON Data: {audit_json}")
            console.print(f"   ℹ️  Review these files to validate the analysis methodology\n")
        
        console.print(f"✅ Topic-based analysis complete")
        console.print(f"📁 Report: {report_file}")
        
        # Generate Gamma presentation if requested
        if generate_gamma:
            console.print("\n🎨 Generating Gamma presentation...")
            try:
                from src.services.gamma_client import GammaClient
                
                gamma_client = GammaClient()
                
                # Send our multi-agent markdown report directly to Gamma
                # Don't use PresentationBuilder - it throws away our work and uses generic templates
                markdown_report = results.get('formatted_report', '')
                
                if not markdown_report:
                    console.print("[yellow]⚠️  No markdown report found - skipping Gamma generation[/yellow]")
                    return
                
                console.print(f"   Sending {len(markdown_report)} characters to Gamma API...")
                
                generation_id = await gamma_client.generate_presentation(
                    input_text=markdown_report,
                    format="presentation",
                    text_mode="preserve",  # Preserve our markdown text
                    card_split="inputTextBreaks",  # Use our --- breaks for slides
                    theme_name="Night Sky",  # Professional dark theme
                    text_options={
                        "tone": "professional, analytical",
                        "audience": "executives, leadership team"
                    }
                )
                
                console.print(f"   ✅ Generation ID: {generation_id}")
                console.print("   ⏳ Waiting for Gamma to process (max 8 minutes)...")
                
                # Use GammaClient.poll_generation() with backoff
                status = await gamma_client.poll_generation(generation_id, max_polls=30, poll_interval=2.0)
                
                console.print(f"   Poll completed with status: {status.get('status')}")
                
                if status.get('status') == 'completed':
                    gamma_url = status.get('gammaUrl')  # Use v0.2 field name
                    if gamma_url:
                        console.print(f"\n🎉 [bold green]SUCCESS![/bold green]")
                        console.print(f"📊 Gamma URL: {gamma_url}")
                        
                        # Save URL to file with descriptive name
                        from src.utils.time_utils import generate_descriptive_filename
                        url_filename = generate_descriptive_filename(
                            'Gamma_URL_Topic', start_date, end_date, file_type='txt', 
                            period_label=results.get('period_label', 'Custom')
                        )
                        url_file = output_base_dir / url_filename
                        with open(url_file, 'w') as f:
                            f.write(gamma_url)
                        console.print(f"📁 URL saved to: {url_file}")
                        
                        # Return URL for CLI output
                        return {'gamma_url': gamma_url, 'url_file': str(url_file)}
                    else:
                        console.print("[yellow]⚠️  Generation completed but no URL returned[/yellow]")
                elif status.get('status') == 'failed':
                    error_msg = status.get('error', 'Unknown error')
                    console.print(f"[red]❌ Gamma generation FAILED: {error_msg}[/red]")
                    console.print(f"[yellow]Generation ID: {generation_id}[/yellow]")
                else:
                    console.print(f"[yellow]⚠️  Unexpected status: {status.get('status')}[/yellow]")
                    console.print(f"[yellow]Full status response: {status}[/yellow]")
                    
            except Exception as e:
                console.print(f"\n[red]{'='*60}[/red]")
                console.print(f"[red]❌ GAMMA GENERATION ERROR[/red]")
                console.print(f"[red]{'='*60}[/red]")
                console.print(f"[red]Error: {e}[/red]")
                console.print(f"[red]Type: {type(e).__name__}[/red]")
                import traceback
                console.print(f"[red]{traceback.format_exc()}[/red]")
                console.print(f"[red]{'='*60}[/red]")
                # Don't raise - let the analysis complete without Gamma
    except Exception as e:
        console.print(f"[red]❌ Analysis failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise





if __name__ == "__main__":
    cli()
