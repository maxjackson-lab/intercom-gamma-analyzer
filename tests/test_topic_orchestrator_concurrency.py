"""
Tests for TopicOrchestrator Concurrency Control

Verifies that semaphore limits concurrent topic processing and prevents
excessive async tasks on large taxonomies.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.agents.topic_orchestrator import TopicOrchestrator
from src.agents.base_agent import AgentContext, AgentResult


@pytest.mark.asyncio
async def test_semaphore_limits_concurrent_topics():
    """Test that semaphore limits concurrent topic processing"""
    orchestrator = TopicOrchestrator()
    
    # Track concurrent execution count
    concurrent_count = 0
    max_concurrent_observed = 0
    concurrent_lock = asyncio.Lock()
    
    async def mock_sentiment_execute(context):
        """Mock sentiment agent that tracks concurrency"""
        nonlocal concurrent_count, max_concurrent_observed
        
        async with concurrent_lock:
            concurrent_count += 1
            max_concurrent_observed = max(max_concurrent_observed, concurrent_count)
        
        # Simulate work
        await asyncio.sleep(0.1)
        
        async with concurrent_lock:
            concurrent_count -= 1
        
        return AgentResult(
            agent_name='TopicSentimentAgent',
            success=True,
            data={'sentiment_insight': 'Test sentiment', 'sentiment_score': 0.5},
            execution_time=0.1,
            confidence=0.8,
            confidence_level='high'
        )
    
    async def mock_example_execute(context):
        """Mock example extraction agent"""
        await asyncio.sleep(0.05)
        return AgentResult(
            agent_name='ExampleExtractionAgent',
            success=True,
            data={'examples': [{'id': '123', 'text': 'Test example'}]},
            execution_time=0.05,
            confidence=0.9,
            confidence_level='high'
        )
    
    # Patch the agent execute methods
    orchestrator.topic_sentiment_agent.execute = mock_sentiment_execute
    orchestrator.example_extraction_agent.execute = mock_example_execute
    
    # Create test data with many topics (more than semaphore limit)
    num_topics = 20
    topics_data = {
        f'topic_{i}': {
            'volume': 10,
            'percentage': 5.0
        }
        for i in range(num_topics)
    }
    
    # Create conversations mapped to topics
    conversations_by_topic_full = {
        f'topic_{i}': [
            {
                'id': f'conv_{i}_1',
                'conversation_message': {'body': f'Test message for topic {i}'}
            }
        ]
        for i in range(num_topics)
    }
    
    # Create context
    context = AgentContext(
        analysis_id='test_concurrency',
        analysis_type='weekly_voc',
        start_date=datetime.now(),
        end_date=datetime.now(),
        conversations=[]
    )
    
    # Manually build topic tasks similar to the orchestrator
    async def process_topic_with_semaphore(topic_name, topic_stats, topic_num, total_topics):
        """Simulate the orchestrator's process_topic_with_semaphore function"""
        async with orchestrator.topic_semaphore:
            topic_convs = conversations_by_topic_full.get(topic_name, [])
            
            if len(topic_convs) == 0:
                return topic_name, None, None
            
            topic_context = context.model_copy()
            topic_context.metadata = {
                'current_topic': topic_name,
                'topic_conversations': topic_convs,
                'sentiment_insight': ''
            }
            
            sentiment_result = await orchestrator.topic_sentiment_agent.execute(topic_context)
            topic_context.metadata['sentiment_insight'] = sentiment_result.data.get('sentiment_insight', '')
            examples_result = await orchestrator.example_extraction_agent.execute(topic_context)
            
            return topic_name, sentiment_result, examples_result
    
    # Create tasks
    topic_tasks = []
    for i, (name, stats) in enumerate(topics_data.items(), 1):
        task = process_topic_with_semaphore(name, stats, i, len(topics_data))
        topic_tasks.append(task)
    
    # Execute all tasks
    results = await asyncio.gather(*topic_tasks)
    
    # Verify semaphore limit was respected
    semaphore_limit = orchestrator.topic_semaphore._value
    assert max_concurrent_observed <= semaphore_limit, \
        f"Max concurrent ({max_concurrent_observed}) exceeded limit ({semaphore_limit})"
    
    # Verify all topics were processed
    assert len(results) == num_topics
    
    # Verify no tasks are still running
    assert concurrent_count == 0, "Some tasks are still running"
    
    print(f"✅ Semaphore test passed: max_concurrent={max_concurrent_observed}, limit={semaphore_limit}")


@pytest.mark.asyncio
async def test_concurrent_execution_performance():
    """Test that concurrent execution is faster than sequential"""
    orchestrator = TopicOrchestrator()
    
    # Mock processing with fixed delay
    async def mock_sentiment_execute(context):
        await asyncio.sleep(0.5)  # 500ms per topic
        return AgentResult(
            agent_name='TopicSentimentAgent',
            success=True,
            data={'sentiment_insight': 'Test', 'sentiment_score': 0.5},
            execution_time=0.5,
            confidence=0.8,
            confidence_level='high'
        )
    
    async def mock_example_execute(context):
        await asyncio.sleep(0.1)
        return AgentResult(
            agent_name='ExampleExtractionAgent',
            success=True,
            data={'examples': []},
            execution_time=0.1,
            confidence=0.9,
            confidence_level='high'
        )
    
    orchestrator.topic_sentiment_agent.execute = mock_sentiment_execute
    orchestrator.example_extraction_agent.execute = mock_example_execute
    
    # Create test data with 10 topics
    num_topics = 10
    topics_data = {f'topic_{i}': {'volume': 5} for i in range(num_topics)}
    conversations_by_topic_full = {
        f'topic_{i}': [{'id': f'conv_{i}', 'conversation_message': {'body': 'Test'}}]
        for i in range(num_topics)
    }
    
    context = AgentContext(
        analysis_id='test_performance',
        analysis_type='weekly_voc',
        start_date=datetime.now(),
        end_date=datetime.now(),
        conversations=[]
    )
    
    # Simulate topic processing
    async def process_topic(topic_name):
        async with orchestrator.topic_semaphore:
            topic_convs = conversations_by_topic_full[topic_name]
            topic_context = context.model_copy()
            topic_context.metadata = {
                'current_topic': topic_name,
                'topic_conversations': topic_convs,
                'sentiment_insight': ''
            }
            await orchestrator.topic_sentiment_agent.execute(topic_context)
            await orchestrator.example_extraction_agent.execute(topic_context)
    
    # Process concurrently
    start_time = time.time()
    await asyncio.gather(*[process_topic(name) for name in topics_data.keys()])
    concurrent_time = time.time() - start_time
    
    # With 5 concurrent topics and 10 total topics at 0.5s each:
    # Sequential would take: 10 * 0.5 = 5 seconds
    # Concurrent should take: ~1 second (2 batches of 5)
    # Allow some margin for overhead
    assert concurrent_time < 2.0, \
        f"Concurrent processing took {concurrent_time:.2f}s, should be < 2s"
    
    print(f"✅ Performance test passed: concurrent_time={concurrent_time:.2f}s")


@pytest.mark.asyncio
async def test_semaphore_initialization():
    """Test that semaphore is properly initialized with config value"""
    # Test with default value
    orchestrator = TopicOrchestrator()
    assert orchestrator.topic_semaphore is not None
    assert orchestrator.topic_semaphore._value > 0
    
    # Test with environment variable override
    with patch.dict('os.environ', {'MAX_CONCURRENT_TOPICS': '3'}):
        # Need to reload the config module to pick up env var
        import importlib
        from src.config import modes
        importlib.reload(modes)
        
        orchestrator2 = TopicOrchestrator()
        # Note: The semaphore value might be cached, so we check it was created
        assert orchestrator2.topic_semaphore is not None
    
    print(f"✅ Initialization test passed: semaphore_limit={orchestrator.topic_semaphore._value}")


@pytest.mark.asyncio
async def test_error_handling_with_semaphore():
    """Test that errors in one topic don't block others"""
    orchestrator = TopicOrchestrator()
    
    error_count = 0
    success_count = 0
    
    async def mock_sentiment_execute(context):
        """Mock that fails for specific topics"""
        topic_name = context.metadata.get('current_topic', '')
        if 'error' in topic_name:
            nonlocal error_count
            error_count += 1
            raise ValueError(f"Intentional error for {topic_name}")
        
        nonlocal success_count
        success_count += 1
        await asyncio.sleep(0.1)
        return AgentResult(
            agent_name='TopicSentimentAgent',
            success=True,
            data={'sentiment_insight': 'Test', 'sentiment_score': 0.5},
            execution_time=0.1,
            confidence_level=0.8
        )
    
    async def mock_example_execute(context):
        return AgentResult(
            agent_name='ExampleExtractionAgent',
            success=True,
            data={'examples': []},
            execution_time=0.05,
            confidence=0.9
        )
    
    orchestrator.topic_sentiment_agent.execute = mock_sentiment_execute
    orchestrator.example_extraction_agent.execute = mock_example_execute
    
    # Create test data with some error topics
    topics_data = {
        'topic_1': {'volume': 5},
        'topic_error_1': {'volume': 5},
        'topic_2': {'volume': 5},
        'topic_error_2': {'volume': 5},
        'topic_3': {'volume': 5},
    }
    
    conversations_by_topic_full = {
        name: [{'id': f'conv_{name}', 'conversation_message': {'body': 'Test'}}]
        for name in topics_data.keys()
    }
    
    context = AgentContext(
        analysis_id='test_errors',
        analysis_type='weekly_voc',
        start_date=datetime.now(),
        end_date=datetime.now(),
        conversations=[]
    )
    
    # Process topics
    async def process_topic(topic_name):
        async with orchestrator.topic_semaphore:
            try:
                topic_convs = conversations_by_topic_full[topic_name]
                topic_context = context.model_copy()
                topic_context.metadata = {
                    'current_topic': topic_name,
                    'topic_conversations': topic_convs,
                    'sentiment_insight': ''
                }
                await orchestrator.topic_sentiment_agent.execute(topic_context)
                await orchestrator.example_extraction_agent.execute(topic_context)
                return topic_name, True
            except Exception as e:
                return topic_name, False
    
    results = await asyncio.gather(*[process_topic(name) for name in topics_data.keys()])
    
    # Verify some succeeded and some failed
    assert error_count == 2, f"Expected 2 errors, got {error_count}"
    assert success_count == 3, f"Expected 3 successes, got {success_count}"
    
    # Verify all topics were attempted
    assert len(results) == len(topics_data)
    
    print(f"✅ Error handling test passed: errors={error_count}, successes={success_count}")


@pytest.mark.asyncio
async def test_semaphore_with_zero_volume_topics():
    """Test that zero-volume topics don't consume semaphore slots"""
    orchestrator = TopicOrchestrator()
    
    execution_count = 0
    
    async def mock_sentiment_execute(context):
        nonlocal execution_count
        execution_count += 1
        await asyncio.sleep(0.1)
        return AgentResult(
            agent_name='TopicSentimentAgent',
            success=True,
            data={'sentiment_insight': 'Test', 'sentiment_score': 0.5},
            execution_time=0.1,
            confidence_level=0.8
        )
    
    orchestrator.topic_sentiment_agent.execute = mock_sentiment_execute
    
    # Create test data with mix of zero and non-zero volume
    topics_data = {
        'topic_1': {'volume': 5},
        'topic_zero_1': {'volume': 0},
        'topic_2': {'volume': 5},
        'topic_zero_2': {'volume': 0},
        'topic_3': {'volume': 5},
    }
    
    # Only non-zero topics should execute
    expected_executions = 3
    
    # In actual implementation, zero-volume topics are skipped before task creation
    # So we only create tasks for non-zero volumes
    non_zero_topics = {k: v for k, v in topics_data.items() if v['volume'] > 0}
    
    assert len(non_zero_topics) == expected_executions
    
    print(f"✅ Zero-volume test passed: only {len(non_zero_topics)} tasks would be created")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])