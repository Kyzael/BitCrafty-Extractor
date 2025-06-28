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

import argparse
import sys
import asyncio
import signal
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from bitcrafty_extractor.config.config_manager import ConfigManager
from bitcrafty_extractor.ai_analysis.vision_client import VisionClient, ImageData
from bitcrafty_extractor.capture.window_capture import WindowCapture
from bitcrafty_extractor.capture.hotkey_handler import HotkeyHandler

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
        self.screenshot_queue: List[ImageData] = []
        self.queue_folder = Path("queue_screenshots")
        self.queue_folder.mkdir(exist_ok=True)
        self.logger = None
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
        
    def create_layout(self):
        """Create the three-section layout."""
        if not RICH_AVAILABLE:
            return None
            
        layout = Layout()
        layout.split_column(
            Layout(name="main", ratio=4),
            Layout(name="debug", ratio=1)
        )
        layout["main"].split_row(
            Layout(name="commands", ratio=1),
            Layout(name="queue", ratio=1)
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
        
        # Session Statistics
        commands_text.append("📊 Session Stats:\n", style="bold magenta")
        commands_text.append(f"  🍎 Items Found: {len(self.session_items_found)}\n", style="green")
        commands_text.append(f"  🔨 Crafts Found: {len(self.session_crafts_found)}\n", style="yellow")
        commands_text.append(f"  📸 Screenshots: {self.total_screenshots_analyzed}\n", style="cyan")
        commands_text.append(f"  💰 Est. Cost: ${self.total_cost:.3f}\n", style="red")
        
        return Panel(commands_text, title="[bold blue]BitCrafty-Extractor[/bold blue]", border_style="blue")
        
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
        header_text.append(f"� Queue: {len(self.screenshot_queue)}\n", style="bold yellow")
        header_text.append("=" * 40 + "\n", style="dim")
        
        if not self.screenshot_queue:
            # Empty queue display
            queue_text = Text()
            queue_text.append("🎯 No screenshots queued\n\n", style="yellow")
            queue_text.append("Ready for screenshots!", style="dim")
            
            content = Layout()
            content.split_column(
                Layout(Panel(header_text, border_style="dim"), ratio=1),
                Layout(Panel(queue_text, border_style="dim"), ratio=3)
            )
            
            return Panel(content, title="[bold green]Live Queue Status[/bold green]", border_style="green")
        
        # Create table for queue items
        table = Table(show_header=True, header_style="bold green", box=None)
        table.add_column("#", style="dim", width=3)
        table.add_column("Timestamp", style="cyan", width=10)
        table.add_column("Size", style="yellow", width=12)
        table.add_column("Status", style="white", width=15)
        
        for i, image_data in enumerate(self.screenshot_queue, 1):
            # Get timestamp from when it was added (approximate)
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Get image size
            if hasattr(image_data, 'image_array') and image_data.image_array is not None:
                h, w = image_data.image_array.shape[:2]
                size = f"{w}x{h}"
            else:
                size = "Unknown"
            
            # Status
            status = "✅ Ready"
            
            table.add_row(str(i), timestamp, size, status)
        
        # Add analysis results if available
        if self.last_analysis:
            analysis_text = Text()
            analysis_text.append("📊 Last Analysis:\n", style="bold magenta")
            items = self.last_analysis.get('items_found', [])
            crafts = self.last_analysis.get('crafts_found', [])
            analysis_text.append(f"📦 Items: {len(items)} | ", style="white")
            analysis_text.append(f"🔧 Recipes: {len(crafts)}\n", style="white")
            confidence = self.last_analysis.get('total_confidence', 0)
            analysis_text.append(f"📈 Confidence: {confidence:.2f}", style="white")
        else:
            analysis_text = Text()
            analysis_text.append("🎯 Ready to analyze!", style="bold yellow")
        
        # Combine everything
        content = Layout()
        content.split_column(
            Layout(Panel(header_text, border_style="dim"), ratio=1),
            Layout(table, ratio=3),
            Layout(Panel(analysis_text, border_style="dim"), ratio=1)
        )
        
        return Panel(content, title="[bold green]Live Queue Status[/bold green]", border_style="green")
        
    def update_debug_panel(self):
        """Update the bottom debug panel."""
        if not RICH_AVAILABLE:
            return Panel("Debug not available")
        
        debug_text = Text()
        debug_text.append("🔧 Debug Log", style="bold magenta")
        debug_text.append("\n" + "=" * 50 + "\n", style="dim")
        
        if not self.debug_messages:
            debug_text.append("🎮 Hotkeys active - take screenshots while playing!", style="cyan")
        else:
            # Show last few debug messages
            for msg in self.debug_messages[-5:]:  # Show last 5 messages
                debug_text.append(f"{msg}\n", style="white")
        
        return Panel(debug_text, title="[bold magenta]Status & Debug[/bold magenta]", border_style="magenta")
        
    def add_debug_message(self, message: str):
        """Add a debug message to the log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}"
        self.debug_messages.append(formatted_msg)
        
        # Keep only recent messages
        if len(self.debug_messages) > self.max_debug_messages:
            self.debug_messages = self.debug_messages[-self.max_debug_messages:]
        
    def update_display(self):
        """Update the entire display."""
        if not RICH_AVAILABLE or not self.layout:
            return
            
        self.layout["commands"].update(self.update_command_panel())
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
        """Check if configuration is valid."""
        has_openai = (self.config_manager.config.openai and 
                     self.config_manager.config.openai.enabled and 
                     self.config_manager.config.openai.api_key)
        has_anthropic = (self.config_manager.config.anthropic and 
                        self.config_manager.config.anthropic.enabled and 
                        self.config_manager.config.anthropic.api_key)
        
        if not (has_openai or has_anthropic):
            print("❌ No API keys configured!")
            print("💡 Please run the GUI app first to configure API keys.")
            print("   Or manually edit: config/user.yaml")
            sys.exit(1)
            
        print(f"✅ Configuration loaded")
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
            
        self.add_debug_message(f"🤖 Hotkey pressed - analyzing {len(self.screenshot_queue)} screenshots")
        
        # Schedule analysis in the event loop
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(self._hotkey_analyze_async())
        except RuntimeError:
            self.add_debug_message("❌ Could not schedule analysis")
            
    async def _hotkey_analyze_async(self):
        """Async analysis for hotkey callback."""
        try:
            success = await self.analyze_queue()
            if success:
                self.add_debug_message("✅ Analysis completed successfully")
            else:
                self.add_debug_message("❌ Analysis failed")
        except Exception as e:
            self.add_debug_message(f"❌ Analysis error: {str(e)}")
            if self.logger:
                self.logger.error("Hotkey analysis error", error=str(e))
            
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
            window_info = self.window_capture.find_bitcraft_window()
            if not window_info:
                return False
                
            # Capture screenshot
            screenshot = self.window_capture.capture_window(window_info)
            if screenshot is None:
                return False
                
            # Add to queue
            timestamp = datetime.now().strftime("%H%M%S")
            image_data = ImageData(image_array=screenshot)
            self.screenshot_queue.append(image_data)
            
            # Save screenshot for reference
            filename = f"queue_{len(self.screenshot_queue):03d}_{timestamp}.png"
            filepath = self.queue_folder / filename
            cv2.imwrite(str(filepath), screenshot)
            
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
            
            # Create analysis prompt
            prompt = self._create_analysis_prompt()
            
            # Analyze with AI
            result = await self.vision_client.analyze_images(
                image_data_list=self.screenshot_queue,
                prompt=prompt,
                use_fallback=True
            )
            
            if result.success:
                self.last_analysis = result.data
                self.add_debug_message(f"✅ Analysis complete - cost: ${result.cost_estimate:.4f}")
                self._show_analysis_results(result.data, result)
                return True
            else:
                self.add_debug_message(f"❌ Analysis failed: {result.error_message}")
                return False
                
        except Exception as e:
            self.add_debug_message(f"❌ Analysis crashed: {str(e)}")
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
                
    def _create_analysis_prompt(self) -> str:
        """Create analysis prompt for the queue."""
        return f"""
TASK: Analyze {len(self.screenshot_queue)} screenshots and extract item details and crafting recipes.

INSTRUCTIONS:
1. Look for item tooltips, descriptions, and details
2. Look for crafting interfaces and recipe views
3. Pay careful attention to quantities - count exactly what you see
4. Extract complete item details AND any crafting recipes shown

REQUIRED JSON RESPONSE:
{{
  "analysis_type": "queue_analysis",
  "screenshots_processed": {len(self.screenshot_queue)},
  "items_found": [
    {{
      "type": "item",
      "name": "string - exact item name",
      "tier": number or null,
      "rarity": "string",
      "description": "string - item description", 
      "uses": "string - what the item is used for",
      "confidence": 0.0-1.0
    }}
  ],
  "crafts_found": [
    {{
      "type": "craft_recipe", 
      "name": "string - recipe name",
      "requirements": {{
        "profession": "string",
        "tool": "string or null",
        "building": "string or null"
      }},
      "input_materials": [
        {{
          "item_name": "string",
          "quantity": number
        }}
      ],
      "output_materials": [
        {{
          "item_name": "string", 
          "quantity": number,
          "variable_quantity": boolean
        }}
      ],
      "confidence": 0.0-1.0
    }}
  ],
  "total_confidence": 0.0-1.0
}}

Analyze all screenshots and extract complete item and recipe data with accurate quantities.
"""

    def _show_analysis_results(self, data: dict, result):
        """Display analysis results."""
        if not RICH_AVAILABLE:
            return
            
        # Update session tracking
        items = data.get('items_found', [])
        crafts = data.get('crafts_found', [])
        screenshots_processed = data.get('screenshots_processed', len(self.screenshot_queue))
        
        # Add to session tracking
        self.session_items_found.extend(items)
        self.session_crafts_found.extend(crafts)
        self.total_screenshots_analyzed += screenshots_processed
        self.total_cost += result.cost_estimate
        
        # Set result display mode
        self.show_analysis_results = True
        
        # Create detailed results panel
        results_text = Text()
        results_text.append("🎉 ANALYSIS COMPLETE\n", style="bold green")
        results_text.append("=" * 30 + "\n\n", style="dim")
        
        # Summary
        results_text.append(f"📊 Summary:\n", style="bold yellow")
        results_text.append(f"  Provider: {result.provider}\n", style="white")
        results_text.append(f"  Confidence: {result.confidence:.2f}\n", style="white")
        results_text.append(f"  Cost: ${result.cost_estimate:.4f}\n", style="white")
        results_text.append(f"  Screenshots: {data.get('screenshots_processed', 0)}\n\n", style="white")
        
        # Items found
        items = data.get('items_found', [])
        if items:
            results_text.append(f"📦 ITEMS FOUND ({len(items)}):\n", style="bold cyan")
            for i, item in enumerate(items, 1):
                name = item.get('name', 'Unknown')
                tier = item.get('tier', 'Unknown')
                rarity = item.get('rarity', 'unknown')
                confidence = item.get('confidence', 0)
                results_text.append(f"  {i}. {name}\n", style="bold white")
                results_text.append(f"     Tier: {tier} | Rarity: {rarity.title()}\n", style="white")
                results_text.append(f"     Confidence: {confidence:.2f}\n", style="white")
                description = item.get('description', 'No description')
                if len(description) > 50:
                    description = description[:50] + "..."
                results_text.append(f"     {description}\n\n", style="dim")
        
        # Crafts found
        crafts = data.get('crafts_found', [])
        if crafts:
            results_text.append(f"🔧 RECIPES FOUND ({len(crafts)}):\n", style="bold magenta")
            for i, craft in enumerate(crafts, 1):
                name = craft.get('name', 'Unknown')
                confidence = craft.get('confidence', 0)
                results_text.append(f"  {i}. {name}\n", style="bold white")
                results_text.append(f"     Confidence: {confidence:.2f}\n", style="white")
                
                # Requirements
                reqs = craft.get('requirements', {})
                if reqs:
                    profession = reqs.get('profession', 'Unknown')
                    results_text.append(f"     Profession: {profession}\n", style="white")
                
                # Materials
                inputs = craft.get('input_materials', [])
                outputs = craft.get('output_materials', [])
                if inputs:
                    materials = ", ".join([f"{m.get('quantity', 1)}x {m.get('item_name', 'Unknown')}" for m in inputs])
                    results_text.append(f"     Inputs: {materials}\n", style="green")
                if outputs:
                    materials = ", ".join([f"{m.get('quantity', 1)}x {m.get('item_name', 'Unknown')}" for m in outputs])
                    results_text.append(f"     Outputs: {materials}\n", style="cyan")
                results_text.append("\n")
        
        # Overall confidence
        total_confidence = data.get('total_confidence', result.confidence)
        results_text.append(f"📈 Overall Confidence: {total_confidence:.2f}\n", style="bold green")
        
        panel = Panel(results_text, title="[bold green]Analysis Results[/bold green]", border_style="green")
        self.console.print(panel)
        
    async def run(self):
        """Main CLI loop with live display."""
        await self.initialize()
        
        if not RICH_AVAILABLE:
            return await self._basic_run()
        
        self.add_debug_message("🚀 BitCrafty-Extractor started")
        self.add_debug_message("💡 Global hotkeys active - use while playing!")
        
        try:
            # Use a simple Live display without screen complications
            with Live(
                self.layout, 
                console=self.console, 
                refresh_per_second=2,
                auto_refresh=True
            ) as live:
                self.live_display = live
                
                while self.running:
                    # Update display
                    self.update_display()
                    
                    # Just wait and let hotkeys do the work
                    # No input prompts = no scrolling issues
                    await asyncio.sleep(1.0)
                        
        except KeyboardInterrupt:
            self.add_debug_message("👋 Interrupted by user")
        except Exception as e:
            self.add_debug_message(f"❌ Display error: {str(e)}")
            
        # Clean up
        self._stop_hotkeys()
        self.console.print("\n🛑 BitCrafty-Extractor stopped")
        
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
  Ctrl+Shift+E - Take screenshot and add to queue
  Ctrl+Shift+X - Analyze screenshot queue with AI
  Ctrl+Shift+Q - Quit application gracefully

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
