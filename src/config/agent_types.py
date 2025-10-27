"""
Centralized Agent & Vendor Type Configuration
==============================================

Single source of truth for all agent and vendor type enums.

This eliminates duplication across:
- src/main.py (CLI options)
- deploy/railway_web.py (schemas)
- src/services/web_command_executor.py (validation)
- src/agents/segmentation_agent.py (detection logic)
- src/services/admin_profile_cache.py (lookups)
- src/services/test_data_generator.py (test data)

Usage:
    from src.config.agent_types import AGENT_TYPES, VENDOR_TYPES, AGENT_DISPLAY_NAMES
"""

from typing import Dict, List

# Agent types (for performance analysis)
AGENT_TYPES: List[str] = ['horatio', 'boldr', 'escalated']

# Vendor types (subset of agents, for coaching reports)
VENDOR_TYPES: List[str] = ['horatio', 'boldr']

# Human-readable display names
AGENT_DISPLAY_NAMES: Dict[str, str] = {
    'horatio': 'Horatio',
    'boldr': 'Boldr',
    'escalated': 'Senior Staff',
    'fin_ai': 'Fin AI',
    'fin_resolved': 'Fin Resolved',
    'unknown': 'Unknown'
}

# Internal agent classification types (used in segmentation)
AGENT_CLASSIFICATION_TYPES: List[str] = [
    'escalated',
    'horatio',
    'boldr',
    'fin_ai',
    'fin_resolved',
    'unknown'
]

# Tier classification
TIER_TYPES: List[str] = ['free', 'pro', 'plus', 'ultra', 'unknown']

TIER_DISPLAY_NAMES: Dict[str, str] = {
    'free': 'Free',
    'pro': 'Pro',
    'plus': 'Plus',
    'ultra': 'Ultra',
    'unknown': 'Unknown'
}


def get_agent_display_name(agent_type: str) -> str:
    """
    Get human-readable display name for agent type.
    
    Args:
        agent_type: Agent type key (e.g., 'horatio', 'boldr')
        
    Returns:
        Display name (e.g., 'Horatio', 'Boldr')
        
    Example:
        >>> get_agent_display_name('horatio')
        'Horatio'
        >>> get_agent_display_name('escalated')
        'Senior Staff'
    """
    return AGENT_DISPLAY_NAMES.get(agent_type, agent_type.title())


def get_tier_display_name(tier: str) -> str:
    """Get human-readable display name for tier."""
    return TIER_DISPLAY_NAMES.get(tier, tier.title())


def is_valid_agent_type(agent_type: str) -> bool:
    """Check if agent type is valid."""
    return agent_type in AGENT_TYPES


def is_valid_vendor_type(vendor_type: str) -> bool:
    """Check if vendor type is valid."""
    return vendor_type in VENDOR_TYPES


def is_valid_tier(tier: str) -> bool:
    """Check if tier is valid."""
    return tier in TIER_TYPES


# Schema definitions for validation
AGENT_CLI_SCHEMA = {
    'type': 'Choice',
    'choices': AGENT_TYPES,
    'help': 'Agent to analyze (horatio, boldr, or escalated to senior staff)'
}

VENDOR_CLI_SCHEMA = {
    'type': 'Choice',
    'choices': VENDOR_TYPES,
    'help': 'Vendor to analyze (horatio or boldr)'
}

AGENT_WEB_SCHEMA = {
    'type': 'enum',
    'values': AGENT_TYPES
}

VENDOR_WEB_SCHEMA = {
    'type': 'enum',
    'values': VENDOR_TYPES
}

