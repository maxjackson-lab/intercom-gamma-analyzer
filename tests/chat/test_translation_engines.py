"""
Unit tests for translation engines.
"""

import pytest
from src.chat.engines.function_calling import FunctionCallingEngine
from src.chat.engines.rag_engine import RAGEngine
from src.chat.engines.intent_classifier import IntentClassifier, IntentType
from src.chat.schemas import ActionType, ModelType


class TestFunctionCallingEngine:
    """Test function calling engine."""
    
    def setup_method(self):
        self.engine = FunctionCallingEngine()
    
    def test_function_matching(self):
        """Test function matching logic."""
        # Test voice of customer matching
        query = "Give me last week's voice of customer report"
        func_name, confidence = self.engine._match_function(query)
        assert func_name == "voice_of_customer_analysis"
        assert confidence > 0.5
        
        # Test comprehensive analysis matching
        query = "Run comprehensive analysis for this month"
        func_name, confidence = self.engine._match_function(query)
        assert func_name == "comprehensive_analysis"
        assert confidence > 0.5
    
    def test_date_extraction(self):
        """Test date range extraction."""
        # Test relative dates
        start, end = self.engine._extract_date_range("last week's report")
        assert start is not None
        assert end is not None
        
        # Test specific dates
        start, end = self.engine._extract_date_range("from 2025-01-01 to 2025-01-31")
        assert start == "2025-01-01"
        assert end == "2025-01-31"
    
    def test_boolean_flag_extraction(self):
        """Test boolean flag extraction."""
        flags = self.engine._extract_boolean_flags("report with gamma presentation")
        assert flags.get("generate_gamma") is True
        
        flags = self.engine._extract_boolean_flags("analysis with canny feedback")
        assert flags.get("include_canny") is True
    
    def test_time_period_extraction(self):
        """Test time period extraction."""
        period = self.engine._extract_time_period("weekly report")
        assert period == "week"
        
        period = self.engine._extract_time_period("monthly analysis")
        assert period == "month"
    
    def test_command_building(self):
        """Test command argument building."""
        parameters = {
            "time_period": "week",
            "generate_gamma": True,
            "include_canny": True
        }
        
        args = self.engine._build_command_args("voice_of_customer_analysis", parameters)
        assert "voice-of-customer" in args
        assert "--time-period" in args
        assert "week" in args
        assert "--generate-gamma" in args
        assert "--include-canny" in args
    
    def test_translation(self):
        """Test complete translation process."""
        query = "Give me last week's voice of customer report with gamma"
        result = self.engine.translate(query)
        
        assert result.action == ActionType.EXECUTE_COMMAND
        assert result.command == "voice-of-customer"
        assert "--generate-gamma" in result.args
        assert result.confidence > 0.5
    
    def test_stats_tracking(self):
        """Test performance statistics tracking."""
        initial_stats = self.engine.get_stats()
        assert initial_stats["total_calls"] == 0
        
        # Make a translation
        self.engine.translate("test query")
        
        updated_stats = self.engine.get_stats()
        assert updated_stats["total_calls"] >= 1
    
    def test_available_functions(self):
        """Test getting available functions."""
        functions = self.engine.get_available_functions()
        assert "voice_of_customer_analysis" in functions
        assert "comprehensive_analysis" in functions
        assert "billing_analysis" in functions


class TestRAGEngine:
    """Test RAG engine."""
    
    def setup_method(self):
        self.engine = RAGEngine()
    
    def test_documentation_database(self):
        """Test documentation database structure."""
        assert len(self.engine.documentation) > 0
        
        # Check that we have documentation for key commands
        commands = [doc.command for doc in self.engine.documentation]
        assert "voice-of-customer" in commands
        assert "comprehensive-analysis" in commands
    
    def test_relevance_calculation(self):
        """Test relevance score calculation."""
        query = "voice of customer analysis"
        doc = self.engine.documentation[0]  # Get first doc
        
        relevance = self.engine._calculate_relevance(query, doc)
        assert 0.0 <= relevance <= 1.0
    
    def test_document_retrieval(self):
        """Test document retrieval."""
        query = "voice of customer report"
        docs = self.engine._retrieve_relevant_docs(query, top_k=2)
        
        assert len(docs) <= 2
        if len(docs) > 1:
            assert docs[0].relevance_score >= docs[1].relevance_score
    
    def test_parameter_extraction(self):
        """Test parameter extraction from context."""
        query = "last week's report with gamma presentation"
        docs = self.engine._retrieve_relevant_docs(query, top_k=1)
        
        if docs:
            parameters = self.engine._extract_parameters_from_context(query, docs)
            assert parameters.get("time_period") == "week"
            assert parameters.get("generate_gamma") is True
    
    def test_translation(self):
        """Test complete RAG translation."""
        query = "voice of customer analysis for last month with gamma"
        result = self.engine.translate(query)
        
        assert result.action in [ActionType.EXECUTE_COMMAND, ActionType.CLARIFY_REQUEST]
        if result.action == ActionType.EXECUTE_COMMAND:
            assert result.command is not None
            assert result.confidence > 0.0
    
    def test_stats_tracking(self):
        """Test performance statistics tracking."""
        initial_stats = self.engine.get_stats()
        assert initial_stats["total_queries"] == 0
        
        # Make a translation
        self.engine.translate("test query")
        
        updated_stats = self.engine.get_stats()
        assert updated_stats["total_queries"] >= 1
    
    def test_documentation_summary(self):
        """Test documentation summary."""
        summary = self.engine.get_documentation_summary()
        assert "total_entries" in summary
        assert "commands_covered" in summary
        assert "topics_covered" in summary
        assert summary["total_entries"] > 0


class TestIntentClassifier:
    """Test intent classifier."""
    
    def setup_method(self):
        self.classifier = IntentClassifier()
    
    def test_intent_classification(self):
        """Test intent classification."""
        # Test voice of customer intent
        intent, confidence = self.classifier._classify_intent("voice of customer analysis")
        assert intent == IntentType.VOICE_OF_CUSTOMER
        assert confidence > 0.0
        
        # Test billing intent
        intent, confidence = self.classifier._classify_intent("billing analysis report")
        assert intent == IntentType.BILLING_ANALYSIS
        assert confidence > 0.0
        
        # Test help intent
        intent, confidence = self.classifier._classify_intent("help me")
        assert intent == IntentType.HELP_REQUEST
        assert confidence > 0.0
    
    def test_time_period_extraction(self):
        """Test time period extraction."""
        period = self.classifier._extract_time_period("last week's report")
        assert period == "week"
        
        period = self.classifier._extract_time_period("monthly analysis")
        assert period == "month"
    
    def test_boolean_flag_extraction(self):
        """Test boolean flag extraction."""
        flags = self.classifier._extract_boolean_flags("report with gamma")
        assert flags.get("generate_gamma") is True
        
        flags = self.classifier._extract_boolean_flags("analysis with canny")
        assert flags.get("include_canny") is True
    
    def test_command_building(self):
        """Test command building."""
        args = self.classifier._build_command_args("voice-of-customer", "weekly report with gamma")
        assert "voice-of-customer" in args
        assert "--time-period" in args
        assert "week" in args
        assert "--generate-gamma" in args
    
    def test_classification(self):
        """Test complete classification process."""
        query = "voice of customer analysis for last week"
        result = self.classifier.classify(query)
        
        assert result.action in [ActionType.EXECUTE_COMMAND, ActionType.CLARIFY_REQUEST]
        if result.action == ActionType.EXECUTE_COMMAND:
            assert result.command == "voice-of-customer"
            assert result.confidence > 0.0
    
    def test_stats_tracking(self):
        """Test performance statistics tracking."""
        initial_stats = self.classifier.get_stats()
        assert initial_stats["total_classifications"] == 0
        
        # Make a classification
        self.classifier.classify("test query")
        
        updated_stats = self.classifier.get_stats()
        assert updated_stats["total_classifications"] >= 1
    
    def test_supported_intents(self):
        """Test getting supported intents."""
        intents = self.classifier.get_supported_intents()
        assert "voice_of_customer" in intents
        assert "billing_analysis" in intents
        assert "help_request" in intents
    
    def test_intent_patterns(self):
        """Test getting intent patterns."""
        patterns = self.classifier.get_intent_patterns()
        assert "voice_of_customer" in patterns
        assert "keywords" in patterns["voice_of_customer"]
        assert "patterns" in patterns["voice_of_customer"]


class TestEngineIntegration:
    """Test integration between engines."""
    
    def test_engine_compatibility(self):
        """Test that engines can work together."""
        # Create all engines
        function_engine = FunctionCallingEngine()
        rag_engine = RAGEngine()
        intent_classifier = IntentClassifier()
        
        # Test that they can all handle the same query
        query = "voice of customer analysis for last week"
        
        func_result = function_engine.translate(query)
        rag_result = rag_engine.translate(query)
        intent_result = intent_classifier.classify(query)
        
        # All should return valid results
        assert func_result.action in [ActionType.EXECUTE_COMMAND, ActionType.CLARIFY_REQUEST]
        assert rag_result.action in [ActionType.EXECUTE_COMMAND, ActionType.CLARIFY_REQUEST]
        assert intent_result.action in [ActionType.EXECUTE_COMMAND, ActionType.CLARIFY_REQUEST]
    
    def test_confidence_comparison(self):
        """Test confidence levels across engines."""
        query = "Give me last week's voice of customer report with gamma presentation"
        
        function_engine = FunctionCallingEngine()
        rag_engine = RAGEngine()
        intent_classifier = IntentClassifier()
        
        func_result = function_engine.translate(query)
        rag_result = rag_engine.translate(query)
        intent_result = intent_classifier.classify(query)
        
        # Function calling should generally have highest confidence for clear queries
        if func_result.action == ActionType.EXECUTE_COMMAND:
            assert func_result.confidence > 0.0
        
        # All engines should return reasonable confidence scores
        assert 0.0 <= func_result.confidence <= 1.0
        assert 0.0 <= rag_result.confidence <= 1.0
        assert 0.0 <= intent_result.confidence <= 1.0
