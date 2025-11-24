"""
Canny analysis command implementations extracted from the main CLI module.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
import json

from src.analyzers.canny_analyzer import CannyAnalyzer
from src.cli.utils import console
from src.services.ai_model_factory import AIModelFactory
from src.services.canny_client import CannyClient
from src.services.gamma_generator import GammaGenerator
from src.utils.ai_client_helper import resolve_ai_model_choice
from src.utils.output_manager import get_output_file_path
from src.utils.time_utils import detect_period_type, generate_descriptive_filename


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
) -> Optional[Path]:
    """Run Canny product feedback analysis."""
    console.record = True
    log_output = ""
    output_file: Optional[Path] = None

    try:
        console.print("[bold blue]Starting Canny Analysis[/bold blue]")
        console.print(f"Date Range: {start_date} to {end_date}")
        console.print(f"AI Model: {ai_model}")
        console.print(f"Board ID: {board_id or 'All boards'}")

        # Initialize components
        ai_factory = AIModelFactory()
        canny_client = CannyClient()
        canny_analyzer = CannyAnalyzer(ai_factory)

        # Test Canny connection
        console.print("[yellow]Testing Canny API connection...[/yellow]")
        await canny_client.test_connection()
        console.print("[green]✅ Canny API connection successful[/green]")

        # Parse dates
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        # Detect period type from date range
        period_type, period_label = detect_period_type(start_dt, end_dt)

        # Fetch Canny data
        console.print("[yellow]Fetching Canny posts...[/yellow]")
        if board_id:
            posts = await canny_client.fetch_posts_by_date_range(
                start_date=start_dt,
                end_date=end_dt,
                board_id=board_id,
                include_comments=include_comments,
                include_votes=include_votes,
            )
        else:
            all_boards_posts = await canny_client.fetch_all_boards_posts(
                start_date=start_dt,
                end_date=end_dt,
                include_comments=include_comments,
                include_votes=include_votes,
            )
            posts = []
            for board_posts in all_boards_posts.values():
                posts.extend(board_posts)

        if not posts:
            console.print("[red]No Canny posts found for the specified date range.[/red]")
            return None

        console.print(f"[green]Found {len(posts)} Canny posts[/green]")

        # Run sentiment analysis
        console.print("[yellow]Running sentiment analysis...[/yellow]")

        ai_model_enum = resolve_ai_model_choice(ai_model)

        analysis_results = await canny_analyzer.analyze_canny_sentiment(
            posts=posts,
            ai_model=ai_model_enum,
            enable_fallback=enable_fallback,
        )

        # Save results via output manager
        output_filename = generate_descriptive_filename("Canny_Analysis", start_date, end_date, file_type="json")
        output_file = get_output_file_path(output_filename, base_dir=output_dir)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "analysis_results": analysis_results,
                    "metadata": {
                        "start_date": start_date,
                        "end_date": end_date,
                        "period_type": period_type,
                        "period_label": period_label,
                        "board_id": board_id,
                        "ai_model": ai_model,
                        "total_posts": len(posts),
                        "generated_at": datetime.now().isoformat(),
                    },
                },
                f,
                indent=2,
            )

        console.print("[green]Canny analysis completed![/green]")
        console.print(f"Results saved to: {output_file}")

        # Generate Gamma presentation if requested
        if generate_gamma:
            console.print("[yellow]Generating Gamma presentation...[/yellow]")

            gamma_generator = GammaGenerator()

            try:
                gamma_result = await gamma_generator.generate_from_canny_analysis(
                    canny_results=analysis_results,
                    style="executive",
                    export_format=None,
                    output_dir=output_file.parent,
                )

                console.print(f"[green]✅ Gamma URL: {gamma_result['gamma_url']}[/green]")

                gamma_filename = generate_descriptive_filename("Canny_Gamma_Metadata", start_date, end_date, file_type="json")
                gamma_output = output_file.parent / gamma_filename
                with open(gamma_output, "w", encoding="utf-8") as f:
                    json.dump(gamma_result, f, indent=2)

                console.print(f"Gamma metadata saved to: {gamma_output}")

            except Exception as exc:
                console.print(f"[red]Gamma generation failed: {exc}[/red]")
                console.print("[yellow]Canny analysis results still saved to JSON[/yellow]")

        # Display insights
        insights = analysis_results.get("insights", [])
        if insights:
            console.print("\n[bold]Key Insights:[/bold]")
            for insight in insights[:5]:
                console.print(f"• {insight}")

        return output_file

    except Exception as exc:
        console.print(f"[red]Canny analysis failed: {exc}[/red]")
        raise
    finally:
        log_output = console.export_text(clear=True)
        console.record = False
        if log_output:
            log_path = (
                output_file.with_suffix(".log")
                if output_file
                else get_output_file_path(
                    f"canny_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
                    base_dir=output_dir,
                )
            )
            log_path.write_text(log_output, encoding="utf-8")
            console.print(f"[dim]🗂️  Complete log saved to: {log_path}[/dim]")

