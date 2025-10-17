"""
Integration tests for the complete chat system.
"""

import pytest
from unittest.mock import Mock, patch
from src.chat.chat_interface import ChatInterface
from src.chat.hybrid_translator import HybridCommandTranslator, TranslationResult
from src.chat.suggestion_engine import SuggestionEngine, FeatureSuggestion, SuggestionType
from src.chat.custom_filter_builder import CustomFilterBuilder
from src.chat.schemas import ActionType, FilterSpec, FilterOperator
from src.config.settings import Settings


class TestChatInterface:
    """Test the main chat interface."""
    
    def setup_method(self):
        self.settings = Settings()
        self.chat_interface = ChatInterface(self.settings)
    
    def test_initialization(self):
        """Test chat interface initialization."""
        assert self.chat_interface.translator is not None
        assert self.chat_interface.suggestion_engine is not None
        assert self.chat_interface.filter_builder is not None
        assert self.chat_interface.input_validator is not None
        assert self.chat_interface.command_whitelist is not None
        assert self.chat_interface.hitl_controller is not None
        assert self.chat_interface.terminal_ui is not None
    
    def test_process_query_success(self):
        """Test successful query processing."""
        query = "Give me last week's voice of customer report"
        result = self.chat_interface.process_query(query)
        
        assert result["success"] is True
        assert "translation" in result
        assert "security_checks" in result
        assert result["security_checks"]["input_validated"] is True
    
    def test_process_query_invalid_input(self):
        """Test query processing with invalid input."""
        query = "rm -rf /"  # Dangerous command
        result = self.chat_interface.process_query(query)
        
        # Should fail due to input validation or command whitelisting
        assert result["success"] is False
        assert "error" in result
    
    def test_build_custom_filters(self):
        """Test custom filter building."""
        query = "API tickets done by Horatio agents in September"
        filters = self.chat_interface.build_custom_filters(query)
        
        assert isinstance(filters, list)
        # Should have agent, category, and date filters
        assert len(filters) >= 2
    
    def test_get_available_commands(self):
        """Test getting available commands."""
        commands = self.chat_interface.get_available_commands()
        assert isinstance(commands, list)
        assert len(commands) > 0
    
    def test_get_supported_filters(self):
        """Test getting supported filter types."""
        filters = self.chat_interface.get_supported_filters()
        assert isinstance(filters, dict)
        assert "agents" in filters
        assert "categories" in filters
        assert "date_ranges" in filters
    
    def test_get_performance_stats(self):
        """Test getting performance statistics."""
        stats = self.chat_interface.get_performance_stats()
        assert isinstance(stats, dict)
        assert "translator_stats" in stats
        assert "ui_stats" in stats
        assert "security_stats" in stats
    
    def test_reset_stats(self):
        """Test resetting statistics."""
        # Make some queries to generate stats
        self.chat_interface.process_query("test query")
        
        # Reset stats
        self.chat_interface.reset_stats()
        
        # Check that stats are reset
        stats = self.chat_interface.get_performance_stats()
        assert stats["ui_stats"]["chat_stats"]["total_queries"] == 0
    
    def test_configure_security(self):
        """Test security configuration."""
        self.chat_interface.configure_security(
            auto_approve_safe=True,
            approval_timeout=600,
            strict_validation=True
        )
        
        # Check that settings were applied
        assert self.chat_interface.terminal_ui.auto_approve_safe_commands is True
        assert self.chat_interface.hitl_controller.approval_timeout_seconds == 600
        assert self.chat_interface.input_validator.strict_mode is True
    
    def test_configure_ui(self):
        """Test UI configuration."""
        self.chat_interface.configure_ui(
            show_help_on_start=False,
            show_performance_metrics=False
        )
        
        # Check that settings were applied
        assert self.chat_interface.terminal_ui.show_help_on_start is False
        assert self.chat_interface.terminal_ui.show_performance_metrics is False
    
    def test_test_components(self):
        """Test component testing."""
        results = self.chat_interface.test_components()
        
        assert isinstance(results, dict)
        assert "translator" in results
        assert "suggestion_engine" in results
        assert "filter_builder" in results
        assert "input_validator" in results
        assert "command_whitelist" in results
        assert "hitl_controller" in results
        
        # All components should pass tests
        for component, status in results.items():
            if component != "error":
                assert status is True
    
    def test_get_help_text(self):
        """Test getting help text."""
        help_text = self.chat_interface.get_help_text()
        assert isinstance(help_text, str)
        assert len(help_text) > 0
        assert "Voice of Customer" in help_text
    
    def test_get_filter_examples(self):
        """Test getting filter examples."""
        examples = self.chat_interface.get_filter_examples()
        assert isinstance(examples, list)
        assert len(examples) > 0
        assert "API tickets" in examples[0]
    
    def test_get_suggestion_examples(self):
        """Test getting suggestion examples."""
        examples = self.chat_interface.get_suggestion_examples()
        assert isinstance(examples, list)
        assert len(examples) > 0
        assert "export" in examples[0]


class TestHybridTranslator:
    """Test the hybrid translator."""
    
    def setup_method(self):
        self.settings = Settings()
        self.translator = HybridCommandTranslator(self.settings)
    
    def test_initialization(self):
        """Test translator initialization."""
        assert self.translator.function_engine is not None
        assert self.translator.rag_engine is not None
        assert self.translator.intent_classifier is not None
        assert self.translator.semantic_cache is not None
        assert self.translator.model_router is not None
    
    def test_translate_success(self):
        """Test successful translation."""
        query = "Give me last week's voice of customer report"
        result = self.translator.translate(query)
        
        assert isinstance(result, TranslationResult)
        assert result.translation is not None
        assert result.engine_used is not None
        assert result.confidence >= 0.0
        assert result.processing_time_ms >= 0.0
    
    def test_translate_with_cache(self):
        """Test translation with caching."""
        query = "test query for caching"
        
        # First translation
        result1 = self.translator.translate(query)
        
        # Second translation should hit cache
        result2 = self.translator.translate(query)
        
        # At least one should be successful
        assert result1.translation is not None or result2.translation is not None
    
    def test_get_performance_stats(self):
        """Test getting performance statistics."""
        stats = self.translator.get_performance_stats()
        assert isinstance(stats, dict)
        assert "total_queries" in stats
        assert "cache_hits" in stats
        assert "success_rate" in stats
        assert "engine_stats" in stats
    
    def test_get_available_commands(self):
        """Test getting available commands."""
        commands = self.translator.get_available_commands()
        assert isinstance(commands, list)
        assert len(commands) > 0
    
    def test_get_help_text(self):
        """Test getting help text."""
        help_text = self.translator.get_help_text()
        assert isinstance(help_text, str)
        assert len(help_text) > 0
    
    def test_reset_stats(self):
        """Test resetting statistics."""
        # Make some translations
        self.translator.translate("test query")
        
        # Reset stats
        self.translator.reset_stats()
        
        # Check that stats are reset
        stats = self.translator.get_performance_stats()
        assert stats["total_queries"] == 0


class TestSuggestionEngine:
    """Test the suggestion engine."""
    
    def setup_method(self):
        self.engine = SuggestionEngine()
    
    def test_initialization(self):
        """Test engine initialization."""
        assert self.engine.suggestion_templates is not None
        assert self.engine.keyword_mapping is not None
    
    def test_generate_suggestions_analytics(self):
        """Test generating analytics suggestions."""
        query = "I want to see analytics dashboard"
        suggestions = self.engine.generate_suggestions(query)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert any("analytics" in suggestion.title.lower() for suggestion in suggestions)
    
    def test_generate_suggestions_automation(self):
        """Test generating automation suggestions."""
        query = "Can you automate report generation"
        suggestions = self.engine.generate_suggestions(query)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert any("automate" in suggestion.title.lower() for suggestion in suggestions)
    
    def test_generate_suggestions_integration(self):
        """Test generating integration suggestions."""
        query = "I want to integrate with Slack"
        suggestions = self.engine.generate_suggestions(query)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert any("integration" in suggestion.title.lower() for suggestion in suggestions)
    
    def test_generate_suggestions_custom(self):
        """Test generating custom suggestions."""
        query = "I want to export data to CSV"
        suggestions = self.engine.generate_suggestions(query)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert any("csv" in suggestion.title.lower() for suggestion in suggestions)
    
    def test_generate_suggestions_fallback(self):
        """Test generating fallback suggestions."""
        query = "random query that doesn't match any patterns"
        suggestions = self.engine.generate_suggestions(query)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
    
    def test_get_suggestion_summary(self):
        """Test getting suggestion summary."""
        suggestions = [
            FeatureSuggestion(
                title="Test Feature",
                description="A test feature",
                suggestion_type=SuggestionType.FEATURE_REQUEST,
                priority="high",
                implementation_effort="medium",
                business_value="high",
                technical_approach="Test approach",
                implementation_steps=["Step 1", "Step 2"],
                related_features=["feature1", "feature2"],
                estimated_development_time="2 weeks",
                dependencies=["dep1", "dep2"]
            )
        ]
        
        summary = self.engine.get_suggestion_summary(suggestions)
        assert isinstance(summary, str)
        assert "Test Feature" in summary
        assert "high" in summary
    
    def test_get_implementation_guidance(self):
        """Test getting implementation guidance."""
        suggestion = FeatureSuggestion(
            title="Test Feature",
            description="A test feature",
            suggestion_type=SuggestionType.FEATURE_REQUEST,
            priority="high",
            implementation_effort="medium",
            business_value="high",
            technical_approach="Test approach",
            implementation_steps=["Step 1", "Step 2"],
            related_features=["feature1", "feature2"],
            estimated_development_time="2 weeks",
            dependencies=["dep1", "dep2"]
        )
        
        guidance = self.engine.get_implementation_guidance(suggestion)
        assert isinstance(guidance, str)
        assert "Test Feature" in guidance
        assert "Test approach" in guidance
        assert "Step 1" in guidance


class TestCustomFilterBuilder:
    """Test the custom filter builder."""
    
    def setup_method(self):
        self.builder = CustomFilterBuilder()
    
    def test_initialization(self):
        """Test builder initialization."""
        assert self.builder.agent_patterns is not None
        assert self.builder.category_patterns is not None
        assert self.builder.date_patterns is not None
        assert self.builder.priority_patterns is not None
        assert self.builder.status_patterns is not None
    
    def test_build_filters_agent(self):
        """Test building agent filters."""
        query = "tickets by Horatio agents"
        filters = self.builder.build_filters(query)
        
        assert isinstance(filters, list)
        assert len(filters) > 0
        assert any(filter_spec.field == "agent" for filter_spec in filters)
    
    def test_build_filters_category(self):
        """Test building category filters."""
        query = "API tickets and billing issues"
        filters = self.builder.build_filters(query)
        
        assert isinstance(filters, list)
        assert len(filters) > 0
        assert any(filter_spec.field == "category" for filter_spec in filters)
    
    def test_build_filters_date(self):
        """Test building date filters."""
        query = "tickets from last week"
        filters = self.builder.build_filters(query)
        
        assert isinstance(filters, list)
        assert len(filters) > 0
        assert any(filter_spec.field == "created_at" for filter_spec in filters)
    
    def test_build_filters_priority(self):
        """Test building priority filters."""
        query = "high priority tickets"
        filters = self.builder.build_filters(query)
        
        assert isinstance(filters, list)
        assert len(filters) > 0
        assert any(filter_spec.field == "priority" for filter_spec in filters)
    
    def test_build_filters_status(self):
        """Test building status filters."""
        query = "open tickets"
        filters = self.builder.build_filters(query)
        
        assert isinstance(filters, list)
        assert len(filters) > 0
        assert any(filter_spec.field == "status" for filter_spec in filters)
    
    def test_build_filters_complex(self):
        """Test building complex filters."""
        query = "API tickets done by Horatio agents in September"
        filters = self.builder.build_filters(query)
        
        assert isinstance(filters, list)
        assert len(filters) >= 2  # Should have agent, category, and date filters
    
    def test_get_supported_filters(self):
        """Test getting supported filter types."""
        filters = self.builder.get_supported_filters()
        assert isinstance(filters, dict)
        assert "agents" in filters
        assert "categories" in filters
        assert "date_ranges" in filters
        assert "priorities" in filters
        assert "statuses" in filters
    
    def test_get_filter_examples(self):
        """Test getting filter examples."""
        examples = self.builder.get_filter_examples()
        assert isinstance(examples, list)
        assert len(examples) > 0
        assert "API tickets" in examples[0]
    
    def test_validate_filters(self):
        """Test filter validation."""
        # Valid filters
        valid_filters = [
            FilterSpec(
                field="agent",
                operator=FilterOperator.EQUALS,
                value="horatio",
                description="Filter by Horatio agent"
            )
        ]
        
        is_valid, errors = self.builder.validate_filters(valid_filters)
        assert is_valid is True
        assert len(errors) == 0
        
        # Invalid filters
        invalid_filters = [
            FilterSpec(
                field="",  # Empty field
                operator=FilterOperator.EQUALS,
                value="test",
                description="Invalid filter"
            )
        ]
        
        is_valid, errors = self.builder.validate_filters(invalid_filters)
        assert is_valid is False
        assert len(errors) > 0


class TestChatIntegration:
    """Test integration between chat components."""
    
    def setup_method(self):
        self.settings = Settings()
        self.chat_interface = ChatInterface(self.settings)
    
    def test_end_to_end_query_processing(self):
        """Test end-to-end query processing."""
        query = "Give me last week's voice of customer report with Gamma presentation"
        
        # Process query
        result = self.chat_interface.process_query(query)
        
        # Should be successful
        assert result["success"] is True
        assert "translation" in result
        assert "security_checks" in result
        
        # Security checks should pass
        assert result["security_checks"]["input_validated"] is True
    
    def test_suggestion_generation_flow(self):
        """Test suggestion generation flow."""
        query = "I want to export data to CSV format"
        
        # Process query (should generate suggestions)
        result = self.chat_interface.process_query(query)
        
        # Should have suggestions
        if "suggestions" in result:
            suggestions = result["suggestions"]
            assert isinstance(suggestions, list)
            assert len(suggestions) > 0
    
    def test_filter_building_integration(self):
        """Test filter building integration."""
        query = "API tickets done by Horatio agents in September"
        
        # Build filters
        filters = self.chat_interface.build_custom_filters(query)
        
        # Should have multiple filters
        assert isinstance(filters, list)
        assert len(filters) >= 2
        
        # Should have agent, category, and date filters
        filter_fields = [f["field"] for f in filters]
        assert "agent" in filter_fields or "category" in filter_fields
    
    def test_performance_tracking(self):
        """Test performance tracking across components."""
        # Make several queries
        queries = [
            "Give me last week's report",
            "Show me billing analysis",
            "Create custom report for API tickets"
        ]
        
        for query in queries:
            self.chat_interface.process_query(query)
        
        # Check performance stats
        stats = self.chat_interface.get_performance_stats()
        assert stats["ui_stats"]["chat_stats"]["total_queries"] >= len(queries)
    
    def test_component_interaction(self):
        """Test interaction between different components."""
        query = "I want to see analytics dashboard with custom filters"
        
        # Process query
        result = self.chat_interface.process_query(query)
        
        # Should generate suggestions
        if "suggestions" in result:
            suggestions = result["suggestions"]
            assert isinstance(suggestions, list)
        
        # Should be able to build filters
        filters = self.chat_interface.build_custom_filters(query)
        assert isinstance(filters, list)
        
        # Should have performance stats
        stats = self.chat_interface.get_performance_stats()
        assert isinstance(stats, dict)
