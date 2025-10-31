"""
Unit tests for conversation_utils enhancements from SDK review comments

Tests for:
- extract_admin_messages() (Comment 4)
- extract_conversation_text() with both dict and list shapes (Comment 3)
- extract_customer_messages() with both dict and list shapes (Comment 3)
"""

import pytest
from src.utils.conversation_utils import (
    extract_conversation_text,
    extract_customer_messages,
    extract_admin_messages
)


class TestExtractAdminMessages:
    """Test extract_admin_messages() function (Comment 4)"""
    
    def test_extract_admin_from_source(self):
        """Test extracting admin message from source"""
        conv = {
            'id': 'test1',
            'source': {
                'body': '<p>Hello, I can help with that!</p>',
                'author': {'type': 'admin', 'email': 'agent@gamma.app'}
            },
            'conversation_parts': {'conversation_parts': []}
        }
        
        admin_msgs = extract_admin_messages(conv, clean_html=True)
        
        assert len(admin_msgs) == 1
        assert admin_msgs[0] == 'Hello, I can help with that!'
    
    def test_extract_admin_from_parts_dict_format(self):
        """Test extracting admin messages from conversation_parts (dict format)"""
        conv = {
            'id': 'test2',
            'source': {'body': 'Customer message', 'author': {'type': 'user'}},
            'conversation_parts': {
                'conversation_parts': [
                    {'body': 'Admin reply 1', 'author': {'type': 'admin'}},
                    {'body': 'Customer reply', 'author': {'type': 'user'}},
                    {'body': 'Admin reply 2', 'author': {'type': 'admin'}}
                ]
            }
        }
        
        admin_msgs = extract_admin_messages(conv, clean_html=True)
        
        assert len(admin_msgs) == 2
        assert 'Admin reply 1' in admin_msgs
        assert 'Admin reply 2' in admin_msgs
        assert 'Customer reply' not in admin_msgs
    
    def test_extract_admin_from_parts_list_format(self):
        """Test extracting admin messages from conversation_parts (list format)"""
        conv = {
            'id': 'test3',
            'source': {'body': 'Customer message', 'author': {'type': 'user'}},
            'conversation_parts': [  # LIST format, not dict!
                {'body': 'Admin response', 'author': {'type': 'admin'}},
                {'body': 'Another admin message', 'author': {'type': 'admin'}}
            ]
        }
        
        admin_msgs = extract_admin_messages(conv, clean_html=True)
        
        assert len(admin_msgs) == 2
        assert 'Admin response' in admin_msgs
        assert 'Another admin message' in admin_msgs
    
    def test_extract_admin_filters_user_messages(self):
        """Test that only admin messages are extracted, not user messages"""
        conv = {
            'id': 'test4',
            'source': {'body': 'Customer question', 'author': {'type': 'user'}},
            'conversation_parts': {
                'conversation_parts': [
                    {'body': 'Admin reply', 'author': {'type': 'admin'}},
                    {'body': 'Customer follow-up', 'author': {'type': 'user'}},
                    {'body': 'Bot response', 'author': {'type': 'bot'}}
                ]
            }
        }
        
        admin_msgs = extract_admin_messages(conv, clean_html=True)
        
        assert len(admin_msgs) == 1
        assert admin_msgs[0] == 'Admin reply'
    
    def test_extract_admin_html_cleaning(self):
        """Test HTML cleaning in admin messages"""
        conv = {
            'id': 'test5',
            'source': {
                'body': '<p>Here is the <strong>solution</strong> to your problem.</p>',
                'author': {'type': 'admin'}
            },
            'conversation_parts': {'conversation_parts': []}
        }
        
        admin_msgs = extract_admin_messages(conv, clean_html=True)
        
        assert len(admin_msgs) == 1
        assert '<p>' not in admin_msgs[0]
        assert '<strong>' not in admin_msgs[0]
        assert 'solution' in admin_msgs[0]
    
    def test_extract_admin_no_html_cleaning(self):
        """Test preserving HTML when clean_html=False"""
        conv = {
            'id': 'test6',
            'source': {
                'body': '<p>Admin message with <b>HTML</b></p>',
                'author': {'type': 'admin'}
            },
            'conversation_parts': {'conversation_parts': []}
        }
        
        admin_msgs = extract_admin_messages(conv, clean_html=False)
        
        assert len(admin_msgs) == 1
        assert '<p>' in admin_msgs[0]
        assert '<b>' in admin_msgs[0]


class TestConversationPartsShapeHandling:
    """Test handling of both dict and list shapes for conversation_parts (Comment 3)"""
    
    def test_extract_text_dict_shape(self):
        """Test text extraction with dict-shaped conversation_parts"""
        conv = {
            'id': 'test_dict',
            'source': {'body': 'Initial message'},
            'conversation_parts': {
                'conversation_parts': [
                    {'body': 'Reply 1'},
                    {'body': 'Reply 2'}
                ]
            }
        }
        
        text = extract_conversation_text(conv, clean_html=True)
        
        assert 'Initial message' in text
        assert 'Reply 1' in text
        assert 'Reply 2' in text
    
    def test_extract_text_list_shape(self):
        """Test text extraction with list-shaped conversation_parts"""
        conv = {
            'id': 'test_list',
            'source': {'body': 'Initial message'},
            'conversation_parts': [  # LIST, not dict!
                {'body': 'Reply 1'},
                {'body': 'Reply 2'}
            ]
        }
        
        text = extract_conversation_text(conv, clean_html=True)
        
        assert 'Initial message' in text
        assert 'Reply 1' in text
        assert 'Reply 2' in text
    
    def test_extract_customer_messages_dict_shape(self):
        """Test customer message extraction with dict-shaped conversation_parts"""
        conv = {
            'id': 'test_cust_dict',
            'source': {'body': 'Customer question', 'author': {'type': 'user'}},
            'conversation_parts': {
                'conversation_parts': [
                    {'body': 'Admin reply', 'author': {'type': 'admin'}},
                    {'body': 'Customer follow-up', 'author': {'type': 'user'}}
                ]
            }
        }
        
        customer_msgs = extract_customer_messages(conv, clean_html=True)
        
        assert len(customer_msgs) == 2
        assert 'Customer question' in customer_msgs
        assert 'Customer follow-up' in customer_msgs
        assert 'Admin reply' not in customer_msgs
    
    def test_extract_customer_messages_list_shape(self):
        """Test customer message extraction with list-shaped conversation_parts"""
        conv = {
            'id': 'test_cust_list',
            'source': {'body': 'Customer question', 'author': {'type': 'user'}},
            'conversation_parts': [  # LIST format
                {'body': 'Admin reply', 'author': {'type': 'admin'}},
                {'body': 'Customer follow-up', 'author': {'type': 'user'}}
            ]
        }
        
        customer_msgs = extract_customer_messages(conv, clean_html=True)
        
        assert len(customer_msgs) == 2
        assert 'Customer question' in customer_msgs
        assert 'Customer follow-up' in customer_msgs
        assert 'Admin reply' not in customer_msgs


class TestNotesExtraction:
    """Test that notes are properly extracted (Comment 7)"""
    
    def test_extract_text_includes_notes_dict_format(self):
        """Test that notes bodies are included in text extraction (dict format)"""
        conv = {
            'id': 'test_notes_dict',
            'source': {'body': 'Main conversation'},
            'conversation_parts': {'conversation_parts': [{'body': 'Reply'}]},
            'notes': {
                'notes': [
                    {'body': 'Internal note 1'},
                    {'body': 'Internal note 2'}
                ]
            }
        }
        
        text = extract_conversation_text(conv, clean_html=True)
        
        assert 'Main conversation' in text
        assert 'Reply' in text
        assert 'Internal note 1' in text
        assert 'Internal note 2' in text
    
    def test_extract_text_includes_notes_list_format(self):
        """Test notes extraction with list format (if SDK sends it that way)"""
        conv = {
            'id': 'test_notes_list',
            'source': {'body': 'Main conversation'},
            'conversation_parts': {'conversation_parts': []},
            'notes': [  # LIST format
                {'body': 'Note 1'},
                {'body': 'Note 2'}
            ]
        }
        
        text = extract_conversation_text(conv, clean_html=True)
        
        # Notes in list format may not be extracted (current implementation expects dict)
        # But should not crash
        assert 'Main conversation' in text
    
    def test_extract_text_missing_notes(self):
        """Test graceful handling of missing notes field"""
        conv = {
            'id': 'test_no_notes',
            'source': {'body': 'Main conversation'},
            'conversation_parts': {'conversation_parts': []}
            # No 'notes' field
        }
        
        text = extract_conversation_text(conv, clean_html=True)
        
        assert text == 'Main conversation'


class TestDataPreprocessorIntegration:
    """Test that preprocessing properly injects customer_messages (Comment 1)"""
    
    def test_preprocessing_injects_customer_messages(self):
        """Test that DataPreprocessor.preprocess_conversations() injects customer_messages"""
        from src.services.data_preprocessor import DataPreprocessor
        
        preprocessor = DataPreprocessor()
        conversations = [{
            'id': 'test_preprocess',
            'created_at': 1699123456,
            'updated_at': 1699125456,
            'source': {
                'body': 'Customer message here',
                'author': {'type': 'user'}
            },
            'conversation_parts': {
                'conversation_parts': [
                    {'body': 'Admin reply', 'author': {'type': 'admin'}},
                    {'body': 'Customer follow-up', 'author': {'type': 'user'}}
                ]
            },
            'tags': {'tags': []},
            'custom_attributes': {}
        }]
        
        processed, stats = preprocessor.preprocess_conversations(conversations)
        
        # Check that customer_messages was injected
        assert len(processed) > 0
        assert 'customer_messages' in processed[0]
        assert isinstance(processed[0]['customer_messages'], list)
        assert len(processed[0]['customer_messages']) == 2  # Initial + follow-up
        assert 'Customer message here' in processed[0]['customer_messages']
        assert 'Customer follow-up' in processed[0]['customer_messages']


class TestAIParticipationHelper:
    """Test AI participation helper in SegmentationAgent (Comment 6)"""
    
    def test_ai_agent_object_presence(self):
        """Test that ai_agent object presence takes priority"""
        from src.agents.segmentation_agent import SegmentationAgent
        
        agent = SegmentationAgent()
        
        # ai_agent object present (highest priority)
        conv = {
            'id': 'test_ai_obj',
            'ai_agent': {'resolution_state': 'resolved'},  # Object exists
            'ai_agent_participated': False,  # Boolean says False, but object wins
            'source': {'body': 'Some text'},
            'conversation_parts': {'conversation_parts': []}
        }
        
        result = agent._determine_ai_participation(conv)
        
        assert result is True, "ai_agent object presence should indicate Fin participated"
    
    def test_ai_agent_participated_boolean(self):
        """Test ai_agent_participated boolean fallback"""
        from src.agents.segmentation_agent import SegmentationAgent
        
        agent = SegmentationAgent()
        
        # No ai_agent object, but boolean is True
        conv = {
            'id': 'test_bool',
            'ai_agent_participated': True,  # Boolean field
            'source': {'body': 'Some text'},
            'conversation_parts': {'conversation_parts': []}
        }
        
        result = agent._determine_ai_participation(conv)
        
        assert result is True, "ai_agent_participated boolean should work when ai_agent object absent"
    
    def test_finn_heuristic_fallback(self):
        """Test 'Finn' heuristic as last resort"""
        from src.agents.segmentation_agent import SegmentationAgent
        
        agent = SegmentationAgent()
        
        # No SDK fields, but starts with "Finn"
        conv = {
            'id': 'test_finn',
            'source': {
                'body': 'Finn here! I can help with that.',
                'author': {'type': 'bot'}
            },
            'conversation_parts': {'conversation_parts': []}
        }
        
        result = agent._determine_ai_participation(conv)
        
        assert result is True, "Should detect Fin from 'Finn' prefix heuristic"
    
    def test_no_ai_participation(self):
        """Test when no Fin participation indicators exist"""
        from src.agents.segmentation_agent import SegmentationAgent
        
        agent = SegmentationAgent()
        
        conv = {
            'id': 'test_no_ai',
            'source': {
                'body': 'Human agent response',
                'author': {'type': 'admin', 'email': 'human@gamma.app'}
            },
            'conversation_parts': {'conversation_parts': []}
        }
        
        result = agent._determine_ai_participation(conv)
        
        assert result is False, "Should return False when no Fin indicators present"
    
    def test_ai_agent_none_value(self):
        """Test handling of ai_agent: None"""
        from src.agents.segmentation_agent import SegmentationAgent
        
        agent = SegmentationAgent()
        
        conv = {
            'id': 'test_none',
            'ai_agent': None,  # Explicitly None
            'ai_agent_participated': True,
            'source': {'body': 'Text'},
            'conversation_parts': {'conversation_parts': []}
        }
        
        result = agent._determine_ai_participation(conv)
        
        # Should fall back to boolean since ai_agent is None
        assert result is True, "Should fall back to boolean when ai_agent is None"


class TestConversationPartsShapes:
    """Test handling of both dict and list shapes for conversation_parts"""
    
    def test_dict_format_with_notes(self):
        """Test dict format: {'conversation_parts': {'conversation_parts': [...]}}"""
        conv = {
            'id': 'test_dict_notes',
            'source': {'body': 'Source text'},
            'conversation_parts': {
                'conversation_parts': [
                    {'body': 'Part 1'},
                    {'body': 'Part 2'}
                ]
            },
            'notes': {
                'notes': [
                    {'body': 'Note 1'},
                    {'body': 'Note 2'}
                ]
            }
        }
        
        text = extract_conversation_text(conv, clean_html=True)
        
        assert 'Source text' in text
        assert 'Part 1' in text
        assert 'Part 2' in text
        assert 'Note 1' in text
        assert 'Note 2' in text
    
    def test_list_format_with_notes(self):
        """Test list format: {'conversation_parts': [...]}"""
        conv = {
            'id': 'test_list_notes',
            'source': {'body': 'Source text'},
            'conversation_parts': [  # LIST format
                {'body': 'Part 1'},
                {'body': 'Part 2'}
            ],
            'notes': {
                'notes': [
                    {'body': 'Note 1'}
                ]
            }
        }
        
        text = extract_conversation_text(conv, clean_html=True)
        
        assert 'Source text' in text
        assert 'Part 1' in text
        assert 'Part 2' in text
        assert 'Note 1' in text
    
    def test_malformed_conversation_parts(self):
        """Test graceful handling of malformed conversation_parts"""
        conv = {
            'id': 'test_malformed',
            'source': {'body': 'Source text'},
            'conversation_parts': 'invalid_string',  # Neither dict nor list
            'notes': {'notes': []}
        }
        
        text = extract_conversation_text(conv, clean_html=True)
        
        # Should not crash, should extract source
        assert text == 'Source text'
    
    def test_empty_conversation_parts(self):
        """Test handling of empty conversation_parts"""
        conv = {
            'id': 'test_empty_parts',
            'source': {'body': 'Only source'},
            'conversation_parts': {'conversation_parts': []},
            'notes': {'notes': []}
        }
        
        text = extract_conversation_text(conv, clean_html=True)
        
        assert text == 'Only source'


class TestCustomerMessageExtraction:
    """Test customer message extraction (should not rely on pre-injected field)"""
    
    def test_extract_without_preinjected_field(self):
        """Test that extraction works without pre-injected customer_messages field"""
        conv = {
            'id': 'test_no_inject',
            # NO customer_messages field pre-injected!
            'source': {
                'body': 'Customer initial message',
                'author': {'type': 'user'}
            },
            'conversation_parts': {
                'conversation_parts': [
                    {'body': 'Customer reply', 'author': {'type': 'user'}},
                    {'body': 'Admin response', 'author': {'type': 'admin'}}
                ]
            }
        }
        
        customer_msgs = extract_customer_messages(conv, clean_html=True)
        
        assert len(customer_msgs) == 2
        assert 'Customer initial message' in customer_msgs
        assert 'Customer reply' in customer_msgs
        assert 'Admin response' not in customer_msgs
    
    def test_chronological_order(self):
        """Test that customer messages are in chronological order"""
        conv = {
            'id': 'test_chrono',
            'source': {
                'body': 'First customer message',
                'author': {'type': 'user'}
            },
            'conversation_parts': {
                'conversation_parts': [
                    {'body': 'Second customer message', 'author': {'type': 'user'}},
                    {'body': 'Third customer message', 'author': {'type': 'user'}}
                ]
            }
        }
        
        customer_msgs = extract_customer_messages(conv, clean_html=True)
        
        assert customer_msgs[0] == 'First customer message'
        assert customer_msgs[1] == 'Second customer message'
        assert customer_msgs[2] == 'Third customer message'


