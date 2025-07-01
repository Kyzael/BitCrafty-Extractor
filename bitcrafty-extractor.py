#!/usr/bin/env python3
"""
BitCrafty-Extractor - AI-powered item and recipe extraction from BitCraft screenshots

This is the main BitCrafty-Extractor application with a three-pane interface:
Left: Hotkey controls and session stats | Right: Live queue status | Bottom: Debug log

Features:
- Global hotkeys that work while playing BitCraft
- Real-time screenshot queue management  
- AI-powered analysis with OpenAI and Anthropic
- Session tracking with cost estimates
- Export-ready data extraction
"""
import cv2
import argparse
import sys
import asyncio
import signal
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from bitcrafty_extractor.config.config_manager import ConfigManager
from bitcrafty_extractor.ai_analysis.vision_client import VisionClient, ImageData
from bitcrafty_extractor.ai_analysis.prompts import PromptBuilder, ExtractionType
from bitcrafty_extractor.capture.window_capture import WindowCapture
from bitcrafty_extractor.capture.hotkey_handler import HotkeyHandler
from bitcrafty_extractor.export.export_manager import ExportManager
from bitcrafty_extractor.audio.audio_manager import AudioManager, AudioEvent



try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.live import Live
    from rich.prompt import Prompt
    from rich.align import Align
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️ Rich library not available. Install with: pip install rich")


class BitCraftyExtractor:
    """Main BitCrafty-Extractor application with three-pane interface and global hotkeys."""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.vision_client = None
        self.window_capture = None
        self.hotkey_handler = None
        self.prompt_builder = PromptBuilder()  # External prompt system
        self.export_manager = ExportManager(config_manager=self.config_manager)  # Export system for items/crafts
        self.audio_manager = None  # Audio feedback system (initialized later)
        self.screenshot_queue: List[ImageData] = []
        self.queue_folder = Path("queue_screenshots")
        self.queue_folder.mkdir(exist_ok=True)
        
        # Analysis log file setup
        self.analysis_log_folder = Path("analysis_logs")
        self.analysis_log_folder.mkdir(exist_ok=True)
        session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.analysis_log_file = self.analysis_log_folder / f"analysis_session_{session_timestamp}.json"
        self.analysis_log_entries = []  # Store log entries in memory before writing
        
        # Error log file setup
        self.error_log_file = Path("error.log")
        
        # Create README for analysis logs
        self._create_analysis_log_readme()
        
        self.logger = None
        self.loop = None  # Store event loop reference
        self.analysis_in_progress = False  # Track analysis state
        self.console = Console() if RICH_AVAILABLE else None
        self.layout = None
        self.live_display = None
        self.running = True
        self.last_analysis = None
        self.debug_messages = []  # Store debug messages
        self.max_debug_messages = 10  # Limit debug message history
        
        # Session tracking
        self.session_items_found = []  # All items found this session
        self.session_crafts_found = []  # All crafts found this session
        self.total_screenshots_analyzed = 0
        self.total_cost = 0.0
        self.is_analyzing = False
        self.show_analysis_results = False
        self.last_export_stats = None  # Track last export statistics
        self.last_analysis_display = None  # Store last analysis for final summary
        
    def create_layout(self):
        """Create the four-section layout with dedicated session stats."""
        if not RICH_AVAILABLE:
            return None
            
        layout = Layout()
        layout.split_column(
            Layout(name="main", ratio=4),
            Layout(name="debug", ratio=1)
        )
        # Split main area into left and right
        layout["main"].split_row(
            Layout(name="left_column", ratio=1),
            Layout(name="queue", ratio=1)
        )
        # Split left column into commands and session stats
        layout["left_column"].split_column(
            Layout(name="commands", ratio=3),
            Layout(name="session_stats", ratio=1)
        )
        return layout
        
    def update_command_panel(self):
        """Update the left command panel."""
        if not RICH_AVAILABLE:
            return Panel("Commands not available")
            
        commands_text = Text()
        commands_text.append("🚀 BitCrafty-Extractor\n", style="bold blue")
        commands_text.append("=" * 30 + "\n\n", style="dim")
        
        # Primary workflow info
        commands_text.append("🎮 Hotkey-Driven Interface\n", style="bold yellow")
        commands_text.append("  This console is controlled via global hotkeys\n", style="white")
        commands_text.append("  that work while playing BitCraft!\n\n", style="white")
        
        # Global hotkeys (main interface)
        if self.config_manager:
            hotkeys = self.config_manager.config.hotkeys
            commands_text.append("🎮 Global Hotkeys:\n", style="bold green")
            commands_text.append(f"  📸 {hotkeys.queue_screenshot} - Take screenshot\n", style="cyan")
            commands_text.append(f"  🤖 {hotkeys.analyze_queue} - Analyze queue\n", style="cyan")
            commands_text.append(f"  🚪 {hotkeys.quit_application} - Quit gracefully\n", style="red")
            commands_text.append("  💡 Work while in-game!\n\n", style="dim")
        
        # Workflow
        commands_text.append("🎯 Workflow:\n", style="bold yellow")
        commands_text.append("  1. Take screenshots in-game\n", style="white")
        commands_text.append("  2. Watch queue fill up (right panel)\n", style="white")
        commands_text.append("  3. Analyze when ready\n", style="white")
        commands_text.append("  4. View results below\n\n", style="white")
        
        # Analysis log information
        commands_text.append("📄 Analysis Log:\n", style="bold yellow")
        commands_text.append(f"  📝 Analyses: {len(self.analysis_log_entries)}\n", style="white")
        commands_text.append(f"  📁 File: {self.analysis_log_file.name}\n", style="dim")
        commands_text.append(f"  💡 Detailed results saved to disk\n", style="dim")
        
        return Panel(commands_text, title="[bold blue]BitCrafty-Extractor[/bold blue]", border_style="blue")
        
    def update_session_stats_panel(self):
        """Update the session statistics panel (separate from commands)."""
        if not RICH_AVAILABLE:
            return Panel("Session stats not available")
            
        stats_text = Text()
        stats_text.append("📊 Session Stats:\n", style="bold magenta")
        
        # Show last analysis details if available with new/duplicate breakdown
        if self.last_export_stats:
            stats = self.last_export_stats
            items_total = stats.get('items_found_total', len(self.session_items_found))
            items_new = stats.get('items_found_new', 0)
            items_duplicates = stats.get('items_found_duplicates', 0)
            
            crafts_total = stats.get('crafts_found_total', len(self.session_crafts_found))
            crafts_new = stats.get('crafts_found_new', 0)
            crafts_duplicates = stats.get('crafts_found_duplicates', 0)
            
            stats_text.append(f"🍎 Items: {items_total}", style="green")
            if items_new < items_total:
                stats_text.append(f" ({items_new} new)", style="cyan")
            stats_text.append("\n")
            
            stats_text.append(f"🔨 Crafts: {crafts_total}", style="yellow")
            if crafts_new < crafts_total:
                stats_text.append(f" ({crafts_new} new)", style="cyan")
            stats_text.append("\n")
            
            # Show duplicate details if any
            if items_duplicates > 0 or crafts_duplicates > 0:
                stats_text.append(f"🔄 Duplicates: {items_duplicates + crafts_duplicates}\n", style="dim")
        else:
            # Fallback for when no analysis has been done yet
            stats_text.append(f"🍎 Items: {len(self.session_items_found)}\n", style="green")
            stats_text.append(f"🔨 Crafts: {len(self.session_crafts_found)}\n", style="yellow")
        
        stats_text.append(f"📸 Screenshots: {self.total_screenshots_analyzed}\n", style="cyan")
        stats_text.append(f"💰 Cost: ${self.total_cost:.3f}", style="red")
        
        return Panel(stats_text, title="[bold magenta]Session Statistics[/bold magenta]", border_style="magenta")
        
    def update_queue_panel(self):
        """Update the right queue panel."""
        if not RICH_AVAILABLE:
            return Panel("Queue not available")
        
        # Get provider info for header
        provider = "Unknown"
        if self.config_manager and self.config_manager.config:
            provider = str(self.config_manager.config.extraction.primary_provider).replace("AIProviderType.", "")
        
        # Create header with provider info
        header_text = Text()
        header_text.append(f"🤖 Provider: {provider} | ", style="bold cyan")
        queue_status = "⏳ Analyzing..." if self.analysis_in_progress else f"Queue: {len(self.screenshot_queue)}"
        header_text.append(f"📊 {queue_status}\n", style="bold yellow")
        header_text.append("=" * 40 + "\n", style="dim")
        
        if not self.screenshot_queue and not self.analysis_in_progress:
            # Empty queue display
            queue_text = Text()
            queue_text.append("🎯 No screenshots queued\n\n", style="yellow")
            queue_text.append("Ready for screenshots!", style="dim")
            
            # Create dedicated analysis results section (always visible)
            analysis_results_text = self._create_analysis_results_panel()
            
            content = Layout()
            content.split_column(
                Layout(Panel(header_text, border_style="dim"), ratio=1),
                Layout(Panel(queue_text, border_style="dim"), ratio=3),
                Layout(Panel(analysis_results_text, title="[bold magenta]Last Analysis Results[/bold magenta]", border_style="magenta"), ratio=2)
            )
            
            return Panel(content, title="[bold green]Live Queue Status[/bold green]", border_style="green")
        
        if self.analysis_in_progress:
            # Show analysis in progress
            queue_text = Text()
            queue_text.append("⏳ Analysis in progress...\n\n", style="bold yellow")
            queue_text.append(f"Processing {len(self.screenshot_queue)} screenshots with AI\n", style="white")
            queue_text.append("Please wait for response...", style="dim")
            
            # Create dedicated analysis results section (always visible)
            analysis_results_text = self._create_analysis_results_panel()
            
            content = Layout()
            content.split_column(
                Layout(Panel(header_text, border_style="dim"), ratio=1),
                Layout(Panel(queue_text, border_style="dim"), ratio=3),
                Layout(Panel(analysis_results_text, title="[bold magenta]Last Analysis Results[/bold magenta]", border_style="magenta"), ratio=2)
            )
            
            return Panel(content, title="[bold yellow]Analysis In Progress[/bold yellow]", border_style="yellow")
        
        # Create table for queue items
        table = Table(show_header=True, header_style="bold green", box=None)
        table.add_column("#", style="dim", width=3)
        table.add_column("Timestamp", style="cyan", width=10)
        table.add_column("Size", style="yellow", width=12)
        table.add_column("Status", style="white", width=15)
        
        for i, image_data in enumerate(self.screenshot_queue, 1):
            # Use actual timestamp from when screenshot was taken
            timestamp = image_data.timestamp.strftime("%H:%M:%S") if hasattr(image_data, 'timestamp') else datetime.now().strftime("%H:%M:%S")
            
            # Get image size
            if hasattr(image_data, 'image_array') and image_data.image_array is not None:
                h, w = image_data.image_array.shape[:2]
                size = f"{w}x{h}"
            else:
                size = "Unknown"
            
            # Status
            status = "✅ Ready"
            
            table.add_row(str(i), timestamp, size, status)
        
        # Create dedicated analysis results section (always visible)
        analysis_results_text = self._create_analysis_results_panel()
        
        # Combine everything with consistent 4:3:2 ratio (header:queue:analysis)
        content = Layout()
        content.split_column(
            Layout(Panel(header_text, border_style="dim"), ratio=1),
            Layout(table, ratio=3),
            Layout(Panel(analysis_results_text, title="[bold magenta]Last Analysis Results[/bold magenta]", border_style="magenta"), ratio=2)
        )
        
        return Panel(content, title="[bold green]Live Queue Status[/bold green]", border_style="green")
        
    def _create_analysis_results_panel(self):
        """Create a consistent analysis results panel that's always visible."""
        if not RICH_AVAILABLE:
            return Text("Analysis results not available")
        
        results_text = Text()
        
        if not self.last_analysis and not self.last_export_stats:
            # No analysis performed yet
            results_text.append("🎯 No analysis performed yet\n", style="bold yellow")
            results_text.append("Ready to analyze screenshots!", style="dim")
            return results_text
        
        if self.last_analysis and self.last_export_stats:
            # Enhanced display with comprehensive stats
            stats = self.last_export_stats
            items_total = stats.get('items_found_total', 0)
            items_new = stats.get('items_found_new', 0)
            items_duplicates = stats.get('items_found_duplicates', 0)
            crafts_total = stats.get('crafts_found_total', 0)
            crafts_new = stats.get('crafts_found_new', 0)
            crafts_duplicates = stats.get('crafts_found_duplicates', 0)
            
            # Summary header
            results_text.append("📊 Analysis Summary:\n", style="bold cyan")
            
            # Items analysis
            if items_total > 0:
                results_text.append(f"📦 Items Found: {items_total}", style="green")
                if items_new < items_total:
                    results_text.append(f" ({items_new} new, {items_duplicates} duplicates)", style="dim")
                results_text.append("\n", style="white")
            else:
                results_text.append("📦 Items Found: 0\n", style="dim")
            
            # Crafts analysis
            if crafts_total > 0:
                results_text.append(f"🔨 Crafts Found: {crafts_total}", style="yellow")
                if crafts_new < crafts_total:
                    results_text.append(f" ({crafts_new} new, {crafts_duplicates} duplicates)", style="dim")
                results_text.append("\n", style="white")
            else:
                results_text.append("🔨 Crafts Found: 0\n", style="dim")
            
            # Confidence and export info
            confidence = self.last_analysis.get('total_confidence', 0)
            results_text.append(f"📈 Confidence: {confidence:.1f}%", style="white")
            
            # Export status
            new_items_added = stats.get('new_items_added', 0)
            new_crafts_added = stats.get('new_crafts_added', 0)
            if new_items_added > 0 or new_crafts_added > 0:
                results_text.append(f" | 📤 Exported: {new_items_added}+{new_crafts_added}", style="cyan")
            else:
                results_text.append(" | ℹ️ No new exports", style="dim")
            results_text.append("\n", style="white")
            
            # Show items and crafts from the last analysis queue only
            try:
                # Get items and crafts from the last analysis
                last_items = self.last_analysis.get('items_found', [])
                last_crafts = self.last_analysis.get('crafts_found', [])
                
                # Show items from last queue
                if isinstance(last_items, list) and last_items:
                    item_names = []
                    for item in last_items:
                        if isinstance(item, dict) and 'name' in item:
                            item_name = str(item['name']).strip()
                            if item_name:
                                item_names.append(item_name)
                    
                    if item_names:
                        # Show up to 5 items from last queue
                        display_items = item_names[:5]
                        results_text.append(f"📦 Last queue items: {', '.join(display_items)}", style="green")
                        if len(item_names) > 5:
                            results_text.append(f" (+{len(item_names)-5} more)", style="dim")
                        results_text.append("\n")
                
                # Show crafts from last queue
                if isinstance(last_crafts, list) and last_crafts:
                    craft_names = []
                    for craft in last_crafts:
                        if isinstance(craft, dict) and 'name' in craft:
                            craft_name = str(craft['name']).strip()
                            if craft_name:
                                craft_names.append(craft_name)
                    
                    if craft_names:
                        # Show up to 5 crafts from last queue
                        display_crafts = craft_names[:5]
                        results_text.append(f"🔨 Last queue crafts: {', '.join(display_crafts)}", style="yellow")
                        if len(craft_names) > 5:
                            results_text.append(f" (+{len(craft_names)-5} more)", style="dim")
                        results_text.append("\n")
                        
            except Exception as e:
                self.add_debug_message(f"⚠️ Error displaying last queue results: {e}")
                
        elif self.last_analysis:
            # Fallback for older analysis format without enhanced stats
            results_text.append("📊 Analysis Summary:\n", style="bold cyan")
            items = self.last_analysis.get('items_found', [])
            crafts = self.last_analysis.get('crafts_found', [])
            results_text.append(f"📦 Items: {len(items)} | 🔨 Crafts: {len(crafts)}\n", style="white")
            confidence = self.last_analysis.get('total_confidence', 0)
            results_text.append(f"📈 Confidence: {confidence:.1f}%\n", style="white")
        
        return results_text
        
    def update_debug_panel(self):
        """Update the bottom debug panel with fixed height."""
        if not RICH_AVAILABLE:
            return Panel("Debug not available")
        
        debug_text = Text()
        debug_text.append("🔧 Debug Log", style="bold magenta")
        debug_text.append("\n" + "=" * 50 + "\n", style="dim")
        
        # Fixed number of lines to maintain consistent height
        max_lines = 3
        
        if not self.debug_messages:
            # Fill with default message and empty lines to maintain height
            debug_text.append("🎮 Hotkeys active - take screenshots while playing!\n", style="cyan")
            # Add empty lines to maintain consistent height
            for _ in range(max_lines - 1):
                debug_text.append("\n")
        else:
            # Show last few debug messages, exactly max_lines
            recent_messages = self.debug_messages[-max_lines:]
            
            # Pad with empty lines if we have fewer messages than max_lines
            while len(recent_messages) < max_lines:
                recent_messages.insert(0, "")
            
            for msg in recent_messages:
                if msg:
                    debug_text.append(f"{msg}\n", style="white")
                else:
                    debug_text.append("\n")
        
        return Panel(debug_text, title="[bold magenta]Status & Debug[/bold magenta]", border_style="magenta")
        
    def add_debug_message(self, message: str):
        """Add a debug message to the log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}"
        self.debug_messages.append(formatted_msg)
        
        # Keep only recent messages
        if len(self.debug_messages) > self.max_debug_messages:
            self.debug_messages = self.debug_messages[-self.max_debug_messages:]
    
    def log_error_to_file(self, error_message: str, exception: Exception = None, context: dict = None):
        """Log errors to error.log file for debugging."""
        try:
            timestamp = datetime.now().isoformat()
            log_entry = {
                "timestamp": timestamp,
                "error_message": error_message,
                "exception_type": type(exception).__name__ if exception else None,
                "exception_details": str(exception) if exception else None,
                "context": context or {}
            }
            
            # Append to error log file
            with open(self.error_log_file, 'a', encoding='utf-8') as f:
                f.write(f"{json.dumps(log_entry, ensure_ascii=False)}\n")
                
        except Exception as log_error:
            # Fallback if error logging fails
            if self.logger:
                self.logger.error("Failed to write to error log", error=str(log_error))
        
    def update_display(self):
        """Update the entire display."""
        if not RICH_AVAILABLE or not self.layout:
            return
            
        self.layout["commands"].update(self.update_command_panel())
        self.layout["session_stats"].update(self.update_session_stats_panel())
        self.layout["queue"].update(self.update_queue_panel())
        self.layout["debug"].update(self.update_debug_panel())
        
    async def initialize(self):
        """Initialize the CLI application."""
        if not RICH_AVAILABLE:
            print("⚠️ Rich library not available. Using basic mode.")
            print("💡 Install with: pip install rich")
            return await self._basic_mode()
        
        # Initialize logger
        import structlog
        self.logger = structlog.get_logger(__name__)
        
        # Initialize vision client
        self.vision_client = VisionClient(self.logger, self.config_manager)
        
        # Initialize window capture
        self.window_capture = WindowCapture(self.logger)
        
        # Initialize hotkey handler
        self.hotkey_handler = HotkeyHandler(self.logger)
        
        # Initialize audio manager
        self.audio_manager = AudioManager(self.config_manager, self.logger)
        
        # Reset session tracking for new session
        self.export_manager.reset_session_tracking()
        
        # Register hotkey callbacks using configuration
        hotkeys = self.config_manager.config.hotkeys
        self.hotkey_handler.register_callback(
            hotkeys.queue_screenshot, 
            self._hotkey_screenshot, 
            "Take screenshot and add to queue"
        )
        self.hotkey_handler.register_callback(
            hotkeys.analyze_queue, 
            self._hotkey_analyze, 
            "Analyze screenshot queue"
        )
        self.hotkey_handler.register_callback(
            hotkeys.quit_application, 
            self._hotkey_quit, 
            "Quit application gracefully"
        )
        
        # Check configuration
        await self._check_configuration()
        
        # Start hotkey monitoring
        self._start_hotkeys()
        
        # Set up layout
        self.layout = self.create_layout()
        
    async def _basic_mode(self):
        """Fallback to basic CLI mode if rich is not available."""
        print("🚀 BitCrafty-Extractor (Basic Mode)")
        print("=" * 40)
        print("💡 Install 'rich' library for enhanced interface: pip install rich")
        return False
        
    async def _check_configuration(self):
        """Check if configuration is valid and validate API keys."""
        has_openai = (self.config_manager.config.openai and 
                     self.config_manager.config.openai.enabled and 
                     self.config_manager.config.openai.api_key)
        has_anthropic = (self.config_manager.config.anthropic and 
                        self.config_manager.config.anthropic.enabled and 
                        self.config_manager.config.anthropic.api_key)
        
        if not (has_openai or has_anthropic):
            print("❌ No API keys configured!")
            print()
            print("🔧 Setup Instructions:")
            print("   1. Open: config/config.yaml")
            print("   2. Add your API key(s) to the 'api_key' fields:")
            print("      • OpenAI: Get from https://platform.openai.com/api-keys")
            print("      • Anthropic: Get from https://console.anthropic.com/")
            print("   3. Save the file and restart the application")
            print()
            print("📝 Example config.yaml:")
            print("   openai:")
            print("     api_key: 'sk-your-openai-key-here'")
            print("   anthropic:")
            print("     api_key: 'sk-ant-your-anthropic-key-here'")
            print()
            sys.exit(1)
        
        # Validate API keys by testing them
        print("🔑 Validating API keys...")
        
        valid_providers = []
        
        if has_openai:
            print("   Testing OpenAI API key...", end=" ")
            if await self._validate_openai_key():
                print("✅ Valid")
                valid_providers.append("OpenAI")
            else:
                print("❌ Invalid")
                
        if has_anthropic:
            print("   Testing Anthropic API key...", end=" ")
            if await self._validate_anthropic_key():
                print("✅ Valid")
                valid_providers.append("Anthropic")
            else:
                print("❌ Invalid")
        
        if not valid_providers:
            print("\n❌ No valid API keys found!")
            print("💡 Check your API keys in config/config.yaml and restart")
            sys.exit(1)
            
        print(f"\n✅ Configuration loaded - Valid providers: {', '.join(valid_providers)}")
        print(f"   Primary: {self.config_manager.config.extraction.primary_provider}")
        print(f"   Fallback: {self.config_manager.config.extraction.fallback_provider}")

    

        
    def _hotkey_screenshot(self):
        """Hotkey callback for taking screenshots."""
        try:
            self.add_debug_message("📸 Hotkey pressed - taking screenshot")
            success = self.take_screenshot()
            if success:
                self.add_debug_message(f"✅ Screenshot added (queue: {len(self.screenshot_queue)})")
            else:
                self.add_debug_message("❌ Screenshot failed - BitCraft window not found")
        except Exception as e:
            self.add_debug_message(f"❌ Screenshot error: {str(e)}")
            if self.logger:
                self.logger.error("Hotkey screenshot error", error=str(e))
            
    def _hotkey_analyze(self):
        """Hotkey callback for analyzing queue."""
        if not self.screenshot_queue:
            self.add_debug_message("❌ No screenshots to analyze")
            return
            
        if self.analysis_in_progress:
            self.add_debug_message("⏳ Analysis already in progress")
            return
            
        # Mark analysis as starting
        self.analysis_in_progress = True
        self.add_debug_message(f"🤖 Starting analysis of {len(self.screenshot_queue)} screenshots...")
        
        # Schedule analysis in the event loop using thread-safe method
        if self.loop and not self.loop.is_closed():
            try:
                # Use call_soon_threadsafe to schedule from hotkey thread
                self.loop.call_soon_threadsafe(
                    lambda: self.loop.create_task(self._hotkey_analyze_async())
                )
            except Exception as e:
                self.analysis_in_progress = False
                self.add_debug_message(f"❌ Could not schedule analysis: {e}")
        else:
            self.analysis_in_progress = False
            self.add_debug_message("❌ Event loop not available")
            
    async def _hotkey_analyze_async(self):
        """Async analysis for hotkey callback."""
        error_occurred = None
        try:
            success = await self.analyze_queue()
            if success:
                # Clear queue and remove screenshot files
                await self._clear_queue_and_cleanup()
                self.add_debug_message("✅ Analysis completed - queue cleared")
                # Force immediate display update to show cleared queue
                if self.layout:
                    self.update_display()
            else:
                self.add_debug_message("❌ Analysis failed - queue retained")
        except Exception as e:
            error_occurred = e
            self.add_debug_message(f"❌ Analysis error: {e}")
        finally:
            self.analysis_in_progress = False
            if error_occurred and self.logger:
                self.logger.error("Hotkey analysis error", error=str(error_occurred))
            
    def _hotkey_quit(self):
        """Hotkey callback for graceful quit."""
        try:
            self.add_debug_message("👋 Quit hotkey pressed - shutting down gracefully")
            self.running = False
        except Exception as e:
            if self.logger:
                self.logger.error("Hotkey quit error", error=str(e))
            
    def take_screenshot(self) -> bool:
        """Take a screenshot and add to queue."""
        try:
            # Find BitCraft window
            window_info = self.window_capture.find_game_window()
            if not window_info:
                return False
                
            # Capture screenshot
            screenshot = self.window_capture.capture_window(window_info)
            if screenshot is None:
                return False
                
            # Create static timestamp for this screenshot
            capture_time = datetime.now()
            timestamp_str = capture_time.strftime("%H%M%S")
            
            # Save screenshot file
            filename = f"queue_{len(self.screenshot_queue)+1:03d}_{timestamp_str}.png"
            filepath = self.queue_folder / filename
            cv2.imwrite(str(filepath), screenshot)
            
            # Create ImageData with timestamp and file path
            image_data = ImageData(image_array=screenshot)
            image_data.timestamp = capture_time  # Store static timestamp
            image_data.file_path = filepath      # Store file path for cleanup
            
            # Add to queue
            self.screenshot_queue.append(image_data)
            
            # Play audio feedback for successful screenshot
            if self.audio_manager:
                self.audio_manager.play_audio_feedback(AudioEvent.SCREENSHOT_TAKEN)
            
            return True
            
        except Exception as e:
            self.logger.error("Screenshot failed", error=str(e))
            return False
            
    async def analyze_queue(self) -> bool:
        """Analyze all screenshots in the queue."""
        if not self.screenshot_queue:
            return False
            
        try:
            self.add_debug_message(f"🤖 Analyzing {len(self.screenshot_queue)} screenshots")
            
            # Play audio feedback for analysis start
            if self.audio_manager:
                self.audio_manager.play_audio_feedback(
                    AudioEvent.ANALYSIS_START, 
                    screenshot_count=len(self.screenshot_queue)
                )
            
            # Create analysis prompt using external prompt system
            prompt = self.prompt_builder.get_queue_analysis_prompt(
                screenshot_count=len(self.screenshot_queue),
                include_examples=True
            )
            
            # Analyze with AI
            result = await self.vision_client.analyze_images(
                image_data_list=self.screenshot_queue,
                prompt=prompt,
                use_fallback=True
            )
            
            if result.success:
                self.last_analysis = result.data
                self.add_debug_message(f"✅ Analysis complete - cost: ${result.cost_estimate:.4f}")
                
                # Log analysis result data type for debugging
                self.log_error_to_file(
                    "Analysis result data inspection",
                    context={
                        "data_type": type(result.data).__name__,
                        "data_content": str(result.data)[:500] if result.data else "None",
                        "result_success": result.success,
                        "provider": str(result.provider) if hasattr(result, 'provider') else "Unknown"
                    }
                )
                
                # Process and validate the analysis results
                processing_success = self._show_analysis_results(result.data, result)
                if not processing_success:
                    self.add_debug_message("❌ Analysis data processing failed")
                    return False
                    
                return True
            else:
                self.add_debug_message(f"❌ Analysis failed: {result.error_message}")
                
                # Play error audio feedback
                if self.audio_manager:
                    self.audio_manager.play_audio_feedback(
                        AudioEvent.ERROR_OCCURRED,
                        error_type="analysis_failed"
                    )
                
                self.log_error_to_file(
                    "AI Analysis failed",
                    context={
                        "error_message": result.error_message,
                        "result_success": result.success,
                        "provider": str(result.provider) if hasattr(result, 'provider') else "Unknown"
                    }
                )
                return False
                
        except Exception as e:
            self.add_debug_message(f"❌ Analysis crashed: {str(e)}")
            
            # Play error audio feedback  
            if self.audio_manager:
                self.audio_manager.play_audio_feedback(
                    AudioEvent.ERROR_OCCURRED,
                    error_type="analysis_crashed"
                )
            
            self.log_error_to_file(
                "Analysis crashed with exception",
                exception=e,
                context={
                    "queue_size": len(self.screenshot_queue),
                    "analysis_method": "analyze_queue"
                }
            )
            return False
            
    def clear_queue(self):
        """Clear the screenshot queue."""
        if self.screenshot_queue:
            count = len(self.screenshot_queue)
            self.screenshot_queue.clear()
            self.last_analysis = None
            
            # Clean up saved screenshots
            for file in self.queue_folder.glob("queue_*.png"):
                file.unlink()
                
            self.add_debug_message(f"🗑️ Cleared {count} screenshots")
        else:
            self.add_debug_message("📋 Queue already empty")
    def show_config_menu(self):
        """Show configuration menu."""
        if not RICH_AVAILABLE:
            print("Configuration menu requires 'rich' library")
            return
            
        config_text = Text()
        config_text.append("⚙️ Configuration Menu\n", style="bold cyan")
        config_text.append("=" * 30 + "\n\n", style="dim")
        
        # Current settings
        config_text.append("📋 Current Settings:\n", style="bold yellow")
        config_text.append(f"  Primary Provider: {self.config_manager.config.extraction.primary_provider}\n", style="white")
        config_text.append(f"  Fallback Provider: {self.config_manager.config.extraction.fallback_provider}\n", style="white")
        
        hotkeys = self.config_manager.config.hotkeys
        config_text.append(f"  Screenshot Hotkey: {hotkeys.queue_screenshot}\n", style="white")
        config_text.append(f"  Analyze Hotkey: {hotkeys.analyze_queue}\n", style="white")
        
        # API status
        has_openai = (self.config_manager.config.openai and 
                     self.config_manager.config.openai.enabled and 
                     self.config_manager.config.openai.api_key)
        has_anthropic = (self.config_manager.config.anthropic and 
                        self.config_manager.config.anthropic.enabled and 
                        self.config_manager.config.anthropic.api_key)
        
        config_text.append(f"\n🔑 API Keys:\n", style="bold yellow")
        config_text.append(f"  OpenAI: {'✅ Configured' if has_openai else '❌ Not configured'}\n", 
                          style="green" if has_openai else "red")
        config_text.append(f"  Anthropic: {'✅ Configured' if has_anthropic else '❌ Not configured'}\n", 
                          style="green" if has_anthropic else "red")
        
        config_text.append(f"\n💡 Note: Use the GUI app to modify settings\n", style="dim")
        config_text.append(f"   Run: python bitcrafty-extractor.py\n", style="dim")
        
        panel = Panel(config_text, title="[bold cyan]Configuration[/bold cyan]", border_style="cyan")
        self.console.print(panel)
        
    def show_help(self):
        """Show detailed help."""
        if not RICH_AVAILABLE:
            print("Help requires 'rich' library")
            return
            
        help_text = Text()
        help_text.append("❓ BitCrafty-Extractor Help\n", style="bold blue")
        help_text.append("=" * 35 + "\n\n", style="dim")
        
        help_text.append("🎯 Purpose:\n", style="bold yellow")
        help_text.append("  Extract item details and crafting recipes from BitCraft\n", style="white")
        help_text.append("  screenshots using AI vision analysis.\n\n", style="white")
        
        help_text.append("🎮 Workflow:\n", style="bold yellow")
        help_text.append("  1. Take screenshots while playing (use hotkeys)\n", style="white")
        help_text.append("  2. Screenshots automatically queue on the right\n", style="white") 
        help_text.append("  3. When ready, run 'analyze' command\n", style="white")
        help_text.append("  4. Review detailed results\n", style="white")
        help_text.append("  5. Clear queue for next item/recipe\n\n", style="white")
        
        help_text.append("⌨️ Commands:\n", style="bold yellow")
        help_text.append("  analyze  - Analyze queued screenshots with AI\n", style="green")
        help_text.append("  clear    - Clear the screenshot queue\n", style="red")
        help_text.append("  config   - Show current configuration\n", style="cyan")
        help_text.append("  help     - Show this help\n", style="blue")
        help_text.append("  exit     - Exit the application\n\n", style="magenta")
        
        if self.config_manager:
            hotkeys = self.config_manager.config.hotkeys
            help_text.append("🎮 Global Hotkeys:\n", style="bold yellow")
            help_text.append(f"  {hotkeys.queue_screenshot} - Take screenshot (works in-game)\n", style="green")
            help_text.append(f"  {hotkeys.analyze_queue} - Analyze queue (works in-game)\n", style="green")
            help_text.append(f"  {hotkeys.quit_application} - Quit application gracefully\n", style="red")
            help_text.append("  💡 These work even when BitCraft has focus!\n\n", style="dim")
        
        help_text.append("🔧 Setup:\n", style="bold yellow")
        help_text.append("  • Configure API keys using the GUI first\n", style="white")
        help_text.append("  • Ensure BitCraft is running and visible\n", style="white")
        help_text.append("  • Use windowed fullscreen mode for best results\n", style="white")
        
        panel = Panel(help_text, title="[bold blue]Help & Instructions[/bold blue]", border_style="blue")
        self.console.print(panel)
    def _start_hotkeys(self):
        """Start global hotkey monitoring."""
        try:
            self.hotkey_handler.start_monitoring()
        except Exception as e:
            if RICH_AVAILABLE:
                self.console.print(f"[yellow]⚠️ Hotkeys failed to start: {str(e)}[/yellow]")
            
    def _stop_hotkeys(self):
        """Stop hotkey monitoring."""
        if self.hotkey_handler:
            try:
                self.hotkey_handler.stop_monitoring()
            except Exception as e:
                pass
                
    def _show_analysis_results(self, data: dict, result) -> bool:
        """Log analysis results to disk and update session tracking.
        
        Returns:
            bool: True if processing was successful, False if data validation failed
        """
        try:
            # Validate that data is a proper dictionary
            if not isinstance(data, dict):
                error_msg = f"Invalid analysis data format: {type(data).__name__}"
                self.add_debug_message(f"❌ {error_msg}")
                self.logger.error("Data validation failed", error=error_msg)
                self.log_error_to_file(
                    error_msg,
                    context={
                        "data_type": type(data).__name__,
                        "data_content": str(data)[:200] if data else "None",
                        "expected_type": "dict"
                    }
                )
                return False
            
            # Additional validation for required fields
            if 'raw_text' in data and len(data) == 1:
                error_msg = "Analysis returned raw text instead of structured data"
                self.add_debug_message(f"❌ {error_msg}")
                self.logger.error("Data validation failed", error=error_msg)
                self.log_error_to_file(
                    error_msg,
                    context={
                        "raw_text": data.get('raw_text', '')[:200],
                        "data_keys": list(data.keys())
                    }
                )
                return False
            
            # Get screenshot timestamps for export metadata
            screenshot_times = []
            for image_data in self.screenshot_queue:
                if hasattr(image_data, 'timestamp'):
                    screenshot_times.append(image_data.timestamp)
            
            # Use earliest screenshot time for extracted_at timestamp
            extracted_at = min(screenshot_times) if screenshot_times else datetime.now()
            
            # Process and export new items/crafts with proper timestamp
            export_stats = self.export_manager.process_extraction_results(data, extracted_at=extracted_at)
            
            # Validate export_stats is a dictionary
            if not isinstance(export_stats, dict):
                error_msg = f"Export manager returned invalid data type: {type(export_stats).__name__}"
                self.add_debug_message(f"❌ {error_msg}")
                self.log_error_to_file(
                    error_msg,
                    context={
                        "export_stats_type": type(export_stats).__name__,
                        "export_stats_content": str(export_stats)[:200] if export_stats else "None",
                        "expected_type": "dict"
                    }
                )
                # Use empty dict as fallback
                export_stats = {
                    'items_found_new': 0,
                    'items_found_duplicates': 0,
                    'crafts_found_new': 0,
                    'crafts_found_duplicates': 0,
                    'new_items_added': 0,
                    'new_crafts_added': 0,
                    'items_rejected': 0,
                    'crafts_rejected': 0
                }
            
            self.last_export_stats = export_stats
            
            # Update session tracking
            items = data.get('items_found', [])
            crafts = data.get('crafts_found', [])
            screenshots_processed = data.get('screenshots_processed', len(self.screenshot_queue))
            
            # Validate that items and crafts are lists
            if not isinstance(items, list):
                self.add_debug_message(f"⚠️ Warning: items_found is not a list, got {type(items).__name__}")
                items = []
            if not isinstance(crafts, list):
                self.add_debug_message(f"⚠️ Warning: crafts_found is not a list, got {type(crafts).__name__}")
                crafts = []
            
            # Add to session tracking (only append valid items/crafts)
            valid_items = []
            for i, item in enumerate(items):
                if isinstance(item, dict):
                    valid_items.append(item)
                else:
                    self.add_debug_message(f"⚠️ Warning: item {i} is not a dict: {type(item)} = {str(item)[:50]}")
            
            valid_crafts = []
            for i, craft in enumerate(crafts):
                if isinstance(craft, dict):
                    valid_crafts.append(craft)
                else:
                    self.add_debug_message(f"⚠️ Warning: craft {i} is not a dict: {type(craft)} = {str(craft)[:50]}")
            
            if len(valid_items) != len(items):
                self.add_debug_message(f"⚠️ Warning: {len(items) - len(valid_items)} non-dict items filtered out")
            if len(valid_crafts) != len(crafts):
                self.add_debug_message(f"⚠️ Warning: {len(crafts) - len(valid_crafts)} non-dict crafts filtered out")
            
            self.session_items_found.extend(valid_items)
            self.session_crafts_found.extend(valid_crafts)
            self.total_screenshots_analyzed += screenshots_processed
            self.total_cost += result.cost_estimate
            
            # Store analysis for queue panel display
            self.last_analysis = data
            
            # Log analysis to disk after updating session totals
            self._log_analysis_to_disk(data, result, export_stats, screenshot_times)
            
            # Show brief summary in debug messages with enhanced duplicate tracking
            items_count = len(valid_items)
            crafts_count = len(valid_crafts)
            
            # Safe access to export_stats with proper fallbacks
            try:
                items_new = export_stats.get('items_found_new', 0)
                if items_new == 0:
                    items_new = export_stats.get('new_items_added', 0)
                    
                crafts_new = export_stats.get('crafts_found_new', 0)
                if crafts_new == 0:
                    crafts_new = export_stats.get('new_crafts_added', 0)
                    
                items_duplicates = export_stats.get('items_found_duplicates', 0)
                crafts_duplicates = export_stats.get('crafts_found_duplicates', 0)
            except Exception as e:
                self.add_debug_message(f"❌ Error accessing export_stats: {e}")
                items_new = 0
                crafts_new = 0
                items_duplicates = 0
                crafts_duplicates = 0
            
            # Enhanced summary message
            summary_parts = []
            if items_count > 0:
                if items_new < items_count:
                    summary_parts.append(f"{items_count} items ({items_new} new)")
                else:
                    summary_parts.append(f"{items_count} items")
            
            if crafts_count > 0:
                if crafts_new < crafts_count:
                    summary_parts.append(f"{crafts_count} crafts ({crafts_new} new)")
                else:
                    summary_parts.append(f"{crafts_count} crafts")
            
            summary = ", ".join(summary_parts) if summary_parts else "no data"
            self.add_debug_message(f"✅ Analysis complete: {summary} (${result.cost_estimate:.3f})")
            
            # Show duplicate information if any found
            total_duplicates = items_duplicates + crafts_duplicates
            if total_duplicates > 0:
                self.add_debug_message(f"🔄 Duplicates skipped: {total_duplicates} ({items_duplicates} items, {crafts_duplicates} crafts)")
            
            # Show validation statistics if any items were rejected
            try:
                items_rejected = export_stats.get('items_rejected', 0)
                crafts_rejected = export_stats.get('crafts_rejected', 0)
                if items_rejected > 0 or crafts_rejected > 0:
                    self.add_debug_message(f"⚠️ Validation: {items_rejected} items, {crafts_rejected} crafts rejected (confidence < {export_stats.get('min_confidence_threshold', 0.7)})")
            except Exception as e:
                self.add_debug_message(f"❌ Error accessing validation stats: {e}")
            
            try:
                if export_stats['new_items_added'] > 0 or export_stats['new_crafts_added'] > 0:
                    self.add_debug_message(f"📤 Exported: {export_stats['new_items_added']} new items, {export_stats['new_crafts_added']} new crafts")
                else:
                    self.add_debug_message("ℹ️ No new data exported (already in database)")
            except Exception as e:
                self.add_debug_message(f"❌ Error accessing export counts: {e}")
            
            # Show where detailed results are logged
            self.add_debug_message(f"📄 Full results: /analysis_logs/{self.analysis_log_file.name}")
            
            # Play audio feedback for successful analysis completion
            if self.audio_manager:
                self.audio_manager.play_audio_feedback(
                    AudioEvent.ANALYSIS_COMPLETE,
                    success=True,
                    items_count=items_count,
                    crafts_count=crafts_count
                )
            
            # Return success
            return True
            
        except Exception as e:
            error_msg = f"Exception in _show_analysis_results: {str(e)}"
            self.add_debug_message(f"❌ {error_msg}")
            self.log_error_to_file(
                error_msg,
                exception=e,
                context={
                    "data_type": type(data).__name__ if data else "None",
                    "data_content": str(data)[:200] if data else "None",
                    "method": "_show_analysis_results"
                }
            )
            if self.logger:
                self.logger.error("Exception in _show_analysis_results", error=str(e))
            return False
        
    def _log_analysis_to_disk(self, data: dict, result, export_stats: dict, screenshot_times: List[datetime]):
        """Log analysis results to disk instead of displaying in console."""
        try:
            # Create log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "session_info": {
                    "analysis_number": len(self.analysis_log_entries) + 1,
                    "screenshots_in_queue": len(self.screenshot_queue),
                    "screenshot_timestamps": [t.isoformat() for t in screenshot_times]
                },
                "ai_analysis": {
                    "provider": str(result.provider),
                    "confidence": result.confidence,
                    "cost_estimate": result.cost_estimate,
                    "screenshots_processed": data.get('screenshots_processed', 0),
                    "total_confidence": data.get('total_confidence', result.confidence)
                },
                "extraction_results": {
                    "items_found": data.get('items_found', []),
                    "crafts_found": data.get('crafts_found', []),
                    "summary": {
                        "total_items": len(data.get('items_found', [])),
                        "total_crafts": len(data.get('crafts_found', [])),
                    }
                },
                "export_statistics": export_stats,
                "session_totals": {
                    "total_items_found": len(self.session_items_found),
                    "total_crafts_found": len(self.session_crafts_found),
                    "total_screenshots_analyzed": self.total_screenshots_analyzed,
                    "total_cost": self.total_cost
                }
            }
            
            # Add to memory log
            self.analysis_log_entries.append(log_entry)
            
            # Write to disk immediately for persistence
            self._write_analysis_log_to_disk()
            
            # Log success message
            self.add_debug_message(f"📝 Analysis logged to: {self.analysis_log_file.name}")
            
        except Exception as e:
            self.add_debug_message(f"❌ Failed to log analysis: {str(e)}")
            if self.logger:
                self.logger.error("Analysis logging failed", error=str(e))
    
    def _write_analysis_log_to_disk(self):
        """Write analysis log entries to disk."""
        try:
            log_data = {
                "session_metadata": {
                    "session_start": datetime.now().isoformat(),
                    "extractor_version": "2.0.0",
                    "total_analyses": len(self.analysis_log_entries)
                },
                "analyses": self.analysis_log_entries
            }
            
            with open(self.analysis_log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            if self.logger:
                self.logger.error("Failed to write analysis log", error=str(e))
    
    def _get_analysis_log_summary(self) -> str:
        """Get a brief summary of the current analysis log for display."""
        if not self.analysis_log_entries:
            return "No analyses logged yet"
            
        last_entry = self.analysis_log_entries[-1]
        total_items = sum(len(entry['extraction_results']['items_found']) for entry in self.analysis_log_entries)
        total_crafts = sum(len(entry['extraction_results']['crafts_found']) for entry in self.analysis_log_entries)
        total_cost = sum(entry['ai_analysis']['cost_estimate'] for entry in self.analysis_log_entries)
        
        return (f"Log: {len(self.analysis_log_entries)} analyses | "
                f"{total_items} items, {total_crafts} crafts | "
                f"${total_cost:.3f} total")
        
    async def _clear_queue_and_cleanup(self):
        """Clear screenshot queue and remove files from disk."""
        try:
            # Remove screenshot files from disk
            for image_data in self.screenshot_queue:
                if hasattr(image_data, 'file_path') and image_data.file_path:
                    try:
                        if image_data.file_path.exists():
                            image_data.file_path.unlink()
                            self.logger.debug("Removed screenshot file", path=str(image_data.file_path))
                    except Exception as e:
                        self.logger.warning("Failed to remove screenshot file", 
                                          path=str(image_data.file_path), error=str(e))
            
            # Clear the queue
            queue_size = len(self.screenshot_queue)
            self.screenshot_queue.clear()
            
            self.logger.info("Queue cleared and files cleaned up", files_removed=queue_size)
            
        except Exception as e:
            self.logger.error("Error during queue cleanup", error=str(e))
            
    async def run(self):
        """Main CLI loop with live display."""
        # Store event loop reference for thread-safe hotkey callbacks
        self.loop = asyncio.get_running_loop()
        
        await self.initialize()
        
        if not RICH_AVAILABLE:
            return await self._basic_run()
        
        self.add_debug_message("🚀 BitCrafty-Extractor started")
        self.add_debug_message("💡 Global hotkeys active - use while playing!")
        self.add_debug_message(f"📄 Analysis results will be logged to: {self.analysis_log_file.name}")
        
        try:
            # Use a simple Live display with reduced refresh rate to prevent scrolling issues
            with Live(
                self.layout, 
                console=self.console, 
                refresh_per_second=1,  # Reduced from 2 to prevent UI scrolling issues
                auto_refresh=True
            ) as live:
                self.live_display = live
                
                while self.running:
                    # Update display less frequently to prevent scrolling issues
                    self.update_display()
                    
                    # Increased sleep time to reduce update frequency
                    await asyncio.sleep(2.0)  # Increased from 1.0 to 2.0 seconds
                        
        except KeyboardInterrupt:
            self.add_debug_message("👋 Interrupted by user")
        except Exception as e:
            self.add_debug_message(f"❌ Display error: {str(e)}")
            
        # Clean up
        self._stop_hotkeys()
        
        # Clean up audio manager
        if self.audio_manager:
            self.audio_manager.cleanup()
        
        self.console.print("\n🛑 BitCrafty-Extractor stopped")
        
        # Print final session analysis summary
        self._print_final_session_summary()
        
    async def _basic_run(self):
        """Basic CLI mode without rich interface."""
        print("Commands: analyze, clear, config, help, exit")
        while True:
            try:
                command = input("bitcrafty> ").strip().lower()
                if command in ['exit', 'quit', 'x']:
                    break
                elif command in ['help', 'h']:
                    print("Commands: analyze, clear, config, help, exit")
                else:
                    print(f"Unknown command: {command}")
            except KeyboardInterrupt:
                break

    async def _validate_openai_key(self) -> bool:
        """Validate OpenAI API key using their health check."""
        try:
            import aiohttp
            
            headers = {
                "Authorization": f"Bearer {self.config_manager.config.openai.api_key}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                # Use the models endpoint as a health check
                async with session.get("https://api.openai.com/v1/models", headers=headers) as response:
                    return response.status == 200
                    
        except Exception as e:
            if self.logger:
                self.logger.debug("OpenAI key validation failed", error=str(e))
            return False
    
    async def _validate_anthropic_key(self) -> bool:
        """Validate Anthropic API key using their health check."""
        try:
            import aiohttp
            
            headers = {
                "x-api-key": self.config_manager.config.anthropic.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            # Simple test request with minimal tokens
            data = {
                "model": "claude-3-haiku-20240307",  # Use cheapest model for validation
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "Hi"}]
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.post("https://api.anthropic.com/v1/messages", 
                                       headers=headers, json=data) as response:
                    return response.status == 200
                    
        except Exception as e:
            if self.logger:
                self.logger.debug("Anthropic key validation failed", error=str(e))
            return False

    def _print_final_session_summary(self):
        """Print final session analysis results summary."""
        if not RICH_AVAILABLE:
            return
            
        # Print session summary
        summary_text = Text()
        summary_text.append("\n📊 FINAL SESSION ANALYSIS RESULTS\n", style="bold blue")
        summary_text.append("=" * 50 + "\n\n", style="dim")
        
        # Session statistics
        summary_text.append("📈 Session Statistics:\n", style="bold yellow")
        summary_text.append(f"  🍎 Total Items Found: {len(self.session_items_found)}\n", style="green")
        summary_text.append(f"  🔨 Total Crafts Found: {len(self.session_crafts_found)}\n", style="yellow")
        summary_text.append(f"  📸 Screenshots Analyzed: {self.total_screenshots_analyzed}\n", style="cyan")
        summary_text.append(f"  💰 Total Cost: ${self.total_cost:.4f}\n\n", style="red")
        
        # Export statistics
        export_stats = self.export_manager.get_stats()
        session_stats = self.export_manager.get_session_stats()
        summary_text.append("💾 Export Database Status:\n", style="bold cyan")
        summary_text.append(f"  📦 Total Items in Database: {export_stats['total_items']}\n", style="white")
        summary_text.append(f"  🔧 Total Crafts in Database: {export_stats['total_crafts']}\n", style="white")
        summary_text.append(f"  📁 Files: /exports/items.json, /exports/crafts.json\n\n", style="dim")
        
        # Total analysis details for the session
        summary_text.append("🔍 Total Analysis Details:\n", style="bold magenta")
        summary_text.append(f"  📦 New Items This Session: {session_stats['session_new_items_count']}\n", style="green")
        summary_text.append(f"  🔧 New Crafts This Session: {session_stats['session_new_crafts_count']}\n", style="yellow")
        
        # Show names in a fixed-height format to prevent UI scrolling issues
        if session_stats['session_new_items_count'] > 0:
            try:
                item_names = session_stats['session_new_item_names']
                # Ensure all items are strings and filter out empty ones
                item_names = [str(name) for name in item_names if name]
                # Limit to first 3 items to maintain consistent height
                display_items = item_names[:3]
                if len(item_names) > 3:
                    summary_text.append(f"  Items: {', '.join(display_items)}... (+{len(item_names)-3} more)\n", style="dim")
                else:
                    summary_text.append(f"  Items: {', '.join(display_items)}\n", style="dim")
            except Exception as e:
                summary_text.append(f"  Items: Error displaying names ({e})\n", style="dim")
        
        if session_stats['session_new_crafts_count'] > 0:
            try:
                craft_names = session_stats['session_new_craft_names']
                # Ensure all crafts are strings and filter out empty ones
                craft_names = [str(name) for name in craft_names if name]
                # Limit to first 3 crafts to maintain consistent height
                display_crafts = craft_names[:3]
                if len(craft_names) > 3:
                    summary_text.append(f"  Crafts: {', '.join(display_crafts)}... (+{len(craft_names)-3} more)\n", style="dim")
                else:
                    summary_text.append(f"  Crafts: {', '.join(display_crafts)}\n", style="dim")
            except Exception as e:
                summary_text.append(f"  Crafts: Error displaying names ({e})\n", style="dim")
        
        # Always show this line to maintain consistent height
        if session_stats['session_new_items_count'] == 0 and session_stats['session_new_crafts_count'] == 0:
            summary_text.append("  No new items or crafts discovered this session\n", style="dim")
        
        summary_text.append("\n")
        
        # Analysis log information
        summary_text.append("📄 Analysis Log Details:\n", style="bold cyan")
        summary_text.append(f"  📝 Total Analyses Logged: {len(self.analysis_log_entries)}\n", style="white")
        summary_text.append(f"  📁 Log File: /analysis_logs/{self.analysis_log_file.name}\n", style="white")
        summary_text.append(f"  💡 Detailed results and metadata preserved\n\n", style="dim")
        
        summary_text.append("\n🎉 Thank you for using BitCrafty-Extractor!\n", style="bold green")
        summary_text.append("   � GitHub: https://github.com/Kyzael/BitCrafty-Extractor\n", style="blue")
        summary_text.append("   �📦 Export data: /exports/ folder for BitCrafty integration\n", style="dim")
        summary_text.append("   📄 Analysis logs: /analysis_logs/ folder for detailed review\n", style="dim")
        
        panel = Panel(summary_text, title="[bold blue]Session Complete[/bold blue]", border_style="blue")
        self.console.print(panel)

    def _create_analysis_log_readme(self):
        """Create a README file explaining the analysis log format."""
        readme_path = self.analysis_log_folder / "README.md"
        if readme_path.exists():
            return  # Don't overwrite existing README
            
        readme_content = """# BitCrafty-Extractor Analysis Logs

This folder contains detailed analysis logs from BitCrafty-Extractor sessions.

## File Format

Each analysis session creates a JSON log file with the following structure:

```json
{
  "session_metadata": {
    "session_start": "2024-12-29T10:30:00.123456",
    "extractor_version": "2.0.0",
    "total_analyses": 3
  },
  "analyses": [
    {
      "timestamp": "2024-12-29T10:35:15.789012",
      "session_info": {
        "analysis_number": 1,
        "screenshots_in_queue": 2,
        "screenshot_timestamps": ["2024-12-29T10:35:10.123456", "2024-12-29T10:35:12.654321"]
      },
      "ai_analysis": {
        "provider": "AIProviderType.OPENAI",
        "confidence": 85.5,
        "cost_estimate": 0.0125,
        "screenshots_processed": 2,
        "total_confidence": 82.3
      },
      "extraction_results": {
        "items_found": [
          {
            "name": "Stone Axe",
            "tier": "Tier 1",
            "rarity": "common",
            "confidence": 90.2,
            "description": "A basic stone cutting tool...",
            // ... other item properties
          }
        ],
        "crafts_found": [
          {
            "name": "Stone Axe Recipe",
            "confidence": 88.7,
            "requirements": {
              "profession": "Tool Making",
              "level": 1
            },
            "materials": [
              {"item": "Stone", "qty": 2},
              {"item": "Wood", "qty": 1}
            ],
            "outputs": [
              {"item": "Stone Axe", "qty": 1}
            ]
            // ... other craft properties
          }
        ],
        "summary": {
          "total_items": 1,
          "total_crafts": 1
        }
      },
      "export_statistics": {
        "new_items_added": 1,
        "new_crafts_added": 1,
        "total_items": 15,
        "total_crafts": 8,
        "duplicates_found": 0
      },
      "session_totals": {
        "total_items_found": 1,
        "total_crafts_found": 1,
        "total_screenshots_analyzed": 2,
        "total_cost": 0.0125
      }
    }
    // ... more analyses
  ]
}
```

## Key Features

- **Complete Analysis History**: Every AI analysis is preserved with full details
- **Metadata Tracking**: Screenshot timestamps, costs, providers, confidence scores
- **Export Integration**: Shows what was exported vs. already in database
- **Session Tracking**: Cumulative statistics throughout the session
- **Searchable Format**: JSON structure allows easy querying and processing

## Usage

These logs are perfect for:
- Reviewing analysis quality and confidence scores
- Tracking extraction costs and efficiency
- Debugging AI analysis issues
- Building analytics on extraction patterns
- Preserving detailed results that would be lost in console output

The console interface only shows brief summaries - these logs contain the complete detailed results.
"""
        
        try:
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
        except Exception as e:
            if self.logger:
                self.logger.warning("Failed to create analysis log README", error=str(e))

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="BitCrafty-Extractor: AI-powered game data extraction tool for BitCraft",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  bitcrafty-extractor                     # Launch the console interface (recommended)
  python bitcrafty-extractor.py          # Alternative launch method
  python -m bitcrafty_extractor          # Package entry point
  
Global Hotkeys (work while playing BitCraft):
  Alt+E - Take screenshot and add to queue
  Alt+Q - Analyze screenshot queue with AI
  Alt+F - Quit application gracefully

For more information, visit: https://github.com/Kyzael/BitCrafty-Extractor
        """
    )
    
    parser.add_argument(
        "--version", 
        action="version", 
        version="BitCrafty-Extractor 2.0.0"
    )
    
    return parser.parse_args()

async def main():
    """Main application entry point."""
    # Parse command line arguments (includes help handling)
    args = parse_arguments()
    
    extractor = BitCraftyExtractor()
    await extractor.run()


if __name__ == "__main__":
    asyncio.run(main())
