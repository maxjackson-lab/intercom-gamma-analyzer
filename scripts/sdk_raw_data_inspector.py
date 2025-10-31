"""
SDK Raw Data Inspector

Purpose:
- Fetch a small sample of conversations (10-50) with FULL SDK response
- Save complete raw JSON with all fields
- Analyze field availability and structure
- Show what data exists but isn't being used
- Help diagnose why topics aren't being detected

Usage:
    python scripts/sdk_raw_data_inspector.py --sample-size 20 --date 2025-10-24
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Set
from collections import Counter

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.intercom_sdk_service import IntercomSDKService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SDKDataInspector:
    """Inspect raw SDK data to understand field availability"""
    
    def __init__(self):
        self.sdk_service = IntercomSDKService()
    
    async def fetch_raw_sample(self, start_date: datetime, end_date: datetime, sample_size: int = 20):
        """
        Fetch raw conversations from SDK with ALL fields
        
        Args:
            start_date: Start date
            end_date: End date  
            sample_size: Number of conversations to fetch
        """
        logger.info(f"Fetching {sample_size} raw conversations from SDK...")
        logger.info(f"Date range: {start_date.date()} to {end_date.date()}")
        
        # Fetch conversations - NO preprocessing to see raw SDK response
        conversations = await self.sdk_service.fetch_conversations_by_date_range(
            start_date,
            end_date,
            max_conversations=sample_size
        )
        
        logger.info(f"✅ Fetched {len(conversations)} conversations")
        
        return conversations
    
    def analyze_field_structure(self, conversations: List[Dict]) -> Dict[str, Any]:
        """
        Analyze what fields exist in the SDK response
        
        Returns:
            Analysis of field availability, types, and sample values
        """
        logger.info(f"Analyzing field structure of {len(conversations)} conversations...")
        
        analysis = {
            'total_conversations': len(conversations),
            'field_presence': {},
            'field_types': {},
            'sample_values': {},
            'nested_field_analysis': {},
            'text_field_analysis': {},
            'topic_field_analysis': {}
        }
        
        # Track field presence across all conversations
        all_fields = set()
        field_counts = Counter()
        field_type_examples = {}
        
        for conv in conversations:
            for key, value in conv.items():
                all_fields.add(key)
                field_counts[key] += 1
                
                # Track type
                value_type = type(value).__name__
                if key not in field_type_examples:
                    field_type_examples[key] = {'types': set(), 'sample': None}
                field_type_examples[key]['types'].add(value_type)
                
                # Save first non-None sample
                if value is not None and field_type_examples[key]['sample'] is None:
                    # Truncate if too long
                    if isinstance(value, str) and len(value) > 200:
                        field_type_examples[key]['sample'] = value[:200] + '...'
                    elif isinstance(value, (dict, list)) and len(str(value)) > 500:
                        field_type_examples[key]['sample'] = str(value)[:500] + '...'
                    else:
                        field_type_examples[key]['sample'] = value
        
        # Build field presence report
        for field in sorted(all_fields):
            presence_count = field_counts[field]
            presence_pct = round(presence_count / len(conversations) * 100, 1)
            
            analysis['field_presence'][field] = {
                'count': presence_count,
                'percentage': presence_pct,
                'types': list(field_type_examples[field]['types']),
                'sample': field_type_examples[field]['sample']
            }
        
        # Analyze key nested structures
        logger.info("Analyzing nested field structures...")
        
        # custom_attributes
        custom_attr_keys = set()
        custom_attr_examples = {}
        for conv in conversations:
            attrs = conv.get('custom_attributes', {})
            if isinstance(attrs, dict):
                for key, val in attrs.items():
                    custom_attr_keys.add(key)
                    if key not in custom_attr_examples and val:
                        custom_attr_examples[key] = val
        
        analysis['nested_field_analysis']['custom_attributes'] = {
            'keys_found': sorted(custom_attr_keys),
            'examples': custom_attr_examples
        }
        
        # tags
        tag_names = []
        for conv in conversations:
            tags_data = conv.get('tags', {})
            if isinstance(tags_data, dict):
                tags_list = tags_data.get('tags', [])
                for tag in tags_list:
                    if isinstance(tag, dict):
                        tag_names.append(tag.get('name', str(tag)))
                    else:
                        tag_names.append(str(tag))
        
        analysis['nested_field_analysis']['tags'] = {
            'total_tags': len(tag_names),
            'unique_tags': len(set(tag_names)),
            'top_tags': Counter(tag_names).most_common(20)
        }
        
        # topics / conversation_topics
        topic_names = []
        topic_structure_examples = []
        for conv in conversations:
            # Check topics.topics
            topics_data = conv.get('topics', {})
            if topics_data:
                topic_structure_examples.append(('topics', topics_data))
                if isinstance(topics_data, dict):
                    topics_list = topics_data.get('topics', [])
                    for topic in topics_list:
                        if isinstance(topic, dict):
                            topic_names.append(topic.get('name', str(topic)))
                        else:
                            topic_names.append(str(topic))
            
            # Check conversation_topics
            conv_topics = conv.get('conversation_topics', [])
            if conv_topics:
                topic_structure_examples.append(('conversation_topics', conv_topics))
                for topic in conv_topics:
                    if isinstance(topic, dict):
                        topic_names.append(topic.get('name', str(topic)))
                    else:
                        topic_names.append(str(topic))
        
        analysis['topic_field_analysis'] = {
            'total_topics': len(topic_names),
            'unique_topics': len(set(topic_names)),
            'top_topics': Counter(topic_names).most_common(20),
            'structure_examples': topic_structure_examples[:5]  # First 5 examples
        }
        
        # Analyze text field availability
        text_field_stats = {
            'source_body': 0,
            'conversation_parts': 0,
            'notes': 0,
            'source_body_empty': 0,
            'conversation_parts_empty': 0
        }
        
        for conv in conversations:
            # source.body
            source = conv.get('source', {})
            if source.get('body'):
                text_field_stats['source_body'] += 1
            else:
                text_field_stats['source_body_empty'] += 1
            
            # conversation_parts
            parts = conv.get('conversation_parts', {})
            if isinstance(parts, dict):
                parts_list = parts.get('conversation_parts', [])
            elif isinstance(parts, list):
                parts_list = parts
            else:
                parts_list = []
            
            if parts_list:
                text_field_stats['conversation_parts'] += 1
            else:
                text_field_stats['conversation_parts_empty'] += 1
            
            # notes
            notes = conv.get('notes', {})
            if isinstance(notes, dict) and notes.get('notes'):
                text_field_stats['notes'] += 1
        
        analysis['text_field_analysis'] = text_field_stats
        
        return analysis
    
    def generate_report(self, conversations: List[Dict], analysis: Dict, output_dir: Path):
        """Generate diagnostic report and save raw data"""
        
        # Save raw JSON
        raw_file = output_dir / 'sdk_raw_sample.json'
        with open(raw_file, 'w') as f:
            json.dump(conversations, f, indent=2, default=str)
        logger.info(f"✅ Raw JSON saved: {raw_file}")
        
        # Save analysis
        analysis_file = output_dir / 'sdk_field_analysis.json'
        # Convert sets to lists for JSON serialization
        analysis_serializable = json.loads(json.dumps(analysis, default=str))
        with open(analysis_file, 'w') as f:
            json.dump(analysis_serializable, f, indent=2, default=str)
        logger.info(f"✅ Analysis saved: {analysis_file}")
        
        # Generate markdown report
        report_lines = [
            "# SDK Raw Data Inspection Report",
            f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Sample Size: {len(conversations)} conversations",
            "",
            "## Field Availability",
            "",
            "Fields present in SDK response:",
            ""
        ]
        
        # Field presence table
        for field, info in sorted(analysis['field_presence'].items(), key=lambda x: x[1]['percentage'], reverse=True):
            report_lines.append(
                f"- **{field}**: {info['count']}/{len(conversations)} ({info['percentage']}%) "
                f"- Type: `{', '.join(info['types'])}`"
            )
            if info['sample'] is not None:
                sample_str = str(info['sample'])[:100]
                report_lines.append(f"  - Sample: `{sample_str}...`")
        
        report_lines.extend([
            "",
            "## Custom Attributes Structure",
            "",
            f"**Keys Found:** {len(analysis['nested_field_analysis']['custom_attributes']['keys_found'])}",
            ""
        ])
        
        for key, value in list(analysis['nested_field_analysis']['custom_attributes']['examples'].items())[:20]:
            report_lines.append(f"- `{key}`: `{value}`")
        
        report_lines.extend([
            "",
            "## Tags Analysis",
            "",
            f"**Total Tags:** {analysis['nested_field_analysis']['tags']['total_tags']}",
            f"**Unique Tags:** {analysis['nested_field_analysis']['tags']['unique_tags']}",
            "",
            "**Top Tags:**"
        ])
        
        for tag, count in analysis['nested_field_analysis']['tags']['top_tags']:
            report_lines.append(f"- {tag}: {count} conversations")
        
        report_lines.extend([
            "",
            "## Topics/Conversation Topics Analysis",
            "",
            f"**Total Topic Assignments:** {analysis['topic_field_analysis']['total_topics']}",
            f"**Unique Topics:** {analysis['topic_field_analysis']['unique_topics']}",
            "",
            "**Top Topics:**"
        ])
        
        for topic, count in analysis['topic_field_analysis']['top_topics']:
            report_lines.append(f"- {topic}: {count} conversations")
        
        report_lines.extend([
            "",
            "## Text Field Availability",
            "",
            f"- **source.body present:** {analysis['text_field_analysis']['source_body']}/{len(conversations)}",
            f"- **source.body empty:** {analysis['text_field_analysis']['source_body_empty']}/{len(conversations)}",
            f"- **conversation_parts present:** {analysis['text_field_analysis']['conversation_parts']}/{len(conversations)}",
            f"- **notes present:** {analysis['text_field_analysis']['notes']}/{len(conversations)}",
            "",
            "## Key Findings",
            ""
        ])
        
        # Add key findings
        if analysis['text_field_analysis']['source_body_empty'] > len(conversations) * 0.1:
            report_lines.append(f"⚠️ **{analysis['text_field_analysis']['source_body_empty']} conversations have empty source.body** - may impact text extraction")
        
        if analysis['topic_field_analysis']['total_topics'] == 0:
            report_lines.append("⚠️ **No topics found in SDK response** - topic detection must rely entirely on keywords")
        
        if len(analysis['nested_field_analysis']['custom_attributes']['keys_found']) < 5:
            report_lines.append(f"⚠️ **Only {len(analysis['nested_field_analysis']['custom_attributes']['keys_found'])} custom attribute keys** - limited attribute-based detection")
        
        report_lines.extend([
            "",
            "## Files Generated",
            "",
            f"1. **Raw SDK JSON:** `{raw_file}`",
            f"2. **Field Analysis:** `{analysis_file}`",
            f"3. **This Report:** `sdk_inspection_report.md`",
            "",
            "## Next Steps",
            "",
            "1. Review `sdk_raw_sample.json` to see full SDK response structure",
            "2. Check which fields are populated vs empty",
            "3. Identify fields we're not currently using",
            "4. Update topic detection to leverage available fields",
            "5. Improve keyword lists based on what's in topics/tags",
            ""
        ])
        
        # Save report
        report_file = output_dir / 'sdk_inspection_report.md'
        with open(report_file, 'w') as f:
            f.write('\n'.join(report_lines))
        logger.info(f"✅ Report saved: {report_file}")
        
        return report_file


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Inspect raw SDK data')
    parser.add_argument('--sample-size', type=int, default=20, help='Number of conversations to fetch')
    parser.add_argument('--date', default='2025-10-24', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, default=7, help='Number of days')
    parser.add_argument('--output-dir', default='outputs/sdk_inspection', help='Output directory')
    
    args = parser.parse_args()
    
    # Parse dates
    start_date = datetime.strptime(args.date, '%Y-%m-%d')
    end_date = start_date + timedelta(days=args.days)
    
    logger.info("=" * 80)
    logger.info("SDK RAW DATA INSPECTOR")
    logger.info("=" * 80)
    logger.info(f"Date Range: {start_date.date()} to {end_date.date()}")
    logger.info(f"Sample Size: {args.sample_size}")
    logger.info("")
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Fetch and analyze
    inspector = SDKDataInspector()
    conversations = await inspector.fetch_raw_sample(start_date, end_date, args.sample_size)
    
    if not conversations:
        logger.error("No conversations fetched!")
        return
    
    # Analyze
    analysis = inspector.analyze_field_structure(conversations)
    
    # Generate report
    report_file = inspector.generate_report(conversations, analysis, output_dir)
    
    # Print summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total Fields: {len(analysis['field_presence'])}")
    logger.info(f"Custom Attribute Keys: {len(analysis['nested_field_analysis']['custom_attributes']['keys_found'])}")
    logger.info(f"Unique Tags: {analysis['nested_field_analysis']['tags']['unique_tags']}")
    logger.info(f"Topic Assignments: {analysis['topic_field_analysis']['total_topics']}")
    logger.info("")
    logger.info("📊 Text Field Availability:")
    logger.info(f"   source.body: {analysis['text_field_analysis']['source_body']}/{len(conversations)}")
    logger.info(f"   conversation_parts: {analysis['text_field_analysis']['conversation_parts']}/{len(conversations)}")
    logger.info(f"   notes: {analysis['text_field_analysis']['notes']}/{len(conversations)}")
    logger.info("")
    logger.info(f"📁 Full report: {report_file}")
    logger.info(f"📁 Raw JSON: {output_dir / 'sdk_raw_sample.json'}")


if __name__ == '__main__':
    asyncio.run(main())

