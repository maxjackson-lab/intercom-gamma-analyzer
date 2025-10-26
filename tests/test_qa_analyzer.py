"""
Tests for QA Analyzer - Automated quality assessment
"""

import pytest
from src.utils.qa_analyzer import (
    analyze_greeting_quality,
    analyze_grammar_quality,
    analyze_formatting_quality,
    calculate_qa_metrics
)


class TestGreetingAnalysis:
    """Test greeting quality detection"""
    
    def test_greeting_with_name(self):
        """Test greeting detection with customer name usage"""
        conversation = {
            'source': {
                'author': {
                    'type': 'user',
                    'name': 'John Smith'
                }
            },
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'author': {'type': 'admin'},
                        'body': 'Hi John! How can I help you today?'
                    }
                ]
            }
        }
        
        result = analyze_greeting_quality(conversation)
        
        assert result['greeting_present'] is True
        assert result['customer_name_used'] is True
        assert result['greeting_quality_score'] == 1.0
    
    def test_greeting_without_name(self):
        """Test greeting without customer name"""
        conversation = {
            'source': {'author': {'type': 'user', 'name': 'Jane Doe'}},
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'author': {'type': 'admin'},
                        'body': 'Hello! Thanks for reaching out.'
                    }
                ]
            }
        }
        
        result = analyze_greeting_quality(conversation)
        
        assert result['greeting_present'] is True
        assert result['customer_name_used'] is False
        assert result['greeting_quality_score'] == 0.5
    
    def test_no_greeting(self):
        """Test message with no greeting"""
        conversation = {
            'source': {'author': {'type': 'user', 'name': 'Bob Jones'}},
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'author': {'type': 'admin'},
                        'body': 'I can see your account shows the following issue...'
                    }
                ]
            }
        }
        
        result = analyze_greeting_quality(conversation)
        
        assert result['greeting_present'] is False
        assert result['customer_name_used'] is False
        assert result['greeting_quality_score'] == 0.0


class TestGrammarAnalysis:
    """Test grammar error detection"""
    
    def test_perfect_grammar(self):
        """Test message with no grammar errors"""
        conversation = {
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'author': {'type': 'admin'},
                        'body': "I'm happy to help you with that. Let me check your account."
                    }
                ]
            }
        }
        
        result = analyze_grammar_quality(conversation)
        
        assert result['avg_grammar_errors_per_message'] == 0.0
        assert result['total_errors'] == 0
        assert result['messages_analyzed'] == 1
    
    def test_common_errors(self):
        """Test detection of common grammar errors"""
        conversation = {
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'author': {'type': 'admin'},
                        'body': "Your welcome! I cant help with that. Its okay."
                    }
                ]
            }
        }
        
        result = analyze_grammar_quality(conversation)
        
        # Should detect: "your welcome", "cant", "Its okay"
        assert result['avg_grammar_errors_per_message'] >= 2.0
        assert result['total_errors'] >= 2
    
    def test_no_agent_messages(self):
        """Test handling of conversation with no agent messages"""
        conversation = {
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'author': {'type': 'user'},
                        'body': 'Customer message only'
                    }
                ]
            }
        }
        
        result = analyze_grammar_quality(conversation)
        
        assert result['avg_grammar_errors_per_message'] == 0.0
        assert result['messages_analyzed'] == 0


class TestFormattingAnalysis:
    """Test formatting quality detection"""
    
    def test_good_formatting(self):
        """Test well-formatted message with proper paragraphs"""
        conversation = {
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'author': {'type': 'admin'},
                        'body': '''<p>Thank you for contacting support.</p>

<p>I've reviewed your account and found the issue. Here's what I can do to help you resolve this quickly.</p>

<p>Let me know if you have any questions!</p>'''
                    }
                ]
            }
        }
        
        result = analyze_formatting_quality(conversation)
        
        assert result['proper_formatting_rate'] > 0.8
    
    def test_wall_of_text(self):
        """Test poorly formatted wall of text"""
        conversation = {
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'author': {'type': 'admin'},
                        'body': 'This is a very long message without any paragraph breaks at all which makes it very difficult to read and should be scored poorly for formatting quality because it is just one big wall of text that goes on and on without any proper structure or organization.'
                    }
                ]
            }
        }
        
        result = analyze_formatting_quality(conversation)
        
        assert result['proper_formatting_rate'] < 0.5


class TestQAMetricsCalculation:
    """Test comprehensive QA metrics calculation"""
    
    def test_calculate_qa_metrics_excellent(self):
        """Test QA calculation for excellent agent"""
        conversations = [
            {
                'source': {'author': {'type': 'user', 'name': 'Alice'}},
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'author': {'type': 'admin'},
                            'body': '<p>Hi Alice! How can I help you today?</p>\n\n<p>I\'m here to assist with any questions.</p>'
                        },
                        {
                            'author': {'type': 'admin'},
                            'body': '<p>Great! I\'ve resolved that for you.</p>'
                        }
                    ]
                }
            },
            {
                'source': {'author': {'type': 'user', 'name': 'Bob'}},
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'author': {'type': 'admin'},
                            'body': '<p>Hello Bob! Thanks for reaching out.</p>\n\n<p>Let me check that for you right away.</p>'
                        }
                    ]
                }
            }
        ]
        
        result = calculate_qa_metrics(conversations, fcr_rate=0.9, reopen_rate=0.05)
        
        assert result is not None
        assert result['greeting_present'] is True
        assert result['customer_name_used'] is True
        assert result['greeting_quality_score'] >= 0.9
        assert result['overall_qa_score'] >= 0.8
        assert result['conversations_sampled'] == 2
    
    def test_calculate_qa_metrics_poor(self):
        """Test QA calculation for poor agent"""
        conversations = [
            {
                'source': {'author': {'type': 'user', 'name': 'Customer'}},
                'conversation_parts': {
                    'conversation_parts': [
                        {
                            'author': {'type': 'admin'},
                            'body': 'your account shows teh problem its cant be fixed'
                        }
                    ]
                }
            }
        ]
        
        result = calculate_qa_metrics(conversations, fcr_rate=0.4, reopen_rate=0.3)
        
        assert result is not None
        assert result['greeting_present'] is False
        assert result['avg_grammar_errors_per_message'] > 0  # Should detect errors
        assert result['overall_qa_score'] < 0.6  # Poor performance
    
    def test_empty_conversations(self):
        """Test handling of empty conversation list"""
        result = calculate_qa_metrics([], fcr_rate=0, reopen_rate=0)
        
        assert result is None


class TestHelperFunctions:
    """Test helper functions"""
    
    def test_get_first_agent_message(self):
        """Test extraction of first agent message"""
        from src.utils.qa_analyzer import get_first_agent_message
        
        conversation = {
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Customer message'},
                    {'author': {'type': 'admin'}, 'body': 'First agent message'},
                    {'author': {'type': 'admin'}, 'body': 'Second agent message'}
                ]
            }
        }
        
        result = get_first_agent_message(conversation)
        assert result == 'First agent message'
    
    def test_get_customer_name(self):
        """Test customer name extraction"""
        from src.utils.qa_analyzer import get_customer_name
        
        conversation = {
            'source': {
                'author': {
                    'type': 'user',
                    'name': 'Test Customer'
                }
            }
        }
        
        result = get_customer_name(conversation)
        assert result == 'Test Customer'
    
    def test_strip_html(self):
        """Test HTML tag removal"""
        from src.utils.qa_analyzer import strip_html
        
        text = '<p>Hello <strong>world</strong>! This is a <em>test</em>.</p>'
        result = strip_html(text)
        
        assert result == 'Hello world! This is a test.'
        assert '<' not in result
        assert '>' not in result

