"""Real-time game window capture for BitCrafty-Extractor.

This module handles detecting and capturing screenshots from the Bitcraft game window
in real-time when triggered by global hotkeys.
"""

import time
from pathlib import Path
from typing import Optional, Tuple, List
import numpy as np
import structlog
from dataclasses import dataclass

try:
    import win32gui
    import win32ui
    import win32con
    import win32process
    import psutil
    from PIL import Image, ImageGrab
    import cv2
    CAPTURE_AVAILABLE = True
except ImportError:
    CAPTURE_AVAILABLE = False


@dataclass
class WindowInfo:
    """Information about a captured window."""
    hwnd: int
    title: str
    rect: Tuple[int, int, int, int]  # (left, top, right, bottom)
    width: int
    height: int
    process_name: str  # Name of the process (e.g., "bitcraft.exe")
    process_id: int    # Process ID


class WindowCapture:
    """Real-time game window capture system."""
    
    def __init__(self, logger: structlog.BoundLogger, config: Optional[object] = None):
        """Initialize the window capture system.
        
        Args:
            logger: Structured logger for operation tracking
            config: Configuration object with capture settings
            
        Raises:
            RuntimeError: If window capture is not available on this platform
        """
        if not CAPTURE_AVAILABLE:
            raise RuntimeError("Window capture not available. Install pywin32 for Windows support.")
        
        self.logger = logger
        
        # Use configuration if provided, otherwise use defaults
        if config and hasattr(config, 'capture'):
            capture_config = config.capture
            self.target_window_names = capture_config.game_window_patterns
            self.target_process_name = capture_config.target_process
            self.min_window_width = capture_config.min_window_width
            self.min_window_height = capture_config.min_window_height
        else:
            # Default configuration
            self.target_window_names = ["BitCraft", "bitcraft", "BITCRAFT", "Bitcraft"]
            self.target_process_name = "bitcraft.exe"
            self.min_window_width = 400
            self.min_window_height = 300
            
        self.current_window: Optional[WindowInfo] = None
        
        self.logger.info("Window capture system initialized", 
                        target_process=self.target_process_name,
                        target_window_names=self.target_window_names,
                        min_size=f"{self.min_window_width}x{self.min_window_height}")

    def find_game_window(self) -> Optional[WindowInfo]:
        """Find the BitCraft game window from bitcraft.exe process.
        
        Returns:
            WindowInfo if game window found from correct process, None otherwise
        """
        def enum_window_callback(hwnd, windows):
            if not win32gui.IsWindowVisible(hwnd):
                return True
                
            window_title = win32gui.GetWindowText(hwnd)
            
            # Check if window title matches our target patterns
            if not any(target.lower() in window_title.lower() for target in self.target_window_names):
                return True
            
            try:
                # Get process ID and name for this window
                _, process_id = win32process.GetWindowThreadProcessId(hwnd)
                
                # Get process info using psutil
                try:
                    process = psutil.Process(process_id)
                    process_name = process.name().lower()
                    
                    # Only accept windows from bitcraft.exe
                    if process_name != self.target_process_name.lower():
                        self.logger.debug("Window found but wrong process",
                                        window_title=window_title,
                                        process_name=process_name,
                                        expected=self.target_process_name)
                        return True
                    
                    # Get window dimensions
                    rect = win32gui.GetWindowRect(hwnd)
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]
                    
                    # Skip very small windows (likely UI elements)
                    if width < self.min_window_width or height < self.min_window_height:
                        self.logger.debug("Window too small, skipping",
                                        window_title=window_title,
                                        size=f"{width}x{height}",
                                        min_size=f"{self.min_window_width}x{self.min_window_height}")
                        return True
                    
                    windows.append(WindowInfo(
                        hwnd=hwnd,
                        title=window_title,
                        rect=rect,
                        width=width,
                        height=height,
                        process_name=process.name(),
                        process_id=process_id
                    ))
                    
                    self.logger.debug("Valid BitCraft window found",
                                    window_title=window_title,
                                    process_name=process.name(),
                                    process_id=process_id,
                                    size=f"{width}x{height}")
                
                except psutil.NoSuchProcess:
                    self.logger.debug("Process no longer exists", process_id=process_id)
                except psutil.AccessDenied:
                    self.logger.debug("Access denied to process", process_id=process_id)
                    
            except Exception as e:
                self.logger.debug("Error checking window process", 
                                window_title=window_title, 
                                error=str(e))
            
            return True
        
        windows = []
        win32gui.EnumWindows(enum_window_callback, windows)
        
        if not windows:
            self.logger.warning("No BitCraft windows found from bitcraft.exe process", 
                              target_process=self.target_process_name,
                              target_names=self.target_window_names)
            return None
        
        # Return the largest window (likely the main game window)
        largest_window = max(windows, key=lambda w: w.width * w.height)
        self.current_window = largest_window
        
        self.logger.info("BitCraft game window found",
                       title=largest_window.title,
                       size=f"{largest_window.width}x{largest_window.height}",
                       process_name=largest_window.process_name,
                       process_id=largest_window.process_id,
                       hwnd=largest_window.hwnd)
        
        return largest_window

    def ensure_window_visible(self, window_info: WindowInfo) -> bool:
        """Ensure the window is visible and ready for capture.
        
        Args:
            window_info: Window information
            
        Returns:
            True if window is ready for capture, False otherwise
        """
        try:
            hwnd = window_info.hwnd
            
            # Check if window is minimized
            if win32gui.IsIconic(hwnd):
                self.logger.info("Window is minimized, attempting to restore", hwnd=hwnd)
                # Restore the window (but don't bring it to foreground)
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.1)  # Brief delay for window state change
                
                # Check if restore was successful
                if win32gui.IsIconic(hwnd):
                    self.logger.warning("Failed to restore minimized window", hwnd=hwnd)
                    return False
                    
                self.logger.info("Window restored successfully", hwnd=hwnd)
            
            # Verify window is visible
            if not win32gui.IsWindowVisible(hwnd):
                self.logger.warning("Window is not visible", hwnd=hwnd)
                return False
                
            return True
            
        except Exception as e:
            self.logger.error("Error ensuring window visibility", error=str(e), hwnd=hwnd)
            return False

    def capture_window(self, window_info: Optional[WindowInfo] = None) -> Optional[np.ndarray]:
        """Capture screenshot of the game window.
        
        Args:
            window_info: Window to capture. If None, uses current_window.
            
        Returns:
            Screenshot as numpy array (BGR format) or None if capture failed
        """
        if window_info is None:
            window_info = self.current_window
        
        if window_info is None:
            self.logger.error("No window to capture")
            return None
        
        # Check if window is still valid
        hwnd = window_info.hwnd
        if not win32gui.IsWindow(hwnd):
            self.logger.warning("Window handle is no longer valid", hwnd=hwnd)
            self.current_window = None
            return None
        
        # Check if BitCraft window is in focus (foreground)
        try:
            foreground_hwnd = win32gui.GetForegroundWindow()
            if foreground_hwnd != window_info.hwnd:
                self.logger.info("BitCraft window is not in focus - capture skipped",
                               foreground_hwnd=foreground_hwnd,
                               bitcraft_hwnd=window_info.hwnd,
                               window_title=window_info.title)
                return None
        except Exception as e:
            self.logger.warning("Could not check window focus", error=str(e))
            # Continue with capture anyway if we can't check focus
        
        # Use fullscreen capture when BitCraft is in focus
        # This works perfectly for windowed fullscreen mode
        try:
            self.logger.debug("Capturing fullscreen while BitCraft is in focus", hwnd=hwnd)
            
            # Capture entire screen using PIL ImageGrab
            screenshot_pil = ImageGrab.grab()
            
            # Convert PIL image to OpenCV format (BGR)
            screenshot_cv = cv2.cvtColor(np.array(screenshot_pil), cv2.COLOR_RGB2BGR)
            
            self.logger.info("Fullscreen capture successful while BitCraft focused", 
                           hwnd=hwnd,
                           dimensions=(screenshot_cv.shape[1], screenshot_cv.shape[0]))
            
            return screenshot_cv
            
        except Exception as e:
            self.logger.error("Fullscreen capture failed", hwnd=hwnd, error=str(e))
            return None

    def capture_window_direct(self, window_info: WindowInfo) -> Optional[np.ndarray]:
        """Capture window content directly using PrintWindow API.
        
        This method captures the actual window content regardless of whether 
        it's obscured by other windows or not in the foreground.
        
        Args:
            window_info: Window to capture
            
        Returns:
            Screenshot as numpy array (BGR format) or None if capture failed
        """
        try:
            hwnd = window_info.hwnd
            left, top, right, bottom = window_info.rect
            width = right - left
            height = bottom - top
            
            # Ensure window is in a capturable state
            if not self.ensure_window_visible(window_info):
                return None
            
            # Create device contexts
            hwnd_dc = win32gui.GetWindowDC(hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            
            # Create bitmap
            save_bitmap = win32ui.CreateBitmap()
            save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(save_bitmap)
            
            # Try PrintWindow first (captures actual window content)
            import ctypes
            from ctypes import wintypes
            
            # PrintWindow API
            user32 = ctypes.windll.user32
            result = user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 0)
            
            if result == 0:
                self.logger.debug("PrintWindow failed, falling back to BitBlt", hwnd=hwnd)
                # Fallback to BitBlt method
                result = save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)
                
                if result == 0:
                    self.logger.error("Both PrintWindow and BitBlt failed", hwnd=hwnd)
                    # Cleanup and return None
                    win32gui.DeleteObject(save_bitmap.GetHandle())
                    save_dc.DeleteDC()
                    mfc_dc.DeleteDC()
                    win32gui.ReleaseDC(hwnd, hwnd_dc)
                    return None
            
            # Convert to PIL Image then numpy array
            bmp_info = save_bitmap.GetInfo()
            bmp_str = save_bitmap.GetBitmapBits(True)
            
            pil_image = Image.frombuffer(
                'RGB',
                (bmp_info['bmWidth'], bmp_info['bmHeight']),
                bmp_str, 'raw', 'BGRX', 0, 1
            )
            
            # Convert to numpy array (BGR format for OpenCV compatibility)
            screenshot = np.array(pil_image)
            screenshot = screenshot[:, :, :3]  # Remove alpha channel
            screenshot = screenshot[:, :, ::-1]  # RGB to BGR
            
            # Cleanup
            win32gui.DeleteObject(save_bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwnd_dc)
            
            self.logger.debug("Window captured successfully using direct method",
                            size=f"{width}x{height}",
                            hwnd=hwnd,
                            method="PrintWindow" if result else "BitBlt")
            
            return screenshot
            
        except Exception as e:
            self.logger.error("Direct window capture failed", 
                            error=str(e),
                            hwnd=hwnd if 'hwnd' in locals() else None)
            return None

    def capture_window_alternative(self, window_info: WindowInfo) -> Optional[np.ndarray]:
        """Alternative capture method for hardware-accelerated windows.
        
        Some games use DirectX/OpenGL rendering that blocks standard capture methods.
        This method tries alternative approaches.
        
        Args:
            window_info: Window to capture
            
        Returns:
            Screenshot as numpy array or None if capture failed
        """
        try:
            hwnd = window_info.hwnd
            
            # Method 1: Try DWM (Desktop Window Manager) composition
            self.logger.debug("Trying DWM composition capture", hwnd=hwnd)
            
            import ctypes
            from ctypes import wintypes, byref
            
            # Check if DWM composition is enabled
            dwmapi = ctypes.windll.dwmapi
            is_composition_enabled = wintypes.BOOL()
            
            if dwmapi.DwmIsCompositionEnabled(byref(is_composition_enabled)) == 0:
                if is_composition_enabled.value:
                    self.logger.debug("DWM composition is enabled", hwnd=hwnd)
                    
                    # Try to get the actual window content through DWM
                    # This is more complex and may require additional implementation
                    pass
            
            # Method 2: Try screen capture of window area (fallback)
            self.logger.debug("Trying screen area capture as fallback", hwnd=hwnd)
            
            # Get window rectangle on screen
            rect = win32gui.GetWindowRect(hwnd)
            left, top, right, bottom = rect
            width = right - left
            height = bottom - top
            
            # Ensure window is not minimized
            if not self.ensure_window_visible(window_info):
                return None
            
            # Capture the screen area where the window should be
            
            # Use PIL's ImageGrab which can sometimes capture hardware-accelerated content
            screen_capture = ImageGrab.grab(bbox=(left, top, right, bottom))
            
            # Convert to numpy array
            screenshot = np.array(screen_capture)
            
            # Convert RGB to BGR for OpenCV compatibility
            if len(screenshot.shape) == 3 and screenshot.shape[2] == 3:
                screenshot = screenshot[:, :, ::-1]
            
            self.logger.debug("Alternative capture completed",
                            size=f"{width}x{height}",
                            hwnd=hwnd,
                            method="screen_area")
            
            return screenshot
            
        except Exception as e:
            self.logger.error("Alternative capture method failed", 
                            error=str(e),
                            hwnd=hwnd if 'hwnd' in locals() else None)
            return None

    def detect_hardware_acceleration(self, screenshot: np.ndarray) -> bool:
        """Detect if a screenshot likely failed due to hardware acceleration.
        
        Args:
            screenshot: Screenshot to analyze
            
        Returns:
            True if screenshot appears to be blocked by hardware acceleration
        """
        if screenshot is None:
            return True
            
        # Check for completely black image
        if np.max(screenshot) < 10:
            return True
            
        # Check for very low variance (solid color)
        if np.var(screenshot) < 1.0:
            return True
            
        # Check for very small file size when saved
        # (This would need to be checked separately)
        
        return False

    def capture_current_window(self) -> Optional[np.ndarray]:
        """Capture screenshot of the currently tracked game window.
        
        Returns:
            Screenshot as numpy array or None if capture failed
        """
        # Try to find window if we don't have one
        if self.current_window is None:
            if self.find_game_window() is None:
                return None
        
        # Validate current window is still from bitcraft.exe
        if self.current_window and not self.validate_window_process(self.current_window):
            self.logger.warning("Current window no longer valid, searching for new window")
            self.current_window = None
            if self.find_game_window() is None:
                return None
        
        # Attempt capture
        screenshot = self.capture_window(self.current_window)
        
        # If capture failed, try to find window again
        if screenshot is None:
            self.logger.info("Retrying window capture after finding new window")
            if self.find_game_window() is not None:
                screenshot = self.capture_window(self.current_window)
        
        return screenshot

    def save_screenshot(self, screenshot: np.ndarray, output_path: Path) -> bool:
        """Save screenshot to file.
        
        Args:
            screenshot: Screenshot array (BGR format)
            output_path: Path to save the screenshot
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Convert BGR to RGB for PIL
            rgb_image = screenshot[:, :, ::-1]
            pil_image = Image.fromarray(rgb_image)
            
            # Ensure directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save with high quality
            pil_image.save(output_path, quality=95, optimize=True)
            
            self.logger.info("Screenshot saved", path=str(output_path))
            return True
            
        except Exception as e:
            self.logger.error("Failed to save screenshot", 
                            error=str(e),
                            path=str(output_path))
            return False

    def get_window_status(self) -> dict:
        """Get current window status information.
        
        Returns:
            Dictionary with window status details
        """
        if self.current_window is None:
            return {
                "window_found": False,
                "window_valid": False,
                "title": None,
                "size": None,
                "process_name": None,
                "process_id": None
            }
        
        # Check if window is still valid
        hwnd = self.current_window.hwnd
        is_valid = win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd)
        
        # Also verify the process is still running and is bitcraft.exe
        process_valid = False
        try:
            process = psutil.Process(self.current_window.process_id)
            process_valid = (process.is_running() and 
                           process.name().lower() == self.target_process_name.lower())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            process_valid = False
        
        return {
            "window_found": True,
            "window_valid": is_valid and process_valid,
            "title": self.current_window.title,
            "size": f"{self.current_window.width}x{self.current_window.height}",
            "process_name": self.current_window.process_name,
            "process_id": self.current_window.process_id,
            "hwnd": hwnd
        }

    def list_bitcraft_processes(self) -> List[dict]:
        """List all running BitCraft processes.
        
        Returns:
            List of dictionaries with process information
        """
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    if proc_info['name'] and proc_info['name'].lower() == self.target_process_name.lower():
                        processes.append({
                            'pid': proc_info['pid'],
                            'name': proc_info['name'],
                            'cmdline': ' '.join(proc_info['cmdline']) if proc_info['cmdline'] else '',
                            'running': proc.is_running()
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            self.logger.error("Error listing BitCraft processes", error=str(e))
        
        self.logger.info(f"Found {len(processes)} BitCraft processes", processes=processes)
        return processes

    def validate_window_process(self, window_info: WindowInfo) -> bool:
        """Validate that a window belongs to the correct BitCraft process.
        
        Args:
            window_info: Window information to validate
            
        Returns:
            True if window is from bitcraft.exe, False otherwise
        """
        try:
            process = psutil.Process(window_info.process_id)
            is_valid = (process.is_running() and 
                       process.name().lower() == self.target_process_name.lower())
            
            if not is_valid:
                self.logger.warning("Window process validation failed",
                                  expected_process=self.target_process_name,
                                  actual_process=process.name(),
                                  process_id=window_info.process_id)
            
            return is_valid
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            self.logger.warning("Cannot validate window process", 
                              process_id=window_info.process_id,
                              error=str(e))
            return False


def capture_game_screenshot(logger: structlog.BoundLogger) -> Optional[np.ndarray]:
    """Convenience function to capture a game screenshot.
    
    Args:
        logger: Structured logger
        
    Returns:
        Screenshot as numpy array or None if capture failed
    """
    try:
        capture = WindowCapture(logger)
        return capture.capture_current_window()
    except Exception as e:
        logger.error("Screenshot capture failed", error=str(e))
        return None
