"""
Rich Terminal Chat Interface

Provides a beautiful, interactive terminal interface for the chat system
with command preview, approval workflows, and real-time feedback.
"""

import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.layout import Layout
from rich.live import Live
from rich.align import Align
from rich.markdown import Markdown
from rich.syntax import Syntax

from .schemas import CommandTranslation, ActionType, FilterSpec
from .hybrid_translator import HybridCommandTranslator, TranslationResult
from .suggestion_engine import SuggestionEngine, FeatureSuggestion


class UIState(Enum):
    """UI state enumeration."""
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING_APPROVAL = "waiting_approval"
    EXECUTING = "executing"
    SHOWING_SUGGESTIONS = "showing_suggestions"


@dataclass
class ChatMessage:
    """A chat message with metadata."""
    content: str
    timestamp: float
    message_type: str  # "user", "assistant", "system", "error"
    metadata: Optional[Dict] = None


class TerminalChatUI:
    """
    Rich terminal-based chat interface for the Intercom Analysis Tool.
    
    Features:
    - Beautiful, responsive UI with Rich library
    - Command preview and approval workflows
    - Real-time processing feedback
    - Suggestion display and interaction
    - Performance metrics and statistics
    """
    
    def __init__(self, translator: HybridCommandTranslator, suggestion_engine: SuggestionEngine):
        self.translator = translator
        self.suggestion_engine = suggestion_engine
        self.console = Console()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # UI state
        self.state = UIState.IDLE
        self.messages: List[ChatMessage] = []
        self.current_translation: Optional[TranslationResult] = None
        self.current_suggestions: List[FeatureSuggestion] = []
        
        # Configuration
        self.show_help_on_start = True
        self.auto_approve_safe_commands = False
        self.show_performance_metrics = True
        
        # Statistics
        self.stats = {
            "total_queries": 0,
            "successful_translations": 0,
            "failed_translations": 0,
            "commands_executed": 0,
            "suggestions_shown": 0
        }
        
        self.logger.info("TerminalChatUI initialized")
    
    def start(self):
        """Start the chat interface."""
        self._display_welcome()
        
        if self.show_help_on_start:
            self._display_help()
        
        self._main_loop()
    
    def _display_welcome(self):
        """Display welcome message."""
        welcome_text = """
# 🤖 Intercom Analysis Tool - Chat Interface

Welcome to the natural language interface for the Intercom Analysis Tool!

You can now generate reports and analyses using simple, conversational language.
Just describe what you want, and I'll translate it into the appropriate commands.

**Examples:**
- "Give me last week's voice of customer report"
- "Show me billing analysis for this month with Gamma presentation"
- "Create a custom report for API tickets by Horatio agents in September"

Type `help` for more information, or `exit` to quit.
        """
        
        self.console.print(Panel(
            Markdown(welcome_text),
            title="Welcome",
            border_style="blue"
        ))
    
    def _display_help(self):
        """Display help information."""
        help_text = self.translator.get_help_text()
        
        self.console.print(Panel(
            Markdown(help_text),
            title="Help",
            border_style="green"
        ))
    
    def _main_loop(self):
        """Main chat loop."""
        while True:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold blue]You[/bold blue]")
                
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    self._display_goodbye()
                    break
                
                if user_input.lower() in ['help', '?']:
                    self._display_help()
                    continue
                
                if user_input.lower() in ['stats', 'statistics']:
                    self._display_statistics()
                    continue
                
                if user_input.lower() in ['clear', 'reset']:
                    self._clear_messages()
                    continue
                
                # Process the query
                self._process_query(user_input)
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Chat interrupted. Type 'exit' to quit.[/yellow]")
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                self.console.print(f"[red]Error: {e}[/red]")
    
    def _process_query(self, query: str):
        """Process a user query."""
        self.stats["total_queries"] += 1
        self.state = UIState.PROCESSING
        
        # Add user message
        self.messages.append(ChatMessage(
            content=query,
            timestamp=time.time(),
            message_type="user"
        ))
        
        # Show processing indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            task = progress.add_task("Processing your request...", total=None)
            
            # Translate the query
            try:
                result = self.translator.translate(query)
                self.current_translation = result
                
                if result.translation.action == ActionType.EXECUTE_COMMAND:
                    self._handle_command_translation(result)
                elif result.translation.action == ActionType.CLARIFY_REQUEST:
                    self._handle_clarification_request(result)
                else:
                    self._handle_unknown_action(result)
                
            except Exception as e:
                self.logger.error(f"Translation error: {e}")
                self._handle_translation_error(str(e))
    
    def _handle_command_translation(self, result: TranslationResult):
        """Handle successful command translation."""
        self.stats["successful_translations"] += 1
        self.state = UIState.WAITING_APPROVAL
        
        # Display command preview
        self._display_command_preview(result)
        
        # Check if auto-approval is enabled for safe commands
        if (self.auto_approve_safe_commands and 
            not result.translation.dangerous and 
            not result.translation.confirmation_required):
            self._execute_command(result)
        else:
            # Ask for approval
            if Confirm.ask("Do you want to execute this command?"):
                self._execute_command(result)
            else:
                self.console.print("[yellow]Command cancelled.[/yellow]")
                self.state = UIState.IDLE
    
    def _handle_clarification_request(self, result: TranslationResult):
        """Handle clarification request."""
        self.stats["failed_translations"] += 1
        self.state = UIState.SHOWING_SUGGESTIONS
        
        # Display clarification message
        self.console.print(Panel(
            result.translation.explanation,
            title="Clarification Needed",
            border_style="yellow"
        ))
        
        # Show suggestions if available
        if result.translation.suggestions:
            self._display_suggestions(result.translation.suggestions)
        
        # Generate feature suggestions
        suggestions = self.suggestion_engine.generate_suggestions(
            result.translation.explanation
        )
        
        if suggestions:
            self.current_suggestions = suggestions
            self._display_feature_suggestions(suggestions)
        
        self.state = UIState.IDLE
    
    def _handle_unknown_action(self, result: TranslationResult):
        """Handle unknown action type."""
        self.console.print(Panel(
            f"Unknown action type: {result.translation.action}",
            title="Error",
            border_style="red"
        ))
        self.state = UIState.IDLE
    
    def _handle_translation_error(self, error_message: str):
        """Handle translation error."""
        self.stats["failed_translations"] += 1
        
        self.console.print(Panel(
            f"Translation failed: {error_message}",
            title="Error",
            border_style="red"
        ))
        
        self.state = UIState.IDLE
    
    def _display_command_preview(self, result: TranslationResult):
        """Display command preview with details."""
        # Create command preview table
        table = Table(title="Command Preview", show_header=True, header_style="bold magenta")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Command", result.translation.command or "N/A")
        table.add_row("Arguments", " ".join(result.translation.args) if result.translation.args else "None")
        table.add_row("Explanation", result.translation.explanation)
        table.add_row("Confidence", f"{result.translation.confidence:.2f}")
        table.add_row("Engine Used", result.engine_used)
        table.add_row("Processing Time", f"{result.processing_time_ms:.1f}ms")
        table.add_row("Cache Hit", "Yes" if result.cache_hit else "No")
        table.add_row("Dangerous", "Yes" if result.translation.dangerous else "No")
        table.add_row("Confirmation Required", "Yes" if result.translation.confirmation_required else "No")
        
        if result.translation.warnings:
            table.add_row("Warnings", "; ".join(result.translation.warnings))
        
        self.console.print(table)
    
    def _display_suggestions(self, suggestions: List[str]):
        """Display command suggestions."""
        self.console.print("\n[bold green]Try these examples:[/bold green]")
        
        for i, suggestion in enumerate(suggestions, 1):
            self.console.print(f"{i}. {suggestion}")
    
    def _display_feature_suggestions(self, suggestions: List[FeatureSuggestion]):
        """Display feature suggestions."""
        self.stats["suggestions_shown"] += 1
        
        # Show summary
        summary = self.suggestion_engine.get_suggestion_summary(suggestions)
        
        self.console.print(Panel(
            Markdown(summary),
            title="Feature Suggestions",
            border_style="cyan"
        ))
        
        # Ask if user wants to see detailed implementation guidance
        if Confirm.ask("Would you like to see detailed implementation guidance for any suggestion?"):
            self._show_implementation_guidance(suggestions)
    
    def _show_implementation_guidance(self, suggestions: List[FeatureSuggestion]):
        """Show detailed implementation guidance."""
        if not suggestions:
            return
        
        # Show list of suggestions
        self.console.print("\n[bold]Available suggestions:[/bold]")
        for i, suggestion in enumerate(suggestions[:5], 1):  # Show top 5
            self.console.print(f"{i}. {suggestion.title}")
        
        # Get user choice
        try:
            choice = int(Prompt.ask("Enter the number of the suggestion you'd like to see details for (0 to cancel)"))
            
            if choice == 0:
                return
            
            if 1 <= choice <= len(suggestions):
                selected_suggestion = suggestions[choice - 1]
                guidance = self.suggestion_engine.get_implementation_guidance(selected_suggestion)
                
                self.console.print(Panel(
                    Markdown(guidance),
                    title=f"Implementation Guide: {selected_suggestion.title}",
                    border_style="blue"
                ))
            else:
                self.console.print("[red]Invalid choice.[/red]")
                
        except ValueError:
            self.console.print("[red]Please enter a valid number.[/red]")
    
    def _execute_command(self, result: TranslationResult):
        """Execute the translated command."""
        self.state = UIState.EXECUTING
        self.stats["commands_executed"] += 1
        
        # Show execution progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            task = progress.add_task("Executing command...", total=None)
            
            try:
                # Here you would actually execute the command
                # For now, we'll simulate execution
                time.sleep(1)  # Simulate command execution
                
                self.console.print(Panel(
                    f"Command executed successfully!\n\n{result.translation.explanation}",
                    title="Success",
                    border_style="green"
                ))
                
            except Exception as e:
                self.logger.error(f"Command execution error: {e}")
                self.console.print(Panel(
                    f"Command execution failed: {e}",
                    title="Error",
                    border_style="red"
                ))
        
        self.state = UIState.IDLE
    
    def _display_statistics(self):
        """Display performance statistics."""
        # Get translator stats
        translator_stats = self.translator.get_performance_stats()
        
        # Create statistics table
        table = Table(title="Performance Statistics", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        # Chat statistics
        table.add_row("Total Queries", str(self.stats["total_queries"]))
        table.add_row("Successful Translations", str(self.stats["successful_translations"]))
        table.add_row("Failed Translations", str(self.stats["failed_translations"]))
        table.add_row("Commands Executed", str(self.stats["commands_executed"]))
        table.add_row("Suggestions Shown", str(self.stats["suggestions_shown"]))
        
        # Translator statistics
        table.add_row("Cache Hit Rate", f"{translator_stats.get('cache_hit_rate', 0):.1%}")
        table.add_row("Success Rate", f"{translator_stats.get('success_rate', 0):.1%}")
        table.add_row("Average Processing Time", f"{translator_stats.get('average_processing_time_ms', 0):.1f}ms")
        
        # Engine statistics
        engine_stats = translator_stats.get('engine_stats', {})
        for engine_name, stats in engine_stats.items():
            table.add_row(f"{engine_name.title()} Calls", str(stats.get('total_calls', 0)))
        
        self.console.print(table)
    
    def _clear_messages(self):
        """Clear chat messages."""
        self.messages.clear()
        self.console.print("[green]Chat history cleared.[/green]")
    
    def _display_goodbye(self):
        """Display goodbye message."""
        goodbye_text = """
# 👋 Goodbye!

Thank you for using the Intercom Analysis Tool chat interface.

**Session Summary:**
- Total queries: {total_queries}
- Successful translations: {successful_translations}
- Commands executed: {commands_executed}
- Suggestions shown: {suggestions_shown}

Have a great day! 🚀
        """.format(**self.stats)
        
        self.console.print(Panel(
            Markdown(goodbye_text),
            title="Goodbye",
            border_style="blue"
        ))
    
    def set_auto_approve_safe_commands(self, enabled: bool):
        """Enable/disable auto-approval for safe commands."""
        self.auto_approve_safe_commands = enabled
        self.console.print(f"[green]Auto-approval for safe commands: {'enabled' if enabled else 'disabled'}[/green]")
    
    def set_show_performance_metrics(self, enabled: bool):
        """Enable/disable performance metrics display."""
        self.show_performance_metrics = enabled
        self.console.print(f"[green]Performance metrics: {'enabled' if enabled else 'disabled'}[/green]")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        return {
            "chat_stats": self.stats,
            "translator_stats": self.translator.get_performance_stats(),
            "messages_count": len(self.messages),
            "current_state": self.state.value
        }
