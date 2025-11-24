"""
Shared CLI flag definitions and decorators.

This module centralizes reusable Click option groups and decorators
so CLI commands across the project stay consistent.
"""

import click

from src.config.test_data import PRESET_HELP_TEXT
from src.utils.time_utils import (
    TIME_PERIOD_CHOICES,
    TIME_PERIOD_HELP,
    PERIODS_BACK_HELP,
)


def validate_sample_count(ctx, param, value):
    """Ensure --count stays within the Railway schema bounds."""
    if value is None:
        return None
    if not 10 <= value <= 100:
        raise click.BadParameter("--count must be between 10 and 100 conversations")
    return value


DEFAULT_FLAGS = [
    click.option('--start-date', help='Start date (YYYY-MM-DD)'),
    click.option('--end-date', help='End date (YYYY-MM-DD)'),
    click.option('--time-period',
                 type=click.Choice(TIME_PERIOD_CHOICES),
                 help=TIME_PERIOD_HELP),
    click.option('--periods-back', type=int, default=1,
                 help=PERIODS_BACK_HELP),
]

OUTPUT_FLAGS = [
    click.option('--output-format',
                 type=click.Choice(['markdown', 'json', 'excel', 'gamma']),
                 default='markdown',
                 help='Output format for results'),
    click.option('--gamma-export',
                 type=click.Choice(['pdf', 'pptx']),
                 help='Gamma export format (when output-format=gamma)'),
    click.option('--output-dir', default='outputs',
                 help='Directory for output files'),
]

TEST_FLAGS = [
    click.option('--test-mode', is_flag=True,
                 help='Use mock data instead of API calls'),
    click.option('--test-data-count', type=str, default='100',
                 help=PRESET_HELP_TEXT),
]

DEBUG_FLAGS = [
    click.option('--verbose', is_flag=True,
                 help='Enable DEBUG level logging'),
    click.option('--audit-trail', is_flag=True,
                 help='Enable audit trail narration'),
]

ANALYSIS_FLAGS = [
    click.option('--ai-model',
                 type=click.Choice(['openai', 'claude']),
                 default=None,
                 help='AI model to use for analysis'),
    click.option('--filter-category',
                 help='Filter by taxonomy category (e.g., Billing, Bug, API)'),
]


def apply_flags(flag_list):
    """Decorator to apply a list of click options to a command."""
    def decorator(func):
        for option in reversed(flag_list):
            func = option(func)
        return func
    return decorator


def standard_flags(
    include_time=True,
    include_output=True,
    include_test=True,
    include_debug=True,
    include_analysis=True,
):
    """
    Composite decorator that applies standard flag groups to commands.

    Args:
        include_time: Include time period flags (start-date, end-date, time-period, periods-back)
        include_output: Include output flags (output-format, gamma-export, output-dir)
        include_test: Include test flags (test-mode, test-data-count)
        include_debug: Include debug flags (verbose, audit-trail)
        include_analysis: Include analysis flags (ai-model, filter-category)
    """
    def decorator(func):
        flags_to_apply = []

        if include_analysis:
            flags_to_apply.extend(ANALYSIS_FLAGS)
        if include_debug:
            flags_to_apply.extend(DEBUG_FLAGS)
        if include_test:
            flags_to_apply.extend(TEST_FLAGS)
        if include_output:
            flags_to_apply.extend(OUTPUT_FLAGS)
        if include_time:
            flags_to_apply.extend(DEFAULT_FLAGS)

        for option in reversed(flags_to_apply):
            func = option(func)

        return func

    return decorator


__all__ = [
    'validate_sample_count',
    'DEFAULT_FLAGS',
    'OUTPUT_FLAGS',
    'TEST_FLAGS',
    'DEBUG_FLAGS',
    'ANALYSIS_FLAGS',
    'apply_flags',
    'standard_flags',
]




