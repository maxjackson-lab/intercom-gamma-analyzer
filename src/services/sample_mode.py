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
import re
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
console = Console()  # Main console for terminal output


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
        save_to_file: bool = True,
        schema_mode: str = 'standard',
        include_hierarchy: bool = True
    ) -> Dict[str, Any]:
        """
        Pull a random sample of real conversations with ultra-rich logging.
        
        Args:
            count: Number of conversations (depends on mode)
            start_date: Start date for sampling
            end_date: End date for sampling
            save_to_file: Save raw JSON to outputs/
            schema_mode: Analysis depth level
                - 'quick': 50 tickets, basic coverage (30 sec)
                - 'standard': 200 tickets, full analysis (2 min)
                - 'deep': 500 tickets, detailed breakdowns (5 min)
                - 'comprehensive': 1000 tickets, everything (10 min)
            include_hierarchy: Show/hide topic hierarchy debugging section
            
        Returns:
            Dict with conversations and analysis
        """
        # Override count based on mode if not explicitly set
        mode_configs = {
            'quick': {'count': 50, 'detail_samples': 5, 'llm_topics': 2},
            'standard': {'count': 200, 'detail_samples': 10, 'llm_topics': 3},
            'deep': {'count': 500, 'detail_samples': 15, 'llm_topics': 5},
            'comprehensive': {'count': 1000, 'detail_samples': 20, 'llm_topics': 7}
        }
        
        config = mode_configs.get(schema_mode, mode_configs['standard'])
        actual_count = config['count']
        detail_samples = config['detail_samples']
        llm_topic_count = config['llm_topics']
        
        console.print(f"\n[bold cyan]Schema Mode: {schema_mode.upper()}[/bold cyan]")
        console.print(f"[dim]Count: {actual_count} | Detail samples: {detail_samples} | LLM topics: {llm_topic_count}[/dim]\n")
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
            f"Mode: {schema_mode.upper()}\n"
            f"Pulling {actual_count} conversations from {time_desc}\n"
            f"Date range: {start_date.strftime('%b %d')} to {end_date.strftime('%b %d, %Y')}\n"
            f"Detail samples: {detail_samples} | LLM topics: {llm_topic_count}",
            border_style="cyan"
        ))
        
        console.print(f"\n[bold]How this works:[/bold]")
        console.print(f"  1. Fetches {actual_count} conversations from {time_desc}")
        console.print(f"  2. Stops IMMEDIATELY after reaching {actual_count}")
        console.print(f"  3. Shows ultra-detailed analysis with ALL raw data")
        console.print(f"  4. Shows {detail_samples} full conversation dumps for debugging")
        console.print(f"  5. Tests LLM sentiment on {llm_topic_count} diverse topics\n")
        
        # Fetch exactly what was requested - NO MORE
        console.print(f"📥 [yellow]Fetching {actual_count} conversations from Intercom...[/yellow]")
        
        # For 3+ day ranges, use ChunkedFetcher to improve progress and resiliency
        from src.services.chunked_fetcher import ChunkedFetcher
        days_diff = (end_date.date() - start_date.date()).days + 1
        if days_diff > 3:
            fetcher = ChunkedFetcher(intercom_service=self.sdk, enable_preprocessing=False)
            def progress_cb(fetched, processed_days, total_days):
                console.print(f"[dim]Progress: fetched ~{fetched} conversations | {processed_days}/{total_days} days[/dim]")
            conversations = await fetcher.fetch_conversations_chunked(
                start_date=start_date,
                end_date=end_date,
                max_conversations=actual_count,
                progress_callback=progress_cb
            )
        else:
            conversations = await self.sdk.fetch_conversations_by_date_range(
                start_date=start_date,
                end_date=end_date,
                max_conversations=actual_count  # STOP at exactly the requested count
            )
        
        fetched_count = len(conversations)
        console.print(f"[green]✅ Fetched {fetched_count} conversations[/green]")
        if fetched_count < actual_count:
            console.print(f"[yellow]⚠️  Only {fetched_count} conversations found in {time_desc}[/yellow]")
        
        if not conversations:
            console.print("[red]❌ No conversations found![/red]")
            return {'conversations': [], 'analysis': {}}
        
        console.print(f"[green]✅ Fetched {len(conversations)} conversations[/green]\n")
        
        # Start recording console output for log file
        console.record = True
        
        # Analyze conversations with rich logging
        analysis = await self._analyze_sample(conversations, detail_samples=detail_samples, llm_topic_count=llm_topic_count, include_hierarchy=include_hierarchy)
        
        # Capture all console output as plain text
        log_output = console.export_text(clear=True)
        console.record = False
        
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
            
            # Also save complete log file for download
            log_file = output_file.with_suffix('.log')
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(log_output)
            console.print(f"📋 [green]Complete log saved to:[/green] {log_file}")
            console.print(f"   (Download from Files tab - has EVERYTHING even if terminal disconnects)")
        else:
            console.print(f"\n[dim]ℹ️  JSON file not saved (use --save-to-file to enable)[/dim]")
        
        return {
            'conversations': conversations,
            'analysis': analysis
        }
    
    async def _analyze_sample(
        self,
        conversations: List[Dict],
        detail_samples: int = 10,
        llm_topic_count: int = 3,
        include_hierarchy: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze sample with ultra-rich logging.
        
        Args:
            conversations: List of conversations to analyze
            detail_samples: Number of full conversation dumps to show
            llm_topic_count: Number of topics to test LLM sentiment on
            include_hierarchy: Whether to display the topic hierarchy debug section
        """
        
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
        
        # ===== CONVERSATION STATISTICS =====
        console.print("\n" + "="*80)
        console.print("[bold]📈 CONVERSATION STATISTICS (All 50)[/bold]")
        console.print("="*80 + "\n")
        
        conv_stats = self._analyze_conversation_statistics(conversations)
        self._display_conversation_statistics(conv_stats)
        
        # ===== AGENT ATTRIBUTION ANALYSIS =====
        console.print("\n" + "="*80)
        console.print("[bold]👤 AGENT ATTRIBUTION ANALYSIS[/bold]")
        console.print("="*80 + "\n")
        
        agent_analysis = self._analyze_agent_attribution(conversations)
        self._display_agent_attribution(agent_analysis)
        
        # ===== TOPIC DETECTION SUMMARY =====
        console.print("\n" + "="*80)
        console.print("[bold]🎯 TOPIC DETECTION SUMMARY (All 50)[/bold]")
        console.print("[dim]Keyword matching across all conversations[/dim]")
        console.print("="*80 + "\n")
        
        topic_summary = self._analyze_topic_detection(conversations)
        self._display_topic_summary(topic_summary)
        
        # ===== CONVERSATION OVERVIEW TABLE =====
        console.print("\n" + "="*80)
        console.print("[bold]📋 ALL 50 CONVERSATIONS (Quick Overview)[/bold]")
        console.print("="*80 + "\n")
        
        self._display_all_conversations_table(conversations)
        
        # ===== TOPIC HIERARCHY & DOUBLE-COUNTING DEBUG =====
        # Only show if include_hierarchy is True (defaults to True)
        if include_hierarchy:
            console.print("\n" + "="*80)
            console.print("[bold]🔍 TOPIC HIERARCHY & DOUBLE-COUNTING DEBUG[/bold]")
            console.print("[dim]Detecting if conversations are being assigned to multiple topics[/dim]")
            console.print("="*80 + "\n")
            
            hierarchy_debug = await self._debug_topic_hierarchy(conversations)
            self._display_hierarchy_debug(hierarchy_debug)
        else:
            # Still compute for JSON export, but don't display
            hierarchy_debug = await self._debug_topic_hierarchy(conversations)
        
        # ===== CONVERSATION SAMPLES =====
        console.print("\n" + "="*80)
        console.print(f"[bold]📝 ULTRA-DETAILED CONVERSATION SAMPLES (First {detail_samples})[/bold]")
        console.print("[dim]Showing ALL raw Intercom data for debugging[/dim]")
        console.print("="*80 + "\n")
        
        for i, conv in enumerate(conversations[:detail_samples], 1):  # Show configurable samples
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
            'conversation_statistics': conv_stats,
            'agent_attribution': agent_analysis,
            'topic_summary': topic_summary,
            'hierarchy_debug': hierarchy_debug,
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
    
    def _analyze_conversation_statistics(self, conversations: List[Dict]) -> Dict[str, Any]:
        """Analyze conversation statistics across all conversations."""
        total = len(conversations)
        
        # State distribution
        states = {}
        for conv in conversations:
            state = conv.get('state', 'unknown')
            states[state] = states.get(state, 0) + 1
        
        # Text length distribution
        text_lengths = []
        for conv in conversations:
            text = extract_conversation_text(conv, clean_html=True)
            text_lengths.append(len(text))
        
        # Parts count distribution
        parts_counts = []
        for conv in conversations:
            stats = conv.get('statistics', {})
            parts_count = stats.get('count_conversation_parts', 0) if isinstance(stats, dict) else 0
            parts_counts.append(parts_count)
        
        # AI agent participation
        ai_participated = sum(1 for c in conversations if c.get('ai_agent_participated'))
        ai_resolution_states = {}
        for conv in conversations:
            ai_agent = conv.get('ai_agent', {})
            if isinstance(ai_agent, dict):
                res_state = ai_agent.get('resolution_state', 'unknown')
                ai_resolution_states[res_state] = ai_resolution_states.get(res_state, 0) + 1
        
        return {
            'total': total,
            'states': states,
            'text_lengths': {
                'min': min(text_lengths) if text_lengths else 0,
                'max': max(text_lengths) if text_lengths else 0,
                'avg': sum(text_lengths) / len(text_lengths) if text_lengths else 0
            },
            'parts_counts': {
                'min': min(parts_counts) if parts_counts else 0,
                'max': max(parts_counts) if parts_counts else 0,
                'avg': sum(parts_counts) / len(parts_counts) if parts_counts else 0
            },
            'ai_participated': ai_participated,
            'ai_resolution_states': ai_resolution_states
        }
    
    def _display_conversation_statistics(self, stats: Dict[str, Any]):
        """Display conversation statistics."""
        # State distribution
        console.print("[bold]State Distribution:[/bold]")
        for state, count in sorted(stats['states'].items(), key=lambda x: x[1], reverse=True):
            pct = count / stats['total'] * 100
            console.print(f"  {state}: {count} ({pct:.1f}%)")
        
        # Text lengths
        console.print(f"\n[bold]Text Length (source.body only):[/bold]")
        console.print(f"  Min: {stats['text_lengths']['min']} chars")
        console.print(f"  Avg: {stats['text_lengths']['avg']:.0f} chars")
        console.print(f"  Max: {stats['text_lengths']['max']} chars")
        
        # Parts counts
        console.print(f"\n[bold]Conversation Parts Count:[/bold]")
        console.print(f"  Min: {stats['parts_counts']['min']}")
        console.print(f"  Avg: {stats['parts_counts']['avg']:.1f}")
        console.print(f"  Max: {stats['parts_counts']['max']}")
        
        # AI participation
        console.print(f"\n[bold]AI Agent (Fin) Participation:[/bold]")
        console.print(f"  Participated: {stats['ai_participated']}/{stats['total']} ({stats['ai_participated']/stats['total']*100:.1f}%)")
        
        if stats['ai_resolution_states']:
            console.print(f"\n[bold]AI Resolution States:[/bold]")
            for state, count in sorted(stats['ai_resolution_states'].items(), key=lambda x: x[1], reverse=True):
                console.print(f"  {state}: {count}")
    
    def _analyze_topic_detection(self, conversations: List[Dict]) -> Dict[str, Any]:
        """Analyze topic detection across all conversations using keyword matching."""
        test_keywords = {
            'Billing': ['billing', 'invoice', 'refund', 'payment', 'subscription', 'charge', 'receipt'],
            'Account': ['account', 'login', 'password', 'email', 'sign in', 'authentication'],
            'Bug': ['bug', 'error', 'broken', 'not working', 'issue', 'problem', 'crash'],
            'Product Question': ['how do', 'how to', 'can i', 'question', 'help', 'support'],
            'Agent/Buddy': ['gamma ai', 'ai assistant', 'chatbot', 'fin ai', 'buddy'],
            'Workspace': ['workspace', 'team', 'member', 'invite', 'collaboration'],
            'Credits': ['credits', 'ai credits', 'credit balance'],
            'Export': ['export', 'download', 'pdf', 'pptx'],
            'Privacy': ['privacy', 'gdpr', 'data', 'security', 'delete account']
        }
        
        topic_matches = {topic: 0 for topic in test_keywords}
        keyword_hit_counts = {topic: {} for topic in test_keywords}
        no_match_count = 0
        
        for conv in conversations:
            text = extract_conversation_text(conv, clean_html=True).lower()
            matched_any = False
            
            for topic, keywords in test_keywords.items():
                for kw in keywords:
                    pattern = r'\b' + re.escape(kw) + r'\b'
                    if re.search(pattern, text):
                        topic_matches[topic] += 1
                        keyword_hit_counts[topic][kw] = keyword_hit_counts[topic].get(kw, 0) + 1
                        matched_any = True
                        break  # Count once per topic per conversation
            
            if not matched_any:
                no_match_count += 1
        
        return {
            'total': len(conversations),
            'topic_matches': topic_matches,
            'keyword_hit_counts': keyword_hit_counts,
            'no_match_count': no_match_count,
            'no_match_percentage': no_match_count / len(conversations) * 100
        }
    
    def _display_topic_summary(self, summary: Dict[str, Any]):
        """Display topic detection summary."""
        table = Table(title="Topic Detection (Keyword Matching)", show_header=True)
        table.add_column("Topic", style="cyan")
        table.add_column("Matched", style="green")
        table.add_column("%", style="yellow")
        table.add_column("Top Keywords", style="magenta", overflow="fold")
        
        for topic, count in sorted(summary['topic_matches'].items(), key=lambda x: x[1], reverse=True):
            pct = count / summary['total'] * 100
            top_keywords = summary['keyword_hit_counts'][topic]
            top_kw_str = ", ".join(f"{kw}({ct})" for kw, ct in sorted(top_keywords.items(), key=lambda x: x[1], reverse=True)[:3])
            
            table.add_row(topic, str(count), f"{pct:.1f}%", top_kw_str if top_kw_str else "(none)")
        
        # Add Unknown row
        table.add_row(
            "[red]Unknown/No Match[/red]",
            f"[red]{summary['no_match_count']}[/red]",
            f"[red]{summary['no_match_percentage']:.1f}%[/red]",
            "[dim](no keywords matched)[/dim]"
        )
        
        console.print(table)
        
        if summary['no_match_percentage'] > 30:
            console.print(f"\n[yellow]⚠️  High unknown rate ({summary['no_match_percentage']:.1f}%) - may need more keywords or conversation_parts enrichment[/yellow]")
    
    def _display_all_conversations_table(self, conversations: List[Dict]):
        """Display a table showing all conversations with key info."""
        table = Table(show_header=True)
        table.add_column("#", style="dim", width=3)
        table.add_column("ID", style="cyan", width=16)
        table.add_column("State", style="yellow", width=8)
        table.add_column("Parts", style="green", width=5)
        table.add_column("AI?", style="magenta", width=4)
        table.add_column("Reason for Contact", style="white", overflow="fold", width=25)
        table.add_column("Text Preview", style="dim", overflow="fold", width=40)
        
        for i, conv in enumerate(conversations, 1):
            conv_id = str(conv.get('id', 'unknown'))[-12:]  # Last 12 chars
            state = conv.get('state', '?')
            stats = conv.get('statistics', {})
            parts_count = stats.get('count_conversation_parts', 0) if isinstance(stats, dict) else 0
            ai_participated = "Yes" if conv.get('ai_agent_participated') else "No"
            
            # Get Reason for contact from custom_attributes
            attrs = conv.get('custom_attributes', {})
            reason = attrs.get('Reason for contact', '-') if isinstance(attrs, dict) else '-'
            
            # Get text preview
            text = extract_conversation_text(conv, clean_html=True)
            preview = text[:60] + "..." if len(text) > 60 else text
            
            table.add_row(
                str(i),
                conv_id,
                state,
                str(parts_count),
                ai_participated,
                str(reason),
                preview
            )
        
        console.print(table)
    
    async def _debug_topic_hierarchy(self, conversations: List[Dict]) -> Dict[str, Any]:
        """
        Debug topic detection to find double-counting and hierarchy issues.
        
        Returns detailed breakdown of:
        - Which conversations match multiple topics
        - What the topic hierarchy looks like from custom_attributes
        - Detection method distribution
        """
        from src.agents.topic_detection_agent import TopicDetectionAgent
        from src.agents.base_agent import AgentContext
        
        # Run actual topic detection
        topic_agent = TopicDetectionAgent()
        context = AgentContext(
            analysis_id="schema_debug",
            conversations=conversations,
            start_date=datetime.now(),
            end_date=datetime.now()
        )
        
        topic_result = await topic_agent.execute(context)
        
        if not topic_result.success:
            return {'error': topic_result.error_message}
        
        topics_by_conversation = topic_result.data.get('topics_by_conversation', {})
        topic_distribution = topic_result.data.get('topic_distribution', {})
        
        # Analyze multi-topic assignments (DOUBLE-COUNTING DETECTION)
        multi_topic_convs = []
        single_topic_count = 0
        no_topic_count = 0
        
        for conv in conversations:
            conv_id = conv.get('id')
            detected = topics_by_conversation.get(conv_id, [])
            
            if len(detected) == 0:
                no_topic_count += 1
            elif len(detected) == 1:
                single_topic_count += 1
            else:
                # Multiple topics detected!
                from src.utils.conversation_utils import extract_conversation_text
                text_preview = extract_conversation_text(conv, clean_html=True)[:150]
                multi_topic_convs.append({
                    'conv_id': str(conv_id)[-12:],
                    'topic_count': len(detected),
                    'topics': [t['topic'] for t in detected],
                    'methods': [t['method'] for t in detected],
                    'text_preview': text_preview
                })
        
        # Analyze hierarchy from custom_attributes
        hierarchy_examples = []
        for conv in conversations[:20]:  # Check first 20
            attrs = conv.get('custom_attributes', {})
            if not attrs or not isinstance(attrs, dict):
                continue
            
            # Look for hierarchical patterns (Billing > Refund > Given)
            hierarchical_keys = [k for k in attrs.keys() if k in ['Reason for contact', 'Billing', 'Refund', 'Bug', 'Account']]
            if len(hierarchical_keys) > 1:
                hierarchy_examples.append({
                    'conv_id': str(conv.get('id', ''))[-12:],
                    'hierarchy': {k: attrs[k] for k in hierarchical_keys},
                    'all_keys': list(attrs.keys())[:10]
                })
        
        return {
            'total': len(conversations),
            'single_topic': single_topic_count,
            'multi_topic': len(multi_topic_convs),
            'no_topic': no_topic_count,
            'multi_topic_examples': multi_topic_convs[:10],  # Show first 10
            'hierarchy_examples': hierarchy_examples[:5],  # Show first 5
            'topic_distribution': topic_distribution
        }
    
    def _display_hierarchy_debug(self, debug_data: Dict[str, Any]):
        """Display hierarchy debugging information."""
        if 'error' in debug_data:
            console.print(f"[red]Topic detection error: {debug_data['error']}[/red]")
            return
        
        # Multi-topic assignment stats
        console.print("[bold]Double-Counting Detection:[/bold]")
        total = debug_data['total']
        console.print(f"  Single topic: {debug_data['single_topic']} ({debug_data['single_topic']/total*100:.1f}%) [green]✅ No double-counting[/green]")
        console.print(f"  Multi-topic: {debug_data['multi_topic']} ({debug_data['multi_topic']/total*100:.1f}%) [yellow]⚠️  Double-counted![/yellow]")
        console.print(f"  No topic: {debug_data['no_topic']} ({debug_data['no_topic']/total*100:.1f}%) [red]❌ Unclassified[/red]")
        
        # Show examples of double-counted conversations
        if debug_data['multi_topic_examples']:
            console.print(f"\n[bold yellow]⚠️  {len(debug_data['multi_topic_examples'])} Conversations Assigned to Multiple Topics:[/bold yellow]")
            console.print("[dim]These conversations are counted multiple times in topic distribution[/dim]\n")
            
            for example in debug_data['multi_topic_examples'][:5]:
                console.print(f"[cyan]ID: ...{example['conv_id']}[/cyan]")
                console.print(f"  Topics: {', '.join(example['topics'])} ({example['topic_count']} topics)")
                console.print(f"  Methods: {', '.join(example['methods'])}")
                console.print(f"  Text: {example['text_preview']}...")
                console.print()
        
        # Show hierarchy examples
        if debug_data['hierarchy_examples']:
            console.print(f"\n[bold]Hierarchical Structure in custom_attributes:[/bold]")
            console.print("[dim]Shows Billing > Refund > Given type nested attributes[/dim]\n")
            
            for example in debug_data['hierarchy_examples']:
                console.print(f"[cyan]ID: ...{example['conv_id']}[/cyan]")
                for key, value in example['hierarchy'].items():
                    console.print(f"  {key}: {value}")
                console.print(f"  [dim](All keys: {', '.join(example['all_keys'][:5])}...)[/dim]")
                console.print()
        
        # Topic distribution summary
        console.print("\n[bold]Current Topic Distribution:[/bold]")
        sorted_topics = sorted(debug_data['topic_distribution'].items(), key=lambda x: x[1]['volume'], reverse=True)[:10]
        for topic, stats in sorted_topics:
            vol = stats['volume']
            pct = stats['percentage']
            method = stats.get('detection_method', 'unknown')
            console.print(f"  {topic}: {vol} ({pct}%) - {method}")
        console.print()
    
    async def test_llm_analysis(self, conversations: List[Dict], llm_topic_count: int = 3):
        """
        Run actual LLM sentiment analysis on top topics to show what agents produce.
        
        This helps debug:
        - Is the LLM prompt working?
        - What sentiment is the LLM actually detecting?
        - Is enrichment corrupting the data?
        """
        console.print("\n" + "="*80)
        console.print("[bold]🤖 LLM SENTIMENT ANALYSIS TEST[/bold]")
        console.print("[dim]Running actual TopicSentimentAgent on top topics[/dim]")
        console.print("="*80 + "\n")
        
        # Import agents
        from src.agents.topic_detection_agent import TopicDetectionAgent
        from src.agents.topic_sentiment_agent import TopicSentimentAgent
        from src.agents.base_agent import AgentContext
        
        # Detect topics first
        topic_agent = TopicDetectionAgent()
        sentiment_agent = TopicSentimentAgent()
        
        context = AgentContext(
            analysis_id="sample_llm_test",
            conversations=conversations,
            start_date=datetime.now(),
            end_date=datetime.now()
        )
        
        console.print("[yellow]🔍 Step 1: Detecting topics...[/yellow]")
        topic_result = await topic_agent.execute(context)
        
        if not topic_result.success:
            console.print(f"[red]❌ Topic detection failed: {topic_result.error_message}[/red]")
            return
        
        topic_dist = topic_result.data.get('topic_distribution', {})
        topics_by_conv = topic_result.data.get('topics_by_conversation', {})
        
        # Select diverse topics: high-volume + low-volume for comprehensive testing
        all_topics = sorted(topic_dist.items(), key=lambda x: x[1]['volume'], reverse=True)
        
        # Strategy: 60% high-volume, 40% low-volume (mix of common + edge cases)
        high_volume_count = max(1, int(llm_topic_count * 0.6))
        low_volume_count = llm_topic_count - high_volume_count
        
        high_volume_topics = all_topics[:high_volume_count]
        low_volume_topics = all_topics[-(low_volume_count):] if low_volume_count > 0 else []
        
        selected_topics = high_volume_topics + low_volume_topics
        
        console.print(f"[green]✅ Found {len(topic_dist)} topics total[/green]\n")
        console.print(f"[bold]Testing LLM sentiment on {len(selected_topics)} diverse topics:[/bold]")
        console.print(f"[dim]Strategy: {high_volume_count} high-volume + {low_volume_count} low-volume topics[/dim]")
        for topic_name, stats in selected_topics:
            console.print(f"  - {topic_name}: {stats['volume']} conversations")
        
        # Test LLM on each selected topic
        for topic_name, stats in selected_topics:
            console.print(f"\n{'─'*80}")
            console.print(f"[bold cyan]TESTING: {topic_name} ({stats['volume']} conversations)[/bold cyan]")
            console.print(f"{'─'*80}\n")
            
            # Get conversations for this topic
            topic_convs = []
            for conv in conversations:
                conv_id = conv.get('id')
                if conv_id in topics_by_conv:
                    conv_topics = topics_by_conv[conv_id]
                    if any(t['topic'] == topic_name for t in conv_topics):
                        topic_convs.append(conv)
            
            if not topic_convs:
                console.print("[yellow]⚠️  No conversations found for this topic[/yellow]")
                continue
            
            console.print(f"[dim]Sample size: {len(topic_convs)} conversations[/dim]\n")
            
            # Show 2 example conversation texts
            console.print("[bold]Sample Conversations:[/bold]")
            for i, conv in enumerate(topic_convs[:2], 1):
                from src.utils.conversation_utils import extract_conversation_text
                text = extract_conversation_text(conv, clean_html=True)
                preview = text[:200] + "..." if len(text) > 200 else text
                console.print(f"{i}. {preview}\n")
            
            # Run actual sentiment analysis
            console.print("[yellow]🤖 Running TopicSentimentAgent...[/yellow]")
            
            topic_context = context.model_copy()
            topic_context.metadata = {
                'current_topic': topic_name,
                'topic_conversations': topic_convs
            }
            
            sentiment_result = await sentiment_agent.execute(topic_context)
            
            if sentiment_result.success:
                insight = sentiment_result.data.get('sentiment_insight', '')
                method = sentiment_result.data.get('method', 'unknown')
                
                console.print(f"\n[bold green]✅ LLM Sentiment Result:[/bold green]")
                console.print(f"[cyan]Method: {method}[/cyan]")
                console.print(f"[white]{insight}[/white]\n")
                
                # Show if it matches the quotes
                console.print("[bold]Does this match the actual customer feedback above?[/bold]")
                console.print("[dim](You decide if sentiment is accurate)[/dim]\n")
            else:
                console.print(f"[red]❌ Sentiment analysis failed: {sentiment_result.error_message}[/red]\n")
        
        console.print(f"\n{'='*80}")
        console.print("[bold green]✅ LLM TEST COMPLETE[/bold green]")
        console.print("="*80)
        console.print("\n[bold]This shows you:[/bold]")
        console.print("  1. What the LLM is actually generating")
        console.print("  2. Whether sentiment matches the actual quotes")
        console.print("  3. If enrichment is corrupting the data")
        console.print("  4. What method was used (llm vs cx_score - should always be 'llm' now)\n")


async def run_sample_mode(
    count: int = 50,
    start_date: datetime = None,
    end_date: datetime = None,
    save_to_file: bool = True,
    test_llm: bool = False,
    schema_mode: str = 'standard',
    include_hierarchy: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to run sample mode.
    
    Args:
        count: Number of conversations (50-100 recommended)
        start_date: Start date (defaults to 7 days ago)
        end_date: End date (defaults to now)
        save_to_file: Save to outputs/
        test_llm: Run actual LLM sentiment analysis on top topics (shows what agents produce)
        include_hierarchy: Show/hide topic hierarchy debugging section
        
    Returns:
        Sample analysis results
    """
    from datetime import timedelta
    
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=7)
    
    sample_mode = SampleMode()
    result = await sample_mode.pull_sample(
        count=count,
        start_date=start_date,
        end_date=end_date,
        save_to_file=save_to_file,
        schema_mode=schema_mode,
        include_hierarchy=include_hierarchy
    )
    
    # Run LLM test if requested
    if test_llm:
        # Get llm_topic_count from mode config
        mode_configs = {
            'quick': 2,
            'standard': 3,
            'deep': 5,
            'comprehensive': 7
        }
        llm_count = mode_configs.get(schema_mode, 3)
        await sample_mode.test_llm_analysis(result['conversations'], llm_topic_count=llm_count)
    
    return result

