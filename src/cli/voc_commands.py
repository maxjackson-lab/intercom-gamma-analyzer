"""
Voice of Customer command implementations.

Extracted from src/main.py during Phase 1.4 of the CLI refactor so that
src/main.py only hosts the Click decorators while the async logic lives
in dedicated modules.

This module contains the flagship multi-agent VoC pipeline and comprehensive
analysis commands, along with their supporting helper functions.
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.progress import Progress, SpinnerColumn, TextColumn
from src.agents.base_agent import AgentContext
from src.cli.utils import console
from src.cli.voc_shared import (
    fetch_canny_conversations_from_warehouse,
    fetch_conversations_for_range,
    run_voc_narrative_analysis,
)
from src.services.strategies import ComprehensiveStrategy
from src.services.unified_orchestrator import UnifiedOrchestrator


async def run_topic_based_analysis_custom(
    start_date: datetime,
    end_date: datetime,
    generate_gamma: bool,
    test_mode: bool = False,
    test_data_count: str = "100",
    audit_trail: bool = False,
    digest_mode: bool = False,
    detail_level: str = "standard",  # New flag: standard, deep, comprehensive
    orchestrator_cls=None,
    mode_label: str = "Topic-based analysis",
    output_slug: str = "topic_based",
    extra_conversations: Optional[List[Dict[str, Any]]] = None,
    legacy_mode: bool = False
):
    """Run topic-based analysis with custom date range"""
    try:
        # 🔧 ENABLE CONSOLE RECORDING (capture ALL output to .log file!)
        # This ensures users have complete logs even if SSE disconnects
        console.record = True

        if legacy_mode:
            if test_mode:
                console.print("[yellow]⚠️ Legacy mode is unavailable in test mode. Continuing with standard pipeline.[/yellow]")
            else:
                week_id = start_date.strftime('%Y-W%W')
                await run_legacy_topic_analysis(
                    start_date=start_date,
                    end_date=end_date,
                    week_id=week_id,
                    generate_gamma=generate_gamma,
                    digest_mode=digest_mode
                )
                return

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

        from src.services.audit_trail import AuditTrail
        from src.utils.time_utils import detect_period_type

        # Initialize audit trail if enabled
        audit = None
        if audit_trail:
            from src.utils.output_manager import get_output_directory
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

        if extra_conversations:
            console.print(
                f"[cyan]Including {len(extra_conversations)} supplemental conversations (e.g., Canny feedback).[/cyan]"
            )
            conversations.extend(extra_conversations)

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

        # Initialize Unified Orchestrator with VoC Strategy
        from src.services.strategies.voc_strategy import VoiceOfCustomerStrategy
        from src.services.unified_orchestrator import UnifiedOrchestrator
        
        strategy = VoiceOfCustomerStrategy(
            audit_trail=audit, 
            execution_monitor=monitor
        )
        orchestrator = UnifiedOrchestrator(strategy=strategy)
        
        week_id = start_date.strftime('%Y-W%W')
        
        # Create AgentContext
        context = AgentContext(
            analysis_id=f"voc_{week_id}",
            analysis_type="voc",
            start_date=start_date,
            end_date=end_date,
            conversations=conversations,
            metadata={
                'week_id': week_id,
                'period_type': period_type,
                'period_label': period_label,
                'digest_mode': digest_mode,
                'detail_level': detail_level,
                'options': {} 
            }
        )

        # Execute
        agent_result = await orchestrator.execute(context)
        
        if not agent_result.success:
             console.print(f"[red]Analysis failed: {agent_result.error_message}[/red]")
             if not agent_result.data:
                 return

        results = agent_result.data

        # Save output
        from src.utils.output_manager import get_output_file_path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = get_output_file_path(f"{output_slug}_{week_id}_{timestamp}.md")
        output_parent_dir = report_file.parent

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

        console.print(f"✅ {mode_label} complete")
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
                        url_file = output_parent_dir / url_filename
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


async def run_synthesis_analysis_custom(
    start_date: datetime,
    end_date: datetime,
    generate_gamma: bool,
    audit_trail: bool = False,
    extra_conversations: Optional[List[Dict[str, Any]]] = None
):
    """Run synthesis-focused VoC narrative using TopicOrchestrator + NarrativeFormatter."""
    from src.agents.topic_orchestrator_v2 import TopicOrchestratorV2

    await run_voc_narrative_analysis(
        start_date,
        end_date,
        generate_gamma=generate_gamma,
        audit_trail=audit_trail,
        digest_mode=False,
        orchestrator_cls=TopicOrchestratorV2,
        analysis_slug="voc_synthesis",
        analysis_mode="synthesis",
        include_synthesis=True,
        extra_conversations=extra_conversations
    )


async def run_complete_analysis_custom(
    start_date: datetime,
    end_date: datetime,
    generate_gamma: bool,
    audit_trail: bool = False,
    digest_mode: bool = False,
    extra_conversations: Optional[List[Dict[str, Any]]] = None
):
    """Run complete VoC analysis (topic + synthesis) through a unified NarrativeFormatter pass."""
    from src.agents.topic_orchestrator import TopicOrchestrator

    await run_voc_narrative_analysis(
        start_date,
        end_date,
        generate_gamma=generate_gamma,
        audit_trail=audit_trail,
        digest_mode=digest_mode,
        orchestrator_cls=TopicOrchestrator,
        analysis_slug="voc_complete",
        analysis_mode="complete",
        include_synthesis=True,
        extra_conversations=extra_conversations
    )


async def run_legacy_topic_analysis(
    start_date: datetime,
    end_date: datetime,
    week_id: str,
    generate_gamma: bool,
    digest_mode: bool = False,
) -> Dict[str, Any]:
    """
    Execute the original MultiAgent workflow (Data → Category → Sentiment → Insight → Presentation).
    """
    console.print("\n[cyan]🕰️ Legacy Mode: Running original Hilary topic workflow (MultiAgentStrategy)[/cyan]")
    console.print("[dim]This path replays the five-agent V1 pipeline for comparison and regression checks.[/dim]\n")

    from src.agents.orchestrator import MultiAgentOrchestrator
    from src.utils.output_manager import get_output_file_path

    orchestrator = MultiAgentOrchestrator()
    results = await orchestrator.execute_analysis(
        analysis_type="voc_legacy_topic_cards",
        start_date=start_date,
        end_date=end_date,
        generate_gamma=generate_gamma,
        metadata={'digest_mode': digest_mode}
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    markdown_file = get_output_file_path(f"voc_legacy_{week_id}_{timestamp}.md")
    json_file = get_output_file_path(f"voc_legacy_{week_id}_{timestamp}.json")

    presentation_content = (
        results.get('agent_results', {})
              .get('PresentationAgent', {})
              .get('data', {})
              .get('presentation_content')
    )

    if not presentation_content:
        summary = results.get('summary', {})
        lines = [
            "# Legacy Hilary Report (Summary)\n",
            f"- Total Agents: {summary.get('total_agents', 'N/A')}",
            f"- Successful Agents: {summary.get('successful_agents', 'N/A')}",
            f"- Average Confidence: {summary.get('average_confidence', 'N/A')}",
            "",
            "## Agent Status",
        ]
        for agent_name, agent_result in (results.get('agent_results') or {}).items():
            status = "✅" if agent_result.get('success') else "⚠️"
            confidence = agent_result.get('confidence')
            confidence_str = f"{confidence:.2f}" if isinstance(confidence, (int, float)) else "N/A"
            lines.append(f"- {status} {agent_name} (confidence {confidence_str})")
        lines.append("")
        lines.append("*(Legacy pipeline executed without PresentationAgent output; showing summary instead.)*")
        presentation_body = "\n".join(lines)
    else:
        presentation_body = presentation_content

    with open(markdown_file, 'w') as f:
        f.write(presentation_body)

    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    console.print(f"📁 Legacy markdown saved to: {markdown_file}")
    console.print(f"📁 Workflow JSON saved to: {json_file}")
    console.print("✅ Legacy pipeline complete\n")

    return results


async def run_voice_of_customer_analysis(
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
    analysis_type: str,
    audit_trail: bool,
    output_dir: str,
    digest_mode: bool,
    enable_correlation_analysis: Optional[bool],
    enable_quality_insights: Optional[bool],
    enable_churn_detection: Optional[bool],
    enable_confidence_meta: Optional[bool],
    enable_subtopic_detection: Optional[bool],
    enable_topic_sentiment: Optional[bool],
    enable_topic_examples: Optional[bool],
    enable_fin_analysis: Optional[bool],
    enable_bpo_analysis: Optional[bool],
    enable_trend_analysis: Optional[bool],
    legacy_mode: bool,
    detail_level: str = "standard"
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

        # Topic-based Hilary cards (TopicOrchestrator workflow)
        python src/main.py voice-of-customer --time-period week --multi-agent --analysis-type topic-based

        # Narrative V2 weekly story (TopicOrchestratorV2 + NarrativeFormatterAgent)
        python src/main.py voice-of-customer --time-period week --multi-agent --analysis-type narrative-v2

        # Synthesis-only strategic insights
        python src/main.py voice-of-customer --time-period week --multi-agent --analysis-type synthesis

        # Complete dual-format output with digest (exec sanity check)
        python src/main.py voice-of-customer --time-period week --multi-agent --analysis-type complete --digest-mode

    Notes:
        - The >31 day and >90 day custom range checks emit warnings by default. Set
          VOC_STRICT_DATE_LIMITS=1 to convert the 90-day warning into a hard error.
    """
    from src.config.modes import get_analysis_mode_config
    from src.utils.time_utils import calculate_date_range, format_date_range_for_display
    from src.utils.timezone_utils import get_date_range_pacific

    config = get_analysis_mode_config()
    feature_overrides = {
        'enable_correlation_analysis': enable_correlation_analysis,
        'enable_quality_insights': enable_quality_insights,
        'enable_churn_detection': enable_churn_detection,
        'enable_confidence_meta': enable_confidence_meta,
        'enable_subtopic_detection': enable_subtopic_detection,
        'enable_topic_sentiment': enable_topic_sentiment,
        'enable_topic_examples': enable_topic_examples,
        'enable_fin_analysis': enable_fin_analysis,
        'enable_bpo_analysis': enable_bpo_analysis,
        'enable_trends': enable_trend_analysis if enable_trend_analysis is not None else (True if include_trends else None),
    }
    applied_overrides: List[str] = []

    try:
        for feature, value in feature_overrides.items():
            if value is not None:
                config.set_feature_override(feature, value)
                applied_overrides.append(feature)

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
                days_span = (end_dt - start_dt).days
                strict_limits_enabled = os.getenv('VOC_STRICT_DATE_LIMITS', '').lower() in ('1', 'true', 'yes')
                if days_span > 31:
                    console.print(f"[yellow]⚠️  Custom date range spans {days_span} days (> 31 days). This may take longer to process and could hit Intercom API limits.[/yellow]")
                if days_span > 90:
                    warning_msg = f"Date range too large ({days_span} days). Consider using --time-period month --periods-back 3 instead."
                    if strict_limits_enabled:
                        console.print(f"[red]❌ {warning_msg} (VOC_STRICT_DATE_LIMITS enforced)[/red]")
                        return
                    console.print(f"[red]⚠️  {warning_msg}[/red]")
                console.print(f"[cyan]📅 Custom Date Range: {start_date} to {end_date} ({days_span} days)[/cyan]")
                
                console.print("[dim]ℹ️  Intercom Search API has a 10,000 conversation limit per request.[/dim]")
                console.print("[dim]ℹ️  Large ranges are chunked daily to avoid this limit.[/dim]")

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
            for module in ['agents', 'services', 'src.agents', 'src.services']:
                logging.getLogger(module).setLevel(logging.DEBUG)
            console.print(f"[yellow]🔍 Verbose Logging: ENABLED (DEBUG level)[/yellow]")

        # Parse test data count (supports presets or custom numbers)
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
            console.print(f"[red]Error: Invalid test data count '{test_data_count}'. Use a number or preset (micro, small, medium, large, xlarge, xxlarge)[/red]")
            return

        if test_mode:
            preset_info = f" ({preset_label})" if preset_label else ""
            console.print(f"[yellow]🧪 Test Mode: ENABLED ({test_data_count_int} mock conversations{preset_info})[/yellow]")
            console.print(f"[dim]   No API calls will be made - using generated test data[/dim]")
            if test_data_count_int >= 5000:
                console.print(f"[dim]   💡 Note: Large datasets may take 1-3 minutes to process[/dim]")

        if ai_model:
            os.environ['AI_MODEL'] = ai_model
            console.print(f"[cyan]🤖 AI Model: {ai_model}[/cyan]")

        if llm_topic_detection:
            os.environ['LLM_TOPIC_DETECTION'] = 'true'
            console.print(f"[bold cyan]🤖 LLM-First Topic Detection: ENABLED[/bold cyan]")
            console.print(f"[dim]   Uses GPT-4o-mini to classify every conversation[/dim]")
            console.print(f"[dim]   More accurate for edge cases (~$1 per 200 convs)[/dim]\n")

        console.print(f"[bold yellow]🤖 Multi-Agent Mode: {analysis_type}[/bold yellow]")
        console.print(f"[cyan]Detail Level: {detail_level.title()}[/cyan]\n")

        start_dt, end_dt = get_date_range_pacific(start_date, end_date)

        extra_canny_conversations: Optional[List[Dict[str, Any]]] = None
        if include_canny and legacy_mode:
            console.print("[yellow]⚠️  Legacy mode ignores Canny data; skipping Canny ingestion.[/yellow]")
            extra_canny_conversations = None
        elif include_canny and not test_mode:
            console.print("[cyan]🔗 Including Canny warehouse feedback in this run[/cyan]")
            extra = await fetch_canny_conversations_from_warehouse(
                start_dt,
                end_dt,
                board_slug=canny_board_id,
                limit=1500,
                log_prefix="[Canny Warehouse]",
            )
            if extra:
                extra_canny_conversations = extra
        elif include_canny and test_mode:
            console.print("[dim]Skipping Canny ingestion in test mode.[/dim]")

        if legacy_mode and analysis_type != 'topic-based':
            console.print("[yellow]⚠️  --legacy-mode only applies to topic-based Hilary cards. Ignoring flag for this analysis type.[/yellow]")
            legacy_mode = False

        if analysis_type == 'topic-based':
            from src.agents.topic_orchestrator_v2 import TopicOrchestratorV2
            await run_topic_based_analysis_custom(
                start_dt,
                end_dt,
                generate_gamma,
                test_mode,
                test_data_count_int,
                audit_trail,
                digest_mode=digest_mode,
                orchestrator_cls=TopicOrchestratorV2,
                mode_label="Voice of Customer (Topic-Based)",
                output_slug="voc_topic_based",
                extra_conversations=extra_canny_conversations,
                legacy_mode=legacy_mode,
                detail_level=detail_level
            )
        elif analysis_type == 'synthesis':
            await run_synthesis_analysis_custom(
                start_dt,
                end_dt,
                generate_gamma,
                audit_trail,
                extra_conversations=extra_canny_conversations,
            )
        else:  # complete
            await run_complete_analysis_custom(
                start_dt,
                end_dt,
                generate_gamma,
                audit_trail,
                digest_mode=digest_mode,
                extra_conversations=extra_canny_conversations
            )

    finally:
        for feature in applied_overrides:
            config.clear_feature_override(feature)


async def run_comprehensive_analysis(
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

    generate_gamma = output_format == 'gamma'

    # Set AI model if specified
    if ai_model:
        os.environ['AI_MODEL'] = ai_model
        console.print(f"[cyan]🤖 AI Model: {ai_model.upper()}[/cyan]")

    # Enable verbose logging if requested
    if verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
        for module in ['agents', 'services', 'src.agents', 'src.services']:
            logging.getLogger(module).setLevel(logging.DEBUG)
        console.print(f"[yellow]🔍 Verbose Logging: ENABLED (DEBUG level)[/yellow]")
    if audit_trail:
        console.print("[purple]📋 Audit Trail Mode: ENABLED[/purple]")

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

            strategy = ComprehensiveStrategy()
            orchestrator = UnifiedOrchestrator(strategy=strategy)
            context = AgentContext(
                analysis_id=f"comprehensive_{timestamp}",
                analysis_type='comprehensive',
                start_date=start_dt,
                end_date=end_dt
            )

            agent_result = await orchestrator.execute(context, options=options)
            results = agent_result.data

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

