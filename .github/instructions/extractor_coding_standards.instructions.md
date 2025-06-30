---
applyTo: '**'
---

# BitCrafty-Extractor Coding Standards

**AI agents and contributors must follow these guidelines** to ensure code quality, maintainability, and architectural consistency.

## 1. Quick Reference

### Development Commands
```powershell
# Setup
python -m venv venv && venv\Scripts\activate
pip install -e ".[dev]"

# Quality Checks
black . --line-length 88 && isort . --profile black
flake8 . --max-line-length 88 && mypy src/ --strict

# Testing
pytest tests/ -v                    # All tests
pytest tests/ --cov=src --cov-report=html  # With coverage

# Run Application
python bitcrafty-extractor.py
```

### Core Architecture
```
Hotkey → Screenshot → AI Analysis → Rich UI → Export
   ↓         ↓           ↓          ↓        ↓
pynput → Win32API → OpenAI/Claude → Rich → JSON
```

## 2. Repository Structure (MANDATORY)

```
bitcrafty-extractor.py             # Main entry point
src/bitcrafty_extractor/            # Package source
├── config/config_manager.py       # YAML configuration
├── capture/{window_capture,hotkey_handler}.py
└── ai_analysis/{vision_client,prompts*}.py
config/default.yaml                # Configuration template
test/                              # Test suite
pyproject.toml                     # Dependencies & settings
```

**REQUIREMENTS:**
- Entry point: `bitcrafty-extractor.py`
- All code: `src/bitcrafty_extractor/` package structure
- Configuration: YAML files in `config/`
- Single responsibility per module

## 3. Python Standards (ENFORCED)

### Code Quality
- **Python 3.11+**: Required for performance and type features
- **Type Hints**: Complete annotations on all functions/methods
- **Black/isort**: Line length 88, automatic formatting
- **mypy**: Strict mode required
- **Dataclasses/Enums**: Use for data structures and constants

### Error Handling & Logging
- **structlog**: Use for all logging throughout application
- **Try/Catch**: Handle AI API failures gracefully with fallback providers
- **User Feedback**: Provide clear error messages in console interface

### Import Organization
```python
# Standard library
import asyncio, json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

# Third-party
import structlog
from rich.console import Console

# Local (package-style)
from ..capture.window_capture import WindowCapture
```

## 4. Console Interface (CRITICAL)

### 4-Panel Layout Structure
```python
# REQUIRED: Hierarchical layout with fixed ratios
layout = Layout()
layout.split_column(Layout(name="main", ratio=4), Layout(name="debug", ratio=1))
layout["main"].split_row(Layout(name="left_column", ratio=1), Layout(name="queue", ratio=1))
layout["left_column"].split_column(Layout(name="commands", ratio=3), Layout(name="session_stats", ratio=1))
```

### Panel Responsibilities
- **Commands** (top-left, 3/4): Application commands, workflow, hotkeys
- **Session Stats** (bottom-left, 1/4): Real-time statistics, costs
- **Queue** (right, full): Screenshot queue + analysis results
- **Debug** (bottom, full): Status messages, error logs

### UI Stability Requirements (MANDATORY)
- **Fixed Ratios**: Panel sizes MUST NOT change during updates
- **Content Constraints**: All content MUST fit within panel boundaries
- **Update Isolation**: Panel updates MUST NOT affect other panels
- **Dedicated Methods**: Each panel MUST have `update_*_panel() -> Panel`
- **Batched Updates**: Use single `update_display()` for all panels
- **Refresh Rate**: Maximum 1Hz to prevent UI flickering

## 5. Core Systems

### AI Vision Client
- **Multi-Provider**: Support OpenAI GPT-4V and Anthropic Claude with fallback
- **Cost Tracking**: Track and report API usage costs in real-time
- **Image Optimization**: Compress images while preserving text clarity
- **JSON Schema**: Enforce structured output validation
- **Rate Limiting**: Respect API limits with exponential backoff

### Configuration (YAML)
```yaml
ai:
  primary_provider: "anthropic"
  fallback_provider: "openai"
  openai: { api_key: "", model: "gpt-4-vision-preview" }
  anthropic: { api_key: "", model: "claude-3-sonnet" }
hotkeys:
  queue_screenshot: "alt+e"
  analyze_queue: "alt+q"
  quit_application: "alt+f"
capture:
  format: "PNG"
  quality: 95
```

### Hotkey System
- **Global Scope**: Work when game has focus (no alt-tabbing)
- **Debouncing**: Prevent accidental triggers (500ms default)
- **Background Thread**: Run monitoring separately from main application
- **Configurable**: All hotkeys customizable via YAML

### Windows Integration
- **pywin32**: Use for game window detection and capture
- **Multi-Monitor**: Support multi-monitor setups
- **Error Handling**: Gracefully handle Windows API failures
- **Admin Rights**: Handle elevation requirements when needed

## 6. Data Models & Export

### Core Data Structures
```python
@dataclass
class QueuedImage:
    image_data: bytes
    timestamp: datetime
    confidence: float
    metadata: Dict[str, Any]

@dataclass 
class AIResponse:
    success: bool
    data: Optional[Dict[str, Any]]
    confidence: float
    provider: AIProvider
    cost_estimate: float
```

### BitCrafty Export Format
- **Items**: `name`, `tier`, `rarity`, `description`, `uses`, `confidence`
- **Crafts**: `requirements`, `input_materials`, `output_materials`, `confidence`
- **Analysis**: `analysis_type`, `screenshots_processed`, `total_confidence`

## 7. Testing Standards (MANDATORY)

### Test Framework
- **pytest**: Primary framework with fixtures and markers
- **pytest-mock**: Mock external dependencies (APIs, file system)
- **pytest-cov**: Code coverage tracking and reporting
- **Test Categories**: `unit`, `integration`, `vision` test markers

### Required Tests
- **Unit Tests**: Component isolation with mocked dependencies
- **Integration Tests**: Real API integration with test accounts
- **Vision Tests**: Screenshot processing and image optimization
- **Console Tests**: Rich interface behavior and layout stability

### Mock Strategy
- **AI APIs**: Mock OpenAI/Anthropic calls in unit tests
- **Windows API**: Mock win32 calls for cross-platform testing
- **File Operations**: Mock file system for deterministic tests

## 8. Development Workflow (MANDATORY)

### Code Quality Pipeline
1. **Format & Lint**: `black . && isort . && flake8 . && mypy src/`
2. **Test**: Run appropriate test suites for changes
3. **Documentation**: Update docstrings and README as needed

### AI Integration Testing
- **Mock Development**: Use mocked responses for fast iteration
- **Real API Testing**: Test with actual APIs using test accounts
- **Cost Monitoring**: Track and limit API usage during development
- **Fallback Verification**: Test provider fallback scenarios

### Release Process
- **Version Update**: Bump version in `pyproject.toml`
- **Dependency Check**: Verify compatibility with latest versions
- **Platform Testing**: Test on target Windows versions
- **Documentation**: Update README and coding standards

## 9. Security & Performance

### API Key Security
- **No Commits**: Never commit API keys to version control
- **Environment Support**: Load API keys from environment variables
- **User Warnings**: Alert users about API key security practices
- **Key Validation**: Test API keys before use

### Performance Optimization
- **Image Compression**: Optimize images while preserving text clarity
- **Token Efficiency**: Minimize prompt tokens for cost reduction
- **Batch Processing**: Process multiple screenshots efficiently
- **Rate Limiting**: Respect API limits with intelligent backoff

### Data Privacy
- **Local Processing**: Keep screenshots local unless sent to AI
- **Temporary Cleanup**: Remove temporary files after processing
- **User Consent**: Make AI analysis opt-in with cost transparency
- **Data Retention**: Don't store analysis results longer than necessary