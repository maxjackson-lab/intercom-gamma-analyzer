"""
Shared time range calculation utilities.

This module provides a standardized approach to computing date ranges across all commands,
ensuring consistent behavior and reducing code duplication.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Union
from pathlib import Path


def calculate_date_range(
    time_period: Optional[str] = None,
    periods_back: int = 1,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    end_is_yesterday: bool = True
) -> Tuple[datetime, datetime]:
    """
    Calculate start and end dates from various input combinations.
    
    Priority:
    1. If start_date and end_date are provided, use them
    2. If time_period is provided, calculate relative to end date
    3. Otherwise, raise ValueError
    
    Args:
        time_period: One of 'yesterday', 'week', 'month', 'quarter', 'year', '6-weeks'
        periods_back: Number of periods to go back (default: 1)
        start_date: Explicit start date in YYYY-MM-DD format
        end_date: Explicit end date in YYYY-MM-DD format
        end_is_yesterday: If True, use yesterday as end date for time_period calculations
                         If False, use today (now)
        
    Returns:
        Tuple of (start_datetime, end_datetime)
        
    Raises:
        ValueError: If inputs are invalid or insufficient
        
    Examples:
        >>> # Last week, ending yesterday
        >>> start, end = calculate_date_range(time_period='week')
        
        >>> # Last 3 months, ending yesterday
        >>> start, end = calculate_date_range(time_period='month', periods_back=3)
        
        >>> # Explicit date range
        >>> start, end = calculate_date_range(start_date='2025-01-01', end_date='2025-01-31')
        
        >>> # Yesterday only
        >>> start, end = calculate_date_range(time_period='yesterday')
    """
    # Case 1: Explicit start and end dates provided
    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            if start_dt > end_dt:
                raise ValueError(f"Start date {start_date} is after end date {end_date}")
            
            return start_dt, end_dt
        except ValueError as e:
            if "does not match format" in str(e):
                raise ValueError(
                    f"Invalid date format. Expected YYYY-MM-DD, got start='{start_date}', end='{end_date}'"
                ) from e
            raise
    
    # Case 2: Time period provided
    if time_period:
        # Determine end date
        if end_is_yesterday:
            end_dt = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            end_dt = end_dt - timedelta(days=1)  # Yesterday
        else:
            end_dt = datetime.now()
        
        # Calculate start date based on period
        if time_period == 'yesterday':
            start_dt = end_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            # end_dt is already set to end of yesterday
        elif time_period == 'week':
            start_dt = end_dt - timedelta(weeks=periods_back)
        elif time_period == 'month':
            start_dt = end_dt - timedelta(days=30 * periods_back)
        elif time_period == '6-weeks':
            start_dt = end_dt - timedelta(weeks=6 * periods_back)
        elif time_period == 'quarter':
            start_dt = end_dt - timedelta(days=90 * periods_back)
        elif time_period == 'year':
            start_dt = end_dt - timedelta(days=365 * periods_back)
        else:
            raise ValueError(
                f"Invalid time_period '{time_period}'. "
                f"Must be one of: yesterday, week, month, quarter, year, 6-weeks"
            )
        
        return start_dt, end_dt
    
    # Case 3: No valid input provided
    raise ValueError(
        "Must provide either (start_date AND end_date) OR time_period. "
        "Got: start_date={start_date}, end_date={end_date}, time_period={time_period}"
    )


def format_date_range_for_display(start_dt: datetime, end_dt: datetime) -> str:
    """
    Format date range for user-friendly display.
    
    Args:
        start_dt: Start datetime
        end_dt: End datetime
        
    Returns:
        Formatted string like "Jan 1, 2025 - Jan 31, 2025"
    """
    return f"{start_dt.strftime('%b %d, %Y')} - {end_dt.strftime('%b %d, %Y')}"


def get_days_difference(start_dt: datetime, end_dt: datetime) -> int:
    """
    Get number of days between start and end dates.
    
    Args:
        start_dt: Start datetime
        end_dt: End datetime
        
    Returns:
        Number of days (rounded)
    """
    return (end_dt - start_dt).days


def detect_period_type(start_dt: datetime, end_dt: datetime) -> Tuple[str, str]:
    """
    Detect the period type from date range.
    
    Args:
        start_dt: Start datetime
        end_dt: End datetime
        
    Returns:
        Tuple of (period_type, period_label)
        - period_type: 'daily', 'weekly', 'monthly', 'quarterly', or 'custom'
        - period_label: Human-readable label like "Week of Nov 01, 2025"
    """
    days = get_days_difference(start_dt, end_dt)
    
    # Determine period type based on duration
    if days <= 1:
        period_type = 'daily'
        period_label = f"Day of {start_dt.strftime('%b %d, %Y')}"
    elif 5 <= days <= 9:
        period_type = 'weekly'
        period_label = f"Week of {start_dt.strftime('%b %d, %Y')}"
    elif 25 <= days <= 35:
        period_type = 'monthly'
        period_label = f"Month of {start_dt.strftime('%B %Y')}"
    elif 80 <= days <= 100:
        period_type = 'quarterly'
        period_label = f"Quarter ending {end_dt.strftime('%b %Y')}"
    else:
        period_type = 'custom'
        period_label = format_date_range_for_display(start_dt, end_dt)
    
    return period_type, period_label


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string like "2h 30m 15s" or "45s"
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes > 0:
            return f"{int(hours)}h {int(minutes)}m"
        return f"{int(hours)}h"


# Standard time period choices for CLI options
TIME_PERIOD_CHOICES = ['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks']

# Help text for time period option
TIME_PERIOD_HELP = (
    "Time period for analysis. Defaults to ending yesterday. "
    "Use --periods-back to analyze multiple periods "
    "(e.g., --time-period month --periods-back 3 for last 3 months)"
)

# Help text for periods back option
PERIODS_BACK_HELP = (
    "Number of periods to go back (default: 1). "
    "Example: --time-period month --periods-back 3 analyzes last 3 months"
)


def generate_descriptive_filename(
    analysis_type: str,
    start_date: datetime,
    end_date: datetime,
    extension: str = "md"
) -> str:
    """
    Generate descriptive filename for analysis outputs.
    
    Args:
        analysis_type: Type of analysis (e.g., 'voice-of-customer', 'billing')
        start_date: Start datetime
        end_date: End datetime
        extension: File extension (default: 'md')
        
    Returns:
        Filename like "voice-of-customer_2025-10-29_to_2025-11-05.md"
    """
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    return f"{analysis_type}_{start_str}_to_{end_str}.{extension}"


def to_utc_datetime(dt: Union[datetime, str]) -> datetime:
    """
    Convert datetime or string to UTC datetime.
    
    Args:
        dt: Datetime object or ISO format string
        
    Returns:
        Datetime in UTC timezone
    """
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
    
    if dt.tzinfo is None:
        # Naive datetime - assume UTC
        return dt.replace(tzinfo=timezone.utc)
    
    # Convert to UTC
    return dt.astimezone(timezone.utc)


def ensure_date(dt: Union[datetime, str]) -> datetime:
    """
    Ensure value is a datetime object.
    
    Args:
        dt: Datetime object or ISO format string
        
    Returns:
        Datetime object
    """
    if isinstance(dt, str):
        return datetime.fromisoformat(dt.replace('Z', '+00:00'))
    return dt


def calculate_time_delta_seconds(start: datetime, end: datetime) -> float:
    """
    Calculate time delta between two datetimes in seconds.
    
    Args:
        start: Start datetime
        end: End datetime
        
    Returns:
        Time delta in seconds
    """
    return (end - start).total_seconds()


def format_datetime_for_display(dt: datetime) -> str:
    """
    Format datetime for user-friendly display.
    
    Args:
        dt: Datetime to format
        
    Returns:
        Formatted string like "Nov 05, 2025 03:30 PM"
    """
    return dt.strftime('%b %d, %Y %I:%M %p')
