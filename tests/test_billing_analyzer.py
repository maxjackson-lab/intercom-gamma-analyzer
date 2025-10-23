"""
Unit tests for BillingAnalyzer.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from typing import List, Dict, Any

from src.analyzers.billing_analyzer import BillingAnalyzer


class TestBillingAnalyzer:
    """Test cases for BillingAnalyzer."""
    
    @pytest.fixture
    def billing_analyzer(self):
        """Create a BillingAnalyzer instance for testing."""
        with patch('analyzers.billing_analyzer.OpenAIClient'), \
             patch('analyzers.billing_analyzer.CategoryFilters'), \
             patch('analyzers.billing_analyzer.taxonomy_manager'):
            
            return BillingAnalyzer()
    
    @pytest.fixture
    def sample_billing_conversations(self):
        """Create sample billing conversation data for testing."""
        return [
            {
                'id': 'conv_billing_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'I need a refund for my subscription'
                        }
                    ]
                },
                'source': {
                    'body': 'billing issue'
                },
                'tags': {
                    'tags': [
                        {'name': 'Refund Request'}
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
                'id': 'conv_billing_2',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'I have a question about my invoice'
                        }
                    ]
                },
                'source': {
                    'body': 'invoice question'
                },
                'tags': {
                    'tags': [
                        {'name': 'Invoice'}
                    ]
                },
                'topics': {
                    'topics': [
                        {'name': 'invoice'}
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
                'id': 'conv_billing_3',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'I need a credit for the service outage'
                        }
                    ]
                },
                'source': {
                    'body': 'credit request'
                },
                'tags': {
                    'tags': [
                        {'name': 'Credit'}
                    ]
                },
                'topics': {
                    'topics': [
                        {'name': 'credit'}
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
                'id': 'conv_billing_4',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'Do you have any discounts available?'
                        }
                    ]
                },
                'source': {
                    'body': 'discount inquiry'
                },
                'tags': {
                    'tags': [
                        {'name': 'Discount'}
                    ]
                },
                'topics': {
                    'topics': [
                        {'name': 'discount'}
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
    
    def test_initialization(self, billing_analyzer):
        """Test BillingAnalyzer initialization."""
        assert billing_analyzer.category_name == "Billing"
        assert billing_analyzer.openai_client is not None
        assert billing_analyzer.category_filters is not None
        assert billing_analyzer.taxonomy_manager is not None
    
    @pytest.mark.asyncio
    async def test_analyze_category_success(self, billing_analyzer, sample_billing_conversations):
        """Test successful billing category analysis."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        options = {'generate_ai_insights': False}
        
        # Mock the category filter to return all conversations
        billing_analyzer.category_filters.filter_by_category = MagicMock(
            return_value=(sample_billing_conversations, {'filtered_count': 4})
        )
        
        result = await billing_analyzer.analyze_category(
            sample_billing_conversations, start_date, end_date, options
        )
        
        assert result['category'] == 'Billing'
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
        assert 'billing_metrics' in analysis_results
        assert 'billing_trends' in analysis_results
        assert 'billing_insights' in analysis_results
        
        # Check billing metrics
        billing_metrics = analysis_results['billing_metrics']
        assert 'refund_conversations' in billing_metrics
        assert 'invoice_conversations' in billing_metrics
        assert 'credit_conversations' in billing_metrics
        assert 'discount_conversations' in billing_metrics
        assert 'total_billing_conversations' in billing_metrics
    
    @pytest.mark.asyncio
    async def test_analyze_category_no_conversations(self, billing_analyzer):
        """Test billing category analysis with no conversations."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        options = {'generate_ai_insights': False}
        
        # Mock the category filter to return no conversations
        billing_analyzer.category_filters.filter_by_category = MagicMock(
            return_value=([], {'filtered_count': 0})
        )
        
        result = await billing_analyzer.analyze_category(
            [], start_date, end_date, options
        )
        
        assert result['category'] == 'Billing'
        assert result['data_summary']['filtered_conversations'] == 0
        assert result['data_summary']['message'] == "No conversations matched the 'Billing' category criteria."
        assert result['analysis_results'] == {}
        assert result['ai_insights'] == "No data to generate AI insights for Billing."
    
    @pytest.mark.asyncio
    async def test_analyze_category_with_ai_insights(self, billing_analyzer, sample_billing_conversations):
        """Test billing category analysis with AI insights generation."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 1, 31)
        options = {'generate_ai_insights': True}
        
        # Mock the category filter
        billing_analyzer.category_filters.filter_by_category = MagicMock(
            return_value=(sample_billing_conversations, {'filtered_count': 4})
        )
        
        # Mock the AI insights generation
        billing_analyzer._generate_ai_insights = AsyncMock(return_value="Test AI insights for billing")
        
        result = await billing_analyzer.analyze_category(
            sample_billing_conversations, start_date, end_date, options
        )
        
        assert result['ai_insights'] == "Test AI insights for billing"
        billing_analyzer._generate_ai_insights.assert_called_once()
    
    def test_analyze_billing_specifics(self, billing_analyzer, sample_billing_conversations):
        """Test billing-specific analysis."""
        metrics = billing_analyzer._analyze_billing_specifics(sample_billing_conversations)
        
        assert 'refund_conversations' in metrics
        assert 'invoice_conversations' in metrics
        assert 'credit_conversations' in metrics
        assert 'discount_conversations' in metrics
        assert 'total_billing_conversations' in metrics
        
        # Check that all conversations are counted
        assert metrics['total_billing_conversations'] == 4
        
        # Check specific counts (should be 1 for each type based on sample data)
        assert metrics['refund_conversations'] == 1
        assert metrics['invoice_conversations'] == 1
        assert metrics['credit_conversations'] == 1
        assert metrics['discount_conversations'] == 1
    
    def test_analyze_billing_specifics_empty_conversations(self, billing_analyzer):
        """Test billing-specific analysis with empty conversations."""
        metrics = billing_analyzer._analyze_billing_specifics([])
        
        assert metrics['refund_conversations'] == 0
        assert metrics['invoice_conversations'] == 0
        assert metrics['credit_conversations'] == 0
        assert metrics['discount_conversations'] == 0
        assert metrics['total_billing_conversations'] == 0
    
    def test_analyze_billing_specifics_keyword_matching(self, billing_analyzer):
        """Test billing-specific analysis with keyword matching."""
        conversations_with_keywords = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need a refund for my subscription'}
                    ]
                },
                'source': {'body': 'refund request'}
            },
            {
                'id': 'conv_2',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I have a question about my invoice'}
                    ]
                },
                'source': {'body': 'invoice question'}
            },
            {
                'id': 'conv_3',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need a credit for the service outage'}
                    ]
                },
                'source': {'body': 'credit request'}
            },
            {
                'id': 'conv_4',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'Do you have any discounts available?'}
                    ]
                },
                'source': {'body': 'discount inquiry'}
            }
        ]
        
        metrics = billing_analyzer._analyze_billing_specifics(conversations_with_keywords)
        
        # Should match based on keywords in the text
        assert metrics['refund_conversations'] == 1
        assert metrics['invoice_conversations'] == 1
        assert metrics['credit_conversations'] == 1
        assert metrics['discount_conversations'] == 1
        assert metrics['total_billing_conversations'] == 4
    
    def test_analyze_billing_specifics_case_insensitive(self, billing_analyzer):
        """Test billing-specific analysis with case insensitive matching."""
        conversations_with_uppercase = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need a REFUND for my subscription'}
                    ]
                },
                'source': {'body': 'REFUND REQUEST'}
            },
            {
                'id': 'conv_2',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I have a question about my INVOICE'}
                    ]
                },
                'source': {'body': 'INVOICE QUESTION'}
            }
        ]
        
        metrics = billing_analyzer._analyze_billing_specifics(conversations_with_uppercase)
        
        # Should match despite uppercase
        assert metrics['refund_conversations'] == 1
        assert metrics['invoice_conversations'] == 1
        assert metrics['total_billing_conversations'] == 2
    
    def test_analyze_billing_specifics_multiple_matches(self, billing_analyzer):
        """Test billing-specific analysis with multiple matches in same conversation."""
        conversation_with_multiple = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need a refund and a credit for my subscription'}
                    ]
                },
                'source': {'body': 'refund and credit request'}
            }
        ]
        
        metrics = billing_analyzer._analyze_billing_specifics(conversation_with_multiple)
        
        # Should count both refund and credit
        assert metrics['refund_conversations'] == 1
        assert metrics['credit_conversations'] == 1
        assert metrics['total_billing_conversations'] == 1
    
    def test_analyze_billing_specifics_no_matches(self, billing_analyzer):
        """Test billing-specific analysis with no keyword matches."""
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
        
        metrics = billing_analyzer._analyze_billing_specifics(conversations_without_keywords)
        
        # Should not match any billing-specific keywords
        assert metrics['refund_conversations'] == 0
        assert metrics['invoice_conversations'] == 0
        assert metrics['credit_conversations'] == 0
        assert metrics['discount_conversations'] == 0
        assert metrics['total_billing_conversations'] == 1
    
    def test_analyze_billing_specifics_missing_text(self, billing_analyzer):
        """Test billing-specific analysis with missing text fields."""
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
        
        metrics = billing_analyzer._analyze_billing_specifics(conversations_with_missing_text)
        
        # Should handle missing text gracefully
        assert metrics['refund_conversations'] == 0
        assert metrics['invoice_conversations'] == 0
        assert metrics['credit_conversations'] == 0
        assert metrics['discount_conversations'] == 0
        assert metrics['total_billing_conversations'] == 2
    
    def test_analyze_billing_specifics_partial_text(self, billing_analyzer):
        """Test billing-specific analysis with partial text."""
        conversations_with_partial_text = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need a refund'}
                    ]
                }
                # Missing source
            },
            {
                'id': 'conv_2',
                'conversation_parts': {
                    'conversation_parts': []
                },
                'source': {'body': 'invoice question'}
            }
        ]
        
        metrics = billing_analyzer._analyze_billing_specifics(conversations_with_partial_text)
        
        # Should still match based on available text
        assert metrics['refund_conversations'] == 1
        assert metrics['invoice_conversations'] == 1
        assert metrics['total_billing_conversations'] == 2
    
    def test_analyze_billing_specifics_special_characters(self, billing_analyzer):
        """Test billing-specific analysis with special characters."""
        conversations_with_special_chars = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need a refund! @#$%^&*()'}
                    ]
                },
                'source': {'body': 'refund request with special chars'}
            }
        ]
        
        metrics = billing_analyzer._analyze_billing_specifics(conversations_with_special_chars)
        
        # Should still match despite special characters
        assert metrics['refund_conversations'] == 1
        assert metrics['total_billing_conversations'] == 1
    
    def test_analyze_billing_specifics_unicode(self, billing_analyzer):
        """Test billing-specific analysis with unicode characters."""
        conversations_with_unicode = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need a refund for my subscription 🚀'}
                    ]
                },
                'source': {'body': 'refund request with emoji'}
            }
        ]
        
        metrics = billing_analyzer._analyze_billing_specifics(conversations_with_unicode)
        
        # Should still match despite unicode characters
        assert metrics['refund_conversations'] == 1
        assert metrics['total_billing_conversations'] == 1
    
    def test_analyze_billing_specifics_long_text(self, billing_analyzer):
        """Test billing-specific analysis with very long text."""
        long_text = "I need a refund " * 1000  # Very long text
        conversations_with_long_text = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': long_text}
                    ]
                },
                'source': {'body': 'long refund request'}
            }
        ]
        
        metrics = billing_analyzer._analyze_billing_specifics(conversations_with_long_text)
        
        # Should still match despite long text
        assert metrics['refund_conversations'] == 1
        assert metrics['total_billing_conversations'] == 1
    
    def test_analyze_billing_specifics_mixed_content(self, billing_analyzer):
        """Test billing-specific analysis with mixed content types."""
        conversations_with_mixed_content = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'I need a refund'},
                        {'part_type': 'note', 'body': 'Internal note about refund'},
                        {'part_type': 'comment', 'body': 'Also need a credit'}
                    ]
                },
                'source': {'body': 'mixed refund and credit request'}
            }
        ]
        
        metrics = billing_analyzer._analyze_billing_specifics(conversations_with_mixed_content)
        
        # Should match both refund and credit
        assert metrics['refund_conversations'] == 1
        assert metrics['credit_conversations'] == 1
        assert metrics['total_billing_conversations'] == 1
    
    def test_analyze_billing_specifics_html_content(self, billing_analyzer):
        """Test billing-specific analysis with HTML content."""
        conversations_with_html = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': '<p>I need a <strong>refund</strong> for my subscription</p>'}
                    ]
                },
                'source': {'body': '<div>refund request</div>'}
            }
        ]
        
        metrics = billing_analyzer._analyze_billing_specifics(conversations_with_html)
        
        # Should still match despite HTML tags
        assert metrics['refund_conversations'] == 1
        assert metrics['total_billing_conversations'] == 1
    
    def test_analyze_billing_specifics_nested_structure(self, billing_analyzer):
        """Test billing-specific analysis with nested conversation structure."""
        conversations_with_nested_structure = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'I need a refund',
                            'nested_data': {
                                'additional_text': 'for my subscription'
                            }
                        }
                    ]
                },
                'source': {
                    'body': 'refund request',
                    'nested_data': {
                        'additional_text': 'with nested structure'
                    }
                }
            }
        ]
        
        metrics = billing_analyzer._analyze_billing_specifics(conversations_with_nested_structure)
        
        # Should still match despite nested structure
        assert metrics['refund_conversations'] == 1
        assert metrics['total_billing_conversations'] == 1






