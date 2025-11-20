"""
Timezone utilities for Intercom Analysis Tool.
Ensures consistent timezone handling between Pacific Time and UTC.
"""

from datetime import datetime, time
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger(__name__)

# Pacific timezone
PACIFIC_TZ = ZoneInfo("America/Los_Angeles")
UTC_TZ = ZoneInfo("UTC")


def naive_date_to_pacific_datetime(date_str: str, end_of_day: bool = False) -> datetime:
    """
    Convert a naive date string (YYYY-MM-DD) to a timezone-aware Pacific datetime.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        end_of_day: If True, set time to 23:59:59; otherwise 00:00:00
        
    Returns:
        Timezone-aware datetime in Pacific Time
        
    Example:
        >>> naive_date_to_pacific_datetime("2025-10-07", False)
        datetime(2025, 10, 7, 0, 0, 0, tzinfo=ZoneInfo('America/Los_Angeles'))
    """
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    
    if end_of_day:
        dt = datetime.combine(dt.date(), time(23, 59, 59))
    else:
        dt = datetime.combine(dt.date(), time(0, 0, 0))
    
    # Make timezone-aware in Pacific
    dt_pacific = dt.replace(tzinfo=PACIFIC_TZ)
    
    logger.debug(f"Converted '{date_str}' to Pacific: {dt_pacific} (UTC: {dt_pacific.astimezone(UTC_TZ)})")
    
    return dt_pacific


def datetime_to_pacific(dt: datetime) -> datetime:
    """
    Convert any datetime to Pacific timezone.
    
    Args:
        dt: Datetime (naive or aware)
        
    Returns:
        Timezone-aware datetime in Pacific Time
    """
    if dt.tzinfo is None:
        # Naive datetime - assume it's already Pacific
        dt = dt.replace(tzinfo=PACIFIC_TZ)
    else:
        # Convert to Pacific
        dt = dt.astimezone(PACIFIC_TZ)
    
    return dt


def datetime_to_utc(dt: datetime) -> datetime:
    """
    Convert any datetime to UTC.
    
    Args:
        dt: Datetime (naive or aware)
        
    Returns:
        Timezone-aware datetime in UTC
    """
    if dt.tzinfo is None:
        # Naive datetime - assume it's Pacific
        dt = dt.replace(tzinfo=PACIFIC_TZ)
    
    return dt.astimezone(UTC_TZ)


def get_date_range_pacific(start_date_str: str, end_date_str: str) -> tuple[datetime, datetime]:
    """
    Get a date range in Pacific Time for Intercom API queries.
    
    Args:
        start_date_str: Start date (YYYY-MM-DD)
        end_date_str: End date (YYYY-MM-DD)
        
    Returns:
        Tuple of (start_datetime, end_datetime) in Pacific timezone
        
    Example:
        >>> get_date_range_pacific("2025-10-07", "2025-10-14")
        (datetime(2025, 10, 7, 0, 0, 0, tzinfo=...), datetime(2025, 10, 14, 23, 59, 59, tzinfo=...))
    """
    start_dt = naive_date_to_pacific_datetime(start_date_str, end_of_day=False)
    end_dt = naive_date_to_pacific_datetime(end_date_str, end_of_day=True)
    
    logger.info(f"Date range (Pacific): {start_dt} to {end_dt}")
    logger.info(f"Date range (UTC): {start_dt.astimezone(UTC_TZ)} to {end_dt.astimezone(UTC_TZ)}")
    
    return start_dt, end_dt

