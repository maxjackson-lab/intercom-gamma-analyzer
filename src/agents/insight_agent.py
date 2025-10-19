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
from typing import Dict, Any, List
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class InsightAgent(BaseAgent):
    """Agent specialized in insight synthesis"""
    
    def __init__(self):
        super().__init__(
            name="InsightAgent",
            model="gpt-4o",
            temperature=0.7  # Higher temperature for creative synthesis
        )
        self.openai_client = OpenAIClient()
    
    def get_agent_specific_instructions(self) -> str:
        """Insight agent specific instructions"""
        return """
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

Output Structure:
1. Executive Summary (2-3 key insights)
2. Major Themes (3-4 themes with evidence)
3. Cross-Category Patterns (what connects seemingly different issues)
4. Business Implications (why this matters)
5. Recommendations (specific, actionable next steps)

Tone: Professional Casualism
- Formal but not stiff
- Lead with insight, not information
- Use "Here's what this means" language
- Avoid bullet points - synthesize into flowing narrative
"""
    
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
    
    def validate_input(self, context: AgentContext) -> bool:
        """Validate that we have previous agent results"""
        if not context.previous_results:
            raise ValueError("No previous agent results provided")
        
        if 'CategoryAgent' not in context.previous_results:
            raise ValueError("CategoryAgent results required")
        
        if 'SentimentAgent' not in context.previous_results:
            raise ValueError("SentimentAgent results required")
        
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate insight synthesis results"""
        required_fields = ['executive_summary', 'major_themes', 'recommendations']
        
        for field in required_fields:
            if field not in result:
                self.logger.warning(f"Missing field '{field}' in insights")
        
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
            
            # Build synthesis prompt
            prompt = self.build_prompt(context)
            
            # Call OpenAI for insight synthesis
            response = await self.openai_client.generate_analysis(
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
                'synthesis_quality': self._assess_synthesis_quality(insights)
            }
            
            # Validate output
            self.validate_output(result_data)
            
            # Calculate confidence
            confidence, confidence_level = self.calculate_confidence(result_data, context)
            
            # Identify limitations
            limitations = []
            if result_data['synthesis_quality'] < 0.7:
                limitations.append("Synthesis quality below threshold - limited insight depth")
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Estimate token count
            token_count = len(prompt) // 4 + len(response) // 4
            
            # Build result
            agent_result = AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=confidence,
                confidence_level=confidence_level,
                limitations=limitations,
                sources=["CategoryAgent results", "SentimentAgent results", "GPT-4o synthesis"],
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
        
        return {
            'executive_summary': response[:500] if len(response) > 500 else response,
            'major_themes': self._extract_themes(response),
            'cross_category_patterns': [],
            'business_implications': response,
            'recommendations': self._extract_recommendations(response)
        }
    
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

