"""
Integration tests for ExampleExtractionAgent

Tests end-to-end example extraction with realistic scenarios.
Validates timestamp fix works in production-like conditions.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

from src.agents.example_extraction_agent import ExampleExtractionAgent
from src.agents.base_agent import AgentContext, ConfidenceLevel


# ============================================================================
# Helper Functions
# ============================================================================

def create_conversation_with_timestamp(conv_id, timestamp_type, message, days_ago=0):
    """
    Create realistic conversation dict with specified timestamp type.
    
    Args:
        conv_id: Conversation ID
        timestamp_type: 'int', 'float', 'datetime', 'invalid', 'none'
        message: Customer message text
        days_ago: How many days ago conversation was created
        
    Returns:
        Conversation dict matching Intercom API structure
    """
    now = datetime.now(timezone.utc)
    conv_date = now - timedelta(days=days_ago)
    
    # Create timestamp based on type
    if timestamp_type == 'int':
        created_at = int(conv_date.timestamp())
    elif timestamp_type == 'float':
        created_at = conv_date.timestamp()
    elif timestamp_type == 'datetime':
        created_at = conv_date
    elif timestamp_type == 'invalid':
        created_at = -1
    elif timestamp_type == 'none':
        created_at = None
    else:
        created_at = int(conv_date.timestamp())
    
    return {
        'id': conv_id,
        'created_at': created_at,
        'updated_at': created_at if timestamp_type != 'none' else None,
        'customer_messages': [message],
        'full_text': f'Customer: {message}',
        'state': 'closed',
        'conversation_rating': 4 if days_ago < 7 else None
    }


def create_realistic_topic_conversations(count, sentiment_keywords):
    """
    Create realistic conversation list with varied characteristics.
    
    Args:
        count: Number of conversations to create
        sentiment_keywords: List of sentiment keywords to include
        
    Returns:
        List of conversations suitable for topic_conversations metadata
    """
    conversations = []
    
    # 70% integer timestamps (most common)
    int_count = int(count * 0.7)
    for i in range(int_count):
        keyword = sentiment_keywords[i % len(sentiment_keywords)]
        message = f"I {keyword} this feature because it impacts our workflow significantly. Message {i}."
        conversations.append(
            create_conversation_with_timestamp(
                conv_id=f'conv_int_{i}',
                timestamp_type='int',
                message=message,
                days_ago=i % 30
            )
        )
    
    # 20% datetime timestamps
    datetime_count = int(count * 0.2)
    for i in range(int_count, int_count + datetime_count):
        keyword = sentiment_keywords[i % len(sentiment_keywords)]
        message = f"The {keyword} experience with this feature is notable. Message {i}."
        conversations.append(
            create_conversation_with_timestamp(
                conv_id=f'conv_datetime_{i}',
                timestamp_type='datetime',
                message=message,
                days_ago=i % 20
            )
        )
    
    # 10% edge cases (float, None, invalid)
    remaining = count - len(conversations)
    for i in range(remaining):
        idx = len(conversations) + i
        if i % 3 == 0:
            ts_type = 'float'
        elif i % 3 == 1:
            ts_type = 'none'
        else:
            ts_type = 'invalid'
        
        keyword = sentiment_keywords[idx % len(sentiment_keywords)]
        message = f"Edge case conversation with {keyword} sentiment. Message {idx}."
        conversations.append(
            create_conversation_with_timestamp(
                conv_id=f'conv_edge_{idx}',
                timestamp_type=ts_type,
                message=message,
                days_ago=idx % 15
            )
        )
    
    return conversations


def assert_examples_valid(examples, min_count, max_count):
    """
    Validate example structure and content.
    
    Args:
        examples: List of examples to validate
        min_count: Minimum expected count
        max_count: Maximum expected count
    """
    assert isinstance(examples, list), "Examples should be a list"
    assert len(examples) >= min_count, f"Should have at least {min_count} examples"
    assert len(examples) <= max_count, f"Should have at most {max_count} examples"
    
    for example in examples:
        # Required fields
        assert 'preview' in example, "Example should have preview field"
        assert 'intercom_url' in example, "Example should have intercom_url field"
        assert 'conversation_id' in example, "Example should have conversation_id field"
        assert 'created_at' in example, "Example should have created_at field"
        
        # Field validation
        assert isinstance(example['preview'], str), "Preview should be string"
        assert len(example['preview']) > 0, "Preview should not be empty"
        assert len(example['preview']) <= 83, "Preview should be truncated"
        
        assert example['intercom_url'].startswith('https://app.intercom.com/'), \
            "Intercom URL should have correct format"
        
        assert isinstance(example['conversation_id'], str), "Conversation ID should be string"
        assert len(example['conversation_id']) > 0, "Conversation ID should not be empty"
        
        # Timestamp can be ISO string or None (handled gracefully)
        if example['created_at'] is not None:
            assert isinstance(example['created_at'], str), "created_at should be ISO string or None"


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_end_to_end_with_integer_timestamps():
    """CRITICAL TEST: End-to-end with ALL integer timestamps."""
    agent = ExampleExtractionAgent()
    
    # Create 50 conversations ALL with integer timestamps
    conversations = []
    now = datetime.now(timezone.utc)
    
    for i in range(50):
        conversations.append({
            'id': f'conv_int_{i}',
            'created_at': int((now - timedelta(days=i % 30)).timestamp()),
            'customer_messages': [
                f'I am frustrated with billing charges because they are unexpected. '
                f'This is causing issues for our team. Message {i}.'
            ],
            'full_text': f'Billing issue message {i}',
            'state': 'closed',
            'conversation_rating': 4 if i % 2 == 0 else None
        })
    
    context = AgentContext(
        analysis_id='test_int_timestamps',
        start_date=now - timedelta(days=30),
        end_date=now,
        conversations=[],
        metadata={
            'current_topic': 'Billing Issues',
            'sentiment_insight': 'Users frustrated with unexpected charges',
            'topic_conversations': conversations
        }
    )
    
    # Mock OpenAI client
    agent.openai_client = AsyncMock()
    agent.openai_client.generate_analysis = AsyncMock(return_value='[1, 2, 3, 4, 5]')
    
    result = await agent.execute(context)
    
    # Validate success
    assert result.success is True, "Execution should succeed"
    assert 'examples' in result.data, "Should have examples in result"
    
    examples = result.data['examples']
    assert len(examples) >= 3, "Should extract at least 3 examples"
    assert len(examples) <= 10, "Should extract at most 10 examples"
    
    # CRITICAL: All examples should have valid timestamps (timestamp conversion worked)
    for example in examples:
        assert example.get('created_at') is not None, \
            "Timestamp should not be None (conversion should work)"
        
        if example['created_at']:
            assert isinstance(example['created_at'], str), \
                "Timestamp should be ISO format string"
            # Should be valid ISO format (basic check)
            assert len(example['created_at']) > 10, "Should be valid date string"
    
    # Validate Intercom URLs
    for example in examples:
        assert example['intercom_url'].startswith('https://app.intercom.com/'), \
            "Should have valid Intercom URL"
    
    # Validate confidence
    assert result.confidence >= 0.0
    assert result.confidence <= 1.0


@pytest.mark.asyncio
async def test_end_to_end_with_mixed_timestamp_types():
    """Test with mixed timestamp types (int, datetime, float, None)."""
    agent = ExampleExtractionAgent()
    now = datetime.now(timezone.utc)
    
    conversations = []
    
    # 35 integer timestamps
    for i in range(35):
        conversations.append(
            create_conversation_with_timestamp(
                conv_id=f'conv_int_{i}',
                timestamp_type='int',
                message=f'Integer timestamp message {i} with enough detail to be useful',
                days_ago=i % 20
            )
        )
    
    # 10 datetime timestamps
    for i in range(35, 45):
        conversations.append(
            create_conversation_with_timestamp(
                conv_id=f'conv_dt_{i}',
                timestamp_type='datetime',
                message=f'Datetime timestamp message {i} with sufficient context',
                days_ago=i % 15
            )
        )
    
    # 3 float timestamps
    for i in range(45, 48):
        conversations.append(
            create_conversation_with_timestamp(
                conv_id=f'conv_float_{i}',
                timestamp_type='float',
                message=f'Float timestamp message {i} with good details',
                days_ago=i % 10
            )
        )
    
    # 2 None timestamps
    for i in range(48, 50):
        conversations.append(
            create_conversation_with_timestamp(
                conv_id=f'conv_none_{i}',
                timestamp_type='none',
                message=f'None timestamp message {i} should still work',
                days_ago=0
            )
        )
    
    context = AgentContext(
        analysis_id='test_mixed',
        start_date=now - timedelta(days=30),
        end_date=now,
        conversations=[],
        metadata={
            'current_topic': 'Product Features',
            'sentiment_insight': 'Mixed feedback on features',
            'topic_conversations': conversations
        }
    )
    
    agent.openai_client = AsyncMock()
    agent.openai_client.generate_analysis = AsyncMock(return_value='[1, 2, 3, 4, 5, 6]')
    
    result = await agent.execute(context)
    
    assert result.success is True
    assert len(result.data['examples']) >= 3
    assert_examples_valid(result.data['examples'], min_count=3, max_count=10)


@pytest.mark.asyncio
async def test_end_to_end_with_realistic_railway_data():
    """Test with realistic Railway production data simulation."""
    agent = ExampleExtractionAgent()
    now = datetime.now(timezone.utc)
    
    # Create 100 conversations mimicking real Railway data
    topics_data = {
        'Billing Issues': ['frustrated', 'confused', 'hate'],
        'Product Questions': ['wondering', 'confused', 'asking'],
        'Technical Problems': ['broken', 'error', 'failed']
    }
    
    conversations = []
    conv_id = 0
    
    for topic, keywords in topics_data.items():
        for i in range(33):  # ~33 per topic
            keyword = keywords[i % len(keywords)]
            message = f"I am {keyword} about this {topic.lower()} situation. " \
                     f"It has been affecting our team workflow significantly for the past few days. " \
                     f"Can someone help resolve this issue? Message {conv_id}."
            
            conversations.append({
                'id': f'conv_railway_{conv_id}',
                'created_at': int((now - timedelta(days=i % 30)).timestamp()),
                'customer_messages': [message],
                'full_text': f'Customer: {message}',
                'state': 'closed',
                'conversation_rating': 4 if i % 3 == 0 else None
            })
            conv_id += 1
    
    # Test execution for each topic
    for topic in topics_data.keys():
        # Filter conversations for this topic (simulate topic_conversations)
        topic_convs = [c for c in conversations if topic.lower() in c['full_text'].lower()]
        
        context = AgentContext(
            analysis_id=f'test_railway_{topic}',
            start_date=now - timedelta(days=30),
            end_date=now,
            conversations=[],
            metadata={
                'current_topic': topic,
                'sentiment_insight': f'Users experiencing {topic.lower()}',
                'topic_conversations': topic_convs
            }
        )
        
        agent.openai_client = AsyncMock()
        agent.openai_client.generate_analysis = AsyncMock(return_value='[1, 2, 3, 4, 5]')
        
        result = await agent.execute(context)
        
        assert result.success is True, f"Should succeed for topic: {topic}"
        assert len(result.data['examples']) >= 3, f"Should have examples for: {topic}"
        assert len(result.data['examples']) <= 10, f"Should not exceed max for: {topic}"


@pytest.mark.asyncio
async def test_end_to_end_with_high_quality_conversations():
    """Test with high-quality conversations."""
    agent = ExampleExtractionAgent()
    now = datetime.now(timezone.utc)
    
    conversations = []
    for i in range(20):
        # High quality: clear, recent, with ratings, good length
        message = f"I am very frustrated with the billing system because it keeps charging " \
                 f"incorrect amounts. This has happened multiple times over the past week and " \
                 f"is causing significant issues for our accounting team. Message {i}."
        
        conversations.append({
            'id': f'conv_quality_{i}',
            'created_at': int((now - timedelta(days=i % 7)).timestamp()),
            'customer_messages': [message],
            'full_text': f'Customer: {message}',
            'state': 'closed',
            'conversation_rating': 5
        })
    
    context = AgentContext(
        analysis_id='test_high_quality',
        start_date=now - timedelta(days=7),
        end_date=now,
        conversations=[],
        metadata={
            'current_topic': 'Billing System Issues',
            'sentiment_insight': 'Users very frustrated with billing errors',
            'topic_conversations': conversations
        }
    )
    
    agent.openai_client = AsyncMock()
    agent.openai_client.generate_analysis = AsyncMock(return_value='[1, 2, 3, 4, 5, 6, 7]')
    
    result = await agent.execute(context)
    
    assert result.success is True
    assert len(result.data['examples']) >= 5, "High quality should yield more examples"
    assert result.confidence >= 0.7, "High quality should have high confidence"


@pytest.mark.asyncio
async def test_end_to_end_with_low_quality_conversations():
    """Test with low-quality conversations."""
    agent = ExampleExtractionAgent()
    now = datetime.now(timezone.utc)
    
    conversations = []
    for i in range(20):
        # Low quality: short, old, no ratings
        conversations.append({
            'id': f'conv_low_{i}',
            'created_at': int((now - timedelta(days=40 + i)).timestamp()),
            'customer_messages': [f'Help {i}'],
            'full_text': f'Help {i}',
            'state': 'closed'
        })
    
    context = AgentContext(
        analysis_id='test_low_quality',
        start_date=now - timedelta(days=60),
        end_date=now,
        conversations=[],
        metadata={
            'current_topic': 'General Help',
            'sentiment_insight': 'Not much context',
            'topic_conversations': conversations
        }
    )
    
    agent.openai_client = AsyncMock()
    agent.openai_client.generate_analysis = AsyncMock(return_value='[1, 2]')
    
    result = await agent.execute(context)
    
    assert result.success is True
    # Low quality may yield few or no examples
    assert len(result.data.get('examples', [])) <= 5
    assert result.confidence < 0.7


@pytest.mark.asyncio
async def test_end_to_end_with_invalid_timestamps():
    """Test with problematic timestamps."""
    agent = ExampleExtractionAgent()
    now = datetime.now(timezone.utc)
    
    conversations = []
    
    # 10 with invalid negative timestamps
    for i in range(10):
        conversations.append({
            'id': f'conv_neg_{i}',
            'created_at': -1,
            'customer_messages': [f'Message with invalid negative timestamp {i}' * 5],
            'full_text': f'Message {i}',
            'state': 'closed'
        })
    
    # 10 with far future timestamps
    for i in range(10, 20):
        conversations.append({
            'id': f'conv_future_{i}',
            'created_at': 9999999999999,
            'customer_messages': [f'Message with far future timestamp {i}' * 5],
            'full_text': f'Message {i}',
            'state': 'closed'
        })
    
    # 10 with valid timestamps (control group)
    for i in range(20, 30):
        conversations.append({
            'id': f'conv_valid_{i}',
            'created_at': int((now - timedelta(days=i % 10)).timestamp()),
            'customer_messages': [f'Message with valid timestamp {i}' * 5],
            'full_text': f'Message {i}',
            'state': 'closed'
        })
    
    context = AgentContext(
        analysis_id='test_invalid',
        start_date=now - timedelta(days=30),
        end_date=now,
        conversations=[],
        metadata={
            'current_topic': 'Test Topic',
            'sentiment_insight': 'Test sentiment',
            'topic_conversations': conversations
        }
    )
    
    agent.openai_client = AsyncMock()
    agent.openai_client.generate_analysis = AsyncMock(return_value='[1, 2, 3, 4]')
    
    result = await agent.execute(context)
    
    # Should not crash despite invalid timestamps
    assert result.success is True
    # Should extract some examples (from valid timestamps)
    assert 'examples' in result.data


@pytest.mark.asyncio
async def test_end_to_end_performance_with_large_dataset():
    """Test performance with 500 conversations."""
    import time
    
    agent = ExampleExtractionAgent()
    now = datetime.now(timezone.utc)
    
    # Create 500 conversations
    conversations = create_realistic_topic_conversations(
        count=500,
        sentiment_keywords=['frustrated', 'confused', 'hate', 'love', 'appreciate']
    )
    
    context = AgentContext(
        analysis_id='test_performance',
        start_date=now - timedelta(days=30),
        end_date=now,
        conversations=[],
        metadata={
            'current_topic': 'Performance Test',
            'sentiment_insight': 'Mixed feedback',
            'topic_conversations': conversations
        }
    )
    
    agent.openai_client = AsyncMock()
    agent.openai_client.generate_analysis = AsyncMock(return_value='[1, 2, 3, 4, 5]')
    
    start_time = time.time()
    result = await agent.execute(context)
    execution_time = time.time() - start_time
    
    assert result.success is True
    assert execution_time < 10, f"Should complete in < 10 seconds, took {execution_time:.2f}s"
    assert len(result.data['examples']) >= 3


@pytest.mark.asyncio
async def test_end_to_end_with_llm_selection():
    """Test LLM selection is used correctly."""
    agent = ExampleExtractionAgent()
    now = datetime.now(timezone.utc)
    
    conversations = create_realistic_topic_conversations(
        count=30,
        sentiment_keywords=['frustrated', 'confused', 'disappointed']
    )
    
    context = AgentContext(
        analysis_id='test_llm',
        start_date=now - timedelta(days=30),
        end_date=now,
        conversations=[],
        metadata={
            'current_topic': 'Feature Issues',
            'sentiment_insight': 'Users frustrated with features',
            'topic_conversations': conversations
        }
    )
    
    # Mock OpenAI to return specific selections
    agent.openai_client = AsyncMock()
    agent.openai_client.generate_analysis = AsyncMock(return_value='[1, 5, 10, 15, 20]')
    
    result = await agent.execute(context)
    
    assert result.success is True
    assert len(result.data['examples']) >= 3
    # LLM should have been called
    assert agent.openai_client.generate_analysis.called


@pytest.mark.asyncio
async def test_end_to_end_with_llm_failure_fallback():
    """Test fallback to rule-based when LLM fails."""
    agent = ExampleExtractionAgent()
    now = datetime.now(timezone.utc)
    
    conversations = create_realistic_topic_conversations(
        count=30,
        sentiment_keywords=['error', 'broken', 'failed']
    )
    
    context = AgentContext(
        analysis_id='test_llm_failure',
        start_date=now - timedelta(days=30),
        end_date=now,
        conversations=[],
        metadata={
            'current_topic': 'Technical Errors',
            'sentiment_insight': 'Users experiencing errors',
            'topic_conversations': conversations
        }
    )
    
    # Mock OpenAI to raise exception
    agent.openai_client = AsyncMock()
    agent.openai_client.generate_analysis = AsyncMock(side_effect=Exception("LLM error"))
    
    result = await agent.execute(context)
    
    # Should still succeed with fallback
    assert result.success is True
    # Should still extract examples (rule-based fallback)
    assert 'examples' in result.data


# ============================================================================
# Edge Case Tests
# ============================================================================

@pytest.mark.asyncio
async def test_edge_case_all_timestamps_none():
    """Test all conversations with None timestamps."""
    agent = ExampleExtractionAgent()
    now = datetime.now(timezone.utc)
    
    conversations = []
    for i in range(20):
        conversations.append({
            'id': f'conv_none_{i}',
            'created_at': None,
            'customer_messages': [f'Message without timestamp {i}' * 10],
            'full_text': f'Message {i}',
            'state': 'closed'
        })
    
    context = AgentContext(
        analysis_id='test_all_none',
        start_date=now - timedelta(days=30),
        end_date=now,
        conversations=[],
        metadata={
            'current_topic': 'Test Topic',
            'sentiment_insight': 'Test sentiment',
            'topic_conversations': conversations
        }
    )
    
    agent.openai_client = AsyncMock()
    agent.openai_client.generate_analysis = AsyncMock(return_value='[1, 2, 3]')
    
    result = await agent.execute(context)
    
    # Should not crash
    assert result.success is True
    # Examples should be extracted (timestamps not required)
    if len(result.data.get('examples', [])) > 0:
        # All timestamps should be None
        for example in result.data['examples']:
            assert example.get('created_at') is None


@pytest.mark.asyncio
async def test_edge_case_missing_created_at_field():
    """Test conversations without created_at field."""
    agent = ExampleExtractionAgent()
    now = datetime.now(timezone.utc)
    
    conversations = []
    for i in range(20):
        conv = {
            'id': f'conv_missing_{i}',
            'customer_messages': [f'Message without created_at field {i}' * 10],
            'full_text': f'Message {i}',
            'state': 'closed'
        }
        # Deliberately omit created_at field
        conversations.append(conv)
    
    context = AgentContext(
        analysis_id='test_missing_field',
        start_date=now - timedelta(days=30),
        end_date=now,
        conversations=[],
        metadata={
            'current_topic': 'Test Topic',
            'sentiment_insight': 'Test sentiment',
            'topic_conversations': conversations
        }
    )
    
    agent.openai_client = AsyncMock()
    agent.openai_client.generate_analysis = AsyncMock(return_value='[1, 2, 3]')
    
    result = await agent.execute(context)
    
    # Should not crash
    assert result.success is True


@pytest.mark.asyncio
async def test_edge_case_timestamp_as_string():
    """Test conversations with timestamp as ISO string."""
    agent = ExampleExtractionAgent()
    now = datetime.now(timezone.utc)
    
    conversations = []
    for i in range(20):
        conversations.append({
            'id': f'conv_string_{i}',
            'created_at': (now - timedelta(days=i)).isoformat(),  # ISO string
            'customer_messages': [f'Message with string timestamp {i}' * 10],
            'full_text': f'Message {i}',
            'state': 'closed'
        })
    
    context = AgentContext(
        analysis_id='test_string_timestamp',
        start_date=now - timedelta(days=30),
        end_date=now,
        conversations=[],
        metadata={
            'current_topic': 'Test Topic',
            'sentiment_insight': 'Test sentiment',
            'topic_conversations': conversations
        }
    )
    
    agent.openai_client = AsyncMock()
    agent.openai_client.generate_analysis = AsyncMock(return_value='[1, 2, 3]')
    
    result = await agent.execute(context)
    
    # Should handle string timestamps gracefully
    assert result.success is True


# ============================================================================
# Validation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_example_structure_validation():
    """Test example structure is correct."""
    agent = ExampleExtractionAgent()
    now = datetime.now(timezone.utc)
    
    conversations = create_realistic_topic_conversations(
        count=20,
        sentiment_keywords=['frustrated', 'confused']
    )
    
    context = AgentContext(
        analysis_id='test_structure',
        start_date=now - timedelta(days=30),
        end_date=now,
        conversations=[],
        metadata={
            'current_topic': 'Structure Test',
            'sentiment_insight': 'Testing structure',
            'topic_conversations': conversations
        }
    )
    
    agent.openai_client = AsyncMock()
    agent.openai_client.generate_analysis = AsyncMock(return_value='[1, 2, 3, 4, 5]')
    
    result = await agent.execute(context)
    
    assert result.success is True
    
    # Validate each example
    for example in result.data['examples']:
        # Check required fields
        assert 'preview' in example
        assert 'intercom_url' in example
        assert 'conversation_id' in example
        assert 'created_at' in example
        
        # Validate preview
        assert isinstance(example['preview'], str)
        assert 1 <= len(example['preview']) <= 83
        
        # Validate URL
        assert example['intercom_url'].startswith('https://app.intercom.com/')
        
        # Validate conversation_id
        assert isinstance(example['conversation_id'], str)
        assert len(example['conversation_id']) > 0
        
        # Validate timestamp (can be string or None)
        if example['created_at'] is not None:
            assert isinstance(example['created_at'], str)


@pytest.mark.asyncio
async def test_example_count_validation():
    """Test example count stays within bounds."""
    agent = ExampleExtractionAgent()
    now = datetime.now(timezone.utc)
    
    # Create 100 conversations (more than max)
    conversations = create_realistic_topic_conversations(
        count=100,
        sentiment_keywords=['frustrated', 'confused', 'hate', 'love']
    )
    
    context = AgentContext(
        analysis_id='test_count',
        start_date=now - timedelta(days=30),
        end_date=now,
        conversations=[],
        metadata={
            'current_topic': 'Count Test',
            'sentiment_insight': 'Testing count limits',
            'topic_conversations': conversations
        }
    )
    
    agent.openai_client = AsyncMock()
    agent.openai_client.generate_analysis = AsyncMock(return_value='[1, 2, 3, 4, 5, 6, 7, 8]')
    
    result = await agent.execute(context)
    
    assert result.success is True
    
    # Count should be within bounds
    example_count = len(result.data['examples'])
    assert 3 <= example_count <= 10, f"Example count {example_count} outside bounds [3, 10]"
    
    # Metadata should match
    if 'selected_count' in result.data:
        assert result.data['selected_count'] == example_count
    
    if 'total_available' in result.data:
        assert result.data['total_available'] <= len(conversations)

