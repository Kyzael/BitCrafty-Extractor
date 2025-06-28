# BitCrafty-Extractor Tests

This directory contains test scripts for validating the BitCrafty-Extractor functionality.

## Test Scripts

### `test_phase1_completion.py`
Validates Phase 1 completion with focus-based fullscreen capture:
- BitCraft process detection (bitcraft.exe only)
- Window finding and validation
- Focus-based fullscreen screenshot capture
- Image quality analysis
- Security validation (process isolation)

**Requirements:**
- BitCraft must be running in windowed fullscreen mode
- BitCraft must be the active foreground window during test
- All dependencies installed (`pip install -r requirements.txt`)

**Usage:**
```bash
cd test
python test_phase1_completion.py
```

The script will:
1. Give you 5 seconds to switch to BitCraft window
2. Test all Phase 1 functionality
3. Save a test screenshot to `test/output/bitcraft_capture_test.png`
4. Provide detailed validation results

## Output

Test screenshots are saved to `test/output/` directory:
- `bitcraft_capture_test.png` - High-quality fullscreen capture for validation

## Expected Results

✅ **Successful Test Output:**
- File size: 2+ MB (indicates rich content)
- Pixel variance: 1000+ (complex game graphics)
- Mean brightness: 10-240 (normal game content)
- All validation checks pass

❌ **Common Issues:**
- BitCraft not in focus → Only captures when foreground
- Black screenshots → Use windowed fullscreen mode
- Small file sizes → Hardware acceleration blocking (fixed with fullscreen)
