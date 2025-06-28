#!/usr/bin/env python3
"""
Test script for hotkey system validation.

This script tests the global hotkey functionality to ensure it works
properly even when other applications (like BitCraft) are in focus.
"""

import sys
import time
import threading
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import structlog
    from bitcrafty_extractor.capture.hotkey_handler import HotkeyHandler, HOTKEY_AVAILABLE
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project directory")
    print("and have installed dependencies with: pip install -r requirements.txt")
    sys.exit(1)

def setup_logging():
    """Setup basic logging for testing."""
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger()

def test_queue_screenshot():
    """Callback for queue screenshot hotkey."""
    print("🖼️  QUEUE SCREENSHOT triggered!")
    print("   (In real app: this would capture and queue a screenshot)")

def test_analyze_queue():
    """Callback for analyze queue hotkey."""
    print("🧠 ANALYZE QUEUE triggered!")
    print("   (In real app: this would send queue to AI for analysis)")

def test_toggle_monitoring():
    """Callback for toggle monitoring hotkey."""
    print("⏸️  TOGGLE MONITORING triggered!")
    print("   (In real app: this would pause/resume the extraction system)")

def main():
    """Test the hotkey system."""
    print("BitCrafty Extractor - Hotkey System Test")
    print("=" * 50)
    
    if not HOTKEY_AVAILABLE:
        print("❌ ERROR: Hotkey system not available!")
        print("Install pynput with: pip install pynput")
        sys.exit(1)
    
    print("✅ Hotkey system available")
    
    # Setup logging
    logger = setup_logging()
    
    try:
        # Create hotkey handler
        print("\n📋 Creating hotkey handler...")
        handler = HotkeyHandler(logger)
        
        # Register test hotkeys
        print("\n🔑 Registering test hotkeys...")
        handler.register_callback(
            "ctrl+shift+e", 
            test_queue_screenshot, 
            "Queue screenshot for analysis"
        )
        handler.register_callback(
            "ctrl+shift+x", 
            test_analyze_queue,
            "Analyze screenshot queue with AI"
        )
        handler.register_callback(
            "ctrl+shift+p", 
            test_toggle_monitoring,
            "Toggle monitoring pause/resume"
        )
        
        # Show registered hotkeys
        hotkey_info = handler.get_hotkey_info()
        print(f"\n📝 Registered {len(hotkey_info)} hotkeys:")
        for hotkey, info in hotkey_info.items():
            status = "✅ Enabled" if info['enabled'] else "❌ Disabled"
            print(f"   {hotkey}: {info['description']} [{status}]")
        
        # Start monitoring
        print("\n🚀 Starting hotkey monitoring...")
        handler.start_monitoring()
        
        status = handler.get_status()
        print(f"   Monitoring: {'✅ Active' if status['is_monitoring'] else '❌ Inactive'}")
        print(f"   Total hotkeys: {status['total_hotkeys']}")
        print(f"   Enabled hotkeys: {status['enabled_hotkeys']}")
        print(f"   Debounce delay: {status['debounce_delay']}s")
        
        # Test instructions
        print("\n" + "="*50)
        print("🎮 HOTKEY TEST ACTIVE!")
        print("="*50)
        print("Test the following hotkeys (they work globally):")
        print("   Ctrl+Shift+E  -> Queue Screenshot")
        print("   Ctrl+Shift+X  -> Analyze Queue") 
        print("   Ctrl+Shift+P  -> Toggle Monitoring")
        print()
        print("💡 Tips:")
        print("   - These work even when other apps have focus")
        print("   - Try switching to another window and testing")
        print("   - Each hotkey has a 0.5s debounce delay")
        print()
        print("Press Ctrl+C to stop the test...")
        print("="*50)
        
        # Keep the test running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n⏹️  Stopping hotkey test...")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.error("Hotkey test failed", error=str(e))
        sys.exit(1)
    
    finally:
        # Clean shutdown
        try:
            if 'handler' in locals():
                print("🛑 Stopping hotkey monitoring...")
                handler.stop_monitoring()
                print("✅ Hotkey monitoring stopped")
        except Exception as e:
            print(f"⚠️  Warning during shutdown: {e}")
    
    print("\n✅ Hotkey test completed successfully!")

if __name__ == "__main__":
    main()
