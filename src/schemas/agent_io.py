"""
Pydantic schemas describing LangChain-facing input/output contracts for VoC agents.

These schemas deliberately mirror the `AgentContext` payloads and `AgentResult.data`
structures so that tool wrappers can validate data going in/out of the existing agents
without modifying their internal logic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class _BaseSchema(BaseModel):
    """Common configuration for all agent IO schemas."""

    class Config:
        extra = "allow"
        arbitrary_types_allowed = True


# ---------------------------------------------------------------------------
# Topic Detection
# ---------------------------------------------------------------------------


class TopicDetectionInput(_BaseSchema):
    """Inputs required to run TopicDetectionAgent via a LangChain tool."""

    conversations: List[Dict[str, Any]]
    start_date: datetime
    end_date: datetime
    analysis_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TopicAssignment(_BaseSchema):
    """Represents a single topic assignment for a conversation."""

    topic: str
    method: Optional[str] = None
    confidence: Optional[float] = None
    subtopic: Optional[str] = None
    sdk_validated: Optional[bool] = None


class TopicSummary(_BaseSchema):
    """Aggregated statistics for a single detected topic."""

    name: str
    topic: Optional[str] = None  # legacy alias
    volume: int = 0
    percentage: float = 0.0
    detection_method: Optional[str] = None
    confidence: Optional[float] = None
    conversation_volume: Optional[int] = None
    llm_smart_count: Optional[int] = 0
    llm_only_count: Optional[int] = 0
    hybrid_count: Optional[int] = 0
    keyword_count: Optional[int] = 0
    sdk_only_count: Optional[int] = 0
    fallback_count: Optional[int] = 0


class TopicDistributionEntry(_BaseSchema):
    """Distribution stats keyed by topic name."""

    volume: int = 0
    percentage: float = 0.0
    detection_method: Optional[str] = None
    confidence: Optional[float] = None
    llm_smart_count: Optional[int] = 0
    llm_only_count: Optional[int] = 0
    hybrid_count: Optional[int] = 0
    keyword_count: Optional[int] = 0
    sdk_only_count: Optional[int] = 0
    fallback_count: Optional[int] = 0


class TopicDetectionOutput(_BaseSchema):
    """Normalized output produced by TopicDetectionAgent."""

    topics: List[TopicSummary] = Field(default_factory=list)
    topic_distribution: Dict[str, TopicDistributionEntry] = Field(default_factory=dict)
    topics_by_conversation: Dict[str, List[TopicAssignment]] = Field(default_factory=dict)
    conversations_by_topic: Dict[str, int] = Field(default_factory=dict)
    total_conversations: int = 0
    conversations_with_topics: int = 0
    conversations_without_topics: int = 0
    fallback_metrics: Dict[str, int] = Field(default_factory=dict)
    optimization_metrics: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Insight Synthesis
# ---------------------------------------------------------------------------


class InsightInput(_BaseSchema):
    """Inputs for InsightAgent via LangChain."""

    previous_results: Dict[str, Any]
    analysis_id: str
    start_date: datetime
    end_date: datetime
    conversations: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InsightOutput(_BaseSchema):
    """Structured insight payload returned by InsightAgent."""

    executive_summary: str
    major_themes: List[str]
    recommendations: List[str]
    cross_category_patterns: List[str] = Field(default_factory=list)
    business_implications: str = ""
    detection_method_tags: List[str] = Field(default_factory=list)
    detection_method_confidence: Optional[float] = None
    detection_method_distribution: Optional[Dict[str, float]] = Field(default_factory=dict)
    synthesis_quality: Optional[float] = 0.0
    insight_duplicate_ratio: Optional[float] = 0.0
    metric_references_count: Optional[int] = 0


# ---------------------------------------------------------------------------
# Editor / Critic
# ---------------------------------------------------------------------------


class CriticScores(_BaseSchema):
    """Detailed scoring rubric emitted by EditorAgent."""

    specificity_score: float = 0.0
    metric_density_score: float = 0.0
    repetition_score: float = 0.0
    distinctness_score: float = 0.0
    actionability_score: float = 0.0
    composite_score: float = 0.0
    rewrite_needed: bool = False
    issues_found: List[str] = Field(default_factory=list)
    rewrite_guidance: str = ""


class EditorInput(_BaseSchema):
    """Inputs required by EditorAgent."""

    previous_results: Dict[str, Any]
    analysis_id: str
    start_date: datetime
    end_date: datetime
    conversations: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EditorOutput(_BaseSchema):
    """EditorAgent output containing critic scores and optional rewrites."""

    critic_scores: CriticScores
    revised_insights: Dict[str, Any]
    rewrite_performed: bool = False


# ---------------------------------------------------------------------------
# Output Formatter
# ---------------------------------------------------------------------------


class FormatterInput(_BaseSchema):
    """Inputs for OutputFormatterAgent."""

    previous_results: Dict[str, Any]
    conversations: List[Dict[str, Any]]
    start_date: datetime
    end_date: datetime
    analysis_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FormatterOutput(_BaseSchema):
    """Structured response from OutputFormatterAgent."""

    formatted_output: str = ""
    total_topics: int = 0
    has_trend_data: bool = False
    has_tier_based_fin_data: bool = False
    structured_data: Dict[str, Any] = Field(default_factory=dict)
    topic_fallback_used: int = 0
    placeholder_volume: int = 0
    quality_control_summary: Optional[Dict[str, Any]] = None
    detection_method_summary: Optional[Dict[str, Any]] = None
    label_summaries: Optional[Dict[str, Any]] = None
    topic_cards: Optional[List[Dict[str, Any]]] = None


