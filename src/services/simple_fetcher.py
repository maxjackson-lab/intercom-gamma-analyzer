"""
SIMPLE FETCHER - NO CLEVERNESS, JUST WORKS
Replaces the over-engineered chunked_fetcher.py
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from src.services.intercom_sdk_service import IntercomSDKService

logger = logging.getLogger(__name__)


class SimpleFetcher:
    """
    Dead simple fetcher - just fetch conversations, no timeout nonsense.
    Like the pre-SDK version that WORKED.
    """
    
    def __init__(self):
        self.intercom_service = IntercomSDKService()
        self.logger = logging.getLogger(__name__)
        self.logger.info("SimpleFetcher initialized - no timeouts, just fetch until done")
    
    async def fetch_conversations(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict]:
        """
        Fetch conversations. Period. No chunking, no timeouts, no bullshit.
        
        The SDK handles:
        - Pagination (50 per page)
        - Rate limiting (5 req/sec)
        - Retries
        
        We just call it and wait for it to finish.
        """
        self.logger.info(f"Fetching conversations from {start_date.date()} to {end_date.date()}")
        
        try:
            # Just fetch. That's it.
            conversations = await self.intercom_service.fetch_conversations_by_date_range(
                start_date,
                end_date
            )
            
            self.logger.info(f"✅ Fetched {len(conversations)} conversations")
            return conversations
            
        except Exception as e:
            self.logger.error(f"❌ Fetch failed: {e}")
            raise

