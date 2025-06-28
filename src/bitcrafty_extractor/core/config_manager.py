"""Configuration management for BitCrafty Extractor."""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
import structlog

from bitcrafty_extractor import ConfigurationError


@dataclass
class WindowConfig:
    """Window monitoring configuration."""
    target_name: str = "Bitcraft"
    capture_interval_ms: int = 500
    max_window_search_attempts: int = 10
    window_search_interval_ms: int = 2000


@dataclass
class OCRConfig:
    """OCR processing configuration."""
    language: str = "eng"
    confidence_threshold: float = 0.75
    config_string: str = "--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,()-+:/ "
    preprocessing_enabled: bool = True


@dataclass
class CaptureConfig:
    """Screen capture configuration."""
    preprocessing: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": True,
        "resize_factor": 1.0,
        "contrast_enhancement": 1.2,
        "brightness_adjustment": 10,
        "noise_reduction": True
    })


@dataclass
class AppConfig:
    """Main application configuration."""
    name: str = "BitCrafty Extractor"
    version: str = "1.0.0"
    debug: bool = False
    window: WindowConfig = field(default_factory=WindowConfig)
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    ocr: OCRConfig = field(default_factory=OCRConfig)


class ConfigManager:
    """Manages application configuration from YAML files and environment variables."""
    
    def __init__(self, config_path: Optional[Path] = None, logger: Optional[structlog.BoundLogger] = None):
        """Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file
            logger: Structured logger instance
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        self.logger = logger or structlog.get_logger()
        self.config_path = config_path or Path("config/default.yaml")
        self._config = self._load_config()
    
    def _load_config(self) -> AppConfig:
        """Load configuration from file and environment variables.
        
        Returns:
            Loaded and validated configuration
            
        Raises:
            ConfigurationError: If configuration cannot be loaded or is invalid
        """
        try:
            # Load default configuration
            config_data = {}
            
            if self.config_path.exists():
                self.logger.info("Loading configuration", config_path=str(self.config_path))
                with open(self.config_path, 'r') as f:
                    config_data = yaml.safe_load(f) or {}
            else:
                self.logger.warning("Configuration file not found, using defaults", 
                                   config_path=str(self.config_path))
            
            # Apply environment variable overrides
            config_data = self._apply_env_overrides(config_data)
            
            # Create configuration objects
            config = AppConfig(
                name=config_data.get("app", {}).get("name", "BitCrafty Extractor"),
                version=config_data.get("app", {}).get("version", "1.0.0"),
                debug=config_data.get("app", {}).get("debug", False),
                window=WindowConfig(
                    **{k: v for k, v in config_data.get("window", {}).items() 
                       if k in ['target_name', 'capture_interval_ms', 'max_window_search_attempts', 'window_search_interval_ms']}
                ),
                capture=CaptureConfig(
                    preprocessing=config_data.get("capture", {}).get("preprocessing", {})
                ),
                ocr=OCRConfig(
                    **{k: v for k, v in config_data.get("ocr", {}).items() 
                       if k in ['language', 'confidence_threshold', 'config_string', 'preprocessing_enabled']}
                )
            )
            
            self._validate_config(config)
            
            self.logger.info("Configuration loaded successfully", 
                           debug=config.debug,
                           window_target=config.window.target_name)
            
            return config
            
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}") from e
    
    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration.
        
        Args:
            config_data: Base configuration data
            
        Returns:
            Configuration with environment overrides applied
        """
        # Environment variable mappings
        env_mappings = {
            "BITCRAFT_WINDOW_NAME": ["window", "target_name"],
            "BITCRAFT_CAPTURE_INTERVAL": ["window", "capture_interval_ms"],
            "BITCRAFT_OCR_CONFIDENCE": ["ocr", "confidence_threshold"],
            "BITCRAFT_DEBUG": ["app", "debug"]
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Navigate to the nested configuration location
                current = config_data
                for key in config_path[:-1]:
                    current = current.setdefault(key, {})
                
                # Convert value to appropriate type
                final_key = config_path[-1]
                if final_key in ["capture_interval_ms", "window_search_interval_ms", "max_window_search_attempts"]:
                    current[final_key] = int(env_value)
                elif final_key in ["confidence_threshold"]:
                    current[final_key] = float(env_value)
                elif final_key in ["debug"]:
                    current[final_key] = env_value.lower() in ("true", "1", "yes")
                else:
                    current[final_key] = env_value
                
                self.logger.debug("Applied environment override", 
                                env_var=env_var, value=env_value, config_path=config_path)
        
        return config_data
    
    def _validate_config(self, config: AppConfig) -> None:
        """Validate configuration values.
        
        Args:
            config: Configuration to validate
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Validate capture interval
        if config.window.capture_interval_ms < 100:
            raise ConfigurationError("capture_interval_ms must be at least 100ms")
        
        if config.window.capture_interval_ms > 5000:
            raise ConfigurationError("capture_interval_ms must not exceed 5000ms")
        
        # Validate OCR confidence threshold
        if not 0.0 <= config.ocr.confidence_threshold <= 1.0:
            raise ConfigurationError("OCR confidence_threshold must be between 0.0 and 1.0")
        
        # Validate window search attempts
        if config.window.max_window_search_attempts < 1:
            raise ConfigurationError("max_window_search_attempts must be at least 1")
    
    @property
    def config(self) -> AppConfig:
        """Get the current configuration."""
        return self._config
    
    def reload(self) -> None:
        """Reload configuration from file."""
        self.logger.info("Reloading configuration")
        self._config = self._load_config()
