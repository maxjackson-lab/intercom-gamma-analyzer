"""
Tests for QualityInsightsAgent

Comprehensive test suite for resolution quality and anomaly detection agent.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.agents.quality_insights_agent import QualityInsightsAgent
from src.agents.base_agent import AgentContext, ConfidenceLevel


@pytest.fixture
def sample_conversations_with_quality_metrics():
    """Create conversations with varied FCR, reopens, resolution times, and CSAT"""
    conversations = []
    
    # Billing topic with good FCR (7/10 closed, no reopens)
    for i in range(10):
        conversations.append({
            'id': f'billing_{i}',
            'state': 'closed',
            'conversation_rating': 4 if i < 8 else 2,
            'statistics': {
                'count_reopens': 0 if i < 7 else 1,
                'handling_time': 3600 * 4  # 4 hours
            },
            'created_at': int((datetime.now() - timedelta(days=i % 7)).timestamp())
        })
    
    # API topic with poor FCR (3/10 closed, many reopens)
    for i in range(10):
        conversations.append({
            'id': f'api_{i}',
            'state': 'closed',
            'conversation_rating': 2 if i < 6 else 4,
            'statistics': {
                'count_reopens': 2 if i < 7 else 0,
                'handling_time': 3600 * 12 if i % 3 == 0 else 3600 * 5  # Some very slow
            },
            'created_at': int((datetime.now() - timedelta(days=i % 7)).timestamp())
        })
    
    # Export topic with exceptional cases (one very fast, one very slow)
    for i in range(10):
        handling_time = 3600 * 3  # Default 3 hours
        if i == 0:
            handling_time = 600  # 10 minutes (exceptionally fast)
        elif i == 1:
            handling_time = 3600 * 48  # 48 hours (exceptionally slow)
        
        conversations.append({
            'id': f'export_{i}',
            'state': 'closed',
            'conversation_rating': 5 if i == 0 else (1 if i == 1 else 3),
            'statistics': {
                'count_reopens': 0,
                'handling_time': handling_time
            },
            'created_at': int((datetime.now() - timedelta(days=i % 3)).timestamp())
        })
    
    return conversations


@pytest.fixture
def sample_topic_detection_with_volumes():
    """Mock TopicDetectionAgent output with volume spike"""
    topics_by_conv = {}
    
    # API has 18 conversations (volume spike)
    for i in range(18):
        topics_by_conv[f'api_{i}'] = ['API Issues']
    
    # Billing has 5 conversations (normal)
    for i in range(5):
        topics_by_conv[f'billing_{i}'] = ['Billing']
    
    # Export has 5 conversations (normal)
    for i in range(5):
        topics_by_conv[f'export_{i}'] = ['Export']
    
    return {
        'topic_distribution': {
            'API Issues': 18,  # Spike
            'Billing': 5,
            'Export': 5
        },
        'topics_by_conversation': topics_by_conv
    }


@pytest.fixture
def quality_insights_agent():
    """QualityInsightsAgent instance"""
    return QualityInsightsAgent()


@pytest.fixture
def agent_context_with_quality_data(sample_conversations_with_quality_metrics, sample_topic_detection_with_volumes):
    """AgentContext with quality data"""
    context = AgentContext(
        conversations=sample_conversations_with_quality_metrics,
        previous_results={
            'TopicDetectionAgent': {'data': sample_topic_detection_with_volumes}
        },
        metadata={
            'topics_by_conversation': sample_topic_detection_with_volumes['topics_by_conversation']
        }
    )
    return context


# FCR Calculation Tests
@pytest.mark.asyncio
async def test_fcr_by_topic_calculation(quality_insights_agent, agent_context_with_quality_data):
    """Test FCR calculation by topic"""
    result = await quality_insights_agent.execute(agent_context_with_quality_data)
    
    assert result.success
    fcr_by_topic = result.data.get('fcr_by_topic', {})
    
    # Should have FCR data for topics
    assert len(fcr_by_topic) > 0
    
    # Each topic should have fcr, sample_size, observation
    for topic, data in fcr_by_topic.items():
        assert 'fcr' in data
        assert 'sample_size' in data
        assert 'observation' in data
        assert 0 <= data['fcr'] <= 1


@pytest.mark.asyncio
async def test_fcr_by_topic_adds_observations(quality_insights_agent, agent_context_with_quality_data):
    """Test observations are added based on FCR thresholds"""
    result = await quality_insights_agent.execute(agent_context_with_quality_data)
    
    assert result.success
    fcr_by_topic = result.data.get('fcr_by_topic', {})
    
    for topic, data in fcr_by_topic.items():
        if data['fcr'] > 0.7:
            assert 'healthy' in data['observation'].lower() or 'good' in data['observation'].lower()
        elif data['fcr'] < 0.5:
            assert 'concerning' in data['observation'].lower() or 'issue' in data['observation'].lower()


@pytest.mark.asyncio
async def test_reopen_rates_by_topic(quality_insights_agent):
    """Test reopen rate calculation by topic"""
    conversations = []
    
    # Topic A with high reopen rate
    for i in range(10):
        conversations.append({
            'id': f'topic_a_{i}',
            'statistics': {'count_reopens': 1 if i < 7 else 0}  # 70% reopen rate
        })
    
    topics_by_conv = {f'topic_a_{i}': ['Topic A'] for i in range(10)}
    
    context = AgentContext(
        conversations=conversations,
        previous_results={
            'TopicDetectionAgent': {'data': {'topic_distribution': {'Topic A': 10}, 'topics_by_conversation': topics_by_conv}}
        },
        metadata={'topics_by_conversation': topics_by_conv}
    )
    
    result = await quality_insights_agent.execute(context)
    
    assert result.success
    reopen_patterns = result.data.get('reopen_patterns', {})
    
    assert 'Topic A' in reopen_patterns
    assert reopen_patterns['Topic A']['reopen_rate'] >= 0.6  # ~70%


@pytest.mark.asyncio
async def test_multi_touch_patterns_calculation(quality_insights_agent):
    """Test multi-touch pattern analysis"""
    conversations = []
    
    # Complex topic requiring many touches
    for i in range(10):
        conversations.append({
            'id': f'complex_{i}',
            'statistics': {'count_conversation_parts': 8}
        })
    
    # Simple topic requiring few touches
    for i in range(10):
        conversations.append({
            'id': f'simple_{i}',
            'statistics': {'count_conversation_parts': 2}
        })
    
    topics_by_conv = {
        **{f'complex_{i}': ['Complex Topic'] for i in range(10)},
        **{f'simple_{i}': ['Simple Topic'] for i in range(10)}
    }
    
    context = AgentContext(
        conversations=conversations,
        previous_results={
            'TopicDetectionAgent': {
                'data': {
                    'topic_distribution': {'Complex Topic': 10, 'Simple Topic': 10},
                    'topics_by_conversation': topics_by_conv
                }
            }
        },
        metadata={'topics_by_conversation': topics_by_conv}
    )
    
    result = await quality_insights_agent.execute(context)
    
    assert result.success
    multi_touch = result.data.get('multi_touch_analysis', {})
    
    # Complex topic should have more touches
    if 'Complex Topic' in multi_touch:
        assert multi_touch['Complex Topic']['avg_touches'] > multi_touch.get('Simple Topic', {}).get('avg_touches', 0)


@pytest.mark.asyncio
async def test_resolution_distribution_buckets(quality_insights_agent):
    """Test resolution time distribution calculation"""
    conversations = []
    
    # Various resolution times
    for i in range(30):
        handling_time = 3600 * (i % 60)  # 0-59 hours
        conversations.append({
            'id': f'conv_{i}',
            'statistics': {'handling_time': handling_time}
        })
    
    context = AgentContext(
        conversations=conversations,
        previous_results={
            'TopicDetectionAgent': {'data': {'topic_distribution': {}, 'topics_by_conversation': {}}}
        }
    )
    
    result = await quality_insights_agent.execute(context)
    
    assert result.success
    dist = result.data.get('resolution_distribution', {})
    
    assert 'under_24h' in dist
    assert '24_48h' in dist
    assert 'over_48h' in dist
    assert 'median_hours' in dist
    
    # Should sum to ~1.0
    total = dist['under_24h'] + dist['24_48h'] + dist['over_48h']
    assert 0.9 <= total <= 1.1


# Anomaly Detection Tests
@pytest.mark.asyncio
async def test_volume_anomaly_detection_z_score(quality_insights_agent):
    """Test volume spike detection using Z-score"""
    # API has 18 conversations vs others with 3-5 (clear spike)
    topic_dist = {
        'API Issues': 18,
        'Billing': 4,
        'Export': 3,
        'Sites': 5
    }
    
    context = AgentContext(
        conversations=[{'id': f'conv_{i}'} for i in range(30)],
        previous_results={
            'TopicDetectionAgent': {'data': {'topic_distribution': topic_dist, 'topics_by_conversation': {}}}
        },
        metadata={'topics_by_conversation': {}}
    )
    
    result = await quality_insights_agent.execute(context)
    
    assert result.success
    anomalies = result.data.get('anomalies', [])
    
    # Should detect API volume spike
    volume_anomalies = [a for a in anomalies if a['type'] == 'volume_spike']
    assert len(volume_anomalies) > 0
    
    api_anomaly = next((a for a in volume_anomalies if a['topic'] == 'API Issues'), None)
    assert api_anomaly is not None
    assert api_anomaly['statistical_significance'] > 2.0


@pytest.mark.asyncio
async def test_resolution_time_outliers_iqr(quality_insights_agent):
    """Test resolution time outlier detection using IQR"""
    conversations = []
    
    # Most conversations: 3-5 hours
    for i in range(20):
        conversations.append({
            'id': f'normal_{i}',
            'statistics': {'handling_time': 3600 * (3 + i % 3)}
        })
    
    # One exceptionally fast
    conversations.append({
        'id': 'fast_outlier',
        'statistics': {'handling_time': 480}  # 8 minutes
    })
    
    # One exceptionally slow
    conversations.append({
        'id': 'slow_outlier',
        'statistics': {'handling_time': 3600 * 48}  # 48 hours
    })
    
    context = AgentContext(
        conversations=conversations,
        previous_results={
            'TopicDetectionAgent': {'data': {'topic_distribution': {}, 'topics_by_conversation': {}}}
        }
    )
    
    result = await quality_insights_agent.execute(context)
    
    assert result.success
    exceptional = result.data.get('exceptional_conversations', [])
    
    # Should find both outliers
    assert len(exceptional) >= 2
    
    # Check for fast outlier
    fast = next((e for e in exceptional if e['exceptional_in'] == 'resolution_speed'), None)
    assert fast is not None
    
    # Check for slow outlier
    slow = next((e for e in exceptional if e['exceptional_in'] == 'resolution_delay'), None)
    assert slow is not None


@pytest.mark.asyncio
async def test_csat_outliers_detection(quality_insights_agent):
    """Test CSAT outlier detection"""
    conversations = []
    
    # Most conversations: ~3 stars
    for i in range(20):
        conversations.append({
            'id': f'normal_{i}',
            'conversation_rating': 3
        })
    
    # One exceptional positive (5 stars when median is 3)
    conversations.append({
        'id': 'positive_outlier',
        'conversation_rating': 5
    })
    
    # One exceptional negative (1 star when median is 3)
    conversations.append({
        'id': 'negative_outlier',
        'conversation_rating': 1
    })
    
    context = AgentContext(
        conversations=conversations,
        previous_results={
            'TopicDetectionAgent': {'data': {'topic_distribution': {}, 'topics_by_conversation': {}}}
        }
    )
    
    result = await quality_insights_agent.execute(context)
    
    assert result.success
    exceptional = result.data.get('exceptional_conversations', [])
    
    # Should find CSAT outliers
    csat_outliers = [e for e in exceptional if 'csat' in e['exceptional_in']]
    assert len(csat_outliers) > 0


# Edge Cases
@pytest.mark.asyncio
async def test_quality_insights_handles_missing_statistics(quality_insights_agent):
    """Test graceful handling when statistics fields are missing"""
    conversations = [
        {'id': f'conv_{i}', 'state': 'closed', 'conversation_parts': {'conversation_parts': ['msg1', 'msg2']}}
        for i in range(10)
    ]
    
    context = AgentContext(
        conversations=conversations,
        previous_results={
            'TopicDetectionAgent': {'data': {'topic_distribution': {'General': 10}, 'topics_by_conversation': {f'conv_{i}': ['General'] for i in range(10)}}}
        },
        metadata={'topics_by_conversation': {f'conv_{i}': ['General'] for i in range(10)}}
    )
    
    result = await quality_insights_agent.execute(context)
    
    assert result.success
    # Should use fallback (conversation_parts length)


@pytest.mark.asyncio
async def test_quality_insights_handles_small_sample_sizes(quality_insights_agent):
    """Test topics with <5 conversations are filtered out"""
    conversations = [
        {'id': f'small_topic_{i}', 'state': 'closed', 'statistics': {'count_reopens': 0}}
        for i in range(3)
    ]
    
    topics_by_conv = {f'small_topic_{i}': ['Small Topic'] for i in range(3)}
    
    context = AgentContext(
        conversations=conversations,
        previous_results={
            'TopicDetectionAgent': {'data': {'topic_distribution': {'Small Topic': 3}, 'topics_by_conversation': topics_by_conv}}
        },
        metadata={'topics_by_conversation': topics_by_conv}
    )
    
    result = await quality_insights_agent.execute(context)
    
    assert result.success
    fcr_by_topic = result.data.get('fcr_by_topic', {})
    
    # Small topic should be filtered out
    assert 'Small Topic' not in fcr_by_topic


@pytest.mark.asyncio
async def test_quality_insights_output_schema(quality_insights_agent, agent_context_with_quality_data):
    """Test output has all required fields"""
    result = await quality_insights_agent.execute(agent_context_with_quality_data)
    
    assert result.success
    assert 'fcr_by_topic' in result.data
    assert 'reopen_patterns' in result.data
    assert 'multi_touch_analysis' in result.data
    assert 'resolution_distribution' in result.data
    assert 'anomalies' in result.data
    assert 'exceptional_conversations' in result.data
    assert 'temporal_clustering' in result.data


@pytest.mark.asyncio
async def test_quality_insights_confidence_based_on_coverage(quality_insights_agent, agent_context_with_quality_data):
    """Test confidence reflects data completeness"""
    result = await quality_insights_agent.execute(agent_context_with_quality_data)
    
    assert result.success
    
    # Confidence should be based on statistics coverage and CSAT coverage
    # With good test data, should have reasonable confidence
    assert result.confidence > 0.5


@pytest.mark.asyncio
async def test_quality_insights_execution_time(quality_insights_agent, agent_context_with_quality_data):
    """Test execution completes in reasonable time"""
    start = datetime.now()
    result = await quality_insights_agent.execute(agent_context_with_quality_data)
    duration = (datetime.now() - start).total_seconds()
    
    assert result.success
    assert duration < 3.0  # Should complete in <3 seconds


@pytest.mark.asyncio
async def test_quality_insights_with_llm_enrichment(agent_context_with_quality_data):
    """Test LLM enrichment when AI client is provided"""
    # Create agent with mock AI client
    mock_ai_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Test quality insights"))]
    mock_ai_client.chat.completions.create.return_value = mock_response
    
    agent = QualityInsightsAgent(ai_client=mock_ai_client)
    
    result = await agent.execute(agent_context_with_quality_data)
    
    assert result.success
    # Should have called LLM for enrichment
    assert 'llm_insights' in result.data
    mock_ai_client.chat.completions.create.assert_called_once()






