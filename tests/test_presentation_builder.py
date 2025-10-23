"""
Unit tests for PresentationBuilder service.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from src.services.presentation_builder import PresentationBuilder


class TestPresentationBuilder:
    """Test cases for PresentationBuilder."""
    
    @pytest.fixture
    def presentation_builder(self):
        """Create a PresentationBuilder instance for testing."""
        with patch('services.presentation_builder.settings') as mock_settings:
            mock_settings.intercom_workspace_id = "test_workspace_id"
            return PresentationBuilder()
    
    @pytest.fixture
    def sample_analysis_results(self):
        """Create sample analysis results for testing."""
        return {
            'conversations': [
                {
                    'id': 'conv_1',
                    'created_at': '2024-01-01T10:00:00Z',
                    'state': 'closed',
                    'conversation_parts': {
                        'conversation_parts': [
                            {
                                'author': {'type': 'user'},
                                'body': 'I need help with my billing issue. The charge seems incorrect.'
                            }
                        ]
                    },
                    'contacts': {
                        'contacts': [
                            {'name': 'John Doe', 'email': 'john@example.com'}
                        ]
                    },
                    'tags': {
                        'tags': [
                            {'name': 'Billing'},
                            {'name': 'Refund'}
                        ]
                    }
                },
                {
                    'id': 'conv_2',
                    'created_at': '2024-01-02T11:00:00Z',
                    'state': 'open',
                    'conversation_parts': {
                        'conversation_parts': [
                            {
                                'author': {'type': 'user'},
                                'body': 'The API is not working properly. Getting 500 errors.'
                            }
                        ]
                    },
                    'contacts': {
                        'contacts': [
                            {'name': 'Jane Smith', 'email': 'jane@example.com'}
                        ]
                    },
                    'tags': {
                        'tags': [
                            {'name': 'API'},
                            {'name': 'Technical'}
                        ]
                    }
                }
            ],
            'category_results': {
                'Billing': {
                    'conversation_count': 1,
                    'percentage': 50.0,
                    'escalation_rate': 20.0,
                    'avg_response_time': '2.5 hours',
                    'top_issues': ['refund', 'charge', 'invoice'],
                    'resolution_rate': 80.0
                },
                'API': {
                    'conversation_count': 1,
                    'percentage': 50.0,
                    'escalation_rate': 15.0,
                    'avg_response_time': '1.8 hours',
                    'top_issues': ['error', 'integration', 'timeout'],
                    'resolution_rate': 85.0
                }
            },
            'start_date': '2024-01-01',
            'end_date': '2024-01-31'
        }
    
    def test_presentation_builder_initialization(self, presentation_builder):
        """Test PresentationBuilder initializes correctly."""
        assert presentation_builder.workspace_id == "test_workspace_id"
    
    def test_build_narrative_content_executive_style(self, presentation_builder, sample_analysis_results):
        """Test executive style narrative generation."""
        result = presentation_builder.build_narrative_content(
            sample_analysis_results, 
            style="executive"
        )
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Executive Summary" in result
        assert "Customer Support Analysis" in result
        assert "Recommendations" in result or "Actions" in result
        assert "2024-01-01 to 2024-01-31" in result
    
    def test_build_narrative_content_detailed_style(self, presentation_builder, sample_analysis_results):
        """Test detailed style narrative generation."""
        result = presentation_builder.build_narrative_content(
            sample_analysis_results, 
            style="detailed"
        )
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Comprehensive Customer Support Analysis" in result
        assert "Category Breakdown" in result
        assert "Performance" in result or "Analysis" in result
        assert "Recommendations" in result or "Improvement" in result
    
    def test_build_narrative_content_training_style(self, presentation_builder, sample_analysis_results):
        """Test training style narrative generation."""
        result = presentation_builder.build_narrative_content(
            sample_analysis_results, 
            style="training"
        )
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Customer Support Training Materials" in result
        assert "Most Common Support Scenarios" in result
        assert "Training" in result or "Exercises" in result
        assert "Best Practices Summary" in result
    
    def test_build_narrative_content_invalid_style(self, presentation_builder, sample_analysis_results):
        """Test handling of invalid presentation style."""
        with pytest.raises(ValueError, match="Unknown presentation style"):
            presentation_builder.build_narrative_content(
                sample_analysis_results, 
                style="invalid_style"
            )
    
    def test_extract_customer_quotes_with_context(self, presentation_builder, sample_analysis_results):
        """Test quote extraction with full context."""
        quotes = presentation_builder.extract_customer_quotes(
            sample_analysis_results['conversations'], 
            max_quotes=2
        )
        
        assert len(quotes) == 2
        assert quotes[0]['quote'] == 'I need help with my billing issue. The charge seems incorrect.'
        assert quotes[0]['customer_name'] == 'John Doe'
        assert quotes[0]['context'] == 'Tags: Billing, Refund'
        assert 'conv_1' in quotes[0]['intercom_url']
        
        assert quotes[1]['quote'] == 'The API is not working properly. Getting 500 errors.'
        assert quotes[1]['customer_name'] == 'Jane Smith'
        assert quotes[1]['context'] == 'Tags: API, Technical'
        assert 'conv_2' in quotes[1]['intercom_url']
    
    def test_extract_customer_quotes_max_limit(self, presentation_builder, sample_analysis_results):
        """Test quote extraction respects max_quotes limit."""
        quotes = presentation_builder.extract_customer_quotes(
            sample_analysis_results['conversations'], 
            max_quotes=1
        )
        
        assert len(quotes) == 1
        assert quotes[0]['customer_name'] == 'John Doe'
    
    def test_extract_customer_quotes_empty_conversations(self, presentation_builder):
        """Test quote extraction with empty conversations list."""
        quotes = presentation_builder.extract_customer_quotes([], max_quotes=5)
        
        assert len(quotes) == 0
    
    def test_extract_customer_quotes_no_customer_messages(self, presentation_builder):
        """Test quote extraction when no customer messages exist."""
        conversations = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'author': {'type': 'admin'},
                            'body': 'Admin response'
                        }
                    ]
                },
                'contacts': {
                    'contacts': [
                        {'name': 'John Doe', 'email': 'john@example.com'}
                    ]
                }
            }
        ]
        
        quotes = presentation_builder.extract_customer_quotes(conversations, max_quotes=5)
        
        assert len(quotes) == 0
    
    def test_extract_customer_quotes_short_messages(self, presentation_builder):
        """Test quote extraction skips very short messages."""
        conversations = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'author': {'type': 'user'},
                            'body': 'Hi'  # Too short
                        }
                    ]
                },
                'contacts': {
                    'contacts': [
                        {'name': 'John Doe', 'email': 'john@example.com'}
                    ]
                }
            }
        ]
        
        quotes = presentation_builder.extract_customer_quotes(conversations, max_quotes=5)
        
        assert len(quotes) == 0
    
    def test_extract_customer_quotes_long_message_truncation(self, presentation_builder):
        """Test quote extraction truncates very long messages."""
        long_message = "This is a very long message that should be truncated because it exceeds the maximum length limit for customer quotes in the presentation builder service." * 10
        
        conversations = [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'author': {'type': 'user'},
                            'body': long_message
                        }
                    ]
                },
                'contacts': {
                    'contacts': [
                        {'name': 'John Doe', 'email': 'john@example.com'}
                    ]
                }
            }
        ]
        
        quotes = presentation_builder.extract_customer_quotes(conversations, max_quotes=5)
        
        assert len(quotes) == 1
        assert len(quotes[0]['quote']) <= 200
        assert quotes[0]['quote'].endswith('...')
    
    def test_format_intercom_url(self, presentation_builder):
        """Test Intercom URL formatting."""
        conversation_id = "test_conv_123"
        url = presentation_builder._build_intercom_url(conversation_id)
        
        expected_url = f"https://app.intercom.com/a/apps/test_workspace_id/inbox/inbox/{conversation_id}"
        assert url == expected_url
    
    def test_get_quote_context_from_tags(self, presentation_builder):
        """Test quote context extraction from tags."""
        conversation = {
            'tags': {
                'tags': [
                    {'name': 'Billing'},
                    {'name': 'Refund'}
                ]
            }
        }
        
        context = presentation_builder._get_quote_context(conversation)
        
        assert context == "Tags: Billing, Refund"
    
    def test_get_quote_context_from_state(self, presentation_builder):
        """Test quote context extraction from state when no tags."""
        conversation = {
            'state': 'closed',
            'tags': {'tags': []}
        }
        
        context = presentation_builder._get_quote_context(conversation)
        
        assert context == "Status: closed"
    
    def test_get_top_categories(self, presentation_builder, sample_analysis_results):
        """Test top categories extraction."""
        categories = presentation_builder._get_top_categories(
            sample_analysis_results['category_results'], 
            limit=2
        )
        
        assert len(categories) == 2
        assert categories[0]['name'] == 'Billing'
        assert categories[0]['count'] == 1
        assert categories[0]['percentage'] == 50.0
        
        assert categories[1]['name'] == 'API'
        assert categories[1]['count'] == 1
        assert categories[1]['percentage'] == 50.0
    
    def test_get_top_categories_empty_results(self, presentation_builder):
        """Test top categories extraction with empty results."""
        categories = presentation_builder._get_top_categories({}, limit=5)
        
        assert len(categories) == 0
    
    def test_get_top_categories_limit(self, presentation_builder, sample_analysis_results):
        """Test top categories respects limit."""
        categories = presentation_builder._get_top_categories(
            sample_analysis_results['category_results'], 
            limit=1
        )
        
        assert len(categories) == 1
        assert categories[0]['name'] == 'Billing'
    
    def test_build_narrative_content_missing_data(self, presentation_builder):
        """Test narrative building with missing data."""
        incomplete_results = {
            'conversations': [],
            'category_results': {},
            'start_date': '2024-01-01',
            'end_date': '2024-01-31'
        }
        
        result = presentation_builder.build_narrative_content(
            incomplete_results, 
            style="executive"
        )
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "2024-01-01 to 2024-01-31" in result
    
    def test_build_narrative_content_no_customer_quotes(self, presentation_builder):
        """Test narrative building when no customer quotes are available."""
        results_without_quotes = {
            'conversations': [
                {
                    'id': 'conv_1',
                    'conversation_parts': {'conversation_parts': []},
                    'contacts': {'contacts': []}
                }
            ],
            'category_results': {},
            'start_date': '2024-01-01',
            'end_date': '2024-01-31'
        }
        
        result = presentation_builder.build_narrative_content(
            results_without_quotes, 
            style="executive"
        )
        
        assert isinstance(result, str)
        assert "No customer quotes available" in result
    
    def test_extract_quote_from_conversation_missing_parts(self, presentation_builder):
        """Test quote extraction when conversation parts are missing."""
        conversation = {
            'id': 'conv_1',
            'contacts': {
                'contacts': [
                    {'name': 'John Doe', 'email': 'john@example.com'}
                ]
            }
        }
        
        quote = presentation_builder._extract_quote_from_conversation(conversation)
        
        assert quote is None
    
    def test_extract_quote_from_conversation_missing_contacts(self, presentation_builder):
        """Test quote extraction when contacts are missing."""
        conversation = {
            'id': 'conv_1',
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'author': {'type': 'user'},
                        'body': 'I need help with billing'
                    }
                ]
            }
        }
        
        quote = presentation_builder._extract_quote_from_conversation(conversation)
        
        assert quote is not None
        assert quote['customer_name'] == 'Anonymous Customer'
    
    def test_build_narrative_content_different_styles_have_different_content(self, presentation_builder, sample_analysis_results):
        """Test that different styles produce different content."""
        executive = presentation_builder.build_narrative_content(
            sample_analysis_results, 
            style="executive"
        )
        
        detailed = presentation_builder.build_narrative_content(
            sample_analysis_results, 
            style="detailed"
        )
        
        training = presentation_builder.build_narrative_content(
            sample_analysis_results, 
            style="training"
        )
        
        # Each style should have unique content
        assert "Executive Summary" in executive
        assert "Comprehensive Customer Support Analysis" in detailed
        assert "Customer Support Training Materials" in training
        
        # Content lengths should be different
        assert len(executive) != len(detailed)
        assert len(detailed) != len(training)
        assert len(executive) != len(training)
