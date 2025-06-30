"""Audio feedback system for BitCrafty-Extractor.

Provides audio notifications for queue operations to enhance user experience.
"""

from .audio_manager import AudioManager, AudioEvent

__all__ = ["AudioManager", "AudioEvent"]
