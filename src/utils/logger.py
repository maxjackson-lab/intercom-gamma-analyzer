"""
Logging utility for the Intercom Gamma Analyzer.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from config.settings import settings


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    
    # Determine log level
    log_level = logging.DEBUG if verbose else getattr(logging, settings.log_level)
    
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

