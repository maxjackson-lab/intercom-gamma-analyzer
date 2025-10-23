"""
Integration test for stratified sampling functionality.
Tests the full pipeline with mock data to ensure stratified sampling works end-to-end.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from src.services.presentation_builder import PresentationBuilder


class TestStratifiedSamplingIntegration:
    """Integration test for stratified sampling."""

    @pytest.fixture
    def mock_conversations(self):
        """Mock conversations with realistic data structure."""
        return [
            {
                'id': 'conv_1',
                'created_at': '2024-01-01T10:00:00Z',
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
                'created_at': '2024-01-02T11:00:00Z',
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
                'created_at': '2024-01-03T12:00:00Z',
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
                'created_at': '2024-01-04T13:00:00Z',
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
                'created_at': '2024-01-05T14:00:00Z',
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
    def mock_category_results(self):
        """Mock category analysis results."""
        return {
            'Billing': {
                'conversation_count': 2,
                'percentage': 40.0,
                'ai_analysis': 'Billing issues are common and require immediate attention'
            },
            'API': {
                'conversation_count': 1,
                'percentage': 20.0,
                'ai_analysis': 'API integration problems need technical support'
            },
            'Product Question': {
                'conversation_count': 1,
                'percentage': 20.0,
                'ai_analysis': 'Product questions about features and functionality'
            },
            'Workspace': {
                'conversation_count': 1,
                'percentage': 20.0,
                'ai_analysis': 'Workspace publishing issues require troubleshooting'
            }
        }

    def test_stratified_quote_extraction_integration(self, mock_conversations, mock_category_results):
        """Test that stratified quote extraction works with realistic data."""
        builder = PresentationBuilder()
        
        # Extract quotes using stratified sampling
        quotes = builder.extract_customer_quotes(
            mock_conversations,
            mock_category_results,
            max_quotes_per_category=2
        )
        
        # Verify we got quotes
        assert len(quotes) > 0
        
        # Verify quotes have category information
        categories_found = set(quote.get('category') for quote in quotes)
        assert len(categories_found) > 1  # Should have multiple categories
        
        # Verify each quote has required fields
        for quote in quotes:
            assert 'quote' in quote
            assert 'category' in quote
            assert 'customer_name' in quote
            assert 'intercom_url' in quote
            assert len(quote['quote']) > 10  # Should have substantial content

    def test_detailed_narrative_with_stratified_quotes_integration(self, mock_conversations, mock_category_results):
        """Test that detailed narrative generation works with stratified quotes."""
        builder = PresentationBuilder()
        
        # Generate detailed narrative
        narrative = builder._build_detailed_narrative(
            mock_conversations,
            mock_category_results,
            "2024-01-01",
            "2024-01-31"
        )
        
        # Verify narrative structure
        assert "Comprehensive Customer Support Analysis" in narrative
        assert "Category Distribution" in narrative
        assert "Customer Voice" in narrative
        assert "Technical Support Standard Operating Procedures" in narrative
        assert "Strategic Recommendations" in narrative
        
        # Verify category information is included
        assert "Billing" in narrative
        assert "API" in narrative
        assert "Product Question" in narrative
        assert "Workspace" in narrative
        
        # Verify percentages are shown
        assert "40.0%" in narrative  # Billing percentage
        assert "20.0%" in narrative  # Other categories

    def test_technical_sop_section_integration(self, mock_category_results):
        """Test that technical SOP section is generated correctly."""
        builder = PresentationBuilder()
        
        # Mock quotes by category
        quotes_by_category = {
            'API': [{'quote': 'API test quote', 'customer_name': 'Test User'}],
            'Product Question': [{'quote': 'Product test quote', 'customer_name': 'Test User'}],
            'Workspace': [{'quote': 'Workspace test quote', 'customer_name': 'Test User'}]
        }
        
        sop_section = builder._build_technical_sop_section(
            mock_category_results,
            quotes_by_category
        )
        
        # Verify SOP section structure
        assert "Technical Support Standard Operating Procedures" in sop_section
        assert "Common Technical Patterns" in sop_section
        
        # Verify technical categories are included
        assert "API" in sop_section
        assert "Product Question" in sop_section
        assert "Workspace" in sop_section
        
        # Verify conversation counts are shown
        assert "1 conversations" in sop_section

    def test_recommendations_section_integration(self, mock_category_results):
        """Test that recommendations section prioritizes by volume."""
        builder = PresentationBuilder()
        
        recommendations = builder._build_recommendations_section(mock_category_results)
        
        # Verify recommendations structure
        assert "Strategic Recommendations" in recommendations
        assert "Immediate Actions" in recommendations
        
        # Verify Billing is listed first (highest volume)
        billing_index = recommendations.find("Billing")
        api_index = recommendations.find("API")
        assert billing_index < api_index  # Billing should come before API

    def test_full_pipeline_simulation(self, mock_conversations, mock_category_results):
        """Simulate the full pipeline to ensure everything works together."""
        builder = PresentationBuilder()
        
        # Step 1: Extract stratified quotes
        quotes = builder.extract_customer_quotes(
            mock_conversations,
            mock_category_results,
            max_quotes_per_category=2
        )
        
        # Step 2: Generate detailed narrative
        narrative = builder._build_detailed_narrative(
            mock_conversations,
            mock_category_results,
            "2024-01-01",
            "2024-01-31"
        )
        
        # Step 3: Verify the narrative contains the quotes
        for quote in quotes:
            if quote['quote'] in narrative:
                # Quote should be in the narrative
                assert True
            else:
                # At least the category should be represented
                assert quote['category'] in narrative
        
        # Step 4: Verify narrative quality
        assert len(narrative) > 1000  # Should be substantial
        assert narrative.count("Customer Voice") > 0  # Should have customer voice sections
        assert narrative.count("---") > 5  # Should have proper section breaks
        
        print(f"\n✅ Full pipeline simulation successful!")
        print(f"   - Extracted {len(quotes)} stratified quotes")
        print(f"   - Generated {len(narrative)} character narrative")
        print(f"   - Categories represented: {set(q['category'] for q in quotes)}")




