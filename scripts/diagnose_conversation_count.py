#!/usr/bin/env python3
"""
Quick diagnostic script to check conversation counts in Intercom.
This will fetch only the first page and estimate total volume.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pytz

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.intercom_sdk_service import IntercomSDKService
from src.utils.timezone_utils import get_date_range


async def diagnose_count(days: int = 7):
    """Check conversation count for the last N days."""
    
    # Get date range (same logic as main app)
    pacific_tz = pytz.timezone('America/Los_Angeles')
    end_date = datetime.now(pacific_tz)
    start_date = end_date - timedelta(days=days)
    
    # Reset to start/end of day
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Convert to UTC for API
    start_utc = start_date.astimezone(pytz.UTC)
    end_utc = end_date.astimezone(pytz.UTC)
    
    print("="*80)
    print(f"Diagnosing conversation count for last {days} days")
    print("="*80)
    print(f"\nPacific Time:")
    print(f"  Start: {start_date}")
    print(f"  End:   {end_date}")
    print(f"\nUTC Time:")
    print(f"  Start: {start_utc}")
    print(f"  End:   {end_utc}")
    print(f"\nTimestamp range:")
    print(f"  Start: {int(start_utc.timestamp())}")
    print(f"  End:   {int(end_utc.timestamp())}")
    
    # Initialize service
    service = IntercomSDKService()
    
    # Test connection
    print("\n" + "="*80)
    print("Testing Intercom connection...")
    print("="*80)
    connected = await service.test_connection()
    if not connected:
        print("❌ Failed to connect to Intercom API")
        return
    print("✅ Connected to Intercom API")
    
    # Fetch first 100 conversations to estimate
    print("\n" + "="*80)
    print("Fetching first 100 conversations to estimate total...")
    print("="*80)
    
    try:
        conversations = await service.fetch_conversations_by_date_range(
            start_utc,
            end_utc,
            max_conversations=100
        )
        
        print(f"\n✅ Fetched {len(conversations)} conversations (limited to 100)")
        
        if conversations:
            # Show date range of actual conversations
            dates = []
            for conv in conversations:
                created_at = conv.get('created_at')
                if created_at:
                    if isinstance(created_at, (int, float)):
                        dt = datetime.fromtimestamp(created_at, tz=pytz.UTC)
                    else:
                        dt = created_at
                    dates.append(dt)
            
            if dates:
                min_date = min(dates)
                max_date = max(dates)
                print(f"\nActual date range in sample:")
                print(f"  Earliest: {min_date}")
                print(f"  Latest:   {max_date}")
                
                # Check if any are outside requested range
                outside_count = sum(1 for d in dates if d < start_utc or d > end_utc)
                if outside_count > 0:
                    print(f"\n⚠️  WARNING: {outside_count}/{len(conversations)} conversations are OUTSIDE the requested date range!")
                    print("This suggests the Intercom API is not respecting date filters properly.")
                else:
                    print(f"\n✅ All {len(conversations)} conversations are within the requested date range")
            
            # Estimate if there are more
            if len(conversations) == 100:
                print("\n⚠️  NOTE: Reached the 100 conversation limit.")
                print("There are likely MORE conversations in this date range.")
                print("Based on pagination patterns, the actual count could be:")
                print("  - Conservative estimate: 1,000 - 5,000 conversations")
                print("  - If volume is high: 5,000 - 20,000+ conversations")
            else:
                print(f"\n✅ Total conversations in date range: {len(conversations)}")
        else:
            print("❌ No conversations found in this date range")
    
    except Exception as e:
        print(f"\n❌ Error fetching conversations: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("Diagnosis complete")
    print("="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Diagnose Intercom conversation counts")
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to check (default: 7)"
    )
    
    args = parser.parse_args()
    
    asyncio.run(diagnose_count(args.days))

