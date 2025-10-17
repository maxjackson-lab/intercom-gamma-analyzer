"""
Unit tests for ClaudeClient.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from services.claude_client import ClaudeClient


class TestClaudeClient:
    """Test cases for ClaudeClient."""
    
    @pytest.fixture
    def claude_client(self):
        """Create a ClaudeClient instance for testing."""
        with patch('services.claude_client.settings') as mock_settings:
            mock_settings.anthropic_api_key = "test-api-key"
            mock_settings.anthropic_model = "claude-3-opus-20240229"
            mock_settings.anthropic_max_tokens = 4000
            
            with patch('services.claude_client.anthropic.AsyncAnthropic'):
                return ClaudeClient()
    
    @pytest.fixture
    def mock_claude_response(self):
        """Create mock Claude API response."""
        return Mock(
            content=[
                Mock(
                    text="Sentiment: positive\nConfidence: 0.85\nAnalysis: Customer is satisfied with the service."
                )
            ]
        )
    
    @pytest.mark.asyncio
    async def test_claude_client_initialization(self, claude_client):
        """Test ClaudeClient initializes correctly."""
        assert claude_client.model == "claude-3-opus-20240229"
        assert claude_client.max_tokens == 4000
        assert claude_client.api_key == "test-api-key"
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self, claude_client, mock_claude_response):
        """Test successful connection to Claude API."""
        with patch.object(claude_client.client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_claude_response
            
            result = await claude_client.test_connection()
            
            assert result is True
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_test_connection_failure(self, claude_client):
        """Test connection failure to Claude API."""
        with patch.object(claude_client.client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("API Error")
            
            with pytest.raises(Exception, match="API Error"):
                await claude_client.test_connection()
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_multilingual_english(self, claude_client, mock_claude_response):
        """Test sentiment analysis for English text."""
        with patch.object(claude_client.client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_claude_response
            
            result = await claude_client.analyze_sentiment_multilingual(
                "Thank you so much! This really helped.",
                language="en"
            )
            
            assert result['sentiment'] == 'positive'
            assert result['confidence'] == 0.85
            assert result['model'] == 'claude'
            assert result['language'] == 'en'
            assert 'analysis' in result
            assert 'emotional_indicators' in result
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_multilingual_spanish(self, claude_client):
        """Test sentiment analysis for Spanish text."""
        mock_response = Mock(
            content=[
                Mock(
                    text="Sentiment: negative\nConfidence: 0.82\nAnalysis: Customer is frustrated with the service."
                )
            ]
        )
        
        with patch.object(claude_client.client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            result = await claude_client.analyze_sentiment_multilingual(
                "Estoy muy frustrado con esta funcionalidad.",
                language="es"
            )
            
            assert result['sentiment'] == 'negative'
            assert result['confidence'] == 0.82
            assert result['model'] == 'claude'
            assert result['language'] == 'es'
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_multilingual_japanese(self, claude_client):
        """Test sentiment analysis for Japanese text."""
        mock_response = Mock(
            content=[
                Mock(
                    text="Sentiment: neutral\nConfidence: 0.68\nAnalysis: Customer is asking a question politely."
                )
            ]
        )
        
        with patch.object(claude_client.client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            result = await claude_client.analyze_sentiment_multilingual(
                "APIの統合について質問があります。",
                language="ja"
            )
            
            assert result['sentiment'] == 'neutral'
            assert result['confidence'] == 0.68
            assert result['model'] == 'claude'
            assert result['language'] == 'ja'
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_api_failure(self, claude_client):
        """Test sentiment analysis when API fails."""
        with patch.object(claude_client.client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("Claude API Error")
            
            with pytest.raises(Exception, match="Claude API Error"):
                await claude_client.analyze_sentiment_multilingual(
                    "Test text",
                    language="en"
                )
    
    def test_parse_sentiment_positive(self, claude_client):
        """Test sentiment parsing for positive text."""
        analysis_text = "The customer is very positive and satisfied with the service."
        result = claude_client._parse_sentiment(analysis_text)
        assert result == 'positive'
    
    def test_parse_sentiment_negative(self, claude_client):
        """Test sentiment parsing for negative text."""
        analysis_text = "The customer is frustrated and disappointed with the product."
        result = claude_client._parse_sentiment(analysis_text)
        assert result == 'negative'
    
    def test_parse_sentiment_neutral(self, claude_client):
        """Test sentiment parsing for neutral text."""
        analysis_text = "The customer is asking a question about the service."
        result = claude_client._parse_sentiment(analysis_text)
        assert result == 'neutral'
    
    def test_extract_confidence_score_explicit(self, claude_client):
        """Test confidence score extraction with explicit score."""
        analysis_text = "Confidence: 0.85"
        result = claude_client._extract_confidence_score(analysis_text)
        assert result == 0.85
    
    def test_extract_confidence_score_very(self, claude_client):
        """Test confidence score extraction with 'very' indicator."""
        analysis_text = "The customer is very satisfied."
        result = claude_client._extract_confidence_score(analysis_text)
        assert result == 0.9
    
    def test_extract_confidence_score_somewhat(self, claude_client):
        """Test confidence score extraction with 'somewhat' indicator."""
        analysis_text = "The customer is somewhat satisfied."
        result = claude_client._extract_confidence_score(analysis_text)
        assert result == 0.6
    
    def test_extract_confidence_score_default(self, claude_client):
        """Test confidence score extraction with default fallback."""
        analysis_text = "The customer is satisfied."
        result = claude_client._extract_confidence_score(analysis_text)
        assert result == 0.8
    
    def test_extract_emotional_indicators(self, claude_client):
        """Test emotional indicators extraction."""
        analysis_text = "The customer is grateful and satisfied with the service."
        result = claude_client._extract_emotional_indicators(analysis_text)
        assert 'grateful' in result
        assert 'satisfied' in result
        assert len(result) <= 3
