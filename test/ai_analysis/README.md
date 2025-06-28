# AI Analysis Tests

This directory contains tests for AI vision analysis functionality and prompt optimization.

## Test Files

### test_prompts.py
- **Purpose**: Validate the optimized prompts.py module and all extraction types
- **Usage**: `python test\ai_analysis\test_prompts.py`
- **What it tests**: 
  - Prompt generation for all extraction types (QUEUE_ANALYSIS, ITEM_TOOLTIP, CRAFT_RECIPE, SINGLE_ITEM_TEST)
  - Size optimizations (55-73% reduction from original prompts)
  - JSON schema validity in examples
  - BitCraft-specific terminology and data format alignment
  - Performance benchmarks for prompt generation
- **Expected Results**: All 14 tests should pass with size metrics showing optimized prompts

### test_provider_comparison.py
- **Purpose**: Compare accuracy and performance across different AI providers and models  
- **Usage**: `python test\ai_analysis\test_provider_comparison.py`
- **What it tests**: 
  - OpenAI GPT-4o, GPT-4-Turbo
  - Anthropic Claude 3.5 Sonnet, Claude 3 Haiku (cheaper model)
  - Recipe quantity accuracy using optimized prompts
  - Item detail extraction with reduced token usage
  - Cost comparison across providers
- **Test Data**: Uses craft recipe screenshots in `test/test_data/craft/`
- **Output**: Table comparison of provider accuracy, costs, and validation results with optimized prompts

## Test Data Requirements

The tests require screenshot data in `test/test_data/craft/`:
- `weave_rough_cloth_strip_input.png` - Input materials view
- `weave_rough_cloth_strip.png` - Main recipe interface
- `weave_rough_cloth_output.png` - Output materials view

## Running Tests

```powershell
# Run prompt validation tests (recommended)
python test\ai_analysis\test_prompts.py

# Run provider comparison test (requires API keys and test screenshots)
python test\ai_analysis\test_provider_comparison.py

# All AI analysis tests using pytest
python -m pytest test\ai_analysis\ -v
```

## Prompt Optimization Results

The `test_prompts.py` validates that our prompt optimizations are working:
- **Queue Analysis (Full)**: ~2,043 characters (55.7% reduction from original 4,607)
- **Queue Analysis (Compact)**: ~1,228 characters (73.3% reduction)
- **Item Tooltip**: ~606 characters 
- **Craft Recipe**: ~1,054 characters
- **Single Item Test**: ~670 characters

## Data Format Alignment

Tests verify that prompts align with actual game data format:
- Uses `"item"` and `"qty"` fields (matching crafts.json)
- Supports variable quantities with strings like `"1-3"`
- Includes profession, building, tool requirements
- Simplified schema without unnecessary complexity

## Provider Accuracy Notes

Based on testing with optimized prompts and table format results:
- **Anthropic Claude 3.5 Sonnet**: Most accurate for quantity reading, fastest processing
- **Anthropic Claude 3 Haiku**: Cheaper alternative, good accuracy for cost-sensitive use cases
- **OpenAI GPT-4-Turbo**: Good accuracy, reliable performance, benefits from size optimization
- **OpenAI GPT-4o**: Latest model but may have quantity reading issues (reports 3x instead of 1x)

**Provider Results Table**: The test displays results in a structured table showing:
- Provider name and model
- Success/failure status
- Confidence scores
- Processing costs
- Response times
- Recipe validation results

Recommended configuration: Claude 3.5 Sonnet primary, Claude 3 Haiku for cost optimization, GPT-4-Turbo fallback.
