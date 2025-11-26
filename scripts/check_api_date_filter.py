#!/usr/bin/env python3
"""
Test script to verify Intercom API date filtering behavior.
This will make a raw API call and show exactly what the API returns.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pytz
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from intercom.client import AsyncClient
from intercom.types import MultipleFilterSearchRequest, SingleFilterSearchRequest, StartingAfterPaging


async def test_date_filter():
    """Test if Intercom API respects date filters."""
    
    # Get credentials
    access_token = os.environ.get('INTERCOM_ACCESS_TOKEN')
    if not access_token:
        print("❌ INTERCOM_ACCESS_TOKEN not set")
        return
    
    # Setup dates for last 7 days
    pacific_tz = pytz.timezone('America/Los_Angeles')
    end_date = datetime.now(pacific_tz)
    start_date = end_date - timedelta(days=7)
    
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    start_utc = start_date.astimezone(pytz.UTC)
    end_utc = end_date.astimezone(pytz.UTC)
    
    start_ts = int(start_utc.timestamp())
    end_ts = int(end_utc.timestamp())
    
    print("="*80)
    print("Testing Intercom API Date Filter")
    print("="*80)
    print(f"\nRequested range (Pacific):")
    print(f"  Start: {start_date}")
    print(f"  End:   {end_date}")
    print(f"\nRequested range (UTC):")
    print(f"  Start: {start_utc}")
    print(f"  End:   {end_utc}")
    print(f"\nTimestamps:")
    print(f"  Start: {start_ts}")
    print(f"  End:   {end_ts}")
    
    # Create client
    client = AsyncClient(access_token=access_token)
    
    # Build query
    search_query = MultipleFilterSearchRequest(
        operator="AND",
        value=[
            SingleFilterSearchRequest(
                field="created_at",
                operator=">=",
                value=start_ts
            ),
            SingleFilterSearchRequest(
                field="created_at",
                operator="<=",
                value=end_ts
            )
        ]
    )
    
    pagination = StartingAfterPaging(
        per_page=50,
        starting_after=None
    )
    
    print("\n" + "="*80)
    print("Making API call (fetching first 50 conversations)...")
    print("="*80)
    
    try:
        pager = await client.conversations.search(
            query=search_query,
            pagination=pagination
        )
        
        conversations = []
        count = 0
        
        async for conversation in pager:
            conversations.append(conversation)
            count += 1
            if count >= 50:
                break
        
        print(f"\n✅ Fetched {len(conversations)} conversations")
        
        if conversations:
            # Analyze dates
            print("\n" + "="*80)
            print("Analyzing conversation dates...")
            print("="*80)
            
            dates_in_range = 0
            dates_outside_range = 0
            earliest = None
            latest = None
            
            print("\nFirst 10 conversations:")
            for i, conv in enumerate(conversations[:10]):
                created_ts = conv.created_at
                created_dt = datetime.fromtimestamp(created_ts, tz=pytz.UTC)
                
                in_range = start_utc <= created_dt <= end_utc
                status = "✅" if in_range else "❌"
                
                if in_range:
                    dates_in_range += 1
                else:
                    dates_outside_range += 1
                
                if earliest is None or created_dt < earliest:
                    earliest = created_dt
                if latest is None or created_dt > latest:
                    latest = created_dt
                
                print(f"  {i+1}. {status} ID: {conv.id} | Created: {created_dt} | In range: {in_range}")
            
            # Process remaining conversations
            for conv in conversations[10:]:
                created_ts = conv.created_at
                created_dt = datetime.fromtimestamp(created_ts, tz=pytz.UTC)
                
                in_range = start_utc <= created_dt <= end_utc
                if in_range:
                    dates_in_range += 1
                else:
                    dates_outside_range += 1
                
                if earliest is None or created_dt < earliest:
                    earliest = created_dt
                if latest is None or created_dt > latest:
                    latest = created_dt
            
            print(f"\n{'='*80}")
            print("Summary:")
            print(f"{'='*80}")
            print(f"Total conversations fetched: {len(conversations)}")
            print(f"  In requested range:  {dates_in_range} ({dates_in_range/len(conversations)*100:.1f}%)")
            print(f"  Outside range:       {dates_outside_range} ({dates_outside_range/len(conversations)*100:.1f}%)")
            print(f"\nActual date range returned:")
            print(f"  Earliest: {earliest}")
            print(f"  Latest:   {latest}")
            print(f"\nRequested date range:")
            print(f"  Start:    {start_utc}")
            print(f"  End:      {end_utc}")
            
            if dates_outside_range > 0:
                print("\n⚠️  WARNING: Intercom API returned conversations OUTSIDE the requested date range!")
                print("This is likely a known issue with Intercom's date filtering.")
                print("The application should be filtering these out client-side.")
            else:
                print("\n✅ All conversations are within the requested date range")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("Test complete")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_date_filter())


