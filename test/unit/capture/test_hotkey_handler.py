"""Unit tests for hotkey handler functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import threading
import time

from src.bitcrafty_extractor.capture.hotkey_handler import HotkeyHandler, HotkeyConfig, HOTKEY_AVAILABLE


@pytest.fixture
def mock_logger():
    """Provide a mock logger for testing."""
    return Mock()


@pytest.mark.unit
class TestHotkeyHandler:
    """Test cases for HotkeyHandler class."""

    @patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True)
    def test_init_success(self, mock_logger):
        """Test HotkeyHandler initialization when available."""
        handler = HotkeyHandler(mock_logger)
        assert handler.logger == mock_logger
        assert handler.hotkeys == {}
        assert handler.listener is None
        assert handler.is_monitoring is False
        assert handler.debounce_delay == 0.5
        assert handler.last_trigger_time == {}

    @patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', False)
    def test_init_unavailable(self, mock_logger):
        """Test HotkeyHandler initialization when unavailable."""
        with pytest.raises(RuntimeError, match="Hotkey system not available"):
            HotkeyHandler(mock_logger)

    @patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True)
    def test_convert_to_pynput_format_basic(self, mock_logger):
        """Test hotkey format conversion."""
        handler = HotkeyHandler(mock_logger)
        
        # Test basic combinations
        assert handler._convert_to_pynput_format("ctrl+shift+e") == "<ctrl>+<shift>+e"
        assert handler._convert_to_pynput_format("ctrl+c") == "<ctrl>+c"
        assert handler._convert_to_pynput_format("alt+tab") == "<alt>+<tab>"
        assert handler._convert_to_pynput_format("ctrl+shift+x") == "<ctrl>+<shift>+x"

    @patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True)
    def test_convert_to_pynput_format_variations(self, mock_logger):
        """Test hotkey format conversion with variations."""
        handler = HotkeyHandler(mock_logger)
        
        # Test key variations
        assert handler._convert_to_pynput_format("control+c") == "<ctrl>+c"
        assert handler._convert_to_pynput_format("win+r") == "<cmd>+r"
        assert handler._convert_to_pynput_format("super+l") == "<cmd>+l"
        assert handler._convert_to_pynput_format("return") == "<enter>"
        assert handler._convert_to_pynput_format("escape") == "<esc>"

    @patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True)
    def test_register_callback_success(self, mock_logger):
        """Test successful callback registration."""
        handler = HotkeyHandler(mock_logger)
        callback = Mock()
        callback.__name__ = "test_callback"  # Mock objects need explicit __name__
        
        handler.register_callback("ctrl+shift+e", callback, "Test callback")
        
        pynput_hotkey = "<ctrl>+<shift>+e"
        assert pynput_hotkey in handler.hotkeys
        config = handler.hotkeys[pynput_hotkey]
        assert config.callback == callback
        assert config.description == "Test callback"
        assert config.enabled is True

    @patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True)
    def test_register_callback_default_description(self, mock_logger):
        """Test callback registration with default description."""
        handler = HotkeyHandler(mock_logger)
        callback = Mock()
        callback.__name__ = "test_callback"
        
        handler.register_callback("ctrl+shift+e", callback)
        
        pynput_hotkey = "<ctrl>+<shift>+e"
        config = handler.hotkeys[pynput_hotkey]
        assert config.description == "Hotkey: ctrl+shift+e"

    @patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True)
    def test_unregister_callback_success(self, mock_logger):
        """Test successful callback unregistration."""
        handler = HotkeyHandler(mock_logger)
        callback = Mock()
        callback.__name__ = "test_callback"
        
        handler.register_callback("ctrl+shift+e", callback, "Test")
        handler.unregister_callback("ctrl+shift+e")
        
        pynput_hotkey = "<ctrl>+<shift>+e"
        assert pynput_hotkey not in handler.hotkeys
        assert pynput_hotkey not in handler.last_trigger_time

    @patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True)
    def test_enable_disable_hotkey(self, mock_logger):
        """Test enabling and disabling hotkeys."""
        handler = HotkeyHandler(mock_logger)
        callback = Mock()
        callback.__name__ = "test_callback"
        
        handler.register_callback("ctrl+shift+e", callback, "Test")
        pynput_hotkey = "<ctrl>+<shift>+e"
        
        # Test disable
        handler.disable_hotkey("ctrl+shift+e")
        assert handler.hotkeys[pynput_hotkey].enabled is False
        
        # Test enable
        handler.enable_hotkey("ctrl+shift+e")
        assert handler.hotkeys[pynput_hotkey].enabled is True

    @patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True)
    def test_get_hotkey_info(self, mock_logger):
        """Test getting hotkey information."""
        handler = HotkeyHandler(mock_logger)
        callback = Mock()
        callback.__name__ = "test_callback"
        
        handler.register_callback("ctrl+shift+e", callback, "Test callback")
        
        info = handler.get_hotkey_info()
        
        pynput_hotkey = "<ctrl>+<shift>+e"
        assert isinstance(info, dict)
        assert pynput_hotkey in info
        assert info[pynput_hotkey]["description"] == "Test callback"
        assert info[pynput_hotkey]["enabled"] is True
        assert info[pynput_hotkey]["callback_name"] == "test_callback"

    @patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True)
    def test_get_status(self, mock_logger):
        """Test getting handler status."""
        handler = HotkeyHandler(mock_logger)
        callback = Mock()
        callback.__name__ = "test_callback"
        
        handler.register_callback("ctrl+shift+e", callback, "Test")
        
        status = handler.get_status()
        
        assert isinstance(status, dict)
        assert "is_monitoring" in status
        assert "total_hotkeys" in status
        assert "enabled_hotkeys" in status
        assert "debounce_delay" in status
        assert "available" in status
        assert status["total_hotkeys"] == 1
        assert status["enabled_hotkeys"] == 1
        assert status["debounce_delay"] == 0.5
        assert status["available"] is True

    @patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True)
    def test_is_running(self, mock_logger):
        """Test is_running method."""
        handler = HotkeyHandler(mock_logger)
        
        # Initially not running
        assert handler.is_running() is False
        
        # Set to monitoring but no listener
        handler.is_monitoring = True
        assert handler.is_running() is False
        
        # Set listener
        handler.listener = Mock()
        assert handler.is_running() is True

    @patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True)
    @patch('src.bitcrafty_extractor.capture.hotkey_handler.keyboard.GlobalHotKeys')
    def test_start_monitoring_success(self, mock_global_hotkeys, mock_logger):
        """Test successful monitoring start."""
        handler = HotkeyHandler(mock_logger)
        callback = Mock()
        callback.__name__ = "test_callback"
        
        # Mock the GlobalHotKeys listener
        mock_listener = Mock()
        mock_global_hotkeys.return_value = mock_listener
        
        handler.register_callback("ctrl+shift+e", callback, "Test")
        handler.start_monitoring()
        
        assert handler.is_monitoring is True
        assert handler.listener == mock_listener
        mock_listener.start.assert_called_once()

    @patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True)
    def test_start_monitoring_already_running(self, mock_logger):
        """Test starting monitoring when already running."""
        handler = HotkeyHandler(mock_logger)
        handler.is_monitoring = True
        
        handler.start_monitoring()
        
        # Should log warning and return early
        mock_logger.warning.assert_called_with("Hotkey monitoring already active")

    @patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True)
    def test_start_monitoring_no_hotkeys(self, mock_logger):
        """Test starting monitoring with no hotkeys."""
        handler = HotkeyHandler(mock_logger)
        
        handler.start_monitoring()
        
        # Should log warning and return early
        mock_logger.warning.assert_called_with("No hotkeys registered")

    @patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True)
    def test_stop_monitoring_success(self, mock_logger):
        """Test successful monitoring stop."""
        handler = HotkeyHandler(mock_logger)
        
        # Setup monitoring state
        mock_listener = Mock()
        handler.listener = mock_listener
        handler.is_monitoring = True
        
        handler.stop_monitoring()
        
        assert handler.is_monitoring is False
        assert handler.listener is None
        mock_listener.stop.assert_called_once()

    @patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True)
    def test_stop_monitoring_not_running(self, mock_logger):
        """Test stopping monitoring when not running."""
        handler = HotkeyHandler(mock_logger)
        
        # Should return early without error
        handler.stop_monitoring()
        
        assert handler.is_monitoring is False

    @patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True)
    def test_create_hotkey_callback_execution(self, mock_logger):
        """Test hotkey callback creation and execution."""
        handler = HotkeyHandler(mock_logger)
        callback = Mock()
        callback.__name__ = "test_callback"
        
        handler.register_callback("ctrl+shift+e", callback, "Test")
        pynput_hotkey = "<ctrl>+<shift>+e"
        
        # Create callback function
        hotkey_callback = handler._create_hotkey_callback(pynput_hotkey)
        
        # Execute it
        hotkey_callback()
        
        # Verify original callback was called
        callback.assert_called_once()

    @patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True)
    def test_create_hotkey_callback_disabled(self, mock_logger):
        """Test that disabled hotkeys don't execute."""
        handler = HotkeyHandler(mock_logger)
        callback = Mock()
        callback.__name__ = "test_callback"
        
        handler.register_callback("ctrl+shift+e", callback, "Test")
        handler.disable_hotkey("ctrl+shift+e")
        
        pynput_hotkey = "<ctrl>+<shift>+e"
        hotkey_callback = handler._create_hotkey_callback(pynput_hotkey)
        
        # Execute disabled hotkey
        hotkey_callback()
        
        # Should not call original callback
        callback.assert_not_called()

    @patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True)
    @patch('src.bitcrafty_extractor.capture.hotkey_handler.time.time')
    def test_create_hotkey_callback_debouncing(self, mock_time, mock_logger):
        """Test hotkey debouncing functionality."""
        handler = HotkeyHandler(mock_logger)
        callback = Mock()
        callback.__name__ = "test_callback"
        handler.debounce_delay = 0.5
        
        handler.register_callback("ctrl+shift+e", callback, "Test")
        pynput_hotkey = "<ctrl>+<shift>+e"
        
        hotkey_callback = handler._create_hotkey_callback(pynput_hotkey)
        
        # First call
        mock_time.return_value = 1.0
        hotkey_callback()
        
        # Second call within debounce window
        mock_time.return_value = 1.2  # 0.2 seconds later
        hotkey_callback()
        
        # Should only be called once due to debouncing
        callback.assert_called_once()

    @patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True)
    def test_create_hotkey_callback_exception_handling(self, mock_logger):
        """Test that callback exceptions are handled gracefully."""
        handler = HotkeyHandler(mock_logger)
        
        def failing_callback():
            raise Exception("Test exception")
        
        handler.register_callback("ctrl+shift+e", failing_callback, "Test")
        pynput_hotkey = "<ctrl>+<shift>+e"
        
        hotkey_callback = handler._create_hotkey_callback(pynput_hotkey)
        
        # Should not raise exception
        hotkey_callback()
        
        # Should log error
        mock_logger.error.assert_called()

    @patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True)
    def test_compatibility_methods(self, mock_logger):
        """Test compatibility start/stop methods."""
        handler = HotkeyHandler(mock_logger)
        
        with patch.object(handler, 'start_monitoring') as mock_start:
            handler.start()
            mock_start.assert_called_once()
        
        with patch.object(handler, 'stop_monitoring') as mock_stop:
            handler.stop()
            mock_stop.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize("hotkey,expected_format", [
    ("ctrl+shift+e", "<ctrl>+<shift>+e"),
    ("ctrl+c", "<ctrl>+c"),
    ("alt+tab", "<alt>+<tab>"),
    ("win+r", "<cmd>+r"),
    ("control+shift+x", "<ctrl>+<shift>+x"),
    ("escape", "<esc>"),
    ("return", "<enter>"),
])
def test_hotkey_format_conversion_parametrized(hotkey, expected_format, mock_logger):
    """Test hotkey format conversion with various inputs."""
    with patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True):
        handler = HotkeyHandler(mock_logger)
        result = handler._convert_to_pynput_format(hotkey)
        assert result == expected_format


@pytest.mark.unit
def test_hotkey_config_dataclass():
    """Test HotkeyConfig dataclass."""
    callback = Mock()
    
    # Test with default enabled
    config = HotkeyConfig("ctrl+c", callback, "Copy")
    assert config.hotkey_string == "ctrl+c"
    assert config.callback == callback
    assert config.description == "Copy"
    assert config.enabled is True
    
    # Test with explicit enabled
    config2 = HotkeyConfig("ctrl+v", callback, "Paste", enabled=False)
    assert config2.enabled is False


@pytest.mark.unit
def test_multiple_hotkeys_management(mock_logger):
    """Test managing multiple hotkeys."""
    with patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True):
        handler = HotkeyHandler(mock_logger)
        
        callbacks = {
            "ctrl+shift+e": Mock(),
            "ctrl+shift+x": Mock(),
            "ctrl+shift+p": Mock(),
        }
        
        # Set __name__ for all mock callbacks
        for hotkey, callback in callbacks.items():
            callback.__name__ = f"callback_{hotkey.replace('+', '_')}"
        
        # Register all callbacks
        for hotkey, callback in callbacks.items():
            handler.register_callback(hotkey, callback, f"Test {hotkey}")
        
        status = handler.get_status()
        assert status["total_hotkeys"] == 3
        assert status["enabled_hotkeys"] == 3
        
        # Disable one
        handler.disable_hotkey("ctrl+shift+e")
        status = handler.get_status()
        assert status["total_hotkeys"] == 3
        assert status["enabled_hotkeys"] == 2
        
        # Unregister one
        handler.unregister_callback("ctrl+shift+x")
        status = handler.get_status()
        assert status["total_hotkeys"] == 2
        assert status["enabled_hotkeys"] == 1


@pytest.mark.unit
def test_hotkey_handler_edge_cases(mock_logger):
    """Test edge cases and error conditions."""
    with patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True):
        handler = HotkeyHandler(mock_logger)
        
        # Test enable/disable non-existent hotkey (should not crash)
        handler.enable_hotkey("non_existent")
        handler.disable_hotkey("non_existent")
        
        # Test unregister non-existent hotkey (should not crash)
        handler.unregister_callback("non_existent")
        
        # Test empty hotkey (edge case)
        callback = Mock()
        callback.__name__ = "empty_callback"
        handler.register_callback("", callback, "Empty hotkey")
        
        # Should still work (converted to empty string)
        assert "" in handler.hotkeys


@pytest.mark.unit 
def test_hotkey_handler_with_restart_scenario(mock_logger):
    """Test hotkey handler restart behavior during registration changes."""
    with patch('src.bitcrafty_extractor.capture.hotkey_handler.HOTKEY_AVAILABLE', True):
        handler = HotkeyHandler(mock_logger)
        
        # Mock the restart behavior
        with patch.object(handler, 'stop_monitoring') as mock_stop, \
             patch.object(handler, 'start_monitoring') as mock_start:
            
            # Set monitoring state
            handler.is_monitoring = True
            
            # Register callback - should trigger restart
            callback = Mock()
            callback.__name__ = "restart_callback"
            handler.register_callback("ctrl+shift+e", callback, "Test")
            
            mock_stop.assert_called_once()
            mock_start.assert_called_once()


@pytest.mark.unit
def test_hotkey_system_availability_check():
    """Test HOTKEY_AVAILABLE constant behavior."""
    # This tests the module-level constant
    assert isinstance(HOTKEY_AVAILABLE, bool)
    # The actual value depends on whether pynput is installed
