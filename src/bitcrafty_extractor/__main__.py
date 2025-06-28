#!/usr/bin/env python3
"""
BitCrafty-Extractor main entry point

This module provides the main entry point for the BitCrafty-Extractor package.
It launches the console-based extractor application.
"""

import sys
import asyncio
from pathlib import Path

# Add the project root to path for running from anywhere
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from bitcrafty_extractor import BitCraftyExtractor


async def main():
    """Main entry point for the BitCrafty-Extractor package."""
    extractor = BitCraftyExtractor()
    await extractor.run()


def cli_main():
    """Synchronous entry point for CLI usage."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
