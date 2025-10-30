"""
Chunked Fetcher Service for Intercom Analysis Tool.
Handles large data fetches with intelligent chunking and rate limiting.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, AsyncGenerator
from pathlib import Path
import json

from src.services.intercom_sdk_service import IntercomSDKService
from src.services.data_preprocessor import DataPreprocessor
from src.utils.time_utils import to_utc_datetime, ensure_date

logger = logging.getLogger(__name__)


class ChunkedFetcher:
    """
    Intelligent chunked fetcher for large Intercom data requests.
    
    Features:
    - Daily chunking for large date ranges
    - Intelligent rate limiting
    - Progress tracking
    - Error recovery
    - Memory-efficient processing
    """
    
    def __init__(
        self,
        intercom_service: Optional[IntercomSDKService] = None,
        enable_preprocessing: bool = True,
        chunk_timeout: int = 300,  # Increased from 120s to 300s (5 minutes) per Intercom best practices
    ):
        """
        Initialize chunked fetcher.
        
        OPTIMIZED per official Intercom SDK documentation:
        - Increased default timeout from 120s to 300s to accommodate larger fetches
        - Smaller default chunk sizes (1 day) to prevent timeouts
        - Exponential backoff retry logic for transient errors
        - Adaptive rate limiting within Intercom's 10k calls/min limit
        
        Args:
            intercom_service: Intercom SDK service instance (optional)
            enable_preprocessing: Whether to preprocess conversations (default: True)
            chunk_timeout: Maximum seconds to wait for a single chunk fetch (default: 300s)
        """
        self.intercom_service = intercom_service or IntercomSDKService()
        self.preprocessor = DataPreprocessor() if enable_preprocessing else None
        self.enable_preprocessing = enable_preprocessing
        self.logger = logging.getLogger(__name__)
        self.chunk_timeout = chunk_timeout
        
        # Chunking configuration - OPTIMIZED per Intercom API best practices
        # Smaller chunks prevent timeouts and align with rate limits
        self.max_days_per_chunk = 1  # Process max 1 day at a time (optimal for 10k/min rate limit)
        self.max_conversations_per_chunk = 1000  # Max conversations per chunk
        self.chunk_delay = 1.0  # Delay between chunks (seconds) - reduced for efficiency
        
        # Retry configuration for exponential backoff
        self.max_retries = 3
        self.retry_backoff_factor = 2
        
        self.logger.info(
            f"Initialized ChunkedFetcher with max_days_per_chunk={self.max_days_per_chunk}, "
            f"preprocessing={'enabled' if enable_preprocessing else 'disabled'}, "
            f"chunk_timeout={self.chunk_timeout}s, "
            f"max_retries={self.max_retries}"
        )
    
    async def fetch_conversations_chunked(
        self, 
        start_date: datetime, 
        end_date: datetime,
        max_conversations: Optional[int] = None,
        # Deprecated alias for backward compatibility
        max_pages: Optional[int] = None,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch conversations in intelligent chunks.
        
        Args:
            start_date: Start date for fetching
            end_date: End date for fetching
            max_conversations: Maximum conversations per chunk (for testing)
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of all conversations fetched
            
        Raises:
            FetchError: If fetching fails
        """
        self.logger.info(f"Starting chunked fetch from {start_date.date()} to {end_date.date()}")
        
        # Calculate total days
        total_days = (end_date - start_date).days + 1
        self.logger.info(f"Total date range: {total_days} days")
        
        # Prefer explicit max_conversations, fallback to deprecated max_pages
        if max_conversations is None and max_pages is not None:
            self.logger.warning("Parameter 'max_pages' is deprecated; use 'max_conversations' instead.")
            max_conversations = max_pages

        # RETRY LOGIC with exponential backoff per Intercom API best practices
        for attempt in range(self.max_retries):
            try:
                # Determine chunking strategy
                if total_days <= self.max_days_per_chunk:
                    # Small range - fetch in one chunk
                    return await asyncio.wait_for(
                        self._fetch_single_chunk(start_date, end_date, max_conversations, progress_callback),
                        timeout=self.chunk_timeout,
                    )
                else:
                    # Large range - fetch in daily chunks
                    return await asyncio.wait_for(
                        self._fetch_daily_chunks(start_date, end_date, max_conversations, progress_callback),
                        timeout=self.chunk_timeout,
                    )
            except asyncio.TimeoutError as exc:
                if attempt < self.max_retries - 1:
                    # Calculate exponential backoff wait time
                    wait_time = self.retry_backoff_factor ** attempt
                    self.logger.warning(
                        f"Chunk fetch timed out (attempt {attempt + 1}/{self.max_retries}). "
                        f"Retrying in {wait_time}s with smaller chunk size..."
                    )
                    # Reduce chunk size for retry
                    self.max_days_per_chunk = max(1, self.max_days_per_chunk // 2)
                    self.logger.info(f"Reduced chunk size to {self.max_days_per_chunk} days for retry")
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(
                        f"Chunk fetch exceeded {self.chunk_timeout}s timeout after {self.max_retries} attempts"
                    )
                    raise FetchError(f"Chunk fetch timed out after {self.max_retries} attempts") from exc
            except asyncio.CancelledError:
                self.logger.warning("Chunked fetch cancelled by caller; propagating cancellation")
                raise
    
    async def _fetch_single_chunk(
        self, 
        start_date: datetime, 
        end_date: datetime,
        max_conversations: Optional[int],
        progress_callback: Optional[callable]
    ) -> List[Dict[str, Any]]:
        """Fetch a single chunk of conversations."""
        self.logger.info(f"Fetching single chunk: {start_date.date()} to {end_date.date()}")
        
        try:
            conversations = await self.intercom_service.fetch_conversations_by_date_range(
                start_date, end_date, max_conversations=max_conversations
            )
            
            # Preprocess conversations if enabled
            if self.enable_preprocessing and self.preprocessor:
                self.logger.info(f"Preprocessing {len(conversations)} conversations...")
                conversations, preprocess_stats = self.preprocessor.preprocess_conversations(
                    conversations,
                    options={'deduplicate': True, 'infer_missing': True, 'clean_text': True}
                )
                self.logger.info(
                    f"Preprocessing complete: {preprocess_stats['processed_count']} valid conversations, "
                    f"{len(preprocess_stats.get('validation_errors', []))} errors"
                )
            
            # Standardized progress callback: (fetched_count, processed_days, total_days)
            if progress_callback:
                total_days = (end_date - start_date).days + 1
                progress_callback(len(conversations), total_days, total_days)
            
            # Debug: Check actual date range of fetched conversations
            if conversations:
                # Convert created_at to datetime, handling both datetime and numeric types
                actual_dates = []
                for c in conversations:
                    created_at = c.get('created_at')
                    if created_at:
                        dt = to_utc_datetime(created_at)
                        if dt:
                            actual_dates.append(dt)
                
                if actual_dates:
                    min_date = min(actual_dates)
                    max_date = max(actual_dates)
                    self.logger.info(f"Actual date range in fetched data: {min_date.date()} to {max_date.date()}")
                    
                    # Check if dates are outside requested range
                    if min_date.date() < start_date.date() or max_date.date() > end_date.date():
                        self.logger.warning(f"API returned conversations outside requested range!")
                        self.logger.warning(f"   Requested: {start_date.date()} to {end_date.date()}")
                        self.logger.warning(f"   Received: {min_date.date()} to {max_date.date()}")
            
            self.logger.info(f"Single chunk completed: {len(conversations)} conversations")
            return conversations
            
        except asyncio.CancelledError:
            self.logger.warning("Single chunk fetch cancelled; propagating cancellation")
            raise
        except Exception as e:
            self.logger.error(f"Single chunk fetch failed: {e}", exc_info=True)
            raise FetchError(f"Failed to fetch single chunk: {e}") from e
    
    async def _fetch_daily_chunks(
        self,
        start_date: datetime,
        end_date: datetime,
        max_conversations: Optional[int],
        progress_callback: Optional[callable]
    ) -> List[Dict[str, Any]]:
        """
        Fetch conversations in daily chunks with deduplication.
        
        OPTIMIZED per Intercom API best practices:
        - Sequential processing with intelligent rate limiting
        - Deduplication to prevent duplicate conversations
        - Progress tracking for user feedback
        - Graceful error handling with partial results
        
        Note: Parallel processing is NOT used here to stay within Intercom's
        10k calls/min rate limit. Sequential processing with proper delays
        is more reliable and prevents rate limit errors.
        """
        self.logger.info(f"Fetching daily chunks: {start_date.date()} to {end_date.date()}")

        all_conversations = []
        seen_ids: set[str] = set()  # Track conversation IDs to prevent duplicates
        current_date = start_date
        total_days = (end_date - start_date).days + 1
        processed_days = 0

        try:
            while current_date <= end_date:
                # Calculate chunk end date
                chunk_end = min(current_date + timedelta(days=self.max_days_per_chunk - 1), end_date)

                self.logger.info(f"Processing chunk: {current_date.date()} to {chunk_end.date()}")

                try:
                    # Fetch chunk with timeout protection
                    chunk_conversations = await asyncio.wait_for(
                        self.intercom_service.fetch_conversations_by_date_range(
                            current_date, chunk_end, max_conversations=max_conversations
                        ),
                        timeout=self.chunk_timeout,
                    )

                    # Deduplicate: only add conversations we haven't seen
                    duplicates = 0
                    for conv in chunk_conversations:
                        conv_id = conv.get('id')
                        if conv_id and conv_id not in seen_ids:
                            seen_ids.add(conv_id)
                            all_conversations.append(conv)
                        elif conv_id:
                            duplicates += 1
                    
                    if duplicates > 0:
                        self.logger.warning(f"Skipped {duplicates} duplicate conversations in this chunk")

                    # Debug: Check actual date range of fetched chunk
                    if chunk_conversations:
                        # Convert created_at to datetime, handling both datetime and numeric types
                        actual_dates = []
                        for c in chunk_conversations:
                            created_at = c.get('created_at')
                            if created_at:
                                dt = to_utc_datetime(created_at)
                                if dt:
                                    actual_dates.append(dt)

                        if actual_dates:
                            min_date = min(actual_dates)
                            max_date = max(actual_dates)
                            self.logger.info(f"Chunk actual dates: {min_date.date()} to {max_date.date()}")

                            # Check if dates are outside requested range
                            if min_date.date() < current_date.date() or max_date.date() > chunk_end.date():
                                self.logger.warning(f"API returned conversations outside chunk range!")
                                self.logger.warning(f"   Requested: {current_date.date()} to {chunk_end.date()}")
                                self.logger.warning(f"   Received: {min_date.date()} to {max_date.date()}")

                    # Track processed days for progress reporting
                    processed_days += (chunk_end - current_date).days + 1

                    # Check absolute cap
                    if max_conversations and len(all_conversations) >= max_conversations:
                        self.logger.warning(
                            f"ChunkedFetcher cap reached — returning first {max_conversations} conversations."
                        )
                        return all_conversations[:max_conversations]

                    # Update progress
                    if progress_callback:
                        progress_callback(len(all_conversations), processed_days, total_days)

                    self.logger.info(f"Chunk completed: {len(chunk_conversations)} conversations (total: {len(all_conversations)})")

                    # Delay between chunks to respect rate limits
                    if chunk_end < end_date:
                        self.logger.debug(f"Waiting {self.chunk_delay}s before next chunk")
                        await asyncio.sleep(self.chunk_delay)

                    # Move to next chunk
                    current_date = chunk_end + timedelta(days=1)

                except asyncio.TimeoutError as exc:
                    self.logger.error(
                        "Chunk fetch for %s-%s exceeded %s s timeout",
                        current_date.date(),
                        chunk_end.date(),
                        self.chunk_timeout,
                    )
                    raise FetchError(
                        f"Chunk fetch timed out for range {current_date.date()}-{chunk_end.date()}"
                    ) from exc
                except asyncio.CancelledError:
                    self.logger.warning(
                        "Chunk fetch cancelled by caller while processing %s-%s",
                        current_date.date(),
                        chunk_end.date(),
                    )
                    raise
                except Exception as e:
                    self.logger.error(f"Chunk fetch failed for {current_date.date()}-{chunk_end.date()}: {e}")

                    # Decide whether to continue or fail
                    if len(all_conversations) > 0:
                        self.logger.warning(f"Continuing with {len(all_conversations)} conversations already fetched")
                        break
                    else:
                        self.logger.error("No conversations fetched, failing")
                        raise FetchError(f"Failed to fetch chunk {current_date.date()}-{chunk_end.date()}: {e}") from e

        finally:
            # Ensure final progress callback with accurate counts
            if progress_callback:
                final_processed_days = min(total_days, processed_days)
                progress_callback(len(all_conversations), final_processed_days, total_days)
        
        # Final verification of all fetched data
        if all_conversations:
            # Convert created_at to datetime, handling both datetime and numeric types
            all_dates = []
            for c in all_conversations:
                created_at = c.get('created_at')
                if created_at:
                    dt = to_utc_datetime(created_at)
                    if dt:
                        all_dates.append(dt)
            
            if all_dates:
                final_min = min(all_dates)
                final_max = max(all_dates)
                self.logger.info(f"FINAL: Fetched {len(all_conversations)} conversations")
                self.logger.info(f"FINAL: Date range {final_min.date()} to {final_max.date()}")
                self.logger.info(f"   Requested: {start_date.date()} to {end_date.date()}")
        else:
            self.logger.info(f"Daily chunking completed: {len(all_conversations)} total conversations")
        
        # Preprocess all conversations if enabled
        if self.enable_preprocessing and self.preprocessor and all_conversations:
            self.logger.info(f"Preprocessing {len(all_conversations)} conversations from daily chunks...")
            all_conversations, preprocess_stats = self.preprocessor.preprocess_conversations(
                all_conversations,
                options={'deduplicate': True, 'infer_missing': True, 'clean_text': True}
            )
            self.logger.info(
                f"Preprocessing complete: {preprocess_stats['processed_count']} valid conversations, "
                f"{len(preprocess_stats.get('validation_errors', []))} errors"
            )
        
        return all_conversations
    
    async def fetch_with_conversation_limit(
        self, 
        start_date: datetime, 
        end_date: datetime,
        max_conversations: int,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch conversations with a hard limit on total count.
        
        Args:
            start_date: Start date for fetching
            end_date: End date for fetching
            max_conversations: Maximum total conversations to fetch
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of conversations (up to max_conversations)
        """
        self.logger.info(f"Fetching with limit: max {max_conversations} conversations")
        
        all_conversations = []
        current_date = start_date
        
        while current_date <= end_date and len(all_conversations) < max_conversations:
            # Calculate remaining conversations needed
            remaining = max_conversations - len(all_conversations)
            
            # Calculate chunk end date
            chunk_end = min(current_date + timedelta(days=self.max_days_per_chunk - 1), end_date)
            
            self.logger.info(f"Fetching chunk: {current_date.date()} to {chunk_end.date()} (need {remaining} more)")
            
            try:
                # Fetch chunk
                chunk_conversations = await self.intercom_service.fetch_conversations_by_date_range(
                    current_date, chunk_end
                )
                
                # Add conversations up to the limit
                for conv in chunk_conversations:
                    if len(all_conversations) >= max_conversations:
                        break
                    all_conversations.append(conv)
                
                # Update progress
                if progress_callback:
                    progress_callback(len(all_conversations), max_conversations)
                
                self.logger.info(f"Chunk completed: {len(chunk_conversations)} available, {len(all_conversations)} total")
                
                # If we've hit the limit, stop
                if len(all_conversations) >= max_conversations:
                    self.logger.info(f"Reached conversation limit: {max_conversations}")
                    break
                
                # Delay between chunks
                if chunk_end < end_date:
                    await asyncio.sleep(self.chunk_delay)
                
                # Move to next chunk
                current_date = chunk_end + timedelta(days=1)
                
            except Exception as e:
                self.logger.error(f"Chunk fetch failed: {e}")
                if len(all_conversations) == 0:
                    raise FetchError(f"Failed to fetch any conversations: {e}") from e
                else:
                    self.logger.warning(f"Continuing with {len(all_conversations)} conversations already fetched")
                    break
        
        self.logger.info(f"Fetch with limit completed: {len(all_conversations)} conversations")
        
        # Preprocess conversations if enabled
        if self.enable_preprocessing and self.preprocessor and all_conversations:
            self.logger.info(f"Preprocessing {len(all_conversations)} conversations with limit...")
            all_conversations, preprocess_stats = self.preprocessor.preprocess_conversations(
                all_conversations,
                options={'deduplicate': True, 'infer_missing': True, 'clean_text': True}
            )
            self.logger.info(
                f"Preprocessing complete: {preprocess_stats['processed_count']} valid conversations, "
                f"{len(preprocess_stats.get('validation_errors', []))} errors"
            )
        
        return all_conversations
    
    async def fetch_conversations_streaming(
        self, 
        start_date: datetime, 
        end_date: datetime,
        max_pages: Optional[int] = None
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Stream conversations in chunks for memory-efficient processing.
        
        Args:
            start_date: Start date for fetching
            end_date: End date for fetching
            max_pages: Maximum pages per chunk
            
        Yields:
            Lists of conversations as they are fetched
        """
        self.logger.info(f"Starting streaming fetch from {start_date.date()} to {end_date.date()}")
        
        current_date = start_date
        
        while current_date <= end_date:
            # Calculate chunk end date
            chunk_end = min(current_date + timedelta(days=self.max_days_per_chunk - 1), end_date)
            
            self.logger.info(f"Streaming chunk: {current_date.date()} to {chunk_end.date()}")
            
            try:
                # Fetch chunk
                chunk_conversations = await self.intercom_service.fetch_conversations_by_date_range(
                    current_date, chunk_end, max_conversations=max_pages
                )
                
                if chunk_conversations:
                    self.logger.info(f"Yielding {len(chunk_conversations)} conversations")
                    yield chunk_conversations
                
                # Delay between chunks
                if chunk_end < end_date:
                    await asyncio.sleep(self.chunk_delay)
                
                # Move to next chunk
                current_date = chunk_end + timedelta(days=1)
                
            except Exception as e:
                self.logger.error(f"Streaming chunk failed: {e}")
                # Continue with next chunk
                current_date = chunk_end + timedelta(days=1)
        
        self.logger.info("Streaming fetch completed")
    
    def save_chunk_to_file(
        self, 
        conversations: List[Dict[str, Any]], 
        chunk_index: int, 
        output_dir: Path
    ) -> Path:
        """
        Save a chunk of conversations to a file.
        
        Args:
            conversations: Conversations to save
            chunk_index: Index of the chunk
            output_dir: Output directory
            
        Returns:
            Path to saved file
        """
        output_dir.mkdir(exist_ok=True)
        
        filename = f"conversations_chunk_{chunk_index:03d}.json"
        filepath = output_dir / filename
        
        self.logger.info(f"Saving chunk {chunk_index} to {filepath}")
        
        try:
            with open(filepath, 'w') as f:
                json.dump(conversations, f, indent=2, default=str)
            
            self.logger.info(f"Chunk {chunk_index} saved: {len(conversations)} conversations")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to save chunk {chunk_index}: {e}")
            raise SaveError(f"Failed to save chunk to {filepath}: {e}") from e
    
    def load_chunks_from_files(self, output_dir: Path) -> List[Dict[str, Any]]:
        """
        Load all conversation chunks from files.
        
        Args:
            output_dir: Directory containing chunk files
            
        Returns:
            List of all conversations from all chunks
        """
        self.logger.info(f"Loading chunks from {output_dir}")
        
        all_conversations = []
        chunk_files = sorted(output_dir.glob("conversations_chunk_*.json"))
        
        if not chunk_files:
            self.logger.warning(f"No chunk files found in {output_dir}")
            return all_conversations
        
        for chunk_file in chunk_files:
            self.logger.info(f"Loading chunk file: {chunk_file.name}")
            
            try:
                with open(chunk_file, 'r') as f:
                    chunk_conversations = json.load(f)
                
                all_conversations.extend(chunk_conversations)
                self.logger.info(f"Loaded {len(chunk_conversations)} conversations from {chunk_file.name}")
                
            except Exception as e:
                self.logger.error(f"Failed to load chunk file {chunk_file}: {e}")
                # Continue with other files
                continue
        
        self.logger.info(f"Loaded {len(all_conversations)} total conversations from {len(chunk_files)} chunks")
        return all_conversations
    
    def get_fetch_statistics(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics about fetched conversations.
        
        Args:
            conversations: List of conversations
            
        Returns:
            Statistics dictionary
        """
        if not conversations:
            return {"total_conversations": 0}
        
        # Calculate date range - normalize all timestamps to UTC datetime
        datetimes = []
        for conv in conversations:
            created_at = conv.get('created_at')
            if created_at:
                dt = to_utc_datetime(created_at)
                if dt:
                    datetimes.append(dt)
        
        if datetimes:
            min_date = min(datetimes)
            max_date = max(datetimes)
        else:
            min_date = max_date = None
        
        # Count by state
        states = {}
        for conv in conversations:
            state = conv.get('state', 'unknown')
            states[state] = states.get(state, 0) + 1
        
        # Count by language
        languages = {}
        for conv in conversations:
            lang = conv.get('custom_attributes', {}).get('Language', 'unknown')
            languages[lang] = languages.get(lang, 0) + 1
        
        # Calculate average per day using date differences
        avg_per_day = 0
        if min_date and max_date:
            days_diff = (max_date.date() - min_date.date()).days + 1
            avg_per_day = len(conversations) / max(1, days_diff)
        
        stats = {
            "total_conversations": len(conversations),
            "date_range": {
                "start": min_date.isoformat() if min_date else None,
                "end": max_date.isoformat() if max_date else None
            },
            "conversation_states": states,
            "languages": languages,
            "avg_conversations_per_day": round(avg_per_day, 2)
        }
        
        self.logger.info(f"Fetch statistics: {stats}")
        return stats


# Custom Exceptions
class FetchError(Exception):
    """Exception raised when fetching fails."""
    pass


class SaveError(Exception):
    """Exception raised when saving fails."""
    pass






