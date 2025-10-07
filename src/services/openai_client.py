"""
OpenAI client for generating AI-powered insights.
"""

import logging
from typing import Dict, List, Any, Optional
import openai
from openai import AsyncOpenAI

from ..config.settings import settings

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Client for OpenAI API interactions."""
    
    def __init__(self):
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model
        self.temperature = settings.openai_temperature
        self.max_tokens = settings.openai_max_tokens
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.logger = logging.getLogger(__name__)
    
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
    
    async def generate_analysis(self, prompt: str) -> str:
        """Generate analysis using OpenAI."""
        try:
            self.logger.info("Generating AI analysis")
            
            response = await self.client.chat.completions.create(
                model=self.model,
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
                temperature=self.temperature
            )
            
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
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of customer feedback."""
        try:
            prompt = f"""
            Analyze the sentiment of the following customer feedback:
            
            {text}
            
            Provide:
            - Overall sentiment (positive, negative, neutral)
            - Sentiment score (0-1)
            - Key emotional indicators
            - Summary of the feedback
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a sentiment analysis expert who provides accurate, nuanced analysis of customer feedback."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            # Parse sentiment analysis
            analysis_text = response.choices[0].message.content
            
            # Simple parsing - in production, you'd want more robust parsing
            sentiment = "neutral"
            score = 0.5
            
            if "positive" in analysis_text.lower():
                sentiment = "positive"
                score = 0.8
            elif "negative" in analysis_text.lower():
                sentiment = "negative"
                score = 0.2
            
            return {
                "sentiment": sentiment,
                "score": score,
                "analysis": analysis_text
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze sentiment: {e}")
            return {
                "sentiment": "neutral",
                "score": 0.5,
                "analysis": "Sentiment analysis failed"
            }
    
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

