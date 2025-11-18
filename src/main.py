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
from rich.console import Console
from rich.panel import Panel

# Note: CLI module exists but implementations are still in this file for now
# TODO: Complete migration to src/cli/ module structure

# Core imports for basic functionality
from src.config.settings import settings
from src.models.analysis_models import AnalysisRequest, AnalysisMode
from src.utils.logger import setup_logging
from src.utils.cli_help import help_system
from src.services.intercom_sdk_service import IntercomSDKService

console = Console()


# ===== HELPER FUNCTIONS =====
def setup_verbose_logging():
    """Enable DEBUG level logging for all relevant modules."""
    logging.getLogger().setLevel(logging.DEBUG)
    for module in ['agents', 'services', 'src.agents', 'src.services']:
        logging.getLogger(module).setLevel(logging.DEBUG)
    console.print(f"[yellow]🔍 Verbose Logging: ENABLED (DEBUG level)[/yellow]")

def show_audit_trail_enabled():
    """Display audit trail enabled message."""
    console.print("[purple]📋 Audit Trail Mode: ENABLED[/purple]")


# ===== CLI FLAGS UNIFICATION =====
# Import shared utilities for consistent date handling and test data
from src.utils.time_utils import TIME_PERIOD_CHOICES, TIME_PERIOD_HELP, PERIODS_BACK_HELP
from src.config.test_data import PRESET_HELP_TEXT

# Define reusable flag groups for consistent behavior across all commands
DEFAULT_FLAGS = [
    click.option('--start-date', help='Start date (YYYY-MM-DD)'),
    click.option('--end-date', help='End date (YYYY-MM-DD)'),
    click.option('--time-period', 
                 type=click.Choice(TIME_PERIOD_CHOICES),
                 help=TIME_PERIOD_HELP),
    click.option('--periods-back', type=int, default=1,
                 help=PERIODS_BACK_HELP),
]

OUTPUT_FLAGS = [
    click.option('--output-format', 
                 type=click.Choice(['markdown', 'json', 'excel', 'gamma']),
                 default='markdown',
                 help='Output format for results'),
    click.option('--gamma-export', 
                 type=click.Choice(['pdf', 'pptx']),
                 help='Gamma export format (when output-format=gamma)'),
    click.option('--output-dir', default='outputs',
                 help='Directory for output files'),
]

TEST_FLAGS = [
    click.option('--test-mode', is_flag=True, 
                 help='Use mock data instead of API calls'),
    click.option('--test-data-count', type=str, default='100',
                 help=PRESET_HELP_TEXT),
]

DEBUG_FLAGS = [
    click.option('--verbose', is_flag=True, 
                 help='Enable DEBUG level logging'),
    click.option('--audit-trail', is_flag=True,
                 help='Enable audit trail narration'),
]

ANALYSIS_FLAGS = [
    click.option('--ai-model',
                 type=click.Choice(['openai', 'claude']),
                 default=None,
                 help='AI model to use for analysis'),
    click.option('--filter-category',
                 help='Filter by taxonomy category (e.g., Billing, Bug, API)'),
]

# Helper function to apply flag groups
def apply_flags(flag_list):
    """Decorator to apply a list of click options to a command"""
    def decorator(func):
        for option in reversed(flag_list):
            func = option(func)
        return func
    return decorator

# Composite decorator for standard flags
def standard_flags(
    include_time=True,
    include_output=True,
    include_test=True,
    include_debug=True,
    include_analysis=True
):
    """
    Composite decorator that applies standard flag groups to commands.
    
    This ensures consistent flag availability across commands unless explicitly opted out.
    
    Args:
        include_time: Include time period flags (start-date, end-date, time-period, periods-back)
        include_output: Include output flags (output-format, gamma-export, output-dir)
        include_test: Include test flags (test-mode, test-data-count)
        include_debug: Include debug flags (verbose, audit-trail)
        include_analysis: Include analysis flags (ai-model, filter-category)
    
    Usage:
        @cli.command()
        @standard_flags()
        def my_command(...):
            pass
        
        # Or with customization:
        @cli.command()
        @standard_flags(include_test=False)  # Exclude test flags
        def my_command(...):
            pass
    """
    def decorator(func):
        flags_to_apply = []
        
        if include_analysis:
            flags_to_apply.extend(ANALYSIS_FLAGS)
        if include_debug:
            flags_to_apply.extend(DEBUG_FLAGS)
        if include_test:
            flags_to_apply.extend(TEST_FLAGS)
        if include_output:
            flags_to_apply.extend(OUTPUT_FLAGS)
        if include_time:
            flags_to_apply.extend(DEFAULT_FLAGS)
        
        # Apply flags in reverse order (Click convention)
        for option in reversed(flags_to_apply):
            func = option(func)
        
        return func
    
    return decorator


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--output-dir', default='outputs', help='Output directory for reports')
def cli(verbose: bool, output_dir: str):
    """Intercom to Gamma Analysis Tool - Dual Mode Analysis"""
    setup_logging(verbose)
    settings.output_directory = output_dir
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    console.print(Panel.fit(
        "[bold blue]Intercom to Gamma Analysis Tool[/bold blue]\n"
        "Dual-mode conversation analysis for Voice of Customer and trend analysis",
        border_style="blue"
    ))


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
    console.print("[bold green]Testing API Connections[/bold green]")

    # Test Intercom connection
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Testing Intercom API...", total=None)

        try:
            intercom_service = IntercomSDKService()
            # Test with a simple request
            test_result = asyncio.run(intercom_service.test_connection())
            progress.update(task, description="✅ Intercom API connection successful")
        except Exception as e:
            progress.update(task, description=f"❌ Intercom API connection failed: {e}")
            return

    # Test OpenAI connection
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Testing OpenAI API...", total=None)

        try:
            openai_client = OpenAIClient()
            test_result = asyncio.run(openai_client.test_connection())
            progress.update(task, description="✅ OpenAI API connection successful")
        except Exception as e:
            progress.update(task, description=f"❌ OpenAI API connection failed: {e}")
            return

    # Test Gamma connection (if API key is provided)
    if settings.gamma_api_key:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Testing Gamma API...", total=None)

            try:
                gamma_client = GammaClient()
                test_result = asyncio.run(gamma_client.test_connection())
                progress.update(task, description="✅ Gamma API connection successful")
            except Exception as e:
                progress.update(task, description=f"❌ Gamma API connection failed: {e}")
                return

    console.print("\n[bold green]All API connections successful![/bold green]")
    console.print("You can now run analysis commands.")


@cli.command()
def system_info():
    """Show system information for debugging"""
    console.print("[bold green]System Information[/bold green]")
    show_system_info()


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
    from src.cli.commands import list_snapshots
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
    from src.cli.commands import export_snapshot_schema
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
    from src.cli.commands import compare_snapshots
    
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
    help_system.show_main_help()

@cli.command()
def interactive():
    """Start interactive mode with guided prompts"""
    help_system.interactive_mode()

@cli.command()
def list_commands():
    """List all available commands"""
    help_system.show_main_help()

@cli.command()
def examples():
    """Show usage examples"""
    help_system.show_examples()

@cli.command()
def show_categories():
    """List available categories"""
    help_system.show_categories()

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
    from src.utils.time_utils import calculate_date_range
    from src.config.test_data import parse_test_data_count, get_preset_display_name
    
    # Deprecation warning for --days
    if days != 30 or (not time_period and not start_date and not end_date):
        console.print("[yellow]⚠️  Warning: --days is deprecated. Please use --time-period and --periods-back instead.[/yellow]")
        console.print("[yellow]   Example: --time-period month --periods-back 1 (for last 30 days)[/yellow]")
    
    console.print(f"[bold green]Technical Troubleshooting Analysis[/bold green]")
    
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
    
    # Determine if AI report should be generated based on output format
    generate_ai_report = output_format in ['markdown', 'gamma']
    
    # Run technical analysis
    asyncio.run(run_technical_analysis_v2(start_dt, end_dt, max_pages, generate_ai_report))

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
    console.print("[bold green]Current Configuration[/bold green]")
    
    # Create configuration table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Intercom API Version", settings.intercom_api_version)
    table.add_row("OpenAI Model", settings.openai_model)
    table.add_row("Default Analysis Days", str(settings.default_analysis_days))
    table.add_row("Output Directory", settings.output_directory)
    table.add_row("Log Level", settings.log_level)
    table.add_row("Tier 1 Countries", ", ".join(settings.default_tier1_countries))
    
    console.print(table)


async def run_voice_analysis(request: AnalysisRequest, generate_gamma: bool, output_format: str):
    """Run Voice of Customer analysis."""
    try:
        # Initialize services
        intercom_service = IntercomSDKService()
        metrics_calculator = MetricsCalculator()
        openai_client = OpenAIClient()
        
        # Initialize analyzer
        analyzer = VoiceAnalyzer(intercom_service, metrics_calculator, openai_client)
        
        # Run analysis
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Running Voice of Customer analysis...", total=None)
            
            results = await analyzer.analyze(request)
            
            progress.update(task, description="✅ Analysis completed")
        
        # Display results
        display_voice_results(results)
        
        # Generate output
        if output_format == 'json':
            save_json_output(results, f"voice_analysis_{request.month}_{request.year}")
        else:
            save_markdown_output(results, f"voice_analysis_{request.month}_{request.year}")
        
        # Generate Gamma presentation if requested
        if generate_gamma and output_format == 'gamma':
            await generate_gamma_presentation(results, f"voice_analysis_{request.month}_{request.year}")
        
        console.print(f"\n[bold green]Analysis completed successfully![/bold green]")
        console.print(f"Results saved to: {settings.output_directory}/")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


async def run_trend_analysis(request: AnalysisRequest, generate_gamma: bool, output_format: str):
    """Run trend analysis."""
    try:
        # Initialize services
        intercom_service = IntercomSDKService()
        metrics_calculator = MetricsCalculator()
        openai_client = OpenAIClient()
        
        # Initialize analyzer
        analyzer = TrendAnalyzer(intercom_service, metrics_calculator, openai_client)
        
        # Run analysis
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Running trend analysis...", total=None)
            
            results = await analyzer.analyze(request)
            
            progress.update(task, description="✅ Analysis completed")
        
        # Display results
        display_trend_results(results)
        
        # Generate output
        if output_format == 'json':
            save_json_output(results, f"trend_analysis_{request.start_date}_{request.end_date}")
        else:
            save_markdown_output(results, f"trend_analysis_{request.start_date}_{request.end_date}")
        
        # Generate Gamma presentation if requested
        if generate_gamma and output_format == 'gamma':
            await generate_gamma_presentation(results, f"trend_analysis_{request.start_date}_{request.end_date}")
        
        console.print(f"\n[bold green]Analysis completed successfully![/bold green]")
        console.print(f"Results saved to: {settings.output_directory}/")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


async def run_custom_analysis(request: AnalysisRequest, generate_gamma: bool, output_format: str):
    """Run custom analysis."""
    try:
        # Initialize services
        intercom_service = IntercomSDKService()
        metrics_calculator = MetricsCalculator()
        openai_client = OpenAIClient()
        
        # Initialize analyzer (using trend analyzer as base)
        analyzer = TrendAnalyzer(intercom_service, metrics_calculator, openai_client)
        
        # Run analysis
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Running custom analysis...", total=None)
            
            results = await analyzer.analyze(request)
            
            progress.update(task, description="✅ Analysis completed")
        
        # Display results
        display_custom_results(results)
        
        # Generate output
        if output_format == 'json':
            save_json_output(results, f"custom_analysis_{request.start_date}_{request.end_date}")
        else:
            save_markdown_output(results, f"custom_analysis_{request.start_date}_{request.end_date}")
        
        # Generate Gamma presentation if requested
        if generate_gamma and output_format == 'gamma':
            await generate_gamma_presentation(results, f"custom_analysis_{request.start_date}_{request.end_date}")
        
        console.print(f"\n[bold green]Analysis completed successfully![/bold green]")
        console.print(f"Results saved to: {settings.output_directory}/")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def display_voice_results(results):
    """Display Voice of Customer results."""
    console.print("\n[bold blue]Voice of Customer Analysis Results[/bold blue]")
    
    # Key metrics table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Conversations", f"{results.total_conversations:,}")
    table.add_row("AI Resolution Rate", f"{results.ai_resolution_rate}%")
    table.add_row("Median Response Time", results.median_response_time)
    table.add_row("Median Handling Time", results.median_handling_time)
    table.add_row("Median Resolution Time", results.median_resolution_time)
    table.add_row("Overall CSAT", f"{results.overall_csat}%")
    table.add_row("Analysis Duration", f"{results.analysis_duration_seconds:.2f}s")
    
    console.print(table)


def display_trend_results(results):
    """Display trend analysis results."""
    console.print("\n[bold blue]Trend Analysis Results[/bold blue]")
    
    # Key trends table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Trend", style="cyan")
    table.add_column("Description", style="green")
    
    for trend in results.key_trends[:5]:  # Top 5 trends
        table.add_row(trend.get("name", "Unknown"), trend.get("description", "No description"))
    
    console.print(table)


def display_custom_results(results):
    """Display custom analysis results."""
    console.print("\n[bold blue]Custom Analysis Results[/bold blue]")
    console.print(f"Analysis completed in {results.analysis_duration_seconds:.2f} seconds")
    console.print(f"Conversations analyzed: {results.total_conversations_analyzed:,}")


def save_json_output(results, filename: str):
    """Save results as JSON."""
    import json
    from pathlib import Path
    
    output_path = Path(settings.effective_output_directory) / f"{filename}.json"
    
    with open(output_path, 'w') as f:
        json.dump(results.dict(), f, indent=2, default=str)
    
    console.print(f"JSON output saved to: {output_path}")


def save_markdown_output(results, filename: str):
    """Save results as Markdown."""
    from pathlib import Path
    
    output_path = Path(settings.effective_output_directory) / f"{filename}.md"
    
    # Generate markdown content based on results type
    if hasattr(results, 'analysis_content'):
        content = results.analysis_content
    else:
        content = f"# {filename.replace('_', ' ').title()}\n\nAnalysis completed successfully."
    
    with open(output_path, 'w') as f:
        f.write(content)
    
    console.print(f"Markdown output saved to: {output_path}")


async def run_data_export(start_date, end_date, export_format: str, max_pages: Optional[int], include_metrics: bool):
    """Run data export."""
    try:
        # Initialize services
        intercom_service = IntercomSDKService()
        data_exporter = DataExporter()
        
        # Fetch conversations
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Fetching conversations...", total=None)
            
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())
            
            conversations = await intercom_service.fetch_conversations_by_date_range(
                start_dt, end_dt, max_conversations=max_pages
            )
            
            progress.update(task, description=f"✅ Fetched {len(conversations)} conversations")
        
        # Export data
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Exporting data...", total=None)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_results = {}
            
            if export_format in ["excel", "all"]:
                excel_path = data_exporter.export_conversations_to_excel(
                    conversations, f"export_{timestamp}", include_metrics=include_metrics
                )
                export_results["excel"] = excel_path
            
            if export_format in ["csv", "all"]:
                csv_paths = data_exporter.export_conversations_to_csv(
                    conversations, f"export_{timestamp}"
                )
                export_results["csv"] = csv_paths
            
            if export_format in ["json", "all"]:
                json_path = data_exporter.export_raw_data_to_json(
                    conversations, f"export_{timestamp}"
                )
                export_results["json"] = json_path
            
            if export_format in ["parquet", "all"]:
                parquet_path = data_exporter.export_to_parquet(
                    conversations, f"export_{timestamp}"
                )
                export_results["parquet"] = parquet_path
            
            progress.update(task, description="✅ Export completed")
        
        # Display results
        console.print(f"\n[bold green]Export completed successfully![/bold green]")
        console.print(f"Total conversations exported: {len(conversations):,}")
        
        for format_type, path in export_results.items():
            if isinstance(path, list):
                console.print(f"{format_type.upper()} files: {len(path)} files")
                for p in path:
                    console.print(f"  • {p}")
            else:
                console.print(f"{format_type.upper()}: {path}")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


async def run_technical_analysis(days: int, max_pages: Optional[int], generate_ai_report: bool):
    """Run technical troubleshooting analysis."""
    try:
        # Initialize services
        intercom_service = IntercomSDKService()
        data_exporter = DataExporter()
        openai_client = OpenAIClient() if generate_ai_report else None
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        console.print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Fetch conversations
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Fetching conversations...", total=None)
            
            conversations = await intercom_service.fetch_conversations_by_date_range(
                start_date, end_date, max_pages=max_pages
            )
            
            progress.update(task, description=f"✅ Fetched {len(conversations)} conversations")
        
        if not conversations:
            console.print("[yellow]No conversations found for the specified date range.[/yellow]")
            return
        
        # Export technical troubleshooting analysis
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Analyzing technical patterns...", total=None)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = data_exporter.export_technical_troubleshooting_analysis(
                conversations, f"tech_analysis_{timestamp}"
            )
            
            progress.update(task, description="✅ Technical analysis completed")
        
        console.print(f"\n[bold green]Technical Analysis Completed![/bold green]")
        console.print(f"Total conversations analyzed: {len(conversations):,}")
        console.print(f"CSV Export: {csv_path}")
        
        # Generate AI report if requested
        if generate_ai_report and openai_client:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Generating AI insights report...", total=None)
                
                # Prepare data summary for AI
                data_summary = f"""
                Total conversations: {len(conversations)}
                Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}
                
                Sample conversation data:
                {json.dumps(conversations[:3], indent=2, default=str)}
                """
                
                # Generate AI report
                from src.config.prompts import PromptTemplates
                prompt = PromptTemplates.get_technical_troubleshooting_prompt(
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d'),
                    data_summary
                )
                
                ai_report = await openai_client.generate_text(prompt)
                
                # Save AI report
                report_path = data_exporter.output_dir / f"tech_analysis_report_{timestamp}.md"
                with open(report_path, 'w') as f:
                    f.write(ai_report or "No report generated")
                
                progress.update(task, description="✅ AI report generated")
            
            console.print(f"AI Report: {report_path}")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def run_general_query(query_type: Optional[str], suggestion: Optional[str], custom_query: Optional[str], export_format: str, max_pages: Optional[int]):
    """Run general query."""
    try:
        # Initialize services
        intercom_service = IntercomSDKService()
        data_exporter = DataExporter()
        query_service = GeneralQueryService(intercom_service, data_exporter)
        
        # Build query
        query = {}
        
        if custom_query:
            import json
            query = json.loads(custom_query)
        elif query_type and suggestion:
            query = query_service.build_suggested_query(query_type, suggestion)
        else:
            console.print("[red]Error: Must provide either custom-query or both query-type and suggestion[/red]")
            sys.exit(1)
        
        console.print(f"Query: {query}")
        
        # Execute query
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Executing query...", total=None)
            
            results = await query_service.execute_query(
                query, max_pages=max_pages, export_format=export_format
            )
            
            progress.update(task, description="✅ Query completed")
        
        # Display results
        console.print(f"\n[bold green]Query executed successfully![/bold green]")
        console.print(f"Total conversations found: {results['total_conversations']:,}")
        
        export_results = results.get('export_results', {})
        for format_type, path in export_results.items():
            if isinstance(path, list):
                console.print(f"{format_type.upper()} files: {len(path)} files")
                for p in path:
                    console.print(f"  • {p}")
            else:
                console.print(f"{format_type.upper()}: {path}")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


async def generate_gamma_presentation(results, filename: str):
    """Generate Gamma presentation."""
    try:
        gamma_client = GammaClient()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Generating Gamma presentation...", total=None)
            
            presentation = await gamma_client.create_presentation(results)
            
            progress.update(task, description="✅ Gamma presentation generated")
        
        if presentation.presentation_url:
            console.print(f"Gamma presentation created: {presentation.presentation_url}")
        else:
            console.print("Gamma presentation generated successfully")
        
    except Exception as e:
        console.print(f"[yellow]Warning: Could not generate Gamma presentation: {e}[/yellow]")


# Async helper functions for new commands
async def run_technical_analysis_v2(start_date: datetime, end_date: datetime, max_pages: Optional[int], generate_ai_report: bool):
    """Run technical analysis with improved pipeline."""
    try:
        # Initialize services
        pipeline = ELTPipeline()
        openai_client = OpenAIClient() if generate_ai_report else None
        
        console.print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Extract and load data
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Extracting and loading data...", total=None)
            
            stats = await pipeline.extract_and_load(start_date, end_date, max_pages)
            
            progress.update(task, description=f"✅ Loaded {stats['conversations_count']} conversations")
        
        if stats['conversations_count'] == 0:
            console.print("[yellow]No conversations found for the specified date range.[/yellow]")
            return
        
        # Transform for technical analysis
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Analyzing technical patterns...", total=None)
            
            filters = {
                'start_date': start_date,
                'end_date': end_date
            }
            
            df = pipeline.transform_for_analysis("technical", filters)
            
            progress.update(task, description="✅ Technical analysis completed")
        
        # Export results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = pipeline.export_analysis_data("technical", filters, "csv")
        
        console.print(f"\n[bold green]Technical Analysis Completed![/bold green]")
        console.print(f"Total conversations analyzed: {stats['conversations_count']:,}")
        console.print(f"CSV Export: {csv_path}")
        
        # Generate AI report if requested
        if generate_ai_report and openai_client:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Generating AI insights report...", total=None)
                
                # Prepare data summary for AI
                data_summary = f"""
                Total conversations: {stats['conversations_count']}
                Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}
                
                Technical patterns found: {len(df)} patterns
                """
                
                # Generate AI report
                from config.prompts import PromptTemplates
                prompt = PromptTemplates.get_technical_troubleshooting_prompt(
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d'),
                    data_summary
                )
                
                ai_report = await openai_client.generate_analysis(prompt)
                
                # Save AI report
                report_path = pipeline.output_dir / f"tech_analysis_report_{timestamp}.md"
                with open(report_path, 'w') as f:
                    f.write(ai_report or "No report generated")
                
                progress.update(task, description="✅ AI report generated")
            
            console.print(f"AI Report: {report_path}")
        
        pipeline.close()
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def run_macro_analysis(start_date: datetime, end_date: datetime, min_occurrences: int):
    """Run macro discovery analysis."""
    console.print(f"[yellow]Macro analysis not yet implemented[/yellow]")
    console.print(f"Would analyze {min_occurrences}+ occurrences from {start_date.date()} to {end_date.date()}")


async def run_fin_analysis(start_date: datetime, end_date: datetime, detailed: bool):
    """Run Fin escalation analysis."""
    console.print(f"[yellow]Fin analysis not yet implemented[/yellow]")
    console.print(f"Would analyze Fin effectiveness from {start_date.date()} to {end_date.date()}")


async def run_agent_analysis(agent: str, start_date: datetime, end_date: datetime):
    """Run agent performance analysis (legacy version)."""
    # Call the full version with default parameters
    await run_agent_performance_analysis(agent, start_date, end_date, None, False, False)


def _display_individual_breakdown(data: Dict, vendor_name: str):
    """Display individual agent breakdown results"""
    from rich.table import Table
    
    # Team summary
    team_metrics = data.get('team_metrics', {})
    console.print(f"[bold]📊 Team Summary:[/bold]")
    console.print(f"   Total Agents: {team_metrics.get('total_agents', 0)}")
    console.print(f"   Total Conversations: {team_metrics.get('total_conversations', 0)}")
    console.print(f"   Team FCR: {team_metrics.get('team_fcr_rate', 0):.1%}")
    console.print(f"   Team Escalation Rate: {team_metrics.get('team_escalation_rate', 0):.1%}")
    
    # Add team QA metrics if available
    if team_metrics.get('team_qa_overall') is not None:
        qa_overall = team_metrics.get('team_qa_overall', 0)
        qa_color = "green" if qa_overall >= 0.8 else "yellow" if qa_overall >= 0.6 else "red"
        console.print(f"   Team QA Score: [{qa_color}]{qa_overall:.2f}/1.0[/{qa_color}] "
                     f"(Connection: {team_metrics.get('team_qa_connection', 0):.2f}, "
                     f"Communication: {team_metrics.get('team_qa_communication', 0):.2f}, "
                     f"Content: {team_metrics.get('team_qa_content', 0):.2f})")
        console.print(f"   QA Metrics Available: {team_metrics.get('agents_with_qa_metrics', 0)}/{team_metrics.get('total_agents', 0)} agents")
    console.print()
    
    # Highlights
    if data.get('highlights'):
        console.print(f"[bold green]✨ Highlights:[/bold green]")
        for highlight in data['highlights']:
            console.print(f"   ✓ {highlight}")
        console.print()
    
    # Lowlights
    if data.get('lowlights'):
        console.print(f"[bold yellow]⚠️  Lowlights:[/bold yellow]")
        for lowlight in data['lowlights']:
            console.print(f"   • {lowlight}")
        console.print()
    
    # Individual agents table
    agents = data.get('agents', [])
    if agents:
        console.print(f"[bold]👥 Individual Agent Performance:[/bold]\n")
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Rank", style="dim", width=5)
        table.add_column("Agent Name", width=20)
        table.add_column("Conversations", justify="right", width=13)
        table.add_column("FCR", justify="right", width=8)
        table.add_column("QA Score", justify="right", width=10)
        table.add_column("Escalation", justify="right", width=11)
        table.add_column("Response Time", justify="right", width=13)
        table.add_column("Coaching", width=10)
        
        for agent in sorted(agents, key=lambda a: a.get('fcr_rank', 999)):
            coaching_priority = agent.get('coaching_priority', 'low')
            coaching_color = "red" if coaching_priority == "high" else "yellow" if coaching_priority == "medium" else "green"
            
            # Get QA score if available
            qa_metrics = agent.get('qa_metrics')
            qa_score_display = "N/A"
            if qa_metrics:
                overall_qa = qa_metrics.get('overall_qa_score', 0)
                qa_color = "green" if overall_qa >= 0.8 else "yellow" if overall_qa >= 0.6 else "red"
                qa_score_display = f"[{qa_color}]{overall_qa:.2f}[/{qa_color}]"
            
            table.add_row(
                str(agent.get('fcr_rank', '?')),
                agent.get('agent_name', 'Unknown'),
                str(agent.get('total_conversations', 0)),
                f"{agent.get('fcr_rate', 0):.1%}",
                qa_score_display,
                f"{agent.get('escalation_rate', 0):.1%}",
                f"{agent.get('median_response_hours', 0):.1f}h",
                f"[{coaching_color}]{coaching_priority.upper()}[/{coaching_color}]"
            )
        
        console.print(table)
        console.print()
    
    # Agents needing coaching
    coaching_needed = data.get('agents_needing_coaching', [])
    if coaching_needed:
        console.print(f"[bold red]🎯 Agents Needing Coaching ({len(coaching_needed)}):[/bold red]")
        for agent in coaching_needed[:5]:  # Top 5
            console.print(f"\n   {agent.get('agent_name', 'Unknown')} ({agent.get('agent_email', '')})")
            console.print(f"   FCR: {agent.get('fcr_rate', 0):.1%}, Escalation: {agent.get('escalation_rate', 0):.1%}")
            
            # Add QA metrics if available
            qa_metrics = agent.get('qa_metrics')
            if qa_metrics:
                overall_qa = qa_metrics.get('overall_qa_score', 0)
                qa_color = "green" if overall_qa >= 0.8 else "yellow" if overall_qa >= 0.6 else "red"
                console.print(f"   QA Score: [{qa_color}]{overall_qa:.2f}[/{qa_color}] "
                            f"(Greeting: {qa_metrics.get('greeting_quality_score', 0):.2f}, "
                            f"Grammar: {qa_metrics.get('avg_grammar_errors_per_message', 0):.1f} errors/msg, "
                            f"Formatting: {qa_metrics.get('proper_formatting_rate', 0):.0%})")
                
                # Add QA-specific coaching points
                if qa_metrics.get('greeting_quality_score', 1.0) < 0.6:
                    console.print(f"   [yellow]→ Improve greetings: use customer names and warm opening[/yellow]")
                if qa_metrics.get('avg_grammar_errors_per_message', 0) > 1.0:
                    console.print(f"   [yellow]→ Reduce grammar errors ({qa_metrics.get('avg_grammar_errors_per_message', 0):.1f}/msg)[/yellow]")
                if qa_metrics.get('proper_formatting_rate', 1.0) < 0.7:
                    console.print(f"   [yellow]→ Use proper paragraph breaks and formatting[/yellow]")
            
            focus_areas = agent.get('coaching_focus_areas', [])
            if focus_areas:
                console.print(f"   Focus on: {', '.join(focus_areas[:3])}")
            
            weak_subcats = agent.get('weak_subcategories', [])
            if weak_subcats:
                console.print(f"   Weak subcategories: {', '.join(weak_subcats[:3])}")
        console.print()
    
    # Agents for praise
    praise_worthy = data.get('agents_for_praise', [])
    if praise_worthy:
        console.print(f"[bold green]🌟 Top Performers ({len(praise_worthy)}):[/bold green]")
        for agent in praise_worthy[:5]:  # Top 5
            console.print(f"\n   {agent.get('agent_name', 'Unknown')} ({agent.get('agent_email', '')})")
            console.print(f"   FCR: {agent.get('fcr_rate', 0):.1%}, Rank: #{agent.get('fcr_rank', '?')}")
            
            # Add QA metrics if available
            qa_metrics = agent.get('qa_metrics')
            if qa_metrics:
                overall_qa = qa_metrics.get('overall_qa_score', 0)
                console.print(f"   [green]QA Score: {overall_qa:.2f}/1.0[/green] "
                            f"(Greeting: {qa_metrics.get('greeting_quality_score', 0):.2f}, "
                            f"Communication: {qa_metrics.get('communication_quality_score', 0):.2f}, "
                            f"Content: {qa_metrics.get('content_quality_score', 0):.2f})")
            
            achievements = agent.get('praise_worthy_achievements', [])
            if achievements:
                for achievement in achievements[:2]:
                    console.print(f"   ✓ {achievement}")
        console.print()
    
    # Team training needs
    training_needs = data.get('team_training_needs', [])
    if training_needs:
        console.print(f"[bold]📚 Team Training Needs:[/bold]")
        for need in training_needs[:5]:
            priority = need.get('priority', 'medium')
            priority_color = "red" if priority == "high" else "yellow"
            
            topic = need.get('topic', 'Unknown')
            affected = need.get('affected_agents', [])
            reason = need.get('reason', '')
            
            console.print(f"\n   [{priority_color}]{priority.upper()}[/{priority_color}]: {topic}")
            console.print(f"   {reason}")
            console.print(f"   Affects: {', '.join(affected[:3])}" + 
                         (f" and {len(affected)-3} more" if len(affected) > 3 else ""))
        console.print()
    
    # Week-over-week changes
    wow_changes = data.get('week_over_week_changes')
    if wow_changes:
        console.print(f"[bold]📈 Week-over-Week Changes:[/bold]")
        for metric, change in wow_changes.items():
            direction = "↑" if change > 0 else "↓"
            color = "green" if (change > 0 and 'fcr' in metric) or (change < 0 and 'escalation' in metric) else "yellow"
            console.print(f"   {metric}: [{color}]{direction} {abs(change):.1f}%[/{color}]")
        console.print()


async def run_agent_performance_analysis(
    agent: str, 
    start_date: datetime, 
    end_date: datetime, 
    focus_categories: Optional[str] = None,
    generate_gamma: bool = False,
    individual_breakdown: bool = False,
    analyze_troubleshooting: bool = False,
    test_mode: bool = False,
    test_data_count: int = 100,
    audit_trail: bool = False
):
    """Run comprehensive agent performance analysis with optional Gamma generation."""
    try:
        # Comment 3: Add timing logs for heavy imports
        verbose_imports = verbose or os.getenv('VERBOSE', '').lower() in ('1', 'true', 'yes')
        if verbose_imports:
            import time as time_module
            import_start = time_module.monotonic()
            console.print(f"[dim]⏱️  Importing ChunkedFetcher...[/dim]")
        
        from src.services.chunked_fetcher import ChunkedFetcher
        
        if verbose_imports:
            import_duration = time_module.monotonic() - import_start
            console.print(f"[dim]✅ ChunkedFetcher imported in {import_duration:.2f}s[/dim]")
        
        from src.agents.agent_performance_agent import AgentPerformanceAgent
        from src.agents.base_agent import AgentContext
        from src.services.gamma_generator import GammaGenerator
        from src.services.gamma_client import GammaAPIError
        from pathlib import Path
        import json
        
        agent_name = {'horatio': 'Horatio', 'boldr': 'Boldr', 'escalated': 'Senior Staff'}.get(agent, agent)
        
        console.print(f"\n📊 [bold cyan]{agent_name} Performance Analysis[/bold cyan]")
        console.print(f"Date Range: {start_date.date()} to {end_date.date()}")
        if focus_categories:
            console.print(f"Focus: {focus_categories}\n")
        
        # Fetch conversations (or generate test data)
        if test_mode:
            console.print(f"🧪 [yellow]TEST MODE: Generating {test_data_count} mock conversations for {agent_name}...[/yellow]")
            from src.services.test_data_generator import TestDataGenerator
            generator = TestDataGenerator()
            all_conversations = generator.generate_conversations(
                count=test_data_count,
                start_date=start_date,
                end_date=end_date,
                agent_filter=agent  # Generate data specific to this agent
            )
            console.print(f"   ✅ Generated {len(all_conversations)} test conversations\n")
        else:
            console.print("📥 Fetching conversations...")
            fetcher = ChunkedFetcher()
            all_conversations = await fetcher.fetch_conversations_chunked(
                start_date=start_date,
                end_date=end_date
            )
            console.print(f"   ✅ Fetched {len(all_conversations)} total conversations\n")
        
        # Filter by agent email domain
        console.print(f"🔍 Filtering conversations for {agent_name}...")
        agent_conversations = []
        
        # Agent email domain patterns
        agent_patterns = {
            'horatio': ['@hirehoratio.co', '@horatio.com'],
            'boldr': ['@boldrimpact.com', '@boldr'],
            'escalated': ['dae-ho', 'max jackson', 'max.jackson', 'hilary']
        }
        
        patterns = agent_patterns.get(agent, [])
        
        for conv in all_conversations:
            # Extract admin emails
            admin_emails = []
            
            # From conversation_parts
            parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
            for part in parts:
                author = part.get('author', {})
                if author.get('type') == 'admin':
                    email = author.get('email', '')
                    if email:
                        admin_emails.append(email.lower())
            
            # From source
            source = conv.get('source', {})
            if source:
                author = source.get('author', {})
                if author.get('type') == 'admin':
                    email = author.get('email', '')
                    if email:
                        admin_emails.append(email.lower())
            
            # From assignee
            assignee = conv.get('admin_assignee', {})
            if assignee:
                email = assignee.get('email', '')
                if email:
                    admin_emails.append(email.lower())
            
            # Check if any email matches agent patterns
            matched = False
            for email in admin_emails:
                if agent == 'escalated':
                    # Check for escalated staff names in email
                    if any(pattern.replace(' ', '.') in email or pattern.replace(' ', '') in email 
                          for pattern in patterns):
                        matched = True
                        break
                else:
                    # Check for domain match
                    if any(pattern in email for pattern in patterns):
                        matched = True
                        break
            
            # Also check text for escalated agents
            if not matched and agent == 'escalated':
                text = str(conv.get('conversation_parts', '')).lower()
                if any(pattern.lower() in text for pattern in patterns):
                    matched = True
            
            if matched:
                agent_conversations.append(conv)
        
        console.print(f"   ✅ Found {len(agent_conversations)} {agent_name} conversations ({len(agent_conversations)/len(all_conversations)*100:.1f}% of total)\n")
        
        if len(agent_conversations) == 0:
            console.print(f"[yellow]⚠ No conversations found for {agent_name}[/yellow]")
            console.print(f"[yellow]   This may indicate:[/yellow]")
            console.print(f"[yellow]   - Agent email domains not in conversation data[/yellow]")
            console.print(f"[yellow]   - Date range has no {agent_name} activity[/yellow]")
            console.print(f"[yellow]   - Email patterns need updating[/yellow]")
            return
        
        # Filter by focus categories if specified
        if focus_categories:
            console.print(f"🎯 Filtering by categories: {focus_categories}...")
            categories = [c.strip().lower() for c in focus_categories.split(',')]
            filtered_conversations = []
            
            for conv in agent_conversations:
                tags = [str(t).lower() for t in conv.get('tags', {}).get('tags', [])]
                if any(cat in tag for cat in categories for tag in tags):
                    filtered_conversations.append(conv)
            
            console.print(f"   ✅ {len(filtered_conversations)} conversations match focus categories\n")
            agent_conversations = filtered_conversations
        
        # Create agent context
        context = AgentContext(
            analysis_id=f"agent_performance_{datetime.now().strftime('%Y%m%d')}",
            analysis_type="agent_performance",
            conversations=agent_conversations,
            start_date=start_date,
            end_date=end_date,
            metadata={'agent_filter': agent, 'agent_name': agent_name}
        )
        
        # Preprocess conversations before analysis
        if individual_breakdown:
            from src.services.data_preprocessor import DataPreprocessor
            
            console.print("🔧 Preprocessing conversations...")
            preprocessor = DataPreprocessor()
            agent_conversations, preprocess_stats = preprocessor.preprocess_conversations(
                agent_conversations,
                options={
                    'deduplicate': True,
                    'infer_missing': True,
                    'clean_text': True,
                    'detect_outliers': True
                }
            )
            console.print(f"   ✅ Preprocessed: {preprocess_stats['processed_count']} valid conversations\n")
            
            # Update context with preprocessed conversations
            context.conversations = agent_conversations
        
        # Run agent performance analysis
        console.print(f"🤖 [bold cyan]Analyzing {agent_name} Performance...[/bold cyan]\n")
        if analyze_troubleshooting:
            console.print("   🔍 Troubleshooting analysis enabled (analyzing diagnostic questions and escalation patterns)\n")
        performance_agent = AgentPerformanceAgent(agent_filter=agent)
        result = await performance_agent.execute(
            context, 
            individual_breakdown=individual_breakdown,
            analyze_troubleshooting=analyze_troubleshooting
        )
        
        if not result.success:
            console.print(f"[red]❌ Analysis failed: {result.error_message}[/red]")
            return
        
        # Display results
        data = result.data
        console.print("="*80)
        console.print(f"[bold green]🎉 {agent_name} Performance Analysis Complete![/bold green]")
        console.print("="*80 + "\n")
        
        # Display differently based on analysis type
        if individual_breakdown and 'agents' in data:
            # Individual agent breakdown display
            _display_individual_breakdown(data, agent_name)
        else:
            # Team-level display (original)
            console.print(f"[bold]📊 Overall Metrics:[/bold]")
            console.print(f"   Total Conversations: {data['total_conversations']}")
            console.print(f"   First Contact Resolution: {data['fcr_rate']:.1%}")
            console.print(f"   Median Resolution Time: {data['median_resolution_hours']:.1f} hours")
            console.print(f"   Escalation Rate: {data['escalation_rate']:.1%}")
            
            # Add QA metrics if available
            if data.get('avg_qa_overall') is not None:
                qa_overall = data.get('avg_qa_overall', 0)
                qa_color = "green" if qa_overall >= 0.8 else "yellow" if qa_overall >= 0.6 else "red"
                console.print(f"   QA Score: [{qa_color}]{qa_overall:.2f}/1.0[/{qa_color}] "
                            f"(Connection: {data.get('avg_qa_connection', 0):.2f}, "
                            f"Communication: {data.get('avg_qa_communication', 0):.2f})")
            
            console.print(f"   Confidence: {result.confidence_level.value}\n")
            
            if data.get('performance_by_category'):
                console.print(f"[bold]📋 Performance by Category:[/bold]")
                for category, metrics in sorted(data['performance_by_category'].items(), 
                                              key=lambda x: x[1]['volume'], reverse=True):
                    console.print(f"   {category}: {metrics['volume']} conversations")
                    console.print(f"      FCR: {metrics['fcr_rate']:.1%}, Escalation: {metrics['escalation_rate']:.1%}, Avg Resolution: {metrics['median_resolution_hours']:.1f}h")
                console.print()
            
            if data.get('llm_insights'):
                console.print(f"[bold]💡 Performance Insights:[/bold]")
                console.print(data['llm_insights'])
                console.print()
        
        # Save results
        output_dir = Path(settings.effective_output_directory)
        output_dir.mkdir(exist_ok=True, parents=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = output_dir / f"agent_performance_{agent}_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        console.print(f"📁 Results saved: {results_file}\n")
        
        # Generate Gamma presentation if requested
        if generate_gamma:
            try:
                console.print(f"🎨 [bold cyan]Generating Gamma presentation...[/bold cyan]")
                
                # Create markdown report
                markdown_report = f"""# {agent_name} Performance Analysis
                
## Analysis Period
{start_date.date()} to {end_date.date()}

---

## Overall Performance

**Total Conversations**: {data['total_conversations']}

**Key Metrics**:
- First Contact Resolution: {data['fcr_rate']:.1%}
- Median Resolution Time: {data['median_resolution_hours']:.1f} hours
- Escalation Rate: {data['escalation_rate']:.1%}

**Quality Assurance (Automated)**:
- Customer Connection Score: {data.get('avg_qa_connection', 'N/A') if isinstance(data.get('avg_qa_connection'), (int, float)) else 'N/A'}
- Communication Quality Score: {data.get('avg_qa_communication', 'N/A') if isinstance(data.get('avg_qa_communication'), (int, float)) else 'N/A'}
- Overall QA Score: {data.get('avg_qa_overall', 'N/A') if isinstance(data.get('avg_qa_overall'), (int, float)) else 'N/A'}

---

## Performance by Category

"""
                
                if data.get('performance_by_category'):
                    for category, metrics in sorted(data['performance_by_category'].items(), 
                                                  key=lambda x: x[1]['volume'], reverse=True):
                        markdown_report += f"""### {category}

**Volume**: {metrics['volume']} conversations

**Metrics**:
- FCR Rate: {metrics['fcr_rate']:.1%}
- Escalation Rate: {metrics['escalation_rate']:.1%}
- Median Resolution: {metrics['median_resolution_hours']:.1f} hours

---

"""
                
                if data.get('llm_insights'):
                    markdown_report += f"""## Performance Insights

{data['llm_insights']}

---
"""
                
                # Generate Gamma presentation
                gamma_generator = GammaGenerator()
                num_cards = min(len(data.get('performance_by_category', {})) + 3, 15)
                
                gamma_result = await gamma_generator.generate_from_markdown(
                    input_text=markdown_report,
                    title=f"{agent_name} Performance Analysis - {start_date.strftime('%b %Y')}",
                    num_cards=num_cards,
                    theme_name=None,
                    export_format=None,
                    output_dir=output_dir
                )
                
                gamma_url = gamma_result.get('gamma_url')
                if gamma_url:
                    console.print(f"\n🎨 [bold green]Gamma presentation generated![/bold green]")
                    console.print(f"📊 Gamma URL: {gamma_url}")
                    console.print(f"💳 Credits used: {gamma_result.get('credits_used', 0)}")
                    console.print(f"⏱️  Generation time: {gamma_result.get('generation_time_seconds', 0):.1f}s\n")
                    
                    # Save Gamma URL
                    gamma_url_file = output_dir / f"gamma_url_agent_{agent}_{timestamp}.txt"
                    with open(gamma_url_file, 'w') as f:
                        f.write(f"{agent_name} Performance Analysis\n")
                        f.write(f"===========================\n\n")
                        f.write(f"Analysis Period: {start_date.date()} to {end_date.date()}\n")
                        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                        f.write(f"Gamma URL: {gamma_url}\n")
                    
                    console.print(f"📁 Gamma URL saved: {gamma_url_file}")
                    
                    # Update results with Gamma metadata
                    data['gamma_presentation'] = {
                        'gamma_url': gamma_url,
                        'generation_id': gamma_result.get('generation_id'),
                        'credits_used': gamma_result.get('credits_used'),
                        'generation_time_seconds': gamma_result.get('generation_time_seconds')
                    }
                    
                    # Re-save with Gamma data
                    with open(results_file, 'w') as f:
                        json.dump(data, f, indent=2, default=str)
                
            except GammaAPIError as e:
                console.print(f"[yellow]Warning: Gamma generation failed: {e}[/yellow]")
            except Exception as e:
                console.print(f"[yellow]Warning: Unexpected error during Gamma generation: {e}[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error in agent performance analysis: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise


async def run_agent_coaching_report(
    vendor: str, 
    start_date: datetime, 
    end_date: datetime, 
    top_n: int, 
    generate_gamma: bool,
    test_mode: bool = False,
    test_data_count: int = 100,
    output_dir: str = 'outputs'
):
    """Run coaching-focused analysis with individual agent breakdowns"""
    try:
        # Comment 3: Add timing logs for heavy imports
        verbose_imports = verbose or os.getenv('VERBOSE', '').lower() in ('1', 'true', 'yes')
        if verbose_imports:
            import time as time_module
            import_start = time_module.monotonic()
            console.print(f"[dim]⏱️  Importing ChunkedFetcher...[/dim]")
        
        from src.services.chunked_fetcher import ChunkedFetcher
        
        if verbose_imports:
            import_duration = time_module.monotonic() - import_start
            console.print(f"[dim]✅ ChunkedFetcher imported in {import_duration:.2f}s[/dim]")
        
        from src.agents.agent_performance_agent import AgentPerformanceAgent
        from src.agents.base_agent import AgentContext
        from src.services.data_preprocessor import DataPreprocessor
        from pathlib import Path
        import json
        
        vendor_name = {'horatio': 'Horatio', 'boldr': 'Boldr'}.get(vendor, vendor.title())
        
        # Fetch conversations (test mode or real)
        console.print("📥 Fetching conversations...")
        if test_mode:
            from src.config.test_data import generate_test_conversations
            all_conversations = generate_test_conversations(test_data_count)
            console.print(f"   ✅ Generated {len(all_conversations)} test conversations\n")
        else:
            fetcher = ChunkedFetcher()
            all_conversations = await fetcher.fetch_conversations_chunked(
                start_date=start_date,
                end_date=end_date
            )
            console.print(f"   ✅ Fetched {len(all_conversations)} total conversations\n")
        
        # Filter by vendor
        console.print(f"🔍 Filtering for {vendor_name} conversations...")
        vendor_conversations = []
        
        # Vendor email patterns
        vendor_patterns = {
            'horatio': ['@hirehoratio.co', '@horatio.com'],
            'boldr': ['@boldrimpact.com', '@boldr']
        }
        
        patterns = vendor_patterns.get(vendor, [])
        
        for conv in all_conversations:
            # Extract admin emails
            admin_emails = []
            parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
            for part in parts:
                author = part.get('author', {})
                if author.get('type') == 'admin':
                    email = author.get('email', '')
                    if email:
                        admin_emails.append(email.lower())
            
            # Check for match
            if any(pattern in email for pattern in patterns for email in admin_emails):
                vendor_conversations.append(conv)
        
        console.print(f"   ✅ Found {len(vendor_conversations)} {vendor_name} conversations\n")
        
        if len(vendor_conversations) == 0:
            console.print(f"[yellow]⚠ No conversations found for {vendor_name}[/yellow]")
            return
        
        # Preprocess conversations
        console.print("🔧 Preprocessing conversations...")
        preprocessor = DataPreprocessor()
        vendor_conversations, preprocess_stats = preprocessor.preprocess_conversations(
            vendor_conversations,
            options={
                'deduplicate': True,
                'infer_missing': True,
                'clean_text': True,
                'detect_outliers': True
            }
        )
        console.print(f"   ✅ Preprocessed: {preprocess_stats['processed_count']} valid conversations\n")
        
        # Create agent context
        context = AgentContext(
            analysis_id=f"{vendor}_coaching_{datetime.now().strftime('%Y%m%d')}",
            analysis_type="coaching_report",
            start_date=start_date,
            end_date=end_date,
            conversations=vendor_conversations,
            metadata={'vendor': vendor, 'vendor_name': vendor_name}
        )
        
        # Run analysis with individual breakdown
        console.print(f"🤖 [bold cyan]Analyzing {vendor_name} Agent Performance...[/bold cyan]\n")
        performance_agent = AgentPerformanceAgent(agent_filter=vendor)
        result = await performance_agent.execute(context, individual_breakdown=True)
        
        if not result.success:
            console.print(f"[red]❌ Analysis failed: {result.error_message}[/red]")
            return
        
        # Display coaching report
        console.print("="*80)
        console.print(f"[bold green]🎉 {vendor_name} Coaching Report Complete![/bold green]")
        console.print("="*80 + "\n")
        
        _display_individual_breakdown(result.data, vendor_name)
        
        # Save detailed JSON
        output_dir = Path(settings.effective_output_directory)
        output_dir.mkdir(exist_ok=True, parents=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"coaching_report_{vendor}_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(result.data, f, indent=2, default=str)
        
        console.print(f"\n📁 Detailed report saved: {output_file}\n")
        
        # Generate Gamma if requested
        if generate_gamma:
            try:
                from src.services.gamma_generator import GammaGenerator
                from src.services.gamma_client import GammaAPIError
                
                console.print("🎨 [bold cyan]Generating Gamma presentation...[/bold cyan]")
                
                # Build markdown report
                markdown_report = _build_coaching_gamma_markdown(result.data, vendor_name, start_date, end_date, top_n)
                
                gamma_generator = GammaGenerator()
                gamma_result = await gamma_generator.generate_from_markdown(
                    input_text=markdown_report,
                    title=f"{vendor_name} Coaching Report - {start_date.strftime('%b %Y')}",
                    num_cards=min(10 + len(result.data.get('agents', [])), 25),
                    theme_name=None,
                    export_format=None,
                    output_dir=output_dir
                )
                
                gamma_url = gamma_result.get('gamma_url')
                if gamma_url:
                    console.print(f"\n🎨 [bold green]Gamma presentation generated![/bold green]")
                    console.print(f"📊 Gamma URL: {gamma_url}\n")
                    
            except GammaAPIError as e:
                console.print(f"[yellow]Warning: Gamma generation failed: {e}[/yellow]")
            except Exception as e:
                console.print(f"[yellow]Warning: Unexpected error during Gamma generation: {e}[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error in coaching report: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise


def _build_coaching_gamma_markdown(
    data: Dict, 
    vendor_name: str, 
    start_date: datetime, 
    end_date: datetime,
    top_n: int
) -> str:
    """Build markdown for Gamma coaching presentation"""
    team_metrics = data.get('team_metrics', {})
    agents = data.get('agents', [])
    
    markdown = f"""# {vendor_name} Coaching Report

## Analysis Period
{start_date.date()} to {end_date.date()}

---

## Team Performance Summary

**Total Agents**: {team_metrics.get('total_agents', 0)}
**Total Conversations**: {team_metrics.get('total_conversations', 0)}

**Team Metrics**:
- First Contact Resolution: {team_metrics.get('team_fcr_rate', 0):.1%}
- Escalation Rate: {team_metrics.get('team_escalation_rate', 0):.1%}

"""
    
    # Add team QA metrics if available
    if team_metrics.get('team_qa_overall') is not None:
        markdown += f"""**Quality Assurance Scores** (Team Average):
- Overall QA Score: {team_metrics.get('team_qa_overall', 0):.2f}/1.0
- Customer Connection: {team_metrics.get('team_qa_connection', 0):.2f}/1.0
- Communication Quality: {team_metrics.get('team_qa_communication', 0):.2f}/1.0
- Content Quality: {team_metrics.get('team_qa_content', 0):.2f}/1.0

_Based on {team_metrics.get('agents_with_qa_metrics', 0)} agents with sufficient message data_

"""
    
    markdown += """---

## Highlights & Achievements

"""
    
    # Add highlights
    for highlight in data.get('highlights', [])[:5]:
        markdown += f"✓ {highlight}\n\n"
    
    markdown += "---\n\n## Areas for Improvement\n\n"
    
    # Add lowlights
    for lowlight in data.get('lowlights', [])[:5]:
        markdown += f"• {lowlight}\n\n"
    
    markdown += "---\n\n"
    
    # Top performers
    top_performers = sorted(agents, key=lambda a: a.get('fcr_rate', 0), reverse=True)[:top_n]
    if top_performers:
        markdown += "## Top Performers\n\n"
        for agent in top_performers:
            markdown += f"### {agent.get('agent_name', 'Unknown')}\n\n"
            markdown += f"**Performance**: {agent.get('fcr_rate', 0):.1%} FCR (Rank #{agent.get('fcr_rank', '?')})\n\n"
            
            # Add QA metrics if available
            qa_metrics = agent.get('qa_metrics')
            if qa_metrics:
                markdown += f"**Quality Scores**: QA {qa_metrics.get('overall_qa_score', 0):.2f}/1.0 "
                markdown += f"(Greeting {qa_metrics.get('greeting_quality_score', 0):.2f}, "
                markdown += f"Communication {qa_metrics.get('communication_quality_score', 0):.2f})\n\n"
            
            for achievement in agent.get('praise_worthy_achievements', [])[:2]:
                markdown += f"✓ {achievement}\n\n"
            
            markdown += "---\n\n"
    
    # Agents needing coaching
    coaching_needed = data.get('agents_needing_coaching', [])[:top_n]
    if coaching_needed:
        markdown += "## Coaching Priorities\n\n"
        for agent in coaching_needed:
            markdown += f"### {agent.get('agent_name', 'Unknown')}\n\n"
            markdown += f"**Current Performance**: {agent.get('fcr_rate', 0):.1%} FCR\n\n"
            
            # Add QA metrics if available
            qa_metrics = agent.get('qa_metrics')
            if qa_metrics:
                markdown += f"**Quality Scores**: QA {qa_metrics.get('overall_qa_score', 0):.2f}/1.0 "
                markdown += f"(Greeting {qa_metrics.get('greeting_quality_score', 0):.2f}, "
                markdown += f"Communication {qa_metrics.get('communication_quality_score', 0):.2f})\n\n"
                
                # Add specific QA-based coaching points
                qa_coaching = []
                if qa_metrics.get('greeting_quality_score', 1.0) < 0.6:
                    qa_coaching.append("Improve greeting quality: consistently greet customers and use their names")
                if qa_metrics.get('avg_grammar_errors_per_message', 0) > 1.0:
                    qa_coaching.append(f"Reduce grammar errors (currently {qa_metrics.get('avg_grammar_errors_per_message', 0):.1f} per message)")
                if qa_metrics.get('proper_formatting_rate', 1.0) < 0.7:
                    qa_coaching.append("Improve message formatting: use proper paragraph breaks")
                
                if qa_coaching:
                    markdown += f"**Communication Quality Coaching**:\n"
                    for coaching_point in qa_coaching:
                        markdown += f"- {coaching_point}\n"
                    markdown += "\n"
            
            markdown += f"**Performance Focus Areas**:\n"
            
            for area in agent.get('coaching_focus_areas', [])[:3]:
                markdown += f"- {area}\n"
            
            markdown += "\n---\n\n"
    
    # Team training needs
    training_needs = data.get('team_training_needs', [])
    if training_needs:
        markdown += "## Team-Wide Training Needs\n\n"
        for need in training_needs[:5]:
            markdown += f"### {need.get('topic', 'Unknown')}\n\n"
            markdown += f"**Priority**: {need.get('priority', 'medium').upper()}\n\n"
            markdown += f"{need.get('reason', '')}\n\n"
            markdown += f"**Affected Agents**: {', '.join(need.get('affected_agents', [])[:5])}\n\n"
            markdown += "---\n\n"
    
    return markdown


async def run_category_analysis(category: str, start_date: datetime, end_date: datetime, output_format: str):
    """Run single category analysis."""
    try:
        # Initialize services
        pipeline = ELTPipeline()
        
        console.print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Extract and load data
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Extracting and loading data...", total=None)
            
            stats = await pipeline.extract_and_load(start_date, end_date)
            
            progress.update(task, description=f"✅ Loaded {stats['conversations_count']} conversations")
        
        if stats['conversations_count'] == 0:
            console.print("[yellow]No conversations found for the specified date range.[/yellow]")
            return
        
        # Get all conversations and filter by category using CategoryFilters
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Analyzing {category} category...", total=None)
            
            # Get all conversations from the date range
            all_conversations = await pipeline.intercom_service.fetch_conversations_by_date_range(
                start_date, end_date
            )
            
            # Use CategoryFilters to filter by category
            from src.services.category_filters import CategoryFilters
            category_filters = CategoryFilters()
            filtered_conversations = category_filters.filter_by_category(
                all_conversations, category, include_subcategories=True
            )
            
            progress.update(task, description=f"✅ {category} analysis completed")
        
        # Export results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(settings.effective_output_directory)
        output_dir.mkdir(exist_ok=True, parents=True)
        
        if output_format == "csv":
            csv_path = output_dir / f"{category}_analysis_{timestamp}.csv"
            import pandas as pd
            df = pd.DataFrame(filtered_conversations)
            df.to_csv(csv_path, index=False)
        elif output_format == "json":
            json_path = output_dir / f"{category}_analysis_{timestamp}.json"
            import json
            with open(json_path, 'w') as f:
                json.dump(filtered_conversations, f, indent=2, default=str)
            csv_path = json_path
        else:
            # Default to CSV
            csv_path = output_dir / f"{category}_analysis_{timestamp}.csv"
            import pandas as pd
            df = pd.DataFrame(filtered_conversations)
            df.to_csv(csv_path, index=False)
        
        console.print(f"\n[bold green]{category.title()} Analysis Completed![/bold green]")
        console.print(f"Total conversations analyzed: {stats['conversations_count']:,}")
        console.print(f"Category matches: {len(filtered_conversations):,}")
        console.print(f"Export: {csv_path}")
        
    except Exception as e:
        console.print(f"[red]Error in category analysis: {e}[/red]")
        raise


async def run_all_categories_analysis(start_date: datetime, end_date: datetime, parallel: bool):
    """Run all categories analysis."""
    console.print(f"[yellow]All categories analysis not yet implemented[/yellow]")
    console.print(f"Would analyze all 13 categories from {start_date.date()} to {end_date.date()}")


async def run_synthesis_analysis(categories: str, pattern: Optional[str], start_date: datetime, end_date: datetime):
    """Run synthesis analysis."""
    console.print(f"[yellow]Synthesis analysis not yet implemented[/yellow]")
    console.print(f"Would synthesize {categories} from {start_date.date()} to {end_date.date()}")


async def run_custom_tag_analysis(tag: str, agent: Optional[str], start_date: datetime, end_date: datetime):
    """Run custom tag analysis."""
    console.print(f"[yellow]Custom tag analysis not yet implemented[/yellow]")
    console.print(f"Would analyze {tag} tag from {start_date.date()} to {end_date.date()}")


async def run_escalation_analysis(to: Optional[str], from_agent: Optional[str], start_date: datetime, end_date: datetime):
    """Run escalation analysis."""
    console.print(f"[yellow]Escalation analysis not yet implemented[/yellow]")
    console.print(f"Would analyze escalations from {start_date.date()} to {end_date.date()}")


async def run_pattern_analysis(pattern: str, start_date: datetime, end_date: datetime, case_sensitive: bool):
    """Run pattern analysis."""
    console.print(f"[yellow]Pattern analysis not yet implemented[/yellow]")
    console.print(f"Would search for '{pattern}' from {start_date.date()} to {end_date.date()}")


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
    
    asyncio.run(run_billing_analysis(start_dt, end_dt, generate_gamma, max_conversations))


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
    
    asyncio.run(run_product_analysis(start_dt, end_dt, generate_gamma, max_conversations))


@cli.command(name='analyze-sites')
@click.option('--days', type=int, default=30, help='Number of days to analyze')
@click.option('--start-date', type=click.DateTime(formats=['%Y-%m-%d']), help='Start date (YYYY-MM-DD)')
@click.option('--end-date', type=click.DateTime(formats=['%Y-%m-%d']), help='End date (YYYY-MM-DD)')
@click.option('--generate-gamma', is_flag=True, help='Generate Gamma presentation')
@click.option('--max-conversations', type=int, help='Maximum conversations to analyze')
@click.option('--verbose', is_flag=True, default=False, help='Enable verbose DEBUG logging')
@click.option('--audit-trail', is_flag=True, default=False, help='Enable audit trail logging')
@click.option('--ai-model', type=click.Choice(['openai', 'claude']), default=None,
              help='AI model to use for analysis (overrides config setting)')
def analyze_sites(days: int, start_date: Optional[datetime], end_date: Optional[datetime], 
                 generate_gamma: bool, max_conversations: Optional[int], verbose: bool = False, audit_trail: bool = False, ai_model: Optional[str] = None):
    """Analyze sites conversations (domain, publishing, education)."""
    if verbose:
        setup_verbose_logging()
    if audit_trail:
        show_audit_trail_enabled()
    
    if not start_date:
        start_date = datetime.now() - timedelta(days=days)
    if not end_date:
        end_date = datetime.now()
    
    asyncio.run(run_sites_analysis(start_date, end_date, generate_gamma, max_conversations))


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
    
    asyncio.run(run_api_analysis(start_dt, end_dt, generate_gamma, max_conversations))


@cli.command(name='analyze-all-categories')
@click.option('--days', type=int, default=30, help='Number of days to analyze')
@click.option('--start-date', type=click.DateTime(formats=['%Y-%m-%d']), help='Start date (YYYY-MM-DD)')
@click.option('--end-date', type=click.DateTime(formats=['%Y-%m-%d']), help='End date (YYYY-MM-DD)')
@click.option('--generate-gamma', is_flag=True, help='Generate Gamma presentations')
@click.option('--parallel', is_flag=True, help='Run analyses in parallel')
@click.option('--max-conversations', type=int, help='Maximum conversations per category')
@click.option('--verbose', is_flag=True, default=False, help='Enable verbose DEBUG logging')
@click.option('--audit-trail', is_flag=True, default=False, help='Enable audit trail logging')
@click.option('--ai-model', type=click.Choice(['openai', 'claude']), default=None,
              help='AI model to use for analysis (overrides config setting)')
def analyze_all_categories(days: int, start_date: Optional[datetime], end_date: Optional[datetime], 
                          generate_gamma: bool, parallel: bool, max_conversations: Optional[int], verbose: bool = False, audit_trail: bool = False, ai_model: Optional[str] = None):
    """Analyze all 4 main categories (Billing, Product, Sites, API)."""
    if verbose:
        setup_verbose_logging()
    if audit_trail:
        show_audit_trail_enabled()
    
    if not start_date:
        start_date = datetime.now() - timedelta(days=days)
    if not end_date:
        end_date = datetime.now()
    
    asyncio.run(run_all_categories_analysis_v2(start_date, end_date, generate_gamma, parallel, max_conversations))


# Analysis Implementation Functions
async def run_billing_analysis(start_date: datetime, end_date: datetime, generate_gamma: bool, max_conversations: Optional[int]):
    """Run billing analysis with new infrastructure."""
    try:
        console.print(f"[bold blue]Billing Analysis[/bold blue]")
        console.print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Initialize services
        chunked_fetcher = ChunkedFetcher()
        data_preprocessor = DataPreprocessor()
        category_filters = CategoryFilters()
        billing_analyzer = BillingAnalyzer()
        gamma_generator = GammaGenerator() if generate_gamma else None
        
        # Fetch conversations
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Fetching conversations...", total=None)
            
            conversations = await chunked_fetcher.fetch_conversations_chunked(
                start_date, end_date, max_pages=None
            )
            
            progress.update(task, description=f"✅ Fetched {len(conversations)} conversations")
        
        if not conversations:
            console.print("[yellow]No conversations found for the specified date range.[/yellow]")
            return
        
        # Preprocess data
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Preprocessing data...", total=None)
            
            processed_conversations, preprocessing_stats = data_preprocessor.preprocess_conversations(
                conversations, {'max_conversations': max_conversations}
            )
            
            progress.update(task, description=f"✅ Preprocessed {len(processed_conversations)} conversations")
        
        # Analyze billing conversations
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Analyzing billing patterns...", total=None)
            
            analysis_results = await billing_analyzer.analyze_category(
                processed_conversations, start_date, end_date, {'generate_ai_insights': True}
            )
            
            progress.update(task, description="✅ Billing analysis completed")
        
        # Export results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(settings.effective_output_directory)
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Save analysis results
        results_file = output_dir / f"billing_analysis_{timestamp}.json"
        with open(results_file, 'w') as f:
            import json
            json.dump(analysis_results, f, indent=2, default=str)
        
        console.print(f"\n[bold green]Billing Analysis Completed![/bold green]")
        console.print(f"Total conversations analyzed: {analysis_results['data_summary']['filtered_conversations']:,}")
        console.print(f"Results saved to: {results_file}")
        
        # Generate Gamma presentation if requested
        if generate_gamma and gamma_generator:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Generating Gamma presentation...", total=None)
                
                gamma_result = await gamma_generator.generate_from_analysis(
                    analysis_results=analysis_results,
                    style="executive",
                    output_dir=output_dir
                )
                
                progress.update(task, description="✅ Gamma presentation generated")
            
            # Print in consistent format for web UI parsing
            console.print(f"Gamma URL: {gamma_result['gamma_url']}")
            console.print(f"Credits used: {gamma_result['credits_used']}")
            console.print(f"Generation time: {gamma_result['generation_time_seconds']:.1f}s")
            if gamma_result.get('markdown_summary_path'):
                console.print(f"Markdown summary: {gamma_result['markdown_summary_path']}")
            
            # Save Gamma metadata
            metadata_file = output_dir / f"billing_gamma_metadata_{timestamp}.json"
            with open(metadata_file, 'w') as f:
                import json
                json.dump(gamma_result, f, indent=2, default=str)
            console.print(f"Gamma metadata saved to: {metadata_file}")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def run_product_analysis(start_date: datetime, end_date: datetime, generate_gamma: bool, max_conversations: Optional[int]):
    """Run product analysis with new infrastructure."""
    try:
        console.print(f"[bold blue]Product Analysis[/bold blue]")
        console.print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Initialize services
        chunked_fetcher = ChunkedFetcher()
        data_preprocessor = DataPreprocessor()
        category_filters = CategoryFilters()
        product_analyzer = ProductAnalyzer()
        gamma_generator = GammaGenerator() if generate_gamma else None
        
        # Fetch conversations
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Fetching conversations...", total=None)
            
            conversations = await chunked_fetcher.fetch_conversations_chunked(
                start_date, end_date, max_pages=None
            )
            
            progress.update(task, description=f"✅ Fetched {len(conversations)} conversations")
        
        if not conversations:
            console.print("[yellow]No conversations found for the specified date range.[/yellow]")
            return
        
        # Preprocess data
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Preprocessing data...", total=None)
            
            processed_conversations, preprocessing_stats = data_preprocessor.preprocess_conversations(
                conversations, {'max_conversations': max_conversations}
            )
            
            progress.update(task, description=f"✅ Preprocessed {len(processed_conversations)} conversations")
        
        # Analyze product conversations
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Analyzing product patterns...", total=None)
            
            analysis_results = await product_analyzer.analyze_category(
                processed_conversations, start_date, end_date, {'generate_ai_insights': True}
            )
            
            progress.update(task, description="✅ Product analysis completed")
        
        # Export results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(settings.effective_output_directory)
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Save analysis results
        results_file = output_dir / f"product_analysis_{timestamp}.json"
        with open(results_file, 'w') as f:
            import json
            json.dump(analysis_results, f, indent=2, default=str)
        
        console.print(f"\n[bold green]Product Analysis Completed![/bold green]")
        console.print(f"Total conversations analyzed: {analysis_results['data_summary']['filtered_conversations']:,}")
        console.print(f"Results saved to: {results_file}")
        
        # Generate Gamma presentation if requested
        if generate_gamma and gamma_generator:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Generating Gamma presentation...", total=None)
                
                gamma_result = await gamma_generator.generate_from_analysis(
                    analysis_results=analysis_results,
                    style="executive",
                    output_dir=output_dir
                )
                
                progress.update(task, description="✅ Gamma presentation generated")
            
            # Print in consistent format for web UI parsing
            console.print(f"Gamma URL: {gamma_result['gamma_url']}")
            console.print(f"Credits used: {gamma_result['credits_used']}")
            console.print(f"Generation time: {gamma_result['generation_time_seconds']:.1f}s")
            if gamma_result.get('markdown_summary_path'):
                console.print(f"Markdown summary: {gamma_result['markdown_summary_path']}")
            
            # Save Gamma metadata
            metadata_file = output_dir / f"product_gamma_metadata_{timestamp}.json"
            with open(metadata_file, 'w') as f:
                import json
                json.dump(gamma_result, f, indent=2, default=str)
            console.print(f"Gamma metadata saved to: {metadata_file}")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def run_sites_analysis(start_date: datetime, end_date: datetime, generate_gamma: bool, max_conversations: Optional[int]):
    """Run sites analysis with new infrastructure."""
    try:
        console.print(f"[bold blue]Sites Analysis[/bold blue]")
        console.print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Initialize services
        chunked_fetcher = ChunkedFetcher()
        data_preprocessor = DataPreprocessor()
        category_filters = CategoryFilters()
        sites_analyzer = SitesAnalyzer()
        gamma_generator = GammaGenerator() if generate_gamma else None
        
        # Fetch conversations
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Fetching conversations...", total=None)
            
            conversations = await chunked_fetcher.fetch_conversations_chunked(
                start_date, end_date, max_pages=None
            )
            
            progress.update(task, description=f"✅ Fetched {len(conversations)} conversations")
        
        if not conversations:
            console.print("[yellow]No conversations found for the specified date range.[/yellow]")
            return
        
        # Preprocess data
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Preprocessing data...", total=None)
            
            processed_conversations, preprocessing_stats = data_preprocessor.preprocess_conversations(
                conversations, {'max_conversations': max_conversations}
            )
            
            progress.update(task, description=f"✅ Preprocessed {len(processed_conversations)} conversations")
        
        # Analyze sites conversations
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Analyzing sites patterns...", total=None)
            
            analysis_results = await sites_analyzer.analyze_category(
                processed_conversations, start_date, end_date, {'generate_ai_insights': True}
            )
            
            progress.update(task, description="✅ Sites analysis completed")
        
        # Export results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(settings.effective_output_directory)
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Save analysis results
        results_file = output_dir / f"sites_analysis_{timestamp}.json"
        with open(results_file, 'w') as f:
            import json
            json.dump(analysis_results, f, indent=2, default=str)
        
        console.print(f"\n[bold green]Sites Analysis Completed![/bold green]")
        console.print(f"Total conversations analyzed: {analysis_results['data_summary']['filtered_conversations']:,}")
        console.print(f"Results saved to: {results_file}")
        
        # Generate Gamma presentation if requested
        if generate_gamma and gamma_generator:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Generating Gamma presentation...", total=None)
                
                gamma_result = await gamma_generator.generate_from_analysis(
                    analysis_results=analysis_results,
                    style="executive",
                    output_dir=output_dir
                )
                
                progress.update(task, description="✅ Gamma presentation generated")
            
            # Print in consistent format for web UI parsing
            console.print(f"Gamma URL: {gamma_result['gamma_url']}")
            console.print(f"Credits used: {gamma_result['credits_used']}")
            console.print(f"Generation time: {gamma_result['generation_time_seconds']:.1f}s")
            if gamma_result.get('markdown_summary_path'):
                console.print(f"Markdown summary: {gamma_result['markdown_summary_path']}")
            
            # Save Gamma metadata
            metadata_file = output_dir / f"sites_gamma_metadata_{timestamp}.json"
            with open(metadata_file, 'w') as f:
                import json
                json.dump(gamma_result, f, indent=2, default=str)
            console.print(f"Gamma metadata saved to: {metadata_file}")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def run_api_analysis(start_date: datetime, end_date: datetime, generate_gamma: bool, max_conversations: Optional[int]):
    """Run API analysis with new infrastructure."""
    try:
        console.print(f"[bold blue]API Analysis[/bold blue]")
        console.print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Initialize services
        chunked_fetcher = ChunkedFetcher()
        data_preprocessor = DataPreprocessor()
        category_filters = CategoryFilters()
        api_analyzer = ApiAnalyzer()
        gamma_generator = GammaGenerator() if generate_gamma else None
        
        # Fetch conversations
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Fetching conversations...", total=None)
            
            conversations = await chunked_fetcher.fetch_conversations_chunked(
                start_date, end_date, max_pages=None
            )
            
            progress.update(task, description=f"✅ Fetched {len(conversations)} conversations")
        
        if not conversations:
            console.print("[yellow]No conversations found for the specified date range.[/yellow]")
            return
        
        # Preprocess data
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Preprocessing data...", total=None)
            
            processed_conversations, preprocessing_stats = data_preprocessor.preprocess_conversations(
                conversations, {'max_conversations': max_conversations}
            )
            
            progress.update(task, description=f"✅ Preprocessed {len(processed_conversations)} conversations")
        
        # Analyze API conversations
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Analyzing API patterns...", total=None)
            
            analysis_results = await api_analyzer.analyze_category(
                processed_conversations, start_date, end_date, {'generate_ai_insights': True}
            )
            
            progress.update(task, description="✅ API analysis completed")
        
        # Export results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(settings.effective_output_directory)
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Save analysis results
        results_file = output_dir / f"api_analysis_{timestamp}.json"
        with open(results_file, 'w') as f:
            import json
            json.dump(analysis_results, f, indent=2, default=str)
        
        console.print(f"\n[bold green]API Analysis Completed![/bold green]")
        console.print(f"Total conversations analyzed: {analysis_results['data_summary']['filtered_conversations']:,}")
        console.print(f"Results saved to: {results_file}")
        
        # Generate Gamma presentation if requested
        if generate_gamma and gamma_generator:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Generating Gamma presentation...", total=None)
                
                gamma_result = await gamma_generator.generate_from_analysis(
                    analysis_results=analysis_results,
                    style="executive",
                    output_dir=output_dir
                )
                
                progress.update(task, description="✅ Gamma presentation generated")
            
            # Print in consistent format for web UI parsing
            console.print(f"Gamma URL: {gamma_result['gamma_url']}")
            console.print(f"Credits used: {gamma_result['credits_used']}")
            console.print(f"Generation time: {gamma_result['generation_time_seconds']:.1f}s")
            if gamma_result.get('markdown_summary_path'):
                console.print(f"Markdown summary: {gamma_result['markdown_summary_path']}")
            
            # Save Gamma metadata
            metadata_file = output_dir / f"api_gamma_metadata_{timestamp}.json"
            with open(metadata_file, 'w') as f:
                import json
                json.dump(gamma_result, f, indent=2, default=str)
            console.print(f"Gamma metadata saved to: {metadata_file}")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def run_all_categories_analysis_v2(start_date: datetime, end_date: datetime, generate_gamma: bool, parallel: bool, max_conversations: Optional[int]):
    """Run all categories analysis with new infrastructure."""
    try:
        console.print(f"[bold blue]All Categories Analysis[/bold blue]")
        console.print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        console.print(f"Categories: Billing, Product, Sites, API")
        
        # Initialize services
        chunked_fetcher = ChunkedFetcher()
        data_preprocessor = DataPreprocessor()
        category_filters = CategoryFilters()
        gamma_generator = GammaGenerator() if generate_gamma else None
        
        # Fetch conversations once
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Fetching conversations...", total=None)
            
            conversations = await chunked_fetcher.fetch_conversations_chunked(
                start_date, end_date, max_pages=None
            )
            
            progress.update(task, description=f"✅ Fetched {len(conversations)} conversations")
        
        if not conversations:
            console.print("[yellow]No conversations found for the specified date range.[/yellow]")
            return
        
        # Preprocess data once
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Preprocessing data...", total=None)
            
            processed_conversations, preprocessing_stats = data_preprocessor.preprocess_conversations(
                conversations, {'max_conversations': max_conversations}
            )
            
            progress.update(task, description=f"✅ Preprocessed {len(processed_conversations)} conversations")
        
        # Initialize analyzers
        analyzers = {
            'Billing': BillingAnalyzer(),
            'Product': ProductAnalyzer(),
            'Sites': SitesAnalyzer(),
            'API': ApiAnalyzer()
        }
        
        # Run analyses
        analysis_results = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(settings.effective_output_directory)
        output_dir.mkdir(exist_ok=True, parents=True)
        
        if parallel:
            # Run analyses in parallel
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Running parallel analyses...", total=len(analyzers))
                
                async def analyze_category(category_name, analyzer):
                    result = await analyzer.analyze_category(
                        processed_conversations, start_date, end_date, {'generate_ai_insights': True}
                    )
                    return category_name, result
                
                # Create tasks for parallel execution
                tasks = [analyze_category(category, analyzer) for category, analyzer in analyzers.items()]
                results = await asyncio.gather(*tasks)
                
                for category_name, result in results:
                    analysis_results[category_name] = result
                    progress.advance(task)
        else:
            # Run analyses sequentially
            for category_name, analyzer in analyzers.items():
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task(f"Analyzing {category_name}...", total=None)
                    
                    result = await analyzer.analyze_category(
                        processed_conversations, start_date, end_date, {'generate_ai_insights': True}
                    )
                    analysis_results[category_name] = result
                    
                    progress.update(task, description=f"✅ {category_name} analysis completed")
        
        # Save individual results
        for category_name, result in analysis_results.items():
            results_file = output_dir / f"{category_name.lower()}_analysis_{timestamp}.json"
            with open(results_file, 'w') as f:
                import json
                json.dump(result, f, indent=2, default=str)
        
        console.print(f"\n[bold green]All Categories Analysis Completed![/bold green]")
        for category_name, result in analysis_results.items():
            console.print(f"{category_name}: {result['data_summary']['filtered_conversations']:,} conversations")
        
        # Generate comprehensive Gamma presentation if requested
        if generate_gamma and gamma_generator:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Generating comprehensive Gamma presentation...", total=None)
                
                # Convert to list format for multi-category presentation
                results_list = list(analysis_results.values())
                presentation_results = await gamma_generator.generate_multi_category_presentation(
                    results_list, output_dir
                )
                
                progress.update(task, description="✅ Comprehensive Gamma presentation generated")
            
            console.print(f"Comprehensive Gamma presentation saved to: {output_dir}")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


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
    """Run comprehensive analysis across all categories and components."""
    from src.utils.time_utils import calculate_date_range
    from src.config.test_data import parse_test_data_count, get_preset_display_name
    
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
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return
    
    try:
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        console.print(f"[bold blue]Starting Comprehensive Analysis[/bold blue]")
        console.print(f"Date range: {start_date} to {end_date}")
        console.print(f"Max conversations: {max_conversations}")
        console.print(f"Output directory: {output_dir}")
        
        # Initialize orchestrator
        orchestrator = AnalysisOrchestrator()
        
        # Set up options
        options = {
            'max_conversations': max_conversations,
            'generate_gamma_presentation': generate_gamma,
            'gamma_style': gamma_style,
            'gamma_export': gamma_export,
            'export_docs': export_docs,
            'include_fin_analysis': include_fin_analysis,
            'include_technical_analysis': include_technical_analysis,
            'include_macro_analysis': include_macro_analysis,
            'generate_ai_insights': True
        }
        
        # Run comprehensive analysis
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Running comprehensive analysis...", total=None)
            
            results = asyncio.run(orchestrator.run_comprehensive_analysis(
                start_dt, end_dt, options
            ))
            
            progress.update(task, description="✅ Comprehensive analysis completed")
        
        # Save results
        results_file = output_path / f"comprehensive_analysis_{timestamp}.json"
        with open(results_file, 'w') as f:
            import json
            json.dump(results, f, indent=2, default=str)
        
        # Display summary
        console.print(f"\n[bold green]Comprehensive Analysis Completed![/bold green]")
        
        if 'error' in results:
            console.print(f"[red]Error: {results['error']}[/red]")
            return
        
        # Display key metrics
        metadata = results.get('analysis_metadata', {})
        console.print(f"Total conversations analyzed: {metadata.get('total_conversations', 0):,}")
        
        # Display category results
        category_results = results.get('category_results', {})
        console.print(f"\n[bold]Category Analysis Results:[/bold]")
        for category, result in category_results.items():
            if 'error' not in result:
                filtered_count = result.get('data_summary', {}).get('filtered_conversations', 0)
                console.print(f"  {category.title()}: {filtered_count:,} conversations")
            else:
                console.print(f"  {category.title()}: Error - {result['error']}")
        
        # Display specialized results
        specialized_results = results.get('specialized_results', {})
        console.print(f"\n[bold]Specialized Analysis Results:[/bold]")
        for analysis_type, result in specialized_results.items():
            if 'error' not in result:
                if analysis_type == 'fin_escalations':
                    escalation_rate = result.get('escalation_analysis', {}).get('escalation_rate', 0)
                    console.print(f"  Fin Escalations: {escalation_rate:.1f}% escalation rate")
                elif analysis_type == 'technical_patterns':
                    pattern_count = len(result.get('technical_patterns', []))
                    console.print(f"  Technical Patterns: {pattern_count} patterns detected")
                elif analysis_type == 'macro_opportunities':
                    opportunity_count = len(result.get('macro_opportunities', []))
                    console.print(f"  Macro Opportunities: {opportunity_count} opportunities found")
            else:
                console.print(f"  {analysis_type.title()}: Error - {result['error']}")
        
        # Display synthesis results
        synthesis_results = results.get('synthesis_results', {})
        if synthesis_results:
            console.print(f"\n[bold]Cross-Category Insights:[/bold]")
            executive_summary = synthesis_results.get('executive_summary', {})
            key_findings = executive_summary.get('overview', {}).get('key_findings', [])
            for finding in key_findings[:3]:  # Show top 3 findings
                console.print(f"  • {finding}")
        
        # Display Gamma presentation info
        if generate_gamma and results.get('gamma_presentation'):
            console.print(f"\n[bold green]Gamma presentation generated![/bold green]")
            console.print(f"Results saved to: {output_path}")
        
        console.print(f"\nDetailed results saved to: {results_file}")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command(name='generate-gamma')
@click.option('--analysis-file', required=True, type=click.Path(exists=True), help='Path to analysis JSON file')
@click.option('--style', default='executive', type=click.Choice(['executive', 'detailed', 'training']), help='Presentation style')
@click.option('--export-pdf', is_flag=True, help='Also export as PDF')
@click.option('--export-pptx', is_flag=True, help='Also export as PPTX')
@click.option('--export-docs', is_flag=True, help='Generate markdown for Google Docs')
@click.option('--output-dir', default='outputs', help='Output directory for results')
def generate_gamma(analysis_file, style, export_pdf, export_pptx, export_docs, output_dir):
    """Generate Gamma presentation from existing analysis JSON file."""
    try:
        import json
        from src.services.gamma_generator import GammaGenerator
        from src.services.google_docs_exporter import GoogleDocsExporter
        from pathlib import Path
        
        # Load analysis results
        with open(analysis_file, 'r') as f:
            analysis_results = json.load(f)
        
        console.print(f"[bold blue]Generating Gamma Presentation[/bold blue]")
        console.print(f"Style: {style}")
        console.print(f"Analysis file: {analysis_file}")
        console.print(f"Output directory: {output_dir}")
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Initialize services
        gamma_generator = GammaGenerator()
        docs_exporter = GoogleDocsExporter()
        
        # Determine export format
        export_format = None
        if export_pdf:
            export_format = "pdf"
        elif export_pptx:
            export_format = "pptx"
        
        # Generate Gamma presentation
        console.print(f"[yellow]Generating {style} presentation...[/yellow]")
        result = asyncio.run(gamma_generator.generate_from_analysis(
            analysis_results=analysis_results,
            style=style,
            export_format=export_format,
            output_dir=output_path
        ))
        
        # Display results
        console.print(f"[green]✅ Gamma presentation generated successfully![/green]")
        console.print(f"Gamma URL: {result['gamma_url']}")
        console.print(f"Generation ID: {result['generation_id']}")
        console.print(f"Credits used: {result['credits_used']}")
        console.print(f"Generation time: {result['generation_time_seconds']:.1f} seconds")
        
        if result.get('export_url'):
            console.print(f"Export URL: {result['export_url']}")
        
        # Generate Google Docs export if requested
        if export_docs:
            console.print(f"[yellow]Generating Google Docs markdown...[/yellow]")
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            docs_filename = f"analysis_{style}_{timestamp}.md"
            docs_path = output_path / docs_filename
            
            docs_exporter.export_to_markdown(
                analysis_results=analysis_results,
                output_path=docs_path,
                style=style
            )
            
            console.print(f"[green]✅ Google Docs markdown generated![/green]")
            console.print(f"Markdown file: {docs_path}")
        
    except Exception as e:
        console.print(f"[red]Error generating Gamma presentation: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command(name='generate-all-gamma')
@click.option('--analysis-file', required=True, type=click.Path(exists=True), help='Path to analysis JSON file')
@click.option('--export-pdf', is_flag=True, help='Also export as PDF')
@click.option('--export-pptx', is_flag=True, help='Also export as PPTX')
@click.option('--export-docs', is_flag=True, help='Generate markdown for Google Docs')
@click.option('--output-dir', default='outputs', help='Output directory for results')
def generate_all_gamma(analysis_file, export_pdf, export_pptx, export_docs, output_dir):
    """Generate all Gamma presentation styles from existing analysis JSON file."""
    try:
        import json
        from src.services.gamma_generator import GammaGenerator
        from src.services.google_docs_exporter import GoogleDocsExporter
        from pathlib import Path
        
        # Load analysis results
        with open(analysis_file, 'r') as f:
            analysis_results = json.load(f)
        
        console.print(f"[bold blue]Generating All Gamma Presentations[/bold blue]")
        console.print(f"Analysis file: {analysis_file}")
        console.print(f"Output directory: {output_dir}")
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Initialize services
        gamma_generator = GammaGenerator()
        docs_exporter = GoogleDocsExporter()
        
        # Determine export format
        export_format = None
        if export_pdf:
            export_format = "pdf"
        elif export_pptx:
            export_format = "pptx"
        
        # Generate all presentation styles
        console.print(f"[yellow]Generating all presentation styles...[/yellow]")
        results = asyncio.run(gamma_generator.generate_all_styles(
            analysis_results=analysis_results,
            export_format=export_format,
            output_dir=output_path
        ))
        
        # Display results
        console.print(f"[green]✅ All Gamma presentations generated![/green]")
        
        for style, result in results.items():
            if result.get('gamma_url'):
                console.print(f"\n[bold]{style.title()} Presentation:[/bold]")
                console.print(f"  Gamma URL: {result['gamma_url']}")
                console.print(f"  Credits used: {result['credits_used']}")
                console.print(f"  Generation time: {result['generation_time_seconds']:.1f} seconds")
                
                if result.get('export_url'):
                    console.print(f"  Export URL: {result['export_url']}")
            else:
                console.print(f"\n[red]{style.title()} Presentation: Failed - {result.get('error', 'Unknown error')}[/red]")
        
        # Generate Google Docs exports if requested
        if export_docs:
            console.print(f"\n[yellow]Generating Google Docs markdown files...[/yellow]")
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            for style in ['executive', 'detailed', 'training']:
                docs_filename = f"analysis_{style}_{timestamp}.md"
                docs_path = output_path / docs_filename
                
                docs_exporter.export_to_markdown(
                    analysis_results=analysis_results,
                    output_path=docs_path,
                    style=style
                )
                
                console.print(f"[green]✅ {style.title()} markdown: {docs_path}[/green]")
        
        # Show summary
        stats = gamma_generator.get_generation_statistics(results)
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Total generations: {stats['total_generations']}")
        console.print(f"  Successful: {stats['successful_generations']}")
        console.print(f"  Failed: {stats['failed_generations']}")
        console.print(f"  Total credits used: {stats['total_credits_used']}")
        console.print(f"  Total time: {stats['total_time_seconds']:.1f} seconds")
        
    except Exception as e:
        console.print(f"[red]Error generating Gamma presentations: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


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


async def run_canny_analysis(
    start_date: str,
    end_date: str,
    board_id: Optional[str],
    ai_model: str,
    enable_fallback: bool,
    include_comments: bool,
    include_votes: bool,
    generate_gamma: bool,
    output_dir: str
):
    """Run Canny product feedback analysis."""
    from src.utils.time_utils import detect_period_type
    from src.services.ai_model_factory import AIModelFactory
    from src.services.canny_client import CannyClient
    from src.analyzers.canny_analyzer import CannyAnalyzer
    
    try:
        console.print(f"[bold blue]Starting Canny Analysis[/bold blue]")
        console.print(f"Date Range: {start_date} to {end_date}")
        console.print(f"AI Model: {ai_model}")
        console.print(f"Board ID: {board_id or 'All boards'}")
        
        # Initialize components
        ai_factory = AIModelFactory()
        canny_client = CannyClient()
        canny_analyzer = CannyAnalyzer(ai_factory)
        
        # Test Canny connection
        console.print(f"[yellow]Testing Canny API connection...[/yellow]")
        await canny_client.test_connection()
        console.print(f"[green]✅ Canny API connection successful[/green]")
        
        # Parse dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Detect period type from date range
        period_type, period_label = detect_period_type(start_dt, end_dt)
        
        # Fetch Canny data
        console.print(f"[yellow]Fetching Canny posts...[/yellow]")
        if board_id:
            posts = await canny_client.fetch_posts_by_date_range(
                start_date=start_dt,
                end_date=end_dt,
                board_id=board_id,
                include_comments=include_comments,
                include_votes=include_votes
            )
        else:
            # Fetch from all boards
            all_boards_posts = await canny_client.fetch_all_boards_posts(
                start_date=start_dt,
                end_date=end_dt,
                include_comments=include_comments,
                include_votes=include_votes
            )
            # Flatten posts from all boards
            posts = []
            for board_posts in all_boards_posts.values():
                posts.extend(board_posts)
        
        if not posts:
            console.print("[red]No Canny posts found for the specified date range.[/red]")
            return
        
        console.print(f"[green]Found {len(posts)} Canny posts[/green]")
        
        # Run sentiment analysis
        console.print(f"[yellow]Running sentiment analysis...[/yellow]")
        
        ai_model_enum = AIModel.ANTHROPIC_CLAUDE if ai_model == 'claude' else AIModel.OPENAI_GPT4
        
        analysis_results = await canny_analyzer.analyze_canny_sentiment(
            posts=posts,
            ai_model=ai_model_enum,
            enable_fallback=enable_fallback
        )
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        from src.utils.time_utils import generate_descriptive_filename
        
        output_filename = generate_descriptive_filename(
            'Canny_Analysis', start_date, end_date, file_type='json'
        )
        output_file = Path(output_dir) / output_filename
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            import json
            json.dump({
                'analysis_results': analysis_results,
                'metadata': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'period_type': period_type,
                    'period_label': period_label,
                    'board_id': board_id,
                    'ai_model': ai_model,
                    'total_posts': len(posts),
                    'generated_at': datetime.now().isoformat()
                }
            }, f, indent=2)
        
        console.print(f"[green]Canny analysis completed![/green]")
        console.print(f"Results saved to: {output_file}")
        
        # Generate Gamma presentation if requested
        if generate_gamma:
            console.print(f"[yellow]Generating Gamma presentation...[/yellow]")
            
            from src.services.gamma_generator import GammaGenerator
            gamma_generator = GammaGenerator()
            
            try:
                gamma_result = await gamma_generator.generate_from_canny_analysis(
                    canny_results=analysis_results,
                    style='executive',
                    export_format=None,
                    output_dir=Path(output_dir)
                )
                
                console.print(f"[green]✅ Gamma URL: {gamma_result['gamma_url']}[/green]")
                
                # Save Gamma metadata with descriptive name
                gamma_filename = generate_descriptive_filename(
                    'Canny_Gamma_Metadata', start_date, end_date, file_type='json'
                )
                gamma_output = output_file.parent / gamma_filename
                with open(gamma_output, 'w') as f:
                    json.dump(gamma_result, f, indent=2)
                
                console.print(f"Gamma metadata saved to: {gamma_output}")
                    
            except Exception as e:
                console.print(f"[red]Gamma generation failed: {e}[/red]")
                console.print("[yellow]Canny analysis results still saved to JSON[/yellow]")
        
        # Display insights
        insights = analysis_results.get('insights', [])
        if insights:
            console.print(f"\n[bold]Key Insights:[/bold]")
            for insight in insights[:5]:  # Show top 5 insights
                console.print(f"• {insight}")
        
        return output_file
        
    except Exception as e:
        console.print(f"[red]Canny analysis failed: {e}[/red]")
        raise


async def run_voc_analysis(
    start_date: str,
    end_date: str,
    ai_model: str,
    enable_fallback: bool,
    include_trends: bool,
    include_canny: bool,
    canny_board_id: Optional[str],
    generate_gamma: bool,
    separate_agent_feedback: bool,
    output_dir: str
):
    """Run Voice of Customer analysis."""
    from src.utils.time_utils import detect_period_type
    from src.services.ai_model_factory import AIModelFactory, AIModel
    from src.services.agent_feedback_separator import AgentFeedbackSeparator
    from src.analyzers.voice_of_customer_analyzer import VoiceOfCustomerAnalyzer
    from src.services.canny_client import CannyClient
    from src.analyzers.canny_analyzer import CannyAnalyzer
    
    try:
        console.print(f"[bold blue]Starting Voice of Customer Analysis[/bold blue]")
        console.print(f"Date Range: {start_date} to {end_date}")
        console.print(f"AI Model: {ai_model}")
        console.print(f"Fallback: {'enabled' if enable_fallback else 'disabled'}")
        
        # Initialize components
        ai_factory = AIModelFactory()
        agent_separator = AgentFeedbackSeparator()
        # HistoricalDataManager deprecated - pass None (historical features disabled)
        voc_analyzer = VoiceOfCustomerAnalyzer(ai_factory, agent_separator, historical_manager=None)
        
        # Parse dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Fetch conversations
        console.print(f"[yellow]Fetching conversations from Intercom...[/yellow]")
        intercom_service = IntercomSDKService()
        conversations = await intercom_service.fetch_conversations_by_date_range(
            start_date=start_dt,
            end_date=end_dt
        )
        
        if not conversations:
            console.print("[red]No conversations found for the specified date range.[/red]")
            return
        
        console.print(f"[green]Found {len(conversations)} conversations[/green]")
        
        # Run VoC analysis
        console.print(f"[yellow]Running Voice of Customer analysis...[/yellow]")
        
        ai_model_enum = AIModel.ANTHROPIC_CLAUDE if ai_model == 'claude' else AIModel.OPENAI_GPT4
        
        analysis_results = await voc_analyzer.analyze_weekly_sentiment(
            conversations=conversations,
            ai_model=ai_model_enum,
            enable_fallback=enable_fallback,
            options={'include_trends': include_trends}
        )
        
        # Fetch and analyze Canny data if requested
        canny_results = None
        if include_canny:
            console.print(f"[yellow]Fetching Canny data...[/yellow]")
            try:
                canny_client = CannyClient()
                canny_analyzer = CannyAnalyzer(ai_factory)
                
                # Test Canny connection
                await canny_client.test_connection()
                console.print(f"[green]✅ Canny API connection successful[/green]")
                
                # Fetch Canny posts
                if canny_board_id:
                    canny_posts = await canny_client.fetch_posts_by_date_range(
                        start_date=start_dt,
                        end_date=end_dt,
                        board_id=canny_board_id,
                        include_comments=True,
                        include_votes=True
                    )
                else:
                    # Fetch from all boards
                    all_boards_posts = await canny_client.fetch_all_boards_posts(
                        start_date=start_dt,
                        end_date=end_dt,
                        include_comments=True,
                        include_votes=True
                    )
                    # Flatten posts from all boards
                    canny_posts = []
                    for board_posts in all_boards_posts.values():
                        canny_posts.extend(board_posts)
                
                if canny_posts:
                    console.print(f"[green]Found {len(canny_posts)} Canny posts[/green]")
                    
                    # Analyze Canny sentiment
                    canny_results = await canny_analyzer.analyze_canny_sentiment(
                        posts=canny_posts,
                        ai_model=ai_model_enum,
                        enable_fallback=enable_fallback
                    )
                    console.print(f"[green]Canny analysis completed![/green]")
                else:
                    console.print("[yellow]No Canny posts found for the specified date range.[/yellow]")
                    
            except Exception as e:
                console.print(f"[red]Canny integration failed: {e}[/red]")
                console.print("[yellow]Continuing with Intercom analysis only...[/yellow]")
        
        # Generate insights
        insights = voc_analyzer.generate_insights(analysis_results)
        
        # Detect period type from date range
        period_type, period_label = detect_period_type(start_date, end_date)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        from src.utils.time_utils import generate_descriptive_filename
        
        output_filename = generate_descriptive_filename(
            'VOC_Analysis', start_date, end_date, file_type='json'
        )
        output_file = Path(output_dir) / output_filename
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            import json
            result_data = {
                'analysis_results': analysis_results,
                'insights': insights,
                'metadata': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'period_type': period_type,
                    'period_label': period_label,
                    'ai_model': ai_model,
                    'total_conversations': len(conversations),
                    'include_canny': include_canny,
                    'canny_board_id': canny_board_id,
                    'generated_at': datetime.now().isoformat()
                }
            }
            
            # Add Canny results if available
            if canny_results:
                result_data['canny_results'] = canny_results
                result_data['metadata']['total_canny_posts'] = canny_results.get('posts_analyzed', 0)
            
            json.dump(result_data, f, indent=2)
        
        console.print(f"[green]VoC analysis completed![/green]")
        console.print(f"Results saved to: {output_file}")
        
        # 🎯 SAVE STRUCTURED DATA (all agent insights before Gamma flattening)
        structured_data_file = output_file.with_name(output_file.stem + '_STRUCTURED_DATA.json')
        formatter_data = analysis_results.get('OutputFormatterAgent', {}).get('data', {})
        structured_data = formatter_data.get('structured_data', {})
        
        if structured_data:
            with open(structured_data_file, 'w') as f:
                json.dump(structured_data, f, indent=2)
            console.print(f"[cyan]📊 Complete structured data saved to: {structured_data_file}[/cyan]")
            console.print(f"[cyan]   This file contains ALL agent insights (topics, confidence, hierarchies, correlations)[/cyan]")
        else:
            console.print(f"[yellow]⚠️  No structured data available (using older OutputFormatter version)[/yellow]")
        
        # Generate Gamma presentation if requested
        if generate_gamma:
            console.print(f"[yellow]Generating Gamma presentation...[/yellow]")
            
            from src.services.gamma_generator import GammaGenerator
            gamma_generator = GammaGenerator()
            
            try:
                # Use combined results if Canny data is available
                if canny_results:
                    # For now, use VoC analysis and note Canny data in metadata
                    combined_results = analysis_results.copy()
                    combined_results['canny_summary'] = {
                        'posts_analyzed': canny_results.get('posts_analyzed', 0),
                        'overall_sentiment': canny_results.get('sentiment_summary', {}).get('overall', 'neutral'),
                        'top_requests': canny_results.get('top_requests', [])[:3],  # Top 3
                        'total_votes': canny_results.get('vote_analysis', {}).get('total_votes', 0)
                    }
                    gamma_result = await gamma_generator.generate_from_voc_analysis(
                        voc_results=combined_results,
                        style='executive',
                        export_format=None,
                        output_dir=Path(output_dir)
                    )
                else:
                    gamma_result = await gamma_generator.generate_from_voc_analysis(
                        voc_results=analysis_results,
                        style='executive',
                        export_format=None,
                        output_dir=Path(output_dir)
                    )
                
                console.print(f"[green]✅ Gamma URL: {gamma_result['gamma_url']}[/green]")
                
                # Save Gamma metadata with descriptive name
                gamma_filename = generate_descriptive_filename(
                    'VOC_Gamma_Metadata', start_date, end_date, file_type='json'
                )
                gamma_output = output_file.parent / gamma_filename
                with open(gamma_output, 'w') as f:
                    json.dump(gamma_result, f, indent=2)
                
                console.print(f"Gamma metadata saved to: {gamma_output}")
                    
            except Exception as e:
                console.print(f"[red]Gamma generation failed: {e}[/red]")
                console.print("[yellow]VoC analysis results still saved to JSON[/yellow]")
        
        # Display insights
        if insights:
            console.print(f"\n[bold]Key Insights:[/bold]")
            for insight in insights[:5]:  # Show top 5 insights
                console.print(f"• {insight}")
        
        return output_file
        
    except Exception as e:
        console.print(f"[red]VoC analysis failed: {e}[/red]")
        raise


@cli.command(name='canny-analysis')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
@click.option('--time-period', type=click.Choice(['week', 'month', 'quarter']),
              help='Time period shortcut (overrides start/end dates)')
@click.option('--board-id', help='Specific Canny board ID (optional)')
@click.option('--ai-model', type=click.Choice(['openai', 'claude']), default='openai', 
              help='AI model to use for sentiment analysis')
@click.option('--enable-fallback/--no-fallback', default=True,
              help='Enable fallback to other AI model if primary fails')
@click.option('--include-comments/--no-comments', default=True,
              help='Include comments in analysis')
@click.option('--include-votes/--no-votes', default=True,
              help='Include votes in analysis')
@click.option('--generate-gamma', is_flag=True, default=False,
              help='Generate Gamma presentation from results')
@click.option('--output-format', type=click.Choice(['gamma', 'markdown', 'json', 'excel']), default='markdown',
              help='Output format for results')
@click.option('--test-mode', is_flag=True, default=False, help='Use mock test data instead of real API calls')
@click.option('--test-data-count', type=str, default='100',
              help='Data volume: micro(100), small(500), medium(1000), large(5000), xlarge(10000), xxlarge(20000) or custom number')
@click.option('--verbose', is_flag=True, default=False, help='Enable verbose DEBUG logging')
@click.option('--audit-trail', is_flag=True, default=False, help='Enable audit trail logging')
@click.option('--output-dir', default='outputs', help='Output directory')
def canny_analysis(
    start_date: Optional[str],
    end_date: Optional[str],
    time_period: Optional[str],
    board_id: Optional[str],
    ai_model: str,
    enable_fallback: bool,
    include_comments: bool,
    include_votes: bool,
    generate_gamma: bool,
    output_format: str,
    test_mode: bool,
    test_data_count: str,
    verbose: bool,
    audit_trail: bool,
    output_dir: str
):
    """
    Analyze Canny product feedback with sentiment analysis.
    
    Examples:
        # Analyze last week
        python src/main.py canny-analysis --time-period week
        
        # Analyze specific dates
        python src/main.py canny-analysis --start-date 2024-01-01 --end-date 2024-01-31
        
        # Test mode with verbose logging
        python src/main.py canny-analysis --time-period week --test-mode --verbose
    """
    console.print(f"[bold]Canny Product Feedback Analysis[/bold]")
    
    # Enable verbose logging if requested
    if verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
        for module in ['agents', 'services', 'src.agents', 'src.services']:
            logging.getLogger(module).setLevel(logging.DEBUG)
        console.print(f"[yellow]🔍 Verbose Logging: ENABLED (DEBUG level)[/yellow]")
    
    # Parse test data count
    test_data_presets = {
        'micro': 100,
        'small': 500,
        'medium': 1000,
        'large': 5000,
        'xlarge': 10000,
        'xxlarge': 20000
    }
    
    try:
        if test_data_count.lower() in test_data_presets:
            test_data_count_int = test_data_presets[test_data_count.lower()]
            preset_label = test_data_count.lower()
        else:
            test_data_count_int = int(test_data_count)
            preset_label = None
    except ValueError:
        console.print(f"[red]Error: Invalid test data count '{test_data_count}'[/red]")
        return
    
    # Test mode indication
    if test_mode:
        preset_info = f" ({preset_label})" if preset_label else ""
        console.print(f"[yellow]🧪 Test Mode: ENABLED ({test_data_count_int} mock posts{preset_info})[/yellow]")
    
    # Audit trail indication
    if audit_trail:
        console.print("[purple]📋 Audit Trail Mode: ENABLED[/purple]")
    
    # Calculate date range
    if time_period:
        from datetime import timedelta
        # Normalize to start of today
        end_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        # All periods end yesterday (not including today)
        end_dt = end_dt - timedelta(days=1)
        
        if time_period == 'week':
            # Exactly 7 complete days
            start_dt = end_dt - timedelta(days=6)
        elif time_period == 'month':
            # Exactly 30 complete days
            start_dt = end_dt - timedelta(days=29)
        elif time_period == 'quarter':
            # Exactly 90 complete days
            start_dt = end_dt - timedelta(days=89)
        start_date = start_dt.strftime('%Y-%m-%d')
        end_date = end_dt.strftime('%Y-%m-%d')
        console.print(f"Analyzing {time_period}: {start_date} to {end_date}")
    elif start_date and end_date:
        console.print(f"Date Range: {start_date} to {end_date}")
    else:
        console.print("[red]Error: Provide either --time-period or both --start-date and --end-date[/red]")
        return
    
    console.print(f"AI Model: {ai_model}")
    console.print(f"Board ID: {board_id or 'All boards'}")
    console.print(f"Comments: {'included' if include_comments else 'excluded'}")
    console.print(f"Votes: {'included' if include_votes else 'excluded'}")
    
    asyncio.run(run_canny_analysis(
        start_date, end_date, board_id, ai_model, enable_fallback,
        include_comments, include_votes, generate_gamma, output_dir
    ))


@cli.command(name='sample-mode')
@click.option('--count', type=int, default=50, help='Number of real conversations to pull (overridden by --schema-mode)')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
@click.option('--time-period', type=click.Choice(['day', 'week', 'month']), default='week',
              help='Time period shortcut (overrides start/end dates)')
@click.option('--save-to-file/--no-save', default=True, help='Save raw JSON to outputs/')
@click.option('--test-llm', is_flag=True, default=False, 
              help='🧪 Run actual LLM sentiment analysis to see what agents produce')
@click.option('--test-all-agents', is_flag=True, default=False,
              help='🧪 Test ALL production agents (SubTopic, Example, Fin, Correlation, Quality, Churn, Confidence)')
@click.option('--show-agent-thinking', is_flag=True, default=False,
              help='🧠 Show agent LLM prompts, responses, and reasoning (for prompt tuning)')
@click.option('--llm-topic-detection', is_flag=True, default=False,
              help='🤖 Use LLM-first for topic detection (more accurate, costs ~$1 per 200 convs)')
@click.option('--schema-mode', type=click.Choice(['quick', 'standard', 'deep', 'comprehensive']), default='quick',
              help='Analysis depth: quick(50/30s), standard(200/2m), deep(500/5m), comprehensive(1000/10m)')
@click.option('--ai-model', type=click.Choice(['openai', 'claude']), default='openai',
              help='AI model for LLM sentiment test (only used if --test-llm enabled)')
@click.option('--include-hierarchy/--no-hierarchy', default=True,
              help='Show/hide topic hierarchy debugging section (default: show)')
@click.option('--verbose', is_flag=True, default=False,
              help='Enable verbose DEBUG logging')
def sample_mode(count: int, start_date: Optional[str], end_date: Optional[str], 
                time_period: str, save_to_file: bool, test_llm: bool, test_all_agents: bool,
                show_agent_thinking: bool, llm_topic_detection: bool, schema_mode: str, 
                ai_model: str, include_hierarchy: bool, verbose: bool):
    """
    SAMPLE MODE: Pull 50-100 REAL conversations with ultra-rich logging
    
    Perfect for:
    - Schema validation
    - Debugging topic detection
    - Testing fixes quickly
    - Seeing real Intercom data structure
    """
    import asyncio
    from src.services.sample_mode import run_sample_mode
    from datetime import timedelta
    
    console.print(Panel.fit(
        "[bold cyan]🔬 SAMPLE MODE[/bold cyan]\n"
        "Pulling REAL conversations with ultra-rich logging",
        border_style="cyan"
    ))
    
    # Parse dates
    if time_period:
        end = datetime.now()
        if time_period == 'day':
            start = end - timedelta(days=1)
        elif time_period == 'week':
            start = end - timedelta(days=7)
        else:  # month
            start = end - timedelta(days=30)
    else:
        start = datetime.strptime(start_date, '%Y-%m-%d') if start_date else datetime.now() - timedelta(days=7)
        end = datetime.strptime(end_date, '%Y-%m-%d') if end_date else datetime.now()
    
    # Show mode description
    mode_descriptions = {
        'quick': '50 tickets, 5 samples, 2 LLM topics (~30 sec)',
        'standard': '200 tickets, 10 samples, 3 LLM topics (~2 min)',
        'deep': '500 tickets, 15 samples, 5 LLM topics (~5 min)',
        'comprehensive': '1000 tickets, 20 samples, 7 LLM topics (~10 min)'
    }
    console.print(f"\n[cyan]Schema Mode: {schema_mode} - {mode_descriptions[schema_mode]}[/cyan]\n")
    
    # Set AI model for LLM test if test_llm is enabled
    if test_llm and ai_model:
        os.environ['AI_MODEL'] = ai_model
        console.print(f"[cyan]🤖 AI Model for LLM Test: {ai_model.upper()}[/cyan]\n")
    
    # Enable verbose logging if requested
    if verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
        for module in ['src.agents', 'src.services']:
            logging.getLogger(module).setLevel(logging.DEBUG)
        console.print(f"[yellow]🔍 Verbose Logging: ENABLED[/yellow]\n")
    
    # Enable agent thinking logger if requested
    if show_agent_thinking:
        from src.utils.agent_thinking_logger import AgentThinkingLogger
        from pathlib import Path
        
        # Create thinking log file
        output_dir = Path(settings.effective_output_directory)
        output_dir.mkdir(exist_ok=True, parents=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        thinking_log = output_dir / f"agent_thinking_{timestamp}.log"
        
        AgentThinkingLogger.enable(thinking_log)
    
    # Enable LLM-first topic detection if requested
    if llm_topic_detection:
        os.environ['LLM_TOPIC_DETECTION'] = 'true'
        console.print("[bold cyan]🤖 LLM-First Topic Detection: ENABLED[/bold cyan]")
        console.print("[dim]Uses GPT-4o-mini to classify every conversation (~$1 per 200 convs)[/dim]\n")
    
    # Run sample mode with error handling (ALWAYS save files even if it crashes!)
    try:
        result = asyncio.run(run_sample_mode(
            count=count,
            start_date=start,
            end_date=end,
            save_to_file=save_to_file,
            test_llm=test_llm,
            test_all_agents=test_all_agents,
            show_agent_thinking=show_agent_thinking,
            schema_mode=schema_mode,
            include_hierarchy=include_hierarchy
        ))
        
        console.print("\n[bold green]✅ Sample mode complete![/bold green]")
        console.print(f"Analyzed {result.get('analysis', {}).get('total_conversations', 0)} conversations")
    except Exception as e:
        console.print(f"\n[bold red]❌ Sample mode failed: {e}[/bold red]")
        console.print(f"[yellow]⚠️  Files should still be saved despite error[/yellow]")
        # Re-raise so Railway sees the error, but files were already saved above!
        raise
    console.print("\n[bold]Key Findings:[/bold]")
    
    # Safe nested access to avoid KeyError
    agent_attr = result.get('analysis', {}).get('agent_attribution', {})
    custom_attrs = result.get('analysis', {}).get('custom_attributes', {})
    
    console.print(f"  Sal conversations: {agent_attr.get('sal_count', 0)} ({agent_attr.get('sal_percentage', 0)}%)")
    console.print(f"  Human admin: {agent_attr.get('human_admin_count', 0)} ({agent_attr.get('human_admin_percentage', 0)}%)")
    console.print(f"  With custom_attributes: {custom_attrs.get('has_custom_attributes', 0)} ({custom_attrs.get('percentage_with_attributes', 0)}%)")


@cli.command(name='test-mode')
@click.option('--test-type', type=click.Choice(['topic-based', 'api', 'horatio']), default='topic-based',
              help='Type of test to run')
@click.option('--num-conversations', type=int, default=50, help='Number of test conversations (default: 50)')
def test_mode(test_type: str, num_conversations: int):
    """TEST MODE: Run with minimal fake data for debugging"""
    import json
    
    console.print(f"[bold yellow]🧪 TEST MODE[/bold yellow]")
    console.print(f"Test type: {test_type}")
    console.print(f"Fake conversations: {num_conversations}")
    console.print("="*80)
    
    # Create minimal fake data
    fake_conversations = []
    topics = ['Billing', 'Bug', 'Credits', 'Account', 'Product Question']
    
    for i in range(num_conversations):
        topic = topics[i % len(topics)]
        conv = {
            'id': f'test_{i}',
            'created_at': int((datetime.now() - timedelta(hours=i)).timestamp()),
            'updated_at': int(datetime.now().timestamp()),
            'state': 'closed',
            'count_reopens': 0 if i % 3 == 0 else 1,
            'admin_assignee_id': '12345',
            'custom_attributes': {topic: True},
            'tags': {'tags': [{'name': topic}]},
            'full_text': f"Customer says: This is about {topic.lower()}. Agent responds: Got it.",
            'customer_messages': [f"This is about {topic.lower()}"],
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': f"This is about {topic.lower()}"},
                    {'author': {'type': 'admin'}, 'body': "Got it."}
                ]
            },
            'source': {'author': {'type': 'user'}, 'body': f"This is about {topic.lower()}"}
        }
        fake_conversations.append(conv)
    
    console.print(f"✅ Created {len(fake_conversations)} fake conversations")
    
    # Save test data
    test_file = Path("outputs/test_data.json")
    test_file.parent.mkdir(exist_ok=True)
    with open(test_file, 'w') as f:
        json.dump(fake_conversations, f, indent=2)
    console.print(f"📁 Test data saved to: {test_file}")
    
    # Run appropriate test
    if test_type == 'topic-based':
        console.print("\n🤖 Running topic-based analysis with test data...")
        asyncio.run(run_test_topic_based(fake_conversations))
    elif test_type == 'api':
        console.print("\n⚙️  Running API analysis with test data...")
        console.print("[yellow]API test not yet implemented[/yellow]")
    elif test_type == 'horatio':
        console.print("\n👤 Running Horatio performance with test data...")
        console.print("[yellow]Horatio test not yet implemented[/yellow]")


async def run_test_topic_based(conversations):
    """Run topic-based analysis with test data"""
    # Comment 3: Add timing logs for heavy imports (TopicOrchestrator, ChunkedFetcher)
    verbose_imports = os.getenv('VERBOSE', '').lower() in ('1', 'true', 'yes')
    if verbose_imports:
        import time as time_module
        import_start = time_module.monotonic()
        console.print(f"[dim]⏱️  Importing TopicOrchestrator...[/dim]")
    
    from src.agents.topic_orchestrator import TopicOrchestrator
    
    if verbose_imports:
        import_duration = time_module.monotonic() - import_start
        console.print(f"[dim]✅ TopicOrchestrator imported in {import_duration:.2f}s[/dim]")
    
    orchestrator = TopicOrchestrator()
    
    try:
        results = await orchestrator.execute_weekly_analysis(
            conversations=conversations,
            week_id="TEST",
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now()
        )
        
        console.print("\n" + "="*80)
        console.print("[bold green]✅ TEST PASSED[/bold green]")
        console.print("="*80)
        
        # Show summary
        summary = results.get('summary', {})
        console.print(f"\n📊 Summary:")
        console.print(f"   Total: {summary.get('total_conversations')}")
        console.print(f"   Topics: {summary.get('topics_analyzed')}")
        console.print(f"   Agents: {summary.get('agents_completed')}")
        console.print(f"   Time: {summary.get('total_execution_time')}s")
        
        # Show report preview
        report = results.get('formatted_report', '')
        if report:
            console.print(f"\n📝 Report preview (first 500 chars):")
            console.print(report[:500])
        
        # Save test output
        test_output = Path("outputs/test_output.md")
        with open(test_output, 'w') as f:
            f.write(report)
        console.print(f"\n📁 Test output: {test_output}")
        
    except Exception as e:
        console.print(f"\n[red]❌ TEST FAILED: {e}[/red]")
        import traceback
        traceback.print_exc()


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
              default='topic-based', help='Analysis type when multi-agent enabled')
@click.option('--ai-model', type=click.Choice(['openai', 'claude']), default=None,
              help='AI model to use (openai or claude). Defaults to config setting.')
@click.option('--audit-trail', is_flag=True, default=False,
              help='Enable audit trail logging for debugging and compliance')
@click.option('--llm-topic-detection', is_flag=True, default=True,
              help='🤖 LLM-first topic detection (DEFAULT: ON for accuracy - use --no-llm-topic-detection to disable)')
@click.option('--output-dir', default='outputs', help='Output directory')
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
    output_dir: str
):
    """
    Generate Voice of Customer sentiment analysis.
    
    Examples:
        # Yesterday (fast test - ~1k conversations)
        python src/main.py voice-of-customer --time-period yesterday
        
        # Last week
        python src/main.py voice-of-customer --time-period week
        
        # Last month
        python src/main.py voice-of-customer --time-period month
        
        # Last 3 months
        python src/main.py voice-of-customer --time-period month --periods-back 3
        
        # Last quarter
        python src/main.py voice-of-customer --time-period quarter
        
        # Custom date range
        python src/main.py voice-of-customer --start-date 2024-01-01 --end-date 2024-01-07
        
        # With Gamma presentation (PDF export)
        python src/main.py voice-of-customer --time-period week --output-format gamma --gamma-export pdf
        
        # With Gamma presentation (PowerPoint export)
        python src/main.py voice-of-customer --time-period week --output-format gamma --gamma-export pptx
    """
    from src.utils.time_utils import calculate_date_range, format_date_range_for_display
    
    # Calculate dates using shared utility
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
        
        if time_period:
            console.print(f"[bold]Voice of Customer Analysis - {time_period.capitalize()}[/bold]")
            console.print(f"Period: Last {periods_back} {time_period}(s)")
        else:
            console.print(f"[bold]Voice of Customer Analysis - Custom Range[/bold]")
        
        console.print(f"Date Range: {format_date_range_for_display(start_dt, end_dt)} (Pacific Time)")
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return
    console.print(f"AI Model: {ai_model}")
    console.print(f"Fallback: {'enabled' if enable_fallback else 'disabled'}")
    
    # Enable verbose logging if requested
    if verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
        # Also set for specific modules
        for module in ['agents', 'services', 'src.agents', 'src.services']:
            logging.getLogger(module).setLevel(logging.DEBUG)
        console.print(f"[yellow]🔍 Verbose Logging: ENABLED (DEBUG level)[/yellow]")
    
    # Parse test data count (supports presets or custom numbers)
    test_data_presets = {
        'micro': 100,       # 1 hour of data
        'small': 500,       # Few hours
        'medium': 1000,     # ~1 day
        'large': 5000,      # ~1 week (realistic)
        'xlarge': 10000,    # 2 weeks
        'xxlarge': 20000    # 1 month
    }
    
    try:
        # Check if it's a preset name
        if test_data_count.lower() in test_data_presets:
            test_data_count_int = test_data_presets[test_data_count.lower()]
            preset_label = test_data_count.lower()
        else:
            # Try to parse as number
            test_data_count_int = int(test_data_count)
            preset_label = None
    except ValueError:
        console.print(f"[red]Error: Invalid test data count '{test_data_count}'. Use a number or preset (micro, small, medium, large, xlarge, xxlarge)[/red]")
        return
    
    # Test mode indication
    if test_mode:
        preset_info = f" ({preset_label})" if preset_label else ""
        console.print(f"[yellow]🧪 Test Mode: ENABLED ({test_data_count_int} mock conversations{preset_info})[/yellow]")
        console.print(f"[dim]   No API calls will be made - using generated test data[/dim]")
        if test_data_count_int >= 5000:
            console.print(f"[dim]   💡 Note: Large datasets may take 1-3 minutes to process[/dim]")
    
    # Set AI model if specified
    if ai_model:
        os.environ['AI_MODEL'] = ai_model
        console.print(f"[cyan]🤖 AI Model: {ai_model}[/cyan]")
    
    # Enable LLM-first topic detection if requested
    if llm_topic_detection:
        os.environ['LLM_TOPIC_DETECTION'] = 'true'
        console.print(f"[bold cyan]🤖 LLM-First Topic Detection: ENABLED[/bold cyan]")
        console.print(f"[dim]   Uses GPT-4o-mini to classify every conversation[/dim]")
        console.print(f"[dim]   More accurate for edge cases (~$1 per 200 convs)[/dim]\n")
    
    # This branch is multi-agent only
    console.print(f"[bold yellow]🤖 Multi-Agent Mode: {analysis_type}[/bold yellow]\n")
    
    # Convert to Pacific Time timezone-aware datetimes
    from src.utils.timezone_utils import get_date_range_pacific
    start_dt, end_dt = get_date_range_pacific(start_date, end_date)
    
    if analysis_type == 'topic-based':
        asyncio.run(run_topic_based_analysis_custom(start_dt, end_dt, generate_gamma, test_mode, test_data_count_int, audit_trail))
    elif analysis_type == 'synthesis':
        asyncio.run(run_synthesis_analysis_custom(start_dt, end_dt, generate_gamma, audit_trail))
    else:  # complete
        asyncio.run(run_complete_analysis_custom(start_dt, end_dt, generate_gamma, audit_trail))


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
    
    console.print(Panel.fit(
        "[bold green]🤖 Intercom Analysis Tool - Chat Interface[/bold green]\n"
        "Natural language interface for generating analysis reports",
        border_style="green"
    ))
    
    try:
        # Import chat components
        from chat.chat_interface import ChatInterface
        from chat.terminal_ui import TerminalChatUI
        from config.settings import Settings
        
        # Initialize settings
        settings = Settings()
        
        # Initialize chat interface
        chat_interface = ChatInterface(settings)
        
        console.print("[green]✅ Chat interface initialized successfully[/green]")
        console.print("[dim]Type 'help' for available commands, 'quit' to exit[/dim]")
        
        # Start the terminal UI
        terminal_ui = TerminalChatUI(chat_interface.translator, chat_interface.suggestion_engine)
        terminal_ui.start_chat()
        
    except ImportError as e:
        console.print(f"[red]❌ Failed to import chat components: {e}[/red]")
        console.print("[yellow]Make sure all chat dependencies are installed[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Failed to start chat interface: {e}[/red]")
        console.print("[yellow]Check the logs for more details[/yellow]")


async def run_topic_based_analysis_custom(
    start_date: datetime, 
    end_date: datetime, 
    generate_gamma: bool,
    test_mode: bool = False,
    test_data_count: str = "100",
    audit_trail: bool = False
):
    """Run topic-based analysis with custom date range"""
    try:
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
            audit = AuditTrail()
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
        
        orchestrator = TopicOrchestrator(audit_trail=audit, execution_monitor=monitor)
        week_id = start_date.strftime('%Y-W%W')
        
        results = await orchestrator.execute_weekly_analysis(
            conversations=conversations,
            week_id=week_id,
            start_date=start_date,
            end_date=end_date,
            period_type=period_type,
            period_label=period_label
        )
        
        # Save output
        output_dir = Path(settings.effective_output_directory)
        output_dir.mkdir(exist_ok=True, parents=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = output_dir / f"topic_based_{week_id}_{timestamp}.md"
        
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
                        url_file = output_dir / url_filename
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


async def run_synthesis_analysis_custom(start_date: datetime, end_date: datetime, generate_gamma: bool, audit_trail: bool = False):
    """Run synthesis analysis with custom date range"""
    from src.agents.orchestrator import MultiAgentOrchestrator
    from src.services.chunked_fetcher import ChunkedFetcher
    from src.services.gamma_generator import GammaGenerator
    
    console.print(f"\n🧠 [bold cyan]Synthesis Multi-Agent Analysis[/bold cyan]")
    console.print("Focus: Cross-category patterns, strategic insights, recommendations\n")
    
    # Fetch conversations
    console.print("📥 Fetching conversations...")
    fetcher = ChunkedFetcher()
    conversations = await fetcher.fetch_conversations_chunked(start_date, end_date)
    console.print(f"   ✅ Fetched {len(conversations)} conversations\n")
    
    # Use multi-agent orchestrator for synthesis
    orchestrator = MultiAgentOrchestrator()
    results = await orchestrator.execute_analysis(
        analysis_type="voice-of-customer",
        start_date=start_date,
        end_date=end_date,
        generate_gamma=generate_gamma
    )
    
    # Display and save results
    console.print("\n🎉 Synthesis analysis complete")
    
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    results_file = output_dir / f"synthesis_custom_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}_{timestamp}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    console.print(f"📁 Results saved: {results_file}")


async def run_complete_analysis_custom(start_date: datetime, end_date: datetime, generate_gamma: bool, audit_trail: bool = False):
    """Run both analyses"""
    await run_topic_based_analysis_custom(start_date, end_date, generate_gamma, audit_trail=audit_trail)
    console.print("\n" + "="*80 + "\n")
    await run_synthesis_analysis_custom(start_date, end_date, generate_gamma, audit_trail)
    console.print("\n🎉 Complete analysis finished!")


async def run_topic_based_analysis(month: int, year: int, tier1_countries: List[str], generate_gamma: bool, output_format: str):
    """Run topic-based analysis (Hilary's VoC card format)"""
    try:
        from src.agents.topic_orchestrator import TopicOrchestrator
        from src.services.chunked_fetcher import ChunkedFetcher
        from src.utils.time_utils import detect_period_type
        
        # Calculate date range for the month
        from calendar import monthrange
        start_date = datetime(year, month, 1)
        last_day = monthrange(year, month)[1]
        end_date = datetime(year, month, last_day, 23, 59, 59)
        
        console.print(f"\n🤖 [bold cyan]Multi-Agent Topic-Based Analysis Starting[/bold cyan]")
        console.print(f"Mode: Topic-Based Workflow (Hilary's Format)")
        console.print(f"Agents: Segmentation → Topic Detection → Per-Topic Sentiment → Examples → Fin Analysis → Trends")
        console.print(f"Expected output: Hilary's exact card format\n")
        
        # Fetch conversations for the period
        console.print("📥 Fetching conversations...")
        fetcher = ChunkedFetcher()
        conversations = await fetcher.fetch_conversations_chunked(
            start_date=start_date,
            end_date=end_date
        )
        
        console.print(f"   ✅ Fetched {len(conversations)} conversations\n")
        
        # Detect period type from date range
        period_type, period_label = detect_period_type(start_date, end_date)
        
        # Initialize topic-based orchestrator
        orchestrator = TopicOrchestrator()
        
        # Execute topic-based workflow
        week_id = f"{year}-{month:02d}"
        results = await orchestrator.execute_weekly_analysis(
            conversations=conversations,
            week_id=week_id,
            start_date=start_date,
            end_date=end_date,
            period_type=period_type,
            period_label=period_label
        )
        
        # Display results
        console.print("\n" + "="*80)
        console.print("[bold green]🎉 Topic-Based Analysis Complete![/bold green]")
        console.print("="*80 + "\n")
        
        summary = results['summary']
        console.print(f"📊 Total conversations: {summary['total_conversations']}")
        console.print(f"   Paid customers (human support): {summary['paid_conversations']}")
        console.print(f"   Free customers (Fin AI): {summary['free_conversations']}")
        console.print(f"🏷️  Topics analyzed: {summary['topics_analyzed']}")
        console.print(f"⏱️  Total time: {summary['total_execution_time']:.1f}s")
        console.print(f"🤖 Agents completed: {summary['agents_completed']}/7")
        
        # Show formatted report preview
        formatted_report = results.get('formatted_report', '')
        if formatted_report:
            console.print("\n📝 [bold]Report Preview:[/bold]")
            console.print(formatted_report[:500] + "..." if len(formatted_report) > 500 else formatted_report)
        
        # Export results
        output_dir = Path(settings.effective_output_directory)
        output_dir.mkdir(exist_ok=True, parents=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Generate descriptive filenames
        from src.utils.time_utils import generate_descriptive_filename
        
        report_filename = generate_descriptive_filename(
            'VoC_Report', start_date, end_date, file_type='md', week_id=week_id
        )
        results_filename = generate_descriptive_filename(
            'VoC_Analysis', start_date, end_date, file_type='json', week_id=week_id
        )
        
        # Save formatted report
        report_file = output_dir / report_filename
        with open(report_file, 'w') as f:
            f.write(formatted_report)
        
        # Save full results JSON
        results_file = output_dir / results_filename
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        console.print(f"\n📁 Report saved: {report_file}")
        console.print(f"📁 Full results: {results_file}")
        
        # Generate Gamma presentation if requested
        if generate_gamma and formatted_report:
            try:
                from src.services.gamma_generator import GammaGenerator
                from src.services.gamma_client import GammaAPIError
                
                console.print(f"\n🎨 [bold cyan]Generating Gamma presentation...[/bold cyan]")
                
                gamma_generator = GammaGenerator()
                
                # Calculate number of cards based on topics
                num_cards = min(summary.get('topics_analyzed', 5) + 3, 20)
                
                # Create proper title with date range
                title_start = start_date.strftime('%b %d')
                title_end = end_date.strftime('%b %d, %Y')
                gamma_title = f"Voice of Customer: {title_start} - {title_end}"
                
                gamma_result = await gamma_generator.generate_from_markdown(
                    input_text=formatted_report,
                    title=gamma_title,
                    num_cards=num_cards,
                    theme_name=None,
                    export_format=None,
                    output_dir=output_dir
                )
                
                # Display Gamma URL
                gamma_url = gamma_result.get('gamma_url')
                if gamma_url:
                    console.print(f"\n🎨 [bold green]Gamma presentation generated![/bold green]")
                    console.print(f"📊 Gamma URL: {gamma_url}")
                    console.print(f"💳 Credits used: {gamma_result.get('credits_used', 0)}")
                    console.print(f"⏱️  Generation time: {gamma_result.get('generation_time_seconds', 0):.1f}s")
                    
                    # Save Gamma URL to separate file with descriptive name
                    gamma_url_filename = generate_descriptive_filename(
                        'Gamma_URL_VoC', start_date, end_date, file_type='txt', week_id=week_id
                    )
                    gamma_url_file = output_dir / gamma_url_filename
                    with open(gamma_url_file, 'w') as f:
                        f.write(f"Gamma Presentation URL\n")
                        f.write(f"=====================\n\n")
                        f.write(f"Analysis: Voice of Customer - {title_start} - {title_end}\n")
                        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                        f.write(f"URL: {gamma_url}\n")
                    
                    console.print(f"📁 Gamma URL saved: {gamma_url_file}")
                    
                    # Add Gamma metadata to results
                    results['gamma_presentation'] = {
                        'gamma_url': gamma_url,
                        'generation_id': gamma_result.get('generation_id'),
                        'credits_used': gamma_result.get('credits_used'),
                        'generation_time_seconds': gamma_result.get('generation_time_seconds'),
                        'theme': gamma_result.get('theme'),
                        'slide_count': gamma_result.get('slide_count')
                    }
                    
                    # Re-save JSON with Gamma metadata
                    with open(results_file, 'w') as f:
                        json.dump(results, f, indent=2, default=str)
                
            except GammaAPIError as e:
                console.print(f"[yellow]Warning: Gamma generation failed: {e}[/yellow]")
                console.print("[yellow]Continuing without Gamma presentation...[/yellow]")
            except Exception as e:
                console.print(f"[yellow]Warning: Unexpected error during Gamma generation: {e}[/yellow]")
                console.print("[yellow]Continuing without Gamma presentation...[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error in topic-based analysis: {e}[/red]")
        raise


async def run_synthesis_analysis(month: int, year: int, tier1_countries: List[str], generate_gamma: bool, output_format: str):
    """Run synthesis analysis (cross-category insights and recommendations)"""
    try:
        from src.agents.orchestrator import MultiAgentOrchestrator
        from src.services.chunked_fetcher import ChunkedFetcher
        from calendar import monthrange
        
        start_date = datetime(year, month, 1)
        last_day = monthrange(year, month)[1]
        end_date = datetime(year, month, last_day, 23, 59, 59)
        
        console.print(f"\n🧠 [bold cyan]Synthesis Multi-Agent Analysis[/bold cyan]")
        console.print("Focus: Cross-category patterns, strategic insights, recommendations\n")
        
        # Fetch conversations
        fetcher = ChunkedFetcher()
        conversations = await fetcher.fetch_conversations_chunked(start_date, end_date)
        console.print(f"   ✅ Fetched {len(conversations)} conversations\n")
        
        # Use original multi-agent orchestrator for synthesis
        orchestrator = MultiAgentOrchestrator()
        results = await orchestrator.execute_analysis(
            analysis_type="voice-of-customer",
            start_date=start_date,
            end_date=end_date,
            generate_gamma=generate_gamma
        )
        
        # Display and save results
        console.print("\n🎉 Synthesis analysis complete")
        
        output_dir = Path(settings.effective_output_directory)
        output_dir.mkdir(exist_ok=True, parents=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        results_file = output_dir / f"synthesis_voc_{month}_{year}_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        console.print(f"📁 Results saved: {results_file}")
        
    except Exception as e:
        console.print(f"[red]Error in synthesis analysis: {e}[/red]")
        raise


async def run_complete_multi_agent_analysis(month: int, year: int, tier1_countries: List[str], generate_gamma: bool, output_format: str):
    """Run BOTH topic-based AND synthesis analysis"""
    console.print("[bold cyan]🎯 Running Complete Multi-Agent Analysis[/bold cyan]")
    console.print("Part 1: Topic-Based Analysis (Hilary's format)")
    console.print("Part 2: Synthesis Analysis (Strategic insights)\n")
    
    # Run topic-based
    await run_topic_based_analysis(month, year, tier1_countries, generate_gamma, output_format)
    
    console.print("\n" + "="*80 + "\n")
    
    # Run synthesis
    await run_synthesis_analysis(month, year, tier1_countries, generate_gamma, output_format)
    
    console.print("\n🎉 [bold green]Complete analysis finished![/bold green]")
    console.print("Check outputs/ for both topic-based cards AND synthesis insights")


if __name__ == "__main__":
    cli()
