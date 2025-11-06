"""
Tests for ConfidenceMetaAgent

Comprehensive test suite for meta-analysis and confidence assessment agent.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.agents.confidence_meta_agent import ConfidenceMetaAgent
from src.agents.base_agent import AgentContext, ConfidenceLevel


@pytest.fixture
def sample_previous_results_with_varied_confidence():
    """Mock previous_results with agents having different confidence levels"""
    return {
        'TopicDetectionAgent': {
            'agent_name': 'TopicDetectionAgent',
            'success': True,
            'confidence': 0.91,
            'confidence_level': 'high',
            'limitations': ['Tag-based detection'],
            'data': {'topic_distribution': {}}
        },
        'FinPerformanceAgent': {
            'agent_name': 'FinPerformanceAgent',
            'success': True,
            'confidence': 0.88,
            'confidence_level': 'high',
            'limitations': ['Clear signals from admin assignments'],
            'data': {}
        },
        'TrendAgent': {
            'agent_name': 'TrendAgent',
            'success': True,
            'confidence': 0.65,
            'confidence_level': 'medium',
            'limitations': ['Only 2 weeks of historical data'],
            'data': {}
        },
        'SegmentationAgent': {
            'agent_name': 'SegmentationAgent',
            'success': True,
            'confidence': 0.54,
            'confidence_level': 'low',
            'limitations': ['42% conversations defaulted to FREE tier'],
            'data': {'tier_distribution': {}}
        }
    }


@pytest.fixture
def sample_conversations_with_data_gaps():
    """Create conversations with various data gaps"""
    conversations = []
    
    # 58% with tier data (42% missing)
    for i in range(100):
        conversations.append({
            'id': f'conv_{i}',
            'tier': 'business' if i < 58 else None,
            'conversation_rating': 4 if i < 18 else None,  # 18% CSAT coverage
            'conversation_parts': {'conversation_parts': ['msg1', 'msg2']} if i < 95 else None,  # 95% coverage
            'statistics': {
                'count_reopens': 0 if i < 82 else None,
                'handling_time': 3600 if i < 82 else None
            } if i < 82 else {}  # 82% statistics coverage
        })
    
    return conversations


@pytest.fixture
def confidence_meta_agent():
    """ConfidenceMetaAgent instance"""
    return ConfidenceMetaAgent()


@pytest.fixture
def agent_context_with_meta_data(sample_conversations_with_data_gaps, sample_previous_results_with_varied_confidence):
    """AgentContext with meta-analysis data"""
    context = AgentContext(
        conversations=sample_conversations_with_data_gaps,
        previous_results=sample_previous_results_with_varied_confidence,
        metadata={
            'historical_context': {
                'weeks_available': 2,
                'can_do_trends': True,
                'can_do_seasonality': False
            }
        }
    )
    return context


# Confidence Distribution Tests
@pytest.mark.asyncio
async def test_confidence_distribution_categorization(confidence_meta_agent, agent_context_with_meta_data):
    """Test confidence levels are categorized correctly"""
    result = await confidence_meta_agent.execute(agent_context_with_meta_data)
    
    assert result.success
    dist = result.data.get('confidence_distribution', {})
    
    assert 'high_confidence_insights' in dist
    assert 'medium_confidence_insights' in dist
    assert 'low_confidence_insights' in dist
    
    # Check categorization
    high_conf = dist['high_confidence_insights']
    medium_conf = dist['medium_confidence_insights']
    low_conf = dist['low_confidence_insights']
    
    # TopicDetectionAgent (0.91) and FinPerformanceAgent (0.88) should be high
    assert len(high_conf) >= 2
    
    # TrendAgent (0.65) should be medium
    assert len(medium_conf) >= 1
    
    # SegmentationAgent (0.54) should be low
    assert len(low_conf) >= 1


@pytest.mark.asyncio
async def test_confidence_distribution_extracts_reasons(confidence_meta_agent, agent_context_with_meta_data):
    """Test reasons are extracted from agent limitations"""
    result = await confidence_meta_agent.execute(agent_context_with_meta_data)
    
    assert result.success
    dist = result.data.get('confidence_distribution', {})
    
    # Check that reasons are present
    all_insights = (
        dist['high_confidence_insights'] +
        dist['medium_confidence_insights'] +
        dist['low_confidence_insights']
    )
    
    for insight in all_insights:
        assert 'agent' in insight
        assert 'confidence' in insight
        assert 'reason' in insight


@pytest.mark.asyncio
async def test_confidence_distribution_handles_missing_confidence(confidence_meta_agent):
    """Test handling of agent results without confidence field"""
    previous_results = {
        'MalformedAgent': {
            'agent_name': 'MalformedAgent',
            'success': True,
            # Missing confidence field
            'data': {}
        }
    }
    
    context = AgentContext(
        conversations=[],
        previous_results=previous_results
    )
    
    result = await confidence_meta_agent.execute(context)
    
    # Should handle gracefully
    assert result.success


# Data Quality Assessment Tests
@pytest.mark.asyncio
async def test_tier_coverage_calculation(confidence_meta_agent, agent_context_with_meta_data):
    """Test tier coverage is calculated correctly"""
    result = await confidence_meta_agent.execute(agent_context_with_meta_data)
    
    assert result.success
    data_quality = result.data.get('data_quality', {})
    
    assert 'tier_coverage' in data_quality
    # 58 out of 100 conversations have tier data
    assert 0.57 <= data_quality['tier_coverage'] <= 0.59


@pytest.mark.asyncio
async def test_csat_coverage_calculation(confidence_meta_agent, agent_context_with_meta_data):
    """Test CSAT coverage is calculated correctly"""
    result = await confidence_meta_agent.execute(agent_context_with_meta_data)
    
    assert result.success
    data_quality = result.data.get('data_quality', {})
    
    assert 'csat_coverage' in data_quality
    # 18 out of 100 conversations have CSAT
    assert 0.17 <= data_quality['csat_coverage'] <= 0.19


@pytest.mark.asyncio
async def test_conversation_parts_coverage_calculation(confidence_meta_agent, agent_context_with_meta_data):
    """Test conversation_parts coverage is calculated correctly"""
    result = await confidence_meta_agent.execute(agent_context_with_meta_data)
    
    assert result.success
    data_quality = result.data.get('data_quality', {})
    
    assert 'conversation_parts_coverage' in data_quality
    # 95 out of 100 conversations have conversation_parts
    assert 0.94 <= data_quality['conversation_parts_coverage'] <= 0.96


@pytest.mark.asyncio
async def test_statistics_coverage_calculation(confidence_meta_agent, agent_context_with_meta_data):
    """Test statistics coverage is calculated correctly"""
    result = await confidence_meta_agent.execute(agent_context_with_meta_data)
    
    assert result.success
    data_quality = result.data.get('data_quality', {})
    
    assert 'statistics_coverage' in data_quality
    # 82 out of 100 conversations have statistics
    assert 0.81 <= data_quality['statistics_coverage'] <= 0.83


@pytest.mark.asyncio
async def test_data_quality_impact_assessment(confidence_meta_agent, agent_context_with_meta_data):
    """Test impact message is generated based on coverage gaps"""
    result = await confidence_meta_agent.execute(agent_context_with_meta_data)
    
    assert result.success
    data_quality = result.data.get('data_quality', {})
    
    assert 'impact' in data_quality
    # With low tier and CSAT coverage, should mention limitations
    impact = data_quality['impact'].lower()
    assert 'tier' in impact or 'sentiment' in impact or 'csat' in impact


# Limitations Identification Tests
@pytest.mark.asyncio
async def test_identifies_no_historical_baseline_limitation(confidence_meta_agent):
    """Test identification of no historical baseline"""
    conversations = [{'id': 'conv_1', 'tier': 'business'}]
    previous_results = {
        'SegmentationAgent': {'data': {}, 'confidence': 0.8},
        'TopicDetectionAgent': {'data': {}, 'confidence': 0.8}
    }
    
    context = AgentContext(
        conversations=conversations,
        previous_results=previous_results,
        metadata={'historical_context': {'weeks_available': 0}}
    )
    
    result = await confidence_meta_agent.execute(context)
    
    assert result.success
    limitations = result.data.get('limitations', [])
    
    assert any('historical baseline' in lim.lower() for lim in limitations)


@pytest.mark.asyncio
async def test_identifies_incomplete_tier_data_limitation(confidence_meta_agent, agent_context_with_meta_data):
    """Test identification of incomplete tier data"""
    result = await confidence_meta_agent.execute(agent_context_with_meta_data)
    
    assert result.success
    limitations = result.data.get('limitations', [])
    
    # 42% missing tier data, should be flagged
    assert any('tier' in lim.lower() for lim in limitations)


@pytest.mark.asyncio
async def test_identifies_low_csat_coverage_limitation(confidence_meta_agent, agent_context_with_meta_data):
    """Test identification of low CSAT coverage"""
    result = await confidence_meta_agent.execute(agent_context_with_meta_data)
    
    assert result.success
    limitations = result.data.get('limitations', [])
    
    # 18% CSAT coverage, should be flagged
    assert any('csat' in lim.lower() for lim in limitations)


@pytest.mark.asyncio
async def test_identifies_small_sample_size_limitations(confidence_meta_agent):
    """Test identification of small sample sizes"""
    conversations = [{'id': f'conv_{i}'} for i in range(20)]
    previous_results = {
        'SegmentationAgent': {'data': {}, 'confidence': 0.8},
        'TopicDetectionAgent': {
            'data': {
                'topic_distribution': {
                    'Small Topic': 3,  # <10 conversations
                    'Another Small': 5
                }
            },
            'confidence': 0.8
        }
    }
    
    context = AgentContext(
        conversations=conversations,
        previous_results=previous_results
    )
    
    result = await confidence_meta_agent.execute(context)
    
    assert result.success
    limitations = result.data.get('limitations', [])
    
    assert any('statistical significance' in lim.lower() for lim in limitations)


# Improvement Suggestions Tests
@pytest.mark.asyncio
async def test_suggests_stripe_tier_completion(confidence_meta_agent, agent_context_with_meta_data):
    """Test suggestion for completing Stripe tier data"""
    result = await confidence_meta_agent.execute(agent_context_with_meta_data)
    
    assert result.success
    suggestions = result.data.get('what_would_improve_confidence', [])
    
    # Low tier coverage should trigger Stripe suggestion
    assert any('stripe' in sug.lower() and 'tier' in sug.lower() for sug in suggestions)


@pytest.mark.asyncio
async def test_suggests_historical_data_collection(confidence_meta_agent):
    """Test suggestion for historical data collection"""
    conversations = [{'id': 'conv_1'}]
    previous_results = {
        'SegmentationAgent': {'data': {}, 'confidence': 0.8},
        'TopicDetectionAgent': {'data': {}, 'confidence': 0.8}
    }
    
    context = AgentContext(
        conversations=conversations,
        previous_results=previous_results,
        metadata={'historical_context': {'weeks_available': 0}}
    )
    
    result = await confidence_meta_agent.execute(context)
    
    assert result.success
    suggestions = result.data.get('what_would_improve_confidence', [])
    
    assert any('historical' in sug.lower() for sug in suggestions)


@pytest.mark.asyncio
async def test_suggests_csat_response_rate_improvement(confidence_meta_agent, agent_context_with_meta_data):
    """Test suggestion for improving CSAT response rate"""
    result = await confidence_meta_agent.execute(agent_context_with_meta_data)
    
    assert result.success
    suggestions = result.data.get('what_would_improve_confidence', [])
    
    # Low CSAT coverage should trigger suggestion
    assert any('csat' in sug.lower() for sug in suggestions)


@pytest.mark.asyncio
async def test_improvement_suggestions_limited_to_top_5(confidence_meta_agent):
    """Test improvement suggestions are limited to top 5"""
    # Create context with many data gaps
    conversations = [{'id': f'conv_{i}'} for i in range(100)]
    
    context = AgentContext(
        conversations=conversations,
        previous_results={
            'SegmentationAgent': {'data': {}, 'confidence': 0.3},
            'TopicDetectionAgent': {'data': {'topic_distribution': {}}, 'confidence': 0.3}
        },
        metadata={'historical_context': {'weeks_available': 0}}
    )
    
    result = await confidence_meta_agent.execute(context)
    
    assert result.success
    suggestions = result.data.get('what_would_improve_confidence', [])
    
    # Should be limited to top 5
    assert len(suggestions) <= 5


# Edge Cases
@pytest.mark.asyncio
async def test_confidence_meta_handles_empty_previous_results(confidence_meta_agent):
    """Test graceful handling of empty previous_results"""
    context = AgentContext(
        conversations=[{'id': 'conv_1'}],
        previous_results={}
    )
    
    result = await confidence_meta_agent.execute(context)
    
    # Should fail validation
    assert not result.success


@pytest.mark.asyncio
async def test_confidence_meta_handles_malformed_agent_results(confidence_meta_agent):
    """Test graceful handling of malformed agent results"""
    previous_results = {
        'GoodAgent': {'data': {}, 'confidence': 0.8},
        'MalformedAgent': 'not a dict',  # Malformed
        'IncompleteAgent': {'data': {}}  # Missing confidence
    }
    
    context = AgentContext(
        conversations=[{'id': 'conv_1'}],
        previous_results=previous_results
    )
    
    result = await confidence_meta_agent.execute(context)
    
    # Should handle gracefully
    assert result.success


@pytest.mark.asyncio
async def test_confidence_meta_output_schema(confidence_meta_agent, agent_context_with_meta_data):
    """Test output has all required fields"""
    result = await confidence_meta_agent.execute(agent_context_with_meta_data)
    
    assert result.success
    assert 'confidence_distribution' in result.data
    assert 'data_quality' in result.data
    assert 'limitations' in result.data
    assert 'what_would_improve_confidence' in result.data
    assert 'overall_data_quality_score' in result.data


@pytest.mark.asyncio
async def test_confidence_meta_always_high_confidence(confidence_meta_agent, agent_context_with_meta_data):
    """Test ConfidenceMetaAgent is always confident about its assessment"""
    result = await confidence_meta_agent.execute(agent_context_with_meta_data)
    
    assert result.success
    # Meta-agent should always have high confidence (self-aware)
    assert result.confidence == 1.0
    assert result.confidence_level == ConfidenceLevel.HIGH


@pytest.mark.asyncio
async def test_confidence_meta_with_full_workflow_results(confidence_meta_agent):
    """Test with realistic full workflow results"""
    conversations = [{'id': f'conv_{i}', 'tier': 'business', 'conversation_rating': 4} for i in range(50)]
    
    # Simulate full workflow results
    previous_results = {
        'SegmentationAgent': {'data': {}, 'confidence': 0.85, 'limitations': []},
        'TopicDetectionAgent': {'data': {'topic_distribution': {}}, 'confidence': 0.90, 'limitations': []},
        'TopicSentiments': {},
        'TopicExamples': {},
        'FinPerformanceAgent': {'data': {}, 'confidence': 0.88, 'limitations': []},
        'TrendAgent': {'data': {}, 'confidence': 0.70, 'limitations': ['Limited historical data']},
        'CorrelationAgent': {'data': {}, 'confidence': 0.75, 'limitations': []},
        'QualityInsightsAgent': {'data': {}, 'confidence': 0.80, 'limitations': []},
        'ChurnRiskAgent': {'data': {}, 'confidence': 0.82, 'limitations': []},
    }
    
    context = AgentContext(
        conversations=conversations,
        previous_results=previous_results,
        metadata={'historical_context': {'weeks_available': 4}}
    )
    
    result = await confidence_meta_agent.execute(context)
    
    assert result.success
    # Should provide comprehensive meta-analysis
    dist = result.data.get('confidence_distribution', {})
    assert len(dist['high_confidence_insights']) >= 3


@pytest.mark.asyncio
async def test_confidence_meta_execution_time(confidence_meta_agent, agent_context_with_meta_data):
    """Test execution completes quickly"""
    start = datetime.now()
    result = await confidence_meta_agent.execute(agent_context_with_meta_data)
    duration = (datetime.now() - start).total_seconds()
    
    assert result.success
    assert duration < 1.0  # Should complete in <1 second


@pytest.mark.asyncio
async def test_confidence_meta_with_llm_insights(agent_context_with_meta_data):
    """Test LLM meta-analysis when AI client is provided"""
    # Create agent with mock AI client
    mock_ai_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Test meta-analysis insights"))]
    mock_ai_client.chat.completions.create.return_value = mock_response
    
    agent = ConfidenceMetaAgent(ai_client=mock_ai_client)
    
    result = await agent.execute(agent_context_with_meta_data)
    
    assert result.success
    assert 'llm_meta_analysis' in result.data
    mock_ai_client.chat.completions.create.assert_called_once()



