"""
Centralized test data configuration and presets.

This module defines the standardized test data presets used across the application
for consistent mock data generation in test mode.
"""

# Test data presets - centralized mapping
TEST_DATA_PRESETS = {
    'tiny': 50,
    'micro': 100,
    'small': 500,
    'medium': 1000,
    'large': 5000,
    'xlarge': 10000,
    'xxlarge': 20000,
    '25k': 25000,
}


def parse_test_data_count(test_data_count: str) -> tuple[int, str | None]:
    """
    Parse test data count from string input.
    
    Args:
        test_data_count: String representing either a preset name or a number
        
    Returns:
        Tuple of (count, preset_name) where preset_name is None if custom number
        
    Raises:
        ValueError: If the input is invalid
        
    Examples:
        >>> parse_test_data_count('micro')
        (100, 'micro')
        >>> parse_test_data_count('500')
        (500, None)
        >>> parse_test_data_count('5000')
        (5000, 'large')  # Matches the 'large' preset
    """
    # Normalize input
    input_str = test_data_count.lower().strip()
    
    # Check if it's a preset name
    if input_str in TEST_DATA_PRESETS:
        return TEST_DATA_PRESETS[input_str], input_str
    
    # Try to parse as integer
    try:
        count = int(test_data_count)
        if count < 1:
            raise ValueError(f"Test data count must be positive, got {count}")
        
        # Check if count matches a preset value
        for preset_name, preset_count in TEST_DATA_PRESETS.items():
            if preset_count == count:
                return count, preset_name
        
        # Custom number
        return count, None
        
    except ValueError as e:
        if "positive" in str(e):
            raise
        raise ValueError(
            f"Invalid test data count '{test_data_count}'. "
            f"Use a preset ({', '.join(TEST_DATA_PRESETS.keys())}) or a positive number."
        ) from e


def get_preset_display_name(count: int, preset_name: str | None) -> str:
    """
    Get display-friendly name for test data count.
    
    Args:
        count: The actual count
        preset_name: The preset name if it matches a preset, None otherwise
        
    Returns:
        Display string like "100 conversations (micro)" or "250 conversations"
    """
    if preset_name:
        return f"{count:,} conversations ({preset_name})"
    return f"{count:,} conversations"


# Export preset names for UI/help text
PRESET_NAMES = list(TEST_DATA_PRESETS.keys())
PRESET_HELP_TEXT = (
    f"Number of test conversations or preset name. "
    f"Presets: {', '.join(f'{name}({count})' for name, count in TEST_DATA_PRESETS.items())}"
)








