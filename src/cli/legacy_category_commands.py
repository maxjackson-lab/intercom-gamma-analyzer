"""
Legacy category command implementations retained for backwards compatibility.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
import json

from rich.progress import Progress, SpinnerColumn, TextColumn

from src.cli.utils import console
from src.config.settings import settings
from src.services.category_filters import CategoryFilters
from src.services.elt_pipeline import ELTPipeline


async def run_category_analysis(
    category: str,
    start_date: datetime,
    end_date: datetime,
    output_format: str,
) -> None:
    """Run single category analysis."""
    try:
        pipeline = ELTPipeline()

        console.print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

        # Extract and load data
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Extracting and loading data...", total=None)

            stats = await pipeline.extract_and_load(start_date, end_date)

            progress.update(task, description=f"✅ Loaded {stats['conversations_count']} conversations")

        if stats["conversations_count"] == 0:
            console.print("[yellow]No conversations found for the specified date range.[/yellow]")
            return

        # Get all conversations and filter by category
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Analyzing {category} category...", total=None)

            all_conversations = await pipeline.intercom_service.fetch_conversations_by_date_range(start_date, end_date)

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
            export_path = output_dir / f"{category}_analysis_{timestamp}.csv"
            import pandas as pd  # Local import to avoid slowing startup for other commands

            df = pd.DataFrame(filtered_conversations)
            df.to_csv(export_path, index=False)
        elif output_format == "json":
            export_path = output_dir / f"{category}_analysis_{timestamp}.json"
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(filtered_conversations, f, indent=2, default=str)
        else:
            # Default to CSV when format is unsupported (e.g., excel legacy flag)
            export_path = output_dir / f"{category}_analysis_{timestamp}.csv"
            import pandas as pd  # Local import to avoid slowing startup for other commands

            df = pd.DataFrame(filtered_conversations)
            df.to_csv(export_path, index=False)

        console.print(f"\n[bold green]{category.title()} Analysis Completed![/bold green]")
        console.print(f"Total conversations analyzed: {stats['conversations_count']:,}")
        console.print(f"Category matches: {len(filtered_conversations):,}")
        console.print(f"Export: {export_path}")

    except Exception as exc:
        console.print(f"[red]Error in category analysis: {exc}[/red]")
        raise


async def run_all_categories_analysis(start_date: datetime, end_date: datetime, parallel: bool) -> None:
    """Placeholder for legacy all categories analysis."""
    console.print("[yellow]All categories analysis not yet implemented[/yellow]")
    console.print(f"Would analyze all 13 categories from {start_date.date()} to {end_date.date()}")
    if parallel:
        console.print("[dim]Parallel mode requested (not yet supported).[/dim]")


async def run_synthesis_analysis(categories: str, pattern: Optional[str], start_date: datetime, end_date: datetime) -> None:
    """Placeholder for synthesis analysis."""
    console.print("[yellow]Synthesis analysis not yet implemented[/yellow]")
    console.print(f"Would synthesize {categories} from {start_date.date()} to {end_date.date()}")
    if pattern:
        console.print(f"[dim]Pattern filter requested: {pattern}[/dim]")


async def run_custom_tag_analysis(tag: str, agent: Optional[str], start_date: datetime, end_date: datetime) -> None:
    """Placeholder for custom tag analysis."""
    console.print("[yellow]Custom tag analysis not yet implemented[/yellow]")
    console.print(f"Would analyze {tag} tag from {start_date.date()} to {end_date.date()}")
    if agent:
        console.print(f"[dim]Agent filter: {agent}[/dim]")


async def run_escalation_analysis(
    to: Optional[str],
    from_agent: Optional[str],
    start_date: datetime,
    end_date: datetime,
) -> None:
    """Placeholder for escalation analysis."""
    console.print("[yellow]Escalation analysis not yet implemented[/yellow]")
    console.print(f"Would analyze escalations from {start_date.date()} to {end_date.date()}")
    if to or from_agent:
        console.print(f"[dim]Filters → to: {to}, from: {from_agent}[/dim]")


async def run_pattern_analysis(pattern: str, start_date: datetime, end_date: datetime, case_sensitive: bool) -> None:
    """Placeholder for pattern analysis."""
    console.print("[yellow]Pattern analysis not yet implemented[/yellow]")
    console.print(f"Would search for '{pattern}' from {start_date.date()} to {end_date.date()}")
    if case_sensitive:
        console.print("[dim]Case sensitive search enabled[/dim]")

