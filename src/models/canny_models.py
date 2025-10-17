"""
Pydantic data models for Canny API integration.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date
from pydantic import BaseModel, Field, validator
from enum import Enum


class CannyPostStatus(str, Enum):
    """Canny post status values."""
    OPEN = "open"
    PLANNED = "planned"
    IN_PROGRESS = "in progress"
    COMPLETE = "complete"
    CLOSED = "closed"


class CannyBoard(BaseModel):
    """Canny board model."""
    id: str
    name: str
    url: str
    postCount: int
    created: Optional[datetime] = None
    description: Optional[str] = None


class CannyAuthor(BaseModel):
    """Canny author/user model."""
    id: str
    name: str
    email: Optional[str] = None
    avatarURL: Optional[str] = None


class CannyPost(BaseModel):
    """Canny post model."""
    id: str
    title: str
    details: str
    board: Dict[str, Any]
    author: Dict[str, Any]
    category: Optional[str] = None
    created: datetime
    score: int = 0  # vote count
    status: CannyPostStatus = CannyPostStatus.OPEN
    commentCount: int = 0
    url: str
    tags: Optional[List[str]] = None
    imageURLs: Optional[List[str]] = None
    
    @validator('created', pre=True)
    def parse_created(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        return v


class CannyComment(BaseModel):
    """Canny comment model."""
    id: str
    author: Dict[str, Any]
    post: str  # post_id
    value: str  # comment text
    created: datetime
    imageURLs: Optional[List[str]] = None
    
    @validator('created', pre=True)
    def parse_created(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        return v


class CannyVote(BaseModel):
    """Canny vote model."""
    id: str
    post: str  # post_id
    voter: Dict[str, Any]
    created: datetime
    
    @validator('created', pre=True)
    def parse_created(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        return v


class CannySentimentAnalysis(BaseModel):
    """Sentiment analysis result for Canny content."""
    sentiment: str  # "positive", "negative", "neutral"
    confidence: float  # 0.0 to 1.0
    analysis: str
    emotional_indicators: List[str] = []
    model: str  # "openai" or "claude"
    language: Optional[str] = None


class CannyPostWithSentiment(CannyPost):
    """Canny post with sentiment analysis."""
    sentiment_analysis: Optional[CannySentimentAnalysis] = None
    comments_sentiment: Optional[Dict[str, CannySentimentAnalysis]] = None
    engagement_score: Optional[float] = None  # Calculated from votes + comments


class CannyAnalysisResults(BaseModel):
    """Results from Canny analysis."""
    boards: List[Dict[str, Any]]
    posts_analyzed: int
    date_range: Dict[str, str]
    sentiment_summary: Dict[str, Any]
    top_requests: List[Dict[str, Any]]
    status_breakdown: Dict[str, int]
    category_breakdown: Dict[str, Any]
    vote_analysis: Dict[str, Any]
    engagement_metrics: Dict[str, Any]
    trending_posts: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class CannyWeeklySnapshot(BaseModel):
    """Weekly snapshot of Canny data for historical analysis."""
    snapshot_date: date
    total_posts: int
    open_posts: int
    planned_posts: int
    in_progress_posts: int
    completed_posts: int
    closed_posts: int
    total_votes: int
    total_comments: int
    sentiment_breakdown: Dict[str, Any]
    top_requests: List[Dict[str, Any]]
    engagement_trends: Dict[str, Any]


class CannyEngagementMetrics(BaseModel):
    """Engagement metrics for Canny posts."""
    total_votes: int
    total_comments: int
    average_votes_per_post: float
    average_comments_per_post: float
    vote_velocity: Dict[str, float]  # votes per day for trending posts
    comment_velocity: Dict[str, float]  # comments per day
    top_engaged_posts: List[Dict[str, Any]]


class CannyVoteAnalysis(BaseModel):
    """Analysis of voting patterns."""
    total_votes: int
    unique_voters: int
    votes_by_status: Dict[str, int]
    votes_by_category: Dict[str, int]
    vote_distribution: Dict[str, int]  # votes per post
    trending_votes: List[Dict[str, Any]]  # posts with high vote velocity


class CannyCrossPlatformInsight(BaseModel):
    """Insights that correlate Canny and Intercom data."""
    intercom_issue: str
    canny_request: str
    correlation_strength: float  # 0.0 to 1.0
    intercom_volume: int
    canny_votes: int
    combined_priority_score: float
    recommendation: str
