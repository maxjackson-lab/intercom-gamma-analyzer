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
    location: str = 'conversation_parts',
    tier: str = None
) -> Dict[str, Any]:
    """
    Create a conversation dict with admin email in specified location.
    
    Args:
        email: Admin email address
        conv_id: Conversation ID (default: auto-generated)
        author_type: Author type ('admin', 'contact', 'team')
        location: Where to place email ('conversation_parts', 'source', 'assignee')
        tier: Customer tier ('Free', 'Pro', 'Plus', 'Ultra')
    
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
    
    # Add tier if provided
    if tier:
        base_conv['contacts'] = {
            'contacts': [
                {
                    'custom_attributes': {
                        'tier': tier
                    }
                }
            ]
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


def create_horatio_conversation(conv_id: str, location: str = 'conversation_parts', tier: str = 'Pro') -> Dict[str, Any]:
    """Create a realistic Horatio conversation."""
    return create_conversation_with_admin_email(
        email='agent@hirehoratio.co',
        conv_id=conv_id,
        location=location,
        tier=tier
    )


def create_boldr_conversation(conv_id: str, tier: str = 'Plus') -> Dict[str, Any]:
    """Create a realistic Boldr conversation."""
    return create_conversation_with_admin_email(
        email='support@boldrimpact.com',
        conv_id=conv_id,
        location='conversation_parts',
        tier=tier
    )


def create_escalated_conversation(conv_id: str, person: str = 'max.jackson', tier: str = 'Ultra') -> Dict[str, Any]:
    """Create a realistic escalated conversation."""
    emails = {
        'max.jackson': 'max.jackson@example.com',
        'dae-ho': 'dae-ho@example.com',
        'hilary': 'hilary@example.com'
    }
    return create_conversation_with_admin_email(
        email=emails.get(person, emails['max.jackson']),
        conv_id=conv_id,
        location='conversation_parts',
        tier=tier
    )


def create_fin_ai_conversation(conv_id: str, tier: str = 'Free') -> Dict[str, Any]:
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
        'assignee': {},
        'contacts': {
            'contacts': [
                {
                    'custom_attributes': {
                        'tier': tier
                    }
                }
            ]
        }
    }


def create_unknown_conversation(conv_id: str, tier: str = None) -> Dict[str, Any]:
    """Create an unknown conversation."""
    conv = {
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
    
    # Add tier if provided
    if tier:
        conv['contacts'] = {
            'contacts': [
                {
                    'custom_attributes': {
                        'tier': tier
                    }
                }
            ]
        }
    
    return conv


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
        
        # Add 15 Horatio conversations (10 Pro, 5 Plus)
        for i in range(10):
            conversations.append(create_horatio_conversation(f'horatio_pro_{i}', tier='Pro'))
        for i in range(5):
            conversations.append(create_horatio_conversation(f'horatio_plus_{i}', tier='Plus'))
        
        # Add 5 Boldr conversations (all Plus)
        for i in range(5):
            conversations.append(create_boldr_conversation(f'boldr_{i}', tier='Plus'))
        
        # Add 5 escalated conversations (all Ultra)
        for i in range(5):
            person = ['max.jackson', 'dae-ho', 'hilary'][i % 3]
            conversations.append(create_escalated_conversation(f'escalated_{i}', person, tier='Ultra'))
        
        # Add 15 Fin AI conversations (all Free)
        for i in range(15):
            conversations.append(create_fin_ai_conversation(f'fin_ai_{i}', tier='Free'))
        
        # Add 10 unknown conversations (5 Free, 5 missing tier)
        for i in range(5):
            conversations.append(create_unknown_conversation(f'unknown_free_{i}', tier='Free'))
        for i in range(5):
            conversations.append(create_unknown_conversation(f'unknown_missing_{i}'))
        
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
        # Note: 10 unknown conversations (5 Free + 5 missing tier) default to fin_ai
        assert_segmentation_result(
            result,
            expected_distribution={
                'horatio': 15,
                'boldr': 5,
                'escalated': 5,
                'fin_ai': 25,  # 15 explicit + 5 Free unknown + 5 missing tier unknown
                'unknown': 0  # All unknowns are Free tier, classified as fin_ai
            },
            expected_paid=25,  # 15 + 5 + 5
            expected_free=25,  # 15 + 5 + 5 (10 unknowns defaulted to Free)
            expected_unknown=0  # All unknowns classified as free/fin_ai
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
            if i < 400:  # 40% Horatio (60% Pro, 40% Plus)
                tier = 'Pro' if i < 240 else 'Plus'
                conversations.append(create_horatio_conversation(f'horatio_{i}', tier=tier))
            elif i < 600:  # 20% Boldr (50% Pro, 50% Plus)
                tier = 'Pro' if i < 500 else 'Plus'
                conversations.append(create_boldr_conversation(f'boldr_{i}', tier=tier))
            elif i < 650:  # 5% Escalated (all Ultra)
                conversations.append(create_escalated_conversation(f'escalated_{i}', tier='Ultra'))
            elif i < 900:  # 25% Fin AI (all Free)
                conversations.append(create_fin_ai_conversation(f'fin_ai_{i}', tier='Free'))
            else:  # 10% Unknown (50% Free, 50% missing tier)
                tier = 'Free' if i < 950 else None
                conversations.append(create_unknown_conversation(f'unknown_{i}', tier=tier))
        
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
        # Note: 100 unknown conversations (50 Free + 50 missing tier) default to fin_ai
        assert_segmentation_result(
            result,
            expected_distribution={
                'horatio': 400,
                'boldr': 200,
                'escalated': 50,
                'fin_ai': 350,  # 250 explicit + 100 unknowns
                'unknown': 0  # All unknowns are Free tier, classified as fin_ai
            },
            expected_paid=650,
            expected_free=350,  # 250 explicit + 100 unknowns
            expected_unknown=0  # All unknowns classified as free/fin_ai
        )

    @pytest.mark.asyncio
    async def test_segmentation_with_only_horatio(self):
        """Test segmentation with only Horatio conversations."""
        agent = SegmentationAgent()
        
        conversations = []
        for i in range(15):
            conversations.append(create_horatio_conversation(f'horatio_pro_{i}', tier='Pro'))
        for i in range(5):
            conversations.append(create_horatio_conversation(f'horatio_plus_{i}', tier='Plus'))
        
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
        
        # 5 conversations: email in conversation_parts only (Pro tier)
        for i in range(5):
            conversations.append(create_horatio_conversation(f'parts_{i}', location='conversation_parts', tier='Pro'))
        
        # 5 conversations: email in source only (Plus tier)
        for i in range(5):
            conversations.append(create_horatio_conversation(f'source_{i}', location='source', tier='Plus'))
        
        # 5 conversations: email in assignee only (Ultra tier)
        for i in range(5):
            conversations.append(create_horatio_conversation(f'assignee_{i}', location='assignee', tier='Ultra'))
        
        # 5 conversations: email in multiple locations (Pro tier)
        for i in range(5):
            conv = create_horatio_conversation(f'multiple_{i}', location='conversation_parts', tier='Pro')
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
        # Free: 13 (8 explicit + 5 unknown defaults to Free)
        # Unknown: 0 (all unknowns defaulted to Free)

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
        
        # Check percentages (updated to account for 5 unknowns defaulting to Free)
        summary = result.data['segmentation_summary']
        expected_paid_pct = round(17 / 30 * 100, 1)  # 56.7%
        expected_free_pct = round(13 / 30 * 100, 1)  # 43.3% (8 explicit + 5 unknown)

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

    @pytest.mark.asyncio
    async def test_tier_based_segmentation_full_pipeline(self):
        """Test full tier-based segmentation pipeline with realistic tier distribution."""
        agent = SegmentationAgent()
        
        conversations = []
        
        # Create 120 conversations with realistic tier distribution
        # Free tier (36 conversations, 30%)
        for i in range(36):
            conversations.append(create_fin_ai_conversation(f'free_{i}', tier='Free'))
        
        # Pro tier (48 conversations, 40%)
        for i in range(30):
            conversations.append(create_horatio_conversation(f'pro_horatio_{i}', tier='Pro'))
        for i in range(10):
            conversations.append(create_boldr_conversation(f'pro_boldr_{i}', tier='Pro'))
        for i in range(5):
            conversations.append(create_escalated_conversation(f'pro_escalated_{i}', tier='Pro'))
        for i in range(3):
            # Fin-resolved (AI-only, no admin)
            conv = create_fin_ai_conversation(f'pro_fin_resolved_{i}', tier='Pro')
            conv['ai_agent_participated'] = True
            conv['admin_assignee_id'] = None
            conversations.append(conv)
        
        # Plus tier (24 conversations, 20%)
        for i in range(15):
            conversations.append(create_horatio_conversation(f'plus_horatio_{i}', tier='Plus'))
        for i in range(5):
            conversations.append(create_boldr_conversation(f'plus_boldr_{i}', tier='Plus'))
        for i in range(2):
            conversations.append(create_escalated_conversation(f'plus_escalated_{i}', tier='Plus'))
        for i in range(2):
            # Fin-resolved (AI-only, no admin)
            conv = create_fin_ai_conversation(f'plus_fin_resolved_{i}', tier='Plus')
            conv['ai_agent_participated'] = True
            conv['admin_assignee_id'] = None
            conversations.append(conv)
        
        # Ultra tier (12 conversations, 10%)
        for i in range(8):
            conversations.append(create_escalated_conversation(f'ultra_escalated_{i}', tier='Ultra'))
        for i in range(2):
            conversations.append(create_horatio_conversation(f'ultra_horatio_{i}', tier='Ultra'))
        for i in range(2):
            # Fin-resolved (AI-only, no admin)
            conv = create_fin_ai_conversation(f'ultra_fin_resolved_{i}', tier='Ultra')
            conv['ai_agent_participated'] = True
            conv['admin_assignee_id'] = None
            conversations.append(conv)
        
        # Create context
        context = AgentContext(
            analysis_id='tier_pipeline_test',
            analysis_type='tier_based_segmentation',
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
            conversations=conversations
        )
        
        # Execute segmentation
        result = await agent.execute(context)
        
        # Assert success
        assert result.success, f"Segmentation failed: {result.error_message}"
        
        # Assert tier distribution
        tier_dist = result.data['segmentation_summary']['tier_distribution']
        assert tier_dist['free'] == 36, f"Expected 36 free tier conversations, got {tier_dist['free']}"
        assert tier_dist['pro'] == 48, f"Expected 48 pro tier conversations, got {tier_dist['pro']}"
        assert tier_dist['plus'] == 24, f"Expected 24 plus tier conversations, got {tier_dist['plus']}"
        assert tier_dist['ultra'] == 12, f"Expected 12 ultra tier conversations, got {tier_dist['ultra']}"
        
        # Assert segmentation summary
        summary = result.data['segmentation_summary']
        assert summary['paid_count'] == 84, f"Expected 84 paid conversations, got {summary['paid_count']}"
        assert summary['free_count'] == 36, f"Expected 36 free conversations, got {summary['free_count']}"
        assert summary['paid_human_count'] == 77, f"Expected 77 paid human conversations, got {summary['paid_human_count']}"
        assert summary['paid_fin_resolved_count'] == 7, f"Expected 7 paid fin-resolved conversations, got {summary['paid_fin_resolved_count']}"
        assert summary['free_fin_only_count'] == 36, f"Expected 36 free fin-only conversations, got {summary['free_fin_only_count']}"
        
        # Assert agent distribution
        agent_dist = result.data['agent_distribution']
        assert agent_dist['horatio'] == 47, f"Expected 47 Horatio conversations, got {agent_dist['horatio']}"
        assert agent_dist['boldr'] == 15, f"Expected 15 Boldr conversations, got {agent_dist['boldr']}"
        assert agent_dist['escalated'] == 15, f"Expected 15 escalated conversations, got {agent_dist['escalated']}"
        assert agent_dist['fin_ai'] == 36, f"Expected 36 fin_ai conversations, got {agent_dist['fin_ai']}"
        assert agent_dist['fin_resolved'] == 7, f"Expected 7 fin_resolved conversations, got {agent_dist['fin_resolved']}"
        
        # Assert tier-aware confidence
        assert result.confidence > 0.95, f"Expected confidence > 0.95, got {result.confidence}"
        assert result.confidence_level == ConfidenceLevel.HIGH.value, f"Expected 'high', got {result.confidence_level}"
        
        # Assert result structure
        assert len(result.data['paid_customer_conversations']) == 84, f"Expected 84 paid customer conversations in result"
        assert len(result.data['paid_fin_resolved_conversations']) == 7, f"Expected 7 paid fin-resolved conversations in result"
        assert len(result.data['free_fin_only_conversations']) == 36, f"Expected 36 free fin-only conversations in result"

    @pytest.mark.asyncio
    async def test_tier_data_quality_tracking(self):
        """Test tier data quality tracking and confidence scoring."""
        agent = SegmentationAgent()
        
        conversations = []
        
        # Create 50 conversations with mixed tier data quality
        # 20 with valid tier='Pro' (Horatio conversations)
        for i in range(20):
            conversations.append(create_horatio_conversation(f'valid_pro_{i}', tier='Pro'))
        
        # 10 with valid tier='Free' (Fin AI conversations)
        for i in range(10):
            conversations.append(create_fin_ai_conversation(f'valid_free_{i}', tier='Free'))
        
        # 10 with invalid tier='Premium' (should default to Free)
        for i in range(10):
            conv = create_fin_ai_conversation(f'invalid_tier_{i}', tier='Premium')
            conversations.append(conv)
        
        # 10 with missing tier (no contacts dict)
        for i in range(10):
            conversations.append(create_unknown_conversation(f'missing_tier_{i}'))
        
        # Create context
        context = AgentContext(
            analysis_id='tier_quality_test',
            analysis_type='tier_data_quality',
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
            conversations=conversations
        )
        
        # Execute segmentation
        result = await agent.execute(context)
        
        # Assert success
        assert result.success, f"Segmentation failed: {result.error_message}"
        
        # Assert tier distribution (invalid and missing should default to Free)
        tier_dist = result.data['segmentation_summary']['tier_distribution']
        assert tier_dist['pro'] == 20, f"Expected 20 pro tier conversations, got {tier_dist['pro']}"
        assert tier_dist['free'] == 30, f"Expected 30 free tier conversations (10 valid + 10 invalid + 10 missing), got {tier_dist['free']}"
        
        # Assert tier data quality affects confidence
        assert result.confidence < 0.9, f"Expected confidence < 0.9 due to tier quality issues, got {result.confidence}"
        assert result.confidence_level in [ConfidenceLevel.MEDIUM.value, ConfidenceLevel.LOW.value], f"Expected 'medium' or 'low', got {result.confidence_level}"
        
        # Assert segmentation still works correctly
        summary = result.data['segmentation_summary']
        assert summary['paid_count'] == 20, f"Expected 20 paid conversations, got {summary['paid_count']}"
        assert summary['free_count'] == 30, f"Expected 30 free conversations, got {summary['free_count']}"
        
        # Assert limitations include tier data quality issues
        assert any('tier' in limitation.lower() for limitation in result.limitations), \
            "Expected limitations to include tier data quality issues"

    @pytest.mark.asyncio
    async def test_free_tier_with_admin_edge_case_integration(self, caplog):
        """Test Free tier with admin_assignee_id edge case at scale."""
        agent = SegmentationAgent()
        
        conversations = []
        
        # 10 Free tier with ai_agent_participated=True, no admin (normal)
        for i in range(10):
            conversations.append(create_fin_ai_conversation(f'free_normal_{i}', tier='Free'))
        
        # 10 Free tier with admin_assignee_id set (abuse/trust & safety edge case)
        for i in range(10):
            conv = create_fin_ai_conversation(f'free_admin_{i}', tier='Free')
            conv['admin_assignee_id'] = f'admin_{i}'
            conv['conversation_parts']['conversation_parts'].append({
                'author': {
                    'type': 'admin',
                    'email': 'support@example.com'
                }
            })
            conversations.append(conv)
        
        # 10 Pro tier with admin (normal paid)
        for i in range(10):
            conversations.append(create_horatio_conversation(f'pro_normal_{i}', tier='Pro'))
        
        # Create context
        context = AgentContext(
            analysis_id='free_admin_edge_test',
            analysis_type='free_tier_admin_edge_case',
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
            conversations=conversations
        )
        
        # Execute segmentation with logging
        with caplog.at_level('WARNING'):
            result = await agent.execute(context)
        
        # Assert success
        assert result.success, f"Segmentation failed: {result.error_message}"
        
        # Assert all Free tier are classified as 'fin_ai'
        summary = result.data['segmentation_summary']
        assert summary['free_count'] == 20, f"Expected 20 free conversations, got {summary['free_count']}"
        assert summary['paid_count'] == 10, f"Expected 10 paid conversations, got {summary['paid_count']}"
        
        agent_dist = result.data['agent_distribution']
        assert agent_dist['fin_ai'] == 20, f"Expected 20 fin_ai conversations, got {agent_dist['fin_ai']}"
        
        # Verify warning logs for edge cases
        warning_logs = [record for record in caplog.records if record.levelname == 'WARNING']
        admin_edge_warnings = [log for log in warning_logs if 'abuse/trust & safety' in log.message]
        assert len(admin_edge_warnings) == 10, f"Expected 10 warning logs for admin edge cases, got {len(admin_edge_warnings)}"

    @pytest.mark.asyncio
    async def test_paid_tier_fin_resolved_vs_free_tier_fin_ai(self):
        """Test distinction between paid tier fin-resolved and free tier fin-ai."""
        agent = SegmentationAgent()
        
        conversations = []
        
        # 10 Free tier with AI-only (should be 'fin_ai')
        for i in range(10):
            conversations.append(create_fin_ai_conversation(f'free_ai_{i}', tier='Free'))
        
        # 10 Pro tier with AI-only (should be 'fin_resolved')
        for i in range(10):
            conv = create_fin_ai_conversation(f'pro_ai_{i}', tier='Pro')
            conv['ai_agent_participated'] = True
            conv['admin_assignee_id'] = None
            conversations.append(conv)
        
        # 10 Plus tier with AI-only (should be 'fin_resolved')
        for i in range(10):
            conv = create_fin_ai_conversation(f'plus_ai_{i}', tier='Plus')
            conv['ai_agent_participated'] = True
            conv['admin_assignee_id'] = None
            conversations.append(conv)
        
        # 10 Ultra tier with AI-only (should be 'fin_resolved')
        for i in range(10):
            conv = create_fin_ai_conversation(f'ultra_ai_{i}', tier='Ultra')
            conv['ai_agent_participated'] = True
            conv['admin_assignee_id'] = None
            conversations.append(conv)
        
        # Create context
        context = AgentContext(
            analysis_id='fin_distinction_test',
            analysis_type='paid_vs_free_fin_distinction',
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
            conversations=conversations
        )
        
        # Execute segmentation
        result = await agent.execute(context)
        
        # Assert success
        assert result.success, f"Segmentation failed: {result.error_message}"
        
        # Assert correct classification
        summary = result.data['segmentation_summary']
        assert summary['free_count'] == 10, f"Expected 10 free conversations, got {summary['free_count']}"
        assert summary['paid_count'] == 30, f"Expected 30 paid conversations, got {summary['paid_count']}"
        
        agent_dist = result.data['agent_distribution']
        assert agent_dist['fin_ai'] == 10, f"Expected 10 fin_ai conversations (only Free tier), got {agent_dist['fin_ai']}"
        assert agent_dist['fin_resolved'] == 30, f"Expected 30 fin_resolved conversations (all paid tiers), got {agent_dist['fin_resolved']}"
        
        assert summary['paid_fin_resolved_count'] == 30, f"Expected 30 paid fin-resolved conversations, got {summary['paid_fin_resolved_count']}"
        assert summary['free_fin_only_count'] == 10, f"Expected 10 free fin-only conversations, got {summary['free_fin_only_count']}"
        
        # Assert result structure
        paid_fin_resolved = result.data['paid_fin_resolved_conversations']
        free_fin_only = result.data['free_fin_only_conversations']
        
        assert len(paid_fin_resolved) == 30, f"Expected 30 paid fin-resolved conversations in result, got {len(paid_fin_resolved)}"
        assert len(free_fin_only) == 10, f"Expected 10 free fin-only conversations in result, got {len(free_fin_only)}"
        
        # Verify no overlap between the two lists
        paid_ids = {conv['id'] for conv in paid_fin_resolved}
        free_ids = {conv['id'] for conv in free_fin_only}
        assert len(paid_ids.intersection(free_ids)) == 0, "Expected no overlap between paid_fin_resolved and free_fin_only lists"
