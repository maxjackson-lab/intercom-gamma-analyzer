"""
Claude client for Anthropic API interactions.
"""

import anthropic
import logging
from typing import Dict, Any, Optional
import re

from src.config.settings import settings

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Client for Anthropic Claude API interactions."""
    
    def __init__(self, use_processor_model: bool = False):
        """
        Initialize Claude client.
        
        Args:
            use_processor_model: If True, use Haiku 4.5 (fast). If False, use Sonnet 4.5 (intensive).
        """
        self.api_key = settings.anthropic_api_key
        self.model = settings.anthropic_processor_model if use_processor_model else settings.anthropic_model
        self.max_tokens = settings.anthropic_max_tokens
        self.temperature = settings.anthropic_temperature
        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        self.logger = logging.getLogger(__name__)
        
        model_type = "Haiku 4.5 (processor)" if use_processor_model else "Sonnet 4.5 (intensive)"
        self.logger.info(f"ClaudeClient initialized with {model_type}: {self.model}")
    
    async def test_connection(self) -> bool:
        """Test connection to Claude API."""
        self.logger.info("Testing Claude API connection")
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}]
            )
            self.logger.info("Claude API connection successful")
            return True
        except Exception as e:
            self.logger.error(f"Claude API connection failed: {e}")
            raise
    
    async def analyze_sentiment_multilingual(
        self, 
        text: str, 
        language: str = None
    ) -> Dict[str, Any]:
        """
        Analyze sentiment using Claude for any language.
        
        Args:
            text: The customer feedback text to analyze
            language: Optional language hint (e.g., 'en', 'es', 'ja')
        
        Returns:
            Dictionary containing:
                - sentiment: 'positive', 'negative', or 'neutral'
                - confidence: Float between 0.0 and 1.0
                - analysis: Detailed explanation of sentiment
                - emotional_indicators: List of detected emotions
                - model: 'claude'
        
        Raises:
            Exception: If Claude API call fails
        """
        self.logger.info(f"Analyzing sentiment with Claude (language: {language})")
        
        try:
            language_context = f" (Language: {language})" if language else ""
            
            prompt = f"""
            Analyze the sentiment of this customer feedback{language_context}:
            
            {text}
            
            Provide:
            - Overall sentiment (positive, negative, neutral)
            - Confidence score (0-1)
            - Key emotional indicators
            - Brief explanation of your analysis
            
            Consider cultural context and language nuances.
            """
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            analysis_text = response.content[0].text
            
            # Parse response (similar to OpenAI)
            sentiment = self._parse_sentiment(analysis_text)
            confidence = self._extract_confidence_score(analysis_text)
            emotional_indicators = self._extract_emotional_indicators(analysis_text)
            
            self.logger.debug(f"Claude analysis: {sentiment} (confidence: {confidence})")
            
            return {
                "sentiment": sentiment,
                "confidence": confidence,
                "analysis": analysis_text,
                "emotional_indicators": emotional_indicators,
                "language": language,
                "model": "claude"
            }
            
        except Exception as e:
            self.logger.error(f"Claude sentiment analysis failed: {e}")
            raise
    
    def _parse_sentiment(self, analysis_text: str) -> str:
        """Parse sentiment from Claude response."""
        text_lower = analysis_text.lower()
        
        # More sophisticated parsing
        if any(word in text_lower for word in ['positive', 'good', 'satisfied', 'happy', 'pleased', 'excellent']):
            return 'positive'
        elif any(word in text_lower for word in ['negative', 'bad', 'dissatisfied', 'unhappy', 'frustrated', 'angry', 'disappointed']):
            return 'negative'
        else:
            return 'neutral'
    
    def _extract_confidence_score(self, analysis_text: str) -> float:
        """Extract confidence score from Claude response."""
        # Look for confidence scores in the text
        confidence_match = re.search(r'confidence[:\s]*(\d+\.?\d*)', analysis_text.lower())
        if confidence_match:
            return float(confidence_match.group(1))
        
        # Default confidence based on sentiment strength indicators
        if 'very' in analysis_text.lower() or 'extremely' in analysis_text.lower():
            return 0.9
        elif 'somewhat' in analysis_text.lower() or 'slightly' in analysis_text.lower():
            return 0.6
        else:
            return 0.8
    
    def _extract_emotional_indicators(self, analysis_text: str) -> list:
        """Extract emotional indicators from Claude response."""
        # Simple extraction - look for emotional words
        emotional_words = []
        text_lower = analysis_text.lower()
        
        emotions = [
            'grateful', 'satisfied', 'pleased', 'happy', 'excited', 'enthusiastic',
            'frustrated', 'disappointed', 'angry', 'worried', 'concerned', 'upset',
            'curious', 'polite', 'neutral', 'professional', 'inquisitive'
        ]
        
        for emotion in emotions:
            if emotion in text_lower:
                emotional_words.append(emotion)
        
        return emotional_words[:3]  # Return top 3 emotions
