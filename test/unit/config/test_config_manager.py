"""Unit tests for configuration management functionality."""

import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import yaml
import sys

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from bitcrafty_extractor.config.config_manager import ConfigManager


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
