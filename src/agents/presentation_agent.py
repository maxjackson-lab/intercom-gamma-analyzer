"""
PresentationAgent: Specialized in presentation generation and Gamma optimization.

Responsibilities:
- Generate executive-ready presentations
- Optimize for Gamma API
- Apply hallucination prevention to presentations
- Ensure insights over lists format
"""

import logging
import json
from typing import Dict, Any, List
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.services.gamma_generator import GammaGenerator
from src.config.gamma_prompts import GammaPrompts

logger = logging.getLogger(__name__)


class PresentationAgent(BaseAgent):
    """Agent specialized in presentation generation"""
    
    def __init__(self):
        super().__init__(
            name="PresentationAgent",
            model="gpt-4o",
            temperature=0.7  # Creative but controlled
        )
        self.gamma_generator = GammaGenerator()
    
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
        Execute presentation generation.
        
        Args:
            context: AgentContext with all previous agent results
            
        Returns:
            AgentResult with Gamma presentation
        """
        start_time = datetime.now()
        
        try:
            # Validate input
            self.validate_input(context)
            
            self.logger.info("PresentationAgent: Generating presentation")
            
            # Get insights from previous agent
            insight_data = context.previous_results['InsightAgent']['data']
            
            # Build presentation content using Gamma prompts
            presentation_style = "executive"  # TODO: Make configurable
            
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
            
            # Generate Gamma presentation
            gamma_result = await self.gamma_generator.generate(
                prompt=prompt,
                style=presentation_style,
                num_slides=10
            )
            
            # Prepare result
            result_data = {
                'presentation_content': prompt,
                'gamma_url': gamma_result.get('url'),
                'gamma_status': gamma_result.get('status'),
                'presentation_quality': self._assess_presentation_quality(prompt),
                'hallucination_check': self._check_for_hallucinations(prompt)
            }
            
            # Validate output
            self.validate_output(result_data)
            
            # Calculate confidence
            confidence, confidence_level = self.calculate_confidence(result_data, context)
            
            # Identify limitations
            limitations = []
            if result_data['hallucination_check']['potential_issues'] > 0:
                limitations.append(f"{result_data['hallucination_check']['potential_issues']} potential hallucination indicators found")
            
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
        
        return {
            'sentiment_distribution': sentiment_results.get('sentiment_distribution', {}),
            'average_confidence': sentiment_results.get('average_confidence', 0),
            'total_analyzed': sentiment_results.get('total_analyzed', 0)
        }
    
    def _extract_customer_quotes(self, context: AgentContext) -> List[Dict]:
        """Extract representative customer quotes"""
        # Placeholder - would extract actual quotes from conversations
        return [{
            'quote': 'Representative quote would be extracted from actual conversation data',
            'customer_name': 'Customer ID from data',
            'intercom_url': 'Only if explicitly provided in data'
        }]
    
    def _assess_presentation_quality(self, content: str) -> float:
        """Assess quality of generated presentation"""
        quality = 1.0
        
        # Deduct for list-heavy content (we want narrative)
        bullet_count = content.count('\n- ') + content.count('\n• ')
        if bullet_count > 20:
            quality -= 0.2
        
        # Deduct for missing key sections
        if 'executive summary' not in content.lower():
            quality -= 0.2
        if 'recommendation' not in content.lower():
            quality -= 0.2
        
        return max(0.0, quality)
    
    def _check_for_hallucinations(self, content: str) -> Dict[str, Any]:
        """Check for potential hallucination indicators"""
        potential_issues = 0
        issues = []
        
        # Check for invented URLs
        if 'https://app.intercom.com' in content and '[WORKSPACE_ID]' not in content:
            potential_issues += 1
            issues.append("Potential invented Intercom URL")
        
        # Check for ungrounded claims
        if 'according to' not in content.lower() and 'based on' not in content.lower():
            potential_issues += 1
            issues.append("Missing source attribution phrases")
        
        return {
            'potential_issues': potential_issues,
            'issues': issues,
            'passed': potential_issues == 0
        }

