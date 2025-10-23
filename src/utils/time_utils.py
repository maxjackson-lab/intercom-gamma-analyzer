"""
Time utilities for consistent timestamp handling across the Intercom Analysis Tool.

This module provides centralized functions to handle conversion between:
- Unix timestamps (int/float seconds since epoch)
- datetime objects (timezone-aware UTC)
- date objects

All functions safely handle multiple input types and return consistent outputs.
"""

from datetime import datetime, date, timezone
from typing import Union, Optional
import logging

logger = logging.getLogger(__name__)


def to_utc_datetime(value: Union[datetime, int, float, str, None]) -> Optional[datetime]:
    """
    Convert various types to a timezone-aware UTC datetime.
    
    Args:
        value: Input value (datetime, int/float timestamp, ISO string, or None)
        
    Returns:
        Timezone-aware UTC datetime, or None if conversion fails
        
    Examples:
        >>> to_utc_datetime(1697558400)  # Unix timestamp
        datetime(2023, 10, 17, 16, 0, 0, tzinfo=timezone.utc)
        
        >>> to_utc_datetime(datetime(2023, 10, 17, 16, 0, 0))  # naive datetime
        datetime(2023, 10, 17, 16, 0, 0, tzinfo=timezone.utc)
        
        >>> to_utc_datetime("2023-10-17T16:00:00Z")  # ISO string
        datetime(2023, 10, 17, 16, 0, 0, tzinfo=timezone.utc)
    """
    if value is None:
        return None
    
    try:
        # Already a datetime
        if isinstance(value, datetime):
            if value.tzinfo is None:
                # Naive datetime - assume UTC
                return value.replace(tzinfo=timezone.utc)
            else:
                # Convert to UTC
                return value.astimezone(timezone.utc)
        
        # Unix timestamp (int or float)
        elif isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        
        # ISO format string
        elif isinstance(value, str):
            # Try parsing ISO format
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        
        else:
            logger.warning(f"Cannot convert type {type(value)} to datetime: {value}")
            return None
            
    except (ValueError, OSError, OverflowError) as e:
        logger.warning(f"Failed to convert value to datetime: {value}, error: {e}")
        return None


def to_timestamp_seconds(value: Union[datetime, int, float, str, None]) -> Optional[int]:
    """
    Convert various types to Unix timestamp (seconds since epoch).
    
    Args:
        value: Input value (datetime, int/float timestamp, ISO string, or None)
        
    Returns:
        Unix timestamp as integer, or None if conversion fails
        
    Examples:
        >>> to_timestamp_seconds(datetime(2023, 10, 17, 16, 0, 0, tzinfo=timezone.utc))
        1697558400
        
        >>> to_timestamp_seconds(1697558400.5)
        1697558400
    """
    if value is None:
        return None
    
    try:
        # Already a timestamp
        if isinstance(value, (int, float)):
            return int(value)
        
        # datetime - convert to timestamp
        elif isinstance(value, datetime):
            if value.tzinfo is None:
                # Naive datetime - assume UTC
                value = value.replace(tzinfo=timezone.utc)
            return int(value.timestamp())
        
        # String - parse to datetime first
        elif isinstance(value, str):
            dt = to_utc_datetime(value)
            if dt:
                return int(dt.timestamp())
            return None
        
        else:
            logger.warning(f"Cannot convert type {type(value)} to timestamp: {value}")
            return None
            
    except (ValueError, OSError, OverflowError) as e:
        logger.warning(f"Failed to convert value to timestamp: {value}, error: {e}")
        return None


def ensure_date(value: Union[datetime, date, int, float, str, None]) -> Optional[date]:
    """
    Convert various types to a date object.
    
    Args:
        value: Input value (datetime, date, int/float timestamp, ISO string, or None)
        
    Returns:
        date object, or None if conversion fails
        
    Examples:
        >>> ensure_date(datetime(2023, 10, 17, 16, 0, 0))
        date(2023, 10, 17)
        
        >>> ensure_date(1697558400)
        date(2023, 10, 17)
    """
    if value is None:
        return None
    
    try:
        # Already a date
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        
        # datetime - extract date
        elif isinstance(value, datetime):
            return value.date()
        
        # Unix timestamp - convert to datetime first
        elif isinstance(value, (int, float)):
            dt = to_utc_datetime(value)
            if dt:
                return dt.date()
            return None
        
        # String - parse to datetime first
        elif isinstance(value, str):
            dt = to_utc_datetime(value)
            if dt:
                return dt.date()
            return None
        
        else:
            logger.warning(f"Cannot convert type {type(value)} to date: {value}")
            return None
            
    except (ValueError, OSError, OverflowError) as e:
        logger.warning(f"Failed to convert value to date: {value}, error: {e}")
        return None


def calculate_time_delta_seconds(
    start: Union[datetime, int, float],
    end: Union[datetime, int, float]
) -> Optional[float]:
    """
    Calculate time difference in seconds between two timestamps.
    
    Args:
        start: Start time (datetime or Unix timestamp)
        end: End time (datetime or Unix timestamp)
        
    Returns:
        Time difference in seconds, or None if calculation fails
        
    Examples:
        >>> calculate_time_delta_seconds(1697558400, 1697562000)
        3600.0
        
        >>> dt1 = datetime(2023, 10, 17, 16, 0, 0, tzinfo=timezone.utc)
        >>> dt2 = datetime(2023, 10, 17, 17, 0, 0, tzinfo=timezone.utc)
        >>> calculate_time_delta_seconds(dt1, dt2)
        3600.0
    """
    try:
        # Convert both to datetime
        start_dt = to_utc_datetime(start)
        end_dt = to_utc_datetime(end)
        
        if start_dt is None or end_dt is None:
            return None
        
        # Calculate difference
        delta = end_dt - start_dt
        return delta.total_seconds()
        
    except Exception as e:
        logger.warning(f"Failed to calculate time delta: {e}")
        return None


def safe_min_datetime(*values: Union[datetime, int, float, None]) -> Optional[datetime]:
    """
    Safely get the minimum datetime from a list of mixed types.
    
    Args:
        *values: Variable number of datetime/timestamp values
        
    Returns:
        Minimum datetime as UTC datetime, or None if no valid values
    """
    datetimes = [to_utc_datetime(v) for v in values if v is not None]
    datetimes = [dt for dt in datetimes if dt is not None]
    
    if not datetimes:
        return None
    
    return min(datetimes)


def safe_max_datetime(*values: Union[datetime, int, float, None]) -> Optional[datetime]:
    """
    Safely get the maximum datetime from a list of mixed types.
    
    Args:
        *values: Variable number of datetime/timestamp values
        
    Returns:
        Maximum datetime as UTC datetime, or None if no valid values
    """
    datetimes = [to_utc_datetime(v) for v in values if v is not None]
    datetimes = [dt for dt in datetimes if dt is not None]
    
    if not datetimes:
        return None
    
    return max(datetimes)


def format_datetime_for_display(value: Union[datetime, int, float, None], fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a datetime or timestamp for human-readable display.
    
    Args:
        value: Input value (datetime or Unix timestamp)
        fmt: strftime format string
        
    Returns:
        Formatted date string, or "unknown" if conversion fails
    """
    dt = to_utc_datetime(value)
    if dt is None:
        return "unknown"
    
    try:
        return dt.strftime(fmt)
    except Exception as e:
        logger.warning(f"Failed to format datetime: {e}")
        return "unknown"

