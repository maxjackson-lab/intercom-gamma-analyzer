"""
Test script to verify connection to your Intercom instance and fetch sample data.
This will help you confirm that the API key works and you can access your data.
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from utils.time_utils import format_datetime_for_display


async def test_basic_connection():
    """Test basic connection to Intercom API."""
    print("🔌 Testing basic connection to Intercom API...")
    
    try:
        from src.services.intercom_sdk_service import IntercomSDKService
        
        load_dotenv()
        access_token = os.getenv('INTERCOM_ACCESS_TOKEN')
        
        if not access_token or access_token == 'your_token_here':
            print("❌ No valid access token found in .env file")
            print("   Run: python configure_api.py")
            return False, None
        
        service = IntercomSDKService()
        await service.test_connection()
        print("✅ Basic connection successful!")
        return True, service
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False, None


async def test_conversation_count(service):
    """Test getting conversation count."""
    print("\n📊 Testing conversation count...")
    
    try:
        # Create a query for last 30 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        conversations = await service.fetch_conversations_by_date_range(start_date, end_date, max_conversations=1)
        count = len(conversations)
        print(f"✅ Found at least {count:,} conversations in the last 30 days")
        return True, count
        
    except Exception as e:
        print(f"❌ Failed to get conversation count: {e}")
        return False, 0


async def test_fetch_sample_conversations(service):
    """Test fetching a small sample of conversations."""
    print("\n📥 Testing conversation fetch...")
    
    try:
        # Create a query for last 7 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        # Fetch only a few conversations
        conversations = await service.fetch_conversations_by_date_range(start_date, end_date, max_conversations=3)
        
        print(f"✅ Successfully fetched {len(conversations)} conversations")
        
        if conversations:
            # Show sample conversation info
            sample = conversations[0]
            print(f"\n📋 Sample conversation:")
            print(f"   ID: {sample.get('id', 'unknown')}")
            print(f"   State: {sample.get('state', 'unknown')}")
            # Use helper to format datetime (handles both datetime and numeric types)
            created_at = sample.get('created_at')
            if created_at:
                if isinstance(created_at, datetime):
                    created_str = created_at.strftime('%Y-%m-%d %H:%M')
                else:
                    created_str = format_datetime_for_display(created_at, '%Y-%m-%d %H:%M')
                print(f"   Created: {created_str}")
            
            # Show source info
            source = sample.get('source', {})
            print(f"   Source type: {source.get('type', 'unknown')}")
            
            # Show conversation body preview
            body = source.get('body', '')
            if body:
                preview = body[:100] + "..." if len(body) > 100 else body
                print(f"   Body preview: {preview}")
        
        return True, conversations
        
    except Exception as e:
        print(f"❌ Failed to fetch conversations: {e}")
        return False, []


async def main():
    """Run all connection tests."""
    print("🧪 Intercom Connection Test")
    print("=" * 50)
    
    # Test 1: Basic connection
    success, service = await test_basic_connection()
    if not success:
        print("\n❌ Basic connection failed. Please check your API token.")
        return
    
    # Test 2: Conversation count
    success, count = await test_conversation_count(service)
    if not success:
        print("\n❌ Could not get conversation count. Check API permissions.")
        return
    
    # Test 3: Fetch sample conversations
    success, conversations = await test_fetch_sample_conversations(service)
    if not success:
        print("\n❌ Could not fetch conversations. Check API permissions.")
        return
    
    # Summary
    print("\n" + "=" * 50)
    print("🎉 Connection test completed!")
    print(f"📊 Your Intercom instance has conversations available")
    print(f"📥 Successfully fetched {len(conversations)} sample conversations")
    print("\n✅ Your setup is working! You can now run:")
    print("   python main.py --days 7 --max-pages 2  (for testing)")
    print("   python main.py  (for full analysis)")


if __name__ == "__main__":
    asyncio.run(main())
