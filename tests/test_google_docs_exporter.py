"""
Unit tests for GoogleDocsExporter service.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import os

from src.services.google_docs_exporter import GoogleDocsExporter


class TestGoogleDocsExporter:
    """Test cases for GoogleDocsExporter."""
    
    @pytest.fixture
    def docs_exporter(self):
        """Create a GoogleDocsExporter instance for testing."""
        return GoogleDocsExporter()
    
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
                                'body': 'I need help with my billing issue. The charge seems incorrect and I would like a refund.'
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
                                'body': 'The API is not working properly. Getting 500 errors when trying to integrate.'
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
    
    def test_docs_exporter_initialization(self, docs_exporter):
        """Test GoogleDocsExporter initializes correctly."""
        assert docs_exporter is not None
    
    def test_export_to_markdown_executive_style(self, docs_exporter, sample_analysis_results):
        """Test executive style markdown export."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_executive.md"
            
            result_path = docs_exporter.export_to_markdown(
                analysis_results=sample_analysis_results,
                output_path=output_path,
                style="executive"
            )
            
            assert result_path == output_path
            assert output_path.exists()
            
            # Read and verify content
            content = output_path.read_text(encoding='utf-8')
            assert "# Customer Support Analysis: 2024-01-01 to 2024-01-31" in content
            assert "## Executive Summary" in content
            assert "## Customer Voice" in content
            assert "## Strategic Recommendations" in content
            assert "John Doe" in content
            assert "I need help with my billing issue" in content
    
    def test_export_to_markdown_detailed_style(self, docs_exporter, sample_analysis_results):
        """Test detailed style markdown export."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_detailed.md"
            
            result_path = docs_exporter.export_to_markdown(
                analysis_results=sample_analysis_results,
                output_path=output_path,
                style="detailed"
            )
            
            assert result_path == output_path
            assert output_path.exists()
            
            # Read and verify content
            content = output_path.read_text(encoding='utf-8')
            assert "# Comprehensive Customer Support Analysis: 2024-01-01 to 2024-01-31" in content
            assert "## Analysis Overview" in content
            assert "## Category Breakdown" in content
            assert "## Customer Sentiment Analysis" in content
            assert "## Technical Performance Analysis" in content
            assert "## Process Improvement Opportunities" in content
    
    def test_export_to_markdown_training_style(self, docs_exporter, sample_analysis_results):
        """Test training style markdown export."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_training.md"
            
            result_path = docs_exporter.export_to_markdown(
                analysis_results=sample_analysis_results,
                output_path=output_path,
                style="training"
            )
            
            assert result_path == output_path
            assert output_path.exists()
            
            # Read and verify content
            content = output_path.read_text(encoding='utf-8')
            assert "# Customer Support Training Materials: 2024-01-01 to 2024-01-31" in content
            assert "## Training Overview" in content
            assert "## Most Common Support Scenarios" in content
            assert "## Practice Scenarios" in content
            assert "## Best Practices Summary" in content
    
    def test_export_to_markdown_creates_directory(self, docs_exporter, sample_analysis_results):
        """Test that export creates output directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "new_dir" / "test.md"
            
            result_path = docs_exporter.export_to_markdown(
                analysis_results=sample_analysis_results,
                output_path=output_path,
                style="executive"
            )
            
            assert result_path == output_path
            assert output_path.exists()
            assert output_path.parent.exists()
    
    def test_export_to_markdown_with_empty_conversations(self, docs_exporter):
        """Test markdown export with empty conversations."""
        empty_results = {
            'conversations': [],
            'category_results': {},
            'start_date': '2024-01-01',
            'end_date': '2024-01-31'
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "empty_test.md"
            
            result_path = docs_exporter.export_to_markdown(
                analysis_results=empty_results,
                output_path=output_path,
                style="executive"
            )
            
            assert result_path == output_path
            assert output_path.exists()
            
            content = output_path.read_text(encoding='utf-8')
            assert "2024-01-01 to 2024-01-31" in content
            assert "No customer quotes available" in content
    
    def test_export_to_markdown_with_missing_data(self, docs_exporter):
        """Test markdown export with missing data fields."""
        incomplete_results = {
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
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "incomplete_test.md"
            
            result_path = docs_exporter.export_to_markdown(
                analysis_results=incomplete_results,
                output_path=output_path,
                style="detailed"
            )
            
            assert result_path == output_path
            assert output_path.exists()
    
    def test_extract_customer_quotes(self, docs_exporter, sample_analysis_results):
        """Test customer quote extraction."""
        quotes = docs_exporter._extract_customer_quotes(
            sample_analysis_results['conversations'], 
            max_quotes=2
        )
        
        assert len(quotes) == 2
        assert quotes[0]['quote'] == 'I need help with my billing issue. The charge seems incorrect and I would like a refund.'
        assert quotes[0]['customer_name'] == 'John Doe'
        assert quotes[0]['context'] == 'Tags: Billing, Refund'
        assert 'conv_1' in quotes[0]['intercom_url']
        
        assert quotes[1]['quote'] == 'The API is not working properly. Getting 500 errors when trying to integrate.'
        assert quotes[1]['customer_name'] == 'Jane Smith'
        assert quotes[1]['context'] == 'Tags: API, Technical'
        assert 'conv_2' in quotes[1]['intercom_url']
    
    def test_extract_customer_quotes_max_limit(self, docs_exporter, sample_analysis_results):
        """Test quote extraction respects max_quotes limit."""
        quotes = docs_exporter._extract_customer_quotes(
            sample_analysis_results['conversations'], 
            max_quotes=1
        )
        
        assert len(quotes) == 1
        assert quotes[0]['customer_name'] == 'John Doe'
    
    def test_extract_customer_quotes_empty_conversations(self, docs_exporter):
        """Test quote extraction with empty conversations list."""
        quotes = docs_exporter._extract_customer_quotes([], max_quotes=5)
        
        assert len(quotes) == 0
    
    def test_extract_customer_quotes_no_customer_messages(self, docs_exporter):
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
        
        quotes = docs_exporter._extract_customer_quotes(conversations, max_quotes=5)
        
        assert len(quotes) == 0
    
    def test_extract_customer_quotes_short_messages(self, docs_exporter):
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
        
        quotes = docs_exporter._extract_customer_quotes(conversations, max_quotes=5)
        
        assert len(quotes) == 0
    
    def test_extract_customer_quotes_long_message_truncation(self, docs_exporter):
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
        
        quotes = docs_exporter._extract_customer_quotes(conversations, max_quotes=5)
        
        assert len(quotes) == 1
        assert len(quotes[0]['quote']) <= 200
        assert quotes[0]['quote'].endswith('...')
    
    def test_get_top_categories(self, docs_exporter, sample_analysis_results):
        """Test top categories extraction."""
        categories = docs_exporter._get_top_categories(
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
    
    def test_get_top_categories_empty_results(self, docs_exporter):
        """Test top categories extraction with empty results."""
        categories = docs_exporter._get_top_categories({}, limit=5)
        
        assert len(categories) == 0
    
    def test_get_top_categories_limit(self, docs_exporter, sample_analysis_results):
        """Test top categories respects limit."""
        categories = docs_exporter._get_top_categories(
            sample_analysis_results['category_results'], 
            limit=1
        )
        
        assert len(categories) == 1
        assert categories[0]['name'] == 'Billing'
    
    def test_extract_quote_from_conversation_missing_parts(self, docs_exporter):
        """Test quote extraction when conversation parts are missing."""
        conversation = {
            'id': 'conv_1',
            'contacts': {
                'contacts': [
                    {'name': 'John Doe', 'email': 'john@example.com'}
                ]
            }
        }
        
        quote = docs_exporter._extract_quote_from_conversation(conversation)
        
        assert quote is None
    
    def test_extract_quote_from_conversation_missing_contacts(self, docs_exporter):
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
        
        quote = docs_exporter._extract_quote_from_conversation(conversation)
        
        assert quote is not None
        assert quote['customer_name'] == 'Anonymous Customer'
    
    def test_get_quote_context_from_tags(self, docs_exporter):
        """Test quote context extraction from tags."""
        conversation = {
            'tags': {
                'tags': [
                    {'name': 'Billing'},
                    {'name': 'Refund'}
                ]
            }
        }
        
        context = docs_exporter._get_quote_context(conversation)
        
        assert context == "Tags: Billing, Refund"
    
    def test_get_quote_context_from_state(self, docs_exporter):
        """Test quote context extraction from state when no tags."""
        conversation = {
            'state': 'closed',
            'tags': {'tags': []}
        }
        
        context = docs_exporter._get_quote_context(conversation)
        
        assert context == "Status: closed"
    
    def test_export_to_markdown_different_styles_have_different_content(self, docs_exporter, sample_analysis_results):
        """Test that different styles produce different content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Export all three styles
            executive_path = Path(temp_dir) / "executive.md"
            detailed_path = Path(temp_dir) / "detailed.md"
            training_path = Path(temp_dir) / "training.md"
            
            docs_exporter.export_to_markdown(sample_analysis_results, executive_path, "executive")
            docs_exporter.export_to_markdown(sample_analysis_results, detailed_path, "detailed")
            docs_exporter.export_to_markdown(sample_analysis_results, training_path, "training")
            
            # Read content
            executive_content = executive_path.read_text(encoding='utf-8')
            detailed_content = detailed_path.read_text(encoding='utf-8')
            training_content = training_path.read_text(encoding='utf-8')
            
            # Each style should have unique content
            assert "Customer Support Analysis:" in executive_content
            assert "Comprehensive Customer Support Analysis:" in detailed_content
            assert "Customer Support Training Materials:" in training_content
            
            # Content lengths should be different
            assert len(executive_content) != len(detailed_content)
            assert len(detailed_content) != len(training_content)
            assert len(executive_content) != len(training_content)
    
    def test_export_to_markdown_includes_timestamp(self, docs_exporter, sample_analysis_results):
        """Test that exported markdown includes generation timestamp."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "timestamp_test.md"
            
            docs_exporter.export_to_markdown(
                analysis_results=sample_analysis_results,
                output_path=output_path,
                style="executive"
            )
            
            content = output_path.read_text(encoding='utf-8')
            assert "Generated on" in content
            assert "2024-" in content  # Should contain current year
    
    def test_export_to_markdown_handles_encoding(self, docs_exporter, sample_analysis_results):
        """Test that markdown export handles UTF-8 encoding properly."""
        # Add some special characters to test encoding
        sample_analysis_results['conversations'][0]['conversation_parts']['conversation_parts'][0]['body'] = "I need help with my billing issue. The charge seems incorrect and I would like a refund. Special chars: éñü"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "encoding_test.md"
            
            docs_exporter.export_to_markdown(
                analysis_results=sample_analysis_results,
                output_path=output_path,
                style="executive"
            )
            
            content = output_path.read_text(encoding='utf-8')
            assert "éñü" in content
    
    def test_export_to_markdown_file_permissions_error(self, docs_exporter, sample_analysis_results):
        """Test handling of file permissions error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "readonly.md"
            
            # Create a readonly file
            output_path.touch()
            output_path.chmod(0o444)  # Read-only
            
            with pytest.raises(PermissionError):
                docs_exporter.export_to_markdown(
                    analysis_results=sample_analysis_results,
                    output_path=output_path,
                    style="executive"
                )





