"""
OutputFormatterAgent: Formats analysis into Hilary's exact card structure.

Purpose:
- Generate output matching Hilary's wishlist format exactly
- Separate VoC (paid) from Fin analysis (free)
- Include detection methods and examples
- Add trend indicators when available
- Display 3-tier sub-topic hierarchies
- Show Finn performance by sub-topic with quality metrics
"""

import logging
from typing import Dict, Any, List, Set
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel

logger = logging.getLogger(__name__)


class OutputFormatterAgent(BaseAgent):
    """Agent specialized in formatting output to match Hilary's format"""
    
    # Define expected agent outputs with required/optional flags
    EXPECTED_AGENTS = {
        'SegmentationAgent': {'required': True, 'key': 'segmentation'},
        'TopicDetectionAgent': {'required': True, 'key': 'topics'},
        'SubTopicDetectionAgent': {'required': False, 'key': 'subtopics'},
        'TrendAgent': {'required': False, 'key': 'trends'},
        'FinPerformanceAgent': {'required': False, 'key': 'fin_performance'},
        'TopicSentiments': {'required': False, 'key': 'sentiments'},
        'TopicExamples': {'required': False, 'key': 'examples'}
    }
    
    def __init__(self):
        super().__init__(
            name="OutputFormatterAgent",
            model="gpt-4o-mini",
            temperature=0.1
        )
    
    def get_agent_specific_instructions(self) -> str:
        """Output formatter instructions"""
        return """
OUTPUT FORMATTER AGENT SPECIFIC RULES:

1. Match Hilary's exact card structure:
   - Topic name as header
   - Volume + percentage
   - Detection method noted
   - Sentiment insight
   - 3-10 example conversation links

2. Separate sections:
   - Voice of Customer (Paid - Human Support)
   - Fin AI Performance (Free - AI Only)
   - Support Operations (Optional)

3. Include all metadata:
   - Which detection method was used
   - Trend indicators (when available)
   - Example count

4. Format for Gamma:
   - Use markdown
   - Clean structure
   - Readable by executives
"""
    
    def get_task_description(self, context: AgentContext) -> str:
        """Describe formatting task"""
        return "Format all agent results into Hilary's card structure for Gamma presentation"
    
    def format_context_data(self, context: AgentContext) -> str:
        """Format agent results for output generation"""
        return "Agent results to format: All previous agents"
    
    def validate_input(self, context: AgentContext) -> bool:
        """
        Validate input with graceful handling of missing sections.
        
        Checks for required and optional agent outputs.
        Logs warnings for missing sections but doesn't fail.
        """
        if not hasattr(context, 'previous_results') or context.previous_results is None:
            raise ValueError("Missing previous_results in context")
        
        previous_results = context.previous_results
        missing_agents = []
        missing_optional = []
        
        # Check each expected agent
        for agent_name, config in self.EXPECTED_AGENTS.items():
            is_required = config['required']
            
            # Check if agent result exists in previous_results
            if agent_name not in previous_results:
                if is_required:
                    missing_agents.append(agent_name)
                else:
                    missing_optional.append(agent_name)
        
        # Log warnings for missing optional sections
        if missing_optional:
            warning_msg = f"Missing optional agent outputs: {', '.join(missing_optional)}"
            self.logger.warning(warning_msg)
            
            # Add to audit trail if available
            if hasattr(self, 'audit') and self.audit:
                self.audit.warning(
                    "Missing Optional Sections",
                    warning_msg,
                    impact="Some sections will show placeholder messages"
                )
        
        # Fail only if required sections are missing
        if missing_agents:
            error_msg = f"Missing required agent outputs: {', '.join(missing_agents)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.logger.info(
            f"Input validation complete. "
            f"Present: {len(previous_results)}, "
            f"Missing optional: {len(missing_optional)}"
        )
        
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate formatted output"""
        return 'formatted_output' in result
    
    def _generate_missing_section_placeholder(self, section_name: str, agent_name: str) -> str:
        """
        Generate placeholder message for missing section.
        
        Args:
            section_name: Name of the missing section (e.g., "Trend Analysis")
            agent_name: Name of the agent that should have provided data
        
        Returns:
            Markdown-formatted placeholder message
        """
        return f"""
## {section_name}

> ⚠️ **Section Unavailable**
>
> The {agent_name} did not complete successfully or was not run.
> This section has been omitted from the report.
>
> To include this section, ensure the {agent_name} runs successfully
> before the OutputFormatterAgent.

---
"""
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute output formatting"""
        start_time = datetime.now()
        
        try:
            self.validate_input(context)
            
            self.logger.info("OutputFormatterAgent: Formatting results into Hilary's structure")
            
            # Get results from previous agents
            segmentation = context.previous_results.get('SegmentationAgent', {}).get('data', {})
            topic_detection = context.previous_results.get('TopicDetectionAgent', {}).get('data', {})
            topic_dist = topic_detection.get('topic_distribution', {})
            topic_sentiments = context.previous_results.get('TopicSentiments', {})  # Dict by topic
            topic_examples = context.previous_results.get('TopicExamples', {})  # Dict by topic
            fin_performance = context.previous_results.get('FinPerformanceAgent', {}).get('data', {})
            trends = context.previous_results.get('TrendAgent', {}).get('data', {}).get('trends', {})
            
            # Get sub-topic data (defensive read for backward compatibility)
            subtopics_data = context.previous_results.get('SubTopicDetectionAgent', {}).get('data', {}).get('subtopics_by_tier1_topic', {})
            if subtopics_data:
                self.logger.info(f"Sub-topic data available: {len(subtopics_data)} Tier 1 topics with sub-topic breakdowns")
            else:
                self.logger.info("No sub-topic data available (backward compatibility mode)")
            
            # Build output
            output_sections = []
            
            # Get period type from metadata
            period_type = context.metadata.get('period_type', 'weekly')
            period_label = context.metadata.get('period_label', 'Weekly')
            week_id = context.metadata.get('week_id', datetime.now().strftime('%Y-W%W'))
            
            # Build header with actual date range instead of week code
            if context.start_date and context.end_date:
                start_str = context.start_date.strftime('%b %d')
                end_str = context.end_date.strftime('%b %d, %Y')
                # If different months, include month in start date
                if context.start_date.month != context.end_date.month:
                    start_str = context.start_date.strftime('%b %d')
                header_title = f"# Voice of Customer Analysis: {start_str} - {end_str}"
            else:
                header_title = f"# Voice of Customer Analysis - Week {week_id}"
            
            output_sections.append(header_title)
            output_sections.append("")
            
            # Executive Summary Section
            output_sections.append("## Executive Summary")
            output_sections.append("")
            
            # Get total counts from segmentation
            seg_summary = segmentation.get('segmentation_summary', {})
            total_convs = len(context.conversations) if context.conversations else 0
            paid_count = seg_summary.get('paid_count', 0)
            free_count = seg_summary.get('free_count', 0)
            
            output_sections.append(f"**Total Interactions**: {total_convs:,} conversations analyzed")
            output_sections.append(f"**Customer Breakdown**:")
            output_sections.append(f"- Paid Customers (Human Support): {paid_count:,} ({seg_summary.get('paid_percentage', 0):.1f}%)")
            output_sections.append(f"- Free Customers (AI-Only): {free_count:,} ({seg_summary.get('free_percentage', 0):.1f}%)")
            output_sections.append("")
            
            # Topics summary
            output_sections.append(f"**Topics Identified**: {len(topic_dist)} categories")
            if len(topic_dist) > 0:
                top_3_topics = sorted(topic_dist.items(), key=lambda x: x[1]['volume'], reverse=True)[:3]
                output_sections.append(f"**Top Issues**:")
                for topic_name, topic_stats in top_3_topics:
                    volume = topic_stats['volume']
                    pct = topic_stats['percentage']
                    output_sections.append(f"- {topic_name}: {volume:,} conversations ({pct:.1f}%)")
            output_sections.append("")
            
            # Add language breakdown if available
            lang_dist = seg_summary.get('language_distribution', {})
            if lang_dist:
                total_langs = seg_summary.get('total_languages', len(lang_dist))
                output_sections.append(f"**Languages**: {total_langs} languages represented")
                
                # Show top 5 languages
                top_langs = list(lang_dist.items())[:5]
                lang_summary = ", ".join([f"{lang} ({count})" for lang, count in top_langs])
                output_sections.append(f"**Primary Languages**: {lang_summary}")
                output_sections.append("")
            
            output_sections.append("---")
            output_sections.append("")
            
            # Week-over-Week Changes Section (if prior snapshot exists)
            comparison_data = context.metadata.get('comparison_data')
            if comparison_data:
                self.logger.info("Adding Week-over-Week Changes section")
                comparison_section = self._format_comparison_section(comparison_data)
                output_sections.append(comparison_section)
                output_sections.append("---")
                output_sections.append("")
            else:
                self.logger.info("No prior snapshot available - skipping week-over-week section")
            
            # Section 1: Voice of Customer (Paid Customers)
            output_sections.append("## Customer Topics (Paid Tier - Human Support)")
            output_sections.append("")
            
            # Sort topics by volume
            sorted_topics = sorted(topic_dist.items(), key=lambda x: x[1]['volume'], reverse=True)
            
            # Get LLM trend insights from TrendAgent (outside loop for efficiency)
            trend_agent_data = context.previous_results.get('TrendAgent', {}).get('data', {})
            trend_insights = trend_agent_data.get('trend_insights', {})
            
            for topic_name, topic_stats in sorted_topics:
                # Get sentiment and examples for this topic (defensive reads)
                sentiment = topic_sentiments.get(topic_name, {}).get('data', {}).get('sentiment_insight', 'No sentiment analysis available')
                examples_data = topic_examples.get(topic_name, {}).get('data', {})
                examples = examples_data.get('examples', []) if examples_data else []
                
                # Validate examples is a list
                if not isinstance(examples, list):
                    self.logger.warning(f"Topic '{topic_name}' has invalid examples format, skipping examples")
                    examples = []
                
                # Get trend if available
                trend = trends.get(topic_name, {})
                trend_indicator = ""
                trend_explanation = ""
                if trend and 'direction' in trend:
                    trend_indicator = f" {trend['direction']} {trend.get('alert', '')}"
                
                # Get trend explanation from pre-fetched trend insights
                if topic_name in trend_insights:
                    trend_explanation = trend_insights[topic_name]
                
                # Get sub-topic data for this topic
                subtopics_for_topic = subtopics_data.get(topic_name, {}) if subtopics_data else {}
                
                # Format card
                card = self._format_topic_card(
                    topic_name,
                    topic_stats,
                    sentiment,
                    examples,
                    trend_indicator,
                    trend_explanation,
                    period_label,
                    subtopics_for_topic
                )
                output_sections.append(card)
            
            # Section 2: Fin AI Performance
            has_tier_data = False
            if fin_performance:
                # Check if we have tier-based data (new format) or legacy format
                has_tier_data = 'free_tier' in fin_performance or 'paid_tier' in fin_performance

                if has_tier_data:
                    # New format: separate cards for each tier
                    output_sections.append("\n## Fin AI Performance Analysis")
                    output_sections.append("")

                    # Free tier card (Fin-only)
                    if 'free_tier' in fin_performance and fin_performance.get('total_free_tier', 0) > 0:
                        free_card = self._format_free_tier_fin_card(fin_performance)
                        output_sections.append(free_card)

                    # Paid tier card (Fin-resolved)
                    if 'paid_tier' in fin_performance and fin_performance.get('total_paid_tier', 0) > 0:
                        paid_card = self._format_paid_tier_fin_card(fin_performance)
                        output_sections.append(paid_card)

                    # Tier comparison insights (if available)
                    tier_comparison = fin_performance.get('tier_comparison')
                    if tier_comparison:
                        comparison_card = self._format_tier_comparison_card(tier_comparison)
                        output_sections.append(comparison_card)
 
                    # Add LLM insights if available (tier-based branch)
                    llm_insights = fin_performance.get('llm_insights')
                    if llm_insights:
                        output_sections.append("**AI Performance Insights**\n")
                        output_sections.append(f"{llm_insights}\n")
                        output_sections.append("\n---\n")
                else:
                    # Legacy format: single unified card (backward compatibility)
                    output_sections.append("\n## Fin AI Performance (AI-Only Support)")
                    output_sections.append("")
                    fin_card = self._format_fin_card(fin_performance)
                    output_sections.append(fin_card)
            else:
                # Fin performance data missing - add placeholder
                placeholder = self._generate_missing_section_placeholder(
                    "Fin AI Performance Analysis",
                    "FinPerformanceAgent"
                )
                output_sections.append(placeholder)
            
            # Combine all sections
            formatted_output = '\n'.join(output_sections)
            
            result_data = {
                'formatted_output': formatted_output,
                'total_topics': len(sorted_topics),
                'week_id': week_id,
                'has_trend_data': len(trends) > 0,
                'has_tier_based_fin_data': has_tier_data if fin_performance else False,
                'free_tier_conversations': fin_performance.get('total_free_tier', 0) if has_tier_data and fin_performance else 0,
                'paid_tier_conversations': fin_performance.get('total_paid_tier', 0) if has_tier_data and fin_performance else 0
            }
            
            self.validate_output(result_data)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"OutputFormatterAgent: Completed in {execution_time:.2f}s")
            self.logger.info(f"   Formatted {len(sorted_topics)} topic cards")

            if fin_performance:
                if has_tier_data:
                    self.logger.info(f"   Fin AI cards: Free tier ({fin_performance.get('total_free_tier', 0)} convs), Paid tier ({fin_performance.get('total_paid_tier', 0)} convs)")
                else:
                    self.logger.info(f"   Fin AI card: Legacy format (single unified card)")
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=1.0,
                confidence_level=ConfidenceLevel.HIGH,
                limitations=[],
                sources=["All previous agent results"],
                execution_time=execution_time,
                token_count=0
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"OutputFormatterAgent error: {e}")
            
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                error_message=str(e),
                execution_time=execution_time
            )
    
    def _format_topic_card(self, topic_name: str, stats: Dict, sentiment: str, examples: List[Dict], trend: str, trend_explanation: str = "", period_label: str = "Weekly", subtopics: Dict = None) -> str:
        """Format a single topic card"""
        detection_method = stats.get('detection_method', 'unknown')
        method_label = "Intercom conversation attribute" if detection_method == 'attribute' else "Keyword detection" if detection_method == 'keyword' else "Detection method not specified"
        
        card = f"""### {topic_name}{trend}
**{stats['volume']} tickets / {stats['percentage']}% of {period_label.lower()} volume**  
**Detection Method**: {method_label}

**Sentiment**: {sentiment}
"""
        
        # Add trend explanation if available
        if trend_explanation:
            card += f"\n**Trend Analysis**: {trend_explanation}\n"
        
        # Add sub-topic breakdown if available
        if subtopics and (subtopics.get('tier2') or subtopics.get('tier3')):
            card += "\n**Sub-Topic Breakdown**:\n"
            
            # Tier 2 sub-topics
            tier2 = subtopics.get('tier2', {})
            if tier2:
                card += "\n_Tier 2: From Intercom Data_\n"
                # Sort by volume descending and limit to top 10
                sorted_tier2 = sorted(tier2.items(), key=lambda x: x[1].get('volume', 0), reverse=True)[:10]
                for subtopic_name, subtopic_data in sorted_tier2:
                    volume = subtopic_data.get('volume', 0)
                    percentage = subtopic_data.get('percentage', 0)
                    source = subtopic_data.get('source', 'unknown')
                    card += f"  - {subtopic_name}: {volume} conversations ({percentage}%) [Source: {source}]\n"
            
            # Tier 3 sub-topics
            tier3 = subtopics.get('tier3', {})
            if tier3:
                card += "\n_Tier 3: AI-Discovered Themes_\n"
                # Sort by volume descending and limit to top 5
                sorted_tier3 = sorted(tier3.items(), key=lambda x: x[1].get('volume', 0), reverse=True)[:5]
                for theme_name, theme_data in sorted_tier3:
                    volume = theme_data.get('volume', 0)
                    percentage = theme_data.get('percentage', 0)
                    card += f"  - {theme_name}: {volume} conversations ({percentage}%)\n"
            
            card += "\n"
        
        card += "**Examples**:\n\n"
        
        # Add examples with validation, language info, translation, and enhanced link formatting
        if examples and len(examples) > 0:
            for i, example in enumerate(examples, 1):
                # Defensive read of example fields
                preview = example.get('preview', 'No preview available') if isinstance(example, dict) else 'Invalid example format'
                url = example.get('intercom_url', '#') if isinstance(example, dict) else '#'
                language = example.get('language', 'English') if isinstance(example, dict) else 'English'
                translation = example.get('translation') if isinstance(example, dict) else None
                
                # Format based on whether translation is available
                if translation and language != 'English':
                    # Show translation first (English), then original in italics
                    card += f"{i}. \"{translation}\"\n"
                    card += f"   _{language}: \"{preview}\"_\n"
                    card += f"   **[📎 View in Intercom →]({url})**\n\n"
                else:
                    # Show language label for non-English without translation
                    lang_label = f"_{language}_ " if language and language != 'English' else ""
                    card += f"{i}. {lang_label}\"{preview}\"\n"
                    card += f"   **[📎 View in Intercom →]({url})**\n\n"
        else:
            card += "_No examples available - topic may have low volume or quality conversations_\n"
        
        card += "\n---\n"
        
        return card
    
    def _format_fin_card(self, fin_data: Dict) -> str:
        """Format Fin AI performance card"""
        total = fin_data.get('total_fin_conversations', 0)
        resolution_rate = fin_data.get('resolution_rate', 0)
        knowledge_gaps = fin_data.get('knowledge_gaps_count', 0)
        
        card = f"""### Fin AI Analysis
**{total} conversations handled by Fin this week**

**What Fin is Doing Well**:
- Resolution rate: {resolution_rate:.1%} of conversations resolved without escalation request
"""
        
        # Top performing topics
        top_topics = fin_data.get('top_performing_topics', [])
        if top_topics:
            card += "\nTop performing topics:\n"
            for topic, stats in top_topics:
                card += f"- {topic}: {stats['resolution_rate']:.1%} resolution rate\n"
        
        card += f"""
**Knowledge Gaps**:
- {knowledge_gaps} conversations where Fin gave incorrect/incomplete information
"""
        
        # Knowledge gap examples
        gap_examples = fin_data.get('knowledge_gap_examples', [])
        if gap_examples:
            card += "\nExamples:\n"
            for ex in gap_examples[:3]:
                preview = ex.get('preview', 'No preview available')
                url = ex.get('intercom_url', '#')
                card += f"- \"{preview}...\" - [View conversation]({url})\n"
        
        # Struggling topics
        struggling = fin_data.get('struggling_topics', [])
        if struggling:
            card += "\n**Topics where Fin struggles**:\n"
            for topic, stats in struggling:
                card += f"- {topic}: {stats['resolution_rate']:.1%} resolution rate ({stats['total']} conversations)\n"
        
        # Add LLM-generated insights if available
        llm_insights = fin_data.get('llm_insights', '')
        if llm_insights:
            card += f"\n**AI Performance Insights**:\n{llm_insights}\n"

        card += "\n---\n"

        return card

    def _format_subtopic_metrics_line(self, subtopic_name: str, metrics: Dict) -> str:
        """
        Format a single sub-topic metrics line with consistent formatting.
        
        Args:
            subtopic_name: Name of the sub-topic
            metrics: Dict with total, resolution_rate, knowledge_gap_rate, escalation_rate, avg_rating, rated_count
            
        Returns:
            Formatted string for sub-topic performance
        """
        total = metrics.get('total', 0)
        resolution_rate = metrics.get('resolution_rate', 0)
        knowledge_gap_rate = metrics.get('knowledge_gap_rate', 0)
        escalation_rate = metrics.get('escalation_rate', 0)
        avg_rating = metrics.get('avg_rating')
        rated_count = metrics.get('rated_count', 0)
        
        line = f"  - {subtopic_name}: {resolution_rate:.1%} resolution | {knowledge_gap_rate:.1%} gaps | {escalation_rate:.1%} escalation"
        
        if avg_rating is not None:
            line += f" | ⭐ {avg_rating:.1f}/5 ({rated_count} rated)"
        
        line += f" ({total} convs)"
        
        return line
    
    def _format_free_tier_fin_card(self, fin_data: Dict) -> str:
        """
        Format Fin AI performance card for Free tier customers.

        Free tier customers can ONLY interact with Fin AI (no human escalation available).
        Focus on resolution rate, knowledge gaps, and topic performance.
        """
        free_tier = fin_data.get('free_tier', {})
        total_free = fin_data.get('total_free_tier', 0)

        if not free_tier or total_free == 0:
            return ""

        resolution_rate = free_tier.get('resolution_rate', 0)
        knowledge_gaps = free_tier.get('knowledge_gaps_count', 0)
        top_topics = free_tier.get('top_performing_topics', [])
        struggling = free_tier.get('struggling_topics', [])
        gap_examples = free_tier.get('knowledge_gap_examples', [])

        # Get CSAT data (updated with eligible count)
        avg_rating = free_tier.get('avg_rating')
        rated_count = free_tier.get('rated_count', 0)
        eligible_count = free_tier.get('rating_eligible_count', 0)
        rating_response_rate = free_tier.get('rating_response_rate', 0)
        
        card = f"""### Free Tier: Fin AI Performance (AI-Only Support)
**{total_free} conversations from Free tier customers**

**Performance Overview**:
- Resolution rate: {resolution_rate:.1%} (Fin resolved without admin escalation)
- Knowledge gaps: {knowledge_gaps} conversations with incorrect/incomplete information ({knowledge_gaps/total_free*100:.1f}% gap rate)
"""
        
        # Add CSAT if available (only for conversations with ≥2 responses from both sides)
        if avg_rating is not None:
            card += f"- **Customer Satisfaction (CSAT):** ⭐ {avg_rating:.2f}/5.0 from {rated_count} ratings ({rating_response_rate:.1f}% of {eligible_count} eligible)\n"
            card += f"  _Note: Only {eligible_count} conversations eligible for rating (≥2 responses from both customer and Fin)_\n"
        else:
            card += f"- **Customer Satisfaction (CSAT):** No ratings ({eligible_count} eligible conversations, {rated_count} actually rated)\n"

        # What Fin does well
        if top_topics:
            card += "\n**What Fin Does Well (Free Tier)**:\n"
            for topic, stats in top_topics:
                card += f"- {topic}: {stats['resolution_rate']:.1%} resolution rate ({stats['total']} conversations)\n"

        # Performance by sub-topic
        performance_by_subtopic = free_tier.get('performance_by_subtopic', {})
        if performance_by_subtopic:
            card += "\n**Performance by Sub-Topic**:\n"
            for tier1_topic in sorted(performance_by_subtopic.keys()):
                card += f"\n_{tier1_topic}_\n"
                subtopic_tiers = performance_by_subtopic[tier1_topic]
                
                # Tier 2 sub-topics (top 5 by resolution rate)
                tier2_metrics = subtopic_tiers.get('tier2', {})
                if tier2_metrics:
                    sorted_tier2 = sorted(tier2_metrics.items(), key=lambda x: x[1].get('resolution_rate', 0), reverse=True)[:5]
                    for subtopic_name, metrics in sorted_tier2:
                        card += self._format_subtopic_metrics_line(subtopic_name, metrics) + "\n"
                
                # Tier 3 themes (top 3 by resolution rate)
                tier3_metrics = subtopic_tiers.get('tier3', {})
                if tier3_metrics:
                    sorted_tier3 = sorted(tier3_metrics.items(), key=lambda x: x[1].get('resolution_rate', 0), reverse=True)[:3]
                    for theme_name, metrics in sorted_tier3:
                        card += self._format_subtopic_metrics_line(theme_name, metrics) + "\n"
            
            card += "\n"

        # Knowledge gaps
        card += f"\n**Knowledge Gaps (Free Tier)**:\n"
        card += f"- {knowledge_gaps} conversations where Fin gave incorrect/incomplete information\n"

        if gap_examples:
            card += "\nExamples:\n"
            for ex in gap_examples:
                preview = ex.get('preview', 'No preview available')
                url = ex.get('intercom_url', '#')
                card += f"- \"{preview}...\" - [View conversation]({url})\n"

        # Struggling topics
        if struggling:
            card += "\n**Topics Where Fin Struggles (Free Tier)**:\n"
            for topic, stats in struggling:
                card += f"- {topic}: {stats['resolution_rate']:.1%} resolution rate ({stats['total']} conversations)\n"

        card += "\n**Key Insight**: Free tier customers have no option to escalate to human support, so Fin's performance directly impacts their experience.\n"
        card += "\n---\n"

        return card

    def _format_paid_tier_fin_card(self, fin_data: Dict) -> str:
        """
        Format Fin AI performance card for Paid tier customers who resolved with Fin.

        Paid tier customers CHOSE not to escalate to human support.
        Focus on why they were satisfied with Fin and what made it successful.
        """
        paid_tier = fin_data.get('paid_tier', {})
        total_paid = fin_data.get('total_paid_tier', 0)

        if not paid_tier or total_paid == 0:
            return ""

        resolution_rate = paid_tier.get('resolution_rate', 0)
        knowledge_gaps = paid_tier.get('knowledge_gaps_count', 0)
        top_topics = paid_tier.get('top_performing_topics', [])
        struggling = paid_tier.get('struggling_topics', [])
        gap_examples = paid_tier.get('knowledge_gap_examples', [])
        
        # Get CSAT data (updated with eligible count)
        avg_rating = paid_tier.get('avg_rating')
        rated_count = paid_tier.get('rated_count', 0)
        eligible_count = paid_tier.get('rating_eligible_count', 0)
        rating_response_rate = paid_tier.get('rating_response_rate', 0)

        card = f"""### Paid Tier: Fin-Resolved Conversations
**{total_paid} paid customers resolved their issues with Fin AI (no human escalation needed)**

**Performance Overview**:
- Resolution rate: {resolution_rate:.1%} (Fin resolved without admin escalation)
- Knowledge gaps: {knowledge_gaps} conversations with incorrect/incomplete information ({knowledge_gaps/total_paid*100:.1f}% gap rate)
"""
        
        # Add CSAT if available (only for conversations with ≥2 responses from both sides)
        if avg_rating is not None:
            card += f"- **Customer Satisfaction (CSAT):** ⭐ {avg_rating:.2f}/5.0 from {rated_count} ratings ({rating_response_rate:.1f}% of {eligible_count} eligible)\n"
            card += f"  _Note: Only {eligible_count} conversations eligible for rating (≥2 responses from both customer and Fin)_\n"
        else:
            card += f"- **Customer Satisfaction (CSAT):** No ratings ({eligible_count} eligible conversations, {rated_count} actually rated)\n"

        # What Fin does well
        if top_topics:
            card += "\n**What Fin Does Well (Paid Tier)**:\n"
            for topic, stats in top_topics:
                card += f"- {topic}: {stats['resolution_rate']:.1%} resolution rate ({stats['total']} conversations)\n"
            card += "- These paid customers had the option to escalate but chose not to\n"

        # Performance by sub-topic
        performance_by_subtopic = paid_tier.get('performance_by_subtopic', {})
        if performance_by_subtopic:
            card += "\n**Performance by Sub-Topic**:\n"
            for tier1_topic in sorted(performance_by_subtopic.keys()):
                card += f"\n_{tier1_topic}_\n"
                subtopic_tiers = performance_by_subtopic[tier1_topic]
                
                # Tier 2 sub-topics (top 5 by resolution rate)
                tier2_metrics = subtopic_tiers.get('tier2', {})
                if tier2_metrics:
                    sorted_tier2 = sorted(tier2_metrics.items(), key=lambda x: x[1].get('resolution_rate', 0), reverse=True)[:5]
                    for subtopic_name, metrics in sorted_tier2:
                        card += self._format_subtopic_metrics_line(subtopic_name, metrics) + "\n"
                
                # Tier 3 themes (top 3 by resolution rate)
                tier3_metrics = subtopic_tiers.get('tier3', {})
                if tier3_metrics:
                    sorted_tier3 = sorted(tier3_metrics.items(), key=lambda x: x[1].get('resolution_rate', 0), reverse=True)[:3]
                    for theme_name, metrics in sorted_tier3:
                        card += self._format_subtopic_metrics_line(theme_name, metrics) + "\n"
            
            card += "\n"

        # Knowledge gaps
        card += f"\n**Knowledge Gaps (Paid Tier)**:\n"
        card += f"- {knowledge_gaps} conversations where Fin gave incorrect/incomplete information\n"

        if gap_examples:
            card += "\nExamples:\n"
            for ex in gap_examples:
                preview = ex.get('preview', 'No preview available')
                url = ex.get('intercom_url', '#')
                card += f"- \"{preview}...\" - [View conversation]({url})\n"

        # Struggling topics
        if struggling:
            card += "\n**Topics Where Fin Struggles (Paid Tier)**:\n"
            for topic, stats in struggling:
                card += f"- {topic}: {stats['resolution_rate']:.1%} resolution rate ({stats['total']} conversations)\n"

        card += "\n**Key Insight**: These paid customers had access to human support but chose to resolve with Fin, indicating high confidence in AI responses for these topics.\n"
        card += "\n---\n"

        return card

    def _format_tier_comparison_card(self, comparison_data: Dict) -> str:
        """
        Format tier comparison insights card.

        Highlights key differences in Fin performance between Free and Paid tiers.
        """
        if not comparison_data:
            return ""

        free_res = comparison_data.get('free_tier_resolution', 0)
        paid_res = comparison_data.get('paid_tier_resolution', 0)
        res_delta = comparison_data.get('resolution_rate_delta', 0)
        res_interpretation = comparison_data.get('resolution_rate_interpretation', '')

        free_gap_rate = comparison_data.get('free_tier_knowledge_gaps', 0)
        paid_gap_rate = comparison_data.get('paid_tier_knowledge_gaps', 0)
        gap_delta = comparison_data.get('knowledge_gap_delta', 0)
        gap_interpretation = comparison_data.get('knowledge_gap_interpretation', '')

        card = f"""### Tier Comparison: Key Insights

**Resolution Rate Comparison**:
- Free tier: {free_res:.1%}
- Paid tier: {paid_res:.1%}
- Delta: {res_delta:+.1%} ({res_interpretation})

**Knowledge Gaps Comparison**:
- Free tier: {free_gap_rate:.1%}
- Paid tier: {paid_gap_rate:.1%}
- Delta: {gap_delta:+.1%} ({gap_interpretation})

**Strategic Implications**:
"""

        # Add strategic implications based on the data
        if abs(res_delta) < 0.05:
            card += "- Both tiers show similar resolution rates, suggesting Fin performs consistently regardless of customer tier\n"
        elif res_delta > 0:
            card += "- Paid tier shows higher resolution rate. This could indicate:\n"
            card += "  - Paid customers may have simpler queries that Fin handles well\n"
            card += "  - Paid customers may have higher tolerance for AI responses\n"
            card += "  - Paid tier queries may be better covered by Fin's knowledge base\n"
        else:
            card += "- Free tier shows higher resolution rate. This could indicate:\n"
            card += "  - Free tier queries are more straightforward\n"
            card += "  - Paid customers may have more complex needs that lead to escalation\n"

        if abs(gap_delta) > 0.05:
            if gap_delta > 0:
                card += "- Paid tier experiences more knowledge gaps, suggesting opportunities to improve Fin's coverage for paid customer topics\n"
            else:
                card += "- Free tier experiences more knowledge gaps, suggesting opportunities to improve Fin's coverage for free customer topics\n"

        card += "\n---\n"

        return card

    def _format_comparison_section(self, comparison_data: Dict[str, Any]) -> str:
        """
        Format week-over-week comparison section.
        
        Args:
            comparison_data: Comparison data from HistoricalSnapshotService
            
        Returns:
            Formatted markdown string with all comparison subsections
        """
        try:
            sections = []
            sections.append("## Week-over-Week Changes 📊")
            sections.append("")
            
            # 1. Volume Changes subsection
            volume_changes = comparison_data.get('volume_changes', {})
            if volume_changes:
                sections.append("### Volume Changes")
                sections.append("")
                
                # Sort by absolute change descending, limit to top 10
                sorted_changes = sorted(
                    volume_changes.items(),
                    key=lambda x: abs(x[1].get('change', 0)),
                    reverse=True
                )[:10]
                
                for topic, changes in sorted_changes:
                    current = changes.get('current', 0)
                    change = changes.get('change', 0)
                    pct = changes.get('pct', 0)
                    sections.append(f"- **{topic}**: {current} conversations ({change:+d}, {pct:+.1%})")
                
                sections.append("")
            
            # 2. Significant Changes subsection
            significant_changes = comparison_data.get('significant_changes', [])
            if significant_changes:
                sections.append("### Significant Changes (>25% change, >5 conversations)")
                sections.append("")
                
                for change in significant_changes:
                    topic = change.get('topic', 'Unknown')
                    alert = change.get('alert', '')
                    change_val = change.get('change', 0)
                    pct = change.get('pct', 0)
                    direction = change.get('direction', 'unknown')
                    
                    sections.append(f"{alert} **{topic}**: {change_val:+d} conversations ({pct:+.1%})")
                
                sections.append("")
                sections.append(f"_Interpretation: {direction} trend detected_")
                sections.append("")
            
            # 3. Emerging Patterns subsection
            emerging_patterns = comparison_data.get('emerging_patterns', [])
            if emerging_patterns:
                sections.append("### Emerging Patterns (New Topics) 🆕")
                sections.append("")
                
                for pattern in emerging_patterns:
                    topic = pattern.get('topic', 'Unknown')
                    volume = pattern.get('volume', 0)
                    sections.append(f"- **{topic}**: {volume} conversations (new this period)")
                
                sections.append("")
                sections.append("_These topics appeared for the first time this period_")
                sections.append("")
            
            # 4. Declining Patterns subsection
            declining_patterns = comparison_data.get('declining_patterns', [])
            if declining_patterns:
                sections.append("### Declining Patterns (Disappeared Topics) 📉")
                sections.append("")
                
                for pattern in declining_patterns:
                    topic = pattern.get('topic', 'Unknown')
                    prior_volume = pattern.get('prior_volume', 0)
                    sections.append(f"- **{topic}**: {prior_volume} conversations last period (disappeared)")
                
                sections.append("")
                sections.append("_These topics were present last period but not this period_")
                sections.append("")
            
            # 5. Sentiment Shifts subsection
            sentiment_changes = comparison_data.get('sentiment_changes', {})
            if sentiment_changes:
                # Filter for notable shifts (>10 percentage point change)
                notable_shifts = [
                    (topic, changes) for topic, changes in sentiment_changes.items()
                    if abs(changes.get('positive_delta', 0)) > 0.1
                ]
                
                if notable_shifts:
                    sections.append("### Sentiment Shifts")
                    sections.append("")
                    
                    # Sort by absolute positive delta, limit to top 5
                    notable_shifts.sort(key=lambda x: abs(x[1].get('positive_delta', 0)), reverse=True)
                    notable_shifts = notable_shifts[:5]
                    
                    for topic, changes in notable_shifts:
                        shift = changes.get('shift', 'stable')
                        positive_delta = changes.get('positive_delta', 0)
                        sections.append(f"- **{topic}**: {shift} ({positive_delta:+.1%} positive sentiment)")
                    
                    sections.append("")
            
            # 6. Resolution Quality Changes subsection
            resolution_changes = comparison_data.get('resolution_changes', {})
            if resolution_changes:
                sections.append("### Resolution Quality Changes")
                sections.append("")
                
                fcr_delta = resolution_changes.get('fcr_rate_delta')
                if fcr_delta is not None:
                    interpretation = "improving" if fcr_delta > 0 else "declining" if fcr_delta < 0 else "stable"
                    sections.append(f"- **First Contact Resolution**: {fcr_delta:+.1%} ({interpretation})")
                
                time_delta = resolution_changes.get('resolution_time_delta')
                if time_delta is not None:
                    interpretation = "improving" if time_delta < 0 else "declining" if time_delta > 0 else "stable"
                    sections.append(f"- **Median Resolution Time**: {time_delta:+.1f} hours ({interpretation})")
                
                overall_interpretation = resolution_changes.get('interpretation', 'stable')
                sections.append("")
                sections.append(f"_Overall: Resolution quality is **{overall_interpretation}**_")
                sections.append("")
            
            return '\n'.join(sections)
            
        except Exception as e:
            self.logger.warning(f"Error formatting comparison section: {e}")
            return "## Week-over-Week Changes 📊\n\n_Comparison data unavailable_\n\n"

