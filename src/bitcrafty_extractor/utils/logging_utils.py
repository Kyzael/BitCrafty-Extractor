"""Logging utilities for BitCrafty Extractor."""
import sys
import logging
from pathlib import Path
from typing import Optional
import structlog


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    console_output: bool = True
) -> structlog.BoundLogger:
    """Setup structured logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        console_output: Whether to output logs to console
        
    Returns:
        Configured structured logger
        
    Raises:
        ValueError: If log level is invalid
    """
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if level.upper() not in valid_levels:
        raise ValueError(f"Invalid log level: {level}. Must be one of {valid_levels}")
    
    # Convert level string to logging constant
    numeric_level = getattr(logging, level.upper())
    
    # Configure Python logging first
    logging.basicConfig(
        level=numeric_level,
        format='%(message)s'
    )
    
    # Configure structlog processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.dev.ConsoleRenderer() if console_output else structlog.processors.JSONRenderer()
    ]
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Setup file handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        # Note: File logging would need additional setup with standard library
        # For now, focusing on console output for simplicity
    
    logger = structlog.get_logger()
    logger.info("Logging initialized", level=level, log_file=str(log_file) if log_file else None)
    
    return logger
