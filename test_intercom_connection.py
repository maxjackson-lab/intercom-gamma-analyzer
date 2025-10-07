"""
Test script to verify connection to your Intercom instance and fetch sample data.
This will help you confirm that the API key works and you can access your data.
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_basic_connection():
    """Test basic connection to Intercom API."""
    print("🔌 Testing basic connection to Intercom API...")
    
    try:
        from intercom_client import IntercomClient
        
        load_dotenv()
        access_token = os.getenv('INTERCOM_ACCESS_TOKEN')
        
        if not access_token or access_token == 'your_token_here':
            print("❌ No valid access token found in .env file")
            print("   Run: python configure_api.py")
            return False, None
        
        client = IntercomClient(access_token=access_token)
        print("✅ Basic connection successful!")
        return True, client
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False, None

def test_conversation_count(client):
    """Test getting conversation count."""
    print("\n📊 Testing conversation count...")
    
    try:
        # Create a query for last 30 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        query = client.create_date_range_query(start_date, end_date)
        
        count = client.get_conversation_count(query)
        print(f"✅ Found {count:,} conversations in the last 30 days")
        return True, count
        
    except Exception as e:
        print(f"❌ Failed to get conversation count: {e}")
        return False, 0

def test_fetch_sample_conversations(client):
    """Test fetching a small sample of conversations."""
    print("\n📥 Testing conversation fetch...")
    
    try:
        # Create a query for last 7 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        query = client.create_date_range_query(start_date, end_date)
        
        # Fetch only 1 page (max 150 conversations)
        conversations = list(client.search_conversations(query=query, max_pages=1))
        
        print(f"✅ Successfully fetched {len(conversations)} conversations")
        
        if conversations:
            # Show sample conversation info
            sample = conversations[0]
            print(f"\n📋 Sample conversation:")
            print(f"   ID: {sample.get('id', 'unknown')}")
            print(f"   State: {sample.get('state', 'unknown')}")
            print(f"   Created: {datetime.fromtimestamp(sample.get('created_at', 0)).strftime('%Y-%m-%d %H:%M')}")
            
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

def test_text_search(client):
    """Test text search functionality."""
    print("\n🔍 Testing text search...")
    
    try:
        # Search for conversations containing "help"
        query = client.create_text_search_query("help")
        
        # Fetch only 1 page
        conversations = list(client.search_conversations(query=query, max_pages=1))
        
        print(f"✅ Found {len(conversations)} conversations containing 'help'")
        
        if conversations:
            print("   Sample search results:")
            for i, conv in enumerate(conversations[:3], 1):
                conv_id = conv.get('id', 'unknown')
                created_at = conv.get('created_at', 0)
                date_str = datetime.fromtimestamp(created_at).strftime('%Y-%m-%d') if created_at else 'unknown'
                print(f"   {i}. {conv_id} (created: {date_str})")
        
        return True
        
    except Exception as e:
        print(f"❌ Text search failed: {e}")
        return False

def main():
    """Run all connection tests."""
    print("🧪 Intercom Connection Test")
    print("=" * 50)
    
    # Test 1: Basic connection
    success, client = test_basic_connection()
    if not success:
        print("\n❌ Basic connection failed. Please check your API token.")
        return
    
    # Test 2: Conversation count
    success, count = test_conversation_count(client)
    if not success:
        print("\n❌ Could not get conversation count. Check API permissions.")
        return
    
    # Test 3: Fetch sample conversations
    success, conversations = test_fetch_sample_conversations(client)
    if not success:
        print("\n❌ Could not fetch conversations. Check API permissions.")
        return
    
    # Test 4: Text search
    success = test_text_search(client)
    if not success:
        print("\n⚠️  Text search failed, but basic functionality works.")
    
    # Summary
    print("\n" + "=" * 50)
    print("🎉 Connection test completed!")
    print(f"📊 Your Intercom instance has {count:,} conversations (last 30 days)")
    print(f"📥 Successfully fetched {len(conversations)} sample conversations")
    print("\n✅ Your setup is working! You can now run:")
    print("   python main.py --days 7 --max-pages 2  (for testing)")
    print("   python main.py  (for full analysis)")

if __name__ == "__main__":
    main()
