#!/usr/bin/env python3
"""
Simple configuration loader for tests.

This module provides easy access to configuration for test scripts.
Uses the same ConfigManager that the main application uses.
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Add src to path so we can import ConfigManager
src_path = Path(__file__).parent.parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

try:
    from bitcrafty_extractor.config.config_manager import ConfigManager
    CONFIG_MANAGER_AVAILABLE = True
except ImportError:
    CONFIG_MANAGER_AVAILABLE = False

def get_config_manager() -> Optional['ConfigManager']:
    """Get a ConfigManager instance if available.
    
    Returns:
        ConfigManager instance or None if not available
    """
    if not CONFIG_MANAGER_AVAILABLE:
        return None
        
    try:
        return ConfigManager()
    except Exception:
        return None

def get_openai_key() -> Optional[str]:
    """Get OpenAI API key from config."""
    config_manager = get_config_manager()
    if config_manager and config_manager.config.openai:
        return config_manager.config.openai.api_key
    
    # Fallback to environment variable
    return os.getenv('OPENAI_API_KEY')

def get_anthropic_key() -> Optional[str]:
    """Get Anthropic API key from config."""
    config_manager = get_config_manager()
    if config_manager and config_manager.config.anthropic:
        return config_manager.config.anthropic.api_key
    
    # Fallback to environment variable
    return os.getenv('ANTHROPIC_API_KEY')

def get_default_provider() -> str:
    """Get default AI provider from config."""
    config_manager = get_config_manager()
    if config_manager and config_manager.config.extraction:
        return config_manager.config.extraction.primary_provider.value
    return 'openai'

def has_api_keys() -> bool:
    """Check if any API keys are configured."""
    return bool(get_openai_key() or get_anthropic_key())

def print_config_status():
    """Print current configuration status."""
    print("🔧 Configuration Status")
    print("-" * 25)
    
    if not CONFIG_MANAGER_AVAILABLE:
        print("❌ ConfigManager not available")
        print("💡 Make sure you're running from the project directory")
        return False
    
    config_manager = get_config_manager()
    if not config_manager:
        print("❌ No configuration found")
        print("💡 Run the main application to configure API keys")
        return False
    
    openai_key = get_openai_key()
    anthropic_key = get_anthropic_key()
    
    if openai_key:
        print(f"✅ OpenAI: {openai_key[:8]}...")
    else:
        print("❌ OpenAI: Not configured")
    
    if anthropic_key:
        print(f"✅ Anthropic: {anthropic_key[:8]}...")
    else:
        print("❌ Anthropic: Not configured")
    
    if openai_key or anthropic_key:
        print(f"🎯 Default provider: {get_default_provider()}")
        print(f"📍 Config file: {config_manager.config_path}")
        return True
    else:
        print("💡 Run the main application to configure API keys")
        return False

if __name__ == "__main__":
    print_config_status()
