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

from src.services.intercom_service_v2 import IntercomServiceV2

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
    
    def __init__(self, intercom_service: Optional[IntercomServiceV2] = None):
        """
        Initialize chunked fetcher.
        
        Args:
            intercom_service: Intercom service instance (optional)
        """
        self.intercom_service = intercom_service or IntercomServiceV2()
        self.logger = logging.getLogger(__name__)
        
        # Chunking configuration
        self.max_days_per_chunk = 7  # Process max 7 days at a time
        self.max_conversations_per_chunk = 1000  # Max conversations per chunk
        self.chunk_delay = 2.0  # Delay between chunks (seconds)
        
        self.logger.info(f"Initialized ChunkedFetcher with max_days_per_chunk={self.max_days_per_chunk}")
    
    async def fetch_conversations_chunked(
        self, 
        start_date: datetime, 
        end_date: datetime,
        max_pages: Optional[int] = None,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch conversations in intelligent chunks.
        
        Args:
            start_date: Start date for fetching
            end_date: End date for fetching
            max_pages: Maximum pages per chunk (for testing)
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
        
        # Determine chunking strategy
        if total_days <= self.max_days_per_chunk:
            # Small range - fetch in one chunk
            return await self._fetch_single_chunk(start_date, end_date, max_pages, progress_callback)
        else:
            # Large range - fetch in daily chunks
            return await self._fetch_daily_chunks(start_date, end_date, max_pages, progress_callback)
    
    async def _fetch_single_chunk(
        self, 
        start_date: datetime, 
        end_date: datetime,
        max_pages: Optional[int],
        progress_callback: Optional[callable]
    ) -> List[Dict[str, Any]]:
        """Fetch a single chunk of conversations."""
        self.logger.info(f"Fetching single chunk: {start_date.date()} to {end_date.date()}")
        
        try:
            conversations = await self.intercom_service.fetch_conversations_by_date_range(
                start_date, end_date, max_pages
            )
            
            if progress_callback:
                progress_callback(len(conversations), len(conversations))
            
            # Debug: Check actual date range of fetched conversations
            if conversations:
                actual_dates = [datetime.fromtimestamp(c.get('created_at')) for c in conversations if c.get('created_at')]
                if actual_dates:
                    min_date = min(actual_dates)
                    max_date = max(actual_dates)
                    self.logger.info(f"📅 Actual date range in fetched data: {min_date.date()} to {max_date.date()}")
                    
                    # Check if dates are outside requested range
                    if min_date.date() < start_date.date() or max_date.date() > end_date.date():
                        self.logger.warning(f"⚠️  API returned conversations outside requested range!")
                        self.logger.warning(f"   Requested: {start_date.date()} to {end_date.date()}")
                        self.logger.warning(f"   Received: {min_date.date()} to {max_date.date()}")
            
            self.logger.info(f"Single chunk completed: {len(conversations)} conversations")
            return conversations
            
        except Exception as e:
            self.logger.error(f"Single chunk fetch failed: {e}", exc_info=True)
            raise FetchError(f"Failed to fetch single chunk: {e}") from e
    
    async def _fetch_daily_chunks(
        self, 
        start_date: datetime, 
        end_date: datetime,
        max_pages: Optional[int],
        progress_callback: Optional[callable]
    ) -> List[Dict[str, Any]]:
        """Fetch conversations in daily chunks."""
        self.logger.info(f"Fetching daily chunks: {start_date.date()} to {end_date.date()}")
        
        all_conversations = []
        current_date = start_date
        total_days = (end_date - start_date).days + 1
        processed_days = 0
        
        while current_date <= end_date:
            # Calculate chunk end date
            chunk_end = min(current_date + timedelta(days=self.max_days_per_chunk - 1), end_date)
            
            self.logger.info(f"Processing chunk: {current_date.date()} to {chunk_end.date()}")
            
            try:
                # Fetch chunk
                chunk_conversations = await self.intercom_service.fetch_conversations_by_date_range(
                    current_date, chunk_end, max_pages
                )
                
                # Debug: Check actual date range of fetched chunk
                if chunk_conversations:
                    actual_dates = [datetime.fromtimestamp(c.get('created_at')) for c in chunk_conversations if c.get('created_at')]
                    if actual_dates:
                        min_date = min(actual_dates)
                        max_date = max(actual_dates)
                        self.logger.info(f"📅 Chunk actual dates: {min_date.date()} to {max_date.date()}")
                        
                        # Check if dates are outside requested range
                        if min_date.date() < current_date.date() or max_date.date() > chunk_end.date():
                            self.logger.warning(f"⚠️  API returned conversations outside chunk range!")
                            self.logger.warning(f"   Requested: {current_date.date()} to {chunk_end.date()}")
                            self.logger.warning(f"   Received: {min_date.date()} to {max_date.date()}")
                
                all_conversations.extend(chunk_conversations)
                processed_days += (chunk_end - current_date).days + 1
                
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
                
            except Exception as e:
                self.logger.error(f"Chunk fetch failed for {current_date.date()}-{chunk_end.date()}: {e}")
                
                # Decide whether to continue or fail
                if len(all_conversations) > 0:
                    self.logger.warning(f"Continuing with {len(all_conversations)} conversations already fetched")
                    break
                else:
                    self.logger.error("No conversations fetched, failing")
                    raise FetchError(f"Failed to fetch chunk {current_date.date()}-{chunk_end.date()}: {e}") from e
        
        # Final verification of all fetched data
        if all_conversations:
            all_dates = [datetime.fromtimestamp(c.get('created_at')) for c in all_conversations if c.get('created_at')]
            if all_dates:
                final_min = min(all_dates)
                final_max = max(all_dates)
                self.logger.info(f"📊 FINAL: Fetched {len(all_conversations)} conversations")
                self.logger.info(f"📅 FINAL: Date range {final_min.date()} to {final_max.date()}")
                self.logger.info(f"   Requested: {start_date.date()} to {end_date.date()}")
        else:
            self.logger.info(f"Daily chunking completed: {len(all_conversations)} total conversations")
        
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
                    current_date, chunk_end, max_pages
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
        
        # Calculate date range
        dates = [conv.get('created_at') for conv in conversations if conv.get('created_at')]
        if dates:
            min_date = min(dates)
            max_date = max(dates)
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
        
        stats = {
            "total_conversations": len(conversations),
            "date_range": {
                "start": min_date,
                "end": max_date
            },
            "conversation_states": states,
            "languages": languages,
            "avg_conversations_per_day": len(conversations) / max(1, (max_date - min_date).days + 1) if min_date and max_date else 0
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






