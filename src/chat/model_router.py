"""
LLM model router for cost optimization.

Routes queries to appropriate models based on complexity and cost considerations,
achieving optimal balance between accuracy and cost.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .schemas import ModelType, CommandTranslation, ActionType, PerformanceMetrics

logger = logging.getLogger(__name__)


class QueryComplexity(Enum):
    """Query complexity levels."""
    SIMPLE = "simple"      # Basic commands, low cost
    MEDIUM = "medium"      # Moderate complexity, balanced cost
    COMPLEX = "complex"    # High complexity, premium cost


@dataclass
class ModelConfig:
    """Configuration for an LLM model."""
    model_type: ModelType
    cost_per_1k_input_tokens: float
    cost_per_1k_output_tokens: float
    max_tokens: int
    context_window: int
    accuracy_score: float  # 0-1 scale
    speed_score: float     # 0-1 scale
    suitable_for: List[QueryComplexity]


@dataclass
class RoutingDecision:
    """Decision about which model to use for a query."""
    model_type: ModelType
    complexity: QueryComplexity
    estimated_cost: float
    estimated_tokens: int
    confidence: float
    reasoning: str


class ModelRouter:
    """
    Routes queries to appropriate LLM models based on cost and complexity.
    
    Features:
    - Cost-aware model selection
    - Complexity-based routing
    - Performance tracking
    - Fallback strategies
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Model configurations (prices as of 2024)
        self.models = {
            ModelType.GEMINI_1_5_FLASH: ModelConfig(
                model_type=ModelType.GEMINI_1_5_FLASH,
                cost_per_1k_input_tokens=0.075,
                cost_per_1k_output_tokens=0.30,
                max_tokens=8192,
                context_window=128000,
                accuracy_score=0.85,
                speed_score=0.95,
                suitable_for=[QueryComplexity.SIMPLE, QueryComplexity.MEDIUM]
            ),
            
            ModelType.GPT_4O_MINI: ModelConfig(
                model_type=ModelType.GPT_4O_MINI,
                cost_per_1k_input_tokens=0.15,
                cost_per_1k_output_tokens=0.60,
                max_tokens=16384,
                context_window=128000,
                accuracy_score=0.90,
                speed_score=0.85,
                suitable_for=[QueryComplexity.SIMPLE, QueryComplexity.MEDIUM, QueryComplexity.COMPLEX]
            ),
            
            ModelType.CLAUDE_3_HAIKU: ModelConfig(
                model_type=ModelType.CLAUDE_3_HAIKU,
                cost_per_1k_input_tokens=0.25,
                cost_per_1k_output_tokens=1.25,
                max_tokens=4096,
                context_window=200000,
                accuracy_score=0.88,
                speed_score=0.80,
                suitable_for=[QueryComplexity.MEDIUM, QueryComplexity.COMPLEX]
            )
        }
        
        # Performance tracking
        self.metrics = PerformanceMetrics()
        
        # Routing rules
        self.routing_rules = {
            # Simple queries: basic commands, common patterns
            QueryComplexity.SIMPLE: [
                ModelType.GEMINI_1_5_FLASH,  # Cheapest
                ModelType.GPT_4O_MINI,       # Fallback
            ],
            
            # Medium queries: custom filters, moderate complexity
            QueryComplexity.MEDIUM: [
                ModelType.GPT_4O_MINI,       # Best balance
                ModelType.GEMINI_1_5_FLASH,  # Cheaper alternative
                ModelType.CLAUDE_3_HAIKU,    # Fallback
            ],
            
            # Complex queries: novel patterns, high accuracy needed
            QueryComplexity.COMPLEX: [
                ModelType.CLAUDE_3_HAIKU,    # Highest accuracy
                ModelType.GPT_4O_MINI,       # Fallback
            ]
        }
    
    def analyze_query_complexity(self, query: str, context: Optional[Dict] = None) -> QueryComplexity:
        """
        Analyze query complexity to determine appropriate model.
        
        Args:
            query: User's natural language query
            context: Additional context about the query
            
        Returns:
            QueryComplexity level
        """
        query_lower = query.lower().strip()
        
        # Simple queries: basic commands, common patterns
        simple_patterns = [
            "last week", "this week", "yesterday", "today",
            "voice of customer", "voc analysis", "generate report",
            "show me", "give me", "create", "run"
        ]
        
        # Complex queries: novel patterns, multiple requirements
        complex_patterns = [
            "predict", "forecast", "trend", "analysis",
            "custom", "specific", "detailed", "comprehensive",
            "compare", "correlate", "relationship", "pattern"
        ]
        
        # Check for simple patterns
        if any(pattern in query_lower for pattern in simple_patterns):
            # Additional check for complexity indicators
            if any(pattern in query_lower for pattern in complex_patterns):
                return QueryComplexity.MEDIUM
            return QueryComplexity.SIMPLE
        
        # Check for complex patterns
        if any(pattern in query_lower for pattern in complex_patterns):
            return QueryComplexity.COMPLEX
        
        # Check query length and structure
        word_count = len(query.split())
        if word_count <= 5:
            return QueryComplexity.SIMPLE
        elif word_count <= 15:
            return QueryComplexity.MEDIUM
        else:
            return QueryComplexity.COMPLEX
    
    def estimate_tokens(self, query: str, context: Optional[Dict] = None) -> int:
        """
        Estimate token count for query and context.
        
        Args:
            query: User's natural language query
            context: Additional context
            
        Returns:
            Estimated token count
        """
        # Rough estimation: 1 token ≈ 4 characters for English
        query_tokens = len(query) // 4
        
        # Add context tokens if provided
        context_tokens = 0
        if context:
            context_tokens = sum(len(str(v)) // 4 for v in context.values())
        
        # Add system prompt tokens (estimated)
        system_tokens = 500
        
        # Add response tokens (estimated)
        response_tokens = 200
        
        total_tokens = query_tokens + context_tokens + system_tokens + response_tokens
        return max(total_tokens, 100)  # Minimum estimate
    
    def calculate_cost(self, model_type: ModelType, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost for using a specific model.
        
        Args:
            model_type: Model to use
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Estimated cost in USD
        """
        if model_type not in self.models:
            return 0.0
        
        config = self.models[model_type]
        
        input_cost = (input_tokens / 1000) * config.cost_per_1k_input_tokens
        output_cost = (output_tokens / 1000) * config.cost_per_1k_output_tokens
        
        return input_cost + output_cost
    
    def select_model(self, query: str, context: Optional[Dict] = None, 
                    budget_limit: Optional[float] = None) -> RoutingDecision:
        """
        Select the best model for a query based on complexity and cost.
        
        Args:
            query: User's natural language query
            context: Additional context
            budget_limit: Maximum cost allowed (in USD)
            
        Returns:
            RoutingDecision with model selection and reasoning
        """
        # Analyze query complexity
        complexity = self.analyze_query_complexity(query, context)
        
        # Estimate tokens
        estimated_tokens = self.estimate_tokens(query, context)
        input_tokens = int(estimated_tokens * 0.7)  # 70% input, 30% output
        output_tokens = int(estimated_tokens * 0.3)
        
        # Get suitable models for complexity
        suitable_models = self.routing_rules.get(complexity, [ModelType.GPT_4O_MINI])
        
        # Calculate costs and select best model
        best_model = None
        best_cost = float('inf')
        best_confidence = 0.0
        
        for model_type in suitable_models:
            if model_type not in self.models:
                continue
            
            config = self.models[model_type]
            cost = self.calculate_cost(model_type, input_tokens, output_tokens)
            
            # Check budget limit
            if budget_limit and cost > budget_limit:
                continue
            
            # Calculate confidence based on accuracy and cost
            cost_efficiency = 1.0 / (cost + 0.001)  # Avoid division by zero
            confidence = (config.accuracy_score * 0.7) + (cost_efficiency * 0.3)
            
            if cost < best_cost or (cost == best_cost and confidence > best_confidence):
                best_model = model_type
                best_cost = cost
                best_confidence = confidence
        
        # Fallback to GPT-4o-mini if no model selected
        if best_model is None:
            best_model = ModelType.GPT_4O_MINI
            best_cost = self.calculate_cost(best_model, input_tokens, output_tokens)
            best_confidence = 0.8
        
        # Generate reasoning
        reasoning = self._generate_reasoning(complexity, best_model, best_cost, estimated_tokens)
        
        return RoutingDecision(
            model_type=best_model,
            complexity=complexity,
            estimated_cost=best_cost,
            estimated_tokens=estimated_tokens,
            confidence=best_confidence,
            reasoning=reasoning
        )
    
    def _generate_reasoning(self, complexity: QueryComplexity, model_type: ModelType, 
                          cost: float, tokens: int) -> str:
        """Generate human-readable reasoning for model selection."""
        config = self.models[model_type]
        
        reasoning_parts = [
            f"Selected {model_type.value} for {complexity.value} complexity query",
            f"Estimated cost: ${cost:.4f} for {tokens} tokens",
            f"Accuracy score: {config.accuracy_score:.2f}",
            f"Speed score: {config.speed_score:.2f}"
        ]
        
        if complexity == QueryComplexity.SIMPLE:
            reasoning_parts.append("Simple query optimized for cost efficiency")
        elif complexity == QueryComplexity.MEDIUM:
            reasoning_parts.append("Medium complexity balanced for cost and accuracy")
        else:
            reasoning_parts.append("Complex query prioritized for accuracy")
        
        return "; ".join(reasoning_parts)
    
    def update_metrics(self, model_type: ModelType, actual_cost: float, 
                      actual_tokens: int, response_time_ms: int, success: bool):
        """Update performance metrics after model usage."""
        self.metrics.total_queries += 1
        self.metrics.total_cost_usd += actual_cost
        self.metrics.total_tokens += actual_tokens
        
        if not success:
            self.metrics.error_count += 1
        
        # Update model usage
        model_name = model_type.value
        self.metrics.model_usage[model_name] = self.metrics.model_usage.get(model_name, 0) + 1
        
        # Update average response time
        if self.metrics.total_queries == 1:
            self.metrics.average_response_time_ms = response_time_ms
        else:
            # Running average
            self.metrics.average_response_time_ms = (
                (self.metrics.average_response_time_ms * (self.metrics.total_queries - 1) + response_time_ms) 
                / self.metrics.total_queries
            )
    
    def get_cost_analysis(self, query: str, context: Optional[Dict] = None) -> Dict[str, any]:
        """Get cost analysis for all available models."""
        estimated_tokens = self.estimate_tokens(query, context)
        input_tokens = int(estimated_tokens * 0.7)
        output_tokens = int(estimated_tokens * 0.3)
        
        analysis = {
            "estimated_tokens": estimated_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "models": {}
        }
        
        for model_type, config in self.models.items():
            cost = self.calculate_cost(model_type, input_tokens, output_tokens)
            analysis["models"][model_type.value] = {
                "cost_usd": round(cost, 4),
                "accuracy_score": config.accuracy_score,
                "speed_score": config.speed_score,
                "suitable_for": [c.value for c in config.suitable_for]
            }
        
        return analysis
    
    def get_performance_metrics(self) -> Dict[str, any]:
        """Get current performance metrics."""
        return self.metrics.to_dict()
    
    def reset_metrics(self):
        """Reset performance metrics."""
        self.metrics = PerformanceMetrics()
        self.logger.info("Performance metrics reset")
    
    def get_recommended_budget(self, queries_per_month: int) -> Dict[str, float]:
        """Get recommended budget allocation for monthly usage."""
        # Assume 70% simple, 20% medium, 10% complex queries
        simple_queries = int(queries_per_month * 0.7)
        medium_queries = int(queries_per_month * 0.2)
        complex_queries = int(queries_per_month * 0.1)
        
        # Average tokens per complexity level
        simple_tokens = 500
        medium_tokens = 1000
        complex_tokens = 2000
        
        # Calculate costs for each complexity level
        simple_cost = simple_queries * self.calculate_cost(
            ModelType.GEMINI_1_5_FLASH, 
            int(simple_tokens * 0.7), 
            int(simple_tokens * 0.3)
        )
        
        medium_cost = medium_queries * self.calculate_cost(
            ModelType.GPT_4O_MINI, 
            int(medium_tokens * 0.7), 
            int(medium_tokens * 0.3)
        )
        
        complex_cost = complex_queries * self.calculate_cost(
            ModelType.CLAUDE_3_HAIKU, 
            int(complex_tokens * 0.7), 
            int(complex_tokens * 0.3)
        )
        
        total_cost = simple_cost + medium_cost + complex_cost
        
        return {
            "total_monthly_budget": round(total_cost, 2),
            "simple_queries_cost": round(simple_cost, 2),
            "medium_queries_cost": round(medium_cost, 2),
            "complex_queries_cost": round(complex_cost, 2),
            "cost_per_query": round(total_cost / queries_per_month, 4),
            "recommended_models": {
                "simple": ModelType.GEMINI_1_5_FLASH.value,
                "medium": ModelType.GPT_4O_MINI.value,
                "complex": ModelType.CLAUDE_3_HAIKU.value
            }
        }
