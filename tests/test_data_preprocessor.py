"""
Unit tests for DataPreprocessor service.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any, Tuple

from src.services.data_preprocessor import DataPreprocessor


class TestDataPreprocessor:
    """Test cases for DataPreprocessor."""
    
    @pytest.fixture
    def data_preprocessor(self):
        """Create a DataPreprocessor instance for testing."""
        return DataPreprocessor()
    
    @pytest.fixture
    def sample_raw_conversations(self):
        """Create sample raw conversation data for testing."""
        return [
            {
                'id': 'conv_1',
                'created_at': 1640995200,  # 2022-01-01
                'updated_at': 1640995200,
                'state': 'open',
                'open': True,
                'read': True,
                'admin_assignee': {
                    'id': 'agent_1',
                    'name': 'Dae-Ho'
                },
                'team_assignee': {
                    'id': 'team_1',
                    'name': 'Support Team'
                },
                'contact': {
                    'id': 'user_1',
                    'email': 'user@example.com'
                },
                'source': {
                    'type': 'conversation',
                    'body': '<p>I need help with <strong>billing</strong></p>'
                },
                'tags': {
                    'tags': [
                        {'name': 'Billing'},
                        {'name': 'Refund Request'}
                    ]
                },
                'conversation_topics': [
                    {'name': 'billing'},
                    {'name': 'refund'}
                ],
                'custom_attributes': {
                    'priority': 'high',
                    'category': 'billing'
                },
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'id': 'part_1',
                            'part_type': 'comment',
                            'body': '<p>I need help with <strong>billing</strong></p>',
                            'author': {
                                'type': 'user',
                                'id': 'user_1'
                            },
                            'created_at': 1640995200
                        },
                        {
                            'id': 'part_2',
                            'part_type': 'comment',
                            'body': '<p>I can help you with that. What specific billing issue are you experiencing?</p>',
                            'author': {
                                'type': 'admin',
                                'id': 'agent_1',
                                'name': 'Dae-Ho'
                            },
                            'created_at': 1640995300
                        }
                    ]
                }
            },
            {
                'id': 'conv_2',
                'created_at': 1640995200,
                'updated_at': 1640995200,
                'state': 'closed',
                'open': False,
                'read': True,
                'admin_assignee': {
                    'id': 'agent_2',
                    'name': 'Hilary'
                },
                'team_assignee': {
                    'id': 'team_1',
                    'name': 'Support Team'
                },
                'contact': {
                    'id': 'user_2',
                    'email': 'user2@example.com'
                },
                'source': {
                    'type': 'conversation',
                    'body': 'I have a bug with the export feature'
                },
                'tags': {
                    'tags': [
                        {'name': 'Bug Report'},
                        {'name': 'Export'}
                    ]
                },
                'conversation_topics': [
                    {'name': 'export'},
                    {'name': 'bug'}
                ],
                'custom_attributes': {
                    'priority': 'medium',
                    'category': 'product'
                },
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'id': 'part_3',
                            'part_type': 'comment',
                            'body': 'I have a bug with the export feature',
                            'author': {
                                'type': 'user',
                                'id': 'user_2'
                            },
                            'created_at': 1640995200
                        }
                    ]
                }
            }
        ]
    
    def test_initialization(self, data_preprocessor):
        """Test DataPreprocessor initialization."""
        assert data_preprocessor.logger is not None
        assert data_preprocessor.logger.name == 'services.data_preprocessor'
    
    def test_clean_html(self, data_preprocessor):
        """Test HTML cleaning functionality."""
        html_content = '<p>I need help with <strong>billing</strong></p>'
        cleaned = data_preprocessor._clean_html(html_content)
        assert cleaned == 'I need help with billing'
        
        # Test with None
        assert data_preprocessor._clean_html(None) == ""
        
        # Test with empty string
        assert data_preprocessor._clean_html("") == ""
        
        # Test with complex HTML
        complex_html = '<div><p>Hello <span>world</span></p><br/><a href="#">link</a></div>'
        cleaned_complex = data_preprocessor._clean_html(complex_html)
        assert cleaned_complex == 'Hello world link'
    
    def test_extract_full_conversation_text(self, data_preprocessor, sample_raw_conversations):
        """Test full conversation text extraction."""
        conv = sample_raw_conversations[0]
        text = data_preprocessor._extract_full_conversation_text(conv)
        
        assert 'I need help with billing' in text
        assert 'I can help you with that' in text
        assert '<p>' not in text  # HTML should be cleaned
        assert '<strong>' not in text  # HTML should be cleaned
    
    def test_extract_full_conversation_text_empty_parts(self, data_preprocessor):
        """Test conversation text extraction with empty parts."""
        conv = {
            'id': 'conv_empty',
            'conversation_parts': {
                'conversation_parts': []
            }
        }
        
        text = data_preprocessor._extract_full_conversation_text(conv)
        assert text == ""
    
    def test_extract_full_conversation_text_missing_parts(self, data_preprocessor):
        """Test conversation text extraction with missing parts."""
        conv = {
            'id': 'conv_missing',
            'conversation_parts': {}
        }
        
        text = data_preprocessor._extract_full_conversation_text(conv)
        assert text == ""
    
    def test_extract_full_conversation_text_missing_conversation_parts(self, data_preprocessor):
        """Test conversation text extraction with missing conversation_parts."""
        conv = {
            'id': 'conv_missing',
            'conversation_parts': {
                'conversation_parts': [
                    {'part_type': 'comment', 'body': 'I need help'}
                ]
            }
        }
        
        text = data_preprocessor._extract_full_conversation_text(conv)
        assert text == "I need help"
    
    def test_extract_metadata(self, data_preprocessor, sample_raw_conversations):
        """Test metadata extraction."""
        conv = sample_raw_conversations[0]
        metadata = data_preprocessor._extract_metadata(conv)
        
        assert metadata['id'] == 'conv_1'
        assert metadata['created_at'] == datetime.fromtimestamp(1640995200)
        assert metadata['updated_at'] == datetime.fromtimestamp(1640995200)
        assert metadata['state'] == 'open'
        assert metadata['open'] is True
        assert metadata['read'] is True
        assert metadata['admin_assignee_id'] == 'agent_1'
        assert metadata['team_assignee_id'] == 'team_1'
        assert metadata['user_id'] == 'user_1'
        assert metadata['user_email'] == 'user@example.com'
        assert metadata['source_type'] == 'conversation'
        assert metadata['source_body'] == 'I need help with billing'
        assert metadata['tags'] == ['Billing', 'Refund Request']
        assert metadata['topics'] == ['billing', 'refund']
        assert metadata['custom_attributes'] == {'priority': 'high', 'category': 'billing'}
        assert metadata['ai_agent_participated'] is False
    
    def test_extract_metadata_with_ai_agent(self, data_preprocessor):
        """Test metadata extraction with AI agent participation."""
        conv_with_ai = {
            'id': 'conv_ai',
            'created_at': 1640995200,
            'updated_at': 1640995200,
            'state': 'open',
            'open': True,
            'read': True,
            'admin_assignee': {'id': 'agent_1', 'name': 'Dae-Ho'},
            'team_assignee': {'id': 'team_1', 'name': 'Support Team'},
            'contact': {'id': 'user_1', 'email': 'user@example.com'},
            'source': {'type': 'conversation', 'body': 'I need help'},
            'tags': {'tags': []},
            'conversation_topics': [],
            'custom_attributes': {},
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'id': 'part_1',
                        'part_type': 'comment',
                        'body': 'I need help',
                        'author': {
                            'type': 'user',
                            'id': 'user_1'
                        },
                        'created_at': 1640995200
                    },
                    {
                        'id': 'part_2',
                        'part_type': 'comment',
                        'body': 'I can help you with that',
                        'author': {
                            'type': 'bot',
                            'bot_id': 'fin'
                        },
                        'created_at': 1640995300
                    }
                ]
            }
        }
        
        metadata = data_preprocessor._extract_metadata(conv_with_ai)
        assert metadata['ai_agent_participated'] is True
    
    def test_extract_metadata_missing_fields(self, data_preprocessor):
        """Test metadata extraction with missing fields."""
        conv_missing_fields = {
            'id': 'conv_missing',
            'created_at': 1640995200,
            'updated_at': 1640995200,
            'state': 'open',
            'open': True,
            'read': True,
            'admin_assignee': {'id': 'agent_1', 'name': 'Dae-Ho'},
            'team_assignee': {'id': 'team_1', 'name': 'Support Team'},
            'contact': {'id': 'user_1', 'email': 'user@example.com'},
            'source': {'type': 'conversation', 'body': 'I need help'},
            'tags': {'tags': []},
            'conversation_topics': [],
            'custom_attributes': {},
            'conversation_parts': {'conversation_parts': []}
        }
        
        metadata = data_preprocessor._extract_metadata(conv_missing_fields)
        
        # Should handle missing fields gracefully
        assert metadata['id'] == 'conv_missing'
        assert metadata['created_at'] == datetime.fromtimestamp(1640995200)
        assert metadata['updated_at'] == datetime.fromtimestamp(1640995200)
        assert metadata['state'] == 'open'
        assert metadata['open'] is True
        assert metadata['read'] is True
        assert metadata['admin_assignee_id'] == 'agent_1'
        assert metadata['team_assignee_id'] == 'team_1'
        assert metadata['user_id'] == 'user_1'
        assert metadata['user_email'] == 'user@example.com'
        assert metadata['source_type'] == 'conversation'
        assert metadata['source_body'] == 'I need help'
        assert metadata['tags'] == []
        assert metadata['topics'] == []
        assert metadata['custom_attributes'] == {}
        assert metadata['ai_agent_participated'] is False
    
    def test_extract_metadata_missing_timestamps(self, data_preprocessor):
        """Test metadata extraction with missing timestamps."""
        conv_missing_timestamps = {
            'id': 'conv_missing_timestamps',
            'state': 'open',
            'open': True,
            'read': True,
            'admin_assignee': {'id': 'agent_1', 'name': 'Dae-Ho'},
            'team_assignee': {'id': 'team_1', 'name': 'Support Team'},
            'contact': {'id': 'user_1', 'email': 'user@example.com'},
            'source': {'type': 'conversation', 'body': 'I need help'},
            'tags': {'tags': []},
            'conversation_topics': [],
            'custom_attributes': {},
            'conversation_parts': {'conversation_parts': []}
        }
        
        metadata = data_preprocessor._extract_metadata(conv_missing_timestamps)
        
        # Should handle missing timestamps gracefully
        assert metadata['created_at'] is None
        assert metadata['updated_at'] is None
        assert metadata['id'] == 'conv_missing_timestamps'
    
    def test_preprocess_conversations_success(self, data_preprocessor, sample_raw_conversations):
        """Test successful conversation preprocessing."""
        processed_conversations, stats = data_preprocessor.preprocess_conversations(
            sample_raw_conversations
        )
        
        assert len(processed_conversations) == 2
        assert stats['initial_count'] == 2
        assert stats['processed_count'] == 2
        assert stats['skipped_empty_text'] == 0
        assert stats['sampled_count'] == 0
        
        # Check first conversation
        conv1 = processed_conversations[0]
        assert conv1['id'] == 'conv_1'
        assert 'I need help with billing' in conv1['full_text']
        assert 'I can help you with that' in conv1['full_text']
        assert conv1['tags'] == ['Billing', 'Refund Request']
        assert conv1['topics'] == ['billing', 'refund']
        assert conv1['custom_attributes'] == {'priority': 'high', 'category': 'billing'}
        assert conv1['ai_agent_participated'] is False
        
        # Check second conversation
        conv2 = processed_conversations[1]
        assert conv2['id'] == 'conv_2'
        assert 'I have a bug with the export feature' in conv2['full_text']
        assert conv2['tags'] == ['Bug Report', 'Export']
        assert conv2['topics'] == ['export', 'bug']
        assert conv2['custom_attributes'] == {'priority': 'medium', 'category': 'product'}
        assert conv2['ai_agent_participated'] is False
    
    def test_preprocess_conversations_with_sampling(self, data_preprocessor, sample_raw_conversations):
        """Test conversation preprocessing with sampling."""
        options = {'max_conversations': 1}
        processed_conversations, stats = data_preprocessor.preprocess_conversations(
            sample_raw_conversations, options
        )
        
        assert len(processed_conversations) == 1
        assert stats['initial_count'] == 2
        assert stats['processed_count'] == 1
        assert stats['sampled_count'] == 1
        assert stats['skipped_empty_text'] == 0
        
        # Should process the first conversation
        assert processed_conversations[0]['id'] == 'conv_1'
    
    def test_preprocess_conversations_with_empty_text(self, data_preprocessor):
        """Test conversation preprocessing with empty text."""
        conversations_with_empty_text = [
            {
                'id': 'conv_empty',
                'created_at': 1640995200,
                'updated_at': 1640995200,
                'state': 'open',
                'open': True,
                'read': True,
                'admin_assignee': {'id': 'agent_1', 'name': 'Dae-Ho'},
                'team_assignee': {'id': 'team_1', 'name': 'Support Team'},
                'contact': {'id': 'user_1', 'email': 'user@example.com'},
                'source': {'type': 'conversation', 'body': ''},
                'tags': {'tags': []},
                'conversation_topics': [],
                'custom_attributes': {},
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'id': 'part_1',
                            'part_type': 'comment',
                            'body': '',
                            'author': {'type': 'user', 'id': 'user_1'},
                            'created_at': 1640995200
                        }
                    ]
                }
            }
        ]
        
        processed_conversations, stats = data_preprocessor.preprocess_conversations(
            conversations_with_empty_text
        )
        
        assert len(processed_conversations) == 0
        assert stats['initial_count'] == 1
        assert stats['processed_count'] == 0
        assert stats['skipped_empty_text'] == 1
        assert stats['sampled_count'] == 0
    
    def test_preprocess_conversations_with_error(self, data_preprocessor):
        """Test conversation preprocessing with error handling."""
        conversations_with_error = [
            {
                'id': 'conv_error',
                'created_at': 1640995200,
                'updated_at': 1640995200,
                'state': 'open',
                'open': True,
                'read': True,
                'admin_assignee': {'id': 'agent_1', 'name': 'Dae-Ho'},
                'team_assignee': {'id': 'team_1', 'name': 'Support Team'},
                'contact': {'id': 'user_1', 'email': 'user@example.com'},
                'source': {'type': 'conversation', 'body': 'I need help'},
                'tags': {'tags': []},
                'conversation_topics': [],
                'custom_attributes': {},
                'conversation_parts': {'conversation_parts': []}
            },
            {
                'id': 'conv_malformed',
                # Missing required fields to cause error
            }
        ]
        
        processed_conversations, stats = data_preprocessor.preprocess_conversations(
            conversations_with_error
        )
        
        # Should handle errors gracefully and continue processing
        assert len(processed_conversations) == 1
        assert stats['initial_count'] == 2
        assert stats['processed_count'] == 1
        assert stats['skipped_empty_text'] == 0
        assert stats['sampled_count'] == 0
        
        # Should process the first conversation successfully
        assert processed_conversations[0]['id'] == 'conv_error'
    
    def test_preprocess_conversations_empty_list(self, data_preprocessor):
        """Test conversation preprocessing with empty list."""
        processed_conversations, stats = data_preprocessor.preprocess_conversations([])
        
        assert len(processed_conversations) == 0
        assert stats['initial_count'] == 0
        assert stats['processed_count'] == 0
        assert stats['skipped_empty_text'] == 0
        assert stats['sampled_count'] == 0
    
    def test_preprocess_conversations_none_options(self, data_preprocessor, sample_raw_conversations):
        """Test conversation preprocessing with None options."""
        processed_conversations, stats = data_preprocessor.preprocess_conversations(
            sample_raw_conversations, None
        )
        
        assert len(processed_conversations) == 2
        assert stats['initial_count'] == 2
        assert stats['processed_count'] == 2
        assert stats['skipped_empty_text'] == 0
        assert stats['sampled_count'] == 0
    
    def test_preprocess_conversations_empty_options(self, data_preprocessor, sample_raw_conversations):
        """Test conversation preprocessing with empty options."""
        processed_conversations, stats = data_preprocessor.preprocess_conversations(
            sample_raw_conversations, {}
        )
        
        assert len(processed_conversations) == 2
        assert stats['initial_count'] == 2
        assert stats['processed_count'] == 2
        assert stats['skipped_empty_text'] == 0
        assert stats['sampled_count'] == 0
    
    def test_preprocess_conversations_large_sampling(self, data_preprocessor, sample_raw_conversations):
        """Test conversation preprocessing with sampling larger than available."""
        options = {'max_conversations': 10}  # More than available
        processed_conversations, stats = data_preprocessor.preprocess_conversations(
            sample_raw_conversations, options
        )
        
        assert len(processed_conversations) == 2
        assert stats['initial_count'] == 2
        assert stats['processed_count'] == 2
        assert stats['sampled_count'] == 2
        assert stats['skipped_empty_text'] == 0
    
    def test_preprocess_conversations_zero_sampling(self, data_preprocessor, sample_raw_conversations):
        """Test conversation preprocessing with zero sampling."""
        options = {'max_conversations': 0}
        processed_conversations, stats = data_preprocessor.preprocess_conversations(
            sample_raw_conversations, options
        )
        
        assert len(processed_conversations) == 0
        assert stats['initial_count'] == 2
        assert stats['processed_count'] == 0
        assert stats['sampled_count'] == 0
        assert stats['skipped_empty_text'] == 0
    
    def test_preprocess_conversations_negative_sampling(self, data_preprocessor, sample_raw_conversations):
        """Test conversation preprocessing with negative sampling."""
        options = {'max_conversations': -1}
        processed_conversations, stats = data_preprocessor.preprocess_conversations(
            sample_raw_conversations, options
        )
        
        # Should handle negative sampling gracefully
        assert len(processed_conversations) == 0
        assert stats['initial_count'] == 2
        assert stats['processed_count'] == 0
        assert stats['sampled_count'] == 0
        assert stats['skipped_empty_text'] == 0
    
    def test_preprocess_conversations_complex_html(self, data_preprocessor):
        """Test conversation preprocessing with complex HTML."""
        conversations_with_complex_html = [
            {
                'id': 'conv_html',
                'created_at': 1640995200,
                'updated_at': 1640995200,
                'state': 'open',
                'open': True,
                'read': True,
                'admin_assignee': {'id': 'agent_1', 'name': 'Dae-Ho'},
                'team_assignee': {'id': 'team_1', 'name': 'Support Team'},
                'contact': {'id': 'user_1', 'email': 'user@example.com'},
                'source': {
                    'type': 'conversation',
                    'body': '<div><p>Hello <span>world</span></p><br/><a href="#">link</a></div>'
                },
                'tags': {'tags': []},
                'conversation_topics': [],
                'custom_attributes': {},
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'id': 'part_1',
                            'part_type': 'comment',
                            'body': '<div><p>Hello <span>world</span></p><br/><a href="#">link</a></div>',
                            'author': {'type': 'user', 'id': 'user_1'},
                            'created_at': 1640995200
                        }
                    ]
                }
            }
        ]
        
        processed_conversations, stats = data_preprocessor.preprocess_conversations(
            conversations_with_complex_html
        )
        
        assert len(processed_conversations) == 1
        assert stats['initial_count'] == 1
        assert stats['processed_count'] == 1
        assert stats['skipped_empty_text'] == 0
        assert stats['sampled_count'] == 0
        
        # Check that HTML is properly cleaned
        conv = processed_conversations[0]
        assert 'Hello world link' in conv['full_text']
        assert '<div>' not in conv['full_text']
        assert '<p>' not in conv['full_text']
        assert '<span>' not in conv['full_text']
        assert '<br/>' not in conv['full_text']
        assert '<a href="#">' not in conv['full_text']
    
    def test_preprocess_conversations_unicode_content(self, data_preprocessor):
        """Test conversation preprocessing with unicode content."""
        conversations_with_unicode = [
            {
                'id': 'conv_unicode',
                'created_at': 1640995200,
                'updated_at': 1640995200,
                'state': 'open',
                'open': True,
                'read': True,
                'admin_assignee': {'id': 'agent_1', 'name': 'Dae-Ho'},
                'team_assignee': {'id': 'team_1', 'name': 'Support Team'},
                'contact': {'id': 'user_1', 'email': 'user@example.com'},
                'source': {
                    'type': 'conversation',
                    'body': 'Hello 🌍 world! I need help with billing 💰'
                },
                'tags': {'tags': []},
                'conversation_topics': [],
                'custom_attributes': {},
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'id': 'part_1',
                            'part_type': 'comment',
                            'body': 'Hello 🌍 world! I need help with billing 💰',
                            'author': {'type': 'user', 'id': 'user_1'},
                            'created_at': 1640995200
                        }
                    ]
                }
            }
        ]
        
        processed_conversations, stats = data_preprocessor.preprocess_conversations(
            conversations_with_unicode
        )
        
        assert len(processed_conversations) == 1
        assert stats['initial_count'] == 1
        assert stats['processed_count'] == 1
        assert stats['skipped_empty_text'] == 0
        assert stats['sampled_count'] == 0
        
        # Check that unicode is preserved
        conv = processed_conversations[0]
        assert 'Hello 🌍 world! I need help with billing 💰' in conv['full_text']
        assert '🌍' in conv['full_text']
        assert '💰' in conv['full_text']
    
    def test_preprocess_conversations_special_characters(self, data_preprocessor):
        """Test conversation preprocessing with special characters."""
        conversations_with_special_chars = [
            {
                'id': 'conv_special',
                'created_at': 1640995200,
                'updated_at': 1640995200,
                'state': 'open',
                'open': True,
                'read': True,
                'admin_assignee': {'id': 'agent_1', 'name': 'Dae-Ho'},
                'team_assignee': {'id': 'team_1', 'name': 'Support Team'},
                'contact': {'id': 'user_1', 'email': 'user@example.com'},
                'source': {
                    'type': 'conversation',
                    'body': 'I need help with billing! @#$%^&*()_+-=[]{}|;:,.<>?'
                },
                'tags': {'tags': []},
                'conversation_topics': [],
                'custom_attributes': {},
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'id': 'part_1',
                            'part_type': 'comment',
                            'body': 'I need help with billing! @#$%^&*()_+-=[]{}|;:,.<>?',
                            'author': {'type': 'user', 'id': 'user_1'},
                            'created_at': 1640995200
                        }
                    ]
                }
            }
        ]
        
        processed_conversations, stats = data_preprocessor.preprocess_conversations(
            conversations_with_special_chars
        )
        
        assert len(processed_conversations) == 1
        assert stats['initial_count'] == 1
        assert stats['processed_count'] == 1
        assert stats['skipped_empty_text'] == 0
        assert stats['sampled_count'] == 0
        
        # Check that special characters are preserved
        conv = processed_conversations[0]
        assert 'I need help with billing! @#$%^&*()_+-=[]{}|;:,.<>?' in conv['full_text']
        assert '!' in conv['full_text']
        assert '@' in conv['full_text']
        assert '#' in conv['full_text']
        assert '$' in conv['full_text']
        assert '%' in conv['full_text']
        assert '^' in conv['full_text']
        assert '&' in conv['full_text']
        assert '*' in conv['full_text']
        assert '(' in conv['full_text']
        assert ')' in conv['full_text']
        assert '_' in conv['full_text']
        assert '+' in conv['full_text']
        assert '-' in conv['full_text']
        assert '=' in conv['full_text']
        assert '[' in conv['full_text']
        assert ']' in conv['full_text']
        assert '{' in conv['full_text']
        assert '}' in conv['full_text']
        assert '|' in conv['full_text']
        assert ';' in conv['full_text']
        assert ':' in conv['full_text']
        assert ',' in conv['full_text']
        assert '.' in conv['full_text']
        assert '<' in conv['full_text']
        assert '>' in conv['full_text']
        assert '?' in conv['full_text']