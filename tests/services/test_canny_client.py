"""
Unit tests for CannyClient.
"""

import pytest
import httpx
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from src.services.canny_client import CannyClient


@pytest.fixture
def mock_settings():
    """Mock settings for CannyClient."""
    with patch('src.services.canny_client.settings') as mock_settings:
        mock_settings.canny_api_key = "test_api_key"
        mock_settings.canny_base_url = "https://canny.io/api/v1"
        mock_settings.canny_timeout = 30
        mock_settings.canny_max_retries = 3
        yield mock_settings


@pytest.fixture
def canny_client(mock_settings):
    """Create CannyClient instance for testing."""
    return CannyClient()


@pytest.mark.asyncio
class TestCannyClient:
    """Test suite for CannyClient."""
    
    async def test_init_without_api_key(self):
        """Test that CannyClient raises error without API key."""
        with patch('src.services.canny_client.settings') as mock_settings:
            mock_settings.canny_api_key = None
            with pytest.raises(ValueError, match="CANNY_API_KEY is required"):
                CannyClient()
    
    async def test_test_connection_success(self, canny_client):
        """Test successful API connection."""
        mock_response = {
            'boards': [
                {'id': '1', 'name': 'Feature Requests'},
                {'id': '2', 'name': 'Bug Reports'}
            ]
        }
        
        with patch.object(canny_client, '_make_request_with_retry', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await canny_client.test_connection()
            
            assert result is True
            mock_request.assert_called_once_with("boards/list", {'apiKey': 'test_api_key'})
    
    async def test_test_connection_failure(self, canny_client):
        """Test API connection failure."""
        with patch.object(canny_client, '_make_request_with_retry', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.HTTPError("Connection failed")
            
            with pytest.raises(httpx.HTTPError):
                await canny_client.test_connection()
    
    async def test_fetch_boards_success(self, canny_client):
        """Test successful board fetching."""
        mock_response = {
            'boards': [
                {'id': '1', 'name': 'Feature Requests', 'postCount': 42},
                {'id': '2', 'name': 'Bug Reports', 'postCount': 15}
            ]
        }
        
        with patch.object(canny_client, '_make_request_with_retry', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            boards = await canny_client.fetch_boards()
            
            assert len(boards) == 2
            assert boards[0]['id'] == '1'
            assert boards[0]['name'] == 'Feature Requests'
            assert boards[1]['postCount'] == 15
    
    async def test_fetch_posts_basic(self, canny_client):
        """Test basic post fetching without filters."""
        mock_response = {
            'posts': [
                {
                    'id': 'post1',
                    'title': 'Add dark mode',
                    'score': 234,
                    'status': 'planned'
                },
                {
                    'id': 'post2',
                    'title': 'Export to CSV',
                    'score': 156,
                    'status': 'open'
                }
            ]
        }
        
        with patch.object(canny_client, '_make_request_with_retry', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            posts = await canny_client.fetch_posts()
            
            assert len(posts) == 2
            assert posts[0]['id'] == 'post1'
            assert posts[1]['score'] == 156
            mock_request.assert_called_once()
    
    async def test_fetch_posts_with_date_range(self, canny_client):
        """Test post fetching with date range."""
        start_date = datetime(2024, 10, 1)
        end_date = datetime(2024, 10, 31)
        
        mock_response = {'posts': []}
        
        with patch.object(canny_client, '_make_request_with_retry', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            await canny_client.fetch_posts(
                start_date=start_date,
                end_date=end_date
            )
            
            call_args = mock_request.call_args[0][1]
            assert 'createdAfter' in call_args
            assert 'createdBefore' in call_args
            assert call_args['createdAfter'] == int(start_date.timestamp())
            assert call_args['createdBefore'] == int(end_date.timestamp())
    
    async def test_fetch_posts_with_board_id(self, canny_client):
        """Test post fetching with board ID filter."""
        mock_response = {'posts': []}
        
        with patch.object(canny_client, '_make_request_with_retry', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            await canny_client.fetch_posts(board_id='board123')
            
            call_args = mock_request.call_args[0][1]
            assert call_args['boardID'] == 'board123'
    
    async def test_fetch_comments(self, canny_client):
        """Test fetching comments for a post."""
        post_id = 'post123'
        mock_response = {
            'comments': [
                {'id': 'comment1', 'value': 'Great idea!'},
                {'id': 'comment2', 'value': 'I need this too'}
            ]
        }
        
        with patch.object(canny_client, '_make_request_with_retry', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            comments = await canny_client.fetch_comments(post_id)
            
            assert len(comments) == 2
            assert comments[0]['id'] == 'comment1'
            mock_request.assert_called_once_with(
                "comments/list",
                {'apiKey': 'test_api_key', 'postID': post_id}
            )
    
    async def test_fetch_votes(self, canny_client):
        """Test fetching votes for a post."""
        post_id = 'post123'
        mock_response = {
            'votes': [
                {'id': 'vote1', 'voter': {'name': 'User1'}},
                {'id': 'vote2', 'voter': {'name': 'User2'}},
                {'id': 'vote3', 'voter': {'name': 'User3'}}
            ]
        }
        
        with patch.object(canny_client, '_make_request_with_retry', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            votes = await canny_client.fetch_votes(post_id)
            
            assert len(votes) == 3
            assert votes[0]['id'] == 'vote1'
    
    async def test_make_request_with_retry_success_first_attempt(self, canny_client):
        """Test successful request on first attempt."""
        mock_response_data = {'success': True, 'data': 'test'}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_client.post.return_value = mock_response
            
            result = await canny_client._make_request_with_retry(
                "test/endpoint",
                {'apiKey': 'test_key'}
            )
            
            assert result == mock_response_data
            mock_client.post.assert_called_once()
    
    async def test_make_request_with_retry_rate_limit(self, canny_client):
        """Test retry on rate limit (429)."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # First call returns 429, second succeeds
            mock_response_429 = MagicMock()
            mock_response_429.status_code = 429
            mock_response_429.headers = {'Retry-After': '1'}
            
            mock_response_success = MagicMock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {'success': True}
            
            mock_client.post.side_effect = [mock_response_429, mock_response_success]
            
            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await canny_client._make_request_with_retry(
                    "test/endpoint",
                    {'apiKey': 'test_key'}
                )
            
            assert result == {'success': True}
            assert mock_client.post.call_count == 2
    
    async def test_make_request_with_retry_timeout(self, canny_client):
        """Test retry on timeout."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # First two calls timeout, third succeeds
            mock_client.post.side_effect = [
                httpx.TimeoutException("Timeout"),
                httpx.TimeoutException("Timeout"),
                MagicMock(status_code=200, json=lambda: {'success': True})
            ]
            
            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await canny_client._make_request_with_retry(
                    "test/endpoint",
                    {'apiKey': 'test_key'}
                )
            
            assert result == {'success': True}
            assert mock_client.post.call_count == 3
    
    async def test_make_request_with_retry_max_retries_exceeded(self, canny_client):
        """Test failure after max retries."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # All attempts timeout
            mock_client.post.side_effect = httpx.TimeoutException("Timeout")
            
            with patch('asyncio.sleep', new_callable=AsyncMock):
                with pytest.raises(httpx.TimeoutException):
                    await canny_client._make_request_with_retry(
                        "test/endpoint",
                        {'apiKey': 'test_key'}
                    )
            
            assert mock_client.post.call_count == 3  # max_retries
    
    async def test_make_request_with_retry_4xx_no_retry(self, canny_client):
        """Test that 4xx errors (except 429) don't retry."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not found", request=MagicMock(), response=mock_response
            )
            mock_client.post.return_value = mock_response
            
            with pytest.raises(httpx.HTTPStatusError):
                await canny_client._make_request_with_retry(
                    "test/endpoint",
                    {'apiKey': 'test_key'}
                )
            
            # Should only attempt once (no retries for 4xx)
            mock_client.post.assert_called_once()
    
    async def test_fetch_posts_by_date_range(self, canny_client):
        """Test fetching posts with enrichment (comments and votes)."""
        start_date = datetime(2024, 10, 1)
        end_date = datetime(2024, 10, 31)
        
        mock_posts = {
            'posts': [
                {'id': 'post1', 'title': 'Test Post 1'},
                {'id': 'post2', 'title': 'Test Post 2'}
            ]
        }
        mock_comments = {'comments': [{'id': 'comment1'}]}
        mock_votes = {'votes': [{'id': 'vote1'}, {'id': 'vote2'}]}
        
        with patch.object(canny_client, '_make_request_with_retry', new_callable=AsyncMock) as mock_request:
            # Mock responses for posts, comments (2x), votes (2x)
            mock_request.side_effect = [
                mock_posts,
                mock_comments,  # post1 comments
                mock_votes,     # post1 votes
                mock_comments,  # post2 comments
                mock_votes      # post2 votes
            ]
            
            with patch('asyncio.sleep', new_callable=AsyncMock):
                posts = await canny_client.fetch_posts_by_date_range(
                    start_date=start_date,
                    end_date=end_date,
                    include_comments=True,
                    include_votes=True
                )
            
            assert len(posts) == 2
            assert 'comments' in posts[0]
            assert 'votes' in posts[0]
            assert len(posts[0]['votes']) == 2
    
    async def test_fetch_all_boards_posts(self, canny_client):
        """Test fetching posts from all boards."""
        mock_boards = {
            'boards': [
                {'id': 'board1', 'name': 'Features'},
                {'id': 'board2', 'name': 'Bugs'}
            ]
        }
        
        with patch.object(canny_client, 'fetch_boards', new_callable=AsyncMock) as mock_fetch_boards:
            with patch.object(canny_client, 'fetch_posts_by_date_range', new_callable=AsyncMock) as mock_fetch_posts:
                mock_fetch_boards.return_value = mock_boards['boards']
                mock_fetch_posts.return_value = [{'id': 'post1'}]
                
                start_date = datetime(2024, 10, 1)
                end_date = datetime(2024, 10, 31)
                
                result = await canny_client.fetch_all_boards_posts(
                    start_date=start_date,
                    end_date=end_date
                )
                
                assert 'board1' in result
                assert 'board2' in result
                assert mock_fetch_posts.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

