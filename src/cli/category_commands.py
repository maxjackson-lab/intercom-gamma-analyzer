"""
Category-specific analysis command implementations.

Extracted from src/main.py during Phase 1.4 of the CLI refactor so that
src/main.py only hosts the Click decorators while the async logic lives
in dedicated modules.

This module contains category deep dive commands (Billing, Product, Sites, API)
and the all-categories analysis command, along with their supporting helper
functions.
"""

import asyncio
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from rich.progress import Progress, SpinnerColumn, TextColumn

from src.analyzers.api_analyzer import ApiAnalyzer
from src.analyzers.billing_analyzer import BillingAnalyzer
from src.analyzers.product_analyzer import ProductAnalyzer
from src.analyzers.sites_analyzer import SitesAnalyzer
from src.cli.utils import console
from src.cli.voc_shared import (
    fetch_canny_conversations_from_warehouse,
    fetch_conversations_for_range,
    run_voc_narrative_analysis,
)
from src.services.category_filters import CategoryFilters
from src.services.chunked_fetcher import ChunkedFetcher
from src.services.data_preprocessor import DataPreprocessor
from src.services.gamma_generator import GammaGenerator
from src.utils.output_manager import get_output_directory


async def _run_category_deep_dive(
    category_name: str,
    start_date: datetime,
    end_date: datetime,
    *,
    generate_gamma: bool,
    audit_trail: bool,
    max_conversations: Optional[int],
    output_slug: str,
    analysis_mode: str,
    extra_conversations: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Filter conversations by taxonomy category and run the multi-agent narrative pipeline."""
    display_name = category_name.strip() or "Bug"
    console.print(f"\n[bold blue]{display_name} Deep Dive[/bold blue]")
    conversations = await fetch_conversations_for_range(start_date, end_date)

    if extra_conversations:
        console.print(
            f"[cyan]Including {len(extra_conversations)} supplemental conversations "
            "from external sources (e.g., Canny warehouse).[/cyan]"
        )
        conversations.extend(extra_conversations)

    filters = CategoryFilters()
    normalized_category = category_name.strip()
    if normalized_category not in filters.category_patterns:
        for cat in filters.category_patterns.keys():
            if cat.lower() == normalized_category.lower():
                normalized_category = cat
                break
    if normalized_category not in filters.category_patterns:
        console.print(
            f"[yellow]⚠️ Unknown taxonomy '{category_name}'. "
            "Falling back to Bug category for troubleshooting.[/yellow]"
        )
        normalized_category = "Bug"

    filtered = filters.filter_by_category(
        conversations, normalized_category, include_subcategories=True
    )

    if not filtered:
        console.print(f"[yellow]⚠️ No conversations found for category '{category_name}' in this range.[/yellow]")
        return {}

    if max_conversations:
        filtered = filtered[:max_conversations]
        console.print(f"[cyan]Limiting deep dive to first {len(filtered)} conversations for performance.[/cyan]")

    console.print(f"[cyan]{len(filtered)} conversations matched the '{display_name}' taxonomy.[/cyan]")

    return await run_voc_narrative_analysis(
        start_date,
        end_date,
        generate_gamma=generate_gamma,
        audit_trail=audit_trail,
        digest_mode=False,
        orchestrator_cls=None,
        analysis_slug=output_slug,
        analysis_mode=analysis_mode,
        include_synthesis=False,
        conversations_override=filtered
    )


async def run_billing_analysis(start_date: datetime, end_date: datetime, generate_gamma: bool, max_conversations: Optional[int], audit_trail: bool = False):
    """Run billing deep dive via the multi-agent narrative pipeline."""
    await _run_category_deep_dive(
        category_name="Billing",
        start_date=start_date,
        end_date=end_date,
        generate_gamma=generate_gamma,
        audit_trail=audit_trail,
        max_conversations=max_conversations,
        output_slug="category_billing",
        analysis_mode="category_billing"
    )


async def run_product_analysis(start_date: datetime, end_date: datetime, generate_gamma: bool, max_conversations: Optional[int], audit_trail: bool = False):
    """Run product feedback deep dive via the multi-agent narrative pipeline."""
    await _run_category_deep_dive(
        category_name="Feedback",
        start_date=start_date,
        end_date=end_date,
        generate_gamma=generate_gamma,
        audit_trail=audit_trail,
        max_conversations=max_conversations,
        output_slug="category_product",
        analysis_mode="category_product"
    )


async def run_sites_analysis(start_date: datetime, end_date: datetime, generate_gamma: bool, max_conversations: Optional[int], audit_trail: bool = False):
    """Run workspace/sites deep dive via the multi-agent narrative pipeline."""
    await _run_category_deep_dive(
        category_name="Workspace",
        start_date=start_date,
        end_date=end_date,
        generate_gamma=generate_gamma,
        audit_trail=audit_trail,
        max_conversations=max_conversations,
        output_slug="category_sites",
        analysis_mode="category_sites"
    )


async def run_api_analysis(start_date: datetime, end_date: datetime, generate_gamma: bool, max_conversations: Optional[int], audit_trail: bool = False):
    """Run API deep dive via the multi-agent narrative pipeline."""
    await _run_category_deep_dive(
        category_name="API",
        start_date=start_date,
        end_date=end_date,
        generate_gamma=generate_gamma,
        audit_trail=audit_trail,
        max_conversations=max_conversations,
        output_slug="category_api",
        analysis_mode="category_api"
    )


async def run_all_categories_analysis_v2(start_date: datetime, end_date: datetime, generate_gamma: bool, parallel: bool, max_conversations: Optional[int]):
    """Run all categories analysis with new infrastructure."""
    try:
        console.print(f"[bold blue]All Categories Analysis[/bold blue]")
        console.print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        console.print(f"Categories: Billing, Product, Sites, API")

        # Initialize services
        chunked_fetcher = ChunkedFetcher()
        data_preprocessor = DataPreprocessor()
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
        output_dir = get_output_directory()
        output_dir.mkdir(exist_ok=True, parents=True)

        if parallel:
            # Run analyses in parallel
            async def analyze_category(category_name, analyzer):
                result = await analyzer.analyze_category(
                    processed_conversations, start_date, end_date, {'generate_ai_insights': True}
                )
                return category_name, result

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Running parallel analyses...", total=len(analyzers))

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
            with open(results_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(result, f, indent=2, default=str, ensure_ascii=False)

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


async def run_technical_troubleshooting_analysis(
    start_date: datetime,
    end_date: datetime,
    *,
    taxonomy_filter: Optional[str],
    generate_gamma: bool,
    audit_trail: bool,
    max_conversations: Optional[int] = None
) -> Dict[str, Any]:
    """Helper to run technical troubleshooting via the narrative pipeline."""
    category = (taxonomy_filter or "Bug").strip() or "Bug"
    slug = f"tech_troubleshooting_{category.lower().replace(' ', '_')}"
    extra_conversations = await fetch_canny_conversations_from_warehouse(
        start_date,
        end_date,
        limit=max_conversations or 1000,
        log_prefix="[Canny Warehouse]",
    )
    if not extra_conversations:
        extra_conversations = None

    return await _run_category_deep_dive(
        category_name=category,
        start_date=start_date,
        end_date=end_date,
        generate_gamma=generate_gamma,
        audit_trail=audit_trail,
        max_conversations=max_conversations,
        output_slug=slug,
        analysis_mode="tech_troubleshooting",
        extra_conversations=extra_conversations
    )

