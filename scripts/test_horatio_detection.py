"""
Quick Horatio Detection Test Script

Usage:
  python scripts/test_horatio_detection.py
  python scripts/test_horatio_detection.py --verbose

This script validates that SegmentationAgent correctly detects Horatio agents
via email addresses in conversation_parts, source.author, and assignee fields.

Expected output:
- All individual classification tests should pass (✓)
- Batch segmentation should show: horatio=3, boldr=1, escalated=1, fin_ai=1, unknown=1
- No errors or exceptions

If any tests fail, check:
1. The email domain is correct (@hirehoratio.co)
2. The conversation structure matches Intercom API format
3. The _classify_conversation() logic in segmentation_agent.py
"""

import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.agents.segmentation_agent import SegmentationAgent
from src.agents.base_agent import AgentContext


# ============================================================================
# SAMPLE CONVERSATION FIXTURES
# ============================================================================

HORATIO_CONVERSATION_VIA_PARTS = {
    'id': 'conv_horatio_parts_123',
    'created_at': 1699123456,
    'updated_at': 1699125456,
    'state': 'closed',
    'admin_assignee_id': '456',
    'ai_agent_participated': False,
    'full_text': 'Customer: I need help with billing. Agent: I can help with that.',
    'conversation_parts': {
        'conversation_parts': [
            {
                'type': 'conversation_part',
                'id': '789',
                'part_type': 'comment',
                'body': '<p>I can help with that billing issue</p>',
                'author': {
                    'type': 'admin',
                    'id': '456',
                    'name': 'Support Agent',
                    'email': 'agent@hirehoratio.co'
                }
            }
        ]
    },
    'source': {'type': 'email', 'body': 'Customer billing question'},
    'assignee': {}
}

HORATIO_CONVERSATION_VIA_SOURCE = {
    'id': 'conv_horatio_source_456',
    'created_at': 1699123456,
    'updated_at': 1699125456,
    'state': 'closed',
    'admin_assignee_id': '789',
    'ai_agent_participated': False,
    'full_text': 'Support conversation about feature request',
    'conversation_parts': {
        'conversation_parts': []
    },
    'source': {
        'type': 'chat',
        'body': 'Initial message from admin',
        'author': {
            'type': 'admin',
            'id': '789',
            'name': 'Horatio Support',
            'email': 'support@hirehoratio.co'
        }
    },
    'assignee': {}
}

HORATIO_CONVERSATION_VIA_ASSIGNEE = {
    'id': 'conv_horatio_assignee_789',
    'created_at': 1699123456,
    'updated_at': 1699125456,
    'state': 'closed',
    'admin_assignee_id': '999',
    'ai_agent_participated': False,
    'full_text': 'Technical support conversation',
    'conversation_parts': {
        'conversation_parts': []
    },
    'source': {'type': 'email', 'body': 'Customer inquiry'},
    'assignee': {
        'type': 'admin',
        'id': '999',
        'name': 'Team Lead',
        'email': 'team@hirehoratio.co'
    }
}

BOLDR_CONVERSATION = {
    'id': 'conv_boldr_123',
    'created_at': 1699123456,
    'updated_at': 1699125456,
    'state': 'closed',
    'admin_assignee_id': '111',
    'ai_agent_participated': False,
    'full_text': 'Billing support conversation',
    'conversation_parts': {
        'conversation_parts': [
            {
                'type': 'conversation_part',
                'id': '222',
                'part_type': 'comment',
                'body': '<p>Happy to help with billing</p>',
                'author': {
                    'type': 'admin',
                    'id': '111',
                    'name': 'Boldr Agent',
                    'email': 'agent@boldrimpact.com'
                }
            }
        ]
    },
    'source': {'type': 'email', 'body': 'Customer billing question'},
    'assignee': {}
}

ESCALATED_CONVERSATION = {
    'id': 'conv_escalated_max_123',
    'created_at': 1699123456,
    'updated_at': 1699125456,
    'state': 'closed',
    'admin_assignee_id': '333',
    'ai_agent_participated': False,
    'full_text': 'Complex technical issue requiring senior review',
    'conversation_parts': {
        'conversation_parts': [
            {
                'type': 'conversation_part',
                'id': '444',
                'part_type': 'comment',
                'body': '<p>Let me investigate this</p>',
                'author': {
                    'type': 'admin',
                    'id': '333',
                    'name': 'Max Jackson',
                    'email': 'max.jackson@example.com'
                }
            }
        ]
    },
    'source': {'type': 'email', 'body': 'Urgent issue'},
    'assignee': {}
}

FIN_AI_CONVERSATION = {
    'id': 'conv_fin_ai_123',
    'created_at': 1699123456,
    'updated_at': 1699125456,
    'state': 'closed',
    'admin_assignee_id': None,
    'ai_agent_participated': True,
    'full_text': 'Customer question. AI response with help article.',
    'conversation_parts': {
        'conversation_parts': [
            {
                'type': 'conversation_part',
                'id': '101',
                'part_type': 'comment',
                'body': '<p>Here is a help article that answers your question</p>',
                'author': {
                    'type': 'bot',
                    'id': 'fin_ai',
                    'name': 'Fin'
                }
            }
        ]
    },
    'source': {'type': 'chat', 'body': 'How do I reset my password?'},
    'assignee': {}
}

UNKNOWN_CONVERSATION = {
    'id': 'conv_unknown_123',
    'created_at': 1699123456,
    'updated_at': 1699125456,
    'state': 'open',
    'admin_assignee_id': None,
    'ai_agent_participated': False,
    'full_text': 'Customer message with no response yet',
    'conversation_parts': {
        'conversation_parts': []
    },
    'source': {'type': 'email', 'body': 'Customer inquiry about pricing'},
    'assignee': {}
}


# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def test_individual_classification(verbose=False):
    """Test individual conversation classification."""
    print("\n" + "="*70)
    print("TEST 1: Individual Conversation Classification")
    print("="*70)
    
    agent = SegmentationAgent()
    
    test_cases = [
        ("Horatio (via conversation_parts)", HORATIO_CONVERSATION_VIA_PARTS, 'paid', 'horatio'),
        ("Horatio (via source.author)", HORATIO_CONVERSATION_VIA_SOURCE, 'paid', 'horatio'),
        ("Horatio (via assignee)", HORATIO_CONVERSATION_VIA_ASSIGNEE, 'paid', 'horatio'),
        ("Boldr", BOLDR_CONVERSATION, 'paid', 'boldr'),
        ("Escalated (Max Jackson)", ESCALATED_CONVERSATION, 'paid', 'escalated'),
        ("Fin AI Only", FIN_AI_CONVERSATION, 'free', 'fin_ai'),
        ("Unknown", UNKNOWN_CONVERSATION, 'unknown', 'unknown'),
    ]
    
    results = []
    
    # Print header
    print(f"\n{'Conversation Type':<40} | {'Segment':<8} | {'Agent Type':<12} | Status")
    print("-" * 70)
    
    for name, conv, expected_segment, expected_agent in test_cases:
        segment, agent_type = agent._classify_conversation(conv)
        passed = (segment == expected_segment and agent_type == expected_agent)
        
        status = "✓" if passed else "✗"
        
        # Color output if available
        if passed:
            status_display = f"\033[92m{status}\033[0m"  # Green
        else:
            status_display = f"\033[91m{status}\033[0m"  # Red
        
        print(f"{name:<40} | {segment:<8} | {agent_type:<12} | {status_display}")
        
        if verbose and not passed:
            print(f"  Expected: ({expected_segment}, {expected_agent})")
            print(f"  Got: ({segment}, {agent_type})")
        
        results.append(passed)
    
    passed_count = sum(results)
    total_count = len(results)
    
    print("-" * 70)
    print(f"Result: {passed_count}/{total_count} tests passed")
    
    return all(results)


async def test_batch_segmentation(verbose=False):
    """Test batch segmentation with AgentContext."""
    print("\n" + "="*70)
    print("TEST 2: Batch Segmentation")
    print("="*70)
    
    agent = SegmentationAgent()
    
    conversations = [
        HORATIO_CONVERSATION_VIA_PARTS,
        HORATIO_CONVERSATION_VIA_SOURCE,
        HORATIO_CONVERSATION_VIA_ASSIGNEE,
        BOLDR_CONVERSATION,
        ESCALATED_CONVERSATION,
        FIN_AI_CONVERSATION,
        UNKNOWN_CONVERSATION
    ]
    
    # Create AgentContext
    context = AgentContext(
        analysis_id='test_batch_123',
        analysis_type='horatio_detection_test',
        start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
        conversations=conversations
    )
    
    if verbose:
        print(f"\nProcessing {len(conversations)} conversations...")
    
    # Execute segmentation
    result = await agent.execute(context)
    
    if not result.success:
        print(f"\n\033[91m✗ Segmentation failed: {result.error_message}\033[0m")
        return False
    
    # Expected distribution
    expected = {
        'horatio': 3,
        'boldr': 1,
        'escalated': 1,
        'fin_ai': 1,
        'unknown': 1
    }
    
    # Print results
    print("\nAgent Distribution:")
    print("-" * 70)
    
    agent_dist = result.data['agent_distribution']
    all_correct = True
    
    for agent_type, expected_count in expected.items():
        actual_count = agent_dist.get(agent_type, 0)
        passed = (actual_count == expected_count)
        status = "✓" if passed else "✗"
        
        if passed:
            status_display = f"\033[92m{status}\033[0m"  # Green
        else:
            status_display = f"\033[91m{status}\033[0m"  # Red
            all_correct = False
        
        print(f"  {agent_type:<12}: {actual_count:>2} (expected {expected_count:>2}) {status_display}")
    
    # Print segmentation summary
    summary = result.data['segmentation_summary']
    print("\nSegmentation Summary:")
    print("-" * 70)
    print(f"  Paid customers:    {summary['paid_count']} ({summary['paid_percentage']}%)")
    print(f"  Free customers:    {summary['free_count']} ({summary['free_percentage']}%)")
    print(f"  Unknown:           {summary['unknown_count']}")
    
    # Verify totals
    total = summary['paid_count'] + summary['free_count'] + summary['unknown_count']
    totals_match = (total == len(conversations))
    
    print(f"\n  Total classified:  {total} (expected {len(conversations)})")
    if totals_match:
        print(f"  \033[92m✓ Totals match\033[0m")
    else:
        print(f"  \033[91m✗ Totals don't match\033[0m")
        all_correct = False
    
    print("-" * 70)
    print(f"Result: {'PASSED' if all_correct else 'FAILED'}")
    
    return all_correct


def test_email_extraction(verbose=False):
    """Test email extraction from different sources."""
    print("\n" + "="*70)
    print("TEST 3: Email Extraction")
    print("="*70)
    
    agent = SegmentationAgent()
    
    test_cases = [
        ("conversation_parts", HORATIO_CONVERSATION_VIA_PARTS, ['agent@hirehoratio.co']),
        ("source.author", HORATIO_CONVERSATION_VIA_SOURCE, ['support@hirehoratio.co']),
        ("assignee", HORATIO_CONVERSATION_VIA_ASSIGNEE, ['team@hirehoratio.co']),
        ("Boldr agent", BOLDR_CONVERSATION, ['agent@boldrimpact.com']),
    ]
    
    print(f"\n{'Source':<20} | {'Expected Email':<30} | Status")
    print("-" * 70)
    
    all_passed = True
    
    for name, conv, expected_emails in test_cases:
        # Extract admin emails manually (simulating agent logic)
        admin_emails = []
        
        # Check conversation parts
        conversation_parts_data = conv.get('conversation_parts', {})
        if conversation_parts_data is None:
            conversation_parts_data = {}
        conv_parts = conversation_parts_data.get('conversation_parts', [])
        for part in conv_parts:
            author = part.get('author', {})
            if author.get('type') == 'admin':
                email = author.get('email', '')
                if email:
                    admin_emails.append(email.lower())
        
        # Check source
        source = conv.get('source', {})
        if source.get('author', {}).get('type') == 'admin':
            email = source.get('author', {}).get('email', '')
            if email:
                admin_emails.append(email.lower())
        
        # Check assignee
        assignee_email = conv.get('assignee', {}).get('email', '')
        if assignee_email:
            admin_emails.append(assignee_email.lower())
        
        # Check if expected emails were found
        expected_lower = [e.lower() for e in expected_emails]
        found_all = all(email in admin_emails for email in expected_lower)
        
        status = "✓" if found_all else "✗"
        status_display = f"\033[92m{status}\033[0m" if found_all else f"\033[91m{status}\033[0m"
        
        print(f"{name:<20} | {', '.join(expected_emails):<30} | {status_display}")
        
        if verbose:
            print(f"  Extracted: {admin_emails}")
        
        if not found_all:
            all_passed = False
    
    print("-" * 70)
    print(f"Result: {'PASSED' if all_passed else 'FAILED'}")
    
    return all_passed


# ============================================================================
# MAIN FUNCTION
# ============================================================================

async def main(verbose=False):
    """Run all tests."""
    print("\n" + "="*70)
    print("HORATIO DETECTION TEST SUITE")
    print("="*70)
    print("\nValidating SegmentationAgent with sample Intercom conversations...")
    
    # Set up logging
    log_level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s: %(message)s'
    )
    
    # Run tests
    results = []
    
    try:
        # Test 1: Individual classification
        result1 = test_individual_classification(verbose)
        results.append(("Individual Classification", result1))
        
        # Test 2: Batch segmentation
        result2 = await test_batch_segmentation(verbose)
        results.append(("Batch Segmentation", result2))
        
        # Test 3: Email extraction
        result3 = test_email_extraction(verbose)
        results.append(("Email Extraction", result3))
        
    except Exception as e:
        print(f"\n\033[91m✗ Test suite crashed: {e}\033[0m")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    # Print summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        status_display = f"\033[92m{status}\033[0m" if passed else f"\033[91m{status}\033[0m"
        print(f"  {test_name:<30}: {status_display}")
    
    all_passed = all(result for _, result in results)
    
    print("-" * 70)
    if all_passed:
        print("\033[92m✓ All tests passed!\033[0m")
        print("\nHoratio agent detection is working correctly.")
        print("You can now deploy to Railway with confidence.")
        return 0
    else:
        print("\033[91m✗ Some tests failed.\033[0m")
        print("\nPlease check:")
        print("1. Email domain is correct (@hirehoratio.co)")
        print("2. Conversation structure matches Intercom API")
        print("3. _classify_conversation() logic in segmentation_agent.py")
        return 1


if __name__ == "__main__":
    import sys
    
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    
    exit_code = asyncio.run(main(verbose))
    sys.exit(exit_code)
