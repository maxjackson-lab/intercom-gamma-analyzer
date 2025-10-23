"""
Unit tests for AIModelFactory.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from src.services.ai_model_factory import AIModelFactory, AIModel
from src.services.openai_client import OpenAIClient
from src.services.claude_client import ClaudeClient


class TestAIModelFactory:
    """Test cases for AIModelFactory."""
    
    @pytest.fixture
    def ai_factory(self):
        """Create an AIModelFactory instance for testing."""
        return AIModelFactory()
    
    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        client = Mock(spec=OpenAIClient)
        client.analyze_sentiment_multilingual = AsyncMock()
        client.test_connection = AsyncMock()
        return client
    
    @pytest.fixture
    def mock_claude_client(self):
        """Create a mock Claude client."""
        client = Mock(spec=ClaudeClient)
        client.analyze_sentiment_multilingual = AsyncMock()
        client.test_connection = AsyncMock()
        return client
    
    def test_get_openai_client(self, ai_factory):
        """Test getting OpenAI client."""
        with patch('services.ai_model_factory.OpenAIClient') as mock_openai:
            mock_openai.return_value = Mock()
            
            client = ai_factory.get_client(AIModel.OPENAI_GPT4)
            
            assert client is not None
            mock_openai.assert_called_once()
    
    def test_get_claude_client(self, ai_factory):
        """Test getting Claude client."""
        with patch('services.ai_model_factory.ClaudeClient') as mock_claude:
            mock_claude.return_value = Mock()
            
            client = ai_factory.get_client(AIModel.ANTHROPIC_CLAUDE)
            
            assert client is not None
            mock_claude.assert_called_once()
    
    def test_get_unsupported_model(self, ai_factory):
        """Test getting unsupported model raises error."""
        with pytest.raises(ValueError, match="Unsupported AI model"):
            # Create a mock enum value that's not supported
            class UnsupportedModel:
                value = "unsupported_model"
            ai_factory.get_client(UnsupportedModel())
    
    def test_client_caching(self, ai_factory):
        """Test that clients are cached and reused."""
        with patch('services.ai_model_factory.OpenAIClient') as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            
            # Get client twice
            client1 = ai_factory.get_client(AIModel.OPENAI_GPT4)
            client2 = ai_factory.get_client(AIModel.OPENAI_GPT4)
            
            # Should be the same instance
            assert client1 is client2
            # Should only be created once
            mock_openai.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_openai_success(self, ai_factory, mock_openai_client):
        """Test successful sentiment analysis with OpenAI."""
        ai_factory._openai_client = mock_openai_client
        mock_openai_client.analyze_sentiment_multilingual.return_value = {
            'sentiment': 'positive',
            'confidence': 0.85,
            'analysis': 'Customer is satisfied',
            'model': 'openai'
        }
        
        result = await ai_factory.analyze_sentiment(
            text="Thank you!",
            language="en",
            model=AIModel.OPENAI_GPT4
        )
        
        assert result['sentiment'] == 'positive'
        assert result['model_used'] == 'openai'
        assert 'fallback' not in result
        mock_openai_client.analyze_sentiment_multilingual.assert_called_once_with("Thank you!", "en")
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_claude_success(self, ai_factory, mock_claude_client):
        """Test successful sentiment analysis with Claude."""
        ai_factory._claude_client = mock_claude_client
        mock_claude_client.analyze_sentiment_multilingual.return_value = {
            'sentiment': 'negative',
            'confidence': 0.82,
            'analysis': 'Customer is frustrated',
            'model': 'claude'
        }
        
        result = await ai_factory.analyze_sentiment(
            text="I'm frustrated",
            language="en",
            model=AIModel.ANTHROPIC_CLAUDE
        )
        
        assert result['sentiment'] == 'negative'
        assert result['model_used'] == 'claude'
        assert 'fallback' not in result
        mock_claude_client.analyze_sentiment_multilingual.assert_called_once_with("I'm frustrated", "en")
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_fallback_success(self, ai_factory, mock_openai_client, mock_claude_client):
        """Test successful fallback when primary model fails."""
        ai_factory._openai_client = mock_openai_client
        ai_factory._claude_client = mock_claude_client
        
        # OpenAI fails
        mock_openai_client.analyze_sentiment_multilingual.side_effect = Exception("OpenAI API Error")
        
        # Claude succeeds
        mock_claude_client.analyze_sentiment_multilingual.return_value = {
            'sentiment': 'positive',
            'confidence': 0.88,
            'analysis': 'Customer is happy',
            'model': 'claude'
        }
        
        result = await ai_factory.analyze_sentiment(
            text="Great service!",
            language="en",
            model=AIModel.OPENAI_GPT4,
            fallback=True
        )
        
        assert result['sentiment'] == 'positive'
        assert result['model_used'] == 'claude'
        assert result['fallback'] is True
        mock_openai_client.analyze_sentiment_multilingual.assert_called_once()
        mock_claude_client.analyze_sentiment_multilingual.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_no_fallback_failure(self, ai_factory, mock_openai_client):
        """Test failure when primary model fails and fallback is disabled."""
        ai_factory._openai_client = mock_openai_client
        mock_openai_client.analyze_sentiment_multilingual.side_effect = Exception("OpenAI API Error")
        
        with pytest.raises(Exception, match="OpenAI API Error"):
            await ai_factory.analyze_sentiment(
                text="Test text",
                language="en",
                model=AIModel.OPENAI_GPT4,
                fallback=False
            )
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_both_models_fail(self, ai_factory, mock_openai_client, mock_claude_client):
        """Test failure when both primary and fallback models fail."""
        ai_factory._openai_client = mock_openai_client
        ai_factory._claude_client = mock_claude_client
        
        # Both models fail
        mock_openai_client.analyze_sentiment_multilingual.side_effect = Exception("OpenAI API Error")
        mock_claude_client.analyze_sentiment_multilingual.side_effect = Exception("Claude API Error")
        
        with pytest.raises(Exception, match="Claude API Error"):
            await ai_factory.analyze_sentiment(
                text="Test text",
                language="en",
                model=AIModel.OPENAI_GPT4,
                fallback=True
            )
    
    @pytest.mark.asyncio
    async def test_test_connections_both_success(self, ai_factory, mock_openai_client, mock_claude_client):
        """Test connection testing when both models succeed."""
        ai_factory._openai_client = mock_openai_client
        ai_factory._claude_client = mock_claude_client
        
        mock_openai_client.test_connection.return_value = True
        mock_claude_client.test_connection.return_value = True
        
        results = await ai_factory.test_connections()
        
        assert results['openai'] is True
        assert results['claude'] is True
        mock_openai_client.test_connection.assert_called_once()
        mock_claude_client.test_connection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_test_connections_openai_fails(self, ai_factory, mock_openai_client, mock_claude_client):
        """Test connection testing when OpenAI fails."""
        ai_factory._openai_client = mock_openai_client
        ai_factory._claude_client = mock_claude_client
        
        mock_openai_client.test_connection.side_effect = Exception("OpenAI Error")
        mock_claude_client.test_connection.return_value = True
        
        results = await ai_factory.test_connections()
        
        assert results['openai'] is False
        assert results['claude'] is True
    
    @pytest.mark.asyncio
    async def test_test_connections_claude_fails(self, ai_factory, mock_openai_client, mock_claude_client):
        """Test connection testing when Claude fails."""
        ai_factory._openai_client = mock_openai_client
        ai_factory._claude_client = mock_claude_client
        
        mock_openai_client.test_connection.return_value = True
        mock_claude_client.test_connection.side_effect = Exception("Claude Error")
        
        results = await ai_factory.test_connections()
        
        assert results['openai'] is True
        assert results['claude'] is False
    
    @pytest.mark.asyncio
    async def test_test_connections_both_fail(self, ai_factory, mock_openai_client, mock_claude_client):
        """Test connection testing when both models fail."""
        ai_factory._openai_client = mock_openai_client
        ai_factory._claude_client = mock_claude_client
        
        mock_openai_client.test_connection.side_effect = Exception("OpenAI Error")
        mock_claude_client.test_connection.side_effect = Exception("Claude Error")
        
        results = await ai_factory.test_connections()
        
        assert results['openai'] is False
        assert results['claude'] is False
