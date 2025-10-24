"""
FinPerformanceAgent: Dedicated analysis of Fin AI performance.

Purpose:
- Analyze Fin AI resolution rate
- Identify knowledge gaps
- Detect unnecessary escalations
- Performance by topic
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class FinPerformanceAgent(BaseAgent):
    """Agent specialized in Fin AI performance analysis with LLM insights"""
    
    def __init__(self):
        super().__init__(
            name="FinPerformanceAgent",
            model="gpt-4o",
            temperature=0.4
        )
        self.openai_client = OpenAIClient()
    
    def get_agent_specific_instructions(self) -> str:
        """Fin performance agent instructions"""
        return """
FIN PERFORMANCE AGENT SPECIFIC RULES:

1. Analyze Fin AI performance objectively:
   - What Fin is doing well
   - Where Fin has knowledge gaps
   - Unnecessary escalations to humans
   - Performance by topic

2. Focus on metrics, not emotions:
   - Resolution rate (% resolved without human request)
   - Knowledge gap frequency
   - Topic-specific performance differences

3. Identify patterns:
   - Which topics Fin handles well
   - Which topics Fin struggles with
   - Common knowledge gaps

4. Be honest about limitations:
   - Fin is AI - has inherent limitations
   - Some topics naturally require human expertise
"""
    
    def get_task_description(self, context: AgentContext) -> str:
        """Describe Fin analysis task"""
        free_fin_convs = context.metadata.get('free_fin_conversations', [])
        paid_fin_convs = context.metadata.get('paid_fin_conversations', [])

        # Backward compatibility
        if not free_fin_convs and not paid_fin_convs:
            fin_convs = context.metadata.get('fin_conversations', [])
            return f"Analyze Fin AI performance across {len(fin_convs)} AI-only conversations."

        return f"""
Analyze Fin AI performance with tier-based segmentation:
- Free tier (Fin-only): {len(free_fin_convs)} conversations
- Paid tier (Fin-resolved): {len(paid_fin_convs)} conversations

Calculate tier-specific metrics:
1. Resolution rate by tier
2. Knowledge gaps by tier
3. Performance differences between tiers
4. Topic-specific performance
"""
    
    def format_context_data(self, context: AgentContext) -> str:
        """Format Fin conversations"""
        fin_convs = context.metadata.get('fin_conversations', [])
        return f"Fin AI conversations: {len(fin_convs)}"
    
    def validate_input(self, context: AgentContext) -> bool:
        """Validate input"""
        # Support both old format (backward compatibility) and new tier-based format
        has_old_format = 'fin_conversations' in context.metadata
        has_new_format = 'free_fin_conversations' in context.metadata or 'paid_fin_conversations' in context.metadata

        if not has_old_format and not has_new_format:
            raise ValueError("No Fin conversations provided (expected 'fin_conversations' or 'free_fin_conversations'/'paid_fin_conversations')")
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate Fin analysis results"""
        # Support both old format (backward compatibility) and new tier-based format
        has_old_format = 'resolution_rate' in result and 'knowledge_gaps_count' in result
        has_new_format = 'free_tier' in result or 'paid_tier' in result

        return has_old_format or has_new_format
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute Fin performance analysis"""
        start_time = datetime.now()
        
        try:
            self.validate_input(context)

            # Extract conversations - support both old and new formats
            free_fin_conversations = context.metadata.get('free_fin_conversations', [])
            paid_fin_conversations = context.metadata.get('paid_fin_conversations', [])

            # Backward compatibility: if old format is used, treat all as free tier
            if not free_fin_conversations and not paid_fin_conversations:
                legacy_conversations = context.metadata.get('fin_conversations', [])
                free_fin_conversations = legacy_conversations
                self.logger.warning("Using legacy 'fin_conversations' format - consider updating to tier-based format")

            total_free = len(free_fin_conversations)
            total_paid = len(paid_fin_conversations)
            total = total_free + total_paid

            self.logger.info(f"FinPerformanceAgent: Analyzing Fin conversations by tier")
            self.logger.info(f"   Free tier (Fin-only): {total_free} conversations")
            self.logger.info(f"   Paid tier (Fin-resolved): {total_paid} conversations")
            
            # Calculate tier-specific metrics
            if total == 0:
                result_data = {
                    # Maintain consistent schema even with zero volume
                    'total_fin_conversations': 0,
                    'total_free_tier': 0,
                    'total_paid_tier': 0,
                    'free_tier': {},
                    'paid_tier': {},
                    'tier_comparison': None,
                    'note': 'No Fin AI conversations found'
                }
            else:
                # Calculate metrics for each tier
                free_tier_metrics = self._calculate_tier_metrics(free_fin_conversations, 'Free') if total_free > 0 else {}
                paid_tier_metrics = self._calculate_tier_metrics(paid_fin_conversations, 'Paid') if total_paid > 0 else {}

                # Build tier-aware result data
                result_data = {
                    # Overall metrics
                    'total_fin_conversations': total,
                    'total_free_tier': total_free,
                    'total_paid_tier': total_paid,

                    # Free tier metrics
                    'free_tier': free_tier_metrics,

                    # Paid tier metrics
                    'paid_tier': paid_tier_metrics,

                    # Tier comparison insights
                    'tier_comparison': self._compare_tiers(free_tier_metrics, paid_tier_metrics) if total_free > 0 and total_paid > 0 else None
                }
            
            # Add LLM interpretation of Fin performance
            if total > 0:
                self.logger.info("Generating tier-specific Fin performance insights with LLM...")
                llm_insights = await self._generate_tier_insights(result_data)
                result_data['llm_insights'] = llm_insights
            
            self.validate_output(result_data)

            # Calculate confidence based on total sample size
            confidence = 1.0 if total >= 100 else 0.7 if total >= 30 else 0.5
            confidence_level = (ConfidenceLevel.HIGH if total >= 100
                              else ConfidenceLevel.MEDIUM if total >= 30
                              else ConfidenceLevel.LOW)

            execution_time = (datetime.now() - start_time).total_seconds()

            self.logger.info(f"FinPerformanceAgent: Completed in {execution_time:.2f}s")
            if total > 0:
                if total_free > 0:
                    free_res = free_tier_metrics.get('resolution_rate', 0)
                    self.logger.info(f"   Free tier resolution rate: {free_res:.1%}")
                if total_paid > 0:
                    paid_res = paid_tier_metrics.get('resolution_rate', 0)
                    self.logger.info(f"   Paid tier resolution rate: {paid_res:.1%}")
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=confidence,
                confidence_level=confidence_level,
                limitations=[f"Based on {total} Fin conversations"] if total < 100 else [],
                sources=["Fin AI conversations", "Escalation pattern analysis"],
                execution_time=execution_time,
                token_count=0
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"FinPerformanceAgent error: {e}")
            
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                error_message=str(e),
                execution_time=execution_time
            )

    def _calculate_tier_metrics(self, conversations: List[Dict], tier_name: str) -> Dict:
        """
        Calculate Fin performance metrics for a specific tier.

        Args:
            conversations: List of conversations for this tier
            tier_name: 'Free' or 'Paid' for logging

        Returns:
            Dict with resolution_rate, knowledge_gaps_count, performance_by_topic, etc.
        """
        total = len(conversations)
        if total == 0:
            return {}

        # Resolution rate
        escalation_phrases = ['speak to human', 'talk to agent', 'real person', 'human support']
        resolved_by_fin = [
            c for c in conversations
            if not any(phrase in c.get('full_text', '').lower() for phrase in escalation_phrases)
        ]
        resolution_rate = len(resolved_by_fin) / total

        # Knowledge gaps
        knowledge_gap_phrases = ['incorrect', 'wrong', 'not helpful', 'didn\'t answer', 'not what i asked']
        knowledge_gaps = [
            c for c in conversations
            if any(phrase in c.get('full_text', '').lower() for phrase in knowledge_gap_phrases)
        ]

        # Performance by topic
        from collections import defaultdict
        topic_performance = defaultdict(lambda: {'total': 0, 'resolved': 0})

        for conv in conversations:
            topics = conv.get('detected_topics', ['Other'])
            is_resolved = conv in resolved_by_fin

            for topic in topics:
                topic_performance[topic]['total'] += 1
                if is_resolved:
                    topic_performance[topic]['resolved'] += 1

        # Calculate rates
        topic_performance_dict = {}
        for topic, stats in topic_performance.items():
            if stats['total'] >= 3:  # Only include topics with meaningful sample size (lowered for tier-specific)
                topic_performance_dict[topic] = {
                    'total': stats['total'],
                    'resolution_rate': stats['resolved'] / stats['total'] if stats['total'] > 0 else 0
                }

        # Sort topics by performance
        top_performing = sorted(
            topic_performance_dict.items(),
            key=lambda x: x[1]['resolution_rate'],
            reverse=True
        )[:3]

        struggling = sorted(
            topic_performance_dict.items(),
            key=lambda x: x[1]['resolution_rate']
        )[:3]

        return {
            'total_conversations': total,
            'resolution_rate': resolution_rate,
            'resolved_count': len(resolved_by_fin),
            'knowledge_gaps_count': len(knowledge_gaps),
            'knowledge_gap_rate': len(knowledge_gaps) / total if total > 0 else 0,
            'knowledge_gap_examples': [
                {
                    'id': c.get('id'),
                    'preview': c.get('customer_messages', [''])[0][:100] if c.get('customer_messages') else 'No preview available',
                    'intercom_url': self._build_intercom_url(c.get('id'))
                }
                for c in knowledge_gaps[:3]
            ],
            'performance_by_topic': topic_performance_dict,
            'top_performing_topics': top_performing,
            'struggling_topics': struggling
        }

    def _compare_tiers(self, free_metrics: Dict, paid_metrics: Dict) -> Dict:
        """
        Compare Fin performance between Free and Paid tiers.

        Returns:
            Dict with comparison insights (resolution rate delta, knowledge gap delta, etc.)
        """
        if not free_metrics or not paid_metrics:
            return {}

        free_res = free_metrics.get('resolution_rate', 0)
        paid_res = paid_metrics.get('resolution_rate', 0)
        free_gap_rate = free_metrics.get('knowledge_gap_rate', 0)
        paid_gap_rate = paid_metrics.get('knowledge_gap_rate', 0)

        resolution_delta = paid_res - free_res
        gap_delta = paid_gap_rate - free_gap_rate

        # Determine interpretation
        if abs(resolution_delta) < 0.05:
            resolution_interpretation = "Similar performance"
        elif resolution_delta > 0:
            resolution_interpretation = "Paid tier performs better"
        else:
            resolution_interpretation = "Free tier performs better"

        if abs(gap_delta) < 0.05:
            gap_interpretation = "Similar knowledge gap rates"
        elif gap_delta > 0:
            gap_interpretation = "Paid tier has more knowledge gaps"
        else:
            gap_interpretation = "Free tier has more knowledge gaps"

        return {
            'resolution_rate_delta': resolution_delta,
            'resolution_rate_interpretation': resolution_interpretation,
            'knowledge_gap_delta': gap_delta,
            'knowledge_gap_interpretation': gap_interpretation,
            'free_tier_resolution': free_res,
            'paid_tier_resolution': paid_res,
            'free_tier_knowledge_gaps': free_gap_rate,
            'paid_tier_knowledge_gaps': paid_gap_rate
        }

    async def _generate_tier_insights(self, result_data: Dict) -> str:
        """
        Use LLM to generate nuanced insights about Fin's performance across tiers

        Args:
            result_data: Complete tier-based Fin performance data

        Returns:
            Nuanced performance insights
        """
        total_free = result_data.get('total_free_tier', 0)
        total_paid = result_data.get('total_paid_tier', 0)
        free_tier = result_data.get('free_tier', {})
        paid_tier = result_data.get('paid_tier', {})
        tier_comparison = result_data.get('tier_comparison', {})

        free_resolution = free_tier.get('resolution_rate', 0)
        paid_resolution = paid_tier.get('resolution_rate', 0)
        free_gaps = free_tier.get('knowledge_gaps_count', 0)
        paid_gaps = paid_tier.get('knowledge_gaps_count', 0)

        # Format top topics for each tier
        free_top = free_tier.get('top_performing_topics', [])
        paid_top = paid_tier.get('top_performing_topics', [])
        free_struggling = free_tier.get('struggling_topics', [])
        paid_struggling = paid_tier.get('struggling_topics', [])

        prompt = f"""
Analyze Fin AI's performance across customer tiers and provide nuanced, actionable insights.

Free Tier (Fin-only) Metrics:
- Total conversations: {total_free}
- Resolution rate: {free_resolution:.1%}
- Knowledge gaps: {free_gaps} conversations
- Top performing topics: {', '.join([f"{t[0]} ({t[1]['resolution_rate']:.1%})" for t in free_top]) if free_top else 'N/A'}
- Struggling topics: {', '.join([f"{t[0]} ({t[1]['resolution_rate']:.1%})" for t in free_struggling]) if free_struggling else 'N/A'}

Paid Tier (Fin-resolved) Metrics:
- Total conversations: {total_paid}
- Resolution rate: {paid_resolution:.1%}
- Knowledge gaps: {paid_gaps} conversations
- Top performing topics: {', '.join([f"{t[0]} ({t[1]['resolution_rate']:.1%})" for t in paid_top]) if paid_top else 'N/A'}
- Struggling topics: {', '.join([f"{t[0]} ({t[1]['resolution_rate']:.1%})" for t in paid_struggling]) if paid_struggling else 'N/A'}

Tier Comparison:
- Resolution rate delta: {tier_comparison.get('resolution_rate_delta', 0):.1%}
- Interpretation: {tier_comparison.get('resolution_rate_interpretation', 'N/A')}

Instructions:
1. Analyze performance differences between tiers
2. Identify why Paid customers might resolve issues with Fin vs escalate
3. Highlight patterns in what Fin does well across both tiers
4. Suggest improvements based on tier-specific insights
5. Keep it under 200 words, professional executive tone
6. Focus on actionable insights for improving AI performance

Insights:"""

        try:
            insights = await self.openai_client.generate_analysis(prompt)
            return insights.strip()
        except Exception as e:
            self.logger.warning(f"LLM insights generation failed: {e}")
            # Fallback insight
            fallback = f"Free tier: {free_resolution:.1%} resolution ({free_gaps} gaps). Paid tier: {paid_resolution:.1%} resolution ({paid_gaps} gaps)."
            if tier_comparison:
                fallback += f" {tier_comparison.get('resolution_rate_interpretation', '')}"
            return fallback
    
    def _build_intercom_url(self, conversation_id: str) -> str:
        """Build Intercom conversation URL with workspace ID"""
        from src.config.settings import settings
        workspace_id = settings.intercom_workspace_id
        
        if not workspace_id or workspace_id == "your-workspace-id-here":
            return f"https://app.intercom.com/a/apps/[WORKSPACE_ID]/inbox/inbox/{conversation_id}"
        return f"https://app.intercom.com/a/apps/{workspace_id}/inbox/inbox/{conversation_id}"

