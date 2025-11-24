"""
Gamma presentation generation utilities extracted from the CLI entrypoint.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from src.cli.utils import console
from src.services.gamma_generator import GammaGenerator
from src.services.gamma_generator_service import (
    generate_all_gamma_presentations_async,
    generate_gamma_presentation_async,
)
from src.services.google_docs_exporter import GoogleDocsExporter


# NOTE: These helpers run asyncio.run(...) and must only be called from synchronous CLI contexts.
def run_gamma_generation(
    analysis_file: str,
    style: str,
    export_pdf: bool,
    export_pptx: bool,
    export_docs: bool,
    output_dir: str,
) -> None:
    """Generate a single Gamma presentation style from a saved analysis."""
    try:
        # Load analysis results
        with open(analysis_file, "r", encoding="utf-8") as f:
            analysis_results = json.load(f)

        console.print("[bold blue]Generating Gamma Presentation[/bold blue]")
        console.print(f"Style: {style}")
        console.print(f"Analysis file: {analysis_file}")
        console.print(f"Output directory: {output_dir}")

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # Initialize services
        gamma_generator = GammaGenerator()
        docs_exporter = GoogleDocsExporter()

        # Determine export format
        export_format = None
        if export_pdf:
            export_format = "pdf"
        elif export_pptx:
            export_format = "pptx"

        # Generate Gamma presentation
        console.print(f"[yellow]Generating {style} presentation...[/yellow]")
        result = asyncio.run(
            generate_gamma_presentation_async(
                gamma_generator=gamma_generator,
                analysis_results=analysis_results,
                style=style,
                export_format=export_format,
                output_dir=output_path,
            )
        )

        # Display results
        console.print("[green]✅ Gamma presentation generated successfully![/green]")
        console.print(f"Gamma URL: {result['gamma_url']}")
        console.print(f"Generation ID: {result['generation_id']}")
        console.print(f"Credits used: {result['credits_used']}")
        console.print(f"Generation time: {result['generation_time_seconds']:.1f} seconds")

        if result.get("export_url"):
            console.print(f"Export URL: {result['export_url']}")

        # Generate Google Docs export if requested
        if export_docs:
            console.print("[yellow]Generating Google Docs markdown...[/yellow]")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            docs_filename = f"analysis_{style}_{timestamp}.md"
            docs_path = output_path / docs_filename

            docs_exporter.export_to_markdown(
                analysis_results=analysis_results,
                output_path=docs_path,
                style=style,
            )

            console.print("[green]✅ Google Docs markdown generated![/green]")
            console.print(f"Markdown file: {docs_path}")

    except Exception as exc:
        console.print(f"[red]Error generating Gamma presentation: {exc}[/red]")
        import traceback

        traceback.print_exc()
        sys.exit(1)


# NOTE: These helpers run asyncio.run(...) and must only be called from synchronous CLI contexts.
def run_bulk_gamma_generation(
    analysis_file: str,
    export_pdf: bool,
    export_pptx: bool,
    export_docs: bool,
    output_dir: str,
) -> None:
    """Generate all Gamma presentation styles from a saved analysis."""
    try:
        # Load analysis results
        with open(analysis_file, "r", encoding="utf-8") as f:
            analysis_results = json.load(f)

        console.print("[bold blue]Generating All Gamma Presentations[/bold blue]")
        console.print(f"Analysis file: {analysis_file}")
        console.print(f"Output directory: {output_dir}")

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # Initialize services
        gamma_generator = GammaGenerator()
        docs_exporter = GoogleDocsExporter()

        # Determine export format
        export_format = None
        if export_pdf:
            export_format = "pdf"
        elif export_pptx:
            export_format = "pptx"

        # Generate all presentation styles
        console.print("[yellow]Generating all presentation styles...[/yellow]")
        results = asyncio.run(
            generate_all_gamma_presentations_async(
                gamma_generator=gamma_generator,
                analysis_results=analysis_results,
                export_format=export_format,
                output_dir=output_path,
            )
        )

        # Display results
        console.print("[green]✅ All Gamma presentations generated![/green]")

        for style, result in results.items():
            if result.get("gamma_url"):
                console.print(f"\n[bold]{style.title()} Presentation:[/bold]")
                console.print(f"  Gamma URL: {result['gamma_url']}")
                console.print(f"  Credits used: {result['credits_used']}")
                console.print(f"  Generation time: {result['generation_time_seconds']:.1f} seconds")

                if result.get("export_url"):
                    console.print(f"  Export URL: {result['export_url']}")
            else:
                console.print(f"\n[red]{style.title()} Presentation: Failed - {result.get('error', 'Unknown error')}[/red]")

        # Generate Google Docs exports if requested
        if export_docs:
            console.print("\n[yellow]Generating Google Docs markdown files...[/yellow]")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            for style in ["executive", "detailed", "training"]:
                docs_filename = f"analysis_{style}_{timestamp}.md"
                docs_path = output_path / docs_filename

                docs_exporter.export_to_markdown(
                    analysis_results=analysis_results,
                    output_path=docs_path,
                    style=style,
                )

                console.print(f"[green]✅ {style.title()} markdown: {docs_path}[/green]")

        # Show summary
        stats = gamma_generator.get_generation_statistics(results)
        console.print("\n[bold]Summary:[/bold]")
        console.print(f"  Total generations: {stats['total_generations']}")
        console.print(f"  Successful: {stats['successful_generations']}")
        console.print(f"  Failed: {stats['failed_generations']}")
        console.print(f"  Total credits used: {stats['total_credits_used']}")
        console.print(f"  Total time: {stats['total_time_seconds']:.1f} seconds")

    except Exception as exc:
        console.print(f"[red]Error generating Gamma presentations: {exc}[/red]")
        import traceback

        traceback.print_exc()
        sys.exit(1)

