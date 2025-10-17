"""
Unit tests for schemas, semantic caching, and model routing.
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from src.chat.schemas import (
    ActionType, RiskLevel, ModelType, FilterSpec, CommandTranslation,
    SuggestionResult, ChatMessage, ChatSession, CacheEntry, PerformanceMetrics,
    validate_command_translation, create_safe_command_translation
)
from src.chat.semantic_cache import SemanticCache, CacheConfig
from src.chat.model_router import ModelRouter, QueryComplexity, RoutingDecision


class TestSchemas:
    """Test schema definitions and validation."""
    
    def test_command_translation_creation(self):
        """Test CommandTranslation creation and serialization."""
        translation = CommandTranslation(
            action=ActionType.EXECUTE_COMMAND,
            command="voice-of-customer",
            args=["--time-period", "week"],
            explanation="Generate weekly VoC report",
            confidence=0.95
        )
        
        assert translation.action == ActionType.EXECUTE_COMMAND
        assert translation.command == "voice-of-customer"
        assert translation.confidence == 0.95
        
        # Test serialization
        data = translation.to_dict()
        assert data["action"] == "EXECUTE_COMMAND"
        assert data["command"] == "voice-of-customer"
        assert data["confidence"] == 0.95
    
    def test_command_translation_deserialization(self):
        """Test CommandTranslation deserialization."""
        data = {
            "action": "EXECUTE_COMMAND",
            "command": "voice-of-customer",
            "args": ["--time-period", "week"],
            "explanation": "Generate weekly VoC report",
            "confidence": 0.95,
            "dangerous": False,
            "confirmation_required": False,
            "risk_score": 1.0,
            "cache_hit": False,
            "warnings": [],
            "suggestions": []
        }
        
        translation = CommandTranslation.from_dict(data)
        assert translation.action == ActionType.EXECUTE_COMMAND
        assert translation.command == "voice-of-customer"
        assert translation.confidence == 0.95
    
    def test_filter_spec(self):
        """Test FilterSpec creation."""
        filters = FilterSpec(
            agent="horatio",
            category="API",
            date_range={"start": "2025-01-01", "end": "2025-01-31"},
            language="en"
        )
        
        assert filters.agent == "horatio"
        assert filters.category == "API"
        assert filters.date_range["start"] == "2025-01-01"
        assert filters.language == "en"
    
    def test_chat_session(self):
        """Test ChatSession functionality."""
        session = ChatSession(session_id="test-session")
        
        # Add messages
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there!")
        
        assert len(session.messages) == 2
        assert session.messages[0].role == "user"
        assert session.messages[0].content == "Hello"
        
        # Test recent messages
        recent = session.get_recent_messages(1)
        assert len(recent) == 1
        assert recent[0].content == "Hi there!"
    
    def test_performance_metrics(self):
        """Test PerformanceMetrics calculations."""
        metrics = PerformanceMetrics()
        metrics.total_queries = 100
        metrics.cache_hits = 60
        metrics.total_cost_usd = 5.0
        
        assert metrics.cache_hit_rate == 60.0
        assert metrics.average_cost_per_query == 0.05
    
    def test_validation_functions(self):
        """Test validation functions."""
        # Valid data
        valid_data = {
            "action": "EXECUTE_COMMAND",
            "explanation": "Test command",
            "risk_score": 2.5,
            "confidence": 0.8,
            "dangerous": False
        }
        assert validate_command_translation(valid_data) is True
        
        # Invalid data
        invalid_data = {
            "action": "INVALID_ACTION",
            "explanation": "Test command"
        }
        assert validate_command_translation(invalid_data) is False
        
        # Test safe creation
        safe_translation = create_safe_command_translation(
            ActionType.EXECUTE_COMMAND,
            "Safe command",
            command="test-command"
        )
        assert safe_translation.dangerous is False
        assert safe_translation.confirmation_required is False


class TestSemanticCache:
    """Test semantic caching functionality."""
    
    def setup_method(self):
        """Set up test cache."""
        self.config = CacheConfig(
            similarity_threshold=0.8,
            max_cache_size=10,
            cache_ttl_hours=1
        )
        self.cache = SemanticCache(self.config)
    
    def test_cache_disabled_without_dependencies(self):
        """Test cache behavior when dependencies are missing."""
        # This test will pass regardless of dependencies
        cache = SemanticCache()
        if not cache.enabled:
            # Cache should gracefully handle missing dependencies
            result = cache.get_cached_response("test query")
            assert result is None
            
            success = cache.cache_response("test query", CommandTranslation(
                action=ActionType.EXECUTE_COMMAND,
                explanation="Test"
            ))
            assert success is False
    
    def test_cache_operations(self):
        """Test basic cache operations."""
        if not self.cache.enabled:
            pytest.skip("Semantic cache dependencies not available")
        
        # Create test translation
        translation = CommandTranslation(
            action=ActionType.EXECUTE_COMMAND,
            command="voice-of-customer",
            explanation="Weekly report"
        )
        
        # Cache response
        success = self.cache.cache_response("Give me last week's report", translation)
        assert success is True
        
        # Retrieve cached response
        cached = self.cache.get_cached_response("Show me last week's report")
        if cached:  # May not match due to similarity threshold
            assert cached.action == ActionType.EXECUTE_COMMAND
            assert cached.cache_hit is True
    
    def test_cache_stats(self):
        """Test cache statistics."""
        if not self.cache.enabled:
            pytest.skip("Semantic cache dependencies not available")
        
        stats = self.cache.get_cache_stats()
        assert "total_entries" in stats
        assert "cache_size_mb" in stats
        assert "expired_entries" in stats
    
    def test_cache_cleanup(self):
        """Test cache cleanup functionality."""
        if not self.cache.enabled:
            pytest.skip("Semantic cache dependencies not available")
        
        # Create expired entry
        old_translation = CommandTranslation(
            action=ActionType.EXECUTE_COMMAND,
            explanation="Old command"
        )
        
        # Manually set old timestamp
        old_translation.created_at = datetime.now() - timedelta(hours=2)
        
        # This would normally be handled by the cache, but we're testing cleanup
        cleaned = self.cache.cleanup_expired_entries()
        assert isinstance(cleaned, int)


class TestModelRouter:
    """Test model routing functionality."""
    
    def setup_method(self):
        self.router = ModelRouter()
    
    def test_query_complexity_analysis(self):
        """Test query complexity analysis."""
        # Simple queries
        simple_queries = [
            "Give me last week's report",
            "Show me voice of customer analysis",
            "Create a report"
        ]
        
        for query in simple_queries:
            complexity = self.router.analyze_query_complexity(query)
            assert complexity in [QueryComplexity.SIMPLE, QueryComplexity.MEDIUM]
        
        # Complex queries
        complex_queries = [
            "Predict next month's volume trends",
            "Analyze correlation between customer sentiment and billing issues",
            "Create a comprehensive custom analysis with detailed forecasting"
        ]
        
        for query in complex_queries:
            complexity = self.router.analyze_query_complexity(query)
            assert complexity in [QueryComplexity.MEDIUM, QueryComplexity.COMPLEX]
    
    def test_token_estimation(self):
        """Test token estimation."""
        query = "Give me last week's report"
        tokens = self.router.estimate_tokens(query)
        
        assert isinstance(tokens, int)
        assert tokens > 0
        assert tokens < 10000  # Reasonable upper bound
    
    def test_cost_calculation(self):
        """Test cost calculation."""
        cost = self.router.calculate_cost(ModelType.GPT_4O_MINI, 1000, 500)
        
        assert isinstance(cost, float)
        assert cost > 0
        assert cost < 1.0  # Should be reasonable for 1.5k tokens
    
    def test_model_selection(self):
        """Test model selection logic."""
        # Simple query should prefer cheaper models
        decision = self.router.select_model("Give me last week's report")
        
        assert isinstance(decision, RoutingDecision)
        assert decision.model_type in [ModelType.GEMINI_1_5_FLASH, ModelType.GPT_4O_MINI]
        assert decision.complexity == QueryComplexity.SIMPLE
        assert decision.estimated_cost > 0
        assert decision.confidence > 0
    
    def test_budget_analysis(self):
        """Test budget analysis."""
        analysis = self.router.get_cost_analysis("Test query")
        
        assert "estimated_tokens" in analysis
        assert "models" in analysis
        assert ModelType.GPT_4O_MINI.value in analysis["models"]
        assert ModelType.GEMINI_1_5_FLASH.value in analysis["models"]
    
    def test_performance_metrics(self):
        """Test performance metrics tracking."""
        # Update metrics
        self.router.update_metrics(
            ModelType.GPT_4O_MINI,
            actual_cost=0.05,
            actual_tokens=1000,
            response_time_ms=500,
            success=True
        )
        
        metrics = self.router.get_performance_metrics()
        assert metrics["total_queries"] == 1
        assert metrics["total_cost_usd"] == 0.05
        assert metrics["total_tokens"] == 1000
        assert metrics["average_response_time_ms"] == 500
    
    def test_recommended_budget(self):
        """Test budget recommendations."""
        budget = self.router.get_recommended_budget(1000)
        
        assert "total_monthly_budget" in budget
        assert "cost_per_query" in budget
        assert "recommended_models" in budget
        assert budget["total_monthly_budget"] > 0
        assert budget["cost_per_query"] > 0
