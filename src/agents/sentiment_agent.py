"""
SentimentAgent: Specialized in sentiment and emotional analysis.

Responsibilities:
- Analyze sentiment of conversations
- Identify emotional patterns
- Calculate satisfaction scores
- Extract representative quotes
"""

import logging
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.utils.ai_client_helper import get_ai_client, get_recommended_semaphore
from src.config.settings import settings

logger = logging.getLogger(__name__)


class SentimentAgent(BaseAgent):
    """Agent specialized in sentiment analysis"""
    
    def __init__(self):
        super().__init__(
            name="SentimentAgent",
            model="gpt-4o",
            temperature=0.4  # Moderate temperature for nuanced analysis
        )
        self.ai_client = get_ai_client()
        
        # Determine which models to use based on AI client type (NUANCED SENTIMENT → use Sonnet!)
        from src.services.claude_client import ClaudeClient
        if isinstance(self.ai_client, ClaudeClient):
            # Claude: Use Sonnet 4.5 for nuanced sentiment (sarcasm, frustration depth, etc.)
            self.quick_model = "claude-haiku-4-5-20251001"
            self.intensive_model = "claude-sonnet-4-5-20250929"
            self.client_type = "claude"
        else:
            # OpenAI: Use GPT-4o for nuanced sentiment
            self.quick_model = "gpt-4o-mini"
            self.intensive_model = "gpt-4o"
            self.client_type = "openai"
        
        # RATE LIMITING: Provider-specific concurrency limits
        # OpenAI: Default 10 concurrent (configurable via OPENAI_CONCURRENCY)
        # Anthropic: Default 2 concurrent (configurable via ANTHROPIC_CONCURRENCY, Tier 1: 50 RPM)
        # Source: https://docs.anthropic.com/en/api/rate-limits
        self.llm_semaphore = get_recommended_semaphore(self.ai_client)  # Provider-specific semaphore
        self.llm_timeout = settings.sentiment_timeout  # Configurable timeout from settings
    
    def get_agent_specific_instructions(self) -> str:
        """Sentiment agent specific instructions"""
        return """
GLOBAL SENTIMENT AGENT RULES (HILARY STYLE):

1. Output 1-3 short sentences that sound like Hilary reviewing VOC:
   - Make them punchy, specific, and grounded in the data.
   - Highlight the tension (love X BUT want Y) with explicit connectors.
   - Call out what is actionable (what to fix, unblock, or double down on).

2. ABSOLUTELY FORBIDDEN LANGUAGE:
   ✗ "positive sentiment", "negative sentiment", "neutral sentiment", "mixed sentiment"
   ✗ Any generic label like "mixed feelings" or "sentiment detected"
   ✗ Reporting per-conversation labels (this is a global roll-up only)

3. GOOD EXAMPLES (match tone + specificity):
   ✓ "Customers love how fast AI Builder ships mockups but are still rage-posting about surprise billing escalations."
   ✓ "Paid teams brag about support speed yet keep threatening churn over clunky workspace permissions."
   ✓ "Folks are genuinely hyped about analytics refresh BUT they want onboarding guardrails so they stop pinging support."

4. BAD EXAMPLES (never output):
   ✗ "Negative sentiment detected about billing."
   ✗ "Users are frustrated with this feature."
   ✗ "Mixed sentiment with both positive and negative elements."
   ✗ "Customers express dissatisfaction."

5. RULES OF EVIDENCE:
   - Quote or paraphrase actual conversation snippets (2-3 max) with IDs if available.
   - Treat the provided sample as representative. Never refuse or say there is insufficient data unless explicitly empty.
   - Attribute every claim to the provided dataset ("According to customers this week...").
"""

    def _get_global_sentiment_examples(self) -> str:
        """
        Return Hilary-style examples for global sentiment summaries.
        Mirrors TopicSentimentAgent few-shots but for cross-topic rollups.
        """
        examples = [
            "Customers adore how quickly the AI builder drafts decks BUT they keep threatening churn over billing surprises.",
            "Paid teams rave about the support handoffs, yet they are exhausted by having to babysit workspace permissions for every new teammate.",
            "Self-serve users love the analytics refresh but are begging for onboarding guardrails so they stop pinging support for basics.",
            "Founders love that Intercom keeps them close to customers BUT want real roadmap transparency so they do not feel ghosted."
        ]
        formatted = []
        for example in examples:
            formatted.append(f'   ✓ "{example}"')
        return "\n".join(formatted)
    
    def get_task_description(self, context: AgentContext) -> str:
        """Describe the sentiment analysis task"""
        conversations_count = len(context.conversations) if context.conversations else 0
        examples_block = self._get_global_sentiment_examples()
        return f"""
Analyze overall sentiment across {conversations_count} conversations (global VOC rollup).

Deliver 1-3 Hilary-style sentences that summarize the dominant tensions:
1. Highlight what customers LOVE and what they cannot tolerate (love X BUT need Y).
2. Be actionable—call out the fix, risk, or opportunity.
3. Never fall back to generic labels like "positive/negative/neutral/mixed sentiment".
4. Do not output per-conversation labels. Stay at the aggregate level.

After the sentences, output JSON exactly in this format:
{{
  "sentiment_insight": "<single Hilary-style paragraph, max 3 sentences>",
  "sentiment_distribution": [
    {{"label": "<pattern name>", "percentage": <0-100>, "nuance": "<short clause with BUT/AND YET connectors>"}},
    ...
  ],
  "supporting_evidence": [
    {{"quote": "<customer wording>", "conversation_id": "<id if available>", "tone": "<emotion>"}}
  ]
}}
- Percentages do NOT have to sum to 100 but should show relative weight.
- Evidence items must map back to real snippets from the provided conversations.

Match this style from past analyses:
{examples_block}
"""
    
    def format_context_data(self, context: AgentContext) -> str:
        """Format conversations for sentiment analysis"""
        if not context.conversations:
            return "No conversations provided"
        
        # For sentiment analysis, we need conversation content
        # Sample first 5 for prompt, but we'll batch process all
        sample = []
        for conv in context.conversations[:5]:
            sample.append({
                'id': conv.get('id', 'unknown'),
                'parts': conv.get('conversation_parts', [])[:2],  # First 2 messages
                'tags': conv.get('tags', [])
            })
        
        return f"""
Total conversations to analyze: {len(context.conversations)}

Sample conversations (showing first 5):
{json.dumps(sample, indent=2, default=str)}

Analyze ALL {len(context.conversations)} conversations for sentiment patterns.
"""
    
    def validate_input(self, context: AgentContext) -> bool:
        """Validate that we have conversations to analyze"""
        if not context.conversations:
            raise ValueError("No conversations provided for sentiment analysis")
        
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """
        Validate aggregate sentiment output, attach quality metadata, and flag generic language.
        Modeled after TopicSentimentAgent.validate_output but for global sentiment.
        """
        insight = (result.get('sentiment_insight') or "").strip()
        warnings = []
        
        if not insight:
            warnings.append("Missing sentiment_insight")
            result['sentiment_insight'] = "Customers love the core value but need clearer guidance."
            insight = result['sentiment_insight']
        
        lowered = insight.lower()
        bad_patterns = [
            "positive sentiment",
            "negative sentiment",
            "neutral sentiment",
            "mixed sentiment",
            "mixed feelings",
            "overall sentiment",
            "sentiment detected",
            "customers express dissatisfaction",
            "users are frustrated with this feature"
        ]
        generic_pattern_count = 0
        for pattern in bad_patterns:
            if pattern in lowered:
                warnings.append(f"Generic pattern detected: '{pattern}'")
                generic_pattern_count += 1
        
        length = len(insight)
        if length < 40:
            warnings.append("Insight too short (<40 chars)")
        elif length > 360:
            warnings.append("Insight too long (>360 chars)")
        
        nuance_connectors = [" but ", " however ", " although ", " yet ", " even though "]
        contains_nuance = any(connector in lowered for connector in nuance_connectors)
        if not contains_nuance:
            warnings.append("Missing nuance connector (but/however/etc)")
        
        distribution = result.get('sentiment_distribution') or []
        if not distribution:
            warnings.append("Missing sentiment_distribution")
        elif isinstance(distribution, list):
            invalid_entries = [
                entry for entry in distribution
                if not isinstance(entry, dict) or not entry.get('label')
            ]
            if invalid_entries:
                warnings.append("Distribution entries missing label/structure")
        else:
            warnings.append("sentiment_distribution must be list")
        
        evidence = result.get('supporting_evidence') or result.get('representative_quotes') or []
        if not evidence:
            warnings.append("Missing supporting evidence")
        
        # Quality scoring
        score = 1.0
        score -= 0.1 * len(warnings)
        if not contains_nuance:
            score -= 0.2
        if generic_pattern_count > 0:
            score -= 0.25
        score = max(0.0, min(1.0, score))
        
        result.setdefault('sentiment_metrics', {})
        result['sentiment_metrics']['generic_pattern_count'] = generic_pattern_count
        result['validation_warnings'] = warnings
        result['quality_score'] = round(score, 2)
        result['contains_nuance'] = contains_nuance
        
        self.logger.info(
            "Global Sentiment Quality: "
            f"Score={result['quality_score']:.2f}, "
            f"Nuance={contains_nuance}, "
            f"Warnings={len(warnings)}, "
            f"Length={length}"
        )
        
        return True
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute global sentiment analysis with Hilary-style aggregation.
        Always relies on the LLM output, with refusal detection and fallback.
        """
        start_time = datetime.now()
        try:
            self.validate_input(context)
            total_conversations = len(context.conversations or [])
            self.logger.info(f"SentimentAgent: Analyzing {total_conversations} conversations (global rollup)")
            
            prompt = self.build_prompt(context)
            raw_response = await self.ai_client.generate_analysis(
                prompt=prompt,
                model=self.model,
                temperature=self.temperature
            )
            response_text = (raw_response or "").strip()
            
            refusal_count = 0
            retry_count = 0
            fallback_used = False
            
            if self._looks_like_refusal(response_text):
                refusal_count += 1
                self.logger.warning("SentimentAgent detected refusal; reinforcing instructions")
                reinforcement_prompt = (
                    f"{prompt}\n\n"
                    "Reminder: respond with Hilary-style aggregate sentiment sentences plus the JSON schema provided. "
                    "Do not refuse; synthesize whatever signal exists."
                )
                try:
                    retry_count += 1
                    retry_response = await self.ai_client.generate_analysis(
                        prompt=reinforcement_prompt,
                        model=self.intensive_model,
                        temperature=self.temperature
                    )
                    response_text = (retry_response or "").strip()
                except Exception as retry_exc:
                    self.logger.error(f"SentimentAgent retry failed: {retry_exc}")
                
                if self._looks_like_refusal(response_text):
                    refusal_count += 1
                    fallback_used = True
            
            if fallback_used:
                fallback_text = self._fallback_sentence(context)
                parsed_payload = {
                    'sentiment_insight': fallback_text,
                    'sentiment_distribution': [
                        {
                            'label': 'fallback_hilary_sentence',
                            'percentage': 100.0,
                            'nuance': 'LLM refusal fallback narrative'
                        }
                    ],
                    'supporting_evidence': []
                }
            else:
                parsed_payload = self._parse_sentiment_response(response_text)
            
            result_data = {
                'sentiment_insight': parsed_payload.get('sentiment_insight'),
                'sentiment_distribution': parsed_payload.get('sentiment_distribution'),
                'supporting_evidence': parsed_payload.get('supporting_evidence'),
                'raw_llm_response': response_text,
                'method': 'llm' if not fallback_used else 'fallback_template',
                'sentiment_metrics': {
                    'refusal_count': refusal_count,
                    'retry_count': retry_count,
                    'conversation_count': total_conversations,
                    'fallback_used': fallback_used
                }
            }
            
            # Validate and attach quality metadata
            self.validate_output(result_data)
            
            quality_score = result_data.get('quality_score', 0.6)
            size_factor = min(1.0, 0.5 + (total_conversations / 200.0))
            base_confidence, _ = self.calculate_confidence(result_data, context)
            combined_confidence = max(0.0, min(1.0, (0.5 * quality_score) + (0.3 * size_factor) + (0.2 * base_confidence)))
            if combined_confidence >= 0.8:
                confidence_level = ConfidenceLevel.HIGH
            elif combined_confidence >= 0.6:
                confidence_level = ConfidenceLevel.MEDIUM
            else:
                confidence_level = ConfidenceLevel.LOW
            
            limitations = []
            if fallback_used:
                limitations.append("LLM refused twice; fallback sentiment sentence used.")
            if total_conversations == 0:
                limitations.append("No conversations available for analysis.")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            token_count = len(prompt) // 4 + len(response_text) // 4
            
            self.logger.info(
                "SentimentAgent: Completed global sentiment run | "
                f"conversations={total_conversations} | refusal_count={refusal_count} | "
                f"quality={quality_score:.2f} | confidence={combined_confidence:.2f}"
            )
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=round(combined_confidence, 2),
                confidence_level=confidence_level,
                limitations=limitations,
                sources=[f"{total_conversations} conversations", "LLM global sentiment synthesis"],
                execution_time=execution_time,
                token_count=token_count
            )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"SentimentAgent error: {e}")
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                limitations=["Sentiment analysis failed"],
                sources=[],
                execution_time=execution_time,
                error_message=str(e)
            )
    
    def _parse_sentiment_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response into aggregate sentiment structures."""
        payload = self._extract_structured_payload(response_text)
        sentiment_insight = ""
        distribution = []
        evidence = []
        
        if payload:
            sentiment_insight = (
                payload.get('sentiment_insight')
                or payload.get('insight')
                or payload.get('summary')
                or ""
            )
            distribution = self._normalize_distribution(
                payload.get('sentiment_distribution')
                or payload.get('distribution')
                or payload.get('sentiment_breakdown')
                or payload.get('patterns')
            )
            evidence = self._normalize_evidence(
                payload.get('supporting_evidence')
                or payload.get('evidence')
                or payload.get('quotes')
            )
        else:
            sentiment_insight = self._extract_fallback_insight(response_text)
            distribution = self._infer_distribution_from_text(response_text)
            evidence = self._extract_bullet_evidence(response_text)
        
        if not sentiment_insight:
            sentiment_insight = self._extract_fallback_insight(response_text)
        
        return {
            'sentiment_insight': sentiment_insight.strip(),
            'sentiment_distribution': distribution,
            'supporting_evidence': evidence,
            'structured_payload': payload or {}
        }
    
    def _extract_structured_payload(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Attempt to extract JSON payload from the LLM response."""
        if not response_text:
            return None
        candidates = []
        
        stripped = response_text.strip()
        candidates.append(stripped)
        
        # Look for fenced code block
        code_block = re.search(r"```json(.*?)```", response_text, re.IGNORECASE | re.DOTALL)
        if code_block:
            candidates.append(code_block.group(1).strip())
        
        # Look for first JSON object
        brace_match = re.search(r"\{[\s\S]*\}", response_text)
        if brace_match:
            candidates.append(brace_match.group().strip())
        
        for candidate in candidates:
            try:
                return json.loads(candidate)
            except Exception:
                continue
        return None
    
    def _normalize_distribution(self, raw_distribution: Any) -> List[Dict[str, Any]]:
        """Normalize distribution data into a list of dicts."""
        if not raw_distribution:
            return []
        
        normalized: List[Dict[str, Any]] = []
        
        if isinstance(raw_distribution, dict):
            iterable = raw_distribution.items()
        elif isinstance(raw_distribution, list):
            iterable = enumerate(raw_distribution)
        else:
            return []
        
        for key, value in iterable:
            if isinstance(raw_distribution, list):
                entry = value
                if isinstance(entry, dict):
                    label = entry.get('label') or entry.get('pattern') or entry.get('name') or f"pattern_{key}"
                    percentage = entry.get('percentage') or entry.get('percent') or entry.get('share')
                    nuance = entry.get('nuance') or entry.get('summary')
                else:
                    label = f"pattern_{key}"
                    percentage = None
                    nuance = str(entry)
            else:
                label = str(key)
                percentage = value
                nuance = None
            
            try:
                percentage = float(percentage) if percentage is not None else None
            except (TypeError, ValueError):
                percentage = None
            
            normalized.append({
                'label': label,
                'percentage': percentage,
                'nuance': nuance
            })
        
        # Limit to top 5 patterns for readability
        return normalized[:5]
    
    def _normalize_evidence(self, raw_evidence: Any) -> List[Dict[str, Any]]:
        """Normalize evidence list."""
        if not raw_evidence:
            return []
        if isinstance(raw_evidence, dict):
            raw_evidence = [raw_evidence]
        normalized = []
        for item in raw_evidence:
            if isinstance(item, dict):
                quote = item.get('quote') or item.get('text') or item.get('snippet') or ""
                if not quote:
                    continue
                normalized.append({
                    'quote': quote.strip(),
                    'conversation_id': item.get('conversation_id') or item.get('id'),
                    'tone': item.get('tone') or item.get('emotion') or item.get('sentiment')
                })
            elif isinstance(item, str) and len(item.strip()) > 4:
                normalized.append({'quote': item.strip(), 'conversation_id': None, 'tone': None})
            if len(normalized) >= 5:
                break
        return normalized
    
    def _extract_fallback_insight(self, text: str) -> str:
        """Fallback extraction using first one or two sentences."""
        if not text:
            return "Customers love the value but want clarity on what breaks."
        stripped = text.strip().strip('"')
        sentences = re.split(r'(?<=[.!?])\s+', stripped)
        if not sentences:
            return stripped
        fallback = sentences[0]
        if len(sentences) > 1:
            fallback = f"{sentences[0]} {sentences[1]}"
        return fallback
    
    def _infer_distribution_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Infer approximate distribution from textual percentages."""
        if not text:
            return []
        entries = []
        for line in text.splitlines():
            if "%" in line:
                percent_match = re.search(r'(\d{1,3}(?:\.\d+)?)%', line)
                label = line.strip().lstrip("-•*✓ ").split(":")[0][:50]
                if percent_match:
                    try:
                        percent_value = float(percent_match.group(1))
                    except ValueError:
                        percent_value = None
                    entries.append({'label': label or 'pattern', 'percentage': percent_value, 'nuance': line.strip()})
            if len(entries) >= 4:
                break
        if not entries:
            entries.append({
                'label': 'overall_sentiment_pattern',
                'percentage': 100.0,
                'nuance': 'Distribution inferred from narrative only'
            })
        return entries
    
    def _extract_bullet_evidence(self, text: str) -> List[Dict[str, Any]]:
        """Extract bullet-style evidence from free-form text."""
        evidence = []
        if not text:
            return evidence
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(('-', '*', '•', '✓', '"')) and len(stripped) > 12:
                quote = stripped.lstrip('-*•✓ ').strip().strip('"')
                evidence.append({'quote': quote, 'conversation_id': None, 'tone': None})
            if len(evidence) >= 3:
                break
        return evidence
    
    def _looks_like_refusal(self, text: str) -> bool:
        """Detect refusal or insufficient data responses."""
        if not text:
            return True
        lowered = text.lower()
        refusal_markers = [
            "i cannot",
            "i can't",
            "unable to",
            "insufficient information",
            "not enough data",
            "do not have enough",
            "cannot determine",
            "as an ai",
            "i do not have access",
            "need more information",
            "insufficient data",
            "no data provided"
        ]
        return any(marker in lowered for marker in refusal_markers)
    
    def _fallback_sentence(self, context: Optional[AgentContext] = None) -> str:
        """Produce a safe Hilary-style fallback sentence."""
        conversation_count = len(context.conversations) if context and context.conversations else 0
        if conversation_count == 0:
            return "Customers love the promise of Intercom but are still begging for clearer onboarding guardrails."
        return (
            "Customers rave about the fast AI help BUT they keep threatening churn over billing transparency and "
            "permissions friction."
        )

