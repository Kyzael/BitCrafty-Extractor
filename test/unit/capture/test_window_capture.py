"""Unit tests for window capture functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import numpy as np
import sys

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from bitcrafty_extractor.capture.window_capture import WindowCapture
from bitcrafty_extractor.config.config_manager import ConfigManager


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    return Mock()


@pytest.fixture
def mock_config_manager():
    """Create a mock config manager for testing."""
    config_manager = Mock(spec=ConfigManager)
    config_manager.config = Mock()
    config_manager.config.capture = Mock()
    config_manager.config.capture.target_process = "bitcraft.exe"
    config_manager.config.capture.game_window_patterns = ["BitCraft"]
    config_manager.config.capture.min_window_width = 800
    config_manager.config.capture.min_window_height = 600
    config_manager.config.capture.focus_based_capture = True
    return config_manager


@pytest.fixture
def window_capture(mock_logger, mock_config_manager):
    """Create a WindowCapture instance for testing."""
    return WindowCapture(mock_logger, mock_config_manager)


@pytest.mark.unit
class TestWindowCapture:
    """Test cases for WindowCapture class."""

    def test_init(self, mock_logger, mock_config_manager):
        """Test WindowCapture initialization."""
        capture = WindowCapture(mock_logger, mock_config_manager)
        assert capture.logger == mock_logger
        assert capture.config_manager == mock_config_manager

    @patch('bitcrafty_extractor.capture.window_capture.psutil.process_iter')
    def test_list_bitcraft_processes(self, mock_process_iter, window_capture):
        """Test BitCraft process detection."""
        # Mock process with bitcraft.exe
        mock_process = Mock()
        mock_process.info = {
            'pid': 1234,
            'name': 'bitcraft.exe',
            'status': 'running'
        }
        mock_process.is_running.return_value = True
        mock_process_iter.return_value = [mock_process]

        processes = window_capture.list_bitcraft_processes()
        
        assert len(processes) == 1
        assert processes[0]['pid'] == 1234
        assert processes[0]['name'] == 'bitcraft.exe'
        assert processes[0]['running'] is True

    @patch('bitcrafty_extractor.capture.window_capture.psutil.process_iter')
    def test_list_bitcraft_processes_empty(self, mock_process_iter, window_capture):
        """Test BitCraft process detection when no processes found."""
        mock_process_iter.return_value = []
        
        processes = window_capture.list_bitcraft_processes()
        
        assert len(processes) == 0

    @patch('bitcrafty_extractor.capture.window_capture.win32gui')
    def test_find_game_window_success(self, mock_win32gui, window_capture):
        """Test successful game window detection."""
        # Mock window enumeration
        mock_hwnd = 12345
        mock_win32gui.EnumWindows.side_effect = lambda callback, _: callback(mock_hwnd, None)
        mock_win32gui.IsWindowVisible.return_value = True
        mock_win32gui.GetWindowText.return_value = "BitCraft - Game Window"
        mock_win32gui.GetWindowRect.return_value = (0, 0, 1920, 1080)
        
        # Mock process info
        mock_win32gui.GetWindowThreadProcessId.return_value = (0, 1234)
        
        with patch('bitcrafty_extractor.capture.window_capture.psutil.Process') as mock_process_class:
            mock_process = Mock()
            mock_process.name.return_value = "bitcraft.exe"
            mock_process_class.return_value = mock_process
            
            window_info = window_capture.find_game_window()
            
            assert window_info is not None
            assert window_info.hwnd == mock_hwnd
            assert window_info.title == "BitCraft - Game Window"
            assert window_info.width == 1920
            assert window_info.height == 1080
            assert window_info.process_name == "bitcraft.exe"
            assert window_info.process_id == 1234

    @patch('bitcrafty_extractor.capture.window_capture.win32gui')
    def test_find_game_window_not_found(self, mock_win32gui, window_capture):
        """Test game window detection when no suitable window found."""
        # Mock no windows or no matching windows
        mock_win32gui.EnumWindows.side_effect = lambda callback, _: None
        
        window_info = window_capture.find_game_window()
        
        assert window_info is None

    def test_validate_window_process_valid(self, window_capture):
        """Test window process validation with valid process."""
        mock_window_info = Mock()
        mock_window_info.process_name = "bitcraft.exe"
        
        is_valid = window_capture.validate_window_process(mock_window_info)
        
        assert is_valid is True

    def test_validate_window_process_invalid(self, window_capture):
        """Test window process validation with invalid process."""
        mock_window_info = Mock()
        mock_window_info.process_name = "notepad.exe"
        
        is_valid = window_capture.validate_window_process(mock_window_info)
        
        assert is_valid is False

    @patch('bitcrafty_extractor.capture.window_capture.ImageGrab')
    def test_capture_current_window_success(self, mock_image_grab, window_capture):
        """Test successful screenshot capture."""
        # Mock PIL ImageGrab
        mock_image = Mock()
        mock_image_grab.grab.return_value = mock_image
        
        # Mock numpy array conversion
        mock_array = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        
        with patch('numpy.array', return_value=mock_array):
            screenshot = window_capture.capture_current_window()
            
            assert screenshot is not None
            assert isinstance(screenshot, np.ndarray)
            assert screenshot.shape == (1080, 1920, 3)

    @patch('bitcrafty_extractor.capture.window_capture.ImageGrab')
    def test_capture_current_window_failure(self, mock_image_grab, window_capture):
        """Test screenshot capture failure."""
        mock_image_grab.grab.side_effect = Exception("Capture failed")
        
        screenshot = window_capture.capture_current_window()
        
        assert screenshot is None

    def test_save_screenshot_success(self, window_capture, tmp_path):
        """Test successful screenshot saving."""
        mock_screenshot = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        output_path = tmp_path / "test_screenshot.png"
        
        with patch('cv2.imwrite', return_value=True):
            result = window_capture.save_screenshot(mock_screenshot, output_path)
            
            assert result is True

    def test_save_screenshot_failure(self, window_capture, tmp_path):
        """Test screenshot saving failure."""
        mock_screenshot = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        output_path = tmp_path / "test_screenshot.png"
        
        with patch('cv2.imwrite', return_value=False):
            result = window_capture.save_screenshot(mock_screenshot, output_path)
            
            assert result is False

    def test_get_window_status_no_window(self, window_capture):
        """Test window status when no window is found."""
        with patch.object(window_capture, 'find_game_window', return_value=None):
            status = window_capture.get_window_status()
            
            assert status['window_found'] is False
            assert status['window_valid'] is False
            assert status['process_count'] >= 0

    def test_get_window_status_with_window(self, window_capture):
        """Test window status when window is found."""
        mock_window_info = Mock()
        mock_window_info.title = "BitCraft"
        mock_window_info.width = 1920
        mock_window_info.height = 1080
        mock_window_info.process_name = "bitcraft.exe"
        mock_window_info.process_id = 1234
        
        with patch.object(window_capture, 'find_game_window', return_value=mock_window_info):
            with patch.object(window_capture, 'validate_window_process', return_value=True):
                with patch.object(window_capture, 'list_bitcraft_processes', return_value=[{'pid': 1234}]):
                    status = window_capture.get_window_status()
                    
                    assert status['window_found'] is True
                    assert status['window_valid'] is True
                    assert status['window_title'] == "BitCraft"
                    assert status['window_dimensions'] == "1920x1080"
                    assert status['process_name'] == "bitcraft.exe"
                    assert status['process_id'] == 1234
                    assert status['process_count'] == 1


@pytest.mark.unit
@pytest.mark.parametrize("process_name,expected", [
    ("bitcraft.exe", True),
    ("BitCraft.exe", True),  # Case insensitive
    ("BITCRAFT.EXE", True),
    ("notepad.exe", False),
    ("chrome.exe", False),
    ("", False),
])
def test_process_validation_parametrized(process_name, expected, mock_logger, mock_config_manager):
    """Test process validation with various process names."""
    capture = WindowCapture(mock_logger, mock_config_manager)
    mock_window_info = Mock()
    mock_window_info.process_name = process_name
    
    result = capture.validate_window_process(mock_window_info)
    assert result == expected


@pytest.mark.unit
def test_window_capture_integration(mock_logger, mock_config_manager):
    """Test basic integration of WindowCapture components."""
    capture = WindowCapture(mock_logger, mock_config_manager)
    
    # Test that all required methods exist
    assert hasattr(capture, 'list_bitcraft_processes')
    assert hasattr(capture, 'find_game_window')
    assert hasattr(capture, 'validate_window_process')
    assert hasattr(capture, 'capture_current_window')
    assert hasattr(capture, 'save_screenshot')
    assert hasattr(capture, 'get_window_status')
    
    # Test that methods are callable
    assert callable(capture.list_bitcraft_processes)
    assert callable(capture.find_game_window)
    assert callable(capture.validate_window_process)
    assert callable(capture.capture_current_window)
    assert callable(capture.save_screenshot)
    assert callable(capture.get_window_status)
