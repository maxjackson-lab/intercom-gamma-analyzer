"""
CorrelationAgent - Detects statistical relationships within current week's data

This agent finds correlations between tier, topic, CSAT, reopens, escalations, 
and resolution time without requiring historical data. Uses LLM to provide rich 
insights and interpretations of statistical patterns.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import numpy as np
from scipy import stats as scipy_stats

from src.agents.base_agent import BaseAgent, AgentResult, ConfidenceLevel, AgentContext
from src.utils.conversation_utils import extract_customer_messages
from src.utils.time_utils import format_duration


logger = logging.getLogger(__name__)


class CorrelationAgent(BaseAgent):
    """Agent that detects statistical correlations in conversation data"""

    def __init__(self, ai_client=None):
        super().__init__(
            name="CorrelationAgent",
            model="gpt-4o",
            temperature=0.3
        )
        # Get AI client if not provided
        if ai_client is None:
            from src.utils.ai_client_helper import get_ai_client
            self.ai_client = get_ai_client()
        else:
            self.ai_client = ai_client
        
        # Determine which models to use based on AI client type (STRATEGIC REASONING → use Sonnet!)
        from src.services.claude_client import ClaudeClient
        if isinstance(self.ai_client, ClaudeClient):
            # Claude: Use Sonnet 4.5 for strategic correlation analysis
            self.quick_model = "claude-haiku-4-5-20251001"
            self.intensive_model = "claude-sonnet-4-5-20250929"
            self.client_type = "claude"
        else:
            # OpenAI: Use GPT-4o for correlation analysis
            self.quick_model = "gpt-4o-mini"
            self.intensive_model = "gpt-4o"
            self.client_type = "openai"

    def get_agent_specific_instructions(self) -> str:
        """Return instructions for observational correlation analysis"""
        return """
You are analyzing statistical correlations in customer support data. Your role is to:

1. **Report correlations observationally** - Describe patterns without prescribing fixes
2. **Use correlation strength** - Report r-values and statistical significance
3. **Provide context for interpretation** - Explain what the correlation suggests
4. **Avoid causal claims** - Correlation ≠ causation, use "associated with" not "causes"
5. **Highlight actionable patterns** - Focus on correlations that suggest opportunities

Format your analysis as insights that help teams understand their support patterns.
"""

    def get_task_description(self, context: AgentContext) -> str:
        """Describe the correlation analysis task"""
        total_convs = len(context.conversations) if context.conversations else 0
        return f"Find statistical correlations within current week's data across tier, topic, CSAT, reopens, and resolution patterns ({total_convs} conversations)"

    def format_context_data(self, context: AgentContext) -> Dict[str, Any]:
        """Format summary of available data for analysis"""
        conversations = context.conversations or []
        
        # Calculate coverage
        tier_coverage = sum(1 for c in conversations if c.get('tier') and c.get('tier') != 'unknown') / len(conversations) if conversations else 0
        csat_coverage = sum(1 for c in conversations if c.get('conversation_rating')) / len(conversations) if conversations else 0
        
        # Get topic count
        topic_data = context.previous_results.get('TopicDetectionAgent', {}).get('data', {})
        topics_detected = len(topic_data.get('topic_distribution', {}))
        
        return {
            'total_conversations': len(conversations),
            'tier_coverage': round(tier_coverage, 2),
            'csat_coverage': round(csat_coverage, 2),
            'topics_detected': topics_detected
        }

    def validate_input(self, context: AgentContext) -> bool:
        """Ensure required data is available"""
        if not context.conversations:
            raise ValueError("No conversations provided for correlation analysis")
        
        if 'SegmentationAgent' not in context.previous_results:
            raise ValueError("SegmentationAgent results required for tier analysis")
        
        if 'TopicDetectionAgent' not in context.previous_results:
            raise ValueError("TopicDetectionAgent results required for topic correlation")
        
        return True

    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Ensure output contains required fields"""
        if 'correlations' not in result:
            raise ValueError("Output missing 'correlations' field")
        
        if not isinstance(result['correlations'], list):
            raise ValueError("'correlations' must be a list")
        
        return True

    async def execute(self, context: AgentContext) -> AgentResult:
        """Main execution method for correlation analysis"""
        start_time = datetime.now()
        
        try:
            # Validate input
            try:
                self.validate_input(context)
            except ValueError as e:
                return AgentResult(
                    agent_name=self.name,
                    success=False,
                    data={'error': str(e)},
                    confidence=0.0,
                    confidence_level=ConfidenceLevel.LOW,
                    limitations=[str(e)],
                    sources=[],
                    execution_time=0.0
                )
            
            # Extract data from context
            conversations = context.conversations
            segmentation_data = context.previous_results.get('SegmentationAgent', {}).get('data', {})
            topic_data = context.previous_results.get('TopicDetectionAgent', {}).get('data', {})
            topic_dist = topic_data.get('topic_distribution', {})
            topics_by_conv = context.metadata.get('topics_by_conversation', {}) if context.metadata else {}
            
            logger.info(f"Analyzing correlations across {len(conversations)} conversations")
            
            # Calculate all correlation types
            correlations = []
            
            # 1. Tier × Topic correlations
            tier_topic_corrs = self._calculate_tier_topic_correlation(conversations, topic_dist, topics_by_conv)
            correlations.extend(tier_topic_corrs)
            
            # 2. CSAT × Reopens correlation
            csat_reopen_corr = self._calculate_csat_reopen_correlation(conversations)
            if csat_reopen_corr:
                correlations.append(csat_reopen_corr)
            
            # 3. Complexity × Escalation correlation
            complexity_esc_corr = self._calculate_complexity_escalation_correlation(conversations)
            if complexity_esc_corr:
                correlations.append(complexity_esc_corr)
            
            # 4. Agent × Resolution Time correlation
            agent_res_corr = self._calculate_agent_resolution_correlation(conversations, segmentation_data)
            if agent_res_corr:
                correlations.append(agent_res_corr)
            
            # Calculate data coverage for confidence
            tier_coverage = sum(1 for c in conversations if c.get('tier') and c.get('tier') != 'unknown') / len(conversations)
            csat_coverage = sum(1 for c in conversations if c.get('conversation_rating')) / len(conversations)
            stats_coverage = sum(1 for c in conversations if c.get('statistics', {}).get('count_reopens') is not None or c.get('statistics', {}).get('handling_time')) / len(conversations)
            
            # Use LLM to enrich insights if available
            if self.ai_client and correlations:
                correlations = await self._enrich_correlations_with_llm(correlations, context)
            
            # Build result
            result_data = {
                'correlations': correlations,
                'total_correlations_found': len(correlations),
                'data_coverage': {
                    'tier_coverage': round(tier_coverage, 2),
                    'csat_coverage': round(csat_coverage, 2),
                    'statistics_coverage': round(stats_coverage, 2)
                }
            }
            
            # Validate output
            try:
                self.validate_output(result_data)
            except ValueError as e:
                logger.error(f"Output validation failed: {e}")
                return AgentResult(
                    agent_name=self.name,
                    success=False,
                    data={'error': str(e)},
                    confidence=0.0,
                    confidence_level=ConfidenceLevel.LOW,
                    limitations=[str(e)],
                    sources=[],
                    execution_time=0.0
                )
            
            # Calculate overall confidence
            overall_confidence = tier_coverage * 0.4 + csat_coverage * 0.3 + stats_coverage * 0.3
            confidence_level = self._calculate_confidence_level(overall_confidence)
            
            # Build limitations
            limitations = []
            if tier_coverage < 0.7:
                limitations.append(f"Tier data only available for {int(tier_coverage*100)}% of conversations")
            if csat_coverage < 0.3:
                limitations.append(f"CSAT data only available for {int(csat_coverage*100)}% of conversations")
            if len(correlations) == 0:
                limitations.append("No significant correlations detected in current data")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=round(overall_confidence, 2),
                confidence_level=confidence_level,
                limitations=limitations,
                sources=['statistical_analysis', 'conversation_metadata'],
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"CorrelationAgent execution failed: {e}", exc_info=True)
            execution_time = (datetime.now() - start_time).total_seconds()
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={'error': str(e)},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                limitations=[f"Execution failed: {str(e)}"],
                sources=[],
                execution_time=execution_time
            )

    def _calculate_tier_topic_correlation(
        self, 
        conversations: List[Dict], 
        topic_dist: Dict[str, int],
        topics_by_conv: Dict[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """Calculate tier × topic correlations (over-representation analysis)"""
        try:
            # Pre-index conversations by ID for O(1) lookup (optimization from O(N²) to O(N))
            conv_by_id = {conv.get('id'): conv for conv in conversations if conv.get('id')}
            
            # Calculate overall tier distribution
            tier_counts = {}
            for conv in conversations:
                tier = conv.get('tier', 'unknown')
                tier_counts[tier] = tier_counts.get(tier, 0) + 1
            
            total_convs = len(conversations)
            overall_tier_dist = {tier: count / total_convs for tier, count in tier_counts.items()}
            
            correlations = []
            
            # For each topic, calculate tier distribution
            for topic_name in topic_dist.keys():
                # Find conversations for this topic using pre-indexed dict (O(N) instead of O(N²))
                topic_convs = []
                for conv_id, topics in topics_by_conv.items():
                    if topic_name in topics and conv_id in conv_by_id:
                        topic_convs.append(conv_by_id[conv_id])
                
                if len(topic_convs) < 5:  # Skip topics with too few conversations
                    continue
                
                # Calculate tier distribution within topic
                topic_tier_counts = {}
                for conv in topic_convs:
                    tier = conv.get('tier', 'unknown')
                    topic_tier_counts[tier] = topic_tier_counts.get(tier, 0) + 1
                
                # Find over-represented tiers
                for tier, count in topic_tier_counts.items():
                    topic_tier_pct = count / len(topic_convs)
                    overall_tier_pct = overall_tier_dist.get(tier, 0)
                    
                    if overall_tier_pct > 0:
                        strength = topic_tier_pct / overall_tier_pct
                        
                        # Only include significant over-representation (>2x expected)
                        if strength > 2.0:
                            correlations.append({
                                'type': 'tier_topic',
                                'description': f"{tier.title()} tier ↔ {topic_name}",
                                'strength': round(strength, 2),
                                'insight': f"{tier.title()} customers represent {int(topic_tier_pct*100)}% of {topic_name} issues (vs {int(overall_tier_pct*100)}% overall)",
                                'context': f"{tier.title()} tier is {int(strength)}x over-represented in {topic_name}",
                                'confidence': min(0.9, 0.5 + (len(topic_convs) / 20)),
                                'sample_size': len(topic_convs)
                            })
            
            return correlations
            
        except Exception as e:
            logger.warning(f"Tier-topic correlation calculation failed: {e}")
            return []

    def _calculate_csat_reopen_correlation(self, conversations: List[Dict]) -> Optional[Dict[str, Any]]:
        """Calculate CSAT × Reopens correlation"""
        try:
            # Filter conversations with CSAT ratings
            rated_convs = [c for c in conversations if c.get('conversation_rating') is not None]
            
            if len(rated_convs) < 10:  # Need minimum sample size
                logger.debug("Insufficient CSAT data for correlation (<10 rated conversations)")
                return None
            
            # Group by reopened vs first-touch
            reopened = [c for c in rated_convs if c.get('statistics', {}).get('count_reopens', 0) > 0]
            first_touch = [c for c in rated_convs if c.get('statistics', {}).get('count_reopens', 0) == 0]
            
            if not reopened or not first_touch:
                return None
            
            # Calculate % with bad CSAT (rating < 3)
            reopened_bad_csat_pct = sum(1 for c in reopened if c.get('conversation_rating', 5) < 3) / len(reopened)
            first_touch_bad_csat_pct = sum(1 for c in first_touch if c.get('conversation_rating', 5) < 3) / len(first_touch)
            
            # Calculate Pearson correlation
            reopen_values = [1 if c.get('statistics', {}).get('count_reopens', 0) > 0 else 0 for c in rated_convs]
            csat_values = [c.get('conversation_rating', 3) for c in rated_convs]
            
            r_value, confidence = self._safe_pearson_correlation(reopen_values, csat_values)
            
            return {
                'type': 'csat_reopens',
                'description': f"Bad CSAT ↔ Multiple Reopens (r={abs(r_value):.2f})",
                'strength': abs(r_value),
                'insight': f"{int(reopened_bad_csat_pct*100)}% of reopened conversations have bad CSAT vs {int(first_touch_bad_csat_pct*100)}% of first-touch",
                'context': "Reopens strongly associated with customer dissatisfaction",
                'confidence': confidence,
                'sample_size': len(rated_convs)
            }
            
        except Exception as e:
            logger.warning(f"CSAT-reopen correlation calculation failed: {e}")
            return None

    def _calculate_complexity_escalation_correlation(self, conversations: List[Dict]) -> Optional[Dict[str, Any]]:
        """Calculate Complexity (message count) × Escalation correlation"""
        try:
            # Group by escalated vs Fin-only
            escalated = [c for c in conversations if c.get('admin_assignee_id')]
            fin_only = [c for c in conversations if not c.get('admin_assignee_id')]
            
            if len(escalated) < 5 or len(fin_only) < 5:
                logger.debug("Insufficient data for complexity-escalation correlation")
                return None
            
            # Calculate average message counts
            def get_message_count(conv):
                # Try statistics field first (safe access)
                count = conv.get('statistics', {}).get('count_conversation_parts')
                if count:
                    return count
                # Fallback to conversation_parts length (safe access)
                parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
                if parts and isinstance(parts, list):
                    return len(parts)
                return 1
            
            escalated_messages = [get_message_count(c) for c in escalated]
            fin_only_messages = [get_message_count(c) for c in fin_only]
            
            escalated_avg = np.mean(escalated_messages)
            fin_only_avg = np.mean(fin_only_messages)
            escalated_median = np.median(escalated_messages)
            fin_only_median = np.median(fin_only_messages)
            
            # Calculate strength as ratio
            strength = escalated_median / fin_only_median if fin_only_median > 0 else 1.0
            
            return {
                'type': 'complexity_escalation',
                'description': f"Message Count ↔ Escalation (ratio={strength:.1f}x)",
                'strength': round(strength, 2),
                'insight': f"Escalated conversations average {escalated_avg:.1f} messages vs {fin_only_avg:.1f} for Fin-only",
                'context': "Higher complexity leads to human escalation",
                'confidence': 0.85,
                'sample_size': len(escalated) + len(fin_only)
            }
            
        except Exception as e:
            logger.warning(f"Complexity-escalation correlation calculation failed: {e}")
            return None

    def _calculate_agent_resolution_correlation(
        self, 
        conversations: List[Dict],
        segmentation_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Calculate Agent Type × Resolution Time correlation"""
        try:
            # Group conversations by agent type using segmentation data if available
            agent_groups = {}
            
            # Try to get agent assignment from segmentation data first
            conversation_assignments = segmentation_data.get('conversation_assignments', {})
            
            for conv in conversations:
                conv_id = conv.get('id')
                
                # Determine agent type from segmentation data or conversation fields
                agent_type = None
                
                # First, check segmentation data for assignment info
                if conv_id and conv_id in conversation_assignments:
                    assignment = conversation_assignments[conv_id]
                    if assignment.get('assigned_to'):
                        agent_type = assignment.get('agent_type', 'Human Agent')
                    elif assignment.get('fin_only'):
                        agent_type = 'Fin AI'
                
                # Fallback to conversation fields
                if not agent_type:
                    if conv.get('admin_assignee_id'):
                        agent_type = 'Human Agent'
                    else:
                        agent_type = 'Fin AI'
                
                # Get resolution time
                handling_time = conv.get('statistics', {}).get('handling_time')
                if not handling_time:
                    time_to_reply = conv.get('statistics', {}).get('time_to_admin_reply')
                    if time_to_reply:
                        handling_time = time_to_reply
                
                if handling_time and agent_type:
                    if agent_type not in agent_groups:
                        agent_groups[agent_type] = []
                    agent_groups[agent_type].append(handling_time)
            
            # Filter agents with sufficient data (at least 5 samples)
            agent_groups = {agent: times for agent, times in agent_groups.items() if len(times) >= 5}
            
            if len(agent_groups) < 2:
                logger.debug("Insufficient agent data for resolution correlation (need at least 2 groups with 5+ samples each)")
                return None
            
            # Calculate median resolution times
            agent_medians = {}
            for agent, times in agent_groups.items():
                median_seconds = np.median(times)
                median_hours = median_seconds / 3600
                agent_medians[agent] = median_hours
            
            # Build insight string
            insight_parts = [f"{agent}: {hours:.1f}h median" for agent, hours in sorted(agent_medians.items())]
            insight = ", ".join(insight_parts)
            
            # Calculate strength as coefficient of variation (std/mean)
            median_values = list(agent_medians.values())
            strength = np.std(median_values) / np.mean(median_values) if median_values and np.mean(median_values) > 0 else 0
            
            return {
                'type': 'agent_resolution_time',
                'description': "Agent Type ↔ Resolution Time",
                'strength': round(strength, 2),
                'insight': insight,
                'context': "Different agent types show varied resolution patterns",
                'confidence': 0.78,
                'sample_size': sum(len(times) for times in agent_groups.values())
            }
            
        except Exception as e:
            logger.warning(f"Agent-resolution correlation calculation failed: {e}")
            return None

    def _safe_pearson_correlation(self, x_values: List[float], y_values: List[float]) -> Tuple[float, float]:
        """Safely calculate Pearson correlation coefficient"""
        try:
            if len(x_values) != len(y_values) or len(x_values) < 3:
                return 0.0, 0.0
            
            # Remove any None values
            pairs = [(x, y) for x, y in zip(x_values, y_values) if x is not None and y is not None]
            if len(pairs) < 3:
                return 0.0, 0.0
            
            x_clean, y_clean = zip(*pairs)
            
            r_value, p_value = scipy_stats.pearsonr(x_clean, y_clean)
            
            # Calculate confidence based on sample size and p-value
            sample_size = len(x_clean)
            confidence = min(0.95, (sample_size / 50) * (1 - p_value))
            
            return r_value, confidence
            
        except Exception as e:
            logger.warning(f"Pearson correlation calculation failed: {e}")
            return 0.0, 0.0

    async def _enrich_correlations_with_llm(
        self, 
        correlations: List[Dict[str, Any]], 
        context: AgentContext
    ) -> List[Dict[str, Any]]:
        """Use LLM to provide richer insights and interpretations"""
        try:
            if not correlations:
                return correlations
            
            # Build prompt with correlation data
            prompt = f"""Analyze these statistical correlations found in customer support data and provide enriched insights:

{self._format_correlations_for_llm(correlations)}

For each correlation, provide:
1. A brief interpretation of what this pattern suggests
2. Potential business implications
3. Observational recommendations (avoid prescriptive "you should" language)

Keep insights concise and actionable. Focus on patterns that teams can investigate further.
"""
            
            messages = [
                {"role": "system", "content": self.get_agent_specific_instructions()},
                {"role": "user", "content": prompt}
            ]
            
            # Use intensive model for strategic correlation analysis
            if self.client_type == "claude":
                response = await self.ai_client.client.messages.create(
                    model=self.intensive_model,
                    max_tokens=4000,
                    temperature=self.temperature,
                    system=self.get_agent_specific_instructions(),
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                llm_insights = response.content[0].text
            else:
                response = await self.ai_client.client.chat.completions.create(
                    model=self.intensive_model,
                    messages=messages,
                    temperature=self.temperature
                )
                llm_insights = response.choices[0].message.content
            
            # Add LLM insights to correlations
            for corr in correlations:
                corr['llm_interpretation'] = llm_insights
            
            return correlations
            
        except Exception as e:
            logger.warning(f"LLM enrichment failed: {e}")
            return correlations  # Return original correlations if LLM fails

    def _format_correlations_for_llm(self, correlations: List[Dict[str, Any]]) -> str:
        """Format correlations for LLM prompt"""
        formatted = []
        for i, corr in enumerate(correlations, 1):
            formatted.append(f"{i}. {corr['description']}")
            formatted.append(f"   Strength: {corr['strength']}")
            formatted.append(f"   Insight: {corr['insight']}")
            formatted.append(f"   Context: {corr['context']}")
            formatted.append(f"   Sample Size: {corr['sample_size']}")
            formatted.append("")
        return "\n".join(formatted)

    def _calculate_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Convert numeric confidence to ConfidenceLevel enum"""
        if confidence >= 0.8:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.6:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

