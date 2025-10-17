"""
RAG (Retrieval Augmented Generation) engine for complex command scenarios.

Handles novel command variations and complex filtering scenarios by retrieving
relevant documentation and examples before generating commands.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import re

from ..schemas import (
    CommandTranslation, ActionType, FilterSpec, ModelType,
    create_safe_command_translation
)
from ..model_router import ModelRouter, QueryComplexity

logger = logging.getLogger(__name__)


@dataclass
class DocumentationEntry:
    """Entry in the documentation database."""
    title: str
    content: str
    command: str
    examples: List[str]
    tags: List[str]
    relevance_score: float = 0.0


class RAGEngine:
    """
    RAG engine for complex command translation.
    
    Uses retrieval-augmented generation to handle novel command variations
    and complex filtering scenarios by retrieving relevant documentation.
    """
    
    def __init__(self, model_router: Optional[ModelRouter] = None):
        self.logger = logging.getLogger(__name__)
        self.model_router = model_router or ModelRouter()
        
        # Documentation database
        self.documentation = self._build_documentation_database()
        
        # Performance tracking
        self.stats = {
            "total_queries": 0,
            "successful_retrievals": 0,
            "failed_retrievals": 0,
            "average_relevance_score": 0.0,
            "average_response_time_ms": 0.0
        }
    
    def _build_documentation_database(self) -> List[DocumentationEntry]:
        """Build documentation database with CLI examples and patterns."""
        return [
            DocumentationEntry(
                title="Voice of Customer Analysis",
                content="""
                The voice-of-customer command generates comprehensive analysis of customer conversations
                to identify trends, sentiment, and key topics. It supports various time periods and
                can include Canny feedback data and generate Gamma presentations.
                
                Common use cases:
                - Weekly sentiment analysis
                - Monthly trend identification
                - Quarterly comprehensive reports
                - Custom date range analysis
                """,
                command="voice-of-customer",
                examples=[
                    "voice-of-customer --time-period week --generate-gamma",
                    "voice-of-customer --start-date 2025-01-01 --end-date 2025-01-31 --include-canny",
                    "voice-of-customer --time-period month --ai-model claude"
                ],
                tags=["voc", "voice-of-customer", "analysis", "sentiment", "trends", "report"]
            ),
            
            DocumentationEntry(
                title="Comprehensive Analysis",
                content="""
                The comprehensive-analysis command runs multi-source analysis combining Intercom
                conversations, Canny feedback, and other data sources. It's ideal for detailed
                reports and presentations.
                
                Features:
                - Multi-source data integration
                - Detailed documentation export
                - Gamma presentation generation
                - Configurable conversation limits
                """,
                command="comprehensive-analysis",
                examples=[
                    "comprehensive-analysis --start-date 2025-01-01 --end-date 2025-01-31 --generate-gamma",
                    "comprehensive-analysis --max-conversations 500 --export-docs",
                    "comprehensive-analysis --start-date 2025-01-01 --end-date 2025-03-31"
                ],
                tags=["comprehensive", "analysis", "multi-source", "detailed", "export", "gamma"]
            ),
            
            DocumentationEntry(
                title="Billing Analysis",
                content="""
                The billing-analysis command focuses on subscription, payment, and billing-related
                conversations. It helps identify billing issues, subscription trends, and payment
                problems.
                
                Use cases:
                - Billing issue identification
                - Subscription trend analysis
                - Payment problem tracking
                - Revenue impact assessment
                """,
                command="billing-analysis",
                examples=[
                    "billing-analysis --start-date 2025-01-01 --end-date 2025-01-31",
                    "billing-analysis --time-period month --include-details",
                    "billing-analysis --start-date 2025-01-01 --end-date 2025-03-31"
                ],
                tags=["billing", "subscription", "payment", "revenue", "financial"]
            ),
            
            DocumentationEntry(
                title="Technical Analysis",
                content="""
                The tech-analysis command analyzes technical troubleshooting conversations,
                API issues, integration problems, and technical support requests.
                
                Categories:
                - API integration issues
                - Technical troubleshooting
                - System errors and bugs
                - Performance problems
                """,
                command="tech-analysis",
                examples=[
                    "tech-analysis --category API --start-date 2025-01-01 --end-date 2025-01-31",
                    "tech-analysis --start-date 2025-01-01 --end-date 2025-01-31",
                    "tech-analysis --category integration --time-period month"
                ],
                tags=["technical", "api", "troubleshooting", "integration", "bugs", "errors"]
            ),
            
            DocumentationEntry(
                title="Product Analysis",
                content="""
                The product-analysis command focuses on product-related questions, feature
                requests, and user feedback about product functionality.
                
                Areas of focus:
                - Feature requests and suggestions
                - Product usage questions
                - Functionality inquiries
                - User experience feedback
                """,
                command="product-analysis",
                examples=[
                    "product-analysis --category features --start-date 2025-01-01 --end-date 2025-01-31",
                    "product-analysis --include-feedback --time-period month",
                    "product-analysis --start-date 2025-01-01 --end-date 2025-03-31"
                ],
                tags=["product", "features", "functionality", "feedback", "requests"]
            ),
            
            DocumentationEntry(
                title="Sites Analysis",
                content="""
                The sites-analysis command analyzes conversations related to site management,
                account administration, and platform configuration.
                
                Topics covered:
                - Site setup and configuration
                - Account management issues
                - Platform administration
                - User access and permissions
                """,
                command="sites-analysis",
                examples=[
                    "sites-analysis --start-date 2025-01-01 --end-date 2025-01-31",
                    "sites-analysis --include-details --time-period month",
                    "sites-analysis --start-date 2025-01-01 --end-date 2025-03-31"
                ],
                tags=["sites", "accounts", "administration", "configuration", "management"]
            ),
            
            DocumentationEntry(
                title="Custom Filtering",
                content="""
                Advanced filtering capabilities allow you to create custom reports by combining
                multiple criteria such as agent, category, date range, language, and sentiment.
                
                Filter options:
                - Agent-specific analysis
                - Category-based filtering
                - Date range customization
                - Language filtering
                - Sentiment-based analysis
                """,
                command="custom-filter",
                examples=[
                    "Filter by agent: horatio",
                    "Filter by category: API",
                    "Filter by date range: 2025-01-01 to 2025-01-31",
                    "Filter by language: en",
                    "Filter by sentiment: positive"
                ],
                tags=["filter", "custom", "agent", "category", "date", "language", "sentiment"]
            ),
            
            DocumentationEntry(
                title="Time Period Options",
                content="""
                Most analysis commands support flexible time period options for different
                reporting needs.
                
                Time period options:
                - --time-period week: Last 7 days
                - --time-period month: Last 30 days
                - --time-period quarter: Last 90 days
                - --time-period year: Last 365 days
                - Custom date ranges with --start-date and --end-date
                """,
                command="time-periods",
                examples=[
                    "--time-period week",
                    "--time-period month",
                    "--start-date 2025-01-01 --end-date 2025-01-31",
                    "--time-period quarter"
                ],
                tags=["time", "period", "date", "range", "week", "month", "quarter", "year"]
            ),
            
            DocumentationEntry(
                title="Output Options",
                content="""
                Analysis commands support various output formats and integrations for
                different use cases.
                
                Output options:
                - --generate-gamma: Create Gamma presentation
                - --export-docs: Export detailed documentation
                - --include-canny: Include Canny feedback data
                - --include-details: Include detailed breakdowns
                - --output-format: Specify output format
                """,
                command="output-options",
                examples=[
                    "--generate-gamma",
                    "--export-docs",
                    "--include-canny",
                    "--include-details",
                    "--output-format json"
                ],
                tags=["output", "gamma", "export", "canny", "details", "format"]
            )
        ]
    
    def _calculate_relevance(self, query: str, doc_entry: DocumentationEntry) -> float:
        """Calculate relevance score between query and documentation entry."""
        query_lower = query.lower()
        content_lower = doc_entry.content.lower()
        title_lower = doc_entry.title.lower()
        
        score = 0.0
        
        # Title matching (highest weight)
        title_words = set(title_lower.split())
        query_words = set(query_lower.split())
        title_overlap = len(title_words.intersection(query_words))
        if title_words:
            score += (title_overlap / len(title_words)) * 0.4
        
        # Content matching
        content_words = set(content_lower.split())
        content_overlap = len(content_words.intersection(query_words))
        if content_words:
            score += (content_overlap / len(content_words)) * 0.3
        
        # Tag matching
        tag_matches = sum(1 for tag in doc_entry.tags if tag in query_lower)
        if doc_entry.tags:
            score += (tag_matches / len(doc_entry.tags)) * 0.2
        
        # Example matching
        example_matches = 0
        for example in doc_entry.examples:
            example_words = set(example.lower().split())
            example_overlap = len(example_words.intersection(query_words))
            if example_words:
                example_matches += example_overlap / len(example_words)
        
        if doc_entry.examples:
            score += (example_matches / len(doc_entry.examples)) * 0.1
        
        return min(score, 1.0)
    
    def _retrieve_relevant_docs(self, query: str, top_k: int = 3) -> List[DocumentationEntry]:
        """Retrieve most relevant documentation entries for the query."""
        # Calculate relevance scores
        for doc in self.documentation:
            doc.relevance_score = self._calculate_relevance(query, doc)
        
        # Sort by relevance and return top-k
        sorted_docs = sorted(
            self.documentation,
            key=lambda x: x.relevance_score,
            reverse=True
        )
        
        # Filter out low-relevance entries
        relevant_docs = [doc for doc in sorted_docs if doc.relevance_score > 0.1]
        
        return relevant_docs[:top_k]
    
    def _extract_parameters_from_context(self, query: str, docs: List[DocumentationEntry]) -> Dict[str, Any]:
        """Extract parameters from query using retrieved documentation context."""
        parameters = {}
        query_lower = query.lower()
        
        # Extract date patterns
        date_patterns = [
            (r"last week", "time_period", "week"),
            (r"this week", "time_period", "week"),
            (r"last month", "time_period", "month"),
            (r"this month", "time_period", "month"),
            (r"last quarter", "time_period", "quarter"),
            (r"this quarter", "time_period", "quarter"),
            (r"last year", "time_period", "year"),
            (r"this year", "time_period", "year"),
        ]
        
        for pattern, param_name, param_value in date_patterns:
            if re.search(pattern, query_lower):
                parameters[param_name] = param_value
                break
        
        # Extract specific dates
        date_range_pattern = r"(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})"
        date_match = re.search(date_range_pattern, query)
        if date_match:
            parameters["start_date"] = date_match.group(1)
            parameters["end_date"] = date_match.group(2)
        
        # Extract boolean flags
        if "with gamma" in query_lower or "gamma presentation" in query_lower:
            parameters["generate_gamma"] = True
        
        if "with canny" in query_lower or "include canny" in query_lower:
            parameters["include_canny"] = True
        
        if "with details" in query_lower or "detailed" in query_lower:
            parameters["include_details"] = True
        
        if "export" in query_lower or "documentation" in query_lower:
            parameters["export_docs"] = True
        
        if "feedback" in query_lower:
            parameters["include_feedback"] = True
        
        # Extract categories
        category_patterns = [
            (r"api", "category", "API"),
            (r"billing", "category", "billing"),
            (r"technical", "category", "technical"),
            (r"product", "category", "product"),
            (r"features", "category", "features"),
            (r"integration", "category", "integration"),
        ]
        
        for pattern, param_name, param_value in category_patterns:
            if re.search(pattern, query_lower):
                parameters[param_name] = param_value
                break
        
        # Extract agent names
        agent_pattern = r"(?:by|from)\s+(\w+)"
        agent_match = re.search(agent_pattern, query_lower)
        if agent_match:
            parameters["agent"] = agent_match.group(1)
        
        return parameters
    
    def _determine_command_from_docs(self, docs: List[DocumentationEntry]) -> Optional[str]:
        """Determine the most appropriate command from retrieved documentation."""
        if not docs:
            return None
        
        # Use the highest relevance document's command
        best_doc = docs[0]
        return best_doc.command
    
    def _build_command_from_docs(self, command: str, parameters: Dict[str, Any]) -> List[str]:
        """Build command arguments from documentation and parameters."""
        args = [command]
        
        # Add parameters as flags
        for key, value in parameters.items():
            if value is None or value == "":
                continue
            
            if isinstance(value, bool):
                if value:
                    args.append(f"--{key.replace('_', '-')}")
            elif isinstance(value, str):
                if key in ["start_date", "end_date"]:
                    args.extend([f"--{key.replace('_', '-')}", value])
                elif key == "time_period":
                    args.extend(["--time-period", value])
                elif key == "ai_model":
                    args.extend(["--ai-model", value])
                else:
                    args.extend([f"--{key.replace('_', '-')}", value])
            elif isinstance(value, int):
                args.extend([f"--{key.replace('_', '-')}", str(value)])
        
        return args
    
    def translate(self, query: str, context: Optional[Dict] = None) -> CommandTranslation:
        """
        Translate query using RAG approach.
        
        Args:
            query: User's natural language input
            context: Additional context for translation
            
        Returns:
            CommandTranslation with command and parameters
        """
        start_time = time.time()
        
        try:
            # Retrieve relevant documentation
            relevant_docs = self._retrieve_relevant_docs(query, top_k=3)
            
            if not relevant_docs or relevant_docs[0].relevance_score < 0.3:
                # Update stats for failed translation
                response_time = int((time.time() - start_time) * 1000)
                self._update_stats(False, 0.0, response_time)
                
                return create_safe_command_translation(
                    ActionType.CLARIFY_REQUEST,
                    "I couldn't find relevant documentation for your request. Could you provide more details?",
                    confidence=0.0,
                    suggestions=[
                        "Try: 'Give me last week's voice of customer report'",
                        "Try: 'Show me billing analysis for this month'",
                        "Try: 'Run comprehensive analysis with Gamma presentation'"
                    ]
                )
            
            # Extract parameters using retrieved context
            parameters = self._extract_parameters_from_context(query, relevant_docs)
            
            # Determine command
            command = self._determine_command_from_docs(relevant_docs)
            if not command:
                return create_safe_command_translation(
                    ActionType.CLARIFY_REQUEST,
                    "I couldn't determine the appropriate command for your request.",
                    confidence=0.0
                )
            
            # Build command arguments
            command_args = self._build_command_from_docs(command, parameters)
            
            # Calculate confidence based on relevance scores
            confidence = min(relevant_docs[0].relevance_score * 1.2, 1.0)
            
            # Calculate risk score
            risk_score = 2.0  # RAG is slightly higher risk than function calling
            
            # Generate explanation
            explanation = self._generate_explanation(command, parameters, relevant_docs[0])
            
            # Update stats
            response_time = int((time.time() - start_time) * 1000)
            self._update_stats(True, relevant_docs[0].relevance_score, response_time)
            
            return create_safe_command_translation(
                ActionType.EXECUTE_COMMAND,
                explanation,
                command=command_args[0] if command_args else None,
                args=command_args[1:] if len(command_args) > 1 else [],
                confidence=confidence,
                risk_score=risk_score,
                processing_time_ms=response_time,
                model_used=ModelType.GPT_4O_MINI
            )
            
        except Exception as e:
            self.logger.error(f"RAG translation failed: {e}")
            self._update_stats(False, 0.0, int((time.time() - start_time) * 1000))
            
            return create_safe_command_translation(
                ActionType.CLARIFY_REQUEST,
                f"Sorry, I encountered an error processing your request: {str(e)}",
                confidence=0.0,
                warnings=[f"RAG translation error: {str(e)}"]
            )
    
    def _generate_explanation(self, command: str, parameters: Dict[str, Any], 
                            doc_entry: DocumentationEntry) -> str:
        """Generate explanation using retrieved documentation."""
        base_explanation = f"Execute {doc_entry.title.lower()}"
        
        # Add parameter details
        details = []
        if "time_period" in parameters:
            details.append(f"for {parameters['time_period']}")
        elif "start_date" in parameters:
            details.append(f"from {parameters['start_date']}")
            if "end_date" in parameters:
                details.append(f"to {parameters['end_date']}")
        
        if "generate_gamma" in parameters and parameters["generate_gamma"]:
            details.append("with Gamma presentation")
        
        if "include_canny" in parameters and parameters["include_canny"]:
            details.append("including Canny feedback")
        
        if "category" in parameters:
            details.append(f"focusing on {parameters['category']} topics")
        
        if "agent" in parameters:
            details.append(f"by agent {parameters['agent']}")
        
        if details:
            return f"{base_explanation} {' '.join(details)}"
        else:
            return base_explanation
    
    def _update_stats(self, success: bool, relevance_score: float, response_time_ms: int):
        """Update performance statistics."""
        self.stats["total_queries"] += 1
        
        if success:
            self.stats["successful_retrievals"] += 1
        else:
            self.stats["failed_retrievals"] += 1
        
        # Update average relevance score
        if self.stats["total_queries"] == 1:
            self.stats["average_relevance_score"] = relevance_score
            self.stats["average_response_time_ms"] = response_time_ms
        else:
            # Running averages
            self.stats["average_relevance_score"] = (
                (self.stats["average_relevance_score"] * (self.stats["total_queries"] - 1) + relevance_score)
                / self.stats["total_queries"]
            )
            self.stats["average_response_time_ms"] = (
                (self.stats["average_response_time_ms"] * (self.stats["total_queries"] - 1) + response_time_ms)
                / self.stats["total_queries"]
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        stats = self.stats.copy()
        if stats["total_queries"] > 0:
            stats["success_rate"] = stats["successful_retrievals"] / stats["total_queries"]
        else:
            stats["success_rate"] = 0.0
        return stats
    
    def get_documentation_summary(self) -> Dict[str, Any]:
        """Get summary of available documentation."""
        return {
            "total_entries": len(self.documentation),
            "commands_covered": list(set(doc.command for doc in self.documentation)),
            "topics_covered": list(set(tag for doc in self.documentation for tag in doc.tags))
        }
