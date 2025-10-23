"""
Unit tests for SegmentationAgent: Validate Horatio detection and conversation segmentation.

This test suite validates:
1. Horatio detection via email in conversation_parts, source, and assignee
2. Boldr detection via email
3. Escalated detection via email and text
4. Fin AI only detection
5. Unknown classification
6. End-to-end segmentation with mixed conversations
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any

from src.agents.segmentation_agent import SegmentationAgent
from src.agents.base_agent import AgentContext, AgentResult, ConfidenceLevel


# ============================================================================
# FIXTURES: Realistic conversation data matching Intercom API structure
# ============================================================================

@pytest.fixture
def mock_horatio_conversation_via_parts() -> Dict[str, Any]:
    """Horatio agent detected via conversation_parts email."""
    return {
        'id': 'conv_horatio_parts_123',
        'created_at': 1699123456,
        'updated_at': 1699125456,
        'state': 'closed',
        'admin_assignee_id': '456',
        'ai_agent_participated': False,
        'full_text': 'Customer message about billing issue. Agent response about payment.',
        'conversation_parts': {
            'conversation_parts': [
                {
                    'type': 'conversation_part',
                    'id': '789',
                    'part_type': 'comment',
                    'body': '<p>I can help with that billing issue</p>',
                    'author': {
                        'type': 'admin',
                        'id': '456',
                        'name': 'Support Agent',
                        'email': 'agent@hirehoratio.co'
                    }
                }
            ]
        },
        'source': {'type': 'email', 'body': 'Customer billing question'},
        'assignee': {}
    }


@pytest.fixture
def mock_horatio_conversation_via_source() -> Dict[str, Any]:
    """Horatio agent detected via source.author email."""
    return {
        'id': 'conv_horatio_source_456',
        'created_at': 1699123456,
        'updated_at': 1699125456,
        'state': 'closed',
        'admin_assignee_id': '789',
        'ai_agent_participated': False,
        'full_text': 'Support conversation about feature request',
        'conversation_parts': {
            'conversation_parts': []
        },
        'source': {
            'type': 'chat',
            'body': 'Initial message from admin',
            'author': {
                'type': 'admin',
                'id': '789',
                'name': 'Horatio Support',
                'email': 'support@hirehoratio.co'
            }
        },
        'assignee': {}
    }


@pytest.fixture
def mock_horatio_conversation_via_assignee() -> Dict[str, Any]:
    """Horatio agent detected via assignee email."""
    return {
        'id': 'conv_horatio_assignee_789',
        'created_at': 1699123456,
        'updated_at': 1699125456,
        'state': 'closed',
        'admin_assignee_id': '999',
        'ai_agent_participated': False,
        'full_text': 'Technical support conversation',
        'conversation_parts': {
            'conversation_parts': []
        },
        'source': {'type': 'email', 'body': 'Customer inquiry'},
        'assignee': {
            'type': 'admin',
            'id': '999',
            'name': 'Team Lead',
            'email': 'team@hirehoratio.co'
        }
    }


@pytest.fixture
def mock_boldr_conversation() -> Dict[str, Any]:
    """Boldr agent detected via email."""
    return {
        'id': 'conv_boldr_123',
        'created_at': 1699123456,
        'updated_at': 1699125456,
        'state': 'closed',
        'admin_assignee_id': '111',
        'ai_agent_participated': False,
        'full_text': 'Billing support conversation',
        'conversation_parts': {
            'conversation_parts': [
                {
                    'type': 'conversation_part',
                    'id': '222',
                    'part_type': 'comment',
                    'body': '<p>Happy to help with billing</p>',
                    'author': {
                        'type': 'admin',
                        'id': '111',
                        'name': 'Boldr Agent',
                        'email': 'agent@boldrimpact.com'
                    }
                }
            ]
        },
        'source': {'type': 'email', 'body': 'Customer billing question'},
        'assignee': {}
    }


@pytest.fixture
def mock_escalated_conversation_max() -> Dict[str, Any]:
    """Escalated conversation detected via Max Jackson email."""
    return {
        'id': 'conv_escalated_max_123',
        'created_at': 1699123456,
        'updated_at': 1699125456,
        'state': 'closed',
        'admin_assignee_id': '333',
        'ai_agent_participated': False,
        'full_text': 'Complex technical issue requiring senior review',
        'conversation_parts': {
            'conversation_parts': [
                {
                    'type': 'conversation_part',
                    'id': '444',
                    'part_type': 'comment',
                    'body': '<p>Let me investigate this</p>',
                    'author': {
                        'type': 'admin',
                        'id': '333',
                        'name': 'Max Jackson',
                        'email': 'max.jackson@example.com'
                    }
                }
            ]
        },
        'source': {'type': 'email', 'body': 'Urgent issue'},
        'assignee': {}
    }


@pytest.fixture
def mock_escalated_conversation_daeho() -> Dict[str, Any]:
    """Escalated conversation detected via Dae-Ho email."""
    return {
        'id': 'conv_escalated_daeho_456',
        'created_at': 1699123456,
        'updated_at': 1699125456,
        'state': 'closed',
        'admin_assignee_id': '555',
        'ai_agent_participated': False,
        'full_text': 'API integration issue',
        'conversation_parts': {
            'conversation_parts': []
        },
        'source': {'type': 'email', 'body': 'Customer inquiry'},
        'assignee': {
            'type': 'admin',
            'id': '555',
            'name': 'Dae-Ho Chung',
            'email': 'dae-ho@example.com'
        }
    }


@pytest.fixture
def mock_escalated_conversation_hilary() -> Dict[str, Any]:
    """Escalated conversation detected via Hilary email."""
    return {
        'id': 'conv_escalated_hilary_789',
        'created_at': 1699123456,
        'updated_at': 1699125456,
        'state': 'closed',
        'admin_assignee_id': '666',
        'ai_agent_participated': False,
        'full_text': 'Product strategy discussion',
        'conversation_parts': {
            'conversation_parts': [
                {
                    'type': 'conversation_part',
                    'id': '777',
                    'part_type': 'comment',
                    'body': '<p>I can help with this</p>',
                    'author': {
                        'type': 'admin',
                        'id': '666',
                        'name': 'Hilary Dudek',
                        'email': 'hilary@example.com'
                    }
                }
            ]
        },
        'source': {'type': 'email', 'body': 'Customer inquiry'},
        'assignee': {}
    }


@pytest.fixture
def mock_escalated_conversation_text() -> Dict[str, Any]:
    """Escalated conversation detected via text pattern (no email)."""
    return {
        'id': 'conv_escalated_text_999',
        'created_at': 1699123456,
        'updated_at': 1699125456,
        'state': 'closed',
        'admin_assignee_id': '888',
        'ai_agent_participated': False,
        'full_text': 'Customer issue. This has been escalated to Max Jackson for review.',
        'conversation_parts': {
            'conversation_parts': [
                {
                    'type': 'conversation_part',
                    'id': '999',
                    'part_type': 'comment',
                    'body': '<p>Escalating to senior team</p>',
                    'author': {
                        'type': 'admin',
                        'id': '888',
                        'name': 'Junior Agent',
                        'email': 'agent@example.com'
                    }
                }
            ]
        },
        'source': {'type': 'email', 'body': 'Customer inquiry'},
        'assignee': {}
    }


@pytest.fixture
def mock_fin_ai_conversation() -> Dict[str, Any]:
    """Fin AI only conversation (free customer)."""
    return {
        'id': 'conv_fin_ai_123',
        'created_at': 1699123456,
        'updated_at': 1699125456,
        'state': 'closed',
        'admin_assignee_id': None,
        'ai_agent_participated': True,
        'full_text': 'Customer question. AI response with help article.',
        'conversation_parts': {
            'conversation_parts': [
                {
                    'type': 'conversation_part',
                    'id': '101',
                    'part_type': 'comment',
                    'body': '<p>Here is a help article that answers your question</p>',
                    'author': {
                        'type': 'bot',
                        'id': 'fin_ai',
                        'name': 'Fin'
                    }
                }
            ]
        },
        'source': {'type': 'chat', 'body': 'How do I reset my password?'},
        'assignee': {}
    }


@pytest.fixture
def mock_unknown_conversation() -> Dict[str, Any]:
    """Unknown classification (no admin, no AI)."""
    return {
        'id': 'conv_unknown_123',
        'created_at': 1699123456,
        'updated_at': 1699125456,
        'state': 'open',
        'admin_assignee_id': None,
        'ai_agent_participated': False,
        'full_text': 'Customer message with no response yet',
        'conversation_parts': {
            'conversation_parts': []
        },
        'source': {'type': 'email', 'body': 'Customer inquiry about pricing'},
        'assignee': {}
    }


@pytest.fixture
def mock_generic_paid_conversation() -> Dict[str, Any]:
    """Generic paid customer with unknown agent."""
    return {
        'id': 'conv_generic_paid_123',
        'created_at': 1699123456,
        'updated_at': 1699125456,
        'state': 'closed',
        'admin_assignee_id': '999',
        'ai_agent_participated': False,
        'full_text': 'Support conversation',
        'conversation_parts': {
            'conversation_parts': [
                {
                    'type': 'conversation_part',
                    'id': '111',
                    'part_type': 'comment',
                    'body': '<p>I can help with that</p>',
                    'author': {
                        'type': 'admin',
                        'id': '999',
                        'name': 'Generic Agent',
                        'email': 'agent@unknowndomain.com'
                    }
                }
            ]
        },
        'source': {'type': 'email', 'body': 'Customer inquiry'},
        'assignee': {}
    }


# ============================================================================
# TEST CASES
# ============================================================================

class TestSegmentationAgent:
    """Test suite for SegmentationAgent."""

    def test_horatio_detection_via_conversation_parts(self, mock_horatio_conversation_via_parts):
        """Test Horatio detection via email in conversation_parts."""
        agent = SegmentationAgent()
        segment, agent_type = agent._classify_conversation(mock_horatio_conversation_via_parts)
        
        assert segment == 'paid', f"Expected 'paid' segment, got '{segment}'"
        assert agent_type == 'horatio', f"Expected 'horatio' agent type, got '{agent_type}'"

    def test_horatio_detection_via_source(self, mock_horatio_conversation_via_source):
        """Test Horatio detection via source.author.email."""
        agent = SegmentationAgent()
        segment, agent_type = agent._classify_conversation(mock_horatio_conversation_via_source)
        
        assert segment == 'paid', f"Expected 'paid' segment, got '{segment}'"
        assert agent_type == 'horatio', f"Expected 'horatio' agent type, got '{agent_type}'"

    def test_horatio_detection_via_assignee(self, mock_horatio_conversation_via_assignee):
        """Test Horatio detection via assignee.email."""
        agent = SegmentationAgent()
        segment, agent_type = agent._classify_conversation(mock_horatio_conversation_via_assignee)
        
        assert segment == 'paid', f"Expected 'paid' segment, got '{segment}'"
        assert agent_type == 'horatio', f"Expected 'horatio' agent type, got '{agent_type}'"

    def test_boldr_detection_via_email(self, mock_boldr_conversation):
        """Test Boldr detection via email."""
        agent = SegmentationAgent()
        segment, agent_type = agent._classify_conversation(mock_boldr_conversation)
        
        assert segment == 'paid', f"Expected 'paid' segment, got '{segment}'"
        assert agent_type == 'boldr', f"Expected 'boldr' agent type, got '{agent_type}'"

    def test_escalated_detection_max_jackson(self, mock_escalated_conversation_max):
        """Test escalated detection via Max Jackson email."""
        agent = SegmentationAgent()
        segment, agent_type = agent._classify_conversation(mock_escalated_conversation_max)
        
        assert segment == 'paid', f"Expected 'paid' segment, got '{segment}'"
        assert agent_type == 'escalated', f"Expected 'escalated' agent type, got '{agent_type}'"

    def test_escalated_detection_daeho(self, mock_escalated_conversation_daeho):
        """Test escalated detection via Dae-Ho email."""
        agent = SegmentationAgent()
        segment, agent_type = agent._classify_conversation(mock_escalated_conversation_daeho)
        
        assert segment == 'paid', f"Expected 'paid' segment, got '{segment}'"
        assert agent_type == 'escalated', f"Expected 'escalated' agent type, got '{agent_type}'"

    def test_escalated_detection_hilary(self, mock_escalated_conversation_hilary):
        """Test escalated detection via Hilary email."""
        agent = SegmentationAgent()
        segment, agent_type = agent._classify_conversation(mock_escalated_conversation_hilary)
        
        assert segment == 'paid', f"Expected 'paid' segment, got '{segment}'"
        assert agent_type == 'escalated', f"Expected 'escalated' agent type, got '{agent_type}'"

    def test_escalated_detection_via_text(self, mock_escalated_conversation_text):
        """Test escalated detection via text pattern (no email)."""
        agent = SegmentationAgent()
        segment, agent_type = agent._classify_conversation(mock_escalated_conversation_text)
        
        assert segment == 'paid', f"Expected 'paid' segment, got '{segment}'"
        assert agent_type == 'escalated', f"Expected 'escalated' agent type, got '{agent_type}'"

    def test_fin_ai_only_free_customer(self, mock_fin_ai_conversation):
        """Test Fin AI only detection (free customer)."""
        agent = SegmentationAgent()
        segment, agent_type = agent._classify_conversation(mock_fin_ai_conversation)
        
        assert segment == 'free', f"Expected 'free' segment, got '{segment}'"
        assert agent_type == 'fin_ai', f"Expected 'fin_ai' agent type, got '{agent_type}'"

    def test_unknown_classification(self, mock_unknown_conversation):
        """Test unknown classification."""
        agent = SegmentationAgent()
        segment, agent_type = agent._classify_conversation(mock_unknown_conversation)
        
        assert segment == 'unknown', f"Expected 'unknown' segment, got '{segment}'"
        assert agent_type == 'unknown', f"Expected 'unknown' agent type, got '{agent_type}'"

    def test_generic_paid_customer_unknown_agent(self, mock_generic_paid_conversation):
        """Test generic paid customer with unknown agent."""
        agent = SegmentationAgent()
        segment, agent_type = agent._classify_conversation(mock_generic_paid_conversation)
        
        assert segment == 'paid', f"Expected 'paid' segment, got '{segment}'"
        assert agent_type == 'unknown', f"Expected 'unknown' agent type, got '{agent_type}'"

    def test_email_case_insensitivity(self):
        """Test that email detection is case-insensitive."""
        agent = SegmentationAgent()
        
        # Test uppercase
        conv_upper = {
            'id': 'conv_upper',
            'created_at': 1699123456,
            'admin_assignee_id': '123',
            'ai_agent_participated': False,
            'full_text': 'Test',
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'author': {
                            'type': 'admin',
                            'email': 'AGENT@HIREHORATIO.CO'
                        }
                    }
                ]
            },
            'source': {},
            'assignee': {}
        }
        segment, agent_type = agent._classify_conversation(conv_upper)
        assert agent_type == 'horatio', f"Expected 'horatio' for uppercase email, got '{agent_type}'"
        
        # Test mixed case
        conv_mixed = {
            'id': 'conv_mixed',
            'created_at': 1699123456,
            'admin_assignee_id': '123',
            'ai_agent_participated': False,
            'full_text': 'Test',
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'author': {
                            'type': 'admin',
                            'email': 'Agent@HireHoratio.Co'
                        }
                    }
                ]
            },
            'source': {},
            'assignee': {}
        }
        segment, agent_type = agent._classify_conversation(conv_mixed)
        assert agent_type == 'horatio', f"Expected 'horatio' for mixed case email, got '{agent_type}'"

    def test_multiple_admin_emails_first_match_wins(self):
        """Test that with multiple admin emails, Horatio is detected."""
        agent = SegmentationAgent()
        
        conv = {
            'id': 'conv_multiple',
            'created_at': 1699123456,
            'admin_assignee_id': '123',
            'ai_agent_participated': False,
            'full_text': 'Test',
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'author': {
                            'type': 'admin',
                            'email': 'support@example.com'
                        }
                    },
                    {
                        'author': {
                            'type': 'admin',
                            'email': 'agent@hirehoratio.co'
                        }
                    }
                ]
            },
            'source': {},
            'assignee': {}
        }
        segment, agent_type = agent._classify_conversation(conv)
        assert agent_type == 'horatio', f"Expected 'horatio' even with multiple emails, got '{agent_type}'"

    @pytest.mark.asyncio
    async def test_end_to_end_segmentation(
        self,
        mock_horatio_conversation_via_parts,
        mock_horatio_conversation_via_source,
        mock_horatio_conversation_via_assignee,
        mock_boldr_conversation,
        mock_escalated_conversation_max,
        mock_fin_ai_conversation,
        mock_unknown_conversation
    ):
        """Test end-to-end segmentation with mixed conversations."""
        agent = SegmentationAgent()
        
        # Create a second Fin AI conversation with different ID
        fin_ai_2 = mock_fin_ai_conversation.copy()
        fin_ai_2['id'] = 'conv_fin_ai_456'
        
        # Create a second unknown conversation with different ID
        unknown_2 = mock_unknown_conversation.copy()
        unknown_2['id'] = 'conv_unknown_456'
        
        conversations = [
            mock_horatio_conversation_via_parts,
            mock_horatio_conversation_via_source,
            mock_horatio_conversation_via_assignee,
            mock_boldr_conversation,
            mock_escalated_conversation_max,
            mock_fin_ai_conversation,
            fin_ai_2,
            mock_unknown_conversation,
            unknown_2
        ]
        
        # Create AgentContext
        context = AgentContext(
            analysis_id='test_analysis_123',
            analysis_type='segmentation_test',
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
            conversations=conversations
        )
        
        # Execute segmentation
        result = await agent.execute(context)
        
        # Assert success
        assert result.success, f"Segmentation failed: {result.error_message}"
        
        # Check agent distribution
        agent_dist = result.data['agent_distribution']
        assert agent_dist['horatio'] == 3, f"Expected 3 Horatio conversations, got {agent_dist['horatio']}"
        assert agent_dist['boldr'] == 1, f"Expected 1 Boldr conversation, got {agent_dist['boldr']}"
        assert agent_dist['escalated'] == 1, f"Expected 1 escalated conversation, got {agent_dist['escalated']}"
        assert agent_dist['fin_ai'] == 2, f"Expected 2 Fin AI conversations, got {agent_dist['fin_ai']}"
        assert agent_dist['unknown'] == 2, f"Expected 2 unknown conversations, got {agent_dist['unknown']}"
        
        # Check segmentation summary
        summary = result.data['segmentation_summary']
        assert summary['paid_count'] == 5, f"Expected 5 paid conversations, got {summary['paid_count']}"
        assert summary['free_count'] == 2, f"Expected 2 free conversations, got {summary['free_count']}"
        assert summary['unknown_count'] == 2, f"Expected 2 unknown conversations, got {summary['unknown_count']}"
        
        # Verify totals match
        total = summary['paid_count'] + summary['free_count'] + summary['unknown_count']
        assert total == len(conversations), f"Total ({total}) doesn't match conversation count ({len(conversations)})"
        
        # Check confidence
        assert result.confidence > 0.7, f"Expected confidence > 0.7, got {result.confidence}"
        assert result.confidence_level == ConfidenceLevel.MEDIUM or result.confidence_level == ConfidenceLevel.HIGH
