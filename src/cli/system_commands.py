"""
System and utility CLI commands.

Low-risk commands for API testing, configuration display, and help.
Extracted from src/main.py as part of Phase 1.1 refactor.
"""

import asyncio
import sys
from typing import List, Tuple

from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.cli.utils import console, show_system_info
from src.config.settings import settings
from src.services.category_filters import CategoryFilters
from src.services.gamma_client import GammaClient
from src.services.intercom_sdk_service import IntercomSDKService
from src.services.openai_client import OpenAIClient
from src.utils.cli_help import help_system


def run_test_command():
    """Test API connections and configuration."""

    async def _execute_with_spinner(
        label: str, runner
    ) -> Tuple[str, str, str]:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"[cyan]Testing {label}...[/cyan]", total=None)
            try:
                success, detail = await runner()
                if success:
                    progress.update(
                        task,
                        description=f"[green]{label} connection successful[/green]",
                    )
                    status = "OK"
                else:
                    progress.update(
                        task, description=f"[red]{label} connection failed[/red]"
                    )
                    status = "FAILED"
                return label, status, detail
            finally:
                progress.stop_task(task)

    async def _test_services() -> List[Tuple[str, str, str]]:
        results: List[Tuple[str, str, str]] = []

        async def _test_intercom():
            service = IntercomSDKService()
            try:
                await service.test_connection()
                return True, "Authenticated with Intercom SDK"
            except Exception as exc:
                return False, str(exc)
            finally:
                await service.close()

        async def _test_openai():
            client = OpenAIClient()
            try:
                await client.test_connection()
                return True, f"Model: {settings.openai_model}"
            except Exception as exc:
                return False, str(exc)

        async def _test_gamma():
            client = GammaClient()
            try:
                await client.test_connection()
                return True, "Generation endpoint reachable"
            except Exception as exc:
                return False, str(exc)
            finally:
                await client.close()

        results.append(await _execute_with_spinner("Intercom API", _test_intercom))
        results.append(await _execute_with_spinner("OpenAI API", _test_openai))

        if settings.gamma_api_key:
            results.append(await _execute_with_spinner("Gamma API", _test_gamma))
        else:
            results.append(
                (
                    "Gamma API",
                    "SKIPPED",
                    "Set GAMMA_API_KEY to enable Gamma tests",
                )
            )

        return results

    console.print("[bold green]Testing API Connections[/bold green]\n")
    test_results = asyncio.run(_test_services())

    summary = Table(
        title="API Connectivity Results",
        show_header=True,
        header_style="bold magenta",
    )
    summary.add_column("Service", style="cyan")
    summary.add_column("Status", style="green")
    summary.add_column("Details", style="white")

    has_failure = False
    for service, status, detail in test_results:
        if status == "FAILED":
            has_failure = True
            status_text = "[red]FAILED[/red]"
        elif status == "SKIPPED":
            status_text = "[yellow]SKIPPED[/yellow]"
        else:
            status_text = "[green]OK[/green]"
        summary.add_row(service, status_text, detail)

    console.print(summary)

    if has_failure:
        console.print(
            "[red]One or more connectivity tests failed. Please check credentials and retry.[/red]"
        )
        sys.exit(1)

    console.print("[bold green]All connectivity tests passed[/bold green]")


def run_system_info_command():
    """Show system information for debugging."""
    console.print("[bold green]System Diagnostics[/bold green]\n")
    show_system_info()


def run_config_command():
    """Show current configuration."""
    console.print("[bold green]Current Configuration[/bold green]\n")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Intercom API Version", settings.intercom_api_version)
    table.add_row("OpenAI Model", settings.openai_model)
    table.add_row("Default Analysis Days", str(settings.default_analysis_days))
    table.add_row("Output Directory", settings.output_directory)
    table.add_row("Log Level", settings.log_level)
    tier1 = ", ".join(settings.default_tier1_countries)
    table.add_row("Tier1 Countries", tier1)

    console.print(table)


def run_help_command():
    """Show comprehensive help message."""
    help_system.show_main_help()


def run_interactive_command():
    """Start interactive mode with guided prompts."""
    help_system.interactive_mode()


def run_list_commands_command():
    """List all available commands."""
    help_system.show_main_help()


def run_examples_command():
    """Show usage examples."""
    help_system.show_examples()


def run_show_categories_command():
    """List available taxonomy categories."""
    console.print("[bold green]Taxonomy Categories[/bold green]\n")
    filters = CategoryFilters()
    taxonomy = filters.taxonomy_config.get("primary_categories", {})

    if not taxonomy:
        console.print("[yellow]No taxonomy configuration found.[/yellow]")
        return

    table = Table(
        title="Available Categories",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Subcategories", style="magenta")
    table.add_column("Description", style="white")

    for category_name, config in taxonomy.items():
        subcategories = config.get("subcategories", [])
        subcat_summary = (
            f"{len(subcategories)} total"
            if subcategories
            else "None defined"
        )
        description = config.get("description", "No description provided")
        table.add_row(category_name, subcat_summary, description)

    console.print(table)
    console.print(
        "\n[bold]Analyze a category with:[/bold] python -m src.main analyze-category billing --time-period month"
    )








