"""
Logging utility for the Intercom Gamma Analyzer.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from src.config.settings import settings


def get_log_level(verbose: bool = False, level_name: Optional[str] = None) -> int:
    """
    Get normalized and validated log level.

    Args:
        verbose: If True, return DEBUG level
        level_name: Optional level name string (e.g., "INFO", "DEBUG")

    Returns:
        logging level integer (e.g., logging.INFO, logging.DEBUG)
    """
    # Priority 1: verbose flag
    if verbose:
        return logging.DEBUG

    # Priority 2: explicit level_name parameter
    if level_name:
        level_upper = level_name.upper()
        valid_levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        if level_upper in valid_levels:
            return valid_levels[level_upper]
        else:
            logging.warning(f"Invalid log level '{level_name}', defaulting to INFO")
            return logging.INFO

    # Priority 3: settings.log_level
    try:
        return getattr(logging, settings.log_level.upper())
    except (AttributeError, ValueError):
        logging.warning(f"Invalid log level in settings: '{settings.log_level}', defaulting to INFO")
        return logging.INFO


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""

    # Determine log level using helper
    log_level = get_log_level(verbose)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # Create file handler
    log_file = Path(settings.output_directory) / settings.log_file
    log_file.parent.mkdir(exist_ok=True)
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Set specific loggers
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)

