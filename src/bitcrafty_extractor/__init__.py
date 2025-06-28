"""BitCrafty Extractor - Real-time game data extraction tool."""

__version__ = "1.0.0"

# Base exceptions
class BitcraftyExtractorError(Exception):
    """Base exception for all BitCrafty Extractor errors."""
    pass


class ConfigurationError(BitcraftyExtractorError):
    """Raised when configuration is invalid or missing."""
    pass


class WindowNotFoundError(BitcraftyExtractorError):
    """Raised when target window cannot be found."""
    pass


class OCRError(BitcraftyExtractorError):
    """Raised when OCR processing fails."""
    pass


class ImageProcessingError(BitcraftyExtractorError):
    """Raised when image processing fails."""
    pass
