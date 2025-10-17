"""
Unit tests for ProductAnalyzer.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from typing import List, Dict, Any

from analyzers.product_analyzer import ProductAnalyzer


class TestProductAnalyzer:
    """Test cases for ProductAnalyzer."""
    
    @pytest.fixture
    def product_analyzer(self):
        """Create a ProductAnalyzer instance for testing."""
        with patch('analyzers.product_analyzer.OpenAIClient'), \
             patch('analyzers.product_analyzer.CategoryFilters'), \
             patch('analyzers.product_analyzer.taxonomy_manager'):
            
            return ProductAnalyzer()
    
    @pytest.fixture
    def sample_product_conversations(self):
        """Create sample product conversation data for testing."""
        return [
            {
                'id': 'conv_product_1',
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
                    'id': 'agent_1',
                    'name': 'Dae-Ho'
                },
                'created_at': 1640995200,  # 2022-01-01
                'updated_at': 1640995200
            },
            {
                'id': 'conv_product_2',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'I need help with the product features'
                        }
                    ]
                },
                'source': {
                    'body': 'product question'
                },
                'tags': {
                    'tags': [
                        {'name': 'Product Question'}
                    ]
                },
                'topics': {
                    'topics': [
                        {'name': 'product'}
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
                'id': 'conv_product_3',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'I would like to request a new feature'
                        }
                    ]
                },
                'source': {
                    'body': 'feature request'
                },
                'tags': {
                    'tags': [
                        {'name': 'Feature Request'}
                    ]
                },
                'topics': {
                    'topics': [
                        {'name': 'feature'}
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
                'id': 'conv_product_4',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'The product is not working as expected'
                        }
                    ]
                },
                'source': {
                    'body': 'product issue'
                },
                'tags': {
                    'tags': [
                        {'name': 'Product Issue'}
                    ]
                },
                'topics': {
                    'topics': [
                        {'name': 'product'}
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
    
    def test_initialization(self, product_analyzer):
        """Test ProductAnalyzer initialization."""
        assert product_analyzer.category_name == "Product"
        assert product_analyzer.openai_client is not None
        assert product_analyzer.category_filters is not None
        assert product_analyzer.taxonomy_manager is not None
    
    @pytest.mark.asyncio
    async def test_analyze_category_success(self, product_analyzer, sample_product_conversations):
        """Test successful product category analysis."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        options = {'generate_ai_insights': False}
        
        # Mock the category filters to return conversations
        product_analyzer.category_filters.filter_by_category = MagicMock(
            side_effect=[
                (sample_product_conversations[:2], {'filtered_count': 2}),  # Bug conversations
                (sample_product_conversations[2:], {'filtered_count': 2})   # Product Question conversations
            ]
        )
        
        result = await product_analyzer.analyze_category(
            sample_product_conversations, start_date, end_date, options
        )
        
        assert result['category'] == 'Product'
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
        assert 'product_metrics' in analysis_results
        assert 'product_trends' in analysis_results
        assert 'product_insights' in analysis_results
        
        # Check product metrics
        product_metrics = analysis_results['product_metrics']
        assert 'export_issue_count' in product_metrics
        assert 'bug_report_count' in product_metrics
        assert 'feature_request_count' in product_metrics
        assert 'total_product_conversations' in product_metrics
    
    @pytest.mark.asyncio
    async def test_analyze_category_no_conversations(self, product_analyzer):
        """Test product category analysis with no conversations."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        options = {'generate_ai_insights': False}
        
        # Mock the category filters to return no conversations
        product_analyzer.category_filters.filter_by_category = MagicMock(
            return_value=([], {'filtered_count': 0})
        )
        
        result = await product_analyzer.analyze_category(
            [], start_date, end_date, options
        )
        
        assert result['category'] == 'Product'
        assert result['data_summary']['filtered_conversations'] == 0
        assert result['data_summary']['message'] == "No conversations matched the 'Product' category criteria."
        assert result['analysis_results'] == {}
        assert result['ai_insights'] == "No data to generate AI insights for Product."
    
    @pytest.mark.asyncio
    async def test_analyze_category_with_ai_insights(self, product_analyzer, sample_product_conversations):
        """Test product category analysis with AI insights generation."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        options = {'generate_ai_insights': True}
        
        # Mock the category filters
        product_analyzer.category_filters.filter_by_category = MagicMock(
            side_effect=[
                (sample_product_conversations[:2], {'filtered_count': 2}),
                (sample_product_conversations[2:], {'filtered_count': 2})
            ]
        )
        
        # Mock the AI insights generation
        product_analyzer._generate_ai_insights = AsyncMock(return_value="Test AI insights for product")
        
        result = await product_analyzer.analyze_category(
            sample_product_conversations, start_date, end_date, options
        )
        
        assert result['ai_insights'] == "Test AI insights for product"
        product_analyzer._generate_ai_insights.assert_called_once()
    
    def test_analyze_product_specifics(self, product_analyzer, sample_product_conversations):
        """Test product-specific analysis."""
        metrics = product_analyzer._analyze_product_specifics(sample_product_conversations)
        
        assert 'export_issue_count' in metrics
        assert 'bug_report_count' in metrics
        assert 'feature_request_count' in metrics
        assert 'total_product_conversations' in metrics
        
        # Check that all conversations are counted
        assert metrics['total_product_conversations'] == 4
        
        # Check specific counts (should be 1 for each type based on sample data)
        assert metrics['export_issue_count'] == 1
        assert metrics['bug_report_count'] == 1
        assert metrics['feature_request_count'] == 1
    
    def test_analyze_product_specifics_empty_conversations(self, product_analyzer):
        """Test product-specific analysis with empty conversations."""
        metrics = product_analyzer._analyze_product_specifics([])
        
        assert metrics['export_issue_count'] == 0
        assert metrics['bug_report_count'] == 0
        assert metrics['feature_request_count'] == 0
        assert metrics['total_product_conversations'] == 0
    
    def test_analyze_product_specifics_keyword_matching(self, product_analyzer):
        """Test product-specific analysis with keyword matching."""
        conversations_with_keywords = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I have a bug with the export feature'}
                    ]
                },
                'source': {'body': 'export not working'}
            },
            {
                'id': 'conv_2',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I found a bug in the system'}
                    ]
                },
                'source': {'body': 'bug report'}
            },
            {
                'id': 'conv_3',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I would like to request a new feature'}
                    ]
                },
                'source': {'body': 'feature request'}
            }
        ]
        
        metrics = product_analyzer._analyze_product_specifics(conversations_with_keywords)
        
        # Should match based on keywords in the text
        assert metrics['export_issue_count'] == 1
        assert metrics['bug_report_count'] == 1
        assert metrics['feature_request_count'] == 1
        assert metrics['total_product_conversations'] == 3
    
    def test_analyze_product_specifics_case_insensitive(self, product_analyzer):
        """Test product-specific analysis with case insensitive matching."""
        conversations_with_uppercase = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I have a BUG with the EXPORT feature'}
                    ]
                },
                'source': {'body': 'EXPORT NOT WORKING'}
            },
            {
                'id': 'conv_2',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I would like to request a new FEATURE'}
                    ]
                },
                'source': {'body': 'FEATURE REQUEST'}
            }
        ]
        
        metrics = product_analyzer._analyze_product_specifics(conversations_with_uppercase)
        
        # Should match despite uppercase
        assert metrics['export_issue_count'] == 1
        assert metrics['bug_report_count'] == 1
        assert metrics['feature_request_count'] == 1
        assert metrics['total_product_conversations'] == 2
    
    def test_analyze_product_specifics_multiple_matches(self, product_analyzer):
        """Test product-specific analysis with multiple matches in same conversation."""
        conversation_with_multiple = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I have a bug with the export feature and would like to request a new feature'}
                    ]
                },
                'source': {'body': 'bug and feature request'}
            }
        ]
        
        metrics = product_analyzer._analyze_product_specifics(conversation_with_multiple)
        
        # Should count both export issue and feature request
        assert metrics['export_issue_count'] == 1
        assert metrics['bug_report_count'] == 1
        assert metrics['feature_request_count'] == 1
        assert metrics['total_product_conversations'] == 1
    
    def test_analyze_product_specifics_no_matches(self, product_analyzer):
        """Test product-specific analysis with no keyword matches."""
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
        
        metrics = product_analyzer._analyze_product_specifics(conversations_without_keywords)
        
        # Should not match any product-specific keywords
        assert metrics['export_issue_count'] == 0
        assert metrics['bug_report_count'] == 0
        assert metrics['feature_request_count'] == 0
        assert metrics['total_product_conversations'] == 1
    
    def test_analyze_product_specifics_missing_text(self, product_analyzer):
        """Test product-specific analysis with missing text fields."""
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
        
        metrics = product_analyzer._analyze_product_specifics(conversations_with_missing_text)
        
        # Should handle missing text gracefully
        assert metrics['export_issue_count'] == 0
        assert metrics['bug_report_count'] == 0
        assert metrics['feature_request_count'] == 0
        assert metrics['total_product_conversations'] == 2
    
    def test_analyze_product_specifics_partial_text(self, product_analyzer):
        """Test product-specific analysis with partial text."""
        conversations_with_partial_text = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I have a bug with the export feature'}
                    ]
                }
                # Missing source
            },
            {
                'id': 'conv_2',
                'conversation_parts': {
                    'conversation_parts': []
                },
                'source': {'body': 'feature request'}
            }
        ]
        
        metrics = product_analyzer._analyze_product_specifics(conversations_with_partial_text)
        
        # Should still match based on available text
        assert metrics['export_issue_count'] == 1
        assert metrics['bug_report_count'] == 1
        assert metrics['feature_request_count'] == 1
        assert metrics['total_product_conversations'] == 2
    
    def test_analyze_product_specifics_special_characters(self, product_analyzer):
        """Test product-specific analysis with special characters."""
        conversations_with_special_chars = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I have a bug with the export feature! @#$%^&*()'}
                    ]
                },
                'source': {'body': 'export issue with special chars'}
            }
        ]
        
        metrics = product_analyzer._analyze_product_specifics(conversations_with_special_chars)
        
        # Should still match despite special characters
        assert metrics['export_issue_count'] == 1
        assert metrics['bug_report_count'] == 1
        assert metrics['total_product_conversations'] == 1
    
    def test_analyze_product_specifics_unicode(self, product_analyzer):
        """Test product-specific analysis with unicode characters."""
        conversations_with_unicode = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I have a bug with the export feature 🐛'}
                    ]
                },
                'source': {'body': 'export issue with emoji'}
            }
        ]
        
        metrics = product_analyzer._analyze_product_specifics(conversations_with_unicode)
        
        # Should still match despite unicode characters
        assert metrics['export_issue_count'] == 1
        assert metrics['bug_report_count'] == 1
        assert metrics['total_product_conversations'] == 1
    
    def test_analyze_product_specifics_long_text(self, product_analyzer):
        """Test product-specific analysis with very long text."""
        long_text = "I have a bug with the export feature " * 1000  # Very long text
        conversations_with_long_text = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': long_text}
                    ]
                },
                'source': {'body': 'long export issue'}
            }
        ]
        
        metrics = product_analyzer._analyze_product_specifics(conversations_with_long_text)
        
        # Should still match despite long text
        assert metrics['export_issue_count'] == 1
        assert metrics['bug_report_count'] == 1
        assert metrics['total_product_conversations'] == 1
    
    def test_analyze_product_specifics_mixed_content(self, product_analyzer):
        """Test product-specific analysis with mixed content types."""
        conversations_with_mixed_content = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I have a bug with the export feature'},
                        {'part_type': 'note', 'body': 'Internal note about export issue'},
                        {'part_type': 'comment', 'body': 'Also would like to request a new feature'}
                    ]
                },
                'source': {'body': 'mixed export and feature request'}
            }
        ]
        
        metrics = product_analyzer._analyze_product_specifics(conversations_with_mixed_content)
        
        # Should match both export issue and feature request
        assert metrics['export_issue_count'] == 1
        assert metrics['bug_report_count'] == 1
        assert metrics['feature_request_count'] == 1
        assert metrics['total_product_conversations'] == 1
    
    def test_analyze_product_specifics_html_content(self, product_analyzer):
        """Test product-specific analysis with HTML content."""
        conversations_with_html = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': '<p>I have a <strong>bug</strong> with the export feature</p>'}
                    ]
                },
                'source': {'body': '<div>export issue</div>'}
            }
        ]
        
        metrics = product_analyzer._analyze_product_specifics(conversations_with_html)
        
        # Should still match despite HTML tags
        assert metrics['export_issue_count'] == 1
        assert metrics['bug_report_count'] == 1
        assert metrics['total_product_conversations'] == 1
    
    def test_analyze_product_specifics_nested_structure(self, product_analyzer):
        """Test product-specific analysis with nested conversation structure."""
        conversations_with_nested_structure = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'I have a bug with the export feature',
                            'nested_data': {
                                'additional_text': 'and need help'
                            }
                        }
                    ]
                },
                'source': {
                    'body': 'export issue',
                    'nested_data': {
                        'additional_text': 'with nested structure'
                    }
                }
            }
        ]
        
        metrics = product_analyzer._analyze_product_specifics(conversations_with_nested_structure)
        
        # Should still match despite nested structure
        assert metrics['export_issue_count'] == 1
        assert metrics['bug_report_count'] == 1
        assert metrics['total_product_conversations'] == 1
    
    def test_analyze_product_specifics_duplicate_conversations(self, product_analyzer):
        """Test product-specific analysis with duplicate conversations."""
        duplicate_conversations = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I have a bug with the export feature'}
                    ]
                },
                'source': {'body': 'export issue'}
            },
            {
                'id': 'conv_1',  # Same ID
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I have a bug with the export feature'}
                    ]
                },
                'source': {'body': 'export issue'}
            }
        ]
        
        metrics = product_analyzer._analyze_product_specifics(duplicate_conversations)
        
        # Should handle duplicates gracefully
        assert metrics['export_issue_count'] == 1  # Should count unique conversations
        assert metrics['bug_report_count'] == 1
        assert metrics['total_product_conversations'] == 1
    
    def test_analyze_product_specifics_malformed_data(self, product_analyzer):
        """Test product-specific analysis with malformed data."""
        malformed_conversations = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I have a bug with the export feature'}
                    ]
                },
                'source': {'body': 'export issue'}
            },
            {
                'id': 'conv_2',
                # Missing conversation_parts
                'source': {'body': 'feature request'}
            },
            {
                'id': 'conv_3',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I would like to request a new feature'}
                    ]
                }
                # Missing source
            }
        ]
        
        metrics = product_analyzer._analyze_product_specifics(malformed_conversations)
        
        # Should handle malformed data gracefully
        assert metrics['export_issue_count'] == 1
        assert metrics['bug_report_count'] == 1
        assert metrics['feature_request_count'] == 1
        assert metrics['total_product_conversations'] == 3






