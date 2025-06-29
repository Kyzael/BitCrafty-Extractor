# AI Analysis Tests

Tests for AI vision analysis, prompt optimization, and provider comparison.

## Quick Start

```powershell
# Prompt validation tests (fast, no API calls)
python test\ai_analysis\test_prompts.py

# Provider comparison (requires API keys, costs ~$0.06)
python test\ai_analysis\test_provider_comparison.py

# With pytest framework
pytest test/ai_analysis/ -v
```

## Test Files

### `test_prompts.py` ✅
**Purpose**: Validate prompt generation and optimization  
**Results**: 28/28 tests passing, validates 55-73% size reduction

**What it tests**:
- All extraction types (queue analysis, item tooltip, craft recipe, single item)
- JSON schema validity and BitCraft terminology alignment
- Performance benchmarks (prompt generation < 1s)

### `test_provider_comparison.py` 💰
**Purpose**: Real AI provider benchmarking with actual API calls  
**Cost**: ~$0.06 per run, requires test screenshots

## Test Data

Screenshots required in `test/test_data/craft/`:
- `weave_rough_cloth_strip_input.png` - Input materials
- `weave_rough_cloth_strip.png` - Recipe interface  
- `weave_rough_cloth_strip_output.png` - Output materials

## Recommended Configuration

**Primary**: Claude 3.5 Sonnet (best accuracy)  
**Fallback**: Claude 3 Haiku (cost-effective) or GPT-4 Turbo (reliable)
