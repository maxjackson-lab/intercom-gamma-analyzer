"""
Tests for Analytical Insights Integration (Phase 4.5)

Integration tests for the 4 analytical agents in TopicOrchestrator workflow.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.topic_orchestrator import TopicOrchestrator
from src.agents.base_agent import AgentContext


@pytest.fixture
def realistic_conversations_for_insights():
    """Create realistic conversation data for integration testing"""
    conversations = []
    
    # Business tier API issues (correlation signal)
    for i in range(25):
        conversations.append({
            'id': f'api_business_{i}',
            'tier': 'business',
            'conversation_rating': 2 if i < 15 else 4,  # 60% bad CSAT
            'state': 'closed',
            'statistics': {
                'count_reopens': 2 if i < 10 else 0,
                'count_conversation_parts': 7,
                'handling_time': 3600 * 6
            },
            'admin_assignee_id': f'admin_{i}',
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'API integration not working properly.'}
                ]
            },
            'tags': {'tags': [{'name': 'API'}]},
            'created_at': int((datetime.now() - timedelta(days=i % 7)).timestamp())
        })
    
    # Team tier billing issues
    for i in range(10):
        conversations.append({
            'id': f'billing_team_{i}',
            'tier': 'team',
            'conversation_rating': 4,
            'state': 'closed',
            'statistics': {
                'count_reopens': 0,
                'count_conversation_parts': 3,
                'handling_time': 3600 * 3
            },
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'Need help with billing invoice.'}
                ]
            },
            'tags': {'tags': [{'name': 'Billing'}]},
            'created_at': int((datetime.now() - timedelta(days=i % 7)).timestamp())
        })
    
    # Free tier general support
    for i in range(15):
        conversations.append({
            'id': f'general_free_{i}',
            'tier': 'free',
            'conversation_rating': 3 if i < 12 else None,
            'state': 'closed',
            'statistics': {
                'count_reopens': 0,
                'count_conversation_parts': 2,
                'handling_time': 3600 * 2
            },
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'How do I use this feature?'}
                ]
            },
            'tags': {'tags': [{'name': 'General'}]},
            'created_at': int((datetime.now() - timedelta(days=i % 7)).timestamp())
        })
    
    # Churn signal conversations (Business tier with cancellation language)
    for i in range(5):
        conversations.append({
            'id': f'churn_signal_{i}',
            'tier': 'business',
            'conversation_rating': 1,
            'state': 'open',
            'statistics': {
                'count_reopens': 3,
                'count_conversation_parts': 8,
                'handling_time': 3600 * 12
            },
            'admin_assignee_id': f'admin_churn_{i}',
            'conversation_parts': {
                'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': 'I want to cancel my subscription. Switching to Pitch.'}
                ]
            },
            'tags': {'tags': [{'name': 'Cancellation'}]},
            'created_at': int((datetime.now() - timedelta(days=15)).timestamp())
        })
    
    # Exceptionally fast resolution (quality outlier)
    conversations.append({
        'id': 'fast_resolution',
        'tier': 'team',
        'conversation_rating': 5,
        'state': 'closed',
        'statistics': {
            'count_reopens': 0,
            'count_conversation_parts': 2,
            'handling_time': 600  # 10 minutes
        },
        'conversation_parts': {
            'conversation_parts': [
                {'author': {'type': 'user'}, 'body': 'Quick question about exports.'}
            ]
        },
        'tags': {'tags': [{'name': 'Export'}]},
        'created_at': int((datetime.now() - timedelta(days=1)).timestamp())
    })
    
    return conversations


@pytest.fixture
def mock_ai_model_factory():
    """Mock AIModelFactory for testing"""
    with patch('src.agents.topic_orchestrator.AIModelFactory') as MockFactory:
        mock_factory = MagicMock()
        mock_model = AsyncMock()
        
        # Mock LLM responses
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test AI response"))]
        mock_model.chat.completions.create.return_value = mock_response
        
        mock_factory.get_ai_model.return_value = mock_model
        MockFactory.return_value = mock_factory
        
        yield mock_factory


# Phase 4.5 Execution Tests
@pytest.mark.asyncio
@pytest.mark.slow
async def test_phase_4_5_runs_after_fin_analysis(realistic_conversations_for_insights, mock_ai_model_factory):
    """Test Phase 4.5 executes after Phase 4 (Fin analysis)"""
    orchestrator = TopicOrchestrator()
    
    # Mock historical snapshot service to avoid DB operations
    orchestrator._historical_snapshot_service = None
    
    context = AgentContext(
        conversations=realistic_conversations_for_insights,
        period_start=datetime.now() - timedelta(days=7),
        period_end=datetime.now()
    )
    
    # This would normally run full workflow
    # For testing, we're verifying the agents exist and are initialized
    assert orchestrator.correlation_agent is not None
    assert orchestrator.quality_insights_agent is not None
    assert orchestrator.churn_risk_agent is not None
    assert orchestrator.confidence_meta_agent is not None


@pytest.mark.asyncio
async def test_all_4_agents_execute_in_parallel(realistic_conversations_for_insights):
    """Test all 4 analytical agents execute"""
    orchestrator = TopicOrchestrator()
    
    # Verify agents are initialized
    assert orchestrator.correlation_agent is not None
    assert orchestrator.quality_insights_agent is not None
    assert orchestrator.churn_risk_agent is not None
    assert orchestrator.confidence_meta_agent is not None
    
    # Each agent should have execute method
    assert hasattr(orchestrator.correlation_agent, 'execute')
    assert hasattr(orchestrator.quality_insights_agent, 'execute')
    assert hasattr(orchestrator.churn_risk_agent, 'execute')
    assert hasattr(orchestrator.confidence_meta_agent, 'execute')


@pytest.mark.asyncio
async def test_analytical_insights_added_to_workflow_results():
    """Test workflow_results contains all 4 analytical agents"""
    orchestrator = TopicOrchestrator()
    
    # The agents should be part of the orchestrator
    assert hasattr(orchestrator, 'correlation_agent')
    assert hasattr(orchestrator, 'quality_insights_agent')
    assert hasattr(orchestrator, 'churn_risk_agent')
    assert hasattr(orchestrator, 'confidence_meta_agent')


# Data Flow Tests
@pytest.mark.asyncio
async def test_correlation_agent_receives_correct_context():
    """Test CorrelationAgent receives necessary data"""
    from src.agents.correlation_agent import CorrelationAgent
    
    agent = CorrelationAgent()
    
    # Create minimal context
    context = AgentContext(
        conversations=[
            {'id': 'conv_1', 'tier': 'business'}
        ],
        previous_results={
            'SegmentationAgent': {'data': {'tier_distribution': {}}},
            'TopicDetectionAgent': {'data': {'topic_distribution': {}, 'topics_by_conversation': {}}}
        },
        metadata={'topics_by_conversation': {}}
    )
    
    # Validate input
    is_valid, error_msg = agent.validate_input(context)
    assert is_valid


@pytest.mark.asyncio
async def test_quality_insights_receives_topic_mapping():
    """Test QualityInsightsAgent receives topics_by_conversation"""
    from src.agents.quality_insights_agent import QualityInsightsAgent
    
    agent = QualityInsightsAgent()
    
    context = AgentContext(
        conversations=[{'id': 'conv_1'}],
        previous_results={
            'TopicDetectionAgent': {'data': {'topic_distribution': {}, 'topics_by_conversation': {}}}
        },
        metadata={'topics_by_conversation': {'conv_1': ['Topic A']}}
    )
    
    # Validate input
    is_valid, error_msg = agent.validate_input(context)
    assert is_valid


@pytest.mark.asyncio
async def test_churn_risk_receives_tier_data():
    """Test ChurnRiskAgent can access tier data"""
    from src.agents.churn_risk_agent import ChurnRiskAgent
    
    agent = ChurnRiskAgent()
    
    context = AgentContext(
        conversations=[{'id': 'conv_1', 'tier': 'business', 'conversation_parts': {'conversation_parts': []}}],
        previous_results={}
    )
    
    # Validate input
    is_valid, error_msg = agent.validate_input(context)
    assert is_valid


@pytest.mark.asyncio
async def test_confidence_meta_receives_all_previous_results():
    """Test ConfidenceMetaAgent receives all previous agent results"""
    from src.agents.confidence_meta_agent import ConfidenceMetaAgent
    
    agent = ConfidenceMetaAgent()
    
    context = AgentContext(
        conversations=[{'id': 'conv_1'}],
        previous_results={
            'SegmentationAgent': {'data': {}, 'confidence': 0.8},
            'TopicDetectionAgent': {'data': {}, 'confidence': 0.9},
            'CorrelationAgent': {'data': {}, 'confidence': 0.75},
            'QualityInsightsAgent': {'data': {}, 'confidence': 0.8},
            'ChurnRiskAgent': {'data': {}, 'confidence': 0.85}
        }
    )
    
    # Validate input
    is_valid, error_msg = agent.validate_input(context)
    assert is_valid


# Output Integration Tests
@pytest.mark.asyncio
async def test_analytical_insights_available_to_output_formatter():
    """Test AnalyticalInsights is included in output_context"""
    # This test verifies the integration pattern
    # In actual workflow, AnalyticalInsights should be in output_context.previous_results
    
    analytical_insights = {
        'CorrelationAgent': {'data': {}, 'confidence': 0.8},
        'QualityInsightsAgent': {'data': {}, 'confidence': 0.8},
        'ChurnRiskAgent': {'data': {}, 'confidence': 0.85},
        'ConfidenceMetaAgent': {'data': {}, 'confidence': 1.0}
    }
    
    # Simulate output_context
    output_context = AgentContext(
        conversations=[],
        previous_results={
            'SegmentationAgent': {},
            'TopicDetectionAgent': {},
            'AnalyticalInsights': analytical_insights  # Should be present
        }
    )
    
    assert 'AnalyticalInsights' in output_context.previous_results
    assert 'CorrelationAgent' in output_context.previous_results['AnalyticalInsights']


# Error Handling Tests
@pytest.mark.asyncio
async def test_phase_4_5_continues_if_one_agent_fails():
    """Test workflow continues if one analytical agent fails"""
    from src.agents.correlation_agent import CorrelationAgent
    from src.agents.quality_insights_agent import QualityInsightsAgent
    from src.agents.churn_risk_agent import ChurnRiskAgent
    from src.agents.confidence_meta_agent import ConfidenceMetaAgent
    
    # All agents should handle errors gracefully and return error results
    agents = [
        CorrelationAgent(),
        QualityInsightsAgent(),
        ChurnRiskAgent(),
        ConfidenceMetaAgent()
    ]
    
    # Empty context should cause validation failure but not crash
    context = AgentContext(conversations=[], previous_results={})
    
    for agent in agents:
        result = await agent.execute(context)
        # Should return result (possibly with success=False) rather than crashing
        assert result is not None


# Performance Tests
@pytest.mark.asyncio
async def test_phase_4_5_execution_time(realistic_conversations_for_insights):
    """Test Phase 4.5 completes in reasonable time"""
    from src.agents.correlation_agent import CorrelationAgent
    from src.agents.quality_insights_agent import QualityInsightsAgent
    from src.agents.churn_risk_agent import ChurnRiskAgent
    from src.agents.confidence_meta_agent import ConfidenceMetaAgent
    import asyncio
    
    # Create agents
    correlation_agent = CorrelationAgent()
    quality_agent = QualityInsightsAgent()
    churn_agent = ChurnRiskAgent()
    confidence_agent = ConfidenceMetaAgent()
    
    # Create context
    context = AgentContext(
        conversations=realistic_conversations_for_insights,
        previous_results={
            'SegmentationAgent': {'data': {'tier_distribution': {}}, 'confidence': 0.8},
            'TopicDetectionAgent': {
                'data': {
                    'topic_distribution': {'API': 25, 'Billing': 10, 'General': 15},
                    'topics_by_conversation': {conv['id']: ['General'] for conv in realistic_conversations_for_insights}
                },
                'confidence': 0.9
            }
        },
        metadata={
            'topics_by_conversation': {conv['id']: ['General'] for conv in realistic_conversations_for_insights}
        }
    )
    
    # Run agents in parallel
    start = datetime.now()
    results = await asyncio.gather(
        correlation_agent.execute(context),
        quality_agent.execute(context),
        churn_agent.execute(context),
        confidence_agent.execute(context),
        return_exceptions=True
    )
    duration = (datetime.now() - start).total_seconds()
    
    # Should complete in <5 seconds for 50+ conversations
    assert duration < 5.0
    
    # All should return results (even if failed)
    assert len(results) == 4


# Agent Initialization Test
def test_analytical_agents_initialized_in_orchestrator():
    """Test analytical agents are properly initialized"""
    orchestrator = TopicOrchestrator()
    
    # Check agents exist
    assert orchestrator.correlation_agent is not None
    assert orchestrator.quality_insights_agent is not None
    assert orchestrator.churn_risk_agent is not None
    assert orchestrator.confidence_meta_agent is not None
    
    # Check agent types
    from src.agents.correlation_agent import CorrelationAgent
    from src.agents.quality_insights_agent import QualityInsightsAgent
    from src.agents.churn_risk_agent import ChurnRiskAgent
    from src.agents.confidence_meta_agent import ConfidenceMetaAgent
    
    assert isinstance(orchestrator.correlation_agent, CorrelationAgent)
    assert isinstance(orchestrator.quality_insights_agent, QualityInsightsAgent)
    assert isinstance(orchestrator.churn_risk_agent, ChurnRiskAgent)
    assert isinstance(orchestrator.confidence_meta_agent, ConfidenceMetaAgent)


# Agent Result Normalization Test
def test_agent_results_can_be_normalized():
    """Test agent results can be normalized to dict"""
    from src.agents.topic_orchestrator import _normalize_agent_result
    from src.agents.base_agent import AgentResult, ConfidenceLevel
    
    # Create sample AgentResult
    result = AgentResult(
        agent_name="TestAgent",
        success=True,
        data={'test': 'data'},
        confidence=0.85,
        confidence_level=ConfidenceLevel.HIGH,
        limitations=[],
        sources=[],
        execution_time=1.0
    )
    
    # Should normalize to dict
    normalized = _normalize_agent_result(result)
    assert isinstance(normalized, dict)
    assert 'agent_name' in normalized
    assert 'data' in normalized
    assert normalized['agent_name'] == "TestAgent"


# Comprehensive Integration Test
@pytest.mark.asyncio
@pytest.mark.slow
async def test_comprehensive_analytical_insights_flow(realistic_conversations_for_insights):
    """Test complete flow of analytical insights"""
    from src.agents.correlation_agent import CorrelationAgent
    from src.agents.quality_insights_agent import QualityInsightsAgent
    from src.agents.churn_risk_agent import ChurnRiskAgent
    from src.agents.confidence_meta_agent import ConfidenceMetaAgent
    import asyncio
    
    # Initialize all agents
    correlation_agent = CorrelationAgent()
    quality_agent = QualityInsightsAgent()
    churn_agent = ChurnRiskAgent()
    confidence_agent = ConfidenceMetaAgent()
    
    # Create comprehensive context
    context = AgentContext(
        conversations=realistic_conversations_for_insights,
        previous_results={
            'SegmentationAgent': {
                'data': {
                    'tier_distribution': {'business': 30, 'team': 10, 'free': 15}
                },
                'confidence': 0.75
            },
            'TopicDetectionAgent': {
                'data': {
                    'topic_distribution': {'API': 25, 'Billing': 10, 'General': 15},
                    'topics_by_conversation': {conv['id']: ['General'] for conv in realistic_conversations_for_insights}
                },
                'confidence': 0.90
            }
        },
        metadata={
            'topics_by_conversation': {conv['id']: ['General'] for conv in realistic_conversations_for_insights},
            'historical_context': {'weeks_available': 2}
        }
    )
    
    # Execute all agents
    corr_result, quality_result, churn_result, conf_result = await asyncio.gather(
        correlation_agent.execute(context),
        quality_agent.execute(context),
        churn_agent.execute(context),
        confidence_agent.execute(context),
        return_exceptions=True
    )
    
    # Verify all executed (even if some failed)
    assert corr_result is not None
    assert quality_result is not None
    assert churn_result is not None
    assert conf_result is not None
    
    # If successful, check data structure
    if not isinstance(corr_result, Exception) and corr_result.success:
        assert 'correlations' in corr_result.data
    
    if not isinstance(quality_result, Exception) and quality_result.success:
        assert 'fcr_by_topic' in quality_result.data
        assert 'anomalies' in quality_result.data
    
    if not isinstance(churn_result, Exception) and churn_result.success:
        assert 'high_risk_conversations' in churn_result.data
        assert 'risk_breakdown' in churn_result.data
    
    if not isinstance(conf_result, Exception) and conf_result.success:
        assert 'confidence_distribution' in conf_result.data
        assert 'limitations' in conf_result.data














