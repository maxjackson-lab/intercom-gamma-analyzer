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

    def test_match_conversation_to_tier2_subtopic_via_tags(self, agent, sample_fin_conversations_with_subtopics):
        """Test matching conversations to Tier 2 sub-topics via tags.tags."""
        conv = sample_fin_conversations_with_subtopics[0]  # Has 'Refund' and 'Invoice' tags
        subtopic_data = {'volume': 1, 'percentage': 100.0, 'source': 'tags'}
        
        # Should match 'Refund'
        assert agent._match_conversation_to_subtopic(conv, 'Refund', 'tier2', subtopic_data) is True
        # Should match 'Invoice'
        assert agent._match_conversation_to_subtopic(conv, 'Invoice', 'tier2', subtopic_data) is True
        # Should not match non-existent
        assert agent._match_conversation_to_subtopic(conv, 'NonExistent', 'tier2', subtopic_data) is False

    def test_match_conversation_to_tier2_subtopic_via_custom_attributes(self, agent, sample_fin_conversations_with_subtopics):
        """Test matching via custom_attributes values."""
        conv = sample_fin_conversations_with_subtopics[10]  # Has 'billing_type': 'annual'
        subtopic_data = {'volume': 1, 'percentage': 100.0, 'source': 'custom_attributes'}
        
        # Should match 'annual'
        assert agent._match_conversation_to_subtopic(conv, 'annual', 'tier2', subtopic_data) is True
        # Should not match 'monthly'
        assert agent._match_conversation_to_subtopic(conv, 'monthly', 'tier2', subtopic_data) is False

    def test_match_conversation_to_tier2_subtopic_via_topics(self, agent, sample_fin_conversations_with_subtopics):
        """Test matching via conversation_topics array."""
        conv = sample_fin_conversations_with_subtopics[20]  # Has 'Subscription' topic
        subtopic_data = {'volume': 1, 'percentage': 100.0, 'source': 'topics'}
        
        # Should match 'Subscription'
        assert agent._match_conversation_to_subtopic(conv, 'Subscription', 'tier2', subtopic_data) is True
        # Should not match 'Payment' (though it's in the list, test for exact match)
        assert agent._match_conversation_to_subtopic(conv, 'Payment', 'tier2', subtopic_data) is True  # Actually should match if present

    def test_match_conversation_to_tier3_subtopic_via_keywords(self, agent, sample_fin_conversations_with_subtopics):
        """Test Tier 3 matching using keyword list against full_text."""
        conv = sample_fin_conversations_with_subtopics[25]  # Has 'refund delay' in full_text
        subtopic_data = {'volume': 1, 'percentage': 100.0, 'method': 'llm_semantic', 'keywords': ['refund', 'delay']}
        
        # Should match due to 'refund' and 'delay' keywords
        assert agent._match_conversation_to_subtopic(conv, 'Refund Processing Delays', 'tier3', subtopic_data) is True
        
        # Test non-matching
        conv_no_match = sample_fin_conversations_with_subtopics[0]  # No keywords
        assert agent._match_conversation_to_subtopic(conv_no_match, 'Refund Processing Delays', 'tier3', subtopic_data) is False

    def test_calculate_single_subtopic_metrics_resolution_rate(self, agent, sample_fin_conversations_with_subtopics):
        """Test resolution rate calculation per sub-topic."""
        # Use conversations without escalation phrases
        convs = [c for c in sample_fin_conversations_with_subtopics[:5] if 'speak to human' not in c.get('full_text', '')]
        
        result = agent._calculate_single_subtopic_metrics(convs, 'Billing Issues', 'Refund', 'tier2')
        
        assert 'resolution_rate' in result
        assert 'total' in result
        assert 'resolved_count' in result
        assert result['total'] == len(convs)
        assert result['resolution_rate'] >= 0.0 and result['resolution_rate'] <= 1.0

    def test_calculate_single_subtopic_metrics_knowledge_gap_rate(self, agent, sample_fin_conversations_with_subtopics):
        """Test knowledge gap rate calculation per sub-topic."""
        # Use conversations with knowledge gap phrases
        convs = sample_fin_conversations_with_subtopics[30:35]  # Have 'wrong not helpful'
        
        result = agent._calculate_single_subtopic_metrics(convs, 'Product Questions', 'Test', 'tier2')
        
        assert 'knowledge_gap_rate' in result
        assert 'knowledge_gap_count' in result
        assert result['knowledge_gap_count'] > 0
        assert result['knowledge_gap_rate'] > 0.0

    def test_calculate_single_subtopic_metrics_escalation_rate(self, agent, sample_fin_conversations_with_subtopics):
        """Test escalation rate calculation using _detect_escalation_request."""
        # Use conversations with escalation phrases
        convs = sample_fin_conversations_with_subtopics[25:30]  # Have 'speak to human'
        
        result = agent._calculate_single_subtopic_metrics(convs, 'Billing Issues', 'Refund Processing Delays', 'tier3')
        
        assert 'escalation_rate' in result
        assert 'escalation_count' in result
        assert result['escalation_count'] > 0
        assert result['escalation_rate'] > 0.0

    def test_calculate_single_subtopic_metrics_avg_rating(self, agent, sample_fin_conversations_with_subtopics):
        """Test average rating calculation from conversation_rating field."""
        # Use conversations with ratings
        convs = [c for c in sample_fin_conversations_with_subtopics if c.get('conversation_rating') is not None][:5]
        
        result = agent._calculate_single_subtopic_metrics(convs, 'Billing Issues', 'Refund', 'tier2')
        
        assert 'avg_rating' in result
        assert 'rated_count' in result
        if result['rated_count'] > 0:
            assert result['avg_rating'] is not None
            assert 1 <= result['avg_rating'] <= 5
        else:
            assert result['avg_rating'] is None

    def test_detect_escalation_request_positive(self, agent):
        """Test _detect_escalation_request returns True for escalation phrases."""
        conv_with_escalation = {'full_text': 'I need to speak to human about this issue'}
        
        assert agent._detect_escalation_request(conv_with_escalation) is True
        
        conv_with_escalate = {'full_text': 'Please escalate this to supervisor'}
        
        assert agent._detect_escalation_request(conv_with_escalate) is True

    def test_detect_escalation_request_negative(self, agent):
        """Test _detect_escalation_request returns False for no escalation phrases."""
        conv_no_escalation = {'full_text': 'This is a normal question about billing'}
        
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