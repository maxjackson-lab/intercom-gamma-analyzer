"""
Output Manager Utility

Centralized output directory management for web executions.
Handles per-execution directories for organized file storage.
"""

import os
from pathlib import Path


def get_output_directory() -> Path:
    """
    Get the output directory for the current execution.
    
    Returns:
        Path to use for output files
        
    Behavior:
        - If EXECUTION_OUTPUT_DIR env var is set (web execution):
          Returns that directory (e.g., /app/outputs/executions/sample-mode_Last-Week_Nov-13-5-27pm/)
        - Otherwise (CLI execution):
          Returns default outputs/ directory
    
    Examples:
        # Web execution:
        EXECUTION_OUTPUT_DIR=/app/outputs/executions/sample-mode_Last-Week_Nov-13-5-27pm/
        get_output_directory() -> Path("/app/outputs/executions/sample-mode_Last-Week_Nov-13-5-27pm")
        
        # CLI execution:
        get_output_directory() -> Path("outputs")
    """
    execution_output_dir = os.getenv('EXECUTION_OUTPUT_DIR')
    
    if execution_output_dir:
        # Web execution - use per-execution directory
        output_dir = Path(execution_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    else:
        # CLI execution - use default outputs/ directory
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)
        return output_dir


def get_output_file_path(filename: str) -> Path:
    """
    Get full path for an output file.
    
    Args:
        filename: The output filename (e.g., "sample_mode_20251113_172746.json")
    
    Returns:
        Full path to the output file in the appropriate directory
    """
    output_dir = get_output_directory()
    return output_dir / filename

