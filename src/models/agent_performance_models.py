"""
Pydantic models for individual agent performance tracking and coaching.
"""

from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class AdminProfile(BaseModel):
    """Cached admin profile from Intercom API"""
    id: str
    name: str
    email: str = Field(description="Work email from Intercom API")
    public_email: Optional[str] = Field(None, description="Public/display email (may differ from work email)")
    vendor: Literal["horatio", "boldr", "gamma", "unknown"]
    active: bool = True
    cached_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CategoryPerformance(BaseModel):
    """Performance metrics for a specific taxonomy category"""
    primary_category: str
    subcategory: Optional[str] = None
    volume: int = Field(description="Number of conversations in this category")
    fcr_rate: float = Field(ge=0, le=1, description="First Contact Resolution rate")
    escalation_rate: float = Field(ge=0, le=1, description="Escalation rate to senior staff")
    median_resolution_hours: float = Field(ge=0, description="Median time to resolution")
    performance_level: Literal["excellent", "good", "fair", "poor"] = Field(
        description="Performance level based on thresholds"
    )


class IndividualAgentMetrics(BaseModel):
    """Comprehensive performance metrics for a single agent"""
    agent_id: str
    agent_name: str
    agent_email: str
    vendor: str
    
    # Overall metrics
    total_conversations: int
    fcr_rate: float = Field(ge=0, le=1)
    reopen_rate: float = Field(ge=0, le=1)
    escalation_rate: float = Field(ge=0, le=1)
    median_resolution_hours: float = Field(ge=0)
    median_response_hours: float = Field(ge=0)
    over_48h_count: int = Field(description="Number of tickets taking over 48 hours")
    avg_conversation_complexity: float = Field(
        description="Average conversation parts per conversation"
    )
    
    # CSAT metrics (customer satisfaction)
    csat_score: float = Field(
        default=0.0,
        ge=0, 
        le=5, 
        description="Average CSAT rating (1-5 stars)"
    )
    csat_survey_count: int = Field(
        default=0,
        description="Number of conversations with CSAT ratings"
    )
    negative_csat_count: int = Field(
        default=0,
        description="Number of low ratings (1-2 stars)"
    )
    rating_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Breakdown by star rating (1-5)"
    )
    
    # Troubleshooting metrics (effort and methodology)
    avg_troubleshooting_score: float = Field(
        default=0.0,
        ge=0,
        le=1,
        description="Average troubleshooting effort score (0-1)"
    )
    avg_diagnostic_questions: float = Field(
        default=0.0,
        description="Average number of diagnostic questions per conversation"
    )
    premature_escalation_rate: float = Field(
        default=0.0,
        ge=0,
        le=1,
        description="% of conversations escalated without adequate troubleshooting"
    )
    troubleshooting_consistency: float = Field(
        default=0.0,
        ge=0,
        le=1,
        description="Consistency of troubleshooting approach (0-1)"
    )
    
    # Taxonomy-based performance breakdown
    performance_by_category: Dict[str, CategoryPerformance] = Field(
        default_factory=dict,
        description="Performance breakdown by primary category (Billing, Bug, Account, etc.)"
    )
    performance_by_subcategory: Dict[str, CategoryPerformance] = Field(
        default_factory=dict,
        description="Detailed performance by subcategory (Billing>Refund, Bug>Export, etc.)"
    )
    
    # Strengths and weaknesses using taxonomy
    strong_categories: List[str] = Field(
        default_factory=list,
        description="Categories with excellent performance (>85% FCR, <10% escalation)"
    )
    weak_categories: List[str] = Field(
        default_factory=list,
        description="Categories needing improvement (<70% FCR or >20% escalation)"
    )
    strong_subcategories: List[str] = Field(
        default_factory=list,
        description="Specific subcategories where agent excels"
    )
    weak_subcategories: List[str] = Field(
        default_factory=list,
        description="Specific subcategories needing coaching"
    )
    
    # Rankings
    fcr_rank: int = Field(description="Rank by FCR (1 = best)")
    response_time_rank: int = Field(description="Rank by response time (1 = fastest)")
    
    # Coaching insights
    coaching_priority: Literal["low", "medium", "high"]
    coaching_focus_areas: List[str] = Field(
        default_factory=list,
        description="Specific subcategories to focus coaching on"
    )
    praise_worthy_achievements: List[str] = Field(
        default_factory=list,
        description="Notable achievements and strengths"
    )
    
    # Example conversations
    best_example_url: Optional[str] = None
    needs_coaching_example_url: Optional[str] = None
    worst_csat_examples: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Worst CSAT examples with conversation links (for coaching)"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TeamTrainingNeed(BaseModel):
    """Identified training need for the team"""
    topic: str = Field(description="Subcategory or topic needing training")
    reason: str = Field(description="Why this training is needed")
    affected_agents: List[str] = Field(description="Agent names who need this training")
    priority: Literal["low", "medium", "high"]
    example_conversations: List[str] = Field(
        default_factory=list,
        description="Intercom URLs showing the issue"
    )


class VendorPerformanceReport(BaseModel):
    """Complete vendor performance report with individual agent breakdowns"""
    vendor_name: str
    analysis_period: Dict[str, str] = Field(
        description="Start and end dates of analysis"
    )
    
    # Team-level metrics
    team_metrics: Dict[str, Any] = Field(
        description="Overall team performance summary"
    )
    
    # Individual agents
    agents: List[IndividualAgentMetrics] = Field(
        description="All agents ranked by performance"
    )
    agents_needing_coaching: List[IndividualAgentMetrics] = Field(
        default_factory=list,
        description="Bottom 25% or those with specific issues"
    )
    agents_for_praise: List[IndividualAgentMetrics] = Field(
        default_factory=list,
        description="Top 25% or significant improvements"
    )
    
    # Team-wide patterns
    team_strengths: List[str] = Field(
        default_factory=list,
        description="Categories where team excels"
    )
    team_weaknesses: List[str] = Field(
        default_factory=list,
        description="Categories where team struggles"
    )
    team_training_needs: List[TeamTrainingNeed] = Field(
        default_factory=list,
        description="Identified training needs with affected agents"
    )
    
    # Trending
    week_over_week_changes: Optional[Dict[str, float]] = Field(
        None,
        description="Percentage changes in key metrics vs previous period"
    )
    
    # Summary
    highlights: List[str] = Field(
        default_factory=list,
        description="Positive achievements this period"
    )
    lowlights: List[str] = Field(
        default_factory=list,
        description="Areas of concern this period"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

