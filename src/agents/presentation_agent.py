"""
PresentationAgent: Specialized in presentation generation and Gamma optimization.

Responsibilities:
- Generate executive-ready presentations
- Optimize for Gamma API
- Apply hallucination prevention to presentations
- Ensure insights over lists format
"""

import asyncio
import logging
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.services.gamma_generator import GammaGenerator
from src.config.gamma_prompts import GammaPrompts
from src.config.settings import settings
from src.services.presentation_builder import PresentationBuilder
from src.utils.ai_client_helper import get_ai_client, get_recommended_semaphore

logger = logging.getLogger(__name__)


class PresentationAgent(BaseAgent):
    """
    Agent specialized in presentation generation.

    Note:
        `result_data['presentation_quality']` is a structured dictionary that
        contains per-dimension scoring plus qualitative feedback. Downstream
        consumers must no longer expect a scalar quality score.
    """
    
    def __init__(self, ai_client: Optional[Any] = None):
        super().__init__(
            name="PresentationAgent",
            temperature=0.7  # Creative but controlled
        )
        self.gamma_generator = GammaGenerator()
        self.presentation_builder = PresentationBuilder()
        self.ai_client = ai_client or get_ai_client()

        from src.services.claude_client import ClaudeClient

        if isinstance(self.ai_client, ClaudeClient):
            self.client_type = "claude"
            self.quality_model = settings.anthropic_model
        else:
            self.client_type = "openai"
            self.quality_model = settings.openai_model

        self.llm_semaphore = get_recommended_semaphore(self.ai_client)
        self.llm_timeout = getattr(settings, "presentation_quality_timeout", settings.llm_timeout_default)
        self.quality_assessment_temperature = 0.2
    
    def get_agent_specific_instructions(self) -> str:
        """Presentation agent specific instructions"""
        return """
PRESENTATION AGENT SPECIFIC RULES:

1. Only use insights from previous agents - never invent new insights
2. Use "According to the analysis" for all claims
3. Never invent URLs, conversation links, or external references
4. DO NOT create placeholder links like "https://app.intercom.com/..." unless provided
5. State limitations when data is incomplete

Presentation Quality Requirements:
- Lead with insights, not raw data
- Use narrative synthesis (minimize bullet points)
- Data-driven analyst tone (not melodramatic)
- 3-4 major themes maximum (not exhaustive catalogs)
- Include 1-2 representative examples per theme (not all examples)

CRITICAL CONTEXT FOR SUPPORT DATA:
- Support tickets are NORMAL business operations
- Customers contact support BECAUSE they have issues (this is expected)
- Negative sentiment in support does NOT mean product failure
- Focus on: Resolution efficiency, trend changes, escalation patterns
- NOT: "Customers are frustrated and upset" (obvious, not actionable)
- YES: "Billing resolution time increased 23% vs last month" (actionable trend)
- NOT: "98% negative sentiment" (meaningless - it's support!)
- YES: "First Contact Resolution dropped from 67% to 54%" (actionable)

What Actually Matters:
- Resolution quality and speed
- Escalation rate changes
- New vs recurring issues
- Category volume changes over time
- Patterns that indicate churn risk
- NPS/CSAT correlation (if available)

Hallucination Prevention for Presentations:
- Every claim must trace back to previous agent outputs
- No invented statistics or percentages
- No fabricated customer quotes
- No external sources unless explicitly provided
- Use confidence levels to qualify uncertain insights

From Claude's research - apply these patterns:
- Data-driven operational analysis (not emotional storytelling)
- "Here's what's changing" framing (not "here's what's broken")
- Focus on efficiency metrics (resolution time, escalation rate, FCR)
- Compare to baselines when available
"""
    
    def get_task_description(self, context: AgentContext) -> str:
        """Describe the presentation generation task"""
        return f"""
Generate an executive presentation from the synthesized insights.

Target: C-level executives and decision makers
Style: Professional Casualism (warm but authoritative)
Length: 8-12 slides
Format: Gamma-optimized markdown

Required sections:
1. Executive Summary (key insights, why they matter)
2. Major Themes (3-4 themes synthesized from data)
3. Business Implications (strategic significance)
4. Recommendations (specific, actionable next steps)

Use insights from previous agents. Focus on narrative synthesis, not data dumps.
"""
    
    def format_context_data(self, context: AgentContext) -> str:
        """Format previous agent results for presentation"""
        insight_results = context.previous_results.get('InsightAgent', {}).get('data', {})
        category_results = context.previous_results.get('CategoryAgent', {}).get('data', {})
        sentiment_results = context.previous_results.get('SentimentAgent', {}).get('data', {})
        
        return f"""
SYNTHESIZED INSIGHTS:
{json.dumps(insight_results, indent=2, default=str)}

CATEGORY DISTRIBUTION:
{json.dumps(category_results.get('category_distribution', {}), indent=2)}

SENTIMENT DISTRIBUTION:
{json.dumps(sentiment_results.get('sentiment_distribution', {}), indent=2)}

DATE RANGE: {context.start_date.strftime('%Y-%m-%d')} to {context.end_date.strftime('%Y-%m-%d')}
TOTAL CONVERSATIONS: {len(context.conversations) if context.conversations else 0}

Use ONLY this data for the presentation. All claims must be grounded in these results.
"""
    
    def validate_input(self, context: AgentContext) -> bool:
        """Validate that we have insights to present"""
        if not context.previous_results:
            raise ValueError("No previous agent results provided")
        
        if 'InsightAgent' not in context.previous_results:
            raise ValueError("InsightAgent results required for presentation")
        
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate presentation output"""
        if 'presentation_content' not in result:
            self.logger.warning("No presentation content generated")
            return False
        
        # Check for hallucination indicators
        content = result['presentation_content']
        if 'https://app.intercom.com' in content and '[WORKSPACE_ID]' not in content:
            # Check if we actually provided valid Intercom URLs
            self.logger.warning("Presentation may contain invented Intercom URLs")
        
        return True
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute presentation generation and quality assessment.
        
        Args:
            context: AgentContext with all previous agent results
            
        Returns:
            AgentResult with Gamma presentation content, Gamma metadata, and a
            structured `presentation_quality` dict containing the per-dimension
            quality assessment scores plus qualitative feedback fields.
        """
        start_time = datetime.now()
        
        try:
            # Validate input
            self.validate_input(context)
            
            self.logger.info("PresentationAgent: Generating presentation")
            
            # Get insights from previous agent
            insight_data = context.previous_results['InsightAgent']['data']

            # Get presentation style from metadata with fallback to settings
            presentation_style = context.metadata.get('gamma_style', 'executive')
            if hasattr(settings, 'default_gamma_style'):
                presentation_style = context.metadata.get('gamma_style', settings.default_gamma_style)

            chart_data = self._extract_chart_data(context)
            if chart_data:
                self.logger.info(
                    "PresentationAgent: Prepared chart data for Gamma instructions",
                    has_category_chart='category_chart' in chart_data,
                    has_sentiment_chart='sentiment_chart' in chart_data
                )
            else:
                self.logger.info("PresentationAgent: No chart data available for presentation")
            
            # Use existing Gamma prompt builder with insights
            prompt = GammaPrompts.build_executive_presentation_prompt(
                start_date=context.start_date.strftime('%Y-%m-%d'),
                end_date=context.end_date.strftime('%Y-%m-%d'),
                conversation_count=len(context.conversations) if context.conversations else 0,
                top_issues=self._format_top_issues(context),
                key_metrics=self._extract_key_metrics(context),
                customer_quotes=self._extract_customer_quotes(context),
                recommendations=insight_data.get('recommendations', [])
            )

            additional_instructions = GammaPrompts.get_additional_instructions_for_style(
                presentation_style,
                chart_data=chart_data
            )
            
            # Generate Gamma presentation using markdown method
            # The prompt is already formatted markdown, so use generate_from_markdown
            gamma_result = await self.gamma_generator.generate_from_markdown(
                input_text=prompt,
                theme_name="Night Sky",  # Professional dark theme (automatically resolved to themeId)
                additional_instructions=additional_instructions
            )

            presentation_quality = await self._assess_presentation_quality(prompt, context)

            # Prepare result (presentation_quality includes scores for
            # overall_score, narrative_flow_score, insight_depth_score,
            # data_grounding_score, executive_appeal_score plus strengths,
            # weaknesses, and improvement_suggestions)
            result_data = {
                'presentation_content': prompt,
                'gamma_url': gamma_result.get('gamma_url'),
                'gamma_status': 'completed' if gamma_result.get('gamma_url') else 'pending',
                'generation_id': gamma_result.get('generation_id'),
                'presentation_quality': presentation_quality,
                'hallucination_check': self._check_for_hallucinations(prompt)
            }
            
            # Validate output
            self.validate_output(result_data)
            
            # Calculate confidence
            confidence, confidence_level = self.calculate_confidence(result_data, context)
            
            # Identify limitations
            limitations = []
            hallucination_issues = result_data['hallucination_check']['potential_issues']
            if hallucination_issues > 0:
                limitations.append(f"{hallucination_issues} potential hallucination indicators found")

            assessment_status = presentation_quality.get('assessment_status')
            if assessment_status != "ok":
                limitations.append(
                    "Presentation quality assessment unavailable; fallback scores used"
                )
            else:
                quality_score = presentation_quality.get('overall_score')
                if quality_score is not None and quality_score < 0.7:
                    suggestions = presentation_quality.get('improvement_suggestions') or []
                    if suggestions:
                        limitations.extend(
                            [f"Quality improvement: {suggestion}" for suggestion in suggestions[:3]]
                        )
                    else:
                        limitations.append("Presentation quality assessment flagged low confidence (<0.70)")
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Estimate token count
            token_count = len(prompt) // 4
            
            # Build result
            agent_result = AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=confidence,
                confidence_level=confidence_level,
                limitations=limitations,
                sources=["InsightAgent synthesis", "Gamma API"],
                execution_time=execution_time,
                token_count=token_count
            )
            
            self.logger.info(f"PresentationAgent: Completed in {execution_time:.2f}s, "
                           f"confidence: {confidence:.2f}, Gamma URL: {gamma_result.get('url', 'N/A')}")
            
            return agent_result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"PresentationAgent error: {e}")
            
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                limitations=["Presentation generation failed"],
                sources=[],
                execution_time=execution_time,
                error_message=str(e)
            )
    
    def _format_top_issues(self, context: AgentContext) -> List[Dict]:
        """Format top issues from category results"""
        category_results = context.previous_results.get('CategoryAgent', {}).get('data', {})
        distribution = category_results.get('category_distribution', {})
        
        total = sum(distribution.values()) if distribution else 1
        
        top_issues = []
        for category, count in sorted(distribution.items(), key=lambda x: x[1], reverse=True)[:5]:
            top_issues.append({
                'name': category,
                'count': count,
                'percentage': round(count / total * 100, 1)
            })
        
        return top_issues
    
    def _extract_key_metrics(self, context: AgentContext) -> Dict[str, Any]:
        """Extract key metrics from previous results"""
        sentiment_results = context.previous_results.get('SentimentAgent', {}).get('data', {})
        
        # Calculate derived metrics
        escalation_rate = self._calculate_escalation_rate(context)
        sentiment_trend = self._calculate_sentiment_trend(context)
        
        return {
            'sentiment_distribution': sentiment_results.get('sentiment_distribution', {}),
            'average_confidence': sentiment_results.get('average_confidence', 0),
            'total_analyzed': sentiment_results.get('total_analyzed', 0),
            'escalation_rate': escalation_rate,
            'sentiment_trend': sentiment_trend,
            # ROI metrics (placeholders for now, but explicit to avoid random hardcoded values)
            'estimated_cost_impact': 'Calculated in detailed report',
            'cost_reduction_potential': '10-15% (estimated)',
            'satisfaction_improvement': '5-10% (projected)',
            'efficiency_gains': '15-20% (projected)',
            'revenue_protection': 'TBD'
        }

    def _calculate_escalation_rate(self, context: AgentContext) -> float:
        """Calculate escalation rate based on conversation tags and content."""
        conversations = context.conversations or []
        if not conversations:
            return 0.0
            
        escalated_count = 0
        for conv in conversations:
            is_escalated = False
            
            # Check tags
            tags = conv.get('tags', {}).get('tags', [])
            tag_names = [t.get('name', '').lower() if isinstance(t, dict) else str(t).lower() for t in tags]
            
            if any('escalat' in t or 'tier 2' in t or 'manager' in t for t in tag_names):
                is_escalated = True
            
            # Check category if available
            if not is_escalated:
                category_results = context.previous_results.get('CategoryAgent', {}).get('data', {})
                classifications = category_results.get('classifications', [])
                # Find classification for this conv
                classification = next((c for c in classifications if c.get('conversation_id') == conv.get('id')), None)
                if classification:
                    cat = classification.get('primary_category', '').lower()
                    sub = classification.get('subcategory', '').lower()
                    if 'escalat' in cat or 'escalat' in sub:
                        is_escalated = True
            
            if is_escalated:
                escalated_count += 1
                
        return round((escalated_count / len(conversations)) * 100, 1)

    def _calculate_sentiment_trend(self, context: AgentContext) -> str:
        """Calculate sentiment trend by comparing first half vs second half of period."""
        conversations = context.conversations or []
        if len(conversations) < 10:
            return "insufficient data for trend"
            
        # Sort by date
        sorted_convs = sorted(conversations, key=lambda c: c.get('created_at', 0))
        midpoint = len(sorted_convs) // 2
        
        first_half = sorted_convs[:midpoint]
        second_half = sorted_convs[midpoint:]
        
        # Helper to get positive %
        def get_positive_rate(convs):
            sentiment_results = context.previous_results.get('SentimentAgent', {}).get('data', {})
            analyses = sentiment_results.get('sentiment_analyses', [])
            conv_ids = set(c.get('id') for c in convs)
            
            positive_count = sum(1 for a in analyses if a.get('conversation_id') in conv_ids and a.get('sentiment') == 'positive')
            return (positive_count / len(convs)) * 100 if convs else 0
            
        first_rate = get_positive_rate(first_half)
        second_rate = get_positive_rate(second_half)
        
        diff = second_rate - first_rate
        
        if diff > 5:
            return "improving positive sentiment"
        elif diff < -5:
            return "declining positive sentiment"
        else:
            return "stable sentiment"

    def _extract_chart_data(self, context: AgentContext) -> Optional[Dict[str, Any]]:
        """Extract and format chart data for Gamma additional instructions."""
        try:
            category_results = context.previous_results.get('CategoryAgent', {}).get('data', {}) or {}
            sentiment_results = context.previous_results.get('SentimentAgent', {}).get('data', {}) or {}

            category_distribution = category_results.get('category_distribution')
            if not isinstance(category_distribution, dict):
                category_distribution = {}

            sentiment_distribution = sentiment_results.get('sentiment_distribution')
            if not isinstance(sentiment_distribution, dict):
                sentiment_distribution = {}

            chart_data: Dict[str, Any] = {}

            if category_distribution:
                sorted_categories = sorted(
                    category_distribution.items(),
                    key=lambda item: item[1],
                    reverse=True
                )
                category_labels = [str(name) for name, _ in sorted_categories]
                category_values = [int(value) for _, value in sorted_categories]

                if category_labels and any(value > 0 for value in category_values):
                    chart_data['category_chart'] = {
                        'type': 'bar',
                        'title': 'Support Volume by Category',
                        'labels': category_labels,
                        'values': category_values
                    }

            if sentiment_distribution:
                sorted_sentiment = sorted(sentiment_distribution.items(), key=lambda item: item[0])
                sentiment_labels = [str(name) for name, _ in sorted_sentiment]
                sentiment_values = [int(value) for _, value in sorted_sentiment]

                if sentiment_labels and any(value > 0 for value in sentiment_values):
                    chart_data['sentiment_chart'] = {
                        'type': 'pie',
                        'title': 'Sentiment Distribution',
                        'labels': sentiment_labels,
                        'values': sentiment_values
                    }

            return chart_data or None

        except Exception as exc:
            self.logger.warning("PresentationAgent: Failed to extract chart data: %s", exc, exc_info=True)
            return None
    
    def _extract_customer_quotes(self, context: AgentContext) -> List[Dict]:
        """Extract representative customer quotes using stratified sampling."""
        conversations = context.conversations or []
        if not conversations:
            self.logger.warning("PresentationAgent: No conversations available for quote extraction")
            return []
        
        category_results = context.previous_results.get('CategoryAgent', {}).get('data', {}) or {}
        
        try:
            quotes = self.presentation_builder.extract_customer_quotes(
                conversations=conversations,
                category_results=category_results if category_results else None,
                max_quotes_per_category=3,
                min_quotes_per_category=1
            )
        except Exception as exc:
            self.logger.warning("PresentationAgent: Quote extraction failed: %s", exc)
            return []
        
        if not quotes:
            self.logger.warning("PresentationAgent: Quote extraction produced no results")
            return []
        
        self.logger.info("PresentationAgent: Extracted %d customer quotes", len(quotes))
        return quotes
    
    async def _assess_presentation_quality(
        self,
        content: str,
        context: AgentContext
    ) -> Dict[str, Any]:
        """Assess presentation quality using LLM-derived evaluation."""
        if not self.ai_client:
            return self._quality_assessment_fallback(
                "Quality assessment skipped: no AI client configured."
            )
        
        prompt = self._build_quality_assessment_prompt(content, context)
        
        try:
            async with self.llm_semaphore:
                system_instructions = self.get_agent_specific_instructions()
                max_quality_tokens = 1200
                if self.client_type == "claude":
                    response = await asyncio.wait_for(
                        self.ai_client.client.messages.create(
                            model=self.quality_model,
                            max_tokens=max_quality_tokens,
                            temperature=self.quality_assessment_temperature,
                            system=system_instructions,
                            messages=[{"role": "user", "content": prompt}]
                        ),
                        timeout=self.llm_timeout
                    )
                    response_text = response.content[0].text if response and response.content else ""
                else:
                    response = await asyncio.wait_for(
                        self.ai_client.client.chat.completions.create(
                            model=self.quality_model,
                            messages=[
                                {"role": "system", "content": system_instructions},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=self.quality_assessment_temperature,
                            max_tokens=max_quality_tokens
                        ),
                        timeout=self.llm_timeout
                    )
                    response_text = (
                        response.choices[0].message.content
                        if response and getattr(response, "choices", None)
                        else ""
                    )
            
            if not response_text:
                return self._quality_assessment_fallback(
                    "Quality assessment returned an empty response."
                )
            
            return self._parse_quality_assessment_response(response_text)
        
        except asyncio.TimeoutError:
            self.logger.warning(
                "PresentationAgent: Quality assessment timed out after %ss",
                self.llm_timeout
            )
            return self._quality_assessment_fallback(
                "Quality assessment timed out; please review manually."
            )
        except Exception as exc:
            self.logger.warning(
                "PresentationAgent: Quality assessment failed: %s",
                exc,
                exc_info=True
            )
            return self._quality_assessment_fallback(
                f"Quality assessment unavailable: {exc}"
            )
    
    def _build_quality_assessment_prompt(self, content: str, context: AgentContext) -> str:
        """Build prompt instructing the LLM to evaluate presentation quality."""
        conversations = len(context.conversations) if context.conversations else 0
        gamma_style = (context.metadata or {}).get('gamma_style', 'executive')
        truncated_content = content[:2000]
        agent_instructions = self.get_agent_specific_instructions().strip()
        
        return f"""You are auditing a Gamma presentation created for Intercom analysis.

ANALYSIS CONTEXT:
- Analysis ID: {context.analysis_id}
- Analysis Type: {context.analysis_type}
- Date Range: {context.start_date.strftime('%Y-%m-%d')} to {context.end_date.strftime('%Y-%m-%d')}
- Conversations Reviewed: {conversations}
- Presentation Style: {gamma_style}

AGENT INSTRUCTIONS (for reference, do NOT repeat verbatim):
{agent_instructions}

EVALUATION CRITERIA:
1. Narrative Flow – Coherent storytelling with smooth transitions.
2. Insight Depth – Specific, actionable insights grounded in the data.
3. Data Grounding – Every claim backed by provided analysis (no hallucinations).
4. Executive Appeal – Tone that resonates with C-level leaders and emphasizes business impact.

TASK:
Review the presentation excerpt below and score each dimension from 0 to 1 (higher is better). Provide structured feedback.

Return JSON ONLY in this shape:
{{
  "overall_score": float,
  "narrative_flow_score": float,
  "insight_depth_score": float,
  "data_grounding_score": float,
  "executive_appeal_score": float,
  "strengths": ["string"],
  "weaknesses": ["string"],
  "improvement_suggestions": ["string"]
}}

PRESENTATION CONTENT (truncated to 2000 characters):
<<<CONTENT_START>>>
{truncated_content}
<<<CONTENT_END>>>"""
    
    def _parse_quality_assessment_response(self, response_text: str) -> Dict[str, Any]:
        """Parse structured response from the LLM quality assessment."""
        try:
            json_match = re.search(r'\{.*?\}', response_text, re.DOTALL)
            raw_json = json_match.group(0) if json_match else response_text
            try:
                data = json.loads(raw_json)
            except json.JSONDecodeError:
                data = json.loads(response_text)
        except Exception as exc:
            self.logger.warning(
                "PresentationAgent: Failed to parse quality assessment response: %s",
                exc
            )
            return self._quality_assessment_fallback(
                "Quality assessment parsing failed; manual review recommended."
            )
        
        return {
            'overall_score': self._clamp_score(data.get('overall_score')),
            'narrative_flow_score': self._clamp_score(data.get('narrative_flow_score')),
            'insight_depth_score': self._clamp_score(data.get('insight_depth_score')),
            'data_grounding_score': self._clamp_score(data.get('data_grounding_score')),
            'executive_appeal_score': self._clamp_score(data.get('executive_appeal_score')),
            'strengths': self._normalize_string_list(data.get('strengths')),
            'weaknesses': self._normalize_string_list(data.get('weaknesses')),
            'improvement_suggestions': self._normalize_string_list(data.get('improvement_suggestions')),
            'assessment_status': 'ok'
        }
    
    def _quality_assessment_fallback(self, message: str) -> Dict[str, Any]:
        """Return default quality assessment structure when LLM evaluation fails."""
        fallback = {
            'overall_score': 0.5,
            'narrative_flow_score': 0.5,
            'insight_depth_score': 0.5,
            'data_grounding_score': 0.5,
            'executive_appeal_score': 0.5,
            'strengths': [],
            'weaknesses': [],
            'improvement_suggestions': [],
            'assessment_status': 'fallback'
        }
        if message:
            fallback['improvement_suggestions'] = [message]
        return fallback
    
    def _clamp_score(self, value: Any) -> float:
        """Ensure scores stay within [0, 1]."""
        try:
            score = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, score))
    
    def _normalize_string_list(self, value: Any) -> List[str]:
        """Normalize string or list inputs into a clean list of strings."""
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []
    
    def _check_for_hallucinations(self, content: str) -> Dict[str, Any]:
        """Check for potential hallucination indicators"""
        potential_issues = 0
        issues = []
        
        # Check for invented URLs
        if 'https://app.intercom.com' in content and '[WORKSPACE_ID]' not in content:
            potential_issues += 1
            issues.append("Potential invented Intercom URL")
        
        # Check for ungrounded claims, but allow legitimate sentiment insights
        if not self._is_sentiment_insight(content):
            if 'according to' not in content.lower() and 'based on' not in content.lower():
                # Also check for other common attribution patterns in sentiment insights
                if not any(p in content.lower() for p in ['users', 'customers', 'appreciate', 'frustrated', 'love', 'hate']):
                    potential_issues += 1
                    issues.append("Missing source attribution phrases")
        
        return {
            'potential_issues': potential_issues,
            'issues': issues,
            'passed': potential_issues == 0
        }

    def _is_sentiment_insight(self, text: str) -> bool:
        """
        Detect if text looks like a legitimate sentiment insight.
        
        Hilary-style insights use specific nuance connectors and emotional language.
        We shouldn't flag these as hallucinations even if they lack "according to".
        """
        # Nuance connectors
        nuance_connectors = ['but', 'however', 'although', 'while', 'despite']
        has_connector = any(f" {c} " in text.lower() for c in nuance_connectors)
        
        # Emotional language (whitelist)
        sentiment_words = [
            'love', 'hate', 'frustrated', 'confused', 'happy', 'appreciate', 
            'difficult', 'easy', 'painful', 'smooth', 'rad', 'annoying'
        ]
        has_sentiment = any(w in text.lower() for w in sentiment_words)
        
        # Subject identifiers
        subjects = ['users', 'customers', 'clients', 'people', 'they']
        has_subject = any(s in text.lower() for s in subjects)
        
        return has_connector and has_sentiment and has_subject

