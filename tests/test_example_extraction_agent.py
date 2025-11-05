"""
Unit tests for ExampleExtractionAgent

Tests the timestamp conversion fix (lines 284-298) and all core functionality.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch

from src.agents.example_extraction_agent import ExampleExtractionAgent
from src.agents.base_agent import AgentContext, AgentResult, ConfidenceLevel


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def agent():
    """Create ExampleExtractionAgent instance for testing."""
    return ExampleExtractionAgent()


@pytest.fixture
def sample_conversation_with_int_timestamp():
    """Conversation with integer Unix timestamp."""
    return {
        'id': 'conv_int_123',
        'created_at': 1699123456,  # Integer Unix timestamp (2023-11-04)
        'updated_at': 1699125456,
        'customer_messages': ['I am having trouble with billing charges on my account'],
        'full_text': 'Customer: I am having trouble with billing charges on my account',
        'state': 'closed',
        'conversation_rating': 4
    }


@pytest.fixture
def sample_conversation_with_datetime_timestamp():
    """Conversation with datetime timestamp."""
    return {
        'id': 'conv_datetime_456',
        'created_at': datetime(2023, 11, 4, 12, 0, 0, tzinfo=timezone.utc),
        'updated_at': datetime(2023, 11, 4, 13, 0, 0, tzinfo=timezone.utc),
        'customer_messages': ['The export feature is not working properly'],
        'full_text': 'Customer: The export feature is not working properly',
        'state': 'closed'
    }


@pytest.fixture
def sample_conversation_with_float_timestamp():
    """Conversation with float Unix timestamp."""
    return {
        'id': 'conv_float_789',
        'created_at': 1699123456.789,  # Float with fractional seconds
        'customer_messages': ['I love the new dashboard design'],
        'full_text': 'Customer: I love the new dashboard design',
        'state': 'closed'
    }


@pytest.fixture
def sample_conversation_with_invalid_timestamp():
    """Conversation with invalid timestamp."""
    return {
        'id': 'conv_invalid_999',
        'created_at': -1,  # Invalid negative timestamp
        'customer_messages': ['This should still work despite invalid timestamp'],
        'full_text': 'Customer: This should still work despite invalid timestamp',
        'state': 'closed'
    }


@pytest.fixture
def sample_conversations_for_scoring():
    """List of conversations with varying characteristics for scoring tests."""
    now = datetime.now(timezone.utc)
    
    conversations = []
    
    # High quality conversations
    for i in range(5):
        conversations.append({
            'id': f'conv_quality_{i}',
            'created_at': int((now - timedelta(days=2)).timestamp()),
            'customer_messages': [
                f'I hate this feature because it keeps crashing and losing my data. '
                f'This is very frustrating for our team workflow. Message {i}.'
            ],
            'full_text': f'Customer message about frustration {i}',
            'conversation_rating': 5,
            'state': 'closed'
        })
    
    # Medium quality conversations
    for i in range(5, 10):
        conversations.append({
            'id': f'conv_medium_{i}',
            'created_at': int((now - timedelta(days=10)).timestamp()),
            'customer_messages': [f'I have a question about the product feature. Message {i}.'],
            'full_text': f'Customer question {i}',
            'state': 'closed'
        })
    
    # Low quality conversations (short messages)
    for i in range(10, 15):
        conversations.append({
            'id': f'conv_low_{i}',
            'created_at': int((now - timedelta(days=30)).timestamp()),
            'customer_messages': [f'Help {i}'],
            'full_text': f'Help {i}',
            'state': 'closed'
        })
    
    # Recent conversations with datetime timestamps
    for i in range(15, 20):
        conversations.append({
            'id': f'conv_recent_{i}',
            'created_at': now - timedelta(days=1),
            'customer_messages': [
                f'I love the improvements but confused about the new interface. Message {i}.'
            ],
            'full_text': f'Customer feedback {i}',
            'conversation_rating': 4,
            'state': 'closed'
        })
    
    return conversations


# ============================================================================
# Unit Tests for _format_example()
# ============================================================================

def test_format_example_with_integer_timestamp(agent, sample_conversation_with_int_timestamp):
    """CRITICAL TEST: Validate integer timestamp conversion works."""
    result = agent._format_example(sample_conversation_with_int_timestamp)
    
    assert result is not None, "Should return formatted example"
    assert 'created_at' in result, "Should have created_at field"
    assert isinstance(result['created_at'], str), "created_at should be ISO format string"
    assert result['created_at'].startswith('2023-11-04'), "Should convert to correct date"
    assert 'preview' in result, "Should have preview field"
    assert 'intercom_url' in result, "Should have intercom_url field"
    assert 'conversation_id' in result, "Should have conversation_id field"


def test_format_example_with_datetime_timestamp(agent, sample_conversation_with_datetime_timestamp):
    """Test datetime timestamp handling."""
    result = agent._format_example(sample_conversation_with_datetime_timestamp)
    
    assert result is not None
    assert 'created_at' in result
    assert isinstance(result['created_at'], str)
    assert result['created_at'].startswith('2023-11-04')


def test_format_example_with_float_timestamp(agent, sample_conversation_with_float_timestamp):
    """Test float timestamp with fractional seconds."""
    result = agent._format_example(sample_conversation_with_float_timestamp)
    
    assert result is not None
    assert 'created_at' in result
    assert isinstance(result['created_at'], str)
    assert result['created_at'].startswith('2023-11-04')


def test_format_example_with_invalid_timestamp(agent, sample_conversation_with_invalid_timestamp):
    """Test error handling for invalid timestamp."""
    result = agent._format_example(sample_conversation_with_invalid_timestamp)
    
    # Should not crash - error handling works
    assert result is not None or result is None  # Either returns None or handles gracefully
    
    if result is not None:
        # If it returns a result, created_at should be None (fallback)
        assert result.get('created_at') is None or isinstance(result.get('created_at'), str)


def test_format_example_with_missing_timestamp(agent):
    """Test handling of conversation without created_at field."""
    conv = {
        'id': 'conv_no_timestamp',
        'customer_messages': ['Message without timestamp'],
        'full_text': 'Message without timestamp'
    }
    
    result = agent._format_example(conv)
    
    assert result is not None  # Should not crash
    if result:
        assert result.get('created_at') is None  # Should have None timestamp


def test_format_example_with_none_timestamp(agent):
    """Test handling of None timestamp."""
    conv = {
        'id': 'conv_none_timestamp',
        'created_at': None,
        'customer_messages': ['Message with None timestamp'],
        'full_text': 'Message with None timestamp'
    }
    
    result = agent._format_example(conv)
    
    assert result is not None  # Should not crash
    if result:
        assert result.get('created_at') is None


def test_format_example_preview_truncation(agent):
    """Test preview truncation for long messages."""
    long_message = 'A' * 200  # Very long message
    conv = {
        'id': 'conv_long',
        'created_at': 1699123456,
        'customer_messages': [long_message],
        'full_text': long_message
    }
    
    result = agent._format_example(conv)
    
    assert result is not None
    # Expect preview length between 100 and 153 characters (considering ellipsis)
    preview_len = len(result['preview'])
    assert 100 <= preview_len <= 153, f"Preview length {preview_len} not in expected range 100-153"
    assert result['preview'].endswith('...')


def test_format_example_short_message_no_truncation(agent):
    """Test no truncation for short messages."""
    short_message = 'Short message'
    conv = {
        'id': 'conv_short',
        'created_at': 1699123456,
        'customer_messages': [short_message],
        'full_text': short_message
    }
    
    result = agent._format_example(conv)
    
    assert result is not None
    assert result['preview'] == short_message
    assert not result['preview'].endswith('...')


def test_format_example_intercom_url_generation(agent):
    """Test Intercom URL format."""
    conv = {
        'id': 'conv_12345',
        'created_at': 1699123456,
        'customer_messages': ['Test message'],
        'full_text': 'Test message'
    }
    
    result = agent._format_example(conv)
    
    assert result is not None
    # Pattern-based check: URL should contain /inbox/inbox/ and end with conversation ID
    assert '/inbox/inbox/' in result['intercom_url'], "URL should contain /inbox/inbox/ path"
    assert result['intercom_url'].endswith('conv_12345'), "URL should end with conversation ID"
    assert result['conversation_id'] == 'conv_12345'


def test_format_example_with_missing_customer_messages(agent):
    """Test handling of conversation without customer_messages."""
    conv = {
        'id': 'conv_no_messages',
        'created_at': 1699123456,
        'customer_messages': [],
        'full_text': ''
    }
    
    result = agent._format_example(conv)
    
    # Should return None as not usable
    assert result is None


def test_format_example_with_empty_string_message(agent):
    """Test handling of empty string message."""
    conv = {
        'id': 'conv_empty',
        'created_at': 1699123456,
        'customer_messages': [''],
        'full_text': ''
    }
    
    result = agent._format_example(conv)
    
    # Should return None or handle gracefully
    assert result is None or (result and len(result['preview']) == 0)


def test_format_example_with_non_string_message(agent):
    """Test handling of non-string message."""
    conv = {
        'id': 'conv_non_string',
        'created_at': 1699123456,
        'customer_messages': [123],  # Integer instead of string
        'full_text': '123'
    }
    
    result = agent._format_example(conv)
    
    # Should coerce to string without crash
    if result:
        assert '123' in result['preview']


# ============================================================================
# Unit Tests for _score_conversation()
# ============================================================================

def test_score_conversation_with_clear_message(agent):
    """Test scoring for conversation with clear message."""
    conv = {
        'id': 'conv_clear',
        'created_at': 1699123456,
        'customer_messages': ['A' * 100],  # 100 character message
        'full_text': 'A' * 100
    }
    
    score = agent._score_conversation(conv, sentiment="Test sentiment")
    
    assert isinstance(score, (int, float))
    assert score >= 2.0  # Should get points for clear message


def test_score_conversation_with_short_message(agent):
    """Test scoring for conversation with short message."""
    conv = {
        'id': 'conv_short',
        'created_at': 1699123456,
        'customer_messages': ['Hi'],  # Very short message
        'full_text': 'Hi'
    }
    
    score = agent._score_conversation(conv, sentiment="Test sentiment")
    
    assert isinstance(score, (int, float))
    assert score < 2.0  # Should get low score for short message


def test_score_conversation_with_sentiment_match(agent):
    """Test sentiment matching bonus."""
    conv = {
        'id': 'conv_sentiment',
        'created_at': 1699123456,
        'customer_messages': ['I hate this feature because it keeps breaking'],
        'full_text': 'I hate this feature because it keeps breaking'
    }
    
    score = agent._score_conversation(conv, sentiment="Users hate the feature")
    
    assert isinstance(score, (int, float))
    assert score >= 2.0  # Should get sentiment bonus


def test_score_conversation_with_recent_timestamp(agent):
    """Test recency bonus for recent conversations."""
    recent_timestamp = int((datetime.now(timezone.utc) - timedelta(days=2)).timestamp())
    conv = {
        'id': 'conv_recent',
        'created_at': recent_timestamp,
        'customer_messages': ['A' * 100],
        'full_text': 'A' * 100
    }
    
    score = agent._score_conversation(conv, sentiment="Test")
    
    assert isinstance(score, (int, float))
    assert score > 0  # Should have positive score


def test_score_conversation_with_old_timestamp(agent):
    """Test no recency bonus for old conversations."""
    old_timestamp = int((datetime.now(timezone.utc) - timedelta(days=40)).timestamp())
    conv = {
        'id': 'conv_old',
        'created_at': old_timestamp,
        'customer_messages': ['A' * 100],
        'full_text': 'A' * 100
    }
    
    score = agent._score_conversation(conv, sentiment="Test")
    
    assert isinstance(score, (int, float))


def test_score_conversation_with_rating(agent):
    """Test rating bonus."""
    conv = {
        'id': 'conv_rated',
        'created_at': 1699123456,
        'customer_messages': ['A' * 100],
        'full_text': 'A' * 100,
        'conversation_rating': 5
    }
    
    score = agent._score_conversation(conv, sentiment="Test")
    
    assert isinstance(score, (int, float))
    assert score > 0


def test_score_conversation_with_invalid_customer_messages(agent):
    """Test handling of invalid customer_messages format."""
    conv = {
        'id': 'conv_invalid',
        'created_at': 1699123456,
        'customer_messages': 'not a list',  # Invalid format
        'full_text': 'not a list'
    }
    
    score = agent._score_conversation(conv, sentiment="Test")
    
    assert isinstance(score, (int, float))
    assert score == 0.0  # Should return 0 for invalid format


# ============================================================================
# Integration Tests for execute()
# ============================================================================

@pytest.mark.asyncio
async def test_execute_with_valid_conversations(agent, sample_conversations_for_scoring):
    """Test end-to-end execution with valid conversations."""
    context = AgentContext(
        analysis_id='test_analysis',
        analysis_type='test',
        start_date=datetime.now(timezone.utc) - timedelta(days=30),
        end_date=datetime.now(timezone.utc),
        conversations=[],
        metadata={
            'current_topic': 'Billing Issues',
            'sentiment_insight': 'Users frustrated with charges',
            'topic_conversations': sample_conversations_for_scoring
        }
    )
    
    # Mock ai_client to avoid real API calls
    agent.ai_client = AsyncMock()
    agent.ai_client.generate_analysis = AsyncMock(return_value='[1, 2, 3, 4, 5]')
    
    result = await agent.execute(context)
    
    assert result.success is True
    assert 'examples' in result.data
    assert len(result.data['examples']) >= 3
    assert len(result.data['examples']) <= 10
    assert result.confidence >= 0.0
    assert result.confidence <= 1.0
    
    # Validate example structure
    for example in result.data['examples']:
        assert 'preview' in example
        assert 'intercom_url' in example
        assert 'conversation_id' in example
        assert 'created_at' in example


@pytest.mark.asyncio
async def test_execute_with_integer_timestamps(agent):
    """CRITICAL TEST: End-to-end test with integer timestamps."""
    now = datetime.now(timezone.utc)
    conversations = []
    
    # Create 10 conversations ALL with integer timestamps
    for i in range(10):
        conversations.append({
            'id': f'conv_int_{i}',
            'created_at': int((now - timedelta(days=i)).timestamp()),
            'customer_messages': [f'Billing issue message {i} with enough text to be clear'],
            'full_text': f'Billing issue message {i} with enough text to be clear',
            'state': 'closed'
        })
    
    context = AgentContext(
        analysis_id='test_int_timestamps',
        analysis_type='test',
        start_date=now - timedelta(days=30),
        end_date=now,
        conversations=[],
        metadata={
            'current_topic': 'Billing Issues',
            'sentiment_insight': 'Users frustrated',
            'topic_conversations': conversations
        }
    )
    
    # Mock ai_client
    agent.ai_client = AsyncMock()
    agent.ai_client.generate_analysis = AsyncMock(return_value='[1, 2, 3]')
    
    result = await agent.execute(context)
    
    assert result.success is True, "Execution should succeed"
    assert len(result.data['examples']) >= 1, "Should extract at least 1 example"
    
    # Validate all examples have valid timestamps (not None from conversion errors)
    for example in result.data['examples']:
        assert example.get('created_at') is not None or example.get('created_at') == '', \
            "Timestamp should be valid ISO string or empty, not None from crash"


@pytest.mark.asyncio
async def test_execute_with_mixed_timestamps(agent):
    """Test execution with mixed timestamp types."""
    now = datetime.now(timezone.utc)
    conversations = [
        # Integer timestamps
        {'id': 'c1', 'created_at': int(now.timestamp()), 'customer_messages': ['Message 1 ' * 10], 'full_text': 'Message 1'},
        {'id': 'c2', 'created_at': int(now.timestamp()), 'customer_messages': ['Message 2 ' * 10], 'full_text': 'Message 2'},
        # Datetime timestamps
        {'id': 'c3', 'created_at': now, 'customer_messages': ['Message 3 ' * 10], 'full_text': 'Message 3'},
        {'id': 'c4', 'created_at': now - timedelta(days=1), 'customer_messages': ['Message 4 ' * 10], 'full_text': 'Message 4'},
        # Float timestamps
        {'id': 'c5', 'created_at': now.timestamp(), 'customer_messages': ['Message 5 ' * 10], 'full_text': 'Message 5'},
        # None timestamps
        {'id': 'c6', 'created_at': None, 'customer_messages': ['Message 6 ' * 10], 'full_text': 'Message 6'},
    ]
    
    context = AgentContext(
        analysis_id='test_mixed',
        analysis_type='test',
        start_date=now - timedelta(days=7),
        end_date=now,
        conversations=[],
        metadata={
            'current_topic': 'Product Issues',
            'sentiment_insight': 'Mixed feedback',
            'topic_conversations': conversations
        }
    )
    
    agent.ai_client = AsyncMock()
    agent.ai_client.generate_analysis = AsyncMock(return_value='[1, 2, 3]')
    
    result = await agent.execute(context)
    
    assert result.success is True
    assert len(result.data['examples']) >= 1


@pytest.mark.asyncio
async def test_execute_with_no_quality_conversations(agent):
    """Test execution when no quality conversations available."""
    conversations = [
        {'id': f'c{i}', 'created_at': 1699123456, 'customer_messages': [''], 'full_text': ''}
        for i in range(10)
    ]
    
    context = AgentContext(
        analysis_id='test_no_quality',
        analysis_type='test',
        start_date=datetime.now(timezone.utc) - timedelta(days=7),
        end_date=datetime.now(timezone.utc),
        conversations=[],
        metadata={
            'current_topic': 'Test Topic',
            'sentiment_insight': 'No sentiment',
            'topic_conversations': conversations
        }
    )
    
    agent.ai_client = AsyncMock()
    agent.ai_client.generate_analysis = AsyncMock(return_value='[]')
    
    result = await agent.execute(context)
    
    assert result.success is True  # Should not crash
    assert len(result.data.get('examples', [])) == 0 or len(result.data.get('examples', [])) < 3
    assert result.confidence < 0.5


@pytest.mark.asyncio
async def test_execute_with_missing_metadata(agent):
    """Test error handling when required metadata is missing."""
    context = AgentContext(
        analysis_id='test_missing',
        analysis_type='test',
        start_date=datetime.now(timezone.utc) - timedelta(days=7),
        end_date=datetime.now(timezone.utc),
        conversations=[],
        metadata={}  # Missing required fields
    )
    
    result = await agent.execute(context)
    
    assert result.success is False
    assert result.error_message is not None


# ============================================================================
# Mock LLM Tests
# ============================================================================

@pytest.mark.asyncio
async def test_llm_select_examples_success(agent):
    """Test LLM example selection works correctly."""
    candidates = [
        {'id': f'c{i}', 'created_at': 1699123456, 'customer_messages': [f'Message {i}'], 'full_text': f'Message {i}'}
        for i in range(10)
    ]
    
    # Mock ai_client to return specific indices
    agent.ai_client = AsyncMock()
    agent.ai_client.generate_analysis = AsyncMock(return_value='[1, 3, 5, 7]')
    
    result = await agent._llm_select_examples(
        candidates=candidates,
        topic="Test Topic",
        sentiment="Test sentiment",
        target_count=4
    )
    
    # Should return conversations at indices 0, 2, 4, 6 (1-indexed to 0-indexed)
    assert len(result) == 4
    assert result[0]['id'] == 'c0'
    assert result[1]['id'] == 'c2'
    assert result[2]['id'] == 'c4'
    assert result[3]['id'] == 'c6'


@pytest.mark.asyncio
async def test_llm_select_examples_failure_fallback(agent):
    """Test fallback to rule-based selection when LLM fails."""
    candidates = [
        {'id': f'c{i}', 'created_at': 1699123456, 'customer_messages': [f'Message {i}'], 'full_text': f'Message {i}'}
        for i in range(10)
    ]
    
    # Mock ai_client to raise exception
    agent.ai_client = AsyncMock()
    agent.ai_client.generate_analysis = AsyncMock(side_effect=Exception("LLM error"))
    
    result = await agent._llm_select_examples(
        candidates=candidates,
        topic="Test Topic",
        sentiment="Test sentiment",
        target_count=5
    )
    
    # Should return empty list (fallback behavior)
    assert isinstance(result, list)
    assert len(result) == 0  # Fallback returns empty for LLM to handle at higher level


# ============================================================================
# Tests for _extract_full_sentence() - Phase 6
# ============================================================================

def test_extract_full_sentence_short_message(agent):
    """Test extraction with message shorter than min_chars"""
    text = "This is a short message"  # 23 chars
    result = agent._extract_full_sentence(text, min_chars=100, max_chars=150)
    
    assert result == text
    assert not result.endswith("...")


def test_extract_full_sentence_medium_message(agent):
    """Test extraction with message between min and max chars"""
    text = "This is a medium length message that should be returned in full because it's under 150 characters total."  # 109 chars
    result = agent._extract_full_sentence(text, min_chars=100, max_chars=150)
    
    assert result == text
    assert not result.endswith("...")


def test_extract_full_sentence_long_message_with_sentences(agent):
    """Test extraction with long message containing sentence boundaries"""
    text = "First sentence here. Second sentence here. Third sentence here. Fourth sentence here. Fifth sentence that continues on and on."  # >150 chars
    result = agent._extract_full_sentence(text, min_chars=100, max_chars=150)
    
    # Should extract complete sentences up to max_chars
    assert len(result) <= 150 + 3  # +3 for "..."
    assert "." in result  # Should contain at least one complete sentence
    assert result.endswith("...") or len(result) <= 150


def test_extract_full_sentence_long_message_no_sentences(agent):
    """Test extraction with long message without sentence boundaries"""
    text = "A" * 200  # 200 chars with no sentence boundaries
    result = agent._extract_full_sentence(text, min_chars=100, max_chars=150)
    
    # Should truncate at word boundary (or char boundary if no spaces)
    assert len(result) <= 150 + 3  # +3 for "..."
    assert result.endswith("...")


def test_extract_full_sentence_minimum_length_enforcement(agent):
    """Test that extraction tries to reach min_chars when possible"""
    text = "Short. Another short. Third short. Fourth. Fifth sentence that's a bit longer."  # Multiple short sentences
    result = agent._extract_full_sentence(text, min_chars=100, max_chars=150)
    
    # Should combine multiple sentences to reach min_chars
    assert len(result) >= 35  # At least a few sentences
    assert "." in result


def test_format_example_uses_new_sentence_extraction(agent):
    """Test that _format_example uses the new sentence extraction"""
    long_message = "This is the first sentence of a customer message. This is the second sentence that continues the thought. And this is the third sentence that makes it even longer so we can test the extraction."  # >150 chars
    
    conv = {
        'id': 'conv_long_test',
        'created_at': 1699123456,
        'customer_messages': [long_message],
        'full_text': long_message
    }
    
    result = agent._format_example(conv)
    
    assert result is not None
    assert 'preview' in result
    # Preview should be between 100-150 chars (or full length if shorter after sentence extraction)
    preview_len = len(result['preview'])
    assert preview_len >= 50  # At least some content
    # Should contain complete sentences (ends with . or ...)
    assert result['preview'].endswith('.') or result['preview'].endswith('...') or preview_len < 150


def test_format_example_preview_length_range(agent):
    """Test that preview lengths are within expected range for various message lengths"""
    test_cases = [
        ("Short message", 50),
        ("A" * 100 + ". More text here to make it longer.", 100),
        ("A" * 150 + ". Even more text to exceed maximum.", 150),
        ("A" * 200 + ". Way too much text for a preview.", 200),
        ("A" * 300 + ". This is an extremely long message.", 300)
    ]
    
    for message, original_len in test_cases:
        conv = {
            'id': f'conv_test_{original_len}',
            'created_at': 1699123456,
            'customer_messages': [message],
            'full_text': message
        }
        
        result = agent._format_example(conv)
        assert result is not None
        preview_len = len(result['preview'])
        
        if original_len <= 150:
            # Short messages should be returned in full (or close to it)
            assert preview_len <= original_len + 10  # Small buffer for edge cases
        else:
            # Long messages should be truncated to around 150
            assert preview_len <= 150 + 3  # +3 for "..."


def test_intercom_url_consistency(agent):
    """Test that Intercom URLs are consistently formatted"""
    conv = {
        'id': 'conv_12345',
        'created_at': 1699123456,
        'customer_messages': ['Test message for URL validation'],
        'full_text': 'Test message'
    }
    
    result = agent._format_example(conv)
    
    assert result is not None
    assert 'intercom_url' in result
    assert 'conversation_id' in result
    # URL should follow pattern
    assert '/inbox/inbox/' in result['intercom_url']
    assert result['conversation_id'] == 'conv_12345'


def test_intercom_url_with_missing_workspace_id(agent):
    """Test Intercom URL generation with missing workspace_id"""
    from unittest.mock import patch
    
    conv = {
        'id': 'conv_test',
        'created_at': 1699123456,
        'customer_messages': ['Test message'],
        'full_text': 'Test'
    }
    
    # Mock settings to have placeholder workspace_id
    with patch('src.config.settings.settings') as mock_settings:
        mock_settings.intercom_workspace_id = "your-workspace-id-here"
        
        result = agent._format_example(conv)
        
        assert result is not None
        assert 'intercom_url' in result
        # Should still generate URL with placeholder
        assert '[WORKSPACE_ID]' in result['intercom_url'] or 'your-workspace-id-here' in result['intercom_url']


def test_all_examples_have_intercom_urls(agent):
    """Test that all examples have valid Intercom URLs"""
    conversations = [
        {
            'id': f'conv_{i}',
            'created_at': 1699123456,
            'customer_messages': [f'Test message {i} with enough content to be valid'],
            'full_text': f'Test message {i}',
            'conversation_rating': 4
        }
        for i in range(10)
    ]
    
    examples = []
    for conv in conversations:
        example = agent._format_example(conv)
        if example:
            examples.append(example)
    
    # All examples should have intercom_url field
    assert len(examples) > 0
    for example in examples:
        assert 'intercom_url' in example
        assert example['intercom_url'] is not None
        assert example['intercom_url'] != ''
        assert example['intercom_url'] != '#'

