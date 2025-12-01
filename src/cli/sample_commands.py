"""
Sample-mode and test-mode command implementations.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from rich.panel import Panel

from src.cli.utils import console
from src.config.settings import settings
from src.services.sample_mode import run_sample_mode
from src.utils.agent_thinking_logger import AgentThinkingLogger
from src.utils.time_utils import calculate_date_range


async def run_sample_mode_command(
    count: Optional[int],
    start_date: Optional[str],
    end_date: Optional[str],
    time_period: str,
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
    audit_mode: bool,
) -> None:
    """Pull real conversations with ultra-rich logging, diagnostics, and optional audit validation."""
    explicit_count = count
    if no_hierarchy:
        include_hierarchy = False

    console.print(
        Panel.fit(
            "[bold cyan]🔬 SAMPLE MODE[/bold cyan]\n"
            "Pulling REAL conversations with ultra-rich logging",
            border_style="cyan",
        )
    )
    
    if audit_mode:
        console.print(
            Panel.fit(
                "[bold yellow]🔍 AUDIT MODE ENABLED[/bold yellow]\n"
                "Running validation checks on all agent outputs",
                border_style="yellow",
            )
        )

    # Parse dates
    if time_period:
        normalized_period = 'yesterday' if time_period == 'day' else time_period
        start, end = calculate_date_range(
            time_period=normalized_period,
            periods_back=1,
            end_is_yesterday=False
        )
    else:
        start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.now() - timedelta(days=7)
        end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.now()

    # Show mode description
    mode_descriptions = {
        "quick": "50 tickets, 5 samples, 2 LLM topics (~30 sec)",
        "standard": "200 tickets, 10 samples, 3 LLM topics (~2 min)",
        "deep": "500 tickets, 15 samples, 5 LLM topics (~5 min)",
        "comprehensive": "1000 tickets, 20 samples, 7 LLM topics (~10 min)",
    }
    console.print(f"\n[cyan]Schema Mode: {schema_mode} - {mode_descriptions[schema_mode]}[/cyan]\n")
    if explicit_count is not None:
        console.print(f"[cyan]🔢 Sample size override via --count: {explicit_count} conversations[/cyan]\n")

    # Set AI model for LLM test if enabled
    if test_llm and ai_model:
        os.environ["AI_MODEL"] = ai_model
        console.print(f"[cyan]🤖 AI Model for LLM Test: {ai_model.upper()}[/cyan]\n")

    # Enable verbose logging if requested
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        for module in ["src.agents", "src.services"]:
            logging.getLogger(module).setLevel(logging.DEBUG)
        console.print("[yellow]🔍 Verbose Logging: ENABLED[/yellow]\n")

    # Always enable metrics-only observability (tracks errors/timeouts without full logging)
    AgentThinkingLogger.enable_metrics_only()

    # Enable full agent thinking logger if requested (opt-in)
    if show_agent_thinking:
        output_dir = Path(settings.effective_output_directory)
        output_dir.mkdir(exist_ok=True, parents=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        thinking_log = output_dir / f"agent_thinking_{timestamp}.log"

        AgentThinkingLogger.enable(thinking_log)

    # Run sample mode with error handling (ALWAYS save files even if it crashes!)
    result: Dict = {}
    try:
        result = await run_sample_mode(
            count=explicit_count,
            start_date=start,
            end_date=end,
            save_to_file=save_to_file,
            test_llm=test_llm,
            test_all_agents=test_all_agents,
            show_agent_thinking=show_agent_thinking,
            llm_topic_detection=llm_topic_detection,
            schema_mode=schema_mode,
            include_hierarchy=include_hierarchy,
            audit_mode=audit_mode,
        )

        console.print("\n[bold green]✅ Sample mode complete![/bold green]")
        console.print(f"Analyzed {result.get('analysis', {}).get('total_conversations', 0)} conversations")
        
        if audit_mode and 'audit_results' in result:
            console.print("[bold cyan]📊 Audit report generated![/bold cyan]")
            console.print(f"Check outputs/ directory for agent_audit_report_*.md")
            
            audit_summary = result.get('audit_summary', {})
            passed = audit_summary.get('passed', 0)
            total = audit_summary.get('total', 0)
            avg_score = audit_summary.get('average_score', 0.0)
            console.print(f"  Audit: {passed}/{total} agents passed (avg quality: {avg_score:.2f})")

    except Exception as exc:
        console.print(f"\n[bold red]❌ Sample mode failed: {exc}[/bold red]")
        console.print("[yellow]⚠️  Files should still be saved despite error[/yellow]")
        raise

    console.print("\n[bold]Key Findings:[/bold]")

    # Safe nested access to avoid KeyError
    agent_attr = result.get("analysis", {}).get("agent_attribution", {})
    custom_attrs = result.get("analysis", {}).get("custom_attributes", {})

    console.print(f"  Sal conversations: {agent_attr.get('sal_count', 0)} ({agent_attr.get('sal_percentage', 0)}%)")
    console.print(
        f"  Human admin: {agent_attr.get('human_admin_count', 0)} ({agent_attr.get('human_admin_percentage', 0)}%)"
    )
    console.print(
        f"  With custom_attributes: {custom_attrs.get('has_custom_attributes', 0)} "
        f"({custom_attrs.get('percentage_with_attributes', 0)}%)"
    )


def run_test_mode_command(
    test_type: str,
    num_conversations: int,
) -> None:
    """Generate fake conversations to validate topic orchestration."""
    console.print("[bold yellow]🧪 TEST MODE[/bold yellow]")
    console.print(f"Test type: {test_type}")
    console.print(f"Fake conversations: {num_conversations}")
    console.print("=" * 80)

    # Create minimal fake data
    fake_conversations: List[Dict] = []
    topics = ["Billing", "Bug", "Credits", "Account", "Product Question"]

    for i in range(num_conversations):
        topic = topics[i % len(topics)]
        conv = {
            "id": f"test_{i}",
            "created_at": int((datetime.now() - timedelta(hours=i)).timestamp()),
            "updated_at": int(datetime.now().timestamp()),
            "state": "closed",
            "count_reopens": 0 if i % 3 == 0 else 1,
            "admin_assignee_id": "12345",
            "custom_attributes": {topic: True},
            "tags": {"tags": [{"name": topic}]},
            "full_text": f"Customer says: This is about {topic.lower()}. Agent responds: Got it.",
            "customer_messages": [f"This is about {topic.lower()}"],
            "conversation_parts": {
                "conversation_parts": [
                    {"author": {"type": "user"}, "body": f"This is about {topic.lower()}"},
                    {"author": {"type": "admin"}, "body": "Got it."},
                ]
            },
            "source": {"author": {"type": "user"}, "body": f"This is about {topic.lower()}"},
        }
        fake_conversations.append(conv)

    console.print(f"✅ Created {len(fake_conversations)} fake conversations")

    # Save test data
    test_file = Path("outputs/test_data.json")
    test_file.parent.mkdir(exist_ok=True)
    with open(test_file, "w", encoding="utf-8") as f:
        json.dump(fake_conversations, f, indent=2)
    console.print(f"📁 Test data saved to: {test_file}")

    # Run appropriate test
    if test_type == "topic-based":
        console.print("\n🤖 Running topic-based analysis with test data...")
        asyncio.run(run_test_topic_based(fake_conversations))
    elif test_type == "api":
        console.print("\n⚙️  Running API analysis with test data...")
        console.print("[yellow]API test not yet implemented[/yellow]")
    elif test_type == "horatio":
        console.print("\n👤 Running Horatio performance with test data...")
        console.print("[yellow]Horatio test not yet implemented[/yellow]")


async def run_test_topic_based(conversations: List[Dict]) -> None:
    """Run topic-based analysis pipeline using fake data."""
    verbose_imports = os.getenv("VERBOSE", "").lower() in ("1", "true", "yes")
    if verbose_imports:
        import time as time_module

        import_start = time_module.monotonic()
        console.print("[dim]⏱️  Importing TopicOrchestrator...[/dim]")

    from src.services.strategies.voc_strategy import VoiceOfCustomerStrategy
    from src.services.unified_orchestrator import UnifiedOrchestrator
    from src.agents.base_agent import AgentContext

    if verbose_imports:
        import_duration = time_module.monotonic() - import_start
        console.print(f"[dim]✅ Strategies imported in {import_duration:.2f}s[/dim]")

    strategy = VoiceOfCustomerStrategy()
    orchestrator = UnifiedOrchestrator(strategy=strategy)

    try:
        context = AgentContext(
            analysis_id="test_topic_based",
            analysis_type="voc",
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now(),
            conversations=conversations,
            metadata={
                'week_id': "TEST",
                'period_type': "test",
                'period_label': "Test Mode"
            }
        )
        agent_result = await orchestrator.execute(context)
        results = agent_result.data

        console.print("\n" + "=" * 80)
        console.print("[bold green]✅ TEST PASSED[/bold green]")
        console.print("=" * 80)

        # Show summary
        summary = results.get("summary", {})
        console.print("\n📊 Summary:")
        console.print(f"   Total: {summary.get('total_conversations')}")
        console.print(f"   Topics: {summary.get('topics_analyzed')}")
        console.print(f"   Agents: {summary.get('agents_completed')}")
        console.print(f"   Time: {summary.get('total_execution_time')}s")

        # Show report preview
        report = results.get("formatted_report", "")
        if report:
            console.print("\n📝 Report preview (first 500 chars):")
            console.print(report[:500])

        # Save test output
        test_output = Path("outputs/test_output.md")
        with open(test_output, "w", encoding="utf-8") as f:
            f.write(report)
        console.print(f"\n📁 Test output: {test_output}")

    except Exception as exc:
        console.print(f"\n[red]❌ TEST FAILED: {exc}[/red]")
        import traceback

        traceback.print_exc()

