#!/usr/bin/env python3
"""
Validate Airbyte Filter Spec Against Actual Sample Data

Analyzes 1,000 real conversations to determine:
1. Which fields are actually populated (vs. theoretical)
2. Field population rates
3. Which fields map to Hilary's CX metrics
4. Refined exclusion recommendations

Input: sample_mode JSON files from Railway runs
Output: Validated Airbyte filter spec with evidence
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple
from collections import defaultdict, Counter
from datetime import datetime

# Simplified output (no rich library dependency)
class Console:
    def print(self, *args, **kwargs):
        print(*args)


def flatten_dict(d: Dict, parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """Flatten nested dict to dot notation."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # Sample first item if list of objects
            if v and isinstance(v[0], dict):
                items.extend(flatten_dict(v[0], f"{new_key}[0]", sep=sep).items())
            else:
                items.append((new_key, v))
        else:
            items.append((new_key, v))
    return dict(items)


def analyze_field_population(conversations: List[Dict]) -> Tuple[Dict[str, int], Dict[str, Set]]:
    """
    Analyze which fields are populated and their value diversity.
    
    Returns:
        (field_counts, field_samples) where:
        - field_counts: {field_path: count_of_non_null}
        - field_samples: {field_path: set_of_sample_values}
    """
    field_counts = defaultdict(int)
    field_samples = defaultdict(set)
    
    total = len(conversations)
    
    for conv in conversations:
        flat = flatten_dict(conv)
        
        for field_path, value in flat.items():
            # Skip empty/null values
            if value is None or value == "" or value == [] or value == {}:
                continue
            
            field_counts[field_path] += 1
            
            # Sample up to 5 unique values per field
            if len(field_samples[field_path]) < 5:
                # Truncate long strings
                sample_val = str(value)[:100] if isinstance(value, str) else str(value)
                field_samples[field_path].add(sample_val)
    
    return dict(field_counts), {k: list(v) for k, v in field_samples.items()}


def map_fields_to_metrics(field_path: str) -> List[str]:
    """Map field to Hilary's metric requirements."""
    metrics = []
    
    # Support interaction flag (binary)
    if any(x in field_path for x in ['admin_assignee', 'teammate', 'team_assignee', 'conversation_rating']):
        metrics.append("Support Interaction Flag")
    
    # Time-to-resolution
    if any(x in field_path for x in ['created_at', 'updated_at', 'state', 'sla']):
        metrics.append("Time-to-Resolution")
    
    # CSAT scores
    if 'rating' in field_path or 'csat' in field_path:
        metrics.append("CSAT Scores")
    
    # Customer identity
    if any(x in field_path for x in ['email', 'external_id', 'id']) and 'contact' in field_path:
        metrics.append("Customer Identity")
    
    # Subscription data
    if any(x in field_path for x in ['stripe', 'subscription', 'tier', 'plan']):
        metrics.append("Subscription Status")
    
    return metrics


def categorize_field(field_path: str) -> str:
    """Categorize field for filtering recommendations."""
    
    # Core identity
    if field_path in ['id', 'contacts.contacts[0].id', 'contacts.contacts[0].email', 'contacts.contacts[0].external_id']:
        return "MUST_SYNC"
    
    # Timestamps
    if 'created_at' in field_path or 'updated_at' in field_path or 'signed_up_at' in field_path:
        return "MUST_SYNC"
    
    # Support interaction markers
    if any(x in field_path for x in ['admin_assignee', 'team_assignee', 'teammate', 'state', 'rating']):
        return "MUST_SYNC"
    
    # Subscription/billing
    if 'stripe' in field_path or 'subscription' in field_path or 'tier' in field_path:
        return "MUST_SYNC"
    
    # Activity signals
    if any(x in field_path for x in ['last_seen', 'last_replied', 'last_contacted', 'last_email']):
        return "USEFUL"
    
    # Contact metadata
    if any(x in field_path for x in ['role', 'name', 'phone', 'location', 'company']):
        return "USEFUL"
    
    # Device/browser metadata (bloat)
    if any(x in field_path for x in ['browser', 'os', 'device', 'user_agent', 'ip_address']):
        return "EXCLUDE"
    
    # Social/avatar (bloat)
    if any(x in field_path for x in ['avatar', 'social', 'twitter', 'linkedin', 'facebook']):
        return "EXCLUDE"
    
    # Rich content (bloat for analytics)
    if field_path in ['source.body', 'source.attachments']:
        return "EXCLUDE"
    
    return "REVIEW"


def generate_validated_spec(
    field_counts: Dict[str, int],
    field_samples: Dict[str, List[str]],
    total_conversations: int
) -> str:
    """Generate validated Airbyte filter spec."""
    
    output = []
    output.append("# VALIDATED Airbyte Filter Spec for Hilary's CX Metrics")
    output.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output.append(f"Based on: {total_conversations:,} real Intercom conversations\n")
    output.append("---\n")
    
    # Group fields by category
    categories = defaultdict(list)
    for field_path, count in sorted(field_counts.items(), key=lambda x: x[1], reverse=True):
        pop_rate = (count / total_conversations) * 100
        category = categorize_field(field_path)
        metrics = map_fields_to_metrics(field_path)
        
        categories[category].append({
            'field': field_path,
            'count': count,
            'pop_rate': pop_rate,
            'metrics': metrics,
            'samples': field_samples.get(field_path, [])
        })
    
    # MUST SYNC section
    output.append("## ✅ MUST SYNC (Critical for CX Metrics)\n")
    output.append("| Field | Population | Maps To | Sample Values |")
    output.append("|-------|-----------|---------|---------------|")
    
    for item in categories['MUST_SYNC']:
        metrics_str = ", ".join(item['metrics']) if item['metrics'] else "Identity/Join Key"
        samples_str = str(item['samples'][0])[:40] if item['samples'] else "—"
        output.append(
            f"| `{item['field']}` | {item['pop_rate']:.1f}% | {metrics_str} | {samples_str} |"
        )
    
    # USEFUL section
    output.append("\n## 🟡 USEFUL (Recommended for analysis)\n")
    output.append("| Field | Population | Notes |")
    output.append("|-------|-----------|-------|")
    
    for item in sorted(categories['USEFUL'], key=lambda x: x['pop_rate'], reverse=True)[:20]:
        output.append(
            f"| `{item['field']}` | {item['pop_rate']:.1f}% | Activity signal |"
        )
    
    # EXCLUDE section
    output.append("\n## ❌ EXCLUDE (Bloat - not needed for metrics)\n")
    output.append("| Field | Population | Why Exclude |")
    output.append("|-------|-----------|-------------|")
    
    for item in categories['EXCLUDE'][:15]:
        reason = "Device metadata" if any(x in item['field'] for x in ['browser', 'os']) else \
                 "Social profiles" if 'social' in item['field'] else \
                 "Rich content" if 'body' in item['field'] or 'attachment' in item['field'] else \
                 "Not needed for metrics"
        output.append(
            f"| `{item['field']}` | {item['pop_rate']:.1f}% | {reason} |"
        )
    
    # Size reduction estimate
    must_sync_count = len(categories['MUST_SYNC'])
    useful_count = len(categories['USEFUL'])
    exclude_count = len(categories['EXCLUDE'])
    total_fields = must_sync_count + useful_count + exclude_count
    
    reduction_pct = (exclude_count / total_fields) * 100 if total_fields > 0 else 0
    
    output.append(f"\n## 📊 Summary\n")
    output.append(f"- **Total unique fields analyzed:** {len(field_counts):,}")
    output.append(f"- **MUST SYNC:** {must_sync_count} fields")
    output.append(f"- **USEFUL:** {useful_count} fields")
    output.append(f"- **EXCLUDE:** {exclude_count} fields (~{reduction_pct:.0f}% size reduction)")
    
    output.append("\n## 🎯 Airbyte Configuration\n")
    output.append("```json")
    output.append("{")
    output.append('  "streams": [')
    output.append('    {')
    output.append('      "stream": "conversations",')
    output.append('      "sync_mode": "incremental",')
    output.append('      "selected_fields": [')
    
    # List all MUST_SYNC fields
    for i, item in enumerate(categories['MUST_SYNC']):
        comma = "," if i < len(categories['MUST_SYNC']) - 1 else ""
        output.append(f'        "{item["field"]}"{comma}')
    
    output.append('      ]')
    output.append('    }')
    output.append('  ]')
    output.append('}')
    output.append("```")
    
    return "\n".join(output)


def main():
    console = Console()
    print("=" * 80)
    print("Airbyte Filter Spec Validator")
    print("Analyzing real Intercom data to validate field requirements")
    print("=" * 80)
    
    # Find sample JSON files
    base_path = Path("/Users/max.jackson/Intercom Analysis Tool ")
    sample_files = []
    
    # Check all the attached folders
    search_paths = [
        base_path / "Sample Mode Last Month 1000 tickets",
        base_path / "Sample Run 1000 tickets 11.16  2 copy",
        base_path / "Sample Run 1000 tickets 11.16  2",
        base_path / "outputs"
    ]
    
    for search_path in search_paths:
        if search_path.exists():
            sample_files.extend(list(search_path.glob("sample_mode_*.json")))
    
    if not sample_files:
        console.print("[red]❌ No sample_mode_*.json files found[/red]")
        return 1
    
    console.print(f"\n📂 Found {len(sample_files)} sample file(s):")
    for f in sample_files:
        console.print(f"   • {f.name}")
    
    # Load most recent
    latest_file = max(sample_files, key=lambda p: p.stat().st_mtime)
    console.print(f"\n📖 Loading: [cyan]{latest_file.name}[/cyan]")
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    conversations = data.get('conversations', [])
    console.print(f"   ✅ Loaded {len(conversations):,} conversations\n")
    
    # Analyze
    console.print("🔍 Analyzing field population rates...")
    field_counts, field_samples = analyze_field_population(conversations)
    
    console.print(f"   ✅ Found {len(field_counts):,} unique populated fields\n")
    
    # Generate spec
    console.print("📝 Generating validated Airbyte spec...\n")
    spec = generate_validated_spec(field_counts, field_samples, len(conversations))
    
    # Write output
    output_file = Path("/Users/max.jackson/Intercom Analysis Tool ") / "outputs" / "VALIDATED_airbyte_spec.md"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(spec)
    
    print(f"✅ Validated spec written to: {output_file.name}\n")
    
    # Print summary table
    print("\nField Population Summary")
    print("-" * 60)
    print(f"{'Category':<15} {'Count':>10} {'Avg Population':>15}")
    print("-" * 60)
    
    categories = defaultdict(list)
    for field, count in field_counts.items():
        cat = categorize_field(field)
        pop_rate = (count / len(conversations)) * 100
        categories[cat].append(pop_rate)
    
    for cat in ['MUST_SYNC', 'USEFUL', 'EXCLUDE', 'REVIEW']:
        if cat in categories:
            avg_pop = sum(categories[cat]) / len(categories[cat])
            print(f"{cat:<15} {len(categories[cat]):>10} {avg_pop:>14.1f}%")
    
    print("-" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

