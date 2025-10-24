"""
OutputFormatterAgent: Formats analysis into Hilary's exact card structure.

Purpose:
- Generate output matching Hilary's wishlist format exactly
- Separate VoC (paid) from Fin analysis (free)
- Include detection methods and examples
- Add trend indicators when available
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel

logger = logging.getLogger(__name__)


class OutputFormatterAgent(BaseAgent):
    """Agent specialized in formatting output to match Hilary's format"""
    
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
        """Validate input"""
        required_agents = ['SegmentationAgent', 'TopicDetectionAgent']
        for agent in required_agents:
            if agent not in context.previous_results:
                raise ValueError(f"Missing {agent} results")
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate formatted output"""
        return 'formatted_output' in result
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute output formatting"""
        start_time = datetime.now()
        
        try:
            self.validate_input(context)
            
            self.logger.info("OutputFormatterAgent: Formatting results into Hilary's structure")
            
            # Get results from previous agents
            segmentation = context.previous_results.get('SegmentationAgent', {}).get('data', {})
            topic_detection = context.previous_results.get('TopicDetectionAgent', {}).get('data', {})
            topic_sentiments = context.previous_results.get('TopicSentiments', {})  # Dict by topic
            topic_examples = context.previous_results.get('TopicExamples', {})  # Dict by topic
            fin_performance = context.previous_results.get('FinPerformanceAgent', {}).get('data', {})
            trends = context.previous_results.get('TrendAgent', {}).get('data', {}).get('trends', {})
            
            # Build output
            output_sections = []
            
            # Get period type from metadata
            period_type = context.metadata.get('period_type', 'weekly')
            period_label = context.metadata.get('period_label', 'Weekly')
            
            # Header
            week_id = context.metadata.get('week_id', datetime.now().strftime('%Y-W%W'))
            output_sections.append(f"# Voice of Customer Analysis - Week {week_id}")
            output_sections.append("")
            
            # Section 1: Voice of Customer (Paid Customers)
            output_sections.append("## Customer Topics (Paid Tier - Human Support)")
            output_sections.append("")
            
            # Sort topics by volume
            topic_dist = topic_detection.get('topic_distribution', {})
            sorted_topics = sorted(topic_dist.items(), key=lambda x: x[1]['volume'], reverse=True)
            
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
                
                # Get LLM trend insights from TrendAgent
                trend_agent_data = context.previous_results.get('TrendAgent', {}).get('data', {})
                trend_insights = trend_agent_data.get('trend_insights', {})
                if topic_name in trend_insights:
                    trend_explanation = trend_insights[topic_name]
                
                # Format card
                card = self._format_topic_card(
                    topic_name,
                    topic_stats,
                    sentiment,
                    examples,
                    trend_indicator,
                    trend_explanation,
                    period_label
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
    
    def _format_topic_card(self, topic_name: str, stats: Dict, sentiment: str, examples: List[Dict], trend: str, trend_explanation: str = "", period_label: str = "Weekly") -> str:
        """Format a single topic card"""
        method_label = "Intercom conversation attribute" if stats['detection_method'] == 'attribute' else "Keyword detection"
        
        card = f"""### {topic_name}{trend}
**{stats['volume']} tickets / {stats['percentage']}% of {period_label.lower()} volume**  
**Detection Method**: {method_label}

**Sentiment**: {sentiment}
"""
        
        # Add trend explanation if available
        if trend_explanation:
            card += f"\n**Trend Analysis**: {trend_explanation}\n"
        
        card += "\n**Examples**:\n"
        
        # Add examples with validation
        if examples and len(examples) > 0:
            for i, example in enumerate(examples, 1):
                # Defensive read of example fields
                preview = example.get('preview', 'No preview available') if isinstance(example, dict) else 'Invalid example format'
                url = example.get('intercom_url', '#') if isinstance(example, dict) else '#'
                card += f"{i}. \"{preview}\" - [View conversation]({url})\n"
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

        card = f"""### Free Tier: Fin AI Performance (AI-Only Support)
**{total_free} conversations from Free tier customers**

**Performance Overview**:
- Resolution rate: {resolution_rate:.1%} (customers satisfied without requesting human support)
- Knowledge gaps: {knowledge_gaps} conversations with incorrect/incomplete information
"""

        # What Fin does well
        if top_topics:
            card += "\n**What Fin Does Well (Free Tier)**:\n"
            for topic, stats in top_topics:
                card += f"- {topic}: {stats['resolution_rate']:.1%} resolution rate ({stats['total']} conversations)\n"

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

        card = f"""### Paid Tier: Fin-Resolved Conversations
**{total_paid} paid customers resolved their issues with Fin AI (no human escalation needed)**

**Performance Overview**:
- Resolution rate: {resolution_rate:.1%} (chose not to escalate to human support)
- Knowledge gaps: {knowledge_gaps} conversations with incorrect/incomplete information
"""

        # What Fin does well
        if top_topics:
            card += "\n**What Fin Does Well (Paid Tier)**:\n"
            for topic, stats in top_topics:
                card += f"- {topic}: {stats['resolution_rate']:.1%} resolution rate ({stats['total']} conversations)\n"
            card += "- These paid customers had the option to escalate but chose not to\n"

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

