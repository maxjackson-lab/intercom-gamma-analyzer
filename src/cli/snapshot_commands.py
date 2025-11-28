"""
Snapshot Commands Module - Snapshot listing, schema export, and comparison commands.

This module contains commands for managing and analyzing historical snapshots,
extracted from src/cli/commands.py as part of Phase 1.2 refactor.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.services.duckdb_storage import DuckDBStorage
from src.services.historical_snapshot_service import HistoricalSnapshotService

console = Console()
logger = logging.getLogger(__name__)

async def list_snapshots(
    analysis_type: Optional[str],
    limit: int,
    show_reviewed: bool,
    show_unreviewed: bool
) -> Dict[str, Any]:
    """List historical analysis snapshots from DuckDB."""
    
    try:
        # Initialize services
        duckdb_storage = DuckDBStorage()
        service = HistoricalSnapshotService(duckdb_storage)
        
        # Query snapshots
        snapshots = service.list_snapshots(analysis_type, limit)
        
        # Filter by review status if requested
        if show_reviewed and not show_unreviewed:
            snapshots = [s for s in snapshots if s.get('reviewed', False)]
        elif show_unreviewed and not show_reviewed:
            snapshots = [s for s in snapshots if not s.get('reviewed', False)]
        # If both or neither, show all
        
        # Get historical context
        context = service.get_historical_context()
        
        # Display snapshots table
        if snapshots:
            table = Table(title="📅 Analysis Snapshots", show_header=True, header_style="bold magenta")
            table.add_column("Snapshot ID", style="cyan")
            table.add_column("Type", style="green")
            table.add_column("Period", style="yellow")
            table.add_column("Conversations", justify="right")
            table.add_column("Status", style="blue")
            table.add_column("Reviewed By")
            
            for snapshot in snapshots:
                status = "✓ Reviewed" if snapshot.get('reviewed', False) else "⏳ Needs Review"
                reviewed_by = snapshot.get('reviewed_by', '-') or '-'
                
                table.add_row(
                    snapshot['snapshot_id'],
                    snapshot['analysis_type'],
                    snapshot.get('date_range_label', 'N/A'),
                    str(snapshot.get('total_conversations', 0)),
                    status,
                    reviewed_by
                )
            
            console.print(table)
        else:
            console.print("[yellow]No snapshots found matching your criteria.[/yellow]")
        
        # Display historical context panel
        panel_content = f"""[bold]Weeks Available:[/bold] {context['weeks_available']}
[bold]Baseline Established:[/bold] {'✓ Yes' if context['has_baseline'] else f"✗ No (need 4 weeks, have {context['weeks_available']})"}
[bold]Trend Analysis:[/bold] {'✓ Available' if context['can_do_trends'] else f"✗ Not yet (need 4 weeks, have {context['weeks_available']})"}
[bold]Seasonality Detection:[/bold] {'✓ Available' if context['can_do_seasonality'] else f"✗ Not yet (need 12 weeks, have {context['weeks_available']})"}"""
        
        panel = Panel(panel_content, title="📊 Historical Data Status", border_style="green")
        console.print(panel)
        
        # Display summary
        weekly_count = sum(1 for s in snapshots if s['analysis_type'] == 'weekly')
        monthly_count = sum(1 for s in snapshots if s['analysis_type'] == 'monthly')
        quarterly_count = sum(1 for s in snapshots if s['analysis_type'] == 'quarterly')
        
        console.print(f"\n[bold]Total Snapshots:[/bold] {len(snapshots)}")
        console.print(f"  Weekly: {weekly_count}")
        console.print(f"  Monthly: {monthly_count}")
        console.print(f"  Quarterly: {quarterly_count}")
        
        return {
            'snapshots': snapshots,
            'total_count': len(snapshots),
            'historical_context': context,
            'weekly_count': weekly_count,
            'monthly_count': monthly_count,
            'quarterly_count': quarterly_count
        }
        
    except Exception as e:
        logger.error(f"Failed to list snapshots: {e}")
        console.print(f"[red]Error listing snapshots: {e}[/red]")
        return {
            'error': str(e),
            'snapshots': [],
            'total_count': 0
        }


async def export_snapshot_schema(
    output_file: Optional[str],
    schema_type: str
) -> Dict[str, Any]:
    """Export JSON schema for snapshot data models (for API documentation)."""
    
    try:
        # Generate schema based on type
        if schema_type == 'snapshot':
            schema = HistoricalSnapshotService.get_snapshot_json_schema(mode='validation')
            schema_name = 'SnapshotData'
        elif schema_type == 'comparison':
            schema = HistoricalSnapshotService.get_comparison_json_schema()
            schema_name = 'ComparisonData'
        else:
            # Generate both
            snapshot_schema = HistoricalSnapshotService.get_snapshot_json_schema(mode='validation')
            comparison_schema = HistoricalSnapshotService.get_comparison_json_schema()
            schema = {
                'SnapshotData': snapshot_schema,
                'ComparisonData': comparison_schema
            }
            schema_name = 'AllSchemas'
        
        # Display schema
        console.print(f"\n[bold green]📄 {schema_name} JSON Schema[/bold green]\n")
        console.print(json.dumps(schema, indent=2))
        
        # Export to file if requested
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(schema, indent=2))
            console.print(f"\n[green]✅ Schema exported to: {output_path}[/green]")
        
        return {
            'schema': schema,
            'schema_type': schema_type,
            'output_file': output_file
        }
        
    except Exception as e:
        logger.error(f"Failed to export schema: {e}")
        console.print(f"[red]Error exporting schema: {e}[/red]")
        return {
            'error': str(e)
        }


async def compare_snapshots(
    current_id: str,
    prior_id: str,
    show_details: bool
) -> Dict[str, Any]:
    """Compare two analysis snapshots and display week-over-week changes."""
    
    try:
        # Initialize services
        duckdb_storage = DuckDBStorage()
        service = HistoricalSnapshotService(duckdb_storage)
        
        # Retrieve snapshots
        current_snapshot = duckdb_storage.get_analysis_snapshot(current_id)
        prior_snapshot = duckdb_storage.get_analysis_snapshot(prior_id)
        
        # Validate both exist
        if current_snapshot is None:
            console.print(f"[red]Error: Snapshot '{current_id}' not found[/red]")
            return {'error': f"Snapshot '{current_id}' not found"}
        
        if prior_snapshot is None:
            console.print(f"[red]Error: Snapshot '{prior_id}' not found[/red]")
            return {'error': f"Snapshot '{prior_id}' not found"}
        
        # Calculate comparison
        logger.info(f"Comparing {current_id} vs {prior_id}")
        comparison = service.calculate_comparison(current_snapshot, prior_snapshot)
        
        # Display comparison summary
        summary_table = Table(title="📊 Week-over-Week Comparison", show_header=True, header_style="bold magenta")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Current", justify="right")
        summary_table.add_column("Prior", justify="right")
        summary_table.add_column("Change", justify="right")
        
        current_total = current_snapshot.get('total_conversations', 0)
        prior_total = prior_snapshot.get('total_conversations', 0)
        total_delta = current_total - prior_total
        total_pct = (total_delta / prior_total * 100) if prior_total > 0 else 0
        
        current_topics = len(current_snapshot.get('topic_volumes', {}))
        prior_topics = len(prior_snapshot.get('topic_volumes', {}))
        topics_delta = current_topics - prior_topics
        
        summary_table.add_row(
            "Total Conversations",
            str(current_total),
            str(prior_total),
            f"{total_delta:+d} ({total_pct:+.1f}%)"
        )
        summary_table.add_row(
            "Topics Analyzed",
            str(current_topics),
            str(prior_topics),
            f"{topics_delta:+d}"
        )
        
        console.print(summary_table)
        console.print("")
        
        # Display volume changes
        volume_changes = comparison.get('volume_changes', {})
        if volume_changes:
            volume_table = Table(title="Volume Changes by Topic", show_header=True, header_style="bold cyan")
            volume_table.add_column("Topic", style="yellow")
            volume_table.add_column("Current", justify="right")
            volume_table.add_column("Prior", justify="right")
            volume_table.add_column("Change", justify="right")
            volume_table.add_column("% Change", justify="right")
            
            # Sort by absolute change descending
            sorted_changes = sorted(
                volume_changes.items(),
                key=lambda x: abs(x[1].get('change', 0)),
                reverse=True
            )[:15]  # Top 15 changes
            
            for topic, changes in sorted_changes:
                current_vol = changes.get('current', 0)
                prior_vol = changes.get('prior', 0)
                change = changes.get('change', 0)
                pct = changes.get('pct', 0)
                
                # Color code: green for decreases, red for increases
                change_style = "green" if change < 0 else "red" if change > 0 else "white"
                
                volume_table.add_row(
                    topic,
                    str(current_vol),
                    str(prior_vol),
                    f"[{change_style}]{change:+d}[/{change_style}]",
                    f"[{change_style}]{pct:+.1%}[/{change_style}]"
                )
            
            console.print(volume_table)
            console.print("")
        
        # Display significant changes
        significant_changes = comparison.get('significant_changes', [])
        if significant_changes:
            sig_content = []
            for change in significant_changes:
                topic = change.get('topic', 'Unknown')
                alert = change.get('alert', '')
                change_val = change.get('change', 0)
                pct = change.get('pct', 0)
                direction = change.get('direction', 'unknown')
                sig_content.append(f"{alert} {topic}: {change_val:+d} conversations ({pct:+.1%}) - {direction} trend")
            
            sig_panel = Panel(
                '\n'.join(sig_content),
                title="⚠️ Significant Changes (>25% change, >5 conversations)",
                border_style="yellow"
            )
            console.print(sig_panel)
            console.print("")
        
        # Display emerging patterns
        emerging_patterns = comparison.get('emerging_patterns', [])
        if emerging_patterns:
            emerging_content = []
            for pattern in emerging_patterns:
                topic = pattern.get('topic', 'Unknown')
                volume = pattern.get('volume', 0)
                emerging_content.append(f"🆕 {topic}: {volume} conversations (new this period)")
            
            emerging_panel = Panel(
                '\n'.join(emerging_content),
                title="🆕 Emerging Patterns (New Topics)",
                border_style="green"
            )
            console.print(emerging_panel)
            console.print("")
        
        # Display declining patterns
        declining_patterns = comparison.get('declining_patterns', [])
        if declining_patterns:
            declining_content = []
            for pattern in declining_patterns:
                topic = pattern.get('topic', 'Unknown')
                prior_volume = pattern.get('prior_volume', 0)
                declining_content.append(f"📉 {topic}: {prior_volume} conversations last period (disappeared)")
            
            declining_panel = Panel(
                '\n'.join(declining_content),
                title="📉 Declining Patterns (Disappeared Topics)",
                border_style="red"
            )
            console.print(declining_panel)
            console.print("")
        
        # Display detailed comparison if requested
        if show_details:
            # Sentiment changes
            sentiment_changes = comparison.get('sentiment_changes', {})
            if sentiment_changes:
                sentiment_table = Table(title="Sentiment Changes", show_header=True)
                sentiment_table.add_column("Topic", style="cyan")
                sentiment_table.add_column("Shift", style="yellow")
                sentiment_table.add_column("Positive Δ", justify="right")
                sentiment_table.add_column("Negative Δ", justify="right")
                
                for topic, changes in sentiment_changes.items():
                    shift = changes.get('shift', 'stable')
                    positive_delta = changes.get('positive_delta', 0)
                    negative_delta = changes.get('negative_delta', 0)
                    
                    sentiment_table.add_row(
                        topic,
                        shift,
                        f"{positive_delta:+.1%}",
                        f"{negative_delta:+.1%}"
                    )
                
                console.print(sentiment_table)
                console.print("")
            
            # Resolution metrics
            resolution_changes = comparison.get('resolution_changes', {})
            if resolution_changes:
                resolution_table = Table(title="Resolution Metrics Changes", show_header=True)
                resolution_table.add_column("Metric", style="cyan")
                resolution_table.add_column("Change", justify="right", style="yellow")
                resolution_table.add_column("Interpretation")
                
                fcr_delta = resolution_changes.get('fcr_rate_delta')
                if fcr_delta is not None:
                    interp = "improving" if fcr_delta > 0 else "declining" if fcr_delta < 0 else "stable"
                    resolution_table.add_row("FCR Rate", f"{fcr_delta:+.1%}", interp)
                
                time_delta = resolution_changes.get('resolution_time_delta')
                if time_delta is not None:
                    interp = "improving" if time_delta < 0 else "declining" if time_delta > 0 else "stable"
                    resolution_table.add_row("Resolution Time", f"{time_delta:+.1f} hours", interp)
                
                overall = resolution_changes.get('interpretation', 'stable')
                resolution_table.add_row("Overall", "", overall)
                
                console.print(resolution_table)
                console.print("")
        
        # Return results
        return {
            'comparison': comparison,
            'current_snapshot': current_snapshot,
            'prior_snapshot': prior_snapshot,
            'significant_changes_count': len(significant_changes),
            'emerging_patterns_count': len(emerging_patterns),
            'declining_patterns_count': len(declining_patterns)
        }
        
    except Exception as e:
        logger.error(f"Failed to compare snapshots: {e}")
        console.print(f"[red]Error comparing snapshots: {e}[/red]")
        return {
            'error': str(e)
        }








