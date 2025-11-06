"""
Standard audit trail helper for consistent audit trail initialization and management.

This module provides a standardized approach to initializing and managing audit trails
across all commands, ensuring consistent artifact generation and logging.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from src.services.audit_trail import AuditTrail

logger = logging.getLogger(__name__)


def initialize_audit_trail(
    command_name: str,
    enabled: bool = False,
    output_dir: str = "outputs",
    additional_context: Optional[Dict[str, Any]] = None
) -> Optional[AuditTrail]:
    """
    Initialize audit trail if enabled.
    
    Args:
        command_name: Name of the command being run (e.g., 'voice-of-customer')
        enabled: Whether audit trail is enabled
        output_dir: Output directory for audit trail artifacts
        additional_context: Additional context to include in audit trail
        
    Returns:
        AuditTrail instance if enabled, None otherwise
        
    Example:
        >>> audit = initialize_audit_trail('voice-of-customer', enabled=True)
        >>> if audit:
        ...     audit.log_step('Data extraction', 'Fetching conversations from Intercom')
        ...     save_audit_artifacts(audit, 'voice_of_customer_20250105')
    """
    if not enabled:
        return None
    
    try:
        # Create audit trail instance
        audit = AuditTrail(
            command=command_name,
            context=additional_context or {}
        )
        
        # Log initialization
        audit.log_step(
            'Initialization',
            f'Audit trail enabled for {command_name}'
        )
        
        logger.info(f"Audit trail initialized for {command_name}")
        return audit
        
    except Exception as e:
        logger.error(f"Failed to initialize audit trail: {e}")
        return None


def save_audit_artifacts(
    audit: AuditTrail,
    analysis_name: str,
    output_dir: str = "outputs"
) -> Dict[str, Path]:
    """
    Save audit trail artifacts to disk.
    
    Args:
        audit: AuditTrail instance
        analysis_name: Base name for output files (e.g., 'voice_of_customer_20250105')
        output_dir: Output directory for artifacts
        
    Returns:
        Dictionary mapping artifact types to file paths
        
    Example:
        >>> artifacts = save_audit_artifacts(audit, 'voice_of_customer_20250105')
        >>> print(f"Markdown: {artifacts['markdown']}")
        >>> print(f"JSON: {artifacts['json']}")
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_name = f"{analysis_name}_audit_{timestamp}"
    
    artifacts = {}
    
    try:
        # Save markdown audit trail
        markdown_path = output_path / f"{base_name}.md"
        audit.save_markdown(str(markdown_path))
        artifacts['markdown'] = markdown_path
        logger.info(f"Saved audit trail markdown: {markdown_path}")
        
        # Save JSON audit trail
        json_path = output_path / f"{base_name}.json"
        audit.save_json(str(json_path))
        artifacts['json'] = json_path
        logger.info(f"Saved audit trail JSON: {json_path}")
        
        return artifacts
        
    except Exception as e:
        logger.error(f"Failed to save audit trail artifacts: {e}")
        return artifacts


def log_command_start(
    audit: Optional[AuditTrail],
    command_name: str,
    parameters: Dict[str, Any]
):
    """
    Log command start with parameters.
    
    Args:
        audit: AuditTrail instance (may be None if disabled)
        command_name: Command name
        parameters: Command parameters
    """
    if not audit:
        return
    
    param_summary = "\n".join(
        f"  - {key}: {value}"
        for key, value in parameters.items()
        if value is not None
    )
    
    audit.log_step(
        'Command Execution',
        f'Starting {command_name}\n\nParameters:\n{param_summary}'
    )


def log_data_extraction(
    audit: Optional[AuditTrail],
    source: str,
    count: int,
    date_range: str
):
    """
    Log data extraction step.
    
    Args:
        audit: AuditTrail instance (may be None if disabled)
        source: Data source (e.g., 'Intercom API', 'Mock Data')
        count: Number of items extracted
        date_range: Date range string
    """
    if not audit:
        return
    
    audit.log_step(
        'Data Extraction',
        f'Extracted {count:,} items from {source}\n'
        f'Date range: {date_range}'
    )


def log_analysis_step(
    audit: Optional[AuditTrail],
    step_name: str,
    details: str,
    metrics: Optional[Dict[str, Any]] = None
):
    """
    Log an analysis step with optional metrics.
    
    Args:
        audit: AuditTrail instance (may be None if disabled)
        step_name: Name of the analysis step
        details: Detailed description
        metrics: Optional metrics dictionary
    """
    if not audit:
        return
    
    message = details
    if metrics:
        metrics_summary = "\n\nMetrics:\n" + "\n".join(
            f"  - {key}: {value}"
            for key, value in metrics.items()
        )
        message += metrics_summary
    
    audit.log_step(step_name, message)


def log_output_generation(
    audit: Optional[AuditTrail],
    output_format: str,
    file_paths: Dict[str, Path]
):
    """
    Log output file generation.
    
    Args:
        audit: AuditTrail instance (may be None if disabled)
        output_format: Output format (e.g., 'markdown', 'json', 'gamma')
        file_paths: Dictionary mapping output types to file paths
    """
    if not audit:
        return
    
    files_summary = "\n".join(
        f"  - {output_type}: {path}"
        for output_type, path in file_paths.items()
    )
    
    audit.log_step(
        'Output Generation',
        f'Generated {output_format} outputs:\n\n{files_summary}'
    )


def finalize_audit_trail(
    audit: Optional[AuditTrail],
    success: bool,
    error_message: Optional[str] = None
) -> None:
    """
    Finalize audit trail with completion status.
    
    Args:
        audit: AuditTrail instance (may be None if disabled)
        success: Whether the command completed successfully
        error_message: Error message if failed
    """
    if not audit:
        return
    
    if success:
        audit.log_step(
            'Completion',
            'Analysis completed successfully'
        )
    else:
        error_detail = f'\n\nError: {error_message}' if error_message else ''
        audit.log_step(
            'Completion',
            f'Analysis failed{error_detail}'
        )





