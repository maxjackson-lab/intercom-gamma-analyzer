"""
CLI Utilities Module - Helper functions for CLI operations.

This module contains utility functions for CLI operations including
display functions, output handling, and common CLI patterns.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.config.settings import settings
from src.services.gamma_client import GammaClient, GammaAPIError
from src.services.gamma_generator import GammaGenerator
from src.utils.time_utils import generate_descriptive_filename

console = Console()
logger = logging.getLogger(__name__)


def display_results(results: Any, analysis_type: str = "analysis"):
    """Display analysis results in a formatted way."""
    console.print(f"\n[bold blue]{analysis_type.title()} Results[/bold blue]")

    if hasattr(results, 'total_conversations'):
        console.print(f"Total conversations: {results.total_conversations:,}")

    if hasattr(results, 'analysis_duration_seconds'):
        console.print(f"Analysis duration: {results.analysis_duration_seconds:.2f}s")

    if hasattr(results, 'key_trends') and results.key_trends:
        console.print(f"\n[bold]Key Trends:[/bold]")
        for trend in results.key_trends[:5]:
            console.print(f"• {trend.get('name', 'Unknown')}: {trend.get('description', 'No description')}")


def save_outputs(results: Any, filename: str, output_format: str = 'json') -> List[str]:
    """Save analysis results to output files."""
    output_dir = Path(settings.output_directory)
    output_dir.mkdir(exist_ok=True)
    saved_files = []

    # Save JSON output
    if output_format in ['json', 'all']:
        json_path = output_dir / f"{filename}.json"
        with open(json_path, 'w') as f:
            json.dump(results.dict() if hasattr(results, 'dict') else results, f, indent=2, default=str)
        saved_files.append(str(json_path))
        console.print(f"JSON output saved to: {json_path}")

    # Save Markdown output if available
    if output_format in ['markdown', 'all'] and hasattr(results, 'analysis_content'):
        md_path = output_dir / f"{filename}.md"
        with open(md_path, 'w') as f:
            f.write(results.analysis_content)
        saved_files.append(str(md_path))
        console.print(f"Markdown output saved to: {md_path}")

    return saved_files


async def generate_gamma_presentation(results: Any, filename: str) -> Optional[str]:
    """Generate Gamma presentation from results."""
    try:
        gamma_client = GammaClient()

        # Prepare content for Gamma
        if hasattr(results, 'analysis_content'):
            content = results.analysis_content
        elif hasattr(results, 'dict'):
            content = json.dumps(results.dict(), indent=2, default=str)
        else:
            content = str(results)

        # Generate presentation
        generation_id = await gamma_client.generate_presentation(
            input_text=content,
            format="presentation",
            text_mode="preserve",
            theme_name="Night Sky",
            text_options={
                "tone": "professional, analytical",
                "audience": "executives, leadership team"
            }
        )

        # Poll for completion
        status = await gamma_client.poll_generation(generation_id, max_polls=30, poll_interval=2.0)

        if status.get('status') == 'completed':
            gamma_url = status.get('gammaUrl')
            if gamma_url:
                console.print(f"Gamma presentation created: {gamma_url}")
                return gamma_url
            else:
                console.print("[yellow]Gamma generation completed but no URL returned[/yellow]")
        else:
            console.print(f"[yellow]Gamma generation status: {status.get('status')}[/yellow]")

    except GammaAPIError as e:
        console.print(f"[yellow]Gamma generation failed: {e}[/yellow]")
    except Exception as e:
        console.print(f"[yellow]Unexpected error during Gamma generation: {e}[/yellow]")

    return None


def parse_date_range(start_date: Optional[str], end_date: Optional[str], time_period: Optional[str] = None) -> tuple[datetime, datetime]:
    """Parse date range from various input formats."""
    from datetime import timedelta

    if time_period:
        end_dt = datetime.now()

        if time_period == 'yesterday':
            start_dt = end_dt - timedelta(days=1)
            end_dt = end_dt - timedelta(days=1)
        elif time_period == 'week':
            start_dt = end_dt - timedelta(weeks=1)
        elif time_period == 'month':
            start_dt = end_dt - timedelta(days=30)
        elif time_period == 'quarter':
            start_dt = end_dt - timedelta(days=90)
        elif time_period == 'year':
            start_dt = end_dt - timedelta(days=365)
        else:
            raise ValueError(f"Unknown time period: {time_period}")
    elif start_date and end_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        raise ValueError("Must provide either time_period or both start_date and end_date")

    return start_dt, end_dt


def validate_inputs(**kwargs) -> bool:
    """Validate common CLI inputs."""
    # Check date formats
    for date_field in ['start_date', 'end_date']:
        if date_field in kwargs and kwargs[date_field]:
            try:
                datetime.strptime(kwargs[date_field], '%Y-%m-%d')
            except ValueError:
                console.print(f"[red]Invalid date format for {date_field}. Use YYYY-MM-DD[/red]")
                return False

    # Check that end date is after start date
    if 'start_date' in kwargs and 'end_date' in kwargs and kwargs['start_date'] and kwargs['end_date']:
        start_dt = datetime.strptime(kwargs['start_date'], '%Y-%m-%d')
        end_dt = datetime.strptime(kwargs['end_date'], '%Y-%m-%d')
        if end_dt <= start_dt:
            console.print("[red]End date must be after start date[/red]")
            return False

    return True


def show_progress(message: str, total: Optional[int] = None):
    """Show progress indicator for long-running operations."""
    from rich.progress import Progress, SpinnerColumn, TextColumn

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(message, total=total)
        return progress, task


def display_summary_table(data: List[Dict[str, Any]], title: str, columns: List[str]):
    """Display data in a formatted table."""
    table = Table(show_header=True, header_style="bold magenta")
    table.title = title

    # Add columns
    for col in columns:
        table.add_column(col.title().replace('_', ' '), style="cyan")

    # Add rows
    for row in data:
        table.add_row(*[str(row.get(col, '')) for col in columns])

    console.print(table)


def create_output_filename(prefix: str, start_date: datetime, end_date: datetime, file_type: str = 'json') -> str:
    """Create a descriptive output filename."""
    return generate_descriptive_filename(prefix, start_date, end_date, file_type=file_type)


def log_operation_start(operation: str, **kwargs):
    """Log the start of an operation with parameters."""
    logger.info(f"Starting {operation}")
    if kwargs:
        logger.debug(f"Parameters: {kwargs}")


def log_operation_end(operation: str, success: bool, duration: Optional[float] = None, **results):
    """Log the end of an operation with results."""
    status = "completed successfully" if success else "failed"
    duration_str = f" in {duration:.2f}s" if duration else ""

    logger.info(f"{operation.title()} {status}{duration_str}")
    if results:
        logger.debug(f"Results: {results}")


def handle_error(error: Exception, operation: str, show_traceback: bool = False):
    """Handle and log errors consistently."""
    logger.error(f"{operation} failed: {error}")

    if show_traceback:
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

    console.print(f"[red]Error in {operation}: {error}[/red]")


def confirm_action(message: str, default: bool = False) -> bool:
    """Ask user to confirm an action."""
    from rich.prompt import Confirm
    return Confirm.ask(message, default=default)


def select_option(message: str, options: List[str], default: Optional[str] = None) -> str:
    """Ask user to select from a list of options."""
    from rich.prompt import Prompt

    if default and default in options:
        prompt_msg = f"{message} (default: {default})"
    else:
        prompt_msg = message

    while True:
        choice = Prompt.ask(prompt_msg, default=default)
        if choice in options:
            return choice
        console.print(f"[red]Invalid choice. Please select from: {', '.join(options)}[/red]")


def get_multiline_input(message: str) -> str:
    """Get multiline input from user."""
    console.print(f"{message} (press Ctrl+D to finish):")
    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass

    return '\n'.join(lines)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"


def check_file_exists(filepath: str, create_if_missing: bool = False) -> bool:
    """Check if file exists, optionally create directory."""
    path = Path(filepath)

    if create_if_missing and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    exists = path.exists()
    if not exists and not create_if_missing:
        console.print(f"[yellow]Warning: File not found: {filepath}[/yellow]")

    return exists


def backup_file(filepath: str) -> Optional[str]:
    """Create a backup of a file."""
    path = Path(filepath)

    if not path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(f".backup_{timestamp}{path.suffix}")

    import shutil
    shutil.copy2(path, backup_path)

    console.print(f"Backup created: {backup_path}")
    return str(backup_path)


def cleanup_old_files(directory: str, pattern: str, keep_days: int = 30):
    """Clean up old files matching a pattern."""
    import glob
    from datetime import timedelta

    cutoff_date = datetime.now() - timedelta(days=keep_days)
    dir_path = Path(directory)

    if not dir_path.exists():
        return

    # Find files matching pattern
    file_pattern = dir_path / pattern
    files = list(file_pattern.parent.glob(file_pattern.name))

    cleaned_count = 0
    for file_path in files:
        if file_path.stat().st_mtime < cutoff_date.timestamp():
            file_path.unlink()
            cleaned_count += 1

    if cleaned_count > 0:
        console.print(f"Cleaned up {cleaned_count} old files from {directory}")


def get_system_info() -> Dict[str, Any]:
    """Get system information for debugging."""
    import platform
    import psutil

    return {
        'platform': platform.platform(),
        'python_version': platform.python_version(),
        'cpu_count': psutil.cpu_count(),
        'memory_gb': psutil.virtual_memory().total / (1024**3),
        'disk_free_gb': psutil.disk_usage('/').free / (1024**3)
    }


def show_system_info():
    """Display system information."""
    info = get_system_info()

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan")
    table.add_column("Value", style="green")

    for key, value in info.items():
        if isinstance(value, float):
            table.add_row(key.replace('_', ' ').title(), f"{value:.1f}")
        else:
            table.add_row(key.replace('_', ' ').title(), str(value))

    console.print(table)