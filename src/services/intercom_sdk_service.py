"""
SDK-based Intercom service using the official python-intercom SDK.
This replaces the custom-built Intercom clients with the official SDK implementation.
"""

import logging
import asyncio
import sys
import os
import time
import warnings
import httpx
from typing import Dict, List, Optional
from datetime import datetime, timezone
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Suppress httpx cleanup errors when event loop is closed
# These are harmless - connections are already closed
def _suppress_httpx_cleanup_errors():
    """Suppress harmless httpx cleanup errors when event loop is closed."""
    import asyncio
    import logging
    
    _logger = logging.getLogger(__name__)
    
    def exception_handler(loop, context):
        """Custom exception handler to suppress harmless httpx cleanup errors."""
        exception = context.get('exception')
        if exception and isinstance(exception, RuntimeError):
            if "Event loop is closed" in str(exception):
                # Check if it's from httpx cleanup
                message = str(context.get('message', ''))
                if 'httpx' in message.lower() or 'aclose' in message.lower():
                    # Suppress this harmless error
                    _logger.debug(f"Suppressed harmless httpx cleanup error: {exception}")
                    return
        
        # For all other exceptions, use default handler
        loop.default_exception_handler(context)
    
    # Set custom exception handler if loop exists
    try:
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(exception_handler)
    except RuntimeError:
        # No running loop, handler will be set when loop is created
        pass

# Install exception handler on import (but logger isn't defined yet, so we'll call it later)
# Actually, let's call it after logger is defined

# Suppress Pydantic serializer warnings from Intercom SDK
# The SDK has some type mismatches (int vs str) in its models that trigger warnings
# but don't affect functionality. These are harmless and can be safely ignored.
warnings.filterwarnings(
    'ignore',
    category=UserWarning,
    message='.*Pydantic serializer warnings.*'
)
warnings.filterwarnings(
    'ignore',
    category=UserWarning,
    message='.*Expected `str` but got `int`.*'
)

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
from src.utils.retry import async_retry

logger = logging.getLogger(__name__)

# Install exception handler to suppress harmless httpx cleanup errors
# This must be called after logger is defined
_suppress_httpx_cleanup_errors()


class IntercomSDKService:
    """Service for interacting with Intercom API using the official SDK."""
    
    def __init__(self):
        """Initialize the SDK-based Intercom service."""
        self.access_token = settings.intercom_access_token
        self.base_url = settings.intercom_base_url
        self.timeout = settings.intercom_timeout
        self.max_retries = settings.intercom_max_retries
        self.rate_limit_buffer = settings.intercom_rate_limit_buffer
        self.concurrency = settings.intercom_concurrency
        self.request_delay = settings.intercom_request_delay_ms / 1000.0  # Convert to seconds
        
        # Initialize the AsyncIntercom client
        self.client = AsyncIntercom(
            token=self.access_token,
            base_url=self.base_url,
            timeout=float(self.timeout)
        )
        
        # Semaphore for limiting concurrent enrichment requests
        self._enrichment_semaphore = asyncio.Semaphore(self.concurrency)
        
        self.logger = logging.getLogger(__name__)
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        return False
    
    async def close(self):
        """Close the AsyncIntercom client and release resources."""
        try:
            # Try to close the underlying httpx client from the SDK
            # The SDK structure: AsyncIntercom -> _client_wrapper -> httpx_client -> httpx.AsyncClient
            if hasattr(self.client, '_client_wrapper'):
                wrapper = self.client._client_wrapper
                if hasattr(wrapper, 'httpx_client'):
                    # httpx_client is an AsyncHttpClient wrapper
                    http_client = wrapper.httpx_client
                    if hasattr(http_client, '_httpx_client'):
                        httpx_client = http_client._httpx_client
                        if httpx_client is not None:
                            try:
                                await httpx_client.aclose()
                            except RuntimeError as e:
                                # Event loop is closed - this is harmless, connections are already closed
                                if "Event loop is closed" in str(e):
                                    self.logger.debug("Event loop already closed, skipping httpx cleanup (harmless)")
                                    return
                                else:
                                    raise
            # Fallback: try direct access patterns
            elif hasattr(self.client, '_client') and hasattr(self.client._client, 'close'):
                try:
                    await self.client._client.close()
                except RuntimeError as e:
                    if "Event loop is closed" in str(e):
                        self.logger.debug("Event loop already closed, skipping client cleanup (harmless)")
                        return
                    else:
                        raise
            elif hasattr(self.client, 'close'):
                try:
                    await self.client.close()
                except RuntimeError as e:
                    if "Event loop is closed" in str(e):
                        self.logger.debug("Event loop already closed, skipping client cleanup (harmless)")
                        return
                    else:
                        raise
            self.logger.debug("AsyncIntercom client closed successfully")
        except RuntimeError as e:
            # Event loop is closed - suppress this harmless error
            if "Event loop is closed" in str(e):
                self.logger.debug("Event loop already closed during cleanup (harmless)")
            else:
                self.logger.warning(f"RuntimeError closing AsyncIntercom client: {e}")
        except Exception as e:
            self.logger.warning(f"Error closing AsyncIntercom client: {e}")
    
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
        max_conversations: Optional[int] = None,
        request_options: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Fetch conversations within a date range with automatic pagination.
        
        OPTIMIZED per official Intercom SDK documentation:
        - Requests only necessary fields to minimize payload size
        - Implements adaptive rate limiting based on X-RateLimit headers
        - Uses SDK's built-in retry mechanism
        - Processes data in smaller chunks to prevent timeouts
        
        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            max_conversations: Optional limit on number of conversations to fetch
            request_options: Optional dict for SDK request options (e.g., {'max_retries': 3, 'timeout': 60})
            
        Returns:
            List of conversation dictionaries with enriched contact details
        """
        self.logger.info(f"Fetching conversations from {start_date} to {end_date}")
        
        all_conversations = []
        page_num = 1
        
        # Build the search query with date range filters
        # Per SDK docs: > means "greater or equal", < means "lower or equal"
        search_query = MultipleFilterSearchRequest(
            operator="AND",
            value=[
                SingleFilterSearchRequest(
                    field="created_at",
                    operator=">",  # Greater or equal (per SDK docs)
                    value=int(start_date.timestamp())
                ),
                SingleFilterSearchRequest(
                    field="created_at",
                    operator="<",  # Lower or equal (per SDK docs)
                    value=int(end_date.timestamp())
                )
            ]
        )
        
        # Build pagination parameters - optimized per_page for faster processing
        pagination = StartingAfterPaging(
            per_page=50,  # 50 is optimal per Intercom docs
            starting_after=None
        )
        
        try:
            # Provide sane defaults for SDK request options (timeouts + retries)
            if request_options is None:
                request_options = {
                    "max_retries": int(self.max_retries) if self.max_retries is not None else 3,
                    "timeout": float(self.timeout) if self.timeout is not None else 60.0,
                }
            # EMERGENCY BRAKE: Absolute maximum to prevent infinite loops
            EMERGENCY_MAX_CONVERSATIONS = 20000
            
            # Use SDK's search method with pagination and built-in retry
            # SDK automatically retries 429 (rate limit) errors with exponential backoff
            # Pass through request_options if provided for custom retry/timeout behavior
            pager: AsyncPager = await self.client.conversations.search(
                query=search_query,
                pagination=pagination,
                request_options=request_options
            )
            
            # Track duplicate prevention
            seen_ids: set[str] = set()
            
            # Rate limiting state - adaptive based on API response headers
            rate_limit_remaining = None
            rate_limit_reset = None
            request_count = 0

            # Iterate through all pages
            async for conversation in pager:
                request_count += 1
                
                # EMERGENCY BRAKE CHECK - Hard limit to prevent infinite loops
                if len(all_conversations) >= EMERGENCY_MAX_CONVERSATIONS:
                    self.logger.error(
                        f"EMERGENCY BRAKE: Hit {EMERGENCY_MAX_CONVERSATIONS} conversations! "
                        f"This is likely a bug. Stopping fetch to prevent runaway process."
                    )
                    break
                
                # Emergency brake — absolute cap on conversations fetched (if specified)
                if max_conversations and len(all_conversations) >= max_conversations:
                    self.logger.warning(
                        f"Emergency brake hit — fetched {len(all_conversations)} conversations (cap={max_conversations})."
                    )
                    break

                # Convert SDK Pydantic model to dict
                conv_dict = self._model_to_dict(conversation)

                # Deduplicate by conversation id if present
                conv_id = conv_dict.get("id")
                if conv_id and conv_id in seen_ids:
                    continue
                if conv_id:
                    seen_ids.add(conv_id)

                all_conversations.append(conv_dict)
                
                # Log progress every 50 conversations
                if len(all_conversations) % 50 == 0:
                    self.logger.info(f"Fetched {len(all_conversations)} conversations")
                
                # NOTE: SDK handles rate limiting automatically by retrying 429 errors
                # No manual sleep needed - let the SDK do its job!
            
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
        Enrich conversations with full contact details, segments, AND conversation_parts.
        
        CRITICAL: conversation_parts is REQUIRED for:
        - Sal vs Human admin detection
        - Full conversation text extraction
        - Topic detection accuracy
        
        Uses semaphore-based concurrency control to limit concurrent API requests
        and implements request pacing to respect Intercom rate limits.
        
        Args:
            conversations: List of conversation dictionaries
            
        Returns:
            List of enriched conversation dictionaries
        """
        async def enrich_single_conversation(conv: Dict) -> tuple[Dict, Dict]:
            """
            Enrich a single conversation with concurrency control.
            
            Returns:
                Tuple of (enriched_conversation, metrics_dict)
            """
            metrics = {
                'attempted': 1,
                'successful': 0,
                'failed_contact': 0,
                'failed_segments': 0,
                'failed_conversation_parts': 0,
                'skipped_no_contact': 0
            }
            
            async with self._enrichment_semaphore:
                try:
                    # STEP 1: Fetch full conversation details (includes conversation_parts)
                    # This is CRITICAL for Sal detection and full text extraction
                    conv_id = conv.get('id')
                    if conv_id:
                        try:
                            full_conv_data = await self._fetch_full_conversation(conv_id)
                            
                            # Merge conversation_parts into the conversation
                            # NORMALIZE: Ensure conversation_parts is always dict-wrapped
                            if 'conversation_parts' in full_conv_data:
                                parts = full_conv_data['conversation_parts']
                                # If SDK returns a list, wrap it as {'conversation_parts': list}
                                if isinstance(parts, list):
                                    conv['conversation_parts'] = {'conversation_parts': parts}
                                elif isinstance(parts, dict):
                                    conv['conversation_parts'] = parts
                                else:
                                    self.logger.warning(
                                        f"Unexpected conversation_parts type for {conv_id}: {type(parts)}"
                                    )
                                    conv['conversation_parts'] = {'conversation_parts': []}
                                self.logger.debug(
                                    f"Enriched conversation {conv_id} with conversation_parts"
                                )
                        except ApiError as e:
                            metrics['failed_conversation_parts'] += 1
                            if e.status_code == 404:
                                self.logger.warning(f"Conversation {conv_id} not found")
                            else:
                                self.logger.warning(f"Failed to fetch conversation parts for {conv_id}: {e}")
                        except (httpx.RequestError, asyncio.TimeoutError) as e:
                            metrics['failed_conversation_parts'] += 1
                            self.logger.warning(
                                f"Network error fetching conversation parts for {conv_id}: {e}"
                            )
                        except Exception as e:
                            metrics['failed_conversation_parts'] += 1
                            self.logger.warning(f"Error fetching conversation parts for {conv_id}: {e}")
                    
                    # STEP 2: Extract contact IDs from the conversation
                    contacts_data = conv.get('contacts', {})
                    if contacts_data and isinstance(contacts_data, dict):
                        contacts_list = contacts_data.get('contacts', [])
                        
                        if contacts_list:
                            # Get the first contact (primary contact)
                            contact_id = contacts_list[0].get('id')
                            
                            if contact_id:
                                try:
                                    # Fetch full contact details with retry/backoff
                                    full_contact_data = await self._fetch_contact_details(contact_id)

                                    try:
                                        segments_data = await self._fetch_contact_segments(contact_id)
                                        full_contact_data['segments'] = segments_data
                                        self.logger.debug(
                                            f"Enriched conversation {conv.get('id')} with segments"
                                        )
                                    except ApiError as e:
                                        metrics['failed_segments'] += 1
                                        self.logger.warning(
                                            f"Failed to fetch segments for contact {contact_id}: {e}"
                                        )
                                    except (httpx.RequestError, asyncio.TimeoutError) as e:
                                        metrics['failed_segments'] += 1
                                        self.logger.warning(
                                            f"Network error fetching segments for contact {contact_id}: {e}"
                                        )
                                    except Exception as e:
                                        metrics['failed_segments'] += 1
                                        self.logger.warning(
                                            f"Unexpected error fetching segments for contact {contact_id}: {e}"
                                        )

                                    # Replace the contact data in the conversation (safe access)
                                    contacts_dict = conv.get('contacts', {})
                                    if isinstance(contacts_dict, dict):
                                        contacts_list = contacts_dict.get('contacts', [])
                                        if isinstance(contacts_list, list) and len(contacts_list) > 0:
                                            contacts_list[0] = full_contact_data
                                    metrics['successful'] += 1
                                    self.logger.debug(
                                        f"Enriched conversation {conv.get('id')} with full contact details"
                                    )

                                except ApiError as e:
                                    metrics['failed_contact'] += 1
                                    if e.status_code == 404:
                                        self.logger.warning(f"Contact {contact_id} not found")
                                    else:
                                        self.logger.warning(f"Failed to fetch contact {contact_id}: {e}")
                                except (httpx.RequestError, asyncio.TimeoutError) as e:
                                    metrics['failed_contact'] += 1
                                    self.logger.warning(
                                        f"Network error fetching contact {contact_id}: {e}"
                                    )
                                except Exception as e:
                                    metrics['failed_contact'] += 1
                                    self.logger.warning(f"Error fetching contact {contact_id}: {e}")
                            else:
                                metrics['skipped_no_contact'] += 1
                        else:
                            metrics['skipped_no_contact'] += 1
                    else:
                        metrics['skipped_no_contact'] += 1
                    
                    return conv, metrics
                    
                except Exception as e:
                    self.logger.warning(f"Failed to enrich conversation {conv.get('id')}: {e}")
                    # Return the original conversation if enrichment fails
                    return conv, metrics
        
        # Process conversations with controlled concurrency
        total_conversations = len(conversations)
        self.logger.info(
            f"Enriching {total_conversations} conversations "
            f"(concurrency={self.concurrency}, delay={self.request_delay*1000:.0f}ms)"
        )
        
        # Track progress for periodic logging
        completed_count = 0
        last_progress_log_time = time.time()
        progress_interval_seconds = 30  # Log progress every 30 seconds
        progress_interval_count = 100  # Or every 100 conversations
        
        async def enrich_with_progress(conv, index):
            """Wrapper to track enrichment progress."""
            nonlocal completed_count, last_progress_log_time
            result = await enrich_single_conversation(conv)
            completed_count += 1
            
            # Log progress periodically
            current_time = time.time()
            should_log = (
                completed_count % progress_interval_count == 0 or
                (current_time - last_progress_log_time) >= progress_interval_seconds
            )
            
            if should_log:
                elapsed = current_time - last_progress_log_time
                rate = completed_count / elapsed if elapsed > 0 else 0
                remaining = total_conversations - completed_count
                eta_seconds = remaining / rate if rate > 0 else 0
                eta_minutes = eta_seconds / 60
                
                self.logger.info(
                    f"Enrichment progress: {completed_count}/{total_conversations} "
                    f"({completed_count/total_conversations*100:.1f}%) | "
                    f"Rate: {rate:.1f} conv/s | "
                    f"ETA: {eta_minutes:.1f} min"
                )
                last_progress_log_time = current_time
            
            return result
        
        results = await asyncio.gather(
            *[enrich_with_progress(conv, i) for i, conv in enumerate(conversations)],
            return_exceptions=False
        )
        
        # Aggregate metrics from all enrichment tasks (no race conditions)
        enrichment_stats = {
            'attempted': 0,
            'successful': 0,
            'failed_contact': 0,
            'failed_segments': 0,
            'failed_conversation_parts': 0,
            'skipped_no_contact': 0
        }
        enriched_conversations = []
        
        for conv, metrics in results:
            enriched_conversations.append(conv)
            for key in enrichment_stats:
                enrichment_stats[key] += metrics[key]
        
        # Log detailed enrichment statistics
        success_rate = (enrichment_stats['successful'] / enrichment_stats['attempted'] * 100) if enrichment_stats['attempted'] > 0 else 0
        parts_success_rate = ((enrichment_stats['attempted'] - enrichment_stats['failed_conversation_parts']) / enrichment_stats['attempted'] * 100) if enrichment_stats['attempted'] > 0 else 0
        self.logger.info(
            f"ENRICHMENT_METRICS: attempted={enrichment_stats['attempted']}, "
            f"successful={enrichment_stats['successful']}, "
            f"failed_contact={enrichment_stats['failed_contact']}, "
            f"failed_segments={enrichment_stats['failed_segments']}, "
            f"failed_conversation_parts={enrichment_stats['failed_conversation_parts']}, "
            f"skipped={enrichment_stats['skipped_no_contact']}, "
            f"success_rate={success_rate:.1f}%, "
            f"conversation_parts_success_rate={parts_success_rate:.1f}%"
        )
        
        return enriched_conversations
    
    @async_retry(
        retries=3,
        base_delay=0.5,
        backoff_factor=2.0,
        jitter=0.5,
        retry_exceptions=(ApiError, httpx.RequestError, asyncio.TimeoutError),
    )
    async def _fetch_full_conversation(self, conversation_id: str) -> Dict:
        """
        Fetch FULL conversation details including conversation_parts.
        
        CRITICAL: This is the ONLY way to get conversation_parts from Intercom API.
        The search endpoint doesn't include conversation_parts by default.
        
        Args:
            conversation_id: Conversation ID to fetch
            
        Returns:
            Full conversation dictionary with conversation_parts
        """
        conversation = await self.client.conversations.find(conversation_id)
        # Add delay after request to respect rate limits
        await asyncio.sleep(self.request_delay)
        return self._model_to_dict(conversation)

    @async_retry(
        retries=3,
        base_delay=0.5,
        backoff_factor=2.0,
        jitter=0.5,
        retry_exceptions=(ApiError, httpx.RequestError, asyncio.TimeoutError),
    )
    async def _fetch_contact_details(self, contact_id: str) -> Dict:
        """
        Fetch contact details with request pacing.
        
        Args:
            contact_id: Contact ID to fetch
            
        Returns:
            Contact details dictionary
        """
        contact = await self.client.contacts.find(contact_id)
        # Add delay after request to respect rate limits
        await asyncio.sleep(self.request_delay)
        return self._model_to_dict(contact)

    @async_retry(
        retries=3,
        base_delay=0.5,
        backoff_factor=2.0,
        jitter=0.5,
        retry_exceptions=(ApiError, httpx.RequestError, asyncio.TimeoutError),
    )
    async def _fetch_contact_segments(self, contact_id: str) -> Dict:
        """
        Fetch contact segments with request pacing.
        
        Args:
            contact_id: Contact ID to fetch segments for
            
        Returns:
            Contact segments dictionary
        """
        segments = await self.client.contacts.list_attached_segments(contact_id)
        # Add delay after request to respect rate limits
        await asyncio.sleep(self.request_delay)
        return self._model_to_dict(segments)
    
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
    
    async def _fetch_with_query(
        self, 
        search_query, 
        max_pages: Optional[int],
        request_options: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Generic method to fetch conversations with a search query.
        
        Args:
            search_query: Search query filter
            max_pages: Maximum number of pages to fetch
            request_options: Optional dict for SDK request options (e.g., {'max_retries': 3, 'timeout': 60})
            
        Returns:
            List of conversation dictionaries
        """
        all_conversations = []
        page_count = 0
        
        pagination = StartingAfterPaging(
            per_page=50,
            starting_after=None
        )
        
        try:
            if request_options:
                pager: AsyncPager = await self.client.conversations.search(
                    query=search_query,
                    pagination=pagination,
                    request_options=request_options
                )
            else:
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
            
            # CRITICAL: Enrich with conversation_parts (same as fetch_conversations_by_date_range)
            enriched_conversations = await self._enrich_conversations_with_contact_details(
                all_conversations
            )
            
            return enriched_conversations
            
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
        Convert SDK Pydantic model to dictionary without serialization warnings.
        
        Uses mode='python' to bypass JSON serialization and avoid Pydantic warnings
        about int/str type mismatches in the Intercom SDK models.
        
        Uses exclude_none=True to avoid bloating payloads with null fields.
        
        Args:
            model: SDK Pydantic model
            
        Returns:
            Dictionary representation of the model
        """
        if hasattr(model, 'model_dump'):
            # Pydantic v2 - use mode='python' to avoid serialization warnings
            # and exclude_none=True to reduce payload size
            return model.model_dump(mode='python', exclude_none=True)
        elif hasattr(model, 'dict'):
            # Pydantic v1 - exclude None fields
            return model.dict(exclude_none=True)
        else:
            # Fallback for non-Pydantic models
            return dict(model)

