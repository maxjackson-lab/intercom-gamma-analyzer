"""
Unit tests for FinPerformanceAgent: Validate enhanced performance analysis with sub-topic support.

This test suite validates:
1. Basic tier-based metrics calculation
2. Sub-topic performance integration
3. Conversation matching to sub-topics (Tier 2 and Tier 3)
4. Data-rooted quality metrics (resolution, knowledge gaps, escalation, ratings)
5. Backward compatibility without sub-topic data
6. End-to-end execution with mocked LLM calls
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from typing import Dict, Any, List

from src.agents.fin_performance_agent import FinPerformanceAgent
from src.agents.base_agent import AgentContext, AgentResult, ConfidenceLevel


# ============================================================================
# FIXTURES: Realistic conversation data with sub-topic indicators
# ============================================================================

@pytest.fixture
def agent():
    """Create FinPerformanceAgent instance for testing."""
    return FinPerformanceAgent()


@pytest.fixture
def sample_fin_conversations_with_subtopics() -> List[Dict[str, Any]]:
    """Create 30+ Finn conversations with varied sub-topic indicators and metrics."""
    conversations = []
    
    # Free tier conversations with Tier 2 indicators via tags
    for i in range(10):
        tier = 'Free' if i < 5 else 'Paid'
        conversations.append({
            'id': f'free_tag_{i}',
            'tier': tier,
            'ai_agent_participated': True,
            'detected_topics': ['Billing Issues'],
            'full_text': f'Billing issue {i} resolved without escalation',
            'tags': {
                'tags': [
                    {'name': 'Refund'},
                    {'name': 'Invoice'}
                ]
            },
            'custom_attributes': {},
            'conversation_topics': [],
            'conversation_rating': 4 if i % 2 == 0 else None
        })
    
    # Conversations with Tier 2 via custom_attributes
    for i in range(10, 20):
        tier = 'Free' if i < 15 else 'Paid'
        conversations.append({
            'id': f'attr_{i}',
            'tier': tier,
            'ai_agent_participated': True,
            'detected_topics': ['Billing Issues'],
            'full_text': f'Billing type issue {i} with escalation',
            'tags': {'tags': []},
            'custom_attributes': {
                'billing_type': 'annual' if i % 2 == 0 else 'monthly',
                'payment_method': 'credit_card'
            },
            'conversation_topics': [],
            'conversation_rating': 2 if i % 3 == 0 else None
        })
    
    # Conversations with Tier 2 via conversation_topics
    for i in range(20, 25):
        tier = 'Free' if i < 22 else 'Paid'
        conversations.append({
            'id': f'topic_{i}',
            'tier': tier,
            'ai_agent_participated': True,
            'detected_topics': ['Account Issues'],
            'full_text': f'Account topic issue {i}',
            'tags': {'tags': []},
            'custom_attributes': {},
            'conversation_topics': [
                {'name': 'Subscription'},
                {'name': 'Payment'}
            ],
            'conversation_rating': 5 if i % 2 == 0 else None
        })
    
    # Conversations with Tier 3 keywords and escalation phrases
    for i in range(25, 30):
        tier = 'Free' if i < 27 else 'Paid'
        conversations.append({
            'id': f'keyword_{i}',
            'tier': tier,
            'ai_agent_participated': True,
            'detected_topics': ['Billing Issues'],
            'full_text': f'Refund delay issue {i} speak to human',
            'tags': {'tags': []},
            'custom_attributes': {},
            'conversation_topics': [],
            'conversation_rating': 1 if i % 2 == 0 else None
        })
    
    # Add some with knowledge gap phrases
    for i in range(30, 35):
        tier = 'Free' if i < 32 else 'Paid'
        conversations.append({
            'id': f'gap_{i}',
            'tier': tier,
            'ai_agent_participated': True,
            'detected_topics': ['Product Questions'],
            'full_text': f'Product issue {i} wrong not helpful',
            'tags': {'tags': []},
            'custom_attributes': {},
            'conversation_topics': [],
            'conversation_rating': 3 if i % 2 == 0 else None
        })
    
    return conversations


@pytest.fixture
def mock_subtopic_detection_result():
    """Create mock SubTopicDetectionAgent output with nested sub-topic structure."""
    return {
        'data': {
            'subtopics_by_tier1_topic': {
                'Billing Issues': {
                    'tier2': {
                        'Refund': {'volume': 15, 'percentage': 50.0, 'source': 'tags'},
                        'Invoice': {'volume': 10, 'percentage': 33.3, 'source': 'tags'},
                        'annual': {'volume': 8, 'percentage': 26.7, 'source': 'custom_attributes'},
                        'monthly': {'volume': 7, 'percentage': 23.3, 'source': 'custom_attributes'}
                    },
                    'tier3': {
                        'Refund Processing Delays': {
                            'volume': 5,
                            'percentage': 16.7,
                            'method': 'llm_semantic',
                            'keywords': ['refund', 'delay']
                        }
                    }
                },
                'Account Issues': {
                    'tier2': {
                        'Subscription': {'volume': 3, 'percentage': 60.0, 'source': 'topics'},
                        'Payment': {'volume': 2, 'percentage': 40.0, 'source': 'topics'}
                    },
                    'tier3': {}
                }
            }
        }
    }


@pytest.fixture
def mock_context_with_subtopics(sample_fin_conversations_with_subtopics, mock_subtopic_detection_result):
    """Create AgentContext with conversations, metadata, and sub-topic results."""
    free_convs = [c for c in sample_fin_conversations_with_subtopics if c.get('tier') == 'Free']
    paid_convs = [c for c in sample_fin_conversations_with_subtopics if c.get('tier') == 'Paid']
    
    return AgentContext(
        analysis_id='test_analysis_123',
        analysis_type='fin_performance_test',
        start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
        conversations=sample_fin_conversations_with_subtopics,
        metadata={
            'free_fin_conversations': free_convs,
            'paid_fin_conversations': paid_convs
        },
        previous_results={
            'SubTopicDetectionAgent': mock_subtopic_detection_result
        }
    )


@pytest.fixture
def mock_context_without_subtopics(sample_fin_conversations_with_subtopics):
    """Create AgentContext without SubTopicDetectionAgent results for backward compatibility."""
    free_convs = [c for c in sample_fin_conversations_with_subtopics if c.get('tier') == 'Free']
    paid_convs = [c for c in sample_fin_conversations_with_subtopics if c.get('tier') == 'Paid']
    
    return AgentContext(
        analysis_id='test_analysis_456',
        analysis_type='fin_performance_backward_compat',
        start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
        conversations=sample_fin_conversations_with_subtopics,
        metadata={
            'free_fin_conversations': free_convs,
            'paid_fin_conversations': paid_convs
        },
        previous_results={}
    )


# ============================================================================
# UNIT TESTS
# ============================================================================

class TestFinPerformanceAgent:
    """Test suite for FinPerformanceAgent."""

    def test_calculate_tier_metrics_basic(self, agent, sample_fin_conversations_with_subtopics):
        """Test basic tier metrics calculation without sub-topics."""
        free_convs = [c for c in sample_fin_conversations_with_subtopics if c.get('tier') == 'Free']
        
        result = agent._calculate_tier_metrics(free_convs, 'Free')
        
        assert 'resolution_rate' in result
        assert 'knowledge_gaps_count' in result
        assert 'performance_by_topic' in result
        # performance_by_subtopic should be present and None when no sub-topics provided
        assert 'performance_by_subtopic' in result
        assert result['performance_by_subtopic'] is None
        assert isinstance(result['resolution_rate'], float)
        assert isinstance(result['knowledge_gaps_count'], int)

    def test_calculate_tier_metrics_with_subtopics(self, agent, sample_fin_conversations_with_subtopics, mock_subtopic_detection_result):
        """Test tier metrics calculation with sub-topic data."""
        free_convs = [c for c in sample_fin_conversations_with_subtopics if c.get('tier') == 'Free']
        subtopics_data = mock_subtopic_detection_result['data']['subtopics_by_tier1_topic']
        
        result = agent._calculate_tier_metrics(free_convs, 'Free', subtopics_data=subtopics_data)
        
        assert 'performance_by_subtopic' in result
        assert 'Billing Issues' in result['performance_by_subtopic']
        assert 'tier2' in result['performance_by_subtopic']['Billing Issues']
        assert 'tier3' in result['performance_by_subtopic']['Billing Issues']
        assert 'Refund' in result['performance_by_subtopic']['Billing Issues']['tier2']

    def test_soft_failure_keywords_coverage(self, agent):
        """Test detection of specific soft failure keywords."""
        keywords = [
            "still broken",
            "didn't fix",
            "I need a human",
            "talk to a human",
            "useless",
            "bad bot"
        ]
        
        for kw in keywords:
            conv = {
                'id': f'sf_{kw.replace(" ", "_")}',
                'conversation_parts': {'conversation_parts': [
                    {'author': {'type': 'user'}, 'body': f'This is {kw}'}
                ]},
                'ai_agent_participated': True
            }
            # Use the imported detect_soft_failure from services
            from src.services.fin_escalation_analyzer import detect_soft_failure
            assert detect_soft_failure(conv) is True, f"Failed to detect keyword: {kw}"

    def test_true_resolution_rate_calculation(self, agent):
        """Test calculation of true resolution rate (excluding soft failures)."""
        from unittest.mock import patch
        
        # Create conversations
        # 5 Soft Failures (technically resolved + frustration)
        soft_fails = [{
            'id': f'sf_{i}',
            'state': 'closed',
            'conversation_parts': {'conversation_parts': [{'author': {'type': 'user'}, 'body': 'useless bot'}]},
            'ai_agent_participated': True
        } for i in range(5)]
        
        # 10 True Resolved (technically resolved + no frustration)
        resolved = [{
            'id': f'tr_{i}',
            'state': 'closed',
            'conversation_parts': {'conversation_parts': [{'author': {'type': 'user'}, 'body': 'thanks'}]},
            'ai_agent_participated': True
        } for i in range(10)]
        
        # 5 Escalated (admin involved - ignored for soft failure check)
        escalated = [{
            'id': f'esc_{i}',
            'state': 'open',
            'conversation_parts': {'conversation_parts': [{'author': {'type': 'admin'}}]},
            'ai_agent_participated': True
        } for i in range(5)]
        
        all_convs = soft_fails + resolved + escalated
        
        # Patch calculate_dual_metrics to return deterministic values
        # We simulate that 15 are considered "deflected" by Intercom rules (the 5 SF + 10 TR)
        with patch('src.utils.fin_metrics_calculator.calculate_dual_metrics') as mock_calc:
            mock_calc.return_value = {
                'intercom_compatible': {'deflected_count': 15, 'deflection_rate': 75.0},
                'quality_adjusted': {},
                'comparison': {}
            }
            
            result = agent._calculate_tier_metrics(all_convs, 'Free')
            
            # Verify metrics
            # Resolution Rate (Intercom) = 75% (from mock)
            assert result['resolution_rate'] == 0.75
            
            # Soft Failures = 5 detected
            assert result['soft_failure_count'] == 5
            assert result['soft_failure_rate'] == 0.25  # 5/20
            
            # True Resolution Rate = (Deflected - Soft Failures) / Total
            # (15 - 5) / 20 = 10 / 20 = 50%
            assert result['true_resolution_rate'] == 0.50
            
            # Verify it is strictly derived from counts: 15 - 5 = 10
            assert result['true_resolution_rate'] == (15 - 5) / 20

    def test_soft_failure_examples_structure(self, agent):
        """Test structure of soft failure examples and end-to-end detection."""
        from unittest.mock import patch
        
        conv = {
            'id': 'sf_struct',
            'state': 'closed',
            'conversation_parts': {'conversation_parts': [
                {'author': {'type': 'user'}, 'body': 'I need a human'}
            ]},
            'ai_agent_participated': True
        }
        
        # Patch calculate_dual_metrics to ensure this is counted as deflected
        # (If it wasn't deflected, it wouldn't be a soft failure, just an escalation)
        with patch('src.utils.fin_metrics_calculator.calculate_dual_metrics') as mock_calc:
            mock_calc.return_value = {
                'intercom_compatible': {'deflected_count': 1, 'deflection_rate': 100.0},
                'quality_adjusted': {},
                'comparison': {}
            }
        
            result = agent._calculate_tier_metrics([conv], 'Free')
            
            assert 'soft_failure_examples' in result
            examples = result['soft_failure_examples']
            assert len(examples) == 1
            assert 'id' in examples[0]
            assert 'preview' in examples[0]
            assert 'intercom_url' in examples[0]
            assert examples[0]['id'] == 'sf_struct'
            
            # Verify end-to-end metric impact
            assert result['soft_failure_count'] == 1
            assert result['soft_failure_rate'] > 0
            # True resolution should be lower than resolution rate because of the soft failure
            # 100% deflected - 100% soft failure = 0% true resolution
            assert result['true_resolution_rate'] < result['resolution_rate']
            assert result['true_resolution_rate'] == 0.0

    def test_match_conversation_to_tier3_subtopic_via_keywords(self, agent, sample_fin_conversations_with_subtopics):
        """Test Tier 3 matching using keyword list against extracted text."""
        # Create a conversation with text in conversation_parts for extraction
        conv = {
            'id': 'keyword_test',
            'conversation_parts': {'conversation_parts': [
                {'author': {'type': 'user'}, 'body': 'refund delay issue'}
            ]}
        }
        subtopic_data = {'volume': 1, 'percentage': 100.0, 'method': 'llm_semantic', 'keywords': ['refund', 'delay']}
        
        # Should match due to 'refund' and 'delay' keywords in body
        assert agent._match_conversation_to_subtopic(conv, 'Refund Processing Delays', 'tier3', subtopic_data) is True
        
        # Test non-matching
        conv_no_match = {
            'id': 'no_match',
            'conversation_parts': {'conversation_parts': [
                {'author': {'type': 'user'}, 'body': 'something else'}
            ]}
        }
        assert agent._match_conversation_to_subtopic(conv_no_match, 'Refund Processing Delays', 'tier3', subtopic_data) is False

    def test_calculate_single_subtopic_metrics_resolution_rate(self, agent, sample_fin_conversations_with_subtopics):
        """Test resolution rate calculation per sub-topic."""
        # Use conversations without escalation phrases
        # Update fixture usage to access list correctly or create new ones
        convs = [
            {'id': '1', 'state': 'closed', 'conversation_parts': {'conversation_parts': [{'author': {'type': 'user'}, 'body': 'thanks'}]}},
            {'id': '2', 'state': 'closed', 'conversation_parts': {'conversation_parts': [{'author': {'type': 'user'}, 'body': 'good'}]}}
        ]
        
        result = agent._calculate_single_subtopic_metrics(convs, 'Billing Issues', 'Refund', 'tier2')
        
        assert 'resolution_rate' in result
        assert result['total'] == 2
        assert result['resolution_rate'] == 1.0

    def test_calculate_single_subtopic_metrics_knowledge_gap_rate(self, agent, sample_fin_conversations_with_subtopics):
        """Test knowledge gap rate calculation per sub-topic."""
        # Use conversations with knowledge gap phrases in BODY and HIGH ENGAGEMENT (to avoid 'resolved' via low engagement)
        convs = [{
            'id': 'gap_1', 
            'conversation_parts': {'conversation_parts': [
                {'author': {'type': 'user'}, 'body': 'wrong not helpful'},
                {'author': {'type': 'user'}, 'body': 'still waiting'},
                {'author': {'type': 'user'}, 'body': 'hello?'}
            ]},
            'state': 'open'
        }]
        
        result = agent._calculate_single_subtopic_metrics(convs, 'Product Questions', 'Test', 'tier2')
        
        assert 'knowledge_gap_rate' in result
        assert result['knowledge_gap_count'] > 0
        assert result['knowledge_gap_rate'] == 1.0

    def test_calculate_single_subtopic_metrics_escalation_rate(self, agent, sample_fin_conversations_with_subtopics):
        """Test escalation rate calculation using _detect_escalation_request."""
        # Use conversations with escalation phrases in BODY and HIGH ENGAGEMENT (to avoid 'resolved' via low engagement)
        # Note: _calculate_single_subtopic_metrics only counts 'escalated' outcome if categorize_fin_outcome says so.
        # categorize_fin_outcome says 'escalated' if resolution_state='routed_to_team' or human responded without explicit routing.
        # It does NOT check text for 'escalation_request' keyword to determine OUTCOME 'escalated'.
        # However, the method returns 'escalation_rate' = len(escalated_convs) / total.
        
        # Wait, does _calculate_single_subtopic_metrics use _detect_escalation_request?
        # Let's check the code in src/agents/fin_performance_agent.py.
        # It does NOT seem to use _detect_escalation_request for the 'escalation_rate' calculation.
        # It uses categorize_fin_outcome.
        
        # So I need to simulate an outcome of 'escalated'.
        # Outcome 'escalated' requires:
        # 1. Has human response OR resolution_state='routed_to_team'.
        
        convs = [{
            'id': 'esc_1',
            'conversation_parts': {'conversation_parts': [
                {'author': {'type': 'user'}, 'body': 'speak to human'},
                {'author': {'type': 'admin'}, 'body': 'I am here'} # Human response
            ]},
            'ai_agent': {'resolution_state': 'routed_to_team'}
        }]
        
        result = agent._calculate_single_subtopic_metrics(convs, 'Billing Issues', 'Refund Processing Delays', 'tier3')
        
        assert 'escalation_rate' in result
        assert result['escalation_count'] > 0
        assert result['escalation_rate'] == 1.0

    def test_calculate_single_subtopic_metrics_avg_rating(self, agent, sample_fin_conversations_with_subtopics):
        """Test average rating calculation from conversation_rating field."""
        # Use conversations with ratings
        convs_with_ratings = [
            {'conversation_rating': {'rating': 5}},
            {'conversation_rating': {'rating': 3}}
        ]
        convs_without_ratings = [{'conversation_rating': None}]
        
        # Test with ratings
        result_with = agent._calculate_single_subtopic_metrics(convs_with_ratings, 'Test', 'Test', 'tier2')
        assert result_with['rated_count'] == 2
        assert result_with['avg_rating'] == 4.0
        
        # Test without ratings
        result_without = agent._calculate_single_subtopic_metrics(convs_without_ratings, 'Test', 'Test', 'tier2')
        assert result_without['rated_count'] == 0
        assert result_without['avg_rating'] is None

    def test_detect_escalation_request_positive(self, agent):
        """Test _detect_escalation_request returns True for escalation phrases."""
        # Put text in conversation_parts for extraction
        conv_with_escalation = {
            'conversation_parts': {'conversation_parts': [
                {'author': {'type': 'user'}, 'body': 'I need to speak to human about this issue'}
            ]}
        }
        
        assert agent._detect_escalation_request(conv_with_escalation) is True
        
        conv_with_escalate = {
            'conversation_parts': {'conversation_parts': [
                {'author': {'type': 'user'}, 'body': 'Please escalate this to supervisor'}
            ]}
        }
        
        assert agent._detect_escalation_request(conv_with_escalate) is True

    def test_detect_escalation_request_negative(self, agent):
        """Test _detect_escalation_request returns False for no escalation phrases."""
        conv_no_escalation = {
            'conversation_parts': {'conversation_parts': [
                {'author': {'type': 'user'}, 'body': 'This is a normal question about billing'}
            ]}
        }
        
        assert agent._detect_escalation_request(conv_no_escalation) is False

    @pytest.mark.asyncio
    async def test_execute_with_subtopics(self, agent, mock_context_with_subtopics):
        """Async test of full execution with sub-topic data."""
        # Mock LLM client
        agent.ai_client = AsyncMock()
        agent.ai_client.generate_analysis = AsyncMock(return_value='Test insights with sub-topics')
        
        result = await agent.execute(mock_context_with_subtopics)
        
        assert result.success is True
        assert 'free_tier' in result.data
        assert 'paid_tier' in result.data
        assert 'performance_by_subtopic' in result.data['free_tier']
        assert 'performance_by_subtopic' in result.data['paid_tier']
        assert 'llm_insights' in result.data

    @pytest.mark.asyncio
    async def test_execute_without_subtopics_backward_compatibility(self, agent, mock_context_without_subtopics):
        """Async test without SubTopicDetectionAgent results for backward compatibility."""
        # Mock LLM client
        agent.ai_client = AsyncMock()
        agent.ai_client.generate_analysis = AsyncMock(return_value='Test insights without sub-topics')
        
        result = await agent.execute(mock_context_without_subtopics)
        
        assert result.success is True
        assert 'free_tier' in result.data
        assert 'paid_tier' in result.data
        # performance_by_subtopic should be present and None when no sub-topics
        assert 'performance_by_subtopic' in result.data['free_tier']
        assert result.data['free_tier']['performance_by_subtopic'] is None
        assert 'performance_by_subtopic' in result.data['paid_tier']
        assert result.data['paid_tier']['performance_by_subtopic'] is None
        assert 'llm_insights' in result.data

    def test_subtopic_metrics_data_rooted(self, agent, sample_fin_conversations_with_subtopics, mock_subtopic_detection_result):
        """Verify all metrics are based on measurable data."""
        free_convs = [c for c in sample_fin_conversations_with_subtopics if c.get('tier') == 'Free']
        subtopics_data = mock_subtopic_detection_result['data']['subtopics_by_tier1_topic']
        
        result = agent._calculate_tier_metrics(free_convs, 'Free', subtopics_data=subtopics_data)
        
        subtopic_perf = result['performance_by_subtopic']['Billing Issues']['tier2']['Refund']
        
        # All metrics should be calculable from data
        assert isinstance(subtopic_perf['total'], int)
        assert isinstance(subtopic_perf['resolution_rate'], float)
        assert isinstance(subtopic_perf['knowledge_gap_rate'], float)
        assert isinstance(subtopic_perf['escalation_rate'], float)
        assert subtopic_perf['avg_rating'] is None or isinstance(subtopic_perf['avg_rating'], float)

    def test_conversation_rating_handling(self, agent, sample_fin_conversations_with_subtopics):
        """Test handling of conversations with and without ratings."""
        convs_with_ratings = [c for c in sample_fin_conversations_with_subtopics if c.get('conversation_rating') is not None][:3]
        convs_without_ratings = [c for c in sample_fin_conversations_with_subtopics if c.get('conversation_rating') is None][:3]
        
        # Test with ratings
        result_with = agent._calculate_single_subtopic_metrics(convs_with_ratings, 'Test', 'Test', 'tier2')
        assert result_with['rated_count'] > 0
        assert result_with['avg_rating'] is not None
        
        # Test without ratings
        result_without = agent._calculate_single_subtopic_metrics(convs_without_ratings, 'Test', 'Test', 'tier2')
        assert result_without['rated_count'] == 0
        assert result_without['avg_rating'] is None

    def test_subtopic_performance_empty_subtopic(self, agent):
        """Test handling when a sub-topic has zero matching conversations."""
        empty_convs = []
        
        result = agent._calculate_single_subtopic_metrics(empty_convs, 'Test Topic', 'Empty Subtopic', 'tier2')
        
        assert result['total'] == 0
        assert result['resolution_rate'] == 0.0
        assert result['knowledge_gap_rate'] == 0.0
        assert result['escalation_rate'] == 0.0
        assert result['avg_rating'] is None
        assert result['rated_count'] == 0

    def test_tier_comparison_with_subtopics(self, agent, sample_fin_conversations_with_subtopics, mock_subtopic_detection_result):
        """Verify _compare_tiers still works when tier metrics include sub-topic data."""
        free_convs = [c for c in sample_fin_conversations_with_subtopics if c.get('tier') == 'Free']
        paid_convs = [c for c in sample_fin_conversations_with_subtopics if c.get('tier') == 'Paid']
        subtopics_data = mock_subtopic_detection_result['data']['subtopics_by_tier1_topic']
        
        free_metrics = agent._calculate_tier_metrics(free_convs, 'Free', subtopics_data=subtopics_data)
        paid_metrics = agent._calculate_tier_metrics(paid_convs, 'Paid', subtopics_data=subtopics_data)
        
        comparison = agent._compare_tiers(free_metrics, paid_metrics)
        
        assert 'resolution_rate_delta' in comparison
        assert 'knowledge_gap_delta' in comparison
        assert 'resolution_rate_interpretation' in comparison
        assert 'knowledge_gap_interpretation' in comparison