"""
Hybrid Command Translator

Combines multiple translation engines (Function Calling, RAG, Intent Classification)
to provide the best possible command translation with fallback mechanisms.
"""

import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .schemas import CommandTranslation, ActionType, ModelType
from .engines.function_calling import FunctionCallingEngine
from .engines.rag_engine import RAGEngine
from .engines.intent_classifier import IntentClassifier
from .semantic_cache import SemanticCache
from .model_router import ModelRouter
from ..config.settings import Settings


@dataclass
class TranslationResult:
    """Result from hybrid translation with metadata."""
    translation: CommandTranslation
    engine_used: str
    confidence: float
    processing_time_ms: float
    cache_hit: bool
    fallback_used: bool


class HybridCommandTranslator:
    """
    Hybrid command translator that combines multiple translation engines.
    
    Uses a tiered approach:
    1. Semantic cache (fastest, most cost-effective)
    2. Function calling (highest accuracy for known commands)
    3. RAG engine (best for complex/documentation-heavy queries)
    4. Intent classification (fallback for simple commands)
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize engines
        self.function_engine = FunctionCallingEngine()
        self.rag_engine = RAGEngine()
        self.intent_classifier = IntentClassifier()
        
        # Initialize supporting components
        self.semantic_cache = SemanticCache()
        self.model_router = ModelRouter()
        
        # Performance tracking
        self.stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "function_calling_success": 0,
            "rag_success": 0,
            "intent_classification_success": 0,
            "fallback_used": 0,
            "average_confidence": 0.0,
            "average_processing_time_ms": 0.0,
            "total_cost_usd": 0.0
        }
        
        self.logger.info("HybridCommandTranslator initialized with all engines")
    
    def translate(self, query: str, context: Optional[Dict] = None) -> TranslationResult:
        """
        Translate natural language query to CLI command using hybrid approach.
        
        Args:
            query: User's natural language input
            context: Additional context for translation
            
        Returns:
            TranslationResult with command and metadata
        """
        start_time = time.time()
        self.stats["total_queries"] += 1
        
        try:
            # Step 1: Check semantic cache first (fastest)
            cached_result = self.semantic_cache.get_cached_response(query)
            if cached_result:
                self.stats["cache_hits"] += 1
                processing_time = (time.time() - start_time) * 1000
                
                return TranslationResult(
                    translation=cached_result,
                    engine_used="semantic_cache",
                    confidence=cached_result.confidence,
                    processing_time_ms=processing_time,
                    cache_hit=True,
                    fallback_used=False
                )
            
            # Step 2: Try function calling (highest accuracy for known commands)
            function_result = self._try_function_calling(query, context)
            if function_result and function_result.confidence >= 0.7:
                self.stats["function_calling_success"] += 1
                processing_time = (time.time() - start_time) * 1000
                
                # Cache the result
                self.semantic_cache.cache_response(query, function_result)
                
                return TranslationResult(
                    translation=function_result,
                    engine_used="function_calling",
                    confidence=function_result.confidence,
                    processing_time_ms=processing_time,
                    cache_hit=False,
                    fallback_used=False
                )
            
            # Step 3: Try RAG engine (best for complex queries)
            rag_result = self._try_rag_engine(query, context)
            if rag_result and rag_result.confidence >= 0.6:
                self.stats["rag_success"] += 1
                processing_time = (time.time() - start_time) * 1000
                
                # Cache the result
                self.semantic_cache.cache_response(query, rag_result)
                
                return TranslationResult(
                    translation=rag_result,
                    engine_used="rag_engine",
                    confidence=rag_result.confidence,
                    processing_time_ms=processing_time,
                    cache_hit=False,
                    fallback_used=False
                )
            
            # Step 4: Fallback to intent classification
            intent_result = self._try_intent_classification(query, context)
            if intent_result:
                self.stats["intent_classification_success"] += 1
                self.stats["fallback_used"] += 1
                processing_time = (time.time() - start_time) * 1000
                
                # Cache the result
                self.semantic_cache.cache_response(query, intent_result)
                
                return TranslationResult(
                    translation=intent_result,
                    engine_used="intent_classification",
                    confidence=intent_result.confidence,
                    processing_time_ms=processing_time,
                    cache_hit=False,
                    fallback_used=True
                )
            
            # Step 5: Ultimate fallback - clarification request
            processing_time = (time.time() - start_time) * 1000
            fallback_translation = self._create_clarification_request(query)
            
            return TranslationResult(
                translation=fallback_translation,
                engine_used="fallback",
                confidence=0.0,
                processing_time_ms=processing_time,
                cache_hit=False,
                fallback_used=True
            )
            
        except Exception as e:
            self.logger.error(f"Hybrid translation failed: {e}")
            processing_time = (time.time() - start_time) * 1000
            
            error_translation = self._create_error_response(str(e))
            
            return TranslationResult(
                translation=error_translation,
                engine_used="error",
                confidence=0.0,
                processing_time_ms=processing_time,
                cache_hit=False,
                fallback_used=True
            )
        
        finally:
            # Update performance stats
            self._update_performance_stats(processing_time)
    
    def _try_function_calling(self, query: str, context: Optional[Dict] = None) -> Optional[CommandTranslation]:
        """Try function calling engine."""
        try:
            return self.function_engine.translate(query, context)
        except Exception as e:
            self.logger.warning(f"Function calling failed: {e}")
            return None
    
    def _try_rag_engine(self, query: str, context: Optional[Dict] = None) -> Optional[CommandTranslation]:
        """Try RAG engine."""
        try:
            return self.rag_engine.translate(query, context)
        except Exception as e:
            self.logger.warning(f"RAG engine failed: {e}")
            return None
    
    def _try_intent_classification(self, query: str, context: Optional[Dict] = None) -> Optional[CommandTranslation]:
        """Try intent classification engine."""
        try:
            return self.intent_classifier.classify(query, context)
        except Exception as e:
            self.logger.warning(f"Intent classification failed: {e}")
            return None
    
    def _create_clarification_request(self, query: str) -> CommandTranslation:
        """Create a clarification request when all engines fail."""
        return CommandTranslation(
            action=ActionType.CLARIFY_REQUEST,
            command=None,
            args=[],
            explanation="I'm not sure what you're asking for. Could you provide more details?",
            dangerous=False,
            confirmation_required=False,
            risk_score=0.0,
            confidence=0.0,
            model_used=None,
            processing_time_ms=0.0,
            cache_hit=False,
            warnings=[],
            suggestions=[
                "Try: 'Give me last week's voice of customer report'",
                "Try: 'Show me billing analysis for this month'",
                "Try: 'Run comprehensive analysis with Gamma presentation'",
                "Try: 'Help' for available commands"
            ]
        )
    
    def _create_error_response(self, error_message: str) -> CommandTranslation:
        """Create an error response."""
        return CommandTranslation(
            action=ActionType.CLARIFY_REQUEST,
            command=None,
            args=[],
            explanation=f"Sorry, I encountered an error: {error_message}",
            dangerous=False,
            confirmation_required=False,
            risk_score=0.0,
            confidence=0.0,
            model_used=None,
            processing_time_ms=0.0,
            cache_hit=False,
            warnings=[f"Translation error: {error_message}"],
            suggestions=[
                "Try rephrasing your request",
                "Try: 'Help' for available commands"
            ]
        )
    
    def _update_performance_stats(self, processing_time_ms: float):
        """Update performance statistics."""
        # Update average processing time
        if self.stats["total_queries"] == 1:
            self.stats["average_processing_time_ms"] = processing_time_ms
        else:
            self.stats["average_processing_time_ms"] = (
                (self.stats["average_processing_time_ms"] * (self.stats["total_queries"] - 1) + processing_time_ms)
                / self.stats["total_queries"]
            )
    
    def get_performance_stats(self) -> Dict:
        """Get comprehensive performance statistics."""
        # Calculate success rates
        total_successful = (
            self.stats["function_calling_success"] +
            self.stats["rag_success"] +
            self.stats["intent_classification_success"]
        )
        
        success_rate = (total_successful / self.stats["total_queries"]) if self.stats["total_queries"] > 0 else 0.0
        cache_hit_rate = (self.stats["cache_hits"] / self.stats["total_queries"]) if self.stats["total_queries"] > 0 else 0.0
        
        return {
            **self.stats,
            "success_rate": success_rate,
            "cache_hit_rate": cache_hit_rate,
            "engine_stats": {
                "function_calling": self.function_engine.get_stats(),
                "rag_engine": self.rag_engine.get_stats(),
                "intent_classifier": self.intent_classifier.get_stats()
            },
            "cache_stats": self.semantic_cache.get_cache_stats()
        }
    
    def get_available_commands(self) -> List[str]:
        """Get list of available commands from all engines."""
        commands = set()
        
        # Get commands from function calling engine
        functions = self.function_engine.get_available_functions()
        commands.update(functions)
        
        # Get commands from RAG engine
        rag_docs = self.rag_engine.get_documentation_summary()
        commands.update(rag_docs.get("commands_covered", []))
        
        # Get commands from intent classifier
        intents = self.intent_classifier.get_supported_intents()
        commands.update(intents)
        
        return sorted(list(commands))
    
    def get_help_text(self) -> str:
        """Get comprehensive help text for the chat interface."""
        return """
# Intercom Analysis Tool - Chat Interface

## Available Commands

### Voice of Customer Analysis
- "Give me last week's voice of customer report"
- "Show me VoC analysis for this month"
- "Generate weekly report with Gamma presentation"
- "Voice of customer analysis for Q1 2025"

### Comprehensive Analysis
- "Run comprehensive analysis for last month"
- "Show me full analysis with all data sources"
- "Generate comprehensive report with Gamma"

### Billing Analysis
- "Show me billing analysis for this quarter"
- "Analyze subscription data for last month"
- "Generate billing report"

### Custom Reports
- "Create custom report for API tickets by Horatio agents in September"
- "Show me conversations about billing issues last week"
- "Generate report for support tickets by category"

## Features
- **Natural Language**: Just describe what you want in plain English
- **Smart Suggestions**: Get helpful suggestions when requests are unclear
- **Cost Optimization**: Uses semantic caching to reduce API costs
- **Security**: All commands are validated and safe to execute
- **Gamma Integration**: Automatically generates presentations when requested

## Tips
- Be specific about time periods (last week, this month, Q1 2025)
- Mention if you want Gamma presentations or Canny feedback included
- Ask for help if you're unsure about available commands
        """.strip()
    
    def reset_stats(self):
        """Reset performance statistics."""
        self.stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "function_calling_success": 0,
            "rag_success": 0,
            "intent_classification_success": 0,
            "fallback_used": 0,
            "average_confidence": 0.0,
            "average_processing_time_ms": 0.0,
            "total_cost_usd": 0.0
        }
        
        # Reset individual engine stats
        self.function_engine.reset_stats()
        self.rag_engine.reset_stats()
        self.intent_classifier.reset_stats()
        # Reset semantic cache stats
        self.semantic_cache.clear_cache()
        
        self.logger.info("Performance statistics reset")
