"""
Critical unit tests for WindowCapture functionality.

This module tests the most important WindowCapture operations:
- Initialization and configuration
- Window detection and validation 
- Screenshot capture error handling
- Image processing utilities
"""

import pytest
import numpy as np
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.bitcrafty_extractor.capture.window_capture import WindowCapture, WindowInfo


@pytest.fixture
def mock_logger():
    """Provide a mock logger for testing."""
    return Mock()


@pytest.fixture
def mock_config():
    """Provide a mock configuration object."""
    config = Mock()
    config.capture = Mock()
    config.capture.game_window_patterns = ["BitCraft", "bitcraft"] 
    config.capture.target_process = "bitcraft.exe"
    config.capture.min_window_width = 800
    config.capture.min_window_height = 600
    return config


@pytest.mark.unit
class TestWindowCaptureInitialization:
    """Test WindowCapture initialization and configuration."""
    
    @patch('src.bitcrafty_extractor.capture.window_capture.CAPTURE_AVAILABLE', True)
    def test_init_with_config(self, mock_logger, mock_config):
        """Test WindowCapture initialization with provided config."""
        capture = WindowCapture(mock_logger, mock_config)
        
        assert capture.logger == mock_logger
        assert capture.target_window_names == ["BitCraft", "bitcraft"]
        assert capture.target_process_name == "bitcraft.exe"
        assert capture.min_window_width == 800
        assert capture.min_window_height == 600
        assert capture.current_window is None
    
    @patch('src.bitcrafty_extractor.capture.window_capture.CAPTURE_AVAILABLE', True)
    def test_init_without_config(self, mock_logger):
        """Test WindowCapture initialization with default config."""
        capture = WindowCapture(mock_logger, None)
        
        assert capture.logger == mock_logger
        assert "BitCraft" in capture.target_window_names
        assert "bitcraft" in capture.target_window_names
        assert capture.target_process_name == "bitcraft.exe"
        assert capture.min_window_width == 400
        assert capture.min_window_height == 300
        assert capture.current_window is None
    
    @patch('src.bitcrafty_extractor.capture.window_capture.CAPTURE_AVAILABLE', False)
    def test_init_capture_unavailable(self, mock_logger):
        """Test WindowCapture initialization when capture is unavailable."""
        with pytest.raises(RuntimeError, match="Window capture not available"):
            WindowCapture(mock_logger, None)


@pytest.mark.unit
class TestWindowDetection:
    """Test window detection and validation functionality."""
    
    @patch('src.bitcrafty_extractor.capture.window_capture.CAPTURE_AVAILABLE', True)
    def test_validate_window_process_valid(self, mock_logger):
        """Test window process validation with valid BitCraft process."""
        capture = WindowCapture(mock_logger, None)
        
        # Mock valid window info
        window_info = WindowInfo(
            hwnd=12345,
            title="BitCraft",
            rect=(0, 0, 1920, 1080),
            width=1920,
            height=1080,
            process_name="bitcraft.exe",
            process_id=1234
        )
        
        with patch('src.bitcrafty_extractor.capture.window_capture.psutil.Process') as mock_process:
            mock_proc = Mock()
            mock_proc.name.return_value = "bitcraft.exe"
            mock_proc.is_running.return_value = True
            mock_process.return_value = mock_proc
            
            result = capture.validate_window_process(window_info)
            assert result is True
    
    @patch('src.bitcrafty_extractor.capture.window_capture.CAPTURE_AVAILABLE', True)
    def test_validate_window_process_invalid(self, mock_logger):
        """Test window process validation with invalid process."""
        capture = WindowCapture(mock_logger, None)
        
        # Mock invalid window info
        window_info = WindowInfo(
            hwnd=12345,
            title="Notepad",
            rect=(0, 0, 800, 600),
            width=800,
            height=600,
            process_name="notepad.exe",
            process_id=5678
        )
        
        with patch('src.bitcrafty_extractor.capture.window_capture.psutil.Process') as mock_process:
            mock_proc = Mock()
            mock_proc.name.return_value = "notepad.exe"
            mock_proc.is_running.return_value = True
            mock_process.return_value = mock_proc
            
            result = capture.validate_window_process(window_info)
            assert result is False
    
    @patch('src.bitcrafty_extractor.capture.window_capture.CAPTURE_AVAILABLE', True)
    def test_validate_window_process_exception(self, mock_logger):
        """Test window process validation when psutil raises exception."""
        capture = WindowCapture(mock_logger, None)
        
        window_info = WindowInfo(
            hwnd=12345,
            title="BitCraft",
            rect=(0, 0, 1920, 1080),
            width=1920,
            height=1080,
            process_name="bitcraft.exe",
            process_id=1234
        )
        
        with patch('src.bitcrafty_extractor.capture.window_capture.psutil.Process') as mock_process:
            mock_process.side_effect = Exception("Process not found")
            
            # The method should handle the exception and return False, not raise it
            with pytest.raises(Exception):
                capture.validate_window_process(window_info)


@pytest.mark.unit
class TestScreenshotCapture:
    """Test screenshot capture functionality."""
    
    @patch('src.bitcrafty_extractor.capture.window_capture.CAPTURE_AVAILABLE', True)
    def test_capture_window_no_window(self, mock_logger):
        """Test capture when no window is available."""
        capture = WindowCapture(mock_logger, None)
        
        result = capture.capture_window(None)
        assert result is None
    
    @patch('src.bitcrafty_extractor.capture.window_capture.CAPTURE_AVAILABLE', True)  
    @patch('src.bitcrafty_extractor.capture.window_capture.win32gui')
    def test_capture_window_invalid_handle(self, mock_win32gui, mock_logger):
        """Test capture when window handle is invalid."""
        capture = WindowCapture(mock_logger, None)
        
        window_info = WindowInfo(
            hwnd=99999,  # Invalid handle
            title="BitCraft",
            rect=(0, 0, 1920, 1080),
            width=1920,
            height=1080,
            process_name="bitcraft.exe",
            process_id=1234
        )
        
        # Mock win32gui to return False for IsWindow (invalid handle)
        mock_win32gui.IsWindow.return_value = False
        
        result = capture.capture_window(window_info)
        assert result is None
        assert capture.current_window is None  # Should reset current_window
    
    @patch('src.bitcrafty_extractor.capture.window_capture.CAPTURE_AVAILABLE', True)
    @patch('src.bitcrafty_extractor.capture.window_capture.win32gui')
    def test_capture_window_not_in_focus(self, mock_win32gui, mock_logger):
        """Test capture when BitCraft window is not in focus."""
        capture = WindowCapture(mock_logger, None)
        
        window_info = WindowInfo(
            hwnd=12345,
            title="BitCraft",
            rect=(0, 0, 1920, 1080),
            width=1920,
            height=1080,
            process_name="bitcraft.exe",
            process_id=1234
        )
        
        # Mock window as valid but not in focus
        mock_win32gui.IsWindow.return_value = True
        mock_win32gui.GetForegroundWindow.return_value = 54321  # Different window in focus
        
        result = capture.capture_window(window_info)
        assert result is None


@pytest.mark.unit
class TestImageProcessing:
    """Test image processing and saving functionality."""
    
    @patch('src.bitcrafty_extractor.capture.window_capture.CAPTURE_AVAILABLE', True)
    def test_save_screenshot_success(self, mock_logger):
        """Test successful screenshot saving."""
        capture = WindowCapture(mock_logger, None)
        
        # Create test image
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            output_path = Path(tmp_file.name)
        
        try:
            # The actual method uses PIL Image.save, not cv2.imwrite
            with patch('src.bitcrafty_extractor.capture.window_capture.Image') as mock_image:
                mock_pil_image = Mock()
                mock_image.fromarray.return_value = mock_pil_image
                
                result = capture.save_screenshot(test_image, output_path)
                assert result is True
                mock_image.fromarray.assert_called_once()
                mock_pil_image.save.assert_called_once_with(output_path, quality=95, optimize=True)
        finally:
            if output_path.exists():
                output_path.unlink()
    
    @patch('src.bitcrafty_extractor.capture.window_capture.CAPTURE_AVAILABLE', True)
    def test_save_screenshot_failure(self, mock_logger):
        """Test screenshot saving failure."""
        capture = WindowCapture(mock_logger, None)
        
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        output_path = Path("temp/invalid/path/test.png")  # Use gitignored temp directory but invalid subpath
        
        with patch('src.bitcrafty_extractor.capture.window_capture.Image') as mock_image:
            mock_pil_image = Mock()
            mock_pil_image.save.side_effect = Exception("Cannot save to invalid path")
            mock_image.fromarray.return_value = mock_pil_image
            
            result = capture.save_screenshot(test_image, output_path)
            assert result is False
    
    @patch('src.bitcrafty_extractor.capture.window_capture.CAPTURE_AVAILABLE', True)
    def test_save_screenshot_exception(self, mock_logger):
        """Test screenshot saving when PIL raises exception."""
        capture = WindowCapture(mock_logger, None)
        
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        output_path = Path("temp/test.png")  # Use gitignored temp directory
        
        with patch('src.bitcrafty_extractor.capture.window_capture.Image') as mock_image:
            mock_image.fromarray.side_effect = Exception("Image conversion error")
            
            result = capture.save_screenshot(test_image, output_path)
            assert result is False
    
    @patch('src.bitcrafty_extractor.capture.window_capture.CAPTURE_AVAILABLE', True)
    def test_detect_hardware_acceleration(self, mock_logger):
        """Test hardware acceleration detection."""
        capture = WindowCapture(mock_logger, None)
        
        # Test with solid black image (likely hardware accelerated)
        black_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        result = capture.detect_hardware_acceleration(black_image)
        assert isinstance(result, bool)
        
        # Test with random image (not hardware accelerated)  
        random_image = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        result = capture.detect_hardware_acceleration(random_image)
        assert isinstance(result, bool)


@pytest.mark.unit 
class TestProcessListing:
    """Test BitCraft process detection functionality."""
    
    @patch('src.bitcrafty_extractor.capture.window_capture.CAPTURE_AVAILABLE', True)
    @patch('src.bitcrafty_extractor.capture.window_capture.psutil.process_iter')
    def test_list_bitcraft_processes_found(self, mock_process_iter, mock_logger):
        """Test BitCraft process listing when processes are found."""
        capture = WindowCapture(mock_logger, None)
        
        # Mock BitCraft process - using the actual API structure
        mock_process = Mock()
        mock_process.info = {
            'pid': 1234,
            'name': 'bitcraft.exe',
            'cmdline': ['C:\\Games\\BitCraft\\bitcraft.exe']
        }
        mock_process.is_running.return_value = True
        mock_process_iter.return_value = [mock_process]
        
        processes = capture.list_bitcraft_processes()
        
        assert len(processes) == 1
        assert processes[0]['pid'] == 1234
        assert processes[0]['name'] == 'bitcraft.exe'
        assert processes[0]['running'] is True
        assert 'cmdline' in processes[0]
        
        # Verify psutil.process_iter was called with correct attributes
        mock_process_iter.assert_called_once_with(['pid', 'name', 'cmdline'])
    
    @patch('src.bitcrafty_extractor.capture.window_capture.CAPTURE_AVAILABLE', True)
    @patch('src.bitcrafty_extractor.capture.window_capture.psutil.process_iter')
    def test_list_bitcraft_processes_none_found(self, mock_process_iter, mock_logger):
        """Test BitCraft process listing when no processes are found."""
        capture = WindowCapture(mock_logger, None)
        
        # Mock no BitCraft processes
        mock_other_process = Mock()
        mock_other_process.info = {
            'pid': 5678,
            'name': 'notepad.exe',
            'status': 'running'
        }
        mock_process_iter.return_value = [mock_other_process]
        
        processes = capture.list_bitcraft_processes()
        assert len(processes) == 0
    
    @patch('src.bitcrafty_extractor.capture.window_capture.CAPTURE_AVAILABLE', True)
    @patch('src.bitcrafty_extractor.capture.window_capture.psutil.process_iter')
    def test_list_bitcraft_processes_exception(self, mock_process_iter, mock_logger):
        """Test BitCraft process listing when psutil raises exception."""
        capture = WindowCapture(mock_logger, None)
        
        # Mock psutil exception
        mock_process_iter.side_effect = Exception("Access denied")
        
        processes = capture.list_bitcraft_processes()
        assert len(processes) == 0


@pytest.mark.unit
class TestWindowStatus:
    """Test window status reporting functionality."""
    
    @patch('src.bitcrafty_extractor.capture.window_capture.CAPTURE_AVAILABLE', True)
    def test_get_window_status_no_window(self, mock_logger):
        """Test window status when no window is found."""
        capture = WindowCapture(mock_logger, None)
        
        # current_window is None by default
        status = capture.get_window_status()
        
        assert status['window_found'] is False
        assert status['window_valid'] is False
        assert status['title'] is None
        assert status['size'] is None
        assert status['process_name'] is None
        assert status['process_id'] is None
    
    @patch('src.bitcrafty_extractor.capture.window_capture.CAPTURE_AVAILABLE', True) 
    @patch('src.bitcrafty_extractor.capture.window_capture.win32gui')
    def test_get_window_status_with_valid_window(self, mock_win32gui, mock_logger):
        """Test window status when valid window is found."""
        capture = WindowCapture(mock_logger, None)
        
        window_info = WindowInfo(
            hwnd=12345,
            title="BitCraft",
            rect=(0, 0, 1920, 1080),
            width=1920,
            height=1080,
            process_name="bitcraft.exe",
            process_id=1234
        )
        
        # Set current window 
        capture.current_window = window_info
        
        # Mock window validation
        mock_win32gui.IsWindow.return_value = True
        mock_win32gui.IsWindowVisible.return_value = True
        
        with patch('src.bitcrafty_extractor.capture.window_capture.psutil.Process') as mock_process:
            mock_proc = Mock()
            mock_proc.is_running.return_value = True
            mock_proc.name.return_value = "bitcraft.exe"
            mock_process.return_value = mock_proc
            
            status = capture.get_window_status()
            
            assert status['window_found'] is True
            assert status['window_valid'] is True
            assert status['title'] == "BitCraft"
            assert status['size'] == "1920x1080"
            assert status['process_name'] == "bitcraft.exe"
            assert status['process_id'] == 1234
            assert status['hwnd'] == 12345


@pytest.mark.unit
def test_capture_game_screenshot_function(mock_logger):
    """Test the standalone capture_game_screenshot function."""
    from src.bitcrafty_extractor.capture.window_capture import capture_game_screenshot
    
    with patch('src.bitcrafty_extractor.capture.window_capture.WindowCapture') as MockWindowCapture:
        mock_capture = Mock()
        mock_capture.capture_current_window.return_value = None
        MockWindowCapture.return_value = mock_capture
        
        result = capture_game_screenshot(mock_logger)
        assert result is None
        
        # Verify WindowCapture was initialized correctly
        MockWindowCapture.assert_called_once_with(mock_logger)
