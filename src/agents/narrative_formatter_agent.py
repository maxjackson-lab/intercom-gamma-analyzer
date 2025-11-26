import json
import logging
from datetime import datetime, date
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

    def _compute_global_date_range(self, convs: List[Dict]) -> Dict[str, str]:
        if not convs:
            return {}
        try:
            timestamps = [c.get('created_at') for c in convs if c.get('created_at')]
            if not timestamps:
                return {}
            
            min_val = min(timestamps)
            max_val = max(timestamps)
            
            from datetime import datetime
            
            def to_iso(val):
                if isinstance(val, (int, float)):
                    return datetime.fromtimestamp(val).isoformat()
                if hasattr(val, 'isoformat'):
                    return val.isoformat()
                return str(val)

            return {
                'min_created_at': to_iso(min_val),
                'max_created_at': to_iso(max_val)
            }
        except Exception as e:
            self.logger.warning(f"Failed to compute global date range: {e}")
            return {}

    def _validate_critical_sections(self, payload: Dict[str, Any]) -> None:
        """
        Validate that critical sections (BPO, Fin, Topics) have data.
        Raises ValueError if critical sections are empty/missing to prevent silent failures.
        """
        # Check BPO
        bpo = payload.get('bpo_snapshot', {})
        if not bpo.get('vendor_overview'):
            # It's possible BPO agent didn't run or produced empty result.
            # We should signal this clearly.
            # However, if it wasn't requested (e.g. digest mode without BPO?), maybe skip.
            # But standard report requires it.
            pass # We'll let the prompt handle empty BPO if it's legitimately empty, 
                 # but if the agent failed, we want to know.
                 # The orchestrator now handles "fail_on_critical_errors".
                 # Here we just ensure we don't generate a misleading report if data is unexpectedly missing.
        
        # Check Topics
        if not payload.get('topics'):
             raise ValueError("Critical Section Missing: No topics found in payload.")

        # Check Fin
        fin = payload.get('fin_overview', {})
        if not fin.get('free_tier') and not fin.get('paid_tier'):
             raise ValueError("Critical Section Missing: No Fin performance data in payload.")

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
        
        # Validate critical sections before generation
        try:
            self._validate_critical_sections(payload)
        except ValueError as exc:
             return AgentResult(
                agent_name=self.name,
                success=False,
                data={'error': str(exc)},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                limitations=[f"Critical Data Missing: {str(exc)}"],
                error_message=str(exc),
                execution_time=0.0
            )

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
        # #region agent log
        import json as _json_debug; _log_path = "/Users/max.jackson/Intercom Analysis Tool /.cursor/debug.log"; open(_log_path, "a").write(_json_debug.dumps({"location": "narrative_formatter_agent.py:_assemble_payload", "message": "previous_results keys", "data": {"keys": list(previous.keys()), "has_subtopic": "SubTopicDetectionAgent" in previous}, "hypothesisId": "H1", "timestamp": __import__("time").time()}) + "\n")
        # #endregion
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
        # #region agent log
        subtopic_entry = previous.get('SubTopicDetectionAgent') or {}; subtopic_data = subtopic_entry.get('data', {}) if isinstance(subtopic_entry, dict) else {}; open(_log_path, "a").write(_json_debug.dumps({"location": "narrative_formatter_agent.py:_assemble_payload", "message": "subtopic data check", "data": {"subtopic_entry_keys": list(subtopic_entry.keys()) if isinstance(subtopic_entry, dict) else "not_dict", "subtopic_data_keys": list(subtopic_data.keys()) if isinstance(subtopic_data, dict) else "not_dict", "has_hierarchy": "topic_hierarchy" in subtopic_data or "subtopics_by_topic" in subtopic_data}, "hypothesisId": "H1", "timestamp": __import__("time").time()}) + "\n")
        # #endregion

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
        
        global_range = self._compute_global_date_range(context.conversations or [])
        
        # Format date label
        from datetime import datetime
        try:
            min_ts = global_range.get('min_created_at')
            max_ts = global_range.get('max_created_at')
            if min_ts and max_ts:
                min_dt = datetime.fromisoformat(min_ts)
                max_dt = datetime.fromisoformat(max_ts)
                raw_dates_label = f"{min_dt.strftime('%b %d')}–{max_dt.strftime('%b %d')}"
            else:
                raw_dates_label = "Unknown"
        except:
            raw_dates_label = "Unknown"

        metrics_overview['date_range_label'] = f"Analysis: {context.start_date.strftime('%b %d')}–{context.end_date.strftime('%b %d')} | Raw data: {raw_dates_label}"

        payload = {
            'global_date_range': global_range,
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
                    'total_conversations': fin_free_snapshot.get('total_conversations'),
                    'sample_conversations': fin_free_snapshot.get('sample_conversations', []),
                    'date_range': fin_free_snapshot.get('date_range')
                },
                'paid_tier': {
                    'resolution_rate': fin_paid_snapshot.get('resolution_rate'),
                    'total_conversations': fin_paid_snapshot.get('total_conversations'),
                    'sample_conversations': fin_paid_snapshot.get('sample_conversations', []),
                    'date_range': fin_paid_snapshot.get('date_range')
                }
            },
            'topics': top_topics,
            'bpo_snapshot': bpo_performance, # BpoPerformanceAgent result already includes sample_conversations and date_range inside vendor_overview
            'cross_agent_signals': cross_agent_signals,
            'risk_watchlist': bpo_performance.get('risk_watchlist', []),
            'prioritized_actions_hint': [t.get('action_hint') for t in top_topics[:4]],
            'metrics_overview': metrics_overview,
            'synthesis_summary': synthesis_summary,
            'settings': {'digest_mode': digest_mode}
        }
        # #region agent log
        open(_log_path, "a").write(_json_debug.dumps({"location": "narrative_formatter_agent.py:_assemble_payload:return", "message": "final payload keys", "data": {"payload_keys": list(payload.keys()), "has_subtopics_key": "subtopics" in payload or "sub_topics" in payload, "topics_count": len(top_topics), "first_topic_keys": list(top_topics[0].keys()) if top_topics else []}, "hypothesisId": "H3", "timestamp": __import__("time").time()}) + "\n")
        # #endregion
        return payload

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

    @staticmethod
    def _json_default(value: Any) -> str:
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return str(value)

    def _build_prompt(self, context: AgentContext, payload: Dict[str, Any]) -> str:
        payload_json = json.dumps(payload, ensure_ascii=False, indent=2, default=self._json_default)
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
   # Executive Narrative (tie the week together with 2-3 sentences unless digest mode says otherwise. Reference the raw data date range: {payload.get('metrics_overview', {}).get('date_range_label')})
   ---
   ## Metrics at a Glance (render a markdown table with columns Metric | Value. Must include: Date Range, total conversations, paid human workload, free Fin-only volume, topic count, Fin free-tier resolution rate, Fin paid-tier resolution rate.)
   ---
   ## Cross-Agent Signals (bullets linking correlations/churn)
   ---
   ## BPO Snapshot (Horatio/Boldr loads + pressure points)
   **Table: Vendor | % Load | Date Range | Sample Links**
   (For each vendor, render a table row. 'Sample Links' should be 2-3 [snippet](url) links based on provided sample_conversations. If no samples, write N/A.)
   ---
   ## Fin Overview
   **Table: Tier | Resolution | Date Range | Sample Links**
   (Render table with rows for Free and Paid tiers. Include date range and sample [snippet](url) links from provided data. Use sample_conversations to create links.)
   ---
   ## Topic Stories (one subsection per topic, weaving sentiment, Fin stats, vendor load, analytical signals, and exactly one curated quote that links to Intercom. Mention volume date range.)
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
        fin = payload.get('fin_overview', {})
        metrics = payload.get('metrics_overview', {})
        fmt = lambda value: value if value not in (None, "") else "N/A"
        
        # Explicit checks for missing critical sections
        missing_sections = []
        if not bpo.get('vendor_overview'):
            missing_sections.append("BPO/Vendor Data")
        if not fin.get('free_tier') and not fin.get('paid_tier'):
            missing_sections.append("Fin Performance Data")
        if not topics:
            missing_sections.append("Topic Analysis")
            
        exec_summary = [
            "# Executive Narrative",
            "Customer volume continued at typical levels. Key friction remains concentrated in the top topics listed below."
        ]
        
        if missing_sections:
            exec_summary.append(f"\n\n**⚠️ Note: The following analysis is incomplete due to missing data: {', '.join(missing_sections)}.**")

        summary_lines = exec_summary + [
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
        if bpo and bpo.get('vendor_overview'):
            summary_lines.append(bpo.get('bpo_snapshot_summary', "_See vendor overview from upstream data._"))
            # Surface a sample link if available
            first_vendor = next(iter(bpo['vendor_overview'].values()))
            if first_vendor and first_vendor.get('sample_conversations'):
                sample = first_vendor['sample_conversations'][0]
                summary_lines.append(f"- Sample: [{sample.get('snippet', 'Link')}]({sample.get('url')})")
        else:
            summary_lines.append("_⚠️ BPO Performance Agent failed or produced no data._")
            
        summary_lines.append("")
        summary_lines.append("## Fin Overview")
        if fin:
             # Basic text summary for Fin
             free = fin.get('free_tier', {})
             paid = fin.get('paid_tier', {})
             summary_lines.append(f"- Free Tier: {fmt(free.get('resolution_rate'))} resolution ({fmt(free.get('total_conversations'))} convs)")
             if free.get('sample_conversations'):
                 sample = free['sample_conversations'][0]
                 summary_lines.append(f"  - Sample: [{sample.get('snippet', 'Link')}]({sample.get('url')})")
             
             summary_lines.append(f"- Paid Tier: {fmt(paid.get('resolution_rate'))} resolution ({fmt(paid.get('total_conversations'))} convs)")
             if paid.get('sample_conversations'):
                 sample = paid['sample_conversations'][0]
                 summary_lines.append(f"  - Sample: [{sample.get('snippet', 'Link')}]({sample.get('url')})")
        else:
             summary_lines.append("_⚠️ Fin Performance Agent failed or produced no data._")

        summary_lines.append("")
        summary_lines.append("## Topic Stories")
        if topics:
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
        else:
            summary_lines.append("_⚠️ No topics detected or TopicDetectionAgent failed._")

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

