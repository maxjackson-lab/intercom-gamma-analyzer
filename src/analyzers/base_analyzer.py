"""
Base analyzer class for Intercom conversation analysis.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.models.analysis_models import AnalysisRequest, AnalysisResults
from src.services.intercom_service import IntercomService
from src.services.metrics_calculator import MetricsCalculator
from src.services.openai_client import OpenAIClient
from src.config.prompts import PromptTemplates

logger = logging.getLogger(__name__)


class BaseAnalyzer(ABC):
    """Base class for all analyzers."""
    
    def __init__(
        self,
        intercom_service: IntercomService,
        metrics_calculator: MetricsCalculator,
        openai_client: OpenAIClient
    ):
        self.intercom_service = intercom_service
        self.metrics_calculator = metrics_calculator
        self.openai_client = openai_client
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def analyze(self, request: AnalysisRequest) -> AnalysisResults:
        """Perform analysis based on the request."""
        pass
    
    async def fetch_conversations(self, request: AnalysisRequest) -> List[Dict]:
        """Fetch conversations based on the analysis request."""
        self.logger.info(f"Fetching conversations for {request.mode} analysis")
        
        if request.mode.value == "voice_of_customer":
            # For voice of customer, fetch the entire month
            if not request.month or not request.year:
                raise ValueError("Month and year are required for voice of customer analysis")
            
            start_date = datetime(request.year, request.month, 1)
            if request.month == 12:
                end_date = datetime(request.year + 1, 1, 1)
            else:
                end_date = datetime(request.year, request.month + 1, 1)
            
            return await self.intercom_service.fetch_conversations_by_date_range(
                start_date, end_date
            )
        
        else:
            # For trend analysis and custom analysis
            if not request.start_date or not request.end_date:
                raise ValueError("Start date and end date are required for trend/custom analysis")
            
            start_date = datetime.combine(request.start_date, datetime.min.time())
            end_date = datetime.combine(request.end_date, datetime.max.time())
            
            return await self.intercom_service.fetch_conversations_by_date_range(
                start_date, end_date
            )
    
    async def calculate_metrics(self, conversations: List[Dict], request: AnalysisRequest) -> Dict[str, Any]:
        """Calculate all relevant metrics for the conversations."""
        self.logger.info(f"Calculating metrics for {len(conversations)} conversations")
        
        # Calculate all metric categories
        volume_metrics = self.metrics_calculator.calculate_volume_metrics(conversations)
        efficiency_metrics = self.metrics_calculator.calculate_efficiency_metrics(conversations)
        satisfaction_metrics = self.metrics_calculator.calculate_satisfaction_metrics(conversations)
        topic_metrics = self.metrics_calculator.calculate_topic_metrics(conversations)
        
        # Geographic metrics (with tier1 countries if available)
        tier1_countries = request.tier1_countries or []
        geographic_metrics = self.metrics_calculator.calculate_geographic_metrics(
            conversations, tier1_countries
        )
        
        friction_metrics = self.metrics_calculator.calculate_friction_metrics(conversations)
        channel_metrics = self.metrics_calculator.calculate_channel_metrics(conversations)
        
        return {
            "volume": volume_metrics,
            "efficiency": efficiency_metrics,
            "satisfaction": satisfaction_metrics,
            "topics": topic_metrics,
            "geographic": geographic_metrics,
            "friction": friction_metrics,
            "channel": channel_metrics
        }
    
    async def generate_ai_insights(
        self, 
        conversations: List[Dict], 
        metrics: Dict[str, Any], 
        request: AnalysisRequest
    ) -> Dict[str, Any]:
        """Generate AI-powered insights using OpenAI."""
        self.logger.info("Generating AI insights")
        
        # Prepare data for AI analysis
        data_summary = self._prepare_data_summary(conversations, metrics)
        
        # Generate insights based on analysis mode
        if request.mode.value == "voice_of_customer":
            insights = await self._generate_voice_insights(data_summary, request)
        elif request.mode.value == "trend_analysis":
            insights = await self._generate_trend_insights(data_summary, request)
        else:  # custom
            insights = await self._generate_custom_insights(data_summary, request)
        
        return insights
    
    def _prepare_data_summary(self, conversations: List[Dict], metrics: Dict[str, Any]) -> str:
        """Prepare a summary of the data for AI analysis."""
        summary = {
            "total_conversations": len(conversations),
            "date_range": {
                "start": min(conv.get('created_at', 0) for conv in conversations) if conversations else 0,
                "end": max(conv.get('created_at', 0) for conv in conversations) if conversations else 0
            },
            "metrics": metrics,
            "sample_conversations": conversations[:5] if conversations else []  # First 5 for context
        }
        
        return str(summary)
    
    async def _generate_voice_insights(self, data_summary: str, request: AnalysisRequest) -> Dict[str, Any]:
        """Generate Voice of Customer insights."""
        prompt = PromptTemplates.get_voice_of_customer_prompt(
            month=request.month,
            year=request.year,
            tier1_countries=request.tier1_countries or [],
            intercom_data=data_summary
        )
        
        response = await self.openai_client.generate_analysis(prompt)
        
        return {
            "analysis_content": response,
            "insights_type": "voice_of_customer"
        }
    
    async def _generate_trend_insights(self, data_summary: str, request: AnalysisRequest) -> Dict[str, Any]:
        """Generate trend analysis insights."""
        prompt = PromptTemplates.get_trend_analysis_prompt(
            start_date=request.start_date.strftime('%Y-%m-%d') if request.start_date else "",
            end_date=request.end_date.strftime('%Y-%m-%d') if request.end_date else "",
            focus_areas=request.focus_areas or [],
            custom_instructions=request.custom_instructions,
            intercom_data=data_summary
        )
        
        response = await self.openai_client.generate_analysis(prompt)
        
        return {
            "analysis_content": response,
            "insights_type": "trend_analysis"
        }
    
    async def _generate_custom_insights(self, data_summary: str, request: AnalysisRequest) -> Dict[str, Any]:
        """Generate custom analysis insights."""
        prompt = PromptTemplates.get_custom_analysis_prompt(
            custom_prompt=request.custom_prompt or "",
            start_date=request.start_date.strftime('%Y-%m-%d') if request.start_date else "",
            end_date=request.end_date.strftime('%Y-%m-%d') if request.end_date else "",
            intercom_data=data_summary
        )
        
        response = await self.openai_client.generate_analysis(prompt)
        
        return {
            "analysis_content": response,
            "insights_type": "custom"
        }
    
    async def extract_customer_quotes(self, conversations: List[Dict], quote_type: str = "positive") -> List[Dict[str, Any]]:
        """Extract customer quotes from conversations."""
        self.logger.info(f"Extracting {quote_type} customer quotes")
        
        # Prepare data for quote extraction
        data_summary = str(conversations[:20])  # First 20 conversations for context
        
        prompt = PromptTemplates.get_quote_extraction_prompt(data_summary, quote_type)
        
        response = await self.openai_client.generate_analysis(prompt)
        
        # Parse the response to extract structured quotes
        quotes = self._parse_quotes_response(response)
        
        return quotes
    
    def _parse_quotes_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse the AI response to extract structured quotes."""
        # This is a simplified parser - in production, you'd want more robust parsing
        quotes = []
        
        # Split by quote sections and extract information
        # This is a placeholder implementation
        lines = response.split('\n')
        current_quote = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith('Quote:'):
                if current_quote:
                    quotes.append(current_quote)
                current_quote = {"quote": line.replace('Quote:', '').strip()}
            elif line.startswith('Context:'):
                current_quote["context"] = line.replace('Context:', '').strip()
            elif line.startswith('Conversation ID:'):
                current_quote["conversation_id"] = line.replace('Conversation ID:', '').strip()
            elif line.startswith('Significance:'):
                current_quote["significance"] = line.replace('Significance:', '').strip()
        
        if current_quote:
            quotes.append(current_quote)
        
        return quotes
    
    def _calculate_analysis_duration(self, start_time: datetime) -> float:
        """Calculate analysis duration in seconds."""
        return (datetime.now() - start_time).total_seconds()
    
    def _calculate_data_quality_score(self, conversations: List[Dict]) -> float:
        """Calculate a data quality score for the conversations."""
        if not conversations:
            return 0.0
        
        total_conversations = len(conversations)
        quality_indicators = 0
        
        for conv in conversations:
            # Check for required fields
            if conv.get('id'):
                quality_indicators += 1
            if conv.get('created_at'):
                quality_indicators += 1
            if conv.get('source', {}).get('body'):
                quality_indicators += 1
            if conv.get('conversation_parts', {}).get('conversation_parts'):
                quality_indicators += 1
        
        # Calculate quality score (0-1)
        max_indicators = total_conversations * 4  # 4 indicators per conversation
        quality_score = quality_indicators / max_indicators if max_indicators > 0 else 0
        
        return round(quality_score, 3)
    
    def _calculate_confidence_score(self, conversations: List[Dict], metrics: Dict[str, Any]) -> float:
        """Calculate confidence score for the analysis."""
        if not conversations:
            return 0.0
        
        # Base confidence on data volume and completeness
        base_confidence = min(len(conversations) / 100, 1.0)  # Max confidence at 100+ conversations
        
        # Adjust based on data quality
        quality_score = self._calculate_data_quality_score(conversations)
        
        # Adjust based on metric completeness
        metric_completeness = self._calculate_metric_completeness(metrics)
        
        # Final confidence score
        confidence = (base_confidence + quality_score + metric_completeness) / 3
        
        return round(confidence, 3)
    
    def _calculate_metric_completeness(self, metrics: Dict[str, Any]) -> float:
        """Calculate how complete the metrics are."""
        total_metrics = 0
        complete_metrics = 0
        
        for category, metric_data in metrics.items():
            if hasattr(metric_data, '__dict__'):
                for field_name, field_value in metric_data.__dict__.items():
                    total_metrics += 1
                    if field_value is not None and field_value != 0:
                        complete_metrics += 1
        
        return complete_metrics / total_metrics if total_metrics > 0 else 0

