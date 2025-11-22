"""
BpoPerformanceAgent: Summarizes Horatio/Boldr performance for narrative reports.

Purpose:
- Aggregate vendor workload from SegmentationAgent results
- Highlight top topics each vendor is handling
- Surface escalation patterns and pressure points
"""

import logging
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, Any, List

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel


class BpoPerformanceAgent(BaseAgent):
    """Summarize BPO vendor performance (Horatio, Boldr, etc.)."""

    VENDOR_BUCKETS = {
        'horatio': ['horatio', 'fin_to_horatio'],
        'boldr': ['boldr', 'fin_to_boldr']
    }

    def __init__(self):
        super().__init__(name="BpoPerformanceAgent", model="gpt-4o-mini", temperature=0.0)
        self.logger = logging.getLogger(__name__)

    def validate_input(self, context: AgentContext) -> bool:
        metadata = context.metadata or {}
        if 'agent_distribution' not in metadata or 'topics_by_conversation' not in metadata:
            raise ValueError("BpoPerformanceAgent requires agent_distribution and topics_by_conversation")
        return True

    def get_task_description(self, context: AgentContext) -> str:
        week_id = context.metadata.get('week_id') or "current range"
        return f"Summarize Horatio/Boldr workload for {week_id}"

    def format_context_data(self, context: AgentContext) -> str:
        vendor_keys = ", ".join(context.metadata.get('agent_distribution', {}).keys())
        return f"Available routing buckets: {vendor_keys}"

    def validate_output(self, result: Dict[str, Any]) -> bool:
        if 'vendors' not in result:
            raise ValueError("BpoPerformanceAgent output must include vendor summaries")
        return True

    async def execute(self, context: AgentContext) -> AgentResult:
        start_time = datetime.now()
        try:
            self.validate_input(context)
            metadata = context.metadata or {}
            agent_distribution = metadata.get('agent_distribution', {})
            topics_by_conversation = metadata.get('topics_by_conversation', {})
            topic_distribution = metadata.get('topic_distribution', {})
            fin_performance = metadata.get('fin_performance', {})

            vendors_summary = {}
            total_vendor_volume = 0

            for vendor, buckets in self.VENDOR_BUCKETS.items():
                conversations = self._collect_vendor_conversations(agent_distribution, buckets)
                if not conversations:
                    continue

                stats = self._build_vendor_stats(vendor, conversations, topics_by_conversation, topic_distribution)
                stats['escalations'] = len(agent_distribution.get(f'fin_to_{vendor}', []))
                vendors_summary[vendor] = stats
                total_vendor_volume += stats['volume']

            # Senior/escalated handling
            senior_conversations = agent_distribution.get('fin_to_vendor_to_senior', []) + agent_distribution.get('fin_to_senior_direct', [])
            if senior_conversations:
                vendors_summary['senior_staff'] = self._build_vendor_stats(
                    'senior_staff', senior_conversations, topics_by_conversation, topic_distribution
                )
                vendors_summary['senior_staff']['note'] = "Includes vendor + senior escalations"
                total_vendor_volume += vendors_summary['senior_staff']['volume']

            highlights, concerns = self._derive_storylines(vendors_summary, fin_performance)

            result_data = {
                'vendors': vendors_summary,
                'total_vendor_conversations': total_vendor_volume,
                'highlights': highlights,
                'concerns': concerns
            }

            execution_time = (datetime.now() - start_time).total_seconds()
            confidence = 1.0 if total_vendor_volume >= 200 else 0.7 if total_vendor_volume >= 50 else 0.5
            confidence_level = (ConfidenceLevel.HIGH if confidence >= 0.9
                                else ConfidenceLevel.MEDIUM if confidence >= 0.7
                                else ConfidenceLevel.LOW)

            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=confidence,
                confidence_level=confidence_level,
                limitations=[],
                sources=["SegmentationAgent.agent_distribution", "TopicDetectionAgent.topics_by_conversation"],
                execution_time=execution_time,
                token_count=0
            )
        except Exception as err:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"BpoPerformanceAgent error: {err}")
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                error_message=str(err),
                execution_time=execution_time
            )

    def _collect_vendor_conversations(self, agent_distribution: Dict[str, List[Dict]], buckets: List[str]) -> List[Dict]:
        seen_ids = set()
        conversations: List[Dict] = []
        for bucket in buckets:
            for conv in agent_distribution.get(bucket, []):
                conv_id = str(conv.get('id'))
                if conv_id in seen_ids:
                    continue
                seen_ids.add(conv_id)
                conversations.append(conv)
        return conversations

    def _build_vendor_stats(
        self,
        vendor: str,
        conversations: List[Dict],
        topics_by_conversation: Dict[str, List[str]],
        topic_distribution: Dict[str, Any]
    ) -> Dict[str, Any]:
        topic_counts = Counter()
        billing_count = 0
        examples = []

        for conv in conversations:
            conv_id = str(conv.get('id'))
            conv_topics = topics_by_conversation.get(conv_id, [])
            if not conv_topics and conv.get('custom_attributes'):
                for attr_topic in conv.get('custom_attributes', {}):
                    if attr_topic in topic_distribution:
                        conv_topics.append(attr_topic)
            for topic in conv_topics:
                topic_counts[topic] += 1
                if topic.lower() == 'billing':
                    billing_count += 1

            if len(examples) < 3:
                preview = self._extract_preview(conv)
                if preview:
                    examples.append({
                        'id': conv_id,
                        'preview': preview,
                        'topics': conv_topics
                    })

        volume = len(conversations)
        top_topics = topic_counts.most_common(5)
        billing_share = (billing_count / volume) if volume else 0.0

        return {
            'vendor': vendor,
            'volume': volume,
            'top_topics': top_topics,
            'billing_share': billing_share,
            'examples': examples
        }

    def _derive_storylines(self, vendors_summary: Dict[str, Dict], fin_performance: Dict[str, Any]):
        highlights = []
        concerns = []

        for vendor, stats in vendors_summary.items():
            volume = stats.get('volume', 0)
            billing_share = stats.get('billing_share', 0.0)
            top_topics = stats.get('top_topics', [])
            if not top_topics:
                continue

            top_topic_name = top_topics[0][0]
            highlights.append(
                f"{vendor.capitalize()} handled {volume} conversations; top load: {top_topic_name} ({top_topics[0][1]} cases)"
            )

            if billing_share >= 0.4:
                concerns.append(f"{vendor.capitalize()} is overwhelmed by billing ( {billing_share:.0%} of their queue )")

        # Add Fin knowledge gap context for escalations
        free_tier = fin_performance.get('free_tier', {})
        struggling_topics = free_tier.get('struggling_topics', [])
        if struggling_topics:
            topic_names = ", ".join(topic for topic, _ in struggling_topics[:3])
            concerns.append(f"Fin free-tier struggles ({topic_names}) are spilling into BPO workloads")

        return highlights, concerns

    def _extract_preview(self, conversation: Dict[str, Any]) -> str:
        messages = conversation.get('customer_messages') or []
        if messages:
            preview = messages[0][:180]
            return preview
        full_text = conversation.get('full_text')
        if full_text:
            return full_text[:180]
        return ""

