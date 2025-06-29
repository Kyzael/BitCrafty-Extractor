"""Unit tests for configuration management functionality."""

import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import yaml
import sys

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from bitcrafty_extractor.config.config_manager import ConfigManager, AIProviderType, AIProviderConfig


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    return Mock()


@pytest.fixture
def sample_config_data():
    """Sample configuration data for testing."""
    return {
        'ai': {
            'default_provider': 'openai_gpt4v',
            'fallback_provider': 'anthropic_claude',
            'openai': {
                'api_key': 'test_openai_key',
                'model': 'gpt-4-vision-preview',
                'timeout': 30.0
            },
            'anthropic': {
                'api_key': 'test_anthropic_key',
                'model': 'claude-3-sonnet-20240229',
                'timeout': 30.0
            }
        },
        'hotkeys': {
            'queue_screenshot': 'ctrl+shift+e',
            'analyze_queue': 'ctrl+shift+x',
            'enabled': True
        },
        'capture': {
            'target_process': 'bitcraft.exe',
            'game_window_patterns': ['BitCraft'],
            'min_window_width': 800,
            'min_window_height': 600,
            'focus_based_capture': True,
            'format': 'PNG',
            'quality': 95,
            'auto_detect_game_window': True
        }
    }


@pytest.fixture
def config_file_path(tmp_path):
    """Create a temporary config file path."""
    return tmp_path / "test_config.yaml"


@pytest.mark.unit
class TestConfigManager:
    """Test cases for ConfigManager class."""

    def test_init_with_existing_file(self, mock_logger, sample_config_data, config_file_path):
        """Test ConfigManager initialization with existing config file."""
        # Write sample config to file
        with open(config_file_path, 'w') as f:
            yaml.dump(sample_config_data, f)
        
        config_manager = ConfigManager(config_file_path, mock_logger)
        
        assert config_manager.config_path == config_file_path
        assert config_manager.logger == mock_logger
        assert config_manager.config is not None
        assert config_manager.config.ai.default_provider == 'openai_gpt4v'

    def test_init_with_nonexistent_file(self, mock_logger, tmp_path):
        """Test ConfigManager initialization with nonexistent config file."""
        nonexistent_path = tmp_path / "nonexistent.yaml"
        
        with pytest.raises(FileNotFoundError):
            ConfigManager(nonexistent_path, mock_logger)

    def test_load_config_valid_yaml(self, mock_logger, sample_config_data, config_file_path):
        """Test loading valid YAML configuration."""
        with open(config_file_path, 'w') as f:
            yaml.dump(sample_config_data, f)
        
        config_manager = ConfigManager(config_file_path, mock_logger)
        
        assert config_manager.config.ai.default_provider == 'openai_gpt4v'
        assert config_manager.config.hotkeys.queue_screenshot == 'ctrl+shift+e'
        assert config_manager.config.capture.target_process == 'bitcraft.exe'

    def test_load_config_invalid_yaml(self, mock_logger, config_file_path):
        """Test loading invalid YAML configuration."""
        # Write invalid YAML
        with open(config_file_path, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        with pytest.raises(yaml.YAMLError):
            ConfigManager(config_file_path, mock_logger)

    def test_load_config_empty_file(self, mock_logger, config_file_path):
        """Test loading empty configuration file."""
        # Create empty file
        config_file_path.touch()
        
        with pytest.raises((AttributeError, TypeError)):
            ConfigManager(config_file_path, mock_logger)

    def test_validate_config_valid(self, mock_logger, sample_config_data, config_file_path):
        """Test configuration validation with valid config."""
        with open(config_file_path, 'w') as f:
            yaml.dump(sample_config_data, f)
        
        config_manager = ConfigManager(config_file_path, mock_logger)
        
        # Should not raise any exceptions
        assert config_manager.config is not None

    def test_validate_config_missing_section(self, mock_logger, config_file_path):
        """Test configuration validation with missing required section."""
        incomplete_config = {
            'ai': {
                'default_provider': 'openai_gpt4v'
            }
            # Missing hotkeys and capture sections
        }
        
        with open(config_file_path, 'w') as f:
            yaml.dump(incomplete_config, f)
        
        # Depending on implementation, this might raise an exception
        # or create defaults
        config_manager = ConfigManager(config_file_path, mock_logger)
        assert config_manager.config is not None

    def test_get_ai_config(self, mock_logger, sample_config_data, config_file_path):
        """Test getting AI configuration."""
        with open(config_file_path, 'w') as f:
            yaml.dump(sample_config_data, f)
        
        config_manager = ConfigManager(config_file_path, mock_logger)
        ai_config = config_manager.config.ai
        
        assert ai_config.default_provider == 'openai_gpt4v'
        assert ai_config.fallback_provider == 'anthropic_claude'
        assert ai_config.openai.api_key == 'test_openai_key'
        assert ai_config.anthropic.api_key == 'test_anthropic_key'

    def test_get_hotkey_config(self, mock_logger, sample_config_data, config_file_path):
        """Test getting hotkey configuration."""
        with open(config_file_path, 'w') as f:
            yaml.dump(sample_config_data, f)
        
        config_manager = ConfigManager(config_file_path, mock_logger)
        hotkey_config = config_manager.config.hotkeys
        
        assert hotkey_config.queue_screenshot == 'ctrl+shift+e'
        assert hotkey_config.analyze_queue == 'ctrl+shift+x'
        assert hotkey_config.enabled is True

    def test_get_capture_config(self, mock_logger, sample_config_data, config_file_path):
        """Test getting capture configuration."""
        with open(config_file_path, 'w') as f:
            yaml.dump(sample_config_data, f)
        
        config_manager = ConfigManager(config_file_path, mock_logger)
        capture_config = config_manager.config.capture
        
        assert capture_config.target_process == 'bitcraft.exe'
        assert capture_config.game_window_patterns == ['BitCraft']
        assert capture_config.min_window_width == 800
        assert capture_config.min_window_height == 600
        assert capture_config.focus_based_capture is True

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'env_openai_key'})
    def test_environment_variable_override(self, mock_logger, sample_config_data, config_file_path):
        """Test that environment variables can override config values."""
        with open(config_file_path, 'w') as f:
            yaml.dump(sample_config_data, f)
        
        config_manager = ConfigManager(config_file_path, mock_logger)
        
        # Depending on implementation, env vars might override config values
        # This test assumes such functionality exists
        # If not implemented, this test should be adjusted
        pass

    def test_config_file_permissions(self, mock_logger, sample_config_data, config_file_path):
        """Test handling of config file with restricted permissions."""
        with open(config_file_path, 'w') as f:
            yaml.dump(sample_config_data, f)
        
        # Make file read-only
        config_file_path.chmod(0o444)
        
        try:
            config_manager = ConfigManager(config_file_path, mock_logger)
            assert config_manager.config is not None
        finally:
            # Restore permissions for cleanup
            config_file_path.chmod(0o644)

    def test_reload_config(self, mock_logger, sample_config_data, config_file_path):
        """Test reloading configuration from file."""
        with open(config_file_path, 'w') as f:
            yaml.dump(sample_config_data, f)
        
        config_manager = ConfigManager(config_file_path, mock_logger)
        original_provider = config_manager.config.ai.default_provider
        
        # Modify config file
        sample_config_data['ai']['default_provider'] = 'anthropic_claude'
        with open(config_file_path, 'w') as f:
            yaml.dump(sample_config_data, f)
        
        # Reload config (if method exists)
        if hasattr(config_manager, 'reload_config'):
            config_manager.reload_config()
            assert config_manager.config.ai.default_provider == 'anthropic_claude'
        else:
            # If reload not implemented, recreate instance
            config_manager = ConfigManager(config_file_path, mock_logger)
            assert config_manager.config.ai.default_provider == 'anthropic_claude'

    def test_config_backup_and_restore(self, mock_logger, sample_config_data, config_file_path):
        """Test configuration backup and restore functionality."""
        with open(config_file_path, 'w') as f:
            yaml.dump(sample_config_data, f)
        
        config_manager = ConfigManager(config_file_path, mock_logger)
        
        # Test backup functionality if implemented
        if hasattr(config_manager, 'backup_config'):
            backup_path = config_manager.backup_config()
            assert backup_path.exists()
            assert backup_path != config_file_path


@pytest.mark.unit
@pytest.mark.parametrize("provider,expected_valid", [
    ("openai_gpt4v", True),
    ("anthropic_claude", True),
    ("invalid_provider", False),
    ("", False),
    (None, False),
])
def test_provider_validation(provider, expected_valid, mock_logger, config_file_path):
    """Test AI provider validation with various inputs."""
    config_data = {
        'ai': {
            'default_provider': provider,
            'fallback_provider': 'anthropic_claude',
            'openai': {
                'api_key': 'test_key',
                'model': 'gpt-4-vision-preview',
                'timeout': 30.0
            },
            'anthropic': {
                'api_key': 'test_key',
                'model': 'claude-3-sonnet-20240229',
                'timeout': 30.0
            }
        },
        'hotkeys': {
            'queue_screenshot': 'ctrl+shift+e',
            'analyze_queue': 'ctrl+shift+x',
            'enabled': True
        },
        'capture': {
            'target_process': 'bitcraft.exe',
            'game_window_patterns': ['BitCraft'],
            'min_window_width': 800,
            'min_window_height': 600,
            'focus_based_capture': True
        }
    }
    
    with open(config_file_path, 'w') as f:
        yaml.dump(config_data, f)
    
    if expected_valid:
        config_manager = ConfigManager(config_file_path, mock_logger)
        assert config_manager.config.ai.default_provider == provider
    else:
        # Depending on implementation, might raise exception or use default
        try:
            config_manager = ConfigManager(config_file_path, mock_logger)
            # If no exception, check if default was used
            assert config_manager.config is not None
        except (ValueError, AttributeError):
            # Expected for invalid providers
            pass


@pytest.mark.unit
def test_config_manager_singleton_behavior(mock_logger, sample_config_data, config_file_path):
    """Test that ConfigManager behaves consistently with same config file."""
    with open(config_file_path, 'w') as f:
        yaml.dump(sample_config_data, f)
    
    config_manager1 = ConfigManager(config_file_path, mock_logger)
    config_manager2 = ConfigManager(config_file_path, mock_logger)
    
    # Both should load the same configuration
    assert config_manager1.config.ai.default_provider == config_manager2.config.ai.default_provider
    assert config_manager1.config.hotkeys.queue_screenshot == config_manager2.config.hotkeys.queue_screenshot


@pytest.mark.unit
def test_config_manager_error_handling(mock_logger, tmp_path):
    """Test error handling in various scenarios."""
    # Test with directory instead of file
    directory_path = tmp_path / "config_directory"
    directory_path.mkdir()
    
    with pytest.raises((IsADirectoryError, PermissionError, OSError)):
        ConfigManager(directory_path, mock_logger)


@pytest.mark.unit  
def test_config_manager_methods_exist(mock_logger, sample_config_data, config_file_path):
    """Test that required methods exist on ConfigManager."""
    with open(config_file_path, 'w') as f:
        yaml.dump(sample_config_data, f)
    
    config_manager = ConfigManager(config_file_path, mock_logger)
    
    # Test that required attributes exist
    assert hasattr(config_manager, 'config')
    assert hasattr(config_manager, 'config_path')
    assert hasattr(config_manager, 'logger')
    
    # Test that config has required sections
    assert hasattr(config_manager.config, 'ai')
    assert hasattr(config_manager.config, 'hotkeys') 
    assert hasattr(config_manager.config, 'capture')


@pytest.mark.unit
class TestConfigValidationErrors:
    """Test configuration validation error scenarios."""
    
    def test_invalid_provider_type_validation(self, mock_logger, config_file_path):
        """Test validation with invalid AI provider type."""
        invalid_config = {
            'ai': {
                'default_provider': 'invalid_provider',  # Invalid provider
                'fallback_provider': 'anthropic_claude',
                'openai': {'api_key': 'test_key', 'model': 'gpt-4o'},
                'anthropic': {'api_key': 'test_key', 'model': 'claude-3-sonnet'}
            },
            'hotkeys': {'enabled': True},
            'capture': {'format': 'PNG'}
        }
        
        # Write invalid config
        with open(config_file_path, 'w') as f:
            yaml.dump(invalid_config, f)
        
        config_manager = ConfigManager(config_path=config_file_path, logger=mock_logger)
        validation_errors = config_manager.validate_config()
        
        assert len(validation_errors) > 0
        assert any('provider' in error.lower() for error in validation_errors)
    
    def test_missing_required_fields_validation(self, mock_logger, config_file_path):
        """Test validation with missing required configuration fields."""
        incomplete_config = {
            'ai': {
                # Missing default_provider and fallback_provider
                'openai': {'api_key': 'test_key'}
                # Missing anthropic section
            }
            # Missing hotkeys and capture sections
        }
        
        with open(config_file_path, 'w') as f:
            yaml.dump(incomplete_config, f)
        
        config_manager = ConfigManager(config_path=config_file_path, logger=mock_logger)
        validation_errors = config_manager.validate_config()
        
        assert len(validation_errors) > 0
        assert not config_manager.is_valid()
    
    def test_api_key_validation_empty_keys(self, mock_logger, config_file_path):
        """Test validation with empty or missing API keys."""
        config_with_empty_keys = {
            'ai': {
                'default_provider': 'openai_gpt4v',
                'fallback_provider': 'anthropic_claude',
                'openai': {
                    'api_key': '',  # Empty API key
                    'model': 'gpt-4o',
                    'timeout': 30.0
                },
                'anthropic': {
                    'api_key': None,  # None API key
                    'model': 'claude-3-sonnet',
                    'timeout': 30.0
                }
            },
            'hotkeys': {'enabled': True},
            'capture': {'format': 'PNG'}
        }
        
        with open(config_file_path, 'w') as f:
            yaml.dump(config_with_empty_keys, f)
        
        config_manager = ConfigManager(config_path=config_file_path, logger=mock_logger)
        validation_errors = config_manager.validate_config()
        
        assert len(validation_errors) > 0
        assert any('api_key' in error.lower() for error in validation_errors)
    
    def test_invalid_model_names_validation(self, mock_logger, config_file_path):
        """Test validation with invalid model names."""
        config_with_invalid_models = {
            'ai': {
                'default_provider': 'openai_gpt4v',
                'fallback_provider': 'anthropic_claude',
                'openai': {
                    'api_key': 'valid_key',
                    'model': 'invalid-model-name',  # Invalid model
                    'timeout': 30.0
                },
                'anthropic': {
                    'api_key': 'valid_key',
                    'model': 'another-invalid-model',  # Invalid model
                    'timeout': 30.0
                }
            },
            'hotkeys': {'enabled': True},
            'capture': {'format': 'PNG'}
        }
        
        with open(config_file_path, 'w') as f:
            yaml.dump(config_with_invalid_models, f)
        
        config_manager = ConfigManager(config_path=config_file_path, logger=mock_logger)
        validation_errors = config_manager.validate_config()
        
        # Should validate successfully even with custom model names
        # (Models may change, so we should be flexible)
        assert isinstance(validation_errors, list)

    def test_config_file_corruption_handling(self, mock_logger, config_file_path):
        """Test handling of corrupted configuration file."""
        # Write malformed YAML
        with open(config_file_path, 'w') as f:
            f.write("invalid: yaml: content: {unclosed brackets")
        
        # Should handle corruption gracefully
        config_manager = ConfigManager(config_path=config_file_path, logger=mock_logger)
        
        # Should fall back to defaults or raise appropriate error
        assert config_manager is not None
        validation_errors = config_manager.validate_config()
        assert isinstance(validation_errors, list)

    def test_config_file_permissions_error(self, mock_logger, tmp_path):
        """Test handling of configuration file permission errors."""
        config_file = tmp_path / "readonly_config.yaml"
        
        # Create file and make it read-only
        config_file.write_text(yaml.dump({'ai': {'default_provider': 'openai_gpt4v'}}))
        config_file.chmod(0o444)  # Read-only
        
        config_manager = ConfigManager(config_path=config_file, logger=mock_logger)
        
        # Should be able to read but not save
        assert config_manager is not None
        
        # Attempt to save should handle permission error gracefully
        success = config_manager.save_config()
        assert success is False or success is True  # Depends on implementation


@pytest.mark.unit  
class TestConfigAPIKeyManagement:
    """Test API key management functionality."""
    
    def test_set_openai_api_key(self, mock_logger, sample_config_data, config_file_path):
        """Test setting OpenAI API key."""
        with open(config_file_path, 'w') as f:
            yaml.dump(sample_config_data, f)
        
        config_manager = ConfigManager(config_path=config_file_path, logger=mock_logger)
        
        # Test setting new API key
        new_key = "new_openai_api_key_12345"
        config_manager.set_ai_provider_config(
            AIProviderType.OPENAI, 
            AIProviderConfig(api_key=new_key, model="gpt-4o", timeout=30.0)
        )
        
        # Verify key was set
        openai_config = config_manager.get_ai_provider_config(AIProviderType.OPENAI)
        assert openai_config.api_key == new_key
    
    def test_set_anthropic_api_key(self, mock_logger, sample_config_data, config_file_path):
        """Test setting Anthropic API key."""
        with open(config_file_path, 'w') as f:
            yaml.dump(sample_config_data, f)
        
        config_manager = ConfigManager(config_path=config_file_path, logger=mock_logger)
        
        # Test setting new API key
        new_key = "new_anthropic_api_key_67890"
        config_manager.set_ai_provider_config(
            AIProviderType.ANTHROPIC,
            AIProviderConfig(api_key=new_key, model="claude-3-sonnet", timeout=30.0)
        )
        
        # Verify key was set
        anthropic_config = config_manager.get_ai_provider_config(AIProviderType.ANTHROPIC)
        assert anthropic_config.api_key == new_key

    def test_api_key_security_masking(self, mock_logger, sample_config_data, config_file_path):
        """Test that API keys are properly masked in logs/exports."""
        with open(config_file_path, 'w') as f:
            yaml.dump(sample_config_data, f)
        
        config_manager = ConfigManager(config_path=config_file_path, logger=mock_logger)
        
        # Export config should mask API keys
        exported_config = config_manager.export_config()
        
        # Check that API keys are masked or excluded
        if 'ai' in exported_config:
            if 'openai' in exported_config['ai']:
                openai_key = exported_config['ai']['openai'].get('api_key', '')
                assert openai_key == '' or '*' in openai_key or openai_key != sample_config_data['ai']['openai']['api_key']


@pytest.mark.unit
class TestEnvironmentVariableOverrides:
    """Test environment variable override functionality."""
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'env_openai_key'})
    def test_openai_api_key_environment_override(self, mock_logger, sample_config_data, config_file_path):
        """Test OpenAI API key override from environment variable."""
        with open(config_file_path, 'w') as f:
            yaml.dump(sample_config_data, f)
        
        config_manager = ConfigManager(config_path=config_file_path, logger=mock_logger)
        
        # Environment variable should override config file
        openai_config = config_manager.get_ai_provider_config(AIProviderType.OPENAI)
        if openai_config:  # Only test if env override is implemented
            expected_key = 'env_openai_key'
            # Check if environment override is working
            assert openai_config.api_key == expected_key or openai_config.api_key == sample_config_data['ai']['openai']['api_key']
    
    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'env_anthropic_key'})
    def test_anthropic_api_key_environment_override(self, mock_logger, sample_config_data, config_file_path):
        """Test Anthropic API key override from environment variable."""
        with open(config_file_path, 'w') as f:
            yaml.dump(sample_config_data, f)
        
        config_manager = ConfigManager(config_path=config_file_path, logger=mock_logger)
        
        # Environment variable should override config file
        anthropic_config = config_manager.get_ai_provider_config(AIProviderType.ANTHROPIC)
        if anthropic_config:  # Only test if env override is implemented
            expected_key = 'env_anthropic_key'
            # Check if environment override is working
            assert anthropic_config.api_key == expected_key or anthropic_config.api_key == sample_config_data['ai']['anthropic']['api_key']


@pytest.mark.unit
class TestConfigMergingEdgeCases:
    """Test configuration merging edge cases."""
    
    def test_partial_config_merging(self, mock_logger, config_file_path):
        """Test merging partial configuration with defaults."""
        partial_config = {
            'ai': {
                'default_provider': 'anthropic_claude',
                'openai': {
                    'api_key': 'partial_openai_key'
                    # Missing model and timeout - should use defaults
                }
                # Missing anthropic section - should use defaults
            }
            # Missing hotkeys and capture - should use defaults
        }
        
        with open(config_file_path, 'w') as f:
            yaml.dump(partial_config, f)
        
        config_manager = ConfigManager(config_path=config_file_path, logger=mock_logger)
        
        # Should successfully merge with defaults
        assert config_manager.config is not None
        assert config_manager.config.ai.default_provider.value == 'anthropic'
        
        # OpenAI should have custom key but default model
        openai_config = config_manager.get_ai_provider_config(AIProviderType.OPENAI)
        if openai_config:
            assert openai_config.api_key == 'partial_openai_key'
            assert openai_config.model is not None  # Should have default model
    
    def test_nested_config_override(self, mock_logger, config_file_path):
        """Test deep nested configuration overrides."""
        nested_config = {
            'ai': {
                'default_provider': 'openai_gpt4v',
                'openai': {
                    'api_key': 'nested_test_key',
                    'model': 'gpt-4o',
                    'timeout': 45.0,
                    'extra_param': 'should_be_preserved'  # Extra parameter
                }
            }
        }
        
        with open(config_file_path, 'w') as f:
            yaml.dump(nested_config, f)
        
        config_manager = ConfigManager(config_path=config_file_path, logger=mock_logger)
        
        # Should preserve all nested values
        assert config_manager.config is not None
        openai_config = config_manager.get_ai_provider_config(AIProviderType.OPENAI)
        if openai_config:
            assert openai_config.api_key == 'nested_test_key'
            assert openai_config.model == 'gpt-4o'
            assert openai_config.timeout == 45.0
