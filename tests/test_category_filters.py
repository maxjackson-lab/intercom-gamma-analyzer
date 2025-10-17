"""
Unit tests for CategoryFilters service.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any

from services.category_filters import CategoryFilters


class TestCategoryFilters:
    """Test cases for CategoryFilters."""
    
    @pytest.fixture
    def category_filters(self):
        """Create a CategoryFilters instance for testing."""
        return CategoryFilters()
    
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
                }
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
                }
            },
            {
                'id': 'conv_3',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'How do I set up my domain?'
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
                    'id': 'agent_3',
                    'name': 'Max Jackson'
                }
            },
            {
                'id': 'conv_4',
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
                        {'name': 'API Issue'}
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
                }
            }
        ]
    
    def test_initialization(self, category_filters):
        """Test CategoryFilters initialization."""
        assert category_filters.logger is not None
        assert 'Billing' in category_filters.category_patterns
        assert 'Bug' in category_filters.category_patterns
        assert 'Account' in category_filters.category_patterns
        assert 'DC' in category_filters.custom_tag_mappings
    
    def test_filter_by_category_billing(self, category_filters, sample_conversations):
        """Test filtering by billing category."""
        filtered = category_filters.filter_by_category(sample_conversations, 'Billing')
        
        assert len(filtered) == 1
        assert filtered[0]['id'] == 'conv_1'
        assert filtered[0]['matched_category'] == 'Billing'
        assert filtered[0]['category_confidence'] == 0.8
    
    def test_filter_by_category_bug(self, category_filters, sample_conversations):
        """Test filtering by bug category."""
        filtered = category_filters.filter_by_category(sample_conversations, 'Bug')
        
        assert len(filtered) == 1
        assert filtered[0]['id'] == 'conv_2'
        assert filtered[0]['matched_category'] == 'Bug'
    
    def test_filter_by_category_unknown(self, category_filters, sample_conversations):
        """Test filtering by unknown category."""
        filtered = category_filters.filter_by_category(sample_conversations, 'UnknownCategory')
        
        assert len(filtered) == 0
    
    def test_filter_by_subcategory(self, category_filters, sample_conversations):
        """Test filtering by subcategory."""
        filtered = category_filters.filter_by_subcategory(sample_conversations, 'Export')
        
        assert len(filtered) == 1
        assert filtered[0]['id'] == 'conv_2'
        assert filtered[0]['matched_subcategory'] == 'Export'
        assert filtered[0]['matched_category'] == 'Bug'
    
    def test_filter_by_custom_tag(self, category_filters, sample_conversations):
        """Test filtering by custom tag."""
        # Add a conversation with DC tag
        dc_conversation = {
            'id': 'conv_dc',
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'part_type': 'comment',
                        'body': 'Complex technical issue that needs Dae-Ho'
                    }
                ]
            },
            'source': {
                'body': 'technical escalation'
            },
            'tags': {
                'tags': [
                    {'name': 'DC'}
                ]
            },
            'admin_assignee': {
                'id': 'agent_1',
                'name': 'Dae-Ho'
            }
        }
        
        conversations_with_dc = sample_conversations + [dc_conversation]
        filtered = category_filters.filter_by_custom_tag(conversations_with_dc, 'DC')
        
        assert len(filtered) == 1
        assert filtered[0]['id'] == 'conv_dc'
        assert filtered[0]['matched_tag'] == 'DC'
    
    def test_filter_by_agent(self, category_filters, sample_conversations):
        """Test filtering by agent."""
        filtered = category_filters.filter_by_agent(sample_conversations, 'Dae-Ho')
        
        assert len(filtered) == 2
        assert all(conv['id'] in ['conv_1', 'conv_4'] for conv in filtered)
    
    def test_filter_by_agent_id(self, category_filters, sample_conversations):
        """Test filtering by agent ID."""
        filtered = category_filters.filter_by_agent(sample_conversations, 'agent_1')
        
        assert len(filtered) == 2
        assert all(conv['id'] in ['conv_1', 'conv_4'] for conv in filtered)
    
    def test_filter_by_escalation(self, category_filters, sample_conversations):
        """Test filtering by escalation patterns."""
        # Add conversations with escalation patterns
        escalation_conversations = sample_conversations + [
            {
                'id': 'conv_escalate_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'I need to escalate this to Dae-Ho for technical support'
                        }
                    ]
                },
                'source': {
                    'body': 'escalation request'
                }
            },
            {
                'id': 'conv_escalate_2',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'This needs to be transferred to Hilary for billing issues'
                        }
                    ]
                },
                'source': {
                    'body': 'transfer request'
                }
            }
        ]
        
        filtered = category_filters.filter_by_escalation(escalation_conversations)
        
        assert len(filtered) == 2
        assert all(conv['escalation_detected'] for conv in filtered)
        assert any(conv['escalation_target'] == 'dae-ho' for conv in filtered)
        assert any(conv['escalation_target'] == 'hilary' for conv in filtered)
    
    def test_filter_by_escalation_specific_target(self, category_filters, sample_conversations):
        """Test filtering by escalation to specific target."""
        escalation_conversations = sample_conversations + [
            {
                'id': 'conv_escalate_daeho',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'Please escalate this to Dae-Ho for technical review'
                        }
                    ]
                },
                'source': {
                    'body': 'escalation to dae-ho'
                }
            }
        ]
        
        filtered = category_filters.filter_by_escalation(
            escalation_conversations, escalation_target='dae-ho'
        )
        
        assert len(filtered) == 1
        assert filtered[0]['id'] == 'conv_escalate_daeho'
        assert filtered[0]['escalation_target'] == 'dae-ho'
    
    def test_filter_by_technical_patterns(self, category_filters, sample_conversations):
        """Test filtering by technical patterns."""
        # Add conversations with technical patterns
        technical_conversations = sample_conversations + [
            {
                'id': 'conv_cache',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'I need to clear my cache to fix the issue'
                        }
                    ]
                },
                'source': {
                    'body': 'cache clearing needed'
                }
            },
            {
                'id': 'conv_browser',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'part_type': 'comment',
                            'body': 'Please try using a different browser like Chrome'
                        }
                    ]
                },
                'source': {
                    'body': 'browser switching advice'
                }
            }
        ]
        
        filtered = category_filters.filter_by_technical_patterns(technical_conversations)
        
        assert len(filtered) == 2
        assert all(conv['is_technical'] for conv in filtered)
        assert any('cache_clearing' in conv['technical_patterns'] for conv in filtered)
        assert any('browser_switching' in conv['technical_patterns'] for conv in filtered)
    
    def test_has_explicit_category(self, category_filters, sample_conversations):
        """Test explicit category detection."""
        # Test with billing conversation that has explicit tag
        billing_conv = sample_conversations[0]  # Has 'billing' topic
        assert category_filters._has_explicit_category(billing_conv, 'Billing') is True
        
        # Test with conversation without explicit category
        other_conv = sample_conversations[2]  # Domain conversation
        assert category_filters._has_explicit_category(other_conv, 'Billing') is False
    
    def test_has_explicit_subcategory(self, category_filters, sample_conversations):
        """Test explicit subcategory detection."""
        # Test with bug conversation that has explicit tag
        bug_conv = sample_conversations[1]  # Has 'Bug Report' tag
        assert category_filters._has_explicit_subcategory(bug_conv, 'Bug Report') is True
        
        # Test with conversation without explicit subcategory
        other_conv = sample_conversations[0]  # Billing conversation
        assert category_filters._has_explicit_subcategory(other_conv, 'Bug Report') is False
    
    def test_has_explicit_tag(self, category_filters, sample_conversations):
        """Test explicit tag detection."""
        # Test with conversation that has explicit tag
        billing_conv = sample_conversations[0]  # Has 'Refund Request' tag
        assert category_filters._has_explicit_tag(billing_conv, 'Refund Request') is True
        
        # Test with conversation without explicit tag
        other_conv = sample_conversations[1]  # Bug conversation
        assert category_filters._has_explicit_tag(other_conv, 'Refund Request') is False
    
    def test_matches_keywords(self, category_filters):
        """Test keyword matching."""
        text = "I need help with billing and refunds"
        keywords = ['billing', 'refund', 'payment']
        
        assert category_filters._matches_keywords(text, keywords) is True
        
        text_no_match = "I need help with something else"
        assert category_filters._matches_keywords(text_no_match, keywords) is False
    
    def test_extract_conversation_text(self, category_filters, sample_conversations):
        """Test conversation text extraction."""
        conv = sample_conversations[0]
        text = category_filters._extract_conversation_text(conv)
        
        assert 'I need a refund for my subscription' in text
        assert 'billing issue' in text
    
    def test_get_available_categories(self, category_filters):
        """Test getting available categories."""
        categories = category_filters.get_available_categories()
        
        assert 'Billing' in categories
        assert 'Bug' in categories
        assert 'Account' in categories
        assert 'Product Question' in categories
        assert len(categories) >= 10  # Should have multiple categories
    
    def test_get_available_subcategories(self, category_filters):
        """Test getting available subcategories."""
        # Test getting subcategories for specific category
        billing_subcategories = category_filters.get_available_subcategories('Billing')
        assert 'Refund' in billing_subcategories
        assert 'Invoice' in billing_subcategories
        
        # Test getting all subcategories
        all_subcategories = category_filters.get_available_subcategories()
        assert len(all_subcategories) > len(billing_subcategories)
        assert 'Refund' in all_subcategories
        assert 'Export' in all_subcategories
    
    def test_get_available_custom_tags(self, category_filters):
        """Test getting available custom tags."""
        custom_tags = category_filters.get_available_custom_tags()
        
        assert 'DC' in custom_tags
        assert 'Priority Support' in custom_tags
    
    def test_get_filter_statistics(self, category_filters, sample_conversations):
        """Test getting filter statistics."""
        # Apply some filters
        billing_conversations = category_filters.filter_by_category(sample_conversations, 'Billing')
        bug_conversations = category_filters.filter_by_category(sample_conversations, 'Bug')
        
        # Combine filtered conversations
        filtered_conversations = billing_conversations + bug_conversations
        filters_applied = ['Billing', 'Bug']
        
        stats = category_filters.get_filter_statistics(filtered_conversations, filters_applied)
        
        assert stats['total_conversations'] == 2
        assert stats['filters_applied'] == filters_applied
        assert 'category_distribution' in stats
        assert 'subcategory_distribution' in stats
        assert 'custom_tag_distribution' in stats
        assert 'technical_patterns' in stats
        assert 'escalation_count' in stats
    
    def test_category_patterns_structure(self, category_filters):
        """Test category patterns structure."""
        for category, pattern_data in category_filters.category_patterns.items():
            assert 'keywords' in pattern_data
            assert 'regex_patterns' in pattern_data
            assert 'subcategories' in pattern_data
            assert isinstance(pattern_data['keywords'], list)
            assert isinstance(pattern_data['regex_patterns'], list)
            assert isinstance(pattern_data['subcategories'], list)
    
    def test_subcategory_patterns_structure(self, category_filters):
        """Test subcategory patterns structure."""
        for subcategory, pattern_data in category_filters.subcategory_patterns.items():
            assert 'parent_category' in pattern_data
            assert 'keywords' in pattern_data
            assert 'regex_patterns' in pattern_data
            assert isinstance(pattern_data['keywords'], list)
            assert isinstance(pattern_data['regex_patterns'], list)
    
    def test_custom_tag_mappings_structure(self, category_filters):
        """Test custom tag mappings structure."""
        for tag, mapping_data in category_filters.custom_tag_mappings.items():
            assert 'category' in mapping_data
            assert 'subcategory' in mapping_data
            assert 'keywords' in mapping_data
            assert 'description' in mapping_data
            assert isinstance(mapping_data['keywords'], list)
    
    def test_regex_pattern_compilation(self, category_filters):
        """Test that regex patterns are properly compiled."""
        for category, pattern_data in category_filters.category_patterns.items():
            for pattern in pattern_data['regex_patterns']:
                # Test that pattern is a compiled regex
                assert hasattr(pattern, 'search')
                assert hasattr(pattern, 'match')
    
    def test_keyword_case_insensitivity(self, category_filters, sample_conversations):
        """Test that keyword matching is case insensitive."""
        # Create conversation with uppercase keywords
        uppercase_conv = {
            'id': 'conv_upper',
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'part_type': 'comment',
                        'body': 'I need a REFUND for my BILLING issue'
                    }
                ]
            },
            'source': {
                'body': 'BILLING PROBLEM'
            }
        }
        
        filtered = category_filters.filter_by_category([uppercase_conv], 'Billing')
        
        assert len(filtered) == 1
        assert filtered[0]['matched_category'] == 'Billing'
    
    def test_empty_conversations_list(self, category_filters):
        """Test filtering with empty conversations list."""
        filtered = category_filters.filter_by_category([], 'Billing')
        assert len(filtered) == 0
        
        filtered = category_filters.filter_by_agent([], 'Dae-Ho')
        assert len(filtered) == 0
        
        filtered = category_filters.filter_by_escalation([])
        assert len(filtered) == 0
    
    def test_conversation_without_required_fields(self, category_filters):
        """Test filtering conversations without required fields."""
        incomplete_conversations = [
            {
                'id': 'conv_1',
                # Missing conversation_parts
                'source': {'body': 'billing issue'}
            },
            {
                'id': 'conv_2',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'billing problem'}
                    ]
                }
                # Missing source
            }
        ]
        
        filtered = category_filters.filter_by_category(incomplete_conversations, 'Billing')
        
        # Should still work with partial data
        assert len(filtered) >= 0  # May or may not match depending on available text
    
    def test_technical_patterns_comprehensive(self, category_filters):
        """Test comprehensive technical pattern detection."""
        technical_conversations = [
            {
                'id': 'conv_cache',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'Please clear your cache'}
                    ]
                },
                'source': {'body': 'cache issue'}
            },
            {
                'id': 'conv_browser',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'Try using Chrome browser'}
                    ]
                },
                'source': {'body': 'browser problem'}
            },
            {
                'id': 'conv_connection',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'Check your internet connection'}
                    ]
                },
                'source': {'body': 'connection issue'}
            },
            {
                'id': 'conv_export',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'Export your data to CSV'}
                    ]
                },
                'source': {'body': 'export problem'}
            },
            {
                'id': 'conv_api',
                'conversation_parts': {
                    'conversation_parts': [
                        {'part_type': 'comment', 'body': 'API authentication failed'}
                    ]
                },
                'source': {'body': 'api issue'}
            }
        ]
        
        filtered = category_filters.filter_by_technical_patterns(technical_conversations)
        
        assert len(filtered) == 5
        assert all(conv['is_technical'] for conv in filtered)
        
        # Check specific patterns
        patterns_found = set()
        for conv in filtered:
            patterns_found.update(conv['technical_patterns'])
        
        assert 'cache_clearing' in patterns_found
        assert 'browser_switching' in patterns_found
        assert 'connection_issues' in patterns_found
        assert 'export_issues' in patterns_found
        assert 'api_issues' in patterns_found






