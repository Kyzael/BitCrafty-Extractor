"""Main application entry point for BitCrafty Extractor."""
import sys
import time
import argparse
from pathlib import Path
from typing import Optional
import structlog

from bitcrafty_extractor import BitcraftyExtractorError
from bitcrafty_extractor.utils.logging_utils import setup_logging
from bitcrafty_extractor.core.config_manager import ConfigManager
from bitcrafty_extractor.core.window_monitor import WindowMonitor
from bitcrafty_extractor.core.ocr_engine import OCREngine


class BitcraftyExtractor:
    """Main application class for the BitCrafty Extractor."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the extractor application.
        
        Args:
            config_path: Optional path to configuration file
        """
        # Setup logging first
        self.logger = setup_logging()
        
        try:
            # Load configuration
            self.config_manager = ConfigManager(config_path, self.logger)
            self.config = self.config_manager.config
            
            # Update logging level if specified in config
            if self.config.debug:
                self.logger = setup_logging(level="DEBUG")
            
            # Initialize core components
            self.window_monitor = WindowMonitor(self.config.window, self.logger)
            self.ocr_engine = OCREngine(self.config.ocr, self.logger)
            
            self.logger.info("BitCrafty Extractor initialized successfully",
                           version=self.config.version,
                           debug=self.config.debug)
            
        except Exception as e:
            self.logger.error("Failed to initialize extractor", error=str(e))
            raise
    
    def run_passive_monitoring(self, duration_seconds: Optional[float] = None) -> None:
        """Run passive monitoring mode.
        
        Args:
            duration_seconds: Optional duration to run (None for indefinite)
        """
        self.logger.info("Starting passive monitoring mode", 
                        duration=duration_seconds,
                        target_window=self.config.window.target_name)
        
        start_time = time.time()
        screenshot_count = 0
        
        try:
            while True:
                # Check duration limit
                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    self.logger.info("Duration limit reached, stopping monitoring")
                    break
                
                # Capture screenshot
                screenshot = self.window_monitor.capture_window()
                
                if screenshot is not None:
                    screenshot_count += 1
                    self.logger.debug("Screenshot captured", 
                                    count=screenshot_count,
                                    shape=screenshot.shape)
                    
                    # Basic OCR test on a small region (for now just log results)
                    if screenshot_count % 10 == 0:  # Test OCR every 10th screenshot
                        self._test_ocr_extraction(screenshot)
                else:
                    # Window not available, wait before retrying
                    self.logger.debug("No screenshot available, waiting for window")
                
                # Wait before next capture
                time.sleep(self.config.window.capture_interval_ms / 1000.0)
                
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user")
        except Exception as e:
            self.logger.error("Error during monitoring", error=str(e))
            raise
        finally:
            self.logger.info("Passive monitoring completed", 
                           screenshots_captured=screenshot_count,
                           duration=time.time() - start_time)
    
    def _test_ocr_extraction(self, screenshot) -> None:
        """Test OCR extraction on a screenshot (Phase 1 testing).
        
        Args:
            screenshot: Screenshot to test OCR on
        """
        try:
            # Test OCR on center region of screenshot
            height, width = screenshot.shape[:2]
            center_region = (
                width // 4,
                height // 4,
                width // 2,
                height // 2
            )
            
            results = self.ocr_engine.extract_text(screenshot, center_region)
            
            if results:
                self.logger.info("OCR test results", 
                               text_count=len(results),
                               sample_text=[r.text for r in results[:3]])  # Show first 3 results
            else:
                self.logger.debug("No text detected in OCR test")
                
        except Exception as e:
            self.logger.warning("OCR test failed", error=str(e))
    
    def test_components(self) -> bool:
        """Test all core components.
        
        Returns:
            True if all tests pass, False otherwise
        """
        self.logger.info("Testing core components...")
        
        try:
            # Test window detection
            self.logger.info("Testing window detection...")
            window_found = self.window_monitor.find_window()
            if window_found:
                self.logger.info("✓ Window detection successful")
                window_info = self.window_monitor.get_window_info()
                if window_info:
                    title, rect = window_info
                    self.logger.info("Window details", title=title, rect=rect)
            else:
                self.logger.warning("✗ Target window not found")
            
            # Test screenshot capture
            if window_found:
                self.logger.info("Testing screenshot capture...")
                screenshot = self.window_monitor.capture_window()
                if screenshot is not None:
                    self.logger.info("✓ Screenshot capture successful", shape=screenshot.shape)
                    
                    # Test OCR
                    self.logger.info("Testing OCR extraction...")
                    results = self.ocr_engine.extract_text(screenshot)
                    self.logger.info("✓ OCR test completed", text_blocks=len(results))
                    
                    if results:
                        self.logger.info("Sample OCR results", 
                                       texts=[r.text for r in results[:5]])
                else:
                    self.logger.error("✗ Screenshot capture failed")
                    return False
            
            self.logger.info("✓ All component tests completed successfully")
            return True
            
        except Exception as e:
            self.logger.error("Component test failed", error=str(e))
            return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="BitCrafty Extractor - Real-time game data extraction")
    parser.add_argument("--config", type=Path, help="Path to configuration file")
    parser.add_argument("--mode", choices=["test", "passive"], default="test", 
                       help="Operation mode")
    parser.add_argument("--duration", type=float, help="Duration in seconds (for passive mode)")
    
    args = parser.parse_args()
    
    try:
        extractor = BitcraftyExtractor(args.config)
        
        if args.mode == "test":
            success = extractor.test_components()
            return 0 if success else 1
        elif args.mode == "passive":
            extractor.run_passive_monitoring(args.duration)
            return 0
            
    except BitcraftyExtractorError as e:
        print(f"Extractor error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped by user", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
