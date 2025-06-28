# BitCrafty-Extractor Tests

This directory contains organized test scripts for validating the BitCrafty-Extractor functionality.

## Test Structure

### Core Component Tests

#### `test_window_capture.py`
Validates Phase 1 completion with focus-based fullscreen capture:
- BitCraft process detection (bitcraft.exe only)
- Window finding and validation
- Focus-based fullscreen screenshot capture
- Image quality analysis
- Security validation (process isolation)

**Usage:** `python test\test_window_capture.py`

#### `test_hotkeys.py`
Validates Phase 2A hotkey system functionality:
- Global hotkey registration and monitoring
- Cross-application hotkey functionality
- Debouncing and error handling
- Hotkey callback execution

**Usage:** `python test\test_hotkeys.py`

### AI Analysis Tests (`ai_analysis/`)

#### `test_provider_comparison.py`
Comprehensive AI provider comparison and accuracy testing:
- Multi-provider analysis (OpenAI GPT-4o/GPT-4-Turbo, Anthropic Claude)
- Recipe quantity accuracy validation
- Item detail extraction testing
- Cost comparison across providers
- Performance benchmarking

**Usage:** `python test\ai_analysis\test_provider_comparison.py`

### Integration Tests (`integration/`)

#### `test_configuration_validation.py`
Complete end-to-end system validation:
- Configuration loading and API key validation
- Real AI analysis with test images
- JSON response parsing verification
- Accuracy assessment with known data
- Provider fallback testing
- Cost estimation validation

**Usage:** `python test\integration\test_configuration_validation.py`

## Test Data

Test images and data are located in `test_data/`:
- `craft/` - Craft recipe screenshots for AI analysis testing
- Other test assets as needed

## Requirements

### General Requirements
- All dependencies installed: `pip install -r requirements.txt`
- Python 3.8+ environment
- Windows OS (for window capture and hotkeys)

### Specific Test Requirements

**Window Capture Tests:**
- BitCraft must be running in windowed fullscreen mode
- BitCraft must be the active foreground window during test

**Hotkey Tests:**
- Appropriate permissions for global hotkeys
- No conflicting applications using same key combinations

**AI Analysis Tests:**
- Valid API keys for OpenAI and/or Anthropic (optional for some tests)
- Internet connectivity for API calls
- Sufficient API credits for analysis

**Integration Tests:**
- At least one AI provider configured with valid API key
- GUI environment (Windows desktop)

## Running All Tests

```powershell
# Run specific test categories
python test\test_window_capture.py
python test\test_hotkeys.py
python test\ai_analysis\test_provider_comparison.py
python test\integration\test_configuration_validation.py

# Or use pytest for structured testing
python -m pytest test\ -v
```

## Expected Results

### Core Component Tests ✅

**Window Capture:**
- File size: 2+ MB (indicates rich content)
- Pixel variance: 4000+ (complex game graphics)  
- Mean brightness: 10-240 (normal game content)
- All validation checks pass

**Hotkey System:**
- Global hotkeys register successfully
- Hotkeys work even when other apps have focus
- Debouncing prevents multiple triggers (0.5s delay)
- Clean startup and shutdown

### AI Analysis Tests ✅

**Provider Comparison:**
- Anthropic Claude: Highest accuracy for quantity reading
- OpenAI GPT-4-Turbo: Good accuracy, reliable fallback
- OpenAI GPT-4o: May misread quantities (3x vs 1x)
- Cost analysis shows Claude is most cost-effective

**Configuration Validation:**
- API key validation passes for all configured providers
- Real AI analysis extracts accurate item details
- Recipe quantities read correctly (1x input → 1x output)
- Confidence scores above 0.9 for good test data
- Provider fallback works when primary fails

## Output Files

Test outputs are saved to appropriate locations:
- Screenshots: Project root (`test_capture_[timestamp].png`)
- Test results: Console output with detailed validation reports
- Error logs: Structured error reporting for debugging

## Common Issues

### Window Capture
- **BitCraft not in focus** → Only captures when foreground
- **Black screenshots** → Use windowed fullscreen mode
- **Small file sizes** → Hardware acceleration blocking (fixed with fullscreen)

### Hotkeys
- **Import errors** → Install dependencies: `pip install -r requirements.txt`
- **Hotkeys not working** → Check for conflicting applications
- **Permission errors** → May need elevated permissions on some systems

### AI Analysis
- **API errors** → Verify API keys are valid and have sufficient credits
- **Import errors** → Ensure `openai` and `anthropic` packages installed
- **Image processing errors** → Check PIL/Pillow installation
- **Cost concerns** → Use compact prompts and image optimization
- **Network errors** → Check internet connection and API service status
- **Quantity misreading** → Switch to Anthropic Claude or GPT-4-Turbo for accuracy

### Integration
- **Configuration not loading** → Check YAML file format and permissions
- **Tests failing** → Ensure all dependencies installed and API keys valid
- **Fallback not working** → Verify secondary provider is configured correctly

## Test Organization

The tests are organized into logical categories:
- **Core component tests** → Individual functionality validation
- **AI analysis tests** → AI provider testing and comparison  
- **Integration tests** → End-to-end system validation

Each category has its own directory with detailed README files explaining the specific tests and their purposes.
