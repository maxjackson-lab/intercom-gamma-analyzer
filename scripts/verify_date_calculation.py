#!/usr/bin/env python3
"""
Verification script to test date range calculations.
Shows what dates would be used for different time periods.
"""

from datetime import datetime, timedelta
import pytz

def test_week_calculation():
    """Test the new week calculation logic."""
    
    print("="*80)
    print("Date Range Calculation Verification")
    print("="*80)
    
    # Simulate today's date
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    print(f"\nToday (normalized): {today.strftime('%Y-%m-%d')}")
    
    # Calculate week (7 complete days, ending yesterday)
    end_dt = today - timedelta(days=1)
    start_dt = end_dt - timedelta(days=6)
    
    print(f"\n{'='*80}")
    print("WEEK Calculation (--time-period week)")
    print(f"{'='*80}")
    print(f"Start date: {start_dt.strftime('%Y-%m-%d')}")
    print(f"End date:   {end_dt.strftime('%Y-%m-%d')}")
    
    # Calculate number of days
    days_diff = (end_dt - start_dt).days + 1
    print(f"Number of complete days: {days_diff}")
    
    # Convert to Pacific and UTC
    pacific_tz = pytz.timezone('America/Los_Angeles')
    
    # Start of start_date in Pacific (00:00:00)
    start_pacific = pacific_tz.localize(datetime.combine(start_dt.date(), datetime.min.time()))
    # End of end_date in Pacific (23:59:59)
    end_pacific = pacific_tz.localize(
        datetime.combine(end_dt.date(), datetime.max.time().replace(microsecond=0))
    )
    
    # Convert to UTC
    start_utc = start_pacific.astimezone(pytz.UTC)
    end_utc = end_pacific.astimezone(pytz.UTC)
    
    print(f"\nPacific Time:")
    print(f"  Start: {start_pacific}")
    print(f"  End:   {end_pacific}")
    print(f"\nUTC Time:")
    print(f"  Start: {start_utc}")
    print(f"  End:   {end_utc}")
    
    # Calculate UTC calendar days
    utc_days = (end_utc.date() - start_utc.date()).days + 1
    print(f"\nUTC calendar days: {utc_days}")
    
    if utc_days > 7:
        print(f"⚠️  WARNING: UTC conversion spans {utc_days} calendar days (expected 7-8 due to timezone)")
    else:
        print("✅ Date range is correct")
    
    # Show what would be queried
    print(f"\n{'='*80}")
    print("What gets sent to Intercom API:")
    print(f"{'='*80}")
    print(f"created_at >= {int(start_utc.timestamp())} ({start_utc})")
    print(f"created_at <= {int(end_utc.timestamp())} ({end_utc})")
    
    # Test other periods
    print(f"\n{'='*80}")
    print("OTHER TIME PERIODS")
    print(f"{'='*80}")
    
    # Month (30 days)
    end_month = today - timedelta(days=1)
    start_month = end_month - timedelta(days=29)
    month_days = (end_month - start_month).days + 1
    print(f"\nMONTH (30 days):")
    print(f"  {start_month.strftime('%Y-%m-%d')} to {end_month.strftime('%Y-%m-%d')}")
    print(f"  Days: {month_days}")
    
    # Quarter (90 days)
    end_quarter = today - timedelta(days=1)
    start_quarter = end_quarter - timedelta(days=89)
    quarter_days = (end_quarter - start_quarter).days + 1
    print(f"\nQUARTER (90 days):")
    print(f"  {start_quarter.strftime('%Y-%m-%d')} to {end_quarter.strftime('%Y-%m-%d')}")
    print(f"  Days: {quarter_days}")
    
    # Year (365 days)
    end_year = today - timedelta(days=1)
    start_year = end_year - timedelta(days=364)
    year_days = (end_year - start_year).days + 1
    print(f"\nYEAR (365 days):")
    print(f"  {start_year.strftime('%Y-%m-%d')} to {end_year.strftime('%Y-%m-%d')}")
    print(f"  Days: {year_days}")
    
    print(f"\n{'='*80}")
    print("✅ Verification complete")
    print(f"{'='*80}")


if __name__ == "__main__":
    test_week_calculation()

