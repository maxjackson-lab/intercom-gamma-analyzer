"""
Tests for CorrelationAgent

Comprehensive test suite for statistical correlation analysis agent.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.agents.correlation_agent import CorrelationAgent
from src.agents.base_agent import AgentContext, ConfidenceLevel


@pytest.fixture
def sample_conversations_with_tiers():
    """Create sample conversations with varied tiers, topics, and metrics"""
    conversations = []
    
    # Business tier heavily represented in API issues (correlation signal)
    for i in range(15):
        conversations.append({
            'id': f'api_business_{i}',
            'tier': 'business',
            'conversation_rating': 2 if i % 3 == 0 else 4,
            'statistics': {
                'count_reopens': 2 if i % 4 == 0 else 0,
                'count_conversation_parts': 6 if i % 3 == 0 else 3,
                'handling_time': 3600 * (8 if i % 5 == 0 else 4)
            },
            'admin_assignee_id': f'admin_{i}' if i % 2 == 0 else None,
            'created_at': int((datetime.now() - timedelta(days=i % 7)).timestamp())
        })
    
    # Free tier in billing issues
    for i in range(10):
        conversations.append({
            'id': f'billing_free_{i}',
            'tier': 'free',
            'conversation_rating': 4 if i % 2 == 0 else 3,
            'statistics': {
                'count_reopens': 0,
                'count_conversation_parts': 2,
                'handling_time': 3600 * 2
            },
            'created_at': int((datetime.now() - timedelta(days=i % 7)).timestamp())
        })
    
    # Team tier mixed across topics
    for i in range(15):
        conversations.append({
            'id': f'mixed_team_{i}',
            'tier': 'team',
            'conversation_rating': 3,
            'statistics': {
                'count_reopens': 1 if i % 5 == 0 else 0,
                'count_conversation_parts': 4,
                'handling_time': 3600 * 3
            },
            'created_at': int((datetime.now() - timedelta(days=i % 7)).timestamp())
        })
    
    return conversations


@pytest.fixture
def sample_segmentation_data():
    """Mock SegmentationAgent output"""
    return {
        'tier_distribution': {
            'business': 15,
            'free': 10,
            'team': 15
        },
        'agent_attribution': {
            'Horatio': 20,
            'Boldr': 10,
            'Fin': 10
        }
    }


@pytest.fixture
def sample_topic_detection_data(sample_conversations_with_tiers):
    """Mock TopicDetectionAgent output"""
    # Create topics_by_conversation mapping
    topics_by_conv = {}
    
    # Business tier → API issues
    for conv in sample_conversations_with_tiers:
        if 'api_business' in conv['id']:
            topics_by_conv[conv['id']] = ['API Issues']
        elif 'billing_free' in conv['id']:
            topics_by_conv[conv['id']] = ['Billing']
        else:
            topics_by_conv[conv['id']] = ['General Support']
    
    return {
        'topic_distribution': {
            'API Issues': 15,
            'Billing': 10,
            'General Support': 15
        },
        'topics_by_conversation': topics_by_conv
    }


@pytest.fixture
def correlation_agent():
    """CorrelationAgent instance"""
    return CorrelationAgent()


@pytest.fixture
def agent_context_with_correlations(sample_conversations_with_tiers, sample_segmentation_data, sample_topic_detection_data):
    """AgentContext with conversations and previous_results populated"""
    context = AgentContext(
        conversations=sample_conversations_with_tiers,
        previous_results={
            'SegmentationAgent': {'data': sample_segmentation_data},
            'TopicDetectionAgent': {'data': sample_topic_detection_data}
        },
        metadata={
            'topics_by_conversation': sample_topic_detection_data['topics_by_conversation']
        }
    )
    return context


# Tier × Topic Correlation Tests
@pytest.mark.asyncio
async def test_tier_topic_correlation_detects_business_api_pattern(correlation_agent, agent_context_with_correlations):
    """Test that Business tier over-representation in API issues is detected"""
    result = await correlation_agent.execute(agent_context_with_correlations)
    
    assert result.success
    correlations = result.data.get('correlations', [])
    
    # Should find Business tier × API correlation
    tier_topic_corrs = [c for c in correlations if c['type'] == 'tier_topic']
    assert len(tier_topic_corrs) > 0
    
    # Check for Business/API correlation
    business_api = next((c for c in tier_topic_corrs if 'business' in c['description'].lower() and 'api' in c['description'].lower()), None)
    assert business_api is not None
    assert business_api['strength'] > 2.0  # Over-represented


@pytest.mark.asyncio
async def test_csat_reopen_correlation_calculates_correctly(correlation_agent):
    """Test CSAT × Reopens correlation calculation"""
    conversations = []
    
    # Reopened conversations with bad CSAT
    for i in range(10):
        conversations.append({
            'id': f'reopened_{i}',
            'conversation_rating': 1 if i < 8 else 4,  # 80% bad CSAT
            'statistics': {'count_reopens': 2}
        })
    
    # First-touch conversations with good CSAT
    for i in range(20):
        conversations.append({
            'id': f'first_touch_{i}',
            'conversation_rating': 4 if i < 18 else 1,  # 90% good CSAT
            'statistics': {'count_reopens': 0}
        })
    
    context = AgentContext(
        conversations=conversations,
        previous_results={
            'SegmentationAgent': {'data': {'tier_distribution': {}}},
            'TopicDetectionAgent': {'data': {'topic_distribution': {}, 'topics_by_conversation': {}}}
        }
    )
    
    result = await correlation_agent.execute(context)
    
    assert result.success
    correlations = result.data.get('correlations', [])
    
    # Should find CSAT × reopens correlation
    csat_corr = next((c for c in correlations if c['type'] == 'csat_reopens'), None)
    assert csat_corr is not None
    assert '80%' in csat_corr['insight'] or '78%' in csat_corr['insight']  # ~80% of reopened have bad CSAT


@pytest.mark.asyncio
async def test_complexity_escalation_correlation(correlation_agent):
    """Test complexity (message count) × escalation correlation"""
    conversations = []
    
    # Escalated conversations with high message count
    for i in range(15):
        conversations.append({
            'id': f'escalated_{i}',
            'admin_assignee_id': f'admin_{i}',
            'statistics': {'count_conversation_parts': 8}
        })
    
    # Fin-only conversations with low message count
    for i in range(15):
        conversations.append({
            'id': f'fin_only_{i}',
            'admin_assignee_id': None,
            'statistics': {'count_conversation_parts': 2}
        })
    
    context = AgentContext(
        conversations=conversations,
        previous_results={
            'SegmentationAgent': {'data': {'tier_distribution': {}}},
            'TopicDetectionAgent': {'data': {'topic_distribution': {}, 'topics_by_conversation': {}}}
        }
    )
    
    result = await correlation_agent.execute(context)
    
    assert result.success
    correlations = result.data.get('correlations', [])
    
    # Should find complexity × escalation correlation
    complexity_corr = next((c for c in correlations if c['type'] == 'complexity_escalation'), None)
    assert complexity_corr is not None
    assert complexity_corr['strength'] > 2.0  # Escalated have ~4x more messages


@pytest.mark.asyncio
async def test_correlation_agent_handles_missing_tier_data(correlation_agent, sample_topic_detection_data):
    """Test agent handles missing tier data gracefully"""
    conversations = [
        {'id': f'conv_{i}', 'tier': None, 'conversation_rating': 3}
        for i in range(20)
    ]
    
    context = AgentContext(
        conversations=conversations,
        previous_results={
            'SegmentationAgent': {'data': {'tier_distribution': {}}},
            'TopicDetectionAgent': {'data': sample_topic_detection_data}
        },
        metadata={'topics_by_conversation': {}}
    )
    
    result = await correlation_agent.execute(context)
    
    assert result.success
    # Should have low confidence due to missing tier data
    assert result.confidence < 0.5
    assert any('tier' in lim.lower() for lim in result.limitations)


@pytest.mark.asyncio
async def test_correlation_agent_handles_missing_csat_data(correlation_agent, sample_conversations_with_tiers, sample_topic_detection_data):
    """Test agent handles insufficient CSAT data"""
    # Remove CSAT ratings from most conversations
    for conv in sample_conversations_with_tiers:
        conv['conversation_rating'] = None
    
    # Keep only 5 with CSAT (insufficient for correlation)
    for i in range(5):
        sample_conversations_with_tiers[i]['conversation_rating'] = 3
    
    context = AgentContext(
        conversations=sample_conversations_with_tiers,
        previous_results={
            'SegmentationAgent': {'data': {'tier_distribution': {}}},
            'TopicDetectionAgent': {'data': sample_topic_detection_data}
        },
        metadata={'topics_by_conversation': sample_topic_detection_data['topics_by_conversation']}
    )
    
    result = await correlation_agent.execute(context)
    
    assert result.success
    correlations = result.data.get('correlations', [])
    
    # CSAT correlation should be skipped or have low confidence
    csat_corrs = [c for c in correlations if c['type'] == 'csat_reopens']
    assert len(csat_corrs) == 0  # Not enough data


@pytest.mark.asyncio
async def test_correlation_agent_output_schema(correlation_agent, agent_context_with_correlations):
    """Test output has required schema"""
    result = await correlation_agent.execute(agent_context_with_correlations)
    
    assert result.success
    assert 'correlations' in result.data
    assert isinstance(result.data['correlations'], list)
    assert 'total_correlations_found' in result.data
    assert isinstance(result.data['total_correlations_found'], int)
    assert 'data_coverage' in result.data
    assert 'tier_coverage' in result.data['data_coverage']
    assert 'csat_coverage' in result.data['data_coverage']


@pytest.mark.asyncio
async def test_correlation_agent_confidence_calculation(correlation_agent, agent_context_with_correlations):
    """Test confidence reflects data coverage"""
    result = await correlation_agent.execute(agent_context_with_correlations)
    
    assert result.success
    
    # Get data coverage
    tier_coverage = result.data['data_coverage']['tier_coverage']
    csat_coverage = result.data['data_coverage']['csat_coverage']
    
    # Confidence should reflect coverage
    expected_confidence = tier_coverage * 0.4 + csat_coverage * 0.3 + result.data['data_coverage']['statistics_coverage'] * 0.3
    assert abs(result.confidence - expected_confidence) < 0.1


@pytest.mark.asyncio
async def test_correlation_agent_empty_conversations(correlation_agent):
    """Test graceful handling of empty conversation list"""
    context = AgentContext(
        conversations=[],
        previous_results={
            'SegmentationAgent': {'data': {}},
            'TopicDetectionAgent': {'data': {}}
        }
    )
    
    result = await correlation_agent.execute(context)
    
    # Should fail validation
    assert not result.success


@pytest.mark.asyncio
async def test_correlation_agent_execution_time(correlation_agent, agent_context_with_correlations):
    """Test execution completes in reasonable time"""
    start = datetime.now()
    result = await correlation_agent.execute(agent_context_with_correlations)
    duration = (datetime.now() - start).total_seconds()
    
    assert result.success
    assert duration < 2.0  # Should complete in <2 seconds


@pytest.mark.asyncio
async def test_correlation_agent_with_llm_enrichment(agent_context_with_correlations):
    """Test LLM enrichment when AI client is provided"""
    # Create agent with mock AI client
    mock_ai_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Test LLM insights"))]
    mock_ai_client.chat.completions.create.return_value = mock_response
    
    agent = CorrelationAgent(ai_client=mock_ai_client)
    
    result = await agent.execute(agent_context_with_correlations)
    
    assert result.success
    # Should have called LLM if correlations were found
    if result.data.get('total_correlations_found', 0) > 0:
        mock_ai_client.chat.completions.create.assert_called_once()



