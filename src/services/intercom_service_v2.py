"""
Improved Intercom API service with better rate limiting and chunking.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Generator
from datetime import datetime, timedelta, timezone
import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)


class IntercomServiceV2:
    """Improved service for interacting with Intercom API."""
    
    def __init__(self):
        self.access_token = settings.intercom_access_token
        self.base_url = settings.intercom_base_url
        self.api_version = settings.intercom_api_version
        self.timeout = 60  # Increased timeout
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
        max_conversations: Optional[int] = None
    ) -> List[Dict]:
        """Fetch conversations within a date range with improved rate limiting and chunking."""
        self.logger.info(f"Fetching conversations from {start_date} to {end_date}")
        
        all_conversations = []
        page = 1
        retry_count = 0
        max_retries = 3
        self._last_cursor = None  # Initialize cursor
        
        while True:
            if max_conversations and len(all_conversations) >= max_conversations:
                self.logger.info(f"Reached max conversations limit: {max_conversations}")
                break
            
            self.logger.info(f"Fetching page {page}")
            
            # Build query parameters with improved pagination
            query_params = {
                'query': {
                    'operator': 'AND',
                    'value': [
                        {
                            'field': 'created_at',
                            'operator': '>=',
                            'value': int(start_date.timestamp())
                        },
                        {
                            'field': 'created_at',
                            'operator': '<=',
                            'value': int(end_date.timestamp())
                        }
                    ]
                },
                'pagination': {
                    'per_page': 50,  # Reduced from 150 to 50 for better reliability
                    'starting_after': None
                }
            }
            
            # Add pagination cursor if not first page
            if page > 1 and hasattr(self, '_last_cursor') and self._last_cursor:
                query_params['pagination']['starting_after'] = self._last_cursor
            
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/conversations/search",
                        headers=self.headers,
                        json=query_params
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    conversations = data.get('conversations', [])
                    
                    if not conversations:
                        self.logger.info("No more conversations found")
                        break
                    
                    all_conversations.extend(conversations)
                    self.logger.info(f"Fetched {len(conversations)} conversations (total: {len(all_conversations)})")
                    
                    # Check if we've reached the max conversations limit
                    if max_conversations and len(all_conversations) >= max_conversations:
                        all_conversations = all_conversations[:max_conversations]
                        self.logger.info(f"Truncated to {max_conversations} conversations")
                        break
                    
                    # Extract cursor for next page from pages object
                    pages = data.get('pages', {})
                    next_page = pages.get('next', {})
                    self._last_cursor = next_page.get('starting_after')
                    
                    # Check if we have more pages
                    if not self._last_cursor:
                        self.logger.info("Reached last page - no more cursor")
                        break
                    
                    page += 1
                    retry_count = 0  # Reset retry count on success
                    
                    # Improved rate limiting with exponential backoff
                    await asyncio.sleep(1.5)  # Increased from 1.0 to 1.5 seconds
                    
            except httpx.TimeoutException:
                retry_count += 1
                self.logger.error(f"Timeout on page {page} (retry {retry_count}/{max_retries})")
                
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count  # Exponential backoff
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    self.logger.error("Max retries reached, stopping")
                    break
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limited
                    retry_count += 1
                    wait_time = min(5 * retry_count, 30)  # Progressive backoff, max 30 seconds
                    self.logger.warning(f"Rate limited on page {page}, waiting {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    self.logger.error(f"HTTP error on page {page}: {e}")
                    break
                    
            except Exception as e:
                retry_count += 1
                self.logger.error(f"Error fetching page {page}: {e}")
                
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    self.logger.error("Max retries reached, stopping")
                    break
        
        self.logger.info(f"Total conversations fetched: {len(all_conversations)}")
        
        # Normalize timestamps to UTC and filter conversations to requested window
        filtered_conversations = self._normalize_and_filter_by_date(
            all_conversations, 
            start_date, 
            end_date
        )
        
        filtered_out_count = len(all_conversations) - len(filtered_conversations)
        if filtered_out_count > 0:
            self.logger.info(
                f"Filtered out {filtered_out_count} conversations that were outside the date window "
                f"(likely timezone-related)"
            )
        
        return filtered_conversations
    
    def _normalize_and_filter_by_date(
        self,
        conversations: List[Dict],
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """
        Normalize timestamps to UTC and filter to the requested date window.
        
        Args:
            conversations: List of conversation dictionaries
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            
        Returns:
            Filtered list of conversations within the date range
        """
        # Ensure start_date and end_date are timezone-aware UTC
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        else:
            start_date = start_date.astimezone(timezone.utc)
        
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        else:
            end_date = end_date.astimezone(timezone.utc)
        
        filtered = []
        
        for conv in conversations:
            # Normalize created_at
            created_at = conv.get('created_at')
            if created_at:
                if isinstance(created_at, (int, float)):
                    # Unix timestamp - convert to UTC datetime
                    created_dt = datetime.fromtimestamp(created_at, tz=timezone.utc)
                    conv['created_at'] = created_dt
                elif isinstance(created_at, datetime):
                    # Already datetime - ensure UTC
                    if created_at.tzinfo is None:
                        created_dt = created_at.replace(tzinfo=timezone.utc)
                    else:
                        created_dt = created_at.astimezone(timezone.utc)
                    conv['created_at'] = created_dt
                else:
                    # Unknown format - skip this conversation
                    self.logger.warning(f"Unknown created_at format for conversation {conv.get('id')}: {type(created_at)}")
                    continue
                
                # Filter: only include if within the date range (inclusive)
                if created_dt < start_date or created_dt > end_date:
                    continue
            
            # Normalize updated_at if present
            updated_at = conv.get('updated_at')
            if updated_at:
                if isinstance(updated_at, (int, float)):
                    conv['updated_at'] = datetime.fromtimestamp(updated_at, tz=timezone.utc)
                elif isinstance(updated_at, datetime):
                    if updated_at.tzinfo is None:
                        conv['updated_at'] = updated_at.replace(tzinfo=timezone.utc)
                    else:
                        conv['updated_at'] = updated_at.astimezone(timezone.utc)
            
            filtered.append(conv)
        
        return filtered
    
    async def fetch_conversations_by_query(
        self,
        query_type: str,
        suggestion: Optional[str] = None,
        custom_query: Optional[str] = None,
        max_pages: Optional[int] = None
    ) -> List[Dict]:
        """Fetch conversations using various query types."""
        self.logger.info(f"Fetching conversations with query type: {query_type}")
        
        if query_type == "text_search" and custom_query:
            return await self._fetch_by_text_search(custom_query, max_pages)
        elif query_type == "tag" and suggestion:
            return await self._fetch_by_tag(suggestion, max_pages)
        elif query_type == "topic" and suggestion:
            return await self._fetch_by_topic(suggestion, max_pages)
        elif query_type == "agent" and suggestion:
            return await self._fetch_by_agent(suggestion, max_pages)
        else:
            raise ValueError(f"Invalid query type or missing parameters: {query_type}")
    
    async def _fetch_by_text_search(self, search_text: str, max_pages: Optional[int]) -> List[Dict]:
        """Fetch conversations containing specific text."""
        self.logger.info(f"Searching for conversations containing: {search_text}")
        
        query_params = {
            'query': {
                'field': 'source.body',
                'operator': 'contains',
                'value': search_text
            },
            'pagination': {
                'per_page': 50
            }
        }
        
        return await self._fetch_with_pagination(query_params, max_pages)
    
    async def _fetch_by_tag(self, tag_name: str, max_pages: Optional[int]) -> List[Dict]:
        """Fetch conversations with specific tag."""
        self.logger.info(f"Searching for conversations with tag: {tag_name}")
        
        query_params = {
            'query': {
                'field': 'tags',
                'operator': 'contains',
                'value': tag_name
            },
            'pagination': {
                'per_page': 50
            }
        }
        
        return await self._fetch_with_pagination(query_params, max_pages)
    
    async def _fetch_by_topic(self, topic_name: str, max_pages: Optional[int]) -> List[Dict]:
        """Fetch conversations with specific topic."""
        self.logger.info(f"Searching for conversations with topic: {topic_name}")
        
        query_params = {
            'query': {
                'field': 'topics',
                'operator': 'contains',
                'value': topic_name
            },
            'pagination': {
                'per_page': 50
            }
        }
        
        return await self._fetch_with_pagination(query_params, max_pages)
    
    async def _fetch_by_agent(self, agent_name: str, max_pages: Optional[int]) -> List[Dict]:
        """Fetch conversations assigned to specific agent."""
        self.logger.info(f"Searching for conversations assigned to: {agent_name}")
        
        # This would need agent ID mapping - simplified for now
        query_params = {
            'query': {
                'field': 'admin_assignee_id',
                'operator': '=',
                'value': agent_name  # This should be agent ID
            },
            'pagination': {
                'per_page': 50
            }
        }
        
        return await self._fetch_with_pagination(query_params, max_pages)
    
    async def _fetch_with_pagination(self, query_params: Dict, max_pages: Optional[int]) -> List[Dict]:
        """Generic method to fetch conversations with pagination."""
        all_conversations = []
        page = 1
        retry_count = 0
        max_retries = 3
        
        while True:
            if max_pages and page > max_pages:
                self.logger.info(f"Reached max pages limit: {max_pages}")
                break
            
            self.logger.info(f"Fetching page {page}")
            
            # Add pagination cursor if not first page
            if page > 1 and all_conversations:
                last_conversation = all_conversations[-1]
                query_params['pagination']['starting_after'] = last_conversation['id']
            
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/conversations/search",
                        headers=self.headers,
                        json=query_params
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    conversations = data.get('conversations', [])
                    
                    if not conversations:
                        self.logger.info("No more conversations found")
                        break
                    
                    all_conversations.extend(conversations)
                    self.logger.info(f"Fetched {len(conversations)} conversations (total: {len(all_conversations)})")
                    
                    # Check if we have more pages
                    if len(conversations) < 50:
                        self.logger.info("Reached last page")
                        break
                    
                    page += 1
                    retry_count = 0
                    
                    # Rate limiting
                    await asyncio.sleep(1.5)
                    
            except httpx.TimeoutException:
                retry_count += 1
                self.logger.error(f"Timeout on page {page} (retry {retry_count}/{max_retries})")
                
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    self.logger.error("Max retries reached, stopping")
                    break
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    retry_count += 1
                    wait_time = min(5 * retry_count, 30)
                    self.logger.warning(f"Rate limited on page {page}, waiting {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    self.logger.error(f"HTTP error on page {page}: {e}")
                    break
                    
            except Exception as e:
                retry_count += 1
                self.logger.error(f"Error fetching page {page}: {e}")
                
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    self.logger.error("Max retries reached, stopping")
                    break
        
        self.logger.info(f"Total conversations fetched: {len(all_conversations)}")
        return all_conversations
