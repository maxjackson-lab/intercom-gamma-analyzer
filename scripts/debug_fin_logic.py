#!/usr/bin/env python3
"""
Debug script to analyze Fin resolution logic on real conversations.

This helps diagnose why Fin performance metrics might be inaccurate.

Usage:
    python scripts/debug_fin_logic.py

This will:
1. Fetch a small sample of recent conversations
2. Show detailed breakdown of each conversation
3. Reveal what the Fin agent is actually checking
4. Help identify why resolution rate might be wrong
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.intercom_sdk_service import IntercomSDKService
from src.services.fin_escalation_analyzer import FinEscalationAnalyzer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


async def analyze_conversation_structure(conv: dict) -> dict:
    """Analyze a conversation's structure for Fin resolution signals."""
    
    # Extract key fields
    conv_id = conv.get('id')
    ai_participated = conv.get('ai_agent_participated', False)
    admin_assignee = conv.get('admin_assignee_id')
    state = conv.get('state')
    rating = conv.get('conversation_rating')
    
    # Check conversation parts for actual admin responses
    parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
    admin_parts = [p for p in parts if p.get('author', {}).get('type') == 'admin']
    user_parts = [p for p in parts if p.get('author', {}).get('type') == 'user']
    bot_parts = [p for p in parts if p.get('author', {}).get('type') == 'bot']
    
    # Check for escalation keywords
    analyzer = FinEscalationAnalyzer()
    has_escalation_keywords = analyzer.detect_escalation_request(conv)
    
    # Extract text snippets
    full_text = conv.get('full_text', '')
    text_preview = full_text[:200] + '...' if len(full_text) > 200 else full_text
    
    # Statistics
    stats = conv.get('statistics', {})
    reopens = stats.get('count_reopens', 0)
    
    # Custom attributes
    custom_attrs = conv.get('custom_attributes', {})
    tier = custom_attrs.get('Tier', 'Unknown')
    language = custom_attrs.get('Language', 'Unknown')
    
    return {
        'id': conv_id,
        'tier': tier,
        'language': language,
        'ai_participated': ai_participated,
        'admin_assignee_id': admin_assignee,
        'state': state,
        'rating': rating,
        'reopens': reopens,
        'user_parts_count': len(user_parts),
        'bot_parts_count': len(bot_parts),
        'admin_parts_count': len(admin_parts),
        'has_admin_response': len(admin_parts) > 0,
        'has_escalation_keywords': has_escalation_keywords,
        'text_preview': text_preview,
        'current_logic_says_resolved': not has_escalation_keywords,  # Current logic
        'better_logic_says_resolved': (
            ai_participated and 
            len(admin_parts) == 0 and 
            state == 'closed' and
            reopens == 0 and
            (rating is None or rating >= 3)
        )
    }


async def main():
    console.print("[bold cyan]🔍 Fin Resolution Logic Debugger[/bold cyan]\n")
    
    # Fetch recent conversations
    console.print("📥 Fetching last 100 conversations from Intercom...")
    service = IntercomSDKService()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)  # Just yesterday
    
    try:
        conversations = await service.fetch_conversations_by_date_range(start_date, end_date)
        console.print(f"   ✅ Fetched {len(conversations)} conversations\n")
    except Exception as e:
        console.print(f"[red]❌ Failed to fetch: {e}[/red]")
        return
    
    # Analyze each conversation
    console.print("🔬 Analyzing conversation structures...\n")
    analyses = []
    for conv in conversations[:50]:  # Analyze first 50
        analysis = await analyze_conversation_structure(conv)
        analyses.append(analysis)
    
    # Summary statistics
    total = len(analyses)
    ai_participated = sum(1 for a in analyses if a['ai_participated'])
    has_admin_response = sum(1 for a in analyses if a['has_admin_response'])
    escalation_keywords = sum(1 for a in analyses if a['has_escalation_keywords'])
    
    current_logic_resolved = sum(1 for a in analyses if a['current_logic_says_resolved'])
    better_logic_resolved = sum(1 for a in analyses if a['better_logic_says_resolved'])
    
    # Display summary
    summary_table = Table(title="📊 Summary Statistics")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="green")
    summary_table.add_column("Percentage", style="yellow")
    
    summary_table.add_row("Total Conversations", str(total), "100%")
    summary_table.add_row("Fin Participated", str(ai_participated), f"{ai_participated/total*100:.1f}%")
    summary_table.add_row("Has Admin Response", str(has_admin_response), f"{has_admin_response/total*100:.1f}%")
    summary_table.add_row("Has Escalation Keywords", str(escalation_keywords), f"{escalation_keywords/total*100:.1f}%")
    summary_table.add_row("", "", "")
    summary_table.add_row("[bold]Current Logic: Resolved[/bold]", str(current_logic_resolved), f"{current_logic_resolved/total*100:.1f}%")
    summary_table.add_row("[bold yellow]Better Logic: Resolved[/bold yellow]", str(better_logic_resolved), f"{better_logic_resolved/total*100:.1f}%")
    
    console.print(summary_table)
    console.print()
    
    # Show discrepancies
    discrepancies = [a for a in analyses if a['current_logic_says_resolved'] != a['better_logic_says_resolved']]
    
    if discrepancies:
        console.print(f"[yellow]⚠️  Found {len(discrepancies)} conversations where current and better logic disagree:[/yellow]\n")
        
        for i, disc in enumerate(discrepancies[:10], 1):  # Show first 10
            panel_content = f"""
**Conversation:** {disc['id']}
**Tier:** {disc['tier']} | **Language:** {disc['language']}

**Current Logic Says:** {'✅ Resolved' if disc['current_logic_says_resolved'] else '❌ Escalated'}
**Better Logic Says:** {'✅ Resolved' if disc['better_logic_says_resolved'] else '❌ Escalated'}

**Why the difference?**
- Fin participated: {disc['ai_participated']}
- Admin response exists: {disc['has_admin_response']}
- Escalation keywords: {disc['has_escalation_keywords']}
- State: {disc['state']}
- Rating: {disc['rating']}
- Reopens: {disc['reopens']}

**Message preview:**
{disc['text_preview']}
"""
            
            color = "yellow" if disc['has_admin_response'] else "green"
            console.print(Panel(panel_content, title=f"Discrepancy #{i}", border_style=color))
    
    # Show examples of each type
    console.print("\n[bold]📋 Sample Conversations by Type:[/bold]\n")
    
    fin_only_no_admin = [a for a in analyses if a['ai_participated'] and not a['has_admin_response']]
    fin_then_admin = [a for a in analyses if a['ai_participated'] and a['has_admin_response']]
    no_fin = [a for a in analyses if not a['ai_participated']]
    
    console.print(f"[green]✅ Fin Only (no admin): {len(fin_only_no_admin)}[/green]")
    if fin_only_no_admin:
        example = fin_only_no_admin[0]
        console.print(f"   Example: {example['id']} - Rating: {example['rating']}, State: {example['state']}")
        console.print(f"   Text: {example['text_preview'][:100]}...\n")
    
    console.print(f"[yellow]🔄 Fin → Admin: {len(fin_then_admin)}[/yellow]")
    if fin_then_admin:
        example = fin_then_admin[0]
        console.print(f"   Example: {example['id']} - Admin parts: {example['admin_parts_count']}")
        console.print(f"   Text: {example['text_preview'][:100]}...\n")
    
    console.print(f"[red]❌ No Fin: {len(no_fin)}[/red]")
    if no_fin:
        example = no_fin[0]
        console.print(f"   Example: {example['id']}")
        console.print(f"   Text: {example['text_preview'][:100]}...\n")
    
    # Save detailed report
    report_path = Path('outputs') / f'fin_debug_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump({
            'summary': {
                'total': total,
                'ai_participated': ai_participated,
                'has_admin_response': has_admin_response,
                'escalation_keywords': escalation_keywords,
                'current_logic_resolved': current_logic_resolved,
                'better_logic_resolved': better_logic_resolved,
                'difference': current_logic_resolved - better_logic_resolved
            },
            'conversations': analyses
        }, f, indent=2)
    
    console.print(f"\n💾 Detailed report saved: {report_path}")
    console.print("\n[bold green]✅ Analysis complete![/bold green]")
    console.print("\n[bold]Next Steps:[/bold]")
    console.print("1. Review discrepancies above")
    console.print("2. Check if 'Better Logic' aligns with your expectations")
    console.print("3. Update fin_performance_agent.py based on findings")


if __name__ == "__main__":
    asyncio.run(main())

