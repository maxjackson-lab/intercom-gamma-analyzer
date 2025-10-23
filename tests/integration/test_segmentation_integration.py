"""
Integration tests for SegmentationAgent: End-to-end validation with realistic scenarios.

This test suite validates:
1. Segmentation with Railway-like data (50+ conversations)
2. Performance with large datasets (1000+ conversations)
3. Segmentation with only Horatio conversations
4. Mixed email sources (conversation_parts, source, assignee)
5. Edge cases (missing fields, malformed data, empty strings)
6. Agent distribution logging
"""

import pytest
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any
from io import StringIO

from src.agents.segmentation_agent import SegmentationAgent
from src.agents.base_agent import AgentContext, AgentResult, ConfidenceLevel


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_conversation_with_admin_email(
    email: str,
    conv_id: str = None,
    author_type: str = 'admin',
    location: str = 'conversation_parts'
) -> Dict[str, Any]:
    """
    Create a conversation dict with admin email in specified location.
    
    Args:
        email: Admin email address
        conv_id: Conversation ID (default: auto-generated)
        author_type: Author type ('admin', 'contact', 'team')
        location: Where to place email ('conversation_parts', 'source', 'assignee')
    
    Returns:
        Conversation dict matching Intercom API structure
    """
    conv_id = conv_id or f"conv_{email.split('@')[0]}_{id(email)}"
    
    base_conv = {
        'id': conv_id,
        'created_at': 1699123456,
        'updated_at': 1699125456,
        'state': 'closed',
        'admin_assignee_id': '123' if author_type == 'admin' else None,
        'ai_agent_participated': False,
        'full_text': 'Customer inquiry and agent response',
        'conversation_parts': {'conversation_parts': []},
        'source': {'type': 'email', 'body': 'Customer message'},
        'assignee': {}
    }
    
    if location == 'conversation_parts':
        base_conv['conversation_parts']['conversation_parts'].append({
            'type': 'conversation_part',
            'id': f'part_{conv_id}',
            'part_type': 'comment',
            'body': '<p>Agent response</p>',
            'author': {
                'type': author_type,
                'id': '123',
                'name': 'Support Agent',
                'email': email
            }
        })
    elif location == 'source':
        base_conv['source'] = {
            'type': 'chat',
            'body': 'Initial admin message',
            'author': {
                'type': author_type,
                'id': '123',
                'name': 'Support Agent',
                'email': email
            }
        }
    elif location == 'assignee':
        base_conv['assignee'] = {
            'type': author_type,
            'id': '123',
            'name': 'Support Agent',
            'email': email
        }
    
    return base_conv


def create_horatio_conversation(conv_id: str, location: str = 'conversation_parts') -> Dict[str, Any]:
    """Create a realistic Horatio conversation."""
    return create_conversation_with_admin_email(
        email='agent@hirehoratio.co',
        conv_id=conv_id,
        location=location
    )


def create_boldr_conversation(conv_id: str) -> Dict[str, Any]:
    """Create a realistic Boldr conversation."""
    return create_conversation_with_admin_email(
        email='support@boldrimpact.com',
        conv_id=conv_id,
        location='conversation_parts'
    )


def create_escalated_conversation(conv_id: str, person: str = 'max.jackson') -> Dict[str, Any]:
    """Create a realistic escalated conversation."""
    emails = {
        'max.jackson': 'max.jackson@example.com',
        'dae-ho': 'dae-ho@example.com',
        'hilary': 'hilary@example.com'
    }
    return create_conversation_with_admin_email(
        email=emails.get(person, emails['max.jackson']),
        conv_id=conv_id,
        location='conversation_parts'
    )


def create_fin_ai_conversation(conv_id: str) -> Dict[str, Any]:
    """Create a realistic Fin AI-only conversation."""
    return {
        'id': conv_id,
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
                    'id': f'part_{conv_id}',
                    'part_type': 'comment',
                    'body': '<p>Here is a help article</p>',
                    'author': {
                        'type': 'bot',
                        'id': 'fin_ai',
                        'name': 'Fin'
                    }
                }
            ]
        },
        'source': {'type': 'chat', 'body': 'How do I reset password?'},
        'assignee': {}
    }


def create_unknown_conversation(conv_id: str) -> Dict[str, Any]:
    """Create an unknown conversation."""
    return {
        'id': conv_id,
        'created_at': 1699123456,
        'updated_at': 1699125456,
        'state': 'open',
        'admin_assignee_id': None,
        'ai_agent_participated': False,
        'full_text': 'Customer message with no response',
        'conversation_parts': {'conversation_parts': []},
        'source': {'type': 'email', 'body': 'Customer inquiry'},
        'assignee': {}
    }


def assert_segmentation_result(
    result: AgentResult,
    expected_distribution: Dict[str, int],
    expected_paid: int = None,
    expected_free: int = None,
    expected_unknown: int = None
):
    """
    Validate segmentation result matches expectations.
    
    Args:
        result: AgentResult from segmentation
        expected_distribution: Expected agent distribution dict
        expected_paid: Expected paid customer count (optional)
        expected_free: Expected free customer count (optional)
        expected_unknown: Expected unknown count (optional)
    """
    assert result.success, f"Segmentation failed: {result.error_message}"
    
    # Check agent distribution
    agent_dist = result.data['agent_distribution']
    for agent_type, expected_count in expected_distribution.items():
        actual_count = agent_dist.get(agent_type, 0)
        assert actual_count == expected_count, \
            f"Expected {expected_count} {agent_type} conversations, got {actual_count}"
    
    # Check segmentation summary if provided
    if expected_paid is not None or expected_free is not None or expected_unknown is not None:
        summary = result.data['segmentation_summary']
        
        if expected_paid is not None:
            assert summary['paid_count'] == expected_paid, \
                f"Expected {expected_paid} paid, got {summary['paid_count']}"
        
        if expected_free is not None:
            assert summary['free_count'] == expected_free, \
                f"Expected {expected_free} free, got {summary['free_count']}"
        
        if expected_unknown is not None:
            assert summary['unknown_count'] == expected_unknown, \
                f"Expected {expected_unknown} unknown, got {summary['unknown_count']}"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestSegmentationIntegration:
    """Integration tests for SegmentationAgent."""

    @pytest.mark.asyncio
    async def test_segmentation_with_railway_like_data(self):
        """Test segmentation with 50 conversations mimicking real Railway data."""
        agent = SegmentationAgent()
        
        conversations = []
        
        # Add 15 Horatio conversations
        for i in range(15):
            conversations.append(create_horatio_conversation(f'horatio_{i}'))
        
        # Add 5 Boldr conversations
        for i in range(5):
            conversations.append(create_boldr_conversation(f'boldr_{i}'))
        
        # Add 5 escalated conversations
        for i in range(5):
            person = ['max.jackson', 'dae-ho', 'hilary'][i % 3]
            conversations.append(create_escalated_conversation(f'escalated_{i}', person))
        
        # Add 15 Fin AI conversations
        for i in range(15):
            conversations.append(create_fin_ai_conversation(f'fin_ai_{i}'))
        
        # Add 10 unknown conversations
        for i in range(10):
            conversations.append(create_unknown_conversation(f'unknown_{i}'))
        
        # Create context
        context = AgentContext(
            analysis_id='railway_test',
            analysis_type='railway_simulation',
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
            conversations=conversations
        )
        
        # Execute segmentation
        result = await agent.execute(context)
        
        # Assert results
        assert_segmentation_result(
            result,
            expected_distribution={
                'horatio': 15,
                'boldr': 5,
                'escalated': 5,
                'fin_ai': 15,
                'unknown': 10
            },
            expected_paid=25,  # 15 + 5 + 5
            expected_free=15,
            expected_unknown=10
        )
        
        # Verify no crashes
        assert result.execution_time < 1.0, \
            f"Execution took too long: {result.execution_time}s (expected < 1s)"
        
        # Verify confidence
        assert result.confidence > 0.7, \
            f"Confidence too low: {result.confidence}"

    @pytest.mark.asyncio
    async def test_segmentation_performance_large_dataset(self):
        """Test segmentation performance with 1000 conversations."""
        agent = SegmentationAgent()
        
        conversations = []
        
        # Generate 1000 conversations with realistic distribution
        for i in range(1000):
            if i < 400:  # 40% Horatio
                conversations.append(create_horatio_conversation(f'horatio_{i}'))
            elif i < 600:  # 20% Boldr
                conversations.append(create_boldr_conversation(f'boldr_{i}'))
            elif i < 650:  # 5% Escalated
                conversations.append(create_escalated_conversation(f'escalated_{i}'))
            elif i < 900:  # 25% Fin AI
                conversations.append(create_fin_ai_conversation(f'fin_ai_{i}'))
            else:  # 10% Unknown
                conversations.append(create_unknown_conversation(f'unknown_{i}'))
        
        # Create context
        context = AgentContext(
            analysis_id='performance_test',
            analysis_type='large_dataset',
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
            conversations=conversations
        )
        
        # Execute segmentation
        result = await agent.execute(context)
        
        # Assert performance
        assert result.success, f"Segmentation failed: {result.error_message}"
        assert result.execution_time < 5.0, \
            f"Execution took too long: {result.execution_time}s (expected < 5s for 1000 conversations)"
        
        # Assert correct counts
        assert_segmentation_result(
            result,
            expected_distribution={
                'horatio': 400,
                'boldr': 200,
                'escalated': 50,
                'fin_ai': 250,
                'unknown': 100
            },
            expected_paid=650,
            expected_free=250,
            expected_unknown=100
        )

    @pytest.mark.asyncio
    async def test_segmentation_with_only_horatio(self):
        """Test segmentation with only Horatio conversations."""
        agent = SegmentationAgent()
        
        conversations = []
        for i in range(20):
            conversations.append(create_horatio_conversation(f'horatio_{i}'))
        
        # Create context
        context = AgentContext(
            analysis_id='horatio_only_test',
            analysis_type='horatio_only',
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
            conversations=conversations
        )
        
        # Execute segmentation
        result = await agent.execute(context)
        
        # Assert all are Horatio
        assert_segmentation_result(
            result,
            expected_distribution={
                'horatio': 20,
                'boldr': 0,
                'escalated': 0,
                'fin_ai': 0,
                'unknown': 0
            },
            expected_paid=20,
            expected_free=0,
            expected_unknown=0
        )

    @pytest.mark.asyncio
    async def test_segmentation_with_mixed_email_sources(self):
        """Test segmentation with emails in different locations."""
        agent = SegmentationAgent()
        
        conversations = []
        
        # 5 conversations: email in conversation_parts only
        for i in range(5):
            conversations.append(create_horatio_conversation(f'parts_{i}', location='conversation_parts'))
        
        # 5 conversations: email in source only
        for i in range(5):
            conversations.append(create_horatio_conversation(f'source_{i}', location='source'))
        
        # 5 conversations: email in assignee only
        for i in range(5):
            conversations.append(create_horatio_conversation(f'assignee_{i}', location='assignee'))
        
        # 5 conversations: email in multiple locations
        for i in range(5):
            conv = create_horatio_conversation(f'multiple_{i}', location='conversation_parts')
            # Add email to source as well
            conv['source'] = {
                'type': 'chat',
                'author': {
                    'type': 'admin',
                    'email': 'another@hirehoratio.co'
                }
            }
            conversations.append(conv)
        
        # Create context
        context = AgentContext(
            analysis_id='mixed_sources_test',
            analysis_type='mixed_email_sources',
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
            conversations=conversations
        )
        
        # Execute segmentation
        result = await agent.execute(context)
        
        # Assert all 20 are detected as Horatio
        assert_segmentation_result(
            result,
            expected_distribution={
                'horatio': 20,
                'boldr': 0,
                'escalated': 0,
                'fin_ai': 0,
                'unknown': 0
            },
            expected_paid=20
        )

    @pytest.mark.asyncio
    async def test_segmentation_with_edge_cases(self):
        """Test segmentation with edge cases and malformed data."""
        agent = SegmentationAgent()
        
        conversations = []
        
        # Empty conversation_parts dict
        conv1 = create_horatio_conversation('edge_1')
        conv1['conversation_parts'] = {'conversation_parts': []}
        conv1['admin_assignee_id'] = None
        conversations.append(conv1)
        
        # Missing conversation_parts key entirely
        conv2 = create_horatio_conversation('edge_2')
        del conv2['conversation_parts']
        conversations.append(conv2)
        
        # conversation_parts as None
        conv3 = create_horatio_conversation('edge_3')
        conv3['conversation_parts'] = None
        conversations.append(conv3)
        
        # Admin author with no email field
        conv4 = {
            'id': 'edge_4',
            'created_at': 1699123456,
            'admin_assignee_id': '123',
            'ai_agent_participated': False,
            'full_text': 'Test',
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'author': {
                            'type': 'admin',
                            'id': '123'
                            # No email field
                        }
                    }
                ]
            },
            'source': {},
            'assignee': {}
        }
        conversations.append(conv4)
        
        # Admin author with empty string email
        conv5 = {
            'id': 'edge_5',
            'created_at': 1699123456,
            'admin_assignee_id': '123',
            'ai_agent_participated': False,
            'full_text': 'Test',
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'author': {
                            'type': 'admin',
                            'email': ''
                        }
                    }
                ]
            },
            'source': {},
            'assignee': {}
        }
        conversations.append(conv5)
        
        # Non-admin authors (should be ignored)
        conv6 = {
            'id': 'edge_6',
            'created_at': 1699123456,
            'admin_assignee_id': None,
            'ai_agent_participated': False,
            'full_text': 'Test',
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'author': {
                            'type': 'contact',  # Not admin
                            'email': 'customer@example.com'
                        }
                    }
                ]
            },
            'source': {},
            'assignee': {}
        }
        conversations.append(conv6)
        
        # Create context
        context = AgentContext(
            analysis_id='edge_cases_test',
            analysis_type='edge_cases',
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
            conversations=conversations
        )
        
        # Execute segmentation - should not crash
        result = await agent.execute(context)
        
        # Assert no crashes
        assert result.success, f"Segmentation failed: {result.error_message}"
        
        # Most of these should be classified as 'unknown' or 'paid' (generic)
        # conv4 and conv5 have admin_assignee_id, so should be 'paid'/'unknown'
        # Others should be 'unknown'
        summary = result.data['segmentation_summary']
        total = summary['paid_count'] + summary['free_count'] + summary['unknown_count']
        assert total == len(conversations), \
            f"Total classified ({total}) doesn't match input ({len(conversations)})"
        
        # Confidence should reflect uncertainty
        assert result.confidence < 1.0, \
            "Confidence should be < 1.0 for edge cases with missing data"

    @pytest.mark.asyncio
    async def test_agent_distribution_logging(self, caplog):
        """Test that agent distribution is logged correctly."""
        agent = SegmentationAgent()
        
        # Create known distribution
        conversations = []
        conversations.extend([create_horatio_conversation(f'h_{i}') for i in range(10)])
        conversations.extend([create_boldr_conversation(f'b_{i}') for i in range(5)])
        conversations.extend([create_escalated_conversation(f'e_{i}') for i in range(2)])
        conversations.extend([create_fin_ai_conversation(f'f_{i}') for i in range(8)])
        conversations.extend([create_unknown_conversation(f'u_{i}') for i in range(5)])
        
        # Total: 30 conversations
        # Paid: 17 (10+5+2)
        # Free: 8
        # Unknown: 5
        
        # Create context
        context = AgentContext(
            analysis_id='logging_test',
            analysis_type='distribution_logging',
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
            conversations=conversations
        )
        
        # Execute with logging enabled
        with caplog.at_level(logging.INFO):
            result = await agent.execute(context)
        
        # Assert success
        assert result.success
        
        # Check that logs contain agent distribution
        log_text = caplog.text
        assert 'Agent distribution:' in log_text, \
            "Expected 'Agent distribution:' in logs"
        assert "'horatio': 10" in log_text, \
            "Expected Horatio count in logs"
        assert "'boldr': 5" in log_text, \
            "Expected Boldr count in logs"
        
        # Check percentages
        summary = result.data['segmentation_summary']
        expected_paid_pct = round(17 / 30 * 100, 1)
        expected_free_pct = round(8 / 30 * 100, 1)
        
        assert summary['paid_percentage'] == expected_paid_pct, \
            f"Expected paid percentage {expected_paid_pct}, got {summary['paid_percentage']}"
        assert summary['free_percentage'] == expected_free_pct, \
            f"Expected free percentage {expected_free_pct}, got {summary['free_percentage']}"

    @pytest.mark.asyncio
    async def test_segmentation_with_missing_fields_comprehensive(self):
        """Comprehensive test for conversations with various missing fields."""
        agent = SegmentationAgent()
        
        conversations = []
        
        # Minimal conversation (only required fields)
        conv_minimal = {
            'id': 'minimal_1',
            'created_at': 1699123456,
        }
        conversations.append(conv_minimal)
        
        # Conversation with no source or conversation_parts
        conv_no_parts = {
            'id': 'no_parts_1',
            'created_at': 1699123456,
            'admin_assignee_id': '123',
            'ai_agent_participated': False,
        }
        conversations.append(conv_no_parts)
        
        # Conversation with assignee but no email
        conv_no_email = {
            'id': 'no_email_1',
            'created_at': 1699123456,
            'admin_assignee_id': '123',
            'ai_agent_participated': False,
            'conversation_parts': {'conversation_parts': []},
            'source': {},
            'assignee': {
                'type': 'admin',
                'id': '123',
                'name': 'Agent'
                # Missing email
            }
        }
        conversations.append(conv_no_email)
        
        # Valid Horatio conversation for comparison
        conversations.append(create_horatio_conversation('valid_horatio'))
        
        # Create context
        context = AgentContext(
            analysis_id='missing_fields_test',
            analysis_type='missing_fields',
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
            conversations=conversations
        )
        
        # Execute - should not crash
        result = await agent.execute(context)
        
        # Assert no crashes
        assert result.success, f"Segmentation failed with missing fields: {result.error_message}"
        
        # At least the valid Horatio conversation should be detected
        agent_dist = result.data['agent_distribution']
        assert agent_dist['horatio'] >= 1, \
            "At least one Horatio conversation should be detected"
        
        # Total should equal input
        total = sum(agent_dist.values())
        assert total == len(conversations), \
            f"Total classified ({total}) doesn't match input ({len(conversations)})"
