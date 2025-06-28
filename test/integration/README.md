# Integration Tests

This directory contains integration tests that test the interaction between multiple components.

## Test Files

### test_configuration_validation.py
- **Purpose**: Comprehensive validation of configuration, API connectivity, and end-to-end AI analysis
- **Usage**: `python test\integration\test_configuration_validation.py`
- **What it tests**:
  - Configuration loading and validation
  - API key validation for all configured providers
  - End-to-end AI vision analysis with real images
  - JSON response parsing and data extraction
  - Provider fallback functionality
  - Cost estimation accuracy
- **Test Data**: Uses craft recipe screenshots for real-world validation
- **Output**: Detailed validation report with accuracy assessment

## Running Tests

```powershell
# Run comprehensive configuration validation
python test\integration\test_configuration_validation.py

# All integration tests (when more are added)
python -m pytest test\integration\ -v
```

## What Gets Validated

1. **Configuration Management**
   - YAML config loading
   - API key presence and format
   - Provider settings validation

2. **API Connectivity**
   - OpenAI API validation (if configured)
   - Anthropic API validation (if configured)
   - Proper error handling for invalid keys

3. **AI Analysis Pipeline**
   - Image processing and optimization
   - Multi-provider AI analysis
   - JSON response parsing
   - Data structure validation

4. **Accuracy Assessment**
   - Item detail extraction (name, tier, rarity, description)
   - Recipe quantity reading (input/output materials)
   - Confidence scoring validation
   - Cost estimation verification

## Test Requirements

- At least one AI provider configured with valid API key
- Test data images in `test/test_data/craft/`
- Internet connectivity for API calls
- Sufficient API credits for test analysis
