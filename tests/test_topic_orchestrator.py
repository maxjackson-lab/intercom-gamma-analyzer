"""
Comprehensive integration tests for TopicOrchestrator with SubTopicDetectionAgent.

Tests the complete multi-agent workflow including the new Phase 2.5 (Sub-Topic Detection).
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from typing import Dict, Any, List

from src.agents.topic_orchestrator import TopicOrchestrator
from src.agents.base_agent import AgentContext, AgentResult, ConfidenceLevel


@pytest.fixture
def orchestrator():
    """Return TopicOrchestrator instance."""
    return TopicOrchestrator()


@pytest.fixture
def sample_paid_conversations_with_subtopic_data():
    """
    Create 50+ paid conversations with sub-topic indicators.
    
    Includes:
    - Mix of topics (Billing, Account, Product) in detected_topics
    - Tier 2 indicators: tags, custom_attributes, conversation_topics
    - Tier 3 indicators: keywords in full_text for LLM discovery
    - Mix of Finn and human conversations
    - Some with conversation_rating
    - customer_messages array (required by orchestrator)
    """
    conversations = []
    topics = ['Billing Issues', 'Account Issues', 'Product Questions']
    
    for i in range(55):
        topic = topics[i % len(topics)]
        is_finn = i % 3 == 0
        
        conv = {
            'id': f'paid_conv_{i}',
            'created_at': 1699123456 + (i * 3600),
            'updated_at': 1699123456 + (i * 3600) + 1800,
            'state': 'closed',
            'admin_assignee_id': f'admin_{i}',
            'ai_agent_participated': is_finn,
            'conversation_rating': (i % 5) + 1 if i % 4 == 0 else None,
            'detected_topics': [topic],
            'full_text': f'Customer inquiry about {topic.lower()} with additional context.',
            'customer_messages': [f'Message about {topic.lower()} {i}'],
            'tags': {'tags': []},
            'conversation_topics': [],
            'custom_attributes': {'Language': 'en'}
        }
        
        # Add Tier 2 indicators based on topic
        if topic == 'Billing Issues':
            if i % 2 == 0:
                conv['tags']['tags'].append({'name': 'Refund'})
                conv['conversation_topics'].append({'name': 'Refund'})
                conv['full_text'] += ' Need refund processing help.'
            else:
                conv['tags']['tags'].append({'name': 'Invoice'})
                conv['conversation_topics'].append({'name': 'Invoice'})
                conv['full_text'] += ' Invoice discrepancy found.'
            conv['custom_attributes']['billing_type'] = 'annual' if i % 4 == 0 else 'monthly'
        elif topic == 'Account Issues':
            conv['tags']['tags'].append({'name': 'Login'})
            conv['conversation_topics'].append({'name': 'Login'})
            conv['custom_attributes']['account_type'] = 'premium' if i % 3 == 0 else 'free'
            conv['full_text'] += ' Login failure occurred.'
        else:  # Product Questions
            conv['tags']['tags'].append({'name': 'Feature'})
            conv['conversation_topics'].append({'name': 'Feature'})
            conv['custom_attributes']['product_version'] = 'v2' if i % 5 == 0 else 'v1'
            conv['full_text'] += ' Feature request submitted.'
        
        conversations.append(conv)
    
    return conversations


@pytest.fixture
def sample_free_conversations():
    """Create 20+ free tier conversations with Finn participation."""
    conversations = []
    
    for i in range(25):
        conv = {
            'id': f'free_conv_{i}',
            'created_at': 1699123456 + (i * 3600),
            'updated_at': 1699123456 + (i * 3600) + 900,
            'state': 'closed',
            'admin_assignee_id': 'admin_finn',
            'ai_agent_participated': True,
            'conversation_rating': None,
            'detected_topics': ['Product Questions'],
            'full_text': f'Free tier inquiry {i}',
            'customer_messages': [f'Free tier message {i}'],
            'tags': {'tags': [{'name': 'support'}]},
            'conversation_topics': [],
            'custom_attributes': {'Language': 'en', 'tier': 'free'}
        }
        conversations.append(conv)
    
    return conversations


@pytest.fixture
def all_conversations(sample_paid_conversations_with_subtopic_data, sample_free_conversations):
    """Combine paid and free conversations."""
    return sample_paid_conversations_with_subtopic_data + sample_free_conversations


@pytest.fixture
def mock_week_params():
    """Return dict with week parameters."""
    return {
        'week_id': '2024-W42',
        'start_date': datetime(2024, 10, 14, tzinfo=timezone.utc),
        'end_date': datetime(2024, 10, 20, tzinfo=timezone.utc),
        'period_type': 'week',
        'period_label': 'Week of Oct 14-20, 2024'
    }


# Test Cases

def test_orchestrator_initialization(orchestrator):
    """Verify all agents are initialized including subtopic_detection_agent."""
    assert orchestrator.segmentation_agent is not None
    assert orchestrator.topic_detection_agent is not None
    assert orchestrator.subtopic_detection_agent is not None
    assert orchestrator.topic_sentiment_agent is not None
    assert orchestrator.example_extraction_agent is not None
    assert orchestrator.fin_performance_agent is not None
    assert orchestrator.trend_agent is not None
    assert orchestrator.output_formatter_agent is not None
    assert orchestrator.logger is not None


@pytest.mark.asyncio
async def test_execute_weekly_analysis_with_subtopics(
    orchestrator, 
    all_conversations, 
    mock_week_params
):
    """
    Test full workflow execution with SubTopicDetectionAgent integration.
    
    Verifies:
    - SubTopicDetectionAgent is called with correct context
    - Result is added to workflow_results
    - Result is passed to OutputFormatterAgent
    - Final output contains sub-topic data
    - FinPerformanceAgent receives sub-topic data in previous_results and metadata
    """
    # Mock all agents
    with patch.object(orchestrator.segmentation_agent, 'execute', new_callable=AsyncMock) as mock_seg, \
         patch.object(orchestrator.topic_detection_agent, 'execute', new_callable=AsyncMock) as mock_topic, \
         patch.object(orchestrator.subtopic_detection_agent, 'execute', new_callable=AsyncMock) as mock_subtopic, \
         patch.object(orchestrator.topic_sentiment_agent, 'execute', new_callable=AsyncMock) as mock_sentiment, \
         patch.object(orchestrator.example_extraction_agent, 'execute', new_callable=AsyncMock) as mock_examples, \
         patch.object(orchestrator.fin_performance_agent, 'execute', new_callable=AsyncMock) as mock_fin, \
         patch.object(orchestrator.trend_agent, 'execute', new_callable=AsyncMock) as mock_trend, \
         patch.object(orchestrator.output_formatter_agent, 'execute', new_callable=AsyncMock) as mock_formatter, \
         patch('src.agents.topic_orchestrator.get_display') as mock_display:
        
        # Setup mock returns
        mock_seg.return_value = AgentResult(
            agent_name='SegmentationAgent',
            success=True,
            confidence=1.0,
            confidence_level=ConfidenceLevel.HIGH,
            data={
                'paid_customer_conversations': all_conversations[:55],
                'free_fin_only_conversations': all_conversations[55:],
                'paid_fin_resolved_conversations': all_conversations[:18]
            }
        )
        
        mock_topic.return_value = AgentResult(
            agent_name='TopicDetectionAgent',
            success=True,
            confidence=0.95,
            confidence_level=ConfidenceLevel.HIGH,
            data={
                'topic_distribution': {
                    'Billing Issues': {'volume': 20, 'percentage': 36.4},
                    'Account Issues': {'volume': 18, 'percentage': 32.7},
                    'Product Questions': {'volume': 17, 'percentage': 30.9}
                },
                'topics_by_conversation': {}
            }
        )
        
        mock_subtopic.return_value = AgentResult(
            agent_name='SubTopicDetectionAgent',
            success=True,
            confidence=0.90,
            confidence_level=ConfidenceLevel.HIGH,
            data={
                'subtopics_by_tier1_topic': {
                    'Billing Issues': {
                        'tier2': {
                            'Refund': {'volume': 10, 'percentage': 50.0, 'source': 'tags'},
                            'Invoice': {'volume': 10, 'percentage': 50.0, 'source': 'tags'}
                        },
                        'tier3': {
                            'Refund Processing Delays': {'keywords': ['refund', 'delay'], 'method': 'llm_semantic'}
                        }
                    },
                    'Account Issues': {
                        'tier2': {
                            'Login': {'volume': 18, 'percentage': 100.0, 'source': 'tags'}
                        },
                        'tier3': {}
                    },
                    'Product Questions': {
                        'tier2': {
                            'Feature': {'volume': 17, 'percentage': 100.0, 'source': 'tags'}
                        },
                        'tier3': {}
                    }
                }
            }
        )
        
        mock_sentiment.return_value = AgentResult(
            agent_name='TopicSentimentAgent',
            success=True,
            confidence=0.85,
            confidence_level=ConfidenceLevel.HIGH,
            data={'sentiment_insight': 'Customers frustrated with issues.'}
        )
        
        mock_examples.return_value = AgentResult(
            agent_name='ExampleExtractionAgent',
            success=True,
            confidence=0.90,
            confidence_level=ConfidenceLevel.HIGH,
            data={'examples': [{'preview': 'Example 1', 'intercom_url': 'https://test.com/1'}]}
        )
        
        mock_fin.return_value = AgentResult(
            agent_name='FinPerformanceAgent',
            success=True,
            confidence=0.92,
            confidence_level=ConfidenceLevel.HIGH,
            data={
                'total_fin_conversations': 43,
                'free_tier': {'total_conversations': 25, 'resolution_rate': 0.7},
                'paid_tier': {'total_conversations': 18, 'resolution_rate': 0.8}
            }
        )
        
        mock_trend.return_value = AgentResult(
            agent_name='TrendAgent',
            success=True,
            confidence=0.88,
            confidence_level=ConfidenceLevel.HIGH,
            data={'trends': {}, 'trend_insights': {}}
        )
        
        mock_formatter.return_value = AgentResult(
            agent_name='OutputFormatterAgent',
            success=True,
            confidence=1.0,
            confidence_level=ConfidenceLevel.HIGH,
            data={'formatted_output': '# Weekly Report\n\nAnalysis complete.'}
        )
        
        # Mock display
        mock_display.return_value = MagicMock()
        
        # Execute workflow
        result = await orchestrator.execute_weekly_analysis(
            conversations=all_conversations,
            **mock_week_params
        )
        
        # Verify SubTopicDetectionAgent was called
        assert mock_subtopic.called
        
        # Verify context passed to SubTopicDetectionAgent
        subtopic_call_context = mock_subtopic.call_args[0][0]
        assert 'TopicDetectionAgent' in subtopic_call_context.previous_results
        assert len(subtopic_call_context.conversations) == 55  # Paid conversations only
        
        # Verify SubTopicDetectionAgent result in workflow_results
        assert 'SubTopicDetectionAgent' in result['agent_results']
        assert result['agent_results']['SubTopicDetectionAgent']['success'] is True
        
        # Verify OutputFormatterAgent received SubTopicDetectionAgent result
        formatter_call_context = mock_formatter.call_args[0][0]
        assert 'SubTopicDetectionAgent' in formatter_call_context.previous_results
        
        # Verify FinPerformanceAgent received sub-topic data (Comment 4)
        fin_call_context = mock_fin.call_args[0][0]
        assert 'SubTopicDetectionAgent' in fin_call_context.previous_results
        assert 'TopicDetectionAgent' in fin_call_context.previous_results
        # Verify metadata also contains subtopics
        assert 'subtopics_by_tier1_topic' in fin_call_context.metadata
        expected_subtopics = {
            'Billing Issues': {
                'tier2': {
                    'Refund': {'volume': 10, 'percentage': 50.0, 'source': 'tags'},
                    'Invoice': {'volume': 10, 'percentage': 50.0, 'source': 'tags'}
                },
                'tier3': {
                    'Refund Processing Delays': {'keywords': ['refund', 'delay'], 'method': 'llm_semantic'}
                }
            },
            'Account Issues': {
                'tier2': {
                    'Login': {'volume': 18, 'percentage': 100.0, 'source': 'tags'}
                },
                'tier3': {}
            },
            'Product Questions': {
                'tier2': {
                    'Feature': {'volume': 17, 'percentage': 100.0, 'source': 'tags'}
                },
                'tier3': {}
            }
        }
        assert fin_call_context.metadata['subtopics_by_tier1_topic'] == expected_subtopics
        
        # Verify final output contains sub-topic data
        assert 'subtopics_analyzed' in result['summary']
        assert result['summary']['subtopics_analyzed'] == 3  # 3 Tier 1 topics


@pytest.mark.asyncio
async def test_subtopic_phase_ordering(orchestrator, all_conversations, mock_week_params):
    """Verify Phase 2.5 runs after Phase 2 and before Phase 3."""
    call_order = []
    
    async def track_call(agent_name):
        async def mock_execute(context):
            call_order.append(agent_name)
            return AgentResult(
                agent_name=agent_name,
                success=True,
                confidence=0.9,
                confidence_level=ConfidenceLevel.HIGH,
                data={
                    'topic_distribution': {} if agent_name == 'TopicDetectionAgent' else {},
                    'subtopics_by_tier1_topic': {} if agent_name == 'SubTopicDetectionAgent' else {},
                    'paid_customer_conversations': all_conversations[:55] if agent_name == 'SegmentationAgent' else [],
                    'free_fin_only_conversations': all_conversations[55:] if agent_name == 'SegmentationAgent' else [],
                    'paid_fin_resolved_conversations': [] if agent_name == 'SegmentationAgent' else [],
                    'topics_by_conversation': {} if agent_name == 'TopicDetectionAgent' else {},
                    'examples': [],
                    'formatted_output': ''
                }
            )
        return mock_execute
    
    with patch.object(orchestrator.segmentation_agent, 'execute', track_call('SegmentationAgent')), \
         patch.object(orchestrator.topic_detection_agent, 'execute', track_call('TopicDetectionAgent')), \
         patch.object(orchestrator.subtopic_detection_agent, 'execute', track_call('SubTopicDetectionAgent')), \
         patch.object(orchestrator.topic_sentiment_agent, 'execute', track_call('TopicSentimentAgent')), \
         patch.object(orchestrator.example_extraction_agent, 'execute', track_call('ExampleExtractionAgent')), \
         patch.object(orchestrator.fin_performance_agent, 'execute', track_call('FinPerformanceAgent')), \
         patch.object(orchestrator.trend_agent, 'execute', track_call('TrendAgent')), \
         patch.object(orchestrator.output_formatter_agent, 'execute', track_call('OutputFormatterAgent')), \
         patch('src.agents.topic_orchestrator.get_display'):
        
        await orchestrator.execute_weekly_analysis(
            conversations=all_conversations,
            **mock_week_params
        )
        
        # Verify ordering
        seg_index = call_order.index('SegmentationAgent')
        topic_index = call_order.index('TopicDetectionAgent')
        subtopic_index = call_order.index('SubTopicDetectionAgent')
        
        assert seg_index < topic_index < subtopic_index


@pytest.mark.asyncio
async def test_subtopic_context_construction(orchestrator, all_conversations, mock_week_params):
    """Verify context passed to SubTopicDetectionAgent contains required data."""
    subtopic_context_captured = None
    
    async def capture_context(context):
        nonlocal subtopic_context_captured
        subtopic_context_captured = context
        return AgentResult(
            agent_name='SubTopicDetectionAgent',
            success=True,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
            data={'subtopics_by_tier1_topic': {}}
        )
    
    with patch.object(orchestrator.segmentation_agent, 'execute', new_callable=AsyncMock) as mock_seg, \
         patch.object(orchestrator.topic_detection_agent, 'execute', new_callable=AsyncMock) as mock_topic, \
         patch.object(orchestrator.subtopic_detection_agent, 'execute', capture_context), \
         patch.object(orchestrator.topic_sentiment_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.example_extraction_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.fin_performance_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.trend_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.output_formatter_agent, 'execute', new_callable=AsyncMock), \
         patch('src.agents.topic_orchestrator.get_display'):
        
        mock_seg.return_value = AgentResult(
            agent_name='SegmentationAgent',
            success=True,
            confidence=1.0,
            confidence_level=ConfidenceLevel.HIGH,
            data={
                'paid_customer_conversations': all_conversations[:55],
                'free_fin_only_conversations': all_conversations[55:],
                'paid_fin_resolved_conversations': []
            }
        )
        
        mock_topic.return_value = AgentResult(
            agent_name='TopicDetectionAgent',
            success=True,
            confidence=0.95,
            confidence_level=ConfidenceLevel.HIGH,
            data={
                'topic_distribution': {'Billing Issues': {'volume': 20}},
                'topics_by_conversation': {}
            }
        )
        
        await orchestrator.execute_weekly_analysis(
            conversations=all_conversations,
            **mock_week_params
        )
        
        # Verify captured context
        assert subtopic_context_captured is not None
        assert 'TopicDetectionAgent' in subtopic_context_captured.previous_results
        assert len(subtopic_context_captured.conversations) == 55
        assert subtopic_context_captured.start_date == mock_week_params['start_date']
        assert subtopic_context_captured.end_date == mock_week_params['end_date']


@pytest.mark.asyncio
async def test_subtopic_results_flow_to_output_formatter(
    orchestrator, 
    all_conversations, 
    mock_week_params
):
    """Verify SubTopicDetectionAgent results appear in output_context.previous_results."""
    formatter_context_captured = None
    
    async def capture_formatter_context(context):
        nonlocal formatter_context_captured
        formatter_context_captured = context
        return AgentResult(
            agent_name='OutputFormatterAgent',
            success=True,
            confidence=1.0,
            confidence_level=ConfidenceLevel.HIGH,
            data={'formatted_output': '# Report'}
        )
    
    with patch.object(orchestrator.segmentation_agent, 'execute', new_callable=AsyncMock) as mock_seg, \
         patch.object(orchestrator.topic_detection_agent, 'execute', new_callable=AsyncMock) as mock_topic, \
         patch.object(orchestrator.subtopic_detection_agent, 'execute', new_callable=AsyncMock) as mock_subtopic, \
         patch.object(orchestrator.topic_sentiment_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.example_extraction_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.fin_performance_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.trend_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.output_formatter_agent, 'execute', capture_formatter_context), \
         patch('src.agents.topic_orchestrator.get_display'):
        
        mock_seg.return_value = AgentResult(
            agent_name='SegmentationAgent',
            success=True,
            confidence=1.0,
            confidence_level=ConfidenceLevel.HIGH,
            data={
                'paid_customer_conversations': all_conversations[:55],
                'free_fin_only_conversations': all_conversations[55:],
                'paid_fin_resolved_conversations': []
            }
        )
        
        mock_topic.return_value = AgentResult(
            agent_name='TopicDetectionAgent',
            success=True,
            confidence=0.95,
            confidence_level=ConfidenceLevel.HIGH,
            data={'topic_distribution': {}, 'topics_by_conversation': {}}
        )
        
        mock_subtopic.return_value = AgentResult(
            agent_name='SubTopicDetectionAgent',
            success=True,
            confidence=0.90,
            confidence_level=ConfidenceLevel.HIGH,
            data={
                'subtopics_by_tier1_topic': {
                    'Billing Issues': {
                        'tier2': {'Refund': {'volume': 10}},
                        'tier3': {}
                    }
                }
            }
        )
        
        await orchestrator.execute_weekly_analysis(
            conversations=all_conversations,
            **mock_week_params
        )
        
        # Verify SubTopicDetectionAgent in formatter context
        assert formatter_context_captured is not None
        assert 'SubTopicDetectionAgent' in formatter_context_captured.previous_results
        subtopic_data = formatter_context_captured.previous_results['SubTopicDetectionAgent']
        assert 'data' in subtopic_data
        assert 'subtopics_by_tier1_topic' in subtopic_data['data']


@pytest.mark.asyncio
async def test_aggregate_metrics_with_subtopics(orchestrator, all_conversations, mock_week_params):
    """Test _aggregate_metrics() includes subtopic_stats section."""
    with patch.object(orchestrator.segmentation_agent, 'execute', new_callable=AsyncMock) as mock_seg, \
         patch.object(orchestrator.topic_detection_agent, 'execute', new_callable=AsyncMock) as mock_topic, \
         patch.object(orchestrator.subtopic_detection_agent, 'execute', new_callable=AsyncMock) as mock_subtopic, \
         patch.object(orchestrator.topic_sentiment_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.example_extraction_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.fin_performance_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.trend_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.output_formatter_agent, 'execute', new_callable=AsyncMock), \
         patch('src.agents.topic_orchestrator.get_display'):
        
        mock_seg.return_value = AgentResult(
            agent_name='SegmentationAgent',
            success=True,
            confidence=1.0,
            confidence_level=ConfidenceLevel.HIGH,
            data={
                'paid_customer_conversations': all_conversations[:55],
                'free_fin_only_conversations': all_conversations[55:],
                'paid_fin_resolved_conversations': []
            }
        )
        
        mock_topic.return_value = AgentResult(
            agent_name='TopicDetectionAgent',
            success=True,
            confidence=0.95,
            confidence_level=ConfidenceLevel.HIGH,
            data={'topic_distribution': {}, 'topics_by_conversation': {}}
        )
        
        mock_subtopic.return_value = AgentResult(
            agent_name='SubTopicDetectionAgent',
            success=True,
            confidence=0.90,
            confidence_level=ConfidenceLevel.HIGH,
            execution_time=2.5,
            token_count=1500,
            data={
                'subtopics_by_tier1_topic': {
                    'Billing Issues': {
                        'tier2': {
                            'Refund': {'volume': 10},
                            'Invoice': {'volume': 8}
                        },
                        'tier3': {
                            'Refund Delays': {'keywords': ['refund', 'delay']}
                        }
                    },
                    'Account Issues': {
                        'tier2': {
                            'Login': {'volume': 15}
                        },
                        'tier3': {}
                    }
                }
            }
        )
        
        result = await orchestrator.execute_weekly_analysis(
            conversations=all_conversations,
            **mock_week_params
        )
        
        # Verify metrics include subtopic_stats
        metrics = result['metrics']
        assert 'subtopic_stats' in metrics
        assert metrics['subtopic_stats']['tier1_topics_analyzed'] == 2
        assert metrics['subtopic_stats']['tier2_subtopics_found'] == 3
        assert metrics['subtopic_stats']['tier3_themes_discovered'] == 1
        
        # Verify phase_breakdown includes subtopic_detection
        assert 'phase_breakdown' in metrics
        assert 'subtopic_detection' in metrics['phase_breakdown']
        assert metrics['phase_breakdown']['subtopic_detection'] == 2.5


@pytest.mark.asyncio
async def test_aggregate_metrics_without_subtopics(orchestrator, all_conversations, mock_week_params):
    """Test backward compatibility when SubTopicDetectionAgent not in workflow_results."""
    with patch.object(orchestrator.segmentation_agent, 'execute', new_callable=AsyncMock) as mock_seg, \
         patch.object(orchestrator.topic_detection_agent, 'execute', new_callable=AsyncMock) as mock_topic, \
         patch.object(orchestrator.subtopic_detection_agent, 'execute', new_callable=AsyncMock) as mock_subtopic, \
         patch.object(orchestrator.topic_sentiment_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.example_extraction_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.fin_performance_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.trend_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.output_formatter_agent, 'execute', new_callable=AsyncMock), \
         patch('src.agents.topic_orchestrator.get_display'):
        
        mock_seg.return_value = AgentResult(
            agent_name='SegmentationAgent',
            success=True,
            confidence=1.0,
            confidence_level=ConfidenceLevel.HIGH,
            data={
                'paid_customer_conversations': all_conversations[:55],
                'free_fin_only_conversations': all_conversations[55:],
                'paid_fin_resolved_conversations': []
            }
        )
        
        mock_topic.return_value = AgentResult(
            agent_name='TopicDetectionAgent',
            success=True,
            confidence=0.95,
            confidence_level=ConfidenceLevel.HIGH,
            data={'topic_distribution': {}, 'topics_by_conversation': {}}
        )
        
        # SubTopicDetectionAgent fails
        mock_subtopic.return_value = AgentResult(
            agent_name='SubTopicDetectionAgent',
            success=False,
            confidence=0.0,
            confidence_level=ConfidenceLevel.HIGH,
            error_message='Failed to execute'
        )
        
        result = await orchestrator.execute_weekly_analysis(
            conversations=all_conversations,
            **mock_week_params
        )
        
        # Verify metrics work without subtopic_stats
        metrics = result['metrics']
        # subtopic_stats may or may not be present, but should not crash
        assert 'phase_breakdown' in metrics
        assert 'subtopic_detection' in metrics['phase_breakdown']


@pytest.mark.asyncio
async def test_subtopic_agent_failure_handling(orchestrator, all_conversations, mock_week_params):
    """Test workflow continues when SubTopicDetectionAgent raises exception."""
    with patch.object(orchestrator.segmentation_agent, 'execute', new_callable=AsyncMock) as mock_seg, \
         patch.object(orchestrator.topic_detection_agent, 'execute', new_callable=AsyncMock) as mock_topic, \
         patch.object(orchestrator.subtopic_detection_agent, 'execute', new_callable=AsyncMock) as mock_subtopic, \
         patch.object(orchestrator.topic_sentiment_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.example_extraction_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.fin_performance_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.trend_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.output_formatter_agent, 'execute', new_callable=AsyncMock) as mock_formatter, \
         patch('src.agents.topic_orchestrator.get_display'):
        
        mock_seg.return_value = AgentResult(
            agent_name='SegmentationAgent',
            success=True,
            confidence=1.0,
            confidence_level=ConfidenceLevel.HIGH,
            data={
                'paid_customer_conversations': all_conversations[:55],
                'free_fin_only_conversations': all_conversations[55:],
                'paid_fin_resolved_conversations': []
            }
        )
        
        mock_topic.return_value = AgentResult(
            agent_name='TopicDetectionAgent',
            success=True,
            confidence=0.95,
            confidence_level=ConfidenceLevel.HIGH,
            data={'topic_distribution': {}, 'topics_by_conversation': {}}
        )
        
        # SubTopicDetectionAgent raises exception
        mock_subtopic.side_effect = Exception('Simulated failure')
        
        mock_formatter.return_value = AgentResult(
            agent_name='OutputFormatterAgent',
            success=True,
            confidence=1.0,
            confidence_level=ConfidenceLevel.HIGH,
            data={'formatted_output': '# Report'}
        )
        
        # Should not crash
        result = await orchestrator.execute_weekly_analysis(
            conversations=all_conversations,
            **mock_week_params
        )
        
        # Verify workflow completed
        assert result is not None
        assert 'formatted_report' in result
        
        # Verify downstream agents received empty sub-topic data
        formatter_context = mock_formatter.call_args[0][0]
        assert 'SubTopicDetectionAgent' in formatter_context.previous_results
        # Should be empty dict due to failure
        assert formatter_context.previous_results['SubTopicDetectionAgent'] == {}


@pytest.mark.asyncio
async def test_display_subtopic_agent_result(orchestrator, all_conversations, mock_week_params):
    """Verify display.display_agent_result() is called for SubTopicDetectionAgent."""
    with patch.object(orchestrator.segmentation_agent, 'execute', new_callable=AsyncMock) as mock_seg, \
         patch.object(orchestrator.topic_detection_agent, 'execute', new_callable=AsyncMock) as mock_topic, \
         patch.object(orchestrator.subtopic_detection_agent, 'execute', new_callable=AsyncMock) as mock_subtopic, \
         patch.object(orchestrator.topic_sentiment_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.example_extraction_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.fin_performance_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.trend_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.output_formatter_agent, 'execute', new_callable=AsyncMock), \
         patch('src.agents.topic_orchestrator.get_display') as mock_get_display:
        
        mock_display = MagicMock()
        mock_get_display.return_value = mock_display
        
        mock_seg.return_value = AgentResult(
            agent_name='SegmentationAgent',
            success=True,
            confidence=1.0,
            confidence_level=ConfidenceLevel.HIGH,
            data={
                'paid_customer_conversations': all_conversations[:55],
                'free_fin_only_conversations': all_conversations[55:],
                'paid_fin_resolved_conversations': []
            }
        )
        
        mock_topic.return_value = AgentResult(
            agent_name='TopicDetectionAgent',
            success=True,
            confidence=0.95,
            confidence_level=ConfidenceLevel.HIGH,
            data={'topic_distribution': {}, 'topics_by_conversation': {}}
        )
        
        subtopic_result = AgentResult(
            agent_name='SubTopicDetectionAgent',
            success=True,
            confidence=0.90,
            confidence_level=ConfidenceLevel.HIGH,
            data={'subtopics_by_tier1_topic': {}}
        )
        mock_subtopic.return_value = subtopic_result
        
        await orchestrator.execute_weekly_analysis(
            conversations=all_conversations,
            **mock_week_params
        )
        
        # Verify display_agent_result was called for SubTopicDetectionAgent
        display_calls = [call[0][0] for call in mock_display.display_agent_result.call_args_list]
        assert 'SubTopicDetectionAgent' in display_calls


@pytest.mark.asyncio
async def test_final_output_structure_with_subtopics(orchestrator, all_conversations, mock_week_params):
    """Verify final output dict contains all expected sub-topic fields."""
    with patch.object(orchestrator.segmentation_agent, 'execute', new_callable=AsyncMock) as mock_seg, \
         patch.object(orchestrator.topic_detection_agent, 'execute', new_callable=AsyncMock) as mock_topic, \
         patch.object(orchestrator.subtopic_detection_agent, 'execute', new_callable=AsyncMock) as mock_subtopic, \
         patch.object(orchestrator.topic_sentiment_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.example_extraction_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.fin_performance_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.trend_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.output_formatter_agent, 'execute', new_callable=AsyncMock), \
         patch('src.agents.topic_orchestrator.get_display'):
        
        mock_seg.return_value = AgentResult(
            agent_name='SegmentationAgent',
            success=True,
            confidence=1.0,
            confidence_level=ConfidenceLevel.HIGH,
            data={
                'paid_customer_conversations': all_conversations[:55],
                'free_fin_only_conversations': all_conversations[55:],
                'paid_fin_resolved_conversations': []
            }
        )
        
        mock_topic.return_value = AgentResult(
            agent_name='TopicDetectionAgent',
            success=True,
            confidence=0.95,
            confidence_level=ConfidenceLevel.HIGH,
            data={'topic_distribution': {'Billing Issues': {'volume': 20}}, 'topics_by_conversation': {}}
        )
        
        mock_subtopic.return_value = AgentResult(
            agent_name='SubTopicDetectionAgent',
            success=True,
            confidence=0.90,
            confidence_level=ConfidenceLevel.HIGH,
            data={
                'subtopics_by_tier1_topic': {
                    'Billing Issues': {
                        'tier2': {'Refund': {'volume': 10}},
                        'tier3': {'Delays': {'keywords': ['delay']}}
                    }
                }
            }
        )
        
        result = await orchestrator.execute_weekly_analysis(
            conversations=all_conversations,
            **mock_week_params
        )
        
        # Verify summary contains subtopics_analyzed
        assert 'summary' in result
        assert 'subtopics_analyzed' in result['summary']
        assert result['summary']['subtopics_analyzed'] == 1
        
        # Verify metrics contains subtopic_stats
        assert 'metrics' in result
        assert 'subtopic_stats' in result['metrics']
        assert result['metrics']['subtopic_stats']['tier1_topics_analyzed'] == 1
        assert result['metrics']['subtopic_stats']['tier2_subtopics_found'] == 1
        assert result['metrics']['subtopic_stats']['tier3_themes_discovered'] == 1
        
        # Verify agent_results contains SubTopicDetectionAgent
        assert 'agent_results' in result
        assert 'SubTopicDetectionAgent' in result['agent_results']
        assert result['agent_results']['SubTopicDetectionAgent']['success'] is True


@pytest.mark.asyncio
async def test_phase_execution_times(orchestrator, all_conversations, mock_week_params):
    """Verify all phase timings are tracked including subtopic_detection phase."""
    with patch.object(orchestrator.segmentation_agent, 'execute', new_callable=AsyncMock) as mock_seg, \
         patch.object(orchestrator.topic_detection_agent, 'execute', new_callable=AsyncMock) as mock_topic, \
         patch.object(orchestrator.subtopic_detection_agent, 'execute', new_callable=AsyncMock) as mock_subtopic, \
         patch.object(orchestrator.topic_sentiment_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.example_extraction_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.fin_performance_agent, 'execute', new_callable=AsyncMock) as mock_fin, \
         patch.object(orchestrator.trend_agent, 'execute', new_callable=AsyncMock) as mock_trend, \
         patch.object(orchestrator.output_formatter_agent, 'execute', new_callable=AsyncMock) as mock_formatter, \
         patch('src.agents.topic_orchestrator.get_display'):
        
        mock_seg.return_value = AgentResult(
            agent_name='SegmentationAgent',
            success=True,
            confidence=1.0,
            confidence_level=ConfidenceLevel.HIGH,
            execution_time=1.2,
            data={
                'paid_customer_conversations': all_conversations[:55],
                'free_fin_only_conversations': all_conversations[55:],
                'paid_fin_resolved_conversations': []
            }
        )
        
        mock_topic.return_value = AgentResult(
            agent_name='TopicDetectionAgent',
            success=True,
            confidence=0.95,
            confidence_level=ConfidenceLevel.HIGH,
            execution_time=3.5,
            data={'topic_distribution': {}, 'topics_by_conversation': {}}
        )
        
        mock_subtopic.return_value = AgentResult(
            agent_name='SubTopicDetectionAgent',
            success=True,
            confidence=0.90,
            confidence_level=ConfidenceLevel.HIGH,
            execution_time=2.8,
            data={'subtopics_by_tier1_topic': {}}
        )
        
        mock_fin.return_value = AgentResult(
            agent_name='FinPerformanceAgent',
            success=True,
            confidence=0.92,
            confidence_level=ConfidenceLevel.HIGH,
            execution_time=4.1,
            data={'free_tier': {}, 'paid_tier': {}}
        )
        
        mock_trend.return_value = AgentResult(
            agent_name='TrendAgent',
            success=True,
            confidence=0.88,
            confidence_level=ConfidenceLevel.HIGH,
            execution_time=2.2,
            data={'trends': {}}
        )
        
        mock_formatter.return_value = AgentResult(
            agent_name='OutputFormatterAgent',
            success=True,
            confidence=1.0,
            confidence_level=ConfidenceLevel.HIGH,
            execution_time=1.5,
            data={'formatted_output': '# Report'}
        )
        
        result = await orchestrator.execute_weekly_analysis(
            conversations=all_conversations,
            **mock_week_params
        )
        
        # Verify phase_breakdown includes all phases
        phase_breakdown = result['metrics']['phase_breakdown']
        assert 'segmentation' in phase_breakdown
        assert 'topic_detection' in phase_breakdown
        assert 'subtopic_detection' in phase_breakdown
        assert 'fin_analysis' in phase_breakdown
        assert 'trend_analysis' in phase_breakdown
        assert 'output_formatting' in phase_breakdown
        
        # Verify specific timing
        assert phase_breakdown['segmentation'] == 1.2
        assert phase_breakdown['topic_detection'] == 3.5
        assert phase_breakdown['subtopic_detection'] == 2.8
        assert phase_breakdown['fin_analysis'] == 4.1


@pytest.mark.asyncio
async def test_token_counting_with_subtopics(orchestrator, all_conversations, mock_week_params):
    """Verify total token count includes tokens from SubTopicDetectionAgent."""
    with patch.object(orchestrator.segmentation_agent, 'execute', new_callable=AsyncMock) as mock_seg, \
         patch.object(orchestrator.topic_detection_agent, 'execute', new_callable=AsyncMock) as mock_topic, \
         patch.object(orchestrator.subtopic_detection_agent, 'execute', new_callable=AsyncMock) as mock_subtopic, \
         patch.object(orchestrator.topic_sentiment_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.example_extraction_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.fin_performance_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.trend_agent, 'execute', new_callable=AsyncMock), \
         patch.object(orchestrator.output_formatter_agent, 'execute', new_callable=AsyncMock), \
         patch('src.agents.topic_orchestrator.get_display'):
        
        mock_seg.return_value = AgentResult(
            agent_name='SegmentationAgent',
            success=True,
            confidence=1.0,
            confidence_level=ConfidenceLevel.HIGH,
            token_count=0,
            data={
                'paid_customer_conversations': all_conversations[:55],
                'free_fin_only_conversations': all_conversations[55:],
                'paid_fin_resolved_conversations': []
            }
        )
        
        mock_topic.return_value = AgentResult(
            agent_name='TopicDetectionAgent',
            success=True,
            confidence=0.95,
            confidence_level=ConfidenceLevel.HIGH,
            token_count=5000,
            data={'topic_distribution': {}, 'topics_by_conversation': {}}
        )
        
        mock_subtopic.return_value = AgentResult(
            agent_name='SubTopicDetectionAgent',
            success=True,
            confidence=0.90,
            confidence_level=ConfidenceLevel.HIGH,
            token_count=3500,
            data={'subtopics_by_tier1_topic': {}}
        )
        
        result = await orchestrator.execute_weekly_analysis(
            conversations=all_conversations,
            **mock_week_params
        )
        
        # Verify total tokens includes subtopic agent tokens
        metrics = result['metrics']
        assert 'llm_stats' in metrics
        # Should include TopicDetectionAgent (5000) + SubTopicDetectionAgent (3500) = 8500
        assert metrics['llm_stats']['total_tokens'] >= 8500
        assert metrics['llm_stats']['total_calls'] >= 2

