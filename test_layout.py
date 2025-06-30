#!/usr/bin/env python3
"""
Quick test for the new 4-panel layout functionality.
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.text import Text
    
    # Test creating the new layout structure
    print("Testing new 4-panel layout...")
    
    def create_test_layout():
        """Create the four-section layout with dedicated session stats."""
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
    
    def create_test_panels():
        """Create test panels for each section."""
        commands_panel = Panel(Text("Commands Panel\n🚀 BitCrafty-Extractor", style="bold blue"), 
                              title="Commands", border_style="blue")
        
        stats_panel = Panel(Text("Session Stats Panel\n📊 0 items, 0 crafts", style="bold magenta"), 
                           title="Session Statistics", border_style="magenta")
        
        queue_panel = Panel(Text("Queue Panel\n📦 No screenshots queued", style="bold green"), 
                           title="Live Queue Status", border_style="green")
        
        debug_panel = Panel(Text("Debug Panel\n🔧 Debug messages here", style="bold cyan"), 
                           title="Status & Debug", border_style="cyan")
        
        return commands_panel, stats_panel, queue_panel, debug_panel
    
    # Create layout and panels
    layout = create_test_layout()
    commands_panel, stats_panel, queue_panel, debug_panel = create_test_panels()
    
    # Update layout with panels
    layout["commands"].update(commands_panel)
    layout["session_stats"].update(stats_panel)
    layout["queue"].update(queue_panel)
    layout["debug"].update(debug_panel)
    
    # Display the layout
    console = Console()
    console.print(layout)
    print("\n✅ Layout test completed successfully!")
    print("📋 Layout structure:")
    print("  ├── Commands Panel (top-left, 3/4 height)")
    print("  ├── Session Stats Panel (bottom-left, 1/4 height)")
    print("  ├── Queue Panel (right side)")
    print("  └── Debug Panel (bottom, full width)")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure Rich library is installed: pip install rich")
except Exception as e:
    print(f"❌ Test error: {e}")
    import traceback
    traceback.print_exc()
