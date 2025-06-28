---
applyTo: '**'
---

# BitCrafty-Extractor Coding Standards

This document outlines coding standards and development practices for the BitCrafty-Extractor project. **AI agents and contributors must follow these guidelines** to ensure code quality, maintainability, and performance for this Python-based computer vision tool.

## Overview
The BitCrafty-Extractor is a Python-based computer vision tool for extracting game data from Bitcraft. All code must adhere to these standards to maintain consistency and quality.

## Technology Stack Requirements

### Core Technologies
- **Python**: 3.11+ (required for latest OpenCV and performance improvements)
- **OpenCV**: 4.8+ for computer vision and image processing
- **Tesseract**: 5.0+ with pytesseract wrapper for OCR
- **NumPy**: Latest stable for array operations
- **Pandas**: Latest stable for data manipulation
- **PyYAML**: For configuration management
- **structlog**: For structured logging

### Development Tools
- **pytest**: For testing with fixtures and parametrization
- **black**: For code formatting (line length: 88)
- **isort**: For import sorting
- **flake8**: For linting with complexity checking
- **mypy**: For static type checking
- **pre-commit**: For automated code quality checks

## Project Structure

```
BitCrafty-Extractor/
├── src/
│   └── bitcrafty_extractor/
│       ├── __init__.py
│       ├── main.py                 # Entry point
│       ├── core/
│       │   ├── __init__.py
│       │   ├── window_monitor.py
│       │   ├── image_processor.py
│       │   ├── ocr_engine.py
│       │   └── config_manager.py
│       ├── extraction/
│       │   ├── __init__.py
│       │   ├── data_extractor.py
│       │   ├── item_extractor.py
│       │   ├── craft_extractor.py
│       │   └── building_extractor.py
│       ├── validation/
│       │   ├── __init__.py
│       │   ├── data_validator.py
│       │   └── confidence_scorer.py
│       ├── output/
│       │   ├── __init__.py
│       │   ├── data_merger.py
│       │   └── bitcrafty_exporter.py
│       └── utils/
│           ├── __init__.py
│           ├── image_utils.py
│           ├── text_utils.py
│           └── logging_utils.py
├── config/
│   ├── default.yaml
│   ├── templates/
│   │   ├── ui_templates.yaml
│   │   └── extraction_rules.yaml
│   └── logging.yaml
├── tests/
│   ├── __init__.py
│   ├── unit/
│   ├── integration/
│   ├── fixtures/
│   └── test_data/
├── docs/
├── scripts/
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── test.txt
├── .github/
├── pyproject.toml
├── setup.py
└── README.md
```

## Code Style Guidelines (MANDATORY)

### General Principles
1. **Readability First (CRITICAL)**: Code MUST be self-documenting with clear intent - AI agents must write code that humans can easily understand and maintain
2. **Performance Conscious (REQUIRED)**: ALWAYS consider memory and CPU usage for real-time processing - this is a performance-critical application
3. **Error Resilient (MANDATORY)**: MUST implement graceful handling of OCR failures and window issues - never let the application crash
4. **Configurable (REQUIRED)**: ALL magic numbers and thresholds MUST be configurable via YAML - no hardcoded values
5. **Testable (CRITICAL)**: Write code that can be easily unit tested with mocked dependencies - every function must be testable

### AI Agent Requirements
- **ALWAYS** use type hints for all function parameters and return values
- **NEVER** use bare except clauses - always specify exception types
- **MUST** follow the established project structure - do not create new modules without justification
- **REQUIRED** to use structured logging with context for all operations
- **MANDATORY** to validate all inputs and handle edge cases gracefully

### Python Style Rules (MANDATORY)

#### Naming Conventions (STRICT COMPLIANCE REQUIRED)
- **Classes**: MUST use PascalCase (`WindowMonitor`, `DataExtractor`)
- **Functions/Methods**: MUST use snake_case (`extract_item_data`, `process_image`)
- **Variables**: MUST use snake_case (`confidence_threshold`, `extracted_items`)
- **Constants**: MUST use UPPER_SNAKE_CASE (`DEFAULT_CONFIDENCE_THRESHOLD`, `MAX_RETRY_ATTEMPTS`)
- **Private members**: MUST use leading underscore (`_internal_method`, `_cached_data`)

#### Type Hints (ABSOLUTELY MANDATORY)
- **REQUIRED**: ALL function signatures MUST include complete type hints
- **REQUIRED**: ALWAYS specify return types, use `None` for procedures
- **MANDATORY**: Use `typing` module imports for complex types
- **REQUIRED**: Use `Optional[T]` or `T | None` (Python 3.10+) for nullable types
- **AI AGENTS**: Never omit type hints - this is non-negotiable

```python
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
from pathlib import Path

def extract_text_regions(
    image: np.ndarray,
    confidence_threshold: float = 0.8,
    region_templates: Optional[Dict[str, Tuple[int, int, int, int]]] = None
) -> List[Dict[str, Union[str, float, Tuple[int, int, int, int]]]]:
    """Extract text regions from image using OCR.
    
    Args:
        image: Input image as numpy array
        confidence_threshold: Minimum confidence for text extraction
        region_templates: Optional predefined regions to search
        
    Returns:
        List of extracted text regions with metadata
        
    Raises:
        OCRError: If OCR processing fails
        ValueError: If image format is invalid
    """
    pass
```

#### Error Handling (CRITICAL REQUIREMENTS)
- **MANDATORY**: Create domain-specific exception classes for all error types
- **REQUIRED**: Log errors with full context before re-raising - never fail silently
- **CRITICAL**: Implement graceful degradation - continue operation when possible
- **MANDATORY**: Use context managers for ALL resource management
- **AI AGENTS**: NEVER use bare `except:` clauses - always specify exception types
- **REQUIRED**: All exceptions must inherit from `BitcraftyExtractorError` base class

```python
class BitcraftyExtractorError(Exception):
    """Base exception for BitCrafty Extractor errors."""
    pass

class OCRError(BitcraftyExtractorError):
    """Raised when OCR processing fails."""
    pass

class WindowNotFoundError(BitcraftyExtractorError):
    """Raised when Bitcraft window cannot be found."""
    pass

def process_screenshot(window_handle: int) -> Optional[np.ndarray]:
    """Process screenshot with proper error handling."""
    try:
        with WindowCapture(window_handle) as capture:
            image = capture.get_screenshot()
            return preprocess_image(image)
    except WindowNotFoundError:
        logger.warning("Bitcraft window lost, retrying in 5 seconds")
        return None
    except Exception as e:
        logger.error("Unexpected error in screenshot processing", error=str(e))
        raise
```

#### Configuration Management (STRICT REQUIREMENTS)
- **MANDATORY**: Use YAML for ALL configuration - never hardcode values
- **REQUIRED**: Support environment variable overrides for deployment flexibility
- **CRITICAL**: Validate ALL configuration on startup with clear error messages
- **MANDATORY**: Provide sensible defaults for ALL configuration options
- **AI AGENTS**: Use dataclasses for configuration objects - never use plain dictionaries

```python
from dataclasses import dataclass
from pathlib import Path
import yaml

@dataclass
class OCRConfig:
    language: str = "eng"
    confidence_threshold: float = 0.8
    preprocessing_enabled: bool = True
    custom_config: str = "--psm 6"

@dataclass
class CaptureConfig:
    interval_ms: int = 500
    window_name: str = "Bitcraft"
    max_retries: int = 3
    
class ConfigManager:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._config = self._load_config()
    
    def _load_config(self) -> dict:
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
```

### Testing Standards

#### Test Structure
- **Unit Tests**: Test individual functions and classes in isolation
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete extraction workflows
- **Performance Tests**: Measure processing speed and memory usage

#### Test Naming
```python
class TestItemExtractor:
    def test_extract_item_name_from_tooltip_success(self):
        """Test successful item name extraction from tooltip."""
        pass
    
    def test_extract_item_name_with_low_confidence_returns_none(self):
        """Test that low confidence OCR results return None."""
        pass
    
    def test_extract_item_name_with_invalid_image_raises_error(self):
        """Test that invalid image format raises ValueError."""
        pass
```

#### Test Data Management
- **Fixtures**: Use pytest fixtures for common test data
- **Test Images**: Store reference images for vision testing
- **Mock Data**: Create realistic mock data for unit tests
- **Golden Files**: Store expected outputs for regression testing

```python
import pytest
from pathlib import Path

@pytest.fixture
def sample_tooltip_image():
    """Load sample tooltip image for testing."""
    image_path = Path(__file__).parent / "test_data" / "tooltip_sample.png"
    return cv2.imread(str(image_path))

@pytest.fixture
def mock_ocr_result():
    """Mock OCR result for testing."""
    return {
        "text": "Iron Sword",
        "confidence": 95.5,
        "bbox": (100, 100, 200, 120)
    }

def test_item_extraction_with_high_confidence(sample_tooltip_image, mock_ocr_result):
    extractor = ItemExtractor()
    result = extractor.extract_from_image(sample_tooltip_image)
    assert result.name == "Iron Sword"
    assert result.confidence > 0.9
```

### Performance Guidelines

#### Image Processing
- **Memory Management**: Process images in chunks for large screenshots
- **Caching**: Cache processed templates and OCR models
- **Optimization**: Use optimized NumPy operations over loops
- **Profiling**: Profile critical paths and optimize bottlenecks

```python
import functools
import numpy as np
from typing import Dict

class ImageProcessor:
    def __init__(self):
        self._template_cache: Dict[str, np.ndarray] = {}
    
    @functools.lru_cache(maxsize=128)
    def get_processed_template(self, template_name: str) -> np.ndarray:
        """Cache processed templates to avoid recomputation."""
        if template_name not in self._template_cache:
            template = self._load_template(template_name)
            self._template_cache[template_name] = self._preprocess_template(template)
        return self._template_cache[template_name]
```

#### OCR Optimization
- **Region Targeting**: Only OCR relevant screen regions
- **Preprocessing**: Optimize images before OCR (contrast, resize, denoise)
- **Batch Processing**: Process multiple regions in batches when possible
- **Model Caching**: Keep OCR models loaded in memory

### Logging Standards

#### Structured Logging
```python
import structlog

logger = structlog.get_logger()

def extract_item_data(image: np.ndarray) -> Optional[Dict]:
    """Extract item data with comprehensive logging."""
    logger.info("Starting item extraction", image_shape=image.shape)
    
    try:
        # Processing logic
        result = process_extraction(image)
        logger.info(
            "Item extraction completed",
            success=True,
            items_found=len(result.get("items", [])),
            confidence=result.get("avg_confidence", 0)
        )
        return result
    except OCRError as e:
        logger.error(
            "OCR processing failed",
            error=str(e),
            image_shape=image.shape,
            retry_count=e.retry_count
        )
        return None
```

#### Log Levels
- **DEBUG**: Detailed processing information, image coordinates, OCR raw results
- **INFO**: Successful operations, extraction summaries, performance metrics
- **WARNING**: Recoverable errors, low confidence results, retry operations
- **ERROR**: Processing failures, configuration errors, critical issues
- **CRITICAL**: Application crashes, data corruption, security issues

### Documentation Standards

#### Docstring Format (Google Style)
```python
def extract_craft_recipe(
    image: np.ndarray,
    recipe_template: Dict[str, Any],
    confidence_threshold: float = 0.8
) -> Optional[CraftRecipe]:
    """Extract craft recipe information from game interface.
    
    This function processes a screenshot of the crafting interface to extract
    recipe information including materials, outputs, and requirements.
    
    Args:
        image: Screenshot of the crafting interface as numpy array
        recipe_template: Template configuration for recipe extraction
        confidence_threshold: Minimum confidence for OCR results (0.0-1.0)
        
    Returns:
        CraftRecipe object if extraction successful, None otherwise
        
    Raises:
        ValueError: If image format is invalid or empty
        OCRError: If OCR processing fails completely
        TemplateError: If recipe template is malformed
        
    Example:
        >>> image = capture_crafting_screen()
        >>> template = load_recipe_template("basic_crafting")
        >>> recipe = extract_craft_recipe(image, template, 0.85)
        >>> if recipe:
        ...     print(f"Recipe: {recipe.name}")
    """
    pass
```

#### Code Comments
- **Why, not What**: Explain reasoning behind complex logic
- **Algorithm Descriptions**: Document non-obvious algorithms
- **Performance Notes**: Explain optimization decisions
- **Edge Cases**: Document special case handling

```python
def preprocess_for_ocr(image: np.ndarray) -> np.ndarray:
    """Preprocess image for optimal OCR results."""
    # Convert to grayscale to reduce noise and improve OCR accuracy
    # Tests show 15% improvement in confidence with this conversion
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply bilateral filter to reduce noise while preserving edges
    # This is crucial for tooltip text which often has subtle backgrounds
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # Increase contrast for better character recognition
    # OCR performs significantly better on high-contrast text
    contrast = cv2.convertScaleAbs(denoised, alpha=1.5, beta=10)
    
    return contrast
```

### Git Workflow (MANDATORY)

#### Branch Naming (REQUIRED FORMAT)
- **Feature branches**: `feature/extract-building-data`
- **Bug fixes**: `fix/ocr-confidence-calculation`
- **Documentation**: `docs/update-api-documentation`
- **Performance**: `perf/optimize-image-processing`

#### Commit Messages (STRICT FORMAT)
```
feat: add building data extraction from construction UI

- Implement BuildingExtractor class with template matching
- Add configuration for building UI regions
- Include tests for common building types
- Update documentation with building extraction flow

Closes #23
```

## AI Agent Specific Requirements (CRITICAL)

### Code Generation Standards
- **NEVER** generate code without proper type hints
- **ALWAYS** include comprehensive error handling
- **MUST** follow the established project structure exactly
- **REQUIRED** to add logging to all significant operations
- **MANDATORY** to include docstrings for all public functions
- **CRITICAL** to validate all inputs before processing

### Implementation Guidelines for AI Agents
1. **Before writing code**: Understand the component's role in the extraction pipeline
2. **Use dependency injection**: Never hardcode dependencies - always inject them
3. **Configuration-driven**: All behavior must be configurable via YAML
4. **Fail fast**: Validate inputs immediately and provide clear error messages
5. **Resource management**: Always use context managers for file/window operations
6. **Performance monitoring**: Add timing and memory usage logging for critical paths

### Specific AI Agent Requirements

#### When implementing image processing:
```python
# CORRECT - AI agents must follow this pattern
def process_image(
    image: np.ndarray, 
    config: ImageProcessingConfig,
    logger: structlog.BoundLogger
) -> ProcessedImage:
    """Process image with comprehensive validation and logging."""
    if image is None or image.size == 0:
        raise ValueError("Image cannot be None or empty")
    
    logger.info("Starting image processing", 
                image_shape=image.shape, 
                config=config.to_dict())
    
    try:
        # Processing logic here
        result = _apply_processing(image, config)
        logger.info("Image processing completed successfully",
                   output_shape=result.shape)
        return ProcessedImage(data=result, metadata={"confidence": 0.95})
    except Exception as e:
        logger.error("Image processing failed", error=str(e))
        raise ImageProcessingError(f"Failed to process image: {e}") from e
```

#### When implementing OCR operations:
```python
# REQUIRED pattern for AI agents
def extract_text(
    image: np.ndarray,
    ocr_config: OCRConfig,
    logger: structlog.BoundLogger
) -> OCRResult:
    """Extract text with confidence scoring and validation."""
    _validate_image_input(image)
    
    logger.debug("Starting OCR extraction", 
                 image_size=image.shape,
                 config=ocr_config.tesseract_config)
    
    try:
        with _ocr_context(ocr_config) as ocr_engine:
            raw_result = ocr_engine.extract_text(image)
            validated_result = _validate_ocr_result(raw_result, ocr_config.min_confidence)
            
            logger.info("OCR extraction completed",
                       text_length=len(validated_result.text),
                       confidence=validated_result.confidence)
            
            return validated_result
    except OCRError as e:
        logger.warning("OCR extraction failed", error=str(e))
        return OCRResult.empty()
```

### Forbidden Practices for AI Agents
- **NEVER** use `print()` statements - always use structured logging
- **NEVER** hardcode file paths - use Path objects and configuration
- **NEVER** ignore exceptions - always handle or re-raise with context
- **NEVER** use global variables - use dependency injection
- **NEVER** write functions longer than 50 lines - break them down
- **NEVER** use magic numbers - define constants or use configuration

### Testing Requirements for AI Agents
- **MUST** write tests for every public function
- **REQUIRED** to use pytest fixtures for test data
- **MANDATORY** to mock external dependencies (OCR, window capture)
- **CRITICAL** to test error conditions and edge cases
- **REQUIRED** to include performance tests for critical paths

```python
# REQUIRED test pattern for AI agents
class TestItemExtractor:
    @pytest.fixture
    def sample_image(self):
        """Provide sample test image."""
        return np.zeros((100, 100, 3), dtype=np.uint8)
    
    @pytest.fixture
    def extractor_config(self):
        """Provide test configuration."""
        return ItemExtractionConfig(confidence_threshold=0.8)
    
    def test_extract_item_success(self, sample_image, extractor_config, mock_logger):
        """Test successful item extraction."""
        extractor = ItemExtractor(config=extractor_config, logger=mock_logger)
        
        with patch('pytesseract.image_to_data') as mock_ocr:
            mock_ocr.return_value = self._mock_ocr_data()
            
            result = extractor.extract_from_image(sample_image)
            
            assert result.confidence > 0.8
            assert result.item_name == "Test Item"
            mock_logger.info.assert_called()
    
    def test_extract_item_invalid_image_raises_error(self, extractor_config, mock_logger):
        """Test that invalid image raises appropriate error."""
        extractor = ItemExtractor(config=extractor_config, logger=mock_logger)
        
        with pytest.raises(ValueError, match="Image cannot be None"):
            extractor.extract_from_image(None)
```

### Code Review Checklist for AI Agents

#### Before submitting code, verify:
- [ ] All functions have complete type hints
- [ ] Error handling covers all expected failure modes
- [ ] Logging provides sufficient context for debugging
- [ ] Configuration is externalized (no hardcoded values)
- [ ] Tests cover both success and failure cases
- [ ] Performance impact has been considered
- [ ] Documentation is clear and complete
- [ ] Code follows established patterns in the codebase

### Performance Requirements for AI Agents
- **Image processing**: Must handle 1920x1080 screenshots in <100ms
- **OCR operations**: Must process tooltip regions in <200ms
- **Memory usage**: Must not exceed 512MB for normal operations
- **CPU usage**: Must not consume >25% of single core continuously

### Security and Privacy Requirements
- **NEVER** extract or log personal information
- **ONLY** capture game window content
- **SANITIZE** all extracted text before storage
- **USE** appropriate file permissions for output files
- **VALIDATE** all external inputs before processing

This document must be followed by all AI agents working on the BitCrafty-Extractor project. Non-compliance will result in code rejection and rework requirements.

