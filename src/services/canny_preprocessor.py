"""
Canny data preprocessor for cleaning and normalizing feedback data.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import re

from models.canny_models import (
    CannyPost, CannyComment, CannyVote, CannyPostWithSentiment,
    CannyPostStatus
)

logger = logging.getLogger(__name__)


class CannyPreprocessor:
    """Preprocessor for Canny feedback data."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def preprocess_posts(self, raw_posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Preprocess raw Canny posts data.
        
        Args:
            raw_posts: Raw posts data from Canny API
            
        Returns:
            Cleaned and normalized posts data
        """
        processed_posts = []
        
        for post in raw_posts:
            try:
                processed_post = self._preprocess_single_post(post)
                if processed_post:
                    processed_posts.append(processed_post)
            except Exception as e:
                self.logger.warning(f"Failed to preprocess post {post.get('id', 'unknown')}: {e}")
                continue
        
        self.logger.info(f"Preprocessed {len(processed_posts)} out of {len(raw_posts)} posts")
        return processed_posts
    
    def _preprocess_single_post(self, post: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Preprocess a single post."""
        try:
            # Extract basic fields
            post_id = post.get('id')
            if not post_id:
                return None
            
            # Clean and normalize text content
            title = self._clean_text(post.get('title', ''))
            details = self._clean_text(post.get('details', ''))
            
            if not title and not details:
                self.logger.warning(f"Post {post_id} has no content")
                return None
            
            # Extract metadata
            board_info = post.get('board', {})
            author_info = post.get('author', {})
            
            # Parse dates
            created_date = self._parse_date(post.get('created'))
            
            # Extract status
            status = self._normalize_status(post.get('status'))
            
            # Calculate engagement metrics
            score = post.get('score', 0)
            comment_count = post.get('commentCount', 0)
            engagement_score = self._calculate_engagement_score(score, comment_count)
            
            # Process comments if available
            comments = self._preprocess_comments(post.get('comments', []))
            
            # Process votes if available
            votes = self._preprocess_votes(post.get('votes', []))
            
            # Extract tags and categories
            tags = self._extract_tags(post)
            category = self._extract_category(post)
            
            # Build processed post
            processed_post = {
                'id': post_id,
                'title': title,
                'details': details,
                'board': {
                    'id': board_info.get('id'),
                    'name': board_info.get('name', 'Unknown Board')
                },
                'author': {
                    'id': author_info.get('id'),
                    'name': author_info.get('name', 'Anonymous'),
                    'email': author_info.get('email')
                },
                'category': category,
                'created': created_date,
                'score': score,
                'status': status,
                'commentCount': comment_count,
                'url': post.get('url', ''),
                'tags': tags,
                'engagement_score': engagement_score,
                'comments': comments,
                'votes': votes,
                'vote_velocity': self._calculate_vote_velocity(post),
                'comment_velocity': self._calculate_comment_velocity(post),
                'is_trending': self._is_trending_post(post),
                'content_for_analysis': self._prepare_content_for_analysis(title, details, comments)
            }
            
            return processed_post
            
        except Exception as e:
            self.logger.error(f"Error preprocessing post {post.get('id', 'unknown')}: {e}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive punctuation
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        
        return text.strip()
    
    def _parse_date(self, date_str: Optional[str]) -> datetime:
        """Parse date string to datetime."""
        if not date_str:
            return datetime.now()
        
        try:
            # Handle Canny's ISO format
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            return datetime.fromisoformat(date_str)
        except Exception as e:
            self.logger.warning(f"Failed to parse date {date_str}: {e}")
            return datetime.now()
    
    def _normalize_status(self, status: Optional[str]) -> str:
        """Normalize post status."""
        if not status:
            return CannyPostStatus.OPEN.value
        
        status_lower = status.lower().strip()
        
        # Map various status formats to standard values
        status_mapping = {
            'open': CannyPostStatus.OPEN.value,
            'new': CannyPostStatus.OPEN.value,
            'planned': CannyPostStatus.PLANNED.value,
            'planning': CannyPostStatus.PLANNED.value,
            'in progress': CannyPostStatus.IN_PROGRESS.value,
            'in_progress': CannyPostStatus.IN_PROGRESS.value,
            'working': CannyPostStatus.IN_PROGRESS.value,
            'complete': CannyPostStatus.COMPLETE.value,
            'completed': CannyPostStatus.COMPLETE.value,
            'done': CannyPostStatus.COMPLETE.value,
            'closed': CannyPostStatus.CLOSED.value,
            'cancelled': CannyPostStatus.CLOSED.value,
            'rejected': CannyPostStatus.CLOSED.value
        }
        
        return status_mapping.get(status_lower, CannyPostStatus.OPEN.value)
    
    def _calculate_engagement_score(self, votes: int, comments: int) -> float:
        """Calculate engagement score for a post."""
        # Weighted score: votes * 2 + comments * 1
        return (votes * 2) + comments
    
    def _preprocess_comments(self, raw_comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Preprocess comments data."""
        processed_comments = []
        
        for comment in raw_comments:
            try:
                processed_comment = {
                    'id': comment.get('id'),
                    'author': {
                        'id': comment.get('author', {}).get('id'),
                        'name': comment.get('author', {}).get('name', 'Anonymous'),
                        'email': comment.get('author', {}).get('email')
                    },
                    'value': self._clean_text(comment.get('value', '')),
                    'created': self._parse_date(comment.get('created')),
                    'content_for_analysis': self._clean_text(comment.get('value', ''))
                }
                
                if processed_comment['value']:  # Only include comments with content
                    processed_comments.append(processed_comment)
                    
            except Exception as e:
                self.logger.warning(f"Failed to preprocess comment {comment.get('id', 'unknown')}: {e}")
                continue
        
        return processed_comments
    
    def _preprocess_votes(self, raw_votes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Preprocess votes data."""
        processed_votes = []
        
        for vote in raw_votes:
            try:
                processed_vote = {
                    'id': vote.get('id'),
                    'voter': {
                        'id': vote.get('voter', {}).get('id'),
                        'name': vote.get('voter', {}).get('name', 'Anonymous'),
                        'email': vote.get('voter', {}).get('email')
                    },
                    'created': self._parse_date(vote.get('created'))
                }
                processed_votes.append(processed_vote)
                
            except Exception as e:
                self.logger.warning(f"Failed to preprocess vote {vote.get('id', 'unknown')}: {e}")
                continue
        
        return processed_votes
    
    def _extract_tags(self, post: Dict[str, Any]) -> List[str]:
        """Extract tags from post."""
        tags = post.get('tags', [])
        if isinstance(tags, list):
            return [tag.get('name', str(tag)) if isinstance(tag, dict) else str(tag) for tag in tags]
        return []
    
    def _extract_category(self, post: Dict[str, Any]) -> Optional[str]:
        """Extract category from post."""
        # Try different possible category fields
        category = post.get('category')
        if category:
            if isinstance(category, dict):
                return category.get('name')
            return str(category)
        
        # Try to extract from tags
        tags = self._extract_tags(post)
        if tags:
            return tags[0]  # Use first tag as category
        
        return None
    
    def _calculate_vote_velocity(self, post: Dict[str, Any]) -> float:
        """Calculate vote velocity (votes per day since creation)."""
        try:
            created_date = self._parse_date(post.get('created'))
            days_since_creation = (datetime.now() - created_date).days
            
            if days_since_creation <= 0:
                return 0.0
            
            votes = post.get('score', 0)
            return votes / days_since_creation
            
        except Exception:
            return 0.0
    
    def _calculate_comment_velocity(self, post: Dict[str, Any]) -> float:
        """Calculate comment velocity (comments per day since creation)."""
        try:
            created_date = self._parse_date(post.get('created'))
            days_since_creation = (datetime.now() - created_date).days
            
            if days_since_creation <= 0:
                return 0.0
            
            comments = post.get('commentCount', 0)
            return comments / days_since_creation
            
        except Exception:
            return 0.0
    
    def _is_trending_post(self, post: Dict[str, Any], threshold: float = 1.0) -> bool:
        """Determine if a post is trending based on velocity."""
        vote_velocity = self._calculate_vote_velocity(post)
        comment_velocity = self._calculate_comment_velocity(post)
        
        # Consider trending if either velocity is above threshold
        return vote_velocity >= threshold or comment_velocity >= threshold
    
    def _prepare_content_for_analysis(self, title: str, details: str, comments: List[Dict[str, Any]]) -> str:
        """Prepare combined content for sentiment analysis."""
        content_parts = []
        
        if title:
            content_parts.append(f"Title: {title}")
        
        if details:
            content_parts.append(f"Details: {details}")
        
        # Add first few comments for context (limit to avoid token limits)
        if comments:
            comment_texts = []
            for comment in comments[:3]:  # Limit to first 3 comments
                comment_text = comment.get('content_for_analysis', '')
                if comment_text:
                    comment_texts.append(comment_text)
            
            if comment_texts:
                content_parts.append(f"Comments: {' '.join(comment_texts)}")
        
        return ' '.join(content_parts)
    
    def categorize_posts(self, posts: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize posts by status, category, and engagement level."""
        categories = {
            'by_status': {},
            'by_category': {},
            'by_engagement': {
                'high': [],  # engagement_score > 20
                'medium': [],  # engagement_score 5-20
                'low': []  # engagement_score < 5
            },
            'trending': [],
            'feature_requests': [],
            'bug_reports': []
        }
        
        for post in posts:
            # Categorize by status
            status = post.get('status', 'open')
            if status not in categories['by_status']:
                categories['by_status'][status] = []
            categories['by_status'][status].append(post)
            
            # Categorize by category
            category = post.get('category', 'uncategorized')
            if category not in categories['by_category']:
                categories['by_category'][category] = []
            categories['by_category'][category].append(post)
            
            # Categorize by engagement
            engagement_score = post.get('engagement_score', 0)
            if engagement_score > 20:
                categories['by_engagement']['high'].append(post)
            elif engagement_score >= 5:
                categories['by_engagement']['medium'].append(post)
            else:
                categories['by_engagement']['low'].append(post)
            
            # Identify trending posts
            if post.get('is_trending', False):
                categories['trending'].append(post)
            
            # Classify as feature request or bug report
            content = post.get('content_for_analysis', '').lower()
            if any(keyword in content for keyword in ['bug', 'error', 'broken', 'issue', 'problem']):
                categories['bug_reports'].append(post)
            else:
                categories['feature_requests'].append(post)
        
        return categories
