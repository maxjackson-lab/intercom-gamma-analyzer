"""
Pydantic data models for analysis results and configurations.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum


class AnalysisMode(str, Enum):
    """Analysis modes available."""
    VOICE_OF_CUSTOMER = "voice_of_customer"
    TREND_ANALYSIS = "trend_analysis"
    CUSTOM = "custom"


class ConversationState(str, Enum):
    """Intercom conversation states."""
    OPEN = "open"
    CLOSED = "closed"
    SNOOZED = "snoozed"


class SourceType(str, Enum):
    """Intercom conversation source types."""
    EMAIL = "email"
    CHAT = "chat"
    PHONE = "phone"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    CUSTOM = "custom"


class CustomerTier(str, Enum):
    """Customer subscription tiers."""
    FREE = "free"
    PRO = "pro"
    PLUS = "plus"
    ULTRA = "ultra"


class ConversationSchema(BaseModel):
    """
    Schema for validating and normalizing Intercom conversations.
    
    This schema ensures conversations have the minimum required fields
    and usable text content before being processed by agents.
    """
    # Required fields
    id: str = Field(..., description="Unique conversation ID")
    created_at: Union[datetime, int, str] = Field(..., description="Conversation creation timestamp")
    
    # Optional but important fields
    updated_at: Optional[Union[datetime, int, str]] = None
    state: Optional[str] = None
    conversation_parts: Optional[Dict[str, Any]] = Field(default_factory=dict)
    source: Optional[Dict[str, Any]] = Field(default_factory=dict)
    custom_attributes: Optional[Dict[str, Any]] = Field(default_factory=dict)
    contacts: Optional[Dict[str, Any]] = Field(default_factory=dict)
    tier: Optional[CustomerTier] = Field(None, description="Customer subscription tier extracted from contact or conversation custom attributes")
    
    # Extracted/normalized fields (added during preprocessing)
    customer_messages: Optional[List[str]] = Field(default_factory=list, description="Extracted customer messages")
    
    @validator('created_at', 'updated_at', pre=True, always=True)
    def normalize_timestamp(cls, v):
        """Normalize timestamps to datetime objects"""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, (int, float)):
            from datetime import timezone
            return datetime.fromtimestamp(v, tz=timezone.utc)
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        return v
    
    @validator('custom_attributes', pre=True, always=True)
    def normalize_custom_attributes(cls, v):
        """Ensure custom_attributes is a dict"""
        if v is None or not isinstance(v, dict):
            return {}
        return v

    @validator('contacts', pre=True, always=True)
    def normalize_contacts(cls, v):
        """Ensure contacts is a dict"""
        if v is None or not isinstance(v, dict):
            return {}
        return v

    @validator('tier', pre=True, always=True)
    def extract_tier(cls, v, values):
        """Extract tier from contact or conversation custom attributes"""
        # If tier is already a CustomerTier instance, return it
        if isinstance(v, CustomerTier):
            return v
        
        # Extract tier string from contact-level (priority) or conversation-level
        tier_string = None
        
        # Try contact-level tier first
        contacts_data = values.get('contacts', {})
        if isinstance(contacts_data, dict):
            contacts_list = contacts_data.get('contacts', [])
            if isinstance(contacts_list, list) and len(contacts_list) > 0:
                contact_custom_attrs = contacts_list[0].get('custom_attributes', {})
                if isinstance(contact_custom_attrs, dict):
                    tier_string = contact_custom_attrs.get('tier')
        
        # Fallback to conversation-level tier if contact-level not found
        if not tier_string:
            custom_attrs = values.get('custom_attributes', {})
            if isinstance(custom_attrs, dict):
                tier_string = custom_attrs.get('tier')
        
        # If no tier string found, return None
        if not tier_string:
            return None
        
        # Normalize and match to CustomerTier enum
        try:
            normalized_tier = tier_string.lower() if isinstance(tier_string, str) else None
            if normalized_tier:
                # Try to match against CustomerTier enum values
                for tier_enum in CustomerTier:
                    if tier_enum.value == normalized_tier:
                        return tier_enum
            # If no match found, log debug and return None
            import logging
            logging.getLogger(__name__).debug(f"Unknown tier value: {tier_string}")
            return None
        except (ValueError, AttributeError):
            return None
    
    def has_usable_text(self) -> bool:
        """Check if conversation has usable text content"""
        return len(self.customer_messages or []) > 0
    
    class Config:
        # Allow extra fields from Intercom API
        extra = "allow"


class AnalysisRequest(BaseModel):
    """Request model for analysis operations."""
    mode: AnalysisMode
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    month: Optional[int] = None
    year: Optional[int] = None
    focus_areas: Optional[List[str]] = None
    custom_prompt: Optional[str] = None
    tier1_countries: Optional[List[str]] = None
    custom_instructions: Optional[str] = None
    
    @validator('month')
    def validate_month(cls, v):
        if v is not None and not (1 <= v <= 12):
            raise ValueError('month must be between 1 and 12')
        return v
    
    @validator('year')
    def validate_year(cls, v):
        if v is not None and v < 2020:
            raise ValueError('year must be 2020 or later')
        return v


class ConversationMetrics(BaseModel):
    """
    Metrics for a single conversation.
    
    Note: `tier` is the canonical field for customer subscription tier.
    `user_tier` mirrors it for backward compatibility and is deprecated.
    """
    conversation_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    state: ConversationState
    source_type: SourceType
    response_time_seconds: Optional[int] = None
    resolution_time_seconds: Optional[int] = None
    handling_time_seconds: Optional[int] = None
    satisfaction_rating: Optional[float] = None
    word_count: int = 0
    message_count: int = 0
    agent_count: int = 0
    customer_count: int = 0
    country: Optional[str] = None
    tier: Optional[CustomerTier] = None
    user_tier: Optional[CustomerTier] = None  # Deprecated: use tier instead
    tags: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)

    @validator('tier', pre=True, always=True)
    def normalize_tier(cls, v):
        """Accept strings (case-insensitive) and coerce to CustomerTier"""
        if v is None:
            return None
        if isinstance(v, CustomerTier):
            return v
        if isinstance(v, str):
            normalized = v.lower()
            try:
                for tier_enum in CustomerTier:
                    if tier_enum.value == normalized:
                        return tier_enum
            except (ValueError, AttributeError):
                pass
        return None

    @validator('user_tier', pre=True, always=True)
    def normalize_and_backfill_user_tier(cls, v, values):
        """Accept strings (case-insensitive), coerce to CustomerTier, and backfill from tier"""
        # If user_tier is not provided but tier is, backfill from tier
        if v is None and 'tier' in values and values['tier'] is not None:
            return values['tier']

        # If user_tier is provided, normalize it
        if v is None:
            return None
        if isinstance(v, CustomerTier):
            return v
        if isinstance(v, str):
            normalized = v.lower()
            try:
                for tier_enum in CustomerTier:
                    if tier_enum.value == normalized:
                        return tier_enum
            except (ValueError, AttributeError):
                pass
        return None

    @root_validator(pre=False, skip_on_failure=True)
    def sync_tier_fields(cls, values):
        """
        Ensure tier and user_tier remain fully synchronized after normalization.
        
        - If only one field is provided, mirror it to the other.
        - If both are provided and differ, prefer tier (canonical field) and overwrite user_tier.
        - Runs post-validation (pre=False) to ensure normalization happens first.
        """
        tier = values.get('tier')
        user_tier = values.get('user_tier')
        
        # If only tier is set, mirror to user_tier
        if tier is not None and user_tier is None:
            values['user_tier'] = tier
        # If only user_tier is set, mirror to tier
        elif user_tier is not None and tier is None:
            values['tier'] = user_tier
        # If both are set and different, prefer tier (canonical field)
        elif tier is not None and user_tier is not None and tier != user_tier:
            values['user_tier'] = tier
        
        return values


class VolumeMetrics(BaseModel):
    """Volume-related metrics."""
    total_conversations: int
    ai_resolution_rate: float
    conversation_growth: Optional[float] = None
    conversations_by_day: Dict[str, int] = Field(default_factory=dict)
    conversations_by_hour: Dict[int, int] = Field(default_factory=dict)
    conversations_by_week: Dict[str, int] = Field(default_factory=dict)


class EfficiencyMetrics(BaseModel):
    """Efficiency-related metrics."""
    median_first_response_seconds: Optional[int] = None
    median_handling_time_seconds: Optional[int] = None
    median_resolution_time_seconds: Optional[int] = None
    response_time_by_channel: Dict[str, int] = Field(default_factory=dict)
    handling_time_by_agent: Dict[str, int] = Field(default_factory=dict)
    resolution_rate: float = 0.0


class SatisfactionMetrics(BaseModel):
    """Satisfaction-related metrics."""
    overall_csat: Optional[float] = None
    csat_by_tier: Dict[str, float] = Field(default_factory=dict)
    csat_trend: Optional[float] = None
    csat_by_channel: Dict[str, float] = Field(default_factory=dict)
    csat_by_country: Dict[str, float] = Field(default_factory=dict)
    positive_sentiment_count: int = 0
    negative_sentiment_count: int = 0
    neutral_sentiment_count: int = 0


class TopicMetrics(BaseModel):
    """Topic-related metrics."""
    top_contact_reasons: List[Dict[str, Any]] = Field(default_factory=list)
    billing_breakdown: Dict[str, int] = Field(default_factory=dict)
    product_questions: List[Dict[str, Any]] = Field(default_factory=list)
    account_questions: Dict[str, int] = Field(default_factory=dict)
    keyword_frequency: Dict[str, int] = Field(default_factory=dict)
    topic_trends: Dict[str, Dict[str, int]] = Field(default_factory=dict)


class GeographicMetrics(BaseModel):
    """Geographic-related metrics."""
    tier1_metrics: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    country_breakdown: Dict[str, int] = Field(default_factory=dict)
    regional_trends: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    top_countries: List[Dict[str, Any]] = Field(default_factory=list)


class FrictionMetrics(BaseModel):
    """Friction-related metrics."""
    escalation_patterns: List[Dict[str, Any]] = Field(default_factory=list)
    friction_points: List[Dict[str, Any]] = Field(default_factory=list)
    chargeback_analysis: Dict[str, Any] = Field(default_factory=dict)
    common_complaints: List[Dict[str, Any]] = Field(default_factory=list)
    resolution_failures: List[Dict[str, Any]] = Field(default_factory=list)


class ChannelMetrics(BaseModel):
    """Channel-related metrics."""
    channel_performance: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    channel_satisfaction: Dict[str, float] = Field(default_factory=dict)
    channel_volume: Dict[str, int] = Field(default_factory=dict)
    channel_response_times: Dict[str, int] = Field(default_factory=dict)


class AnalysisResults(BaseModel):
    """Complete analysis results."""
    request: AnalysisRequest
    analysis_date: datetime = Field(default_factory=datetime.now)
    data_period: Dict[str, Any] = Field(default_factory=dict)
    
    # Core metrics
    volume: VolumeMetrics
    efficiency: EfficiencyMetrics
    satisfaction: SatisfactionMetrics
    topics: TopicMetrics
    geographic: GeographicMetrics
    friction: FrictionMetrics
    channel: ChannelMetrics
    
    # Additional data
    customer_quotes: List[Dict[str, Any]] = Field(default_factory=list)
    notable_trends: List[Dict[str, Any]] = Field(default_factory=list)
    actionable_insights: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Metadata
    total_conversations_analyzed: int
    analysis_duration_seconds: float
    data_quality_score: Optional[float] = None
    confidence_score: Optional[float] = None


class TrendAnalysisResults(BaseModel):
    """Results for trend analysis mode."""
    request: AnalysisRequest
    analysis_date: datetime = Field(default_factory=datetime.now)
    
    # Trend data
    volume_trends: Dict[str, Any] = Field(default_factory=dict)
    response_time_trends: Dict[str, Any] = Field(default_factory=dict)
    satisfaction_trends: Dict[str, Any] = Field(default_factory=dict)
    topic_trends: Dict[str, Any] = Field(default_factory=dict)
    keyword_trends: Dict[str, Any] = Field(default_factory=dict)
    sentiment_trends: Dict[str, Any] = Field(default_factory=dict)
    
    # Insights
    key_trends: List[Dict[str, Any]] = Field(default_factory=list)
    trend_explanations: Dict[str, str] = Field(default_factory=dict)
    trend_implications: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Metadata
    total_conversations_analyzed: int
    analysis_duration_seconds: float


class VoiceOfCustomerResults(BaseModel):
    """Results for Voice of Customer analysis mode."""
    request: AnalysisRequest
    analysis_date: datetime = Field(default_factory=datetime.now)
    
    # Executive metrics
    executive_summary: Dict[str, Any] = Field(default_factory=dict)
    tier1_analysis: Dict[str, Any] = Field(default_factory=dict)
    month_over_month_comparison: Dict[str, Any] = Field(default_factory=dict)
    
    # Detailed analysis
    top_contact_reasons_analysis: str = ""
    billing_analysis: str = ""
    product_questions_analysis: str = ""
    account_questions_analysis: str = ""
    friction_points_analysis: str = ""
    customer_quotes: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Metrics
    total_conversations: int
    ai_resolution_rate: float
    median_response_time: str
    median_handling_time: str
    median_resolution_time: str
    overall_csat: float
    
    # Metadata
    analysis_duration_seconds: float
    tier1_countries: List[str] = Field(default_factory=list)


class CustomAnalysisResults(BaseModel):
    """Results for custom analysis mode."""
    request: AnalysisRequest
    analysis_date: datetime = Field(default_factory=datetime.now)
    
    # Custom analysis content
    custom_analysis_content: str = ""
    custom_insights: List[Dict[str, Any]] = Field(default_factory=list)
    custom_metrics: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    total_conversations_analyzed: int
    analysis_duration_seconds: float
    custom_prompt_used: str = ""


class GammaPresentationRequest(BaseModel):
    """Request for generating Gamma presentations."""
    analysis_results: Union[AnalysisResults, TrendAnalysisResults, VoiceOfCustomerResults, CustomAnalysisResults]
    template_type: str = "presentation"
    include_images: bool = True
    custom_styling: Optional[Dict[str, Any]] = None
    output_format: str = "gamma"  # gamma, markdown, html


class GammaPresentationResponse(BaseModel):
    """Response from Gamma presentation generation."""
    presentation_id: Optional[str] = None
    presentation_url: Optional[str] = None
    markdown_content: str = ""
    generation_successful: bool = False
    error_message: Optional[str] = None
    generation_time_seconds: float = 0.0


# ============================================================================
# INTER-AGENT PAYLOAD CONTRACTS
# ============================================================================


class SegmentationPayload(BaseModel):
    """
    Output from SegmentationAgent.
    
    Represents conversation segmentation by customer tier and agent type.
    """
    paid_customer_conversations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="All paid tier conversations"
    )
    paid_fin_resolved_conversations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Paid tier conversations resolved by Fin only"
    )
    free_fin_only_conversations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Free tier conversations (Fin-only)"
    )
    unknown_tier: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Conversations with unknown tier"
    )
    agent_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of conversations by agent type"
    )
    segmentation_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary statistics for segmentation"
    )
    
    @validator('agent_distribution')
    def validate_agent_types(cls, v):
        """Ensure only valid agent types are present"""
        valid_types = {
            # Legacy types
            'escalated', 'horatio', 'boldr', 'fin_ai', 'fin_resolved', 'unknown',
            # Escalation chain types (when track_escalations=True)
            'fin_only', 'fin_to_horatio', 'fin_to_boldr', 
            'fin_to_senior_direct', 'fin_to_vendor_to_senior'
        }
        invalid_keys = set(v.keys()) - valid_types
        if invalid_keys:
            raise ValueError(f"Invalid agent types: {invalid_keys}")
        return v


class TopicDetectionResult(BaseModel):
    """
    Output from TopicDetectionAgent.
    
    Represents detected topics with conversation assignments.
    """
    topics: List[Dict[str, Any]] = Field(
        description="List of detected topics with metadata"
    )
    topic_distribution: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Distribution of conversations across topics"
    )
    topics_by_conversation: Dict[str, List[Dict[str, Any]]] = Field(
        default_factory=dict,
        description="Mapping of conversation IDs to assigned topics"
    )
    unassigned_conversations: List[str] = Field(
        default_factory=list,
        description="Conversations that couldn't be assigned to a topic"
    )
    detection_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the detection process"
    )
    confidence_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Confidence scores for each topic"
    )
    
    @validator('topics')
    def validate_topics_structure(cls, v):
        """Ensure each topic has required fields"""
        for topic in v:
            if 'name' not in topic:
                raise ValueError(f"Topic missing required 'name' field")
        return v
    
    @validator('confidence_scores')
    def validate_confidence_range(cls, v):
        """Ensure confidence scores are between 0 and 1"""
        for topic, score in v.items():
            if not 0 <= score <= 1:
                raise ValueError(f"Confidence score for {topic} must be between 0 and 1, got {score}")
        return v


class SubtopicDetectionResult(BaseModel):
    """
    Output from SubtopicDetectionAgent.
    
    Represents detected subtopics within parent topics.
    """
    subtopics_by_tier1_topic: Dict[str, Dict[str, Any]] = Field(
        description="Nested mapping: parent_topic -> {tier2: {...}, tier3: {...}}"
    )
    subtopic_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about subtopic detection"
    )
    
    @validator('subtopics_by_tier1_topic')
    def validate_subtopics_structure(cls, v):
        """Ensure subtopics have required tier structure"""
        for parent_topic, subtopic_data in v.items():
            if not isinstance(subtopic_data, dict):
                raise ValueError(f"Subtopic data for {parent_topic} must be a dict")
            if 'tier2' not in subtopic_data or 'tier3' not in subtopic_data:
                raise ValueError(f"Subtopic data for {parent_topic} must contain 'tier2' and 'tier3' keys")
        return v


class FinAnalysisPayload(BaseModel):
    """
    Output from FinPerformanceAgent.
    
    Represents FIN performance analysis results with tier-based breakdown.
    """
    total_fin_conversations: int = Field(
        ge=0,
        description="Total conversations analyzed"
    )
    total_free_tier: int = Field(
        ge=0,
        description="Total free tier conversations"
    )
    total_paid_tier: int = Field(
        ge=0,
        description="Total paid tier conversations"
    )
    free_tier: Dict[str, Any] = Field(
        default_factory=dict,
        description="Free tier performance metrics"
    )
    paid_tier: Dict[str, Any] = Field(
        default_factory=dict,
        description="Paid tier performance metrics"
    )
    tier_comparison: Optional[Dict[str, Any]] = Field(
        None,
        description="Comparison between tiers"
    )
    llm_insights: Optional[str] = Field(
        None,
        description="LLM-generated insights about Fin performance"
    )
    
    @validator('free_tier', 'paid_tier')
    def validate_tier_metrics(cls, v):
        """Ensure tier metrics have required fields"""
        if v:  # Only validate if not empty
            required_fields = {'resolution_rate', 'knowledge_gaps_count', 'performance_by_topic'}
            missing = required_fields - set(v.keys())
            if missing:
                raise ValueError(f"Tier metrics missing required fields: {missing}")
        return v


class TrendAnalysisPayload(BaseModel):
    """
    Output from TrendAgent.
    
    Represents trend analysis results over time.
    """
    trends: List[Dict[str, Any]] = Field(
        description="List of detected trends with metadata"
    )
    week_over_week_changes: Dict[str, float] = Field(
        default_factory=dict,
        description="Percentage changes week-over-week"
    )
    trending_topics: List[str] = Field(
        default_factory=list,
        description="Topics with significant trend changes"
    )
    analysis_period: Dict[str, str] = Field(
        description="Start and end dates of analysis"
    )
    trend_insights: Optional[str] = Field(
        None,
        description="Natural language insights about trends"
    )
    
    @validator('analysis_period')
    def validate_period_fields(cls, v):
        """Ensure period has required date fields"""
        if 'start_date' not in v or 'end_date' not in v:
            raise ValueError("analysis_period must contain 'start_date' and 'end_date'")
        return v
