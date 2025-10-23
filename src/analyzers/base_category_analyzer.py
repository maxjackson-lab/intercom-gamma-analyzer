"""
Base Category Analyzer for Intercom Analysis Tool.
Provides common functionality for all category-specific analyzers.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
import json

from src.services.openai_client import OpenAIClient
from src.services.data_preprocessor import DataPreprocessor
from src.services.category_filters import CategoryFilters
from src.config.prompts import PromptTemplates
from src.utils.time_utils import to_utc_datetime, calculate_time_delta_seconds

logger = logging.getLogger(__name__)


class BaseCategoryAnalyzer:
    """
    Base class for category-specific analyzers.
    
    Provides common functionality:
    - Data preprocessing and filtering
    - Pattern detection and analysis
    - Report generation with GPT-4o
    - Statistical analysis
    - Export capabilities
    """
    
    def __init__(
        self, 
        category_name: str,
        openai_client: Optional[OpenAIClient] = None,
        data_preprocessor: Optional[DataPreprocessor] = None,
        category_filters: Optional[CategoryFilters] = None
    ):
        """
        Initialize base category analyzer.
        
        Args:
            category_name: Name of the category being analyzed
            openai_client: OpenAI client for report generation
            data_preprocessor: Data preprocessor instance
            category_filters: Category filters instance
        """
        self.category_name = category_name
        self.openai_client = openai_client or OpenAIClient()
        self.data_preprocessor = data_preprocessor or DataPreprocessor()
        self.category_filters = category_filters or CategoryFilters()
        self.logger = logging.getLogger(__name__)
        
        # Analysis configuration
        self.analysis_config = {
            "min_confidence_threshold": 0.6,
            "max_conversations_for_analysis": 1000,
            "enable_statistical_sampling": True,
            "generate_ai_insights": True
        }
        
        self.logger.info(f"Initialized BaseCategoryAnalyzer for category: {category_name}")
    
    async def analyze_category(
        self, 
        conversations: List[Dict[str, Any]], 
        start_date: datetime, 
        end_date: datetime,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive category analysis.
        
        Args:
            conversations: List of conversations to analyze
            start_date: Analysis start date
            end_date: Analysis end date
            options: Analysis options
            
        Returns:
            Analysis results dictionary
        """
        self.logger.info(f"Starting {self.category_name} analysis for {len(conversations)} conversations")
        
        options = options or {}
        analysis_start_time = datetime.now()
        
        try:
            # Step 1: Preprocess data (skip if already preprocessed)
            if not options.get('skip_preprocessing', False):
                self.logger.info("Step 1: Preprocessing conversations")
                processed_conversations, preprocessing_stats = self.data_preprocessor.preprocess_conversations(
                    conversations, options.get('preprocessing', {})
                )
            else:
                self.logger.info("Step 1: Skipping preprocessing (already done)")
                processed_conversations = conversations
                preprocessing_stats = {'skipped': True}
            
            # Step 2: Filter by category
            self.logger.info(f"Step 2: Filtering conversations by {self.category_name}")
            filtered_conversations = self._filter_conversations(processed_conversations, options)
            
            if not filtered_conversations:
                self.logger.warning(f"No conversations found for category: {self.category_name}")
                return self._create_empty_analysis_result(start_date, end_date)
            
            # Step 3: Perform category-specific analysis
            self.logger.info("Step 3: Performing category-specific analysis")
            category_analysis = await self._perform_category_analysis(
                filtered_conversations, start_date, end_date, options
            )
            
            # Step 4: Generate statistical insights
            self.logger.info("Step 4: Generating statistical insights")
            statistical_insights = self._generate_statistical_insights(
                filtered_conversations, category_analysis
            )
            
            # Step 5: Generate AI-powered insights
            ai_insights = None
            if options.get('generate_ai_insights', self.analysis_config['generate_ai_insights']):
                self.logger.info("Step 5: Generating AI-powered insights")
                ai_insights = await self._generate_ai_insights(
                    filtered_conversations, category_analysis, statistical_insights
                )
            
            # Step 6: Compile final results
            analysis_duration = (datetime.now() - analysis_start_time).total_seconds()
            
            results = {
                "category": self.category_name,
                "analysis_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "duration_days": (end_date - start_date).days + 1
                },
                "data_summary": {
                    "total_conversations": len(conversations),
                    "processed_conversations": len(processed_conversations),
                    "filtered_conversations": len(filtered_conversations),
                    "preprocessing_stats": preprocessing_stats
                },
                "category_analysis": category_analysis,
                "statistical_insights": statistical_insights,
                "ai_insights": ai_insights,
                "analysis_metadata": {
                    "analyzer_version": "1.0.0",
                    "analysis_duration_seconds": analysis_duration,
                    "analysis_timestamp": datetime.now().isoformat(),
                    "options_used": options
                }
            }
            
            self.logger.info(f"{self.category_name} analysis completed in {analysis_duration:.2f} seconds")
            return results
            
        except Exception as e:
            self.logger.error(f"Category analysis failed: {e}", exc_info=True)
            raise AnalysisError(f"Failed to analyze {self.category_name} category: {e}") from e
    
    def _filter_conversations(
        self, 
        conversations: List[Dict[str, Any]], 
        options: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Filter conversations for this category.
        
        Args:
            conversations: List of conversations to filter
            options: Filtering options
            
        Returns:
            Filtered conversations
        """
        # Use category filters to get relevant conversations
        filtered = self.category_filters.filter_by_category(
            conversations, 
            self.category_name,
            include_subcategories=options.get('include_subcategories', True)
        )
        
        # Apply additional category-specific filtering
        filtered = self._apply_category_specific_filters(filtered, options)
        
        # Apply conversation limit if specified
        max_conversations = options.get('max_conversations', self.analysis_config['max_conversations_for_analysis'])
        if len(filtered) > max_conversations:
            self.logger.info(f"Limiting analysis to {max_conversations} conversations (from {len(filtered)})")
            filtered = filtered[:max_conversations]
        
        return filtered
    
    def _apply_category_specific_filters(
        self, 
        conversations: List[Dict[str, Any]], 
        options: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Apply category-specific filtering logic.
        Override in subclasses for specific filtering needs.
        
        Args:
            conversations: List of conversations to filter
            options: Filtering options
            
        Returns:
            Filtered conversations
        """
        return conversations
    
    async def _perform_category_analysis(
        self, 
        conversations: List[Dict[str, Any]], 
        start_date: datetime, 
        end_date: datetime,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform category-specific analysis.
        Override in subclasses for specific analysis logic.
        
        Args:
            conversations: Filtered conversations for this category
            start_date: Analysis start date
            end_date: Analysis end date
            options: Analysis options
            
        Returns:
            Category-specific analysis results
        """
        # Base analysis - can be overridden by subclasses
        return {
            "conversation_count": len(conversations),
            "analysis_type": "base_analysis",
            "patterns_detected": [],
            "key_metrics": {}
        }
    
    def _generate_statistical_insights(
        self, 
        conversations: List[Dict[str, Any]], 
        category_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate statistical insights from the analysis.
        
        Args:
            conversations: Analyzed conversations
            category_analysis: Category-specific analysis results
            
        Returns:
            Statistical insights dictionary
        """
        insights = {
            "conversation_volume": {
                "total": len(conversations),
                "daily_average": 0,
                "trend": "stable"
            },
            "response_times": {
                "average_hours": 0,
                "median_hours": 0,
                "p95_hours": 0
            },
            "resolution_rates": {
                "resolved": 0,
                "unresolved": 0,
                "resolution_rate": 0
            },
            "customer_satisfaction": {
                "average_rating": 0,
                "rating_distribution": {}
            },
            "top_issues": [],
            "escalation_patterns": {
                "escalation_rate": 0,
                "common_escalation_reasons": []
            }
        }
        
        if not conversations:
            return insights
        
        # Calculate daily average
        date_range = self._get_date_range(conversations)
        if date_range:
            days = (date_range['end'] - date_range['start']).days + 1
            insights["conversation_volume"]["daily_average"] = len(conversations) / days
        
        # Calculate response times
        response_times = self._calculate_response_times(conversations)
        if response_times:
            insights["response_times"] = response_times
        
        # Calculate resolution rates
        resolution_stats = self._calculate_resolution_rates(conversations)
        insights["resolution_rates"] = resolution_stats
        
        # Calculate satisfaction ratings
        satisfaction_stats = self._calculate_satisfaction_ratings(conversations)
        insights["customer_satisfaction"] = satisfaction_stats
        
        # Identify top issues
        top_issues = self._identify_top_issues(conversations)
        insights["top_issues"] = top_issues
        
        # Analyze escalation patterns
        escalation_stats = self._analyze_escalation_patterns(conversations)
        insights["escalation_patterns"] = escalation_stats
        
        return insights
    
    async def _generate_ai_insights(
        self, 
        conversations: List[Dict[str, Any]], 
        category_analysis: Dict[str, Any],
        statistical_insights: Dict[str, Any]
    ) -> Optional[str]:
        """
        Generate AI-powered insights using GPT-4o.
        
        Args:
            conversations: Analyzed conversations
            category_analysis: Category-specific analysis results
            statistical_insights: Statistical insights
            
        Returns:
            AI-generated insights text
        """
        try:
            # Prepare data summary for AI
            data_summary = self._prepare_data_summary_for_ai(
                conversations, category_analysis, statistical_insights
            )
            
            # Get appropriate prompt template
            prompt = self._get_ai_analysis_prompt(data_summary)
            
            # Generate AI insights
            ai_insights = await self.openai_client.generate_analysis(prompt)
            
            self.logger.info("AI insights generated successfully")
            return ai_insights
            
        except Exception as e:
            self.logger.error(f"Failed to generate AI insights: {e}")
            return None
    
    def _prepare_data_summary_for_ai(
        self, 
        conversations: List[Dict[str, Any]], 
        category_analysis: Dict[str, Any],
        statistical_insights: Dict[str, Any]
    ) -> str:
        """
        Prepare a data summary for AI analysis.
        
        Args:
            conversations: Analyzed conversations
            category_analysis: Category-specific analysis results
            statistical_insights: Statistical insights
            
        Returns:
            Formatted data summary
        """
        summary_parts = [
            f"Category: {self.category_name}",
            f"Total conversations analyzed: {len(conversations)}",
            f"Analysis period: {category_analysis.get('analysis_period', 'N/A')}",
            "",
            "Statistical Insights:",
            f"- Daily average: {statistical_insights.get('conversation_volume', {}).get('daily_average', 0):.1f} conversations",
            f"- Resolution rate: {statistical_insights.get('resolution_rates', {}).get('resolution_rate', 0):.1%}",
            f"- Average response time: {statistical_insights.get('response_times', {}).get('average_hours', 0):.1f} hours",
            "",
            "Top Issues:",
        ]
        
        top_issues = statistical_insights.get('top_issues', [])
        for i, issue in enumerate(top_issues[:5], 1):
            summary_parts.append(f"{i}. {issue}")
        
        # Add sample conversation excerpts
        summary_parts.extend([
            "",
            "Sample Conversation Excerpts:",
        ])
        
        for i, conv in enumerate(conversations[:3], 1):
            text = self._extract_conversation_text(conv)
            excerpt = text[:200] + "..." if len(text) > 200 else text
            summary_parts.append(f"Conversation {i}: {excerpt}")
        
        return "\n".join(summary_parts)
    
    def _get_ai_analysis_prompt(self, data_summary: str) -> str:
        """
        Get AI analysis prompt for this category.
        Override in subclasses for category-specific prompts.
        
        Args:
            data_summary: Data summary for AI analysis
            
        Returns:
            Formatted prompt for AI analysis
        """
        return PromptTemplates.get_custom_analysis_prompt(
            custom_prompt=f"Analyze {self.category_name} conversations",
            start_date=data_summary.get('start_date', ''),
            end_date=data_summary.get('end_date', ''),
            intercom_data=str(data_summary)
        )
    
    def _create_empty_analysis_result(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Create empty analysis result when no conversations are found."""
        return {
            "category": self.category_name,
            "analysis_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "duration_days": (end_date - start_date).days + 1
            },
            "data_summary": {
                "total_conversations": 0,
                "processed_conversations": 0,
                "filtered_conversations": 0
            },
            "category_analysis": {
                "conversation_count": 0,
                "analysis_type": "empty_analysis"
            },
            "statistical_insights": {
                "conversation_volume": {"total": 0, "daily_average": 0},
                "resolution_rates": {"resolution_rate": 0}
            },
            "ai_insights": f"No conversations found for {self.category_name} category in the specified date range.",
            "analysis_metadata": {
                "analyzer_version": "1.0.0",
                "analysis_timestamp": datetime.now().isoformat(),
                "empty_result": True
            }
        }
    
    def _get_date_range(self, conversations: List[Dict[str, Any]]) -> Optional[Dict[str, datetime]]:
        """Get date range from conversations."""
        if not conversations:
            return None
        
        dates = []
        for conv in conversations:
            created_at = conv.get('created_at')
            if created_at:
                # Use helper to handle both datetime and numeric types
                dt = to_utc_datetime(created_at)
                if dt:
                    dates.append(dt)
        
        if not dates:
            return None
        
        return {
            'start': min(dates),
            'end': max(dates)
        }
    
    def _calculate_response_times(self, conversations: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate response time statistics."""
        response_times = []
        
        for conv in conversations:
            created_at = conv.get('created_at')
            first_response = conv.get('first_contact_reply_at')
            
            if created_at and first_response:
                try:
                    # Use helper to calculate time delta in seconds
                    delta_seconds = calculate_time_delta_seconds(created_at, first_response)
                    if delta_seconds is not None:
                        response_time = delta_seconds / 3600  # Convert to hours
                        response_times.append(response_time)
                except Exception as e:
                    self.logger.warning(f"Error calculating response time: {e}")
                    continue
        
        if not response_times:
            return {"average_hours": 0, "median_hours": 0, "p95_hours": 0}
        
        response_times.sort()
        n = len(response_times)
        
        return {
            "average_hours": sum(response_times) / n,
            "median_hours": response_times[n // 2],
            "p95_hours": response_times[int(n * 0.95)] if n > 1 else response_times[0]
        }
    
    def _calculate_resolution_rates(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate resolution rate statistics."""
        resolved = 0
        unresolved = 0
        
        for conv in conversations:
            state = conv.get('state', '').lower()
            if state in ['closed', 'resolved']:
                resolved += 1
            else:
                unresolved += 1
        
        total = resolved + unresolved
        resolution_rate = resolved / total if total > 0 else 0
        
        return {
            "resolved": resolved,
            "unresolved": unresolved,
            "resolution_rate": resolution_rate
        }
    
    def _calculate_satisfaction_ratings(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate customer satisfaction statistics."""
        ratings = []
        
        for conv in conversations:
            # Look for satisfaction ratings in custom attributes or conversation parts
            custom_attrs = conv.get('custom_attributes', {})
            rating = custom_attrs.get('satisfaction_rating') or custom_attrs.get('rating')
            
            if rating:
                try:
                    ratings.append(float(rating))
                except (ValueError, TypeError):
                    continue
        
        if not ratings:
            return {"average_rating": 0, "rating_distribution": {}}
        
        # Calculate distribution
        distribution = {}
        for rating in ratings:
            rating_bucket = f"{int(rating)}-{int(rating)+1}"
            distribution[rating_bucket] = distribution.get(rating_bucket, 0) + 1
        
        return {
            "average_rating": sum(ratings) / len(ratings),
            "rating_distribution": distribution
        }
    
    def _identify_top_issues(self, conversations: List[Dict[str, Any]]) -> List[str]:
        """Identify top issues from conversations."""
        # This is a simplified implementation - can be enhanced with NLP
        issue_keywords = {}
        
        for conv in conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Simple keyword counting
            common_issues = [
                'error', 'bug', 'broken', 'not working', 'issue', 'problem',
                'refund', 'billing', 'payment', 'subscription',
                'login', 'password', 'access', 'authentication',
                'export', 'download', 'data', 'csv'
            ]
            
            for issue in common_issues:
                if issue in text:
                    issue_keywords[issue] = issue_keywords.get(issue, 0) + 1
        
        # Sort by frequency and return top issues
        sorted_issues = sorted(issue_keywords.items(), key=lambda x: x[1], reverse=True)
        return [issue for issue, count in sorted_issues[:10]]
    
    def _analyze_escalation_patterns(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze escalation patterns in conversations."""
        escalation_keywords = ['escalate', 'escalation', 'escalated', 'transfer', 'supervisor', 'manager']
        escalated_conversations = 0
        escalation_reasons = {}
        
        for conv in conversations:
            text = self._extract_conversation_text(conv).lower()
            
            if any(keyword in text for keyword in escalation_keywords):
                escalated_conversations += 1
                
                # Try to identify escalation reason
                if 'technical' in text:
                    escalation_reasons['technical'] = escalation_reasons.get('technical', 0) + 1
                elif 'billing' in text:
                    escalation_reasons['billing'] = escalation_reasons.get('billing', 0) + 1
                elif 'complex' in text:
                    escalation_reasons['complex'] = escalation_reasons.get('complex', 0) + 1
        
        total_conversations = len(conversations)
        escalation_rate = escalated_conversations / total_conversations if total_conversations > 0 else 0
        
        return {
            "escalation_rate": escalation_rate,
            "common_escalation_reasons": list(escalation_reasons.keys())
        }
    
    def _extract_conversation_text(self, conv: Dict[str, Any]) -> str:
        """Extract all text content from a conversation."""
        text_parts = []
        
        # Extract from conversation parts
        parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
        for part in parts:
            if part.get('part_type') == 'comment':
                body = part.get('body', '')
                if body:
                    text_parts.append(body)
        
        # Extract from source
        source = conv.get('source', {})
        if source.get('body'):
            text_parts.append(source['body'])
        
        return ' '.join(text_parts)
    
    def export_analysis_results(
        self, 
        results: Dict[str, Any], 
        output_dir: Path,
        format: str = "json"
    ) -> Path:
        """
        Export analysis results to file.
        
        Args:
            results: Analysis results to export
            output_dir: Output directory
            format: Export format (json, md, txt)
            
        Returns:
            Path to exported file
        """
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.category_name.lower()}_analysis_{timestamp}.{format}"
        filepath = output_dir / filename
        
        self.logger.info(f"Exporting {self.category_name} analysis results to {filepath}")
        
        try:
            if format == "json":
                with open(filepath, 'w') as f:
                    json.dump(results, f, indent=2, default=str)
            elif format == "md":
                markdown_content = self._format_results_as_markdown(results)
                with open(filepath, 'w') as f:
                    f.write(markdown_content)
            elif format == "txt":
                text_content = self._format_results_as_text(results)
                with open(filepath, 'w') as f:
                    f.write(text_content)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            self.logger.info(f"Analysis results exported successfully to {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to export analysis results: {e}")
            raise ExportError(f"Failed to export results to {filepath}: {e}") from e
    
    def _format_results_as_markdown(self, results: Dict[str, Any]) -> str:
        """Format analysis results as markdown."""
        md_parts = [
            f"# {self.category_name} Analysis Report",
            f"**Analysis Period:** {results['analysis_period']['start_date']} to {results['analysis_period']['end_date']}",
            f"**Total Conversations:** {results['data_summary']['filtered_conversations']}",
            "",
            "## Statistical Insights",
            f"- **Daily Average:** {results['statistical_insights']['conversation_volume']['daily_average']:.1f} conversations",
            f"- **Resolution Rate:** {results['statistical_insights']['resolution_rates']['resolution_rate']:.1%}",
            f"- **Average Response Time:** {results['statistical_insights']['response_times']['average_hours']:.1f} hours",
            "",
            "## Top Issues",
        ]
        
        for i, issue in enumerate(results['statistical_insights']['top_issues'][:5], 1):
            md_parts.append(f"{i}. {issue}")
        
        if results.get('ai_insights'):
            md_parts.extend([
                "",
                "## AI-Powered Insights",
                results['ai_insights']
            ])
        
        return "\n".join(md_parts)
    
    def _format_results_as_text(self, results: Dict[str, Any]) -> str:
        """Format analysis results as plain text."""
        text_parts = [
            f"{self.category_name} Analysis Report",
            f"Analysis Period: {results['analysis_period']['start_date']} to {results['analysis_period']['end_date']}",
            f"Total Conversations: {results['data_summary']['filtered_conversations']}",
            "",
            "Statistical Insights:",
            f"- Daily Average: {results['statistical_insights']['conversation_volume']['daily_average']:.1f} conversations",
            f"- Resolution Rate: {results['statistical_insights']['resolution_rates']['resolution_rate']:.1%}",
            f"- Average Response Time: {results['statistical_insights']['response_times']['average_hours']:.1f} hours",
            "",
            "Top Issues:",
        ]
        
        for i, issue in enumerate(results['statistical_insights']['top_issues'][:5], 1):
            text_parts.append(f"{i}. {issue}")
        
        if results.get('ai_insights'):
            text_parts.extend([
                "",
                "AI-Powered Insights:",
                results['ai_insights']
            ])
        
        return "\n".join(text_parts)


# Custom Exceptions
class AnalysisError(Exception):
    """Exception raised when analysis fails."""
    pass


class ExportError(Exception):
    """Exception raised when export fails."""
    pass
