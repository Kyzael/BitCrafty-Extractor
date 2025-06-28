#!/usr/bin/env python3
"""
Test script to validate logging behavior in ConfigManager and VisionClient.

This script tests:
- Standard Python logging suppression
- structlog behavior with different log levels
- ConfigManager logging behavior
- VisionClient logging behavior
"""

import sys
import logging
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

import structlog

def test_standard_logging():
    """Test standard Python logging suppression."""
    print("="*60)
    print("Testing Standard Python Logging")
    print("="*60)
    
    # Configure standard logging
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    logger = logging.getLogger("test_standard")
    
    print("\n1. Before suppression (should see all levels):")
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    print("\n2. After disabling INFO and below (should only see WARNING+):")
    logging.disable(logging.INFO)
    logger.debug("Debug message (should be suppressed)")
    logger.info("Info message (should be suppressed)")
    logger.warning("Warning message (should appear)")
    logger.error("Error message (should appear)")
    
    print("\n3. Re-enabling logging:")
    logging.disable(logging.NOTSET)
    logger.info("Info message (should appear again)")


def test_structlog_behavior():
    """Test structlog behavior with different configurations."""
    print("\n" + "="*60)
    print("Testing structlog Behavior")
    print("="*60)
    
    # Configure structlog to use standard library
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Create structlog logger
    logger = structlog.get_logger("test_structlog")
    
    print("\n1. structlog with default level:")
    logger.debug("structlog debug message")
    logger.info("structlog info message")
    logger.warning("structlog warning message")
    logger.error("structlog error message")
    
    print("\n2. Setting stdlib logging level to WARNING:")
    logging.getLogger().setLevel(logging.WARNING)
    logger.debug("structlog debug (should be suppressed)")
    logger.info("structlog info (should be suppressed)")
    logger.warning("structlog warning (should appear)")
    logger.error("structlog error (should appear)")


def test_config_manager_logging():
    """Test ConfigManager logging behavior."""
    print("\n" + "="*60)
    print("Testing ConfigManager Logging")
    print("="*60)
    
    # Reset logging
    logging.disable(logging.NOTSET)
    logging.getLogger().setLevel(logging.DEBUG)
    
    print("\n1. Creating ConfigManager with default logger:")
    try:
        from bitcrafty_extractor.config.config_manager import ConfigManager
        config_manager1 = ConfigManager()
        print("ConfigManager created successfully with default logger")
    except Exception as e:
        print(f"Error creating ConfigManager: {e}")
    
    print("\n2. Creating ConfigManager with custom logger (INFO level):")
    try:
        custom_logger = structlog.get_logger("custom_test")
        # Set the underlying stdlib logger to WARNING
        logging.getLogger("custom_test").setLevel(logging.WARNING)
        
        config_manager2 = ConfigManager(logger=custom_logger)
        print("ConfigManager created with custom logger (WARNING level)")
    except Exception as e:
        print(f"Error creating ConfigManager with custom logger: {e}")
    
    print("\n3. Testing logging suppression with ConfigManager:")
    try:
        # Suppress all logging
        logging.disable(logging.ERROR)
        print("Logging disabled (ERROR level) - should suppress info/debug:")
        
        config_manager3 = ConfigManager()
        print("ConfigManager created with suppressed logging")
        
        # Re-enable logging
        logging.disable(logging.NOTSET)
    except Exception as e:
        print(f"Error with suppressed logging: {e}")


def test_vision_client_logging():
    """Test VisionClient logging behavior."""
    print("\n" + "="*60)
    print("Testing VisionClient Logging")
    print("="*60)
    
    try:
        from bitcrafty_extractor.config.config_manager import ConfigManager
        from bitcrafty_extractor.ai_analysis.vision_client import VisionClient
        
        print("\n1. Creating VisionClient with default logging:")
        config_manager = ConfigManager()
        logger = structlog.get_logger("vision_test")
        vision_client = VisionClient(logger, config_manager)
        print("VisionClient created successfully")
        
        print("\n2. Creating VisionClient with suppressed logging:")
        # Suppress logging
        logging.disable(logging.INFO)
        
        logger2 = structlog.get_logger("vision_test_suppressed")
        config_manager2 = ConfigManager(logger=logger2)
        vision_client2 = VisionClient(logger2, config_manager2)
        print("VisionClient created with suppressed logging")
        
        # Re-enable logging
        logging.disable(logging.NOTSET)
        
    except Exception as e:
        print(f"Error testing VisionClient: {e}")


def test_logging_levels():
    """Test different logging level configurations."""
    print("\n" + "="*60)
    print("Testing Logging Level Configurations")
    print("="*60)
    
    # Test different approaches to suppress logging
    approaches = [
        ("logging.disable(logging.INFO)", lambda: logging.disable(logging.INFO)),
        ("logging.disable(logging.WARNING)", lambda: logging.disable(logging.WARNING)),
        ("getLogger().setLevel(WARNING)", lambda: logging.getLogger().setLevel(logging.WARNING)),
        ("getLogger().setLevel(ERROR)", lambda: logging.getLogger().setLevel(logging.ERROR)),
    ]
    
    for name, setup_func in approaches:
        print(f"\n--- Testing: {name} ---")
        
        # Reset logging
        logging.disable(logging.NOTSET)
        logging.getLogger().setLevel(logging.DEBUG)
        
        # Apply suppression
        setup_func()
        
        # Test with structlog
        logger = structlog.get_logger("level_test")
        logger.debug("Debug message")
        logger.info("Info message") 
        logger.warning("Warning message")
        logger.error("Error message")


if __name__ == "__main__":
    print("BitCrafty-Extractor Logging Behavior Test")
    print("="*60)
    
    test_standard_logging()
    test_structlog_behavior()
    test_config_manager_logging()
    test_vision_client_logging()
    test_logging_levels()
    
    print("\n" + "="*60)
    print("Logging behavior test complete!")
    print("="*60)
