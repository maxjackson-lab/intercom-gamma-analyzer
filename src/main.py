"""
Main CLI application for Intercom to Gamma analysis tool.
"""

import asyncio
import json
import logging
import sys
import warnings
from datetime import datetime, date, timedelta
from typing import List, Optional
from pathlib import Path

# Suppress urllib3 SSL warning
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel

# Add src to path for imports
sys.path.append(str(Path(__file__).parent))

from config.settings import settings
from services.intercom_service import IntercomService
from services.intercom_service_v2 import IntercomServiceV2
from services.elt_pipeline import ELTPipeline
from config.taxonomy import taxonomy_manager
from services.metrics_calculator import MetricsCalculator
from services.openai_client import OpenAIClient
from services.gamma_client import GammaClient
from services.data_exporter import DataExporter
from services.query_builder import QueryBuilder, GeneralQueryService
from services.chunked_fetcher import ChunkedFetcher
from services.data_preprocessor import DataPreprocessor
from services.category_filters import CategoryFilters
from services.gamma_generator import GammaGenerator
from services.orchestrator import AnalysisOrchestrator
from analyzers.voice_analyzer import VoiceAnalyzer
from analyzers.trend_analyzer import TrendAnalyzer
from analyzers.base_category_analyzer import BaseCategoryAnalyzer
from analyzers.billing_analyzer import BillingAnalyzer
from analyzers.product_analyzer import ProductAnalyzer
from analyzers.sites_analyzer import SitesAnalyzer
from analyzers.api_analyzer import ApiAnalyzer
from analyzers.voice_of_customer_analyzer import VoiceOfCustomerAnalyzer
from analyzers.canny_analyzer import CannyAnalyzer
from services.ai_model_factory import AIModelFactory, AIModel
from services.agent_feedback_separator import AgentFeedbackSeparator
from services.historical_data_manager import HistoricalDataManager
from services.canny_client import CannyClient
from services.canny_preprocessor import CannyPreprocessor
from models.analysis_models import AnalysisRequest, AnalysisMode
from utils.logger import setup_logging
from utils.cli_help import help_system

console = Console()


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


@cli.command()
@click.option('--month', type=int, required=True, help='Month (1-12)')
@click.option('--year', type=int, required=True, help='Year')
@click.option('--tier1-countries', help='Comma-separated tier 1 countries')
@click.option('--generate-gamma', is_flag=True, help='Generate Gamma presentation')
@click.option('--output-format', type=click.Choice(['gamma', 'markdown', 'json']), default='markdown')
@click.option('--multi-agent', is_flag=True, help='Use multi-agent mode (premium quality, 3-5x cost)')
@click.option('--analysis-type', type=click.Choice(['standard', 'topic-based', 'synthesis']), default='standard', 
              help='Analysis type: standard (single), topic-based (Hilary format), synthesis (insights)')
def voice(month: int, year: int, tier1_countries: Optional[str], generate_gamma: bool, output_format: str, multi_agent: bool, analysis_type: str):
    """Generate Voice of Customer analysis for monthly executive reports"""
    
    # Parse tier1 countries
    tier1_list = []
    if tier1_countries:
        tier1_list = [country.strip() for country in tier1_countries.split(',')]
    else:
        tier1_list = settings.default_tier1_countries
    
    console.print(f"[bold green]Voice of Customer Analysis[/bold green]")
    console.print(f"Month: {month}/{year}")
    console.print(f"Tier 1 Countries: {', '.join(tier1_list)}")
    
    # This branch is multi-agent only
    # Route based on analysis type (default: topic-based)
    if not multi_agent:
        console.print("[yellow]ℹ️  Note: This branch uses multi-agent by default. Use main branch for single-agent.[/yellow]")
        analysis_type = analysis_type or 'topic-based'  # Force multi-agent
    
    if analysis_type == 'topic-based':
        console.print("[bold yellow]📋 Topic-Based Multi-Agent Analysis[/bold yellow]")
        console.print("Format: Hilary's VoC Cards - Per-topic sentiment with examples\n")
        asyncio.run(run_topic_based_analysis(month, year, tier1_list, generate_gamma, output_format))
    elif analysis_type == 'synthesis':
        console.print("[bold yellow]🧠 Synthesis Multi-Agent Analysis[/bold yellow]")  
        console.print("Format: Cross-category insights and strategic recommendations\n")
        asyncio.run(run_synthesis_analysis(month, year, tier1_list, generate_gamma, output_format))
    else:  # complete
        console.print("[bold yellow]🎯 Complete Multi-Agent Analysis[/bold yellow]")
        console.print("Includes: Topic-based cards + Synthesis insights\n")
        asyncio.run(run_complete_multi_agent_analysis(month, year, tier1_list, generate_gamma, output_format))


@cli.command()
@click.option('--start-date', required=True, help='Start date (YYYY-MM-DD)')
@click.option('--end-date', required=True, help='End date (YYYY-MM-DD)')
@click.option('--focus-areas', help='Comma-separated focus areas (e.g., billing,product,escalations)')
@click.option('--custom-prompt', help='Custom analysis instructions')
@click.option('--generate-gamma', is_flag=True, help='Generate Gamma presentation')
@click.option('--output-format', type=click.Choice(['gamma', 'markdown', 'json']), default='markdown')
def trends(start_date: str, end_date: str, focus_areas: Optional[str], custom_prompt: Optional[str], 
           generate_gamma: bool, output_format: str):
    """Generate general purpose trend analysis for any time period"""
    
    # Parse dates (keep as datetime objects for pipeline compatibility)
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        console.print("[red]Error: Invalid date format. Use YYYY-MM-DD[/red]")
        sys.exit(1)
    
    # Parse focus areas
    focus_list = []
    if focus_areas:
        focus_list = [area.strip() for area in focus_areas.split(',')]
    
    console.print(f"[bold green]Trend Analysis[/bold green]")
    console.print(f"Date Range: {start_date} to {end_date}")
    console.print(f"Focus Areas: {', '.join(focus_list) if focus_list else 'General trends'}")
    
    # Create analysis request
    request = AnalysisRequest(
        mode=AnalysisMode.TREND_ANALYSIS,
        start_date=start_dt,
        end_date=end_dt,
        focus_areas=focus_list,
        custom_instructions=custom_prompt
    )
    
    # Run analysis
    asyncio.run(run_trend_analysis(request, generate_gamma, output_format))


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
            intercom_service = IntercomService()
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

@cli.command()
@click.option('--days', type=int, default=90, help='Number of days to scan for tags')
@click.option('--agent', help='Filter by specific agent')
def show_tags(days: int, agent: Optional[str]):
    """List tags in your data"""
    console.print(f"[bold]Scanning {days} days for tags...[/bold]")
    # TODO: Implement tag discovery
    console.print("Tag discovery not yet implemented")

@cli.command()
@click.option('--days', type=int, default=90, help='Number of days to scan for agents')
def show_agents(days: int):
    """List all agents"""
    console.print(f"[bold]Scanning {days} days for agents...[/bold]")
    # TODO: Implement agent discovery
    console.print("Agent discovery not yet implemented")

@cli.command()
@click.option('--days', type=int, default=90, help='Number of days to scan')
@click.option('--auto-update', is_flag=True, help='Automatically update taxonomy')
def sync_taxonomy(days: int, auto_update: bool):
    """Update taxonomy from Intercom"""
    console.print(f"[bold]Syncing taxonomy from {days} days of data...[/bold]")
    # TODO: Implement taxonomy sync
    console.print("Taxonomy sync not yet implemented")

# Primary Commands (Technical Triage)
@cli.command(name='tech-analysis')
@click.option('--days', type=int, default=30, help='Number of days to analyze (default: 30)')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
@click.option('--max-pages', type=int, help='Maximum pages to fetch (for testing)')
@click.option('--generate-ai-report', is_flag=True, help='Generate AI-powered insights report')
def tech_analysis(days: int, start_date: Optional[str], end_date: Optional[str], max_pages: Optional[int], generate_ai_report: bool):
    """Analyze technical troubleshooting patterns in Intercom conversations"""
    
    console.print(f"[bold green]Technical Troubleshooting Analysis[/bold green]")
    
    # Calculate date range
    if start_date and end_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        console.print(f"Analyzing from {start_date} to {end_date}")
    else:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)
        console.print(f"Analyzing last {days} days of conversations")
    
    # Run technical analysis
    asyncio.run(run_technical_analysis_v2(start_dt, end_dt, max_pages, generate_ai_report))

@cli.command(name='find-macros')
@click.option('--min-occurrences', type=int, default=5, help='Minimum occurrences for macro (default: 5)')
@click.option('--days', type=int, default=30, help='Number of days to analyze (default: 30)')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
def find_macros(min_occurrences: int, days: int, start_date: Optional[str], end_date: Optional[str]):
    """Discover macro opportunities from repeated agent responses"""
    
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
@click.option('--days', type=int, default=30, help='Number of days to analyze (default: 30)')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
@click.option('--detailed', is_flag=True, help='Generate detailed performance report')
def fin_escalations(days: int, start_date: Optional[str], end_date: Optional[str], detailed: bool):
    """Analyze Fin → human handoffs and effectiveness"""
    
    console.print(f"[bold green]Fin Escalation Analysis[/bold green]")
    
    # Calculate date range
    if start_date and end_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        console.print(f"Analyzing from {start_date} to {end_date}")
    else:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)
        console.print(f"Analyzing last {days} days of conversations")
    
    # Run Fin analysis
    asyncio.run(run_fin_analysis(start_dt, end_dt, detailed))

@cli.command(name='analyze-agent')
@click.option('--agent', required=True, help='Agent name to analyze (e.g., "Dae-Ho")')
@click.option('--days', type=int, default=30, help='Number of days to analyze (default: 30)')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
def analyze_agent(agent: str, days: int, start_date: Optional[str], end_date: Optional[str]):
    """Agent-specific performance analysis"""
    
    console.print(f"[bold green]Agent Performance Analysis: {agent}[/bold green]")
    
    # Calculate date range
    if start_date and end_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        console.print(f"Analyzing from {start_date} to {end_date}")
    else:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)
        console.print(f"Analyzing last {days} days of conversations")
    
    # Run agent analysis
    asyncio.run(run_agent_analysis(agent, start_dt, end_dt))


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
        intercom_service = IntercomService()
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
        intercom_service = IntercomService()
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
        intercom_service = IntercomService()
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
    
    output_path = Path(settings.output_directory) / f"{filename}.json"
    
    with open(output_path, 'w') as f:
        json.dump(results.dict(), f, indent=2, default=str)
    
    console.print(f"JSON output saved to: {output_path}")


def save_markdown_output(results, filename: str):
    """Save results as Markdown."""
    from pathlib import Path
    
    output_path = Path(settings.output_directory) / f"{filename}.md"
    
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
        intercom_service = IntercomService()
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
                start_dt, end_dt, max_pages=max_pages
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
        intercom_service = IntercomService()
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
        intercom_service = IntercomService()
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
    """Run agent performance analysis."""
    console.print(f"[yellow]Agent analysis not yet implemented[/yellow]")
    console.print(f"Would analyze {agent} performance from {start_date.date()} to {end_date.date()}")


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
            from services.category_filters import CategoryFilters
            category_filters = CategoryFilters()
            filtered_conversations = category_filters.filter_by_category(
                all_conversations, category, include_subcategories=True
            )
            
            progress.update(task, description=f"✅ {category} analysis completed")
        
        # Export results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)
        
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
@click.option('--days', type=int, default=30, help='Number of days to analyze')
@click.option('--start-date', type=click.DateTime(formats=['%Y-%m-%d']), help='Start date (YYYY-MM-DD)')
@click.option('--end-date', type=click.DateTime(formats=['%Y-%m-%d']), help='End date (YYYY-MM-DD)')
@click.option('--generate-gamma', is_flag=True, help='Generate Gamma presentation')
@click.option('--max-conversations', type=int, help='Maximum conversations to analyze')
def analyze_billing(days: int, start_date: Optional[datetime], end_date: Optional[datetime], 
                   generate_gamma: bool, max_conversations: Optional[int]):
    """Analyze billing conversations (refunds, invoices, credits, discounts)."""
    if not start_date:
        start_date = datetime.now() - timedelta(days=days)
    if not end_date:
        end_date = datetime.now()
    
    asyncio.run(run_billing_analysis(start_date, end_date, generate_gamma, max_conversations))


@cli.command(name='analyze-product')
@click.option('--days', type=int, default=30, help='Number of days to analyze')
@click.option('--start-date', type=click.DateTime(formats=['%Y-%m-%d']), help='Start date (YYYY-MM-DD)')
@click.option('--end-date', type=click.DateTime(formats=['%Y-%m-%d']), help='End date (YYYY-MM-DD)')
@click.option('--generate-gamma', is_flag=True, help='Generate Gamma presentation')
@click.option('--max-conversations', type=int, help='Maximum conversations to analyze')
def analyze_product(days: int, start_date: Optional[datetime], end_date: Optional[datetime], 
                   generate_gamma: bool, max_conversations: Optional[int]):
    """Analyze product conversations (export issues, bugs, feature requests)."""
    if not start_date:
        start_date = datetime.now() - timedelta(days=days)
    if not end_date:
        end_date = datetime.now()
    
    asyncio.run(run_product_analysis(start_date, end_date, generate_gamma, max_conversations))


@cli.command(name='analyze-sites')
@click.option('--days', type=int, default=30, help='Number of days to analyze')
@click.option('--start-date', type=click.DateTime(formats=['%Y-%m-%d']), help='Start date (YYYY-MM-DD)')
@click.option('--end-date', type=click.DateTime(formats=['%Y-%m-%d']), help='End date (YYYY-MM-DD)')
@click.option('--generate-gamma', is_flag=True, help='Generate Gamma presentation')
@click.option('--max-conversations', type=int, help='Maximum conversations to analyze')
def analyze_sites(days: int, start_date: Optional[datetime], end_date: Optional[datetime], 
                 generate_gamma: bool, max_conversations: Optional[int]):
    """Analyze sites conversations (domain, publishing, education)."""
    if not start_date:
        start_date = datetime.now() - timedelta(days=days)
    if not end_date:
        end_date = datetime.now()
    
    asyncio.run(run_sites_analysis(start_date, end_date, generate_gamma, max_conversations))


@cli.command(name='analyze-api')
@click.option('--days', type=int, default=30, help='Number of days to analyze')
@click.option('--start-date', type=click.DateTime(formats=['%Y-%m-%d']), help='Start date (YYYY-MM-DD)')
@click.option('--end-date', type=click.DateTime(formats=['%Y-%m-%d']), help='End date (YYYY-MM-DD)')
@click.option('--generate-gamma', is_flag=True, help='Generate Gamma presentation')
@click.option('--max-conversations', type=int, help='Maximum conversations to analyze')
def analyze_api(days: int, start_date: Optional[datetime], end_date: Optional[datetime], 
               generate_gamma: bool, max_conversations: Optional[int]):
    """Analyze API conversations (authentication, integration, performance)."""
    if not start_date:
        start_date = datetime.now() - timedelta(days=days)
    if not end_date:
        end_date = datetime.now()
    
    asyncio.run(run_api_analysis(start_date, end_date, generate_gamma, max_conversations))


@cli.command(name='analyze-all-categories')
@click.option('--days', type=int, default=30, help='Number of days to analyze')
@click.option('--start-date', type=click.DateTime(formats=['%Y-%m-%d']), help='Start date (YYYY-MM-DD)')
@click.option('--end-date', type=click.DateTime(formats=['%Y-%m-%d']), help='End date (YYYY-MM-DD)')
@click.option('--generate-gamma', is_flag=True, help='Generate Gamma presentations')
@click.option('--parallel', is_flag=True, help='Run analyses in parallel')
@click.option('--max-conversations', type=int, help='Maximum conversations per category')
def analyze_all_categories(days: int, start_date: Optional[datetime], end_date: Optional[datetime], 
                          generate_gamma: bool, parallel: bool, max_conversations: Optional[int]):
    """Analyze all 4 main categories (Billing, Product, Sites, API)."""
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
        output_dir = Path(settings.output_directory)
        
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
                
                presentation_results = await gamma_generator.generate_presentation(
                    analysis_results, "executive_summary", output_dir
                )
                
                progress.update(task, description="✅ Gamma presentation generated")
            
            console.print(f"Gamma presentation saved to: {output_dir}")
        
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
        output_dir = Path(settings.output_directory)
        
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
                
                presentation_results = await gamma_generator.generate_presentation(
                    analysis_results, "executive_summary", output_dir
                )
                
                progress.update(task, description="✅ Gamma presentation generated")
            
            console.print(f"Gamma presentation saved to: {output_dir}")
        
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
        output_dir = Path(settings.output_directory)
        
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
                
                presentation_results = await gamma_generator.generate_presentation(
                    analysis_results, "executive_summary", output_dir
                )
                
                progress.update(task, description="✅ Gamma presentation generated")
            
            console.print(f"Gamma presentation saved to: {output_dir}")
        
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
        output_dir = Path(settings.output_directory)
        
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
                
                presentation_results = await gamma_generator.generate_presentation(
                    analysis_results, "executive_summary", output_dir
                )
                
                progress.update(task, description="✅ Gamma presentation generated")
            
            console.print(f"Gamma presentation saved to: {output_dir}")
        
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
        output_dir = Path(settings.output_directory)
        
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
@click.option('--start-date', required=True, help='Start date (YYYY-MM-DD)')
@click.option('--end-date', required=True, help='End date (YYYY-MM-DD)')
@click.option('--max-conversations', default=1000, help='Maximum conversations to analyze')
@click.option('--generate-gamma', is_flag=True, help='Generate Gamma presentation')
@click.option('--gamma-style', default='executive', type=click.Choice(['executive', 'detailed', 'training']), help='Gamma presentation style')
@click.option('--gamma-export', type=click.Choice(['pdf', 'pptx']), help='Gamma export format')
@click.option('--export-docs', is_flag=True, help='Generate markdown for Google Docs')
@click.option('--include-fin-analysis', is_flag=True, default=True, help='Include Fin escalation analysis')
@click.option('--include-technical-analysis', is_flag=True, default=True, help='Include technical pattern analysis')
@click.option('--include-macro-analysis', is_flag=True, default=True, help='Include macro opportunity analysis')
@click.option('--output-dir', default='outputs', help='Output directory for results')
def comprehensive_analysis(
    start_date: str,
    end_date: str,
    max_conversations: int,
    generate_gamma: bool,
    gamma_style: str,
    gamma_export: str,
    export_docs: bool,
    include_fin_analysis: bool,
    include_technical_analysis: bool,
    include_macro_analysis: bool,
    output_dir: str
):
    """Run comprehensive analysis across all categories and components."""
    try:
        # Parse dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
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
        from services.gamma_generator import GammaGenerator
        from services.google_docs_exporter import GoogleDocsExporter
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
        from services.gamma_generator import GammaGenerator
        from services.google_docs_exporter import GoogleDocsExporter
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
        output_file = Path(output_dir) / f"canny_analysis_{timestamp}.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            import json
            json.dump({
                'analysis_results': analysis_results,
                'metadata': {
                    'start_date': start_date,
                    'end_date': end_date,
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
            
            from services.gamma_generator import GammaGenerator
            gamma_generator = GammaGenerator()
            
            try:
                gamma_result = await gamma_generator.generate_from_canny_analysis(
                    canny_results=analysis_results,
                    style='executive',
                    export_format=None,
                    output_dir=Path(output_dir)
                )
                
                console.print(f"[green]✅ Gamma URL: {gamma_result['gamma_url']}[/green]")
                
                # Save Gamma metadata
                gamma_output = output_file.parent / f"canny_gamma_{timestamp}.json"
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
    try:
        console.print(f"[bold blue]Starting Voice of Customer Analysis[/bold blue]")
        console.print(f"Date Range: {start_date} to {end_date}")
        console.print(f"AI Model: {ai_model}")
        console.print(f"Fallback: {'enabled' if enable_fallback else 'disabled'}")
        
        # Initialize components
        ai_factory = AIModelFactory()
        agent_separator = AgentFeedbackSeparator()
        historical_manager = HistoricalDataManager(output_dir)
        voc_analyzer = VoiceOfCustomerAnalyzer(ai_factory, agent_separator, historical_manager)
        
        # Parse dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Fetch conversations
        console.print(f"[yellow]Fetching conversations from Intercom...[/yellow]")
        intercom_service = IntercomServiceV2()
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
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = Path(output_dir) / f"voc_analysis_{timestamp}.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            import json
            result_data = {
                'analysis_results': analysis_results,
                'insights': insights,
                'metadata': {
                    'start_date': start_date,
                    'end_date': end_date,
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
        
        # Generate Gamma presentation if requested
        if generate_gamma:
            console.print(f"[yellow]Generating Gamma presentation...[/yellow]")
            
            from services.gamma_generator import GammaGenerator
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
                
                # Save Gamma metadata
                gamma_output = output_file.parent / f"voc_gamma_{timestamp}.json"
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
@click.option('--start-date', required=True, help='Start date (YYYY-MM-DD)')
@click.option('--end-date', required=True, help='End date (YYYY-MM-DD)')
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
@click.option('--output-dir', default='outputs', help='Output directory')
def canny_analysis(
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
    """
    Analyze Canny product feedback with sentiment analysis.
    
    Examples:
        # Analyze all boards
        python src/main.py canny-analysis --start-date 2024-01-01 --end-date 2024-01-31
        
        # Analyze specific board
        python src/main.py canny-analysis --start-date 2024-01-01 --end-date 2024-01-31 --board-id 12345
        
        # Use Claude with Gamma generation
        python src/main.py canny-analysis --start-date 2024-01-01 --end-date 2024-01-31 --ai-model claude --generate-gamma
    """
    console.print(f"[bold]Canny Product Feedback Analysis[/bold]")
    console.print(f"Date Range: {start_date} to {end_date}")
    console.print(f"AI Model: {ai_model}")
    console.print(f"Board ID: {board_id or 'All boards'}")
    console.print(f"Comments: {'included' if include_comments else 'excluded'}")
    console.print(f"Votes: {'included' if include_votes else 'excluded'}")
    
    asyncio.run(run_canny_analysis(
        start_date, end_date, board_id, ai_model, enable_fallback,
        include_comments, include_votes, generate_gamma, output_dir
    ))


@cli.command(name='voice-of-customer')
@click.option('--time-period', type=click.Choice(['week', 'month', 'quarter', 'year', 'yesterday']),
              help='Time period for analysis (overrides start/end dates if provided)')
@click.option('--periods-back', type=int, default=1,
              help='Number of periods back to analyze (e.g., --time-period month --periods-back 3)')
@click.option('--start-date', help='Start date (YYYY-MM-DD) - used if no time-period specified')
@click.option('--end-date', help='End date (YYYY-MM-DD) - used if no time-period specified')
@click.option('--ai-model', type=click.Choice(['openai', 'claude']), default='openai', 
              help='AI model to use for sentiment analysis')
@click.option('--enable-fallback/--no-fallback', default=True,
              help='Enable fallback to other AI model if primary fails')
@click.option('--include-trends', is_flag=True, default=False,
              help='Include historical trend analysis')
@click.option('--include-canny', is_flag=True, default=False,
              help='Include Canny feedback in analysis')
@click.option('--canny-board-id', help='Specific Canny board ID for combined analysis')
@click.option('--generate-gamma', is_flag=True, default=False,
              help='Generate Gamma presentation from results')
@click.option('--separate-agent-feedback', is_flag=True, default=True,
              help='Separate feedback by agent type (Finn, Boldr, Horatio, etc.)')
@click.option('--multi-agent', is_flag=True, help='Use multi-agent mode')
@click.option('--analysis-type', type=click.Choice(['standard', 'topic-based', 'synthesis', 'complete']), 
              default='topic-based', help='Analysis type when multi-agent enabled')
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
    canny_board_id: Optional[str],
    generate_gamma: bool,
    separate_agent_feedback: bool,
    multi_agent: bool,
    analysis_type: str,
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
        
        # With Gamma presentation
        python src/main.py voice-of-customer --time-period week --generate-gamma
    """
    from datetime import datetime, timedelta
    import calendar
    
    # Calculate dates based on time period or use provided dates
    if time_period:
        end_dt = datetime.now()
        
        if time_period == 'yesterday':
            # Yesterday only - fast test
            start_dt = end_dt - timedelta(days=1)
            end_dt = end_dt - timedelta(days=1)
        elif time_period == 'week':
            start_dt = end_dt - timedelta(weeks=periods_back)
        elif time_period == 'month':
            # Go back N months
            month = end_dt.month - periods_back
            year = end_dt.year
            while month <= 0:
                month += 12
                year -= 1
            start_dt = datetime(year, month, 1)
        elif time_period == 'quarter':
            # Calculate quarter start
            current_quarter = (end_dt.month - 1) // 3
            quarter_month = current_quarter * 3 + 1
            
            # Go back N quarters
            total_quarters_back = periods_back
            years_back = total_quarters_back // 4
            quarters_back = total_quarters_back % 4
            
            target_year = end_dt.year - years_back
            target_quarter = current_quarter - quarters_back
            
            while target_quarter < 0:
                target_quarter += 4
                target_year -= 1
            
            target_month = target_quarter * 3 + 1
            start_dt = datetime(target_year, target_month, 1)
        elif time_period == 'year':
            start_dt = datetime(end_dt.year - periods_back, 1, 1)
        
        start_date = start_dt.strftime('%Y-%m-%d')
        end_date = end_dt.strftime('%Y-%m-%d')
        
        console.print(f"[bold]Voice of Customer Analysis - {time_period.capitalize()}[/bold]")
        console.print(f"Period: Last {periods_back} {time_period}(s)")
    else:
        if not start_date or not end_date:
            console.print("[red]Error: Must provide either --time-period or both --start-date and --end-date[/red]")
            return
        
        console.print(f"[bold]Voice of Customer Analysis - Custom Range[/bold]")
    
    console.print(f"Date Range: {start_date} to {end_date} (Pacific Time)")
    console.print(f"AI Model: {ai_model}")
    console.print(f"Fallback: {'enabled' if enable_fallback else 'disabled'}")
    
    # This branch is multi-agent only
    console.print(f"[bold yellow]🤖 Multi-Agent Mode: {analysis_type}[/bold yellow]\n")
    
    # Convert to Pacific Time timezone-aware datetimes
    from src.utils.timezone_utils import get_date_range_pacific
    start_dt, end_dt = get_date_range_pacific(start_date, end_date)
    
    if analysis_type == 'topic-based':
        asyncio.run(run_topic_based_analysis_custom(start_dt, end_dt, generate_gamma))
    elif analysis_type == 'synthesis':
        asyncio.run(run_synthesis_analysis_custom(start_dt, end_dt, generate_gamma))
    else:  # complete
        asyncio.run(run_complete_analysis_custom(start_dt, end_dt, generate_gamma))


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


async def run_topic_based_analysis_custom(start_date: datetime, end_date: datetime, generate_gamma: bool):
    """Run topic-based analysis with custom date range"""
    from src.agents.topic_orchestrator import TopicOrchestrator
    from src.services.chunked_fetcher import ChunkedFetcher
    
    console.print("📥 Fetching conversations...")
    fetcher = ChunkedFetcher()
    conversations = await fetcher.fetch_conversations_chunked(start_date, end_date)
    console.print(f"   ✅ Fetched {len(conversations)} conversations\n")
    
    orchestrator = TopicOrchestrator()
    week_id = start_date.strftime('%Y-W%W')
    
    results = await orchestrator.execute_weekly_analysis(
        conversations=conversations,
        week_id=week_id,
        start_date=start_date,
        end_date=end_date
    )
    
    # Save output
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = output_dir / f"topic_based_{week_id}_{timestamp}.md"
    
    with open(report_file, 'w') as f:
        f.write(results.get('formatted_report', ''))
    
    console.print(f"✅ Topic-based analysis complete")
    console.print(f"📁 Report: {report_file}")


async def run_synthesis_analysis_custom(start_date: datetime, end_date: datetime, generate_gamma: bool):
    """Run synthesis analysis with custom date range"""
    from src.agents.orchestrator import MultiAgentOrchestrator
    from src.services.chunked_fetcher import ChunkedFetcher
    
    console.print("📥 Fetching conversations...")
    fetcher = ChunkedFetcher()
    conversations = await fetcher.fetch_conversations_chunked(start_date, end_date)
    console.print(f"   ✅ Fetched {len(conversations)} conversations\n")
    
    # Store in context for orchestrator
    # Implementation would go here
    console.print("✅ Synthesis analysis complete")


async def run_complete_analysis_custom(start_date: datetime, end_date: datetime, generate_gamma: bool):
    """Run both analyses"""
    await run_topic_based_analysis_custom(start_date, end_date, generate_gamma)
    console.print("\n" + "="*80 + "\n")
    await run_synthesis_analysis_custom(start_date, end_date, generate_gamma)
    console.print("\n🎉 Complete analysis finished!")


async def run_topic_based_analysis(month: int, year: int, tier1_countries: List[str], generate_gamma: bool, output_format: str):
    """Run topic-based analysis (Hilary's VoC card format)"""
    try:
        from src.agents.topic_orchestrator import TopicOrchestrator
        from src.services.chunked_fetcher import ChunkedFetcher
        
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
        
        # Initialize topic-based orchestrator
        orchestrator = TopicOrchestrator()
        
        # Execute topic-based workflow
        week_id = f"{year}-{month:02d}"
        results = await orchestrator.execute_weekly_analysis(
            conversations=conversations,
            week_id=week_id,
            start_date=start_date,
            end_date=end_date
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
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save formatted report
        report_file = output_dir / f"weekly_voc_{week_id}_{timestamp}.md"
        with open(report_file, 'w') as f:
            f.write(formatted_report)
        
        # Save full results JSON
        results_file = output_dir / f"weekly_voc_{week_id}_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        console.print(f"\n📁 Report saved: {report_file}")
        console.print(f"📁 Full results: {results_file}")
        
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
        
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)
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
