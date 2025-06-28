# AI Analysis Tests

This directory contains tests for AI vision analysis functionality.

## Test Files

### test_provider_comparison.py
- **Purpose**: Compare accuracy and performance across different AI providers and models
- **Usage**: `python test\ai_analysis\test_provider_comparison.py`
- **What it tests**: 
  - OpenAI GPT-4o, GPT-4-Vision-Preview, GPT-4-Turbo
  - Anthropic Claude 3.5 Sonnet
  - Recipe quantity accuracy 
  - Item detail extraction
  - Cost comparison across providers
- **Test Data**: Uses craft recipe screenshots in `test/test_data/craft/`
- **Output**: Detailed comparison of provider accuracy and costs

## Test Data Requirements

The tests require screenshot data in `test/test_data/craft/`:
- `weave_rough_cloth_strip_input.png` - Input materials view
- `weave_rough_cloth_strip.png` - Main recipe interface
- `weave_rough_cloth_output.png` - Output materials view

## Running Tests

```powershell
# Run provider comparison test
python test\ai_analysis\test_provider_comparison.py

# All AI analysis tests (when more are added)
python -m pytest test\ai_analysis\ -v
```

## Provider Accuracy Notes

Based on testing:
- **Anthropic Claude 3.5 Sonnet**: Most accurate for quantity reading
- **OpenAI GPT-4-Turbo**: Good accuracy, reliable fallback
- **OpenAI GPT-4o**: Tends to misread quantities (3x instead of 1x)
- **OpenAI GPT-4-Vision-Preview**: Older model, less accurate

Recommended configuration: Claude primary, GPT-4-Turbo fallback.
