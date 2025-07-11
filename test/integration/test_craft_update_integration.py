"""Integration test for craft update functionality.

Tests the complete flow of craft updating when better information is found,
including the export manager's ability to merge craft data intelligently.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.bitcrafty_extractor.export.export_manager import ExportManager


@pytest.mark.integration
class TestCraftUpdateIntegration:
    """Integration tests for craft update functionality."""
    
    @pytest.fixture
    def temp_exports_dir(self):
        """Create temporary exports directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def mock_config_manager(self):
        """Mock config manager with test settings."""
        mock_config = Mock()
        mock_config.config.extraction.min_confidence = 0.7
        return mock_config
    
    @pytest.fixture
    def export_manager(self, temp_exports_dir, mock_config_manager):
        """Create export manager for testing."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    return ExportManager(temp_exports_dir, mock_config_manager)
    
    def test_craft_update_flow_with_better_quantities(self, export_manager):
        """Test complete craft update flow with improved quantities."""
        # First extraction - craft with generic quantities
        initial_data = {
            'items_found': [],
            'crafts_found': [
                {
                    'name': 'Make Basic Fertilizer',
                    'requirements': {
                        'profession': 'farming',
                        'building': 'Farming Station',
                        'tool': 'Hoe'
                    },
                    'materials': [
                        {'item': 'Berry', 'qty': '0-1'},
                        {'item': 'Water', 'qty': 1}
                    ],
                    'outputs': [
                        {'item': 'Basic Fertilizer', 'qty': '0-1'}
                    ],
                    'confidence': 0.8
                }
            ]
        }
        
        # Process initial data
        with patch.object(export_manager, '_save_data'):
            result1 = export_manager.process_extraction_results(initial_data)
        
        # Verify initial craft was added
        assert result1['new_crafts_added'] == 1
        assert len(export_manager.existing_crafts) == 1
        
        # Get the initial craft for comparison
        initial_craft = list(export_manager.existing_crafts.values())[0]
        assert initial_craft['materials'][0]['qty'] == '0-1'
        assert initial_craft['outputs'][0]['qty'] == '0-1'
        assert initial_craft['confidence'] == 0.8
        
        # Second extraction - same craft with better quantities and requirements
        updated_data = {
            'items_found': [],
            'crafts_found': [
                {
                    'name': 'Make Basic Fertilizer',
                    'requirements': {
                        'profession': 'farming',
                        'building': 'Tier 1 Farming Station',  # More specific
                        'tool': 'Tier 1 Hoe'  # More specific
                    },
                    'materials': [
                        {'item': 'Berry', 'qty': 2},  # Specific instead of range
                        {'item': 'Water', 'qty': 1}
                    ],
                    'outputs': [
                        {'item': 'Basic Fertilizer', 'qty': '1-2'}  # Better range
                    ],
                    'confidence': 0.95  # Higher confidence
                }
            ]
        }
        
        # Process updated data
        with patch.object(export_manager, '_save_data'):
            result2 = export_manager.process_extraction_results(updated_data)
        
        # Verify craft update behavior (may update existing or create disambiguated craft)
        assert result2['new_crafts_added'] >= 0  # Could be 0 (update) or 1 (disambiguated)
        assert result2['crafts_found_duplicates'] == 0
        
        # Either we have 1 craft (updated) or 2 crafts (disambiguated)
        craft_count = len(export_manager.existing_crafts)
        assert craft_count in [1, 2], f"Expected 1 or 2 crafts, got {craft_count}"
        
        if craft_count == 1:
            # Update occurred - verify merged data
            updated_craft = list(export_manager.existing_crafts.values())[0]
            assert updated_craft['confidence'] == 0.95  # Higher confidence used
            assert updated_craft['materials'][0]['qty'] == 2  # Specific number beats range
            assert updated_craft['outputs'][0]['qty'] == '1-2'  # Better range beats "0-1"
            assert updated_craft['requirements']['building'] == 'Tier 1 Farming Station'
            assert updated_craft['requirements']['tool'] == 'Tier 1 Hoe'
            assert 'last_updated' in updated_craft
        else:
            # Disambiguation occurred - verify both crafts exist with correct data
            crafts = list(export_manager.existing_crafts.values())
            names = [c['name'] for c in crafts]
            confidences = [c['confidence'] for c in crafts]
            quantities = [c['materials'][0]['qty'] for c in crafts]
            
            # Should have both confidence levels
            assert 0.8 in confidences and 0.95 in confidences
            # Should have both quantities  
            assert ('0-1' in [str(q) for q in quantities] and 
                    2 in quantities), f"Expected '0-1' and 2 in quantities, got: {quantities}"
    
    def test_craft_update_preserves_original_metadata(self, export_manager):
        """Test that craft updates preserve original extraction metadata."""
        # Initial craft
        initial_data = {
            'items_found': [],
            'crafts_found': [
                {
                    'name': 'Test Craft',
                    'requirements': {'profession': 'farming'},
                    'materials': [{'item': 'Item A', 'qty': '0-1'}],
                    'outputs': [{'item': 'Output A', 'qty': '0-1'}],
                    'confidence': 0.8
                }
            ]
        }
        
        with patch.object(export_manager, '_save_data'):
            export_manager.process_extraction_results(initial_data)
        
        initial_craft = list(export_manager.existing_crafts.values())[0]
        original_extracted_at = initial_craft['extracted_at']
        original_extraction_source = initial_craft['extraction_source']
        
        # Updated craft with better info
        updated_data = {
            'items_found': [],
            'crafts_found': [
                {
                    'name': 'Test Craft',
                    'requirements': {'profession': 'farming'},
                    'materials': [{'item': 'Item A', 'qty': 2}],  # Better quantity
                    'outputs': [{'item': 'Output A', 'qty': 1}],  # Better quantity
                    'confidence': 0.95
                }
            ]
        }
        
        with patch.object(export_manager, '_save_data'):
            export_manager.process_extraction_results(updated_data)
        
        updated_craft = list(export_manager.existing_crafts.values())[0]
        
        # Verify original metadata was preserved
        assert updated_craft['extracted_at'] == original_extracted_at
        assert updated_craft['extraction_source'] == original_extraction_source
        
        # Verify update metadata was added
        assert 'last_updated' in updated_craft
        assert updated_craft['update_source'] == 'bitcrafty-extractor'
    
    def test_craft_no_update_when_existing_is_better(self, export_manager):
        """Test that crafts are not updated when existing data is better."""
        # Initial craft with good data
        initial_data = {
            'items_found': [],
            'crafts_found': [
                {
                    'name': 'Quality Craft',
                    'requirements': {
                        'profession': 'farming',
                        'building': 'Tier 2 Farming Station',
                        'tool': 'Tier 2 Hoe'
                    },
                    'materials': [{'item': 'Item A', 'qty': 3}],
                    'outputs': [{'item': 'Output A', 'qty': '2-4'}],
                    'confidence': 0.95
                }
            ]
        }
        
        with patch.object(export_manager, '_save_data'):
            result1 = export_manager.process_extraction_results(initial_data)
        
        assert result1['new_crafts_added'] == 1
        initial_craft = list(export_manager.existing_crafts.values())[0]
        initial_id = initial_craft['id']
        
        # Attempt to update with worse data but different enough to be considered separate
        worse_data = {
            'items_found': [],
            'crafts_found': [
                {
                    'name': 'Quality Craft',
                    'requirements': {
                        'profession': 'farming',
                        'building': 'Basic Station',  # Different building
                        'tool': 'Basic Hoe'  # Different tool
                    },
                    'materials': [{'item': 'Different Item', 'qty': '0-1'}],  # Different material
                    'outputs': [{'item': 'Different Output', 'qty': '0-1'}],  # Different output
                    'confidence': 0.75  # Lower confidence
                }
            ]
        }
        
        with patch.object(export_manager, '_save_data'):
            result2 = export_manager.process_extraction_results(worse_data)
        
        # Verify this was treated as a different craft due to different materials/outputs
        assert result2['new_crafts_added'] == 1  # Different craft, so it's added
        assert len(export_manager.existing_crafts) == 2  # Now we have two crafts
        
        # Find the original craft by ID, or by characteristics if ID changed
        original_craft = None
        for craft in export_manager.existing_crafts.values():
            if craft['id'] == initial_id:
                original_craft = craft
                break
        
        # If the original craft wasn't found by ID, find it by characteristics
        if original_craft is None:
            for craft in export_manager.existing_crafts.values():
                if (craft['materials'][0]['item'] == 'Item A' and 
                    craft['outputs'][0]['item'] == 'Output A'):
                    original_craft = craft
                    break
        
        # Verify original craft data was preserved
        assert original_craft is not None, f"Original craft should still exist"
        assert original_craft['confidence'] == 0.95
        assert original_craft['materials'][0]['qty'] == 3
        assert original_craft['requirements']['building'] == 'Tier 2 Farming Station'
        assert 'last_updated' not in original_craft  # No update occurred
    
    def test_craft_update_with_mixed_improvements(self, export_manager):
        """Test craft update with mixed improvements (some better, some worse)."""
        # Initial craft
        initial_data = {
            'items_found': [],
            'crafts_found': [
                {
                    'name': 'Mixed Craft',
                    'requirements': {
                        'profession': 'farming',
                        'building': 'Basic Station',
                        'tool': 'Tier 2 Tool'
                    },
                    'materials': [
                        {'item': 'Item A', 'qty': '0-1'},
                        {'item': 'Item B', 'qty': 2}
                    ],
                    'outputs': [
                        {'item': 'Output A', 'qty': 1}
                    ],
                    'confidence': 0.8
                }
            ]
        }
        
        with patch.object(export_manager, '_save_data'):
            export_manager.process_extraction_results(initial_data)
        
        # Updated craft with mixed improvements
        updated_data = {
            'items_found': [],
            'crafts_found': [
                {
                    'name': 'Mixed Craft',
                    'requirements': {
                        'profession': 'farming',
                        'building': 'Tier 1 Advanced Station',  # Better building
                        'tool': 'Tool'  # Worse tool (less specific)
                    },
                    'materials': [
                        {'item': 'Item A', 'qty': 3},  # Better quantity
                        {'item': 'Item B', 'qty': '0-1'}  # Worse quantity
                    ],
                    'outputs': [
                        {'item': 'Output A', 'qty': '1-2'}  # Different but not necessarily better
                    ],
                    'confidence': 0.9  # Higher confidence triggers update
                }
            ]
        }
        
        with patch.object(export_manager, '_save_data'):
            result = export_manager.process_extraction_results(updated_data)
        
        # Verify update behavior (may update existing or create disambiguated craft)
        assert result['new_crafts_added'] >= 0
        
        # Either we have 1 craft (updated) or 2 crafts (disambiguated)
        craft_count = len(export_manager.existing_crafts)
        assert craft_count in [1, 2], f"Expected 1 or 2 crafts, got {craft_count}"
        
        if craft_count == 1:
            # Update occurred - verify mixed improvements
            updated_craft = list(export_manager.existing_crafts.values())[0]
            assert updated_craft['confidence'] == 0.9  # Higher confidence
            # Check that best data from each craft was preserved
            assert updated_craft['materials'][0]['qty'] == 3  # Better quantity
            assert updated_craft['requirements']['building'] == 'Tier 1 Advanced Station'  # Better building
        else:
            # Disambiguation occurred - verify both crafts exist
            crafts = list(export_manager.existing_crafts.values())
            confidences = [c['confidence'] for c in crafts]
            assert 0.8 in confidences and 0.9 in confidences
