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
                # Get sentiment and examples for this topic
                sentiment = topic_sentiments.get(topic_name, {}).get('data', {}).get('sentiment_insight', 'No sentiment analysis available')
                examples = topic_examples.get(topic_name, {}).get('data', {}).get('examples', [])
                
                # Get trend if available
                trend = trends.get(topic_name, {})
                trend_indicator = ""
                if trend and 'direction' in trend:
                    trend_indicator = f" {trend['direction']} {trend.get('alert', '')}"
                
                # Format card
                card = self._format_topic_card(
                    topic_name,
                    topic_stats,
                    sentiment,
                    examples,
                    trend_indicator
                )
                output_sections.append(card)
            
            # Section 2: Fin AI Performance
            if fin_performance:
                output_sections.append("\n## Fin AI Performance (Free Tier - AI-Only Support)")
                output_sections.append("")
                
                fin_card = self._format_fin_card(fin_performance)
                output_sections.append(fin_card)
            
            # Combine all sections
            formatted_output = '\n'.join(output_sections)
            
            result_data = {
                'formatted_output': formatted_output,
                'total_topics': len(sorted_topics),
                'week_id': week_id,
                'has_trend_data': len(trends) > 0
            }
            
            self.validate_output(result_data)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"OutputFormatterAgent: Completed in {execution_time:.2f}s")
            self.logger.info(f"   Formatted {len(sorted_topics)} topic cards")
            
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
    
    def _format_topic_card(self, topic_name: str, stats: Dict, sentiment: str, examples: List[Dict], trend: str) -> str:
        """Format a single topic card"""
        method_label = "Intercom conversation attribute" if stats['detection_method'] == 'attribute' else "Keyword detection"
        
        card = f"""### {topic_name}{trend}
**{stats['volume']} tickets / {stats['percentage']}% of weekly volume**  
**Detection Method**: {method_label}

**Sentiment**: {sentiment}

**Examples**:
"""
        
        # Add examples
        for i, example in enumerate(examples, 1):
            card += f"{i}. \"{example['preview']}\" - [View conversation]({example['intercom_url']})\n"
        
        if not examples:
            card += "_No examples extracted_\n"
        
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
                card += f"- \"{ex['preview']}...\"\n"
        
        # Struggling topics
        struggling = fin_data.get('struggling_topics', [])
        if struggling:
            card += "\n**Topics where Fin struggles**:\n"
            for topic, stats in struggling:
                card += f"- {topic}: {stats['resolution_rate']:.1%} resolution rate ({stats['total']} conversations)\n"
        
        card += "\n---\n"
        
        return card

