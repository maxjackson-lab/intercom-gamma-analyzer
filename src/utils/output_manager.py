"""
Output Manager Utility

Centralized output directory management for web executions.
Handles per-execution directories for organized file storage.
"""

import logging
import os
from pathlib import Path
from typing import Optional, Union


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


def get_output_file_path(
    filename: str,
    base_dir: Optional[Union[str, Path]] = None
) -> Path:
    """
    Get full path for an output file.
    
    Args:
        filename: The output filename (e.g., "sample_mode_20251113_172746.json")
    
    Returns:
        Full path to the output file in the appropriate directory
    """
    if base_dir is not None:
        output_dir = Path(base_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = get_output_directory()
    return output_dir / filename


def save_review_packet(packet_content: str, output_dir: Path, analysis_id: str) -> Optional[Path]:
    """
    Persist review packet markdown alongside other outputs.

    Args:
        packet_content: Markdown content to write
        output_dir: Target directory for outputs
        analysis_id: Identifier to include in filename

    Returns:
        Path to saved file, or None on error.
    """
    logger = logging.getLogger(__name__)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"review_packet_{analysis_id}.md"
        filepath = output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(packet_content)
        logger.info("Review packet saved to %s", filepath)
        return filepath
    except Exception as exc:
        logger.error("Failed to save review packet: %s", exc)
        return None


def get_relative_output_path(file_path: Union[str, Path]) -> str:
    """
    Convert an absolute file path into the relative path expected by /outputs routes.

    Args:
        file_path: Absolute or relative path to an output artifact.

    Returns:
        Relative path string scoped to the outputs root, or just the filename
        when the file sits outside of known roots.
    """
    if not file_path:
        return ""

    path_obj = Path(file_path).resolve()
    candidate_roots = []

    volume_path = os.getenv('RAILWAY_VOLUME_MOUNT_PATH')
    if volume_path:
        candidate_roots.append((Path(volume_path) / "outputs").resolve())

    candidate_roots.append(Path("/app/outputs").resolve())
    candidate_roots.append((Path.cwd() / "outputs").resolve())

    for root in candidate_roots:
        try:
            relative = path_obj.relative_to(root)
            return str(relative)
        except ValueError:
            continue

    return path_obj.name

