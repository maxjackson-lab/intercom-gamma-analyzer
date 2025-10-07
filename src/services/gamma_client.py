"""
Gamma client for generating presentations.
"""

import logging
from typing import Dict, List, Any, Optional
import httpx

from ..config.settings import settings
from ..models.analysis_models import GammaPresentationRequest, GammaPresentationResponse

logger = logging.getLogger(__name__)


class GammaClient:
    """Client for Gamma presentation generation."""
    
    def __init__(self):
        self.api_key = settings.gamma_api_key
        self.base_url = settings.gamma_base_url
        self.default_template = settings.gamma_default_template
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        } if self.api_key else {}
        
        self.logger = logging.getLogger(__name__)
    
    async def test_connection(self) -> bool:
        """Test connection to Gamma API."""
        if not self.api_key:
            self.logger.warning("Gamma API key not provided, skipping connection test")
            return True
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/templates",
                    headers=self.headers
                )
                response.raise_for_status()
                self.logger.info("Gamma API connection successful")
                return True
        except Exception as e:
            self.logger.error(f"Gamma API connection failed: {e}")
            raise
    
    async def create_presentation(self, analysis_results: Any) -> GammaPresentationResponse:
        """Create a Gamma presentation from analysis results."""
        if not self.api_key:
            self.logger.warning("Gamma API key not provided, generating markdown only")
            return self._generate_markdown_only(analysis_results)
        
        try:
            # Prepare presentation data
            presentation_data = self._prepare_presentation_data(analysis_results)
            
            # Create presentation
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/presentations",
                    headers=self.headers,
                    json=presentation_data
                )
                response.raise_for_status()
                
                result = response.json()
                
                return GammaPresentationResponse(
                    presentation_id=result.get('id'),
                    presentation_url=result.get('url'),
                    markdown_content=presentation_data.get('content', ''),
                    generation_successful=True
                )
                
        except Exception as e:
            self.logger.error(f"Failed to create Gamma presentation: {e}")
            return GammaPresentationResponse(
                generation_successful=False,
                error_message=str(e),
                markdown_content=self._generate_markdown_only(analysis_results).markdown_content
            )
    
    def _prepare_presentation_data(self, analysis_results: Any) -> Dict[str, Any]:
        """Prepare data for Gamma presentation."""
        # Generate markdown content
        markdown_content = self._generate_markdown_content(analysis_results)
        
        return {
            "title": self._get_presentation_title(analysis_results),
            "content": markdown_content,
            "template": self.default_template,
            "settings": {
                "include_images": True,
                "theme": "professional"
            }
        }
    
    def _generate_markdown_content(self, analysis_results: Any) -> str:
        """Generate markdown content for the presentation."""
        content = []
        
        # Title
        content.append(f"# {self._get_presentation_title(analysis_results)}")
        content.append("")
        
        # Executive Summary
        if hasattr(analysis_results, 'executive_summary'):
            content.append("## Executive Summary")
            content.append("")
            summary = analysis_results.executive_summary
            if isinstance(summary, dict):
                for key, value in summary.items():
                    content.append(f"**{key.replace('_', ' ').title()}:** {value}")
            else:
                content.append(str(summary))
            content.append("")
        
        # Key Metrics
        content.append("## Key Metrics")
        content.append("")
        
        if hasattr(analysis_results, 'total_conversations'):
            content.append(f"- **Total Conversations:** {analysis_results.total_conversations:,}")
        
        if hasattr(analysis_results, 'ai_resolution_rate'):
            content.append(f"- **AI Resolution Rate:** {analysis_results.ai_resolution_rate}%")
        
        if hasattr(analysis_results, 'overall_csat'):
            content.append(f"- **Customer Satisfaction:** {analysis_results.overall_csat}%")
        
        if hasattr(analysis_results, 'median_response_time'):
            content.append(f"- **Median Response Time:** {analysis_results.median_response_time}")
        
        content.append("")
        
        # Analysis Content
        if hasattr(analysis_results, 'analysis_content'):
            content.append("## Analysis")
            content.append("")
            content.append(analysis_results.analysis_content)
            content.append("")
        
        # Customer Quotes
        if hasattr(analysis_results, 'customer_quotes') and analysis_results.customer_quotes:
            content.append("## Customer Feedback")
            content.append("")
            for quote in analysis_results.customer_quotes[:5]:  # Top 5 quotes
                if isinstance(quote, dict):
                    quote_text = quote.get('quote', '')
                    context = quote.get('context', '')
                    if quote_text:
                        content.append(f"> \"{quote_text}\"")
                        if context:
                            content.append(f"*{context}*")
                        content.append("")
        
        # Recommendations
        if hasattr(analysis_results, 'recommendations') and analysis_results.recommendations:
            content.append("## Recommendations")
            content.append("")
            for rec in analysis_results.recommendations:
                content.append(f"- {rec}")
            content.append("")
        
        return "\n".join(content)
    
    def _get_presentation_title(self, analysis_results: Any) -> str:
        """Get presentation title based on analysis results."""
        if hasattr(analysis_results, 'request'):
            request = analysis_results.request
            if request.mode.value == "voice_of_customer":
                return f"Voice of Customer - {request.month}/{request.year}"
            elif request.mode.value == "trend_analysis":
                return f"Trend Analysis - {request.start_date} to {request.end_date}"
            else:
                return f"Custom Analysis - {request.start_date} to {request.end_date}"
        else:
            return "Intercom Analysis Report"
    
    def _generate_markdown_only(self, analysis_results: Any) -> GammaPresentationResponse:
        """Generate markdown-only response when Gamma API is not available."""
        markdown_content = self._generate_markdown_content(analysis_results)
        
        return GammaPresentationResponse(
            markdown_content=markdown_content,
            generation_successful=True,
            error_message="Gamma API not available, generated markdown only"
        )

