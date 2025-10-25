"""
Canny API client for fetching product feedback data.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import httpx
from urllib.parse import urlencode

from src.config.settings import settings
from src.models.canny_models import (
    CannyBoard, CannyPost, CannyComment, CannyVote,
    CannyPostStatus
)

logger = logging.getLogger(__name__)


class CannyClient:
    """Client for interacting with Canny API."""
    
    def __init__(self):
        self.api_key = settings.canny_api_key
        self.base_url = settings.canny_base_url
        self.timeout = settings.canny_timeout
        self.max_retries = settings.canny_max_retries
        
        if not self.api_key:
            raise ValueError("CANNY_API_KEY is required")
        
        self.logger = logging.getLogger(__name__)
    
    async def _make_request_with_retry(
        self,
        endpoint: str,
        data: Dict[str, Any],
        method: str = "POST"
    ) -> Dict[str, Any]:
        """
        Make API request with exponential backoff retry.
        
        Args:
            endpoint: API endpoint (e.g., "boards/list")
            data: Request data including apiKey
            method: HTTP method (default: POST)
            
        Returns:
            JSON response from API
            
        Raises:
            httpx.HTTPError: If all retries fail
        """
        base_delay = 1.0
        max_delay = 30.0
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if method == "POST":
                        response = await client.post(
                            f"{self.base_url}/{endpoint}",
                            data=data
                        )
                    else:
                        response = await client.get(
                            f"{self.base_url}/{endpoint}",
                            params=data
                        )
                    
                    # Handle rate limiting
                    if response.status_code == 429:
                        retry_after = int(response.headers.get('Retry-After', base_delay * (2 ** attempt)))
                        retry_after = min(retry_after, max_delay)
                        self.logger.warning(f"Rate limited. Retrying after {retry_after}s (attempt {attempt + 1}/{self.max_retries})")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    # Raise for other HTTP errors
                    response.raise_for_status()
                    return response.json()
                    
            except httpx.TimeoutException as e:
                if attempt == self.max_retries - 1:
                    self.logger.error(f"Request timeout after {self.max_retries} attempts: {e}")
                    raise
                delay = min(base_delay * (2 ** attempt), max_delay)
                self.logger.warning(f"Request timeout. Retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(delay)
                
            except httpx.HTTPStatusError as e:
                if attempt == self.max_retries - 1:
                    self.logger.error(f"HTTP error after {self.max_retries} attempts: {e}")
                    raise
                # Don't retry on 4xx errors (except 429) as they won't succeed
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    self.logger.error(f"Client error {e.response.status_code}: {e}")
                    raise
                delay = min(base_delay * (2 ** attempt), max_delay)
                self.logger.warning(f"HTTP error {e.response.status_code}. Retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(delay)
                
            except httpx.HTTPError as e:
                if attempt == self.max_retries - 1:
                    self.logger.error(f"HTTP error after {self.max_retries} attempts: {e}")
                    raise
                delay = min(base_delay * (2 ** attempt), max_delay)
                self.logger.warning(f"HTTP error. Retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(delay)
        
        raise Exception(f"Failed after {self.max_retries} retries")
    
    async def test_connection(self) -> bool:
        """Test connection to Canny API."""
        try:
            data = await self._make_request_with_retry("boards/list", {'apiKey': self.api_key})
            self.logger.info("Canny API connection successful")
            return True
        except Exception as e:
            self.logger.error(f"Canny API connection failed: {e}")
            raise
    
    async def fetch_boards(self) -> List[Dict[str, Any]]:
        """Fetch all feedback boards."""
        try:
            data = await self._make_request_with_retry("boards/list", {'apiKey': self.api_key})
            boards = data.get('boards', [])
            self.logger.info(f"Fetched {len(boards)} boards")
            return boards
        except Exception as e:
            self.logger.error(f"Failed to fetch boards: {e}")
            raise
    
    async def fetch_posts(
        self,
        board_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch posts from Canny.
        
        Args:
            board_id: Specific board ID (optional)
            start_date: Start date for filtering
            end_date: End date for filtering
            limit: Maximum number of posts to fetch
        """
        try:
            # Canny API uses POST with parameters in body
            post_data = {
                'apiKey': self.api_key,
                'limit': limit,
                'sort': 'newest'
            }
            
            if board_id:
                post_data['boardID'] = board_id
            
            if start_date:
                post_data['createdAfter'] = int(start_date.timestamp())
            
            if end_date:
                post_data['createdBefore'] = int(end_date.timestamp())
            
            data = await self._make_request_with_retry("posts/list", post_data)
            posts = data.get('posts', [])
            self.logger.info(f"Fetched {len(posts)} posts")
            return posts
        except Exception as e:
            self.logger.error(f"Failed to fetch posts: {e}")
            raise
    
    async def fetch_post_details(self, post_id: str) -> Dict[str, Any]:
        """Fetch detailed information for a specific post."""
        try:
            data = await self._make_request_with_retry(
                "posts/retrieve",
                {'apiKey': self.api_key, 'id': post_id}
            )
            self.logger.debug(f"Fetched details for post {post_id}")
            return data
        except Exception as e:
            self.logger.error(f"Failed to fetch post details for {post_id}: {e}")
            raise
    
    async def fetch_comments(self, post_id: str) -> List[Dict[str, Any]]:
        """Fetch all comments for a specific post."""
        try:
            data = await self._make_request_with_retry(
                "comments/list",
                {'apiKey': self.api_key, 'postID': post_id}
            )
            comments = data.get('comments', [])
            self.logger.debug(f"Fetched {len(comments)} comments for post {post_id}")
            return comments
        except Exception as e:
            self.logger.error(f"Failed to fetch comments for post {post_id}: {e}")
            raise
    
    async def fetch_votes(self, post_id: str) -> List[Dict[str, Any]]:
        """Fetch all votes for a specific post."""
        try:
            data = await self._make_request_with_retry(
                "votes/list",
                {'apiKey': self.api_key, 'postID': post_id}
            )
            votes = data.get('votes', [])
            self.logger.debug(f"Fetched {len(votes)} votes for post {post_id}")
            return votes
        except Exception as e:
            self.logger.error(f"Failed to fetch votes for post {post_id}: {e}")
            raise
    
    async def fetch_posts_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        board_id: Optional[str] = None,
        include_comments: bool = True,
        include_votes: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Fetch posts within a date range with optional comments and votes.
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            board_id: Specific board ID (optional)
            include_comments: Whether to fetch comments for each post
            include_votes: Whether to fetch votes for each post
        """
        try:
            # Fetch posts
            posts = await self.fetch_posts(
                board_id=board_id,
                start_date=start_date,
                end_date=end_date,
                limit=1000  # Canny API limit
            )
            
            # Enrich posts with comments and votes if requested
            enriched_posts = []
            for post in posts:
                post_id = post.get('id')
                if not post_id:
                    continue
                
                # Add comments if requested
                if include_comments:
                    try:
                        comments = await self.fetch_comments(post_id)
                        post['comments'] = comments
                    except Exception as e:
                        self.logger.warning(f"Failed to fetch comments for post {post_id}: {e}")
                        post['comments'] = []
                
                # Add votes if requested
                if include_votes:
                    try:
                        votes = await self.fetch_votes(post_id)
                        post['votes'] = votes
                    except Exception as e:
                        self.logger.warning(f"Failed to fetch votes for post {post_id}: {e}")
                        post['votes'] = []
                
                enriched_posts.append(post)
                
                # Rate limiting - small delay between requests
                await asyncio.sleep(0.1)
            
            self.logger.info(f"Enriched {len(enriched_posts)} posts with comments and votes")
            return enriched_posts
            
        except Exception as e:
            self.logger.error(f"Failed to fetch posts by date range: {e}")
            raise
    
    async def fetch_all_boards_posts(
        self,
        start_date: datetime,
        end_date: datetime,
        include_comments: bool = True,
        include_votes: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch posts from all boards within a date range.
        
        Returns:
            Dictionary mapping board_id to list of posts
        """
        try:
            # Get all boards
            boards = await self.fetch_boards()
            board_posts = {}
            
            for board in boards:
                board_id = board.get('id')
                board_name = board.get('name', 'Unknown')
                
                if not board_id:
                    continue
                
                self.logger.info(f"Fetching posts from board: {board_name}")
                
                try:
                    posts = await self.fetch_posts_by_date_range(
                        start_date=start_date,
                        end_date=end_date,
                        board_id=board_id,
                        include_comments=include_comments,
                        include_votes=include_votes
                    )
                    board_posts[board_id] = posts
                    self.logger.info(f"Fetched {len(posts)} posts from board {board_name}")
                except Exception as e:
                    self.logger.error(f"Failed to fetch posts from board {board_name}: {e}")
                    board_posts[board_id] = []
            
            return board_posts
            
        except Exception as e:
            self.logger.error(f"Failed to fetch all boards posts: {e}")
            raise
    
    def _parse_canny_date(self, date_str: str) -> datetime:
        """Parse Canny date string to datetime."""
        try:
            # Canny uses ISO format with Z suffix
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception as e:
            self.logger.warning(f"Failed to parse date {date_str}: {e}")
            return datetime.now()
    
    def _calculate_engagement_score(self, post: Dict[str, Any]) -> float:
        """Calculate engagement score for a post."""
        votes = post.get('score', 0)
        comments = post.get('commentCount', 0)
        
        # Weighted score: votes * 2 + comments * 1
        return (votes * 2) + comments
    
    def _is_trending_post(self, post: Dict[str, Any], threshold: int = 10) -> bool:
        """Determine if a post is trending based on engagement."""
        engagement_score = self._calculate_engagement_score(post)
        return engagement_score >= threshold
