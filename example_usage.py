"""
Example usage of the Intercom Conversation Trend Analyzer.
This script demonstrates how to use the tool programmatically.
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add src to path
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from intercom_client import IntercomClient
from text_analyzer import TextAnalyzer
from trend_analyzer import TrendAnalyzer
from report_generator import ReportGenerator

def example_basic_analysis():
    """Example: Basic conversation analysis for last 30 days."""
    print("=== Basic Analysis Example ===")
    
    # Load environment
    load_dotenv()
    access_token = os.getenv('INTERCOM_ACCESS_TOKEN')
    
    if not access_token:
        print("Please set INTERCOM_ACCESS_TOKEN in your .env file")
        return
    
    # Initialize clients
    client = IntercomClient(access_token=access_token)
    text_analyzer = TextAnalyzer()
    
    # Define date range (last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Create query
    query = client.create_date_range_query(start_date, end_date)
    
    print(f"Fetching conversations from {start_date.date()} to {end_date.date()}")
    
    # Fetch conversations (limit to 5 pages for example)
    conversations = list(client.search_conversations(query=query, max_pages=5))
    print(f"Found {len(conversations)} conversations")
    
    if not conversations:
        print("No conversations found in the specified date range")
        return
    
    # Analyze text
    text_results = text_analyzer.analyze_conversations(conversations)
    
    # Show top keywords
    print("\nTop 10 Keywords:")
    for i, (keyword, count) in enumerate(text_results['top_keywords'][:10], 1):
        print(f"  {i:2d}. {keyword:30s} ({count})")
    
    # Analyze trends
    patterns = ['error', 'bug', 'issue', 'problem', 'help']
    pattern_counts = TrendAnalyzer.pattern_analysis(conversations, patterns)
    
    print("\nPattern Analysis:")
    for pattern, count in pattern_counts.items():
        percentage = (count / len(conversations)) * 100
        print(f"  {pattern:10s}: {count:3d} ({percentage:5.1f}%)")

def example_text_search():
    """Example: Search for conversations containing specific text."""
    print("\n=== Text Search Example ===")
    
    # Load environment
    load_dotenv()
    access_token = os.getenv('INTERCOM_ACCESS_TOKEN')
    
    if not access_token:
        print("Please set INTERCOM_ACCESS_TOKEN in your .env file")
        return
    
    # Initialize client
    client = IntercomClient(access_token=access_token)
    
    # Search for conversations mentioning "cache"
    query = client.create_text_search_query("cache")
    
    print("Searching for conversations containing 'cache'...")
    
    # Fetch conversations (limit to 3 pages for example)
    conversations = list(client.search_conversations(query=query, max_pages=3))
    print(f"Found {len(conversations)} conversations mentioning 'cache'")
    
    if conversations:
        # Show first few conversation IDs
        print("\nFirst 5 conversation IDs:")
        for i, conv in enumerate(conversations[:5], 1):
            conv_id = conv.get('id', 'unknown')
            created_at = conv.get('created_at', 0)
            date_str = datetime.fromtimestamp(created_at).strftime('%Y-%m-%d') if created_at else 'unknown'
            print(f"  {i}. {conv_id} (created: {date_str})")

def example_custom_analysis():
    """Example: Custom analysis with specific patterns."""
    print("\n=== Custom Analysis Example ===")
    
    # Load environment
    load_dotenv()
    access_token = os.getenv('INTERCOM_ACCESS_TOKEN')
    
    if not access_token:
        print("Please set INTERCOM_ACCESS_TOKEN in your .env file")
        return
    
    # Initialize clients
    client = IntercomClient(access_token=access_token)
    text_analyzer = TextAnalyzer(num_keywords=10)  # Extract fewer keywords
    
    # Define date range (last 7 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    # Create query
    query = client.create_date_range_query(start_date, end_date)
    
    print(f"Analyzing conversations from {start_date.date()} to {end_date.date()}")
    
    # Fetch conversations
    conversations = list(client.search_conversations(query=query, max_pages=3))
    print(f"Found {len(conversations)} conversations")
    
    if not conversations:
        print("No conversations found in the specified date range")
        return
    
    # Custom patterns for tech support
    tech_patterns = [
        'browser', 'chrome', 'firefox', 'safari', 'edge',
        'extension', 'plugin', 'addon',
        'cache', 'cookies', 'storage',
        'slow', 'loading', 'timeout', 'error'
    ]
    
    # Analyze patterns
    pattern_counts = TrendAnalyzer.pattern_analysis(conversations, tech_patterns)
    
    print("\nTech Support Pattern Analysis:")
    sorted_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)
    for pattern, count in sorted_patterns:
        percentage = (count / len(conversations)) * 100
        print(f"  {pattern:15s}: {count:3d} ({percentage:5.1f}%)")
    
    # Analyze by hour
    hourly_data = TrendAnalyzer.conversations_by_hour(conversations)
    if not hourly_data.empty:
        print("\nTop 5 Busiest Hours:")
        top_hours = hourly_data.nlargest(5, 'count')
        for _, row in top_hours.iterrows():
            hour = row['hour']
            count = row['count']
            print(f"  {hour:2d}:00 - {count} conversations")

if __name__ == "__main__":
    print("Intercom Analysis Tool - Example Usage")
    print("=" * 50)
    
    try:
        example_basic_analysis()
        example_text_search()
        example_custom_analysis()
        
        print("\n" + "=" * 50)
        print("Examples completed successfully!")
        print("Check the outputs/ directory for generated reports.")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        print("Make sure you have:")
        print("1. Set INTERCOM_ACCESS_TOKEN in your .env file")
        print("2. Installed all dependencies: pip install -r requirements.txt")
        print("3. Valid Intercom API access")


