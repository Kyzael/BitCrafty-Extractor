"""
Unit tests for the main BitCraftyExtractor class.

These tests focus on the analyze_queue method and _show_analysis_results data validation.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import sys
import os
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the main module
import importlib.util
spec = importlib.util.spec_from_file_location("main", "bitcrafty-extractor.py")
main_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_module)
BitCraftyExtractor = main_module.BitCraftyExtractor
ImageData = main_module.ImageData


class TestBitCraftyExtractor:
    """Test the main BitCraftyExtractor class."""
    
    @pytest.fixture
    def extractor(self):
        """Create a BitCraftyExtractor instance for testing."""
        extractor = BitCraftyExtractor()
        
        # Mock dependencies
        extractor.logger = Mock()
        extractor.vision_client = Mock()
        extractor.export_manager = Mock()
        extractor.prompt_builder = Mock()
        extractor.add_debug_message = Mock()
        
        # Mock config
        extractor.config_manager = Mock()
        extractor.config_manager.config.extraction.primary_provider = "openai"
        
        # Initialize lists
        extractor.screenshot_queue = []
        extractor.session_items_found = []
        extractor.session_crafts_found = []
        extractor.total_screenshots_analyzed = 0
        extractor.total_cost = 0.0
        extractor.analysis_log_entries = []
        
        return extractor
    
    @pytest.fixture
    def sample_image_data(self):
        """Create sample image data for testing."""
        import numpy as np
        image_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        image_data = ImageData(image_array=image_array)
        image_data.timestamp = datetime.now()
        return image_data
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_queue_empty_queue(self, extractor):
        """Test analyze_queue with empty screenshot queue."""
        result = await extractor.analyze_queue()
        assert result is False
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_queue_success_with_valid_data(self, extractor, sample_image_data):
        """Test analyze_queue with successful AI response and valid data."""
        # Set up screenshot queue
        extractor.screenshot_queue = [sample_image_data]
        
        # Mock prompt builder
        extractor.prompt_builder.get_queue_analysis_prompt.return_value = "test prompt"
        
        # Mock successful AI response with valid data
        mock_ai_response = Mock()
        mock_ai_response.success = True
        mock_ai_response.data = {
            'items_found': [{'name': 'Test Item', 'confidence': 0.9}],
            'crafts_found': [{'name': 'Test Craft', 'confidence': 0.8}],
            'screenshots_processed': 1,
            'total_confidence': 85.0
        }
        mock_ai_response.cost_estimate = 0.05
        mock_ai_response.error_message = None
        
        extractor.vision_client.analyze_images = AsyncMock(return_value=mock_ai_response)
        
        # Mock export manager
        extractor.export_manager.process_extraction_results.return_value = {
            'new_items_added': 1,
            'new_crafts_added': 1,
            'items_found_total': 1,
            'crafts_found_total': 1,
            'items_found_new': 1,
            'crafts_found_new': 1,
            'items_found_duplicates': 0,
            'crafts_found_duplicates': 0
        }
        
        # Mock _log_analysis_to_disk method
        extractor._log_analysis_to_disk = Mock()
        
        # Run analyze_queue
        result = await extractor.analyze_queue()
        
        # Verify results
        assert result is True
        assert extractor.last_analysis == mock_ai_response.data
        extractor.add_debug_message.assert_called()
        extractor.vision_client.analyze_images.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_queue_ai_failure(self, extractor, sample_image_data):
        """Test analyze_queue when AI analysis fails."""
        # Set up screenshot queue
        extractor.screenshot_queue = [sample_image_data]
        
        # Mock prompt builder
        extractor.prompt_builder.get_queue_analysis_prompt.return_value = "test prompt"
        
        # Mock failed AI response
        mock_ai_response = Mock()
        mock_ai_response.success = False
        mock_ai_response.error_message = "AI analysis failed"
        
        extractor.vision_client.analyze_images = AsyncMock(return_value=mock_ai_response)
        
        # Run analyze_queue
        result = await extractor.analyze_queue()
        
        # Verify results
        assert result is False
        extractor.add_debug_message.assert_called()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_queue_with_invalid_data_string(self, extractor, sample_image_data):
        """Test analyze_queue when AI returns string instead of dict (the main bug)."""
        # Set up screenshot queue
        extractor.screenshot_queue = [sample_image_data]
        
        # Mock prompt builder
        extractor.prompt_builder.get_queue_analysis_prompt.return_value = "test prompt"
        
        # Mock AI response that returns a string instead of structured data
        mock_ai_response = Mock()
        mock_ai_response.success = True
        mock_ai_response.data = "This is a string response instead of a dictionary"  # The bug scenario
        mock_ai_response.cost_estimate = 0.05
        mock_ai_response.error_message = None
        
        extractor.vision_client.analyze_images = AsyncMock(return_value=mock_ai_response)
        
        # Run analyze_queue
        result = await extractor.analyze_queue()
        
        # Verify that analysis is considered failed due to invalid data
        assert result is False
        
        # Verify error message was logged
        error_calls = [call for call in extractor.add_debug_message.call_args_list 
                      if "Invalid analysis data format" in str(call)]
        assert len(error_calls) > 0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_queue_with_raw_text_data(self, extractor, sample_image_data):
        """Test analyze_queue when AI returns raw_text fallback format."""
        # Set up screenshot queue
        extractor.screenshot_queue = [sample_image_data]
        
        # Mock prompt builder
        extractor.prompt_builder.get_queue_analysis_prompt.return_value = "test prompt"
        
        # Mock AI response that returns raw_text format (JSON parsing failed)
        mock_ai_response = Mock()
        mock_ai_response.success = True
        mock_ai_response.data = {"raw_text": "AI could not parse this into structured data"}
        mock_ai_response.cost_estimate = 0.05
        mock_ai_response.error_message = None
        
        extractor.vision_client.analyze_images = AsyncMock(return_value=mock_ai_response)
        
        # Run analyze_queue
        result = await extractor.analyze_queue()
        
        # Verify that analysis is considered failed due to raw_text only response
        assert result is False
        
        # Verify error message was logged
        error_calls = [call for call in extractor.add_debug_message.call_args_list 
                      if "Analysis returned raw text instead of structured data" in str(call)]
        assert len(error_calls) > 0
    
    @pytest.mark.unit
    def test_show_analysis_results_with_string_data(self, extractor):
        """Test _show_analysis_results with string data (should fail)."""
        extractor.screenshot_queue = []
        mock_result = Mock()
        mock_result.cost_estimate = 0.05
        
        # Call with string data (the original bug)
        result = extractor._show_analysis_results("invalid string data", mock_result)
        
        # Should return False indicating failure
        assert result is False
        
        # Verify error message was logged
        extractor.add_debug_message.assert_called_with("❌ Invalid analysis data format: str")
        extractor.logger.error.assert_called()
    
    @pytest.mark.unit
    def test_show_analysis_results_with_raw_text_only(self, extractor):
        """Test _show_analysis_results with raw_text only data (should fail)."""
        extractor.screenshot_queue = []
        mock_result = Mock()
        mock_result.cost_estimate = 0.05
        
        # Call with raw_text only data
        raw_text_data = {"raw_text": "This is just raw text, not structured data"}
        result = extractor._show_analysis_results(raw_text_data, mock_result)
        
        # Should return False indicating failure
        assert result is False
        
        # Verify error message was logged
        error_calls = [call for call in extractor.add_debug_message.call_args_list 
                      if "Analysis returned raw text instead of structured data" in str(call)]
        assert len(error_calls) > 0
    
    @pytest.mark.unit
    def test_show_analysis_results_with_valid_data(self, extractor, sample_image_data):
        """Test _show_analysis_results with valid structured data."""
        # Set up mock data
        extractor.screenshot_queue = [sample_image_data]
        extractor.session_items_found = []
        extractor.session_crafts_found = []
        extractor.total_screenshots_analyzed = 0
        extractor.total_cost = 0.0
        extractor.analysis_log_entries = []
        
        mock_result = Mock()
        mock_result.cost_estimate = 0.05
        
        # Mock export manager
        extractor.export_manager.process_extraction_results.return_value = {
            'new_items_added': 1,
            'new_crafts_added': 1,
            'items_found_total': 1,
            'crafts_found_total': 1,
            'items_found_new': 1,
            'crafts_found_new': 1,
            'items_found_duplicates': 0,
            'crafts_found_duplicates': 0,
            'items_rejected': 0,
            'crafts_rejected': 0
        }
        
        # Mock _log_analysis_to_disk method
        extractor._log_analysis_to_disk = Mock()
        
        # Valid structured data
        valid_data = {
            'items_found': [{'name': 'Test Item', 'confidence': 0.9}],
            'crafts_found': [{'name': 'Test Craft', 'confidence': 0.8}],
            'screenshots_processed': 1,
            'total_confidence': 85.0
        }
        
        # Call with valid data
        result = extractor._show_analysis_results(valid_data, mock_result)
        
        # Should return True indicating success
        assert result is True
        
        # Verify processing occurred
        extractor.export_manager.process_extraction_results.assert_called_once()
        extractor._log_analysis_to_disk.assert_called_once()
        
        # Verify session tracking was updated
        assert len(extractor.session_items_found) == 1
        assert len(extractor.session_crafts_found) == 1
        assert extractor.total_screenshots_analyzed == 1
        assert extractor.total_cost == 0.05
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_queue_exception_handling(self, extractor, sample_image_data):
        """Test analyze_queue exception handling."""
        # Set up screenshot queue
        extractor.screenshot_queue = [sample_image_data]
        
        # Mock prompt builder
        extractor.prompt_builder.get_queue_analysis_prompt.return_value = "test prompt"
        
        # Mock AI client to raise an exception
        extractor.vision_client.analyze_images = AsyncMock(side_effect=Exception("Test exception"))
        
        # Run analyze_queue
        result = await extractor.analyze_queue()
        
        # Verify that exception was caught and False returned
        assert result is False
        
        # Verify error message was logged
        error_calls = [call for call in extractor.add_debug_message.call_args_list 
                      if "Analysis crashed" in str(call)]
        assert len(error_calls) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
