"""
Unit tests for SitesAnalyzer.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from typing import List, Dict, Any

from src.analyzers.sites_analyzer import SitesAnalyzer


class TestSitesAnalyzer:
    """Test cases for SitesAnalyzer."""
    
    @pytest.fixture
    def sites_analyzer(self):
        """Create a SitesAnalyzer instance for testing."""
        with patch('analyzers.sites_analyzer.OpenAIClient'), \
             patch('analyzers.sites_analyzer.CategoryFilters'), \
             patch('analyzers.sites_analyzer.taxonomy_manager'):
            
            return SitesAnalyzer()
    
    @pytest.fixture
    def sample_sites_conversations(self):
        """Create sample sites conversation data for testing."""
        return [
            {
                'id': 'conv_sites_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'I need help setting up my domain'
                        }
                    ]
                },
                'source': {
                    'body': 'domain setup question'
                },
                'tags': {
                    'tags': [
                        {'name': 'Domain Setup'}
                    ]
                },
                'topics': {
                    'topics': [
                        {'name': 'domain'}
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
                'id': 'conv_sites_2',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'I have a question about publishing my site'
                        }
                    ]
                },
                'source': {
                    'body': 'publishing question'
                },
                'tags': {
                    'tags': [
                        {'name': 'Publishing'}
                    ]
                },
                'topics': {
                    'topics': [
                        {'name': 'publishing'}
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
                'id': 'conv_sites_3',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'I need help with the education features'
                        }
                    ]
                },
                'source': {
                    'body': 'education question'
                },
                'tags': {
                    'tags': [
                        {'name': 'Education'}
                    ]
                },
                'topics': {
                    'topics': [
                        {'name': 'education'}
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
                'id': 'conv_sites_4',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'I have a question about my website'
                        }
                    ]
                },
                'source': {
                    'body': 'website question'
                },
                'tags': {
                    'tags': [
                        {'name': 'Website'}
                    ]
                },
                'topics': {
                    'topics': [
                        {'name': 'website'}
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
    
    def test_initialization(self, sites_analyzer):
        """Test SitesAnalyzer initialization."""
        assert sites_analyzer.category_name == "Sites"
        assert sites_analyzer.openai_client is not None
        assert sites_analyzer.category_filters is not None
        assert sites_analyzer.taxonomy_manager is not None
    
    @pytest.mark.asyncio
    async def test_analyze_category_success(self, sites_analyzer, sample_sites_conversations):
        """Test successful sites category analysis."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        options = {'generate_ai_insights': False}
        
        # Mock the category filter to return all conversations
        sites_analyzer.category_filters.filter_by_category = MagicMock(
            return_value=(sample_sites_conversations, {'filtered_count': 4})
        )
        
        result = await sites_analyzer.analyze_category(
            sample_sites_conversations, start_date, end_date, options
        )
        
        assert result['category'] == 'Sites'
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
        assert 'sites_metrics' in analysis_results
        assert 'sites_trends' in analysis_results
        assert 'sites_insights' in analysis_results
        
        # Check sites metrics
        sites_metrics = analysis_results['sites_metrics']
        assert 'domain_conversations' in sites_metrics
        assert 'publishing_conversations' in sites_metrics
        assert 'education_conversations' in sites_metrics
        assert 'website_conversations' in sites_metrics
        assert 'total_sites_conversations' in sites_metrics
    
    @pytest.mark.asyncio
    async def test_analyze_category_no_conversations(self, sites_analyzer):
        """Test sites category analysis with no conversations."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        options = {'generate_ai_insights': False}
        
        # Mock the category filter to return no conversations
        sites_analyzer.category_filters.filter_by_category = MagicMock(
            return_value=([], {'filtered_count': 0})
        )
        
        result = await sites_analyzer.analyze_category(
            [], start_date, end_date, options
        )
        
        assert result['category'] == 'Sites'
        assert result['data_summary']['filtered_conversations'] == 0
        assert result['data_summary']['message'] == "No conversations matched the 'Sites' category criteria."
        assert result['analysis_results'] == {}
        assert result['ai_insights'] == "No data to generate AI insights for Sites."
    
    @pytest.mark.asyncio
    async def test_analyze_category_with_ai_insights(self, sites_analyzer, sample_sites_conversations):
        """Test sites category analysis with AI insights generation."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        options = {'generate_ai_insights': True}
        
        # Mock the category filter
        sites_analyzer.category_filters.filter_by_category = MagicMock(
            return_value=(sample_sites_conversations, {'filtered_count': 4})
        )
        
        # Mock the AI insights generation
        sites_analyzer._generate_ai_insights = AsyncMock(return_value="Test AI insights for sites")
        
        result = await sites_analyzer.analyze_category(
            sample_sites_conversations, start_date, end_date, options
        )
        
        assert result['ai_insights'] == "Test AI insights for sites"
        sites_analyzer._generate_ai_insights.assert_called_once()
    
    def test_analyze_sites_specifics(self, sites_analyzer, sample_sites_conversations):
        """Test sites-specific analysis."""
        metrics = sites_analyzer._analyze_sites_specifics(sample_sites_conversations)
        
        assert 'domain_conversations' in metrics
        assert 'publishing_conversations' in metrics
        assert 'education_conversations' in metrics
        assert 'website_conversations' in metrics
        assert 'total_sites_conversations' in metrics
        
        # Check that all conversations are counted
        assert metrics['total_sites_conversations'] == 4
        
        # Check specific counts (should be 1 for each type based on sample data)
        assert metrics['domain_conversations'] == 1
        assert metrics['publishing_conversations'] == 1
        assert metrics['education_conversations'] == 1
        assert metrics['website_conversations'] == 1
    
    def test_analyze_sites_specifics_empty_conversations(self, sites_analyzer):
        """Test sites-specific analysis with empty conversations."""
        metrics = sites_analyzer._analyze_sites_specifics([])
        
        assert metrics['domain_conversations'] == 0
        assert metrics['publishing_conversations'] == 0
        assert metrics['education_conversations'] == 0
        assert metrics['website_conversations'] == 0
        assert metrics['total_sites_conversations'] == 0
    
    def test_analyze_sites_specifics_keyword_matching(self, sites_analyzer):
        """Test sites-specific analysis with keyword matching."""
        conversations_with_keywords = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help setting up my domain'}
                    ]
                },
                'source': {'body': 'domain setup question'}
            },
            {
                'id': 'conv_2',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I have a question about publishing my site'}
                    ]
                },
                'source': {'body': 'publishing question'}
            },
            {
                'id': 'conv_3',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help with the education features'}
                    ]
                },
                'source': {'body': 'education question'}
            },
            {
                'id': 'conv_4',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I have a question about my website'}
                    ]
                },
                'source': {'body': 'website question'}
            }
        ]
        
        metrics = sites_analyzer._analyze_sites_specifics(conversations_with_keywords)
        
        # Should match based on keywords in the text
        assert metrics['domain_conversations'] == 1
        assert metrics['publishing_conversations'] == 1
        assert metrics['education_conversations'] == 1
        assert metrics['website_conversations'] == 1
        assert metrics['total_sites_conversations'] == 4
    
    def test_analyze_sites_specifics_case_insensitive(self, sites_analyzer):
        """Test sites-specific analysis with case insensitive matching."""
        conversations_with_uppercase = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help setting up my DOMAIN'}
                    ]
                },
                'source': {'body': 'DOMAIN SETUP QUESTION'}
            },
            {
                'id': 'conv_2',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I have a question about PUBLISHING my site'}
                    ]
                },
                'source': {'body': 'PUBLISHING QUESTION'}
            }
        ]
        
        metrics = sites_analyzer._analyze_sites_specifics(conversations_with_uppercase)
        
        # Should match despite uppercase
        assert metrics['domain_conversations'] == 1
        assert metrics['publishing_conversations'] == 1
        assert metrics['total_sites_conversations'] == 2
    
    def test_analyze_sites_specifics_multiple_matches(self, sites_analyzer):
        """Test sites-specific analysis with multiple matches in same conversation."""
        conversation_with_multiple = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help setting up my domain and publishing my site'}
                    ]
                },
                'source': {'body': 'domain and publishing question'}
            }
        ]
        
        metrics = sites_analyzer._analyze_sites_specifics(conversation_with_multiple)
        
        # Should count both domain and publishing
        assert metrics['domain_conversations'] == 1
        assert metrics['publishing_conversations'] == 1
        assert metrics['total_sites_conversations'] == 1
    
    def test_analyze_sites_specifics_no_matches(self, sites_analyzer):
        """Test sites-specific analysis with no keyword matches."""
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
        
        metrics = sites_analyzer._analyze_sites_specifics(conversations_without_keywords)
        
        # Should not match any sites-specific keywords
        assert metrics['domain_conversations'] == 0
        assert metrics['publishing_conversations'] == 0
        assert metrics['education_conversations'] == 0
        assert metrics['website_conversations'] == 0
        assert metrics['total_sites_conversations'] == 1
    
    def test_analyze_sites_specifics_missing_text(self, sites_analyzer):
        """Test sites-specific analysis with missing text fields."""
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
        
        metrics = sites_analyzer._analyze_sites_specifics(conversations_with_missing_text)
        
        # Should handle missing text gracefully
        assert metrics['domain_conversations'] == 0
        assert metrics['publishing_conversations'] == 0
        assert metrics['education_conversations'] == 0
        assert metrics['website_conversations'] == 0
        assert metrics['total_sites_conversations'] == 2
    
    def test_analyze_sites_specifics_partial_text(self, sites_analyzer):
        """Test sites-specific analysis with partial text."""
        conversations_with_partial_text = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help setting up my domain'}
                    ]
                }
                # Missing source
            },
            {
                'id': 'conv_2',
                'conversation_parts': {
                    'conversation_parts': []
                },
                'source': {'body': 'publishing question'}
            }
        ]
        
        metrics = sites_analyzer._analyze_sites_specifics(conversations_with_partial_text)
        
        # Should still match based on available text
        assert metrics['domain_conversations'] == 1
        assert metrics['publishing_conversations'] == 1
        assert metrics['total_sites_conversations'] == 2
    
    def test_analyze_sites_specifics_special_characters(self, sites_analyzer):
        """Test sites-specific analysis with special characters."""
        conversations_with_special_chars = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help setting up my domain! @#$%^&*()'}
                    ]
                },
                'source': {'body': 'domain setup with special chars'}
            }
        ]
        
        metrics = sites_analyzer._analyze_sites_specifics(conversations_with_special_chars)
        
        # Should still match despite special characters
        assert metrics['domain_conversations'] == 1
        assert metrics['total_sites_conversations'] == 1
    
    def test_analyze_sites_specifics_unicode(self, sites_analyzer):
        """Test sites-specific analysis with unicode characters."""
        conversations_with_unicode = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help setting up my domain 🌐'}
                    ]
                },
                'source': {'body': 'domain setup with emoji'}
            }
        ]
        
        metrics = sites_analyzer._analyze_sites_specifics(conversations_with_unicode)
        
        # Should still match despite unicode characters
        assert metrics['domain_conversations'] == 1
        assert metrics['total_sites_conversations'] == 1
    
    def test_analyze_sites_specifics_long_text(self, sites_analyzer):
        """Test sites-specific analysis with very long text."""
        long_text = "I need help setting up my domain " * 1000  # Very long text
        conversations_with_long_text = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': long_text}
                    ]
                },
                'source': {'body': 'long domain setup question'}
            }
        ]
        
        metrics = sites_analyzer._analyze_sites_specifics(conversations_with_long_text)
        
        # Should still match despite long text
        assert metrics['domain_conversations'] == 1
        assert metrics['total_sites_conversations'] == 1
    
    def test_analyze_sites_specifics_mixed_content(self, sites_analyzer):
        """Test sites-specific analysis with mixed content types."""
        conversations_with_mixed_content = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help setting up my domain'},
                        {'part_type': 'note', 'body': 'Internal note about domain setup'},
                        {'part_type': 'comment', 'body': 'Also need help with publishing'}
                    ]
                },
                'source': {'body': 'mixed domain and publishing question'}
            }
        ]
        
        metrics = sites_analyzer._analyze_sites_specifics(conversations_with_mixed_content)
        
        # Should match both domain and publishing
        assert metrics['domain_conversations'] == 1
        assert metrics['publishing_conversations'] == 1
        assert metrics['total_sites_conversations'] == 1
    
    def test_analyze_sites_specifics_html_content(self, sites_analyzer):
        """Test sites-specific analysis with HTML content."""
        conversations_with_html = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': '<p>I need help setting up my <strong>domain</strong></p>'}
                    ]
                },
                'source': {'body': '<div>domain setup question</div>'}
            }
        ]
        
        metrics = sites_analyzer._analyze_sites_specifics(conversations_with_html)
        
        # Should still match despite HTML tags
        assert metrics['domain_conversations'] == 1
        assert metrics['total_sites_conversations'] == 1
    
    def test_analyze_sites_specifics_nested_structure(self, sites_analyzer):
        """Test sites-specific analysis with nested conversation structure."""
        conversations_with_nested_structure = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'I need help setting up my domain',
                            'nested_data': {
                                'additional_text': 'and publishing my site'
                            }
                        }
                    ]
                },
                'source': {
                    'body': 'domain setup question',
                    'nested_data': {
                        'additional_text': 'with nested structure'
                    }
                }
            }
        ]
        
        metrics = sites_analyzer._analyze_sites_specifics(conversations_with_nested_structure)
        
        # Should still match despite nested structure
        assert metrics['domain_conversations'] == 1
        assert metrics['publishing_conversations'] == 1
        assert metrics['total_sites_conversations'] == 1
    
    def test_analyze_sites_specifics_duplicate_conversations(self, sites_analyzer):
        """Test sites-specific analysis with duplicate conversations."""
        duplicate_conversations = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help setting up my domain'}
                    ]
                },
                'source': {'body': 'domain setup question'}
            },
            {
                'id': 'conv_1',  # Same ID
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help setting up my domain'}
                    ]
                },
                'source': {'body': 'domain setup question'}
            }
        ]
        
        metrics = sites_analyzer._analyze_sites_specifics(duplicate_conversations)
        
        # Should handle duplicates gracefully
        assert metrics['domain_conversations'] == 1  # Should count unique conversations
        assert metrics['total_sites_conversations'] == 1
    
    def test_analyze_sites_specifics_malformed_data(self, sites_analyzer):
        """Test sites-specific analysis with malformed data."""
        malformed_conversations = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help setting up my domain'}
                    ]
                },
                'source': {'body': 'domain setup question'}
            },
            {
                'id': 'conv_2',
                # Missing conversation_parts
                'source': {'body': 'publishing question'}
            },
            {
                'id': 'conv_3',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I have a question about publishing my site'}
                    ]
                }
                # Missing source
            }
        ]
        
        metrics = sites_analyzer._analyze_sites_specifics(malformed_conversations)
        
        # Should handle malformed data gracefully
        assert metrics['domain_conversations'] == 1
        assert metrics['publishing_conversations'] == 1
        assert metrics['total_sites_conversations'] == 3
    
    def test_analyze_sites_specifics_edge_cases(self, sites_analyzer):
        """Test sites-specific analysis with edge cases."""
        edge_case_conversations = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'domain'}  # Single word
                    ]
                },
                'source': {'body': 'd'}  # Single character
            },
            {
                'id': 'conv_2',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need help with domain setup and publishing and education and website'}
                    ]
                },
                'source': {'body': 'all keywords in one conversation'}
            }
        ]
        
        metrics = sites_analyzer._analyze_sites_specifics(edge_case_conversations)
        
        # Should handle edge cases gracefully
        assert metrics['domain_conversations'] == 2
        assert metrics['publishing_conversations'] == 1
        assert metrics['education_conversations'] == 1
        assert metrics['website_conversations'] == 1
        assert metrics['total_sites_conversations'] == 2






