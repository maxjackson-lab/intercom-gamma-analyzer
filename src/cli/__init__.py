"""
CLI Module - Command Line Interface for Intercom Analysis Tool

This module provides the command-line interface for the Intercom analysis tool,
including all analysis commands, data export functionality, and interactive features.
"""

from .commands import (
    voice_analysis,
    trend_analysis,
    custom_analysis,
    data_export,
    technical_analysis,
    agent_performance,
    comprehensive_analysis,
    voice_of_customer,
    canny_analysis
)

from .runners import (
    run_voice_analysis,
    run_trend_analysis,
    run_custom_analysis,
    run_data_export,
    run_technical_analysis_v2,
    run_agent_performance_analysis,
    run_comprehensive_analysis,
    run_canny_analysis,
    run_voc_analysis
)

from .utils import (
    display_results,
    save_outputs,
    generate_gamma_presentation,
    parse_date_range,
    validate_inputs
)

__all__ = [
    # Commands
    'voice_analysis',
    'trend_analysis', 
    'custom_analysis',
    'data_export',
    'technical_analysis',
    'agent_performance',
    'comprehensive_analysis',
    'voice_of_customer',
    'canny_analysis',
    
    # Runners
    'run_voice_analysis',
    'run_trend_analysis',
    'run_custom_analysis',
    'run_data_export',
    'run_technical_analysis_v2',
    'run_agent_performance_analysis',
    'run_comprehensive_analysis',
    'run_canny_analysis',
    'run_voc_analysis',
    
    # Utils
    'display_results',
    'save_outputs',
    'generate_gamma_presentation',
    'parse_date_range',
    'validate_inputs'
]