# BitCrafty-Extractor Test Suite

Comprehensive test suite with **pytest framework** (modern) and **standalone scripts** (legacy support).

## ✅ Quick Start (52/52 Working Tests)

```powershell
# Install test dependencies
pip install -e ".[dev]"

# Run all working tests (~5 seconds, no API costs)
pytest test/unit/ai_analysis/ test/integration/ -v

# Run by component
pytest test/unit/ai_analysis/test_vision_client.py -v    # 16 tests
pytest test/unit/ai_analysis/test_prompts.py -v         # 28 tests  
pytest test/integration/test_configuration_validation.py -v  # 8 tests
```

## Test Categories

### 🧪 Unit Tests (`test/unit/`)
Fast, isolated component testing with mocked dependencies:
- **AI Analysis**: VisionClient, PromptBuilder ✅ **44/44 PASSED**
- **Config/Capture**: Needs API updates 🔧

### 🔗 Integration Tests (`test/integration/`)
Component integration without expensive API calls:
- **Configuration Validation**: System integration ✅ **8/8 PASSED**
- **Performance**: ~2.5 seconds (optimized, no API costs)

### 🤖 AI Provider Comparison (Standalone)
Real AI testing with actual API calls (costs money):
```powershell
python test\ai_analysis\test_provider_comparison.py          # Quick comparison
python test\ai_analysis\test_provider_comparison.py -verbose # Detailed analysis
```

## Test Structure

```
test/
├── conftest.py                      # Pytest configuration
├── unit/ai_analysis/               # Unit tests ✅
│   ├── test_vision_client.py       # 16/16 PASSED  
│   └── test_prompts.py             # 28/28 PASSED
├── integration/                    # Integration tests ✅
│   └── test_configuration_validation.py  # 8/8 PASSED
├── ai_analysis/                    # Standalone tools
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

# All tests (some may fail due to interface mismatches)
pytest test/ -v
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

| Test Type | Count | Time | API Costs |
|-----------|-------|------|-----------|
| Unit Tests | 44 | ~3s | None |
| Integration | 8 | ~2.5s | None ✅ |
| Provider Comparison | 5 | ~50s | ~$0.06 💰 |

**Total Development Tests**: 52 tests in ~5 seconds with zero API costs!
