"""
OpenAI client for generating AI-powered insights.
"""

import logging
from typing import Dict, List, Any, Optional
import openai
from openai import AsyncOpenAI

from src.config.settings import settings

logger = logging.getLogger(__name__)


class ProviderUnavailableError(Exception):
    """Raised when LLM provider is unavailable (circuit breaker open)"""
    pass


class OpenAIClient:
    """Client for OpenAI API interactions."""
    
    def __init__(self):
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model
        self.temperature = settings.openai_temperature
        self.max_tokens = settings.openai_max_tokens
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.logger = logging.getLogger(__name__)
        
        # Initialize circuit breaker for resilience
        from src.utils.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
        self.circuit_breaker = CircuitBreaker(
            name="openai_api",
            config=CircuitBreakerConfig(
                failure_threshold=5,
                timeout_seconds=60,
                expected_exceptions=(Exception,)
            )
        )
    
    async def test_connection(self) -> bool:
        """Test connection to OpenAI API."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Hello, this is a test message."}
                ],
                max_tokens=10,
                temperature=0
            )
            
            self.logger.info("OpenAI API connection successful")
            return True
            
        except Exception as e:
            self.logger.error(f"OpenAI API connection failed: {e}")
            raise
    
    async def generate_analysis(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **_: Any
    ) -> str:
        """
        Generate analysis using OpenAI with retry + timeout.
        
        Per OpenAI docs: https://platform.openai.com/docs/guides/rate-limits
        Implements exponential backoff retry for production reliability.
        """
        try:
            self.logger.info("Generating AI analysis")
            
            # RETRY WITH EXPONENTIAL BACKOFF (per OpenAI docs)
            from tenacity import retry, wait_random_exponential, stop_after_attempt, retry_if_exception_type
            import asyncio
            
            # Wrap API call with circuit breaker
            from src.utils.circuit_breaker import CircuitBreakerOpenError
            
            async def _make_api_call():
                @retry(
                    wait=wait_random_exponential(min=1, max=60),
                    stop=stop_after_attempt(6),
                    retry=retry_if_exception_type((Exception,)),
                    reraise=True
                )
                async def _call_with_retry():
                    return await self.client.chat.completions.create(
                        model=model or self.model,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an expert data analyst specializing in customer support analytics. You provide clear, actionable insights based on conversation data."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        max_tokens=self.max_tokens,
                        temperature=temperature if temperature is not None else self.temperature
                    )
                
                # Execute with configurable timeout from settings
                return await asyncio.wait_for(_call_with_retry(), timeout=settings.llm_client_timeout)
            
            # Call through circuit breaker
            try:
                response = await self.circuit_breaker.call_async(_make_api_call)
            except CircuitBreakerOpenError as e:
                self.logger.error(f"OpenAI API circuit breaker is open: {e}")
                raise ProviderUnavailableError("OpenAI API circuit breaker is open - service temporarily unavailable") from e
            
            analysis = response.choices[0].message.content
            self.logger.info("AI analysis generated successfully")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Failed to generate AI analysis: {e}")
            raise
    
    async def generate_summary(self, data: str) -> str:
        """Generate a summary of the data."""
        try:
            prompt = f"""
            Please provide a concise summary of the following customer support data:
            
            {data}
            
            Focus on:
            - Key statistics and metrics
            - Notable trends or patterns
            - Important insights for business decision-making
            
            Keep the summary under 500 words and make it executive-friendly.
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a business analyst who creates concise, executive-friendly summaries of customer support data."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.1
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Failed to generate summary: {e}")
            raise
    
    async def extract_insights(self, data: str, focus_areas: List[str]) -> Dict[str, str]:
        """Extract specific insights based on focus areas."""
        try:
            insights = {}
            
            for area in focus_areas:
                prompt = f"""
                Analyze the following customer support data with a focus on {area}:
                
                {data}
                
                Provide insights about:
                - Key trends related to {area}
                - Performance metrics
                - Areas for improvement
                - Recommendations
                
                Keep the analysis focused and actionable.
                """
                
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": f"You are a customer support analyst specializing in {area} analysis."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    max_tokens=800,
                    temperature=0.1
                )
                
                insights[area] = response.choices[0].message.content
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Failed to extract insights: {e}")
            raise
    
    async def generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on metrics."""
        try:
            prompt = f"""
            Based on the following customer support metrics, provide 5-7 actionable recommendations:
            
            {metrics}
            
            Focus on:
            - Improving customer satisfaction
            - Reducing response times
            - Increasing efficiency
            - Addressing common issues
            
            Make recommendations specific and implementable.
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a customer support operations expert who provides practical, actionable recommendations for improving support performance."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.2
            )
            
            # Parse recommendations from response
            recommendations_text = response.choices[0].message.content
            recommendations = [
                rec.strip() for rec in recommendations_text.split('\n')
                if rec.strip() and not rec.strip().startswith('#')
            ]
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to generate recommendations: {e}")
            raise
    
    async def analyze_sentiment(
        self,
        text: str,
        language: Optional[str] = None,
        model: Optional[str] = None,
        fallback: bool = False,
        **_: Any
    ) -> Dict[str, Any]:
        """
        Analyze sentiment of customer feedback (legacy compatibility helper).
        
        Accepts the newer factory signature but simply forwards to the multilingual
        implementation since model selection is handled upstream.
        """
        return await self.analyze_sentiment_multilingual(
            text,
            language=language
        )
    
    async def analyze_sentiment_multilingual(
        self, 
        text: str, 
        language: str = None
    ) -> Dict[str, Any]:
        """
        Analyze sentiment using ChatGPT for any language.
        
        Args:
            text: The customer feedback text to analyze
            language: Optional language hint (e.g., 'en', 'es', 'ja')
        
        Returns:
            Dictionary containing:
                - sentiment: 'positive', 'negative', or 'neutral'
                - confidence: Float between 0.0 and 1.0
                - analysis: Detailed explanation of sentiment
                - emotional_indicators: List of detected emotions
                - model: 'openai'
        
        Raises:
            Exception: If OpenAI API call fails
        """
        self.logger.info(f"Analyzing sentiment with OpenAI (language: {language})")
        
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
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a multilingual sentiment analysis expert who provides accurate, nuanced analysis of customer feedback in any language, considering cultural context and language-specific expressions."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            analysis_text = response.choices[0].message.content
            
            # Enhanced parsing for better accuracy
            sentiment = self._parse_sentiment_enhanced(analysis_text)
            confidence = self._extract_confidence_score(analysis_text)
            emotional_indicators = self._extract_emotional_indicators(analysis_text)
            
            self.logger.debug(f"OpenAI analysis: {sentiment} (confidence: {confidence})")
            
            return {
                "sentiment": sentiment,
                "confidence": confidence,
                "analysis": analysis_text,
                "emotional_indicators": emotional_indicators,
                "language": language,
                "model": "openai"
            }
            
        except Exception as e:
            self.logger.error(f"OpenAI sentiment analysis failed: {e}")
            raise
    
    def _parse_sentiment_enhanced(self, analysis_text: str) -> str:
        """Enhanced sentiment parsing from ChatGPT response."""
        text_lower = analysis_text.lower()
        
        # More sophisticated parsing
        if any(word in text_lower for word in ['positive', 'good', 'satisfied', 'happy', 'pleased', 'excellent']):
            return 'positive'
        elif any(word in text_lower for word in ['negative', 'bad', 'dissatisfied', 'unhappy', 'frustrated', 'angry', 'disappointed']):
            return 'negative'
        else:
            return 'neutral'
    
    def _extract_confidence_score(self, analysis_text: str) -> float:
        """Extract confidence score from ChatGPT response."""
        import re
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
        """Extract emotional indicators from ChatGPT response."""
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
    
    async def generate_trend_explanation(self, trend_data: Dict[str, Any]) -> str:
        """Generate explanation for trend data."""
        try:
            prompt = f"""
            Explain the following trend data in business terms:

            {trend_data}

            Provide:
            - What the trends mean
            - Business implications
            - Why these trends might be occurring
            - What actions should be considered
            """

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a business analyst who explains data trends in clear, actionable terms for executives."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=800,
                temperature=0.2
            )

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"Failed to generate trend explanation: {e}")
            return "Trend explanation generation failed"

    async def chat_completion_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        model: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> Any:
        """
        Create a chat completion with tool calling support.

        Args:
            messages: List of message dictionaries (OpenAI format)
            tools: Optional list of tool definitions in OpenAI format
            tool_choice: Tool choice strategy ("auto", "none", or specific tool)
            model: Optional model override (defaults to self.model)
            temperature: Optional temperature override (defaults to self.temperature)

        Returns:
            OpenAI ChatCompletion response object

        Raises:
            Exception: If API call fails
        """
        try:
            call_params = {
                "model": model or self.model,
                "messages": messages,
                "temperature": temperature if temperature is not None else self.temperature
            }

            # Add tools if provided
            if tools:
                call_params["tools"] = tools
                call_params["tool_choice"] = tool_choice

            response = await self.client.chat.completions.create(**call_params)

            return response

        except Exception as e:
            self.logger.error(f"Chat completion with tools failed: {e}")
            raise

