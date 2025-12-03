"""
InsightAgent: Specialized in cross-category synthesis and strategic insights.

Responsibilities:
- Synthesize insights from category and sentiment data
- Identify cross-category patterns
- Generate "so what" implications
- Create actionable recommendations
"""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.utils.ai_client_helper import get_ai_client

logger = logging.getLogger(__name__)


class InsightAgent(BaseAgent):
    """Agent specialized in insight synthesis"""
    
    def __init__(self):
        super().__init__(
            name="InsightAgent",
            temperature=0.7  # Higher temperature for creative synthesis
        )
        self.ai_client = get_ai_client()
        self.workflow_type = 'standard'
    
    def get_agent_specific_instructions(self) -> str:
        """Insight agent specific instructions"""
        instructions = """
INSIGHT AGENT SPECIFIC RULES:

1. Only synthesize insights from data provided by previous agents - never invent patterns
2. Use "According to the analysis" for all claims about patterns
3. State limitations when data is incomplete: "Analysis limited by [reason]"
4. Never invent statistics or trends not present in the source data
5. Focus on "why it matters" not just "what happened"

Synthesis Requirements:
- Identify 3-4 major themes (not exhaustive lists)
- Connect patterns across categories
- Explain root causes where evident
- Provide business implications
- Generate actionable recommendations

CRITICAL CONTEXT ABOUT SUPPORT DATA:
- Customers write to support BECAUSE they're unhappy - this is normal
- Negative sentiment in support ≠ product failure
- What matters: Resolution quality, churn correlation, NPS/CSAT trends
- Focus on: First Contact Resolution, Time to Resolution, Escalation patterns
- NOT: "Customers are frustrated" (that's obvious - they're in support)
- YES: "23% of billing issues require escalation vs 12% last month" (actionable trend)

Output Structure:
1. Resolution Patterns (what's getting solved vs escalated)
2. Actionable Trends (volume changes, new issue types, resolution time changes)
3. Churn Indicators (if any patterns suggest customer loss risk)
4. Process Improvements (what would reduce ticket volume or improve resolution)
5. Recommendations (specific, data-driven next steps)

Tone: Data-Driven Analyst
- Assume support tickets are normal business operations
- Focus on efficiency and resolution quality
- Avoid melodrama about sentiment (it's support - people are upset)
- Lead with "Here's what's changing" not "Here's what's wrong"
- Compare to baselines and benchmarks when possible
"""
        if getattr(self, 'workflow_type', 'standard') == 'topic_based':
            instructions += """

DETECTION METHOD TAGGING (Topic-Based Workflow):
- Tag each insight with detection provenance from TopicDetectionAgent.
- Use "(Verified by AI Analysis)" for llm_smart or llm_only dominant detections.
- Use "(Trend detected via keyword patterns)" for keyword-led signals.
- Use "(Hybrid detection: AI + Keywords)" when hybrid detections drive the pattern.
- Call out attribute/fallback detections when confidence is low.
- Example: "Billing escalations up 23% (Verified by AI Analysis)."
- Example: "Refund macros spiking (Trend detected via keyword patterns)."
"""
        return instructions
    
    def get_task_description(self, context: AgentContext) -> str:
        """Describe the insight synthesis task"""
        return f"""
Synthesize strategic insights from the category and sentiment analysis.

You have been provided with:
- Category classifications with distribution
- Sentiment analysis with emotional patterns
- {len(context.conversations)} total conversations analyzed

Your task:
1. Identify the 3-4 most significant patterns
2. Explain what drives these patterns (root causes)
3. Connect insights across categories (what's the bigger story?)
4. Describe business implications (why should leadership care?)
5. Generate specific, actionable recommendations

Write this as a narrative briefing for executives, not a data dump.
"""
    
    def format_context_data(self, context: AgentContext) -> str:
        """Format previous agent results for synthesis"""
        if getattr(self, 'workflow_type', 'standard') == 'topic_based':
            return self._format_topic_based_context_data(context)
        
        category_results = context.previous_results.get('CategoryAgent', {}).get('data', {})
        sentiment_results = context.previous_results.get('SentimentAgent', {}).get('data', {})
        
        return f"""
CATEGORY ANALYSIS RESULTS:
{json.dumps(category_results.get('category_distribution', {}), indent=2)}

Total Classified: {category_results.get('total_classified', 0)}
High Confidence: {category_results.get('high_confidence_count', 0)}
Low Confidence: {category_results.get('low_confidence_count', 0)}

SENTIMENT ANALYSIS RESULTS:
{json.dumps(sentiment_results.get('sentiment_distribution', {}), indent=2)}

Total Analyzed: {sentiment_results.get('total_analyzed', 0)}
Average Confidence: {sentiment_results.get('average_confidence', 0):.2f}

Use ONLY this data to generate insights. Do not invent additional statistics.
"""

    def _format_topic_based_context_data(self, context: AgentContext) -> str:
        """Format topic-based workflow inputs for synthesis"""
        topic_detection = context.previous_results.get('TopicDetectionAgent', {}).get('data', {})
        topic_dist = topic_detection.get('topic_distribution', {})
        topic_sentiments = (
            context.previous_results.get('TopicSentimentAgent', {})
            or context.previous_results.get('TopicSentiments', {})
        )
        lines: List[str] = []

        lines.append("TOPIC DETECTION RESULTS:")
        if not topic_dist:
            lines.append("- No topic detection data available.")
        else:
            sorted_topics = sorted(
                topic_dist.items(),
                key=lambda item: item[1].get('volume', 0),
                reverse=True
            )
            for topic_name, stats in sorted_topics:
                volume = stats.get('volume', 0)
                pct = stats.get('percentage', 0.0)
                detection_label = self._get_detection_method_provenance(stats.get('detection_method'))
                lines.append(f"- {topic_name}: {volume} conversations ({pct}%)")
                lines.append(f"  Detection Method: {detection_label}")
                confidence_value = stats.get('confidence')
                if isinstance(confidence_value, (int, float)):
                    lines.append(f"  Detection Confidence: {confidence_value:.2f}")
                breakdown_parts = []
                ai_verified = (stats.get('llm_smart_count', 0) or 0) + (stats.get('llm_only_count', 0) or 0)
                if ai_verified:
                    breakdown_parts.append(f"{ai_verified} AI-verified")
                if stats.get('keyword_count'):
                    breakdown_parts.append(f"{stats.get('keyword_count')} Keyword")
                if stats.get('hybrid_count'):
                    breakdown_parts.append(f"{stats.get('hybrid_count')} Hybrid")
                if stats.get('sdk_only_count'):
                    breakdown_parts.append(f"{stats.get('sdk_only_count')} Attribute")
                if stats.get('fallback_count'):
                    breakdown_parts.append(f"{stats.get('fallback_count')} Fallback")
                if len(breakdown_parts) > 1:
                    lines.append(f"  Detection Mix: {', '.join(breakdown_parts)}")

        detection_confidence, method_distribution = self._extract_detection_method_confidence(topic_dist)
        if method_distribution:
            ai_pct = (method_distribution.get('llm_smart', 0.0) +
                      method_distribution.get('llm_only', 0.0))
            keyword_pct = method_distribution.get('keyword', 0.0)
            hybrid_pct = method_distribution.get('hybrid', 0.0)
            lines.append("")
            lines.append(
                f"DETECTION SUMMARY: {ai_pct:.1f}% AI-verified, "
                f"{keyword_pct:.1f}% keyword patterns, {hybrid_pct:.1f}% hybrid detection"
            )
            sdk_pct = method_distribution.get('sdk_only', 0.0)
            fallback_pct = method_distribution.get('fallback', 0.0)
            if sdk_pct or fallback_pct:
                extra = []
                if sdk_pct:
                    extra.append(f"{sdk_pct:.1f}% attributes")
                if fallback_pct:
                    extra.append(f"{fallback_pct:.1f}% fallback")
                lines.append(f"Additional coverage: {', '.join(extra)}")
            lines.append(f"Average detection confidence: {detection_confidence:.2f}")

        lines.append("")
        lines.append("TOPIC SENTIMENT RESULTS:")
        if topic_sentiments:
            for topic_name, sentiment_payload in topic_sentiments.items():
                data = sentiment_payload.get('data', sentiment_payload)
                insight = data.get('sentiment_insight') or data.get('sentiment')
                if insight:
                    lines.append(f"- {topic_name}: {insight}")
        else:
            lines.append("- No per-topic sentiment insights available.")

        lines.append("")
        lines.append("Tag insights with detection provenance:")
        lines.append("- (Verified by AI Analysis) → llm_smart or llm_only signals dominate")
        lines.append("- (Trend detected via keyword patterns) → keyword detections lead")
        lines.append("- (Hybrid detection) → AI + Keyword agreement drives the trend")

        return "\n".join(lines)

    def _get_detection_method_provenance(self, method: Optional[str]) -> str:
        """Return human-readable detection method label without emojis."""
        mapping = {
            'llm_smart': "Verified by AI Analysis (context hints)",
            'llm_only': "Verified by AI Analysis",
            'hybrid': "Hybrid detection (AI + Keywords)",
            'keyword': "Trend detected via keyword patterns",
            'sdk_only': "Detected via Intercom attributes",
            'attribute': "Detected via Intercom attributes",
            'fallback': "Fallback classification (low confidence)"
        }
        return mapping.get((method or '').lower(), "Detection method not specified")
    
    def validate_input(self, context: AgentContext) -> bool:
        """Validate presence of upstream agent outputs for both workflows"""
        previous_results = context.previous_results or {}
        if not previous_results:
            raise ValueError("No previous agent results provided")
        
        has_standard = (
            'CategoryAgent' in previous_results and
            'SentimentAgent' in previous_results
        )
        has_topic_detection = 'TopicDetectionAgent' in previous_results
        has_topic_sentiment = any(
            key in previous_results for key in ('TopicSentimentAgent', 'TopicSentiments')
        )
        
        if has_topic_detection and has_topic_sentiment:
            self.workflow_type = 'topic_based'
            return True
        
        if has_standard:
            self.workflow_type = 'standard'
            return True
        
        raise ValueError(
            "InsightAgent requires CategoryAgent + SentimentAgent results "
            "or TopicDetectionAgent + TopicSentimentAgent results"
        )
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate insight synthesis results"""
        required_fields = ['executive_summary', 'major_themes', 'recommendations']
        
        for field in required_fields:
            if field not in result:
                self.logger.warning(f"Missing field '{field}' in insights")
        
        if getattr(self, 'workflow_type', 'standard') == 'topic_based':
            detection_conf = result.get('detection_method_confidence')
            if detection_conf is None:
                self.logger.warning("Topic-based insights missing detection_method_confidence")
            elif detection_conf < 0.5:
                self.logger.warning(
                    f"Detection method confidence is low ({detection_conf:.2f})"
                )
            distribution = result.get('detection_method_distribution')
            if not distribution:
                self.logger.warning("Topic-based insights missing detection_method_distribution")
            else:
                pct_sum = sum(
                    value for key, value in distribution.items()
                    if key in {'llm_smart', 'llm_only', 'hybrid', 'keyword', 'sdk_only', 'fallback'}
                    and isinstance(value, (int, float))
                )
                if pct_sum and abs(pct_sum - 100) > 1:
                    self.logger.warning(
                        f"Detection method distribution does not sum to 100% (got {pct_sum:.1f}%)"
                    )
            tags = result.get('detection_method_tags') or []
            if not tags:
                section_text = " ".join(result.get('major_themes', [])) + " " + " ".join(result.get('recommendations', []))
                tags = self._extract_detection_method_tags_from_text(section_text)
                if tags:
                    result['detection_method_tags'] = tags
            if not tags:
                self.logger.warning("LLM did not include detection method tags in topic-based insights")
        
        return True
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute insight synthesis.
        
        Args:
            context: AgentContext with previous agent results
            
        Returns:
            AgentResult with synthesized insights
        """
        start_time = datetime.now()
        
        try:
            # Validate input
            self.validate_input(context)
            
            self.logger.info("InsightAgent: Synthesizing insights from previous agents")
            topic_distribution = {}
            if self.workflow_type == 'topic_based':
                topic_distribution = (
                    context.previous_results
                    .get('TopicDetectionAgent', {})
                    .get('data', {})
                    .get('topic_distribution', {})
                )
            
            # Build synthesis prompt
            prompt = self.build_prompt(context)
            
            # Call OpenAI for insight synthesis
            response = await self.ai_client.generate_analysis(
                prompt=prompt,
                model=self.model,
                temperature=self.temperature
            )
            
            # Parse response
            insights = self._parse_insights_response(response)
            
            # Prepare result
            result_data = {
                'executive_summary': insights.get('executive_summary', ''),
                'major_themes': insights.get('major_themes', []),
                'cross_category_patterns': insights.get('cross_category_patterns', []),
                'business_implications': insights.get('business_implications', ''),
                'recommendations': insights.get('recommendations', []),
                'synthesis_quality': self._assess_synthesis_quality(insights),
                'detection_method_tags': insights.get('detection_method_tags', [])
            }

            detection_method_confidence = None
            detection_method_distribution: Dict[str, float] = {}
            if self.workflow_type == 'topic_based':
                detection_method_confidence, detection_method_distribution = self._extract_detection_method_confidence(
                    topic_distribution
                )
                result_data['detection_method_confidence'] = detection_method_confidence
                result_data['detection_method_distribution'] = detection_method_distribution
            
            # Validate output
            self.validate_output(result_data)
            
            # Calculate confidence
            confidence, confidence_level = self.calculate_confidence(result_data, context)
            if (
                self.workflow_type == 'topic_based'
                and detection_method_confidence is not None
            ):
                blended_confidence = (
                    (result_data['synthesis_quality'] * 0.6) +
                    (detection_method_confidence * 0.4)
                )
                confidence = max(0.0, min(1.0, blended_confidence))
                if confidence >= 0.8:
                    confidence_level = ConfidenceLevel.HIGH
                elif confidence >= 0.6:
                    confidence_level = ConfidenceLevel.MEDIUM
                else:
                    confidence_level = ConfidenceLevel.LOW
            
            # Identify limitations
            limitations = []
            if result_data['synthesis_quality'] < 0.7:
                limitations.append("Synthesis quality below threshold - limited insight depth")
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Estimate token count
            token_count = len(prompt) // 4 + len(response) // 4

            sources = [
                "CategoryAgent results",
                "SentimentAgent results",
                "GPT-4o synthesis"
            ]
            if self.workflow_type == 'topic_based':
                ai_verified_pct = (
                    detection_method_distribution.get('llm_smart', 0.0) +
                    detection_method_distribution.get('llm_only', 0.0)
                )
                provenance = "TopicDetectionAgent results"
                if detection_method_distribution:
                    provenance += f" ({ai_verified_pct:.1f}% AI-verified mix)"
                sources = [
                    provenance,
                    "TopicSentimentAgent results",
                    "GPT-4o synthesis"
                ]
            
            # Build result
            agent_result = AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=confidence,
                confidence_level=confidence_level,
                limitations=limitations,
                sources=sources,
                execution_time=execution_time,
                token_count=token_count
            )
            
            self.logger.info(f"InsightAgent: Completed in {execution_time:.2f}s, "
                           f"confidence: {confidence:.2f}, tokens: ~{token_count}")
            
            return agent_result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"InsightAgent error: {e}")
            
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                limitations=["Insight synthesis failed"],
                sources=[],
                execution_time=execution_time,
                error_message=str(e)
            )
    
    def _parse_insights_response(self, response: str) -> Dict[str, Any]:
        """Parse OpenAI response into structured insights"""
        # For POC, return the raw response structured
        # Production implementation would parse into specific sections
        
        tags = self._extract_detection_method_tags_from_text(response)
        if getattr(self, 'workflow_type', 'standard') == 'topic_based' and not tags:
            self.logger.warning("LLM response missing detection method tags for topic-based workflow")
        
        return {
            'executive_summary': response[:500] if len(response) > 500 else response,
            'major_themes': self._extract_themes(response),
            'cross_category_patterns': [],
            'business_implications': response,
            'recommendations': self._extract_recommendations(response),
            'detection_method_tags': tags
        }

    def _extract_detection_method_tags_from_text(self, text: str) -> List[str]:
        """Identify detection method provenance tags emitted by the LLM."""
        if not text:
            return []
        tag_phrases = [
            "(Verified by AI Analysis)",
            "(Trend detected via keyword patterns)",
            "(Hybrid detection)",
            "(Hybrid detection: AI + Keywords)",
            "(Hybrid detection: AI + Keyword patterns)"
        ]
        detected: List[str] = []
        lowered = text.lower()
        for phrase in tag_phrases:
            if phrase.lower() in lowered:
                canonical = phrase
                if "hybrid detection" in phrase.lower():
                    canonical = "(Hybrid detection: AI + Keywords)"
                if canonical not in detected:
                    detected.append(canonical)
        return detected
    
    def _extract_themes(self, text: str) -> List[str]:
        """Extract major themes from synthesis"""
        # Simple extraction - look for numbered points or headers
        themes = []
        lines = text.split('\n')
        
        for line in lines:
            if line.strip().startswith(('1.', '2.', '3.', '4.', '-', '•')):
                themes.append(line.strip())
                if len(themes) >= 4:
                    break
        
        return themes
    
    def _extract_recommendations(self, text: str) -> List[str]:
        """Extract recommendations from synthesis"""
        # Look for recommendation sections
        recommendations = []
        
        if 'recommend' in text.lower():
            lines = text.split('\n')
            in_recommendations = False
            
            for line in lines:
                if 'recommend' in line.lower():
                    in_recommendations = True
                if in_recommendations and line.strip().startswith(('1.', '2.', '3.', '-', '•')):
                    recommendations.append(line.strip())
                    if len(recommendations) >= 5:
                        break
        
        return recommendations
    
    def _assess_synthesis_quality(self, insights: Dict[str, Any]) -> float:
        """Assess quality of synthesis"""
        quality = 1.0
        
        # Deduct if sections are missing or empty
        if not insights.get('executive_summary'):
            quality -= 0.3
        if not insights.get('major_themes') or len(insights['major_themes']) < 3:
            quality -= 0.2
        if not insights.get('recommendations') or len(insights['recommendations']) < 3:
            quality -= 0.2
        
        return max(0.0, quality)

    def _extract_detection_method_confidence(
        self,
        topic_distribution: Dict[str, Dict[str, Any]]
    ) -> Tuple[float, Dict[str, float]]:
        """
        Compute weighted detection confidence and method distribution percentages.
        """
        if not topic_distribution:
            return 0.0, {}
        
        method_keys = ['llm_smart', 'llm_only', 'hybrid', 'keyword', 'sdk_only', 'fallback']
        method_counts = {key: 0 for key in method_keys}
        total_volume = 0
        weighted_confidence = 0.0
        
        for stats in topic_distribution.values():
            volume = stats.get('volume', 0) or 0
            total_volume += volume
            confidence = stats.get('confidence', 0.7)
            if not isinstance(confidence, (int, float)):
                confidence = 0.7
            weighted_confidence += confidence * volume
            for key in method_keys:
                method_counts[key] += stats.get(f"{key}_count", 0) or 0
        
        # Second pass: ensure detection_method contributes even if per-method counts are missing
        for stats in topic_distribution.values():
            per_method_total = sum((stats.get(f"{key}_count", 0) or 0) for key in method_keys)
            detection_method = (stats.get('detection_method') or '').lower()
            if detection_method == 'attribute':
                detection_method = 'sdk_only'
            if per_method_total == 0 and detection_method in method_counts:
                method_counts[detection_method] += stats.get('volume', 0) or 0
        
        if total_volume <= 0:
            return 0.0, {}
        
        avg_confidence = weighted_confidence / total_volume if total_volume else 0.0
        total_method_count = sum(method_counts.values())
        
        if total_method_count == 0:
            return round(avg_confidence, 3), {}
        
        distribution = {
            key: round((count / total_method_count) * 100, 1)
            for key, count in method_counts.items()
            if total_method_count
        }
        return round(avg_confidence, 3), distribution

