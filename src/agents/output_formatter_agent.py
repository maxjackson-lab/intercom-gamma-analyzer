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
        'TopicExamples': {'required': False, 'key': 'examples'},
        'AnalyticalInsights': {'required': False, 'key': 'analytical_insights'}
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
            
            # Auto-generated narrative summary
            analytical_insights = context.previous_results.get('AnalyticalInsights', {})
            if analytical_insights:
                narrative_parts = []
                
                # Base narrative
                narrative_parts.append(f"This week's analysis reveals {len(topic_dist)} customer topics across {total_convs:,} conversations.")
                
                # Significant changes (if comparison data available)
                comparison_data = context.metadata.get('comparison_data')
                if comparison_data:
                    significant_changes = comparison_data.get('significant_changes', [])
                    if significant_changes:
                        top_change = significant_changes[0]
                        top_topic = top_change.get('topic', 'Unknown')
                        pct = top_change.get('pct', 0)
                        narrative_parts.append(f"Notable changes include {top_topic} ({pct:+.1%}).")
                
                # Churn signals
                churn_data = analytical_insights.get('ChurnRiskAgent', {}).get('data', {})
                high_risk_count = len(churn_data.get('high_risk_conversations', []))
                if high_risk_count > 0:
                    narrative_parts.append(f"{high_risk_count} conversation{'s' if high_risk_count != 1 else ''} flagged for churn risk review.")
                
                # Anomalies
                quality_data = analytical_insights.get('QualityInsightsAgent', {}).get('data', {})
                anomaly_count = len(quality_data.get('anomalies', []))
                if anomaly_count > 0:
                    narrative_parts.append(f"{anomaly_count} statistical anomal{'ies' if anomaly_count != 1 else 'y'} detected.")
                
                if len(narrative_parts) > 1:
                    output_sections.append("")
                    output_sections.append(" ".join(narrative_parts))
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
            
            # Pattern Intelligence Section (if analytical insights available)
            # Note: This now returns separate top-level sections for Correlations and Anomalies
            if analytical_insights:
                try:
                    pattern_section = self._format_pattern_intelligence_section(analytical_insights)
                    if pattern_section:
                        output_sections.append(pattern_section)
                except Exception as e:
                    self.logger.warning(f"Error adding Pattern Intelligence section: {e}")
            
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
                    subtopics_for_topic,
                    context.conversations  # Pass conversations for highlights/lowlights extraction
                )
                output_sections.append(card)
            
            # Churn Risk Section (if analytical insights available)
            if analytical_insights:
                try:
                    churn_data = analytical_insights.get('ChurnRiskAgent', {}).get('data', {})
                    if churn_data and churn_data.get('high_risk_conversations'):
                        churn_section = self._format_churn_risk_section(churn_data)
                        if churn_section:
                            output_sections.append(churn_section)
                            output_sections.append("---")
                            output_sections.append("")
                except Exception as e:
                    self.logger.warning(f"Error adding Churn Risk section: {e}")
            
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
            
            # Resolution Quality Metrics Section (if analytical insights available)
            if analytical_insights:
                try:
                    quality_data = analytical_insights.get('QualityInsightsAgent', {}).get('data', {})
                    if quality_data:
                        quality_section = self._format_resolution_quality_section(quality_data)
                        if quality_section:
                            output_sections.append(quality_section)
                            output_sections.append("---")
                            output_sections.append("")
                except Exception as e:
                    self.logger.warning(f"Error adding Resolution Quality section: {e}")
            
            # Analysis Confidence & Limitations Section (if analytical insights available)
            if analytical_insights:
                try:
                    confidence_data = analytical_insights.get('ConfidenceMetaAgent', {}).get('data', {})
                    if confidence_data:
                        confidence_section = self._format_confidence_limitations_section(confidence_data)
                        if confidence_section:
                            output_sections.append(confidence_section)
                            output_sections.append("---")
                            output_sections.append("")
                except Exception as e:
                    self.logger.warning(f"Error adding Confidence & Limitations section: {e}")
            
            # What We Cannot Determine (Yet) Section
            historical_context = context.metadata.get('historical_context', {'weeks_available': 0})
            confidence_data_for_cannot_determine = analytical_insights.get('ConfidenceMetaAgent', {}).get('data', {}) if analytical_insights else {}
            try:
                cannot_determine_section = self._format_cannot_determine_section(historical_context, confidence_data_for_cannot_determine)
                if cannot_determine_section:
                    output_sections.append(cannot_determine_section)
            except Exception as e:
                self.logger.warning(f"Error adding Cannot Determine section: {e}")
            
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
            
            # Log new analytical sections
            if analytical_insights:
                correlations_count = len(analytical_insights.get('CorrelationAgent', {}).get('data', {}).get('correlations', []))
                churn_signals_count = len(analytical_insights.get('ChurnRiskAgent', {}).get('data', {}).get('high_risk_conversations', []))
                anomalies_count = len(analytical_insights.get('QualityInsightsAgent', {}).get('data', {}).get('anomalies', []))
                self.logger.info(f"   Formatted {correlations_count} correlations, {churn_signals_count} churn signals, {anomalies_count} anomalies")
            
            # Log total section count
            self.logger.info(f"   Total sections: {len(output_sections)}")
            
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
    
    def _format_topic_card(self, topic_name: str, stats: Dict, sentiment: str, examples: List[Dict], trend: str, trend_explanation: str = "", period_label: str = "Weekly", subtopics: Dict = None, conversations: List[Dict] = None) -> str:
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
        
        # Extract highlights/lowlights if conversations are provided
        if conversations and examples and len(examples) >= 5:
            try:
                highlights_lowlights = self._extract_highlights_lowlights(examples, topic_name, conversations)
                highlights = highlights_lowlights.get('highlights', [])
                lowlights = highlights_lowlights.get('lowlights', [])
                
                # Format highlights
                if highlights:
                    card += "**Highlights** (Best Experiences) ✅:\n\n"
                    for i, example in enumerate(highlights, 1):
                        preview = example.get('preview', 'No preview available')
                        url = example.get('intercom_url', '#')
                        language = example.get('language', 'English')
                        translation = example.get('translation')
                        
                        if translation and language != 'English':
                            card += f"{i}. \"{translation}\"\n"
                            card += f"   _{language}: \"{preview}\"_\n"
                            card += f"   **[📎 View in Intercom →]({url})**\n\n"
                        else:
                            lang_label = f"_{language}_ " if language and language != 'English' else ""
                            card += f"{i}. {lang_label}\"{preview}\"\n"
                            card += f"   **[📎 View in Intercom →]({url})**\n\n"
                
                # Format lowlights
                if lowlights:
                    card += "**Lowlights** (Areas for Improvement) ⚠️:\n\n"
                    for i, example in enumerate(lowlights, 1):
                        preview = example.get('preview', 'No preview available')
                        url = example.get('intercom_url', '#')
                        language = example.get('language', 'English')
                        translation = example.get('translation')
                        
                        if translation and language != 'English':
                            card += f"{i}. \"{translation}\"\n"
                            card += f"   _{language}: \"{preview}\"_\n"
                            card += f"   **[📎 View in Intercom →]({url})**\n\n"
                        else:
                            lang_label = f"_{language}_ " if language and language != 'English' else ""
                            card += f"{i}. {lang_label}\"{preview}\"\n"
                            card += f"   **[📎 View in Intercom →]({url})**\n\n"
                
            except Exception as e:
                self.logger.warning(f"Error extracting highlights/lowlights for {topic_name}: {e}")
                # Fall back to showing all examples
        
        # If no highlights/lowlights extraction, show all examples
        if not (conversations and examples and len(examples) >= 5):
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
    
    def _extract_highlights_lowlights(self, examples: List[Dict], topic_name: str, conversations: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Extract highlights (best) and lowlights (worst) from examples based on CSAT, resolution time, and sentiment.
        
        Args:
            examples: List of example dicts
            topic_name: Topic name for context
            conversations: Full conversation list for looking up additional data
            
        Returns:
            Dict with 'highlights' and 'lowlights' lists
        """
        if len(examples) < 5:
            # Not enough examples to split meaningfully
            return {'highlights': examples, 'lowlights': []}
        
        # Create conversation lookup with normalized string keys
        conv_lookup = {str(conv.get('id')): conv for conv in conversations}
        
        # Score each example
        scored_examples = []
        skipped_count = 0  # Counter for visibility
        for example in examples:
            # Normalize conversation_id to string before lookup
            conv_id = str(example.get('conversation_id'))
            conv = conv_lookup.get(conv_id)
            
            if not conv:
                # Skip if conversation not found
                skipped_count += 1
                continue
            
            composite_score = 0.0
            
            # CSAT score (if available)
            csat = conv.get('conversation_rating')
            if csat:
                if csat == 5:
                    composite_score += 2.0
                elif csat == 4:
                    composite_score += 1.0
                elif csat == 3:
                    composite_score += 0.0
                elif csat == 2:
                    composite_score += -1.0
                elif csat == 1:
                    composite_score += -2.0
            
            # Resolution time score
            handling_time = conv.get('statistics', {}).get('handling_time')
            if handling_time:
                hours = handling_time / 3600
                if hours < 1:
                    composite_score += 1.0
                elif hours > 6:
                    composite_score += -1.0
            
            # Sentiment score (basic keyword matching)
            preview = example.get('preview', '').lower()
            positive_keywords = ['love', 'great', 'excellent', 'thank', 'appreciate', 'perfect', 'amazing']
            negative_keywords = ['hate', 'terrible', 'awful', 'frustrated', 'angry', 'disappointed', 'cancel']
            
            if any(kw in preview for kw in positive_keywords):
                composite_score += 0.5
            if any(kw in preview for kw in negative_keywords):
                composite_score += -0.5
            
            scored_examples.append((composite_score, example))
        
        # Sort by score (highest to lowest)
        scored_examples.sort(reverse=True, key=lambda x: x[0])
        
        # Log how many examples were skipped for visibility
        if skipped_count > 0:
            self.logger.info(f"Skipped {skipped_count} examples due to missing conversation matches in highlights/lowlights extraction")
        
        # Top 2-3 are highlights, bottom 2-3 are lowlights
        num_highlights = min(3, len(scored_examples) // 2)
        num_lowlights = min(3, len(scored_examples) // 2)
        
        highlights = [ex for score, ex in scored_examples[:num_highlights]]
        lowlights = [ex for score, ex in scored_examples[-num_lowlights:]] if num_lowlights > 0 else []
        
        return {'highlights': highlights, 'lowlights': lowlights}
    
    def _format_pattern_intelligence_section(self, analytical_insights: Dict[str, Any]) -> str:
        """
        Format Pattern Intelligence as separate top-level sections for Correlations and Anomalies.
        
        Args:
            analytical_insights: Dict containing CorrelationAgent and QualityInsightsAgent data
            
        Returns:
            Formatted markdown string with separate top-level sections
        """
        try:
            sections = []
            
            # Extract data from analytical insights
            correlation_data = analytical_insights.get('CorrelationAgent', {}).get('data', {})
            quality_data = analytical_insights.get('QualityInsightsAgent', {}).get('data', {})
            
            # 1. Correlations as top-level section
            correlations = correlation_data.get('correlations', [])
            if correlations:
                sections.append("## Correlations 🔗")
                sections.append("")
                
                # Limit to top 5 correlations
                for corr in correlations[:5]:
                    description = corr.get('description', 'Unknown correlation')
                    strength = corr.get('strength', 'Unknown')
                    insight = corr.get('insight', '')
                    context = corr.get('context', '')
                    
                    sections.append(f"- **{description}** (strength: {strength})")
                    if insight:
                        sections.append(f"  - {insight}")
                    if context:
                        sections.append(f"  - Context: {context}")
                    sections.append("")
                
                sections.append("---")
                sections.append("")
            
            # 2. Anomalies as top-level section
            anomalies = quality_data.get('anomalies', [])
            temporal_clustering = quality_data.get('temporal_clustering', [])
            
            if anomalies or temporal_clustering:
                sections.append("## Anomalies & Temporal Patterns 📊")
                sections.append("")
                
                # Statistical anomalies
                if anomalies:
                    sections.append("### Statistical Anomalies")
                    sections.append("")
                    
                    for anomaly in anomalies:
                        anomaly_type = anomaly.get('type', 'Unknown')
                        topic = anomaly.get('topic', 'Unknown')
                        observation = anomaly.get('observation', '')
                        significance = anomaly.get('significance', '')
                        
                        sections.append(f"- **{topic}**: {anomaly_type}")
                        if observation:
                            sections.append(f"  - {observation}")
                        if significance:
                            sections.append(f"  - Statistical significance: {significance}")
                        sections.append("")
                
                # Temporal patterns
                if temporal_clustering:
                    sections.append("### Temporal Patterns")
                    sections.append("")
                    
                    for cluster in temporal_clustering:
                        topic = cluster.get('topic', 'Unknown')
                        observation = cluster.get('observation', '')
                        clustering_pct = cluster.get('clustering_pct', 0)
                        
                        sections.append(f"- **{topic}**: {observation} ({clustering_pct}% concentration)")
                    sections.append("")
                
                sections.append("---")
                sections.append("")
            
            # If no pattern data at all
            if not correlations and not anomalies and not temporal_clustering:
                return ""  # Return empty string to skip the section entirely
            
            return '\n'.join(sections)
            
        except Exception as e:
            self.logger.warning(f"Error formatting pattern intelligence section: {e}")
            return ""  # Return empty on error to skip the section
    
    def _format_churn_risk_section(self, churn_data: Dict[str, Any]) -> str:
        """
        Format Churn Risk section with high-risk conversations.
        
        Args:
            churn_data: ChurnRiskAgent data
            
        Returns:
            Formatted markdown string
        """
        try:
            sections = []
            sections.append("## Risk & Opportunity Signals ⚠️")
            sections.append("")
            
            high_risk_conversations = churn_data.get('high_risk_conversations', [])
            risk_breakdown = churn_data.get('risk_breakdown', {})
            
            if not high_risk_conversations:
                sections.append("_No churn signals detected this period_")
                sections.append("")
                return '\n'.join(sections)
            
            # Show risk breakdown
            sections.append("### Churn Risk Flagged")
            sections.append("")
            
            high_value_at_risk = risk_breakdown.get('high_value_at_risk', 0)
            if high_value_at_risk > 0:
                sections.append(f"**{high_value_at_risk} high-value customers flagged**")
                sections.append("")
            
            # Group by priority
            immediate = [c for c in high_risk_conversations if c.get('priority') == 'immediate']
            high = [c for c in high_risk_conversations if c.get('priority') == 'high']
            medium = [c for c in high_risk_conversations if c.get('priority') == 'medium']
            
            # Show immediate priority first (limit to top 10 overall)
            all_risk_convs = immediate + high + medium
            for i, conv in enumerate(all_risk_convs[:10], 1):
                conv_id = conv.get('conversation_id', 'Unknown')
                tier = conv.get('tier', 'Unknown')
                signals = ', '.join(conv.get('signals', []))
                csat = conv.get('csat', 'N/A')
                intercom_url = conv.get('intercom_url', '#')
                priority_icon = '🔴' if conv.get('priority') == 'immediate' else '🟠' if conv.get('priority') == 'high' else '🟡'
                
                sections.append(f"{i}. {priority_icon} Conv #{conv_id} - {tier} tier, {signals}, CSAT {csat}")
                sections.append(f"   **[View in Intercom →]({intercom_url})**")
                
                # Include quote if available
                quote = conv.get('quote')
                if quote:
                    sections.append(f"   > \"{quote}\"")
                sections.append("")
            
            # Add LLM analysis if available
            llm_analysis = churn_data.get('llm_analysis')
            if llm_analysis:
                sections.append("**AI Analysis**:")
                sections.append(f"{llm_analysis}")
                sections.append("")
            
            return '\n'.join(sections)
            
        except Exception as e:
            self.logger.warning(f"Error formatting churn risk section: {e}")
            return "## Risk & Opportunity Signals ⚠️\n\n_Churn risk analysis unavailable_\n\n"
    
    def _format_resolution_quality_section(self, quality_data: Dict[str, Any]) -> str:
        """
        Format Resolution Quality Metrics section.
        
        Args:
            quality_data: QualityInsightsAgent data
            
        Returns:
            Formatted markdown string
        """
        try:
            sections = []
            sections.append("## Resolution Quality Metrics 📈")
            sections.append("")
            
            # 1. FCR by Topic
            fcr_by_topic = quality_data.get('fcr_by_topic', {})
            if fcr_by_topic:
                sections.append("### First Contact Resolution by Topic")
                sections.append("")
                
                for topic, fcr_data in fcr_by_topic.items():
                    fcr_rate = fcr_data.get('fcr_rate', 0)
                    total = fcr_data.get('total', 0)
                    observation = fcr_data.get('observation', '')
                    
                    sections.append(f"- **{topic}**: {fcr_rate:.1%} FCR ({total} conversations)")
                    if observation:
                        sections.append(f"  - {observation}")
                sections.append("")
            
            # 2. Reopen Patterns
            reopen_patterns = quality_data.get('reopen_patterns', {})
            if reopen_patterns:
                sections.append("### Reopen Patterns")
                sections.append("")
                
                for topic, reopen_data in reopen_patterns.items():
                    reopen_rate = reopen_data.get('reopen_rate', 0)
                    count = reopen_data.get('reopen_count', 0)
                    
                    if reopen_rate > 0.1:  # Only show topics with >10% reopen rate
                        sections.append(f"- **{topic}**: {reopen_rate:.1%} reopen rate ({count} reopened)")
                sections.append("")
            
            # 3. Multi-Touch Analysis
            multi_touch = quality_data.get('multi_touch_analysis', {})
            if multi_touch:
                sections.append("### Multi-Touch Analysis")
                sections.append("")
                
                for topic, touch_data in multi_touch.items():
                    avg_touches = touch_data.get('avg_touches', 0)
                    if avg_touches > 5:  # Only show topics requiring many interactions
                        sections.append(f"- **{topic}**: {avg_touches:.1f} average interactions")
                sections.append("")
            
            # 4. Resolution Time Distribution
            resolution_dist = quality_data.get('resolution_distribution', {})
            if resolution_dist:
                sections.append("### Resolution Time Distribution")
                sections.append("")
                
                fast = resolution_dist.get('fast_pct', 0)
                medium = resolution_dist.get('medium_pct', 0)
                slow = resolution_dist.get('slow_pct', 0)
                
                sections.append(f"- Fast (<1 hour): {fast:.1%}")
                sections.append(f"- Medium (1-6 hours): {medium:.1%}")
                sections.append(f"- Slow (>6 hours): {slow:.1%}")
                sections.append("")
            
            # 5. Exceptional Conversations
            exceptional = quality_data.get('exceptional_conversations', [])
            if exceptional:
                sections.append("### Exceptional Conversations")
                sections.append("")
                
                for conv in exceptional[:5]:  # Top 5
                    conv_id = conv.get('conversation_id', 'Unknown')
                    reason = conv.get('reason', '')
                    intercom_url = conv.get('intercom_url', '#')
                    recommendation = conv.get('recommendation', '')
                    
                    sections.append(f"- Conv #{conv_id}: {reason}")
                    sections.append(f"  **[View in Intercom →]({intercom_url})**")
                    if recommendation:
                        sections.append(f"  - {recommendation}")
                sections.append("")
            
            # Add LLM insights if available
            llm_insights = quality_data.get('llm_insights')
            if llm_insights:
                sections.append("**Quality Insights**:")
                sections.append(f"{llm_insights}")
                sections.append("")
            
            return '\n'.join(sections)
            
        except Exception as e:
            self.logger.warning(f"Error formatting resolution quality section: {e}")
            return "## Resolution Quality Metrics 📈\n\n_Quality metrics unavailable_\n\n"
    
    def _format_confidence_limitations_section(self, confidence_data: Dict[str, Any]) -> str:
        """
        Format Analysis Confidence & Limitations section.
        
        Args:
            confidence_data: ConfidenceMetaAgent data
            
        Returns:
            Formatted markdown string
        """
        try:
            sections = []
            sections.append("## Analysis Confidence & Limitations 🎯")
            sections.append("")
            
            # 1. Confidence Distribution
            confidence_dist = confidence_data.get('confidence_distribution', {})
            if confidence_dist:
                sections.append("### Confidence Distribution")
                sections.append("")
                
                high_conf = confidence_dist.get('high', [])
                medium_conf = confidence_dist.get('medium', [])
                low_conf = confidence_dist.get('low', [])
                
                if high_conf:
                    sections.append("**High Confidence Insights:**")
                    for item in high_conf:
                        agent = item.get('agent', 'Unknown')
                        reason = item.get('reason', '')
                        sections.append(f"- {agent}: {reason}")
                    sections.append("")
                
                if medium_conf:
                    sections.append("**Medium Confidence Insights:**")
                    for item in medium_conf:
                        agent = item.get('agent', 'Unknown')
                        reason = item.get('reason', '')
                        sections.append(f"- {agent}: {reason}")
                    sections.append("")
                
                if low_conf:
                    sections.append("**Low Confidence Insights:**")
                    for item in low_conf:
                        agent = item.get('agent', 'Unknown')
                        reason = item.get('reason', '')
                        sections.append(f"- {agent}: {reason}")
                    sections.append("")
            
            # 2. Data Quality
            data_quality = confidence_data.get('data_quality', {})
            if data_quality:
                sections.append("### Data Quality")
                sections.append("")
                
                tier_coverage = data_quality.get('tier_coverage', 0)
                csat_coverage = data_quality.get('csat_coverage', 0)
                stats_coverage = data_quality.get('statistics_coverage', 0)
                overall_score = confidence_data.get('overall_data_quality_score', 0)
                
                sections.append(f"- Tier Coverage: {tier_coverage:.1%}")
                sections.append(f"- CSAT Coverage: {csat_coverage:.1%}")
                sections.append(f"- Statistics Coverage: {stats_coverage:.1%}")
                sections.append(f"- **Overall Quality Score: {overall_score:.2f}/10**")
                sections.append("")
                
                impact = data_quality.get('impact', '')
                if impact:
                    sections.append(f"_Impact: {impact}_")
                    sections.append("")
            
            # 3. Current Limitations
            limitations = confidence_data.get('limitations', [])
            if limitations:
                sections.append("### Current Limitations")
                sections.append("")
                
                for limitation in limitations:
                    sections.append(f"- {limitation}")
                sections.append("")
            
            # 4. What Would Improve Confidence
            improvements = confidence_data.get('what_would_improve_confidence', [])
            if improvements:
                sections.append("### What Would Improve Confidence")
                sections.append("")
                
                for improvement in improvements:
                    sections.append(f"- {improvement}")
                sections.append("")
            
            # Add LLM meta-analysis if available
            llm_meta = confidence_data.get('llm_meta_analysis')
            if llm_meta:
                sections.append("**Meta-Analysis**:")
                sections.append(f"{llm_meta}")
                sections.append("")
            
            return '\n'.join(sections)
            
        except Exception as e:
            self.logger.warning(f"Error formatting confidence limitations section: {e}")
            return "## Analysis Confidence & Limitations 🎯\n\n_Confidence analysis unavailable_\n\n"
    
    def _format_cannot_determine_section(self, historical_context: Dict[str, Any], confidence_data: Dict[str, Any]) -> str:
        """
        Format "What We Cannot Determine (Yet)" section.
        
        Args:
            historical_context: Historical context data (weeks_available, etc.)
            confidence_data: Confidence data for additional limitations
            
        Returns:
            Formatted markdown string
        """
        try:
            sections = []
            sections.append("## What We Cannot Determine (Yet) ⏳")
            sections.append("")
            
            weeks_available = historical_context.get('weeks_available', 0)
            
            cannot_determine_items = []
            
            # Baseline trends
            if weeks_available < 4:
                weeks_needed = 4 - weeks_available
                cannot_determine_items.append(
                    f"**Is current volume normal?** (Baseline establishes in {weeks_needed} more week{'s' if weeks_needed != 1 else ''})"
                )
            
            # Seasonality
            if weeks_available < 12:
                weeks_needed = 12 - weeks_available
                cannot_determine_items.append(
                    f"**Seasonality patterns?** (Need {weeks_needed} more weeks for full seasonal analysis)"
                )
            
            # Long-term trends
            if weeks_available < 26:
                cannot_determine_items.append(
                    "**Long-term trends?** (Need 6+ months of data for reliable trend analysis)"
                )
            
            # Add data gaps from confidence analysis
            limitations = confidence_data.get('limitations', [])
            for limitation in limitations:
                if 'cannot determine' in limitation.lower() or 'insufficient' in limitation.lower():
                    cannot_determine_items.append(f"**{limitation}**")
            
            if cannot_determine_items:
                for item in cannot_determine_items:
                    sections.append(f"- {item}")
                sections.append("")
            
            # Add progress indicator
            if weeks_available > 0:
                sections.append(f"**Building baseline**: Week {weeks_available} of 12 needed for seasonality detection")
                sections.append("")
            else:
                sections.append("**Getting started**: This is the first analysis period")
                sections.append("")
            
            return '\n'.join(sections)
            
        except Exception as e:
            self.logger.warning(f"Error formatting cannot determine section: {e}")
            return "## What We Cannot Determine (Yet) ⏳\n\n_Historical context unavailable_\n\n"

