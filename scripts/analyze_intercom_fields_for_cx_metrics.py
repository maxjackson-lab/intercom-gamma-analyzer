#!/usr/bin/env python3
"""
Analyze Intercom Contact + Conversation Schema for CX Growth/Retention Metrics

Purpose:
Generate Airbyte filter spec for Hilary's requirements:
1. Support-Influenced Retention Rate
2. Expansion Revenue After Support
3. Churn Reduction Value (ARR Impact)

Output:
- Which Intercom fields are needed
- Which fields are bloat (can be filtered out)
- Field population rates (% non-null)
- Mapping to Hilary's metric requirements
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Set, Any
from collections import defaultdict
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.intercom_sdk_service import IntercomSDKService
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


# Hilary's Required Fields (from spec)
REQUIRED_FOR_METRICS = {
    'contacts': {
        # Identity
        'id': 'Customer/User ID (join key)',
        'email': 'Customer email (join key with Sundial)',
        'external_id': 'External user ID if mapped',
        
        # Subscription context (if available in Intercom)
        'custom_attributes.tier': 'Subscription tier (free/team/business)',
        'custom_attributes.stripe_plan': 'Stripe plan info',
        'custom_attributes.stripe_subscription_status': 'Active/cancelled status',
        
        # Segmentation
        'role': 'Lead vs User distinction',
        'signed_up_at': 'Account creation date',
        'updated_at': 'Last profile update',
        
        # Engagement signals (for expansion correlation)
        'last_seen_at': 'Recent product activity',
        'session_count': 'Product engagement frequency',
    },
    
    'conversations': {
        # Identity + linking
        'id': 'Conversation/ticket ID',
        'contacts.contacts[0].id': 'Contact ID (join key)',
        
        # Support interaction flag
        'created_at': 'When support interaction happened',
        'updated_at': 'Last activity timestamp',
        'state': 'Open/closed status',
        
        # Time-to-resolution metric
        'statistics.time_to_close': 'Resolution time (seconds)',
        'statistics.time_to_first_close': 'First resolution time',
        'statistics.handling_time': 'Total handling duration',
        
        # CSAT correlation
        'conversation_rating.rating': 'CSAT score (1-5)',
        'conversation_rating.created_at': 'Survey response date',
        'conversation_rating.remark': 'Customer feedback text',
        
        # Issue categorization (for "type of interaction")
        'custom_attributes.Category': 'Billing/Bug/Product Question',
        'custom_attributes.subcategory': 'Tier 2 categorization',
        'tags.tags[].name': 'Issue tags',
        
        # Multi-touch attribution
        'statistics.count_reopens': 'Number of follow-ups',
        'conversation_parts.conversation_parts': 'All messages (for multi-touch)',
        
        # Cancellation signal detection
        'conversation_message.body': 'First customer message (churn keywords)',
    }
}


async def fetch_sample_contacts(count: int = 100) -> List[Dict]:
    """Fetch contact data via enriched conversations."""
    console.print(f"\n📥 Fetching contact data from recent conversations...")
    
    # Fetch recent conversations
    end_date = datetime.now()
    start_date = end_date - timedelta(days=14)  # 2 weeks to get diverse contacts
    
    from src.services.chunked_fetcher import ChunkedFetcher
    from src.services.intercom_sdk_service import IntercomSDKService
    
    fetcher = ChunkedFetcher()
    conversations = await fetcher.fetch_conversations_chunked(start_date, end_date)
    
    conversations = conversations[:count]
    console.print(f"   Fetched {len(conversations)} conversations")
    
    # Enrich to get full contact data
    console.print(f"   Enriching to extract contact fields...")
    service = IntercomSDKService()
    
    try:
        enriched = await service.enrich_conversations(conversations)
        
        # Extract unique contacts
        contacts = []
        seen_contact_ids = set()
        
        for conv in enriched:
            contacts_obj = conv.get('contacts', {})
            if isinstance(contacts_obj, dict):
                contact_list = contacts_obj.get('contacts', [])
                for contact in contact_list:
                    contact_id = contact.get('id')
                    if contact_id and contact_id not in seen_contact_ids:
                        contacts.append(contact)
                        seen_contact_ids.add(contact_id)
        
        console.print(f"   ✅ Extracted {len(contacts)} unique contacts\n")
        return contacts
    finally:
        await service.close()


async def fetch_sample_conversations(count: int = 100) -> List[Dict]:
    """Fetch sample conversations from Intercom."""
    console.print(f"\n📥 Fetching {count} sample conversations from Intercom...")
    
    service = IntercomSDKService()
    
    try:
        # Fetch recent week
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        from src.services.chunked_fetcher import ChunkedFetcher
        fetcher = ChunkedFetcher()
        conversations = await fetcher.fetch_conversations_chunked(start_date, end_date)
        
        conversations = conversations[:count]
        console.print(f"   ✅ Fetched {len(conversations)} conversations\n")
        return conversations
        
    except Exception as e:
        console.print(f"[red]   ❌ Error fetching conversations: {e}[/red]")
        return []
    finally:
        await service.close()


def analyze_field_population(objects: List[Dict], object_type: str) -> Dict[str, Dict]:
    """
    Analyze which fields are populated in a list of objects.
    
    Returns:
        Dict[field_path, {
            'populated_count': int,
            'population_rate': float,
            'sample_values': List[Any],
            'required_for_metric': str or None
        }]
    """
    field_stats = defaultdict(lambda: {
        'populated_count': 0,
        'total_count': 0,
        'sample_values': [],
        'required_for_metric': None
    })
    
    def traverse_object(obj: Any, path: str = ""):
        """Recursively traverse object and record field population."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                field_path = f"{path}.{key}" if path else key
                
                # Record this field
                field_stats[field_path]['total_count'] += 1
                
                if value is not None and value != "" and value != []:
                    field_stats[field_path]['populated_count'] += 1
                    
                    # Store sample value (first 3)
                    if len(field_stats[field_path]['sample_values']) < 3:
                        sample = str(value)[:100] if isinstance(value, str) else value
                        field_stats[field_path]['sample_values'].append(sample)
                
                # Recurse into nested objects (but limit depth to avoid explosion)
                if isinstance(value, dict) and path.count('.') < 3:
                    traverse_object(value, field_path)
                elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                    # For arrays, analyze first item as representative
                    traverse_object(value[0], f"{field_path}[0]")
        
        elif isinstance(obj, list) and len(obj) > 0:
            # Analyze first item in array
            traverse_object(obj[0], f"{path}[0]")
    
    # Traverse all objects
    for obj in objects:
        traverse_object(obj)
    
    # Calculate population rates and check against required fields
    results = {}
    required_fields = REQUIRED_FOR_METRICS.get(object_type, {})
    
    for field_path, stats in field_stats.items():
        total = stats['total_count']
        populated = stats['populated_count']
        population_rate = (populated / total * 100) if total > 0 else 0
        
        # Check if this field is required for metrics
        required_reason = None
        for required_path, reason in required_fields.items():
            # Fuzzy match (handles array notation differences)
            if required_path in field_path or field_path in required_path:
                required_reason = reason
                break
        
        results[field_path] = {
            'populated_count': populated,
            'total_count': total,
            'population_rate': round(population_rate, 1),
            'sample_values': stats['sample_values'],
            'required_for_metric': required_reason
        }
    
    return results


def generate_airbyte_filter_spec(contact_stats: Dict, conversation_stats: Dict) -> Dict:
    """
    Generate Airbyte sync configuration recommendations.
    
    Returns:
        {
            'contacts': {
                'include_fields': [...],
                'exclude_fields': [...],
                'rationale': {...}
            },
            'conversations': {...}
        }
    """
    spec = {
        'contacts': {
            'include_fields': [],
            'exclude_fields': [],
            'rationale': {}
        },
        'conversations': {
            'include_fields': [],
            'exclude_fields': [],
            'rationale': {}
        }
    }
    
    # Contacts: Include if required OR >50% populated
    for field, stats in contact_stats.items():
        if stats['required_for_metric']:
            spec['contacts']['include_fields'].append(field)
            spec['contacts']['rationale'][field] = f"✅ REQUIRED: {stats['required_for_metric']}"
        elif stats['population_rate'] > 50:
            spec['contacts']['include_fields'].append(field)
            spec['contacts']['rationale'][field] = f"ℹ️  OPTIONAL: {stats['population_rate']}% populated"
        else:
            spec['contacts']['exclude_fields'].append(field)
            spec['contacts']['rationale'][field] = f"❌ EXCLUDE: Only {stats['population_rate']}% populated"
    
    # Conversations: Same logic
    for field, stats in conversation_stats.items():
        if stats['required_for_metric']:
            spec['conversations']['include_fields'].append(field)
            spec['conversations']['rationale'][field] = f"✅ REQUIRED: {stats['required_for_metric']}"
        elif stats['population_rate'] > 50:
            spec['conversations']['include_fields'].append(field)
            spec['conversations']['rationale'][field] = f"ℹ️  OPTIONAL: {stats['population_rate']}% populated"
        else:
            spec['conversations']['exclude_fields'].append(field)
            spec['conversations']['rationale'][field] = f"❌ EXCLUDE: Only {stats['population_rate']}% populated"
    
    return spec


async def main():
    """Main analysis workflow."""
    console.print(Panel.fit(
        "[bold cyan]Intercom Schema Analysis for CX Metrics[/bold cyan]\n"
        "Analyzing which fields to sync via Airbyte for Hilary's requirements",
        border_style="cyan"
    ))
    
    # Fetch samples
    contacts = await fetch_sample_contacts(count=100)
    conversations = await fetch_sample_conversations(count=100)
    
    if not contacts or not conversations:
        console.print("[red]❌ Failed to fetch samples. Check API credentials.[/red]")
        return
    
    # Analyze field population
    console.print("\n🔍 Analyzing contact fields...")
    contact_stats = analyze_field_population(contacts, 'contacts')
    
    console.print("🔍 Analyzing conversation fields...")
    conversation_stats = analyze_field_population(conversations, 'conversations')
    
    # Generate filter spec
    console.print("\n📊 Generating Airbyte filter recommendations...\n")
    filter_spec = generate_airbyte_filter_spec(contact_stats, conversation_stats)
    
    # Display results
    console.print("=" * 100)
    console.print("[bold]CONTACT FIELDS ANALYSIS[/bold]")
    console.print("=" * 100)
    
    # Required fields
    console.print("\n[bold green]✅ REQUIRED FIELDS (for Hilary's metrics)[/bold green]")
    table = Table(show_header=True, header_style="bold green")
    table.add_column("Field", style="cyan", width=40)
    table.add_column("Population", justify="right", width=12)
    table.add_column("Why Required", width=45)
    
    for field in sorted(filter_spec['contacts']['include_fields']):
        if '✅ REQUIRED' in filter_spec['contacts']['rationale'][field]:
            stats = contact_stats.get(field, {})
            pop_rate = stats.get('population_rate', 0)
            reason = stats.get('required_for_metric', 'Unknown')
            table.add_row(field, f"{pop_rate}%", reason)
    
    console.print(table)
    
    # Optional high-value fields
    console.print("\n[bold yellow]ℹ️  OPTIONAL FIELDS (>50% populated, may be useful)[/bold yellow]")
    optional_table = Table(show_header=True, header_style="bold yellow")
    optional_table.add_column("Field", style="dim", width=40)
    optional_table.add_column("Population", justify="right", width=12)
    
    for field in sorted(filter_spec['contacts']['include_fields']):
        if 'ℹ️  OPTIONAL' in filter_spec['contacts']['rationale'][field]:
            stats = contact_stats.get(field, {})
            pop_rate = stats.get('population_rate', 0)
            optional_table.add_row(field, f"{pop_rate}%")
    
    console.print(optional_table)
    
    # Excludable fields
    console.print("\n[bold red]❌ EXCLUDE FIELDS (low population / not needed)[/bold red]")
    exclude_count = len(filter_spec['contacts']['exclude_fields'])
    console.print(f"   {exclude_count} fields can be excluded to reduce warehouse size")
    console.print(f"   (Showing first 20 for readability)")
    
    for field in sorted(filter_spec['contacts']['exclude_fields'])[:20]:
        stats = contact_stats.get(field, {})
        pop_rate = stats.get('population_rate', 0)
        console.print(f"   • {field} ({pop_rate}% populated)")
    
    # Repeat for conversations
    console.print("\n" + "=" * 100)
    console.print("[bold]CONVERSATION FIELDS ANALYSIS[/bold]")
    console.print("=" * 100)
    
    console.print("\n[bold green]✅ REQUIRED FIELDS (for Hilary's metrics)[/bold green]")
    conv_table = Table(show_header=True, header_style="bold green")
    conv_table.add_column("Field", style="cyan", width=40)
    conv_table.add_column("Population", justify="right", width=12)
    conv_table.add_column("Why Required", width=45)
    
    for field in sorted(filter_spec['conversations']['include_fields']):
        if '✅ REQUIRED' in filter_spec['conversations']['rationale'][field]:
            stats = conversation_stats.get(field, {})
            pop_rate = stats.get('population_rate', 0)
            reason = stats.get('required_for_metric', 'Unknown')
            conv_table.add_row(field, f"{pop_rate}%", reason)
    
    console.print(conv_table)
    
    # Save full report to JSON
    output_file = Path("outputs/intercom_field_analysis_for_airbyte.json")
    output_file.parent.mkdir(exist_ok=True)
    
    report = {
        'generated_at': datetime.now().isoformat(),
        'sample_size': {
            'contacts': len(contacts),
            'conversations': len(conversations)
        },
        'hilary_requirements': {
            'retention_metrics': [
                'Support interaction flag (did customer contact support?)',
                'Renewal/cancellation status',
                'Support ticket IDs',
                'Time-to-resolution',
                'CSAT scores'
            ],
            'growth_metrics': [
                'Expansion revenue events',
                'Support interaction before expansion',
                'Product engagement after support'
            ],
            'arr_impact': [
                'Cancellation process start date',
                'Support intervention (yes/no)',
                'Final status (cancelled or stayed)',
                'Subscription value'
            ]
        },
        'contact_analysis': {
            'total_fields_found': len(contact_stats),
            'required_fields': [f for f in filter_spec['contacts']['include_fields'] 
                               if '✅ REQUIRED' in filter_spec['contacts']['rationale'][f]],
            'optional_fields': [f for f in filter_spec['contacts']['include_fields'] 
                               if 'ℹ️  OPTIONAL' in filter_spec['contacts']['rationale'][f]],
            'exclude_fields': filter_spec['contacts']['exclude_fields'],
            'field_stats': contact_stats
        },
        'conversation_analysis': {
            'total_fields_found': len(conversation_stats),
            'required_fields': [f for f in filter_spec['conversations']['include_fields'] 
                               if '✅ REQUIRED' in filter_spec['conversations']['rationale'][f]],
            'optional_fields': [f for f in filter_spec['conversations']['include_fields'] 
                               if 'ℹ️  OPTIONAL' in filter_spec['conversations']['rationale'][f]],
            'exclude_fields': filter_spec['conversations']['exclude_fields'],
            'field_stats': conversation_stats
        },
        'airbyte_recommendation': {
            'contacts_sync_config': {
                'fields_to_include': filter_spec['contacts']['include_fields'][:30],  # Top 30
                'fields_to_exclude': filter_spec['contacts']['exclude_fields'][:50],  # Top 50 bloat
                'estimated_size_reduction': f"{len(filter_spec['contacts']['exclude_fields']) / len(contact_stats) * 100:.0f}%"
            },
            'conversations_sync_config': {
                'fields_to_include': filter_spec['conversations']['include_fields'][:30],
                'fields_to_exclude': filter_spec['conversations']['exclude_fields'][:50],
                'estimated_size_reduction': f"{len(filter_spec['conversations']['exclude_fields']) / len(conversation_stats) * 100:.0f}%"
            }
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    console.print(f"\n💾 Full report saved to: {output_file}")
    
    # Summary
    console.print("\n" + "=" * 100)
    console.print("[bold]SUMMARY: Airbyte Filter Recommendations[/bold]")
    console.print("=" * 100)
    
    console.print(f"\n[green]Contacts:[/green]")
    console.print(f"   • Keep {len([f for f in filter_spec['contacts']['include_fields'] if '✅' in filter_spec['contacts']['rationale'][f]])} required fields")
    console.print(f"   • Optionally keep {len([f for f in filter_spec['contacts']['include_fields'] if 'ℹ️' in filter_spec['contacts']['rationale'][f]])} high-population fields")
    console.print(f"   • Exclude {len(filter_spec['contacts']['exclude_fields'])} low-value fields (~{len(filter_spec['contacts']['exclude_fields']) / len(contact_stats) * 100:.0f}% reduction)")
    
    console.print(f"\n[green]Conversations:[/green]")
    console.print(f"   • Keep {len([f for f in filter_spec['conversations']['include_fields'] if '✅' in filter_spec['conversations']['rationale'][f]])} required fields")
    console.print(f"   • Optionally keep {len([f for f in filter_spec['conversations']['include_fields'] if 'ℹ️' in filter_spec['conversations']['rationale'][f]])} high-population fields")
    console.print(f"   • Exclude {len(filter_spec['conversations']['exclude_fields'])} low-value fields (~{len(filter_spec['conversations']['exclude_fields']) / len(conversation_stats) * 100:.0f}% reduction)")
    
    console.print(f"\n📄 Give `{output_file}` to backend engineer for Airbyte configuration")
    console.print()


if __name__ == '__main__':
    asyncio.run(main())

