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
    from PyQt6.QtGui import QIcon, QPixmap, QFont, QFontDatabase
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
    from bitcrafty_extractor.config.config_manager import ConfigManager
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    COMPONENTS_AVAILABLE = False
    print(f"Local components not available: {e}")
    # Define stubs to prevent NameError - must be before class definitions
    class ExtractionType:
        QUEUE_ANALYSIS = "queue_analysis"
        value = "queue_analysis"
    
    class ImageData:
        def __init__(self, image_array):
            self.image_array = image_array
    
    class AIProvider:
        OPENAI_GPT4V = "openai_gpt4v"
        ANTHROPIC_CLAUDE = "anthropic_claude"
    
    class VisionClient:
        def __init__(self, *args, **kwargs):
            pass
        
        def configure_openai(self, *args, **kwargs):
            pass
            
        def configure_anthropic(self, *args, **kwargs):
            pass
        
        async def analyze_image(self, *args, **kwargs):
            return type('MockResponse', (), {'success': False, 'data': None, 'cost_estimate': 0, 'confidence': 0, 'error_message': 'Components not available'})()
        
        async def analyze_images(self, *args, **kwargs):
            return type('MockResponse', (), {'success': False, 'data': None, 'cost_estimate': 0, 'confidence': 0, 'error_message': 'Components not available'})()
        
        def get_stats(self):
            return {'total_requests': 0, 'total_cost': 0, 'average_cost_per_request': 0, 'configured_providers': {'openai': False, 'anthropic': False}, 'default_provider': 'openai_gpt4v', 'fallback_provider': 'anthropic_claude'}
    
    class PromptBuilder:
        def __init__(self, *args, **kwargs):
            pass
            
        def get_prompt(self, extraction_type):
            return "Mock prompt"
    
    class WindowCapture:
        def __init__(self, *args, **kwargs):
            pass
        
        def capture_current_window(self):
            return None
    
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
    
    def __init__(self, config_manager):
        super().__init__()
        
        # Store configuration (required)
        if config_manager is None:
            raise ValueError("ConfigManager is required")
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
        self.vision_client = VisionClient(self.logger, self.config_manager)
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
        
        # System tray will be set up in showEvent
        self.tray_icon = None
        
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
        
        # Load existing configuration
        self.load_configuration()

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

    def showEvent(self, event):
        """Handle window show event - set up system tray after window is shown."""
        super().showEvent(event)
        
        # Set up system tray only once, after the window is properly initialized
        if self.tray_icon is None:
            self.setup_system_tray()

    def setup_system_tray(self):
        """Setup system tray icon and menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.logger.warning("System tray not available")
            return
        
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self)  # Pass parent
        
        # Create a simple icon
        try:
            # Create a simple 16x16 blue square icon
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.GlobalColor.blue)
            
            # Ensure the pixmap is valid
            if not pixmap.isNull():
                icon = QIcon(pixmap)
                self.tray_icon.setIcon(icon)
                self.logger.debug("Tray icon set successfully")
            else:
                raise Exception("Pixmap creation failed")
                
        except Exception as e:
            self.logger.warning(f"Failed to create custom tray icon: {e}")
            # Try using system style icon as fallback
            try:
                icon = self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon)
                self.tray_icon.setIcon(icon)
                self.logger.debug("System tray icon set using fallback")
            except Exception as e2:
                self.logger.error(f"Failed to set any tray icon: {e2}")
                return  # Don't show tray if no icon can be set
        
        # Set tooltip
        self.tray_icon.setToolTip("BitCrafty Extractor")
        
        # Create tray menu
        tray_menu = QMenu(self)  # Pass parent
        
        show_action = tray_menu.addAction("Show")
        show_action.triggered.connect(self.show)
        
        tray_menu.addSeparator()
        
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_application)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        # Show tray icon (now with icon set)
        self.tray_icon.show()

    def save_configuration(self):
        """Save current configuration."""
        try:
            # Get values from UI
            openai_key = self.openai_key_input.text().strip()
            anthropic_key = self.anthropic_key_input.text().strip()
            
            if not openai_key and not anthropic_key:
                QMessageBox.warning(self, "Configuration", 
                                  "Please provide at least one API key.")
                return
            
            # Update config manager with API keys
            if openai_key:
                from bitcrafty_extractor.config.config_manager import AIProviderConfig
                openai_config = AIProviderConfig(
                    api_key=openai_key,
                    model='gpt-4o',
                    enabled=True,
                    max_tokens=1000,
                    temperature=0.1,
                    timeout=30.0
                )
                self.config_manager.config.openai = openai_config
            
            if anthropic_key:
                from bitcrafty_extractor.config.config_manager import AIProviderConfig
                anthropic_config = AIProviderConfig(
                    api_key=anthropic_key,
                    model='claude-3-5-sonnet-20241022',
                    enabled=True,
                    max_tokens=1000,
                    temperature=0.1,
                    timeout=30.0
                )
                self.config_manager.config.anthropic = anthropic_config
            
            # Update provider preferences
            from bitcrafty_extractor.config.config_manager import AIProviderType
            if self.provider_combo.currentText() == "OpenAI GPT-4V":
                self.config_manager.config.extraction.primary_provider = AIProviderType.OPENAI
                self.config_manager.config.extraction.fallback_provider = AIProviderType.ANTHROPIC
            else:
                self.config_manager.config.extraction.primary_provider = AIProviderType.ANTHROPIC
                self.config_manager.config.extraction.fallback_provider = AIProviderType.OPENAI
            
            # Save configuration to file
            if self.config_manager.save_config():
                # Re-initialize vision client with new config
                self.vision_client = VisionClient(self.logger, self.config_manager)
                
                self.is_configured = True
                self.status_label.setText("Status: Configured ✓")
                self.queue_screenshot_btn.setEnabled(True)
                self.analyze_queue_btn.setEnabled(True)
                self.clear_queue_btn.setEnabled(True)
                self.toggle_hotkeys_btn.setEnabled(True)
                
                QMessageBox.information(self, "Configuration", 
                                      f"Configuration saved successfully!\nConfig file: {self.config_manager.config_path}")
                
                self.logger.info("Configuration saved successfully", 
                               config_path=str(self.config_manager.config_path))
            else:
                QMessageBox.critical(self, "Configuration Error", 
                                   "Failed to save configuration to file.")
            
        except Exception as e:
            QMessageBox.critical(self, "Configuration Error", 
                               f"Configuration failed: {str(e)}")
            self.logger.error("Configuration failed", error=str(e))

    def test_configuration(self):
        """Test current configuration by validating API keys."""
        if not self.is_configured:
            QMessageBox.warning(self, "Test Configuration", "Please save configuration first.")
            return
        
        # Use QProgressDialog instead of custom QMessageBox
        from PyQt6.QtWidgets import QProgressDialog
        progress = QProgressDialog("Validating API keys...", None, 0, 0, self)
        progress.setWindowTitle("Testing Configuration")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)  # No cancel button
        progress.show()
        
        # Process events to show the dialog
        QApplication.processEvents()
        
        try:
            test_results = []
            
            # Test OpenAI if configured
            if (self.config_manager.config.openai and 
                self.config_manager.config.openai.enabled and 
                self.config_manager.config.openai.api_key):
                
                progress.setLabelText("Testing OpenAI API key...")
                QApplication.processEvents()
                
                try:
                    # Test OpenAI API key by listing models (minimal cost operation)
                    import openai
                    openai_client = openai.OpenAI(api_key=self.config_manager.config.openai.api_key)
                    
                    # This is a very cheap operation that validates the API key
                    models = openai_client.models.list()
                    test_results.append(("OpenAI", True, "API key valid"))
                    
                except Exception as e:
                    test_results.append(("OpenAI", False, str(e)))
            
            # Test Anthropic if configured
            if (self.config_manager.config.anthropic and 
                self.config_manager.config.anthropic.enabled and 
                self.config_manager.config.anthropic.api_key):
                
                progress.setLabelText("Testing Anthropic API key...")
                QApplication.processEvents()
                
                try:
                    # Test Anthropic API key with a minimal request
                    import anthropic
                    anthropic_client = anthropic.Anthropic(api_key=self.config_manager.config.anthropic.api_key)
                    
                    # Send a very minimal message to validate the key (low cost)
                    response = anthropic_client.messages.create(
                        model="claude-3-haiku-20240307",  # Cheapest model
                        max_tokens=1,
                        messages=[{"role": "user", "content": "Hi"}]
                    )
                    test_results.append(("Anthropic", True, "API key valid"))
                    
                except Exception as e:
                    test_results.append(("Anthropic", False, str(e)))
            
        except Exception as e:
            # Always close progress dialog on error
            progress.close()
            progress.deleteLater()
            QApplication.processEvents()
            QMessageBox.critical(self, "Test Error", 
                               f"Test failed with error:\n{str(e)}")
            self.logger.error("Configuration test failed", error=str(e))
            return
        
        # Always close and delete progress dialog before showing results
        progress.close()
        progress.deleteLater()
        QApplication.processEvents()
        
        # Show results
        if not test_results:
            QMessageBox.warning(self, "Test Configuration", 
                              "No API keys are configured.\n\n"
                              "Please add at least one API key (OpenAI or Anthropic) and save the configuration.")
            return
        
        # Check if any provider worked
        working_providers = [result for result in test_results if result[1]]
        failed_providers = [result for result in test_results if not result[1]]
        
        if working_providers and not failed_providers:
            # All configured providers work
            provider_list = "\n".join([f"✅ {name}: {message}" for name, success, message in working_providers])
            QMessageBox.information(self, "Test Successful! ✅", 
                                  f"All configured API keys are working!\n\n{provider_list}\n\n"
                                  f"Your configuration is ready for AI analysis.")
            
        elif working_providers and failed_providers:
            # Some work, some don't
            working_list = "\n".join([f"✅ {name}: Working" for name, success, message in working_providers])
            failed_list = "\n".join([f"❌ {name}: {message}" for name, success, message in failed_providers])
            QMessageBox.warning(self, "Test Partial ⚠️", 
                              f"Some API keys are working:\n\n{working_list}\n\nFailed:\n{failed_list}\n\n"
                              f"You can use the working providers, but consider fixing the failed ones.")
            
        else:
            # None work
            failed_list = "\n".join([f"❌ {name}: {message}" for name, success, message in failed_providers])
            QMessageBox.critical(self, "Test Failed ❌", 
                               f"No API keys are working!\n\n{failed_list}\n\n"
                               f"Please check your API keys and network connection.")

    def queue_screenshot(self):
        """Queue a screenshot for later analysis."""
        if not self.is_configured:
            QMessageBox.warning(self, "Queue", "Please configure the application first.")
            return
        
        try:
            # Capture screenshot (returns numpy array)
            screenshot_array = self.window_capture.capture_current_window()
            if screenshot_array is None:
                QMessageBox.warning(self, "Queue", 
                                  "Could not capture game window. Is Bitcraft running?")
                return
            
            # Convert to ImageData for AI analysis
            image_data = ImageData(image_array=screenshot_array)
            
            # Add to queue
            self.screenshot_queue.append(image_data)
            self.update_queue_display()
            
            self.logger.info("Screenshot queued", 
                           queue_size=len(self.screenshot_queue),
                           image_shape=screenshot_array.shape)
            
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
            # Start analysis (queue already contains ImageData objects)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate
            self.worker.add_queue_analysis(self.screenshot_queue)
            
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
                    self.hotkey_queue_screenshot,
                    "Queue screenshot for AI analysis"
                )
                self.hotkey_handler.register_callback(
                    self.analyze_hotkey_input.text(),
                    self.hotkey_analyze_queue,
                    "Analyze screenshot queue with AI"
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
            # Capture screenshot (returns numpy array)
            screenshot_array = self.window_capture.capture_current_window()
            if screenshot_array is None:
                self.logger.warning("Hotkey queue failed - no game window")
                return
            
            # Convert to ImageData for AI analysis
            image_data = ImageData(image_array=screenshot_array)
            
            # Add to queue
            self.screenshot_queue.append(image_data)
            self.update_queue_display()
            
            self.logger.info("Screenshot queued via hotkey", 
                           queue_size=len(self.screenshot_queue),
                           image_shape=screenshot_array.shape)
            
        except Exception as e:
            self.logger.error("Hotkey queue failed", error=str(e))

    def hotkey_analyze_queue(self):
        """Handle hotkey-triggered queue analysis."""
        if not self.is_configured or not self.screenshot_queue:
            return
        
        try:
            # Start analysis (queue already contains ImageData objects)
            self.worker.add_queue_analysis(self.screenshot_queue)
            
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
        """Handle window close event - close gracefully instead of minimizing to tray."""
        self.logger.info("Close event received - shutting down gracefully")
        
        # Stop worker thread
        if hasattr(self, 'worker') and self.worker:
            self.worker.stop()
            self.worker.wait()
        
        # Stop hotkey handler
        if hasattr(self, 'hotkey_handler') and self.hotkey_handler:
            self.hotkey_handler.stop()
        
        # Hide tray icon
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.hide()
        
        # Accept the close event to allow the application to exit
        event.accept()
        
        # Quit the application
        QApplication.quit()

    def quit_application(self):
        """Quit the application completely."""
        self.logger.info("Quit application requested")
        
        # Stop worker thread
        if hasattr(self, 'worker') and self.worker:
            self.worker.stop()
            self.worker.wait()
        
        # Stop hotkey handler
        if hasattr(self, 'hotkey_handler') and self.hotkey_handler:
            self.hotkey_handler.stop()
        
        # Hide tray icon
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.hide()
        
        QApplication.quit()

    def load_configuration(self):
        """Load configuration from config manager and update UI."""
        try:
            if not self.config_manager:
                return
                
            # Load API keys into UI
            if self.config_manager.config.openai and self.config_manager.config.openai.api_key:
                self.openai_key_input.setText(self.config_manager.config.openai.api_key)
            
            if self.config_manager.config.anthropic and self.config_manager.config.anthropic.api_key:
                self.anthropic_key_input.setText(self.config_manager.config.anthropic.api_key)
            
            # Set provider preference
            if (self.config_manager.config.extraction and 
                self.config_manager.config.extraction.primary_provider.value == 'anthropic'):
                self.provider_combo.setCurrentText("Anthropic Claude")
            else:
                self.provider_combo.setCurrentText("OpenAI GPT-4V")
            
            # Check if we have at least one API key configured
            has_openai = (self.config_manager.config.openai and 
                         self.config_manager.config.openai.enabled and 
                         self.config_manager.config.openai.api_key)
            has_anthropic = (self.config_manager.config.anthropic and 
                           self.config_manager.config.anthropic.enabled and 
                           self.config_manager.config.anthropic.api_key)
            
            if has_openai or has_anthropic:
                self.is_configured = True
                self.status_label.setText("Status: Configured ✓")
                self.queue_screenshot_btn.setEnabled(True)
                self.analyze_queue_btn.setEnabled(True)
                self.clear_queue_btn.setEnabled(True)
                self.toggle_hotkeys_btn.setEnabled(True)
                
                self.logger.info("Configuration loaded successfully", 
                               has_openai=has_openai, has_anthropic=has_anthropic)
            else:
                self.status_label.setText("Status: Not configured")
                
        except Exception as e:
            self.logger.error("Failed to load configuration", error=str(e))
            self.status_label.setText("Status: Configuration error")


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
    
    # Set environment variables to help with Qt font rendering on Windows
    import os
    # Force Qt to use GDI instead of DirectWrite for font rendering
    os.environ['QT_QPA_PLATFORM'] = 'windows:fontengine=gdi'
    # Alternative: disable hardware acceleration
    os.environ.setdefault('QT_OPENGL', 'software')
    # Force Qt to not use problematic fonts
    os.environ['QT_FONT_DPI'] = '96'
    
    app = QApplication(sys.argv)
    
    # Set Qt attributes to reduce font rendering issues
    try:
        app.setAttribute(Qt.ApplicationAttribute.AA_DisableWindowContextHelpButton, True)
    except AttributeError:
        pass  # Ignore if not available
    
    # Configure comprehensive font handling to avoid DirectWrite issues
    def setup_fonts():
        """Setup proper font configuration to avoid MS Sans Serif issues."""
        try:
            # List of preferred fonts in order of preference
            font_preferences = [
                ("Segoe UI", 9),           # Modern Windows default
                ("Microsoft Sans Serif", 9), # Proper substitute for MS Sans Serif
                ("Tahoma", 9),             # Fallback 1
                ("Arial", 9),              # Fallback 2  
                ("Sans Serif", 9)          # Generic fallback
            ]
            
            # Try each font until we find one that works
            font_set = False
            for font_name, size in font_preferences:
                try:
                    font = QFont(font_name, size)
                    app.setFont(font)
                    font_set = True
                    break
                except Exception:
                    continue
            
            # Set additional font substitutions to prevent MS Sans Serif issues
            try:
                # Add font substitutions to replace problematic fonts
                font_substitutions = {
                    "MS Sans Serif": "Microsoft Sans Serif",
                    "MS Shell Dlg": "Segoe UI", 
                    "MS Shell Dlg 2": "Segoe UI",
                    "System": "Segoe UI"
                }
                
                # Note: QFont.insertSubstitution is static
                for old_font, new_font in font_substitutions.items():
                    QFont.insertSubstitution(old_font, new_font)
                    
            except Exception:
                pass
                
        except Exception:
            pass
    
    # Setup fonts before creating any widgets
    setup_fonts()
    
    # Set application properties
    app.setApplicationName("BitCrafty Extractor")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("BitCrafty")
    
    # Initialize configuration manager
    config_manager = ConfigManager()
    
    # Create main window with config manager
    window = BitCraftyExtractorApp(config_manager)
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
