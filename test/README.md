# BitCrafty-Extractor Tests

This directory contains test scripts for validating the BitCrafty-Extractor functionality.

## Test Scripts

### `test_window_capture.py`
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
python test\test_window_capture.py
```

### `test_hotkeys.py`
Validates Phase 2A hotkey system functionality:
- Global hotkey registration and monitoring
- Cross-application hotkey functionality
- Debouncing and error handling
- Hotkey callback execution

**Requirements:**
- `pynput` library installed (included in requirements.txt)
- Appropriate permissions for global hotkeys
- No conflicting applications using same key combinations

**Usage:**
```bash
python test\test_hotkeys.py
```

**Test Hotkeys:**
- `Ctrl+Shift+E` - Queue Screenshot
- `Ctrl+Shift+X` - Analyze Queue
- `Ctrl+Shift+P` - Toggle Monitoring

## Output

Test screenshots are saved to project root:
- `test_capture_[timestamp].png` - High-quality fullscreen capture for validation

## Expected Results

### Window Capture Test ✅
- File size: 2+ MB (indicates rich content)
- Pixel variance: 4000+ (complex game graphics)
- Mean brightness: 10-240 (normal game content)
- All validation checks pass

### Hotkey Test ✅
- Global hotkeys register successfully
- Hotkeys work even when other apps have focus
- Debouncing prevents multiple triggers (0.5s delay)
- Clean startup and shutdown

## Common Issues

### Window Capture
- BitCraft not in focus → Only captures when foreground
- Black screenshots → Use windowed fullscreen mode
- Small file sizes → Hardware acceleration blocking (fixed with fullscreen)

### Hotkeys
- Import errors → Install dependencies: `pip install -r requirements.txt`
- Hotkeys not working → Check for conflicting applications
- Permission errors → May need elevated permissions on some systems
