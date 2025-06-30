#!/usr/bin/env python3
"""
Comprehensive test for all BitCrafty-Extractor audio feedback.
"""

import sys
import time
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from bitcrafty_extractor.config.config_manager import ConfigManager
from bitcrafty_extractor.audio.audio_manager import AudioManager, AudioEvent
import structlog

def test_audio_system():
    """Complete test of all audio feedback features."""
    print("🎉 BitCrafty-Extractor Audio Feedback Test")
    print("=" * 45)
    
    # Initialize logger
    structlog.configure(
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    logger = structlog.get_logger(__name__)
    
    # Initialize config manager and audio manager
    config_manager = ConfigManager()
    audio_manager = AudioManager(config_manager, logger)
    
    if not audio_manager.enabled:
        print("❌ Audio is disabled")
        return
    
    print("✅ Audio manager initialized successfully!")
    print()
    
    # Test 1: Screenshot Sound
    print("📸 1. Screenshot captured sound...")
    audio_manager.play_audio_feedback(AudioEvent.SCREENSHOT_TAKEN)
    time.sleep(2)
    
    # Test 2: Multiple screenshots analysis
    print("🤖 2. Analysis start: 3 screenshots...")
    audio_manager.play_audio_feedback(
        AudioEvent.ANALYSIS_START, 
        screenshot_count=3
    )
    time.sleep(3)
    
    # Test 3: Single screenshot analysis  
    print("🤖 3. Analysis start: 1 screenshot...")
    audio_manager.play_audio_feedback(
        AudioEvent.ANALYSIS_START, 
        screenshot_count=1
    )
    time.sleep(3)
    
    # Test 4: Successful analysis completion
    print("✅ 4. Analysis completed successfully...")
    audio_manager.play_audio_feedback(
        AudioEvent.ANALYSIS_COMPLETE,
        success=True,
        items_count=5,
        crafts_count=2
    )
    time.sleep(3)
    
    # Test 5: Error sound
    print("❌ 5. Error occurred...")
    audio_manager.play_audio_feedback(
        AudioEvent.ERROR_OCCURRED,
        error_type="test_error"
    )
    time.sleep(2)
    
    print()
    print("🎉 Audio feedback test completed!")
    print()
    print("🎯 Expected sounds:")
    print("   1. 📸 High-pitched beep (camera shutter)")
    print("   2. 🗣️ Voice: 'Analyzing'")
    print("   3. 🗣️ Voice: 'Analyzing'")
    print("   4. 🎵 Two quick medium tones (success)")
    print("   5. ⚠️ Low-pitched error beep")
    print()
    print("💡 The audio feedback system is ready for use!")
    
    # Cleanup
    audio_manager.cleanup()

if __name__ == "__main__":
    try:
        test_audio_system()
    except KeyboardInterrupt:
        print("\n👋 Test interrupted")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
