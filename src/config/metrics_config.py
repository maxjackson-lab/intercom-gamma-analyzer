"""
Metrics configuration for Voice of Customer and trend analysis.
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum


class MetricCategory(Enum):
    """Categories of metrics for analysis."""
    VOLUME = "volume"
    EFFICIENCY = "efficiency"
    SATISFACTION = "satisfaction"
    TOPICS = "topics"
    GEOGRAPHIC = "geographic"
    FRICTION = "friction"
    CHANNEL = "channel"


@dataclass
class MetricDefinition:
    """Definition of a business metric."""
    name: str
    description: str
    calculation_method: str
    category: MetricCategory
    required_fields: List[str]
    aggregation_type: str = "sum"  # sum, mean, median, count, etc.


# Voice of Customer Metrics Configuration
VOICE_METRICS: Dict[str, MetricDefinition] = {
    # Volume Metrics
    "total_conversations": MetricDefinition(
        name="total_conversations",
        description="Total customer interactions",
        calculation_method="count_conversations",
        category=MetricCategory.VOLUME,
        required_fields=["id"],
        aggregation_type="count"
    ),
    "ai_resolution_rate": MetricDefinition(
        name="ai_resolution_rate",
        description="Cases handled by AI without human intervention",
        calculation_method="calculate_ai_resolution_rate",
        category=MetricCategory.VOLUME,
        required_fields=["conversation_parts"],
        aggregation_type="percentage"
    ),
    "conversation_growth": MetricDefinition(
        name="conversation_growth",
        description="Month-over-month growth rate",
        calculation_method="calculate_growth_rate",
        category=MetricCategory.VOLUME,
        required_fields=["created_at"],
        aggregation_type="percentage"
    ),
    
    # Efficiency Metrics
    "median_first_response": MetricDefinition(
        name="median_first_response",
        description="Median first response time",
        calculation_method="calculate_median_response_time",
        category=MetricCategory.EFFICIENCY,
        required_fields=["created_at", "conversation_parts"],
        aggregation_type="median"
    ),
    "median_handling_time": MetricDefinition(
        name="median_handling_time",
        description="Median time spent by teammate",
        calculation_method="calculate_median_handling_time",
        category=MetricCategory.EFFICIENCY,
        required_fields=["conversation_parts"],
        aggregation_type="median"
    ),
    "median_resolution_time": MetricDefinition(
        name="median_resolution_time",
        description="Median time to close",
        calculation_method="calculate_median_resolution_time",
        category=MetricCategory.EFFICIENCY,
        required_fields=["created_at", "state"],
        aggregation_type="median"
    ),
    "response_time_by_channel": MetricDefinition(
        name="response_time_by_channel",
        description="Response time breakdown (Chat vs Email)",
        calculation_method="calculate_response_time_by_channel",
        category=MetricCategory.EFFICIENCY,
        required_fields=["source", "conversation_parts"],
        aggregation_type="grouped_median"
    ),
    
    # Satisfaction Metrics
    "overall_csat": MetricDefinition(
        name="overall_csat",
        description="Customer Satisfaction Rating",
        calculation_method="calculate_overall_csat",
        category=MetricCategory.SATISFACTION,
        required_fields=["conversation_rating"],
        aggregation_type="mean"
    ),
    "csat_by_tier": MetricDefinition(
        name="csat_by_tier",
        description="CSAT by user tier (Pro, Plus, Free)",
        calculation_method="calculate_csat_by_tier",
        category=MetricCategory.SATISFACTION,
        required_fields=["conversation_rating", "contacts"],
        aggregation_type="grouped_mean"
    ),
    "csat_trend": MetricDefinition(
        name="csat_trend",
        description="Month-over-month CSAT change",
        calculation_method="calculate_csat_trend",
        category=MetricCategory.SATISFACTION,
        required_fields=["conversation_rating", "created_at"],
        aggregation_type="trend"
    ),
    
    # Topic Metrics
    "top_contact_reasons": MetricDefinition(
        name="top_contact_reasons",
        description="Top 3 reasons for contacting support",
        calculation_method="extract_top_contact_reasons",
        category=MetricCategory.TOPICS,
        required_fields=["source", "conversation_parts"],
        aggregation_type="top_n"
    ),
    "billing_breakdown": MetricDefinition(
        name="billing_breakdown",
        description="Billing question categories",
        calculation_method="categorize_billing_questions",
        category=MetricCategory.TOPICS,
        required_fields=["source", "conversation_parts"],
        aggregation_type="categorized_count"
    ),
    "product_questions": MetricDefinition(
        name="product_questions",
        description="Top 15 product question areas",
        calculation_method="extract_product_questions",
        category=MetricCategory.TOPICS,
        required_fields=["source", "conversation_parts"],
        aggregation_type="top_n"
    ),
    "account_questions": MetricDefinition(
        name="account_questions",
        description="Account management issues",
        calculation_method="extract_account_questions",
        category=MetricCategory.TOPICS,
        required_fields=["source", "conversation_parts"],
        aggregation_type="categorized_count"
    ),
    
    # Geographic Metrics
    "tier1_metrics": MetricDefinition(
        name="tier1_metrics",
        description="Performance by tier 1 countries",
        calculation_method="calculate_tier1_metrics",
        category=MetricCategory.GEOGRAPHIC,
        required_fields=["contacts"],
        aggregation_type="grouped_metrics"
    ),
    "country_breakdown": MetricDefinition(
        name="country_breakdown",
        description="Conversation volume by country",
        calculation_method="calculate_country_breakdown",
        category=MetricCategory.GEOGRAPHIC,
        required_fields=["contacts"],
        aggregation_type="grouped_count"
    ),
    "regional_trends": MetricDefinition(
        name="regional_trends",
        description="Regional performance patterns",
        calculation_method="calculate_regional_trends",
        category=MetricCategory.GEOGRAPHIC,
        required_fields=["contacts", "created_at"],
        aggregation_type="trend_analysis"
    ),
    
    # Friction Metrics
    "escalation_patterns": MetricDefinition(
        name="escalation_patterns",
        description="Common escalation triggers",
        calculation_method="identify_escalation_patterns",
        category=MetricCategory.FRICTION,
        required_fields=["conversation_parts", "state"],
        aggregation_type="pattern_analysis"
    ),
    "friction_points": MetricDefinition(
        name="friction_points",
        description="Customer pain points",
        calculation_method="identify_friction_points",
        category=MetricCategory.FRICTION,
        required_fields=["source", "conversation_parts"],
        aggregation_type="sentiment_analysis"
    ),
    "chargeback_analysis": MetricDefinition(
        name="chargeback_analysis",
        description="Chargeback trends and reasons",
        calculation_method="analyze_chargeback_patterns",
        category=MetricCategory.FRICTION,
        required_fields=["source", "conversation_parts"],
        aggregation_type="pattern_analysis"
    ),
    
    # Channel Metrics
    "channel_performance": MetricDefinition(
        name="channel_performance",
        description="Performance by communication channel",
        calculation_method="calculate_channel_performance",
        category=MetricCategory.CHANNEL,
        required_fields=["source"],
        aggregation_type="grouped_metrics"
    ),
    "channel_satisfaction": MetricDefinition(
        name="channel_satisfaction",
        description="Satisfaction by channel",
        calculation_method="calculate_channel_satisfaction",
        category=MetricCategory.CHANNEL,
        required_fields=["source", "conversation_rating"],
        aggregation_type="grouped_mean"
    )
}


# General Purpose Trend Analysis Metrics
TREND_METRICS: Dict[str, MetricDefinition] = {
    "conversation_volume": MetricDefinition(
        name="conversation_volume",
        description="Conversation volume over time",
        calculation_method="calculate_volume_trend",
        category=MetricCategory.VOLUME,
        required_fields=["created_at"],
        aggregation_type="time_series"
    ),
    "response_time_trend": MetricDefinition(
        name="response_time_trend",
        description="Response time trends",
        calculation_method="calculate_response_time_trend",
        category=MetricCategory.EFFICIENCY,
        required_fields=["created_at", "conversation_parts"],
        aggregation_type="time_series"
    ),
    "satisfaction_trend": MetricDefinition(
        name="satisfaction_trend",
        description="Satisfaction trends over time",
        calculation_method="calculate_satisfaction_trend",
        category=MetricCategory.SATISFACTION,
        required_fields=["conversation_rating", "created_at"],
        aggregation_type="time_series"
    ),
    "topic_trends": MetricDefinition(
        name="topic_trends",
        description="Topic trends over time",
        calculation_method="calculate_topic_trends",
        category=MetricCategory.TOPICS,
        required_fields=["source", "conversation_parts", "created_at"],
        aggregation_type="time_series"
    ),
    "keyword_analysis": MetricDefinition(
        name="keyword_analysis",
        description="Keyword frequency and trends",
        calculation_method="extract_keyword_trends",
        category=MetricCategory.TOPICS,
        required_fields=["source", "conversation_parts"],
        aggregation_type="frequency_analysis"
    ),
    "sentiment_analysis": MetricDefinition(
        name="sentiment_analysis",
        description="Sentiment trends over time",
        calculation_method="analyze_sentiment_trends",
        category=MetricCategory.SATISFACTION,
        required_fields=["source", "conversation_parts", "created_at"],
        aggregation_type="sentiment_analysis"
    )
}


# Metric calculation patterns
CALCULATION_PATTERNS = {
    "time_based": ["created_at", "updated_at", "closed_at"],
    "rating_based": ["conversation_rating"],
    "text_based": ["source.body", "conversation_parts.body"],
    "geographic_based": ["contacts.location"],
    "channel_based": ["source.type"],
    "state_based": ["state"],
    "agent_based": ["conversation_parts.author"]
}


def get_metrics_by_category(category: MetricCategory) -> Dict[str, MetricDefinition]:
    """Get all metrics for a specific category."""
    return {
        name: metric for name, metric in VOICE_METRICS.items()
        if metric.category == category
    }


def get_required_fields_for_metrics(metric_names: List[str]) -> List[str]:
    """Get all required fields for a list of metrics."""
    all_fields = set()
    for metric_name in metric_names:
        if metric_name in VOICE_METRICS:
            all_fields.update(VOICE_METRICS[metric_name].required_fields)
        elif metric_name in TREND_METRICS:
            all_fields.update(TREND_METRICS[metric_name].required_fields)
    return list(all_fields)

