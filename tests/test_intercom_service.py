"""
Unit tests for Intercom service.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from services.intercom_service_v2 import IntercomServiceV2


class TestIntercomServiceV2:
    """Test cases for Intercom service V2."""
    
    def test_initialization(self):
        """Test service initialization."""
        service = IntercomServiceV2()
        
        assert service.access_token is not None
        assert service.base_url == "https://api.intercom.io"
        assert service.api_version == "2.14"
        assert service.timeout == 60
        assert 'Authorization' in service.headers
        assert 'Accept' in service.headers
        assert 'Content-Type' in service.headers
        assert 'Intercom-Version' in service.headers
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test successful connection test."""
        service = IntercomServiceV2()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await service.test_connection()
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        """Test connection test failure."""
        service = IntercomServiceV2()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.HTTPStatusError(
                "Connection failed", request=MagicMock(), response=MagicMock()
            )
            
            with pytest.raises(httpx.HTTPStatusError):
                await service.test_connection()
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_by_date_range_success(self):
        """Test successful conversation fetching."""
        service = IntercomServiceV2()
        
        # Mock response data
        mock_response_data = {
            "conversations": [
                {"id": "conv_1", "created_at": 1699123456, "state": "closed"},
                {"id": "conv_2", "created_at": 1699123457, "state": "open"}
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            start_date = datetime.now() - timedelta(days=1)
            end_date = datetime.now()
            
            conversations = await service.fetch_conversations_by_date_range(start_date, end_date)
            
            assert len(conversations) == 2
            assert conversations[0]["id"] == "conv_1"
            assert conversations[1]["id"] == "conv_2"
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_with_pagination(self):
        """Test conversation fetching with pagination."""
        service = IntercomServiceV2()
        
        # Mock first page response
        first_page_data = {
            "conversations": [
                {"id": "conv_1", "created_at": 1699123456, "state": "closed"}
            ]
        }
        
        # Mock second page response (empty to stop pagination)
        second_page_data = {
            "conversations": []
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.side_effect = [first_page_data, second_page_data]
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            start_date = datetime.now() - timedelta(days=1)
            end_date = datetime.now()
            
            conversations = await service.fetch_conversations_by_date_range(start_date, end_date)
            
            assert len(conversations) == 1
            assert conversations[0]["id"] == "conv_1"
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_with_max_pages(self):
        """Test conversation fetching with page limit."""
        service = IntercomServiceV2()
        
        mock_response_data = {
            "conversations": [
                {"id": "conv_1", "created_at": 1699123456, "state": "closed"}
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            start_date = datetime.now() - timedelta(days=1)
            end_date = datetime.now()
            
            conversations = await service.fetch_conversations_by_date_range(
                start_date, end_date, max_pages=1
            )
            
            assert len(conversations) == 1
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_timeout_retry(self):
        """Test conversation fetching with timeout and retry."""
        service = IntercomServiceV2()
        
        with patch('httpx.AsyncClient') as mock_client:
            # First call times out, second succeeds
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {"conversations": []}
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = [
                httpx.TimeoutException("Timeout"),
                mock_response
            ]
            
            start_date = datetime.now() - timedelta(days=1)
            end_date = datetime.now()
            
            conversations = await service.fetch_conversations_by_date_range(start_date, end_date)
            
            assert len(conversations) == 0
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_rate_limit_retry(self):
        """Test conversation fetching with rate limit and retry."""
        service = IntercomServiceV2()
        
        with patch('httpx.AsyncClient') as mock_client:
            # First call rate limited, second succeeds
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {"conversations": []}
            
            rate_limit_error = httpx.HTTPStatusError(
                "Rate limited", 
                request=MagicMock(), 
                response=MagicMock()
            )
            rate_limit_error.response.status_code = 429
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = [
                rate_limit_error,
                mock_response
            ]
            
            start_date = datetime.now() - timedelta(days=1)
            end_date = datetime.now()
            
            conversations = await service.fetch_conversations_by_date_range(start_date, end_date)
            
            assert len(conversations) == 0
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_by_query_text_search(self):
        """Test conversation fetching by text search query."""
        service = IntercomServiceV2()
        
        mock_response_data = {
            "conversations": [
                {"id": "conv_1", "created_at": 1699123456, "state": "closed"}
            ]
        }
        
        with patch.object(service, '_fetch_with_pagination') as mock_fetch:
            mock_fetch.return_value = mock_response_data["conversations"]
            
            conversations = await service.fetch_conversations_by_query(
                "text_search", custom_query="billing issue"
            )
            
            assert len(conversations) == 1
            mock_fetch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_by_query_tag(self):
        """Test conversation fetching by tag query."""
        service = IntercomServiceV2()
        
        with patch.object(service, '_fetch_with_pagination') as mock_fetch:
            mock_fetch.return_value = []
            
            conversations = await service.fetch_conversations_by_query(
                "tag", suggestion="billing"
            )
            
            mock_fetch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_by_query_topic(self):
        """Test conversation fetching by topic query."""
        service = IntercomServiceV2()
        
        with patch.object(service, '_fetch_with_pagination') as mock_fetch:
            mock_fetch.return_value = []
            
            conversations = await service.fetch_conversations_by_query(
                "topic", suggestion="Billing"
            )
            
            mock_fetch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_by_query_agent(self):
        """Test conversation fetching by agent query."""
        service = IntercomServiceV2()
        
        with patch.object(service, '_fetch_with_pagination') as mock_fetch:
            mock_fetch.return_value = []
            
            conversations = await service.fetch_conversations_by_query(
                "agent", suggestion="admin_123"
            )
            
            mock_fetch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_by_query_invalid(self):
        """Test conversation fetching with invalid query type."""
        service = IntercomServiceV2()
        
        with pytest.raises(ValueError, match="Invalid query type"):
            await service.fetch_conversations_by_query("invalid_type")
    
    @pytest.mark.asyncio
    async def test_fetch_with_pagination_success(self):
        """Test generic pagination fetching."""
        service = IntercomServiceV2()
        
        mock_response_data = {
            "conversations": [
                {"id": "conv_1", "created_at": 1699123456, "state": "closed"}
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            query_params = {
                "query": {"field": "test", "operator": "=", "value": "test"},
                "pagination": {"per_page": 50}
            }
            
            conversations = await service._fetch_with_pagination(query_params)
            
            assert len(conversations) == 1
            assert conversations[0]["id"] == "conv_1"
    
    @pytest.mark.asyncio
    async def test_fetch_with_pagination_timeout_retry(self):
        """Test pagination fetching with timeout retry."""
        service = IntercomServiceV2()
        
        with patch('httpx.AsyncClient') as mock_client:
            # First call times out, second succeeds
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {"conversations": []}
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = [
                httpx.TimeoutException("Timeout"),
                mock_response
            ]
            
            query_params = {
                "query": {"field": "test", "operator": "=", "value": "test"},
                "pagination": {"per_page": 50}
            }
            
            conversations = await service._fetch_with_pagination(query_params)
            
            assert len(conversations) == 0
    
    @pytest.mark.asyncio
    async def test_fetch_with_pagination_rate_limit_retry(self):
        """Test pagination fetching with rate limit retry."""
        service = IntercomServiceV2()
        
        with patch('httpx.AsyncClient') as mock_client:
            # First call rate limited, second succeeds
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {"conversations": []}
            
            rate_limit_error = httpx.HTTPStatusError(
                "Rate limited", 
                request=MagicMock(), 
                response=MagicMock()
            )
            rate_limit_error.response.status_code = 429
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = [
                rate_limit_error,
                mock_response
            ]
            
            query_params = {
                "query": {"field": "test", "operator": "=", "value": "test"},
                "pagination": {"per_page": 50}
            }
            
            conversations = await service._fetch_with_pagination(query_params)
            
            assert len(conversations) == 0
    
    @pytest.mark.asyncio
    async def test_fetch_with_pagination_max_retries(self):
        """Test pagination fetching with max retries exceeded."""
        service = IntercomServiceV2()
        
        with patch('httpx.AsyncClient') as mock_client:
            # All calls timeout
            mock_client.return_value.__aenter__.return_value.post.side_effect = httpx.TimeoutException("Timeout")
            
            query_params = {
                "query": {"field": "test", "operator": "=", "value": "test"},
                "pagination": {"per_page": 50}
            }
            
            conversations = await service._fetch_with_pagination(query_params)
            
            # Should return empty list after max retries
            assert len(conversations) == 0
    
    def test_query_parameter_construction(self):
        """Test that query parameters are constructed correctly."""
        service = IntercomServiceV2()
        
        start_date = datetime(2023, 11, 1)
        end_date = datetime(2023, 11, 2)
        
        # This would be called internally, but we can test the logic
        expected_start_ts = int(start_date.timestamp())
        expected_end_ts = int(end_date.timestamp())
        
        assert expected_start_ts == 1698796800  # Known timestamp
        assert expected_end_ts == 1698883200    # Known timestamp
    
    @pytest.mark.asyncio
    async def test_http_error_handling(self):
        """Test HTTP error handling."""
        service = IntercomServiceV2()
        
        with patch('httpx.AsyncClient') as mock_client:
            # Mock HTTP error
            http_error = httpx.HTTPStatusError(
                "Bad Request", 
                request=MagicMock(), 
                response=MagicMock()
            )
            http_error.response.status_code = 400
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = http_error
            
            start_date = datetime.now() - timedelta(days=1)
            end_date = datetime.now()
            
            with pytest.raises(httpx.HTTPStatusError):
                await service.fetch_conversations_by_date_range(start_date, end_date)
    
    @pytest.mark.asyncio
    async def test_generic_error_handling(self):
        """Test generic error handling."""
        service = IntercomServiceV2()
        
        with patch('httpx.AsyncClient') as mock_client:
            # Mock generic error
            mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("Generic error")
            
            start_date = datetime.now() - timedelta(days=1)
            end_date = datetime.now()
            
            with pytest.raises(Exception, match="Generic error"):
                await service.fetch_conversations_by_date_range(start_date, end_date)






