"""
CLI interface for the chat system.
"""

import click
import logging
from typing import Optional

from .chat_interface import ChatInterface
from ..config.settings import Settings


@click.command()
@click.option('--config', '-c', help='Path to configuration file')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--test', is_flag=True, help='Test components and exit')
@click.option('--stats', is_flag=True, help='Show performance statistics and exit')
def chat(config: Optional[str], verbose: bool, test: bool, stats: bool):
    """
    Start the Intercom Analysis Tool chat interface.
    
    This provides a natural language interface for generating reports and analyses.
    """
    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Load settings
        settings = Settings()
        
        # Initialize chat interface
        chat_interface = ChatInterface(settings)
        
        if test:
            # Test components
            click.echo("Testing chat components...")
            results = chat_interface.test_components()
            
            for component, status in results.items():
                if component == "error":
                    click.echo(f"❌ Test failed: {status}")
                else:
                    status_icon = "✅" if status else "❌"
                    click.echo(f"{status_icon} {component}: {'OK' if status else 'FAILED'}")
            
            if all(status for component, status in results.items() if component != "error"):
                click.echo("🎉 All components are working correctly!")
            else:
                click.echo("⚠️  Some components failed tests.")
                raise click.Abort()
        
        elif stats:
            # Show statistics
            click.echo("Performance Statistics:")
            stats_data = chat_interface.get_performance_stats()
            
            # Display translator stats
            translator_stats = stats_data.get("translator_stats", {})
            click.echo(f"Total Queries: {translator_stats.get('total_queries', 0)}")
            click.echo(f"Success Rate: {translator_stats.get('success_rate', 0):.1%}")
            click.echo(f"Cache Hit Rate: {translator_stats.get('cache_hit_rate', 0):.1%}")
            click.echo(f"Average Processing Time: {translator_stats.get('average_processing_time_ms', 0):.1f}ms")
            
            # Display UI stats
            ui_stats = stats_data.get("ui_stats", {})
            chat_stats = ui_stats.get("chat_stats", {})
            click.echo(f"Commands Executed: {chat_stats.get('commands_executed', 0)}")
            click.echo(f"Suggestions Shown: {chat_stats.get('suggestions_shown', 0)}")
        
        else:
            # Start interactive chat
            click.echo("🚀 Starting Intercom Analysis Tool Chat Interface...")
            chat_interface.start_chat()
    
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        raise click.Abort()


if __name__ == '__main__':
    chat()
