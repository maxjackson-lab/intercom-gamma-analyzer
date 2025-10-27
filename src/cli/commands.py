"""
CLI Commands Module - Individual command implementations for the Intercom analysis tool.

This module contains all the CLI command implementations, organized by functionality.
Each command function handles the specific logic for that command type.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel

from src.config.settings import settings
from src.models.analysis_models import AnalysisRequest, AnalysisMode
from src.utils.time_utils import detect_period_type
from src.utils.timezone_utils import get_date_range_pacific
from src.services.audit_trail import AuditTrail

console = Console()
logger = logging.getLogger(__name__)


async def voice_analysis(
    month: int,
    year: int,
    tier1_countries: Optional[List[str]],
    generate_gamma: bool,
    output_format: str,
    multi_agent: bool,
    analysis_type: str,
    ai_model: Optional[str]
) -> Dict[str, Any]:
    """Generate Voice of Customer analysis for monthly executive reports."""
    
    # Set AI model if specified
    if ai_model:
        import os
        os.environ['AI_MODEL'] = ai_model
        console.print(f"[cyan]Using AI model: {ai_model}[/cyan]")
    
    # Parse tier1 countries
    tier1_list = tier1_countries or settings.default_tier1_countries
    
    console.print(f"[bold green]Voice of Customer Analysis[/bold green]")
    console.print(f"Month: {month}/{year}")
    console.print(f"Tier 1 Countries: {', '.join(tier1_list)}")
    
    # This branch is multi-agent only
    if not multi_agent:
        console.print("[yellow]ℹ️  Note: This branch uses multi-agent by default. Use main branch for single-agent.[/yellow]")
        analysis_type = analysis_type or 'topic-based'
    
    if analysis_type == 'topic-based':
        console.print("[bold yellow]📋 Topic-Based Multi-Agent Analysis[/bold yellow]")
        console.print("Format: Hilary's VoC Cards - Per-topic sentiment with examples\n")
        return await run_topic_based_analysis(month, year, tier1_list, generate_gamma, output_format)
    elif analysis_type == 'synthesis':
        console.print("[bold yellow]🧠 Synthesis Multi-Agent Analysis[/bold yellow]")
        console.print("Format: Cross-category insights and strategic recommendations\n")
        return await run_synthesis_analysis(month, year, tier1_list, generate_gamma, output_format)
    else:  # complete
        console.print("[bold yellow]🎯 Complete Multi-Agent Analysis[/bold yellow]")
        console.print("Includes: Topic-based cards + Synthesis insights\n")
        return await run_complete_multi_agent_analysis(month, year, tier1_list, generate_gamma, output_format)


async def trend_analysis(
    start_date: str,
    end_date: str,
    focus_areas: Optional[List[str]],
    custom_prompt: Optional[str],
    generate_gamma: bool,
    output_format: str
) -> Dict[str, Any]:
    """Generate general purpose trend analysis for any time period."""
    
    # Parse dates
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        console.print("[red]Error: Invalid date format. Use YYYY-MM-DD[/red]")
        raise ValueError("Invalid date format")
    
    console.print(f"[bold green]Trend Analysis[/bold green]")
    console.print(f"Date Range: {start_date} to {end_date}")
    console.print(f"Focus Areas: {', '.join(focus_areas) if focus_areas else 'General trends'}")
    
    # Create analysis request
    request = AnalysisRequest(
        mode=AnalysisMode.TREND_ANALYSIS,
        start_date=start_dt,
        end_date=end_dt,
        focus_areas=focus_areas or [],
        custom_instructions=custom_prompt
    )
    
    return await run_trend_analysis(request, generate_gamma, output_format)


async def custom_analysis(
    prompt_file: str,
    start_date: str,
    end_date: str,
    generate_gamma: bool,
    output_format: str
) -> Dict[str, Any]:
    """Generate analysis with custom prompt."""
    
    # Read custom prompt
    try:
        with open(prompt_file, 'r') as f:
            custom_prompt = f.read()
    except FileNotFoundError:
        console.print(f"[red]Error: Prompt file not found: {prompt_file}[/red]")
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
    
    # Parse dates
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        console.print("[red]Error: Invalid date format. Use YYYY-MM-DD[/red]")
        raise ValueError("Invalid date format")
    
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
    
    return await run_custom_analysis(request, generate_gamma, output_format)


async def data_export(
    start_date: str,
    end_date: str,
    export_format: str,
    max_pages: Optional[int],
    include_metrics: bool
) -> Dict[str, Any]:
    """Export raw conversation data to spreadsheets and other formats."""
    
    # Parse dates
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        console.print("[red]Error: Invalid date format. Use YYYY-MM-DD[/red]")
        raise ValueError("Invalid date format")
    
    console.print(f"[bold green]Data Export[/bold green]")
    console.print(f"Date Range: {start_date} to {end_date}")
    console.print(f"Export Format: {export_format}")
    
    return await run_data_export(start_dt, end_dt, export_format, max_pages, include_metrics)


async def technical_analysis(
    days: int,
    start_date: Optional[str],
    end_date: Optional[str],
    max_pages: Optional[int],
    generate_ai_report: bool
) -> Dict[str, Any]:
    """Analyze technical troubleshooting patterns in Intercom conversations."""
    
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
    
    return await run_technical_analysis_v2(start_dt, end_dt, max_pages, generate_ai_report)


async def agent_performance(
    agent: str,
    individual_breakdown: bool,
    time_period: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
    focus_categories: Optional[str],
    generate_gamma: bool,
    analyze_troubleshooting: bool = False
) -> Dict[str, Any]:
    """Analyze support agent/team performance with operational metrics."""
    
    from datetime import timedelta
    
    # Calculate dates
    if time_period:
        end_dt = datetime.now()
        if time_period == 'week':
            start_dt = end_dt - timedelta(weeks=1)
        elif time_period == 'month':
            start_dt = end_dt - timedelta(days=30)
        elif time_period == '6-weeks':
            start_dt = end_dt - timedelta(weeks=6)
        elif time_period == 'quarter':
            start_dt = end_dt - timedelta(days=90)
        
        start_date = start_dt.strftime('%Y-%m-%d')
        end_date = end_dt.strftime('%Y-%m-%d')
    else:
        if not start_date or not end_date:
            raise ValueError("Provide either --time-period or both --start-date and --end-date")
    
    agent_name = {'horatio': 'Horatio', 'boldr': 'Boldr', 'escalated': 'Senior Staff'}.get(agent, agent)
    
    console.print(f"[bold green]{agent_name} Performance Analysis[/bold green]")
    console.print(f"Date Range: {start_date} to {end_date}")
    if individual_breakdown:
        console.print("[cyan]Mode: Individual Agent Breakdown with Taxonomy Analysis[/cyan]")
    if focus_categories:
        console.print(f"Focus: {focus_categories}")
    
    # Convert string dates to datetime objects
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    return await run_agent_performance_analysis(
        agent, start_dt, end_dt, focus_categories, generate_gamma, 
        individual_breakdown, analyze_troubleshooting
    )


async def comprehensive_analysis(
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
) -> Dict[str, Any]:
    """Run comprehensive analysis across all categories and components."""
    
    # Parse dates
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        console.print("[red]Error: Invalid date format. Use YYYY-MM-DD[/red]")
        raise ValueError("Invalid date format")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    console.print(f"[bold blue]Starting Comprehensive Analysis[/bold blue]")
    console.print(f"Date range: {start_date} to {end_date}")
    console.print(f"Max conversations: {max_conversations}")
    console.print(f"Output directory: {output_dir}")
    
    # Initialize orchestrator
    from src.services.orchestrator import AnalysisOrchestrator
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
    
    return await run_comprehensive_analysis(orchestrator, start_dt, end_dt, options, output_path, timestamp)


async def voice_of_customer(
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
    test_mode: bool,
    test_data_count: int,
    verbose: bool,
    separate_agent_feedback: bool,
    multi_agent: bool,
    analysis_type: str,
    audit_trail: bool,
    output_dir: str
) -> Dict[str, Any]:
    """Generate Voice of Customer sentiment analysis."""
    
    from datetime import timedelta
    import calendar
    import os
    
    # Calculate dates based on time period or use provided dates
    if time_period:
        end_dt = datetime.now()
        
        if time_period == 'yesterday':
            start_dt = end_dt - timedelta(days=1)
            end_dt = end_dt - timedelta(days=1)
        elif time_period == 'week':
            start_dt = end_dt - timedelta(weeks=periods_back)
        elif time_period == 'month':
            month = end_dt.month - periods_back
            year = end_dt.year
            while month <= 0:
                month += 12
                year -= 1
            start_dt = datetime(year, month, 1)
        elif time_period == 'quarter':
            current_quarter = (end_dt.month - 1) // 3
            quarter_month = current_quarter * 3 + 1
            
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
            raise ValueError("Must provide either --time-period or both --start-date and --end-date")
        
        console.print(f"[bold]Voice of Customer Analysis - Custom Range[/bold]")
    
    console.print(f"Date Range: {start_date} to {end_date} (Pacific Time)")
    console.print(f"AI Model: {ai_model}")
    console.print(f"Fallback: {'enabled' if enable_fallback else 'disabled'}")
    
    # Enable verbose logging if requested
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        for module in ['agents', 'services', 'src.agents', 'src.services']:
            logging.getLogger(module).setLevel(logging.DEBUG)
        console.print(f"[yellow]🔍 Verbose Logging: ENABLED (DEBUG level)[/yellow]")
    
    # Test mode indication
    if test_mode:
        console.print(f"[yellow]🧪 Test Mode: ENABLED ({test_data_count} mock conversations)[/yellow]")
    
    # Set AI model if specified
    if ai_model:
        os.environ['AI_MODEL'] = ai_model
        console.print(f"[cyan]🤖 AI Model: {ai_model}[/cyan]")
    
    console.print(f"[bold yellow]🤖 Multi-Agent Mode: {analysis_type}[/bold yellow]\n")
    
    # Convert to Pacific Time timezone-aware datetimes
    start_dt, end_dt = get_date_range_pacific(start_date, end_date)
    
    if analysis_type == 'topic-based':
        return await run_voc_analysis(
            start_date, end_date, ai_model, enable_fallback, include_trends,
            include_canny, canny_board_id, generate_gamma, separate_agent_feedback,
            output_dir, test_mode, test_data_count, audit_trail
        )
    elif analysis_type == 'synthesis':
        return await run_synthesis_analysis_custom(start_dt, end_dt, generate_gamma, audit_trail)
    else:  # complete
        return await run_complete_analysis_custom(start_dt, end_dt, generate_gamma, audit_trail)


async def canny_analysis(
    start_date: str,
    end_date: str,
    board_id: Optional[str],
    ai_model: str,
    enable_fallback: bool,
    include_comments: bool,
    include_votes: bool,
    generate_gamma: bool,
    output_dir: str
) -> Dict[str, Any]:
    """Analyze Canny product feedback with sentiment analysis."""
    
    console.print(f"[bold]Canny Product Feedback Analysis[/bold]")
    console.print(f"Date Range: {start_date} to {end_date}")
    console.print(f"AI Model: {ai_model}")
    console.print(f"Board ID: {board_id or 'All boards'}")
    console.print(f"Comments: {'included' if include_comments else 'excluded'}")
    console.print(f"Votes: {'included' if include_votes else 'excluded'}")
    
    return await run_canny_analysis(
        start_date, end_date, board_id, ai_model, enable_fallback,
        include_comments, include_votes, generate_gamma, output_dir
   )