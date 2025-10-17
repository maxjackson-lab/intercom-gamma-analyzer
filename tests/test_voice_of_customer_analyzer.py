"""
Unit tests for VoiceOfCustomerAnalyzer.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, List, Any

from analyzers.voice_of_customer_analyzer import VoiceOfCustomerAnalyzer
from services.ai_model_factory import AIModelFactory, AIModel
from services.agent_feedback_separator import AgentFeedbackSeparator
from services.historical_data_manager import HistoricalDataManager


class TestVoiceOfCustomerAnalyzer:
    """Test cases for VoiceOfCustomerAnalyzer."""
    
    @pytest.fixture
    def mock_ai_factory(self):
        """Create a mock AI model factory."""
        factory = Mock(spec=AIModelFactory)
        factory.analyze_sentiment = AsyncMock()
        return factory
    
    @pytest.fixture
    def mock_agent_separator(self):
        """Create a mock agent separator."""
        separator = Mock(spec=AgentFeedbackSeparator)
        separator.separate_by_agent_type.return_value = {
            'finn_ai': [],
            'boldr_support': [],
            'horatio_support': [],
            'gamma_cx_staff': [],
            'mixed_agent': [],
            'customer_only': []
        }
        return separator
    
    @pytest.fixture
    def mock_historical_manager(self):
        """Create a mock historical data manager."""
        manager = Mock(spec=HistoricalDataManager)
        manager.store_weekly_snapshot = AsyncMock()
        manager.get_trend_analysis.return_value = {'trends': {}, 'insights': []}
        return manager
    
    @pytest.fixture
    def analyzer(self, mock_ai_factory, mock_agent_separator, mock_historical_manager):
        """Create a VoiceOfCustomerAnalyzer instance for testing."""
        return VoiceOfCustomerAnalyzer(
            mock_ai_factory,
            mock_agent_separator,
            mock_historical_manager
        )
    
    @pytest.fixture
    def sample_conversations(self):
        """Create sample conversations for testing."""
        return [
            {
                'id': 'conv_1',
                'tags': {
                    'tags': [{'name': 'Billing'}]
                },
                'custom_attributes': {
                    'User Sentiment': 'positive',
                    'CX Score rating': '4.5',
                    'CX Score explanation': 'Customer was satisfied',
                    'Language': 'en'
                },
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'body': 'Thank you so much! This really helped me understand the billing process.',
                            'author': {'type': 'user', 'name': 'John Doe', 'email': 'john@example.com'}
                        }
                    ]
                }
            },
            {
                'id': 'conv_2',
                'tags': {
                    'tags': [{'name': 'Product Question'}]
                },
                'custom_attributes': {
                    'User Sentiment': 'negative',
                    'CX Score rating': '2.0',
                    'CX Score explanation': 'Customer frustrated',
                    'Language': 'es'
                },
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'body': 'Estoy muy frustrado con esta funcionalidad.',
                            'author': {'type': 'user', 'name': 'María García', 'email': 'maria@example.com'}
                        }
                    ]
                }
            },
            {
                'id': 'conv_3',
                'tags': {
                    'tags': [{'name': 'Billing'}]
                },
                'custom_attributes': {
                    'User Sentiment': 'neutral',
                    'CX Score rating': '3.0',
                    'Language': 'en'
                },
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'body': 'I have a question about my billing statement.',
                            'author': {'type': 'user', 'name': 'Bob Smith', 'email': 'bob@example.com'}
                        }
                    ]
                }
            }
        ]
    
    @pytest.mark.asyncio
    async def test_analyze_weekly_sentiment_with_attributes(self, analyzer, sample_conversations, mock_ai_factory):
        """Test weekly sentiment analysis using custom attributes."""
        # Mock AI factory to not be called since we have good attribute coverage
        mock_ai_factory.analyze_sentiment = AsyncMock()
        
        result = await analyzer.analyze_weekly_sentiment(
            sample_conversations,
            ai_model=AIModel.OPENAI_GPT4,
            enable_fallback=True
        )
        
        assert 'results' in result
        assert 'metadata' in result
        assert result['metadata']['total_conversations'] == 3
        assert result['metadata']['ai_model'] == 'openai'
        
        # Check that Billing category was analyzed
        assert 'Billing' in result['results']
        assert 'Product Question' in result['results']
        
        # Verify AI factory was not called due to good attribute coverage
        mock_ai_factory.analyze_sentiment.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_analyze_weekly_sentiment_with_ai_fallback(self, analyzer, sample_conversations, mock_ai_factory):
        """Test weekly sentiment analysis with AI fallback."""
        # Create conversations without custom attributes
        conversations_no_attrs = [
            {
                'id': 'conv_no_attrs',
                'tags': {'tags': [{'name': 'General'}]},
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'body': 'I need help with something',
                            'author': {'type': 'user', 'name': 'User', 'email': 'user@example.com'}
                        }
                    ]
                }
            }
        ]
        
        # Mock AI response
        mock_ai_factory.analyze_sentiment.return_value = {
            'sentiment': 'positive',
            'confidence': 0.85,
            'analysis': 'Customer seems satisfied',
            'emotional_indicators': ['satisfied'],
            'model_used': 'openai'
        }
        
        result = await analyzer.analyze_weekly_sentiment(
            conversations_no_attrs,
            ai_model=AIModel.OPENAI_GPT4,
            enable_fallback=True
        )
        
        # Verify AI factory was called
        mock_ai_factory.analyze_sentiment.assert_called_once()
        
        # Check results
        assert 'General' in result['results']
        sentiment_data = result['results']['General']['sentiment_breakdown']
        assert sentiment_data['sentiment'] == 'positive'
        assert sentiment_data['source'] == 'ai_analysis'
    
    @pytest.mark.asyncio
    async def test_analyze_weekly_sentiment_with_trends(self, analyzer, sample_conversations):
        """Test weekly sentiment analysis with trends included."""
        result = await analyzer.analyze_weekly_sentiment(
            sample_conversations,
            ai_model=AIModel.OPENAI_GPT4,
            options={'include_trends': True}
        )
        
        assert '_trends' in result['results']
        assert 'trends' in result['results']['_trends']
    
    def test_extract_sentiment_from_attributes(self, analyzer, sample_conversations):
        """Test extracting sentiment from custom attributes."""
        result = analyzer._extract_sentiment_from_attributes(sample_conversations)
        
        assert 'sentiment_breakdown' in result
        assert 'average_cx_score' in result
        assert 'coverage' in result
        assert result['source'] == 'intercom_attributes'
        
        # Check sentiment breakdown
        breakdown = result['sentiment_breakdown']
        assert 'positive' in breakdown
        assert 'negative' in breakdown
        assert 'neutral' in breakdown
        
        # Check percentages
        assert breakdown['positive']['percentage'] == 33.33  # 1 out of 3
        assert breakdown['negative']['percentage'] == 33.33  # 1 out of 3
        assert breakdown['neutral']['percentage'] == 33.33  # 1 out of 3
    
    def test_get_top_categories_by_volume(self, analyzer, sample_conversations):
        """Test getting top categories by volume."""
        categories = analyzer._get_top_categories_by_volume(sample_conversations)
        
        assert 'Billing' in categories
        assert 'Product Question' in categories
        assert len(categories['Billing']) == 2  # Two billing conversations
        assert len(categories['Product Question']) == 1  # One product question
    
    def test_get_sentiment_examples(self, analyzer, sample_conversations):
        """Test getting sentiment examples."""
        examples = analyzer._get_sentiment_examples(sample_conversations)
        
        assert 'positive' in examples
        assert 'negative' in examples
        assert 'neutral' in examples
        
        # Check that examples contain actual quotes
        assert len(examples['positive']) > 0
        assert 'Thank you so much!' in examples['positive'][0]
    
    def test_get_agent_breakdown(self, analyzer, sample_conversations, mock_agent_separator):
        """Test getting agent breakdown."""
        # Mock agent separator to return specific breakdown
        mock_agent_separator.separate_by_agent_type.return_value = {
            'finn_ai': [sample_conversations[0]],
            'boldr_support': [sample_conversations[1]],
            'horatio_support': [],
            'gamma_cx_staff': [],
            'mixed_agent': [],
            'customer_only': [sample_conversations[2]]
        }
        
        breakdown = analyzer._get_agent_breakdown(sample_conversations)
        
        assert breakdown['finn_ai'] == 1
        assert breakdown['boldr_support'] == 1
        assert breakdown['customer_only'] == 1
    
    def test_get_language_breakdown(self, analyzer, sample_conversations):
        """Test getting language breakdown."""
        breakdown = analyzer._get_language_breakdown(sample_conversations)
        
        assert breakdown['en'] == 2  # Two English conversations
        assert breakdown['es'] == 1  # One Spanish conversation
    
    def test_combine_conversation_texts(self, analyzer, sample_conversations):
        """Test combining conversation texts."""
        combined_text = analyzer._combine_conversation_texts(sample_conversations)
        
        assert 'Thank you so much!' in combined_text
        assert 'Estoy muy frustrado' in combined_text
        assert 'billing statement' in combined_text
    
    def test_extract_quote_from_conversation(self, analyzer, sample_conversations):
        """Test extracting quotes from conversations."""
        quote = analyzer._extract_quote_from_conversation(sample_conversations[0])
        
        assert quote is not None
        assert 'Thank you so much!' in quote
    
    def test_extract_quote_from_conversation_no_user_message(self, analyzer):
        """Test extracting quotes when no user message exists."""
        conv = {
            'id': 'conv_no_user',
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'body': 'This is an admin message',
                        'author': {'type': 'admin', 'name': 'Admin', 'email': 'admin@example.com'}
                    }
                ]
            }
        }
        
        quote = analyzer._extract_quote_from_conversation(conv)
        assert quote is None
    
    def test_generate_insights(self, analyzer):
        """Test generating insights from analysis results."""
        analysis_results = {
            'results': {
                'Billing': {
                    'volume': 25,
                    'sentiment_breakdown': {
                        'sentiment': 'positive',
                        'confidence': 0.85
                    },
                    'agent_breakdown': {
                        'finn_ai': 15,
                        'boldr_support': 10
                    }
                },
                'Support': {
                    'volume': 10,
                    'sentiment_breakdown': {
                        'sentiment': 'negative',
                        'confidence': 0.75
                    },
                    'agent_breakdown': {
                        'gamma_cx_staff': 10
                    }
                }
            }
        }
        
        insights = analyzer.generate_insights(analysis_results)
        
        assert len(insights) > 0
        assert any('Top volume category: Billing' in insight for insight in insights)
        assert any('High negative sentiment in Support' in insight for insight in insights)
        assert any('Billing primarily handled by finn_ai' in insight for insight in insights)
    
    @pytest.mark.asyncio
    async def test_store_historical_snapshot(self, analyzer, mock_historical_manager):
        """Test storing historical snapshot."""
        analysis_results = {
            'results': {'test': 'data'},
            'metadata': {'total_conversations': 10}
        }
        
        await analyzer._store_historical_snapshot(analysis_results)
        
        mock_historical_manager.store_weekly_snapshot.assert_called_once()
    
    def test_get_historical_trends(self, analyzer, mock_historical_manager):
        """Test getting historical trends."""
        trends = analyzer._get_historical_trends()
        
        mock_historical_manager.get_trend_analysis.assert_called_once_with(weeks_back=12)
        assert 'trends' in trends
    
    def test_get_historical_trends_error_handling(self, analyzer, mock_historical_manager):
        """Test error handling in historical trends."""
        mock_historical_manager.get_trend_analysis.side_effect = Exception("Database error")
        
        trends = analyzer._get_historical_trends()
        
        assert 'error' in trends
        assert trends['error'] == 'Historical trends unavailable'
    
    def test_conversations_without_tags(self, analyzer):
        """Test handling conversations without tags."""
        conversations_no_tags = [
            {
                'id': 'conv_no_tags',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'body': 'I need help',
                            'author': {'type': 'user', 'name': 'User', 'email': 'user@example.com'}
                        }
                    ]
                }
            }
        ]
        
        categories = analyzer._get_top_categories_by_volume(conversations_no_tags)
        
        assert 'General' in categories
        assert len(categories['General']) == 1
