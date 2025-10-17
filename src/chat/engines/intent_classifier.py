"""
Intent classification engine for fallback command translation.

Provides lightweight fallback using pattern matching and simple classification
when function calling and RAG approaches fail.
"""

import logging
import time
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from ..schemas import (
    CommandTranslation, ActionType, ModelType,
    create_safe_command_translation
)

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Types of user intents."""
    VOICE_OF_CUSTOMER = "voice_of_customer"
    COMPREHENSIVE_ANALYSIS = "comprehensive_analysis"
    BILLING_ANALYSIS = "billing_analysis"
    TECH_ANALYSIS = "tech_analysis"
    PRODUCT_ANALYSIS = "product_analysis"
    SITES_ANALYSIS = "sites_analysis"
    HELP_REQUEST = "help_request"
    UNKNOWN = "unknown"


@dataclass
class IntentPattern:
    """Pattern for intent classification."""
    intent: IntentType
    keywords: List[str]
    patterns: List[str]
    confidence_boost: float = 0.0


class IntentClassifier:
    """
    Intent classification engine for fallback command translation.
    
    Uses lightweight pattern matching and keyword analysis to classify
    user intents when more sophisticated approaches fail.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Define intent patterns
        self.intent_patterns = self._define_intent_patterns()
        
        # Performance tracking
        self.stats = {
            "total_classifications": 0,
            "successful_classifications": 0,
            "failed_classifications": 0,
            "average_confidence": 0.0,
            "average_response_time_ms": 0.0
        }
    
    def _define_intent_patterns(self) -> List[IntentPattern]:
        """Define patterns for intent classification."""
        return [
            IntentPattern(
                intent=IntentType.VOICE_OF_CUSTOMER,
                keywords=["voice", "customer", "voc", "vof", "sentiment", "feedback", "insights"],
                patterns=[
                    r"voice of customer",
                    r"customer feedback",
                    r"sentiment analysis",
                    r"customer insights",
                    r"vof analysis",
                    r"voc report"
                ],
                confidence_boost=0.1
            ),
            
            IntentPattern(
                intent=IntentType.COMPREHENSIVE_ANALYSIS,
                keywords=["comprehensive", "full", "complete", "detailed", "everything", "all"],
                patterns=[
                    r"comprehensive analysis",
                    r"full report",
                    r"complete analysis",
                    r"detailed report",
                    r"everything",
                    r"all data"
                ],
                confidence_boost=0.1
            ),
            
            IntentPattern(
                intent=IntentType.BILLING_ANALYSIS,
                keywords=["billing", "subscription", "payment", "invoice", "revenue", "financial"],
                patterns=[
                    r"billing analysis",
                    r"subscription issues",
                    r"payment problems",
                    r"revenue analysis",
                    r"financial report"
                ],
                confidence_boost=0.1
            ),
            
            IntentPattern(
                intent=IntentType.TECH_ANALYSIS,
                keywords=["technical", "tech", "api", "integration", "troubleshooting", "bugs", "errors"],
                patterns=[
                    r"technical issues",
                    r"api problems",
                    r"integration issues",
                    r"troubleshooting",
                    r"technical support"
                ],
                confidence_boost=0.1
            ),
            
            IntentPattern(
                intent=IntentType.PRODUCT_ANALYSIS,
                keywords=["product", "feature", "functionality", "requests", "suggestions"],
                patterns=[
                    r"product questions",
                    r"feature requests",
                    r"product feedback",
                    r"functionality issues"
                ],
                confidence_boost=0.1
            ),
            
            IntentPattern(
                intent=IntentType.SITES_ANALYSIS,
                keywords=["sites", "accounts", "administration", "configuration", "management"],
                patterns=[
                    r"sites analysis",
                    r"account management",
                    r"administration",
                    r"configuration issues"
                ],
                confidence_boost=0.1
            ),
            
            IntentPattern(
                intent=IntentType.HELP_REQUEST,
                keywords=["help", "how", "what", "can you", "show me", "explain"],
                patterns=[
                    r"how do i",
                    r"what can you",
                    r"can you help",
                    r"show me how",
                    r"explain"
                ],
                confidence_boost=0.05
            )
        ]
    
    def _extract_time_period(self, query: str) -> Optional[str]:
        """Extract time period from query."""
        query_lower = query.lower()
        
        time_patterns = [
            (r"last week|this week|weekly", "week"),
            (r"last month|this month|monthly", "month"),
            (r"last quarter|this quarter|quarterly", "quarter"),
            (r"last year|this year|yearly|annual", "year")
        ]
        
        for pattern, period in time_patterns:
            if re.search(pattern, query_lower):
                return period
        
        return None
    
    def _extract_boolean_flags(self, query: str) -> Dict[str, bool]:
        """Extract boolean flags from query."""
        query_lower = query.lower()
        
        flags = {}
        
        if "with gamma" in query_lower or "gamma presentation" in query_lower:
            flags["generate_gamma"] = True
        
        if "with canny" in query_lower or "include canny" in query_lower:
            flags["include_canny"] = True
        
        if "with details" in query_lower or "detailed" in query_lower:
            flags["include_details"] = True
        
        if "export" in query_lower or "documentation" in query_lower:
            flags["export_docs"] = True
        
        return flags
    
    def _classify_intent(self, query: str) -> Tuple[IntentType, float]:
        """
        Classify user intent from query.
        
        Returns:
            Tuple of (intent_type, confidence_score)
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        best_intent = IntentType.UNKNOWN
        best_score = 0.0
        
        for pattern in self.intent_patterns:
            score = 0.0
            
            # Keyword matching
            keyword_matches = sum(1 for keyword in pattern.keywords if keyword in query_lower)
            if pattern.keywords:
                keyword_score = keyword_matches / len(pattern.keywords)
                score += keyword_score * 0.6
            
            # Pattern matching
            pattern_matches = sum(1 for regex_pattern in pattern.patterns 
                                if re.search(regex_pattern, query_lower))
            if pattern.patterns:
                pattern_score = pattern_matches / len(pattern.patterns)
                score += pattern_score * 0.4
            
            # Apply confidence boost
            score += pattern.confidence_boost
            
            if score > best_score:
                best_score = score
                best_intent = pattern.intent
        
        return best_intent, min(best_score, 1.0)
    
    def _intent_to_command(self, intent: IntentType) -> str:
        """Convert intent to CLI command."""
        command_map = {
            IntentType.VOICE_OF_CUSTOMER: "voice-of-customer",
            IntentType.COMPREHENSIVE_ANALYSIS: "comprehensive-analysis",
            IntentType.BILLING_ANALYSIS: "billing-analysis",
            IntentType.TECH_ANALYSIS: "tech-analysis",
            IntentType.PRODUCT_ANALYSIS: "product-analysis",
            IntentType.SITES_ANALYSIS: "sites-analysis",
            IntentType.HELP_REQUEST: "help",
            IntentType.UNKNOWN: None
        }
        
        return command_map.get(intent)
    
    def _build_command_args(self, command: str, query: str) -> List[str]:
        """Build command arguments from query."""
        args = [command]
        
        # Extract time period
        time_period = self._extract_time_period(query)
        if time_period:
            args.extend(["--time-period", time_period])
        
        # Extract boolean flags
        flags = self._extract_boolean_flags(query)
        for flag, value in flags.items():
            if value:
                args.append(f"--{flag.replace('_', '-')}")
        
        # Set defaults for common commands
        if command == "voice-of-customer":
            if "generate_gamma" not in flags:
                args.append("--generate-gamma")
        
        return args
    
    def _generate_explanation(self, intent: IntentType, command: str, query: str) -> str:
        """Generate explanation for the classified intent."""
        explanations = {
            IntentType.VOICE_OF_CUSTOMER: "Generate Voice of Customer analysis report",
            IntentType.COMPREHENSIVE_ANALYSIS: "Run comprehensive analysis with multiple data sources",
            IntentType.BILLING_ANALYSIS: "Analyze billing and subscription data",
            IntentType.TECH_ANALYSIS: "Analyze technical troubleshooting conversations",
            IntentType.PRODUCT_ANALYSIS: "Analyze product-related questions and feedback",
            IntentType.SITES_ANALYSIS: "Analyze sites and account-related conversations",
            IntentType.HELP_REQUEST: "Show available commands and help information",
            IntentType.UNKNOWN: "Unable to determine the appropriate command"
        }
        
        base_explanation = explanations.get(intent, "Execute analysis command")
        
        # Add time period if detected
        time_period = self._extract_time_period(query)
        if time_period:
            base_explanation += f" for {time_period}"
        
        # Add flags if detected
        flags = self._extract_boolean_flags(query)
        if flags.get("generate_gamma"):
            base_explanation += " with Gamma presentation"
        if flags.get("include_canny"):
            base_explanation += " including Canny feedback"
        
        return base_explanation
    
    def classify(self, query: str, context: Optional[Dict] = None) -> CommandTranslation:
        """
        Classify user intent and generate command translation.
        
        Args:
            query: User's natural language input
            context: Additional context for classification
            
        Returns:
            CommandTranslation with command and parameters
        """
        start_time = time.time()
        
        try:
            # Classify intent
            intent, confidence = self._classify_intent(query)
            
            if intent == IntentType.UNKNOWN or confidence < 0.3:
                # Update stats for failed classification
                response_time = int((time.time() - start_time) * 1000)
                self._update_stats(False, confidence, response_time)
                
                return create_safe_command_translation(
                    ActionType.CLARIFY_REQUEST,
                    "I'm not sure what you're asking for. Could you provide more details?",
                    confidence=confidence,
                    suggestions=[
                        "Try: 'Give me last week's voice of customer report'",
                        "Try: 'Show me billing analysis for this month'",
                        "Try: 'Run comprehensive analysis with Gamma presentation'",
                        "Try: 'Help' for available commands"
                    ]
                )
            
            # Convert intent to command
            command = self._intent_to_command(intent)
            if not command:
                return create_safe_command_translation(
                    ActionType.CLARIFY_REQUEST,
                    "I couldn't determine the appropriate command for your request.",
                    confidence=confidence
                )
            
            # Build command arguments
            command_args = self._build_command_args(command, query)
            
            # Generate explanation
            explanation = self._generate_explanation(intent, command, query)
            
            # Calculate risk score (intent classification is generally safe)
            risk_score = 1.0
            
            # Update stats
            response_time = int((time.time() - start_time) * 1000)
            self._update_stats(True, confidence, response_time)
            
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
            self.logger.error(f"Intent classification failed: {e}")
            self._update_stats(False, 0.0, int((time.time() - start_time) * 1000))
            
            return create_safe_command_translation(
                ActionType.CLARIFY_REQUEST,
                f"Sorry, I encountered an error processing your request: {str(e)}",
                confidence=0.0,
                warnings=[f"Intent classification error: {str(e)}"]
            )
    
    def _update_stats(self, success: bool, confidence: float, response_time_ms: int):
        """Update performance statistics."""
        self.stats["total_classifications"] += 1
        
        if success:
            self.stats["successful_classifications"] += 1
        else:
            self.stats["failed_classifications"] += 1
        
        # Update average confidence
        if self.stats["total_classifications"] == 1:
            self.stats["average_confidence"] = confidence
            self.stats["average_response_time_ms"] = response_time_ms
        else:
            # Running averages
            self.stats["average_confidence"] = (
                (self.stats["average_confidence"] * (self.stats["total_classifications"] - 1) + confidence)
                / self.stats["total_classifications"]
            )
            self.stats["average_response_time_ms"] = (
                (self.stats["average_response_time_ms"] * (self.stats["total_classifications"] - 1) + response_time_ms)
                / self.stats["total_classifications"]
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        stats = self.stats.copy()
        if stats["total_classifications"] > 0:
            stats["success_rate"] = stats["successful_classifications"] / stats["total_classifications"]
        else:
            stats["success_rate"] = 0.0
        return stats
    
    def get_supported_intents(self) -> List[str]:
        """Get list of supported intent types."""
        return [intent.value for intent in IntentType if intent != IntentType.UNKNOWN]
    
    def get_intent_patterns(self) -> Dict[str, List[str]]:
        """Get intent patterns for debugging."""
        return {
            pattern.intent.value: {
                "keywords": pattern.keywords,
                "patterns": pattern.patterns
            }
            for pattern in self.intent_patterns
        }
