"""
Centralized Configuration Module
=================================

This module provides single-source-of-truth configurations for all
enums, limits, and validation schemas used throughout the application.

**Problem Solved:**
Before: Configuration values were duplicated in 15+ files
After: Import from one place, guaranteed consistency

**Modules:**
- test_data_config: Test data limits and presets
- agent_types: Agent and vendor type enums
- analysis_modes: Analysis type options
- time_periods: Time period options
- output_formats: Output format enums

**Usage:**

```python
# Instead of this (old way):
@click.option('--agent', type=click.Choice(['horatio', 'boldr', 'escalated']))

# Do this (new way):
from src.config.agent_types import AGENT_TYPES
@click.option('--agent', type=click.Choice(AGENT_TYPES))
```

**Benefits:**
1. Change config once, applied everywhere
2. No more hunting through files
3. Tests catch mismatches automatically
4. Type hints for validation
"""

# Test data configuration
from .test_data_config import (
    TEST_DATA_LIMITS,
    TEST_DATA_PRESETS,
    TEST_DATA_PRESET_VALUES,
    parse_test_data_count,
    validate_test_data_count,
    get_preset_value,
    get_preset_names,
    get_cli_help_text as get_test_data_help_text
)

# Agent types
from .agent_types import (
    AGENT_TYPES,
    VENDOR_TYPES,
    AGENT_DISPLAY_NAMES,
    AGENT_CLASSIFICATION_TYPES,
    TIER_TYPES,
    TIER_DISPLAY_NAMES,
    get_agent_display_name,
    get_tier_display_name,
    is_valid_agent_type,
    is_valid_vendor_type,
    is_valid_tier
)

# Analysis modes
from .analysis_modes import (
    ANALYSIS_TYPES,
    ANALYSIS_TYPE_DESCRIPTIONS,
    DEFAULT_ANALYSIS_TYPE,
    get_analysis_type_description,
    is_valid_analysis_type
)

# Time periods
from .time_periods import (
    TIME_PERIOD_OPTIONS,
    CLI_TIME_PERIOD_OPTIONS,
    AGENT_PERFORMANCE_PERIODS,
    TIME_PERIOD_DELTAS,
    TIME_PERIOD_DESCRIPTIONS,
    get_timedelta_for_period,
    get_period_description,
    is_valid_period
)

# Output formats
from .output_formats import (
    OUTPUT_FORMATS,
    EXPORT_FORMATS,
    DEFAULT_OUTPUT_FORMAT,
    is_valid_output_format,
    is_valid_export_format
)

__all__ = [
    # Test data
    'TEST_DATA_LIMITS',
    'TEST_DATA_PRESETS',
    'TEST_DATA_PRESET_VALUES',
    'parse_test_data_count',
    'validate_test_data_count',
    'get_preset_value',
    'get_preset_names',
    'get_test_data_help_text',
    
    # Agent types
    'AGENT_TYPES',
    'VENDOR_TYPES',
    'AGENT_DISPLAY_NAMES',
    'AGENT_CLASSIFICATION_TYPES',
    'TIER_TYPES',
    'TIER_DISPLAY_NAMES',
    'get_agent_display_name',
    'get_tier_display_name',
    'is_valid_agent_type',
    'is_valid_vendor_type',
    'is_valid_tier',
    
    # Analysis modes
    'ANALYSIS_TYPES',
    'ANALYSIS_TYPE_DESCRIPTIONS',
    'DEFAULT_ANALYSIS_TYPE',
    'get_analysis_type_description',
    'is_valid_analysis_type',
    
    # Time periods
    'TIME_PERIOD_OPTIONS',
    'CLI_TIME_PERIOD_OPTIONS',
    'AGENT_PERFORMANCE_PERIODS',
    'TIME_PERIOD_DELTAS',
    'TIME_PERIOD_DESCRIPTIONS',
    'get_timedelta_for_period',
    'get_period_description',
    'is_valid_period',
    
    # Output formats
    'OUTPUT_FORMATS',
    'EXPORT_FORMATS',
    'DEFAULT_OUTPUT_FORMAT',
    'is_valid_output_format',
    'is_valid_export_format',
]
