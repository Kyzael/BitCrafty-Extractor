"""Tests for configuration manager."""
import pytest
import tempfile
from pathlib import Path
import yaml
import os

from bitcrafty_extractor.core.config_manager import ConfigManager, AppConfig, WindowConfig, OCRConfig
from bitcrafty_extractor import ConfigurationError


class TestConfigManager:
    """Test cases for ConfigManager."""
    
    def test_default_config_creation(self):
        """Test creation with default configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "nonexistent.yaml"
            manager = ConfigManager(config_path)
            
            assert manager.config.name == "BitCrafty Extractor"
            assert manager.config.version == "1.0.0"
            assert manager.config.debug is False
            assert manager.config.window.target_name == "Bitcraft"
            assert manager.config.window.capture_interval_ms == 500
    
    def test_config_loading_from_file(self):
        """Test loading configuration from YAML file."""
        config_data = {
            "app": {
                "name": "Test Extractor",
                "version": "2.0.0",
                "debug": True
            },
            "window": {
                "target_name": "TestGame",
                "capture_interval_ms": 1000
            },
            "ocr": {
                "confidence_threshold": 0.9
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)
        
        try:
            manager = ConfigManager(config_path)
            config = manager.config
            
            assert config.name == "Test Extractor"
            assert config.version == "2.0.0"
            assert config.debug is True
            assert config.window.target_name == "TestGame"
            assert config.window.capture_interval_ms == 1000
            assert config.ocr.confidence_threshold == 0.9
        finally:
            os.unlink(config_path)
    
    def test_environment_variable_overrides(self):
        """Test environment variable overrides."""
        # Set environment variables
        os.environ["BITCRAFT_WINDOW_NAME"] = "EnvTestGame"
        os.environ["BITCRAFT_CAPTURE_INTERVAL"] = "2000"
        os.environ["BITCRAFT_OCR_CONFIDENCE"] = "0.95"
        os.environ["BITCRAFT_DEBUG"] = "true"
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                config_path = Path(temp_dir) / "nonexistent.yaml"
                manager = ConfigManager(config_path)
                config = manager.config
                
                assert config.window.target_name == "EnvTestGame"
                assert config.window.capture_interval_ms == 2000
                assert config.ocr.confidence_threshold == 0.95
                assert config.debug is True
        finally:
            # Clean up environment variables
            for var in ["BITCRAFT_WINDOW_NAME", "BITCRAFT_CAPTURE_INTERVAL", 
                       "BITCRAFT_OCR_CONFIDENCE", "BITCRAFT_DEBUG"]:
                os.environ.pop(var, None)
    
    def test_invalid_capture_interval_validation(self):
        """Test validation of invalid capture intervals."""
        config_data = {
            "window": {
                "capture_interval_ms": 50  # Too low
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)
        
        try:
            with pytest.raises(ConfigurationError, match="capture_interval_ms must be at least 100ms"):
                ConfigManager(config_path)
        finally:
            os.unlink(config_path)
    
    def test_invalid_confidence_threshold_validation(self):
        """Test validation of invalid confidence threshold."""
        config_data = {
            "ocr": {
                "confidence_threshold": 1.5  # Too high
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)
        
        try:
            with pytest.raises(ConfigurationError, match="OCR confidence_threshold must be between 0.0 and 1.0"):
                ConfigManager(config_path)
        finally:
            os.unlink(config_path)
