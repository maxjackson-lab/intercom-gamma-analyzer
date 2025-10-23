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

