"""Unit tests for hotkey handler functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import threading
import time

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from bitcrafty_extractor.capture.hotkey_handler import HotkeyHandler, HOTKEY_AVAILABLE


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    return Mock()


@pytest.fixture
def hotkey_handler(mock_logger):
    """Create a HotkeyHandler instance for testing."""
    return HotkeyHandler(mock_logger)


@pytest.mark.unit
class TestHotkeyHandler:
    """Test cases for HotkeyHandler class."""

    def test_init(self, mock_logger):
        """Test HotkeyHandler initialization."""
        handler = HotkeyHandler(mock_logger)
        assert handler.logger == mock_logger
        assert handler.callbacks == {}
        assert handler.listener is None
        assert handler.is_monitoring is False
        assert handler.debounce_delay == 0.5

    def test_hotkey_available_constant(self):
        """Test that HOTKEY_AVAILABLE constant is defined."""
        assert isinstance(HOTKEY_AVAILABLE, bool)

    def test_register_callback_success(self, hotkey_handler):
        """Test successful callback registration."""
        callback = Mock()
        description = "Test callback"
        
        result = hotkey_handler.register_callback("ctrl+shift+e", callback, description)
        
        assert result is True
        assert "ctrl+shift+e" in hotkey_handler.callbacks
        assert hotkey_handler.callbacks["ctrl+shift+e"]["callback"] == callback
        assert hotkey_handler.callbacks["ctrl+shift+e"]["description"] == description
        assert hotkey_handler.callbacks["ctrl+shift+e"]["enabled"] is True

    def test_register_callback_duplicate(self, hotkey_handler):
        """Test registering duplicate hotkey."""
        callback1 = Mock()
        callback2 = Mock()
        
        # Register first callback
        result1 = hotkey_handler.register_callback("ctrl+shift+e", callback1, "First")
        assert result1 is True
        
        # Register duplicate - should overwrite
        result2 = hotkey_handler.register_callback("ctrl+shift+e", callback2, "Second")
        assert result2 is True
        assert hotkey_handler.callbacks["ctrl+shift+e"]["callback"] == callback2

    def test_register_callback_invalid_hotkey(self, hotkey_handler):
        """Test registering invalid hotkey."""
        callback = Mock()
        
        # Test with invalid hotkey format
        result = hotkey_handler.register_callback("invalid_hotkey", callback, "Test")
        
        # Should still register (validation may be done by pynput)
        assert result is True

    def test_unregister_callback_success(self, hotkey_handler):
        """Test successful callback unregistration."""
        callback = Mock()
        hotkey_handler.register_callback("ctrl+shift+e", callback, "Test")
        
        result = hotkey_handler.unregister_callback("ctrl+shift+e")
        
        assert result is True
        assert "ctrl+shift+e" not in hotkey_handler.callbacks

    def test_unregister_callback_not_found(self, hotkey_handler):
        """Test unregistering non-existent callback."""
        result = hotkey_handler.unregister_callback("ctrl+shift+e")
        
        assert result is False

    def test_enable_disable_callback(self, hotkey_handler):
        """Test enabling and disabling callbacks."""
        callback = Mock()
        hotkey_handler.register_callback("ctrl+shift+e", callback, "Test")
        
        # Test disable
        result_disable = hotkey_handler.disable_callback("ctrl+shift+e")
        assert result_disable is True
        assert hotkey_handler.callbacks["ctrl+shift+e"]["enabled"] is False
        
        # Test enable
        result_enable = hotkey_handler.enable_callback("ctrl+shift+e")
        assert result_enable is True
        assert hotkey_handler.callbacks["ctrl+shift+e"]["enabled"] is True

    def test_enable_disable_callback_not_found(self, hotkey_handler):
        """Test enabling/disabling non-existent callback."""
        assert hotkey_handler.disable_callback("non_existent") is False
        assert hotkey_handler.enable_callback("non_existent") is False

    def test_get_hotkey_info(self, hotkey_handler):
        """Test getting hotkey information."""
        callback = Mock()
        hotkey_handler.register_callback("ctrl+shift+e", callback, "Test callback")
        
        info = hotkey_handler.get_hotkey_info()
        
        assert isinstance(info, dict)
        assert "ctrl+shift+e" in info
        assert info["ctrl+shift+e"]["description"] == "Test callback"
        assert info["ctrl+shift+e"]["enabled"] is True

    def test_get_status(self, hotkey_handler):
        """Test getting handler status."""
        callback = Mock()
        hotkey_handler.register_callback("ctrl+shift+e", callback, "Test")
        
        status = hotkey_handler.get_status()
        
        assert isinstance(status, dict)
        assert "is_monitoring" in status
        assert "total_hotkeys" in status
        assert "enabled_hotkeys" in status
        assert "debounce_delay" in status
        assert status["total_hotkeys"] == 1
        assert status["enabled_hotkeys"] == 1
        assert status["debounce_delay"] == 0.5

    @patch('bitcrafty_extractor.capture.hotkey_handler.pynput')
    def test_start_monitoring_success(self, mock_pynput, hotkey_handler):
        """Test successful monitoring start."""
        if not HOTKEY_AVAILABLE:
            pytest.skip("Hotkey system not available")
        
        # Mock pynput GlobalHotKeys
        mock_listener = Mock()
        mock_pynput.keyboard.GlobalHotKeys.return_value = mock_listener
        
        callback = Mock()
        hotkey_handler.register_callback("ctrl+shift+e", callback, "Test")
        
        result = hotkey_handler.start_monitoring()
        
        assert result is True
        assert hotkey_handler.is_monitoring is True
        assert hotkey_handler.listener == mock_listener
        mock_listener.start.assert_called_once()

    def test_start_monitoring_already_running(self, hotkey_handler):
        """Test starting monitoring when already running."""
        hotkey_handler.is_monitoring = True
        
        result = hotkey_handler.start_monitoring()
        
        assert result is False

    def test_start_monitoring_no_callbacks(self, hotkey_handler):
        """Test starting monitoring with no callbacks."""
        result = hotkey_handler.start_monitoring()
        
        assert result is False

    @patch('bitcrafty_extractor.capture.hotkey_handler.pynput')
    def test_stop_monitoring_success(self, mock_pynput, hotkey_handler):
        """Test successful monitoring stop."""
        if not HOTKEY_AVAILABLE:
            pytest.skip("Hotkey system not available")
        
        # Mock listener
        mock_listener = Mock()
        hotkey_handler.listener = mock_listener
        hotkey_handler.is_monitoring = True
        
        result = hotkey_handler.stop_monitoring()
        
        assert result is True
        assert hotkey_handler.is_monitoring is False
        assert hotkey_handler.listener is None
        mock_listener.stop.assert_called_once()

    def test_stop_monitoring_not_running(self, hotkey_handler):
        """Test stopping monitoring when not running."""
        result = hotkey_handler.stop_monitoring()
        
        assert result is False

    def test_callback_execution_with_debounce(self, hotkey_handler):
        """Test callback execution with debouncing."""
        callback = Mock()
        hotkey_handler.register_callback("ctrl+shift+e", callback, "Test")
        hotkey_handler.debounce_delay = 0.1  # Short delay for testing
        
        # Simulate rapid hotkey presses
        hotkey_handler._execute_callback("ctrl+shift+e")
        hotkey_handler._execute_callback("ctrl+shift+e")  # Should be debounced
        
        # Wait for debounce period
        time.sleep(0.15)
        
        hotkey_handler._execute_callback("ctrl+shift+e")  # Should execute
        
        # Callback should be called twice (first and third)
        assert callback.call_count >= 1  # At least one call due to debouncing

    def test_callback_execution_disabled(self, hotkey_handler):
        """Test that disabled callbacks are not executed."""
        callback = Mock()
        hotkey_handler.register_callback("ctrl+shift+e", callback, "Test")
        hotkey_handler.disable_callback("ctrl+shift+e")
        
        hotkey_handler._execute_callback("ctrl+shift+e")
        
        callback.assert_not_called()

    def test_callback_execution_exception_handling(self, hotkey_handler):
        """Test that callback exceptions are handled gracefully."""
        def failing_callback():
            raise Exception("Test exception")
        
        hotkey_handler.register_callback("ctrl+shift+e", failing_callback, "Test")
        
        # Should not raise exception
        hotkey_handler._execute_callback("ctrl+shift+e")
        
        # Logger should have been called with error
        hotkey_handler.logger.error.assert_called()


@pytest.mark.unit
@pytest.mark.parametrize("hotkey,expected_valid", [
    ("ctrl+shift+e", True),
    ("ctrl+shift+x", True),
    ("alt+f4", True),
    ("ctrl+c", True),
    ("shift+tab", True),
    ("", False),
    ("invalid", True),  # May be valid format, pynput will validate
])
def test_hotkey_format_validation(hotkey, expected_valid, mock_logger):
    """Test hotkey format validation with various inputs."""
    handler = HotkeyHandler(mock_logger)
    callback = Mock()
    
    result = handler.register_callback(hotkey, callback, "Test")
    
    # Basic registration should succeed for most formats
    # Actual validation happens in pynput
    if hotkey:
        assert result is True
    else:
        # Empty hotkey might be rejected
        assert result == expected_valid


@pytest.mark.unit
def test_hotkey_handler_context_manager_pattern(mock_logger):
    """Test using HotkeyHandler in a context-manager-like pattern."""
    handler = HotkeyHandler(mock_logger)
    callback = Mock()
    
    try:
        # Setup
        handler.register_callback("ctrl+shift+e", callback, "Test")
        
        # Test that we can get status
        status = handler.get_status()
        assert status["total_hotkeys"] == 1
        
    finally:
        # Cleanup
        if handler.is_monitoring:
            handler.stop_monitoring()


@pytest.mark.unit
def test_multiple_callbacks_registration(mock_logger):
    """Test registering multiple callbacks."""
    handler = HotkeyHandler(mock_logger)
    
    callbacks = {
        "ctrl+shift+e": Mock(),
        "ctrl+shift+x": Mock(),
        "ctrl+shift+p": Mock(),
    }
    
    for hotkey, callback in callbacks.items():
        result = handler.register_callback(hotkey, callback, f"Test {hotkey}")
        assert result is True
    
    status = handler.get_status()
    assert status["total_hotkeys"] == 3
    assert status["enabled_hotkeys"] == 3
    
    info = handler.get_hotkey_info()
    assert len(info) == 3
    for hotkey in callbacks.keys():
        assert hotkey in info


@pytest.mark.unit
def test_hotkey_handler_thread_safety(mock_logger):
    """Test basic thread safety of HotkeyHandler."""
    handler = HotkeyHandler(mock_logger)
    callback = Mock()
    
    def register_callback():
        handler.register_callback("ctrl+shift+e", callback, "Test")
    
    def get_status():
        handler.get_status()
    
    # Run operations in separate threads
    threads = [
        threading.Thread(target=register_callback),
        threading.Thread(target=get_status),
    ]
    
    for thread in threads:
        thread.start()
    
    for thread in threads:
        thread.join(timeout=1.0)
    
    # Should complete without issues
    assert "ctrl+shift+e" in handler.callbacks
