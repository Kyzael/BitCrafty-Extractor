"""
Test script to verify the error handling fixes for the BitCrafty Extractor.

This script tests:
1. The UnboundLocalError fix in _hotkey_analyze_async
2. The data validation fix in _show_analysis_results
"""

import asyncio
import sys
import os
from unittest.mock import Mock, patch, AsyncMock

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the main script and extract the class
import importlib.util
spec = importlib.util.spec_from_file_location("main", "bitcrafty-extractor.py")
main_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_module)
BitCraftyExtractor = main_module.BitCraftyExtractor

async def test_hotkey_analyze_async_error_handling():
    """Test that _hotkey_analyze_async handles exceptions without UnboundLocalError."""
    print("Testing _hotkey_analyze_async error handling...")
    
    # Create a mock extractor instance
    extractor = BitCraftyExtractor()
    extractor.add_debug_message = Mock()
    extractor.logger = Mock()
    extractor.analysis_in_progress = False
    
    # Mock analyze_queue to raise an exception
    extractor.analyze_queue = AsyncMock(side_effect=Exception("Test exception"))
    
    # This should not raise UnboundLocalError
    try:
        await extractor._hotkey_analyze_async()
        print("✅ No UnboundLocalError occurred")
        
        # Verify error handling was called
        extractor.add_debug_message.assert_called()
        extractor.logger.error.assert_called_with("Hotkey analysis error", error="Test exception")
        
        # Verify analysis_in_progress was reset
        assert extractor.analysis_in_progress == False
        print("✅ Error handling and cleanup worked correctly")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    return True

def test_show_analysis_results_data_validation():
    """Test that _show_analysis_results handles invalid data types."""
    print("Testing _show_analysis_results data validation...")
    
    # Create a mock extractor instance
    extractor = BitCraftyExtractor()
    extractor.add_debug_message = Mock()
    extractor.logger = Mock()
    extractor.screenshot_queue = []
    
    # Test with string instead of dict (the original error)
    mock_result = Mock()
    mock_result.cost_estimate = 0.0
    
    try:
        # This should not raise AttributeError: 'str' object has no attribute 'get'
        extractor._show_analysis_results("invalid string data", mock_result)
        
        # Verify error message was logged
        extractor.add_debug_message.assert_called_with("❌ Invalid analysis data format: str")
        extractor.logger.error.assert_called()
        print("✅ Invalid data type handled correctly")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    # Test with valid dict data
    extractor.add_debug_message.reset_mock()
    extractor.logger.reset_mock()
    
    # Mock the export manager
    extractor.export_manager = Mock()
    extractor.export_manager.process_extraction_results.return_value = {
        'items_found_new': 0,
        'crafts_found_new': 0,
        'items_found_duplicates': 0,
        'crafts_found_duplicates': 0,
        'new_items_added': 0,
        'new_crafts_added': 0
    }
    extractor.session_items_found = []
    extractor.session_crafts_found = []
    extractor.total_screenshots_analyzed = 0
    extractor.total_cost = 0.0
    extractor._log_analysis_to_disk = Mock()
    
    valid_data = {
        'items_found': [],
        'crafts_found': [],
        'screenshots_processed': 1
    }
    
    try:
        extractor._show_analysis_results(valid_data, mock_result)
        # Should not call error logging for valid data
        error_calls = [call for call in extractor.add_debug_message.call_args_list 
                      if "Invalid analysis data format" in str(call)]
        assert len(error_calls) == 0
        print("✅ Valid data processed correctly")
        
    except Exception as e:
        print(f"❌ Unexpected error with valid data: {e}")
        return False
    
    return True

async def main():
    """Run all error handling tests."""
    print("🧪 Running BitCrafty Extractor Error Handling Tests")
    print("=" * 60)
    
    test1 = await test_hotkey_analyze_async_error_handling()
    print()
    test2 = test_show_analysis_results_data_validation()
    
    print()
    print("=" * 60)
    if test1 and test2:
        print("🎉 All error handling tests passed!")
        return True
    else:
        print("❌ Some tests failed")
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
