"""
Canny sentiment analyzer for product feedback analysis.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter

from src.services.ai_model_factory import AIModelFactory, AIModel
from src.services.canny_preprocessor import CannyPreprocessor
from src.models.canny_models import (
    CannyAnalysisResults, CannySentimentAnalysis, CannyPostWithSentiment,
    CannyEngagementMetrics, CannyVoteAnalysis, CannyWeeklySnapshot
)

logger = logging.getLogger(__name__)


class CannyAnalyzer:
    """Analyzer for Canny product feedback data."""
    
    def __init__(self, ai_factory: AIModelFactory):
        self.ai_factory = ai_factory
        self.preprocessor = CannyPreprocessor()
        self.logger = logging.getLogger(__name__)
    
    async def analyze_canny_sentiment(
        self,
        posts: List[Dict[str, Any]],
        ai_model: AIModel,
        enable_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze sentiment for Canny posts and comments.
        
        Args:
            posts: List of preprocessed Canny posts
            ai_model: AI model to use for sentiment analysis
            enable_fallback: Whether to fallback to other AI model if primary fails
            
        Returns:
            Analysis results with sentiment breakdown
        """
        self.logger.info(f"Starting Canny sentiment analysis for {len(posts)} posts")
        
        try:
            # Preprocess posts
            processed_posts = self.preprocessor.preprocess_posts(posts)
            
            if not processed_posts:
                self.logger.warning("No posts to analyze after preprocessing")
                return self._create_empty_results()
            
            # Analyze sentiment for each post
            posts_with_sentiment = []
            for post in processed_posts:
                try:
                    post_with_sentiment = await self._analyze_post_sentiment(
                        post, ai_model, enable_fallback
                    )
                    if post_with_sentiment:
                        posts_with_sentiment.append(post_with_sentiment)
                except Exception as e:
                    self.logger.warning(f"Failed to analyze sentiment for post {post.get('id')}: {e}")
                    continue
            
            # Generate analysis results
            results = await self._generate_analysis_results(posts_with_sentiment)
            
            self.logger.info(f"Canny sentiment analysis completed for {len(posts_with_sentiment)} posts")
            return results
            
        except Exception as e:
            self.logger.error(f"Canny sentiment analysis failed: {e}")
            raise
    
    async def _analyze_post_sentiment(
        self,
        post: Dict[str, Any],
        ai_model: AIModel,
        enable_fallback: bool
    ) -> Optional[Dict[str, Any]]:
        """Analyze sentiment for a single post."""
        try:
            # Get AI client
            ai_client = self.ai_factory.get_client(ai_model)
            
            # Analyze post content
            content = post.get('content_for_analysis', '')
            if not content:
                self.logger.warning(f"Post {post.get('id')} has no content for analysis")
                return None
            
            # Analyze main post sentiment
            post_sentiment = await self.ai_factory.analyze_sentiment(
                content, ai_model, enable_fallback
            )
            
            # Analyze comments sentiment
            comments_sentiment = {}
            comments = post.get('comments', [])
            
            for comment in comments:
                try:
                    comment_content = comment.get('content_for_analysis', '')
                    if comment_content:
                        comment_sentiment = await self.ai_factory.analyze_sentiment(
                            comment_content, ai_model, enable_fallback
                        )
                        comments_sentiment[comment['id']] = comment_sentiment
                except Exception as e:
                    self.logger.warning(f"Failed to analyze comment {comment.get('id')}: {e}")
                    continue
            
            # Add sentiment analysis to post
            post['sentiment_analysis'] = post_sentiment
            post['comments_sentiment'] = comments_sentiment
            
            return post
            
        except Exception as e:
            self.logger.error(f"Failed to analyze post sentiment: {e}")
            return None
    
    async def _generate_analysis_results(self, posts_with_sentiment: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive analysis results."""
        if not posts_with_sentiment:
            return self._create_empty_results()
        
        # Calculate sentiment summary
        sentiment_summary = self._calculate_sentiment_summary(posts_with_sentiment)
        
        # Identify top requests
        top_requests = self._identify_top_requests(posts_with_sentiment)
        
        # Calculate status breakdown
        status_breakdown = self._calculate_status_breakdown(posts_with_sentiment)
        
        # Calculate category breakdown
        category_breakdown = self._calculate_category_breakdown(posts_with_sentiment)
        
        # Analyze voting patterns
        vote_analysis = self._analyze_voting_patterns(posts_with_sentiment)
        
        # Calculate engagement metrics
        engagement_metrics = self._calculate_engagement_metrics(posts_with_sentiment)
        
        # Identify trending posts
        trending_posts = self._identify_trending_posts(posts_with_sentiment)
        
        # Generate insights
        insights = self._generate_insights(
            sentiment_summary, top_requests, status_breakdown,
            category_breakdown, vote_analysis, engagement_metrics
        )
        
        return {
            'posts_analyzed': len(posts_with_sentiment),
            'sentiment_summary': sentiment_summary,
            'top_requests': top_requests,
            'status_breakdown': status_breakdown,
            'category_breakdown': category_breakdown,
            'vote_analysis': vote_analysis,
            'engagement_metrics': engagement_metrics,
            'trending_posts': trending_posts,
            'insights': insights,
            'metadata': {
                'analysis_date': datetime.now().isoformat(),
                'total_posts': len(posts_with_sentiment),
                'posts_with_sentiment': len([p for p in posts_with_sentiment if p.get('sentiment_analysis')])
            }
        }
    
    def _calculate_sentiment_summary(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall sentiment summary."""
        sentiment_counts = Counter()
        confidence_scores = []
        sentiment_by_status = defaultdict(Counter)
        sentiment_by_category = defaultdict(Counter)
        
        for post in posts:
            sentiment_analysis = post.get('sentiment_analysis')
            if not sentiment_analysis:
                continue
            
            sentiment = sentiment_analysis.get('sentiment', 'neutral')
            confidence = sentiment_analysis.get('confidence', 0.0)
            
            sentiment_counts[sentiment] += 1
            confidence_scores.append(confidence)
            
            # Sentiment by status
            status = post.get('status', 'open')
            sentiment_by_status[status][sentiment] += 1
            
            # Sentiment by category
            category = post.get('category', 'uncategorized')
            sentiment_by_category[category][sentiment] += 1
        
        total_posts = len(posts)
        if total_posts == 0:
            return {
                'overall': 'neutral',
                'distribution': {'positive': 0, 'negative': 0, 'neutral': 0},
                'average_confidence': 0.0,
                'by_status': {},
                'by_category': {}
            }
        
        # Calculate percentages
        distribution = {
            'positive': round((sentiment_counts['positive'] / total_posts) * 100, 1),
            'negative': round((sentiment_counts['negative'] / total_posts) * 100, 1),
            'neutral': round((sentiment_counts['neutral'] / total_posts) * 100, 1)
        }
        
        # Determine overall sentiment
        overall_sentiment = sentiment_counts.most_common(1)[0][0] if sentiment_counts else 'neutral'
        
        return {
            'overall': overall_sentiment,
            'distribution': distribution,
            'counts': dict(sentiment_counts),
            'average_confidence': round(sum(confidence_scores) / len(confidence_scores), 2) if confidence_scores else 0.0,
            'by_status': {status: dict(sentiment) for status, sentiment in sentiment_by_status.items()},
            'by_category': {category: dict(sentiment) for category, sentiment in sentiment_by_category.items()}
        }
    
    def _identify_top_requests(self, posts: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
        """Identify top requests by engagement and sentiment."""
        # Sort by engagement score (votes + comments)
        sorted_posts = sorted(
            posts,
            key=lambda p: p.get('engagement_score', 0),
            reverse=True
        )
        
        top_requests = []
        for post in sorted_posts[:limit]:
            sentiment_analysis = post.get('sentiment_analysis', {})
            
            request = {
                'id': post.get('id'),
                'title': post.get('title', ''),
                'votes': post.get('score', 0),
                'comments': post.get('commentCount', 0),
                'engagement_score': post.get('engagement_score', 0),
                'sentiment': sentiment_analysis.get('sentiment', 'neutral'),
                'confidence': sentiment_analysis.get('confidence', 0.0),
                'status': post.get('status', 'open'),
                'category': post.get('category', 'uncategorized'),
                'url': post.get('url', ''),
                'created': post.get('created'),
                'is_trending': post.get('is_trending', False)
            }
            top_requests.append(request)
        
        return top_requests
    
    def _calculate_status_breakdown(self, posts: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate breakdown by status."""
        status_counts = Counter()
        
        for post in posts:
            status = post.get('status', 'open')
            status_counts[status] += 1
        
        return dict(status_counts)
    
    def _calculate_category_breakdown(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate breakdown by category."""
        category_counts = Counter()
        category_engagement = defaultdict(list)
        
        for post in posts:
            category = post.get('category', 'uncategorized')
            category_counts[category] += 1
            category_engagement[category].append(post.get('engagement_score', 0))
        
        # Calculate average engagement per category
        category_metrics = {}
        for category, engagement_scores in category_engagement.items():
            category_metrics[category] = {
                'count': category_counts[category],
                'average_engagement': round(sum(engagement_scores) / len(engagement_scores), 2),
                'total_engagement': sum(engagement_scores)
            }
        
        return category_metrics
    
    def _analyze_voting_patterns(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze voting patterns and trends."""
        total_votes = sum(post.get('score', 0) for post in posts)
        total_posts = len(posts)
        
        # Votes by status
        votes_by_status = defaultdict(int)
        for post in posts:
            status = post.get('status', 'open')
            votes = post.get('score', 0)
            votes_by_status[status] += votes
        
        # Vote distribution
        vote_distribution = [post.get('score', 0) for post in posts]
        vote_distribution.sort(reverse=True)
        
        return {
            'total_votes': total_votes,
            'average_votes_per_post': round(total_votes / total_posts, 2) if total_posts > 0 else 0,
            'votes_by_status': dict(votes_by_status),
            'top_voted_posts': vote_distribution[:10],
            'vote_distribution': {
                'min': min(vote_distribution) if vote_distribution else 0,
                'max': max(vote_distribution) if vote_distribution else 0,
                'median': vote_distribution[len(vote_distribution)//2] if vote_distribution else 0
            }
        }
    
    def _calculate_engagement_metrics(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate engagement metrics."""
        total_votes = sum(post.get('score', 0) for post in posts)
        total_comments = sum(post.get('commentCount', 0) for post in posts)
        total_posts = len(posts)
        
        engagement_scores = [post.get('engagement_score', 0) for post in posts]
        engagement_scores.sort(reverse=True)
        
        return {
            'total_votes': total_votes,
            'total_comments': total_comments,
            'total_posts': total_posts,
            'average_votes_per_post': round(total_votes / total_posts, 2) if total_posts > 0 else 0,
            'average_comments_per_post': round(total_comments / total_posts, 2) if total_posts > 0 else 0,
            'average_engagement_score': round(sum(engagement_scores) / len(engagement_scores), 2) if engagement_scores else 0,
            'top_engagement_scores': engagement_scores[:10],
            'high_engagement_posts': len([score for score in engagement_scores if score > 20]),
            'medium_engagement_posts': len([score for score in engagement_scores if 5 <= score <= 20]),
            'low_engagement_posts': len([score for score in engagement_scores if score < 5])
        }
    
    def _identify_trending_posts(self, posts: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        """Identify trending posts based on velocity and engagement."""
        trending_posts = []
        
        for post in posts:
            if post.get('is_trending', False):
                sentiment_analysis = post.get('sentiment_analysis', {})
                
                trending_post = {
                    'id': post.get('id'),
                    'title': post.get('title', ''),
                    'votes': post.get('score', 0),
                    'comments': post.get('commentCount', 0),
                    'vote_velocity': post.get('vote_velocity', 0),
                    'comment_velocity': post.get('comment_velocity', 0),
                    'sentiment': sentiment_analysis.get('sentiment', 'neutral'),
                    'status': post.get('status', 'open'),
                    'url': post.get('url', ''),
                    'created': post.get('created')
                }
                trending_posts.append(trending_post)
        
        # Sort by vote velocity
        trending_posts.sort(key=lambda p: p.get('vote_velocity', 0), reverse=True)
        
        return trending_posts[:limit]
    
    def _generate_insights(
        self,
        sentiment_summary: Dict[str, Any],
        top_requests: List[Dict[str, Any]],
        status_breakdown: Dict[str, int],
        category_breakdown: Dict[str, Any],
        vote_analysis: Dict[str, Any],
        engagement_metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable insights from analysis."""
        insights = []
        
        # Sentiment insights
        overall_sentiment = sentiment_summary.get('overall', 'neutral')
        if overall_sentiment == 'positive':
            insights.append("Overall sentiment is positive, indicating strong user satisfaction with product direction")
        elif overall_sentiment == 'negative':
            insights.append("Overall sentiment is negative, suggesting urgent attention needed for user concerns")
        else:
            insights.append("Overall sentiment is neutral, indicating mixed user feedback requiring careful analysis")
        
        # Top request insights
        if top_requests:
            top_request = top_requests[0]
            insights.append(f"Top request '{top_request['title']}' has {top_request['votes']} votes and {top_request['sentiment']} sentiment")
        
        # Status insights
        open_posts = status_breakdown.get('open', 0)
        planned_posts = status_breakdown.get('planned', 0)
        if open_posts > planned_posts * 2:
            insights.append(f"High number of open requests ({open_posts}) compared to planned ({planned_posts}), consider prioritizing roadmap planning")
        
        # Engagement insights
        avg_engagement = engagement_metrics.get('average_engagement_score', 0)
        if avg_engagement > 15:
            insights.append("High average engagement indicates active user community and strong product interest")
        elif avg_engagement < 5:
            insights.append("Low average engagement suggests need for better user engagement strategies")
        
        # Trending insights
        high_engagement = engagement_metrics.get('high_engagement_posts', 0)
        if high_engagement > 5:
            insights.append(f"{high_engagement} posts have high engagement, indicating strong user interest in specific features")
        
        return insights
    
    def _create_empty_results(self) -> Dict[str, Any]:
        """Create empty results structure."""
        return {
            'posts_analyzed': 0,
            'sentiment_summary': {
                'overall': 'neutral',
                'distribution': {'positive': 0, 'negative': 0, 'neutral': 0},
                'average_confidence': 0.0,
                'by_status': {},
                'by_category': {}
            },
            'top_requests': [],
            'status_breakdown': {},
            'category_breakdown': {},
            'vote_analysis': {
                'total_votes': 0,
                'average_votes_per_post': 0,
                'votes_by_status': {},
                'top_voted_posts': [],
                'vote_distribution': {'min': 0, 'max': 0, 'median': 0}
            },
            'engagement_metrics': {
                'total_votes': 0,
                'total_comments': 0,
                'total_posts': 0,
                'average_votes_per_post': 0,
                'average_comments_per_post': 0,
                'average_engagement_score': 0,
                'top_engagement_scores': [],
                'high_engagement_posts': 0,
                'medium_engagement_posts': 0,
                'low_engagement_posts': 0
            },
            'trending_posts': [],
            'insights': ["No posts available for analysis"],
            'metadata': {
                'analysis_date': datetime.now().isoformat(),
                'total_posts': 0,
                'posts_with_sentiment': 0
            }
        }
