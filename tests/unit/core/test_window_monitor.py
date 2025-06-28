"""Tests for window monitoring functionality."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from bitcrafty_extractor.core.window_monitor import WindowMonitor
from bitcrafty_extractor.core.config_manager import WindowConfig


class TestWindowMonitor:
    """Test cases for WindowMonitor class."""
    
    @pytest.fixture
    def window_config(self):
        """Create test window configuration."""
        return WindowConfig(
            target_name="Bitcraft",
            capture_interval_ms=500,
            max_window_search_attempts=5,
            window_search_interval_ms=1000
        )
    
    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return Mock()
    
    @patch('bitcrafty_extractor.core.window_monitor.WINDOWS_AVAILABLE', True)
    @patch('bitcrafty_extractor.core.window_monitor.PROCESS_VERIFICATION_AVAILABLE', False)  # Disable process verification to test title logic
    def test_window_verification_rejects_vscode(self, window_config, mock_logger):
        """Test that VS Code windows are rejected."""
        monitor = WindowMonitor(window_config, mock_logger)
        
        # VS Code window should be rejected
        vscode_titles = [
            "BitCrafty (Workspace) - Visual Studio Code",
            "base.txt - BitCrafty-Extractor - VS Code",
            "test.py - Visual Studio Code - Insiders"
        ]
        
        for title in vscode_titles:
            result = monitor._is_bitcraft_window(12345, title)
            assert result is False, f"Should reject VS Code window: {title}"
    
    @patch('bitcrafty_extractor.core.window_monitor.WINDOWS_AVAILABLE', True)
    @patch('bitcrafty_extractor.core.window_monitor.PROCESS_VERIFICATION_AVAILABLE', False)
    def test_window_verification_accepts_game_titles(self, window_config, mock_logger):
        """Test that actual game windows are accepted."""
        monitor = WindowMonitor(window_config, mock_logger)
        
        # These should be accepted as game windows
        game_titles = [
            "Bitcraft",
            "Bitcraft - Server Alpha",
            "Bitcraft - MyServer"
        ]
        
        for title in game_titles:
            result = monitor._is_bitcraft_window(12345, title)
            assert result is True, f"Should accept game window: {title}"
    
    @patch('bitcrafty_extractor.core.window_monitor.WINDOWS_AVAILABLE', True)
    @patch('bitcrafty_extractor.core.window_monitor.PROCESS_VERIFICATION_AVAILABLE', False)
    def test_window_verification_rejects_other_apps(self, window_config, mock_logger):
        """Test that other applications are rejected."""
        monitor = WindowMonitor(window_config, mock_logger)
        
        # These should be rejected
        other_app_titles = [
            "Bitcraft Tutorial - Chrome",
            "Discord - BitCraft Server",
            "OBS Studio - Recording Bitcraft",
            "Notepad - bitcraft_notes.txt"
        ]
        
        for title in other_app_titles:
            result = monitor._is_bitcraft_window(12345, title)
            assert result is False, f"Should reject other app: {title}"
    
    @patch('bitcrafty_extractor.core.window_monitor.WINDOWS_AVAILABLE', True)
    @patch('bitcrafty_extractor.core.window_monitor.PROCESS_VERIFICATION_AVAILABLE', True)
    @patch('bitcrafty_extractor.core.window_monitor.win32process')
    @patch('bitcrafty_extractor.core.window_monitor.psutil')
    def test_process_verification_accepts_game_process(self, mock_psutil, mock_win32process, window_config, mock_logger):
        """Test that process verification accepts actual game processes."""
        monitor = WindowMonitor(window_config, mock_logger)
        
        # Mock process verification that finds BitCraft.exe
        mock_win32process.GetWindowThreadProcessId.return_value = (123, 456)
        mock_process = Mock()
        mock_process.name.return_value = "BitCraft.exe"
        mock_process.exe.return_value = "C:\\Games\\BitCraft\\BitCraft.exe"
        mock_psutil.Process.return_value = mock_process
        
        result = monitor._is_bitcraft_window(12345, "Some Window Title")
        assert result is True
        
        # Verify the process checking was called
        mock_win32process.GetWindowThreadProcessId.assert_called_once_with(12345)
        mock_psutil.Process.assert_called_once_with(456)
    
    @patch('bitcrafty_extractor.core.window_monitor.WINDOWS_AVAILABLE', True)
    @patch('bitcrafty_extractor.core.window_monitor.PROCESS_VERIFICATION_AVAILABLE', True)
    @patch('bitcrafty_extractor.core.window_monitor.win32process')
    @patch('bitcrafty_extractor.core.window_monitor.psutil')
    def test_process_verification_rejects_other_process(self, mock_psutil, mock_win32process, window_config, mock_logger):
        """Test that process verification rejects non-game processes."""
        monitor = WindowMonitor(window_config, mock_logger)
        
        # Mock process verification that finds Code.exe (VS Code)
        mock_win32process.GetWindowThreadProcessId.return_value = (123, 456)
        mock_process = Mock()
        mock_process.name.return_value = "Code.exe"
        mock_process.exe.return_value = "C:\\Program Files\\Microsoft VS Code\\Code.exe"
        mock_psutil.Process.return_value = mock_process
        
        # Should fall back to title analysis and reject VS Code
        result = monitor._is_bitcraft_window(12345, "Visual Studio Code")
        assert result is False
    
    @patch('bitcrafty_extractor.core.window_monitor.WINDOWS_AVAILABLE', False)
    def test_initialization_fails_without_windows_apis(self, window_config, mock_logger):
        """Test that initialization fails gracefully without Windows APIs."""
        from bitcrafty_extractor import WindowNotFoundError
        
        with pytest.raises(WindowNotFoundError, match="Windows API libraries not available"):
            WindowMonitor(window_config, mock_logger)
    
    @patch('bitcrafty_extractor.core.window_monitor.WINDOWS_AVAILABLE', True)
    @patch('bitcrafty_extractor.core.window_monitor.gw')
    def test_find_window_filters_candidates(self, mock_gw, window_config, mock_logger):
        """Test that find_window properly filters candidate windows."""
        monitor = WindowMonitor(window_config, mock_logger)
        
        # Mock multiple windows found
        mock_vscode_window = Mock()
        mock_vscode_window.title = "BitCrafty - VS Code"
        mock_vscode_window.visible = True
        mock_vscode_window.width = 1920
        mock_vscode_window.height = 1080
        mock_vscode_window._hWnd = 11111
        
        mock_game_window = Mock()
        mock_game_window.title = "Bitcraft"
        mock_game_window.visible = True
        mock_game_window.width = 1920
        mock_game_window.height = 1080
        mock_game_window._hWnd = 22222
        
        mock_gw.getAllWindows.return_value = [mock_vscode_window, mock_game_window]
        
        # Mock the window verification to reject VS Code but accept game
        with patch.object(monitor, '_is_bitcraft_window') as mock_verify:
            mock_verify.side_effect = lambda handle, title: "VS Code" not in title
            
            result = monitor.find_window()
            
            # Should find the game window and reject VS Code
            assert result is True
            assert monitor._window_handle == 22222
            
            # Verify both windows were checked
            assert mock_verify.call_count == 2
