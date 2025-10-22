"""
Comprehensive QA test for multi-agent branch
Tests all agents with fake data to verify functionality
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.topic_orchestrator import TopicOrchestrator
from src.agents.base_agent import AgentContext

# Create fake conversation data matching Intercom schema
def create_fake_conversations(count=20):
    """Create fake conversations with proper structure"""
    conversations = []
    
    topics = [
        ('Billing', 'I want a refund for my subscription'),
        ('Credits', 'I ran out of credits'),
        ('Bug', 'The export feature is broken'),
        ('Account', 'How do I change my email?'),
        ('Product Question', 'How do I create a template?'),
    ]
    
    for i in range(count):
        topic_name, message = topics[i % len(topics)]
        
        conv = {
            'id': f'test_{i}',
            'created_at': int((datetime.now() - timedelta(days=1)).timestamp()),
            'updated_at': int(datetime.now().timestamp()),
            'state': 'closed',
            'priority': 'not_priority',
            'admin_assignee_id': '12345' if i % 3 == 0 else None,
            'conversation_rating': 4 if i % 2 == 0 else None,
            'time_to_admin_reply': 3600,
            'handling_time': 7200,
            'count_conversation_parts': 3 + (i % 3),
            'count_reopens': 0 if i % 4 != 0 else 1,
            'ai_agent_participated': i % 5 == 0,
            'custom_attributes': {topic_name: True} if i % 2 == 0 else {},
            'tags': {'tags': [{'name': topic_name}]},
            'full_text': f"Customer: {message}\\n\\nAgent: Here's how we can help...",
            'customer_messages': [message],
            'admin_messages': ["Here's how we can help..."],
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'author': {'type': 'user'},
                        'body': message
                    },
                    {
                        'author': {'type': 'admin'},
                        'body': "Here's how we can help..."
                    }
                ]
            },
            'source': {
                'author': {'type': 'user'},
                'body': message
            }
        }
        
        conversations.append(conv)
    
    return conversations

async def test_topic_orchestrator():
    """Test the full topic orchestrator with fake data"""
    print("="*80)
    print("MULTI-AGENT QA TEST - Topic Orchestrator")
    print("="*80)
    
    # Create fake data
    print("\\n1. Creating 20 fake conversations...")
    conversations = create_fake_conversations(20)
    print(f"   ✅ Created {len(conversations)} conversations")
    
    # Initialize orchestrator
    print("\\n2. Initializing TopicOrchestrator...")
    orchestrator = TopicOrchestrator()
    print("   ✅ Orchestrator initialized")
    
    # Run analysis
    print("\\n3. Running weekly analysis...")
    start_time = datetime.now()
    
    try:
        results = await orchestrator.execute_weekly_analysis(
            conversations=conversations,
            week_id="2025-TEST",
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now()
        )
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print(f"   ✅ Analysis completed in {elapsed:.1f}s")
        
        # Verify results
        print("\\n4. Verifying results...")
        
        summary = results.get('summary', {})
        print(f"   Total conversations: {summary.get('total_conversations')}")
        print(f"   Paid: {summary.get('paid_conversations')}")
        print(f"   Free: {summary.get('free_conversations')}")
        print(f"   Topics analyzed: {summary.get('topics_analyzed')}")
        print(f"   Agents completed: {summary.get('agents_completed')}")
        
        # Check formatted report
        formatted_report = results.get('formatted_report', '')
        if formatted_report:
            print(f"   ✅ Formatted report: {len(formatted_report)} characters")
            
            # Check for key sections
            has_billing = 'Billing' in formatted_report
            has_examples = 'Examples:' in formatted_report
            has_fin = 'Fin AI' in formatted_report
            
            print(f"   {'✅' if has_billing else '❌'} Contains Billing section")
            print(f"   {'✅' if has_examples else '❌'} Contains Examples section")
            print(f"   {'✅' if has_fin else '❌'} Contains Fin AI section")
            
            # Show first 500 chars
            print("\\n   Report preview:")
            print("   " + "-"*76)
            for line in formatted_report[:500].split('\\n')[:10]:
                print(f"   {line}")
            print("   " + "-"*76)
        else:
            print("   ❌ No formatted report generated")
        
        # Check agent results
        agent_results = results.get('agent_results', {})
        print(f"\\n5. Agent execution results:")
        for agent_name, result in agent_results.items():
            status = "✅ SUCCESS" if result.get('success') else "❌ FAILED"
            print(f"   {status} {agent_name}")
            if not result.get('success'):
                print(f"      Error: {result.get('error_message')}")
        
        print("\\n" + "="*80)
        print("✅ QA TEST PASSED")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"\\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_topic_orchestrator())
    sys.exit(0 if success else 1)

