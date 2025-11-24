"""
Interactive chat command helpers.
"""

from typing import Dict

import click
from rich.panel import Panel

from src.cli.utils import console


def _detect_flag_overrides() -> Dict[str, bool]:
    """Return a map indicating which chat flags were explicitly provided."""
    ctx = click.get_current_context(silent=True)
    if ctx is None:
        return {}

    overrides: Dict[str, bool] = {}

    try:
        from click.core import ParameterSource
    except ImportError:
        return overrides

    for param in ("model", "enable_cache", "railway"):
        try:
            source = ctx.get_parameter_source(param)
        except (AttributeError, RuntimeError):
            continue

        overrides[param] = source not in (
            ParameterSource.DEFAULT,
            ParameterSource.DEFAULT_MAP,
        )

    return overrides


def _warn_unused_chat_flags(flag_overrides: Dict[str, bool]) -> None:
    """Emit a consolidated warning for chat flags that are currently ignored."""
    ignored_flags = []

    if flag_overrides.get("model"):
        ignored_flags.append("--model")
    if flag_overrides.get("enable_cache"):
        ignored_flags.append("--enable-cache")
    if flag_overrides.get("railway"):
        ignored_flags.append("--railway")

    if not ignored_flags:
        return

    flag_list = ", ".join(ignored_flags)
    console.print(
        f"[yellow]⚠️  The chat flags {flag_list} are currently ignored. "
        "They remain for backward compatibility and may be removed in a future release.[/yellow]"
    )


def run_chat_interface(
    model: str,
    enable_cache: bool,
    railway: bool,
) -> None:
    """Start the terminal-based chat interface."""
    _warn_unused_chat_flags(_detect_flag_overrides())

    console.print(
        Panel.fit(
            "[bold green]🤖 Intercom Analysis Tool - Chat Interface[/bold green]\n"
            "Natural language interface for generating analysis reports",
            border_style="green",
        )
    )

    try:
        from chat.chat_interface import ChatInterface
        from chat.terminal_ui import TerminalChatUI
        from config.settings import Settings

        settings = Settings()
        chat_interface = ChatInterface(settings)

        console.print("[green]✅ Chat interface initialized successfully[/green]")
        console.print("[dim]Type 'help' for available commands, 'quit' to exit[/dim]")

        terminal_ui = TerminalChatUI(chat_interface.translator, chat_interface.suggestion_engine)
        terminal_ui.start_chat()

    except ImportError as exc:
        console.print(f"[red]❌ Failed to import chat components: {exc}[/red]")
        console.print("[yellow]Make sure all chat dependencies are installed[/yellow]")
    except Exception as exc:
        console.print(f"[red]❌ Failed to start chat interface: {exc}[/red]")
        console.print("[yellow]Check the logs for more details[/yellow]")

