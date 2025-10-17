#!/usr/bin/env python3
"""
Demo script for the Intercom Analysis Tool Chat Interface

This script demonstrates the natural language chat interface capabilities
without requiring the full terminal UI.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.chat.chat_interface import ChatInterface
from src.config.settings import Settings


def demo_chat_interface():
    """Demonstrate the chat interface capabilities."""
    print("🤖 Intercom Analysis Tool - Chat Interface Demo")
    print("=" * 50)
    
    # Initialize chat interface
    try:
        settings = Settings()
        chat = ChatInterface(settings)
        print("✅ Chat interface initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize chat interface: {e}")
        return
    
    # Demo queries
    demo_queries = [
        "Give me last week's voice of customer report",
        "Show me billing analysis for this month with Gamma presentation",
        "Create a custom report for API tickets by Horatio agents in September",
        "I want to export data to CSV format",
        "Can you integrate with our Slack workspace?",
        "Help me understand what commands are available"
    ]
    
    print(f"\n📝 Running {len(demo_queries)} demo queries...")
    print("-" * 50)
    
    for i, query in enumerate(demo_queries, 1):
        print(f"\n{i}. Query: '{query}'")
        print("-" * 30)
        
        try:
            # Process the query
            result = chat.process_query(query)
            
            if result["success"]:
                translation = result["translation"]
                print(f"✅ Success: {translation.translation.explanation}")
                print(f"   Action: {translation.translation.action.value}")
                print(f"   Confidence: {translation.translation.confidence:.2f}")
                
                if translation.translation.action.value == "EXECUTE_COMMAND":
                    print(f"   Command: {translation.translation.command}")
                    if translation.translation.args:
                        print(f"   Args: {' '.join(translation.translation.args)}")
                
                # Show suggestions if available
                if "suggestions" in result and result["suggestions"]:
                    print(f"   💡 Generated {len(result['suggestions'])} feature suggestions")
                
                # Show security checks
                security = result.get("security_checks", {})
                print(f"   🔒 Security: Input validated={security.get('input_validated', False)}")
                
            else:
                print(f"❌ Failed: {result.get('error', 'Unknown error')}")
                if "details" in result:
                    print(f"   Details: {result['details']}")
        
        except Exception as e:
            print(f"❌ Error processing query: {e}")
    
    # Show performance statistics
    print(f"\n📊 Performance Statistics")
    print("-" * 50)
    stats = chat.get_performance_stats()
    
    translator_stats = stats.get("translator_stats", {})
    print(f"Total Queries: {translator_stats.get('total_queries', 0)}")
    print(f"Success Rate: {translator_stats.get('success_rate', 0):.1%}")
    print(f"Cache Hit Rate: {translator_stats.get('cache_hit_rate', 0):.1%}")
    print(f"Average Processing Time: {translator_stats.get('average_processing_time_ms', 0):.1f}ms")
    
    # Show available commands
    print(f"\n🎯 Available Commands")
    print("-" * 50)
    commands = chat.get_available_commands()
    print(f"Total commands available: {len(commands)}")
    for cmd in commands[:5]:  # Show first 5
        print(f"  - {cmd}")
    if len(commands) > 5:
        print(f"  ... and {len(commands) - 5} more")
    
    # Show supported filters
    print(f"\n🔍 Supported Filters")
    print("-" * 50)
    filters = chat.get_supported_filters()
    for filter_type, values in filters.items():
        print(f"  {filter_type.title()}: {len(values)} options")
    
    # Show filter examples
    print(f"\n📋 Filter Examples")
    print("-" * 50)
    filter_examples = chat.get_filter_examples()
    for example in filter_examples[:3]:  # Show first 3
        print(f"  - {example}")
    
    # Show suggestion examples
    print(f"\n💡 Suggestion Examples")
    print("-" * 50)
    suggestion_examples = chat.get_suggestion_examples()
    for example in suggestion_examples[:3]:  # Show first 3
        print(f"  - {example}")
    
    print(f"\n🎉 Demo completed successfully!")
    print("=" * 50)


def demo_custom_filters():
    """Demonstrate custom filter building."""
    print("\n🔍 Custom Filter Builder Demo")
    print("-" * 50)
    
    try:
        settings = Settings()
        chat = ChatInterface(settings)
        
        filter_queries = [
            "API tickets done by Horatio agents in September",
            "High priority billing issues from last week",
            "Open technical problems by support team"
        ]
        
        for query in filter_queries:
            print(f"\nQuery: '{query}'")
            filters = chat.build_custom_filters(query)
            print(f"Generated {len(filters)} filters:")
            for filter_spec in filters:
                print(f"  - {filter_spec['field']}: {filter_spec['value']} ({filter_spec['operator']})")
    
    except Exception as e:
        print(f"❌ Error in filter demo: {e}")


if __name__ == "__main__":
    demo_chat_interface()
    demo_custom_filters()
