"""Audio feedback manager for BitCrafty-Extractor queue operations.

Provides audio notifications for screenshot capture, analysis start, and completion.
Uses text-to-speech for voice notifications and system sounds for other events.
"""

import threading
import time
from enum import Enum
from typing import Optional, Dict, Any
import structlog

# Audio dependencies (with fallbacks)
try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False


class AudioEvent(Enum):
    """Audio event types for queue operations."""
    SCREENSHOT_TAKEN = "screenshot_taken"
    ANALYSIS_START = "analysis_start"
    ANALYSIS_COMPLETE = "analysis_complete"
    ERROR_OCCURRED = "error_occurred"


class AudioManager:
    """Manages audio feedback for queue operations."""
    
    def __init__(self, config_manager=None, logger: Optional[structlog.BoundLogger] = None):
        """Initialize audio manager with configuration.
        
        Args:
            config_manager: Configuration manager instance
            logger: Structured logger instance
        """
        self.config_manager = config_manager
        self.logger = logger or structlog.get_logger(__name__)
        self.enabled = True
        self.tts_engine = None
        self.tts_lock = threading.Lock()  # Prevent concurrent TTS usage
        
        # Audio settings (will be loaded from config)
        self.settings = {
            "enabled": True,
            "volume": 0.7,
            "voice_enabled": True,
            "voice_rate": 150,
            "voice_volume": 0.8,
            "sound_effects_enabled": True,
            "sound_volume": 0.6
        }
        
        # Load configuration
        self._load_config()
        
        # Initialize audio systems
        self._initialize_audio()
        
        self.logger.info("Audio manager initialized",
                        tts_available=TTS_AVAILABLE,
                        winsound_available=WINSOUND_AVAILABLE,
                        enabled=self.enabled)
    
    def _load_config(self):
        """Load audio configuration from config manager."""
        if not self.config_manager or not hasattr(self.config_manager, 'config'):
            return
            
        try:
            # Get audio config from YAML (will add this to default.yaml)
            audio_config = getattr(self.config_manager.config, 'audio', {})
            if audio_config:
                self.settings.update(audio_config)
                self.enabled = self.settings.get('enabled', True)
                
        except Exception as e:
            self.logger.warning("Could not load audio config", error=str(e))
    
    def _initialize_audio(self):
        """Initialize audio systems (TTS and sound effects)."""
        if not self.enabled:
            return
            
        # Initialize Text-to-Speech
        if TTS_AVAILABLE and self.settings.get('voice_enabled', True):
            try:
                self.tts_engine = pyttsx3.init()
                
                # Configure TTS settings
                self.tts_engine.setProperty('rate', self.settings.get('voice_rate', 150))
                self.tts_engine.setProperty('volume', self.settings.get('voice_volume', 0.8))
                
                # Try to set a voice (prefer female voice for BitCrafty)
                voices = self.tts_engine.getProperty('voices')
                if voices:
                    # Look for a female voice, fallback to first available
                    for voice in voices:
                        if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                            self.tts_engine.setProperty('voice', voice.id)
                            break
                    else:
                        # Use first available voice
                        self.tts_engine.setProperty('voice', voices[0].id)
                
                self.logger.info("TTS engine initialized successfully")
                
            except Exception as e:
                self.logger.warning("Could not initialize TTS engine", error=str(e))
                self.tts_engine = None
    
    def _reinitialize_tts(self):
        """Reinitialize TTS engine to recover from errors."""
        try:
            if self.tts_engine:
                self.tts_engine.stop()
                del self.tts_engine
                time.sleep(0.2)  # Give time for cleanup
            
            self.tts_engine = pyttsx3.init()
            
            # Reconfigure TTS settings
            self.tts_engine.setProperty('rate', self.settings.get('voice_rate', 150))
            self.tts_engine.setProperty('volume', self.settings.get('voice_volume', 0.8))
            
            # Restore voice preference
            voices = self.tts_engine.getProperty('voices')
            if voices:
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        break
                else:
                    self.tts_engine.setProperty('voice', voices[0].id)
            
            self.logger.info("TTS engine reinitialized successfully")
            
        except Exception as e:
            self.logger.error("TTS reinitialization failed", error=str(e))
            self.tts_engine = None
    
    def play_audio_feedback(self, event: AudioEvent, **kwargs):
        """Play audio feedback for the specified event.
        
        Args:
            event: Type of audio event
            **kwargs: Additional context for the event
        """
        if not self.enabled:
            return
            
        # Run audio in background thread to avoid blocking
        threading.Thread(
            target=self._play_audio_background,
            args=(event, kwargs),
            daemon=True
        ).start()
    
    def _play_audio_background(self, event: AudioEvent, context: Dict[str, Any]):
        """Play audio feedback in background thread.
        
        Args:
            event: Type of audio event
            context: Additional context for the event
        """
        try:
            if event == AudioEvent.SCREENSHOT_TAKEN:
                self._play_screenshot_sound()
                
            elif event == AudioEvent.ANALYSIS_START:
                screenshot_count = context.get('screenshot_count', 0)
                self._play_analysis_start_voice(screenshot_count)
                
            elif event == AudioEvent.ANALYSIS_COMPLETE:
                success = context.get('success', True)
                items_count = context.get('items_count', 0)
                crafts_count = context.get('crafts_count', 0)
                self._play_analysis_complete_sound(success, items_count, crafts_count)
                
            elif event == AudioEvent.ERROR_OCCURRED:
                error_type = context.get('error_type', 'unknown')
                self._play_error_sound(error_type)
                
        except Exception as e:
            self.logger.error("Audio feedback failed", event=event.value, error=str(e))
    
    def _play_screenshot_sound(self):
        """Play camera shutter sound for screenshot capture."""
        try:
            if WINSOUND_AVAILABLE:
                # High-pitched quick beep (like camera shutter)
                winsound.Beep(800, 100)  # 800Hz for 100ms
                
        except Exception as e:
            self.logger.debug("Screenshot sound failed", error=str(e))
    
    def _play_analysis_start_voice(self, screenshot_count: int):
        """Play voice notification for analysis start.
        
        Args:
            screenshot_count: Number of screenshots being analyzed
        """
        if not TTS_AVAILABLE or not self.settings.get('voice_enabled', True):
            # Fallback to system sound
            self._play_system_sound("analysis_start")
            return
            
        try:
            # Create voice message - always say "Analyzing" regardless of count
            message = "Analyzing"
            
            self.logger.debug("Playing TTS message", message=message, screenshot_count=screenshot_count)
            
            # Use lock to prevent concurrent TTS usage and reinitialize engine each time
            with self.tts_lock:
                try:
                    # Stop and recreate engine to avoid state conflicts
                    if hasattr(self, '_temp_tts_engine'):
                        try:
                            self._temp_tts_engine.stop()
                            del self._temp_tts_engine
                        except:
                            pass
                    
                    # Wait a moment for cleanup
                    time.sleep(0.1)
                    
                    # Create completely fresh engine instance
                    self._temp_tts_engine = pyttsx3.init(driverName='sapi5')  # Force SAPI5 driver
                    
                    # Configure the engine
                    self._temp_tts_engine.setProperty('rate', self.settings.get('voice_rate', 150))
                    self._temp_tts_engine.setProperty('volume', self.settings.get('voice_volume', 0.8))
                    
                    # Set voice preference
                    voices = self._temp_tts_engine.getProperty('voices')
                    if voices:
                        # Look for Zira (female voice)
                        for voice in voices:
                            if 'zira' in voice.name.lower():
                                self._temp_tts_engine.setProperty('voice', voice.id)
                                break
                        else:
                            # Use first available voice
                            self._temp_tts_engine.setProperty('voice', voices[0].id)
                    
                    # Play voice message
                    self._temp_tts_engine.say(message)
                    self._temp_tts_engine.runAndWait()
                    
                    # Immediate cleanup
                    self._temp_tts_engine.stop()
                    del self._temp_tts_engine
                    
                except Exception as tts_error:
                    self.logger.debug("TTS error during playback", error=str(tts_error))
                    # Clean up on error
                    if hasattr(self, '_temp_tts_engine'):
                        try:
                            self._temp_tts_engine.stop()
                            del self._temp_tts_engine
                        except:
                            pass
                    # Fallback to system sound
                    self._play_system_sound("analysis_start")
            
            self.logger.debug("TTS message completed", message=message)
            
        except Exception as e:
            self.logger.error("Analysis start voice failed", error=str(e))
            # Fallback to system sound
            self._play_system_sound("analysis_start")
    
    def _play_analysis_complete_sound(self, success: bool, items_count: int, crafts_count: int):
        """Play completion sound for analysis finish.
        
        Args:
            success: Whether analysis was successful
            items_count: Number of items found
            crafts_count: Number of crafts found
        """
        try:
            if success:
                # Two quick medium tones for success
                if WINSOUND_AVAILABLE:
                    winsound.Beep(600, 200)  # Medium tone
                    time.sleep(0.05)
                    winsound.Beep(600, 200)  # Same medium tone
            else:
                # Error sound
                self._play_error_sound("analysis_failed")
                
        except Exception as e:
            self.logger.debug("Analysis complete sound failed", error=str(e))
    
    def _play_error_sound(self, error_type: str):
        """Play error notification sound.
        
        Args:
            error_type: Type of error that occurred
        """
        try:
            if WINSOUND_AVAILABLE:
                # Use custom beep for error sound (more reliable than Windows system sounds)
                winsound.Beep(300, 500)  # Low tone for error
                    
        except Exception as e:
            self.logger.debug("Error sound failed", error=str(e))
    
    def _play_system_sound(self, sound_type: str):
        """Play system sound as fallback using custom beeps.
        
        Args:
            sound_type: Type of system sound to play
        """
        if not WINSOUND_AVAILABLE:
            return
            
        try:
            # Use custom beeps since Windows system sounds are often muted
            sound_map = {
                "analysis_start": (500, 150),    # Medium-low tone for analysis start
                "success": (600, 200),           # Medium tone for success
                "error": (300, 500)              # Low tone for error
            }
            
            frequency, duration = sound_map.get(sound_type, (600, 200))
            winsound.Beep(frequency, duration)
            
        except Exception as e:
            self.logger.debug("System sound failed", sound_type=sound_type, error=str(e))
    
    def set_enabled(self, enabled: bool):
        """Enable or disable audio feedback.
        
        Args:
            enabled: Whether to enable audio feedback
        """
        self.enabled = enabled
        self.logger.info("Audio feedback toggled", enabled=enabled)
    
    def set_volume(self, volume: float):
        """Set overall audio volume.
        
        Args:
            volume: Volume level (0.0 to 1.0)
        """
        volume = max(0.0, min(1.0, volume))  # Clamp to valid range
        self.settings['volume'] = volume
        
        # Update TTS volume
        if self.tts_engine:
            try:
                self.tts_engine.setProperty('volume', volume * self.settings.get('voice_volume', 0.8))
            except Exception as e:
                self.logger.debug("Could not set TTS volume", error=str(e))
        
        self.logger.info("Audio volume updated", volume=volume)
    
    def test_audio(self):
        """Test audio system with sample sounds."""
        self.logger.info("Testing audio system...")
        
        # Test screenshot sound
        self.play_audio_feedback(AudioEvent.SCREENSHOT_TAKEN)
        time.sleep(1)
        
        # Test analysis start voice
        self.play_audio_feedback(AudioEvent.ANALYSIS_START, screenshot_count=3)
        time.sleep(3)
        
        # Test completion sound
        self.play_audio_feedback(AudioEvent.ANALYSIS_COMPLETE, 
                               success=True, items_count=5, crafts_count=2)
        time.sleep(2)
        
        self.logger.info("Audio test completed")
    
    def cleanup(self):
        """Clean up audio resources."""
        if self.tts_engine:
            try:
                self.tts_engine.stop()
            except Exception as e:
                self.logger.debug("TTS cleanup failed", error=str(e))
        
        self.logger.info("Audio manager cleanup completed")
