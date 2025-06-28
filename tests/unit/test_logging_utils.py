"""Tests for logging utilities."""
import pytest
from pathlib import Path
import tempfile
import structlog

from bitcrafty_extractor.utils.logging_utils import setup_logging


class TestLoggingUtils:
    """Test cases for logging utilities."""
    
    def test_setup_logging_default(self):
        """Test setup logging with default parameters."""
        logger = setup_logging()
        assert logger is not None
        # Check if it's a structlog logger (can be a proxy or bound logger)
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'debug')
        assert hasattr(logger, 'error')
    
    def test_setup_logging_with_level(self):
        """Test setup logging with different levels."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            logger = setup_logging(level=level)
            assert logger is not None
    
    def test_setup_logging_invalid_level(self):
        """Test setup logging with invalid level."""
        with pytest.raises(ValueError, match="Invalid log level"):
            setup_logging(level="INVALID")
    
    def test_setup_logging_with_file(self):
        """Test setup logging with file output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            logger = setup_logging(log_file=log_file)
            assert logger is not None
            # File creation is handled differently, just verify no errors
    
    def test_logging_functionality(self):
        """Test basic logging functionality."""
        logger = setup_logging(level="DEBUG")
        
        # Test that logging methods don't raise errors
        logger.debug("Debug message")
        logger.info("Info message", key="value")
        logger.warning("Warning message")
        logger.error("Error message")
        
        # No assertions here as we're just testing no exceptions are raised
