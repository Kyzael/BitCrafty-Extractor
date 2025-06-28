"""Global hotkey handling for BitCrafty-Extractor.

This module manages global hotkeys that work even when the game is in focus,
allowing players to trigger data extraction without alt-tabbing.
"""

import time
from typing import Callable, Dict, Optional
import structlog
from dataclasses import dataclass

try:
    import pynput
    from pynput import keyboard
    HOTKEY_AVAILABLE = True
except ImportError:
    HOTKEY_AVAILABLE = False


@dataclass
class HotkeyConfig:
    """Configuration for a hotkey binding."""
    hotkey_string: str  # e.g., "ctrl+shift+e"
    callback: Callable
    description: str
    enabled: bool = True


class HotkeyHandler:
    """Global hotkey management system."""
    
    def __init__(self, logger: structlog.BoundLogger):
        """Initialize the hotkey handler.
        
        Args:
            logger: Structured logger for operation tracking
            
        Raises:
            RuntimeError: If hotkey system is not available
        """
        if not HOTKEY_AVAILABLE:
            raise RuntimeError("Hotkey system not available. Install pynput library.")
        
        self.logger = logger
        self.hotkeys: Dict[str, HotkeyConfig] = {}  # hotkey_string -> config
        self.listener: Optional[keyboard.GlobalHotKeys] = None
        self.is_monitoring = False
        
        # Track key states for debouncing
        self.last_trigger_time: Dict[str, float] = {}
        self.debounce_delay = 0.5  # seconds
        
        self.logger.info("Hotkey handler initialized")

    def register_callback(self, hotkey_string: str, callback: Callable, description: str = ""):
        """Register a callback function for a hotkey.
        
        Args:
            hotkey_string: Hotkey combination (e.g., "ctrl+shift+e")
            callback: Function to call when hotkey is triggered
            description: Human-readable description of the hotkey
        """
        # Convert to pynput format
        pynput_hotkey = self._convert_to_pynput_format(hotkey_string)
        
        config = HotkeyConfig(
            hotkey_string=pynput_hotkey,
            callback=callback,
            description=description or f"Hotkey: {hotkey_string}",
            enabled=True
        )
        
        self.hotkeys[pynput_hotkey] = config
        
        self.logger.info("Hotkey registered", 
                        hotkey=hotkey_string,
                        pynput_format=pynput_hotkey,
                        callback_name=callback.__name__,
                        description=description)
        
        # Restart listener if already monitoring
        if self.is_monitoring:
            self.stop_monitoring()
            self.start_monitoring()

    def unregister_callback(self, hotkey_string: str):
        """Unregister a callback for a hotkey.
        
        Args:
            hotkey_string: The hotkey to unregister
        """
        pynput_hotkey = self._convert_to_pynput_format(hotkey_string)
        
        if pynput_hotkey in self.hotkeys:
            del self.hotkeys[pynput_hotkey]
            if pynput_hotkey in self.last_trigger_time:
                del self.last_trigger_time[pynput_hotkey]
            
            self.logger.info("Hotkey unregistered", hotkey=hotkey_string)
            
            # Restart listener if already monitoring
            if self.is_monitoring:
                self.stop_monitoring()
                self.start_monitoring()

    def _convert_to_pynput_format(self, hotkey_string: str) -> str:
        """Convert a hotkey string to pynput format.
        
        Args:
            hotkey_string: Input hotkey (e.g., "ctrl+shift+e")
            
        Returns:
            Pynput-formatted hotkey string (e.g., "<ctrl>+<shift>+e")
        """
        # Split the hotkey string
        keys = [key.strip().lower() for key in hotkey_string.split('+')]
        
        # Map common key names to pynput format
        key_mapping = {
            'ctrl': '<ctrl>',
            'control': '<ctrl>',
            'shift': '<shift>',
            'alt': '<alt>',
            'cmd': '<cmd>',
            'win': '<cmd>',  # Windows key
            'super': '<cmd>',  # Super key (Linux)
            'tab': '<tab>',
            'space': '<space>',
            'enter': '<enter>',
            'return': '<enter>',
            'esc': '<esc>',
            'escape': '<esc>'
        }
        
        formatted_keys = []
        for key in keys:
            if key in key_mapping:
                formatted_keys.append(key_mapping[key])
            else:
                # Regular key (letter, number, etc.) - no brackets needed
                formatted_keys.append(key)
        
        return '+'.join(formatted_keys)

    def _create_hotkey_callback(self, pynput_hotkey: str):
        """Create a debounced callback function for a specific hotkey.
        
        Args:
            pynput_hotkey: The pynput-formatted hotkey string
            
        Returns:
            Callback function
        """
        def callback():
            try:
                # Check if hotkey is still registered and enabled
                if pynput_hotkey not in self.hotkeys or not self.hotkeys[pynput_hotkey].enabled:
                    return
                
                # Check debouncing
                current_time = time.time()
                if pynput_hotkey in self.last_trigger_time:
                    if current_time - self.last_trigger_time[pynput_hotkey] < self.debounce_delay:
                        self.logger.debug("Hotkey debounced", hotkey=pynput_hotkey)
                        return
                
                self.last_trigger_time[pynput_hotkey] = current_time
                
                # Log the trigger
                config = self.hotkeys[pynput_hotkey]
                self.logger.info("Hotkey triggered", 
                               hotkey=pynput_hotkey,
                               description=config.description)
                
                # Call the registered callback
                try:
                    config.callback()
                except Exception as e:
                    self.logger.error("Hotkey callback failed",
                                    hotkey=pynput_hotkey,
                                    error=str(e))
                    
            except Exception as e:
                self.logger.error("Hotkey processing failed",
                                hotkey=pynput_hotkey,
                                error=str(e))
        
        return callback

    def start_monitoring(self):
        """Start the global hotkey listener."""
        if self.is_monitoring:
            self.logger.warning("Hotkey monitoring already active")
            return
        
        if not self.hotkeys:
            self.logger.warning("No hotkeys registered")
            return
        
        try:
            # Build hotkey dictionary for pynput
            hotkey_dict = {}
            for pynput_hotkey, config in self.hotkeys.items():
                if config.enabled:
                    callback = self._create_hotkey_callback(pynput_hotkey)
                    hotkey_dict[pynput_hotkey] = callback
            
            if not hotkey_dict:
                self.logger.warning("No enabled hotkeys to register")
                return
            
            # Create and start the listener
            self.listener = keyboard.GlobalHotKeys(hotkey_dict)
            self.listener.start()
            self.is_monitoring = True
            
            self.logger.info("Hotkey monitoring started",
                           registered_hotkeys=len(hotkey_dict),
                           hotkeys=list(hotkey_dict.keys()))
            
        except Exception as e:
            self.logger.error("Failed to start hotkey monitoring", error=str(e))
            self.is_monitoring = False
            raise

    def stop_monitoring(self):
        """Stop the global hotkey listener."""
        if not self.is_monitoring:
            return
        
        try:
            if self.listener:
                self.listener.stop()
                self.listener = None
            
            self.is_monitoring = False
            self.logger.info("Hotkey monitoring stopped")
            
        except Exception as e:
            self.logger.error("Failed to stop hotkey monitoring", error=str(e))

    def is_running(self) -> bool:
        """Check if the hotkey listener is running.
        
        Returns:
            True if listener is active, False otherwise
        """
        return self.is_monitoring and self.listener is not None

    def enable_hotkey(self, hotkey_string: str):
        """Enable a specific hotkey.
        
        Args:
            hotkey_string: The hotkey to enable
        """
        pynput_hotkey = self._convert_to_pynput_format(hotkey_string)
        
        if pynput_hotkey in self.hotkeys:
            self.hotkeys[pynput_hotkey].enabled = True
            self.logger.info("Hotkey enabled", hotkey=hotkey_string)
            
            # Restart listener if active to apply changes
            if self.is_monitoring:
                self.stop_monitoring()
                self.start_monitoring()

    def disable_hotkey(self, hotkey_string: str):
        """Disable a specific hotkey.
        
        Args:
            hotkey_string: The hotkey to disable
        """
        pynput_hotkey = self._convert_to_pynput_format(hotkey_string)
        
        if pynput_hotkey in self.hotkeys:
            self.hotkeys[pynput_hotkey].enabled = False
            self.logger.info("Hotkey disabled", hotkey=hotkey_string)
            
            # Restart listener if active to apply changes
            if self.is_monitoring:
                self.stop_monitoring()
                self.start_monitoring()

    def get_hotkey_info(self) -> Dict[str, Dict]:
        """Get information about all configured hotkeys.
        
        Returns:
            Dictionary with hotkey information
        """
        info = {}
        for pynput_hotkey, config in self.hotkeys.items():
            info[pynput_hotkey] = {
                "hotkey_string": pynput_hotkey,
                "description": config.description,
                "enabled": config.enabled,
                "callback_name": config.callback.__name__ if config.callback else None
            }
        
        return info

    def get_status(self) -> Dict[str, any]:
        """Get current status of the hotkey system.
        
        Returns:
            Status information dictionary
        """
        return {
            "is_monitoring": self.is_monitoring,
            "total_hotkeys": len(self.hotkeys),
            "enabled_hotkeys": sum(1 for h in self.hotkeys.values() if h.enabled),
            "debounce_delay": self.debounce_delay,
            "available": HOTKEY_AVAILABLE
        }

    # Compatibility methods for the main application
    def start(self):
        """Compatibility method - alias for start_monitoring."""
        self.start_monitoring()

    def stop(self):
        """Compatibility method - alias for stop_monitoring."""
        self.stop_monitoring()
