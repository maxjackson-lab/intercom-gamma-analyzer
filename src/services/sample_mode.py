"""
SAMPLE MODE: Pull 50-100 REAL conversations with ultra-rich logging

Purpose:
- Quick schema validation with real Intercom data
- Debug topic detection issues
- Test fixes without running full analysis
- See what custom_attributes actually contain
- Validate Sal vs Human detection

Output: Rich console output + JSON dump of raw conversations
"""

import logging
import json
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from src.services.intercom_sdk_service import IntercomSDKService
from src.utils.conversation_utils import extract_conversation_text, extract_customer_messages

logger = logging.getLogger(__name__)
console = Console()


class SampleMode:
    """Pull and analyze a small sample of real conversations with rich logging."""
    
    def __init__(self, sdk_service: IntercomSDKService = None):
        self.sdk = sdk_service or IntercomSDKService()
        self.logger = logging.getLogger(__name__)
    
    def _format_timestamp_for_display(self, value):
        """Format timestamps robustly (supports int/float/str/datetime)."""
        from datetime import datetime
        if value is None:
            return "(none)"
        try:
            if isinstance(value, datetime):
                dt = value
            elif isinstance(value, (int, float)):
                dt = datetime.fromtimestamp(value)
            elif isinstance(value, str):
                # Try ISO-8601 parsing; fall back to raw string
                try:
                    iso_val = value.replace('Z', '+00:00')
                    dt = datetime.fromisoformat(iso_val)
                except Exception:
                    return str(value)
            else:
                return str(value)
            return f"{dt} ({value})"
        except Exception:
            return str(value)
    
    async def pull_sample(
        self,
        count: int = 50,
        start_date: datetime = None,
        end_date: datetime = None,
        save_to_file: bool = True
    ) -> Dict[str, Any]:
        """
        Pull a random sample of real conversations with ultra-rich logging.
        
        Args:
            count: Number of conversations (50-100 recommended)
            start_date: Start date for sampling
            end_date: End date for sampling
            save_to_file: Save raw JSON to outputs/
            
        Returns:
            Dict with conversations and analysis
        """
        # Calculate time range description
        days_diff = (end_date - start_date).days
        if days_diff <= 1:
            time_desc = "last 24 hours"
        elif days_diff <= 7:
            time_desc = "last 7 days"
        else:
            time_desc = f"last {days_diff} days"
        
        console.print(Panel.fit(
            "[bold cyan]🔬 SAMPLE MODE: Real Data Extraction[/bold cyan]\n\n"
            f"Pulling {count} conversations from {time_desc}\n"
            f"Date range: {start_date.strftime('%b %d')} to {end_date.strftime('%b %d, %Y')}\n"
            f"Strategy: Fast fetch, stops at {count}",
            border_style="cyan"
        ))
        
        console.print(f"\n[bold]How this works:[/bold]")
        console.print(f"  1. Fetches {count} conversations from {time_desc}")
        console.print(f"  2. Stops IMMEDIATELY after reaching {count}")
        console.print(f"  3. Shows ultra-detailed analysis with ALL raw data")
        console.print(f"  4. Fast: ~30-60 seconds for schema validation\n")
        
        # Fetch exactly what was requested - NO MORE
        console.print(f"📥 [yellow]Fetching {count} conversations from Intercom...[/yellow]")
        
        conversations = await self.sdk.fetch_conversations_by_date_range(
            start_date=start_date,
            end_date=end_date,
            max_conversations=count  # STOP at exactly the requested count
        )
        
        actual_count = len(conversations)
        console.print(f"[green]✅ Fetched {actual_count} conversations[/green]")
        if actual_count < count:
            console.print(f"[yellow]⚠️  Only {actual_count} conversations found in {time_desc}[/yellow]")
        
        if not conversations:
            console.print("[red]❌ No conversations found![/red]")
            return {'conversations': [], 'analysis': {}}
        
        console.print(f"[green]✅ Fetched {len(conversations)} conversations[/green]\n")
        
        # Analyze conversations with rich logging
        analysis = await self._analyze_sample(conversations)
        
        # Save to file if requested
        if save_to_file:
            output_file = Path("outputs") / f"sample_mode_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            output_file.parent.mkdir(exist_ok=True)
            
            with open(output_file, 'w') as f:
                json.dump({
                    'metadata': {
                        'count': len(conversations),
                        'timestamp': datetime.now().isoformat(),
                        'date_range': {
                            'start': start_date.isoformat(),
                            'end': end_date.isoformat()
                        }
                    },
                    'conversations': conversations,
                    'analysis': analysis
                }, f, indent=2, default=str)
            
            console.print(f"\n💾 [green]Raw JSON saved to:[/green] {output_file}")
            console.print(f"   (All detailed analysis is shown above in console)")
        else:
            console.print(f"\n[dim]ℹ️  JSON file not saved (use --save-to-file to enable)[/dim]")
        
        return {
            'conversations': conversations,
            'analysis': analysis
        }
    
    async def _analyze_sample(self, conversations: List[Dict]) -> Dict[str, Any]:
        """Analyze sample with ultra-rich logging."""
        
        # ===== FIELD COVERAGE ANALYSIS =====
        console.print("\n" + "="*80)
        console.print("[bold]📊 FIELD COVERAGE ANALYSIS[/bold]")
        console.print("="*80 + "\n")
        
        field_coverage = self._check_field_coverage(conversations)
        self._display_field_coverage(field_coverage)
        
        # ===== CUSTOM ATTRIBUTES DEEP DIVE =====
        console.print("\n" + "="*80)
        console.print("[bold]🔍 CUSTOM ATTRIBUTES DEEP DIVE[/bold]")
        console.print("="*80 + "\n")
        
        custom_attrs_analysis = self._analyze_custom_attributes(conversations)
        self._display_custom_attributes_analysis(custom_attrs_analysis)
        
        # ===== AGENT ATTRIBUTION ANALYSIS =====
        console.print("\n" + "="*80)
        console.print("[bold]👤 AGENT ATTRIBUTION ANALYSIS[/bold]")
        console.print("="*80 + "\n")
        
        agent_analysis = self._analyze_agent_attribution(conversations)
        self._display_agent_attribution(agent_analysis)
        
        # ===== CONVERSATION SAMPLES =====
        console.print("\n" + "="*80)
        console.print("[bold]📝 ULTRA-DETAILED CONVERSATION SAMPLES (First 3)[/bold]")
        console.print("[dim]Showing ALL raw Intercom data for debugging[/dim]")
        console.print("="*80 + "\n")
        
        for i, conv in enumerate(conversations[:3], 1):  # Show 3 instead of 5 for more detail
            self._display_conversation_detail(conv, i)
        
        # ===== SUMMARY =====
        console.print("\n" + "="*80)
        console.print("[bold green]✅ SAMPLE MODE COMPLETE[/bold green]")
        console.print("="*80)
        console.print("\n[bold]All detailed analysis is shown above in this console.[/bold]")
        console.print("No need to check JSON files - everything you need is here! 👆\n")
        
        return {
            'field_coverage': field_coverage,
            'custom_attributes': custom_attrs_analysis,
            'agent_attribution': agent_analysis,
            'total_conversations': len(conversations)
        }
    
    def _check_field_coverage(self, conversations: List[Dict]) -> Dict[str, Any]:
        """Check which fields are present across conversations."""
        total = len(conversations)
        
        fields_to_check = [
            'id', 'created_at', 'updated_at', 'state', 'priority',
            'admin_assignee_id', 'conversation_rating', 'ai_agent_participated',
            'ai_agent', 'custom_attributes', 'tags', 'topics',
            'conversation_parts', 'source', 'statistics', 'tier',
            'contacts', 'assignee'
        ]
        
        coverage = {}
        for field in fields_to_check:
            present = sum(1 for c in conversations if field in c and c[field] is not None)
            coverage[field] = {
                'present': present,
                'missing': total - present,
                'percentage': round(present / total * 100, 1)
            }
        
        return coverage
    
    def _display_field_coverage(self, coverage: Dict[str, Any]):
        """Display field coverage as table."""
        table = Table(title="Field Coverage", show_header=True)
        table.add_column("Field", style="cyan")
        table.add_column("Present", style="green")
        table.add_column("Missing", style="red")
        table.add_column("%", style="yellow")
        
        for field, data in sorted(coverage.items(), key=lambda x: x[1]['percentage'], reverse=True):
            table.add_row(
                field,
                str(data['present']),
                str(data['missing']),
                f"{data['percentage']}%"
            )
        
        console.print(table)
    
    def _analyze_custom_attributes(self, conversations: List[Dict]) -> Dict[str, Any]:
        """Deep dive into custom_attributes structure."""
        total = len(conversations)
        
        # Check if custom_attributes exists and what keys it has
        has_custom_attrs = sum(1 for c in conversations if c.get('custom_attributes'))
        
        # Collect all unique keys
        all_keys = set()
        key_counts = {}
        value_samples = {}
        
        for conv in conversations:
            attrs = conv.get('custom_attributes', {})
            if attrs and isinstance(attrs, dict):
                for key, value in attrs.items():
                    all_keys.add(key)
                    key_counts[key] = key_counts.get(key, 0) + 1
                    
                    # Sample values
                    if key not in value_samples:
                        value_samples[key] = []
                    if len(value_samples[key]) < 10:  # Keep first 10 unique values
                        if value not in value_samples[key]:
                            value_samples[key].append(value)
        
        return {
            'total_conversations': total,
            'has_custom_attributes': has_custom_attrs,
            'percentage_with_attributes': round(has_custom_attrs / total * 100, 1),
            'unique_keys': sorted(all_keys),
            'key_counts': key_counts,
            'value_samples': value_samples
        }
    
    def _display_custom_attributes_analysis(self, analysis: Dict[str, Any]):
        """Display custom attributes analysis."""
        console.print(f"[bold]Total conversations with custom_attributes:[/bold] {analysis['has_custom_attributes']} ({analysis['percentage_with_attributes']}%)")
        console.print(f"[bold]Unique attribute keys:[/bold] {len(analysis['unique_keys'])}\n")
        
        # Show key frequency table
        table = Table(title="Custom Attribute Keys (Top 20)", show_header=True)
        table.add_column("Key", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("%", style="yellow")
        table.add_column("Sample Values", style="magenta", overflow="fold")
        
        sorted_keys = sorted(analysis['key_counts'].items(), key=lambda x: x[1], reverse=True)[:20]
        for key, count in sorted_keys:
            percentage = round(count / analysis['total_conversations'] * 100, 1)
            samples = analysis['value_samples'].get(key, [])
            sample_str = ", ".join(str(v)[:30] for v in samples[:3])
            
            table.add_row(key, str(count), f"{percentage}%", sample_str)
        
        console.print(table)
    
    def _analyze_agent_attribution(self, conversations: List[Dict]) -> Dict[str, Any]:
        """Analyze agent attribution patterns."""
        total = len(conversations)
        
        sal_conversations = []
        human_admin_conversations = []
        bot_conversations = []
        no_admin_conversations = []
        
        for conv in conversations:
            parts_data = conv.get('conversation_parts', {})
            parts = parts_data.get('conversation_parts', []) if isinstance(parts_data, dict) else []
            
            has_sal = False
            has_human_admin = False
            has_bot = False
            
            for part in parts:
                author = part.get('author', {})
                author_type = author.get('type')
                author_name = author.get('name', '').lower()
                author_email = author.get('email', '').lower()
                
                if author_type == 'admin':
                    # Check if this is Sal or human
                    is_sal = ('sal' in author_name or 'sal' in author_email or 'finn' in author_name)
                    
                    if is_sal:
                        has_sal = True
                    else:
                        has_human_admin = True
                elif author_type == 'bot':
                    has_bot = True
            
            if has_sal:
                sal_conversations.append(conv)
            elif has_human_admin:
                human_admin_conversations.append(conv)
            elif has_bot:
                bot_conversations.append(conv)
            else:
                no_admin_conversations.append(conv)
        
        return {
            'total': total,
            'sal_count': len(sal_conversations),
            'sal_percentage': round(len(sal_conversations) / total * 100, 1),
            'human_admin_count': len(human_admin_conversations),
            'human_admin_percentage': round(len(human_admin_conversations) / total * 100, 1),
            'bot_count': len(bot_conversations),
            'bot_percentage': round(len(bot_conversations) / total * 100, 1),
            'no_admin_count': len(no_admin_conversations),
            'no_admin_percentage': round(len(no_admin_conversations) / total * 100, 1),
            'sal_samples': sal_conversations[:3],
            'human_samples': human_admin_conversations[:3]
        }
    
    def _display_agent_attribution(self, analysis: Dict[str, Any]):
        """Display agent attribution breakdown."""
        table = Table(title="Agent Attribution", show_header=True)
        table.add_column("Agent Type", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("%", style="yellow")
        table.add_column("Note", style="white")
        
        table.add_row(
            "Support Sal (Fin AI)",
            str(analysis['sal_count']),
            f"{analysis['sal_percentage']}%",
            "✅ Should be ~75% if fix works"
        )
        table.add_row(
            "Human Admin",
            str(analysis['human_admin_count']),
            f"{analysis['human_admin_percentage']}%",
            "✅ Should be ~25%"
        )
        table.add_row(
            "Bot (No Sal)",
            str(analysis['bot_count']),
            f"{analysis['bot_percentage']}%",
            "Old Fin format"
        )
        table.add_row(
            "No Admin Response",
            str(analysis['no_admin_count']),
            f"{analysis['no_admin_percentage']}%",
            "User-only messages"
        )
        
        console.print(table)
        
        # Show Sal sample
        if analysis['sal_samples']:
            console.print("\n[bold]Sample Sal Conversation:[/bold]")
            sal_conv = analysis['sal_samples'][0]
            parts = sal_conv.get('conversation_parts', {}).get('conversation_parts', [])
            for part in parts:
                author = part.get('author', {})
                if author.get('type') == 'admin':
                    console.print(f"  Name: {author.get('name')}")
                    console.print(f"  Email: {author.get('email')}")
                    console.print(f"  Type: {author.get('type')}")
                    break
    
    def _display_conversation_detail(self, conv: Dict, index: int):
        """Display ULTRA-detailed view showing ALL raw Intercom data."""
        conv_id = conv.get('id', 'unknown')
        
        console.print(f"\n[bold cyan]{'='*80}[/bold cyan]")
        console.print(f"[bold cyan]CONVERSATION #{index}: {conv_id}[/bold cyan]")
        console.print(f"[bold cyan]{'='*80}[/bold cyan]\n")
        
        # ===== SECTION 1: TOP-LEVEL FIELDS =====
        console.print("[bold]📋 TOP-LEVEL FIELDS (ALL):[/bold]")
        top_level_fields = {
            'id': conv.get('id'),
            'type': conv.get('type'),
            'created_at': self._format_timestamp_for_display(conv.get('created_at')),
            'updated_at': self._format_timestamp_for_display(conv.get('updated_at')),
            'state': conv.get('state'),
            'priority': conv.get('priority'),
            'read': conv.get('read'),
            'waiting_since': self._format_timestamp_for_display(conv.get('waiting_since')),
            'snoozed_until': self._format_timestamp_for_display(conv.get('snoozed_until')),
            'open': conv.get('open'),
            'admin_assignee_id': conv.get('admin_assignee_id'),
            'team_assignee_id': conv.get('team_assignee_id'),
            'title': conv.get('title'),
            'tier': conv.get('tier'),
        }
        for field, value in top_level_fields.items():
            if value is not None:
                console.print(f"  {field}: {value}")
        
        # ===== SECTION 2: AI AGENT DATA (CRITICAL FOR SAL DETECTION) =====
        console.print("\n[bold]🤖 AI AGENT DATA:[/bold]")
        console.print(f"  ai_agent_participated: {conv.get('ai_agent_participated')}")
        
        ai_agent = conv.get('ai_agent')
        if ai_agent:
            console.print(f"  ai_agent object: [green]EXISTS[/green]")
            if isinstance(ai_agent, dict):
                for key, value in ai_agent.items():
                    console.print(f"    {key}: {value}")
        else:
            console.print(f"  ai_agent object: [red]MISSING[/red]")
        
        # ===== SECTION 3: CUSTOM ATTRIBUTES (TOPIC DETECTION) =====
        console.print("\n[bold]🏷️  CUSTOM ATTRIBUTES:[/bold]")
        attrs = conv.get('custom_attributes', {})
        if attrs and isinstance(attrs, dict):
            for key, value in attrs.items():
                console.print(f"  {key}: {value}")
        else:
            console.print("  [red](empty or missing)[/red]")
        
        # ===== SECTION 4: TAGS =====
        console.print("\n[bold]🔖 TAGS:[/bold]")
        tags_obj = conv.get('tags', {})
        if isinstance(tags_obj, dict):
            tags = tags_obj.get('tags', [])
            if tags:
                for tag in tags:
                    tag_name = tag.get('name', tag) if isinstance(tag, dict) else tag
                    console.print(f"  - {tag_name}")
            else:
                console.print("  [red](empty)[/red]")
        else:
            console.print(f"  [red](malformed: {type(tags_obj)})[/red]")
        
        # ===== SECTION 5: TOPICS =====
        console.print("\n[bold]📑 TOPICS:[/bold]")
        topics_obj = conv.get('topics', {})
        if isinstance(topics_obj, dict):
            topics = topics_obj.get('topics', [])
            if topics:
                for topic in topics:
                    if isinstance(topic, dict):
                        console.print(f"  - {topic.get('name')} (type: {topic.get('type')})")
                    else:
                        console.print(f"  - {topic}")
            else:
                console.print("  [red](empty)[/red]")
        else:
            console.print(f"  [red](malformed: {type(topics_obj)})[/red]")
        
        # ===== SECTION 6: ASSIGNEE (ADMIN INFO) =====
        console.print("\n[bold]👤 ASSIGNEE:[/bold]")
        assignee = conv.get('assignee')
        if assignee:
            if isinstance(assignee, dict):
                console.print(f"  Type: {assignee.get('type')}")
                console.print(f"  ID: {assignee.get('id')}")
                console.print(f"  Name: {assignee.get('name')}")
                console.print(f"  Email: {assignee.get('email')}")
            else:
                console.print(f"  {assignee}")
        else:
            console.print("  [red](none)[/red]")
        
        # ===== SECTION 7: CONVERSATION PARTS (AGENT DETECTION) =====
        console.print("\n[bold]💬 CONVERSATION PARTS:[/bold]")
        parts_data = conv.get('conversation_parts', {})
        parts = parts_data.get('conversation_parts', []) if isinstance(parts_data, dict) else []
        console.print(f"  Total parts: {len(parts)}")
        
        for i, part in enumerate(parts[:5], 1):  # Show first 5
            author = part.get('author', {})
            body = part.get('body', '')[:150]
            
            console.print(f"\n  [cyan]Part {i}:[/cyan]")
            console.print(f"    Type: {author.get('type')}")
            console.print(f"    Name: {author.get('name', '(no name)')}")
            console.print(f"    Email: {author.get('email', '(no email)')}")
            console.print(f"    ID: {author.get('id', '(no id)')}")
            console.print(f"    Created: {self._format_timestamp_for_display(part.get('created_at'))}")
            console.print(f"    Body: {body}...")
            
            # Sal detection test
            if author.get('type') == 'admin':
                is_sal = ('sal' in author.get('name', '').lower() or 
                         'sal' in author.get('email', '').lower() or
                         'finn' in author.get('name', '').lower())
                if is_sal:
                    console.print(f"    [green]✅ DETECTED AS SAL/FIN AI[/green]")
                else:
                    console.print(f"    [yellow]⚠️  DETECTED AS HUMAN ADMIN[/yellow]")
        
        if len(parts) > 5:
            console.print(f"\n  [dim]... and {len(parts) - 5} more parts[/dim]")
        
        # ===== SECTION 8: STATISTICS =====
        console.print("\n[bold]📊 STATISTICS:[/bold]")
        stats = conv.get('statistics', {})
        if stats and isinstance(stats, dict):
            for key, value in stats.items():
                console.print(f"  {key}: {value}")
        else:
            console.print("  [red](empty or missing)[/red]")
        
        # ===== SECTION 9: CONVERSATION RATING =====
        console.print("\n[bold]⭐ CONVERSATION RATING:[/bold]")
        rating = conv.get('conversation_rating')
        if rating:
            if isinstance(rating, dict):
                for key, value in rating.items():
                    console.print(f"  {key}: {value}")
            else:
                console.print(f"  Rating: {rating}")
        else:
            console.print("  [red](no rating)[/red]")
        
        # ===== SECTION 10: CONTACTS =====
        console.print("\n[bold]👥 CONTACTS:[/bold]")
        contacts_obj = conv.get('contacts', {})
        if isinstance(contacts_obj, dict):
            contacts = contacts_obj.get('contacts', [])
            if contacts:
                for i, contact in enumerate(contacts[:2], 1):  # Show first 2
                    console.print(f"  Contact {i}:")
                    console.print(f"    ID: {contact.get('id')}")
                    console.print(f"    Email: {contact.get('email')}")
                    console.print(f"    Role: {contact.get('role')}")
                    
                    # Contact custom attributes
                    contact_attrs = contact.get('custom_attributes', {})
                    if contact_attrs:
                        console.print(f"    Custom Attributes: {list(contact_attrs.keys())[:5]}")
            else:
                console.print("  [red](empty)[/red]")
        else:
            console.print(f"  [red](malformed)[/red]")
        
        # ===== SECTION 11: SOURCE MESSAGE =====
        console.print("\n[bold]📨 SOURCE MESSAGE:[/bold]")
        source = conv.get('source', {})
        if source:
            console.print(f"  Type: {source.get('type')}")
            console.print(f"  ID: {source.get('id')}")
            author = source.get('author', {})
            if author:
                console.print(f"  Author Type: {author.get('type')}")
                console.print(f"  Author ID: {author.get('id')}")
            body = source.get('body', '')[:150]
            console.print(f"  Body: {body}...")
        else:
            console.print("  [red](missing)[/red]")
        
        # ===== SECTION 12: FULL TEXT =====
        console.print("\n[bold]📝 EXTRACTED TEXT:[/bold]")
        text = extract_conversation_text(conv, clean_html=True)
        console.print(f"  Length: {len(text)} chars")
        console.print(f"  First 300 chars: {text[:300]}...")
        
        # ===== SECTION 13: KEYWORD DETECTION TEST =====
        console.print("\n[bold]🔍 KEYWORD DETECTION TEST (Word Boundaries):[/bold]")
        text_lower = text.lower()
        test_keywords = {
            'Billing': ['billing', 'invoice', 'refund', 'payment', 'subscription'],
            'Account': ['account', 'login', 'password', 'email'],
            'Bug': ['bug', 'error', 'broken', 'not working'],
            'Product Question': ['how do', 'how to', 'can i', 'question'],
            'Agent/Buddy': ['gamma ai', 'ai assistant', 'chatbot', 'fin ai'],
            'Workspace': ['workspace', 'team', 'member', 'invite']
        }
        
        import re
        detected_topics = []
        for topic, keywords in test_keywords.items():
            matched = []
            for kw in keywords:
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, text_lower):
                    matched.append(kw)
            if matched:
                detected_topics.append(topic)
                console.print(f"  ✅ {topic}: [green]{matched}[/green]")
        
        if not detected_topics:
            console.print("  [red]❌ NO KEYWORDS MATCHED (Would be classified as Unknown)[/red]")
        
        # ===== SECTION 14: RAW JSON KEYS =====
        console.print("\n[bold]🔑 ALL RAW KEYS IN CONVERSATION OBJECT:[/bold]")
        all_keys = sorted(conv.keys())
        console.print(f"  {', '.join(all_keys)}")
        
        console.print("\n")
    
    def _display_agent_attribution(self, analysis: Dict[str, Any]):
        """Already defined above"""
        pass


async def run_sample_mode(
    count: int = 50,
    start_date: datetime = None,
    end_date: datetime = None,
    save_to_file: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to run sample mode.
    
    Args:
        count: Number of conversations (50-100 recommended)
        start_date: Start date (defaults to 7 days ago)
        end_date: End date (defaults to now)
        save_to_file: Save to outputs/
        
    Returns:
        Sample analysis results
    """
    from datetime import timedelta
    
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=7)
    
    sample_mode = SampleMode()
    return await sample_mode.pull_sample(
        count=count,
        start_date=start_date,
        end_date=end_date,
        save_to_file=save_to_file
    )

