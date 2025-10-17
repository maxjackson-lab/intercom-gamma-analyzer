"""
Unit tests for AgentFeedbackSeparator.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, List

from services.agent_feedback_separator import AgentFeedbackSeparator


class TestAgentFeedbackSeparator:
    """Test cases for AgentFeedbackSeparator."""
    
    @pytest.fixture
    def separator(self):
        """Create an AgentFeedbackSeparator instance for testing."""
        return AgentFeedbackSeparator()
    
    @pytest.fixture
    def sample_conversations(self):
        """Create sample conversations for testing."""
        return [
            {
                'id': 'conv_1',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'body': 'Hi, I need help with billing',
                            'author': {'type': 'user', 'name': 'John Doe', 'email': 'john@example.com'}
                        },
                        {
                            'body': 'Hello! I\'m Finn, your AI assistant. How can I help you today?',
                            'author': {'type': 'admin', 'name': 'Finn AI', 'email': 'finn@intercom.com'}
                        }
                    ]
                }
            },
            {
                'id': 'conv_2',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'body': 'I have a technical issue',
                            'author': {'type': 'user', 'name': 'Jane Smith', 'email': 'jane@example.com'}
                        },
                        {
                            'body': 'Hello from Boldr support team. We\'re here to help!',
                            'author': {'type': 'admin', 'name': 'Boldr Agent', 'email': 'support@boldr.com'}
                        }
                    ]
                }
            },
            {
                'id': 'conv_3',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'body': 'Can you help me with my account?',
                            'author': {'type': 'user', 'name': 'Bob Wilson', 'email': 'bob@example.com'}
                        },
                        {
                            'body': 'Horatio support team here. How can we assist you?',
                            'author': {'type': 'admin', 'name': 'Horatio Agent', 'email': 'support@horatio.com'}
                        }
                    ]
                }
            },
            {
                'id': 'conv_4',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'body': 'I need assistance with the product',
                            'author': {'type': 'user', 'name': 'Alice Brown', 'email': 'alice@example.com'}
                        },
                        {
                            'body': 'Gamma CX team here to help with your request.',
                            'author': {'type': 'admin', 'name': 'Gamma CX', 'email': 'cx@gamma.app'}
                        }
                    ]
                }
            },
            {
                'id': 'conv_5',
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'body': 'I have a question about pricing',
                            'author': {'type': 'user', 'name': 'Charlie Davis', 'email': 'charlie@example.com'}
                        }
                    ]
                }
            }
        ]
    
    def test_identify_finn_ai(self, separator, sample_conversations):
        """Test identification of Finn AI conversations."""
        conv = sample_conversations[0]  # Contains Finn AI response
        agent_type = separator._identify_agent_type(conv)
        assert agent_type == 'finn_ai'
    
    def test_identify_boldr_support(self, separator, sample_conversations):
        """Test identification of Boldr support conversations."""
        conv = sample_conversations[1]  # Contains Boldr response
        agent_type = separator._identify_agent_type(conv)
        assert agent_type == 'boldr_support'
    
    def test_identify_horatio_support(self, separator, sample_conversations):
        """Test identification of Horatio support conversations."""
        conv = sample_conversations[2]  # Contains Horatio response
        agent_type = separator._identify_agent_type(conv)
        assert agent_type == 'horatio_support'
    
    def test_identify_gamma_cx_staff(self, separator, sample_conversations):
        """Test identification of Gamma CX staff conversations."""
        conv = sample_conversations[3]  # Contains Gamma CX response
        agent_type = separator._identify_agent_type(conv)
        assert agent_type == 'gamma_cx_staff'
    
    def test_identify_customer_only(self, separator, sample_conversations):
        """Test identification of customer-only conversations."""
        conv = sample_conversations[4]  # Only customer message
        agent_type = separator._identify_agent_type(conv)
        assert agent_type == 'customer_only'
    
    def test_case_insensitive_matching(self, separator):
        """Test case-insensitive matching for agent patterns."""
        conv = {
            'id': 'conv_case_test',
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'body': 'Hello from BOLDR support team!',
                        'author': {'type': 'admin', 'name': 'Boldr Agent', 'email': 'support@BOLDR.COM'}
                    }
                ]
            }
        }
        
        agent_type = separator._identify_agent_type(conv)
        assert agent_type == 'boldr_support'
    
    def test_separate_by_agent_type(self, separator, sample_conversations):
        """Test separating conversations by agent type."""
        separated = separator.separate_by_agent_type(sample_conversations)
        
        assert len(separated['finn_ai']) == 1
        assert len(separated['boldr_support']) == 1
        assert len(separated['horatio_support']) == 1
        assert len(separated['gamma_cx_staff']) == 1
        assert len(separated['customer_only']) == 1
        assert len(separated['mixed_agent']) == 0
    
    def test_get_agent_statistics(self, separator, sample_conversations):
        """Test getting agent statistics."""
        separated = separator.separate_by_agent_type(sample_conversations)
        stats = separator.get_agent_statistics(separated)
        
        assert stats['total_conversations'] == 5
        assert stats['agent_distribution']['finn_ai'] == 1
        assert stats['agent_distribution']['boldr_support'] == 1
        assert stats['agent_percentages']['finn_ai'] == 20.0
        assert stats['agent_percentages']['boldr_support'] == 20.0
    
    def test_filter_by_agent_type(self, separator, sample_conversations):
        """Test filtering conversations by specific agent types."""
        filtered = separator.filter_by_agent_type(
            sample_conversations, 
            ['finn_ai', 'boldr_support']
        )
        
        assert len(filtered) == 2
        agent_types = [separator._identify_agent_type(conv) for conv in filtered]
        assert 'finn_ai' in agent_types
        assert 'boldr_support' in agent_types
    
    def test_extract_conversation_text(self, separator, sample_conversations):
        """Test extracting text content from conversations."""
        conv = sample_conversations[0]
        text = separator._extract_conversation_text(conv)
        
        assert 'Hi, I need help with billing' in text
        assert 'Finn' in text
        assert 'john@example.com' in text
    
    def test_mixed_agent_detection(self, separator):
        """Test detection of conversations with multiple agent types."""
        conv = {
            'id': 'conv_mixed',
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'body': 'I need help',
                        'author': {'type': 'user', 'name': 'User', 'email': 'user@example.com'}
                    },
                    {
                        'body': 'Hello! I\'m Finn, your AI assistant.',
                        'author': {'type': 'admin', 'name': 'Finn AI', 'email': 'finn@intercom.com'}
                    },
                    {
                        'body': 'Boldr support team here to help!',
                        'author': {'type': 'admin', 'name': 'Boldr Agent', 'email': 'support@boldr.com'}
                    }
                ]
            }
        }
        
        agent_type = separator._identify_agent_type(conv)
        assert agent_type == 'mixed_agent'
    
    def test_empty_conversation_list(self, separator):
        """Test handling of empty conversation list."""
        separated = separator.separate_by_agent_type([])
        
        for agent_type, conversations in separated.items():
            assert len(conversations) == 0
    
    def test_conversation_without_parts(self, separator):
        """Test handling of conversations without conversation_parts."""
        conv = {
            'id': 'conv_no_parts',
            'source': {'body': 'I need help with something'}
        }
        
        agent_type = separator._identify_agent_type(conv)
        assert agent_type == 'customer_only'
    
    def test_conversation_with_custom_attributes(self, separator):
        """Test handling of conversations with custom attributes."""
        conv = {
            'id': 'conv_custom_attrs',
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'body': 'I need help',
                        'author': {'type': 'user', 'name': 'User', 'email': 'user@example.com'}
                    }
                ]
            },
            'custom_attributes': {
                'User Sentiment': 'positive',
                'Language': 'en'
            }
        }
        
        text = separator._extract_conversation_text(conv)
        assert 'positive' in text
        assert 'en' in text
