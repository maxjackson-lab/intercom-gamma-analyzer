"""
Centralized Test Data Configuration
====================================

Single source of truth for all test data limits, presets, and validation.

This eliminates duplication across:
- src/main.py (4 locations)
- deploy/railway_web.py (3 schemas)
- src/services/web_command_executor.py (1 schema)

Usage:
    from src.config.test_data_config import TEST_DATA_PRESETS, TEST_DATA_LIMITS
"""

from typing import Dict, Optional

# Test data volume limits
TEST_DATA_LIMITS = {
    'min': 10,
    'max': 25000,
    'default': 100
}

# Test data presets with descriptions
TEST_DATA_PRESETS = {
    'micro': {
        'count': 100,
        'description': '1 hour of data',
        'label': '100 conversations (1 hour)'
    },
    'small': {
        'count': 500,
        'description': 'Few hours',
        'label': '500 conversations (few hours)'
    },
    'medium': {
        'count': 1000,
        'description': '~1 day',
        'label': '1,000 conversations (~1 day)'
    },
    'large': {
        'count': 5000,
        'description': '~1 week (realistic)',
        'label': '5,000 conversations (~1 week) ⭐'
    },
    'xlarge': {
        'count': 10000,
        'description': '2 weeks',
        'label': '10,000 conversations (2 weeks)'
    },
    'xxlarge': {
        'count': 20000,
        'description': '1 month',
        'label': '20,000 conversations (1 month)'
    }
}

# Simple value-only dict for backward compatibility
TEST_DATA_PRESET_VALUES = {
    name: preset['count']
    for name, preset in TEST_DATA_PRESETS.items()
}


def get_preset_value(name: str) -> Optional[int]:
    """
    Get test data count for a preset name.
    
    Args:
        name: Preset name (micro, small, medium, large, xlarge, xxlarge)
        
    Returns:
        Integer count or None if preset doesn't exist
        
    Example:
        >>> get_preset_value('large')
        5000
        >>> get_preset_value('invalid')
        None
    """
    return TEST_DATA_PRESET_VALUES.get(name.lower())


def parse_test_data_count(value: str) -> tuple[int, Optional[str]]:
    """
    Parse test data count from string (preset name or number).
    
    Args:
        value: Preset name (e.g., 'large') or number string (e.g., '2500')
        
    Returns:
        Tuple of (count, preset_name) where preset_name is None if custom number
        
    Raises:
        ValueError: If value is invalid
        
    Example:
        >>> parse_test_data_count('large')
        (5000, 'large')
        >>> parse_test_data_count('2500')
        (2500, None)
        >>> parse_test_data_count('invalid')
        ValueError: Invalid test data count
    """
    # Try preset first
    if value.lower() in TEST_DATA_PRESET_VALUES:
        return TEST_DATA_PRESET_VALUES[value.lower()], value.lower()
    
    # Try as integer
    try:
        count = int(value)
        if not validate_test_data_count(count):
            raise ValueError(
                f"Test data count {count} out of range "
                f"({TEST_DATA_LIMITS['min']}-{TEST_DATA_LIMITS['max']})"
            )
        return count, None
    except ValueError as e:
        if "out of range" in str(e):
            raise
        raise ValueError(
            f"Invalid test data count '{value}'. "
            f"Use a number ({TEST_DATA_LIMITS['min']}-{TEST_DATA_LIMITS['max']}) "
            f"or preset: {', '.join(TEST_DATA_PRESET_VALUES.keys())}"
        )


def validate_test_data_count(value: int) -> bool:
    """
    Validate test data count is within configured limits.
    
    Args:
        value: Test data count to validate
        
    Returns:
        True if valid, False otherwise
        
    Example:
        >>> validate_test_data_count(5000)
        True
        >>> validate_test_data_count(50000)
        False
    """
    return TEST_DATA_LIMITS['min'] <= value <= TEST_DATA_LIMITS['max']


def get_preset_names() -> list[str]:
    """Get list of all preset names."""
    return list(TEST_DATA_PRESET_VALUES.keys())


def get_cli_help_text() -> str:
    """
    Get help text for CLI --test-data-count option.
    
    Returns:
        Formatted help string
        
    Example:
        >>> get_cli_help_text()
        'Data volume: micro(100), small(500), ..., or custom number'
    """
    preset_desc = ', '.join(
        f"{name}({preset['count']})"
        for name, preset in TEST_DATA_PRESETS.items()
    )
    return f"Data volume: {preset_desc} or custom number"


# Schema definitions for validation
CLI_OPTION_SCHEMA = {
    'type': 'str',
    'default': str(TEST_DATA_LIMITS['default']),
    'help': get_cli_help_text()
}

WEB_SCHEMA = {
    'type': 'integer',
    'default': TEST_DATA_LIMITS['default'],
    'min': TEST_DATA_LIMITS['min'],
    'max': TEST_DATA_LIMITS['max'],
    'description': 'Number of test conversations to generate'
}

EXECUTOR_SCHEMA = {
    'type': 'int',
    'min': TEST_DATA_LIMITS['min'],
    'max': TEST_DATA_LIMITS['max']
}

