"""
Natural Language Chat Interface for Intercom Analysis Tool

This module provides a cost-effective, enterprise-grade chat interface that translates
natural language requests into CLI commands with multi-layer security and caching.
"""

__version__ = "1.0.0"
__author__ = "Intercom Analysis Tool Team"

# Import core components
from .chat_interface import ChatInterface
from .hybrid_translator import HybridCommandTranslator, TranslationResult
from .terminal_ui import TerminalChatUI

# Import engines
from .engines.function_calling import FunctionCallingEngine
from .engines.rag_engine import RAGEngine
from .engines.intent_classifier import IntentClassifier

# Import supporting components
from .suggestion_engine import SuggestionEngine, FeatureSuggestion
from .custom_filter_builder import CustomFilterBuilder
from .semantic_cache import SemanticCache
from .model_router import ModelRouter

# Import security components
from .security import InputValidator, CommandWhitelist, HITLController

# Import schemas
from .schemas import (
    CommandTranslation, ActionType, ModelType, FilterSpec, FilterType, FilterOperator,
    ChatSession, PerformanceMetrics, CacheStats, QueryComplexity, IntentType
)

__all__ = [
    # Core interface
    "ChatInterface",
    "HybridCommandTranslator",
    "TranslationResult",
    "TerminalChatUI",
    
    # Engines
    "FunctionCallingEngine",
    "RAGEngine", 
    "IntentClassifier",
    
    # Supporting components
    "SuggestionEngine",
    "FeatureSuggestion",
    "CustomFilterBuilder",
    "SemanticCache",
    "ModelRouter",
    
    # Security
    "InputValidator",
    "CommandWhitelist",
    "HITLController",
    
    # Schemas
    "CommandTranslation",
    "ActionType",
    "ModelType",
    "FilterSpec",
    "FilterType", 
    "FilterOperator",
    "ChatSession",
    "PerformanceMetrics",
    "CacheStats",
    "QueryComplexity",
    "IntentType",
]
