"""
Unit tests for FIN resolution logic standardization.

Tests the is_fin_resolved() and has_knowledge_gap() helper functions
to ensure consistent resolution detection across the codebase.
"""

import pytest
from src.services.fin_escalation_analyzer import is_fin_resolved, has_knowledge_gap


class TestFinResolved:
    """Test cases for is_fin_resolved() function"""
    
    def test_resolved_closed_no_admin(self):
        """Closed conversation with no admin intervention is resolved"""
        conv = {
            'state': 'closed',
            'admin_assignee_id': None,
            'conversation_rating': None,
            'statistics': {'count_reopens': 0},
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'I have a question'},
                    {'author': {'type': 'bot'}, 'body': 'Here is the answer'}
                ]
            }
        }
        assert is_fin_resolved(conv) == True
    
    def test_not_resolved_admin_reply(self):
        """Admin reply present means not resolved by Fin"""
        conv = {
            'state': 'closed',
            'admin_assignee_id': 123,
            'conversation_rating': 4,
            'statistics': {'count_reopens': 0},
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'I have a question'},
                    {'author': {'type': 'bot'}, 'body': 'Let me help'},
                    {'author': {'type': 'admin'}, 'body': 'Actually, here is the correct answer'}
                ]
            }
        }
        assert is_fin_resolved(conv) == False
    
    def test_not_resolved_negative_csat(self):
        """Negative CSAT blocks resolution"""
        conv = {
            'state': 'closed',
            'admin_assignee_id': None,
            'conversation_rating': 1,
            'statistics': {'count_reopens': 0},
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Help'},
                    {'author': {'type': 'bot'}, 'body': 'Answer'}
                ]
            }
        }
        assert is_fin_resolved(conv) == False
    
    def test_not_resolved_multiple_reopens(self):
        """Multiple reopens block resolution"""
        conv = {
            'state': 'closed',
            'admin_assignee_id': None,
            'conversation_rating': 4,
            'statistics': {'count_reopens': 3},
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Help'},
                    {'author': {'type': 'bot'}, 'body': 'Answer'}
                ]
            }
        }
        assert is_fin_resolved(conv) == False
    
    def test_resolved_low_engagement(self):
        """Open but ≤2 user messages is resolved (low engagement)"""
        conv = {
            'state': 'open',
            'admin_assignee_id': None,
            'conversation_rating': None,
            'statistics': {'count_reopens': 0},
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Quick question'},
                    {'author': {'type': 'bot'}, 'body': 'Here is the answer'},
                    {'author': {'type': 'user'}, 'body': 'Thanks'}
                ]
            }
        }
        assert is_fin_resolved(conv) == True
    
    def test_not_resolved_high_engagement_open(self):
        """Open with >2 user messages is not resolved"""
        conv = {
            'state': 'open',
            'admin_assignee_id': None,
            'conversation_rating': None,
            'statistics': {'count_reopens': 0},
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Question 1'},
                    {'author': {'type': 'bot'}, 'body': 'Answer 1'},
                    {'author': {'type': 'user'}, 'body': 'Question 2'},
                    {'author': {'type': 'bot'}, 'body': 'Answer 2'},
                    {'author': {'type': 'user'}, 'body': 'Question 3'}
                ]
            }
        }
        assert is_fin_resolved(conv) == False
    
    def test_resolved_good_rating(self):
        """Closed with good rating (≥3) is resolved"""
        conv = {
            'state': 'closed',
            'admin_assignee_id': None,
            'conversation_rating': 4,
            'statistics': {'count_reopens': 0},
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Help'},
                    {'author': {'type': 'bot'}, 'body': 'Answer'}
                ]
            }
        }
        assert is_fin_resolved(conv) == True
    
    def test_resolved_rating_dict_format(self):
        """Handle rating as dict format (conversation_rating.rating)"""
        conv = {
            'state': 'closed',
            'admin_assignee_id': None,
            'conversation_rating': {'rating': 4, 'remark': 'Good'},
            'statistics': {'count_reopens': 0},
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Help'},
                    {'author': {'type': 'bot'}, 'body': 'Answer'}
                ]
            }
        }
        assert is_fin_resolved(conv) == True
    
    def test_not_resolved_rating_dict_negative(self):
        """Rating dict with negative value blocks resolution"""
        conv = {
            'state': 'closed',
            'admin_assignee_id': None,
            'conversation_rating': {'rating': 2, 'remark': 'Not helpful'},
            'statistics': {'count_reopens': 0},
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Help'},
                    {'author': {'type': 'bot'}, 'body': 'Answer'}
                ]
            }
        }
        assert is_fin_resolved(conv) == False
    
    def test_resolved_missing_rating(self):
        """Missing rating doesn't block resolution (treated as neutral)"""
        conv = {
            'state': 'closed',
            'admin_assignee_id': None,
            'conversation_rating': None,
            'statistics': {'count_reopens': 0},
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Help'},
                    {'author': {'type': 'bot'}, 'body': 'Answer'}
                ]
            }
        }
        assert is_fin_resolved(conv) == True
    
    def test_resolved_missing_reopens(self):
        """Missing reopens field treated as 0 (doesn't block resolution)"""
        conv = {
            'state': 'closed',
            'admin_assignee_id': None,
            'conversation_rating': None,
            'statistics': {},  # No count_reopens field
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Help'},
                    {'author': {'type': 'bot'}, 'body': 'Answer'}
                ]
            }
        }
        assert is_fin_resolved(conv) == True
    
    def test_resolved_waiting_since_fallback(self):
        """Handle waiting_since as top-level field (legacy format)"""
        conv = {
            'state': 'closed',
            'admin_assignee_id': None,
            'conversation_rating': None,
            'waiting_since': 1,  # Top-level field
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Help'},
                    {'author': {'type': 'bot'}, 'body': 'Answer'}
                ]
            }
        }
        assert is_fin_resolved(conv) == True
    
    def test_not_resolved_waiting_since_multiple(self):
        """Multiple waiting_since values block resolution"""
        conv = {
            'state': 'closed',
            'admin_assignee_id': None,
            'conversation_rating': None,
            'waiting_since': 3,  # Multiple reopens
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Help'},
                    {'author': {'type': 'bot'}, 'body': 'Answer'}
                ]
            }
        }
        assert is_fin_resolved(conv) == False
    
    def test_edge_case_empty_conversation_parts(self):
        """Handle empty conversation_parts gracefully"""
        conv = {
            'state': 'closed',
            'admin_assignee_id': None,
            'conversation_rating': None,
            'statistics': {'count_reopens': 0},
            'conversation_parts': {
                'conversation_parts': []
            }
        }
        # No admin response (empty), closed, no bad rating, no reopens
        assert is_fin_resolved(conv) == True
    
    def test_edge_case_missing_conversation_parts(self):
        """Handle missing conversation_parts gracefully"""
        conv = {
            'state': 'closed',
            'admin_assignee_id': None,
            'conversation_rating': None,
            'statistics': {'count_reopens': 0}
            # No conversation_parts field at all
        }
        # No admin response (missing), closed, no bad rating, no reopens
        assert is_fin_resolved(conv) == True
    
    def test_edge_case_conversation_parts_as_list(self):
        """Handle conversation_parts as direct list (alternative format)"""
        conv = {
            'state': 'closed',
            'admin_assignee_id': None,
            'conversation_rating': None,
            'statistics': {'count_reopens': 0},
            'conversation_parts': [  # Direct list instead of nested dict
                {'author': {'type': 'user'}, 'body': 'Help'},
                {'author': {'type': 'bot'}, 'body': 'Answer'}
            ]
        }
        assert is_fin_resolved(conv) == True


class TestKnowledgeGap:
    """Test cases for has_knowledge_gap() function"""
    
    def test_no_gap_if_resolved(self):
        """Resolved conversation has no knowledge gap"""
        conv = {
            'state': 'closed',
            'admin_assignee_id': None,
            'conversation_rating': 4,
            'statistics': {'count_reopens': 0},
            'full_text': 'Customer: Help please. Bot: Here is the answer.',
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Help'},
                    {'author': {'type': 'bot'}, 'body': 'Answer'}
                ]
            }
        }
        assert has_knowledge_gap(conv) == False
    
    def test_gap_admin_intervention(self):
        """Unresolved with admin intervention = knowledge gap"""
        conv = {
            'state': 'closed',
            'admin_assignee_id': 123,
            'conversation_rating': None,
            'statistics': {'count_reopens': 0},
            'full_text': 'Customer: Help. Admin: Let me assist you.',
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Help'},
                    {'author': {'type': 'bot'}, 'body': 'Answer'},
                    {'author': {'type': 'admin'}, 'body': 'Let me assist'}
                ]
            }
        }
        assert has_knowledge_gap(conv) == True
    
    def test_gap_negative_csat(self):
        """Unresolved with bad rating = knowledge gap"""
        conv = {
            'state': 'closed',
            'admin_assignee_id': None,
            'conversation_rating': 1,
            'statistics': {'count_reopens': 0},
            'full_text': 'Customer: This is not helpful at all.',
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Help'},
                    {'author': {'type': 'bot'}, 'body': 'Answer'}
                ]
            }
        }
        assert has_knowledge_gap(conv) == True
    
    def test_gap_negative_feedback(self):
        """Explicit negative feedback indicates knowledge gap"""
        conv = {
            'state': 'open',  # Changed to open to make it unresolved
            'admin_assignee_id': None,
            'conversation_rating': None,
            'statistics': {'count_reopens': 0},
            'full_text': 'Customer: That answer is incorrect and not helpful.',
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Help'},
                    {'author': {'type': 'bot'}, 'body': 'Wrong answer'},
                    {'author': {'type': 'user'}, 'body': 'That is incorrect'},
                    {'author': {'type': 'user'}, 'body': 'Not helpful at all'}  # >2 user messages to make it unresolved
                ]
            }
        }
        assert has_knowledge_gap(conv) == True
    
    def test_gap_rating_remark_negative(self):
        """Negative feedback in rating remark indicates gap"""
        conv = {
            'state': 'open',  # Changed to open with high engagement to make unresolved
            'admin_assignee_id': None,
            'conversation_rating': {'rating': 3, 'remark': 'Still doesn\'t work'},
            'statistics': {'count_reopens': 0},
            'full_text': 'Customer: Help please.',
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Help'},
                    {'author': {'type': 'bot'}, 'body': 'Answer'},
                    {'author': {'type': 'user'}, 'body': 'Still having issues'},
                    {'author': {'type': 'user'}, 'body': 'Not working'}  # >2 user messages
                ]
            }
        }
        assert has_knowledge_gap(conv) == True
    
    def test_gap_frustration_phrases(self):
        """Frustration phrases indicate knowledge gap"""
        conv = {
            'state': 'open',  # Changed to open with high engagement to make unresolved
            'admin_assignee_id': None,
            'conversation_rating': None,
            'statistics': {'count_reopens': 0},
            'full_text': 'Customer: I am so frustrated. This is a waste of time.',
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Help'},
                    {'author': {'type': 'bot'}, 'body': 'Answer'},
                    {'author': {'type': 'user'}, 'body': 'Frustrated'},
                    {'author': {'type': 'user'}, 'body': 'Waste of time'}  # >2 user messages
                ]
            }
        }
        assert has_knowledge_gap(conv) == True
    
    def test_gap_long_unresolved(self):
        """Long unresolved conversation indicates knowledge gap"""
        conv = {
            'state': 'open',  # Still open
            'admin_assignee_id': None,
            'conversation_rating': None,
            'statistics': {'count_conversation_parts': 10},  # >8 messages
            'full_text': 'Long back and forth conversation',
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': f'Message {i}'}
                    for i in range(10)
                ]
            }
        }
        assert has_knowledge_gap(conv) == True
    
    def test_no_gap_short_conversation(self):
        """Short conversation without negative signals = no gap"""
        conv = {
            'state': 'closed',
            'admin_assignee_id': None,
            'conversation_rating': None,
            'statistics': {'count_conversation_parts': 3},
            'full_text': 'Customer: Help. Bot: Answer.',
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Help'},
                    {'author': {'type': 'bot'}, 'body': 'Answer'},
                    {'author': {'type': 'user'}, 'body': 'Thanks'}
                ]
            }
        }
        # Not resolved (>2 user messages but open), but no strong negative signals
        # Actually this should be resolved because it's closed
        assert has_knowledge_gap(conv) == False
    
    def test_no_gap_closed_long_conversation(self):
        """Long but closed conversation = no gap (resolved)"""
        conv = {
            'state': 'closed',
            'admin_assignee_id': None,
            'conversation_rating': None,
            'statistics': {'count_conversation_parts': 10},
            'full_text': 'Long conversation that was eventually resolved',
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Help'},
                    {'author': {'type': 'bot'}, 'body': 'Answer'}
                ]
            }
        }
        # Closed with ≤2 user messages = resolved, so no gap
        assert has_knowledge_gap(conv) == False
    
    def test_edge_case_missing_full_text(self):
        """Handle missing full_text field gracefully"""
        conv = {
            'state': 'closed',
            'admin_assignee_id': 123,  # Admin intervened
            'conversation_rating': None,
            'statistics': {'count_reopens': 0},
            # No full_text field
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Help'},
                    {'author': {'type': 'admin'}, 'body': 'Answer'}
                ]
            }
        }
        # Should still detect knowledge gap due to admin intervention
        assert has_knowledge_gap(conv) == True
    
    def test_combined_signals(self):
        """Multiple negative signals combined"""
        conv = {
            'state': 'closed',
            'admin_assignee_id': 123,
            'conversation_rating': {'rating': 1, 'remark': 'Wrong answer, not helpful'},
            'statistics': {'count_reopens': 0},
            'full_text': 'Customer: This is incorrect and frustrated me.',
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Help'},
                    {'author': {'type': 'bot'}, 'body': 'Wrong answer'},
                    {'author': {'type': 'admin'}, 'body': 'Let me correct that'}
                ]
            }
        }
        # Multiple signals: admin, negative CSAT, negative feedback, frustration
        assert has_knowledge_gap(conv) == True


class TestEdgeCases:
    """Test edge cases and data quality issues"""
    
    def test_minimal_conversation(self):
        """Handle minimal conversation with only required fields"""
        conv = {
            'state': 'closed',
            'conversation_parts': {}
        }
        # Minimal data should still work - defaults to resolved
        assert is_fin_resolved(conv) == True
        assert has_knowledge_gap(conv) == False
    
    def test_none_values(self):
        """Handle None values gracefully"""
        conv = {
            'state': None,
            'admin_assignee_id': None,
            'conversation_rating': None,
            'statistics': None,
            'full_text': None,
            'conversation_parts': None
        }
        # State None treated as open, no admin, no rating, no reopens
        # But no user parts either (≤2), so should be resolved
        assert is_fin_resolved(conv) == True
    
    def test_malformed_statistics(self):
        """Handle malformed statistics dict"""
        conv = {
            'state': 'closed',
            'admin_assignee_id': None,
            'conversation_rating': None,
            'statistics': 'invalid',  # String instead of dict
            'conversation_parts': {
                'conversation_parts': []
            }
        }
        # Should handle gracefully and still resolve
        assert is_fin_resolved(conv) == True
    
    def test_empty_dict(self):
        """Handle completely empty conversation dict"""
        conv = {}
        # All fields missing - should default to resolved
        # (no admin, no bad rating, no reopens, ≤2 user messages)
        assert is_fin_resolved(conv) == True
        assert has_knowledge_gap(conv) == False