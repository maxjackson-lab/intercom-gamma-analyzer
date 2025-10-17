"""
Unit tests for GammaClient service.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import httpx
import asyncio

from services.gamma_client import GammaClient, GammaAPIError


class TestGammaClient:
    """Test cases for GammaClient."""
    
    @pytest.fixture
    def gamma_client(self):
        """Create a GammaClient instance for testing."""
        with patch('services.gamma_client.settings') as mock_settings:
            mock_settings.gamma_api_key = "test_gamma_key"
            mock_settings.intercom_workspace_id = "test_workspace_id"
            
            return GammaClient()
    
    @pytest.fixture
    def mock_response(self):
        """Create a mock HTTP response."""
        response = Mock()
        response.json.return_value = {
            'generationId': 'test_generation_id',
            'status': 'completed',
            'gammaUrl': 'https://gamma.app/p/test_url'
        }
        response.raise_for_status.return_value = None
        return response
    
    @pytest.mark.asyncio
    async def test_gamma_client_initialization(self, gamma_client):
        """Test GammaClient initializes with correct headers."""
        assert gamma_client.api_key == "test_gamma_key"
        assert gamma_client.base_url == "https://public-api.gamma.app/v0.2"
        assert gamma_client.headers['X-API-KEY'] == "test_gamma_key"
        assert gamma_client.headers['Content-Type'] == 'application/json'
    
    @pytest.mark.asyncio
    async def test_generate_presentation_success(self, gamma_client, mock_response):
        """Test successful presentation generation."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await gamma_client.generate_presentation(
                input_text="Test presentation content",
                format="presentation",
                num_cards=10
            )
            
            assert result == "test_generation_id"
    
    @pytest.mark.asyncio
    async def test_generate_presentation_invalid_api_key(self, gamma_client):
        """Test handling of invalid API key."""
        gamma_client.api_key = None
        
        with pytest.raises(GammaAPIError, match="Gamma API key not provided"):
            await gamma_client.generate_presentation("Test content")
    
    @pytest.mark.asyncio
    async def test_generate_presentation_invalid_input_length(self, gamma_client):
        """Test handling of invalid input text length."""
        with pytest.raises(GammaAPIError, match="Input text must be 1-750,000 characters"):
            await gamma_client.generate_presentation("")  # Empty string
        
        with pytest.raises(GammaAPIError, match="Input text must be 1-750,000 characters"):
            await gamma_client.generate_presentation("x" * 750001)  # Too long
    
    @pytest.mark.asyncio
    async def test_generate_presentation_http_error(self, gamma_client):
        """Test handling of HTTP errors."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = "Bad Request"
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = httpx.HTTPStatusError(
                "Bad Request", request=Mock(), response=mock_response
            )
            
            with pytest.raises(GammaAPIError, match="Gamma API error 400"):
                await gamma_client.generate_presentation("Test content")
    
    @pytest.mark.asyncio
    async def test_get_generation_status_completed(self, gamma_client, mock_response):
        """Test polling when generation completes."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await gamma_client.get_generation_status("test_generation_id")
            
            assert result['status'] == 'completed'
            assert result['gammaUrl'] == 'https://gamma.app/p/test_url'
    
    @pytest.mark.asyncio
    async def test_get_generation_status_failed(self, gamma_client):
        """Test handling of failed generation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'generationId': 'test_generation_id',
            'status': 'failed',
            'error': 'Generation failed'
        }
        mock_response.raise_for_status.return_value = None
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await gamma_client.get_generation_status("test_generation_id")
            
            assert result['status'] == 'failed'
            assert result['error'] == 'Generation failed'
    
    @pytest.mark.asyncio
    async def test_poll_generation_success(self, gamma_client):
        """Test successful polling with completion."""
        # Mock the get_generation_status method to return completed status
        with patch.object(gamma_client, 'get_generation_status') as mock_get_status:
            mock_get_status.return_value = {
                'generationId': 'test_generation_id',
                'status': 'completed',
                'gammaUrl': 'https://gamma.app/p/test_url'
            }
            
            result = await gamma_client.poll_generation("test_generation_id")
            
            assert result['status'] == 'completed'
            assert result['gammaUrl'] == 'https://gamma.app/p/test_url'
    
    @pytest.mark.asyncio
    async def test_poll_generation_failed(self, gamma_client):
        """Test polling when generation fails."""
        with patch.object(gamma_client, 'get_generation_status') as mock_get_status:
            mock_get_status.return_value = {
                'generationId': 'test_generation_id',
                'status': 'failed',
                'error': 'Generation failed'
            }
            
            with pytest.raises(GammaAPIError, match="Generation failed"):
                await gamma_client.poll_generation("test_generation_id")
    
    @pytest.mark.asyncio
    async def test_poll_generation_timeout(self, gamma_client):
        """Test polling timeout."""
        with patch.object(gamma_client, 'get_generation_status') as mock_get_status:
            mock_get_status.return_value = {
                'generationId': 'test_generation_id',
                'status': 'processing'
            }
            
            with pytest.raises(GammaAPIError, match="Generation polling timed out"):
                await gamma_client.poll_generation("test_generation_id", max_polls=2)
    
    @pytest.mark.asyncio
    async def test_poll_generation_with_exponential_backoff(self, gamma_client):
        """Test polling respects exponential backoff."""
        with patch.object(gamma_client, 'get_generation_status') as mock_get_status, \
             patch('asyncio.sleep') as mock_sleep:
            
            # First call returns processing, second returns completed
            mock_get_status.side_effect = [
                {'status': 'processing'},
                {'status': 'completed', 'gammaUrl': 'https://gamma.app/p/test_url'}
            ]
            
            result = await gamma_client.poll_generation("test_generation_id", max_polls=3)
            
            assert result['status'] == 'completed'
            # Verify sleep was called with exponential backoff
            mock_sleep.assert_called()
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self, gamma_client, mock_response):
        """Test successful connection test."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await gamma_client.test_connection()
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_test_connection_no_api_key(self, gamma_client):
        """Test connection test when no API key is provided."""
        gamma_client.api_key = None
        
        result = await gamma_client.test_connection()
        
        assert result is True  # Should return True and skip test
    
    @pytest.mark.asyncio
    async def test_generate_presentation_with_export(self, gamma_client, mock_response):
        """Test presentation generation with export format."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await gamma_client.generate_presentation(
                input_text="Test content",
                export_as="pdf"
            )
            
            assert result == "test_generation_id"
    
    @pytest.mark.asyncio
    async def test_generate_presentation_with_additional_instructions(self, gamma_client, mock_response):
        """Test presentation generation with additional instructions."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await gamma_client.generate_presentation(
                input_text="Test content",
                additional_instructions="Make it professional"
            )
            
            assert result == "test_generation_id"
    
    @pytest.mark.asyncio
    async def test_generate_presentation_with_image_options(self, gamma_client, mock_response):
        """Test presentation generation with image options."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            image_options = {
                'source': 'aiGenerated',
                'style': 'professional'
            }
            
            result = await gamma_client.generate_presentation(
                input_text="Test content",
                image_options=image_options
            )
            
            assert result == "test_generation_id"
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, gamma_client):
        """Test handling of 429 rate limit response."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.text = "Rate Limited"
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = httpx.HTTPStatusError(
                "Rate Limited", request=Mock(), response=mock_response
            )
            
            with pytest.raises(GammaAPIError, match="Gamma API error 429"):
                await gamma_client.generate_presentation("Test content")
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self, gamma_client):
        """Test handling of network errors."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = httpx.ConnectError("Network error")
            
            with pytest.raises(GammaAPIError, match="Failed to generate presentation"):
                await gamma_client.generate_presentation("Test content")
    
    @pytest.mark.asyncio
    async def test_invalid_response_format(self, gamma_client):
        """Test handling of invalid response format."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {}  # Missing generationId
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            with pytest.raises(GammaAPIError, match="No generationId returned from API"):
                await gamma_client.generate_presentation("Test content")
    
    @pytest.mark.asyncio
    async def test_poll_generation_unknown_status(self, gamma_client):
        """Test polling with unknown status."""
        with patch.object(gamma_client, 'get_generation_status') as mock_get_status:
            mock_get_status.return_value = {
                'generationId': 'test_generation_id',
                'status': 'unknown_status'
            }
            
            with pytest.raises(GammaAPIError, match="Generation polling timed out"):
                await gamma_client.poll_generation("test_generation_id", max_polls=1)
    
    @pytest.mark.asyncio
    async def test_poll_generation_exception_handling(self, gamma_client):
        """Test polling exception handling."""
        with patch.object(gamma_client, 'get_generation_status') as mock_get_status:
            mock_get_status.side_effect = Exception("Network error")
            
            with pytest.raises(GammaAPIError, match="Generation polling timed out"):
                await gamma_client.poll_generation("test_generation_id", max_polls=1)





