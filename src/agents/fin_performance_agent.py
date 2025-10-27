"""
FinPerformanceAgent: Dedicated analysis of Fin AI performance.

Purpose:
- Analyze Fin AI resolution rate
- Identify knowledge gaps
- Detect unnecessary escalations
- Performance by topic
- Performance by sub-topic (Tier 2 and Tier 3)
- Data-rooted quality metrics (ratings, escalation rate)
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
from collections import defaultdict
from pydantic import ValidationError

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.utils.ai_client_helper import get_ai_client
from src.services.fin_escalation_analyzer import FinEscalationAnalyzer, is_fin_resolved, has_knowledge_gap
from src.models.analysis_models import FinAnalysisPayload

logger = logging.getLogger(__name__)


class FinPerformanceAgent(BaseAgent):
    """Agent specialized in Fin AI performance analysis with LLM insights"""
    
    def __init__(self, audit=None):
        super().__init__(
            name="FinPerformanceAgent",
            model="gpt-4o",
            temperature=0.4
        )
        self.logger = logging.getLogger(__name__)
        self.ai_client = get_ai_client()
        # Honor the agent's model choice
        if hasattr(self.ai_client, 'model'):
            self.ai_client.model = self.model
        self.escalation_analyzer = FinEscalationAnalyzer()
        self.audit = audit
    
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
   - Escalation rate (% requesting human support)
   - Average conversation rating per sub-topic
   - Sub-topic performance breakdown (when available)

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
            description = f"Analyze Fin AI performance across {len(fin_convs)} AI-only conversations."
            if 'SubTopicDetectionAgent' in context.previous_results:
                description += "\n5. Sub-topic performance breakdown (Tier 2 + Tier 3)"
            return description

        description = f"""
Analyze Fin AI performance with tier-based segmentation:
- Free tier (Fin-only): {len(free_fin_convs)} conversations
- Paid tier (Fin-resolved): {len(paid_fin_convs)} conversations

Calculate tier-specific metrics:
1. Resolution rate by tier
2. Knowledge gaps by tier
3. Performance differences between tiers
4. Topic-specific performance
"""
        if 'SubTopicDetectionAgent' in context.previous_results:
            description += "\n5. Sub-topic performance breakdown (Tier 2 + Tier 3)"
        return description
    
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
        """
        Validate Fin analysis results using Pydantic model.
        
        Args:
            result: Raw output dictionary to validate
            
        Returns:
            True if validation passes
            
        Raises:
            ValueError: If validation fails with clear error message
        """
        try:
            # Use Pydantic model for validation
            FinAnalysisPayload(**result)
            return True
        except ValidationError as e:
            error_msg = f"Fin analysis output validation failed: {e}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
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

            # Check for sub-topic data (supports both previous_results and metadata pathways)
            subtopics_data = None
            if 'SubTopicDetectionAgent' in context.previous_results:
                subtopics_data = context.previous_results['SubTopicDetectionAgent'].get('data', {}).get('subtopics_by_tier1_topic')
                if subtopics_data:
                    self.logger.info(f"Sub-topic data available (from previous_results): {len(subtopics_data)} Tier 1 topics")
            # Fallback to metadata if not found in previous_results
            if not subtopics_data and 'subtopics_by_tier1_topic' in context.metadata:
                subtopics_data = context.metadata.get('subtopics_by_tier1_topic')
                if subtopics_data:
                    self.logger.info(f"Sub-topic data available (from metadata): {len(subtopics_data)} Tier 1 topics")

            total_free = len(free_fin_conversations)
            total_paid = len(paid_fin_conversations)
            total = total_free + total_paid

            self.logger.info(f"FinPerformanceAgent: Analyzing Fin conversations by tier")
            self.logger.info(f"   Free tier (Fin-only): {total_free} conversations")
            self.logger.info(f"   Paid tier (Fin-resolved): {total_paid} conversations")
            
            if self.audit:
                self.audit.step("FIN Performance Analysis",
                              "Starting FIN performance evaluation",
                              {
                                  'total_conversations': total,
                                  'free_tier': total_free,
                                  'paid_tier': total_paid
                              })
            
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
                # Record resolution definition decision
                if self.audit:
                    self.audit.decision(
                        "What resolution definition should be used for Fin AI?",
                        "Using strict resolution criteria: no admin response + (closed OR ≤2 user responses) + no bad rating",
                        "This ensures we only count true Fin resolutions where customer was satisfied and didn't need human help",
                        {
                            'criteria': [
                                'No admin response (Fin handled alone)',
                                'Either closed OR ≤2 user responses',
                                'No bad rating (rating ≥3 or None)'
                            ]
                        }
                    )
                
                # Calculate metrics for each tier
                free_tier_metrics = self._calculate_tier_metrics(free_fin_conversations, 'Free', subtopics_data) if total_free > 0 else {}
                paid_tier_metrics = self._calculate_tier_metrics(paid_fin_conversations, 'Paid', subtopics_data) if total_paid > 0 else {}

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
                
                # Data quality checks
                if self.audit:
                    # CSAT coverage check
                    free_csat_coverage = (free_tier_metrics.get('rated_count', 0) / total_free * 100) if total_free > 0 else 0
                    paid_csat_coverage = (paid_tier_metrics.get('rated_count', 0) / total_paid * 100) if total_paid > 0 else 0
                    overall_csat_coverage = ((free_tier_metrics.get('rated_count', 0) + paid_tier_metrics.get('rated_count', 0)) / total * 100) if total > 0 else 0
                    
                    csat_status = "good" if overall_csat_coverage >= 30 else "limited" if overall_csat_coverage >= 15 else "poor"
                    
                    self.audit.data_quality_check(
                        "CSAT Coverage",
                        f"{overall_csat_coverage:.1f}% of conversations have CSAT ratings",
                        csat_status
                    )
                    
                    self.audit.step("FIN Performance Analysis",
                                  f"Data quality assessment: CSAT coverage {csat_status}",
                                  {
                                      'overall_csat_coverage_pct': f"{overall_csat_coverage:.1f}%",
                                      'free_tier_csat_coverage_pct': f"{free_csat_coverage:.1f}%",
                                      'paid_tier_csat_coverage_pct': f"{paid_csat_coverage:.1f}%",
                                      'eligible_for_rating': free_tier_metrics.get('rating_eligible_count', 0) + paid_tier_metrics.get('rating_eligible_count', 0),
                                      'actually_rated': free_tier_metrics.get('rated_count', 0) + paid_tier_metrics.get('rated_count', 0)
                                  })
                    
                    # Record aggregate performance patterns
                    free_res = free_tier_metrics.get('resolution_rate', 0)
                    paid_res = paid_tier_metrics.get('resolution_rate', 0)
                    free_gaps = free_tier_metrics.get('knowledge_gap_rate', 0)
                    paid_gaps = paid_tier_metrics.get('knowledge_gap_rate', 0)
                    
                    performance_flags = []
                    if free_res < 0.5:
                        performance_flags.append(f"Free tier below 50% resolution threshold ({free_res:.1%})")
                    if paid_res < 0.5:
                        performance_flags.append(f"Paid tier below 50% resolution threshold ({paid_res:.1%})")
                    if free_gaps > 0.3:
                        performance_flags.append(f"High knowledge gap rate in free tier ({free_gaps:.1%})")
                    if paid_gaps > 0.3:
                        performance_flags.append(f"High knowledge gap rate in paid tier ({paid_gaps:.1%})")
                    
                    if performance_flags:
                        self.audit.step("FIN Performance Analysis",
                                      f"Performance concerns identified: {len(performance_flags)} issues",
                                      {'issues': performance_flags})
            
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
                
                # Record final summary in audit
                if self.audit:
                    self.audit.step("FIN Performance Analysis",
                                  f"Completed FIN analysis in {execution_time:.2f}s",
                                  {
                                      'execution_time_seconds': execution_time,
                                      'free_tier_resolution': f"{free_tier_metrics.get('resolution_rate', 0):.1%}" if total_free > 0 else "N/A",
                                      'paid_tier_resolution': f"{paid_tier_metrics.get('resolution_rate', 0):.1%}" if total_paid > 0 else "N/A",
                                      'total_knowledge_gaps': (free_tier_metrics.get('knowledge_gaps_count', 0) + paid_tier_metrics.get('knowledge_gaps_count', 0)),
                                      'topics_analyzed': len(free_tier_metrics.get('performance_by_topic', {}).keys()) if total_free > 0 else 0
                                  })
            
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

    def _calculate_tier_metrics(self, conversations: List[Dict], tier_name: str, subtopics_data: Dict = None) -> Dict:
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

        # Resolution rate - Using standardized is_fin_resolved() helper
        resolved_by_fin = []
        escalated = []
        
        for c in conversations:
            conv_id = c.get('id')
            
            # Use standardized resolution detection
            fin_resolved = is_fin_resolved(c)
            
            # DEBUG logging to trace Fin resolution logic
            parts = c.get('conversation_parts', {}).get('conversation_parts', [])
            admin_parts = [p for p in parts if p.get('author', {}).get('type') == 'admin']
            user_parts = [p for p in parts if p.get('author', {}).get('type') == 'user']
            
            rating_data = c.get('conversation_rating')
            if isinstance(rating_data, dict):
                rating = rating_data.get('rating')
            else:
                rating = rating_data if isinstance(rating_data, (int, float)) else None
            
            self.logger.debug(
                f"Fin resolution check for {conv_id}: "
                f"admin_response={len(admin_parts) > 0}, "
                f"user_responses={len(user_parts)}, "
                f"closed={c.get('state') == 'closed'}, "
                f"rating={rating}, "
                f"detected_topics={c.get('detected_topics', [])}, "
                f"→ {'RESOLVED' if fin_resolved else 'ESCALATED/FAILED'}"
            )
            
            if fin_resolved:
                resolved_by_fin.append(c)
            else:
                escalated.append(c)
        
        resolution_rate = len(resolved_by_fin) / total if total > 0 else 0
        self.logger.info(f"{tier_name} tier: {len(resolved_by_fin)} resolved ({resolution_rate:.1%}), {len(escalated)} escalated/failed")

        # Knowledge gaps - Using standardized has_knowledge_gap() helper
        knowledge_gaps = []
        
        for c in conversations:
            conv_id = c.get('id')
            
            # Use standardized knowledge gap detection
            if has_knowledge_gap(c):
                knowledge_gaps.append(c)
                
                # DEBUG logging to show reason
                text = c.get('full_text', '').lower()
                rating_data = c.get('conversation_rating')
                if isinstance(rating_data, dict):
                    rating = rating_data.get('rating')
                else:
                    rating = rating_data if isinstance(rating_data, (int, float)) else None
                
                parts = c.get('conversation_parts', {}).get('conversation_parts', [])
                admin_intervened = any(p.get('author', {}).get('type') == 'admin' for p in parts)
                
                self.logger.debug(
                    f"Knowledge gap detected for {conv_id}: "
                    f"admin_intervened={admin_intervened}, rating={rating}"
                )
        
        self.logger.info(f"{tier_name} tier knowledge gaps: {len(knowledge_gaps)} ({len(knowledge_gaps)/total*100:.1f}%)")

        # Performance by topic
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

        # Sub-topic performance
        performance_by_subtopic = None
        if subtopics_data is not None:
            performance_by_subtopic = self._calculate_subtopic_performance(conversations, subtopics_data, resolved_by_fin, knowledge_gaps)

        # CRITICAL: Calculate CSAT for the entire tier
        # Per user: "A CX Score is only calculated for conversations with at least 2 responses from both customer and agent"
        eligible_for_rating = []
        all_ratings = []
        
        for c in conversations:
            parts = c.get('conversation_parts', {}).get('conversation_parts', [])
            user_parts = [p for p in parts if p.get('author', {}).get('type') == 'user']
            # For Fin, check bot parts OR admin parts (Support Sal = Fin per user)
            agent_parts = [p for p in parts if p.get('author', {}).get('type') in ['bot', 'admin']]
            
            # Eligible for rating if ≥2 responses from each side
            if len(user_parts) >= 2 and len(agent_parts) >= 2:
                eligible_for_rating.append(c)
                # Extract rating (handle dict format)
                rating_data = c.get('conversation_rating')
                if isinstance(rating_data, dict):
                    rating = rating_data.get('rating')
                elif isinstance(rating_data, (int, float)):
                    rating = rating_data
                else:
                    rating = None
                
                if rating is not None:
                    all_ratings.append(rating)
        
        overall_avg_rating = sum(all_ratings) / len(all_ratings) if all_ratings else None
        overall_rated_count = len(all_ratings)
        eligible_count = len(eligible_for_rating)
        rating_response_rate = (overall_rated_count / eligible_count * 100) if eligible_count > 0 else 0
        
        self.logger.info(
            f"{tier_name} tier CSAT: {overall_avg_rating:.2f}/5.0 from {overall_rated_count} ratings "
            f"({rating_response_rate:.1f}% of {eligible_count} eligible conversations)" 
            if overall_avg_rating else 
            f"{tier_name} tier CSAT: No ratings ({eligible_count} eligible, {overall_rated_count} rated)"
        )

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
            'struggling_topics': struggling,
            'performance_by_subtopic': performance_by_subtopic,
            # CSAT metrics (updated with eligible count)
            'avg_rating': overall_avg_rating,
            'rated_count': overall_rated_count,
            'rating_eligible_count': eligible_count,
            'rating_response_rate': rating_response_rate
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
        # Handle None values explicitly - use {} as fallback
        free_tier = result_data.get('free_tier') or {}
        paid_tier = result_data.get('paid_tier') or {}
        tier_comparison = result_data.get('tier_comparison') or {}

        free_resolution = free_tier.get('resolution_rate', 0)
        paid_resolution = paid_tier.get('resolution_rate', 0)
        free_gaps = free_tier.get('knowledge_gaps_count', 0)
        paid_gaps = paid_tier.get('knowledge_gaps_count', 0)

        # Format top topics for each tier
        free_top = free_tier.get('top_performing_topics', [])
        paid_top = paid_tier.get('top_performing_topics', [])
        free_struggling = free_tier.get('struggling_topics', [])
        paid_struggling = paid_tier.get('struggling_topics', [])

        # Format sub-topic performance if available
        free_subtopics = free_tier.get('performance_by_subtopic', {})
        paid_subtopics = paid_tier.get('performance_by_subtopic', {})

        # Helper to format sub-topics
        def format_subtopics(subtopic_data, tier_name):
            if not subtopic_data:
                return f"{tier_name} sub-topics: N/A"
            lines = [f"{tier_name} sub-topics:"]
            for tier1, subs in subtopic_data.items():
                tier2_top = sorted(subs['tier2'].items(), key=lambda x: x[1]['resolution_rate'], reverse=True)[:2]
                tier3_top = sorted(subs['tier3'].items(), key=lambda x: x[1]['resolution_rate'], reverse=True)[:2]
                if tier2_top:
                    tier2_formatted = ', '.join([f"{k} ({v['resolution_rate']:.1%})" for k, v in tier2_top])
                    lines.append(f"  Tier 2 ({tier1}): {tier2_formatted}")
                if tier3_top:
                    tier3_formatted = ', '.join([f"{k} ({v['resolution_rate']:.1%})" for k, v in tier3_top])
                    lines.append(f"  Tier 3 ({tier1}): {tier3_formatted}")
            return '\n'.join(lines)

        subtopic_info = ""
        if free_subtopics or paid_subtopics:
            subtopic_info = f"\n{format_subtopics(free_subtopics, 'Free Tier')}\n{format_subtopics(paid_subtopics, 'Paid Tier')}"

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

{subtopic_info}

Instructions:
1. Analyze performance differences between tiers
2. Identify why Paid customers might resolve issues with Fin vs escalate
3. Highlight patterns in what Fin does well across both tiers
4. Suggest improvements based on tier-specific insights
5. Keep it under 200 words, professional executive tone
6. Focus on actionable insights for improving AI performance
7. Highlight sub-topic patterns if available (which specific sub-topics Fin excels at vs struggles with)

Insights:"""

        try:
            insights = await self.ai_client.generate_analysis(prompt)
            return insights.strip()
        except Exception as e:
            self.logger.warning(f"LLM insights generation failed: {e}")
            # Fallback insight
            fallback = f"Free tier: {free_resolution:.1%} resolution ({free_gaps} gaps). Paid tier: {paid_resolution:.1%} resolution ({paid_gaps} gaps)."
            if tier_comparison:
                fallback += f" {tier_comparison.get('resolution_rate_interpretation', '')}"
            return fallback
    
    def _calculate_subtopic_performance(self, conversations: List[Dict], subtopics_data: Dict, resolved_by_fin: List[Dict], knowledge_gaps: List[Dict]) -> Dict:
        subtopic_metrics = {}
        for tier1_topic, subtopics in subtopics_data.items():
            subtopic_metrics[tier1_topic] = {'tier2': {}, 'tier3': {}}
            # Get conversations for this topic
            convs_for_topic = [c for c in conversations if tier1_topic in c.get('detected_topics', [])]
            self.logger.debug(f"Analyzing {len(convs_for_topic)} conversations for Tier 1 topic: {tier1_topic}")
            # Tier 2 sub-topics
            for subtopic_name, subtopic_data in subtopics['tier2'].items():
                matched_convs = [c for c in convs_for_topic if self._match_conversation_to_subtopic(c, subtopic_name, 'tier2', subtopic_data)]
                if matched_convs:
                    metrics = self._calculate_single_subtopic_metrics(matched_convs, tier1_topic, subtopic_name, 'tier2')
                    subtopic_metrics[tier1_topic]['tier2'][subtopic_name] = metrics
            # Tier 3 sub-topics
            for subtopic_name, subtopic_data in subtopics['tier3'].items():
                matched_convs = [c for c in convs_for_topic if self._match_conversation_to_subtopic(c, subtopic_name, 'tier3', subtopic_data)]
                if matched_convs:
                    metrics = self._calculate_single_subtopic_metrics(matched_convs, tier1_topic, subtopic_name, 'tier3')
                    subtopic_metrics[tier1_topic]['tier3'][subtopic_name] = metrics
        return subtopic_metrics

    def _calculate_single_subtopic_metrics(self, conversations: List[Dict], tier1_topic: str, subtopic_name: str, tier_level: str) -> Dict:
        """Calculate metrics for a single sub-topic using UPDATED logic."""
        total = len(conversations)
        if total == 0:
            return {
                'total': 0,
                'resolution_rate': 0,
                'knowledge_gap_rate': 0,
                'escalation_rate': 0,
                'avg_rating': None,
                'rated_count': 0,
                'resolved_count': 0,
                'knowledge_gap_count': 0,
                'escalation_count': 0
            }
        
        # Use same logic as main tier metrics (updated logic)
        resolved_convs = []
        gap_convs = []
        escalation_convs = []
        ratings = []
        
        for c in conversations:
            # Use standardized resolution and knowledge gap detection
            if is_fin_resolved(c):
                resolved_convs.append(c)
            else:
                escalation_convs.append(c)
            
            if has_knowledge_gap(c):
                gap_convs.append(c)
            
            # Collect ratings
            rating_data = c.get('conversation_rating')
            if isinstance(rating_data, dict):
                rating = rating_data.get('rating')
            else:
                rating = rating_data if isinstance(rating_data, (int, float)) else None
            
            if rating is not None:
                ratings.append(rating)
        
        resolution_rate = len(resolved_convs) / total if total > 0 else 0
        knowledge_gap_rate = len(gap_convs) / total if total > 0 else 0
        escalation_rate = len(escalation_convs) / total if total > 0 else 0
        avg_rating = sum(ratings) / len(ratings) if ratings else None
        rated_count = len(ratings)
        
        return {
            'total': total,
            'resolution_rate': resolution_rate,
            'knowledge_gap_rate': knowledge_gap_rate,
            'escalation_rate': escalation_rate,
            'avg_rating': avg_rating,
            'rated_count': rated_count,
            'resolved_count': len(resolved_convs),
            'knowledge_gap_count': len(gap_convs),
            'escalation_count': len(escalation_convs)
        }

    def _detect_escalation_request(self, conv: Dict) -> bool:
        """Detect escalation request using centralized FinEscalationAnalyzer."""
        return self.escalation_analyzer.detect_escalation_request(conv)

    def _match_conversation_to_subtopic(self, conv: Dict, subtopic_name: str, tier_level: str, subtopic_data: Dict) -> bool:
        if tier_level == 'tier2':
            # Check tags
            tags = conv.get('tags', {}).get('tags', [])
            if any(tag.get('name', tag) == subtopic_name for tag in tags):
                return True
            # Check custom_attributes
            custom_attrs = conv.get('custom_attributes', {})
            if any(str(value).lower() == subtopic_name.lower() for value in custom_attrs.values()):
                return True
            # Check conversation_topics - normalize to handle dicts with 'name'
            topics = conv.get('conversation_topics', [])
            topic_names = set()
            for t in topics:
                if isinstance(t, dict):
                    topic_names.add(t.get('name', '').lower())
                else:
                    topic_names.add(str(t).lower())
            if subtopic_name.lower() in topic_names:
                return True
            return False
        elif tier_level == 'tier3':
            keywords = subtopic_data.get('keywords', [])
            text = conv.get('full_text', '').lower()
            # Lowercase keywords for case-insensitive matching
            return any(kw.lower() in text for kw in keywords)
        return False

    def _build_intercom_url(self, conversation_id: str) -> str:
        """Build Intercom conversation URL with workspace ID"""
        from src.config.settings import settings
        workspace_id = settings.intercom_workspace_id
        
        if not workspace_id or workspace_id == "your-workspace-id-here":
            return f"https://app.intercom.com/a/apps/[WORKSPACE_ID]/inbox/inbox/{conversation_id}"
        return f"https://app.intercom.com/a/apps/{workspace_id}/inbox/inbox/{conversation_id}"

