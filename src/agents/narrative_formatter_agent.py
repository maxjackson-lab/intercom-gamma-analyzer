import json
import logging
from typing import Dict, Any, List, Optional

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.utils.ai_client_helper import get_ai_client


class NarrativeFormatterAgent(BaseAgent):
    """
    LLM-powered formatter that stitches all agent outputs into a cohesive narrative.

    Focuses on executive storyline, cross-agent signals, vendor workload, and
    prioritized actions instead of card-by-card restatement.
    """

    def __init__(self):
        super().__init__(
            name="NarrativeFormatterAgent",
            model="gpt-4o",
            temperature=0.35
        )
        self.logger = logging.getLogger(__name__)
        self.ai_client = get_ai_client()

    def get_agent_specific_instructions(self) -> str:
        return """
You are Hilary's weekly storyteller. Synthesize multi-agent outputs into a single,
connected narrative. Link topics together, reference vendor workload inline,
and explain what needs to happen next. Avoid bullet dumps of raw data.
"""

    def get_task_description(self, context: AgentContext) -> str:
        return "Craft the VoC Narrative V2 report (executive storyline, topic stories, actions)."

    def validate_input(self, context: AgentContext) -> bool:
        required_keys = [
            'SegmentationAgent',
            'TopicDetectionAgent',
            'TopicSentiments',
            'FinPerformanceAgent'
        ]
        previous = context.previous_results or {}
        missing = [key for key in required_keys if key not in previous]
        if missing:
            raise ValueError(f"Missing agent outputs: {', '.join(missing)}")
        return True

    def validate_output(self, result: Dict[str, Any]) -> bool:
        if 'formatted_output' not in result:
            raise ValueError("NarrativeFormatterAgent output missing formatted_output")
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

        payload = self._assemble_payload(context)
        prompt = self._build_prompt(context, payload)

        try:
            narrative = await self.ai_client.generate_analysis(prompt)
            formatted_output = narrative.strip()
        except Exception as exc:
            self.logger.warning(f"Narrative LLM call failed, falling back: {exc}")
            formatted_output = self._fallback_narrative(payload)

        result_data = {
            'formatted_output': formatted_output,
            'structured_data': payload
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

        confidence = 0.85 if "Executive Narrative" in formatted_output else 0.7
        return AgentResult(
            agent_name=self.name,
            success=True,
            data=result_data,
            confidence=confidence,
            confidence_level=ConfidenceLevel.HIGH if confidence >= 0.8 else ConfidenceLevel.MEDIUM,
            limitations=[],
            sources=["multi-agent synthesis"],
            execution_time=0.0
        )

    def _assemble_payload(self, context: AgentContext) -> Dict[str, Any]:
        previous = context.previous_results or {}
        segmentation = (previous.get('SegmentationAgent') or {}).get('data', {})
        segmentation_summary = segmentation.get('segmentation_summary', {}) if isinstance(segmentation.get('segmentation_summary'), dict) else {}
        topic_detection = (previous.get('TopicDetectionAgent') or {}).get('data', {})
        topic_dist = topic_detection.get('topic_distribution', {})
        topic_sentiments = previous.get('TopicSentiments', {})
        fin_performance = (previous.get('FinPerformanceAgent') or {}).get('data', {})
        bpo_entry = previous.get('BpoPerformanceAgent') or {}
        bpo_performance = bpo_entry.get('data', {}) if isinstance(bpo_entry, dict) else {}
        topic_examples = previous.get('TopicExamples') or {}
        if not isinstance(topic_examples, dict):
            topic_examples = {}
        analytical = previous.get('AnalyticalInsights', {})
        synthesis_summary = previous.get('SynthesisEngine') or {}
        if not isinstance(synthesis_summary, dict):
            synthesis_summary = {'data': synthesis_summary}
        digest_mode = bool((context.metadata or {}).get('digest_mode'))

        top_topics = self._build_topic_profiles(
            topic_dist,
            topic_sentiments,
            fin_performance,
            bpo_performance,
            analytical,
            topic_examples,
            digest_mode
        )
        total_conversations = len(context.conversations or [])
        fin_free_snapshot = fin_performance.get('free_tier', {}) if isinstance(fin_performance.get('free_tier'), dict) else {}
        fin_paid_snapshot = fin_performance.get('paid_tier', {}) if isinstance(fin_performance.get('paid_tier'), dict) else {}

        metrics_overview = {
            'total_conversations': total_conversations,
            'paid_human_conversations': segmentation_summary.get('paid_human_count'),
            'free_fin_only_conversations': segmentation_summary.get('free_fin_only_count'),
            'topic_count': len(top_topics),
            'fin_free_resolution_rate': fin_free_snapshot.get('resolution_rate'),
            'fin_paid_resolution_rate': fin_paid_snapshot.get('resolution_rate')
        }

        cross_agent_signals = self._extract_cross_agent_signals(analytical)

        return {
            'timeframe': {
                'start': context.start_date.isoformat() if context.start_date else None,
                'end': context.end_date.isoformat() if context.end_date else None,
                'week_id': context.metadata.get('week_id')
            },
            'volume_summary': {
                'total_conversations': total_conversations,
                'paid_human': segmentation_summary.get('paid_human_count'),
                'free_fin_only': segmentation_summary.get('free_fin_only_count'),
                'topic_count': len(top_topics)
            },
            'fin_overview': {
                'free_tier': {
                    'resolution_rate': fin_free_snapshot.get('resolution_rate'),
                    'total_conversations': fin_free_snapshot.get('total_conversations')
                },
                'paid_tier': {
                    'resolution_rate': fin_paid_snapshot.get('resolution_rate'),
                    'total_conversations': fin_paid_snapshot.get('total_conversations')
                }
            },
            'topics': top_topics,
            'bpo_snapshot': bpo_performance,
            'cross_agent_signals': cross_agent_signals,
            'risk_watchlist': bpo_performance.get('risk_watchlist', []),
            'prioritized_actions_hint': [t.get('action_hint') for t in top_topics[:4]],
            'metrics_overview': metrics_overview,
            'synthesis_summary': synthesis_summary,
            'settings': {'digest_mode': digest_mode}
        }

    def _build_topic_profiles(
        self,
        topic_dist: Dict[str, Dict[str, Any]],
        sentiments: Dict[str, Any],
        fin_performance: Dict[str, Any],
        bpo_performance: Dict[str, Any],
        analytical: Dict[str, Any],
        topic_examples: Dict[str, Any],
        digest_mode: bool = False
    ) -> List[Dict[str, Any]]:
        profiles: List[Dict[str, Any]] = []
        bpo_highlights = bpo_performance.get('topic_vendor_highlights', {})
        churn_highlights = self._extract_churn_highlights(analytical)
        correlation_highlights = self._extract_correlation_highlights(analytical)
        max_topics = 3 if digest_mode else 8

        sorted_topics = sorted(
            topic_dist.items(),
            key=lambda x: x[1].get('volume', 0),
            reverse=True
        )
        for topic_name, stats in sorted_topics[:max_topics]:
            sentiment_payload = sentiments.get(topic_name, {}).get('data', {})
            quotes = self._extract_topic_quotes(topic_examples, topic_name, digest_mode)
            profile = {
                'name': topic_name,
                'volume': stats.get('volume'),
                'percentage': stats.get('percentage'),
                'sentiment': sentiment_payload.get('sentiment_insight'),
                'examples': self._extract_example_snippet(sentiments, topic_name),
                'bpo_callout': bpo_highlights.get(topic_name, {}),
                'fin_performance': self._extract_fin_topic_metrics(topic_name, fin_performance),
                'signals': [],
                'quotes': quotes
            }
            if churn_highlights.get(topic_name):
                profile['signals'].append(churn_highlights[topic_name])
            if correlation_highlights.get(topic_name):
                profile['signals'].append(correlation_highlights[topic_name])
            profile['action_hint'] = sentiment_payload.get('sentiment_insight')
            profiles.append(profile)
        return profiles

    def _extract_example_snippet(self, sentiments: Dict[str, Any], topic: str) -> Optional[str]:
        examples = sentiments.get(topic, {}).get('data', {}).get('sample_quotes')
        if examples:
            return examples[0]
        return None

    def _extract_topic_quotes(
        self,
        topic_examples: Dict[str, Any],
        topic: str,
        digest_mode: bool
    ) -> List[Dict[str, Any]]:
        """
        Returns curated quote metadata (text + link) for a topic.
        Limits to 1 quote in digest mode, else 2.
        """
        examples_payload = topic_examples.get(topic, {})
        data = examples_payload.get('data', {}) if isinstance(examples_payload, dict) else {}
        raw_examples = data.get('examples') or []
        if not isinstance(raw_examples, list):
            return []

        max_quotes = 1 if digest_mode else 2
        quotes: List[Dict[str, Any]] = []
        for example in raw_examples[:max_quotes]:
            preview = example.get('translation') or example.get('preview')
            link = example.get('intercom_url')
            if not preview or not link:
                continue
            quotes.append({
                'text': preview.strip(),
                'original_preview': example.get('preview'),
                'intercom_url': link,
                'conversation_id': example.get('conversation_id'),
                'language': example.get('language'),
                'translation': example.get('translation'),
                'needs_translation': example.get('needs_translation'),
                'created_at': example.get('created_at')
            })
        return quotes

    def _extract_fin_topic_metrics(self, topic: str, fin_performance: Dict[str, Any]) -> Dict[str, Any]:
        summary: Dict[str, Any] = {}
        for tier_key, label in (('free_tier', 'Free Tier'), ('paid_tier', 'Paid Tier')):
            tier_metrics = fin_performance.get(tier_key, {})
            perf = tier_metrics.get('performance_by_topic', {})
            if isinstance(perf, dict) and topic in perf:
                summary[label] = {
                    'resolution_rate': perf[topic].get('resolution_rate'),
                    'total': perf[topic].get('total')
                }
        return summary

    def _extract_cross_agent_signals(self, analytical: Dict[str, Any]) -> Dict[str, List[str]]:
        signals = {'correlations': [], 'churn': []}
        if not analytical:
            return signals
        correlation_data = analytical.get('CorrelationAgent', {}).get('data', {})
        for corr in correlation_data.get('correlations', [])[:3]:
            signals['correlations'].append(
                f"{corr.get('description')}: {corr.get('insight')}"
            )
        churn_data = analytical.get('ChurnRiskAgent', {}).get('data', {})
        high_risk = churn_data.get('risk_breakdown', {}).get('total_risk_signals')
        if high_risk:
            signals['churn'].append(
                f"{high_risk} explicit churn signals detected (see watchlist)."
            )
        return signals

    def _extract_churn_highlights(self, analytical: Dict[str, Any]) -> Dict[str, str]:
        highlights: Dict[str, str] = {}
        if not analytical:
            return highlights
        churn_data = analytical.get('ChurnRiskAgent', {}).get('data', {})
        for convo in churn_data.get('high_risk_conversations', [])[:5]:
            topics = convo.get('detected_topics') or convo.get('topics') or []
            summary = convo.get('llm_analysis') or ", ".join(convo.get('signals', [])[:2])
            for topic in topics:
                highlights[str(topic)] = f"Churn risk: {summary}"
        return highlights

    def _extract_correlation_highlights(self, analytical: Dict[str, Any]) -> Dict[str, str]:
        highlights: Dict[str, str] = {}
        if not analytical:
            return highlights
        correlation_data = analytical.get('CorrelationAgent', {}).get('data', {})
        for corr in correlation_data.get('correlations', [])[:5]:
            description = corr.get('description', '')
            insight = corr.get('insight', '')
            for topic_word in description.split('↔'):
                topic_name = topic_word.strip()
                if topic_name:
                    highlights[topic_name] = f"Correlation: {insight or description}"
        return highlights

    def _build_prompt(self, context: AgentContext, payload: Dict[str, Any]) -> str:
        payload_json = json.dumps(payload, ensure_ascii=False, indent=2)
        digest_mode = payload.get('settings', {}).get('digest_mode', False)
        digest_guidance = ""
        if digest_mode:
            digest_guidance = """
DIGEST MODE CONSTRAINTS:
- Executive Narrative must be a single concise paragraph (≤3 sentences).
- Topic Stories should cover only the provided topics (already trimmed) and stay to ~2 sentences plus one inline quote per topic.
- Prioritized Actions should include no more than two brief bullets with crisp verbs.
"""
        return f"""
You are the NarrativeFormatterAgent. Based on the structured data below,
craft the "VoC: Narrative V2 (Hilary Weekly Story)" report.

DATA (representative sample of the week's conversations):
{payload_json}

OUTPUT RULES:
1. Return clean markdown only.
2. Follow this section order exactly and use "---" to separate every major section (this creates slides):
   # Executive Narrative (tie the week together with 2-3 sentences unless digest mode says otherwise)
   ---
   ## Metrics at a Glance (render a markdown table with columns Metric | Value that covers: total conversations, paid human workload, free Fin-only volume, topic count, Fin free-tier resolution rate, Fin paid-tier resolution rate. Use "N/A" if a number is missing.)
   ---
   ## Cross-Agent Signals (bullets linking correlations/churn)
   ---
   ## BPO Snapshot (Horatio/Boldr loads + pressure points)
   ---
   ## Topic Stories (one subsection per topic, weaving sentiment, Fin stats, vendor load, analytical signals, and exactly one curated quote that links to Intercom)
   ---
   ## Prioritized Actions (3 numbered items max unless digest mode constrains further)
   ---
   ## Risk Watchlist (bullets or '_No acute risks detected_')
3. When writing Topic Stories, embed one curated quote inline using the format ["customer text"](intercom_url). Prefer translations when available and note the original language if it was not English.
4. Mention Fin resolution performance or knowledge gaps inline when relevant and cite vendor workload inline (e.g., "Horatio carrying 62% of escalations").
5. Use the provided metrics verbatim—do not invent numbers. If data is missing, explicitly write "N/A".
6. Keep sentences concise, human, and confident. No generic refusals. Refer to the data as a "representative weekly sample."
{digest_guidance}
"""

    def _fallback_narrative(self, payload: Dict[str, Any]) -> str:
        topics = payload.get('topics', [])
        cross_signals = payload.get('cross_agent_signals', {})
        bpo = payload.get('bpo_snapshot', {})
        metrics = payload.get('metrics_overview', {})
        fmt = lambda value: value if value not in (None, "") else "N/A"
        summary_lines = [
            "# Executive Narrative",
            "Customer volume continued at typical levels. Key friction remains concentrated in the top topics listed below.",
            "",
            "## Metrics at a Glance",
            "| Metric | Value |",
            "| --- | --- |",
            f"| Total conversations | {fmt(metrics.get('total_conversations'))} |",
            f"| Paid human workload | {fmt(metrics.get('paid_human_conversations'))} |",
            f"| Free Fin-only volume | {fmt(metrics.get('free_fin_only_conversations'))} |",
            f"| Topic count | {fmt(metrics.get('topic_count'))} |",
            f"| Fin free-tier resolution rate | {fmt(metrics.get('fin_free_resolution_rate'))} |",
            f"| Fin paid-tier resolution rate | {fmt(metrics.get('fin_paid_resolution_rate'))} |",
            "",
            "## Cross-Agent Signals"
        ]
        if any(cross_signals.values()):
            for bucket in ('correlations', 'churn'):
                for item in cross_signals.get(bucket, []):
                    summary_lines.append(f"- {item}")
        else:
            summary_lines.append("- No cross-agent anomalies detected.")
        summary_lines.append("")
        summary_lines.append("## BPO Snapshot")
        if bpo:
            summary_lines.append(bpo.get('bpo_snapshot_summary', "_See vendor overview from upstream data._"))
        else:
            summary_lines.append("_No vendor workload data available._")
        summary_lines.append("")
        summary_lines.append("## Topic Stories")
        for topic in topics[:3]:
            summary_lines.append(f"### {topic['name']}")
            summary_lines.append(f"- Sentiment: {topic.get('sentiment') or 'No sentiment insight available.'}")
            bpo_line = topic.get('bpo_callout', {}).get('inline_callout')
            if bpo_line:
                summary_lines.append(f"- Vendor Load: {bpo_line}")
            quote = (topic.get('quotes') or [])
            if quote:
                quote_payload = quote[0]
                text = quote_payload.get('text') or quote_payload.get('original_preview') or ''
                if len(text) > 140:
                    text = text[:137] + "..."
                summary_lines.append(f"- Quote: [{text}]({quote_payload.get('intercom_url')})")
            summary_lines.append("")
        summary_lines.append("## Prioritized Actions")
        summary_lines.append("1. Focus on top friction topics and rebalance Horatio/Boldr workload.")
        summary_lines.append("")
        summary_lines.append("## Risk Watchlist")
        risks = payload.get('risk_watchlist') or ["_No acute risks detected_"]
        for risk in risks:
            summary_lines.append(f"- {risk}")
        return "\n".join(summary_lines)

    def format_context_data(self, context: AgentContext) -> str:
        """
        Provide a concise JSON summary for BaseAgent prompt builders.

        NarrativeFormatterAgent primarily consumes prior agent outputs
        rather than raw conversation text, so we list those keys and
        high-level metadata to avoid bloating prompts.
        """
        summary = {
            "analysis_id": context.analysis_id,
            "analysis_type": context.analysis_type,
            "date_range": {
                "start": context.start_date.isoformat() if context.start_date else None,
                "end": context.end_date.isoformat() if context.end_date else None,
            },
            "conversation_count": len(context.conversations or []),
            "previous_results_keys": sorted(list((context.previous_results or {}).keys())),
            "metadata": context.metadata,
        }
        return json.dumps(summary, ensure_ascii=False, indent=2)

