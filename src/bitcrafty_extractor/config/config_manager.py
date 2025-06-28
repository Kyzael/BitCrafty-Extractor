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
    quit_application: str = "ctrl+shift+q"
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
            # Use local config directory in project
            project_root = Path(__file__).parent.parent.parent.parent
            config_dir = project_root / "config"
            config_dir.mkdir(exist_ok=True)
            self.config_path = config_dir / "config.yaml"
            self.default_config_path = config_dir / "default.yaml"
        else:
            self.config_path = Path(config_path)
            self.default_config_path = self.config_path.parent / "default.yaml"
        
        # Initialize with defaults
        self.config = AppConfig()
        
        # Load configuration (creates from default if needed)
        self._initialize_config()
        
        self.logger.info("Configuration manager initialized", 
                        config_path=str(self.config_path))

    def _initialize_config(self):
        """Initialize configuration from default template and user config."""
        try:
            # Always start with default configuration
            if self.default_config_path.exists():
                self.logger.info("Loading default configuration template", 
                               path=str(self.default_config_path))
                with open(self.default_config_path, 'r', encoding='utf-8') as f:
                    default_data = yaml.safe_load(f)
                    self.config = self._dict_to_config(default_data)
            else:
                self.logger.warning("Default configuration template not found, using hardcoded defaults",
                                  expected_path=str(self.default_config_path))
                # Keep hardcoded defaults if template missing
            
            # Load user config if it exists and merge with defaults
            if self.config_path.exists():
                self.logger.info("Loading user configuration", 
                               path=str(self.config_path))
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_data = yaml.safe_load(f)
                    
                # Merge user settings with defaults
                self._merge_config(user_data)
            else:
                self.logger.info("User configuration not found, will create from template",
                               path=str(self.config_path))
                # Save initial config from template
                self.save_config()
                
        except Exception as e:
            self.logger.error("Failed to initialize configuration", error=str(e))
            # Keep hardcoded defaults on error
            self.config = AppConfig()
    
    def _merge_config(self, user_data: Dict[str, Any]):
        """Merge user configuration with loaded defaults.
        
        Args:
            user_data: User configuration data from YAML
        """
        try:
            # Convert user data to config objects
            user_config = self._dict_to_config(user_data)
            
            # Merge AI provider configurations
            if user_config.openai and user_config.openai.api_key:
                self.config.openai = user_config.openai
            if user_config.anthropic and user_config.anthropic.api_key:
                self.config.anthropic = user_config.anthropic
            
            # Merge hotkey configuration
            if user_config.hotkeys:
                self.config.hotkeys = user_config.hotkeys
            
            # Merge capture configuration
            if user_config.capture:
                self.config.capture = user_config.capture
                
            # Merge extraction configuration  
            if user_config.extraction:
                self.config.extraction = user_config.extraction
            
            # Merge application settings
            if hasattr(user_config, 'log_level') and user_config.log_level:
                self.config.log_level = user_config.log_level
            if hasattr(user_config, 'auto_save_results'):
                self.config.auto_save_results = user_config.auto_save_results
            if hasattr(user_config, 'results_directory') and user_config.results_directory:
                self.config.results_directory = user_config.results_directory
                    
            self.logger.info("Successfully merged user configuration with defaults")
            
        except Exception as e:
            self.logger.error("Failed to merge user configuration", error=str(e))
            # Keep defaults on merge error
    
    def _dict_to_config(self, data: Dict[str, Any]) -> AppConfig:
        """Convert dictionary data to configuration objects.
        
        Args:
            data: Configuration data from YAML
            
        Returns:
            AppConfig object
        """
        config = AppConfig()
        
        # Parse AI provider configurations
        if 'ai' in data:
            ai_data = data['ai']
            
            # Parse OpenAI configuration
            if 'openai' in ai_data:
                openai_data = ai_data['openai']
                config.openai = AIProviderConfig(
                    api_key=openai_data.get('api_key', ''),
                    model=openai_data.get('model', 'gpt-4-vision-preview'),
                    enabled=openai_data.get('enabled', True),
                    max_tokens=openai_data.get('max_tokens', 1000),
                    temperature=openai_data.get('temperature', 0.1),
                    timeout=openai_data.get('timeout', 30.0)
                )
            
            # Parse Anthropic configuration
            if 'anthropic' in ai_data:
                anthropic_data = ai_data['anthropic']
                config.anthropic = AIProviderConfig(
                    api_key=anthropic_data.get('api_key', ''),
                    model=anthropic_data.get('model', 'claude-3-sonnet-20240229'),
                    enabled=anthropic_data.get('enabled', True),
                    max_tokens=anthropic_data.get('max_tokens', 1000),
                    temperature=anthropic_data.get('temperature', 0.1),
                    timeout=anthropic_data.get('timeout', 30.0)
                )
        else:
            # Also handle legacy format for backwards compatibility
            if 'openai' in data:
                openai_data = data['openai']
                config.openai = AIProviderConfig(
                    api_key=openai_data.get('api_key', ''),
                    model=openai_data.get('model', 'gpt-4-vision-preview'),
                    enabled=openai_data.get('enabled', True),
                    max_tokens=openai_data.get('max_tokens', 1000),
                    temperature=openai_data.get('temperature', 0.1),
                    timeout=openai_data.get('timeout', 30.0)
                )
            
            if 'anthropic' in data:
                anthropic_data = data['anthropic']
                config.anthropic = AIProviderConfig(
                    api_key=anthropic_data.get('api_key', ''),
                    model=anthropic_data.get('model', 'claude-3-sonnet-20240229'),
                    enabled=anthropic_data.get('enabled', True),
                    max_tokens=anthropic_data.get('max_tokens', 1000),
                    temperature=anthropic_data.get('temperature', 0.1),
                    timeout=anthropic_data.get('timeout', 30.0)
                )
        
        # Parse hotkey configuration
        if 'hotkeys' in data:
            hotkey_data = data['hotkeys']
            config.hotkeys = HotkeyConfig(
                queue_screenshot=hotkey_data.get('queue_screenshot', 'ctrl+shift+e'),
                analyze_queue=hotkey_data.get('analyze_queue', 'ctrl+shift+x'),
                quit_application=hotkey_data.get('quit_application', 'ctrl+shift+q'),
                enable_global=hotkey_data.get('enable_global', True),
                debounce_ms=hotkey_data.get('debounce_ms', 500)
            )
        
        # Parse capture configuration
        if 'capture' in data:
            capture_data = data['capture']
            config.capture = CaptureConfig(
                window_name=capture_data.get('window_name', 'Bitcraft'),
                target_process=capture_data.get('target_process', 'bitcraft.exe'),
                game_window_patterns=capture_data.get('game_window_patterns'),
                max_image_size=capture_data.get('max_image_size', 1024),
                image_format=capture_data.get('image_format', 'PNG'),
                image_quality=capture_data.get('image_quality', 85),
                capture_timeout=capture_data.get('capture_timeout', 5.0),
                queue_max_size=capture_data.get('queue_max_size', 20),
                min_window_width=capture_data.get('min_window_width', 400),
                min_window_height=capture_data.get('min_window_height', 300)
            )
        
        # Parse extraction configuration
        if 'extraction' in data:
            extraction_data = data['extraction']
            
            # Parse provider enums
            primary_provider = AIProviderType.OPENAI
            if extraction_data.get('primary_provider') == 'anthropic':
                primary_provider = AIProviderType.ANTHROPIC
            
            fallback_provider = AIProviderType.ANTHROPIC
            if extraction_data.get('fallback_provider') == 'openai':
                fallback_provider = AIProviderType.OPENAI
            
            config.extraction = ExtractionConfig(
                primary_provider=primary_provider,
                fallback_provider=fallback_provider,
                use_fallback=extraction_data.get('use_fallback', True),
                include_examples=extraction_data.get('include_examples', True),
                min_confidence=extraction_data.get('min_confidence', 0.7),
                max_retries=extraction_data.get('max_retries', 3),
                rate_limit_delay=extraction_data.get('rate_limit_delay', 1.0)
            )
        
        # Parse application settings
        config.log_level = data.get('log_level', 'INFO')
        config.auto_save_results = data.get('auto_save_results', True)
        config.results_directory = data.get('results_directory', 'results')
        
        return config
    def load_config(self) -> bool:
        """Load configuration from file (legacy method - now uses _initialize_config).
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            self._initialize_config()
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
            ('analyze_queue', self.config.hotkeys.analyze_queue),
            ('quit_application', self.config.hotkeys.quit_application)
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
            elif hotkey_name == 'quit_application':
                self.config.hotkeys.quit_application = hotkey_value
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
