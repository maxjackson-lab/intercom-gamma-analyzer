"""Regression tests for ChunkedFetcher resilience features."""
import asyncio
from datetime import datetime, timedelta
import pytest
from src.services.chunked_fetcher import ChunkedFetcher, FetchError


class StubIntercomService:
    """Stub service for testing."""
    def __init__(self, responses, delay: float = 0.0):
        self._responses = responses
        self._delay = delay
        self.calls = []

    async def fetch_conversations_by_date_range(self, start_date, end_date, max_conversations=None):
        self.calls.append((start_date, end_date, max_conversations))
        if self._delay:
            await asyncio.sleep(self._delay)
        index = min(len(self.calls) - 1, len(self._responses) - 1)
        return list(self._responses[index])


@pytest.mark.asyncio
async def test_deduplication_across_chunks():
    """Test that duplicates are filtered across daily chunks."""
    responses = [
        [{'id': 'a'}, {'id': 'b'}],
        [{'id': 'b'}, {'id': 'c'}],
    ]
    service = StubIntercomService(responses)
    fetcher = ChunkedFetcher(intercom_service=service, enable_preprocessing=False, chunk_timeout=5)
    fetcher.max_days_per_chunk = 1

    start = datetime(2024, 1, 1)
    end = start + timedelta(days=1)

    conversations = await fetcher.fetch_conversations_chunked(start, end, max_conversations=10)
    assert len(conversations) == 3
    assert len({c['id'] for c in conversations}) == 3


@pytest.mark.asyncio
async def test_max_conversations_cap():
    """Test that max_conversations cap is enforced."""
    responses = [
        [{'id': 'a'}, {'id': 'b'}],
        [{'id': 'c'}, {'id': 'd'}],
    ]
    service = StubIntercomService(responses)
    fetcher = ChunkedFetcher(intercom_service=service, enable_preprocessing=False, chunk_timeout=5)
    fetcher.max_days_per_chunk = 1

    start = datetime(2024, 1, 1)
    end = start + timedelta(days=1)

    conversations = await fetcher.fetch_conversations_chunked(start, end, max_conversations=2)
    assert len(conversations) == 2


@pytest.mark.asyncio
async def test_timeout_raises_fetch_error():
    """Test that timeout raises FetchError."""
    service = StubIntercomService([[{'id': 'slow'}]], delay=0.2)
    fetcher = ChunkedFetcher(intercom_service=service, enable_preprocessing=False, chunk_timeout=0.05)

    start = datetime(2024, 1, 1)

    with pytest.raises(FetchError, match="timed out"):
        await fetcher.fetch_conversations_chunked(start, start)

