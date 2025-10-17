"""
Tests for stratified sampling functionality in presentation builder.
"""

import pytest
from unittest.mock import Mock, patch
from services.presentation_builder import PresentationBuilder


class TestStratifiedSampling:
    """Test stratified sampling functionality."""

    @pytest.fixture
    def presentation_builder(self):
        """Fixture to provide a PresentationBuilder instance."""
        return PresentationBuilder()

    @pytest.fixture
    def sample_conversations(self):
        """Sample conversations for testing."""
        return [
            {
                'id': 'conv_1',
                'tags': {'tags': [{'name': 'Billing'}]},
                'source': {'body': 'I need help with my billing issue'},
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'author': {'type': 'user'},
                            'body': 'I need help with my billing issue'
                        }
                    ]
                },
                'contacts': {'contacts': [{'name': 'John Doe', 'email': 'john@example.com'}]}
            },
            {
                'id': 'conv_2',
                'tags': {'tags': [{'name': 'API'}]},
                'source': {'body': 'My API integration is failing'},
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'author': {'type': 'user'},
                            'body': 'My API integration is failing'
                        }
                    ]
                },
                'contacts': {'contacts': [{'name': 'Jane Smith', 'email': 'jane@example.com'}]}
            },
            {
                'id': 'conv_3',
                'tags': {'tags': [{'name': 'Product Question'}]},
                'source': {'body': 'How do I export my data?'},
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'author': {'type': 'user'},
                            'body': 'How do I export my data?'
                        }
                    ]
                },
                'contacts': {'contacts': [{'name': 'Bob Wilson', 'email': 'bob@example.com'}]}
            },
            {
                'id': 'conv_4',
                'tags': {'tags': [{'name': 'Billing'}]},
                'source': {'body': 'I was charged incorrectly'},
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'author': {'type': 'user'},
                            'body': 'I was charged incorrectly'
                        }
                    ]
                },
                'contacts': {'contacts': [{'name': 'Alice Brown', 'email': 'alice@example.com'}]}
            },
            {
                'id': 'conv_5',
                'tags': {'tags': [{'name': 'Workspace'}]},
                'source': {'body': 'My site is not publishing'},
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'author': {'type': 'user'},
                            'body': 'My site is not publishing'
                        }
                    ]
                },
                'contacts': {'contacts': [{'name': 'Charlie Davis', 'email': 'charlie@example.com'}]}
            }
        ]

    @pytest.fixture
    def sample_category_results(self):
        """Sample category results for testing."""
        return {
            'Billing': {
                'conversation_count': 2,
                'ai_analysis': 'Billing issues are common'
            },
            'API': {
                'conversation_count': 1,
                'ai_analysis': 'API integration problems'
            },
            'Product Question': {
                'conversation_count': 1,
                'ai_analysis': 'Product questions about features'
            },
            'Workspace': {
                'conversation_count': 1,
                'ai_analysis': 'Workspace publishing issues'
            }
        }

    def test_extract_customer_quotes_stratified(self, presentation_builder, sample_conversations, sample_category_results):
        """Test stratified quote extraction."""
        quotes = presentation_builder.extract_customer_quotes(
            sample_conversations,
            sample_category_results,
            max_quotes_per_category=2
        )
        
        # Should extract quotes from multiple categories
        assert len(quotes) > 0
        
        # Check that quotes have category information
        categories_found = set(quote.get('category') for quote in quotes)
        assert len(categories_found) > 1  # Should have multiple categories
        
        # Check that quotes have required fields
        for quote in quotes:
            assert 'quote' in quote
            assert 'category' in quote
            assert 'intercom_url' in quote

    def test_conversation_matches_category(self, presentation_builder):
        """Test category matching logic."""
        conversation = {
            'tags': {'tags': [{'name': 'Billing'}]}
        }
        
        assert presentation_builder._conversation_matches_category(conversation, 'Billing')
        assert not presentation_builder._conversation_matches_category(conversation, 'API')

    def test_extract_quotes_from_conversations(self, presentation_builder, sample_conversations):
        """Test quote extraction from specific conversations."""
        billing_conversations = [
            c for c in sample_conversations
            if presentation_builder._conversation_matches_category(c, 'Billing')
        ]
        
        quotes = presentation_builder._extract_quotes_from_conversations(
            billing_conversations,
            num_quotes=2,
            category='Billing'
        )
        
        assert len(quotes) <= 2
        for quote in quotes:
            assert quote['category'] == 'Billing'

    def test_build_technical_sop_section(self, presentation_builder, sample_category_results):
        """Test technical SOP section building."""
        quotes_by_category = {
            'API': [{'quote': 'API test quote', 'customer_name': 'Test User'}],
            'Product Question': [{'quote': 'Product test quote', 'customer_name': 'Test User'}]
        }
        
        sop_section = presentation_builder._build_technical_sop_section(
            sample_category_results,
            quotes_by_category
        )
        
        assert "Technical Support Standard Operating Procedures" in sop_section
        assert "API" in sop_section
        assert "Product Question" in sop_section

    def test_build_recommendations_section(self, presentation_builder, sample_category_results):
        """Test recommendations section building."""
        recommendations = presentation_builder._build_recommendations_section(sample_category_results)
        
        assert "Strategic Recommendations" in recommendations
        assert "Immediate Actions" in recommendations
        assert "Billing" in recommendations  # Should prioritize by volume

    def test_detailed_narrative_with_stratified_quotes(self, presentation_builder, sample_conversations, sample_category_results):
        """Test detailed narrative building with stratified quotes."""
        narrative = presentation_builder._build_detailed_narrative(
            sample_conversations,
            sample_category_results,
            "2024-01-01",
            "2024-01-31"
        )
        
        # Should include category distribution
        assert "Category Distribution" in narrative
        assert "Billing" in narrative
        assert "API" in narrative
        
        # Should include customer voice sections
        assert "Customer Voice" in narrative
        
        # Should include technical SOP section
        assert "Technical Support Standard Operating Procedures" in narrative
        
        # Should include recommendations
        assert "Strategic Recommendations" in narrative

    def test_fallback_to_simple_sampling(self, presentation_builder, sample_conversations):
        """Test fallback to simple sampling when no category results provided."""
        quotes = presentation_builder.extract_customer_quotes(
            sample_conversations,
            category_results=None,
            max_quotes_per_category=2
        )
        
        # Should still extract quotes
        assert len(quotes) > 0
        
        # Should not have category information
        for quote in quotes:
            assert 'category' not in quote or quote['category'] is None
