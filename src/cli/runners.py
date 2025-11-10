
"""
Analysis Runners Module - Core analysis execution functions.

This module contains the actual implementation of analysis workflows,
separated from the CLI command interface for better modularity and testability.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.config.settings import settings
from src.models.analysis_models import AnalysisRequest, AnalysisMode
from src.services.intercom_sdk_service import IntercomSDKService
from src.services.metrics_calculator import MetricsCalculator
from src.services.openai_client import OpenAIClient
from src.services.gamma_client import GammaClient, GammaAPIError
from src.services.gamma_generator import GammaGenerator
from src.services.chunked_fetcher import ChunkedFetcher
from src.services.data_exporter import DataExporter
from src.services.query_builder import GeneralQueryService
from src.services.elt_pipeline import ELTPipeline
from src.services.orchestrator import AnalysisOrchestrator
from src.analyzers.voice_analyzer import VoiceAnalyzer
from src.analyzers.trend_analyzer import TrendAnalyzer
from src.analyzers.billing_analyzer import BillingAnalyzer
from src.analyzers.product_analyzer import ProductAnalyzer
from src.analyzers.sites_analyzer import SitesAnalyzer
from src.analyzers.api_analyzer import ApiAnalyzer
from src.analyzers.voice_of_customer_analyzer import VoiceOfCustomerAnalyzer
from src.analyzers.canny_analyzer import CannyAnalyzer
from src.services.canny_client import CannyClient
from src.services.canny_preprocessor import CannyPreprocessor
from src.services.ai_model_factory import AIModelFactory, AIModel
from src.services.agent_feedback_separator import AgentFeedbackSeparator
from src.agents.agent_performance_agent import AgentPerformanceAgent
from src.agents.base_agent import AgentContext
from src.agents.topic_orchestrator import TopicOrchestrator
from src.agents.orchestrator import MultiAgentOrchestrator
from src.services.test_data_generator import TestDataGenerator
from src.utils.time_utils import generate_descriptive_filename, detect_period_type
from src.utils.timezone_utils import get_date_range_pacific

console = Console()
logger = logging.getLogger(__name__)


async def run_voice_analysis(request: AnalysisRequest, generate_gamma: bool, output_format: str) -> Dict[str, Any]:
    """Run Voice of Customer analysis."""
    try:
        # Initialize services with async context manager for graceful cleanup
        async with IntercomSDKService() as intercom_service:
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
            
            return {
                'success': True,
                'results': results,
                'output_files': get_output_files(f"voice_analysis_{request.month}_{request.year}")
            }
        
    except Exception as e:
        logger.error(f"Voice analysis failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }


async def run_trend_analysis(request: AnalysisRequest, generate_gamma: bool, output_format: str) -> Dict[str, Any]:
    """Run trend analysis."""
    try:
        # Initialize services with async context manager for graceful cleanup
        async with IntercomSDKService() as intercom_service:
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
            
            return {
                'success': True,
                'results': results,
                'output_files': get_output_files(f"trend_analysis_{request.start_date}_{request.end_date}")
            }
        
    except Exception as e:
        logger.error(f"Trend analysis failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }


async def run_custom_analysis(request: AnalysisRequest, generate_gamma: bool, output_format: str) -> Dict[str, Any]:
    """Run custom analysis."""
    try:
        # Initialize services with async context manager for graceful cleanup
        async with IntercomSDKService() as intercom_service:
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
            
            return {
                'success': True,
                'results': results,
                'output_files': get_output_files(f"custom_analysis_{request.start_date}_{request.end_date}")
            }
        
    except Exception as e:
        logger.error(f"Custom analysis failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }


async def run_data_export(start_date: datetime, end_date: datetime, export_format: str, max_pages: Optional[int], include_metrics: bool) -> Dict[str, Any]:
    """Run data export."""
    try:
        # Initialize services with async context manager for graceful cleanup
        async with IntercomSDKService() as intercom_service:
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
            
            return {
                'success': True,
                'conversations_count': len(conversations),
                'export_results': export_results
            }
        
    except Exception as e:
        logger.error(f"Data export failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }


async def run_technical_analysis_v2(start_date: datetime, end_date: datetime, max_pages: Optional[int], generate_ai_report: bool) -> Dict[str, Any]:
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
            return {
                'success': True,
                'conversations_count': 0,
                'message': 'No conversations found'
            }
        
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
                from src.config.prompts import PromptTemplates
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
        
        return {
            'success': True,
            'conversations_count': stats['conversations_count'],
            'csv_path': csv_path,
            'ai_report_path': report_path if generate_ai_report else None
        }
        
    except Exception as e:
        logger.error(f"Technical analysis failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }


async def run_agent_performance_analysis(
    agent: str,
    start_date: datetime,
    end_date: datetime,
    focus_categories: Optional[str] = None,
    generate_gamma: bool = False,
    individual_breakdown: bool = False,
    analyze_troubleshooting: bool = False
) -> Dict[str, Any]:
    """Run comprehensive agent performance analysis with optional Gamma generation."""
    try:
        from src.services.chunked_fetcher import ChunkedFetcher
        from src.agents.agent_performance_agent import AgentPerformanceAgent
        from src.agents.base_agent import AgentContext
        from src.services.gamma_generator import GammaGenerator
        from src.services.gamma_client import GammaAPIError
        from pathlib import Path
        
        agent_name = {'horatio': 'Horatio', 'boldr': 'Boldr', 'escalated': 'Senior Staff'}.get(agent, agent)
        
        console.print(f"\n📊 [bold cyan]{agent_name} Performance Analysis[/bold cyan]")
        console.print(f"Date Range: {start_date.date()} to {end_date.date()}")
        if focus_categories:
            console.print(f"Focus: {focus_categories}\n")
        
        # Fetch conversations
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
            return {
                'success': False,
                'error': f"No conversations found for {agent_name}",
                'agent_name': agent_name
            }
        
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
            return {
                'success': False,
                'error': result.error_message
            }
        
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
                console.print(f"[bold]🤖 AI Insights:[/bold]")
                console.print(data['llm_insights'])
                console.print()
        
        # Generate Gamma presentation if requested
        if generate_gamma:
            console.print("🎨 Generating Gamma presentation...")
            try:
                gamma_generator = GammaGenerator()
                gamma_result = await gamma_generator.generate_from_agent_performance(
                    analysis_results=data,
                    agent_name=agent_name,
                    start_date=start_date,
                    end_date=end_date,
                    output_dir=Path("outputs")
                )
                
                if gamma_result.get('gamma_url'):
                    console.print(f"\n🎉 [bold green]Gamma presentation generated![/bold green]")
                    console.print(f"📊 Gamma URL: {gamma_result['gamma_url']}")
                    console.print(f"💳 Credits used: {gamma_result.get('credits_used', 0)}")
                else:
                    console.print("[yellow]⚠️  Gamma generation completed but no URL returned[/yellow]")
                    
            except GammaAPIError as e:
                console.print(f"[yellow]Warning: Gamma generation failed: {e}[/yellow]")
                console.print("[yellow]Continuing without Gamma presentation...[/yellow]")
            except Exception as e:
                console.print(f"[yellow]Warning: Unexpected error during Gamma generation: {e}[/yellow]")
                console.print("[yellow]Continuing without Gamma presentation...[/yellow]")
        
        console.print(f"\nDetailed results saved to: {Path('outputs')}")
        
        return {
            'success': True,
            'results': data,
            'agent_name': agent_name,
            'conversations_analyzed': len(agent_conversations)
        }
        
    except Exception as e:
        logger.error(f"Agent performance analysis failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }


async def run_comprehensive_analysis(orchestrator: AnalysisOrchestrator, start_date: datetime, end_date: datetime, 
                                   options: Dict[str, Any], output_path: Path, timestamp: str) -> Dict[str, Any]:
    """Run comprehensive analysis across all categories and components."""
    try:
        # Run analysis
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Running comprehensive analysis...", total=None)
            
            results = await orchestrator.run_comprehensive_analysis(
                start_date=start_date,
                end_date=end_date,
                options=options
            )
            
            progress.update(task, description="✅ Analysis completed")
        
        # Save results
        results_file = output_path / f"comprehensive_analysis_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Display results
        console.print(f"\n[bold green]Comprehensive Analysis Completed![/bold green]")
        console.print(f"Total conversations: {results.get('total_conversations', 0):,}")
        
        # Display category results
        category_results = results.get('category_results', {})
        if category_results:
            console.print(f"\n[bold]Category Analysis Results:[/bold]")
            for category, result in category_results.items():
                if result.get('success'):
                    console.print(f"  ✓ {category.title()}: {result.get('conversations_analyzed', 0)} conversations")
                else:
                    console.print(f"  ✗ {category.title()}: Error - {result.get('error', 'Unknown error')}")
        
        # Display synthesis results
        synthesis_results = results.get('synthesis_results', {})
        if synthesis_results:
            console.print(f"\n[bold]Cross-Category Insights:[/bold]")
            executive_summary = synthesis_results.get('executive_summary', {})
            key_findings = executive_summary.get('overview', {}).get('key_findings', [])
            for finding in key_findings[:3]:  # Show top 3 findings
                console.print(f"  • {finding}")
        
        # Display Gamma presentation info
        if options.get('generate_gamma_presentation') and results.get('gamma_presentation'):
            console.print(f"\n[bold green]Gamma presentation generated![/bold green]")
            console.print(f"Results saved to: {results_file}")
        
        console.print(f"\nDetailed results saved to: {results_file}")
        
        return {
            'success': True,
            'results': results,
            'results_file': str(results_file),
            'total_conversations': results.get('total_conversations', 0)
        }
        
    except Exception as e:
        logger.error(f"Comprehensive analysis failed: {e}")
        return {
            'success': False,
            'error': str(e)
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
) -> Dict[str, Any]:
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
            return {
                'success': False,
                'error': 'No Canny posts found'
            }
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
        output_filename = generate_descriptive_filename(
            'Canny_Analysis', start_date, end_date, file_type='json'
        )
        output_file = Path(output_dir) / output_filename
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
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
        
        return {
            'success': True,
            'output_file': str(output_file),
            'total_posts': len(posts),
            'analysis_results': analysis_results
        }
        
    except Exception as e:
        logger.error(f"Canny analysis failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }


# Helper/Display Functions (stubs - need implementation)

def display_voice_results(results: Any):
    """Display voice analysis results."""
    console.print("[bold green]Voice Analysis Results:[/bold green]")
    console.print(results)


def display_trend_results(results: Any):
    """Display trend analysis results."""
    console.print("[bold green]Trend Analysis Results:[/bold green]")
    console.print(results)


def display_custom_results(results: Any):
    """Display custom analysis results."""
    console.print("[bold green]Custom Analysis Results:[/bold green]")
    console.print(results)


def _display_individual_breakdown(data: Dict[str, Any], agent_name: str):
    """Display individual agent breakdown."""
    console.print(f"\n[bold]Individual {agent_name} Agent Breakdown:[/bold]")
    
    agents = data.get('agents', [])
    console.print(f"Total agents: {len(agents)}\n")
    
    for agent in agents[:10]:  # Show top 10
        console.print(f"  {agent.get('name', 'Unknown')}: {agent.get('conversations', 0)} conversations")


def save_json_output(results: Any, filename: str):
    """Save results as JSON."""
    from src.cli.utils import save_outputs
    save_outputs(results, filename, output_format='json')


def save_markdown_output(results: Any, filename: str):
    """Save results as Markdown."""
    from src.cli.utils import save_outputs
    save_outputs(results, filename, output_format='markdown')


def get_output_files(filename: str) -> List[str]:
    """Get list of output files for a given base filename."""
    output_dir = Path(settings.output_directory)
    matches = list(output_dir.glob(f"{filename}*"))
    return [str(m) for m in matches]


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
    output_dir: str,
    test_mode: bool,
    test_data_count: int,
    audit_trail: bool
) -> Dict[str, Any]:
    """Run VoC analysis (topic-based)."""
    console.print("[yellow]VoC topic-based analysis not yet implemented in CLI module[/yellow]")
    return {'success': False, 'error': 'Not implemented'}


async def run_topic_based_analysis(
    month: int,
    year: int,
    tier1_list: List[str],
    generate_gamma: bool,
    output_format: str
) -> Dict[str, Any]:
    """Run topic-based multi-agent analysis."""
    console.print("[yellow]Topic-based analysis not yet implemented in CLI module[/yellow]")
    return {'success': False, 'error': 'Not implemented'}


async def run_synthesis_analysis(
    month: int,
    year: int,
    tier1_list: List[str],
    generate_gamma: bool,
    output_format: str
) -> Dict[str, Any]:
    """Run synthesis multi-agent analysis."""
    console.print("[yellow]Synthesis analysis not yet implemented in CLI module[/yellow]")
    return {'success': False, 'error': 'Not implemented'}


async def run_synthesis_analysis_custom(
    start_dt: datetime,
    end_dt: datetime,
    generate_gamma: bool,
    audit_trail: bool
) -> Dict[str, Any]:
    """Run custom synthesis analysis."""
    console.print("[yellow]Custom synthesis analysis not yet implemented in CLI module[/yellow]")
    return {'success': False, 'error': 'Not implemented'}


async def run_complete_multi_agent_analysis(
    month: int,
    year: int,
    tier1_list: List[str],
    generate_gamma: bool,
    output_format: str
) -> Dict[str, Any]:
    """Run complete multi-agent analysis."""
    console.print("[yellow]Complete multi-agent analysis not yet implemented in CLI module[/yellow]")
    return {'success': False, 'error': 'Not implemented'}


async def run_complete_analysis_custom(
    start_dt: datetime,
    end_dt: datetime,
    generate_gamma: bool,
    audit_trail: bool
) -> Dict[str, Any]:
    """Run custom complete analysis."""
    console.print("[yellow]Custom complete analysis not yet implemented in CLI module[/yellow]")
    return {'success': False, 'error': 'Not implemented'}
