"""
SDK-based Intercom service using the official python-intercom SDK.
This replaces the custom-built Intercom clients with the official SDK implementation.
"""

import logging
import asyncio
import sys
import os
from typing import Dict, List, Optional
from datetime import datetime, timezone
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Import the official Intercom SDK
# Add SDK path for deployment environments
sdk_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'python-intercom-master', 'src')
if os.path.exists(sdk_path) and sdk_path not in sys.path:
    sys.path.insert(0, sdk_path)

from intercom import AsyncIntercom
from intercom.types import (
    MultipleFilterSearchRequest,
    SingleFilterSearchRequest,
    StartingAfterPaging,
)
from intercom.core.api_error import ApiError
from intercom.core.pagination import AsyncPager

from src.config.settings import settings

logger = logging.getLogger(__name__)


class IntercomSDKService:
    """Service for interacting with Intercom API using the official SDK."""
    
    def __init__(self):
        """Initialize the SDK-based Intercom service."""
        self.access_token = settings.intercom_access_token
        self.base_url = settings.intercom_base_url
        self.timeout = settings.intercom_timeout
        self.max_retries = settings.intercom_max_retries
        self.rate_limit_buffer = settings.intercom_rate_limit_buffer
        
        # Initialize the AsyncIntercom client
        self.client = AsyncIntercom(
            token=self.access_token,
            base_url=self.base_url,
            timeout=float(self.timeout)
        )
        
        self.logger = logging.getLogger(__name__)
    
    async def test_connection(self) -> bool:
        """
        Test connection to Intercom API.
        
        Returns:
            bool: True if connection successful
            
        Raises:
            ApiError: If connection fails
        """
        try:
            # Use the identify endpoint to test connection
            await self.client.admins.identify()
            self.logger.info("Intercom API connection successful")
            return True
        except ApiError as e:
            self.logger.error(f"Intercom API connection failed: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error testing connection: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ApiError, asyncio.TimeoutError)),
        reraise=True
    )
    async def fetch_conversations_by_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime,
        max_conversations: Optional[int] = None
    ) -> List[Dict]:
        """
        Fetch conversations within a date range with automatic pagination.
        
        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            max_conversations: Optional limit on number of conversations to fetch
            
        Returns:
            List of conversation dictionaries with enriched contact details
        """
        self.logger.info(f"Fetching conversations from {start_date} to {end_date}")
        
        all_conversations = []
        page_num = 1
        
        # Build the search query with date range filters
        search_query = MultipleFilterSearchRequest(
            operator="AND",  # String literal, not enum
            value=[
                SingleFilterSearchRequest(
                    field="created_at",
                    operator=">=",  # String literal, not enum
                    value=int(start_date.timestamp())
                ),
                SingleFilterSearchRequest(
                    field="created_at",
                    operator="<=",  # String literal, not enum
                    value=int(end_date.timestamp())
                )
            ]
        )
        
        # Build pagination parameters
        pagination = StartingAfterPaging(
            per_page=50,
            starting_after=None
        )
        
        try:
            # Use SDK's search method with pagination
            pager: AsyncPager = await self.client.conversations.search(
                query=search_query,
                pagination=pagination
            )
            
            # Iterate through all pages
            async for conversation in pager:
                if max_conversations and len(all_conversations) >= max_conversations:
                    self.logger.info(f"Reached max conversations limit: {max_conversations}")
                    break
                
                # Convert SDK Pydantic model to dict
                conv_dict = self._model_to_dict(conversation)
                all_conversations.append(conv_dict)
                
                # Log progress every 50 conversations
                if len(all_conversations) % 50 == 0:
                    self.logger.info(f"Fetched {len(all_conversations)} conversations")
                
                # Rate limiting - respect Intercom's 300 req/min limit
                await asyncio.sleep(0.2)  # 200ms delay = ~5 req/sec (safe under 300/min limit)
            
            self.logger.info(f"Fetched {len(all_conversations)} conversations from SDK")
            
            # Enrich conversations with contact details
            enriched_conversations = await self._enrich_conversations_with_contact_details(
                all_conversations
            )
            
            # Normalize timestamps and filter by date range
            filtered_conversations = self._normalize_and_filter_by_date(
                enriched_conversations,
                start_date,
                end_date
            )
            
            filtered_out_count = len(enriched_conversations) - len(filtered_conversations)
            if filtered_out_count > 0:
                self.logger.info(
                    f"Filtered out {filtered_out_count} conversations outside date range "
                    f"(likely timezone-related)"
                )
            
            return filtered_conversations
            
        except ApiError as e:
            if e.status_code == 429:
                self.logger.warning(f"Rate limited, will retry with backoff")
                raise
            else:
                self.logger.error(f"API error fetching conversations: {e}")
                raise
        except Exception as e:
            self.logger.error(f"Error fetching conversations: {e}")
            raise
    
    async def _enrich_conversations_with_contact_details(
        self,
        conversations: List[Dict]
    ) -> List[Dict]:
        """
        Enrich conversations with full contact details including segments.
        
        Args:
            conversations: List of conversation dictionaries
            
        Returns:
            List of enriched conversation dictionaries
        """
        enriched_conversations = []
        enrichment_stats = {
            'attempted': 0,
            'successful': 0,
            'failed_contact': 0,
            'failed_segments': 0
        }
        
        for conv in conversations:
            enrichment_stats['attempted'] += 1
            try:
                # Extract contact IDs from the conversation
                contacts_data = conv.get('contacts', {})
                if contacts_data and isinstance(contacts_data, dict):
                    contacts_list = contacts_data.get('contacts', [])
                    
                    if contacts_list:
                        # Get the first contact (primary contact)
                        contact_id = contacts_list[0].get('id')
                        
                        if contact_id:
                            try:
                                # Fetch full contact details using SDK
                                contact = await self.client.contacts.find(contact_id)
                                full_contact_data = self._model_to_dict(contact)
                                
                                # Fetch segments for the contact
                                try:
                                    segments = await self.client.contacts.list_attached_segments(contact_id)
                                    segments_data = self._model_to_dict(segments)
                                    full_contact_data['segments'] = segments_data
                                    
                                    self.logger.debug(f"Enriched conversation {conv.get('id')} with segments")
                                    
                                except Exception as e:
                                    enrichment_stats['failed_segments'] += 1
                                    self.logger.warning(f"Failed to fetch segments for contact {contact_id}: {e}")
                                    # Continue without segments data
                                
                                # Replace the contact data in the conversation
                                conv['contacts']['contacts'][0] = full_contact_data
                                enrichment_stats['successful'] += 1
                                
                                self.logger.debug(f"Enriched conversation {conv.get('id')} with full contact details")
                                
                            except ApiError as e:
                                enrichment_stats['failed_contact'] += 1
                                if e.status_code == 404:
                                    self.logger.warning(f"Contact {contact_id} not found")
                                else:
                                    self.logger.warning(f"Failed to fetch contact {contact_id}: {e}")
                                # Continue with original contact data
                            except Exception as e:
                                enrichment_stats['failed_contact'] += 1
                                self.logger.warning(f"Error fetching contact {contact_id}: {e}")
                                # Continue with original contact data
                
                enriched_conversations.append(conv)
                
            except Exception as e:
                self.logger.warning(f"Failed to enrich conversation {conv.get('id')}: {e}")
                # Add the original conversation if enrichment fails
                enriched_conversations.append(conv)
        
        # Log enrichment statistics
        success_rate = (enrichment_stats['successful'] / enrichment_stats['attempted'] * 100) if enrichment_stats['attempted'] > 0 else 0
        self.logger.info(
            f"Contact enrichment complete: {enrichment_stats['successful']}/{enrichment_stats['attempted']} successful "
            f"({success_rate:.1f}%), {enrichment_stats['failed_contact']} contact failures, "
            f"{enrichment_stats['failed_segments']} segment failures"
        )
        
        return enriched_conversations
    
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
        """
        Fetch conversations using various query types.
        
        Args:
            query_type: Type of query (text_search, tag, topic, agent)
            suggestion: Query suggestion/value
            custom_query: Custom search query
            max_pages: Maximum number of pages to fetch
            
        Returns:
            List of conversation dictionaries
        """
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
        
        search_query = SingleFilterSearchRequest(
            field="source.body",
            operator="~",  # Contains operator (string literal)
            value=search_text
        )
        
        return await self._fetch_with_query(search_query, max_pages)
    
    async def _fetch_by_tag(self, tag_name: str, max_pages: Optional[int]) -> List[Dict]:
        """Fetch conversations with specific tag."""
        self.logger.info(f"Searching for conversations with tag: {tag_name}")
        
        search_query = SingleFilterSearchRequest(
            field="tags",
            operator="~",  # Contains operator (string literal)
            value=tag_name
        )
        
        return await self._fetch_with_query(search_query, max_pages)
    
    async def _fetch_by_topic(self, topic_name: str, max_pages: Optional[int]) -> List[Dict]:
        """Fetch conversations with specific topic."""
        self.logger.info(f"Searching for conversations with topic: {topic_name}")
        
        search_query = SingleFilterSearchRequest(
            field="topics",
            operator="~",  # Contains operator (string literal)
            value=topic_name
        )
        
        return await self._fetch_with_query(search_query, max_pages)
    
    async def _fetch_by_agent(self, agent_id: str, max_pages: Optional[int]) -> List[Dict]:
        """
        Fetch conversations assigned to specific agent.
        
        Args:
            agent_id: The admin/agent ID (not name) to filter by
            max_pages: Maximum number of pages to fetch
            
        Returns:
            List of conversations assigned to the agent
        """
        self.logger.info(f"Searching for conversations assigned to agent ID: {agent_id}")
        
        search_query = SingleFilterSearchRequest(
            field="admin_assignee_id",
            operator="=",  # Equals operator (string literal)
            value=agent_id
        )
        
        return await self._fetch_with_query(search_query, max_pages)
    
    async def _fetch_with_query(self, search_query, max_pages: Optional[int]) -> List[Dict]:
        """Generic method to fetch conversations with a search query."""
        all_conversations = []
        page_count = 0
        
        pagination = StartingAfterPaging(
            per_page=50,
            starting_after=None
        )
        
        try:
            pager: AsyncPager = await self.client.conversations.search(
                query=search_query,
                pagination=pagination
            )
            
            async for page in pager.iter_pages():
                page_count += 1
                
                if max_pages and page_count > max_pages:
                    self.logger.info(f"Reached max pages limit: {max_pages}")
                    break
                
                if page.items:
                    for conversation in page.items:
                        conv_dict = self._model_to_dict(conversation)
                        all_conversations.append(conv_dict)
                    
                    self.logger.info(f"Fetched page {page_count}: {len(page.items)} conversations (total: {len(all_conversations)})")
                
                # Rate limiting between pages
                await asyncio.sleep(1.5)
            
            self.logger.info(f"Total conversations fetched: {len(all_conversations)}")
            return all_conversations
            
        except ApiError as e:
            if e.status_code == 429:
                self.logger.warning("Rate limited")
                raise
            else:
                self.logger.error(f"API error: {e}")
                raise
        except Exception as e:
            self.logger.error(f"Error fetching conversations: {e}")
            raise
    
    async def get_conversation_details(self, conversation_id: str) -> Optional[Dict]:
        """
        Get details for a specific conversation.
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            Conversation dictionary or None if not found
        """
        try:
            conversation = await self.client.conversations.find(conversation_id)
            return self._model_to_dict(conversation)
        except ApiError as e:
            if e.status_code == 404:
                self.logger.warning(f"Conversation {conversation_id} not found")
                return None
            else:
                self.logger.error(f"Error fetching conversation {conversation_id}: {e}")
                raise
        except Exception as e:
            self.logger.error(f"Error fetching conversation {conversation_id}: {e}")
            raise
    
    async def get_conversation_count(self, query) -> int:
        """
        Get the count of conversations matching a query.
        
        Args:
            query: Search query
            
        Returns:
            Count of matching conversations
        """
        try:
            pagination = StartingAfterPaging(per_page=50, starting_after=None)
            pager = await self.client.conversations.search(query=query, pagination=pagination)
            
            # Iterate through pages and sum the count
            count = 0
            async for page in pager.iter_pages():
                if page.items:
                    count += len(page.items)
            
            return count
        except Exception as e:
            self.logger.error(f"Error getting conversation count: {e}")
            return 0
    
    def _model_to_dict(self, model) -> Dict:
        """
        Convert SDK Pydantic model to dictionary.
        
        Args:
            model: SDK Pydantic model
            
        Returns:
            Dictionary representation of the model
        """
        if hasattr(model, 'model_dump'):
            # Pydantic v2
            return model.model_dump(exclude_none=False)
        elif hasattr(model, 'dict'):
            # Pydantic v1
            return model.dict(exclude_none=False)
        else:
            # Fallback
            return dict(model)

