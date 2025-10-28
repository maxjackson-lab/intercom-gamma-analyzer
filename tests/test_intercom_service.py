"""
Unit tests for Intercom SDK service.
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, MagicMock, patch

from src.services.intercom_sdk_service import IntercomSDKService


class MockAsyncPager:
    """Mock AsyncPager for testing."""
    
    def __init__(self, items):
        self.items = items
        self._index = 0
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self._index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self._index]
        self._index += 1
        return item
    
    async def iter_pages(self):
        """Simulate iterating pages."""
        class MockPage:
            def __init__(self, items):
                self.items = items
        
        yield MockPage(self.items)


class TestIntercomSDKService:
    """Test cases for Intercom SDK service."""
    
    def test_initialization(self):
        """Test service initialization."""
        service = IntercomSDKService()
        
        assert service.access_token is not None
        assert service.base_url == "https://api.intercom.io"
        assert service.timeout == 60
        assert service.client is not None
        assert hasattr(service.client, 'conversations')
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test successful connection test."""
        service = IntercomSDKService()
        
        with patch.object(service.client.admins, 'identify', new_callable=AsyncMock) as mock_identify:
            mock_identify.return_value = {"type": "admin", "id": "test"}
            
            result = await service.test_connection()
            
            assert result is True
            mock_identify.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        """Test connection test failure."""
        from intercom.core.api_error import ApiError
        
        service = IntercomSDKService()
        
        with patch.object(service.client.admins, 'identify', new_callable=AsyncMock) as mock_identify:
            mock_identify.side_effect = ApiError(status_code=401, body={"errors": [{"message": "Unauthorized"}]})
            
            with pytest.raises(ApiError):
                await service.test_connection()
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_by_date_range_success(self):
        """Test successful conversation fetching."""
        service = IntercomSDKService()
        
        # Mock conversation data
        mock_conversations = [
            Mock(id="conv_1", created_at=1699123456, state="closed"),
            Mock(id="conv_2", created_at=1699123457, state="open")
        ]
        
        mock_pager = MockAsyncPager(mock_conversations)
        
        with patch.object(service.client.conversations, 'search', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_pager
            
            # Mock _model_to_dict
            service._model_to_dict = Mock(side_effect=lambda x: {
                'id': x.id,
                'created_at': x.created_at,
                'state': x.state
            })
            
            # Mock enrichment to return conversations as-is
            service._enrich_conversations_with_contact_details = AsyncMock(
                side_effect=lambda convs: convs
            )
            
            start_date = datetime(2023, 11, 1, tzinfo=timezone.utc)
            end_date = datetime(2023, 11, 2, tzinfo=timezone.utc)
            
            conversations = await service.fetch_conversations_by_date_range(start_date, end_date)
            
            assert len(conversations) == 2
            assert conversations[0]["id"] == "conv_1"
            assert conversations[1]["id"] == "conv_2"
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_with_max_conversations(self):
        """Test conversation fetching with max limit."""
        service = IntercomSDKService()
        
        # Mock more conversations than limit
        mock_conversations = [
            Mock(id=f"conv_{i}", created_at=1699123456 + i, state="closed")
            for i in range(10)
        ]
        
        mock_pager = MockAsyncPager(mock_conversations)
        
        with patch.object(service.client.conversations, 'search', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_pager
            
            service._model_to_dict = Mock(side_effect=lambda x: {
                'id': x.id,
                'created_at': x.created_at,
                'state': x.state
            })
            
            service._enrich_conversations_with_contact_details = AsyncMock(
                side_effect=lambda convs: convs
            )
            
            start_date = datetime(2023, 11, 1, tzinfo=timezone.utc)
            end_date = datetime(2023, 11, 2, tzinfo=timezone.utc)
            
            conversations = await service.fetch_conversations_by_date_range(
                start_date, end_date, max_conversations=5
            )
            
            assert len(conversations) == 5
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_by_query_text_search(self):
        """Test conversation fetching by text search query."""
        service = IntercomSDKService()
        
        mock_conversations = [
            Mock(id="conv_1", created_at=1699123456, state="closed")
        ]
        
        with patch.object(service, '_fetch_with_query', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [{'id': 'conv_1', 'created_at': 1699123456, 'state': 'closed'}]
            
            conversations = await service.fetch_conversations_by_query(
                "text_search", custom_query="billing issue"
            )
            
            assert len(conversations) == 1
            mock_fetch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_by_query_invalid(self):
        """Test conversation fetching with invalid query type."""
        service = IntercomSDKService()
        
        with pytest.raises(ValueError, match="Invalid query type"):
            await service.fetch_conversations_by_query("invalid_type")
    
    @pytest.mark.asyncio
    async def test_get_conversation_count(self):
        """Test getting conversation count."""
        from intercom.types import MultipleFilterSearchRequest
        
        service = IntercomSDKService()
        
        # Mock page with items
        mock_items = [Mock() for _ in range(50)]
        mock_pager = MockAsyncPager(mock_items)
        
        with patch.object(service.client.conversations, 'search', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_pager
            
            query = MultipleFilterSearchRequest(operator="AND", value=[])
            count = await service.get_conversation_count(query)
            
            assert count == 50
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test API error handling."""
        from intercom.core.api_error import ApiError
        
        service = IntercomSDKService()
        
        with patch.object(service.client.conversations, 'search', new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = ApiError(status_code=400, body={"errors": [{"message": "Bad Request"}]})
            
            start_date = datetime(2023, 11, 1, tzinfo=timezone.utc)
            end_date = datetime(2023, 11, 2, tzinfo=timezone.utc)
            
            with pytest.raises(ApiError):
                await service.fetch_conversations_by_date_range(start_date, end_date)
    
    @pytest.mark.asyncio
    async def test_normalize_and_filter_by_date(self):
        """Test date normalization and filtering."""
        service = IntercomSDKService()
        
        conversations = [
            {'id': 'conv_1', 'created_at': 1699123456},  # Unix timestamp
            {'id': 'conv_2', 'created_at': datetime(2023, 11, 5, tzinfo=timezone.utc)},  # datetime
            {'id': 'conv_3', 'created_at': 1699209856},  # Outside range
        ]
        
        start_date = datetime(2023, 11, 4, tzinfo=timezone.utc)
        end_date = datetime(2023, 11, 5, tzinfo=timezone.utc)
        
        filtered = service._normalize_and_filter_by_date(conversations, start_date, end_date)
        
        # Should have 2 conversations in range
        assert len(filtered) == 2
        # All created_at should be datetime objects
        assert all(isinstance(conv['created_at'], datetime) for conv in filtered)
    
    def test_model_to_dict(self):
        """Test model to dict conversion."""
        service = IntercomSDKService()
        
        # Test with Pydantic v2 style (model_dump)
        class MockModel:
            def model_dump(self, exclude_none=False):
                return {'id': '123', 'name': 'test'}
        
        result = service._model_to_dict(MockModel())
        assert result == {'id': '123', 'name': 'test'}
        
        # Test with Pydantic v1 style (dict)
        class MockModelV1:
            def dict(self, exclude_none=False):
                return {'id': '456', 'name': 'testv1'}
        
        result = service._model_to_dict(MockModelV1())
        assert result == {'id': '456', 'name': 'testv1'}
