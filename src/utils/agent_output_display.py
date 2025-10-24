"""
Agent Output Display Module

Provides beautiful terminal formatting and display for agent outputs and API calls.
Allows visibility into what each agent produces and what API calls are made.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.tree import Tree
from rich import box

logger = logging.getLogger(__name__)
console = Console()


class AgentOutputDisplay:
    """Display agent outputs and API calls in a beautiful terminal format."""
    
    def __init__(self, enabled: bool = True):
        """
        Initialize the display.
        
        Args:
            enabled: Whether to display output (can be disabled via feature flag)
        """
        self.enabled = enabled
        self.console = Console()
    
    def display_agent_result(
        self, 
        agent_name: str, 
        result: Dict[str, Any],
        show_full_data: bool = False
    ):
        """
        Display agent result in a formatted panel.
        
        Args:
            agent_name: Name of the agent
            result: Agent result dictionary
            show_full_data: Whether to show full data or just summary
        """
        if not self.enabled:
            return
        
        try:
            # Create header
            success = result.get('success', False)
            confidence = result.get('confidence', 0.0)
            confidence_level = result.get('confidence_level', 'UNKNOWN')
            execution_time = result.get('execution_time', 0.0)
            
            status_emoji = "✅" if success else "❌"
            title = f"{status_emoji} {agent_name} Result"
            
            # Create content
            content_parts = []
            
            # Status line
            status_line = f"[bold]Status:[/bold] {'Success' if success else 'Failed'}"
            content_parts.append(status_line)
            
            # Confidence line
            confidence_color = self._get_confidence_color(confidence)
            confidence_line = f"[bold]Confidence:[/bold] [{confidence_color}]{confidence:.2%}[/{confidence_color}] ({confidence_level})"
            content_parts.append(confidence_line)
            
            # Execution time
            time_line = f"[bold]Execution Time:[/bold] {execution_time:.2f}s"
            content_parts.append(time_line)
            
            # Token count if available
            token_count = result.get('token_count', 0)
            if token_count > 0:
                token_line = f"[bold]Tokens Used:[/bold] {token_count:,}"
                content_parts.append(token_line)
            
            # Error message if failed
            if not success:
                error_msg = result.get('error_message', 'Unknown error')
                content_parts.append(f"\n[bold red]Error:[/bold red] {error_msg}")
            
            # Limitations if any
            limitations = result.get('limitations', [])
            if limitations:
                content_parts.append("\n[bold yellow]Limitations:[/bold yellow]")
                for limitation in limitations:
                    content_parts.append(f"  • {limitation}")
            
            # Data summary
            data = result.get('data', {})
            if data:
                content_parts.append("\n[bold cyan]Data Summary:[/bold cyan]")
                summary = self._create_data_summary(agent_name, data)
                content_parts.append(summary)
            
            # Full data if requested
            if show_full_data and data:
                content_parts.append("\n[bold]Full Data:[/bold]")
                data_str = json.dumps(data, indent=2, default=str)
                syntax = Syntax(data_str, "json", theme="monokai", line_numbers=False)
                content_parts.append(str(syntax))
            
            content = "\n".join(content_parts)
            
            # Display panel
            panel = Panel(
                content,
                title=title,
                border_style="green" if success else "red",
                box=box.ROUNDED
            )
            
            self.console.print(panel)
            self.console.print()  # Add spacing
            
        except Exception as e:
            logger.error(f"Error displaying agent result: {e}")
    
    def display_markdown_preview(
        self, 
        markdown_content: str, 
        title: str = "Formatted Report Preview",
        max_lines: Optional[int] = 50
    ):
        """
        Display a preview of the formatted markdown report.
        
        Args:
            markdown_content: The markdown content to display
            title: Title for the preview panel
            max_lines: Maximum number of lines to display (None for all)
        """
        if not self.enabled:
            return
        
        try:
            # Truncate if needed
            lines = markdown_content.split('\n')
            if max_lines and len(lines) > max_lines:
                display_content = '\n'.join(lines[:max_lines])
                display_content += f"\n\n... ({len(lines) - max_lines} more lines)"
            else:
                display_content = markdown_content
            
            # Create markdown object
            md = Markdown(display_content)
            
            # Display in panel
            panel = Panel(
                md,
                title=f"📄 {title}",
                border_style="blue",
                box=box.ROUNDED
            )
            
            self.console.print(panel)
            self.console.print()  # Add spacing
            
        except Exception as e:
            logger.error(f"Error displaying markdown preview: {e}")
    
    def display_gamma_api_call(
        self, 
        input_text: str,
        parameters: Dict[str, Any],
        show_full_text: bool = False
    ):
        """
        Display the Gamma API call details before sending.
        
        Args:
            input_text: The markdown text being sent to Gamma
            parameters: API call parameters
            show_full_text: Whether to show full input text or just summary
        """
        if not self.enabled:
            return
        
        try:
            content_parts = []
            
            # API endpoint
            content_parts.append("[bold]Endpoint:[/bold] /api/generate")
            
            # Parameters
            content_parts.append("\n[bold cyan]Parameters:[/bold cyan]")
            
            param_table = Table(show_header=False, box=None, padding=(0, 2))
            param_table.add_column("Parameter", style="bold")
            param_table.add_column("Value")
            
            for key, value in parameters.items():
                if key == 'input_text' and not show_full_text:
                    # Show truncated version
                    text_preview = input_text[:200] + "..." if len(input_text) > 200 else input_text
                    param_table.add_row(key, text_preview)
                else:
                    param_table.add_row(key, str(value))
            
            # Input text stats
            content_parts.append("\n[bold]Input Text Statistics:[/bold]")
            lines = input_text.split('\n')
            words = input_text.split()
            chars = len(input_text)
            
            stats_table = Table(show_header=False, box=None, padding=(0, 2))
            stats_table.add_column("Metric", style="bold")
            stats_table.add_column("Value", style="cyan")
            
            stats_table.add_row("Lines", f"{len(lines):,}")
            stats_table.add_row("Words", f"{len(words):,}")
            stats_table.add_row("Characters", f"{chars:,}")
            
            # Display panel with tables
            from rich.console import Group
            
            combined_group = Group(
                "\n".join(content_parts),
                "",
                param_table,
                "",
                stats_table
            )
            
            panel = Panel(
                combined_group,
                title="🚀 Gamma API Call",
                border_style="magenta",
                box=box.ROUNDED
            )
            
            self.console.print(panel)
            
            # Show full text preview if requested
            if show_full_text:
                self.display_markdown_preview(
                    input_text, 
                    title="Full Input Text for Gamma",
                    max_lines=None
                )
            
            self.console.print()  # Add spacing
            
        except Exception as e:
            logger.error(f"Error displaying Gamma API call: {e}")
    
    def display_all_agent_results(
        self, 
        agent_results: Dict[str, Dict[str, Any]],
        title: str = "All Agent Results Summary"
    ):
        """
        Display a summary of all agent results in a table.
        
        Args:
            agent_results: Dictionary of agent name to result
            title: Title for the summary
        """
        if not self.enabled:
            return
        
        try:
            table = Table(title=title, box=box.ROUNDED)
            
            table.add_column("Agent", style="bold cyan")
            table.add_column("Status", justify="center")
            table.add_column("Confidence", justify="right")
            table.add_column("Time (s)", justify="right")
            table.add_column("Tokens", justify="right")
            
            for agent_name, result in agent_results.items():
                success = result.get('success', False)
                confidence = result.get('confidence', 0.0)
                execution_time = result.get('execution_time', 0.0)
                token_count = result.get('token_count', 0)
                
                status = "✅" if success else "❌"
                confidence_color = self._get_confidence_color(confidence)
                confidence_str = f"[{confidence_color}]{confidence:.1%}[/{confidence_color}]"
                
                table.add_row(
                    agent_name,
                    status,
                    confidence_str,
                    f"{execution_time:.2f}",
                    f"{token_count:,}" if token_count > 0 else "-"
                )
            
            self.console.print(table)
            self.console.print()  # Add spacing
            
        except Exception as e:
            logger.error(f"Error displaying all agent results: {e}")
    
    def _get_confidence_color(self, confidence: float) -> str:
        """Get color based on confidence level."""
        if confidence >= 0.9:
            return "green"
        elif confidence >= 0.7:
            return "yellow"
        else:
            return "red"
    
    def _create_data_summary(self, agent_name: str, data: Dict[str, Any]) -> str:
        """Create a summary of the data based on agent type."""
        summary_parts = []
        
        # SegmentationAgent specific
        if 'segmentation_summary' in data:
            seg_summary = data['segmentation_summary']
            summary_parts.append(f"  • Paid: {seg_summary.get('paid_count', 0)} ({seg_summary.get('paid_percentage', 0):.1f}%)")
            summary_parts.append(f"  • Free: {seg_summary.get('free_count', 0)} ({seg_summary.get('free_percentage', 0):.1f}%)")
            
            if 'tier_distribution' in seg_summary:
                tier_dist = seg_summary['tier_distribution']
                summary_parts.append(f"  • Tier breakdown: {tier_dist}")
        
        # CategoryAgent specific
        elif 'categories' in data:
            categories = data['categories']
            if isinstance(categories, list):
                summary_parts.append(f"  • Found {len(categories)} categories")
                for cat in categories[:5]:  # Show top 5
                    if isinstance(cat, dict):
                        name = cat.get('name', 'Unknown')
                        count = cat.get('count', 0)
                        summary_parts.append(f"    - {name}: {count}")
        
        # SentimentAgent specific
        elif 'sentiment_distribution' in data:
            sent_dist = data['sentiment_distribution']
            summary_parts.append(f"  • Sentiment distribution: {sent_dist}")
        
        # ExampleExtractionAgent specific
        elif 'extracted_examples' in data:
            examples = data['extracted_examples']
            summary_parts.append(f"  • Extracted {len(examples)} examples")
        
        # Generic fallback
        else:
            # Show top-level keys with counts if they're lists
            for key, value in data.items():
                if isinstance(value, list):
                    summary_parts.append(f"  • {key}: {len(value)} items")
                elif isinstance(value, dict):
                    summary_parts.append(f"  • {key}: {len(value)} keys")
                else:
                    summary_parts.append(f"  • {key}: {value}")
        
        return "\n".join(summary_parts) if summary_parts else "  No summary available"


# Global display instance
_display_instance: Optional[AgentOutputDisplay] = None


def get_display() -> AgentOutputDisplay:
    """Get the global display instance."""
    global _display_instance
    if _display_instance is None:
        _display_instance = AgentOutputDisplay()
    return _display_instance


def set_display_enabled(enabled: bool):
    """Enable or disable the display globally."""
    global _display_instance
    if _display_instance is None:
        _display_instance = AgentOutputDisplay(enabled=enabled)
    else:
        _display_instance.enabled = enabled


def display_agent_result(agent_name: str, result: Dict[str, Any], show_full_data: bool = False):
    """Convenience function to display agent result."""
    get_display().display_agent_result(agent_name, result, show_full_data)


def display_markdown_preview(markdown_content: str, title: str = "Formatted Report Preview", max_lines: Optional[int] = 50):
    """Convenience function to display markdown preview."""
    get_display().display_markdown_preview(markdown_content, title, max_lines)


def display_gamma_api_call(input_text: str, parameters: Dict[str, Any], show_full_text: bool = False):
    """Convenience function to display Gamma API call."""
    get_display().display_gamma_api_call(input_text, parameters, show_full_text)


def display_all_agent_results(agent_results: Dict[str, Dict[str, Any]], title: str = "All Agent Results Summary"):
    """Convenience function to display all agent results."""
    get_display().display_all_agent_results(agent_results, title)

