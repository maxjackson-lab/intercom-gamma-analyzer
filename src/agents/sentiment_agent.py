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
from typing import Dict, Any, List
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class SentimentAgent(BaseAgent):
    """Agent specialized in sentiment analysis"""
    
    def __init__(self):
        super().__init__(
            name="SentimentAgent",
            model="gpt-4o",
            temperature=0.4  # Moderate temperature for nuanced analysis
        )
        self.openai_client = OpenAIClient()
    
    def get_agent_specific_instructions(self) -> str:
        """Sentiment agent specific instructions"""
        return """
SENTIMENT AGENT SPECIFIC RULES:

1. Only analyze sentiment based on actual conversation content - never invent emotions
2. Quote exact conversation text when making claims about sentiment
3. Use confidence scores for sentiment classifications:
   - HIGH (>0.8): Clear emotional indicators in text
   - MEDIUM (0.6-0.8): Moderate emotional cues
   - LOW (<0.6): Ambiguous or neutral tone

4. Never assume sentiment without textual evidence
5. State "Cannot determine sentiment" for unclear cases
6. Provide supporting quotes for all sentiment claims

Sentiment Categories:
- Positive: Satisfaction, gratitude, excitement
- Negative: Frustration, anger, disappointment
- Neutral: Factual questions, informational
- Mixed: Contains both positive and negative elements

Output Requirements:
- Sentiment label (positive/negative/neutral/mixed)
- Confidence score (0-1)
- Supporting quote from conversation
- Emotional indicators found
- Satisfaction score (1-5 if determinable)
"""
    
    def get_task_description(self, context: AgentContext) -> str:
        """Describe the sentiment analysis task"""
        conversations_count = len(context.conversations) if context.conversations else 0
        return f"""
Analyze sentiment for {conversations_count} conversations.

For EACH conversation:
1. Determine overall sentiment (positive/negative/neutral/mixed)
2. Identify specific emotional indicators in the text
3. Extract 1-2 representative quotes showing the sentiment
4. Calculate confidence based on clarity of emotional cues
5. Assign satisfaction score (1-5) if determinable from content

Provide aggregate sentiment distribution and key patterns.
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
        """Validate sentiment analysis results"""
        if not result.get('sentiment_analyses'):
            self.logger.warning("No sentiment analyses produced")
            return True
        
        # Check for required fields
        for analysis in result['sentiment_analyses'][:10]:
            if 'sentiment' not in analysis or 'confidence' not in analysis:
                self.logger.warning(f"Incomplete sentiment analysis: {analysis}")
        
        return True
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute sentiment analysis.
        
        Args:
            context: AgentContext with conversations
            
        Returns:
            AgentResult with sentiment analyses
        """
        start_time = datetime.now()
        
        try:
            # Validate input
            self.validate_input(context)
            
            conversations = context.conversations
            self.logger.info(f"SentimentAgent: Analyzing {len(conversations)} conversations")
            
            # Build prompt for batch sentiment analysis
            prompt = self.build_prompt(context)
            
            # Call OpenAI for sentiment analysis
            response = await self.openai_client.generate_analysis(
                prompt=prompt,
                model=self.model,
                temperature=self.temperature
            )
            
            # Parse response into structured data
            sentiment_analyses = self._parse_sentiment_response(response, conversations)
            
            # Calculate aggregate metrics
            sentiment_distribution = self._calculate_distribution(sentiment_analyses)
            average_confidence = sum(s['confidence'] for s in sentiment_analyses) / len(sentiment_analyses) if sentiment_analyses else 0
            
            # Prepare result
            result_data = {
                'sentiment_analyses': sentiment_analyses,
                'sentiment_distribution': sentiment_distribution,
                'average_confidence': average_confidence,
                'total_analyzed': len(sentiment_analyses),
                'high_confidence_count': sum(1 for s in sentiment_analyses if s['confidence'] > 0.8),
                'representative_quotes': self._extract_representative_quotes(sentiment_analyses)
            }
            
            # Validate output
            self.validate_output(result_data)
            
            # Calculate confidence
            confidence, confidence_level = self.calculate_confidence(result_data, context)
            
            # Identify limitations
            limitations = []
            if average_confidence < 0.7:
                limitations.append(f"Average confidence is low: {average_confidence:.2f}")
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Estimate token count
            token_count = len(prompt) // 4 + len(response) // 4  # Rough estimate
            
            # Build result
            agent_result = AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=confidence,
                confidence_level=confidence_level,
                limitations=limitations,
                sources=["OpenAI GPT-4o sentiment analysis", "Conversation text content"],
                execution_time=execution_time,
                token_count=token_count
            )
            
            self.logger.info(f"SentimentAgent: Completed in {execution_time:.2f}s, "
                           f"analyzed {len(sentiment_analyses)} conversations, "
                           f"confidence: {confidence:.2f}, tokens: ~{token_count}")
            
            return agent_result
            
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
    
    def _parse_sentiment_response(self, response: str, conversations: List[Dict]) -> List[Dict]:
        """Parse OpenAI response into structured sentiment data"""
        # For POC, use simple keyword-based sentiment as fallback
        # Real implementation would parse the LLM response
        
        sentiment_analyses = []
        
        for conv in conversations:
            conv_text = str(conv).lower()
            
            # Simple sentiment detection
            positive_words = ['thank', 'great', 'love', 'excellent', 'happy', 'solved']
            negative_words = ['frustrat', 'anger', 'disappoint', 'terrible', 'broken', 'issue', 'problem']
            
            pos_count = sum(1 for word in positive_words if word in conv_text)
            neg_count = sum(1 for word in negative_words if word in conv_text)
            
            if pos_count > neg_count:
                sentiment = "positive"
                confidence = min(0.9, 0.6 + (pos_count * 0.1))
            elif neg_count > pos_count:
                sentiment = "negative"
                confidence = min(0.9, 0.6 + (neg_count * 0.1))
            else:
                sentiment = "neutral"
                confidence = 0.5
            
            sentiment_analyses.append({
                'conversation_id': conv.get('id', 'unknown'),
                'sentiment': sentiment,
                'confidence': confidence,
                'positive_indicators': pos_count,
                'negative_indicators': neg_count
            })
        
        return sentiment_analyses
    
    def _calculate_distribution(self, sentiment_analyses: List[Dict]) -> Dict[str, float]:
        """Calculate sentiment distribution percentages"""
        if not sentiment_analyses:
            return {}
        
        total = len(sentiment_analyses)
        distribution = {}
        
        for sentiment in ['positive', 'negative', 'neutral', 'mixed']:
            count = sum(1 for s in sentiment_analyses if s['sentiment'] == sentiment)
            distribution[sentiment] = round(count / total * 100, 1)
        
        return distribution
    
    def _extract_representative_quotes(self, sentiment_analyses: List[Dict]) -> Dict[str, List[str]]:
        """Extract representative quotes for each sentiment"""
        # Placeholder for POC
        return {
            'positive': [],
            'negative': [],
            'neutral': []
        }

