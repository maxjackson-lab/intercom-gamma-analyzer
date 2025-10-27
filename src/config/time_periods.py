"""
Centralized Time Period Configuration
======================================

Single source of truth for time period options.

This eliminates duplication across:
- src/main.py (multiple CLI options)
- deploy/railway_web.py (schemas)
- src/services/web_command_executor.py (validation)

Usage:
    from src.config.time_periods import TIME_PERIOD_OPTIONS, get_timedelta_for_period
"""

from datetime import timedelta
from typing import Dict, List, Optional

# Standard time period options
TIME_PERIOD_OPTIONS: List[str] = ['yesterday', 'week', 'month', 'quarter', 'year']

# CLI-specific options (subset)
CLI_TIME_PERIOD_OPTIONS: List[str] = ['week', 'month', 'quarter']

# Agent performance specific
AGENT_PERFORMANCE_PERIODS: List[str] = ['week', 'month', '6-weeks', 'quarter']

# Time period to timedelta mapping
TIME_PERIOD_DELTAS: Dict[str, timedelta] = {
    'yesterday': timedelta(days=1),
    'week': timedelta(weeks=1),
    'month': timedelta(days=30),
    '6-weeks': timedelta(weeks=6),
    'quarter': timedelta(days=90),
    'year': timedelta(days=365)
}

# Human-readable descriptions
TIME_PERIOD_DESCRIPTIONS: Dict[str, str] = {
    'yesterday': 'Last 24 hours',
    'week': 'Last 7 days',
    'month': 'Last 30 days',
    '6-weeks': 'Last 6 weeks',
    'quarter': 'Last 90 days (quarter)',
    'year': 'Last 365 days (year)'
}


def get_timedelta_for_period(period: str) -> Optional[timedelta]:
    """
    Get timedelta for a time period string.
    
    Args:
        period: Time period key (e.g., 'week', 'month')
        
    Returns:
        timedelta object or None if invalid
        
    Example:
        >>> get_timedelta_for_period('week')
        timedelta(weeks=1)
        >>> get_timedelta_for_period('month')
        timedelta(days=30)
    """
    return TIME_PERIOD_DELTAS.get(period)


def get_period_description(period: str) -> str:
    """Get human-readable description for period."""
    return TIME_PERIOD_DESCRIPTIONS.get(period, period)


def is_valid_period(period: str) -> bool:
    """Check if period is valid."""
    return period in TIME_PERIOD_OPTIONS


# Schema definitions
STANDARD_CLI_SCHEMA = {
    'type': 'Choice',
    'choices': CLI_TIME_PERIOD_OPTIONS,
    'help': 'Time period shortcut'
}

FULL_CLI_SCHEMA = {
    'type': 'Choice',
    'choices': TIME_PERIOD_OPTIONS,
    'help': 'Time period for analysis'
}

AGENT_PERFORMANCE_CLI_SCHEMA = {
    'type': 'Choice',
    'choices': AGENT_PERFORMANCE_PERIODS,
    'help': 'Time period for analysis'
}

WEB_SCHEMA = {
    'type': 'enum',
    'values': TIME_PERIOD_OPTIONS
}

