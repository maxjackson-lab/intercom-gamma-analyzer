"""
Unit tests for BaseCategoryAnalyzer.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from typing import List, Dict, Any

from src.analyzers.base_category_analyzer import BaseCategoryAnalyzer


class TestBaseCategoryAnalyzer:
    """Test cases for BaseCategoryAnalyzer."""
    
    @pytest.fixture
    def mock_analyzer(self):
        """Create a mock analyzer instance for testing."""
        with patch('analyzers.base_category_analyzer.OpenAIClient'), \
             patch('analyzers.base_category_analyzer.CategoryFilters'), \
             patch('analyzers.base_category_analyzer.taxonomy_manager'):
            
            class MockAnalyzer(BaseCategoryAnalyzer):
                async def analyze_category(self, conversations: List[Dict], start_date: datetime, end_date: datetime, options: Dict[str, Any]) -> Dict:
                    return {
                        'category': self.category_name,
                        'data_summary': self._extract_common_metrics(conversations, start_date, end_date),
                        'analysis_results': {},
                        'ai_insights': None
                    }
            
            return MockAnalyzer("TestCategory")
    
    @pytest.fixture
    def sample_conversations(self):
        """Create sample conversation data for testing."""
        return [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'I need help with billing'
                        }
                    ]
                },
                'source': {
                    'body': 'billing issue'
                },
                'tags': {
                    'tags': [
                        {'name': 'Billing'}
                    ]
                },
                'topics': {
                    'topics': [
                        {'name': 'billing'}
                    ]
                },
                'admin_assignee': {
                    'id': 'agent_1',
                    'name': 'Dae-Ho'
                },
                'created_at': 1640995200,  # 2022-01-01
                'updated_at': 1640995200
            },
            {
                'id': 'conv_2',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'I have a bug with the export feature'
                        }
                    ]
                },
                'source': {
                    'body': 'export not working'
                },
                'tags': {
                    'tags': [
                        {'name': 'Bug Report'}
                    ]
                },
                'topics': {
                    'topics': [
                        {'name': 'export'}
                    ]
                },
                'admin_assignee': {
                    'id': 'agent_2',
                    'name': 'Hilary'
                },
                'created_at': 1640995200,
                'updated_at': 1640995200
            }
        ]
    
    def test_initialization(self, mock_analyzer):
        """Test BaseCategoryAnalyzer initialization."""
        assert mock_analyzer.category_name == "TestCategory"
        assert mock_analyzer.openai_client is not None
        assert mock_analyzer.category_filters is not None
        assert mock_analyzer.taxonomy_manager is not None
    
    def test_extract_common_metrics(self, mock_analyzer, sample_conversations):
        """Test common metrics extraction."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        
        metrics = mock_analyzer._extract_common_metrics(sample_conversations, start_date, end_date)
        
        assert metrics['start_date'] == '2022-01-01'
        assert metrics['end_date'] == '2022-01-31'
        assert metrics['total_conversations'] == 2
        assert metrics['filtered_conversations'] == 2
        assert 'top_topics' in metrics
        assert 'top_tags' in metrics
        assert 'sentiment_distribution' in metrics
        assert 'agent_distribution' in metrics
        assert 'channel_distribution' in metrics
        assert 'response_time_metrics' in metrics
        assert 'resolution_metrics' in metrics
    
    def test_extract_common_metrics_empty_conversations(self, mock_analyzer):
        """Test common metrics extraction with empty conversations."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        
        metrics = mock_analyzer._extract_common_metrics([], start_date, end_date)
        
        assert metrics['total_conversations'] == 0
        assert metrics['filtered_conversations'] == 0
        assert metrics['top_topics'] == []
        assert metrics['top_tags'] == []
        assert metrics['sentiment_distribution'] == {'positive': 0, 'neutral': 0, 'negative': 0}
        assert metrics['agent_distribution'] == {}
        assert metrics['channel_distribution'] == {}
    
    def test_extract_common_metrics_with_topics_and_tags(self, mock_analyzer, sample_conversations):
        """Test common metrics extraction with topics and tags."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        
        metrics = mock_analyzer._extract_common_metrics(sample_conversations, start_date, end_date)
        
        # Check topics
        assert len(metrics['top_topics']) == 2
        topic_names = [topic['topic'] for topic in metrics['top_topics']]
        assert 'billing' in topic_names
        assert 'export' in topic_names
        
        # Check tags
        assert len(metrics['top_tags']) == 2
        tag_names = [tag['tag'] for tag in metrics['top_tags']]
        assert 'Billing' in tag_names
        assert 'Bug Report' in tag_names
    
    def test_extract_common_metrics_agent_distribution(self, mock_analyzer, sample_conversations):
        """Test agent distribution in common metrics."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        
        metrics = mock_analyzer._extract_common_metrics(sample_conversations, start_date, end_date)
        
        agent_dist = metrics['agent_distribution']
        assert 'Dae-Ho' in agent_dist
        assert 'Hilary' in agent_dist
        assert agent_dist['Dae-Ho'] == 1
        assert agent_dist['Hilary'] == 1
    
    def test_extract_common_metrics_channel_distribution(self, mock_analyzer, sample_conversations):
        """Test channel distribution in common metrics."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        
        metrics = mock_analyzer._extract_common_metrics(sample_conversations, start_date, end_date)
        
        channel_dist = metrics['channel_distribution']
        assert 'conversation' in channel_dist
        assert channel_dist['conversation'] == 2
    
    def test_extract_common_metrics_response_time(self, mock_analyzer, sample_conversations):
        """Test response time metrics in common metrics."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        
        metrics = mock_analyzer._extract_common_metrics(sample_conversations, start_date, end_date)
        
        response_time = metrics['response_time_metrics']
        assert 'average_response_time_hours' in response_time
        assert 'median_response_time_hours' in response_time
        assert 'response_time_distribution' in response_time
    
    def test_extract_common_metrics_resolution(self, mock_analyzer, sample_conversations):
        """Test resolution metrics in common metrics."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        
        metrics = mock_analyzer._extract_common_metrics(sample_conversations, start_date, end_date)
        
        resolution = metrics['resolution_metrics']
        assert 'resolution_rate' in resolution
        assert 'average_resolution_time_hours' in resolution
        assert 'resolution_time_distribution' in resolution
    
    @pytest.mark.asyncio
    async def test_generate_ai_insights_disabled(self, mock_analyzer, sample_conversations):
        """Test AI insights generation when disabled."""
        data_summary = {
            'generate_ai_insights': False,
            'start_date': '2022-01-01',
            'end_date': '2022-01-31',
            'total_conversations': 2,
            'filtered_conversations': 2
        }
        
        insights = await mock_analyzer._generate_ai_insights(
            data_summary, sample_conversations, 'test_prompt'
        )
        
        assert insights is None
    
    @pytest.mark.asyncio
    async def test_generate_ai_insights_enabled(self, mock_analyzer, sample_conversations):
        """Test AI insights generation when enabled."""
        data_summary = {
            'generate_ai_insights': True,
            'start_date': '2022-01-01',
            'end_date': '2022-01-31',
            'total_conversations': 2,
            'filtered_conversations': 2,
            'top_topics': [{'topic': 'billing', 'count': 1}],
            'top_tags': [{'tag': 'Billing', 'count': 1}],
            'sentiment_distribution': {'positive': 0, 'neutral': 1, 'negative': 1}
        }
        
        # Mock the OpenAI client
        mock_analyzer.openai_client.generate_analysis = AsyncMock(return_value="Test AI insights")
        
        # Mock the prompt template
        with patch('analyzers.base_category_analyzer.PromptTemplates') as mock_prompts:
            mock_prompts.test_prompt.return_value = "Test prompt"
            
            insights = await mock_analyzer._generate_ai_insights(
                data_summary, sample_conversations, 'test_prompt'
            )
        
        assert insights == "Test AI insights"
        mock_analyzer.openai_client.generate_analysis.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_ai_insights_error_handling(self, mock_analyzer, sample_conversations):
        """Test AI insights generation error handling."""
        data_summary = {
            'generate_ai_insights': True,
            'start_date': '2022-01-01',
            'end_date': '2022-01-31',
            'total_conversations': 2,
            'filtered_conversations': 2
        }
        
        # Mock the OpenAI client to raise an exception
        mock_analyzer.openai_client.generate_analysis = AsyncMock(side_effect=Exception("API Error"))
        
        # Mock the prompt template
        with patch('analyzers.base_category_analyzer.PromptTemplates') as mock_prompts:
            mock_prompts.test_prompt.return_value = "Test prompt"
            
            insights = await mock_analyzer._generate_ai_insights(
                data_summary, sample_conversations, 'test_prompt'
            )
        
        assert "AI report generation failed: API Error" in insights
    
    @pytest.mark.asyncio
    async def test_generate_ai_insights_invalid_prompt(self, mock_analyzer, sample_conversations):
        """Test AI insights generation with invalid prompt key."""
        data_summary = {
            'generate_ai_insights': True,
            'start_date': '2022-01-01',
            'end_date': '2022-01-31',
            'total_conversations': 2,
            'filtered_conversations': 2
        }
        
        # Mock the prompt template to return None
        with patch('analyzers.base_category_analyzer.PromptTemplates') as mock_prompts:
            mock_prompts.invalid_prompt = None
            
            insights = await mock_analyzer._generate_ai_insights(
                data_summary, sample_conversations, 'invalid_prompt'
            )
        
        assert "AI report generation failed: Invalid prompt key." in insights
    
    def test_extract_conversation_text(self, mock_analyzer, sample_conversations):
        """Test conversation text extraction."""
        conv = sample_conversations[0]
        text = mock_analyzer._extract_conversation_text(conv)
        
        assert 'I need help with billing' in text
        assert 'billing issue' in text
    
    def test_extract_conversation_text_empty_parts(self, mock_analyzer):
        """Test conversation text extraction with empty parts."""
        conv = {
            'id': 'conv_empty',
            'conversation_parts': {
                'conversation_parts': []
            },
            'source': {
                'body': 'only source text'
            }
        }
        
        text = mock_analyzer._extract_conversation_text(conv)
        assert text == 'only source text'
    
    def test_extract_conversation_text_missing_fields(self, mock_analyzer):
        """Test conversation text extraction with missing fields."""
        conv = {
            'id': 'conv_missing',
            'source': {
                'body': 'only source text'
            }
        }
        
        text = mock_analyzer._extract_conversation_text(conv)
        assert text == 'only source text'
    
    def test_extract_conversation_text_no_text(self, mock_analyzer):
        """Test conversation text extraction with no text."""
        conv = {
            'id': 'conv_no_text',
            'conversation_parts': {
                'conversation_parts': [
                    {'part_type': 'comment', 'body': ''}
                ]
            },
            'source': {
                'body': ''
            }
        }
        
        text = mock_analyzer._extract_conversation_text(conv)
        assert text == ''
    
    def test_calculate_response_time_metrics(self, mock_analyzer, sample_conversations):
        """Test response time metrics calculation."""
        metrics = mock_analyzer._calculate_response_time_metrics(sample_conversations)
        
        assert 'average_response_time_hours' in metrics
        assert 'median_response_time_hours' in metrics
        assert 'response_time_distribution' in metrics
        assert isinstance(metrics['average_response_time_hours'], (int, float))
        assert isinstance(metrics['median_response_time_hours'], (int, float))
        assert isinstance(metrics['response_time_distribution'], dict)
    
    def test_calculate_resolution_metrics(self, mock_analyzer, sample_conversations):
        """Test resolution metrics calculation."""
        metrics = mock_analyzer._calculate_resolution_metrics(sample_conversations)
        
        assert 'resolution_rate' in metrics
        assert 'average_resolution_time_hours' in metrics
        assert 'resolution_time_distribution' in metrics
        assert isinstance(metrics['resolution_rate'], (int, float))
        assert isinstance(metrics['average_resolution_time_hours'], (int, float))
        assert isinstance(metrics['resolution_time_distribution'], dict)
    
    def test_extract_agent_distribution(self, mock_analyzer, sample_conversations):
        """Test agent distribution extraction."""
        distribution = mock_analyzer._extract_agent_distribution(sample_conversations)
        
        assert 'Dae-Ho' in distribution
        assert 'Hilary' in distribution
        assert distribution['Dae-Ho'] == 1
        assert distribution['Hilary'] == 1
    
    def test_extract_channel_distribution(self, mock_analyzer, sample_conversations):
        """Test channel distribution extraction."""
        distribution = mock_analyzer._extract_channel_distribution(sample_conversations)
        
        assert 'conversation' in distribution
        assert distribution['conversation'] == 2
    
    def test_extract_topic_distribution(self, mock_analyzer, sample_conversations):
        """Test topic distribution extraction."""
        distribution = mock_analyzer._extract_topic_distribution(sample_conversations)
        
        assert 'billing' in distribution
        assert 'export' in distribution
        assert distribution['billing'] == 1
        assert distribution['export'] == 1
    
    def test_extract_tag_distribution(self, mock_analyzer, sample_conversations):
        """Test tag distribution extraction."""
        distribution = mock_analyzer._extract_tag_distribution(sample_conversations)
        
        assert 'Billing' in distribution
        assert 'Bug Report' in distribution
        assert distribution['Billing'] == 1
        assert distribution['Bug Report'] == 1
    
    def test_format_top_items(self, mock_analyzer):
        """Test formatting top items."""
        distribution = {'item1': 5, 'item2': 3, 'item3': 1}
        formatted = mock_analyzer._format_top_items(distribution, 'item', 'count', 2)
        
        assert len(formatted) == 2
        assert formatted[0]['item'] == 'item1'
        assert formatted[0]['count'] == 5
        assert formatted[1]['item'] == 'item2'
        assert formatted[1]['count'] == 3
    
    def test_format_top_items_empty(self, mock_analyzer):
        """Test formatting top items with empty distribution."""
        distribution = {}
        formatted = mock_analyzer._format_top_items(distribution, 'item', 'count', 5)
        
        assert len(formatted) == 0
    
    def test_format_top_items_less_than_limit(self, mock_analyzer):
        """Test formatting top items with fewer items than limit."""
        distribution = {'item1': 5}
        formatted = mock_analyzer._format_top_items(distribution, 'item', 'count', 5)
        
        assert len(formatted) == 1
        assert formatted[0]['item'] == 'item1'
        assert formatted[0]['count'] == 5
    
    def test_analyze_category_abstract_method(self, mock_analyzer, sample_conversations):
        """Test that analyze_category is properly implemented."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        options = {'generate_ai_insights': False}
        
        # This should not raise an exception since MockAnalyzer implements the method
        result = mock_analyzer.analyze_category(sample_conversations, start_date, end_date, options)
        
        assert result['category'] == 'TestCategory'
        assert 'data_summary' in result
        assert 'analysis_results' in result
        assert 'ai_insights' in result
    
    def test_category_name_property(self, mock_analyzer):
        """Test category name property."""
        assert mock_analyzer.category_name == "TestCategory"
    
    def test_services_initialization(self, mock_analyzer):
        """Test that all required services are initialized."""
        assert mock_analyzer.openai_client is not None
        assert mock_analyzer.category_filters is not None
        assert mock_analyzer.taxonomy_manager is not None
    
    def test_logger_initialization(self, mock_analyzer):
        """Test that logger is properly initialized."""
        assert mock_analyzer.logger is not None
        assert mock_analyzer.logger.name == 'analyzers.base_category_analyzer'






