"""Global hotkey handling for BitCrafty-Extractor.

This module manages global hotkeys that work even when the game is in focus,
allowing players to trigger data extraction without alt-tabbing.
"""

import time
from typing import Callable, Dict, Set, Optional
import structlog
from dataclasses import dataclass
from enum import Enum

try:
    import pynput
    from pynput import keyboard
    HOTKEY_AVAILABLE = True
except ImportError:
    HOTKEY_AVAILABLE = False


class HotkeyAction(Enum):
    """Available hotkey actions."""
    QUEUE_SCREENSHOT = "queue_screenshot"
    ANALYZE_QUEUE = "analyze_queue" 
    TOGGLE_PAUSE = "toggle_pause"
    SHOW_STATUS = "show_status"


@dataclass
class HotkeyConfig:
    """Configuration for a hotkey binding."""
    action: HotkeyAction
    keys: Set[str]  # e.g., {'ctrl', 'shift', 'e'}
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
        self.hotkeys: Dict[HotkeyAction, HotkeyConfig] = {}
        self.callbacks: Dict[HotkeyAction, Callable] = {}
        self.listener: Optional[keyboard.GlobalHotKeys] = None
        self.is_active = False
        
        # Track key states for debouncing
        self.last_trigger_time: Dict[HotkeyAction, float] = {}
        self.debounce_delay = 1.0  # seconds
        
        # Default hotkey configurations
        self._setup_default_hotkeys()
        
        self.logger.info("Hotkey handler initialized")

    def _setup_default_hotkeys(self):
        """Set up default hotkey configurations."""
        self.hotkeys = {
            HotkeyAction.EXTRACT_AUTO: HotkeyConfig(
                action=HotkeyAction.EXTRACT_AUTO,
                keys={'ctrl', 'shift', 'e'},
                description="Auto-detect and extract item/craft data",
                enabled=True
            ),
            HotkeyAction.EXTRACT_ITEM: HotkeyConfig(
                action=HotkeyAction.EXTRACT_ITEM,
                keys={'ctrl', 'shift', 'i'},
                description="Force extract as item tooltip",
                enabled=True
            ),
            HotkeyAction.EXTRACT_CRAFT: HotkeyConfig(
                action=HotkeyAction.EXTRACT_CRAFT,
                keys={'ctrl', 'shift', 'c'},
                description="Force extract as craft recipe",
                enabled=True
            ),
            HotkeyAction.TOGGLE_PAUSE: HotkeyConfig(
                action=HotkeyAction.TOGGLE_PAUSE,
                keys={'ctrl', 'shift', 'p'},
                description="Pause/resume extraction system",
                enabled=True
            ),
            HotkeyAction.SHOW_STATUS: HotkeyConfig(
                action=HotkeyAction.SHOW_STATUS,
                keys={'ctrl', 'shift', 's'},
                description="Show system status",
                enabled=True
            )
        }

    def register_callback(self, action: HotkeyAction, callback: Callable):
        """Register a callback function for a hotkey action.
        
        Args:
            action: The hotkey action to register
            callback: Function to call when hotkey is triggered
        """
        self.callbacks[action] = callback
        self.logger.info("Callback registered", 
                        action=action.value,
                        callback_name=callback.__name__)

    def unregister_callback(self, action: HotkeyAction):
        """Unregister a callback for a hotkey action.
        
        Args:
            action: The hotkey action to unregister
        """
        if action in self.callbacks:
            del self.callbacks[action]
            self.logger.info("Callback unregistered", action=action.value)

    def _format_hotkey_string(self, keys: Set[str]) -> str:
        """Format a set of keys into a hotkey string for pynput.
        
        Args:
            keys: Set of key names
            
        Returns:
            Formatted hotkey string (e.g., '<ctrl>+<shift>+e')
        """
        # Map common key names to pynput format
        key_mapping = {
            'ctrl': '<ctrl>',
            'shift': '<shift>',
            'alt': '<alt>',
            'cmd': '<cmd>',
            'win': '<cmd>',  # Windows key
            'super': '<cmd>'  # Super key (Linux)
        }
        
        formatted_keys = []
        for key in sorted(keys):
            if key in key_mapping:
                formatted_keys.append(key_mapping[key])
            else:
                # Regular key (letter, number, etc.)
                formatted_keys.append(key)
        
        return '+'.join(formatted_keys)

    def _create_hotkey_callback(self, action: HotkeyAction):
        """Create a callback function for a specific action.
        
        Args:
            action: The action to create a callback for
            
        Returns:
            Callback function
        """
        def callback():
            try:
                # Check if action is enabled
                if action not in self.hotkeys or not self.hotkeys[action].enabled:
                    return
                
                # Check debouncing
                current_time = time.time()
                if action in self.last_trigger_time:
                    if current_time - self.last_trigger_time[action] < self.debounce_delay:
                        self.logger.debug("Hotkey debounced", action=action.value)
                        return
                
                self.last_trigger_time[action] = current_time
                
                # Log the trigger
                self.logger.info("Hotkey triggered", 
                               action=action.value,
                               keys=self.hotkeys[action].keys)
                
                # Call registered callback if available
                if action in self.callbacks:
                    try:
                        self.callbacks[action]()
                    except Exception as e:
                        self.logger.error("Hotkey callback failed",
                                        action=action.value,
                                        error=str(e))
                else:
                    self.logger.warning("No callback registered for hotkey",
                                      action=action.value)
                    
            except Exception as e:
                self.logger.error("Hotkey processing failed",
                                action=action.value,
                                error=str(e))
        
        return callback

    def start(self):
        """Start the global hotkey listener."""
        if self.is_active:
            self.logger.warning("Hotkey handler already active")
            return
        
        try:
            # Build hotkey dictionary for pynput
            hotkey_dict = {}
            for action, config in self.hotkeys.items():
                if config.enabled:
                    hotkey_string = self._format_hotkey_string(config.keys)
                    callback = self._create_hotkey_callback(action)
                    hotkey_dict[hotkey_string] = callback
            
            if not hotkey_dict:
                self.logger.warning("No enabled hotkeys to register")
                return
            
            # Create and start the listener
            self.listener = keyboard.GlobalHotKeys(hotkey_dict)
            self.listener.start()
            self.is_active = True
            
            self.logger.info("Hotkey listener started",
                           registered_hotkeys=len(hotkey_dict),
                           hotkeys=list(hotkey_dict.keys()))
            
        except Exception as e:
            self.logger.error("Failed to start hotkey listener", error=str(e))
            self.is_active = False

    def stop(self):
        """Stop the global hotkey listener."""
        if not self.is_active:
            return
        
        try:
            if self.listener:
                self.listener.stop()
                self.listener = None
            
            self.is_active = False
            self.logger.info("Hotkey listener stopped")
            
        except Exception as e:
            self.logger.error("Failed to stop hotkey listener", error=str(e))

    def is_running(self) -> bool:
        """Check if the hotkey listener is running.
        
        Returns:
            True if listener is active, False otherwise
        """
        return self.is_active and self.listener is not None

    def update_hotkey(self, action: HotkeyAction, keys: Set[str], enabled: bool = True):
        """Update a hotkey configuration.
        
        Args:
            action: The action to update
            keys: New set of keys for the hotkey
            enabled: Whether the hotkey should be enabled
        """
        if action in self.hotkeys:
            old_keys = self.hotkeys[action].keys
            self.hotkeys[action].keys = keys
            self.hotkeys[action].enabled = enabled
            
            self.logger.info("Hotkey updated",
                           action=action.value,
                           old_keys=old_keys,
                           new_keys=keys,
                           enabled=enabled)
            
            # Restart listener if active to apply changes
            if self.is_active:
                self.stop()
                self.start()
        else:
            self.logger.warning("Attempted to update unknown hotkey", action=action.value)

    def enable_hotkey(self, action: HotkeyAction):
        """Enable a specific hotkey.
        
        Args:
            action: The action to enable
        """
        if action in self.hotkeys:
            self.hotkeys[action].enabled = True
            self.logger.info("Hotkey enabled", action=action.value)
            
            # Restart listener if active to apply changes
            if self.is_active:
                self.stop()
                self.start()

    def disable_hotkey(self, action: HotkeyAction):
        """Disable a specific hotkey.
        
        Args:
            action: The action to disable
        """
        if action in self.hotkeys:
            self.hotkeys[action].enabled = False
            self.logger.info("Hotkey disabled", action=action.value)
            
            # Restart listener if active to apply changes
            if self.is_active:
                self.stop()
                self.start()

    def get_hotkey_info(self) -> Dict[str, Dict]:
        """Get information about all configured hotkeys.
        
        Returns:
            Dictionary with hotkey information
        """
        info = {}
        for action, config in self.hotkeys.items():
            hotkey_string = self._format_hotkey_string(config.keys)
            info[action.value] = {
                "keys": list(config.keys),
                "hotkey_string": hotkey_string,
                "description": config.description,
                "enabled": config.enabled,
                "has_callback": action in self.callbacks
            }
        
        return info

    def get_status(self) -> Dict[str, any]:
        """Get current status of the hotkey system.
        
        Returns:
            Status information dictionary
        """
        return {
            "is_active": self.is_active,
            "total_hotkeys": len(self.hotkeys),
            "enabled_hotkeys": sum(1 for h in self.hotkeys.values() if h.enabled),
            "registered_callbacks": len(self.callbacks),
            "debounce_delay": self.debounce_delay
        }
