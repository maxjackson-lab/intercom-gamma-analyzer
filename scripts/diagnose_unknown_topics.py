"""
Diagnostic Script for Unknown Topic Detection Issues

Purpose:
- Analyze conversations that fall into "Unknown/unresponsive" category
- Identify root causes (empty text, missing SDK fields, keyword gaps)
- Generate detailed diagnostic report

Usage:
    python scripts/diagnose_unknown_topics.py --date 2025-10-24 --sample-size 200
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
from collections import Counter, defaultdict

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.chunked_fetcher import ChunkedFetcher
from src.agents.topic_detection_agent import TopicDetectionAgent
from src.utils.conversation_utils import extract_conversation_text, extract_customer_messages
from src.agents.base_agent import AgentContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TopicDiagnostic:
    """Diagnostic analyzer for topic detection issues"""
    
    def __init__(self):
        self.topic_agent = TopicDetectionAgent()
        # Get topic definitions for keyword matching
        self.topic_keywords = self.topic_agent.topics
        
    async def analyze_sample(self, start_date: datetime, end_date: datetime, sample_size: int = 200):
        """
        Fetch and analyze a sample of conversations
        
        Args:
            start_date: Start date for fetching
            end_date: End date for fetching
            sample_size: Number of conversations to analyze
        """
        logger.info(f"Fetching {sample_size} conversations from {start_date.date()} to {end_date.date()}")
        
        # Fetch conversations
        fetcher = ChunkedFetcher()
        conversations = await fetcher.fetch_conversations_chunked(
            start_date, 
            end_date,
            max_conversations=sample_size
        )
        
        logger.info(f"Fetched {len(conversations)} conversations")
        
        # Run topic detection
        logger.info("Running topic detection...")
        context = AgentContext(conversations=conversations)
        result = await self.topic_agent.execute(context)
        
        if not result.success:
            logger.error(f"Topic detection failed: {result.error_message}")
            return None
        
        result_data = result.data
        topics_by_conversation = result_data['topics_by_conversation']
        
        # Analyze conversations
        logger.info("Analyzing topic detection results...")
        return self._analyze_results(conversations, topics_by_conversation)
    
    def _analyze_results(self, conversations: List[Dict], topics_by_conversation: Dict) -> Dict[str, Any]:
        """Analyze topic detection results to identify issues"""
        
        analysis = {
            'total_conversations': len(conversations),
            'unknown_conversations': [],
            'empty_text_count': 0,
            'missing_attributes_count': 0,
            'missing_tags_count': 0,
            'short_text_count': 0,
            'should_have_matched': defaultdict(list),
            'text_length_distribution': [],
            'sample_unknown_conversations': []
        }
        
        for conv in conversations:
            conv_id = conv.get('id', 'unknown')
            detected_topics = topics_by_conversation.get(conv_id, [])
            
            # Check if classified as Unknown/unresponsive
            is_unknown = any(t['topic'] == 'Unknown/unresponsive' for t in detected_topics)
            
            if is_unknown:
                analysis['unknown_conversations'].append(conv_id)
                
                # Extract text
                text = extract_conversation_text(conv, clean_html=True)
                text_length = len(text)
                analysis['text_length_distribution'].append(text_length)
                
                # Check for empty text
                if text_length == 0:
                    analysis['empty_text_count'] += 1
                elif text_length < 50:
                    analysis['short_text_count'] += 1
                
                # Check for missing SDK fields
                custom_attributes = conv.get('custom_attributes', {})
                if not custom_attributes or len(custom_attributes) == 0:
                    analysis['missing_attributes_count'] += 1
                
                tags = conv.get('tags', {}).get('tags', [])
                if not tags or len(tags) == 0:
                    analysis['missing_tags_count'] += 1
                
                # Try to manually match keywords to see what SHOULD have matched
                text_lower = text.lower()
                manual_matches = self._manual_keyword_matching(text_lower, custom_attributes, tags)
                
                if manual_matches:
                    for matched_topic in manual_matches:
                        analysis['should_have_matched'][matched_topic].append({
                            'conv_id': conv_id,
                            'text_snippet': text[:200] if text else '(empty)',
                            'text_length': text_length,
                            'matched_keywords': manual_matches[matched_topic]
                        })
                
                # Save first 10 unknown conversations as samples
                if len(analysis['sample_unknown_conversations']) < 10:
                    customer_msgs = extract_customer_messages(conv, clean_html=True)
                    analysis['sample_unknown_conversations'].append({
                        'id': conv_id,
                        'text': text[:500] if text else '(empty)',
                        'text_length': text_length,
                        'customer_messages': customer_msgs[:3] if customer_msgs else [],
                        'custom_attributes': dict(custom_attributes) if custom_attributes else {},
                        'tags': [tag.get('name', str(tag)) if isinstance(tag, dict) else str(tag) for tag in tags],
                        'source_body': conv.get('source', {}).get('body', '(missing)')[:200],
                        'parts_count': len(conv.get('conversation_parts', {}).get('conversation_parts', []))
                    })
        
        # Calculate percentages
        unknown_count = len(analysis['unknown_conversations'])
        if unknown_count > 0:
            analysis['unknown_percentage'] = round(unknown_count / len(conversations) * 100, 1)
            analysis['empty_text_percentage'] = round(analysis['empty_text_count'] / unknown_count * 100, 1)
            analysis['missing_attributes_percentage'] = round(analysis['missing_attributes_count'] / unknown_count * 100, 1)
            analysis['missing_tags_percentage'] = round(analysis['missing_tags_count'] / unknown_count * 100, 1)
            analysis['short_text_percentage'] = round(analysis['short_text_count'] / unknown_count * 100, 1)
        else:
            analysis['unknown_percentage'] = 0.0
            analysis['empty_text_percentage'] = 0.0
            analysis['missing_attributes_percentage'] = 0.0
            analysis['missing_tags_percentage'] = 0.0
            analysis['short_text_percentage'] = 0.0
        
        # Text length statistics
        if analysis['text_length_distribution']:
            analysis['text_length_stats'] = {
                'min': min(analysis['text_length_distribution']),
                'max': max(analysis['text_length_distribution']),
                'avg': sum(analysis['text_length_distribution']) / len(analysis['text_length_distribution'])
            }
        
        return analysis
    
    def _manual_keyword_matching(self, text: str, custom_attributes: Dict, tags: List) -> Dict[str, List[str]]:
        """
        Manually try to match keywords to identify what SHOULD have been detected
        
        Returns:
            Dict of {topic_name: [matched_keywords]}
        """
        matches = {}
        
        for topic_name, config in self.topic_keywords.items():
            matched_keywords = []
            
            # Check attribute matching
            if config['attribute']:
                # Check in custom_attributes keys/values
                if config['attribute'] in custom_attributes:
                    matched_keywords.append(f"attribute:{config['attribute']}")
                
                # Check in tags
                tag_names = [tag.get('name', str(tag)) if isinstance(tag, dict) else str(tag) for tag in tags]
                if config['attribute'] in tag_names:
                    matched_keywords.append(f"tag:{config['attribute']}")
            
            # Check keyword matching
            for keyword in config['keywords']:
                if keyword in text:
                    matched_keywords.append(f"keyword:{keyword}")
            
            if matched_keywords:
                matches[topic_name] = matched_keywords[:5]  # Limit to 5 matches
        
        return matches
    
    def generate_report(self, analysis: Dict[str, Any], output_path: Path):
        """Generate markdown diagnostic report"""
        
        report_lines = [
            "# Topic Detection Diagnostic Report",
            f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Executive Summary",
            "",
            f"- **Total Conversations Analyzed:** {analysis['total_conversations']}",
            f"- **Unknown/Unresponsive:** {len(analysis['unknown_conversations'])} ({analysis['unknown_percentage']}%)",
            "",
            "## Root Cause Analysis",
            "",
            "### Data Quality Issues",
            "",
            f"- **Empty Text:** {analysis['empty_text_count']} ({analysis['empty_text_percentage']}% of unknown)",
            f"- **Short Text (<50 chars):** {analysis['short_text_count']} ({analysis['short_text_percentage']}% of unknown)",
            f"- **Missing Custom Attributes:** {analysis['missing_attributes_count']} ({analysis['missing_attributes_percentage']}% of unknown)",
            f"- **Missing Tags:** {analysis['missing_tags_count']} ({analysis['missing_tags_percentage']}% of unknown)",
            ""
        ]
        
        # Text length statistics
        if 'text_length_stats' in analysis:
            stats = analysis['text_length_stats']
            report_lines.extend([
                "### Text Length Statistics (Unknown Conversations)",
                "",
                f"- **Minimum:** {stats['min']} characters",
                f"- **Maximum:** {stats['max']} characters",
                f"- **Average:** {stats['avg']:.1f} characters",
                ""
            ])
        
        # Should-have-matched analysis
        if analysis['should_have_matched']:
            report_lines.extend([
                "## Topics That Should Have Matched",
                "",
                "These topics had keyword matches but were not detected:",
                ""
            ])
            
            for topic, examples in sorted(analysis['should_have_matched'].items(), key=lambda x: len(x[1]), reverse=True):
                report_lines.append(f"### {topic} ({len(examples)} conversations)")
                report_lines.append("")
                
                # Show first 3 examples
                for example in examples[:3]:
                    report_lines.extend([
                        f"**Conversation:** `{example['conv_id']}`",
                        f"- Text length: {example['text_length']} characters",
                        f"- Matched keywords: {', '.join(example['matched_keywords'])}",
                        f"- Text snippet: \"{example['text_snippet']}...\"",
                        ""
                    ])
        
        # Sample unknown conversations
        report_lines.extend([
            "## Sample Unknown/Unresponsive Conversations",
            "",
            "Detailed inspection of first 10 unknown conversations:",
            ""
        ])
        
        for i, sample in enumerate(analysis['sample_unknown_conversations'], 1):
            report_lines.extend([
                f"### Sample {i}: `{sample['id']}`",
                "",
                f"- **Text Length:** {sample['text_length']} characters",
                f"- **Conversation Parts:** {sample['parts_count']}",
                f"- **Customer Messages:** {len(sample['customer_messages'])}",
                f"- **Custom Attributes:** {len(sample['custom_attributes'])} ({', '.join(sample['custom_attributes'].keys()) if sample['custom_attributes'] else 'none'})",
                f"- **Tags:** {len(sample['tags'])} ({', '.join(sample['tags']) if sample['tags'] else 'none'})",
                "",
                "**Source Body:**",
                f"```",
                sample['source_body'],
                "```",
                "",
                "**Extracted Text:**",
                f"```",
                sample['text'][:300] if sample['text'] else '(empty)',
                "```",
                "",
                "**Customer Messages:**",
                ""
            ])
            
            if sample['customer_messages']:
                for j, msg in enumerate(sample['customer_messages'][:2], 1):
                    report_lines.append(f"{j}. \"{msg[:200]}...\"")
                report_lines.append("")
            else:
                report_lines.extend(["(no customer messages)", ""])
        
        # Recommendations
        report_lines.extend([
            "## Recommendations",
            "",
            "### Priority Fixes",
            ""
        ])
        
        if analysis['empty_text_percentage'] > 10:
            report_lines.extend([
                f"1. **HIGH PRIORITY:** {analysis['empty_text_percentage']}% of unknown conversations have empty text",
                "   - Investigate text extraction from SDK payloads",
                "   - Check if source.body or conversation_parts are missing",
                "   - Verify extract_conversation_text() is working correctly",
                ""
            ])
        
        if analysis['should_have_matched']:
            report_lines.extend([
                "2. **MEDIUM PRIORITY:** Keyword matching is failing",
                "   - Review why detected keywords aren't being matched",
                "   - Check case sensitivity issues",
                "   - Verify topic detection logic in _detect_topics_for_conversation()",
                ""
            ])
        
        if analysis['missing_attributes_percentage'] > 50:
            report_lines.extend([
                f"3. **MEDIUM PRIORITY:** {analysis['missing_attributes_percentage']}% missing custom_attributes",
                "   - Most conversations lack custom attributes for attribute-based detection",
                "   - Rely more heavily on keyword matching",
                "   - Consider adding more keywords to improve coverage",
                ""
            ])
        
        # Write report
        with open(output_path, 'w') as f:
            f.write('\n'.join(report_lines))
        
        logger.info(f"Report generated: {output_path}")


async def main():
    """Main diagnostic runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Diagnose unknown topic detection issues')
    parser.add_argument('--date', default='2025-10-24', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, default=7, help='Number of days to analyze')
    parser.add_argument('--sample-size', type=int, default=200, help='Number of conversations to sample')
    parser.add_argument('--output', default='outputs/unknown_topic_diagnostic_report.md', help='Output report path')
    
    args = parser.parse_args()
    
    # Parse date
    start_date = datetime.strptime(args.date, '%Y-%m-%d')
    end_date = start_date + timedelta(days=args.days)
    
    logger.info("=" * 80)
    logger.info("Topic Detection Diagnostic Tool")
    logger.info("=" * 80)
    logger.info(f"Date Range: {start_date.date()} to {end_date.date()}")
    logger.info(f"Sample Size: {args.sample_size}")
    logger.info("")
    
    # Run diagnostic
    diagnostic = TopicDiagnostic()
    analysis = await diagnostic.analyze_sample(start_date, end_date, args.sample_size)
    
    if analysis:
        # Save raw analysis data
        output_dir = Path(args.output).parent
        output_dir.mkdir(exist_ok=True, parents=True)
        
        json_output = output_dir / 'diagnostic_unknown_sample.json'
        with open(json_output, 'w') as f:
            # Convert to JSON-serializable format
            json_analysis = {
                k: v for k, v in analysis.items() 
                if k not in ['should_have_matched']  # Skip complex nested structures
            }
            json_analysis['should_have_matched_topics'] = list(analysis['should_have_matched'].keys())
            json.dump(json_analysis, f, indent=2, default=str)
        
        logger.info(f"Raw analysis saved: {json_output}")
        
        # Generate report
        diagnostic.generate_report(analysis, Path(args.output))
        
        # Print summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("DIAGNOSTIC SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Unknown Rate: {analysis['unknown_percentage']}%")
        logger.info(f"Empty Text: {analysis['empty_text_percentage']}% of unknown")
        logger.info(f"Missing Attributes: {analysis['missing_attributes_percentage']}% of unknown")
        logger.info(f"Missing Tags: {analysis['missing_tags_percentage']}% of unknown")
        
        if analysis['should_have_matched']:
            logger.info("")
            logger.info("Topics with keyword matches that failed:")
            for topic, examples in sorted(analysis['should_have_matched'].items(), key=lambda x: len(x[1]), reverse=True)[:5]:
                logger.info(f"  - {topic}: {len(examples)} conversations")
        
        logger.info("")
        logger.info(f"Full report: {args.output}")


if __name__ == '__main__':
    asyncio.run(main())


