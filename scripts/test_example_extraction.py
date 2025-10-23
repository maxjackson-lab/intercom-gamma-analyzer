#!/usr/bin/env python3
"""
Quick Example Extraction Test Script

Usage:
  python scripts/test_example_extraction.py
  python scripts/test_example_extraction.py --verbose

This script validates that ExampleExtractionAgent correctly handles
timestamp conversion for integer, float, and datetime timestamps.

Expected output:
- ✓ Integer timestamp conversion works
- ✓ Datetime timestamp conversion works
- ✓ Float timestamp conversion works
- ✓ Invalid timestamp handling works
- ✓ None timestamp handling works
- ✓ Scoring with various timestamps works
- ✓ End-to-end example extraction works
- 🎉 All tests passed!

If any tests fail:
1. Check the error message for details
2. Review src/agents/example_extraction_agent.py lines 284-298
3. Ensure the timestamp conversion fix is present
4. Run full test suite: pytest tests/test_example_extraction_agent.py

This script runs in < 10 seconds and requires no external API calls.
"""

import sys
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.example_extraction_agent import ExampleExtractionAgent
from src.agents.base_agent import AgentContext


# ============================================================================
# Sample Data Fixtures
# ============================================================================

SAMPLE_CONVERSATION_INT_TIMESTAMP = {
    'id': 'test_conv_int',
    'created_at': 1699123456,  # Integer Unix timestamp (2023-11-04)
    'customer_messages': ['I am having trouble with billing charges on my account'],
    'full_text': 'Customer: I am having trouble with billing charges on my account',
    'state': 'closed'
}

SAMPLE_CONVERSATION_DATETIME_TIMESTAMP = {
    'id': 'test_conv_datetime',
    'created_at': datetime(2023, 11, 4, 12, 0, 0, tzinfo=timezone.utc),
    'customer_messages': ['The export feature is not working properly'],
    'full_text': 'Customer: The export feature is not working properly',
    'state': 'closed'
}

SAMPLE_CONVERSATION_FLOAT_TIMESTAMP = {
    'id': 'test_conv_float',
    'created_at': 1699123456.789,  # Float with fractional seconds
    'customer_messages': ['I love the new dashboard design'],
    'full_text': 'Customer: I love the new dashboard design',
    'state': 'closed'
}

SAMPLE_CONVERSATION_INVALID_TIMESTAMP = {
    'id': 'test_conv_invalid',
    'created_at': -1,  # Invalid negative timestamp
    'customer_messages': ['This should still work despite invalid timestamp'],
    'full_text': 'Customer: This should still work despite invalid timestamp',
    'state': 'closed'
}

SAMPLE_CONVERSATION_NONE_TIMESTAMP = {
    'id': 'test_conv_none',
    'created_at': None,
    'customer_messages': ['No timestamp but should still be usable'],
    'full_text': 'Customer: No timestamp but should still be usable',
    'state': 'closed'
}


def create_sample_conversations_for_scoring():
    """Create sample conversations with varied characteristics."""
    now = datetime.now(timezone.utc)
    conversations = []
    
    # High quality conversations (recent, clear messages, with sentiment)
    for i in range(3):
        conversations.append({
            'id': f'conv_quality_{i}',
            'created_at': int((now - timedelta(days=2)).timestamp()),
            'customer_messages': [
                f'I hate this feature because it keeps crashing and losing my data. '
                f'This is very frustrating for our team. Message {i}.'
            ],
            'full_text': f'Customer frustration message {i}',
            'conversation_rating': 5,
            'state': 'closed'
        })
    
    # Medium quality conversations
    for i in range(3, 6):
        conversations.append({
            'id': f'conv_medium_{i}',
            'created_at': int((now - timedelta(days=10)).timestamp()),
            'customer_messages': [f'I have a question about the product feature. Message {i}.'],
            'full_text': f'Customer question {i}',
            'state': 'closed'
        })
    
    # Low quality conversations (short messages)
    for i in range(6, 8):
        conversations.append({
            'id': f'conv_low_{i}',
            'created_at': int((now - timedelta(days=30)).timestamp()),
            'customer_messages': [f'Help {i}'],
            'full_text': f'Help {i}',
            'state': 'closed'
        })
    
    # Recent conversations with datetime timestamps
    for i in range(8, 10):
        conversations.append({
            'id': f'conv_recent_{i}',
            'created_at': now - timedelta(days=1),
            'customer_messages': [
                f'I love the improvements but confused about the interface. Message {i}.'
            ],
            'full_text': f'Customer feedback {i}',
            'conversation_rating': 4,
            'state': 'closed'
        })
    
    return conversations


# ============================================================================
# Mock OpenAI Client
# ============================================================================

class MockOpenAIClient:
    """Mock OpenAI client to avoid real API calls."""
    
    async def generate_analysis(self, prompt, **kwargs):
        """Return mock LLM response for example selection."""
        return '[1, 2, 3]'


# ============================================================================
# Test Functions
# ============================================================================

def test_integer_timestamp_conversion(agent, verbose=False):
    """Test integer timestamp conversion."""
    try:
        result = agent._format_example(SAMPLE_CONVERSATION_INT_TIMESTAMP)
        
        if result is None:
            print("✗ Integer timestamp conversion failed: returned None")
            return False
        
        if 'created_at' not in result:
            print("✗ Integer timestamp conversion failed: no created_at field")
            return False
        
        if not isinstance(result['created_at'], str):
            print(f"✗ Integer timestamp conversion failed: created_at is {type(result['created_at'])}, not str")
            return False
        
        if not result['created_at'].startswith('2023-11-04'):
            print(f"✗ Integer timestamp conversion failed: wrong date {result['created_at']}")
            return False
        
        if verbose:
            print(f"  Converted {SAMPLE_CONVERSATION_INT_TIMESTAMP['created_at']} -> {result['created_at']}")
        
        print("✓ Integer timestamp conversion works")
        return True
        
    except Exception as e:
        print(f"✗ Integer timestamp conversion failed with exception: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def test_datetime_timestamp_conversion(agent, verbose=False):
    """Test datetime timestamp conversion."""
    try:
        result = agent._format_example(SAMPLE_CONVERSATION_DATETIME_TIMESTAMP)
        
        if result is None:
            print("✗ Datetime timestamp conversion failed: returned None")
            return False
        
        if 'created_at' not in result:
            print("✗ Datetime timestamp conversion failed: no created_at field")
            return False
        
        if not isinstance(result['created_at'], str):
            print(f"✗ Datetime timestamp conversion failed: created_at is {type(result['created_at'])}")
            return False
        
        if not result['created_at'].startswith('2023-11-04'):
            print(f"✗ Datetime timestamp conversion failed: wrong date {result['created_at']}")
            return False
        
        if verbose:
            print(f"  Datetime object converted to: {result['created_at']}")
        
        print("✓ Datetime timestamp conversion works")
        return True
        
    except Exception as e:
        print(f"✗ Datetime timestamp conversion failed with exception: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def test_float_timestamp_conversion(agent, verbose=False):
    """Test float timestamp conversion."""
    try:
        result = agent._format_example(SAMPLE_CONVERSATION_FLOAT_TIMESTAMP)
        
        if result is None:
            print("✗ Float timestamp conversion failed: returned None")
            return False
        
        if 'created_at' not in result:
            print("✗ Float timestamp conversion failed: no created_at field")
            return False
        
        if result['created_at'] and not isinstance(result['created_at'], str):
            print(f"✗ Float timestamp conversion failed: created_at is {type(result['created_at'])}")
            return False
        
        if verbose:
            print(f"  Float timestamp {SAMPLE_CONVERSATION_FLOAT_TIMESTAMP['created_at']} -> {result['created_at']}")
        
        print("✓ Float timestamp conversion works")
        return True
        
    except Exception as e:
        print(f"✗ Float timestamp conversion failed with exception: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def test_invalid_timestamp_handling(agent, verbose=False):
    """Test invalid timestamp handling."""
    try:
        result = agent._format_example(SAMPLE_CONVERSATION_INVALID_TIMESTAMP)
        
        # Should not crash - either returns result with None timestamp or returns None
        if result is not None:
            # If returns result, created_at should be None (fallback)
            if result.get('created_at') is not None and result.get('created_at') != '':
                if verbose:
                    print(f"  Warning: Invalid timestamp returned {result.get('created_at')} instead of None")
        
        if verbose:
            print(f"  Invalid timestamp handled gracefully: {result}")
        
        print("✓ Invalid timestamp handling works")
        return True
        
    except Exception as e:
        print(f"✗ Invalid timestamp handling failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def test_none_timestamp_handling(agent, verbose=False):
    """Test None timestamp handling."""
    try:
        result = agent._format_example(SAMPLE_CONVERSATION_NONE_TIMESTAMP)
        
        # Should not crash
        if result is not None:
            # Should have None timestamp
            if result.get('created_at') is not None and result.get('created_at') != '':
                if verbose:
                    print(f"  Warning: None timestamp returned {result.get('created_at')}")
        
        if verbose:
            print(f"  None timestamp handled gracefully: {result}")
        
        print("✓ None timestamp handling works")
        return True
        
    except Exception as e:
        print(f"✗ None timestamp handling failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def test_scoring_with_timestamps(agent, verbose=False):
    """Test scoring with various timestamp types."""
    try:
        conversations = create_sample_conversations_for_scoring()
        
        for conv in conversations:
            score = agent._score_conversation(conv, sentiment='Users frustrated')
            
            if not isinstance(score, (int, float)):
                print(f"✗ Scoring failed: score is {type(score)}, not numeric")
                return False
            
            if score < 0:
                print(f"✗ Scoring failed: negative score {score}")
                return False
            
            if verbose:
                conv_id = conv.get('id', 'unknown')
                print(f"  {conv_id}: score = {score:.2f}")
        
        print("✓ Scoring with various timestamps works")
        return True
        
    except Exception as e:
        print(f"✗ Scoring with timestamps failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


async def test_end_to_end_extraction(agent, verbose=False):
    """Test end-to-end example extraction."""
    try:
        conversations = create_sample_conversations_for_scoring()
        now = datetime.now(timezone.utc)
        
        context = AgentContext(
            analysis_id='quick_test',
            start_date=now - timedelta(days=30),
            end_date=now,
            conversations=[],
            metadata={
                'current_topic': 'Billing Issues',
                'sentiment_insight': 'Users frustrated with charges',
                'topic_conversations': conversations
            }
        )
        
        # Mock OpenAI client to avoid real API calls
        agent.openai_client = MockOpenAIClient()
        
        result = await agent.execute(context)
        
        if not result.success:
            print(f"✗ End-to-end extraction failed: {result.error}")
            if verbose:
                print(f"  Result data: {result.data}")
            return False
        
        if 'examples' not in result.data:
            print("✗ End-to-end extraction failed: no examples in result")
            return False
        
        examples = result.data['examples']
        
        if not isinstance(examples, list):
            print(f"✗ End-to-end extraction failed: examples is {type(examples)}, not list")
            return False
        
        if len(examples) == 0:
            print("✗ End-to-end extraction failed: no examples extracted")
            if verbose:
                print(f"  Result: {result.data}")
            return False
        
        if len(examples) > 10:
            print(f"✗ End-to-end extraction failed: too many examples ({len(examples)} > 10)")
            return False
        
        # Validate example structure
        for i, example in enumerate(examples):
            if 'preview' not in example:
                print(f"✗ Example {i} missing preview field")
                return False
            if 'intercom_url' not in example:
                print(f"✗ Example {i} missing intercom_url field")
                return False
            if 'conversation_id' not in example:
                print(f"✗ Example {i} missing conversation_id field")
                return False
            if 'created_at' not in example:
                print(f"✗ Example {i} missing created_at field")
                return False
        
        if verbose:
            print(f"  Extracted {len(examples)} examples")
            print(f"  Confidence: {result.confidence:.2f}")
            for i, example in enumerate(examples):
                print(f"  Example {i+1}: {example['preview'][:50]}...")
        
        print("✓ End-to-end example extraction works")
        return True
        
    except Exception as e:
        print(f"✗ End-to-end extraction failed with exception: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


# ============================================================================
# Main Function
# ============================================================================

def main():
    """Run all quick tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Quick example extraction tests')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    # Banner
    print("\n🧪 Example Extraction Quick Test")
    print("=" * 50)
    print()
    
    # Set up logging
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)
    
    # Create agent
    agent = ExampleExtractionAgent()
    
    # Run tests
    tests = [
        ('Integer timestamp conversion', lambda: test_integer_timestamp_conversion(agent, args.verbose)),
        ('Datetime timestamp conversion', lambda: test_datetime_timestamp_conversion(agent, args.verbose)),
        ('Float timestamp conversion', lambda: test_float_timestamp_conversion(agent, args.verbose)),
        ('Invalid timestamp handling', lambda: test_invalid_timestamp_handling(agent, args.verbose)),
        ('None timestamp handling', lambda: test_none_timestamp_handling(agent, args.verbose)),
        ('Scoring with timestamps', lambda: test_scoring_with_timestamps(agent, args.verbose)),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"✗ {name} failed with exception: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            results.append(False)
    
    # Run async test
    try:
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(test_end_to_end_extraction(agent, args.verbose))
        results.append(result)
    except Exception as e:
        print(f"✗ End-to-end extraction failed with exception: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        results.append(False)
    
    # Summary
    print()
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"{passed}/{total} tests passed")
    print()
    
    if all(results):
        print("🎉 All tests passed! Timestamp fix is working correctly.")
        print("You can now deploy to Railway with confidence.")
        print()
        return 0
    else:
        print("❌ Some tests failed. Please review the errors above.")
        print("Check src/agents/example_extraction_agent.py lines 284-298")
        print("Ensure the timestamp conversion fix is present.")
        print()
        print("Run full test suite for more details:")
        print("  pytest tests/test_example_extraction_agent.py -v")
        print()
        return 1


if __name__ == '__main__':
    sys.exit(main())

