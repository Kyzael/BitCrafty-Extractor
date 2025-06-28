"""Configuration management for BitCrafty Extractor.

This module handles loading, saving, and validating configuration
for the AI-powered extraction system.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import structlog
from enum import Enum


class AIProviderType(Enum):
    """Available AI provider types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class AIProviderConfig:
    """Configuration for an AI provider."""
    api_key: str
    model: str
    enabled: bool = True
    max_tokens: int = 1000
    temperature: float = 0.1
    timeout: float = 30.0


@dataclass
class HotkeyConfig:
    """Configuration for hotkeys."""
    queue_screenshot: str = "ctrl+shift+e"
    analyze_queue: str = "ctrl+shift+x"
    enable_global: bool = True
    debounce_ms: int = 500


@dataclass
class CaptureConfig:
    """Configuration for screen capture."""
    window_name: str = "Bitcraft"
    target_process: str = "bitcraft.exe"
    game_window_patterns: List[str] = None
    max_image_size: int = 1024
    image_format: str = "PNG"
    image_quality: int = 85
    capture_timeout: float = 5.0
    queue_max_size: int = 20  # Maximum screenshots in queue
    min_window_width: int = 400
    min_window_height: int = 300
    
    def __post_init__(self):
        """Initialize default window patterns if not provided."""
        if self.game_window_patterns is None:
            self.game_window_patterns = ["BitCraft", "bitcraft", "BITCRAFT", "Bitcraft"]


@dataclass
class ExtractionConfig:
    """Configuration for data extraction."""
    primary_provider: AIProviderType = AIProviderType.ANTHROPIC
    fallback_provider: AIProviderType = AIProviderType.ANTHROPIC
    use_fallback: bool = True
    include_examples: bool = True
    min_confidence: float = 0.7
    max_retries: int = 3
    rate_limit_delay: float = 1.0


@dataclass
class AppConfig:
    """Main application configuration."""
    # AI Providers
    openai: Optional[AIProviderConfig] = None
    anthropic: Optional[AIProviderConfig] = None
    
    # System Configuration
    hotkeys: HotkeyConfig = None
    capture: CaptureConfig = None
    extraction: ExtractionConfig = None
    
    # Application Settings
    log_level: str = "INFO"
    auto_save_results: bool = True
    results_directory: str = "results"
    config_file: str = "config.yaml"
    
    def __post_init__(self):
        """Initialize default configurations if not provided."""
        if self.hotkeys is None:
            self.hotkeys = HotkeyConfig()
        if self.capture is None:
            self.capture = CaptureConfig()
        if self.extraction is None:
            self.extraction = ExtractionConfig()


class ConfigManager:
    """Configuration manager for BitCrafty Extractor."""
    
    def __init__(self, config_path: Optional[Path] = None, logger: Optional[structlog.BoundLogger] = None):
        """Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file
            logger: Structured logger
        """
        self.logger = logger or structlog.get_logger()
        
        # Determine config path
        if config_path is None:
            # Default to user config directory
            if Path.home().exists():
                config_dir = Path.home() / ".bitcrafty-extractor"
            else:
                config_dir = Path.cwd() / "config"
            
            config_dir.mkdir(exist_ok=True)
            self.config_path = config_dir / "config.yaml"
        else:
            self.config_path = Path(config_path)
        
        # Initialize with defaults
        self.config = AppConfig()
        
        # Load existing config if it exists
        if self.config_path.exists():
            self.load_config()
        else:
            # Save default config
            self.save_config()
        
        self.logger.info("Configuration manager initialized", 
                        config_path=str(self.config_path))

    def load_config(self) -> bool:
        """Load configuration from file.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data:
                self.logger.warning("Config file is empty, using defaults")
                return False
            
            # Parse configuration sections
            self.config = AppConfig()
            
            # AI Provider configurations
            if 'openai' in config_data:
                openai_data = config_data['openai']
                self.config.openai = AIProviderConfig(
                    api_key=openai_data.get('api_key', ''),
                    model=openai_data.get('model', 'gpt-4-vision-preview'),
                    enabled=openai_data.get('enabled', True),
                    max_tokens=openai_data.get('max_tokens', 1000),
                    temperature=openai_data.get('temperature', 0.1),
                    timeout=openai_data.get('timeout', 30.0)
                )
            
            if 'anthropic' in config_data:
                anthropic_data = config_data['anthropic']
                self.config.anthropic = AIProviderConfig(
                    api_key=anthropic_data.get('api_key', ''),
                    model=anthropic_data.get('model', 'claude-3-opus-20240229'),
                    enabled=anthropic_data.get('enabled', True),
                    max_tokens=anthropic_data.get('max_tokens', 1000),
                    temperature=anthropic_data.get('temperature', 0.1),
                    timeout=anthropic_data.get('timeout', 30.0)
                )
            
            # Hotkey configuration
            if 'hotkeys' in config_data:
                hotkey_data = config_data['hotkeys']
                self.config.hotkeys = HotkeyConfig(
                    queue_screenshot=hotkey_data.get('queue_screenshot', 'ctrl+shift+e'),
                    analyze_queue=hotkey_data.get('analyze_queue', 'ctrl+shift+x'),
                    enable_global=hotkey_data.get('enable_global', True),
                    debounce_ms=hotkey_data.get('debounce_ms', 500)
                )
            else:
                self.config.hotkeys = HotkeyConfig()
            
            # Capture configuration
            if 'capture' in config_data:
                capture_data = config_data['capture']
                self.config.capture = CaptureConfig(
                    window_name=capture_data.get('window_name', 'Bitcraft'),
                    target_process=capture_data.get('target_process', 'bitcraft.exe'),
                    game_window_patterns=capture_data.get('game_window_patterns', None),
                    max_image_size=capture_data.get('max_image_size', 1024),
                    image_format=capture_data.get('image_format', 'PNG'),
                    image_quality=capture_data.get('image_quality', 85),
                    capture_timeout=capture_data.get('capture_timeout', 5.0),
                    queue_max_size=capture_data.get('queue_max_size', 20),
                    min_window_width=capture_data.get('min_window_width', 400),
                    min_window_height=capture_data.get('min_window_height', 300)
                )
            else:
                self.config.capture = CaptureConfig()
            
            # Extraction configuration
            if 'extraction' in config_data:
                extraction_data = config_data['extraction']
                
                # Parse provider enums
                primary_provider = AIProviderType.OPENAI
                if extraction_data.get('primary_provider') == 'anthropic':
                    primary_provider = AIProviderType.ANTHROPIC
                
                fallback_provider = AIProviderType.ANTHROPIC
                if extraction_data.get('fallback_provider') == 'openai':
                    fallback_provider = AIProviderType.OPENAI
                
                self.config.extraction = ExtractionConfig(
                    primary_provider=primary_provider,
                    fallback_provider=fallback_provider,
                    use_fallback=extraction_data.get('use_fallback', True),
                    include_examples=extraction_data.get('include_examples', True),
                    min_confidence=extraction_data.get('min_confidence', 0.7),
                    max_retries=extraction_data.get('max_retries', 3),
                    rate_limit_delay=extraction_data.get('rate_limit_delay', 1.0)
                )
            else:
                self.config.extraction = ExtractionConfig()
            
            # Application settings
            self.config.log_level = config_data.get('log_level', 'INFO')
            self.config.auto_save_results = config_data.get('auto_save_results', True)
            self.config.results_directory = config_data.get('results_directory', 'results')
            
            self.logger.info("Configuration loaded successfully")
            return True
            
        except Exception as e:
            self.logger.error("Failed to load configuration", error=str(e))
            return False

    def save_config(self) -> bool:
        """Save current configuration to file.
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Prepare configuration data
            config_data = {
                'log_level': self.config.log_level,
                'auto_save_results': self.config.auto_save_results,
                'results_directory': self.config.results_directory,
                'hotkeys': asdict(self.config.hotkeys),
                'capture': asdict(self.config.capture),
                'extraction': {
                    'primary_provider': self.config.extraction.primary_provider.value,
                    'fallback_provider': self.config.extraction.fallback_provider.value,
                    'use_fallback': self.config.extraction.use_fallback,
                    'include_examples': self.config.extraction.include_examples,
                    'min_confidence': self.config.extraction.min_confidence,
                    'max_retries': self.config.extraction.max_retries,
                    'rate_limit_delay': self.config.extraction.rate_limit_delay
                }
            }
            
            # Add AI provider configurations if they exist
            if self.config.openai:
                config_data['openai'] = asdict(self.config.openai)
            
            if self.config.anthropic:
                config_data['anthropic'] = asdict(self.config.anthropic)
            
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write configuration
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
            
            self.logger.info("Configuration saved successfully")
            return True
            
        except Exception as e:
            self.logger.error("Failed to save configuration", error=str(e))
            return False

    def validate_config(self) -> List[str]:
        """Validate current configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check AI provider configuration
        has_provider = False
        
        if self.config.openai and self.config.openai.enabled:
            if not self.config.openai.api_key:
                errors.append("OpenAI API key is required when OpenAI is enabled")
            else:
                has_provider = True
        
        if self.config.anthropic and self.config.anthropic.enabled:
            if not self.config.anthropic.api_key:
                errors.append("Anthropic API key is required when Anthropic is enabled")
            else:
                has_provider = True
        
        if not has_provider:
            errors.append("At least one AI provider must be configured and enabled")
        
        # Validate hotkey format
        hotkey_pattern = r'^(ctrl\+)?(shift\+)?(alt\+)?[a-z0-9]$'
        import re
        
        for hotkey_name, hotkey_value in [
            ('queue_screenshot', self.config.hotkeys.queue_screenshot),
            ('analyze_queue', self.config.hotkeys.analyze_queue)
        ]:
            if not re.match(hotkey_pattern, hotkey_value, re.IGNORECASE):
                errors.append(f"Invalid hotkey format for {hotkey_name}: {hotkey_value}")
        
        # Validate numeric ranges
        if not 0.0 <= self.config.extraction.min_confidence <= 1.0:
            errors.append("Min confidence must be between 0.0 and 1.0")
        
        if self.config.extraction.max_retries < 0:
            errors.append("Max retries must be non-negative")
        
        if self.config.capture.max_image_size < 256:
            errors.append("Max image size must be at least 256 pixels")
        
        if not 0 <= self.config.capture.image_quality <= 100:
            errors.append("Image quality must be between 0 and 100")
        
        return errors

    def is_valid(self) -> bool:
        """Check if current configuration is valid.
        
        Returns:
            True if configuration is valid
        """
        return len(self.validate_config()) == 0

    def get_ai_provider_config(self, provider_type: AIProviderType) -> Optional[AIProviderConfig]:
        """Get configuration for specific AI provider.
        
        Args:
            provider_type: Type of AI provider
            
        Returns:
            Provider configuration or None if not configured
        """
        if provider_type == AIProviderType.OPENAI:
            return self.config.openai
        elif provider_type == AIProviderType.ANTHROPIC:
            return self.config.anthropic
        else:
            return None

    def set_ai_provider_config(self, provider_type: AIProviderType, config: AIProviderConfig):
        """Set configuration for specific AI provider.
        
        Args:
            provider_type: Type of AI provider
            config: Provider configuration
        """
        if provider_type == AIProviderType.OPENAI:
            self.config.openai = config
        elif provider_type == AIProviderType.ANTHROPIC:
            self.config.anthropic = config
        
        self.logger.info("AI provider configuration updated", provider=provider_type.value)

    def update_hotkey(self, hotkey_name: str, hotkey_value: str) -> bool:
        """Update a specific hotkey configuration.
        
        Args:
            hotkey_name: Name of the hotkey to update
            hotkey_value: New hotkey combination
            
        Returns:
            True if updated successfully
        """
        try:
            if hotkey_name == 'queue_screenshot':
                self.config.hotkeys.queue_screenshot = hotkey_value
            elif hotkey_name == 'analyze_queue':
                self.config.hotkeys.analyze_queue = hotkey_value
            else:
                return False
            
            self.logger.info("Hotkey updated", name=hotkey_name, value=hotkey_value)
            return True
            
        except Exception as e:
            self.logger.error("Failed to update hotkey", name=hotkey_name, error=str(e))
            return False

    def get_results_directory(self) -> Path:
        """Get the results directory path, creating it if necessary.
        
        Returns:
            Path to results directory
        """
        results_path = Path(self.config.results_directory)
        
        # Make relative to config directory if not absolute
        if not results_path.is_absolute():
            results_path = self.config_path.parent / results_path
        
        # Create directory if it doesn't exist
        results_path.mkdir(parents=True, exist_ok=True)
        
        return results_path

    def export_config(self) -> Dict[str, Any]:
        """Export configuration as dictionary (for sharing/backup).
        
        Returns:
            Configuration dictionary
        """
        config_dict = {
            'hotkeys': asdict(self.config.hotkeys),
            'capture': asdict(self.config.capture),
            'extraction': {
                'primary_provider': self.config.extraction.primary_provider.value,
                'fallback_provider': self.config.extraction.fallback_provider.value,
                'use_fallback': self.config.extraction.use_fallback,
                'include_examples': self.config.extraction.include_examples,
                'min_confidence': self.config.extraction.min_confidence,
                'max_retries': self.config.extraction.max_retries,
                'rate_limit_delay': self.config.extraction.rate_limit_delay
            },
            'log_level': self.config.log_level,
            'auto_save_results': self.config.auto_save_results,
            'results_directory': self.config.results_directory
        }
        
        # Include provider configs but mask API keys
        if self.config.openai:
            openai_config = asdict(self.config.openai)
            openai_config['api_key'] = '***MASKED***' if openai_config['api_key'] else ''
            config_dict['openai'] = openai_config
        
        if self.config.anthropic:
            anthropic_config = asdict(self.config.anthropic)
            anthropic_config['api_key'] = '***MASKED***' if anthropic_config['api_key'] else ''
            config_dict['anthropic'] = anthropic_config
        
        return config_dict
