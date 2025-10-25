#!/usr/bin/env python3
"""
Analyze specific conversations to understand Fin resolution patterns.

Usage:
    python scripts/analyze_specific_conversations.py <conv_id1> <conv_id2> <conv_id3>
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.intercom_service import IntercomService
from src.services.fin_escalation_analyzer import FinEscalationAnalyzer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


def analyze_conversation_structure(conv: dict, label: str) -> dict:
    """Deep analysis of a single conversation."""
    
    # Basic info
    conv_id = conv.get('id')
    state = conv.get('state')
    rating = conv.get('conversation_rating')
    ai_participated = conv.get('ai_agent_participated', False)
    admin_assignee = conv.get('admin_assignee_id')
    
    # Statistics
    stats = conv.get('statistics', {})
    count_parts = stats.get('count_conversation_parts', 0)
    count_reopens = stats.get('count_reopens', 0)
    time_to_admin_reply = stats.get('time_to_admin_reply')
    handling_time = stats.get('handling_time')
    
    # Conversation parts - THE KEY DATA
    parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
    
    user_parts = []
    admin_parts = []
    bot_parts = []
    
    for part in parts:
        author = part.get('author', {})
        author_type = author.get('type')
        
        part_info = {
            'type': part.get('part_type'),
            'body_preview': part.get('body', '')[:150],
            'created_at': part.get('created_at')
        }
        
        if author_type == 'user':
            user_parts.append(part_info)
        elif author_type == 'admin':
            part_info['admin_id'] = author.get('id')
            part_info['admin_email'] = author.get('email')
            part_info['admin_name'] = author.get('name')
            admin_parts.append(part_info)
        elif author_type == 'bot':
            part_info['bot_name'] = author.get('name')
            bot_parts.append(part_info)
    
    # Check escalation analyzer
    analyzer = FinEscalationAnalyzer()
    has_escalation_keywords = analyzer.detect_escalation_request(conv)
    
    # Full text
    full_text = conv.get('full_text', '')
    
    # Custom attributes
    custom_attrs = conv.get('custom_attributes', {})
    
    return {
        'label': label,
        'id': conv_id,
        'basic': {
            'state': state,
            'rating': rating,
            'ai_participated': ai_participated,
            'admin_assignee_id': admin_assignee
        },
        'statistics': {
            'total_parts': count_parts,
            'reopens': count_reopens,
            'time_to_admin_reply': time_to_admin_reply,
            'handling_time': handling_time
        },
        'parts_breakdown': {
            'user_parts': len(user_parts),
            'admin_parts': len(admin_parts),
            'bot_parts': len(bot_parts),
            'has_actual_admin_response': len(admin_parts) > 0
        },
        'admin_parts_detail': admin_parts,
        'user_parts_detail': user_parts,
        'bot_parts_detail': bot_parts,
        'escalation': {
            'has_escalation_keywords': has_escalation_keywords
        },
        'custom_attributes': custom_attrs,
        'full_text_preview': full_text[:500]
    }


def display_analysis(analysis: dict):
    """Display conversation analysis in a beautiful format."""
    
    console.print(f"\n[bold cyan]{'='*70}[/bold cyan]")
    console.print(f"[bold yellow]{analysis['label'].upper()}[/bold yellow]")
    console.print(f"[bold cyan]{'='*70}[/bold cyan]\n")
    
    console.print(f"[bold]Conversation ID:[/bold] {analysis['id']}")
    
    # Basic info table
    basic_table = Table(title="📋 Basic Information", show_header=True)
    basic_table.add_column("Field", style="cyan")
    basic_table.add_column("Value", style="green")
    
    for key, value in analysis['basic'].items():
        basic_table.add_row(key, str(value))
    
    console.print(basic_table)
    
    # Statistics table
    stats_table = Table(title="📊 Statistics", show_header=True)
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="green")
    
    for key, value in analysis['statistics'].items():
        stats_table.add_row(key, str(value))
    
    console.print(stats_table)
    
    # Parts breakdown
    parts_table = Table(title="💬 Conversation Parts Breakdown", show_header=True)
    parts_table.add_column("Author Type", style="cyan")
    parts_table.add_column("Count", style="green")
    
    parts_table.add_row("User Messages", str(analysis['parts_breakdown']['user_parts']))
    parts_table.add_row("Bot/Fin Messages", str(analysis['parts_breakdown']['bot_parts']))
    parts_table.add_row("Admin Messages", str(analysis['parts_breakdown']['admin_parts']))
    parts_table.add_row("[bold]Has Admin Response?[/bold]", 
                        "[bold green]YES[/bold green]" if analysis['parts_breakdown']['has_actual_admin_response'] 
                        else "[bold red]NO[/bold red]")
    
    console.print(parts_table)
    
    # Admin details if present
    if analysis['admin_parts_detail']:
        console.print("\n[bold yellow]🧑 Admin Response Details:[/bold yellow]")
        for i, admin_part in enumerate(analysis['admin_parts_detail'], 1):
            console.print(f"\n  Admin Response #{i}:")
            console.print(f"    Email: {admin_part.get('admin_email', 'N/A')}")
            console.print(f"    Name: {admin_part.get('admin_name', 'N/A')}")
            console.print(f"    Body: {admin_part['body_preview']}")
    
    # Current vs proposed logic
    console.print("\n[bold]🤖 Fin Resolution Logic:[/bold]")
    
    # Current logic
    current_resolved = not analysis['escalation']['has_escalation_keywords']
    console.print(f"  [dim]Current logic (keyword-based):[/dim] {'✅ Resolved' if current_resolved else '❌ Escalated'}")
    
    # Proposed logic (based on user answers)
    has_admin_response = analysis['parts_breakdown']['has_actual_admin_response']
    is_closed = analysis['basic']['state'] == 'closed'
    rating = analysis['basic']['rating']
    reopens = analysis['statistics']['reopens']
    user_responses = analysis['parts_breakdown']['user_parts']
    bot_responses = analysis['parts_breakdown']['bot_parts']
    
    # User's definition: 
    # Q1: "Either customer finished or never got back but didn't give a rating indicating either way"
    # Q3: More than 2 responses threshold
    
    proposed_resolved = (
        not has_admin_response and  # No human admin responded
        (is_closed or user_responses <= 2) and  # Closed OR customer only responded 1-2 times
        (rating is None or rating >= 3)  # No bad rating
    )
    
    console.print(f"  [bold]Proposed logic (admin-based):[/bold] {'✅ Resolved' if proposed_resolved else '❌ Escalated/Failed'}")
    
    # Show why
    console.print(f"\n  [dim]Decision factors:[/dim]")
    console.print(f"    Admin responded: {has_admin_response}")
    console.print(f"    Closed: {is_closed}")
    console.print(f"    User responses: {user_responses}")
    console.print(f"    Rating: {rating}")
    console.print(f"    Reopens: {reopens}")
    
    # Text preview
    console.print(f"\n[bold]💬 Text Preview:[/bold]")
    console.print(Panel(analysis['full_text_preview'], border_style="blue"))


async def main():
    if len(sys.argv) < 4:
        console.print("[red]Usage: python scripts/analyze_specific_conversations.py <conv_id1> <conv_id2> <conv_id3>[/red]")
        console.print("\nExample conversation IDs to test:")
        console.print("  1. 215471441657032 - Fin resolved successfully")
        console.print("  2. 215471425791360 - Escalated to human")
        console.print("  3. 215471374104625 - Fin failed")
        sys.exit(1)
    
    conv_ids = sys.argv[1:4]
    labels = [
        "Example 1: Fin Resolved Successfully",
        "Example 2: Escalated to Human",
        "Example 3: Fin Failed"
    ]
    
    console.print("[bold cyan]🔍 Analyzing Specific Conversations for Fin Logic[/bold cyan]\n")
    
    # Fetch conversations
    service = IntercomService()
    
    analyses = []
    for conv_id, label in zip(conv_ids, labels):
        console.print(f"📥 Fetching conversation {conv_id}...")
        try:
            conv = await service.get_conversation_details(conv_id)
            analysis = analyze_conversation_structure(conv, label)
            analyses.append(analysis)
            display_analysis(analysis)
        except Exception as e:
            console.print(f"[red]❌ Failed to fetch {conv_id}: {e}[/red]")
    
    # Save report
    report_path = Path('outputs') / f'fin_logic_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(report_path, 'w') as f:
        json.dump(analyses, f, indent=2, default=str)
    
    console.print(f"\n💾 [bold green]Analysis saved to: {report_path}[/bold green]")
    
    # Summary of findings
    console.print("\n[bold]📊 Summary of Findings:[/bold]")
    console.print("Based on user requirements:")
    console.print("  - Fin resolved = No admin response AND (closed OR ≤2 user responses) AND no bad rating")
    console.print("  - CSAT only calculated for conversations with ≥2 responses from both sides")
    console.print("  - Knowledge gap = Low rating OR negative sentiment indicators")


if __name__ == "__main__":
    asyncio.run(main())

