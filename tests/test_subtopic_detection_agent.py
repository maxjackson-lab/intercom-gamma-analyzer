"""
Unit tests for SubTopicDetectionAgent: Validate 3-tier sub-topic hierarchy creation.

This test suite validates:
1. Tier 2 sub-topic extraction from Intercom data (custom_attributes, tags, topics)
2. Tier 3 theme discovery via LLM with proper fallback
3. End-to-end execution with mocked LLM calls
4. Input validation and error handling
5. Percentage calculations and confidence scoring
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from typing import Dict, Any, List

from src.agents.subtopic_detection_agent import SubTopicDetectionAgent
from src.agents.base_agent import AgentContext, AgentResult, ConfidenceLevel


# ============================================================================
# FIXTURES: Realistic conversation data with Tier 2 sub-topic sources
# ============================================================================

@pytest.fixture
def agent():
    """Create SubTopicDetectionAgent instance for testing."""
    return SubTopicDetectionAgent()


@pytest.fixture
def sample_conversations_with_tier2_data() -> List[Dict[str, Any]]:
    """Create 20+ conversations with varied custom_attributes, tags.tags, and conversation_topics."""
    conversations = []
    
    # Billing conversations with tags
    for i in range(5):
        conversations.append({
            'id': f'billing_tag_{i}',
            'created_at': 1699123456 + i * 1000,
            'customer_messages': [f'Billing issue {i}'],
            'full_text': f'Billing issue {i}',
            'tags': {
                'tags': [
                    {'name': 'Refund'},
                    {'name': 'Invoice'}
                ]
            },
            'custom_attributes': {},
            'conversation_topics': []
        })
    
    # Billing conversations with custom attributes
    for i in range(5, 10):
        conversations.append({
            'id': f'billing_attr_{i}',
            'created_at': 1699123456 + i * 1000,
            'customer_messages': [f'Billing type issue {i}'],
            'full_text': f'Billing type issue {i}',
            'tags': {'tags': []},
            'custom_attributes': {
                'billing_type': 'annual' if i % 2 == 0 else 'monthly',
                'payment_method': 'credit_card'
            },
            'conversation_topics': []
        })
    
    # Billing conversations with topics
    for i in range(10, 15):
        conversations.append({
            'id': f'billing_topic_{i}',
            'created_at': 1699123456 + i * 1000,
            'customer_messages': [f'Billing topic issue {i}'],
            'full_text': f'Billing topic issue {i}',
            'tags': {'tags': []},
            'custom_attributes': {},
            'conversation_topics': [
                {'name': 'Subscription'},
                {'name': 'Payment'}
            ]
        })
    
    # Mixed sources
    for i in range(15, 20):
        conversations.append({
            'id': f'mixed_{i}',
            'created_at': 1699123456 + i * 1000,
            'customer_messages': [f'Mixed issue {i}'],
            'full_text': f'Mixed issue {i}',
            'tags': {
                'tags': [{'name': 'Refund'}]
            },
            'custom_attributes': {
                'billing_type': 'annual'
            },
            'conversation_topics': [
                {'name': 'Subscription'}
            ]
        })
    
    return conversations


@pytest.fixture
def mock_topic_detection_result(sample_conversations_with_tier2_data):
    """Create mock TopicDetectionAgent output with topic_distribution and topics_by_conversation."""
    # All conversations are under 'Billing Issues' topic
    topic_distribution = {
        'Billing Issues': {
            'volume': len(sample_conversations_with_tier2_data),
            'percentage': 100.0
        }
    }
    
    topics_by_conversation = {}
    for conv in sample_conversations_with_tier2_data:
        topics_by_conversation[conv['id']] = [
            {'topic': 'Billing Issues', 'confidence': 0.9}
        ]
    
    return {
        'data': {
            'topic_distribution': topic_distribution,
            'topics_by_conversation': topics_by_conversation
        }
    }


@pytest.fixture
def mock_context_with_topics(sample_conversations_with_tier2_data, mock_topic_detection_result):
    """Create AgentContext with conversations and previous_results containing mock topic detection data."""
    return AgentContext(
        analysis_id='test_analysis_123',
        analysis_type='subtopic_test',
        start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
        conversations=sample_conversations_with_tier2_data,
        previous_results={
            'TopicDetectionAgent': mock_topic_detection_result
        }
    )


# ============================================================================
# UNIT TESTS
# ============================================================================

class TestSubTopicDetectionAgent:
    """Test suite for SubTopicDetectionAgent."""

    def test_validate_input_success(self, agent, mock_context_with_topics):
        """Verify validation passes with proper TopicDetectionAgent results in context."""
        assert agent.validate_input(mock_context_with_topics) is True

    def test_validate_input_missing_topic_detection(self, agent):
        """Verify validation fails when TopicDetectionAgent results missing."""
        context = AgentContext(
            analysis_id='test',
            analysis_type='test',
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc),
            conversations=[],
            previous_results={}
        )
        
        with pytest.raises(ValueError, match="TopicDetectionAgent results not found"):
            agent.validate_input(context)

    def test_detect_tier2_subtopics_from_tags(self, agent, sample_conversations_with_tier2_data):
        """Test extraction of sub-topics from tags.tags array, verify counts and percentages."""
        # Filter to conversations with tags
        tagged_convs = [c for c in sample_conversations_with_tier2_data if c['tags']['tags']]
        
        result = agent._detect_tier2_subtopics(tagged_convs, 'Billing Issues')
        
        # Should find 'Refund' and 'Invoice'
        assert 'Refund' in result
        assert 'Invoice' in result
        assert result['Refund']['volume'] == len(tagged_convs)  # Each has 'Refund'
        assert result['Invoice']['volume'] == len(tagged_convs)  # Each has 'Invoice'
        
        # Percentages should be 100% since all conversations have these tags
        assert result['Refund']['percentage'] == 100.0
        assert result['Invoice']['percentage'] == 100.0
        assert result['Refund']['source'] == 'intercom_data'

    def test_detect_tier2_subtopics_from_custom_attributes(self, agent, sample_conversations_with_tier2_data):
        """Test extraction from custom_attributes dict, verify filtering for relevant attributes."""
        # Filter to conversations with custom attributes
        attr_convs = [c for c in sample_conversations_with_tier2_data if c['custom_attributes']]
        
        result = agent._detect_tier2_subtopics(attr_convs, 'Billing Issues')
        
        # Should find 'annual', 'monthly', 'credit_card'
        assert 'annual' in result
        assert 'monthly' in result
        assert 'credit_card' in result
        
        # Count how many have each
        annual_count = sum(1 for c in attr_convs if c['custom_attributes'].get('billing_type') == 'annual')
        monthly_count = sum(1 for c in attr_convs if c['custom_attributes'].get('billing_type') == 'monthly')
        credit_count = len(attr_convs)  # All have payment_method
        
        assert result['annual']['volume'] == annual_count
        assert result['monthly']['volume'] == monthly_count
        assert result['credit_card']['volume'] == credit_count

    def test_detect_tier2_subtopics_from_topics(self, agent, sample_conversations_with_tier2_data):
        """Test extraction from conversation_topics array."""
        # Filter to conversations with topics
        topic_convs = [c for c in sample_conversations_with_tier2_data if c['conversation_topics']]
        
        result = agent._detect_tier2_subtopics(topic_convs, 'Billing Issues')
        
        # Should find 'Subscription' and 'Payment'
        assert 'Subscription' in result
        assert 'Payment' in result
        assert result['Subscription']['volume'] == len(topic_convs)  # Each has 'Subscription'
        assert result['Payment']['volume'] == len(topic_convs)  # Each has 'Payment'

    def test_detect_tier2_subtopics_mixed_sources(self, agent, sample_conversations_with_tier2_data):
        """Test when sub-topics come from multiple sources (tags + attributes + topics)."""
        # Use all conversations
        result = agent._detect_tier2_subtopics(sample_conversations_with_tier2_data, 'Billing Issues')
        
        # Should have sub-topics from all sources
        expected_subtopics = {'Refund', 'Invoice', 'annual', 'monthly', 'credit_card', 'Subscription', 'Payment'}
        found_subtopics = set(result.keys())
        
        assert expected_subtopics.issubset(found_subtopics)

    def test_tier2_percentage_calculation(self, agent, sample_conversations_with_tier2_data):
        """Verify percentage calculations are correct relative to Tier 1 category volume."""
        # Test with subset of conversations
        subset = sample_conversations_with_tier2_data[:10]
        result = agent._detect_tier2_subtopics(subset, 'Billing Issues')
        
        total_convs = len(subset)
        for subtopic, data in result.items():
            expected_percentage = round((data['volume'] / total_convs * 100), 1)
            assert data['percentage'] == expected_percentage

    @pytest.mark.asyncio
    async def test_discover_tier3_themes_with_llm(self, agent, sample_conversations_with_tier2_data):
        """Mock LLM response with JSON themes, verify parsing and conversation matching."""
        # Mock the OpenAI client
        agent.openai_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = '{"Pricing Confusion": ["pricing", "cost"], "Payment Issues": ["payment", "failed"]}'
        mock_response.usage.total_tokens = 150
        agent.openai_client.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        tier2_subtopics = {'Refund': {}, 'Invoice': {}}  # Mock existing tier2
        
        result, token_count = await agent._discover_tier3_themes(sample_conversations_with_tier2_data, 'Billing Issues', tier2_subtopics)
        
        assert token_count == 150
        assert 'Pricing Confusion' in result
        assert 'Payment Issues' in result
        assert result['Pricing Confusion']['keywords'] == ['pricing', 'cost']
        assert result['Payment Issues']['keywords'] == ['payment', 'failed']
        assert result['Pricing Confusion']['method'] == 'llm_semantic'

    @pytest.mark.asyncio
    async def test_discover_tier3_themes_llm_failure(self, agent, sample_conversations_with_tier2_data):
        """Test graceful fallback when LLM call fails."""
        # Mock the OpenAI client to raise exception
        agent.openai_client = AsyncMock()
        agent.openai_client.client.chat.completions.create = AsyncMock(side_effect=Exception("LLM error"))
        
        tier2_subtopics = {}
        
        result, token_count = await agent._discover_tier3_themes(sample_conversations_with_tier2_data, 'Billing Issues', tier2_subtopics)
        
        assert result == {}
        assert token_count == 0

    @pytest.mark.asyncio
    async def test_execute_end_to_end(self, agent, mock_context_with_topics):
        """Async test of full execution with mocked LLM, verify output structure."""
        # Mock the OpenAI client
        agent.openai_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = '{"New Theme": ["keyword"]}'
        mock_response.usage.total_tokens = 100
        agent.openai_client.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        result = await agent.execute(mock_context_with_topics)
        
        assert result.success is True
        assert 'subtopics_by_tier1_topic' in result.data
        assert 'Billing Issues' in result.data['subtopics_by_tier1_topic']
        
        billing_data = result.data['subtopics_by_tier1_topic']['Billing Issues']
        assert 'tier2' in billing_data
        assert 'tier3' in billing_data
        assert isinstance(billing_data['tier2'], dict)
        assert isinstance(billing_data['tier3'], dict)

    @pytest.mark.asyncio
    async def test_execute_with_zero_topics(self, agent):
        """Test handling when no Tier 1 topics detected."""
        context = AgentContext(
            analysis_id='test_zero',
            analysis_type='test',
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc),
            conversations=[],
            previous_results={
                'TopicDetectionAgent': {
                    'data': {
                        'topic_distribution': {},
                        'topics_by_conversation': {}
                    }
                }
            }
        )
        
        result = await agent.execute(context)
        
        assert result.success is True
        assert result.data['subtopics_by_tier1_topic'] == {}
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_execute_token_counting(self, agent, mock_context_with_topics):
        """Verify token usage is tracked and returned in AgentResult.token_count."""
        # Mock the OpenAI client
        agent.openai_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = '{}'
        mock_response.usage.total_tokens = 200
        agent.openai_client.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        result = await agent.execute(mock_context_with_topics)
        
        assert result.token_count == 200

    def test_confidence_calculation(self, agent, mock_context_with_topics):
        """Test confidence scoring based on coverage and sample size."""
        # Mock the OpenAI client for execute
        agent.openai_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = '{}'
        mock_response.usage.total_tokens = 100
        agent.openai_client.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Test with full coverage (all conversations covered)
        import asyncio
        async def run_test():
            result = await agent.execute(mock_context_with_topics)
            # All conversations are covered, so confidence should be 1.0
            assert result.confidence == 1.0
            assert result.confidence_level == ConfidenceLevel.HIGH
        
        asyncio.run(run_test())
        
        # Test with partial coverage
        partial_context = mock_context_with_topics
        partial_context.conversations = mock_context_with_topics.conversations[:10]  # Half the conversations
        
        async def run_partial_test():
            result = await agent.execute(partial_context)
            expected_coverage = 10 / len(mock_context_with_topics.conversations)
            assert result.confidence == pytest.approx(expected_coverage, abs=0.01)
        
        asyncio.run(run_partial_test())
"""