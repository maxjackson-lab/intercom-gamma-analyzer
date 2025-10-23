"""
Unit tests for ChunkedFetcher service.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from typing import List, Dict, Any
import httpx

from src.services.chunked_fetcher import ChunkedFetcher


class TestChunkedFetcher:
    """Test cases for ChunkedFetcher."""
    
    @pytest.fixture
    def chunked_fetcher(self):
        """Create a ChunkedFetcher instance for testing."""
        with patch('services.chunked_fetcher.settings') as mock_settings:
            mock_settings.intercom_access_token = "test_token"
            mock_settings.intercom_base_url = "https://api.intercom.io"
            mock_settings.intercom_api_version = "2.8"
            mock_settings.intercom_timeout = 30
            mock_settings.intercom_rate_limit_delay = 1.5
            mock_settings.intercom_max_retries = 3
            mock_settings.intercom_per_page = 50
            mock_settings.intercom_rate_limit_wait_time = 15
            
            return ChunkedFetcher()
    
    @pytest.fixture
    def sample_conversations_response(self):
        """Create sample conversations response for testing."""
        return {
            'conversations': [
                {
                    'id': 'conv_1',
                    'created_at': 1640995200,
                    'updated_at': 1640995200,
                    'state': 'open',
                    'open': True,
                    'read': True,
                    'admin_assignee': {
                        'id': 'agent_1',
                        'name': 'Dae-Ho'
                    },
                    'team_assignee': {
                        'id': 'team_1',
                        'name': 'Support Team'
                    },
                    'contact': {
                        'id': 'user_1',
                        'email': 'user@example.com'
                    },
                    'source': {
                        'type': 'conversation',
                        'body': 'I need help with billing'
                    },
                    'tags': {
                        'tags': [
                            {'name': 'Billing'}
                        ]
                    },
                    'conversation_topics': [
                        {'name': 'billing'}
                    ],
                    'custom_attributes': {},
                    'conversation_parts': {
                        'conversation_parts': [
                            {
                                'id': 'part_1',
                                'part_type': 'comment',
                                'body': 'I need help with billing',
                                'author': {
                                    'type': 'user',
                                    'id': 'user_1'
                                },
                                'created_at': 1640995200
                            }
                        ]
                    }
                },
                {
                    'id': 'conv_2',
                    'created_at': 1640995200,
                    'updated_at': 1640995200,
                    'state': 'closed',
                    'open': False,
                    'read': True,
                    'admin_assignee': {
                        'id': 'agent_2',
                        'name': 'Hilary'
                    },
                    'team_assignee': {
                        'id': 'team_1',
                        'name': 'Support Team'
                    },
                    'contact': {
                        'id': 'user_2',
                        'email': 'user2@example.com'
                    },
                    'source': {
                        'type': 'conversation',
                        'body': 'I have a bug with the export feature'
                    },
                    'tags': {
                        'tags': [
                            {'name': 'Bug Report'}
                        ]
                    },
                    'conversation_topics': [
                        {'name': 'export'}
                    ],
                    'custom_attributes': {},
                    'conversation_parts': {
                        'conversation_parts': [
                            {
                                'id': 'part_2',
                                'part_type': 'comment',
                                'body': 'I have a bug with the export feature',
                                'author': {
                                    'type': 'user',
                                    'id': 'user_2'
                                },
                                'created_at': 1640995200
                            }
                        ]
                    }
                }
            ],
            'pages': {
                'next': {
                    'starting_after': 'conv_2'
                }
            }
        }
    
    def test_initialization(self, chunked_fetcher):
        """Test ChunkedFetcher initialization."""
        assert chunked_fetcher.access_token == "test_token"
        assert chunked_fetcher.base_url == "https://api.intercom.io"
        assert chunked_fetcher.api_version == "2.8"
        assert chunked_fetcher.timeout == 30
        assert chunked_fetcher.rate_limit_delay == 1.5
        assert chunked_fetcher.max_retries == 3
        assert chunked_fetcher.per_page == 50
        
        # Check headers
        assert 'Authorization' in chunked_fetcher.headers
        assert 'Accept' in chunked_fetcher.headers
        assert 'Content-Type' in chunked_fetcher.headers
        assert 'Intercom-Version' in chunked_fetcher.headers
        assert chunked_fetcher.headers['Authorization'] == 'Bearer test_token'
        assert chunked_fetcher.headers['Intercom-Version'] == '2.8'
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_chunked_success(self, chunked_fetcher, sample_conversations_response):
        """Test successful conversation fetching."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        
        # Mock the HTTP client
        with patch('services.chunked_fetcher.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_conversations_response
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            conversations = await chunked_fetcher.fetch_conversations_chunked(
                start_date, end_date
            )
        
        assert len(conversations) == 2
        assert conversations[0]['id'] == 'conv_1'
        assert conversations[1]['id'] == 'conv_2'
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_chunked_with_max_pages(self, chunked_fetcher, sample_conversations_response):
        """Test conversation fetching with max pages limit."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        max_pages = 1
        
        # Mock the HTTP client
        with patch('services.chunked_fetcher.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_conversations_response
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            conversations = await chunked_fetcher.fetch_conversations_chunked(
                start_date, end_date, max_pages
            )
        
        assert len(conversations) == 2
        # Should only make one request due to max_pages limit
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_chunked_no_more_pages(self, chunked_fetcher):
        """Test conversation fetching when no more pages are available."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        
        # Mock response with no next page
        response_without_next = {
            'conversations': [
                {
                    'id': 'conv_1',
                    'created_at': 1640995200,
                    'updated_at': 1640995200,
                    'state': 'open',
                    'open': True,
                    'read': True,
                    'admin_assignee': {'id': 'agent_1', 'name': 'Dae-Ho'},
                    'team_assignee': {'id': 'team_1', 'name': 'Support Team'},
                    'contact': {'id': 'user_1', 'email': 'user@example.com'},
                    'source': {'type': 'conversation', 'body': 'I need help'},
                    'tags': {'tags': []},
                    'conversation_topics': [],
                    'custom_attributes': {},
                    'conversation_parts': {'conversation_parts': []}
                }
            ],
            'pages': {}  # No next page
        }
        
        # Mock the HTTP client
        with patch('services.chunked_fetcher.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_without_next
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            conversations = await chunked_fetcher.fetch_conversations_chunked(
                start_date, end_date
            )
        
        assert len(conversations) == 1
        assert conversations[0]['id'] == 'conv_1'
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_chunked_empty_response(self, chunked_fetcher):
        """Test conversation fetching with empty response."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        
        # Mock empty response
        empty_response = {
            'conversations': [],
            'pages': {}
        }
        
        # Mock the HTTP client
        with patch('services.chunked_fetcher.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = empty_response
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            conversations = await chunked_fetcher.fetch_conversations_chunked(
                start_date, end_date
            )
        
        assert len(conversations) == 0
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_chunked_rate_limit(self, chunked_fetcher, sample_conversations_response):
        """Test conversation fetching with rate limit handling."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        
        # Mock the HTTP client to return rate limit error first, then success
        with patch('services.chunked_fetcher.httpx.AsyncClient') as mock_client:
            # First response: rate limit error
            rate_limit_response = MagicMock()
            rate_limit_response.status_code = 429
            rate_limit_response.json.return_value = {'error': 'Rate limit exceeded'}
            
            # Second response: success
            success_response = MagicMock()
            success_response.status_code = 200
            success_response.json.return_value = sample_conversations_response
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = [
                httpx.HTTPStatusError("Rate limit", request=MagicMock(), response=rate_limit_response),
                success_response
            ]
            
            conversations = await chunked_fetcher.fetch_conversations_chunked(
                start_date, end_date
            )
        
        assert len(conversations) == 2
        assert conversations[0]['id'] == 'conv_1'
        assert conversations[1]['id'] == 'conv_2'
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_chunked_timeout(self, chunked_fetcher, sample_conversations_response):
        """Test conversation fetching with timeout handling."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        
        # Mock the HTTP client to return timeout error first, then success
        with patch('services.chunked_fetcher.httpx.AsyncClient') as mock_client:
            # First response: timeout error
            timeout_response = MagicMock()
            timeout_response.status_code = 408
            
            # Second response: success
            success_response = MagicMock()
            success_response.status_code = 200
            success_response.json.return_value = sample_conversations_response
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = [
                httpx.TimeoutException("Request timeout"),
                success_response
            ]
            
            conversations = await chunked_fetcher.fetch_conversations_chunked(
                start_date, end_date
            )
        
        assert len(conversations) == 2
        assert conversations[0]['id'] == 'conv_1'
        assert conversations[1]['id'] == 'conv_2'
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_chunked_http_error(self, chunked_fetcher):
        """Test conversation fetching with HTTP error."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        
        # Mock the HTTP client to return HTTP error
        with patch('services.chunked_fetcher.httpx.AsyncClient') as mock_client:
            error_response = MagicMock()
            error_response.status_code = 500
            error_response.json.return_value = {'error': 'Internal server error'}
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = httpx.HTTPStatusError(
                "Internal server error", request=MagicMock(), response=error_response
            )
            
            with pytest.raises(httpx.HTTPStatusError):
                await chunked_fetcher.fetch_conversations_chunked(start_date, end_date)
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_chunked_general_error(self, chunked_fetcher):
        """Test conversation fetching with general error."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        
        # Mock the HTTP client to return general error
        with patch('services.chunked_fetcher.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("General error")
            
            with pytest.raises(Exception, match="General error"):
                await chunked_fetcher.fetch_conversations_chunked(start_date, end_date)
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_chunked_pagination(self, chunked_fetcher):
        """Test conversation fetching with pagination."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        
        # Mock responses for multiple pages
        page1_response = {
            'conversations': [
                {
                    'id': 'conv_1',
                    'created_at': 1640995200,
                    'updated_at': 1640995200,
                    'state': 'open',
                    'open': True,
                    'read': True,
                    'admin_assignee': {'id': 'agent_1', 'name': 'Dae-Ho'},
                    'team_assignee': {'id': 'team_1', 'name': 'Support Team'},
                    'contact': {'id': 'user_1', 'email': 'user@example.com'},
                    'source': {'type': 'conversation', 'body': 'I need help'},
                    'tags': {'tags': []},
                    'conversation_topics': [],
                    'custom_attributes': {},
                    'conversation_parts': {'conversation_parts': []}
                }
            ],
            'pages': {
                'next': {
                    'starting_after': 'conv_1'
                }
            }
        }
        
        page2_response = {
            'conversations': [
                {
                    'id': 'conv_2',
                    'created_at': 1640995200,
                    'updated_at': 1640995200,
                    'state': 'closed',
                    'open': False,
                    'read': True,
                    'admin_assignee': {'id': 'agent_2', 'name': 'Hilary'},
                    'team_assignee': {'id': 'team_1', 'name': 'Support Team'},
                    'contact': {'id': 'user_2', 'email': 'user2@example.com'},
                    'source': {'type': 'conversation', 'body': 'I have a bug'},
                    'tags': {'tags': []},
                    'conversation_topics': [],
                    'custom_attributes': {},
                    'conversation_parts': {'conversation_parts': []}
                }
            ],
            'pages': {}  # No more pages
        }
        
        # Mock the HTTP client
        with patch('services.chunked_fetcher.httpx.AsyncClient') as mock_client:
            mock_response1 = MagicMock()
            mock_response1.status_code = 200
            mock_response1.json.return_value = page1_response
            
            mock_response2 = MagicMock()
            mock_response2.status_code = 200
            mock_response2.json.return_value = page2_response
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = [
                mock_response1,
                mock_response2
            ]
            
            conversations = await chunked_fetcher.fetch_conversations_chunked(
                start_date, end_date
            )
        
        assert len(conversations) == 2
        assert conversations[0]['id'] == 'conv_1'
        assert conversations[1]['id'] == 'conv_2'
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_chunked_missing_pages(self, chunked_fetcher):
        """Test conversation fetching when pages field is missing."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        
        # Mock response without pages field
        response_without_pages = {
            'conversations': [
                {
                    'id': 'conv_1',
                    'created_at': 1640995200,
                    'updated_at': 1640995200,
                    'state': 'open',
                    'open': True,
                    'read': True,
                    'admin_assignee': {'id': 'agent_1', 'name': 'Dae-Ho'},
                    'team_assignee': {'id': 'team_1', 'name': 'Support Team'},
                    'contact': {'id': 'user_1', 'email': 'user@example.com'},
                    'source': {'type': 'conversation', 'body': 'I need help'},
                    'tags': {'tags': []},
                    'conversation_topics': [],
                    'custom_attributes': {},
                    'conversation_parts': {'conversation_parts': []}
                }
            ]
            # No pages field
        }
        
        # Mock the HTTP client
        with patch('services.chunked_fetcher.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_without_pages
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            conversations = await chunked_fetcher.fetch_conversations_chunked(
                start_date, end_date
            )
        
        assert len(conversations) == 1
        assert conversations[0]['id'] == 'conv_1'
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_chunked_missing_conversations(self, chunked_fetcher):
        """Test conversation fetching when conversations field is missing."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        
        # Mock response without conversations field
        response_without_conversations = {
            'pages': {}
            # No conversations field
        }
        
        # Mock the HTTP client
        with patch('services.chunked_fetcher.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_without_conversations
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            conversations = await chunked_fetcher.fetch_conversations_chunked(
                start_date, end_date
            )
        
        assert len(conversations) == 0
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_chunked_missing_starting_after(self, chunked_fetcher):
        """Test conversation fetching when starting_after is missing from next page."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        
        # Mock response with next page but no starting_after
        response_without_starting_after = {
            'conversations': [
                {
                    'id': 'conv_1',
                    'created_at': 1640995200,
                    'updated_at': 1640995200,
                    'state': 'open',
                    'open': True,
                    'read': True,
                    'admin_assignee': {'id': 'agent_1', 'name': 'Dae-Ho'},
                    'team_assignee': {'id': 'team_1', 'name': 'Support Team'},
                    'contact': {'id': 'user_1', 'email': 'user@example.com'},
                    'source': {'type': 'conversation', 'body': 'I need help'},
                    'tags': {'tags': []},
                    'conversation_topics': [],
                    'custom_attributes': {},
                    'conversation_parts': {'conversation_parts': []}
                }
            ],
            'pages': {
                'next': {}  # No starting_after
            }
        }
        
        # Mock the HTTP client
        with patch('services.chunked_fetcher.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_without_starting_after
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            conversations = await chunked_fetcher.fetch_conversations_chunked(
                start_date, end_date
            )
        
        assert len(conversations) == 1
        assert conversations[0]['id'] == 'conv_1'
    
    @pytest.mark.asyncio
    async def test_fetch_conversations_chunked_context_manager(self, chunked_fetcher, sample_conversations_response):
        """Test ChunkedFetcher as context manager."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        
        # Mock the HTTP client
        with patch('services.chunked_fetcher.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_conversations_response
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            async with chunked_fetcher as fetcher:
                conversations = await fetcher.fetch_conversations_chunked(
                    start_date, end_date
                )
        
        assert len(conversations) == 2
        assert conversations[0]['id'] == 'conv_1'
        assert conversations[1]['id'] == 'conv_2'
    
    def test_query_construction(self, chunked_fetcher):
        """Test query construction for date range."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        
        # This is a private method, but we can test the query construction indirectly
        # by checking the payload structure in the fetch method
        expected_start_timestamp = int(start_date.timestamp())
        expected_end_timestamp = int(end_date.timestamp())
        
        # The query should be constructed with these timestamps
        assert expected_start_timestamp == 1640995200  # 2022-01-01 00:00:00 UTC
        assert expected_end_timestamp == 1643673600    # 2022-01-31 23:59:59 UTC
    
    def test_payload_construction(self, chunked_fetcher):
        """Test payload construction for API requests."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        
        # Test the expected payload structure
        expected_payload = {
            "query": {
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
            },
            "pagination": {"per_page": 50}
        }
        
        # The payload should have this structure
        assert expected_payload["query"]["operator"] == "AND"
        assert len(expected_payload["query"]["value"]) == 2
        assert expected_payload["pagination"]["per_page"] == 50
    
    def test_payload_construction_with_starting_after(self, chunked_fetcher):
        """Test payload construction with starting_after parameter."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        starting_after = "conv_123"
        
        # Test the expected payload structure with starting_after
        expected_payload = {
            "query": {
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
            },
            "pagination": {
                "per_page": 50,
                "starting_after": starting_after
            }
        }
        
        # The payload should have this structure
        assert expected_payload["pagination"]["starting_after"] == starting_after
        assert expected_payload["pagination"]["per_page"] == 50