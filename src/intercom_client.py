"""
Intercom API client with pagination, rate limiting, and error handling.
"""

import requests
import time
import logging
from typing import Dict, List, Optional, Generator, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class IntercomAPIError(Exception):
    """Custom exception for Intercom API errors."""
    pass

class RateLimitError(IntercomAPIError):
    """Exception raised when rate limit is exceeded."""
    pass

class IntercomClient:
    """Intercom API client with comprehensive error handling and rate limiting."""
    
    BASE_URL = "https://api.intercom.io"
    
    def __init__(self, access_token: str, rate_limit_buffer: int = 10, timeout: int = 30):
        """
        Initialize Intercom API client.
        
        Args:
            access_token: Intercom API access token
            rate_limit_buffer: Buffer requests before rate limit (safety margin)
            timeout: Request timeout in seconds
        """
        self.access_token = access_token
        self.rate_limit_buffer = rate_limit_buffer
        self.timeout = timeout
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Intercom-Version': '2.14'
        }
        
        # Validate token on initialization
        self._validate_token()
        
    def _validate_token(self):
        """Validate the access token by making a test request."""
        try:
            response = requests.get(
                f"{self.BASE_URL}/me",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info("Access token validated successfully")
        except requests.exceptions.RequestException as e:
            logger.error(f"Token validation failed: {e}")
            raise IntercomAPIError(f"Invalid access token: {e}")
            
    def _check_rate_limit(self, response: requests.Response):
        """Check and handle rate limiting."""
        remaining = int(response.headers.get('X-RateLimit-Remaining', 100))
        limit = int(response.headers.get('X-RateLimit-Limit', 1000))
        
        logger.debug(f"Rate limit: {remaining}/{limit} remaining")
        
        if remaining < self.rate_limit_buffer:
            reset_time = int(response.headers.get('X-RateLimit-Reset', time.time() + 10))
            sleep_duration = max(reset_time - time.time(), 0) + 1
            logger.warning(f"Approaching rate limit. Sleeping for {sleep_duration:.1f}s")
            time.sleep(sleep_duration)
            
    def _handle_api_error(self, response: requests.Response):
        """Handle API errors with detailed logging."""
        try:
            error_data = response.json()
            error_message = error_data.get('errors', [{}])[0].get('message', 'Unknown error')
            error_type = error_data.get('errors', [{}])[0].get('type', 'unknown')
        except (json.JSONDecodeError, KeyError, IndexError):
            error_message = response.text
            error_type = 'unknown'
            
        logger.error(f"API Error {response.status_code}: {error_type} - {error_message}")
        
        if response.status_code == 429:
            raise RateLimitError(f"Rate limit exceeded: {error_message}")
        else:
            raise IntercomAPIError(f"API Error {response.status_code}: {error_message}")
            
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with error handling and rate limiting."""
        url = f"{self.BASE_URL}{endpoint}"
        
        # Set default timeout
        kwargs.setdefault('timeout', self.timeout)
        
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            
            # Check for rate limiting
            self._check_rate_limit(response)
            
            # Handle errors
            if not response.ok:
                self._handle_api_error(response)
                
            return response
            
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for {url}")
            raise IntercomAPIError(f"Request timeout for {endpoint}")
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error for {url}")
            raise IntercomAPIError(f"Connection error for {endpoint}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            raise IntercomAPIError(f"Request failed for {endpoint}: {e}")
            
    def search_conversations(
        self, 
        query: Dict,
        per_page: int = 150,
        max_pages: Optional[int] = None
    ) -> Generator[Dict, None, None]:
        """
        Search conversations with pagination.
        
        Yields individual conversation objects.
        
        Args:
            query: Intercom query object (field, operator, value)
            per_page: Results per page (max 150)
            max_pages: Maximum number of pages to fetch (None for all)
            
        Yields:
            Dict: Individual conversation objects
        """
        if per_page > 150:
            logger.warning("per_page cannot exceed 150, setting to 150")
            per_page = 150
            
        endpoint = "/conversations/search"
        starting_after = None
        page_count = 0
        total_conversations = 0
        
        logger.info(f"Starting conversation search with query: {query}")
        
        while True:
            if max_pages and page_count >= max_pages:
                logger.info(f"Reached maximum pages limit: {max_pages}")
                break
                
            payload = {
                "query": query,
                "pagination": {"per_page": per_page}
            }
            
            if starting_after:
                payload["pagination"]["starting_after"] = starting_after
                
            try:
                response = self._make_request('POST', endpoint, json=payload)
                data = response.json()
                conversations = data.get('conversations', [])
                
                page_count += 1
                total_conversations += len(conversations)
                
                logger.info(f"Fetched page {page_count}: {len(conversations)} conversations "
                          f"(total: {total_conversations})")
                
                # Yield individual conversations
                for conv in conversations:
                    yield conv
                
                # Check for next page
                pages = data.get('pages', {})
                next_page = pages.get('next')
                
                if not next_page or not conversations:
                    logger.info("No more pages available")
                    break
                    
                starting_after = next_page.get('starting_after')
                
                if not starting_after:
                    logger.info("No starting_after cursor found")
                    break
                    
            except (IntercomAPIError, RateLimitError) as e:
                logger.error(f"API error during pagination: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error during pagination: {e}")
                raise IntercomAPIError(f"Pagination failed: {e}")
                
        logger.info(f"Completed pagination: {page_count} pages, {total_conversations} conversations")
        
    def get_conversation(self, conversation_id: str) -> Dict:
        """
        Fetch full conversation details by ID.
        
        Args:
            conversation_id: Intercom conversation ID
            
        Returns:
            Dict: Full conversation object
        """
        endpoint = f"/conversations/{conversation_id}"
        
        try:
            response = self._make_request('GET', endpoint)
            return response.json()
        except IntercomAPIError as e:
            logger.error(f"Failed to fetch conversation {conversation_id}: {e}")
            raise
            
    def get_conversation_count(self, query: Dict) -> int:
        """
        Get total count of conversations matching query without fetching all data.
        
        Args:
            query: Intercom query object
            
        Returns:
            int: Total count of matching conversations
        """
        endpoint = "/conversations/search"
        payload = {
            "query": query,
            "pagination": {"per_page": 1}  # Minimal data
        }
        
        try:
            response = self._make_request('POST', endpoint, json=payload)
            data = response.json()
            
            # Get total count from response
            total_count = data.get('total_count', 0)
            logger.info(f"Query matches {total_count} conversations")
            return total_count
            
        except IntercomAPIError as e:
            logger.error(f"Failed to get conversation count: {e}")
            raise
            
    def create_date_range_query(
        self, 
        start_date: datetime, 
        end_date: Optional[datetime] = None,
        additional_filters: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Create a query for conversations within a date range.
        
        Args:
            start_date: Start date for the query
            end_date: End date for the query (defaults to now)
            additional_filters: Additional query filters
            
        Returns:
            Dict: Intercom query object
        """
        if end_date is None:
            end_date = datetime.now()
            
        query_filters = [
            {
                "field": "created_at",
                "operator": ">=",
                "value": int(start_date.timestamp())
            },
            {
                "field": "created_at",
                "operator": "<=",
                "value": int(end_date.timestamp())
            }
        ]
        
        if additional_filters:
            query_filters.extend(additional_filters)
            
        return {
            "operator": "AND",
            "value": query_filters
        }
        
    def create_text_search_query(
        self, 
        search_text: str, 
        date_range: Optional[Dict] = None
    ) -> Dict:
        """
        Create a query for conversations containing specific text.
        
        Args:
            search_text: Text to search for in conversation bodies
            date_range: Optional date range query
            
        Returns:
            Dict: Intercom query object
        """
        text_filter = {
            "field": "source.body",
            "operator": "~",
            "value": search_text
        }
        
        if date_range:
            return {
                "operator": "AND",
                "value": [text_filter, date_range]
            }
        else:
            return text_filter


