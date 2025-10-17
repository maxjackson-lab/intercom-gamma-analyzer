"""
Unit tests for ApiAnalyzer.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from typing import List, Dict, Any

from analyzers.api_analyzer import ApiAnalyzer


class TestApiAnalyzer:
    """Test cases for ApiAnalyzer."""
    
    @pytest.fixture
    def api_analyzer(self):
        """Create an ApiAnalyzer instance for testing."""
        with patch('analyzers.api_analyzer.OpenAIClient'), \
             patch('analyzers.api_analyzer.CategoryFilters'), \
             patch('analyzers.api_analyzer.taxonomy_manager'):
            
            return ApiAnalyzer()
    
    @pytest.fixture
    def sample_api_conversations(self):
        """Create sample API conversation data for testing."""
        return [
            {
                'id': 'conv_api_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'I need help with API authentication'
                        }
                    ]
                },
                'source': {
                    'body': 'API key not working'
                },
                'tags': {
                    'tags': [
                        {'name': 'API Authentication'}
                    ]
                },
                'topics': {
                    'topics': [
                        {'name': 'api'}
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
                'id': 'conv_api_2',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'I have a question about API integration'
                        }
                    ]
                },
                'source': {
                    'body': 'API integration question'
                },
                'tags': {
                    'tags': [
                        {'name': 'API Integration'}
                    ]
                },
                'topics': {
                    'topics': [
                        {'name': 'integration'}
                    ]
                },
                'admin_assignee': {
                    'id': 'agent_2',
                    'name': 'Hilary'
                },
                'created_at': 1640995200,
                'updated_at': 1640995200
            },
            {
                'id': 'conv_api_3',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'I need help with API performance issues'
                        }
                    ]
                },
                'source': {
                    'body': 'API performance problem'
                },
                'tags': {
                    'tags': [
                        {'name': 'API Performance'}
                    ]
                },
                'topics': {
                    'topics': [
                        {'name': 'performance'}
                    ]
                },
                'admin_assignee': {
                    'id': 'agent_3',
                    'name': 'Max Jackson'
                },
                'created_at': 1640995200,
                'updated_at': 1640995200
            },
            {
                'id': 'conv_api_4',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'I have a question about API documentation'
                        }
                    ]
                },
                'source': {
                    'body': 'API documentation question'
                },
                'tags': {
                    'tags': [
                        {'name': 'API Documentation'}
                    ]
                },
                'topics': {
                    'topics': [
                        {'name': 'documentation'}
                    ]
                },
                'admin_assignee': {
                    'id': 'agent_1',
                    'name': 'Dae-Ho'
                },
                'created_at': 1640995200,
                'updated_at': 1640995200
            }
        ]
    
    def test_initialization(self, api_analyzer):
        """Test ApiAnalyzer initialization."""
        assert api_analyzer.category_name == "API"
        assert api_analyzer.openai_client is not None
        assert api_analyzer.category_filters is not None
        assert api_analyzer.taxonomy_manager is not None
    
    @pytest.mark.asyncio
    async def test_analyze_category_success(self, api_analyzer, sample_api_conversations):
        """Test successful API category analysis."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        options = {'generate_ai_insights': False}
        
        # Mock the category filter to return all conversations
        api_analyzer.category_filters.filter_by_category = MagicMock(
            return_value=(sample_api_conversations, {'filtered_count': 4})
        )
        
        result = await api_analyzer.analyze_category(
            sample_api_conversations, start_date, end_date, options
        )
        
        assert result['category'] == 'API'
        assert 'data_summary' in result
        assert 'analysis_results' in result
        assert 'ai_insights' in result
        
        # Check data summary
        data_summary = result['data_summary']
        assert data_summary['start_date'] == '2022-01-01'
        assert data_summary['end_date'] == '2022-01-31'
        assert data_summary['total_conversations'] == 4
        assert data_summary['filtered_conversations'] == 4
        
        # Check analysis results
        analysis_results = result['analysis_results']
        assert 'api_metrics' in analysis_results
        assert 'api_trends' in analysis_results
        assert 'api_insights' in analysis_results
        
        # Check API metrics
        api_metrics = analysis_results['api_metrics']
        assert 'authentication_conversations' in api_metrics
        assert 'integration_conversations' in api_metrics
        assert 'performance_conversations' in api_metrics
        assert 'documentation_conversations' in api_metrics
        assert 'total_api_conversations' in api_metrics
    
    @pytest.mark.asyncio
    async def test_analyze_category_no_conversations(self, api_analyzer):
        """Test API category analysis with no conversations."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        options = {'generate_ai_insights': False}
        
        # Mock the category filter to return no conversations
        api_analyzer.category_filters.filter_by_category = MagicMock(
            return_value=([], {'filtered_count': 0})
        )
        
        result = await api_analyzer.analyze_category(
            [], start_date, end_date, options
        )
        
        assert result['category'] == 'API'
        assert result['data_summary']['filtered_conversations'] == 0
        assert result['data_summary']['message'] == "No conversations matched the 'API' category criteria."
        assert result['analysis_results'] == {}
        assert result['ai_insights'] == "No data to generate AI insights for API."
    
    @pytest.mark.asyncio
    async def test_analyze_category_with_ai_insights(self, api_analyzer, sample_api_conversations):
        """Test API category analysis with AI insights generation."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        options = {'generate_ai_insights': True}
        
        # Mock the category filter
        api_analyzer.category_filters.filter_by_category = MagicMock(
            return_value=(sample_api_conversations, {'filtered_count': 4})
        )
        
        # Mock the AI insights generation
        api_analyzer._generate_ai_insights = AsyncMock(return_value="Test AI insights for API")
        
        result = await api_analyzer.analyze_category(
            sample_api_conversations, start_date, end_date, options
        )
        
        assert result['ai_insights'] == "Test AI insights for API"
        api_analyzer._generate_ai_insights.assert_called_once()
    
    def test_analyze_api_specifics(self, api_analyzer, sample_api_conversations):
        """Test API-specific analysis."""
        metrics = api_analyzer._analyze_api_specifics(sample_api_conversations)
        
        assert 'authentication_conversations' in metrics
        assert 'integration_conversations' in metrics
        assert 'performance_conversations' in metrics
        assert 'documentation_conversations' in metrics
        assert 'total_api_conversations' in metrics
        
        # Check that all conversations are counted
        assert metrics['total_api_conversations'] == 4
        
        # Check specific counts (should be 1 for each type based on sample data)
        assert metrics['authentication_conversations'] == 1
        assert metrics['integration_conversations'] == 1
        assert metrics['performance_conversations'] == 1
        assert metrics['documentation_conversations'] == 1
    
    def test_analyze_api_specifics_empty_conversations(self, api_analyzer):
        """Test API-specific analysis with empty conversations."""
        metrics = api_analyzer._analyze_api_specifics([])
        
        assert metrics['authentication_conversations'] == 0
        assert metrics['integration_conversations'] == 0
        assert metrics['performance_conversations'] == 0
        assert metrics['documentation_conversations'] == 0
        assert metrics['total_api_conversations'] == 0
    
    def test_analyze_api_specifics_keyword_matching(self, api_analyzer):
        """Test API-specific analysis with keyword matching."""
        conversations_with_keywords = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help with API authentication'}
                    ]
                },
                'source': {'body': 'API key not working'}
            },
            {
                'id': 'conv_2',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I have a question about API integration'}
                    ]
                },
                'source': {'body': 'API integration question'}
            },
            {
                'id': 'conv_3',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help with API performance issues'}
                    ]
                },
                'source': {'body': 'API performance problem'}
            },
            {
                'id': 'conv_4',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I have a question about API documentation'}
                    ]
                },
                'source': {'body': 'API documentation question'}
            }
        ]
        
        metrics = api_analyzer._analyze_api_specifics(conversations_with_keywords)
        
        # Should match based on keywords in the text
        assert metrics['authentication_conversations'] == 1
        assert metrics['integration_conversations'] == 1
        assert metrics['performance_conversations'] == 1
        assert metrics['documentation_conversations'] == 1
        assert metrics['total_api_conversations'] == 4
    
    def test_analyze_api_specifics_case_insensitive(self, api_analyzer):
        """Test API-specific analysis with case insensitive matching."""
        conversations_with_uppercase = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help with API AUTHENTICATION'}
                    ]
                },
                'source': {'body': 'API KEY NOT WORKING'}
            },
            {
                'id': 'conv_2',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I have a question about API INTEGRATION'}
                    ]
                },
                'source': {'body': 'API INTEGRATION QUESTION'}
            }
        ]
        
        metrics = api_analyzer._analyze_api_specifics(conversations_with_uppercase)
        
        # Should match despite uppercase
        assert metrics['authentication_conversations'] == 1
        assert metrics['integration_conversations'] == 1
        assert metrics['total_api_conversations'] == 2
    
    def test_analyze_api_specifics_multiple_matches(self, api_analyzer):
        """Test API-specific analysis with multiple matches in same conversation."""
        conversation_with_multiple = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help with API authentication and integration'}
                    ]
                },
                'source': {'body': 'API auth and integration question'}
            }
        ]
        
        metrics = api_analyzer._analyze_api_specifics(conversation_with_multiple)
        
        # Should count both authentication and integration
        assert metrics['authentication_conversations'] == 1
        assert metrics['integration_conversations'] == 1
        assert metrics['total_api_conversations'] == 1
    
    def test_analyze_api_specifics_no_matches(self, api_analyzer):
        """Test API-specific analysis with no keyword matches."""
        conversations_without_keywords = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I have a general question'}
                    ]
                },
                'source': {'body': 'general inquiry'}
            }
        ]
        
        metrics = api_analyzer._analyze_api_specifics(conversations_without_keywords)
        
        # Should not match any API-specific keywords
        assert metrics['authentication_conversations'] == 0
        assert metrics['integration_conversations'] == 0
        assert metrics['performance_conversations'] == 0
        assert metrics['documentation_conversations'] == 0
        assert metrics['total_api_conversations'] == 1
    
    def test_analyze_api_specifics_missing_text(self, api_analyzer):
        """Test API-specific analysis with missing text fields."""
        conversations_with_missing_text = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': ''}
                    ]
                },
                'source': {'body': ''}
            },
            {
                'id': 'conv_2',
                'conversation_parts': {
                    'conversation_parts': []
                },
                'source': {}
            }
        ]
        
        metrics = api_analyzer._analyze_api_specifics(conversations_with_missing_text)
        
        # Should handle missing text gracefully
        assert metrics['authentication_conversations'] == 0
        assert metrics['integration_conversations'] == 0
        assert metrics['performance_conversations'] == 0
        assert metrics['documentation_conversations'] == 0
        assert metrics['total_api_conversations'] == 2
    
    def test_analyze_api_specifics_partial_text(self, api_analyzer):
        """Test API-specific analysis with partial text."""
        conversations_with_partial_text = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help with API authentication'}
                    ]
                }
                # Missing source
            },
            {
                'id': 'conv_2',
                'conversation_parts': {
                    'conversation_parts': []
                },
                'source': {'body': 'API integration question'}
            }
        ]
        
        metrics = api_analyzer._analyze_api_specifics(conversations_with_partial_text)
        
        # Should still match based on available text
        assert metrics['authentication_conversations'] == 1
        assert metrics['integration_conversations'] == 1
        assert metrics['total_api_conversations'] == 2
    
    def test_analyze_api_specifics_special_characters(self, api_analyzer):
        """Test API-specific analysis with special characters."""
        conversations_with_special_chars = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help with API authentication! @#$%^&*()'}
                    ]
                },
                'source': {'body': 'API auth with special chars'}
            }
        ]
        
        metrics = api_analyzer._analyze_api_specifics(conversations_with_special_chars)
        
        # Should still match despite special characters
        assert metrics['authentication_conversations'] == 1
        assert metrics['total_api_conversations'] == 1
    
    def test_analyze_api_specifics_unicode(self, api_analyzer):
        """Test API-specific analysis with unicode characters."""
        conversations_with_unicode = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help with API authentication 🔑'}
                    ]
                },
                'source': {'body': 'API auth with emoji'}
            }
        ]
        
        metrics = api_analyzer._analyze_api_specifics(conversations_with_unicode)
        
        # Should still match despite unicode characters
        assert metrics['authentication_conversations'] == 1
        assert metrics['total_api_conversations'] == 1
    
    def test_analyze_api_specifics_long_text(self, api_analyzer):
        """Test API-specific analysis with very long text."""
        long_text = "I need help with API authentication " * 1000  # Very long text
        conversations_with_long_text = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': long_text}
                    ]
                },
                'source': {'body': 'long API auth question'}
            }
        ]
        
        metrics = api_analyzer._analyze_api_specifics(conversations_with_long_text)
        
        # Should still match despite long text
        assert metrics['authentication_conversations'] == 1
        assert metrics['total_api_conversations'] == 1
    
    def test_analyze_api_specifics_mixed_content(self, api_analyzer):
        """Test API-specific analysis with mixed content types."""
        conversations_with_mixed_content = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help with API authentication'},
                        {'part_type': 'note', 'body': 'Internal note about API auth'},
                        {'part_type': 'comment', 'body': 'Also need help with API integration'}
                    ]
                },
                'source': {'body': 'mixed API auth and integration question'}
            }
        ]
        
        metrics = api_analyzer._analyze_api_specifics(conversations_with_mixed_content)
        
        # Should match both authentication and integration
        assert metrics['authentication_conversations'] == 1
        assert metrics['integration_conversations'] == 1
        assert metrics['total_api_conversations'] == 1
    
    def test_analyze_api_specifics_html_content(self, api_analyzer):
        """Test API-specific analysis with HTML content."""
        conversations_with_html = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': '<p>I need help with <strong>API authentication</strong></p>'}
                    ]
                },
                'source': {'body': '<div>API auth question</div>'}
            }
        ]
        
        metrics = api_analyzer._analyze_api_specifics(conversations_with_html)
        
        # Should still match despite HTML tags
        assert metrics['authentication_conversations'] == 1
        assert metrics['total_api_conversations'] == 1
    
    def test_analyze_api_specifics_nested_structure(self, api_analyzer):
        """Test API-specific analysis with nested conversation structure."""
        conversations_with_nested_structure = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'I need help with API authentication',
                            'nested_data': {
                                'additional_text': 'and integration'
                            }
                        }
                    ]
                },
                'source': {
                    'body': 'API auth question',
                    'nested_data': {
                        'additional_text': 'with nested structure'
                    }
                }
            }
        ]
        
        metrics = api_analyzer._analyze_api_specifics(conversations_with_nested_structure)
        
        # Should still match despite nested structure
        assert metrics['authentication_conversations'] == 1
        assert metrics['integration_conversations'] == 1
        assert metrics['total_api_conversations'] == 1
    
    def test_analyze_api_specifics_duplicate_conversations(self, api_analyzer):
        """Test API-specific analysis with duplicate conversations."""
        duplicate_conversations = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help with API authentication'}
                    ]
                },
                'source': {'body': 'API auth question'}
            },
            {
                'id': 'conv_1',  # Same ID
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help with API authentication'}
                    ]
                },
                'source': {'body': 'API auth question'}
            }
        ]
        
        metrics = api_analyzer._analyze_api_specifics(duplicate_conversations)
        
        # Should handle duplicates gracefully
        assert metrics['authentication_conversations'] == 1  # Should count unique conversations
        assert metrics['total_api_conversations'] == 1
    
    def test_analyze_api_specifics_malformed_data(self, api_analyzer):
        """Test API-specific analysis with malformed data."""
        malformed_conversations = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help with API authentication'}
                    ]
                },
                'source': {'body': 'API auth question'}
            },
            {
                'id': 'conv_2',
                # Missing conversation_parts
                'source': {'body': 'API integration question'}
            },
            {
                'id': 'conv_3',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I have a question about API integration'}
                    ]
                }
                # Missing source
            }
        ]
        
        metrics = api_analyzer._analyze_api_specifics(malformed_conversations)
        
        # Should handle malformed data gracefully
        assert metrics['authentication_conversations'] == 1
        assert metrics['integration_conversations'] == 1
        assert metrics['total_api_conversations'] == 3
    
    def test_analyze_api_specifics_edge_cases(self, api_analyzer):
        """Test API-specific analysis with edge cases."""
        edge_case_conversations = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'API'}  # Single word
                    ]
                },
                'source': {'body': 'a'}  # Single character
            },
            {
                'id': 'conv_2',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help with API authentication and integration and performance and documentation'}
                    ]
                },
                'source': {'body': 'all API keywords in one conversation'}
            }
        ]
        
        metrics = api_analyzer._analyze_api_specifics(edge_case_conversations)
        
        # Should handle edge cases gracefully
        assert metrics['authentication_conversations'] == 2
        assert metrics['integration_conversations'] == 1
        assert metrics['performance_conversations'] == 1
        assert metrics['documentation_conversations'] == 1
        assert metrics['total_api_conversations'] == 2
    
    def test_analyze_api_specifics_technical_terms(self, api_analyzer):
        """Test API-specific analysis with technical terms."""
        technical_conversations = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help with OAuth 2.0 authentication'}
                    ]
                },
                'source': {'body': 'OAuth API question'}
            },
            {
                'id': 'conv_2',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I have a question about REST API integration'}
                    ]
                },
                'source': {'body': 'REST API question'}
            },
            {
                'id': 'conv_3',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help with GraphQL API performance'}
                    ]
                },
                'source': {'body': 'GraphQL API question'}
            }
        ]
        
        metrics = api_analyzer._analyze_api_specifics(technical_conversations)
        
        # Should match technical API terms
        assert metrics['authentication_conversations'] == 1
        assert metrics['integration_conversations'] == 1
        assert metrics['performance_conversations'] == 1
        assert metrics['total_api_conversations'] == 3






