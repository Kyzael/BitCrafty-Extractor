"""Real-time BitCrafty data extractor with AI vision analysis.

This is the main application that provides a hotkey-triggered system for 
extracting game data from Bitcraft using AI vision models.
"""

import asyncio
import json
import sys
import argparse
from pathlib import Path
from typing import Optional, Dict, Any
import threading
import time
from dataclasses import dataclass
from datetime import datetime

try:
    import structlog
    from PyQt6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, 
                                QWidget, QVBoxLayout, QLabel, QPushButton,
                                QTextEdit, QComboBox, QSpinBox, QCheckBox,
                                QMessageBox, QProgressBar, QTabWidget,
                                QFormLayout, QLineEdit, QGroupBox)
    from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt
    from PyQt6.QtGui import QIcon, QPixmap, QFont
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print("PyQt6 not available. Install with: pip install PyQt6")

# Local imports
try:
    from bitcrafty_extractor.capture.window_capture import WindowCapture
    from bitcrafty_extractor.capture.hotkey_handler import HotkeyHandler
    from bitcrafty_extractor.ai_analysis.vision_client import VisionClient, ImageData, AIProvider
    from bitcrafty_extractor.ai_analysis.prompts import PromptBuilder, ExtractionType
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    COMPONENTS_AVAILABLE = False
    print(f"Local components not available: {e}")
    # Define stubs to prevent NameError - must be before class definitions
    class ExtractionType:
        QUEUE_ANALYSIS = "queue_analysis"
        value = "queue_analysis"
    
    class ImageData:
        pass
    
    class AIProvider:
        pass
    
    class VisionClient:
        def __init__(self, *args, **kwargs):
            pass
        
        async def analyze_image(self, *args, **kwargs):
            return type('MockResponse', (), {'success': False, 'data': None, 'cost_estimate': 0, 'confidence': 0, 'error_message': 'Components not available'})()
        
        async def analyze_images(self, *args, **kwargs):
            return type('MockResponse', (), {'success': False, 'data': None, 'cost_estimate': 0, 'confidence': 0, 'error_message': 'Components not available'})()
    
    class PromptBuilder:
        def __init__(self, *args, **kwargs):
            pass
            
        def get_prompt(self, extraction_type):
            return "Mock prompt"
    
    class WindowCapture:
        def __init__(self, *args, **kwargs):
            pass
    
    class HotkeyHandler:
        def __init__(self, *args, **kwargs):
            pass


@dataclass
class ExtractionResult:
    """Result of an AI extraction operation."""
    success: bool
    data: Optional[Dict[str, Any]]
    extraction_type: ExtractionType
    timestamp: datetime
    processing_time: float
    cost_estimate: float
    confidence: float
    error_message: Optional[str] = None


class ExtractionWorker(QThread):
    """Worker thread for AI analysis to prevent UI blocking."""
    
    # Signals for communication with main thread
    result_ready = pyqtSignal(object)  # ExtractionResult
    progress_update = pyqtSignal(str)  # Status message
    
    def __init__(self, vision_client: VisionClient, prompt_builder: PromptBuilder):
        super().__init__()
        self.vision_client = vision_client
        self.prompt_builder = prompt_builder
        self.extraction_queue = asyncio.Queue()
        self.running = True
        
    def add_extraction(self, image_data: ImageData, extraction_type: ExtractionType):
        """Add extraction task to queue."""
        asyncio.run_coroutine_threadsafe(
            self.extraction_queue.put((image_data, extraction_type)),
            self.loop
        )
    
    def add_queue_analysis(self, image_data_list: list):
        """Add queue analysis task."""
        asyncio.run_coroutine_threadsafe(
            self.extraction_queue.put((image_data_list, ExtractionType.QUEUE_ANALYSIS)),
            self.loop
        )
    
    def run(self):
        """Main worker thread loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self._process_extractions())
        except Exception as e:
            print(f"Worker thread error: {e}")
        finally:
            self.loop.close()
    
    async def _process_extractions(self):
        """Process extraction requests from queue."""
        while self.running:
            try:
                # Wait for extraction request
                data, extraction_type = await asyncio.wait_for(
                    self.extraction_queue.get(), timeout=1.0
                )
                
                self.progress_update.emit(f"Analyzing {extraction_type.value}...")
                
                # Get appropriate prompt
                prompt = self.prompt_builder.get_prompt(extraction_type)
                
                # Perform AI analysis
                start_time = time.time()
                
                if extraction_type == ExtractionType.QUEUE_ANALYSIS:
                    # Handle multiple images
                    ai_response = await self.vision_client.analyze_images(
                        data, prompt  # data is list of ImageData objects
                    )
                else:
                    # Handle single image
                    ai_response = await self.vision_client.analyze_image(
                        data, prompt  # data is single ImageData object
                    )
                
                processing_time = time.time() - start_time
                
                # Create result
                result = ExtractionResult(
                    success=ai_response.success,
                    data=ai_response.data,
                    extraction_type=extraction_type,
                    timestamp=datetime.now(),
                    processing_time=processing_time,
                    cost_estimate=ai_response.cost_estimate,
                    confidence=ai_response.confidence,
                    error_message=ai_response.error_message
                )
                
                # Emit result
                self.result_ready.emit(result)
                self.progress_update.emit("Analysis complete")
                
            except asyncio.TimeoutError:
                # No requests in queue, continue
                continue
            except Exception as e:
                error_result = ExtractionResult(
                    success=False,
                    data=None,
                    extraction_type=ExtractionType.QUEUE_ANALYSIS,
                    timestamp=datetime.now(),
                    processing_time=0.0,
                    cost_estimate=0.0,
                    confidence=0.0,
                    error_message=str(e)
                )
                self.result_ready.emit(error_result)
                self.progress_update.emit(f"Error: {e}")

    def stop(self):
        """Stop the worker thread."""
        self.running = False


class BitCraftyExtractorApp(QWidget):
    """Main application window for BitCrafty Extractor."""
    
    def __init__(self, config_manager=None):
        super().__init__()
        
        # Store configuration
        self.config_manager = config_manager
        
        # Initialize logging
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="ISO"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        self.logger = structlog.get_logger()
        
        # Initialize components with configuration
        self.window_capture = WindowCapture(self.logger, self.config_manager)
        self.vision_client = VisionClient(self.logger)
        self.prompt_builder = PromptBuilder()
        self.hotkey_handler = None
        
        # UI state
        self.extraction_results = []
        self.screenshot_queue = []  # Queue for screenshots
        self.is_configured = False
        
        # Worker thread
        self.worker = ExtractionWorker(self.vision_client, self.prompt_builder)
        self.worker.result_ready.connect(self.on_extraction_result)
        self.worker.progress_update.connect(self.on_progress_update)
        self.worker.start()
        
        # Initialize UI
        self.init_ui()
        self.setup_system_tray()
        
        # Statistics
        self.total_extractions = 0
        self.successful_extractions = 0
        
        self.logger.info("BitCrafty Extractor initialized")

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("BitCrafty Extractor")
        self.setGeometry(100, 100, 800, 600)
        
        # Create main layout
        layout = QVBoxLayout()
        
        # Create tab widget
        tabs = QTabWidget()
        
        # Configuration tab
        config_tab = self.create_config_tab()
        tabs.addTab(config_tab, "Configuration")
        
        # Extraction tab
        extraction_tab = self.create_extraction_tab()
        tabs.addTab(extraction_tab, "Extraction")
        
        # Results tab
        results_tab = self.create_results_tab()
        tabs.addTab(results_tab, "Results")
        
        # Statistics tab
        stats_tab = self.create_stats_tab()
        tabs.addTab(stats_tab, "Statistics")
        
        layout.addWidget(tabs)
        self.setLayout(layout)

    def create_config_tab(self):
        """Create configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # API Configuration
        api_group = QGroupBox("AI Provider Configuration")
        api_layout = QFormLayout()
        
        # OpenAI Configuration
        self.openai_key_input = QLineEdit()
        self.openai_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_key_input.setPlaceholderText("Enter OpenAI API key")
        api_layout.addRow("OpenAI API Key:", self.openai_key_input)
        
        # Anthropic Configuration
        self.anthropic_key_input = QLineEdit()
        self.anthropic_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.anthropic_key_input.setPlaceholderText("Enter Anthropic API key")
        api_layout.addRow("Anthropic API Key:", self.anthropic_key_input)
        
        # Provider selection
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["OpenAI GPT-4V", "Anthropic Claude"])
        api_layout.addRow("Primary Provider:", self.provider_combo)
        
        # Use fallback
        self.use_fallback_check = QCheckBox("Use fallback provider on failure")
        self.use_fallback_check.setChecked(True)
        api_layout.addRow("", self.use_fallback_check)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # Hotkey Configuration
        hotkey_group = QGroupBox("Hotkey Configuration")
        hotkey_layout = QFormLayout()
        
        self.queue_hotkey_input = QLineEdit("ctrl+shift+e")
        hotkey_layout.addRow("Queue Screenshot:", self.queue_hotkey_input)
        
        self.analyze_hotkey_input = QLineEdit("ctrl+shift+x")
        hotkey_layout.addRow("Analyze Queue:", self.analyze_hotkey_input)
        
        hotkey_group.setLayout(hotkey_layout)
        layout.addWidget(hotkey_group)
        
        # Configuration buttons
        button_layout = QVBoxLayout()
        
        self.save_config_btn = QPushButton("Save Configuration")
        self.save_config_btn.clicked.connect(self.save_configuration)
        button_layout.addWidget(self.save_config_btn)
        
        self.test_config_btn = QPushButton("Test Configuration")
        self.test_config_btn.clicked.connect(self.test_configuration)
        button_layout.addWidget(self.test_config_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget

    def create_extraction_tab(self):
        """Create extraction control tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Status
        self.status_label = QLabel("Status: Not configured")
        self.status_label.setFont(QFont("", 12, QFont.Weight.Bold))
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Manual extraction
        manual_group = QGroupBox("Manual Extraction")
        manual_layout = QVBoxLayout()
        
        # Queue controls
        queue_layout = QFormLayout()
        
        self.queue_size_label = QLabel("Queue Size: 0")
        queue_layout.addRow("Current Queue:", self.queue_size_label)
        
        manual_layout.addLayout(queue_layout)
        
        # Queue buttons
        queue_buttons_layout = QVBoxLayout()
        
        self.queue_screenshot_btn = QPushButton("Queue Screenshot")
        self.queue_screenshot_btn.clicked.connect(self.queue_screenshot)
        self.queue_screenshot_btn.setEnabled(False)
        queue_buttons_layout.addWidget(self.queue_screenshot_btn)
        
        self.analyze_queue_btn = QPushButton("Analyze Queue")
        self.analyze_queue_btn.clicked.connect(self.analyze_queue)
        self.analyze_queue_btn.setEnabled(False)
        queue_buttons_layout.addWidget(self.analyze_queue_btn)
        
        self.clear_queue_btn = QPushButton("Clear Queue")
        self.clear_queue_btn.clicked.connect(self.clear_queue)
        self.clear_queue_btn.setEnabled(False)
        queue_buttons_layout.addWidget(self.clear_queue_btn)
        
        manual_layout.addLayout(queue_buttons_layout)
        
        manual_group.setLayout(manual_layout)
        layout.addWidget(manual_group)
        
        # Hotkey status
        hotkey_group = QGroupBox("Hotkey Status")
        hotkey_layout = QVBoxLayout()
        
        self.hotkey_status_label = QLabel("Hotkeys: Disabled")
        hotkey_layout.addWidget(self.hotkey_status_label)
        
        self.toggle_hotkeys_btn = QPushButton("Enable Hotkeys")
        self.toggle_hotkeys_btn.clicked.connect(self.toggle_hotkeys)
        self.toggle_hotkeys_btn.setEnabled(False)
        hotkey_layout.addWidget(self.toggle_hotkeys_btn)
        
        hotkey_group.setLayout(hotkey_layout)
        layout.addWidget(hotkey_group)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget

    def create_results_tab(self):
        """Create results display tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Results display
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.results_text)
        
        # Results controls
        controls_layout = QVBoxLayout()
        
        self.clear_results_btn = QPushButton("Clear Results")
        self.clear_results_btn.clicked.connect(self.clear_results)
        controls_layout.addWidget(self.clear_results_btn)
        
        self.export_results_btn = QPushButton("Export Results")
        self.export_results_btn.clicked.connect(self.export_results)
        controls_layout.addWidget(self.export_results_btn)
        
        layout.addLayout(controls_layout)
        
        widget.setLayout(layout)
        return widget

    def create_stats_tab(self):
        """Create statistics tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Statistics display
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.stats_text)
        
        # Update button
        self.update_stats_btn = QPushButton("Update Statistics")
        self.update_stats_btn.clicked.connect(self.update_statistics)
        layout.addWidget(self.update_stats_btn)
        
        widget.setLayout(layout)
        return widget

    def setup_system_tray(self):
        """Setup system tray icon and menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.logger.warning("System tray not available")
            return
        
        # Create tray icon
        self.tray_icon = QSystemTrayIcon()
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = tray_menu.addAction("Show")
        show_action.triggered.connect(self.show)
        
        tray_menu.addSeparator()
        
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_application)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        # Show tray icon
        self.tray_icon.show()

    def save_configuration(self):
        """Save current configuration."""
        try:
            # Configure AI providers
            openai_key = self.openai_key_input.text().strip()
            anthropic_key = self.anthropic_key_input.text().strip()
            
            if openai_key:
                self.vision_client.configure_openai(openai_key)
            
            if anthropic_key:
                self.vision_client.configure_anthropic(anthropic_key)
            
            if not openai_key and not anthropic_key:
                QMessageBox.warning(self, "Configuration", 
                                  "Please provide at least one API key.")
                return
            
            # Set provider preferences
            if self.provider_combo.currentText() == "OpenAI GPT-4V":
                self.vision_client.default_provider = AIProvider.OPENAI_GPT4V
                self.vision_client.fallback_provider = AIProvider.ANTHROPIC_CLAUDE
            else:
                self.vision_client.default_provider = AIProvider.ANTHROPIC_CLAUDE
                self.vision_client.fallback_provider = AIProvider.OPENAI_GPT4V
            
            self.is_configured = True
            self.status_label.setText("Status: Configured")
            self.queue_screenshot_btn.setEnabled(True)
            self.analyze_queue_btn.setEnabled(True)
            self.clear_queue_btn.setEnabled(True)
            self.toggle_hotkeys_btn.setEnabled(True)
            
            QMessageBox.information(self, "Configuration", 
                                  "Configuration saved successfully!")
            
            self.logger.info("Configuration saved")
            
        except Exception as e:
            QMessageBox.critical(self, "Configuration Error", str(e))
            self.logger.error("Configuration failed", error=str(e))

    def test_configuration(self):
        """Test current configuration."""
        if not self.is_configured:
            QMessageBox.warning(self, "Test", "Please save configuration first.")
            return
        
        QMessageBox.information(self, "Test", "Configuration test not yet implemented.")

    def queue_screenshot(self):
        """Queue a screenshot for later analysis."""
        if not self.is_configured:
            QMessageBox.warning(self, "Queue", "Please configure the application first.")
            return
        
        try:
            # Capture screenshot
            screenshot = self.window_capture.capture_current_window()
            if screenshot is None:
                QMessageBox.warning(self, "Queue", 
                                  "Could not capture game window. Is Bitcraft running?")
                return
            
            # Add to queue
            self.screenshot_queue.append(screenshot)
            self.update_queue_display()
            
            self.logger.info("Screenshot queued", queue_size=len(self.screenshot_queue))
            
        except Exception as e:
            QMessageBox.critical(self, "Queue Error", str(e))
            self.logger.error("Failed to queue screenshot", error=str(e))

    def analyze_queue(self):
        """Analyze all screenshots in the queue."""
        if not self.is_configured:
            QMessageBox.warning(self, "Analysis", "Please configure the application first.")
            return
        
        if not self.screenshot_queue:
            QMessageBox.warning(self, "Analysis", "No screenshots in queue to analyze.")
            return
        
        try:
            # Create image data from queue
            image_data_list = [ImageData(img) for img in self.screenshot_queue]
            
            # Start analysis
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate
            self.worker.add_queue_analysis(image_data_list)
            
            self.logger.info("Queue analysis started", queue_size=len(self.screenshot_queue))
            
        except Exception as e:
            QMessageBox.critical(self, "Analysis Error", str(e))
            self.logger.error("Queue analysis failed", error=str(e))

    def clear_queue(self):
        """Clear the screenshot queue."""
        self.screenshot_queue.clear()
        self.update_queue_display()
        self.logger.info("Screenshot queue cleared")

    def update_queue_display(self):
        """Update the queue size display."""
        self.queue_size_label.setText(f"Queue Size: {len(self.screenshot_queue)}")
        self.analyze_queue_btn.setEnabled(len(self.screenshot_queue) > 0)

    def toggle_hotkeys(self):
        """Toggle hotkey monitoring."""
        if self.hotkey_handler is None:
            # Start hotkeys
            try:
                self.hotkey_handler = HotkeyHandler(self.logger)
                
                # Register hotkey callbacks
                self.hotkey_handler.register_callback(
                    self.queue_hotkey_input.text(),
                    self.hotkey_queue_screenshot
                )
                self.hotkey_handler.register_callback(
                    self.analyze_hotkey_input.text(),
                    self.hotkey_analyze_queue
                )
                
                self.hotkey_handler.start_monitoring()
                
                self.hotkey_status_label.setText("Hotkeys: Enabled")
                self.toggle_hotkeys_btn.setText("Disable Hotkeys")
                
                self.logger.info("Hotkeys enabled")
                
            except Exception as e:
                QMessageBox.critical(self, "Hotkey Error", str(e))
                self.logger.error("Failed to enable hotkeys", error=str(e))
        else:
            # Stop hotkeys
            self.hotkey_handler.stop_monitoring()
            self.hotkey_handler = None
            
            self.hotkey_status_label.setText("Hotkeys: Disabled")
            self.toggle_hotkeys_btn.setText("Enable Hotkeys")
            
            self.logger.info("Hotkeys disabled")

    def hotkey_queue_screenshot(self):
        """Handle hotkey-triggered screenshot queueing."""
        if not self.is_configured:
            return
        
        try:
            # Capture screenshot
            screenshot = self.window_capture.capture_current_window()
            if screenshot is None:
                self.logger.warning("Hotkey queue failed - no game window")
                return
            
            # Add to queue
            self.screenshot_queue.append(screenshot)
            self.update_queue_display()
            
            self.logger.info("Screenshot queued via hotkey", queue_size=len(self.screenshot_queue))
            
        except Exception as e:
            self.logger.error("Hotkey queue failed", error=str(e))

    def hotkey_analyze_queue(self):
        """Handle hotkey-triggered queue analysis."""
        if not self.is_configured or not self.screenshot_queue:
            return
        
        try:
            # Create image data from queue
            image_data_list = [ImageData(img) for img in self.screenshot_queue]
            
            # Start analysis
            self.worker.add_queue_analysis(image_data_list)
            
            self.logger.info("Queue analysis triggered via hotkey", queue_size=len(self.screenshot_queue))
            
        except Exception as e:
            self.logger.error("Hotkey analysis failed", error=str(e))

    def on_extraction_result(self, result: ExtractionResult):
        """Handle extraction result from worker."""
        self.progress_bar.setVisible(False)
        
        # Add to results
        self.extraction_results.append(result)
        self.total_extractions += 1
        
        if result.success:
            self.successful_extractions += 1
            
            # Display result
            result_text = f"""
=== {result.extraction_type.value.upper()} EXTRACTION ===
Time: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Confidence: {result.confidence:.2f}
Processing Time: {result.processing_time:.2f}s
Cost Estimate: ${result.cost_estimate:.4f}

Data:
{json.dumps(result.data, indent=2)}

"""
            self.results_text.append(result_text)
            
            # Auto-scroll to bottom
            cursor = self.results_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.results_text.setTextCursor(cursor)
            
            # For queue analysis, clear the queue after successful processing
            if result.extraction_type == ExtractionType.QUEUE_ANALYSIS:
                self.screenshot_queue.clear()
                self.queue_size_label.setText(f"Queue Size: {len(self.screenshot_queue)}")
            
            self.logger.info("Extraction completed successfully",
                           type=result.extraction_type.value,
                           confidence=result.confidence)
        else:
            error_text = f"""
=== EXTRACTION FAILED ===
Time: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Type: {result.extraction_type.value}
Error: {result.error_message}

"""
            self.results_text.append(error_text)
            
            self.logger.error("Extraction failed",
                            type=result.extraction_type.value,
                            error=result.error_message)

    def on_progress_update(self, message: str):
        """Handle progress update from worker."""
        self.status_label.setText(f"Status: {message}")

    def clear_results(self):
        """Clear results display."""
        self.results_text.clear()
        self.extraction_results.clear()
        self.total_extractions = 0
        self.successful_extractions = 0

    def export_results(self):
        """Export results to file."""
        if not self.extraction_results:
            QMessageBox.information(self, "Export", "No results to export.")
            return
        
        # TODO: Implement file dialog and export functionality
        QMessageBox.information(self, "Export", "Export functionality not yet implemented.")

    def update_statistics(self):
        """Update statistics display."""
        # Vision client stats
        vision_stats = self.vision_client.get_stats()
        
        # Application stats
        success_rate = (self.successful_extractions / max(self.total_extractions, 1)) * 100
        
        stats_text = f"""
=== BITCRAFTY EXTRACTOR STATISTICS ===

Application Stats:
- Total Extractions: {self.total_extractions}
- Successful Extractions: {self.successful_extractions}
- Success Rate: {success_rate:.1f}%

AI Vision Stats:
- Total Requests: {vision_stats['total_requests']}
- Total Cost: ${vision_stats['total_cost']:.4f}
- Average Cost per Request: ${vision_stats['average_cost_per_request']:.4f}
- Default Provider: {vision_stats['default_provider']}
- Fallback Provider: {vision_stats['fallback_provider']}

Provider Configuration:
- OpenAI Configured: {vision_stats['configured_providers']['openai']}
- Anthropic Configured: {vision_stats['configured_providers']['anthropic']}

"""
        self.stats_text.setPlainText(stats_text)

    def tray_icon_activated(self, reason):
        """Handle system tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()

    def closeEvent(self, event):
        """Handle window close event."""
        # Hide to system tray instead of closing
        event.ignore()
        self.hide()
        
        if self.tray_icon.isVisible():
            QMessageBox.information(
                self, "BitCrafty Extractor",
                "Application minimized to system tray. "
                "Right-click the tray icon to quit."
            )

    def quit_application(self):
        """Quit the application completely."""
        # Stop worker thread
        self.worker.stop()
        self.worker.wait()
        
        # Stop hotkeys
        if self.hotkey_handler:
            self.hotkey_handler.stop_monitoring()
        
        QApplication.quit()


# Alias for backward compatibility
BitCraftyExtractor = BitCraftyExtractorApp

def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description="BitCrafty Extractor - AI-powered game data extraction tool",
        prog="bitcrafty-extractor"
    )
    parser.add_argument(
        "--version", 
        action="version", 
        version="%(prog)s 1.0.0"
    )
    parser.add_argument(
        "--test-capture",
        action="store_true",
        help="Run capture test (Phase 1 validation)"
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        default=True,
        help="Launch GUI application (default)"
    )
    
    args = parser.parse_args()
    
    # Handle test capture mode
    if args.test_capture:
        print("Running capture test...")
        print("Make sure BitCraft is running and in focus!")
        try:
            # Find the test script relative to the package
            test_script = Path(__file__).parent.parent.parent / "test" / "test_window_capture.py"
            if not test_script.exists():
                print(f"Test script not found at: {test_script}")
                print("Run from project directory or check test location")
                sys.exit(1)
            
            import subprocess
            subprocess.run([sys.executable, str(test_script)], check=True)
        except Exception as e:
            print(f"Test failed: {e}")
            sys.exit(1)
        return
    
    # GUI mode (default)
    if not PYQT_AVAILABLE:
        print("ERROR: PyQt6 is required but not available.")
        print("Install with: pip install PyQt6")
        sys.exit(1)
    
    if not COMPONENTS_AVAILABLE:
        print("ERROR: Required components not available.")
        print("Make sure you're running from the correct directory.")
        print("Try running from the project root or using: pip install -e .")
        sys.exit(1)
    
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("BitCrafty Extractor")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("BitCrafty")
    
    # Create main window
    window = BitCraftyExtractorApp()
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
