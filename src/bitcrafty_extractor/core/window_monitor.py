"""Window monitoring for game window detection and capture."""
import time
from typing import Optional, Tuple
import numpy as np
import structlog

try:
    import pygetwindow as gw
    import win32gui
    import win32con
    import win32ui
    from PIL import Image
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False

from bitcrafty_extractor import WindowNotFoundError, ImageProcessingError
from bitcrafty_extractor.core.config_manager import WindowConfig


class WindowMonitor:
    """Monitors and captures screenshots from the target game window."""
    
    def __init__(self, config: WindowConfig, logger: structlog.BoundLogger):
        """Initialize window monitor.
        
        Args:
            config: Window monitoring configuration
            logger: Structured logger instance
            
        Raises:
            WindowNotFoundError: If Windows APIs are not available
        """
        if not WINDOWS_AVAILABLE:
            raise WindowNotFoundError("Windows API libraries not available. Install pygetwindow and pywin32.")
        
        self.config = config
        self.logger = logger
        self._window_handle: Optional[int] = None
        self._last_window_search = 0.0
        
        self.logger.info("Window monitor initialized", target_window=config.target_name)
    
    def find_window(self) -> bool:
        """Find the target game window.
        
        Returns:
            True if window was found, False otherwise
        """
        current_time = time.time()
        
        # Rate limit window searches
        if (current_time - self._last_window_search) < (self.config.window_search_interval_ms / 1000.0):
            return self._window_handle is not None
        
        self._last_window_search = current_time
        
        try:
            # Search for windows with the target name
            windows = gw.getWindowsWithTitle(self.config.target_name)
            
            if windows:
                window = windows[0]  # Take the first match
                self._window_handle = window._hWnd
                
                self.logger.info("Target window found", 
                               window_title=window.title,
                               window_handle=self._window_handle,
                               position=(window.left, window.top),
                               size=(window.width, window.height))
                return True
            else:
                if self._window_handle is not None:
                    self.logger.warning("Target window lost", target=self.config.target_name)
                    self._window_handle = None
                return False
                
        except Exception as e:
            self.logger.error("Error searching for window", error=str(e), target=self.config.target_name)
            self._window_handle = None
            return False
    
    def capture_window(self) -> Optional[np.ndarray]:
        """Capture a screenshot of the target window.
        
        Returns:
            Screenshot as numpy array (BGR format) or None if capture failed
            
        Raises:
            WindowNotFoundError: If target window is not available
            ImageProcessingError: If screenshot capture fails
        """
        if not self._window_handle or not self.is_window_valid():
            if not self.find_window():
                return None
        
        try:
            # Get window dimensions
            window_rect = win32gui.GetWindowRect(self._window_handle)
            width = window_rect[2] - window_rect[0]
            height = window_rect[3] - window_rect[1]
            
            if width <= 0 or height <= 0:
                self.logger.warning("Invalid window dimensions", width=width, height=height)
                return None
            
            # Capture window content
            window_dc = win32gui.GetWindowDC(self._window_handle)
            dc_obj = win32ui.CreateDCFromHandle(window_dc)
            mem_dc = dc_obj.CreateCompatibleDC()
            
            # Create bitmap
            screenshot_bmp = win32ui.CreateBitmap()
            screenshot_bmp.CreateCompatibleBitmap(dc_obj, width, height)
            mem_dc.SelectObject(screenshot_bmp)
            
            # Copy window content to bitmap
            mem_dc.BitBlt((0, 0), (width, height), dc_obj, (0, 0), win32con.SRCCOPY)
            
            # Convert to PIL Image
            bmp_info = screenshot_bmp.GetInfo()
            bmp_str = screenshot_bmp.GetBitmapBits(True)
            pil_image = Image.frombuffer(
                'RGB',
                (bmp_info['bmWidth'], bmp_info['bmHeight']),
                bmp_str,
                'raw',
                'BGRX',
                0,
                1
            )
            
            # Convert to numpy array (BGR format for OpenCV compatibility)
            image_array = np.array(pil_image)
            image_bgr = image_array[:, :, [2, 1, 0]]  # RGB to BGR
            
            # Cleanup
            dc_obj.DeleteDC()
            mem_dc.DeleteDC()
            win32gui.ReleaseDC(self._window_handle, window_dc)
            win32gui.DeleteObject(screenshot_bmp.GetHandle())
            
            self.logger.debug("Window screenshot captured", 
                            shape=image_bgr.shape,
                            window_handle=self._window_handle)
            
            return image_bgr
            
        except Exception as e:
            self.logger.error("Failed to capture window screenshot", 
                            error=str(e),
                            window_handle=self._window_handle)
            raise ImageProcessingError(f"Screenshot capture failed: {e}") from e
    
    def is_window_valid(self) -> bool:
        """Check if the current window handle is still valid.
        
        Returns:
            True if window is valid and visible, False otherwise
        """
        if not self._window_handle:
            return False
        
        try:
            # Check if window still exists and is visible
            return win32gui.IsWindow(self._window_handle) and win32gui.IsWindowVisible(self._window_handle)
        except Exception:
            return False
    
    def get_window_info(self) -> Optional[Tuple[str, Tuple[int, int, int, int]]]:
        """Get information about the current target window.
        
        Returns:
            Tuple of (window_title, (left, top, right, bottom)) or None if no window
        """
        if not self._window_handle or not self.is_window_valid():
            return None
        
        try:
            window_rect = win32gui.GetWindowRect(self._window_handle)
            window_title = win32gui.GetWindowText(self._window_handle)
            return window_title, window_rect
        except Exception:
            return None
    
    @property
    def is_monitoring(self) -> bool:
        """Check if actively monitoring a valid window."""
        return self._window_handle is not None and self.is_window_valid()
