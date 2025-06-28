---
applyTo: '**'
---

# BitCrafty-Extractor Coding Standards

This document outlines coding standards and best practices for the BitCrafty-Extractor project. **AI agents and contributors must follow these guidelines** to ensure code quality, maintainability, and architectural consistency.

## 1. Core Commands

### Development Setup
```powershell
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -e ".[dev]"

# Run application
python bitcrafty-extractor.py
```

**Note**: This project is Windows-specific and requires PowerShell syntax for terminal commands.

### Code Quality & Testing
```powershell
# Format code
black src/ --line-length 88
isort src/ --profile black

# Lint code
flake8 src/ --max-line-length 88
mypy src/ --strict

# Run tests
pytest tests/ -v
pytest tests/ -m "unit" -v          # Unit tests only
pytest tests/ -m "integration" -v   # Integration tests only

# Test coverage
pytest tests/ --cov=src --cov-report=html

# Test Phase 1 completion
python test_window_capture.py
```

**Note**: Use PowerShell for all terminal commands in this Windows-specific project.

## 2. Architecture Overview

### Core Components
- **Application Entry**: `bitcrafty-extractor.py` - Main runner script
- **Real-time Extractor**: `realtime_extractor.py` - PyQt6 GUI application with system tray
- **Configuration**: `config/config_manager.py` - YAML-based configuration management
- **Window Capture**: `capture/window_capture.py` - Windows API game window capture
- **Hotkey Handler**: `capture/hotkey_handler.py` - Global hotkey system using pynput
- **AI Vision**: `ai_analysis/vision_client.py` - OpenAI GPT-4V/Anthropic Claude integration
- **Prompt System**: `ai_analysis/prompts*.py` - Structured prompts for AI analysis

### Major Dependencies
- **PyQt6**: GUI framework for main application
- **pynput**: Global hotkey handling across applications
- **pywin32**: Windows API integration for window capture
- **openai**: GPT-4 Vision API client
- **anthropic**: Claude Vision API client
- **structlog**: Structured logging throughout application
- **opencv-python**: Image processing and optimization
- **PyYAML**: Configuration file management

### Data Flow
```
Hotkey Press → Screenshot Queue → AI Analysis → Structured JSON → Export
     ↓              ↓                ↓             ↓            ↓
Global Hotkey → Window Capture → Vision Client → Data Merge → BitCrafty Format
```

### External APIs
- **OpenAI GPT-4 Vision API**: Primary AI vision analysis
- **Anthropic Claude Vision API**: Fallback AI provider
- **Windows API**: Game window detection and capture

## 3. Repository Structure (MANDATORY)

```
src/bitcrafty_extractor/
├── realtime_extractor.py      # Main PyQt6 application
├── config/
│   └── config_manager.py      # YAML configuration management
├── capture/
│   ├── window_capture.py      # Windows game window capture
│   └── hotkey_handler.py      # Global hotkey system
└── ai_analysis/
    ├── vision_client.py       # AI vision API clients
    ├── prompts.py            # Queue-based analysis prompts
    ├── prompts_new.py        # Single-item analysis prompts
    └── prompts_queue.py      # Additional queue prompts
config/
└── default.yaml              # Default configuration template
bitcrafty-extractor.py        # Application entry point
```

**REQUIREMENTS:**
- **Entry Point**: `bitcrafty-extractor.py` MUST handle application initialization
- **Source Package**: All code MUST be in `src/bitcrafty_extractor/` for proper packaging
- **Modular Components**: Each module MUST have single responsibility
- **Configuration**: MUST use YAML configuration in `config/` directory

## 4. Python Standards (ENFORCED)

### Version & Dependencies
- **Python 3.11+**: Required for performance and type hinting features
- **Type Hints**: MUST use complete type annotations on all functions/methods
- **Dataclasses**: MUST use `@dataclass` for data structures
- **Enums**: MUST use `Enum` classes for constants and options
- **Async/Await**: Use for AI API calls and I/O operations

### Code Style (pyproject.toml enforced)
- **Black Formatting**: Line length 88, Python 3.11+ target
- **Import Organization**: isort with black profile
- **Type Checking**: mypy strict mode required
- **Docstrings**: Google-style docstrings for all public functions

### Error Handling
- **Structured Logging**: MUST use `structlog` for all logging
- **Try/Catch Blocks**: MUST handle AI API failures gracefully
- **Fallback Providers**: MUST implement provider fallback for AI services
- **User Feedback**: MUST provide clear error messages in GUI

## 5. Component Guidelines (CRITICAL)

### Import Patterns
```python
# Standard library first
import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

# Third-party libraries
import structlog
from PyQt6.QtWidgets import QApplication

# Local relative imports (package-style)
from ..capture.window_capture import WindowCapture
from .vision_client import VisionClient
```

### AI Vision Client Requirements
- **Provider Abstraction**: MUST support multiple AI providers with fallback
- **Cost Tracking**: MUST estimate and track API usage costs
- **Image Optimization**: MUST compress images while preserving text clarity
- **Structured Output**: MUST enforce JSON schema validation
- **Rate Limiting**: MUST implement rate limiting and timeout handling

### Configuration Management
- **YAML-Based**: All configuration MUST use YAML format
- **Validation**: MUST validate configuration on load
- **Hot Reload**: SHOULD support configuration updates without restart
- **Secure Storage**: API keys MUST be stored securely
- **Environment Override**: MUST support environment variable overrides

### GUI Application (PyQt6)
- **System Tray**: MUST support minimizing to system tray
- **Background Operation**: MUST work while game is in focus
- **Threading**: MUST use QThread for long-running operations
- **Progress Feedback**: MUST provide visual/audio feedback for operations

## 6. Data Models & APIs (STRICT FORMAT)

### Screenshot Queue System
```python
@dataclass
class QueuedImage:
    image_data: bytes
    timestamp: datetime
    confidence: float
    metadata: Dict[str, Any]
```

### AI Response Format
```python
@dataclass 
class AIResponse:
    success: bool
    data: Optional[Dict[str, Any]]
    confidence: float
    provider: AIProvider
    cost_estimate: float
```

### Export Format (BitCrafty Integration)
- **Items**: Must include `name`, `tier`, `rarity`, `description`, `uses`, `confidence`
- **Crafts**: Must include `requirements`, `input_materials`, `output_materials`, `confidence`
- **Analysis**: Must include `analysis_type`, `screenshots_processed`, `total_confidence`

## 7. Hotkey System (SPECIFIC REQUIREMENTS)

### Default Bindings
- **Ctrl+Shift+E**: Queue screenshot for later analysis
- **Ctrl+Shift+X**: Analyze entire screenshot queue with AI
- **Configurable**: All hotkeys MUST be customizable in configuration

### Implementation Requirements
- **Global Scope**: MUST work when game has focus
- **Debouncing**: MUST prevent accidental multiple triggers (500ms default)
- **Background Monitoring**: MUST run in separate thread
- **Error Handling**: MUST gracefully handle hotkey conflicts

## 8. AI Analysis Standards (CRITICAL)

### Prompt Engineering
- **Structured Output**: MUST enforce JSON schema in prompts
- **Context-Aware**: MUST include game-specific context and examples
- **Error Recovery**: MUST handle malformed AI responses gracefully
- **Cost Optimization**: MUST use efficient prompts to minimize token usage

### Queue-Based Analysis
- **Batch Processing**: MUST analyze multiple screenshots together
- **Smart Detection**: AI MUST automatically identify items vs crafts
- **Confidence Scoring**: MUST provide confidence scores for all extractions
- **Data Merging**: MUST combine related data from multiple screenshots

### Provider Management
- **Primary/Fallback**: MUST support configurable primary and fallback providers
- **Cost Tracking**: MUST track and report API usage costs
- **Rate Limiting**: MUST respect API rate limits and implement backoff

## 9. Testing Standards (MANDATORY)

### Test Framework
- **pytest**: Primary testing framework with fixtures
- **pytest-mock**: For mocking external dependencies
- **pytest-cov**: Code coverage tracking
- **Test Markers**: Use markers for `unit`, `integration`, `vision` tests

### Required Test Categories
- **Unit Tests**: Component isolation, mocking external dependencies
- **Integration Tests**: AI API integration, configuration loading
- **Vision Tests**: Screenshot processing, image optimization
- **GUI Tests**: PyQt6 widget behavior, user interactions

### Mock Requirements
- **AI APIs**: MUST mock OpenAI/Anthropic API calls in unit tests
- **Windows API**: MUST mock win32 calls for cross-platform testing
- **File System**: MUST mock file operations for deterministic tests

## 10. Windows Platform Requirements (CRITICAL)

### Windows API Integration
- **pywin32**: MUST use for window detection and capture
- **Error Handling**: MUST handle Windows API failures gracefully
- **Administrator Rights**: SHOULD handle elevation requirements
- **Multi-Monitor**: MUST support multi-monitor setups

### Game Window Detection
- **Pattern Matching**: MUST support configurable window title patterns
- **Auto-Detection**: MUST automatically find game windows
- **Validation**: MUST verify window accessibility before capture

## 11. Configuration Management (ENFORCED)

### YAML Structure
```yaml
ai:
  default_provider: "openai_gpt4v"
  fallback_provider: "anthropic_claude"
  openai:
    api_key: ""
    model: "gpt-4-vision-preview"
    timeout: 30.0
  anthropic:
    api_key: ""
    model: "claude-3-sonnet-20240229" 
    timeout: 30.0

hotkeys:
  queue_screenshot: "ctrl+shift+e"
  analyze_queue: "ctrl+shift+x"
  enabled: true

capture:
  format: "PNG"
  quality: 95
  auto_detect_game_window: true
```

### Validation Requirements
- **Schema Validation**: MUST validate all configuration on load
- **Type Checking**: MUST validate data types and ranges
- **API Key Validation**: MUST verify API keys before use
- **Hotkey Validation**: MUST validate hotkey format and availability

## 12. Development Workflow (MANDATORY)

### Code Quality Pipeline
1. **Pre-commit Hooks**: black, isort, flake8, mypy
2. **Testing**: Run appropriate test suites for changes
3. **Type Checking**: mypy strict mode compliance
4. **Documentation**: Update docstrings and README as needed

### AI Integration Testing
- **Mock Testing**: Use mocked API responses for unit tests
- **Integration Testing**: Test with real APIs using test accounts
- **Cost Monitoring**: Track API usage during development
- **Fallback Testing**: Verify provider fallback mechanisms

### Release Process
- **Version Bumping**: Update version in pyproject.toml
- **Dependency Updates**: Verify compatibility with latest versions
- **Platform Testing**: Test on target Windows versions
- **Documentation**: Update README with new features/changes

## 13. Performance & Cost Optimization (CRITICAL)

### Image Processing
- **Compression**: MUST optimize images while preserving text clarity
- **Format Selection**: Use PNG for text-heavy images, JPEG for screenshots
- **Size Limits**: Enforce maximum image dimensions (1024px default)
- **Batch Processing**: Process multiple images efficiently

### API Cost Management
- **Provider Selection**: Choose cost-effective providers for routine tasks
- **Token Optimization**: Minimize prompt tokens while maintaining accuracy
- **Caching**: Cache similar analysis results when appropriate
- **Usage Tracking**: Monitor and report real-time API costs

## 14. Security & Privacy (IMPORTANT)

### API Key Management
- **Secure Storage**: Never commit API keys to version control
- **Environment Variables**: Support API key loading from environment
- **Configuration Protection**: Warn users about API key security
- **Key Validation**: Verify API keys before making requests

### Data Handling
- **Local Processing**: Keep screenshots local unless explicitly sent to AI
- **Temporary Files**: Clean up temporary screenshot files
- **User Consent**: Make AI analysis opt-in with clear cost implications
- **Data Retention**: Don't store analysis results longer than necessary