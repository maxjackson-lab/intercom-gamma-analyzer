"""
Main CLI application for Intercom to Gamma analysis tool.
"""

import asyncio
import logging
import sys
from datetime import datetime, date
from typing import List, Optional
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel

# Add src to path for imports
sys.path.append(str(Path(__file__).parent))

from config.settings import settings
from services.intercom_service import IntercomService
from services.metrics_calculator import MetricsCalculator
from services.openai_client import OpenAIClient
from services.gamma_client import GammaClient
from services.data_exporter import DataExporter
from services.query_builder import QueryBuilder, GeneralQueryService
from analyzers.voice_analyzer import VoiceAnalyzer
from analyzers.trend_analyzer import TrendAnalyzer
from models.analysis_models import AnalysisRequest, AnalysisMode
from utils.logger import setup_logging

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
def voice(month: int, year: int, tier1_countries: Optional[str], generate_gamma: bool, output_format: str):
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
    
    # Create analysis request
    request = AnalysisRequest(
        mode=AnalysisMode.VOICE_OF_CUSTOMER,
        month=month,
        year=year,
        tier1_countries=tier1_list
    )
    
    # Run analysis
    asyncio.run(run_voice_analysis(request, generate_gamma, output_format))


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
    
    # Parse dates
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
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
    
    # Parse dates
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
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
    
    # Parse dates
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
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


@cli.command()
def query-suggestions():
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


if __name__ == "__main__":
    cli()
