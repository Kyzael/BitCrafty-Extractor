"""BitCrafty-Extractor: AI-powered data extraction for BitCraft game.

This package provides a console-based application with global hotkeys for 
extracting item and crafting data from BitCraft using AI vision analysis.

Main Components:
- BitCraftyExtractor: Main console application class
- ConfigManager: Configuration management
- VisionClient: AI vision analysis
- HotkeyHandler: Global hotkey system
- WindowCapture: Game window capture
"""

__version__ = "2.0.0"
__author__ = "BitCrafty Team"

import asyncio
import sys
from pathlib import Path

def main():
    """Entry point for the bitcrafty-extractor console application."""
    # Import and run the main application
    try:
        # Add project root to path for the main application import
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))
        
        # Import the main application
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "bitcrafty_extractor_main", 
            project_root / "bitcrafty-extractor.py"
        )
        extractor_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(extractor_module)
        
        # Run the main function
        asyncio.run(extractor_module.main())
        
    except ImportError as e:
        print(f"❌ Failed to import main application: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Application error: {e}")
        sys.exit(1)

# Import main classes for external use (optional)
try:
    # Add project root to path for the main application import
    _project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(_project_root))
    
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "bitcrafty_extractor_main", 
        _project_root / "bitcrafty-extractor.py"
    )
    _extractor_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_extractor_module)
    
    BitCraftyExtractor = _extractor_module.BitCraftyExtractor
    
except ImportError:
    # Fallback if import fails
    class BitCraftyExtractor:
        def __init__(self):
            raise ImportError("Could not import main application")

# Export public API
__all__ = [
    "main",
    "BitCraftyExtractor", 
    "__version__",
    "__author__"
]
