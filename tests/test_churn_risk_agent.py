"""
Tests for ChurnRiskAgent

Comprehensive test suite for churn signal detection agent.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.agents.churn_risk_agent import ChurnRiskAgent
from src.agents.base_agent import AgentContext, ConfidenceLevel


@pytest.fixture
def sample_conversations_with_churn_signals():
    """Create conversations with various churn signals"""
    conversations = []
    
    # Conversations with cancellation language
    for i in range(5):
        conversations.append({
            'id': f'cancel_{i}',
            'tier': 'business',
            'conversation_rating': 1,
            'statistics': {'count_reopens': 2},
            'state': 'closed',
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': f"I'd like to cancel my subscription please. Not satisfied with the service."}
                ]
            },
            'created_at': int((datetime.now() - timedelta(days=2)).timestamp())
        })
    
    # Conversations with competitor mentions
    for i in range(3):
        conversations.append({
            'id': f'competitor_{i}',
            'tier': 'team',
            'conversation_rating': 2,
            'statistics': {'count_reopens': 1},
            'state': 'closed',
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': f"We're considering switching to Pitch. It has better features for our team."}
                ]
            },
            'created_at': int((datetime.now() - timedelta(days=1)).timestamp())
        })
    
    # Frustration + high-value pattern (Business tier + bad CSAT + multiple reopens)
    for i in range(4):
        conversations.append({
            'id': f'frustration_{i}',
            'tier': 'business',
            'conversation_rating': 1,
            'statistics': {'count_reopens': 3},
            'state': 'open',
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': f"This is the third time I'm contacting you about this issue. Fed up with this!"}
                ]
            },
            'created_at': int((datetime.now() - timedelta(days=10)).timestamp())
        })
    
    # Resolution failure (multiple reopens + open state + >7 days)
    for i in range(2):
        conversations.append({
            'id': f'resolution_fail_{i}',
            'tier': 'pro',
            'conversation_rating': 2,
            'statistics': {'count_reopens': 4},
            'state': 'open',
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': f"Still waiting for a resolution on this critical issue."}
                ]
            },
            'created_at': int((datetime.now() - timedelta(days=15)).timestamp())
        })
    
    # Normal conversations (no churn signals)
    for i in range(16):
        conversations.append({
            'id': f'normal_{i}',
            'tier': 'free',
            'conversation_rating': 4,
            'statistics': {'count_reopens': 0},
            'state': 'closed',
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': f"Thanks for the quick help!"}
                ]
            },
            'created_at': int((datetime.now() - timedelta(days=1)).timestamp())
        })
    
    return conversations


@pytest.fixture
def churn_risk_agent():
    """ChurnRiskAgent instance"""
    return ChurnRiskAgent()


@pytest.fixture
def agent_context_with_churn_data(sample_conversations_with_churn_signals):
    """AgentContext with churn data"""
    context = AgentContext(
        conversations=sample_conversations_with_churn_signals,
        previous_results={
            'SegmentationAgent': {
                'data': {
                    'tier_distribution': {
                        'business': 9,
                        'team': 3,
                        'pro': 2,
                        'free': 16
                    }
                }
            }
        }
    )
    return context


# Signal Detection Tests
@pytest.mark.asyncio
async def test_detects_cancellation_language(churn_risk_agent):
    """Test detection of cancellation language"""
    conversations = [{
        'id': 'test_cancel',
        'tier': 'business',
        'conversation_parts': {
            'conversation_parts': [
                {'author': {'type': 'user'}, 'body': 'I want to cancel my subscription immediately.'}
            ]
        }
    }]
    
    context = AgentContext(conversations=conversations, previous_results={})
    result = await churn_risk_agent.execute(context)
    
    assert result.success
    high_risk = result.data.get('high_risk_conversations', [])
    
    assert len(high_risk) > 0
    assert 'cancellation_language' in high_risk[0]['signals']


@pytest.mark.asyncio
async def test_detects_competitor_mentions(churn_risk_agent):
    """Test detection of competitor mentions"""
    conversations = [{
        'id': 'test_competitor',
        'tier': 'team',
        'conversation_parts': {
            'conversation_parts': [
                {'author': {'type': 'user'}, 'body': 'Considering moving to Canva for better design tools.'}
            ]
        }
    }]
    
    context = AgentContext(conversations=conversations, previous_results={})
    result = await churn_risk_agent.execute(context)
    
    assert result.success
    high_risk = result.data.get('high_risk_conversations', [])
    
    assert len(high_risk) > 0
    assert 'competitor_mentioned' in high_risk[0]['signals']
    assert any('canva' in quote.lower() for quote in high_risk[0]['quotes'])


@pytest.mark.asyncio
async def test_detects_frustration_high_value_pattern(churn_risk_agent):
    """Test detection of frustration + high-value pattern"""
    conversations = [{
        'id': 'test_frustration',
        'tier': 'business',
        'conversation_rating': 1,
        'statistics': {'count_reopens': 3},
        'conversation_parts': {
            'conversation_parts': [
                {'author': {'type': 'user'}, 'body': 'This is unacceptable. Had enough of these issues.'}
            ]
        }
    }]
    
    context = AgentContext(conversations=conversations, previous_results={})
    result = await churn_risk_agent.execute(context)
    
    assert result.success
    high_risk = result.data.get('high_risk_conversations', [])
    
    assert len(high_risk) > 0
    assert 'frustration_pattern' in high_risk[0]['signals']


@pytest.mark.asyncio
async def test_detects_resolution_failure_pattern(churn_risk_agent):
    """Test detection of resolution failure pattern"""
    conversations = [{
        'id': 'test_resolution_fail',
        'tier': 'pro',
        'state': 'open',
        'statistics': {'count_reopens': 4},
        'conversation_parts': {
            'conversation_parts': [
                {'author': {'type': 'user'}, 'body': 'Still no resolution.'}
            ]
        },
        'created_at': int((datetime.now() - timedelta(days=10)).timestamp())
    }]
    
    context = AgentContext(conversations=conversations, previous_results={})
    result = await churn_risk_agent.execute(context)
    
    assert result.success
    high_risk = result.data.get('high_risk_conversations', [])
    
    assert len(high_risk) > 0
    assert 'resolution_failure' in high_risk[0]['signals']


@pytest.mark.asyncio
async def test_extracts_churn_quotes(churn_risk_agent, agent_context_with_churn_data):
    """Test that churn quotes are extracted"""
    result = await churn_risk_agent.execute(agent_context_with_churn_data)
    
    assert result.success
    high_risk = result.data.get('high_risk_conversations', [])
    
    # Each high-risk conversation should have quotes
    for conv in high_risk:
        assert 'quotes' in conv
        assert len(conv['quotes']) > 0


# Risk Scoring Tests
@pytest.mark.asyncio
async def test_risk_score_calculation_multiple_signals(churn_risk_agent):
    """Test risk score with multiple signals"""
    conversations = [{
        'id': 'multi_signal',
        'tier': 'business',
        'conversation_rating': 1,
        'statistics': {'count_reopens': 2},
        'conversation_parts': {
            'conversation_parts': [
                {'author': {'type': 'user'}, 'body': 'Canceling and moving to Pitch. Had enough.'}
            ]
        }
    }]
    
    context = AgentContext(conversations=conversations, previous_results={})
    result = await churn_risk_agent.execute(context)
    
    assert result.success
    high_risk = result.data.get('high_risk_conversations', [])
    
    assert len(high_risk) > 0
    # Should have high risk score due to multiple signals
    assert high_risk[0]['risk_score'] > 0.7


@pytest.mark.asyncio
async def test_risk_score_tier_weighting(churn_risk_agent):
    """Test tier multiplier in risk scoring"""
    # Same signals, different tiers
    conversations = [
        {
            'id': 'business_churn',
            'tier': 'business',
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'I want to cancel my subscription.'}
                ]
            }
        },
        {
            'id': 'free_churn',
            'tier': 'free',
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'I want to cancel my subscription.'}
                ]
            }
        }
    ]
    
    context = AgentContext(conversations=conversations, previous_results={})
    result = await churn_risk_agent.execute(context)
    
    assert result.success
    high_risk = result.data.get('high_risk_conversations', [])
    
    # Find both conversations
    business_conv = next((c for c in high_risk if c['tier'] == 'business'), None)
    free_conv = next((c for c in high_risk if c['tier'] == 'free'), None)
    
    # Business tier should have higher risk score
    if business_conv and free_conv:
        assert business_conv['risk_score'] > free_conv['risk_score']


@pytest.mark.asyncio
async def test_risk_score_capped_at_1_0(churn_risk_agent):
    """Test risk score doesn't exceed 1.0"""
    conversations = [{
        'id': 'max_risk',
        'tier': 'business',
        'conversation_rating': 1,
        'statistics': {'count_reopens': 5},
        'state': 'open',
        'conversation_parts': {
            'conversation_parts': [
                {'author': {'type': 'user'}, 'body': 'Canceling and switching to Pitch. Fed up. This is unacceptable.'}
            ]
        },
        'created_at': int((datetime.now() - timedelta(days=15)).timestamp())
    }]
    
    context = AgentContext(conversations=conversations, previous_results={})
    result = await churn_risk_agent.execute(context)
    
    assert result.success
    high_risk = result.data.get('high_risk_conversations', [])
    
    assert len(high_risk) > 0
    assert high_risk[0]['risk_score'] <= 1.0


# Priority Assignment Tests
@pytest.mark.asyncio
async def test_priority_immediate_for_business_high_risk(churn_risk_agent):
    """Test immediate priority for high-risk Business tier"""
    conversations = [{
        'id': 'immediate',
        'tier': 'business',
        'conversation_rating': 1,
        'statistics': {'count_reopens': 3},
        'conversation_parts': {
            'conversation_parts': [
                {'author': {'type': 'user'}, 'body': 'Cancel my subscription immediately.'}
            ]
        }
    }]
    
    context = AgentContext(conversations=conversations, previous_results={})
    result = await churn_risk_agent.execute(context)
    
    assert result.success
    high_risk = result.data.get('high_risk_conversations', [])
    
    assert len(high_risk) > 0
    assert high_risk[0]['priority'] == 'immediate'


# Risk Breakdown Tests
@pytest.mark.asyncio
async def test_risk_breakdown_by_tier(churn_risk_agent, agent_context_with_churn_data):
    """Test risk breakdown correctly counts by tier"""
    result = await churn_risk_agent.execute(agent_context_with_churn_data)
    
    assert result.success
    risk_breakdown = result.data.get('risk_breakdown', {})
    
    assert 'high_value_at_risk' in risk_breakdown
    assert 'medium_value_at_risk' in risk_breakdown
    assert 'low_value_at_risk' in risk_breakdown
    assert 'total_risk_signals' in risk_breakdown
    
    # Should have some high-value customers at risk (business tier conversations)
    assert risk_breakdown['high_value_at_risk'] > 0


@pytest.mark.asyncio
async def test_signal_distribution_calculation(churn_risk_agent, agent_context_with_churn_data):
    """Test signal distribution counts each signal type"""
    result = await churn_risk_agent.execute(agent_context_with_churn_data)
    
    assert result.success
    signal_dist = result.data.get('signal_distribution', {})
    
    assert 'cancellation_language' in signal_dist
    assert 'competitor_mentioned' in signal_dist
    assert 'frustration_pattern' in signal_dist
    assert 'resolution_failure' in signal_dist
    
    # Should detect signals from test data
    assert signal_dist['cancellation_language'] > 0


# Edge Cases
@pytest.mark.asyncio
async def test_churn_risk_handles_missing_tier(churn_risk_agent):
    """Test graceful handling of missing tier data"""
    conversations = [{
        'id': 'no_tier',
        'tier': None,
        'conversation_parts': {
            'conversation_parts': [
                {'author': {'type': 'user'}, 'body': 'Cancel my subscription.'}
            ]
        }
    }]
    
    context = AgentContext(conversations=conversations, previous_results={})
    result = await churn_risk_agent.execute(context)
    
    assert result.success
    # Should default to 'free' for risk calculation


@pytest.mark.asyncio
async def test_churn_risk_handles_missing_csat(churn_risk_agent):
    """Test graceful handling of missing CSAT"""
    conversations = [{
        'id': 'no_csat',
        'tier': 'business',
        'conversation_rating': None,  # No CSAT
        'conversation_parts': {
            'conversation_parts': [
                {'author': {'type': 'user'}, 'body': 'Cancel my subscription.'}
            ]
        }
    }]
    
    context = AgentContext(conversations=conversations, previous_results={})
    result = await churn_risk_agent.execute(context)
    
    assert result.success
    # Should still detect cancellation signal


@pytest.mark.asyncio
async def test_churn_risk_handles_no_churn_signals(churn_risk_agent):
    """Test handling when no churn signals detected"""
    conversations = [{
        'id': f'normal_{i}',
        'tier': 'free',
        'conversation_rating': 4,
        'statistics': {'count_reopens': 0},
        'conversation_parts': {
            'conversation_parts': [
                {'author': {'type': 'user'}, 'body': 'Thank you for the help!'}
            ]
        }
    } for i in range(10)]
    
    context = AgentContext(conversations=conversations, previous_results={})
    result = await churn_risk_agent.execute(context)
    
    assert result.success
    high_risk = result.data.get('high_risk_conversations', [])
    
    assert len(high_risk) == 0
    risk_breakdown = result.data.get('risk_breakdown', {})
    assert risk_breakdown['total_risk_signals'] == 0


@pytest.mark.asyncio
async def test_churn_risk_output_schema(churn_risk_agent, agent_context_with_churn_data):
    """Test output has required schema"""
    result = await churn_risk_agent.execute(agent_context_with_churn_data)
    
    assert result.success
    assert 'high_risk_conversations' in result.data
    assert 'risk_breakdown' in result.data
    assert 'signal_distribution' in result.data


@pytest.mark.asyncio
async def test_churn_risk_intercom_urls_generated(churn_risk_agent, agent_context_with_churn_data):
    """Test all high-risk conversations have valid Intercom URLs"""
    result = await churn_risk_agent.execute(agent_context_with_churn_data)
    
    assert result.success
    high_risk = result.data.get('high_risk_conversations', [])
    
    for conv in high_risk:
        assert 'intercom_url' in conv
        assert 'intercom.com' in conv['intercom_url']
        assert conv['conversation_id'] in conv['intercom_url']


@pytest.mark.asyncio
async def test_churn_risk_execution_time(churn_risk_agent, agent_context_with_churn_data):
    """Test execution completes in reasonable time"""
    start = datetime.now()
    result = await churn_risk_agent.execute(agent_context_with_churn_data)
    duration = (datetime.now() - start).total_seconds()
    
    assert result.success
    assert duration < 2.0  # Should complete in <2 seconds


@pytest.mark.asyncio
async def test_churn_risk_with_llm_analysis(agent_context_with_churn_data):
    """Test LLM analysis when AI client is provided"""
    # Create agent with mock AI client
    mock_ai_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Test churn analysis"))]
    mock_ai_client.chat.completions.create.return_value = mock_response
    
    agent = ChurnRiskAgent(ai_client=mock_ai_client)
    
    result = await agent.execute(agent_context_with_churn_data)
    
    assert result.success
    high_risk = result.data.get('high_risk_conversations', [])
    
    # Should have LLM analysis for high-risk conversations
    if high_risk:
        # LLM should have been called for at least one conversation
        assert mock_ai_client.chat.completions.create.call_count >= 1

