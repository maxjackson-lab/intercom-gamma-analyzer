"""
CLI entrypoint definition.

This module defines the Click group used by the main CLI application.
"""

import asyncio
import sys
from pathlib import Path

import click
from rich.panel import Panel

from src.cli.utils import console
from src.config.settings import settings
from src.utils.logger import setup_logging


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--output-dir', default='outputs', help='Output directory for reports')
@click.option('--skip-validation', is_flag=True, help='Skip API key validation on startup (for testing)')
def cli(verbose: bool, output_dir: str, skip_validation: bool):
    """Intercom to Gamma Analysis Tool - Dual Mode Analysis"""
    setup_logging(verbose)
    settings.output_directory = output_dir

    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)

    console.print(Panel.fit(
        "[bold blue]Intercom to Gamma Analysis Tool[/bold blue]\n"
        "Dual-mode conversation analysis for Voice of Customer and trend analysis",
        border_style="blue"
    ))

    # Validate configuration on startup (unless skipped)
    if not skip_validation:
        try:
            from src.services.config_validator import (
                validate_configuration,
                validate_environment_variables,
            )

            # Run async validation
            validation_results = asyncio.run(validate_configuration())
            _ = validate_environment_variables()

            # Log summary
            status_icons = []
            for service, is_valid in validation_results.items():
                icon = "✅" if is_valid else "❌"
                status_icons.append(f"{service}: {icon}")

            console.print(f"[dim]API Keys: {', '.join(status_icons)}[/dim]")

        except ValueError as e:
            # Critical API keys missing - fail fast
            console.print(f"[bold red]❌ Configuration Error: {e}[/bold red]")
            console.print("[yellow]Fix API keys in environment variables or use --skip-validation to bypass[/yellow]")
            sys.exit(1)
        except Exception as e:
            # Non-critical validation error - warn but continue
            console.print(f"[yellow]⚠️  Configuration validation warning: {e}[/yellow]")
            console.print("[dim]Continuing with limited functionality...[/dim]")


__all__ = ['cli']

