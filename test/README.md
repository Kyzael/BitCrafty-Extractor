# BitCrafty-Extractor Test Suite

Comprehensive test suite with **pytest framework** (modern) and **standalone scripts** (legacy support).

## ✅ Quick Start

```powershell
# Install test dependencies
pip install -e ".[dev]"

# Run all unit tests (fast, no API costs) 
pytest test/ -v

# Run by component
pytest test/unit/ai_analysis/ -v           # AI component tests
pytest test/unit/capture/ -v               # Capture component tests
pytest test/unit/config/ -v                # Config component tests
pytest test/integration/ -v                # Integration tests
```

## Test Categories

### 🧪 Unit Tests (`test/unit/`)
Fast, isolated component testing with mocked dependencies:
- **AI Analysis**: VisionClient, PromptBuilder ✅
- **Config**: ConfigManager validation ✅  
- **Capture**: WindowCapture, HotkeyHandler ✅
- **Performance**: ~6 seconds total, zero API costs

### 🔗 Integration Tests (`test/integration/`)
Component integration without expensive API calls:
- **Configuration Validation**: System integration ✅
- **Performance**: ~2.5 seconds (optimized, no API costs)

### 🤖 AI Provider Comparison (Standalone)
Real AI testing with actual API calls (costs money) - **excluded from pytest test/**:
```powershell
# Run separately with real API calls
python test\ai_analysis\test_provider_comparison.py          # Quick comparison
python test\ai_analysis\test_provider_comparison.py -verbose # Detailed analysis
```

## Test Structure

```
test/
├── conftest.py                      # Pytest configuration
├── unit/ai_analysis/               # Unit tests ✅
│   ├── test_vision_client.py       # VisionClient tests  
│   └── test_prompts.py             # PromptBuilder tests
├── unit/config/                    # Config tests ✅
│   ├── test_config_manager.py      # ConfigManager tests
│   └── test_config_validation.py   # Config validation tests
├── unit/capture/                   # Capture tests ✅
│   ├── test_window_capture.py      # WindowCapture tests
│   └── test_hotkey_handler.py      # HotkeyHandler tests
├── integration/                    # Integration tests ✅
│   └── test_configuration_validation.py  # System integration tests
├── ai_analysis/                    # Standalone tools (excluded from pytest)
│   └── test_provider_comparison.py # Provider benchmarking
└── test_data/                      # Test assets
    ├── item/                       # Item screenshots
    └── craft/                      # Recipe screenshots
```

## Pytest Options

```powershell
# Test markers
pytest test/ -m "unit"              # Fast unit tests only
pytest test/ -m "integration"       # Integration tests only  

# Coverage
pytest test/ --cov=src --cov-report=html

# Run all tests (includes some failing config tests due to interface mismatches)
pytest test/ -v

# Run the excluded provider comparison tests separately
python test\ai_analysis\test_provider_comparison.py -verbose
```

## Requirements & Troubleshooting

### Prerequisites
- Python 3.11+, Windows OS
- Dependencies: `pip install -r requirements.txt`
- For AI tests: Valid API keys for OpenAI/Anthropic

### Common Issues
- **API errors**: Check API keys and credits
- **Import errors**: Run `pip install -e ".[dev]"`
- **Window capture tests**: Need BitCraft running in windowed fullscreen
- **Hotkey tests**: May require elevated permissions

## Performance Summary

| Test Type | Runtime | API Costs |
|-----------|---------|-----------|
| Unit Tests | ~5s | None |
| Integration | ~2.5s | None ✅ |
| Provider Comparison | ~50s | ~$0.06 💰 |

**Development Tests**: Fast execution with zero API costs!
