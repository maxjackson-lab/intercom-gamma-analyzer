"""
NarrativeFormatterAgent: Builds data-rich VOC narratives for Hilary's ops readout.

Key goals:
- Executive storyline grounded in metrics
- Topic stories with quotes + vendor impact
- Embedded BPO snapshot
- Prioritized actions
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent, AgentContext, AgentResult, ConfidenceLevel


class NarrativeFormatterAgent(BaseAgent):
    """Format multi-agent outputs into a narrative weekly digest."""

    def __init__(self):
        super().__init__(name="NarrativeFormatterAgent", model="gpt-4o-mini", temperature=0.0)
        self.logger = logging.getLogger(__name__)

    def validate_input(self, context: AgentContext) -> bool:
        if not context.previous_results:
            raise ValueError("NarrativeFormatterAgent requires previous agent results")
        return True

    def get_task_description(self, context: AgentContext) -> str:
        week_id = context.metadata.get('week_id') or context.metadata.get('period_label') or "current range"
        return f"Compose a narrative Voice of Customer report for {week_id} using aggregated agent outputs."

    def format_context_data(self, context: AgentContext) -> str:
        topics = context.previous_results.get('TopicDetectionAgent', {}).get('data', {}).get('topic_distribution', {})
        top_topics = ", ".join(list(topics.keys())[:5]) or "No topics detected"
        return f"Top topics in scope: {top_topics}"

    def validate_output(self, result: Dict[str, Any]) -> bool:
        formatted = result.get('formatted_output')
        if not formatted:
            raise ValueError("Narrative formatter must return 'formatted_output'")
        return True

    async def execute(self, context: AgentContext) -> AgentResult:
        start_time = datetime.now()
        try:
            self.validate_input(context)
            digest_mode = context.metadata.get('digest_mode', False)

            prev = context.previous_results
            segmentation = prev.get('SegmentationAgent', {}).get('data', {})
            topic_detection = prev.get('TopicDetectionAgent', {}).get('data', {})
            subtopics = prev.get('SubTopicDetectionAgent', {}).get('data', {}).get('subtopics_by_tier1_topic', {})
            topic_sentiments = prev.get('TopicSentiments', {})
            topic_examples = prev.get('TopicExamples', {})
            fin_summary = prev.get('FinPerformanceAgent', {}).get('data', {})
            trend_data = prev.get('TrendAgent', {}).get('data', {})
            bpo_summary = prev.get('BpoPerformanceAgent', {}).get('data', {})
            analytical = prev.get('AnalyticalInsights', {})

            topic_dist = topic_detection.get('topic_distribution', {})
            topics_by_volume = sorted(
                [
                    (topic, stats) if isinstance(stats, dict) else (topic, {'volume': stats, 'percentage': 0})
                    for topic, stats in topic_dist.items()
                ],
                key=lambda item: item[1].get('volume', 0),
                reverse=True
            )

            header = self._build_header(context)
            exec_section = self._build_exec_summary(topics_by_volume, topic_sentiments, bpo_summary)
            metrics_section = self._build_metrics_table(segmentation, topic_dist, fin_summary)
            bpo_section = self._build_bpo_section(bpo_summary)
            topic_sections, topic_summaries = self._build_topic_sections(
                topics_by_volume,
                topic_sentiments,
                topic_examples,
                subtopics,
                trend_data,
                bpo_summary,
                fin_summary,
                analytical,
                digest_mode
            )
            actions_section = self._build_actions(topic_summaries, digest_mode)
            risk_section = self._build_risk_section(analytical, fin_summary, digest_mode)
            signals_section = self._build_cross_agent_section(analytical, fin_summary)

            report_parts = [
                header,
                exec_section,
                metrics_section,
                signals_section,
                bpo_section,
                "## Topic Stories",
                *topic_sections,
                actions_section
            ]

            if risk_section:
                report_parts.append(risk_section)

            if digest_mode:
                report_parts.append("_Digest mode enabled: full historical analyses available via voc-v2 standard run._")

            formatted_output = "\n\n".join(part for part in report_parts if part)

            execution_time = (datetime.now() - start_time).total_seconds()
            return AgentResult(
                agent_name=self.name,
                success=True,
                data={
                    'formatted_output': formatted_output,
                    'topics_included': [t for t, _ in topics_by_volume[:5]],
                    'digest_mode': digest_mode
                },
                confidence=1.0,
                confidence_level=ConfidenceLevel.HIGH,
                execution_time=execution_time,
                token_count=0
            )
        except Exception as err:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"NarrativeFormatterAgent error: {err}", exc_info=True)
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                error_message=str(err),
                execution_time=execution_time
            )

    def _build_header(self, context: AgentContext) -> str:
        start = context.start_date
        end = context.end_date
        if start and end:
            header = f"# Voice of Customer Narrative: {start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}"
        else:
            period_label = context.metadata.get('period_label') or context.metadata.get('week_id', '')
            header = f"# Voice of Customer Narrative - {period_label}"
        return header

    def _build_exec_summary(
        self,
        topics_by_volume: List,
        topic_sentiments: Dict,
        bpo_summary: Dict
    ) -> str:
        if not topics_by_volume:
            return "## Executive Narrative\n\n_No topics detected._"

        lines = ["## Executive Narrative", ""]
        for topic, stats in topics_by_volume[:3]:
            pct = stats.get('percentage', 0.0)
            sentiment = self._get_sentiment_line(topic, topic_sentiments)
            vendor_callout = self._vendor_pressure_line(topic, bpo_summary)
            narrative = f"- {topic}: {pct:.1f}% of weekly volume. {sentiment}"
            if vendor_callout:
                narrative += f" {vendor_callout}"
            lines.append(narrative.strip())

        if len(topics_by_volume) > 3:
            remaining = sum(stats.get('percentage', 0.0) for _, stats in topics_by_volume[3:])
            lines.append(f"- Other topics collectively represent {remaining:.1f}% of weekly contacts.")

        return "\n".join(lines)

    def _build_metrics_table(self, segmentation: Dict, topic_dist: Dict, fin_summary: Dict) -> str:
        total_convs = len(segmentation.get('paid_customer_conversations', [])) + len(segmentation.get('free_fin_only_conversations', []))
        paid = len(segmentation.get('paid_customer_conversations', []))
        free = len(segmentation.get('free_fin_only_conversations', []))
        total_topics = len(topic_dist)
        free_resolution = fin_summary.get('free_tier', {}).get('resolution_rate', 0.0)
        paid_resolution = fin_summary.get('paid_tier', {}).get('resolution_rate', 0.0)

        lines = [
            "## Metrics at a Glance",
            "",
            "| Metric | Value |",
            "| --- | --- |",
            f"| Total Conversations | {total_convs:,} |",
            f"| Paid vs Free | {paid:,} paid / {free:,} free |",
            f"| Topics Identified | {total_topics} |"
        ]

        if free_resolution:
            lines.append(f"| Fin Free-tier Resolution | {free_resolution:.1%} |")
        if paid_resolution:
            lines.append(f"| Fin Paid-tier Resolution | {paid_resolution:.1%} |")

        return "\n".join(lines)

    def _build_bpo_section(self, bpo_summary: Dict) -> str:
        vendors = bpo_summary.get('vendors')
        if not vendors:
            return "## BPO Snapshot\n\n_No vendor workload recorded this week._"

        lines = ["## BPO Snapshot", ""]
        for vendor, stats in vendors.items():
            volume = stats.get('volume', 0)
            top_topics = ", ".join(f"{topic} ({count})" for topic, count in stats.get('top_topics', [])[:3])
            lines.append(f"**{vendor.capitalize()}** — {volume} conversations")
            if top_topics:
                lines.append(f"- Top focus: {top_topics}")
            billing_share = stats.get('billing_share')
            if billing_share:
                lines.append(f"- Billing load: {billing_share:.0%} of their queue")
            note = stats.get('note')
            if note:
                lines.append(f"- Note: {note}")
            lines.append("")

        if bpo_summary.get('concerns'):
            lines.append("**Pressure Points:**")
            for concern in bpo_summary['concerns']:
                lines.append(f"- {concern}")

        return "\n".join(lines)

    def _build_topic_sections(
        self,
        topics_by_volume: List,
        topic_sentiments: Dict,
        topic_examples: Dict,
        subtopics: Dict,
        trend_data: Dict,
        bpo_summary: Dict,
        fin_summary: Dict,
        analytical: Dict,
        digest_mode: bool
    ):
        sections = []
        topic_summaries = []
        max_topics = 3 if digest_mode else 5

        for topic, stats in topics_by_volume[:max_topics]:
            pct = stats.get('percentage', 0.0)
            sentiment_line = self._get_sentiment_line(topic, topic_sentiments)
            quote_lines = self._select_quotes(topic_examples, topic, digest_mode)
            subtopic_line = self._summarize_subtopics(topic, subtopics)
            vendor_line = self._vendor_pressure_line(topic, bpo_summary)
            trend_line = self._trend_line(topic, trend_data)
            fin_line = self._fin_line(topic, fin_summary)
            correlation_line = self._correlation_line(topic, analytical)

            section_lines = [
                f"### {topic} ({pct:.1f}% of weekly volume)",
                sentiment_line
            ]
            if trend_line:
                section_lines.append(trend_line)
            if subtopic_line:
                section_lines.append(subtopic_line)
            if vendor_line:
                section_lines.append(vendor_line)
            if fin_line:
                section_lines.append(fin_line)
            if correlation_line:
                section_lines.append(correlation_line)
            if quote_lines:
                section_lines.append("**Customer Quotes:**")
                section_lines.extend(quote_lines)

            sections.append("\n".join(section_lines))

            topic_summaries.append({
                'name': topic,
                'volume_pct': pct,
                'severity': self._estimate_severity(topic, bpo_summary),
                'actionable_insight': sentiment_line,
                'severity_reasons': [trend_line] if trend_line else [],
                'supporting_evidence': quote_lines[:1] if quote_lines else []
            })

        return sections, topic_summaries

    def _build_actions(self, topic_summaries: List[Dict[str, Any]], digest_mode: bool) -> str:
        recommendations = self._build_weighted_recommendations(topic_summaries)
        limit = 3 if digest_mode else 5
        lines = ["## Prioritized Actions", ""]
        for idx, rec in enumerate(recommendations[:limit], start=1):
            line = f"{idx}. **{rec['topic']}** — {rec['action']} (Impact: {rec['impact']:.2f})"
            lines.append(line)
            if rec.get('rationale'):
                lines.append(f"   {rec['rationale']}")
        if len(lines) == 2:
            lines.append("_No high-impact actions identified_")
        return "\n".join(lines)

    def _build_risk_section(self, analytical: Dict, fin_summary: Dict, digest_mode: bool) -> Optional[str]:
        if digest_mode:
            return None

        churn_data = analytical.get('ChurnRiskAgent', {}).get('data', {}) if analytical else {}
        if not churn_data:
            return None

        high_risk = churn_data.get('high_risk_conversations', [])
        if not high_risk:
            return None

        lines = ["## Risk & Escalation Watchlist", ""]
        lines.append(f"- {len(high_risk)} conversations flagged as churn-risk this week.")
        patterns = churn_data.get('risk_breakdown', {}).get('top_signals')
        if patterns:
            lines.append("- Signals: " + ", ".join(patterns[:5]))
        if fin_summary.get('free_tier', {}).get('knowledge_gap_rate', 0) > 0.3:
            lines.append("- Free-tier Fin knowledge gaps remain high (>30%) and escalate to humans.")
        return "\n".join(lines)

    def _build_cross_agent_section(self, analytical: Dict, fin_summary: Dict) -> str:
        if not analytical and not fin_summary:
            return ""

        lines: List[str] = ["## Cross-Agent Signals", ""]
        content_added = False

        correlation_data = analytical.get('CorrelationAgent', {}).get('data', {}) if analytical else {}
        correlations = correlation_data.get('correlations', []) if correlation_data else []
        if correlations:
            lines.append("**Correlation Highlights:**")
            for corr in correlations[:3]:
                insight = corr.get('insight') or corr.get('description')
                if insight:
                    lines.append(f"- {insight}")
            lines.append("")
            content_added = True

        churn_data = analytical.get('ChurnRiskAgent', {}).get('data', {}) if analytical else {}
        breakdown = churn_data.get('risk_breakdown', {}) if churn_data else {}
        total_signals = breakdown.get('total_risk_signals')
        if total_signals:
            high_value = breakdown.get('high_value_at_risk', 0)
            lines.append(f"**Churn Watch:** {total_signals} signals, {high_value} high-value accounts at risk.")
            content_added = True

        free_gap = fin_summary.get('free_tier', {}).get('knowledge_gap_rate') if fin_summary else None
        if free_gap:
            lines.append(f"**Fin Free-tier Gaps:** Knowledge gap rate at {free_gap:.0%}.")
            content_added = True

        paid_gap = fin_summary.get('paid_tier', {}).get('knowledge_gap_rate') if fin_summary else None
        if paid_gap and paid_gap > 0.05:
            lines.append(f"**Fin Paid-tier Drift:** {paid_gap:.0%} of paid cases need escalation.")
            content_added = True

        return "\n".join(lines).strip() if content_added else ""

    def _get_sentiment_line(self, topic: str, topic_sentiments: Dict) -> str:
        insight = topic_sentiments.get(topic, {}).get('data', {}).get('sentiment_insight')
        if insight:
            return insight
        return f"Customers continue to raise issues related to {topic.lower()}."

    def _vendor_pressure_line(self, topic: str, bpo_summary: Dict) -> Optional[str]:
        vendors = bpo_summary.get('vendors') or {}
        pressures = []
        for vendor, stats in vendors.items():
            topic_counts = dict(stats.get('top_topics', []))
            if topic in topic_counts:
                pressures.append(f"{vendor.capitalize()} is handling {topic_counts[topic]} cases here")
        if pressures:
            return "; ".join(pressures)
        return None

    def _trend_line(self, topic: str, trend_data: Dict) -> Optional[str]:
        insights = trend_data.get('trend_insights') or {}
        return insights.get(topic)

    def _summarize_subtopics(self, topic: str, subtopics: Dict) -> Optional[str]:
        topic_data = subtopics.get(topic, {})
        tier2 = topic_data.get('tier2', {})
        if not tier2:
            return None
        top = sorted(tier2.items(), key=lambda item: item[1].get('volume', 0), reverse=True)[:3]
        summary = ", ".join(f"{name} ({data.get('volume', 0)})" for name, data in top)
        return f"Top subtopics: {summary}"

    def _select_quotes(self, topic_examples: Dict, topic: str, digest_mode: bool) -> List[str]:
        examples = topic_examples.get(topic, {}).get('data', {}).get('examples', [])
        limit = 1 if digest_mode else 2
        quotes = []
        for example in examples[:limit]:
            preview = example.get('preview')
            if not preview:
                continue
            url = example.get('intercom_url')
            quote = f"- \"{preview.strip()}\""
            if url:
                quote += f" — [View in Intercom]({url})"
            quotes.append(quote)
        return quotes

    def _estimate_severity(self, topic: str, bpo_summary: Dict) -> float:
        severity = 1.0
        vendors = bpo_summary.get('vendors') or {}
        for stats in vendors.values():
            topic_counts = dict(stats.get('top_topics', []))
            if topic in topic_counts and topic_counts[topic] >= 50:
                severity += 0.2
        return severity

    def _build_weighted_recommendations(self, topic_summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        recommendations: List[Dict[str, Any]] = []
        for summary in topic_summaries:
            volume_pct = summary.get('volume_pct', 0.0)
            severity = summary.get('severity', 1.0)
            impact = (volume_pct / 100.0) * severity
            action = summary.get('actionable_insight') or f"Address {summary.get('name')}"
            reasons = summary.get('severity_reasons', [])
            evidence = summary.get('supporting_evidence', [])
            rationale_parts = [part for part in reasons + evidence if part]
            rationale = "; ".join(rationale_parts)
            recommendations.append({
                'topic': summary.get('name'),
                'impact': impact,
                'severity': severity,
                'volume_pct': volume_pct,
                'action': action,
                'rationale': rationale
            })
        return sorted(recommendations, key=lambda x: x['impact'], reverse=True)

    def _fin_line(self, topic: str, fin_summary: Dict) -> Optional[str]:
        if not fin_summary:
            return None
        struggling = fin_summary.get('free_tier', {}).get('struggling_topics', [])
        for entry in struggling:
            if isinstance(entry, (list, tuple)) and entry and entry[0] == topic:
                count = entry[1] if len(entry) > 1 else None
                if count:
                    return f"Fin free-tier struggling here ({count} unresolved cases)."
                return "Fin free-tier struggling on this workflow."
        return None

    def _correlation_line(self, topic: str, analytical: Dict) -> Optional[str]:
        if not analytical:
            return None
        correlation_data = analytical.get('CorrelationAgent', {}).get('data', {})
        correlations = correlation_data.get('correlations', [])
        for corr in correlations:
            description = corr.get('description', '')
            insight = corr.get('insight')
            if topic.lower() in description.lower():
                return f"{insight or description}"
        return None

