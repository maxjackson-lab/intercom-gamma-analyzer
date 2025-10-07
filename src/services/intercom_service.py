"""
Intercom API service for fetching conversation data.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Generator
from datetime import datetime, timedelta
import httpx

from ..config.settings import settings

logger = logging.getLogger(__name__)


class IntercomService:
    """Service for interacting with Intercom API."""
    
    def __init__(self):
        self.access_token = settings.intercom_access_token
        self.base_url = settings.intercom_base_url
        self.api_version = settings.intercom_api_version
        self.timeout = settings.intercom_timeout
        self.rate_limit_buffer = settings.intercom_rate_limit_buffer
        
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Intercom-Version': self.api_version
        }
        
        self.logger = logging.getLogger(__name__)
    
    async def test_connection(self) -> bool:
        """Test connection to Intercom API."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/me",
                    headers=self.headers
                )
                response.raise_for_status()
                self.logger.info("Intercom API connection successful")
                return True
        except Exception as e:
            self.logger.error(f"Intercom API connection failed: {e}")
            raise
    
    async def fetch_conversations_by_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime,
        max_pages: Optional[int] = None
    ) -> List[Dict]:
        """Fetch conversations within a date range."""
        self.logger.info(f"Fetching conversations from {start_date} to {end_date}")
        
        # Create query
        query = {
            "operator": "AND",
            "value": [
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
        }
        
        conversations = []
        page_count = 0
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            starting_after = None
            
            while True:
                if max_pages and page_count >= max_pages:
                    self.logger.info(f"Reached maximum pages limit: {max_pages}")
                    break
                
                payload = {
                    "query": query,
                    "pagination": {"per_page": settings.max_conversations_per_request}
                }
                
                if starting_after:
                    payload["pagination"]["starting_after"] = starting_after
                
                try:
                    response = await client.post(
                        f"{self.base_url}/conversations/search",
                        headers=self.headers,
                        json=payload
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    page_conversations = data.get('conversations', [])
                    
                    page_count += 1
                    conversations.extend(page_conversations)
                    
                    self.logger.info(f"Fetched page {page_count}: {len(page_conversations)} conversations")
                    
                    # Check for next page
                    pages = data.get('pages', {})
                    next_page = pages.get('next')
                    
                    if not next_page or not page_conversations:
                        break
                    
                    starting_after = next_page.get('starting_after')
                    if not starting_after:
                        break
                    
                    # Rate limiting
                    await self._handle_rate_limiting(response)
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        self.logger.warning("Rate limit exceeded, waiting...")
                        await asyncio.sleep(10)
                        continue
                    else:
                        self.logger.error(f"HTTP error: {e}")
                        raise
                except Exception as e:
                    self.logger.error(f"Request failed: {e}")
                    raise
        
        self.logger.info(f"Fetched {len(conversations)} conversations in {page_count} pages")
        return conversations
    
    async def fetch_conversations_by_text_search(
        self, 
        search_text: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_pages: Optional[int] = None
    ) -> List[Dict]:
        """Fetch conversations containing specific text."""
        self.logger.info(f"Searching for conversations containing: {search_text}")
        
        # Create query
        query_filters = [
            {
                "field": "source.body",
                "operator": "~",
                "value": search_text
            }
        ]
        
        if start_date and end_date:
            query_filters.extend([
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
            ])
        
        query = {
            "operator": "AND",
            "value": query_filters
        }
        
        conversations = []
        page_count = 0
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            starting_after = None
            
            while True:
                if max_pages and page_count >= max_pages:
                    break
                
                payload = {
                    "query": query,
                    "pagination": {"per_page": settings.max_conversations_per_request}
                }
                
                if starting_after:
                    payload["pagination"]["starting_after"] = starting_after
                
                try:
                    response = await client.post(
                        f"{self.base_url}/conversations/search",
                        headers=self.headers,
                        json=payload
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    page_conversations = data.get('conversations', [])
                    
                    page_count += 1
                    conversations.extend(page_conversations)
                    
                    self.logger.info(f"Fetched page {page_count}: {len(page_conversations)} conversations")
                    
                    # Check for next page
                    pages = data.get('pages', {})
                    next_page = pages.get('next')
                    
                    if not next_page or not page_conversations:
                        break
                    
                    starting_after = next_page.get('starting_after')
                    if not starting_after:
                        break
                    
                    # Rate limiting
                    await self._handle_rate_limiting(response)
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        self.logger.warning("Rate limit exceeded, waiting...")
                        await asyncio.sleep(10)
                        continue
                    else:
                        self.logger.error(f"HTTP error: {e}")
                        raise
                except Exception as e:
                    self.logger.error(f"Request failed: {e}")
                    raise
        
        self.logger.info(f"Found {len(conversations)} conversations containing '{search_text}'")
        return conversations
    
    async def get_conversation_count(self, query: Dict) -> int:
        """Get total count of conversations matching query."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "query": query,
                    "pagination": {"per_page": 1}
                }
                
                response = await client.post(
                    f"{self.base_url}/conversations/search",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                total_count = data.get('total_count', 0)
                
                self.logger.info(f"Query matches {total_count} conversations")
                return total_count
                
        except Exception as e:
            self.logger.error(f"Failed to get conversation count: {e}")
            raise
    
    async def get_conversation_details(self, conversation_id: str) -> Dict:
        """Get detailed information about a specific conversation."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/conversations/{conversation_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                
                return response.json()
                
        except Exception as e:
            self.logger.error(f"Failed to get conversation details for {conversation_id}: {e}")
            raise
    
    async def fetch_conversations_by_query(
        self, 
        query: Dict,
        max_pages: Optional[int] = None
    ) -> List[Dict]:
        """Fetch conversations using a custom query."""
        self.logger.info("Fetching conversations with custom query")
        
        conversations = []
        page_count = 0
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            starting_after = None
            
            while True:
                if max_pages and page_count >= max_pages:
                    self.logger.info(f"Reached maximum pages limit: {max_pages}")
                    break
                
                payload = {
                    "query": query,
                    "pagination": {"per_page": settings.max_conversations_per_request}
                }
                
                if starting_after:
                    payload["pagination"]["starting_after"] = starting_after
                
                try:
                    response = await client.post(
                        f"{self.base_url}/conversations/search",
                        headers=self.headers,
                        json=payload
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    page_conversations = data.get('conversations', [])
                    
                    page_count += 1
                    conversations.extend(page_conversations)
                    
                    self.logger.info(f"Fetched page {page_count}: {len(page_conversations)} conversations")
                    
                    # Check for next page
                    pages = data.get('pages', {})
                    next_page = pages.get('next')
                    
                    if not next_page or not page_conversations:
                        break
                    
                    starting_after = next_page.get('starting_after')
                    if not starting_after:
                        break
                    
                    # Rate limiting
                    await self._handle_rate_limiting(response)
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        self.logger.warning("Rate limit exceeded, waiting...")
                        await asyncio.sleep(10)
                        continue
                    else:
                        self.logger.error(f"HTTP error: {e}")
                        raise
                except Exception as e:
                    self.logger.error(f"Request failed: {e}")
                    raise
        
        self.logger.info(f"Fetched {len(conversations)} conversations in {page_count} pages")
        return conversations
    
    async def _handle_rate_limiting(self, response: httpx.Response):
        """Handle rate limiting from Intercom API."""
        remaining = int(response.headers.get('X-RateLimit-Remaining', 100))
        
        if remaining < self.rate_limit_buffer:
            reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
            if reset_time:
                sleep_duration = max(reset_time - datetime.now().timestamp(), 0) + 1
                self.logger.warning(f"Approaching rate limit. Sleeping for {sleep_duration:.1f}s")
                await asyncio.sleep(sleep_duration)
