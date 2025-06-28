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

__version__ = "1.0.0"
__author__ = "BitCrafty Team"

# Import main classes for external use
from pathlib import Path
import sys

# Add project root to path for the main application import
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

try:
    # Import the main application class from the root level
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "bitcrafty_extractor_main", 
        _project_root / "bitcrafty-extractor.py"
    )
    _extractor_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_extractor_module)
    
    BitCraftyExtractor = _extractor_module.BitCraftyExtractor
    
except ImportError as e:
    # Fallback if import fails
    class BitCraftyExtractor:
        def __init__(self):
            raise ImportError(f"Could not import main application: {e}")

# Export public API
__all__ = [
    "BitCraftyExtractor",
    "__version__",
    "__author__"
]
