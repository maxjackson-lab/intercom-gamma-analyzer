import logging
import random
from collections import defaultdict
from typing import Dict, Any, List, Optional, Tuple

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel


class BpoPerformanceAgent(BaseAgent):
    """
    Summarizes Horatio/Boldr workload distribution and pressure points.

    Consumes segmentation + topic outputs to highlight vendor-specific load,
    workload imbalances, and topics where a single vendor is carrying the majority
    of human volume.
    """

    def __init__(self):
        super().__init__(
            name="BpoPerformanceAgent",
            model="gpt-4o-mini",
            temperature=0.0
        )
        self.logger = logging.getLogger(__name__)

    def get_agent_specific_instructions(self) -> str:
        return """
You are a workload analyst focused on BPO partners.
Quantify how Horatio and Boldr workloads are distributed across topics,
identify pressure points, and highlight imbalances executives should see.
"""

    def get_task_description(self, context: AgentContext) -> str:
        assignments = (context.metadata or {}).get('agent_assignments', {})
        return f"Evaluate BPO workload across {len(assignments)} paid-tier conversations."

    def format_context_data(self, context: AgentContext) -> str:
        metadata = context.metadata or {}
        assignments = metadata.get('agent_assignments', {})
        summary = metadata.get('segmentation_summary', {})
        paid_human = summary.get('paid_human_count', 0)
        return (
            f"Assignments analyzed: {len(assignments)}\n"
            f"Paid human conversations: {paid_human}"
        )

    def validate_input(self, context: AgentContext) -> bool:
        metadata = context.metadata or {}
        self.logger.info(f"BPO Input Validation: {len(metadata.get('agent_assignments', {}))} assignments, {len(metadata.get('topics_by_conversation', {}))} topic maps")
        if not metadata.get('agent_assignments'):
            raise ValueError("agent_assignments metadata missing for BPO analysis")
        if not metadata.get('topics_by_conversation'):
            raise ValueError("topics_by_conversation metadata missing for BPO analysis")
        return True

    def validate_output(self, result: Dict[str, Any]) -> bool:
        required_fields = ['vendor_overview', 'topic_vendor_highlights']
        for field in required_fields:
            if field not in result:
                raise ValueError(f"BPO output missing '{field}'")
        return True

    async def execute(self, context: AgentContext) -> AgentResult:
        try:
            self.validate_input(context)
        except ValueError as exc:
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={'error': str(exc)},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                limitations=[str(exc)],
                execution_time=0.0
            )

        metadata = context.metadata or {}
        assignments = metadata.get('agent_assignments', {})
        topics_by_conversation = metadata.get('topics_by_conversation', {})
        topic_distribution = metadata.get('topic_distribution', {})
        segmentation_summary = metadata.get('segmentation_summary', {})

        vendor_totals = defaultdict(int)
        vendor_topic_totals = defaultdict(lambda: defaultdict(int))
        topic_vendor_counts = defaultdict(lambda: defaultdict(int))

        for conv_id, assignment in assignments.items():
            vendor_bucket = self._map_vendor_bucket(assignment)
            if not vendor_bucket:
                continue

            conversations_topics = topics_by_conversation.get(conv_id, [])
            normalized_topics = self._normalize_topic_list(conversations_topics)

            vendor_totals[vendor_bucket] += 1
            for topic_name in normalized_topics:
                topic_vendor_counts[topic_name][vendor_bucket] += 1
                vendor_topic_totals[vendor_bucket][topic_name] += 1

        paid_human_total = sum(
            vendor_totals[v] for v in ('horatio', 'boldr', 'senior')
        )
        if paid_human_total == 0:
            paid_human_total = segmentation_summary.get('paid_human_count', 0)

        vendor_overview = self._build_vendor_overview(
            vendor_totals,
            vendor_topic_totals,
            paid_human_total
        )

        # Build id_to_conv lookup
        convs = context.conversations or []
        id_to_conv = {c['id']: c for c in convs}
        
        # Add samples + date range per vendor
        for vendor, data in vendor_overview.items():
            vendor_conv_ids = [
                conv_id for conv_id, assignment in assignments.items()
                if self._map_vendor_bucket(assignment) == vendor
            ]
            if vendor_conv_ids:
                sample_ids = random.sample(vendor_conv_ids, min(3, len(vendor_conv_ids)))
                samples = []
                vendor_dates = []
                for conv_id in sample_ids:
                    conv = id_to_conv.get(conv_id)
                    if conv:
                        url = BaseAgent.build_conversation_url(conv_id)
                        snippet = BaseAgent.extract_conversation_snippet(conv)
                        created_at = conv.get('created_at', 'Unknown')
                        vendor_dates.append(created_at)
                        samples.append({
                            'id': conv_id,
                            'created_at': created_at,
                            'url': url,
                            'snippet': snippet
                        })
                data['sample_conversations'] = samples
                if vendor_dates:
                    # Normalize all dates to ISO strings for consistent comparison
                    try:
                        normalized_dates = []
                        for d in vendor_dates:
                            if isinstance(d, (int, float)):
                                from datetime import datetime
                                normalized_dates.append(datetime.fromtimestamp(d).isoformat())
                            elif hasattr(d, 'isoformat'):
                                normalized_dates.append(d.isoformat())
                            elif isinstance(d, str):
                                # Assume already ISO or string rep, try to keep as is if valid
                                # If it's "Unknown", we skip
                                if d != 'Unknown':
                                    normalized_dates.append(d)
                        
                        if normalized_dates:
                            min_date = min(normalized_dates)
                            max_date = max(normalized_dates)
                            
                            data['date_range'] = {
                                'min_created_at': min_date,
                                'max_created_at': max_date
                            }
                    except Exception as e:
                        self.logger.warning(f"Failed to compute date range for {vendor}: {e}")

        topic_highlights, pressure_points = self._build_topic_highlights(
            topic_vendor_counts,
            topic_distribution
        )

        summary_text = self._build_snapshot_summary(vendor_overview, paid_human_total)

        result_data = {
            'vendor_overview': vendor_overview,
            'topic_vendor_highlights': topic_highlights,
            'bpo_snapshot_summary': summary_text,
            'pressure_points': pressure_points,
            'risk_watchlist': pressure_points[:5]
        }

        try:
            self.validate_output(result_data)
        except ValueError as exc:
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={'error': str(exc)},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                limitations=[str(exc)],
                execution_time=0.0
            )

        confidence = 0.9 if paid_human_total >= 200 else 0.7
        return AgentResult(
            agent_name=self.name,
            success=True,
            data=result_data,
            confidence=confidence,
            confidence_level=ConfidenceLevel.HIGH if confidence >= 0.8 else ConfidenceLevel.MEDIUM,
            limitations=[],
            sources=['SegmentationAgent', 'TopicDetectionAgent'],
            execution_time=0.0
        )

    def _map_vendor_bucket(self, assignment: Dict[str, Any]) -> Optional[str]:
        segment = assignment.get('segment')
        if segment != 'paid':
            return None
        agent_type = assignment.get('agent_type', '')
        vendor = assignment.get('vendor')

        if vendor in {'horatio', 'boldr', 'senior'}:
            return vendor
        if agent_type in {'horatio', 'fin_to_horatio'}:
            return 'horatio'
        if agent_type in {'boldr', 'fin_to_boldr'}:
            return 'boldr'
        if agent_type in {'fin_to_vendor_to_senior', 'escalated', 'fin_to_senior_direct'}:
            return vendor if vendor in {'horatio', 'boldr'} else 'senior'
        return None

    def _normalize_topic_list(self, topics: Any) -> List[str]:
        normalized: List[str] = []
        if isinstance(topics, list):
            for entry in topics:
                if isinstance(entry, dict):
                    topic_name = entry.get('topic')
                    if topic_name:
                        normalized.append(topic_name)
                elif isinstance(entry, str):
                    normalized.append(entry)
        return normalized

    def _build_vendor_overview(
        self,
        vendor_totals: Dict[str, int],
        vendor_topic_totals: Dict[str, Dict[str, int]],
        paid_human_total: int
    ) -> Dict[str, Dict[str, Any]]:
        overview: Dict[str, Dict[str, Any]] = {}
        for vendor, total in vendor_totals.items():
            if vendor not in {'horatio', 'boldr', 'senior'} or total == 0:
                continue
            share = (total / paid_human_total) if paid_human_total else 0.0
            top_topics = sorted(
                vendor_topic_totals[vendor].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            overview[vendor] = {
                'total_conversations': total,
                'share_of_paid_workload': share,
                'top_topics': top_topics,
                'pressure_level': self._derive_pressure_level(total, share),
                'notes': self._build_vendor_note(vendor, total, share)
            }
        return overview

    def _build_topic_highlights(
        self,
        topic_vendor_counts: Dict[str, Dict[str, int]],
        topic_distribution: Dict[str, Dict[str, Any]]
    ) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
        highlights: Dict[str, Dict[str, Any]] = {}
        pressure_points: List[str] = []
        for topic, vendor_counts in topic_vendor_counts.items():
            total = sum(vendor_counts.values())
            if total == 0:
                continue
            sorted_vendors = sorted(
                vendor_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )
            leader, leader_count = sorted_vendors[0]
            share = leader_count / total
            inline_callout = self._format_topic_callout(sorted_vendors, total)
            highlights[topic] = {
                'leading_vendor': leader,
                'leading_share': share,
                'inline_callout': inline_callout,
                'human_volume': total
            }
            topic_volume = topic_distribution.get(topic, {}).get('volume', total)
            if total >= 80 and share >= 0.65:
                pressure_points.append(
                    f"{topic}: {self._label_vendor(leader)} carrying {leader_count}/{total} "
                    f"({share:.0%}) human escalations"
                )
        return highlights, pressure_points

    def _build_snapshot_summary(self, overview: Dict[str, Dict[str, Any]], total: int) -> str:
        if total == 0 or not overview:
            return "No paid human workload detected for Horatio or Boldr this week."
        parts = []
        for vendor_key in ['horatio', 'boldr']:
            vendor = overview.get(vendor_key)
            if not vendor:
                continue
            share_pct = vendor['share_of_paid_workload'] * 100
            parts.append(
                f"{self._label_vendor(vendor_key)} handling {vendor['total_conversations']:,} "
                f"cases ({share_pct:.0f}% of human volume)"
            )
        senior = overview.get('senior')
        if senior:
            parts.append(
                f"Senior staff managing {senior['total_conversations']:,} urgent escalations"
            )
        return "; ".join(parts)

    def _derive_pressure_level(self, total: int, share: float) -> str:
        if share >= 0.6 or total >= 800:
            return 'high'
        if share >= 0.45 or total >= 500:
            return 'medium'
        return 'stable'

    def _build_vendor_note(self, vendor: str, total: int, share: float) -> str:
        label = self._label_vendor(vendor)
        share_pct = share * 100
        if share_pct >= 60:
            return f"{label} is absorbing {share_pct:.0f}% of human workload – monitor burnout risk."
        if share_pct <= 30:
            return f"{label} volume light at {share_pct:.0f}% – opportunity to rebalance."
        return f"{label} workload steady at {share_pct:.0f}%."

    def _label_vendor(self, vendor: str) -> str:
        mapping = {
            'horatio': 'Horatio',
            'boldr': 'Boldr',
            'senior': 'Senior staff'
        }
        return mapping.get(vendor, vendor.title() if vendor else 'Vendor')

    def _format_topic_callout(
        self,
        sorted_vendors: List[Tuple[str, int]],
        total: int
    ) -> str:
        parts = []
        for vendor, count in sorted_vendors[:2]:
            label = self._label_vendor(vendor)
            parts.append(f"{label} {count:,} ({(count/total):.0%})")
        return "; ".join(parts)

