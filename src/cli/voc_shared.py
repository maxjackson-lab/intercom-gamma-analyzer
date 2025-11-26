"""
Shared helper functions for Voice of Customer CLI commands.

These utilities are imported by both `voc_commands` and `category_commands`
to avoid circular dependencies and keep the logic centralized.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agents.base_agent import AgentContext
from src.cli.utils import console
from src.services.category_filters import CategoryFilters
from src.services.canny_warehouse_service import (
    CannyWarehouseService,
    SnowflakeNotConfiguredError,
)
from src.utils.output_manager import get_output_file_path


async def fetch_conversations_for_range(
    start_date: datetime, end_date: datetime
) -> List[Dict[str, Any]]:
    """Fetch conversations for the provided date range using ChunkedFetcher."""
    from src.services.chunked_fetcher import ChunkedFetcher

    console.print("📥 [cyan]Fetching conversations for analysis...[/cyan]")
    fetcher = ChunkedFetcher()
    conversations = await fetcher.fetch_conversations_chunked(start_date, end_date)
    console.print(f"   ✅ Retrieved {len(conversations)} conversations\n")
    return conversations


async def fetch_canny_conversations_from_warehouse(
    start_date: datetime,
    end_date: datetime,
    *,
    board_slug: Optional[str] = None,
    limit: int = 1000,
    log_prefix: str = "[Canny Warehouse]",
) -> List[Dict[str, Any]]:
    """
    Attempt to fetch Canny conversations from Snowflake.
    Returns [] when warehouse credentials/connectivity are unavailable.
    """
    service = CannyWarehouseService()
    if not service.enabled:
        console.print(
            f"{log_prefix} [dim]Snowflake warehouse not configured. "
            "Set SNOWFLAKE_* env vars to enable Canny ingestion.[/dim]"
        )
        return []

    try:
        conversations = await service.fetch_conversations(
            start_date=start_date,
            end_date=end_date,
            board_slug=board_slug,
            limit=limit,
        )
        if conversations:
            console.print(
                f"{log_prefix} [green]✅ Retrieved {len(conversations)} Canny posts[/green]"
            )
        else:
            console.print(f"{log_prefix} [dim]No Canny posts for this window.[/dim]")
        return conversations
    except SnowflakeNotConfiguredError as exc:
        console.print(f"{log_prefix} [dim]{exc}[/dim]")
    except Exception as exc:  # pragma: no cover - defensive logging
        console.print(
            f"{log_prefix} [yellow]⚠️ Failed to load Canny data: {exc}[/yellow]"
        )
    return []


async def _execute_topic_pipeline_basic(
    conversations: List[Dict[str, Any]],
    start_date: datetime,
    end_date: datetime,
    period_type: str,
    period_label: str,
    digest_mode: bool = False,
    orchestrator_cls=None,
    ai_model: Optional[str] = None,
) -> Dict[str, Any]:
    """Run TopicOrchestrator (or custom subclass) to gather agent outputs for narrative formatting."""
    if orchestrator_cls is None:
        from src.agents.topic_orchestrator import TopicOrchestrator

        orchestrator_cls = TopicOrchestrator

    orchestrator = orchestrator_cls()
    week_id = start_date.strftime("%Y-W%W")

    return await orchestrator.execute_weekly_analysis(
        conversations=conversations,
        week_id=week_id,
        start_date=start_date,
        end_date=end_date,
        period_type=period_type,
        period_label=period_label,
        canny_posts=None,
        ai_model=ai_model,
        digest_mode=digest_mode,
    )


def _build_category_results_from_agent_data(
    agent_results: Dict[str, Any]
) -> Dict[str, Dict[str, Any]]:
    """
    Convert topic detection + sentiment artifacts into the structure expected by SynthesisEngine.
    Each Tier-1 topic acts as a synthetic category so cross-category synthesis works for VoC.
    """
    category_results: Dict[str, Dict[str, Any]] = {}
    topic_detection_data = (agent_results.get("TopicDetectionAgent") or {}).get(
        "data", {}
    )
    topic_distribution = topic_detection_data.get("topic_distribution", {})
    topic_sentiments = agent_results.get("TopicSentiments", {}) or {}

    for topic_name, stats in topic_distribution.items():
        sentiment_entry = topic_sentiments.get(topic_name) or {}
        sentiment_data = (
            sentiment_entry.get("data", {}) if isinstance(sentiment_entry, dict) else {}
        )
        sentiment_distribution = (
            sentiment_data.get("sentiment_distribution")
            or sentiment_data.get("sentiment_breakdown")
            or {}
        )

        category_results[topic_name] = {
            "data_summary": {
                "total_conversations": stats.get("volume", 0),
                "filtered_conversations": stats.get("volume", 0),
                "sentiment_distribution": sentiment_distribution,
                "top_topics": [
                    {"topic": topic_name, "count": stats.get("volume", 0)}
                ],
                "top_tags": sentiment_data.get("top_tags", []),
            },
            "analysis_results": {
                "common_issues": sentiment_data.get("top_pain_points", []),
                "escalation_analysis": {
                    "escalation_rate": sentiment_data.get("escalation_rate"),
                    "escalation_signals": sentiment_data.get("escalation_signals"),
                },
                "success_analysis": {
                    "success_rate": sentiment_data.get("success_rate"),
                    "patterns": sentiment_data.get("success_patterns"),
                },
            },
        }

    return category_results


def _build_narrative_context_from_topic_results(
    topic_results: Dict[str, Any],
    conversations: List[Dict[str, Any]],
    start_date: datetime,
    end_date: datetime,
    *,
    digest_mode: bool = False,
    analysis_mode: str = "synthesis",
    synthesis_results: Optional[Dict[str, Any]] = None,
) -> AgentContext:
    """Assemble AgentContext for NarrativeFormatterAgent using orchestrator outputs."""
    agent_results = topic_results.get("agent_results", {}) or {}

    def _agent_result(name: str) -> Dict[str, Any]:
        return agent_results.get(name) or {}

    previous_results: Dict[str, Any] = {
        "SegmentationAgent": _agent_result("SegmentationAgent"),
        "TopicDetectionAgent": _agent_result("TopicDetectionAgent"),
        "SubTopicDetectionAgent": _agent_result("SubTopicDetectionAgent"),
        "TopicSentiments": _agent_result("TopicSentiments"),
        "TopicExamples": _agent_result("TopicExamples"),
        "FinPerformanceAgent": _agent_result("FinPerformanceAgent"),
        "BpoPerformanceAgent": _agent_result("BpoPerformanceAgent"),
        "TrendAgent": _agent_result("TrendAgent"),
        "AnalyticalInsights": _agent_result("AnalyticalInsights"),
    }

    if synthesis_results:
        previous_results["SynthesisEngine"] = synthesis_results

    metadata = {
        "week_id": topic_results.get("week_id"),
        "period_type": topic_results.get("period_type"),
        "period_label": topic_results.get("period_label"),
        "digest_mode": digest_mode,
        "analysis_mode": analysis_mode,
        "summary": topic_results.get("summary"),
    }

    metadata = {k: v for k, v in metadata.items() if v is not None}

    return AgentContext(
        analysis_id=f"voc_{analysis_mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        analysis_type="voice-of-customer",
        start_date=start_date,
        end_date=end_date,
        conversations=conversations,
        previous_results=previous_results,
        metadata=metadata,
    )


async def run_voc_narrative_analysis(
    start_date: datetime,
    end_date: datetime,
    *,
    generate_gamma: bool,
    audit_trail: bool,
    digest_mode: bool,
    orchestrator_cls=None,
    analysis_slug: str,
    analysis_mode: str,
    include_synthesis: bool = True,
    conversations_override: Optional[List[Dict[str, Any]]] = None,
    taxonomy_filter: Optional[str] = None,
    extra_conversations: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Shared execution path for synthesis/complete VoC modes that now rely on NarrativeFormatterAgent.
    Returns metadata about saved files for downstream callers/tests.
    """
    if audit_trail:
        console.print(
            "[yellow]⚠️ Audit trail is not yet available for the Narrative V2 synthesis pipeline.[/yellow]"
        )

    console.record = True
    log_output = ""
    output_file: Optional[Path] = None

    try:
        conversations = conversations_override
        if conversations is None:
            conversations = await fetch_conversations_for_range(start_date, end_date)

        if extra_conversations:
            console.print(
                f"[cyan]Including {len(extra_conversations)} supplemental conversations (e.g., Canny feedback).[/cyan]"
            )
            conversations.extend(extra_conversations)

        if taxonomy_filter:
            filters = CategoryFilters()
            filtered = filters.filter_by_category(
                conversations, taxonomy_filter, include_subcategories=True
            )
            if not filtered:
                console.print(
                    f"[yellow]⚠️ No conversations matched taxonomy filter '{taxonomy_filter}'.[/yellow]"
                )
                return {}
            conversations = filtered
            console.print(
                f"[cyan]Applied taxonomy filter '{taxonomy_filter}' → {len(conversations)} conversations remain.[/cyan]"
            )
        if not conversations:
            console.print("[red]No conversations found for the specified range.[/red]")
            return {}

        from src.utils.time_utils import detect_period_type

        period_type, period_label = detect_period_type(start_date, end_date)

        topic_results = await _execute_topic_pipeline_basic(
            conversations=conversations,
            start_date=start_date,
            end_date=end_date,
            period_type=period_type,
            period_label=period_label,
            digest_mode=digest_mode,
            orchestrator_cls=orchestrator_cls,
        )

        agent_results = topic_results.get("agent_results", {}) or {}

        synthesis_results = None
        if include_synthesis:
            category_results = _build_category_results_from_agent_data(agent_results)
            if category_results:
                from src.services.synthesis_engine import SynthesisEngine

                synthesis_engine = SynthesisEngine()
                synthesis_results = await synthesis_engine.synthesize_category_results(
                    category_results,
                    start_date,
                    end_date,
                    options={"analysis_mode": analysis_mode},
                )
            else:
                console.print(
                    "[yellow]⚠️ No category results available for synthesis. Skipping synthesis layer.[/yellow]"
                )

        narrative_context = _build_narrative_context_from_topic_results(
            topic_results,
            conversations,
            start_date,
            end_date,
            digest_mode=digest_mode,
            analysis_mode=analysis_mode,
            synthesis_results=synthesis_results,
        )

        from src.agents.narrative_formatter_agent import NarrativeFormatterAgent

        formatter = NarrativeFormatterAgent()
        narrative_result = await formatter.execute(narrative_context)

        if not narrative_result.success:
            raise RuntimeError(
                f"NarrativeFormatterAgent failed: {narrative_result.data.get('error')}"
            )

        markdown_report = narrative_result.data.get("formatted_output", "")
        if not markdown_report:
            raise RuntimeError("NarrativeFormatterAgent returned an empty report")

        structured_data = narrative_result.data.get("structured_data", {})

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = get_output_file_path(f"{analysis_slug}_{timestamp}.md")
        output_file.write_text(markdown_report, encoding="utf-8")
        console.print(f"[green]✅ Narrative saved to: {output_file}[/green]")

        structured_file = output_file.with_name(output_file.stem + "_STRUCTURED_DATA.json")
        if structured_data:
            import json

            structured_file.write_text(
                json.dumps(structured_data, indent=2), encoding="utf-8"
            )
            console.print(f"[cyan]📊 Structured data saved to: {structured_file}[/cyan]")
        else:
            structured_file = None

        synthesis_file = None
        if synthesis_results:
            import json

            synthesis_file = output_file.with_name(output_file.stem + "_SYNTHESIS.json")
            synthesis_file.write_text(
                json.dumps(synthesis_results, indent=2), encoding="utf-8"
            )
            console.print(f"[cyan]🧠 Synthesis metadata saved to: {synthesis_file}[/cyan]")

        if generate_gamma:
            from src.services.gamma_client import GammaClient

            gamma_client = GammaClient()
            console.print("\n🎨 Generating Gamma presentation...")
            generation_id = await gamma_client.generate_presentation(
                input_text=markdown_report,
                format="presentation",
                text_mode="preserve",
                card_split="inputTextBreaks",
                theme_name="Night Sky",
                text_options={
                    "tone": "professional, analytical",
                    "audience": "executives",
                },
            )
            console.print(f"   Submitted to Gamma (ID: {generation_id})")
            status = await gamma_client.poll_generation(
                generation_id, max_polls=30, poll_interval=2.0
            )
            if status.get("status") == "completed":
                gamma_url = status.get("gammaUrl")
                if gamma_url:
                    url_file = output_file.with_name(output_file.stem + "_GAMMA_URL.txt")
                    url_file.write_text(gamma_url, encoding="utf-8")
                    console.print(f"[green]🎉 Gamma presentation ready: {gamma_url}[/green]")
                    console.print(f"   URL saved to: {url_file}")
            else:
                console.print(
                    f"[yellow]⚠️ Gamma generation ended with status: {status.get('status')}[/yellow]"
                )

        summary = topic_results.get("summary") or {}
        console.print(
            f"\n📊 Conversations analyzed: {summary.get('total_conversations', len(conversations))}"
        )
        if synthesis_results and synthesis_results.get("executive_summary"):
            console.print(
                f"🧠 Synthesis highlight: {synthesis_results['executive_summary']}"
            )

        return {
            "report_file": str(output_file),
            "structured_file": str(structured_file) if structured_file else None,
            "synthesis_file": str(synthesis_file) if synthesis_file else None,
        }

    finally:
        log_output = console.export_text(clear=True)
        console.record = False
        if log_output:
            if output_file:
                log_file = output_file.with_suffix(".log")
            else:
                log_file = get_output_file_path(
                    f"voc_{analysis_mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
                )
            log_file.write_text(log_output, encoding="utf-8")
            console.print(f"[dim]🗂️  Complete log captured at {log_file}[/dim]")




