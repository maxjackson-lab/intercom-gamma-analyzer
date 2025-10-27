"""
Centralized Analysis Mode Configuration
========================================

Single source of truth for analysis types and modes.

This eliminates duplication across:
- src/main.py (CLI options)
- deploy/railway_web.py (schemas)
- src/services/web_command_executor.py (validation)

Usage:
    from src.config.analysis_modes import ANALYSIS_TYPES, ANALYSIS_TYPE_DESCRIPTIONS
"""

from typing import Dict, List

# Analysis types
ANALYSIS_TYPES: List[str] = ['standard', 'topic-based', 'synthesis', 'complete']

# Analysis type descriptions
ANALYSIS_TYPE_DESCRIPTIONS: Dict[str, str] = {
    'standard': 'Standard single-pass analysis',
    'topic-based': 'Topic-based analysis (Hilary format with cards)',
    'synthesis': 'Synthesis analysis (cross-topic insights)',
    'complete': 'Complete analysis (all modes combined)'
}

# Default analysis type
DEFAULT_ANALYSIS_TYPE = 'topic-based'


def get_analysis_type_description(analysis_type: str) -> str:
    """
    Get description for analysis type.
    
    Args:
        analysis_type: Analysis type key
        
    Returns:
        Description string
        
    Example:
        >>> get_analysis_type_description('topic-based')
        'Topic-based analysis (Hilary format with cards)'
    """
    return ANALYSIS_TYPE_DESCRIPTIONS.get(
        analysis_type,
        f"Unknown analysis type: {analysis_type}"
    )


def is_valid_analysis_type(analysis_type: str) -> bool:
    """Check if analysis type is valid."""
    return analysis_type in ANALYSIS_TYPES


# Schema definitions
CLI_SCHEMA = {
    'type': 'Choice',
    'choices': ANALYSIS_TYPES,
    'default': DEFAULT_ANALYSIS_TYPE,
    'help': 'Type of analysis to perform'
}

WEB_SCHEMA = {
    'type': 'enum',
    'values': ANALYSIS_TYPES,
    'default': DEFAULT_ANALYSIS_TYPE
}

