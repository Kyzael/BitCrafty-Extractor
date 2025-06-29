"""
Unit tests for ConfigManager validation functionality.

This module tests the configuration validation logic, ensuring proper
error detection for invalid configurations.
"""

import pytest
import yaml
import tempfile
from pathlib import Path
from unittest.mock import Mock

from src.bitcrafty_extractor.config.config_manager import ConfigManager


@pytest.fixture
def mock_logger():
    """Provide a mock logger for testing."""
    return Mock()


@pytest.fixture
def config_file_path():
    """Provide a temporary configuration file path."""
    with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as tmp:
        tmp_path = Path(tmp.name)
    yield tmp_path
    # Cleanup
    if tmp_path.exists():
        tmp_path.unlink()


@pytest.mark.unit
class TestConfigValidation:
    """Test configuration validation scenarios."""
    
    def test_no_enabled_providers_validation(self, mock_logger, config_file_path):
        """Test validation when no AI providers are enabled."""
        config_no_providers = {
            'log_level': 'INFO',
            'auto_save_results': True,
            'results_directory': './exports',
            'hotkeys': {
                'queue_screenshot': 'ctrl+shift+e',
                'analyze_queue': 'ctrl+shift+x',
                'quit_application': 'ctrl+shift+q',
                'enabled': True
            },
            'capture': {
                'format': 'PNG',
                'quality': 95,
                'max_image_size': 1024,
                'auto_detect_game_window': True
            },
            'extraction': {
                'primary_provider': 'openai_gpt4v',
                'fallback_provider': 'anthropic_claude',
                'use_fallback': True,
                'include_examples': True,
                'min_confidence': 0.8,
                'max_retries': 3,
                'rate_limit_delay': 1.0
            },
            'openai': {
                'api_key': '',  # Empty API key - provider disabled
                'model': 'gpt-4o',
                'timeout': 30.0,
                'enabled': False
            },
            'anthropic': {
                'api_key': '',  # Empty API key - provider disabled
                'model': 'claude-3-sonnet',
                'timeout': 30.0,
                'enabled': False
            }
        }
        
        with open(config_file_path, 'w') as f:
            yaml.dump(config_no_providers, f)
        
        config_manager = ConfigManager(config_path=config_file_path, logger=mock_logger)
        validation_errors = config_manager.validate_config()
        
        assert len(validation_errors) > 0
        assert any('provider' in error.lower() for error in validation_errors)
    
    def test_missing_api_keys_validation(self, mock_logger, config_file_path):
        """Test validation when enabled providers have missing API keys."""
        config_missing_keys = {
            'log_level': 'INFO',
            'auto_save_results': True,
            'results_directory': './exports',
            'hotkeys': {
                'queue_screenshot': 'ctrl+shift+e',
                'analyze_queue': 'ctrl+shift+x',
                'quit_application': 'ctrl+shift+q',
                'enabled': True
            },
            'capture': {
                'format': 'PNG',
                'quality': 95,
                'max_image_size': 1024,
                'auto_detect_game_window': True
            },
            'extraction': {
                'primary_provider': 'openai_gpt4v',
                'fallback_provider': 'anthropic_claude',
                'use_fallback': True,
                'include_examples': True,
                'min_confidence': 0.8,
                'max_retries': 3,
                'rate_limit_delay': 1.0
            },
            'openai': {
                'api_key': '',  # Empty API key but enabled
                'model': 'gpt-4o',
                'timeout': 30.0,
                'enabled': True
            }
        }
        
        with open(config_file_path, 'w') as f:
            yaml.dump(config_missing_keys, f)
        
        config_manager = ConfigManager(config_path=config_file_path, logger=mock_logger)
        validation_errors = config_manager.validate_config()
        
        assert len(validation_errors) > 0
        # When API key is empty, provider is effectively disabled, so we get "no providers" error
        assert any('provider' in error.lower() for error in validation_errors)
    
    def test_invalid_hotkey_format_validation(self, mock_logger, config_file_path):
        """Test validation with invalid hotkey formats."""
        config_invalid_hotkeys = {
            'log_level': 'INFO',
            'auto_save_results': True,
            'results_directory': './exports',
            'hotkeys': {
                'queue_screenshot': 'invalid+hotkey+format',  # Invalid format
                'analyze_queue': 'ctrl+shift+x',
                'quit_application': 'ctrl+shift+q',
                'enabled': True
            },
            'capture': {
                'format': 'PNG',
                'quality': 95,
                'max_image_size': 1024,
                'auto_detect_game_window': True
            },
            'extraction': {
                'primary_provider': 'openai_gpt4v',
                'fallback_provider': 'anthropic_claude',
                'use_fallback': True,
                'include_examples': True,
                'min_confidence': 0.8,
                'max_retries': 3,
                'rate_limit_delay': 1.0
            },
            'openai': {
                'api_key': 'test_key',
                'model': 'gpt-4o',
                'timeout': 30.0,
                'enabled': True
            }
        }
        
        with open(config_file_path, 'w') as f:
            yaml.dump(config_invalid_hotkeys, f)
        
        config_manager = ConfigManager(config_path=config_file_path, logger=mock_logger)
        validation_errors = config_manager.validate_config()
        
        assert len(validation_errors) > 0
        assert any('hotkey' in error.lower() for error in validation_errors)
    
    def test_invalid_confidence_range_validation(self, mock_logger, config_file_path):
        """Test validation with invalid confidence values."""
        config_invalid_confidence = {
            'log_level': 'INFO',
            'auto_save_results': True,
            'results_directory': './exports',
            'hotkeys': {
                'queue_screenshot': 'ctrl+shift+e',
                'analyze_queue': 'ctrl+shift+x',
                'quit_application': 'ctrl+shift+q',
                'enabled': True
            },
            'capture': {
                'format': 'PNG',
                'quality': 95,
                'max_image_size': 1024,
                'auto_detect_game_window': True
            },
            'extraction': {
                'primary_provider': 'openai_gpt4v',
                'fallback_provider': 'anthropic_claude',
                'use_fallback': True,
                'include_examples': True,
                'min_confidence': 1.5,  # Invalid confidence > 1.0
                'max_retries': 3,
                'rate_limit_delay': 1.0
            },
            'openai': {
                'api_key': 'test_key',
                'model': 'gpt-4o',
                'timeout': 30.0,
                'enabled': True
            }
        }
        
        with open(config_file_path, 'w') as f:
            yaml.dump(config_invalid_confidence, f)
        
        config_manager = ConfigManager(config_path=config_file_path, logger=mock_logger)
        validation_errors = config_manager.validate_config()
        
        assert len(validation_errors) > 0
        assert any('confidence' in error.lower() for error in validation_errors)
    
    def test_negative_retries_validation(self, mock_logger, config_file_path):
        """Test validation with negative retry values."""
        config_negative_retries = {
            'log_level': 'INFO',
            'auto_save_results': True,
            'results_directory': './exports',
            'hotkeys': {
                'queue_screenshot': 'ctrl+shift+e',
                'analyze_queue': 'ctrl+shift+x',
                'quit_application': 'ctrl+shift+q',
                'enabled': True
            },
            'capture': {
                'format': 'PNG',
                'quality': 95,
                'max_image_size': 1024,
                'auto_detect_game_window': True
            },
            'extraction': {
                'primary_provider': 'openai_gpt4v',
                'fallback_provider': 'anthropic_claude',
                'use_fallback': True,
                'include_examples': True,
                'min_confidence': 0.8,
                'max_retries': -1,  # Invalid negative retries
                'rate_limit_delay': 1.0
            },
            'openai': {
                'api_key': 'test_key',
                'model': 'gpt-4o',
                'timeout': 30.0,
                'enabled': True
            }
        }
        
        with open(config_file_path, 'w') as f:
            yaml.dump(config_negative_retries, f)
        
        config_manager = ConfigManager(config_path=config_file_path, logger=mock_logger)
        validation_errors = config_manager.validate_config()
        
        assert len(validation_errors) > 0
        assert any('retries' in error.lower() for error in validation_errors)
    
    def test_small_image_size_validation(self, mock_logger, config_file_path):
        """Test validation with too small max image size."""
        config_small_image = {
            'log_level': 'INFO',
            'auto_save_results': True,
            'results_directory': './exports',
            'hotkeys': {
                'queue_screenshot': 'ctrl+shift+e',
                'analyze_queue': 'ctrl+shift+x',
                'quit_application': 'ctrl+shift+q',
                'enabled': True
            },
            'capture': {
                'format': 'PNG',
                'quality': 95,
                'max_image_size': 128,  # Too small (< 256)
                'auto_detect_game_window': True
            },
            'extraction': {
                'primary_provider': 'openai_gpt4v',
                'fallback_provider': 'anthropic_claude',
                'use_fallback': True,
                'include_examples': True,
                'min_confidence': 0.8,
                'max_retries': 3,
                'rate_limit_delay': 1.0
            },
            'openai': {
                'api_key': 'test_key',
                'model': 'gpt-4o',
                'timeout': 30.0,
                'enabled': True
            }
        }
        
        with open(config_file_path, 'w') as f:
            yaml.dump(config_small_image, f)
        
        config_manager = ConfigManager(config_path=config_file_path, logger=mock_logger)
        validation_errors = config_manager.validate_config()
        
        assert len(validation_errors) > 0
        assert any('image size' in error.lower() for error in validation_errors)

    def test_valid_configuration_no_errors(self, mock_logger, config_file_path):
        """Test that a valid configuration produces no validation errors."""
        valid_config = {
            'log_level': 'INFO',
            'auto_save_results': True,
            'results_directory': './exports',
            'hotkeys': {
                'queue_screenshot': 'ctrl+shift+e',
                'analyze_queue': 'ctrl+shift+x',
                'quit_application': 'ctrl+shift+q',
                'enabled': True
            },
            'capture': {
                'format': 'PNG',
                'quality': 95,
                'max_image_size': 1024,
                'auto_detect_game_window': True
            },
            'extraction': {
                'primary_provider': 'openai_gpt4v',
                'fallback_provider': 'anthropic_claude',
                'use_fallback': True,
                'include_examples': True,
                'min_confidence': 0.8,
                'max_retries': 3,
                'rate_limit_delay': 1.0
            },
            'openai': {
                'api_key': 'test_key',
                'model': 'gpt-4o',
                'timeout': 30.0,
                'enabled': True
            }
        }
        
        with open(config_file_path, 'w') as f:
            yaml.dump(valid_config, f)
        
        config_manager = ConfigManager(config_path=config_file_path, logger=mock_logger)
        validation_errors = config_manager.validate_config()
        
        assert len(validation_errors) == 0
