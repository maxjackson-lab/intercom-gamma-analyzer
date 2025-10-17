"""
Command translation schemas and structured output validation.

Defines the data structures for natural language to CLI command translation,
ensuring type safety and validation throughout the chat interface.
"""

from typing import Dict, List, Optional, Any, Union, Literal
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class ActionType(Enum):
    """Types of actions that can be performed."""
    EXECUTE_COMMAND = "EXECUTE_COMMAND"
    CUSTOM_FILTER = "CUSTOM_FILTER"
    SUGGEST_FEATURE = "SUGGEST_FEATURE"
    CLARIFY_REQUEST = "CLARIFY_REQUEST"
    SHOW_HELP = "SHOW_HELP"


class RiskLevel(Enum):
    """Risk levels for command execution."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ModelType(Enum):
    """Supported LLM models for translation."""
    GPT_4O_MINI = "gpt-4o-mini"
    CLAUDE_3_HAIKU = "claude-3-haiku"
    GEMINI_1_5_FLASH = "gemini-1.5-flash"


class FilterType(str, Enum):
    """Filter type enumeration."""
    STRING = "string"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    ARRAY = "array"


class FilterOperator(str, Enum):
    """Filter operator enumeration."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    BETWEEN = "between"
    IN = "in"
    NOT_IN = "not_in"


@dataclass
class FilterSpec:
    """Specification for custom filtering."""
    field: str
    operator: FilterOperator
    value: Any
    description: str
    filter_type: Optional[FilterType] = None


@dataclass
class CommandTranslation:
    """Structured result of natural language to command translation."""
    action: ActionType
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    filters: Optional[FilterSpec] = None
    explanation: str = ""
    dangerous: bool = False
    confirmation_required: bool = False
    risk_score: float = 0.0
    confidence: float = 0.0
    model_used: Optional[ModelType] = None
    processing_time_ms: Optional[int] = None
    cache_hit: bool = False
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "action": self.action.value,
            "command": self.command,
            "args": self.args,
            "filters": self.filters.__dict__ if self.filters else None,
            "explanation": self.explanation,
            "dangerous": self.dangerous,
            "confirmation_required": self.confirmation_required,
            "risk_score": self.risk_score,
            "confidence": self.confidence,
            "model_used": self.model_used.value if self.model_used else None,
            "processing_time_ms": self.processing_time_ms,
            "cache_hit": self.cache_hit,
            "warnings": self.warnings,
            "suggestions": self.suggestions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CommandTranslation":
        """Create from dictionary."""
        return cls(
            action=ActionType(data["action"]),
            command=data.get("command"),
            args=data.get("args", []),
            filters=FilterSpec(**data["filters"]) if data.get("filters") else None,
            explanation=data.get("explanation", ""),
            dangerous=data.get("dangerous", False),
            confirmation_required=data.get("confirmation_required", False),
            risk_score=data.get("risk_score", 0.0),
            confidence=data.get("confidence", 0.0),
            model_used=ModelType(data["model_used"]) if data.get("model_used") else None,
            processing_time_ms=data.get("processing_time_ms"),
            cache_hit=data.get("cache_hit", False),
            warnings=data.get("warnings", []),
            suggestions=data.get("suggestions", [])
        )


@dataclass
class SuggestionResult:
    """Result of feature suggestion analysis."""
    exists: bool
    workaround: Optional[str] = None
    implementation: Optional[str] = None
    effort_hours: Optional[int] = None
    affected_files: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    priority: str = "medium"  # "low", "medium", "high", "critical"
    estimated_cost: Optional[float] = None
    alternative_approaches: List[str] = field(default_factory=list)


@dataclass
class ChatMessage:
    """Individual message in chat conversation."""
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class ChatSession:
    """Complete chat session with history and context."""
    session_id: str
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a message to the session."""
        message = ChatMessage(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.last_activity = datetime.now()
    
    def get_recent_messages(self, count: int = 10) -> List[ChatMessage]:
        """Get the most recent messages."""
        return self.messages[-count:] if len(self.messages) > count else self.messages
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "context": self.context,
            "settings": self.settings
        }


@dataclass
class CacheEntry:
    """Entry in semantic cache."""
    query_hash: str
    query_text: str
    response: CommandTranslation
    created_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "query_hash": self.query_hash,
            "query_text": self.query_text,
            "response": self.response.to_dict(),
            "created_at": self.created_at.isoformat(),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat()
        }


@dataclass
class PerformanceMetrics:
    """Performance and cost metrics for chat operations."""
    total_queries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    average_response_time_ms: float = 0.0
    error_count: int = 0
    model_usage: Dict[str, int] = field(default_factory=dict)
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        if self.total_queries == 0:
            return 0.0
        return (self.cache_hits / self.total_queries) * 100
    
    @property
    def average_cost_per_query(self) -> float:
        """Calculate average cost per query."""
        if self.total_queries == 0:
            return 0.0
        return self.total_cost_usd / self.total_queries
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_queries": self.total_queries,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "total_cost_usd": self.total_cost_usd,
            "total_tokens": self.total_tokens,
            "average_response_time_ms": self.average_response_time_ms,
            "error_count": self.error_count,
            "model_usage": self.model_usage,
            "cache_hit_rate": self.cache_hit_rate,
            "average_cost_per_query": self.average_cost_per_query
        }


# JSON Schema for OpenAI Function Calling
COMMAND_TRANSLATION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": [action.value for action in ActionType]
        },
        "command": {
            "type": "string",
            "description": "The CLI command to execute"
        },
        "args": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Command arguments and flags"
        },
        "filters": {
            "type": "object",
            "properties": {
                "agent": {"type": "string"},
                "category": {"type": "string"},
                "date_range": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "string", "format": "date"},
                        "end": {"type": "string", "format": "date"}
                    }
                },
                "language": {"type": "string"},
                "sentiment": {"type": "string", "enum": ["positive", "negative", "neutral"]}
            }
        },
        "explanation": {
            "type": "string",
            "description": "Human-readable explanation of what the command does"
        },
        "dangerous": {
            "type": "boolean",
            "description": "Whether this command is potentially dangerous"
        },
        "confirmation_required": {
            "type": "boolean",
            "description": "Whether user confirmation is required before execution"
        },
        "risk_score": {
            "type": "number",
            "minimum": 0,
            "maximum": 10,
            "description": "Risk score from 0 (safe) to 10 (critical)"
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confidence in the translation accuracy"
        },
        "warnings": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Security or validation warnings"
        },
        "suggestions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Alternative suggestions or improvements"
        }
    },
    "required": ["action", "explanation"]
}


# Validation functions
def validate_command_translation(data: Dict[str, Any]) -> bool:
    """Validate command translation data against schema."""
    try:
        # Check required fields
        if "action" not in data or "explanation" not in data:
            return False
        
        # Validate action type
        try:
            ActionType(data["action"])
        except ValueError:
            return False
        
        # Validate risk score if present
        if "risk_score" in data:
            risk_score = data["risk_score"]
            if not isinstance(risk_score, (int, float)) or not (0 <= risk_score <= 10):
                return False
        
        # Validate confidence if present
        if "confidence" in data:
            confidence = data["confidence"]
            if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
                return False
        
        # Validate dangerous flag
        if "dangerous" in data and not isinstance(data["dangerous"], bool):
            return False
        
        # Validate confirmation required flag
        if "confirmation_required" in data and not isinstance(data["confirmation_required"], bool):
            return False
        
        return True
        
    except Exception:
        return False


def create_safe_command_translation(
    action: ActionType,
    explanation: str,
    command: Optional[str] = None,
    args: Optional[List[str]] = None,
    **kwargs
) -> CommandTranslation:
    """Create a safe command translation with validation."""
    return CommandTranslation(
        action=action,
        command=command,
        args=args or [],
        explanation=explanation,
        dangerous=kwargs.get("dangerous", False),
        confirmation_required=kwargs.get("confirmation_required", False),
        risk_score=kwargs.get("risk_score", 0.0),
        confidence=kwargs.get("confidence", 1.0),
        warnings=kwargs.get("warnings", []),
        suggestions=kwargs.get("suggestions", [])
    )


class IntentType(Enum):
    """Intent types for classification."""
    VOICE_OF_CUSTOMER = "voice_of_customer"
    BILLING_ANALYSIS = "billing_analysis"
    COMPREHENSIVE_ANALYSIS = "comprehensive_analysis"
    CUSTOM_REPORT = "custom_report"
    HELP_REQUEST = "help_request"
    UNKNOWN = "unknown"


class QueryComplexity(Enum):
    """Query complexity levels."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


@dataclass
class CacheStats:
    """Cache performance statistics."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    hit_rate: float = 0.0
    total_size: int = 0
    evictions: int = 0


@dataclass
class PerformanceMetrics:
    """Performance metrics for the chat system."""
    total_queries: int = 0
    successful_translations: int = 0
    failed_translations: int = 0
    average_confidence: float = 0.0
    average_processing_time_ms: float = 0.0
    total_cost_usd: float = 0.0
    cache_hit_rate: float = 0.0
