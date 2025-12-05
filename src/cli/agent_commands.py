"""
Agent-focused CLI command implementations extracted from src/main.py during
Phase 1.5 of the CLI refactor. The Click decorators remain in src/main.py
while the async implementations live here following the lightweight pattern
established in earlier phases.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from src.cli.entry import console
from src.config.settings import settings

# Maintain compatibility with verbose flag usage in the legacy CLI scope.
verbose = False


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
        console.print(
            f"   Team QA Score: [{qa_color}]{qa_overall:.2f}/1.0[/{qa_color}] "
            f"(Connection: {team_metrics.get('team_qa_connection', 0):.2f}, "
            f"Communication: {team_metrics.get('team_qa_communication', 0):.2f}, "
            f"Content: {team_metrics.get('team_qa_content', 0):.2f})"
        )
        console.print(
            f"   QA Metrics Available: {team_metrics.get('agents_with_qa_metrics', 0)}/"
            f"{team_metrics.get('total_agents', 0)} agents"
        )
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
            coaching_color = (
                "red" if coaching_priority == "high" else "yellow" if coaching_priority == "medium" else "green"
            )

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
                console.print(
                    f"   QA Score: [{qa_color}]{overall_qa:.2f}[/{qa_color}] "
                    f"(Greeting: {qa_metrics.get('greeting_quality_score', 0):.2f}, "
                    f"Grammar: {qa_metrics.get('avg_grammar_errors_per_message', 0):.1f} errors/msg, "
                    f"Formatting: {qa_metrics.get('proper_formatting_rate', 0):.0%})"
                )

                # Add QA-specific coaching points
                if qa_metrics.get('greeting_quality_score', 1.0) < 0.6:
                    console.print(f"   [yellow]→ Improve greetings: use customer names and warm opening[/yellow]")
                if qa_metrics.get('avg_grammar_errors_per_message', 0) > 1.0:
                    console.print(
                        f"   [yellow]→ Reduce grammar errors ({qa_metrics.get('avg_grammar_errors_per_message', 0):.1f}/msg)[/yellow]"
                    )
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
                console.print(
                    f"   [green]QA Score: {overall_qa:.2f}/1.0[/green] "
                    f"(Greeting: {qa_metrics.get('greeting_quality_score', 0):.2f}, "
                    f"Communication: {qa_metrics.get('communication_quality_score', 0):.2f}, "
                    f"Content: {qa_metrics.get('content_quality_score', 0):.2f})"
                )

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
            console.print(
                f"   Affects: {', '.join(affected[:3])}"
                + (f" and {len(affected)-3} more" if len(affected) > 3 else "")
            )
        console.print()

    # Week-over-week changes
    wow_changes = data.get('week_over_week_changes')
    if wow_changes:
        console.print(f"[bold]📈 Week-over-Week Changes:[/bold]")
        for metric, change in wow_changes.items():
            direction = "↑" if change > 0 else "↓"
            color = (
                "green"
                if (change > 0 and 'fcr' in metric) or (change < 0 and 'escalation' in metric)
                else "yellow"
            )
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

        agent_name = {'horatio': 'Horatio', 'boldr': 'Boldr', 'escalated': 'Senior Staff'}.get(agent, agent)

        console.print(f"\n📊 [bold cyan]{agent_name} Performance Analysis[/bold cyan]")
        console.print(f"Date Range: {start_date.date()} to {end_date.date()}")
        if focus_categories:
            console.print(f"Focus: {focus_categories}\n")

        # Fetch conversations (or generate test data)
        if test_mode:
            console.print(
                f"🧪 [yellow]TEST MODE: Generating {test_data_count} mock conversations for {agent_name}...[/yellow]"
            )
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
                    if any(
                        pattern.replace(' ', '.') in email or pattern.replace(' ', '') in email
                        for pattern in patterns
                    ):
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

        console.print(
            f"   ✅ Found {len(agent_conversations)} {agent_name} conversations "
            f"({len(agent_conversations)/len(all_conversations)*100:.1f}% of total)\n"
        )

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
        from src.agents.base_agent import AgentContext

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

            # Update context immutably (AgentContext is frozen)
            context = context.model_copy(
                update={'conversations': agent_conversations}
            )

        # Run agent performance analysis
        console.print(f"🤖 [bold cyan]Analyzing {agent_name} Performance...[/bold cyan]\n")
        if analyze_troubleshooting:
            console.print(
                "   🔍 Troubleshooting analysis enabled (analyzing diagnostic questions and escalation patterns)\n"
            )
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
        console.print("=" * 80)
        console.print(f"[bold green]🎉 {agent_name} Performance Analysis Complete![/bold green]")
        console.print("=" * 80 + "\n")

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
                console.print(
                    f"   QA Score: [{qa_color}]{qa_overall:.2f}/1.0[/{qa_color}] "
                    f"(Connection: {data.get('avg_qa_connection', 0):.2f}, "
                    f"Communication: {data.get('avg_qa_communication', 0):.2f})"
                )

            console.print(f"   Confidence: {result.confidence_level.value}\n")

            if data.get('performance_by_category'):
                console.print(f"[bold]📋 Performance by Category:[/bold]")
                for category, metrics in sorted(
                    data['performance_by_category'].items(),
                    key=lambda x: x[1]['volume'],
                    reverse=True
                ):
                    console.print(f"   {category}: {metrics['volume']} conversations")
                    console.print(
                        f"      FCR: {metrics['fcr_rate']:.1%}, Escalation: {metrics['escalation_rate']:.1%}, "
                        f"Avg Resolution: {metrics['median_resolution_hours']:.1f}h"
                    )
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
                    for category, metrics in sorted(
                        data['performance_by_category'].items(),
                        key=lambda x: x[1]['volume'],
                        reverse=True
                    ):
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
                    additional_instructions=None,
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
        console.print("=" * 80)
        console.print(f"[bold green]🎉 {vendor_name} Coaching Report Complete![/bold green]")
        console.print("=" * 80 + "\n")

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
                    additional_instructions=None,
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
                markdown += (
                    f"**Quality Scores**: QA {qa_metrics.get('overall_qa_score', 0):.2f}/1.0 "
                    f"(Greeting {qa_metrics.get('greeting_quality_score', 0):.2f}, "
                    f"Communication {qa_metrics.get('communication_quality_score', 0):.2f})\n\n"
                )

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
                markdown += (
                    f"**Quality Scores**: QA {qa_metrics.get('overall_qa_score', 0):.2f}/1.0 "
                    f"(Greeting {qa_metrics.get('greeting_quality_score', 0):.2f}, "
                    f"Communication {qa_metrics.get('communication_quality_score', 0):.2f})\n\n"
                )

                # Add specific QA-based coaching points
                qa_coaching = []
                if qa_metrics.get('greeting_quality_score', 1.0) < 0.6:
                    qa_coaching.append("Improve greeting quality: consistently greet customers and use their names")
                if qa_metrics.get('avg_grammar_errors_per_message', 0) > 1.0:
                    qa_coaching.append(
                        f"Reduce grammar errors (currently {qa_metrics.get('avg_grammar_errors_per_message', 0):.1f} per message)"
                    )
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


__all__ = [
    'run_agent_analysis',
    'run_agent_performance_analysis',
    'run_agent_coaching_report',
]

