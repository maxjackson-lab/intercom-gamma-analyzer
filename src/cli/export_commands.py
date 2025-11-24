"""
Export, query, and custom analysis command implementations.

Extracted from src/main.py during Phase 1.3 of the CLI refactor so that
src/main.py only hosts the Click decorators while the async logic lives
in dedicated modules.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from rich.progress import Progress, SpinnerColumn, TextColumn

from src.cli.utils import console
from src.config.settings import settings
from src.models.analysis_models import AnalysisRequest, AnalysisMode
from src.services.data_exporter import DataExporter
from src.services.gamma_client import GammaClient
from src.services.intercom_sdk_service import IntercomSDKService
from src.services.metrics_calculator import MetricsCalculator
from src.services.openai_client import OpenAIClient
from src.services.query_builder import GeneralQueryService
from src.analyzers.trend_analyzer import TrendAnalyzer


async def run_custom_analysis(
    request: AnalysisRequest,
    generate_gamma: bool,
    output_format: str,
):
    """Run custom analysis."""
    try:
        if request.mode != AnalysisMode.CUSTOM:
            request.mode = AnalysisMode.CUSTOM

        intercom_service = IntercomSDKService()
        metrics_calculator = MetricsCalculator()
        openai_client = OpenAIClient()
        analyzer = TrendAnalyzer(intercom_service, metrics_calculator, openai_client)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running custom analysis...", total=None)
            await asyncio.sleep(0)
            results = await analyzer.analyze(request)
            progress.update(task, description="✅ Analysis completed")

        display_custom_results(results)

        if output_format == "json":
            save_json_output(results, f"custom_analysis_{request.start_date}_{request.end_date}")
        else:
            save_markdown_output(results, f"custom_analysis_{request.start_date}_{request.end_date}")

        if generate_gamma:
            await generate_gamma_presentation(results, f"custom_analysis_{request.start_date}_{request.end_date}")

        console.print(f"\n[bold green]Analysis completed successfully![/bold green]")
        console.print(f"Results saved to: {settings.effective_output_directory}/")

    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        sys.exit(1)


async def run_data_export(
    start_date: datetime,
    end_date: datetime,
    export_format: str,
    max_pages: Optional[int],
    include_metrics: bool,
):
    """Run data export."""
    valid_formats = ["excel", "csv", "json", "parquet", "all"]
    if export_format not in valid_formats:
        console.print(
            f"[red]Error: Invalid export_format '{export_format}'. Allowed: {', '.join(valid_formats)}[/red]"
        )
        sys.exit(1)

    try:
        intercom_service = IntercomSDKService()
        data_exporter = DataExporter()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching conversations...", total=None)

            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())

            conversations = await intercom_service.fetch_conversations_by_date_range(
                start_dt, end_dt, max_conversations=max_pages
            )

            progress.update(task, description=f"✅ Fetched {len(conversations)} conversations")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Exporting data...", total=None)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_results: Dict[str, Any] = {}

            if export_format in ["excel", "all"]:
                excel_path = data_exporter.export_conversations_to_excel(
                    conversations,
                    f"export_{timestamp}",
                    include_metrics=include_metrics,
                )
                export_results["excel"] = excel_path

            if export_format in ["csv", "all"]:
                csv_paths = data_exporter.export_conversations_to_csv(
                    conversations,
                    f"export_{timestamp}",
                )
                export_results["csv"] = csv_paths

            if export_format in ["json", "all"]:
                json_path = data_exporter.export_raw_data_to_json(
                    conversations,
                    f"export_{timestamp}",
                )
                export_results["json"] = json_path

            if export_format in ["parquet", "all"]:
                parquet_path = data_exporter.export_to_parquet(
                    conversations,
                    f"export_{timestamp}",
                )
                export_results["parquet"] = parquet_path

            progress.update(task, description="✅ Export completed")

        console.print(f"\n[bold green]Export completed successfully![/bold green]")
        console.print(f"Total conversations exported: {len(conversations):,}")

        for format_type, path in export_results.items():
            if isinstance(path, list):
                console.print(f"{format_type.upper()} files: {len(path)} files")
                for file_path in path:
                    console.print(f"  • {file_path}")
            else:
                console.print(f"{format_type.upper()}: {path}")

    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        sys.exit(1)


async def run_general_query(
    query_type: Optional[str],
    suggestion: Optional[str],
    custom_query: Optional[str],
    export_format: str,
    max_pages: Optional[int],
):
    """Run general query."""
    try:
        intercom_service = IntercomSDKService()
        data_exporter = DataExporter()
        query_service = GeneralQueryService(intercom_service, data_exporter)

        query: Dict[str, Any] = {}

        if custom_query:
            try:
                query = json.loads(custom_query)
            except json.JSONDecodeError as exc:
                console.print(
                    f"[red]Invalid JSON in --custom-query: {exc}. Check quotes, commas, braces.[/red]"
                )
                sys.exit(1)
        elif query_type and suggestion:
            query = query_service.build_suggested_query(query_type, suggestion)
        else:
            console.print("[red]Error: Must provide either custom-query or both query-type and suggestion[/red]")
            sys.exit(1)

        console.print(f"Query: {query}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Executing query...", total=None)
            await asyncio.sleep(0)

            results = await query_service.execute_query(
                query,
                max_pages=max_pages,
                export_format=export_format,
            )

            progress.update(task, description="✅ Query completed")

        console.print(f"\n[bold green]Query executed successfully![/bold green]")
        console.print(f"Total conversations found: {results['total_conversations']:,}")

        export_results = results.get("export_results", {})
        for format_type, path in export_results.items():
            if isinstance(path, list):
                console.print(f"{format_type.upper()} files: {len(path)} files")
                for file_path in path:
                    console.print(f"  • {file_path}")
            else:
                console.print(f"{format_type.upper()}: {path}")

    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        sys.exit(1)


def display_custom_results(results):
    """Display custom analysis results."""
    console.print("\n[bold blue]Custom Analysis Results[/bold blue]")
    console.print(f"Analysis completed in {results.analysis_duration_seconds:.2f} seconds")
    console.print(f"Conversations analyzed: {results.total_conversations_analyzed:,}")


def save_json_output(results, filename: str):
    """Save results as JSON."""
    output_path = Path(settings.effective_output_directory) / f"{filename}.json"

    with open(output_path, "w") as file_handle:
        json.dump(results.dict(), file_handle, indent=2, default=str)

    console.print(f"JSON output saved to: {output_path}")


def save_markdown_output(results, filename: str):
    """Save results as Markdown."""
    output_path = Path(settings.effective_output_directory) / f"{filename}.md"

    if hasattr(results, "analysis_content"):
        content = results.analysis_content
    else:
        content = f"# {filename.replace('_', ' ').title()}\n\nAnalysis completed successfully."

    with open(output_path, "w") as file_handle:
        file_handle.write(content)

    console.print(f"Markdown output saved to: {output_path}")


async def generate_gamma_presentation(results, filename: str):
    """Generate Gamma presentation."""
    try:
        gamma_client = GammaClient()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating Gamma presentation...", total=None)
            await asyncio.sleep(0)

            presentation = await gamma_client.create_presentation(results)

            progress.update(task, description="✅ Gamma presentation generated")

        if presentation.presentation_url:
            console.print(f"Gamma presentation created: {presentation.presentation_url}")
        else:
            console.print("Gamma presentation generated successfully")

    except Exception as exc:
        console.print(f"[yellow]Warning: Could not generate Gamma presentation: {exc}[/yellow]")


