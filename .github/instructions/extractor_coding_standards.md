---
applyTo: 'g:\SC\BitCrafty-Extractor\**'
---

# BitCrafty-Extractor Coding Standards

This document outlines coding standards and development practices for the BitCrafty-Extractor project. **AI agents and contributors must follow these guidelines** to ensure code quality, maintainability, and performance for this Python-based computer vision tool.

## 1. Architecture Principles (CRITICAL)
- **Modular Design:** ALWAYS use the established component-based architecture with clear separation of concerns
- **Dependency Injection:** Components MUST receive dependencies via constructor, never import directly
- **Single Responsibility:** Each class/module MUST have one clear purpose
- **Configuration-Driven:** ALL behavior MUST be configurable via YAML - no hardcoded values
- **Error Resilient:** MUST implement graceful degradation - never let the application crash

## 2. Project Structure (MANDATORY)
```
src/bitcrafty_extractor/
├── main.py                   # Application entry point
├── core/
│   ├── window_monitor.py     # Game window detection and capture
│   ├── image_processor.py    # Image preprocessing for OCR
│   ├── ocr_engine.py         # Text extraction from images
│   └── config_manager.py     # Configuration loading and validation
├── extraction/
│   ├── data_extractor.py     # Base extraction logic
│   ├── item_extractor.py     # Item data extraction
│   ├── craft_extractor.py    # Craft recipe extraction
│   └── building_extractor.py # Building data extraction
├── validation/
│   ├── data_validator.py     # Data validation against existing datasets
│   └── confidence_scorer.py  # Confidence scoring for extracted data
├── output/
│   ├── data_merger.py        # Merge new data with existing
│   └── bitcrafty_exporter.py # Export to BitCrafty format
└── utils/
    ├── image_utils.py        # Image processing utilities
    ├── text_utils.py         # Text processing utilities
    └── logging_utils.py      # Logging configuration
```

**REQUIREMENTS:**
- **Entry Point:** `main.py` MUST initialize all components with dependency injection
- **Core Services:** Window monitoring, image processing, OCR MUST be in `core/`
- **Domain Logic:** Extraction logic MUST be organized by data type in `extraction/`
- **Clean Imports:** MUST use absolute imports, import only what's needed
- **No New Modules:** Do NOT create new top-level modules without justification

## 3. Python Standards (ENFORCED)
- **Type Hints:** ABSOLUTELY MANDATORY for ALL function signatures and return types
- **Error Handling:** MUST use custom exceptions that inherit from `BitcraftyExtractorError`
- **Logging:** MUST use structlog with context for ALL operations
- **Configuration:** MUST use dataclasses for configuration objects
- **Resource Management:** MUST use context managers for file/window operations
- **No Print Statements:** Use structured logging only

## 4. Code Patterns (MANDATORY)

### Function Signatures
```python
def extract_item_data(
    image: np.ndarray,
    config: ExtractionConfig,
    logger: structlog.BoundLogger
) -> Optional[ItemData]:
    """Extract item data from image with validation."""
    if image is None or image.size == 0:
        raise ValueError("Image cannot be None or empty")
    
    logger.info("Starting item extraction", image_shape=image.shape)
    # Implementation here
```

### Error Handling
```python
class BitcraftyExtractorError(Exception):
    """Base exception for all extractor errors."""
    pass

class OCRError(BitcraftyExtractorError):
    """OCR processing failed."""
    pass

try:
    result = process_image(image)
except OCRError as e:
    logger.warning("OCR failed, continuing", error=str(e))
    return None
```

### Configuration
```python
@dataclass
class OCRConfig:
    language: str = "eng"
    confidence_threshold: float = 0.8
    preprocessing_enabled: bool = True
```

## 5. Component Guidelines (MANDATORY)
- **Initialization:** Each component MUST accept dependencies via constructor
- **Validation:** MUST validate ALL inputs before processing
- **Context Logging:** MUST include relevant context in all log messages
- **Graceful Failures:** MUST handle failures without crashing the application
- **Configuration:** MUST support configuration override via environment variables

## 6. AI Agent Requirements (CRITICAL)
- **NEVER** generate code without complete type hints
- **ALWAYS** include error handling for expected failure modes
- **MUST** follow the established project structure exactly
- **REQUIRED** to add structured logging to all operations
- **MANDATORY** to validate inputs and handle edge cases
- **NEVER** use bare `except:` clauses - always specify exception types
- **NEVER** hardcode values - use configuration or constants
- **NEVER** write functions longer than 50 lines - break them down

### Forbidden Practices
- Using `print()` statements (use logging)
- Hardcoding file paths (use Path objects)
- Ignoring exceptions (handle or re-raise with context)
- Global variables (use dependency injection)
- Magic numbers (use configuration)

This document must be followed by all AI agents working on the BitCrafty-Extractor project.

