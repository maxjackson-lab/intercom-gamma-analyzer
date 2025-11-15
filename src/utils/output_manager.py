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
        - If RAILWAY_VOLUME_MOUNT_PATH is set (Railway persistent storage):
          Uses volume path (survives redeploys!)
        - If EXECUTION_OUTPUT_DIR env var is set (web execution):
          Returns that directory
        - Otherwise (CLI execution):
          Returns default outputs/ directory
    
    Examples:
        # Railway with persistent volume:
        RAILWAY_VOLUME_MOUNT_PATH=/mnt/persistent
        get_output_directory() -> Path("/mnt/persistent/outputs/executions/...")
        
        # Web execution (ephemeral):
        EXECUTION_OUTPUT_DIR=/app/outputs/executions/sample-mode_Last-Week_Nov-13-5-27pm/
        get_output_directory() -> Path("/app/outputs/executions/sample-mode_Last-Week_Nov-13-5-27pm")
        
        # CLI execution:
        get_output_directory() -> Path("outputs")
    """
    # Priority 1: Railway persistent volume (if available)
    volume_path = os.getenv('RAILWAY_VOLUME_MOUNT_PATH')
    if volume_path:
        # Use volume for persistent storage
        base_dir = Path(volume_path) / "outputs"
        
        # Check if we have an execution-specific directory
        execution_output_dir = os.getenv('EXECUTION_OUTPUT_DIR')
        if execution_output_dir:
            # Extract just the directory name (not full path)
            dir_name = Path(execution_output_dir).name
            output_dir = base_dir / "executions" / dir_name
        else:
            output_dir = base_dir
        
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    
    # Priority 2: Web execution (ephemeral)
    execution_output_dir = os.getenv('EXECUTION_OUTPUT_DIR')
    if execution_output_dir:
        output_dir = Path(execution_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    
    # Priority 3: CLI execution (default)
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

