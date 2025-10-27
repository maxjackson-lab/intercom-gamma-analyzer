"""
Centralized Output Format Configuration
========================================

Single source of truth for output format options.

This eliminates duplication across:
- src/main.py (CLI options)
- src/services/web_command_executor.py (validation)

Usage:
    from src.config.output_formats import OUTPUT_FORMATS, EXPORT_FORMATS
"""

from typing import List

# Standard output formats (for analysis results)
OUTPUT_FORMATS: List[str] = ['gamma', 'markdown', 'json', 'excel']

# Export formats (for data exports)
EXPORT_FORMATS: List[str] = ['json', 'csv', 'markdown', 'excel']

# Default format
DEFAULT_OUTPUT_FORMAT = 'markdown'


def is_valid_output_format(format_type: str) -> bool:
    """Check if output format is valid."""
    return format_type in OUTPUT_FORMATS


def is_valid_export_format(format_type: str) -> bool:
    """Check if export format is valid."""
    return format_type in EXPORT_FORMATS


# Schema definitions
OUTPUT_CLI_SCHEMA = {
    'type': 'Choice',
    'choices': OUTPUT_FORMATS,
    'default': DEFAULT_OUTPUT_FORMAT,
    'help': 'Output format for results'
}

EXPORT_CLI_SCHEMA = {
    'type': 'Choice',
    'choices': EXPORT_FORMATS,
    'default': 'csv',
    'help': 'Export format for data'
}

OUTPUT_WEB_SCHEMA = {
    'type': 'enum',
    'values': OUTPUT_FORMATS,
    'default': DEFAULT_OUTPUT_FORMAT
}

EXPORT_WEB_SCHEMA = {
    'type': 'enum',
    'values': EXPORT_FORMATS
}

