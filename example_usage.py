"""
Example usage of the Intercom Conversation Trend Analyzer.
This script demonstrates how to use the tool programmatically with the official SDK.
"""

import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add src to path
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.services.intercom_sdk_service import IntercomSDKService
from utils.time_utils import format_datetime_for_display

async def example_basic_analysis():
    """Example: Basic conversation analysis for last 30 days."""
    print("=== Basic Analysis Example ===")
    
    # Load environment
    load_dotenv()
    
    # Initialize SDK service
    service = IntercomSDKService()
    
    # Define date range (last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    print(f"Fetching conversations from {start_date.date()} to {end_date.date()}")
    
    # Fetch conversations (limit to 250 for example - 5 pages * 50 per page)
    conversations = await service.fetch_conversations_by_date_range(
        start_date, end_date, max_conversations=250
    )
    print(f"Found {len(conversations)} conversations")
    
    if not conversations:
        print("No conversations found in the specified date range")
        return
    
    # Show sample conversation data
    print("\nSample Conversations:")
    for i, conv in enumerate(conversations[:5], 1):
        conv_id = conv.get('id', 'unknown')
        created_at = conv.get('created_at')
        date_str = format_datetime_for_display(created_at, '%Y-%m-%d') if created_at else 'unknown'
        print(f"  {i}. {conv_id} (created: {date_str})")
    
    print(f"\n✅ Successfully fetched {len(conversations)} conversations using SDK")

async def example_text_search():
    """Example: Search for conversations containing specific text."""
    print("\n=== Text Search Example ===")
    
    # Initialize SDK service
    service = IntercomSDKService()
    
    print("Searching for conversations containing 'error'...")
    
    # Search for conversations using SDK (limit to 3 pages)
    conversations = await service.fetch_conversations_by_query(
        query_type="text_search",
        custom_query="error",
        max_pages=3
    )
    print(f"Found {len(conversations)} conversations mentioning 'error'")
    
    if conversations:
        # Show first few conversation IDs
        print("\nFirst 5 conversation IDs:")
        for i, conv in enumerate(conversations[:5], 1):
            conv_id = conv.get('id', 'unknown')
            created_at = conv.get('created_at')
            # Use helper to format datetime (handles both datetime and numeric types)
            date_str = format_datetime_for_display(created_at, '%Y-%m-%d') if created_at else 'unknown'
            print(f"  {i}. {conv_id} (created: {date_str})")

async def example_custom_analysis():
    """Example: Custom analysis with date range."""
    print("\n=== Custom Analysis Example ===")
    
    # Initialize SDK service
    service = IntercomSDKService()
    
    # Define date range (last 7 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    print(f"Analyzing conversations from {start_date.date()} to {end_date.date()}")
    
    # Fetch conversations using SDK (limit to 150 - 3 pages * 50)
    conversations = await service.fetch_conversations_by_date_range(
        start_date, end_date, max_conversations=150
    )
    print(f"Found {len(conversations)} conversations")
    
    if not conversations:
        print("No conversations found in the specified date range")
        return
    
    # Show conversation states
    states = {}
    for conv in conversations:
        state = conv.get('state', 'unknown')
        states[state] = states.get(state, 0) + 1
    
    print("\nConversation States:")
    for state, count in sorted(states.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(conversations)) * 100
        print(f"  {state:15s}: {count:3d} ({percentage:5.1f}%)")
    
    print(f"\n✅ Successfully analyzed {len(conversations)} conversations using SDK")

async def main():
    """Run all examples."""
    print("Intercom Analysis Tool - Example Usage (SDK)")
    print("=" * 50)
    
    try:
        await example_basic_analysis()
        await example_text_search()
        await example_custom_analysis()
        
        print("\n" + "=" * 50)
        print("Examples completed successfully!")
        print("All examples now use the official Intercom SDK.")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        print("Make sure you have:")
        print("1. Set INTERCOM_ACCESS_TOKEN in your .env file")
        print("2. Installed all dependencies: pip install -r requirements.txt")
        print("3. Valid Intercom API access")

if __name__ == "__main__":
    asyncio.run(main())


