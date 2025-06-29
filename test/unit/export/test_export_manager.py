"""Unit tests for ExportManager functionality."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import sys

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from bitcrafty_extractor.export.export_manager import ExportManager


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    return Mock()


@pytest.fixture
def temp_exports_dir():
    """Create a temporary directory for exports."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_config_manager():
    """Create a mock config manager."""
    config_manager = Mock()
    config_manager.config.extraction.min_confidence = 0.7
    return config_manager


@pytest.fixture
def sample_item():
    """Sample item data for testing."""
    return {
        'name': 'Rough Spool of Thread',
        'description': 'A basic spool of thread used in crafting',
        'tier': 1,
        'rarity': 'common',
        'uses': ['crafting'],
        'confidence': 0.85
    }


@pytest.fixture
def sample_craft():
    """Sample craft data for testing."""
    return {
        'name': 'Weave Rough Cloth Strip',
        'materials': [
            {'name': 'Rough Spool of Thread', 'quantity': 2}
        ],
        'outputs': [
            {'name': 'Rough Cloth Strip', 'quantity': 1}
        ],
        'confidence': 0.90
    }


@pytest.mark.unit
class TestExportManagerInitialization:
    """Test ExportManager initialization."""
    
    def test_init_with_default_exports_dir(self, mock_config_manager):
        """Test initialization with default exports directory."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch('pathlib.Path.mkdir') as mock_mkdir:
                with patch.object(ExportManager, '_load_existing_items', return_value={}):
                    with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                        export_manager = ExportManager(config_manager=mock_config_manager)
                        
                        assert export_manager.exports_dir == Path("exports")
                        assert export_manager.min_confidence == 0.7
                        mock_mkdir.assert_called_once_with(exist_ok=True)
    
    def test_init_with_custom_exports_dir(self, temp_exports_dir, mock_config_manager):
        """Test initialization with custom exports directory."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    assert export_manager.exports_dir == temp_exports_dir
                    assert export_manager.items_file == temp_exports_dir / "items.json"
                    assert export_manager.crafts_file == temp_exports_dir / "crafts.json"
    
    def test_init_without_config_manager(self):
        """Test initialization without config manager uses defaults."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch('pathlib.Path.mkdir'):
                with patch.object(ExportManager, '_load_existing_items', return_value={}):
                    with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                        export_manager = ExportManager()
                        
                        assert export_manager.min_confidence == 0.7  # Default value


@pytest.mark.unit
class TestExportManagerFileLoading:
    """Test ExportManager file loading functionality."""
    
    def test_load_existing_items_file_not_exists(self, temp_exports_dir):
        """Test loading items when file doesn't exist."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                export_manager = ExportManager(temp_exports_dir)
                items = export_manager._load_existing_items()
                
                assert items == {}
                mock_logger.info.assert_called()
    
    def test_load_existing_items_valid_file(self, temp_exports_dir):
        """Test loading items from valid JSON file."""
        items_data = {
            'items': [
                {'name': 'Item 1', 'description': 'Description 1'},
                {'name': 'Item 2', 'description': 'Description 2'}
            ]
        }
        
        # Create items file
        items_file = temp_exports_dir / "items.json"
        with open(items_file, 'w') as f:
            json.dump(items_data, f)
        
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                export_manager = ExportManager(temp_exports_dir)
                items = export_manager._load_existing_items()
                
                assert len(items) == 2
                # Items should be keyed by hash
                assert all(isinstance(key, str) for key in items.keys())
    
    def test_load_existing_items_invalid_json(self, temp_exports_dir):
        """Test loading items from invalid JSON file."""
        # Create invalid JSON file
        items_file = temp_exports_dir / "items.json"
        with open(items_file, 'w') as f:
            f.write("invalid json content")
        
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                export_manager = ExportManager(temp_exports_dir)
                items = export_manager._load_existing_items()
                
                assert items == {}
                mock_logger.error.assert_called()
    
    def test_load_existing_crafts_valid_file(self, temp_exports_dir):
        """Test loading crafts from valid JSON file."""
        crafts_data = {
            'crafts': [
                {'name': 'Craft 1', 'materials': [], 'outputs': []},
                {'name': 'Craft 2', 'materials': [], 'outputs': []}
            ]
        }
        
        # Create crafts file
        crafts_file = temp_exports_dir / "crafts.json"
        with open(crafts_file, 'w') as f:
            json.dump(crafts_data, f)
        
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                export_manager = ExportManager(temp_exports_dir)
                crafts = export_manager._load_existing_crafts()
                
                assert len(crafts) == 2
                # Crafts should be keyed by hash
                assert all(isinstance(key, str) for key in crafts.keys())


@pytest.mark.unit
class TestExportManagerHashing:
    """Test ExportManager hashing functionality."""
    
    def test_generate_item_hash_consistent(self, temp_exports_dir):
        """Test that item hash generation is consistent."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_get_logger.return_value = Mock()
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir)
                    
                    item = {'name': 'Test Item', 'description': 'Test Description'}
                    hash1 = export_manager._generate_item_hash(item)
                    hash2 = export_manager._generate_item_hash(item)
                    
                    assert hash1 == hash2
                    assert len(hash1) == 12  # Should be 12 character hash
    
    def test_generate_item_hash_different_items(self, temp_exports_dir):
        """Test that different items generate different hashes."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_get_logger.return_value = Mock()
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir)
                    
                    item1 = {'name': 'Item 1', 'description': 'Description 1'}
                    item2 = {'name': 'Item 2', 'description': 'Description 2'}
                    
                    hash1 = export_manager._generate_item_hash(item1)
                    hash2 = export_manager._generate_item_hash(item2)
                    
                    assert hash1 != hash2
    
    def test_generate_item_hash_case_insensitive(self, temp_exports_dir):
        """Test that item hash is case insensitive."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_get_logger.return_value = Mock()
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir)
                    
                    item1 = {'name': 'Test Item', 'description': 'Test Description'}
                    item2 = {'name': 'TEST ITEM', 'description': 'TEST DESCRIPTION'}
                    
                    hash1 = export_manager._generate_item_hash(item1)
                    hash2 = export_manager._generate_item_hash(item2)
                    
                    assert hash1 == hash2
    
    def test_generate_craft_hash_basic(self, temp_exports_dir):
        """Test basic craft hash generation."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_get_logger.return_value = Mock()
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir)
                    
                    craft = {
                        'name': 'Test Craft',
                        'materials': [{'name': 'Material 1', 'quantity': 1}],
                        'outputs': [{'name': 'Output 1', 'quantity': 1}]
                    }
                    
                    craft_hash = export_manager._generate_craft_hash(craft)
                    
                    assert isinstance(craft_hash, str)
                    assert len(craft_hash) == 12


@pytest.mark.unit
class TestExportManagerValidation:
    """Test ExportManager validation functionality."""
    
    def test_validate_item_high_confidence(self, temp_exports_dir, mock_config_manager):
        """Test item validation with high confidence."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_get_logger.return_value = Mock()
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    item = {'name': 'Test Item', 'confidence': 0.85}
                    validation = export_manager._validate_item(item)
                    
                    assert validation['is_valid'] is True
                    assert len(validation['reasons']) == 0
    
    def test_validate_item_low_confidence(self, temp_exports_dir, mock_config_manager):
        """Test item validation with low confidence."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_get_logger.return_value = Mock()
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    item = {'name': 'Test Item', 'confidence': 0.5}
                    validation = export_manager._validate_item(item)
                    
                    assert validation['is_valid'] is False
                    assert any('below threshold' in reason for reason in validation['reasons'])
    
    def test_validate_item_missing_name(self, temp_exports_dir, mock_config_manager):
        """Test item validation with missing name."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_get_logger.return_value = Mock()
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    item = {'confidence': 0.8}  # Missing name
                    validation = export_manager._validate_item(item)
                    
                    assert validation['is_valid'] is False
                    assert any('Missing or empty name' in reason for reason in validation['reasons'])
    
    def test_validate_craft_valid(self, temp_exports_dir, mock_config_manager):
        """Test craft validation with valid data."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_get_logger.return_value = Mock()
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    craft = {
                        'name': 'Test Craft',
                        'confidence': 0.8,
                        'requirements': {'profession': 'farming'},
                        'materials': [{'item': 'Material', 'qty': 1}],
                        'outputs': [{'item': 'Output', 'qty': 1}]
                    }
                    validation = export_manager._validate_craft(craft)
                    
                    assert validation['is_valid'] is True
                    assert len(validation['reasons']) == 0
    
    def test_validate_craft_empty_requirements(self, temp_exports_dir, mock_config_manager):
        """Test craft validation with empty requirements."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_get_logger.return_value = Mock()
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    craft = {
                        'name': 'Test Craft',
                        'confidence': 0.8,
                        'requirements': {},  # Empty requirements
                        'materials': [{'item': 'Material', 'qty': 1}],
                        'outputs': [{'item': 'Output', 'qty': 1}]
                    }
                    validation = export_manager._validate_craft(craft)
                    
                    assert validation['is_valid'] is False
                    assert any('Empty or missing requirements' in reason for reason in validation['reasons'])


@pytest.mark.unit
class TestExportManagerProcessing:
    """Test ExportManager processing functionality."""
    
    def test_process_extraction_results_with_items(self, temp_exports_dir, mock_config_manager, sample_item):
        """Test processing extraction results with valid items."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    # Mock _save_data to avoid file operations
                    with patch.object(export_manager, '_save_data'):
                        data = {'items_found': [sample_item], 'crafts_found': []}
                        result = export_manager.process_extraction_results(data)
                        
                        assert result['items_processed'] == 1
                        assert result['new_items_added'] == 1
                        assert result['items_rejected'] == 0
                        assert len(export_manager.existing_items) == 1
    
    def test_process_extraction_results_with_crafts(self, temp_exports_dir, mock_config_manager, sample_craft):
        """Test processing extraction results with valid crafts."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    # Add requirements to sample craft
                    enhanced_craft = {
                        **sample_craft,
                        'requirements': {'profession': 'farming'}
                    }
                    
                    # Mock _save_data to avoid file operations
                    with patch.object(export_manager, '_save_data'):
                        data = {'items_found': [], 'crafts_found': [enhanced_craft]}
                        result = export_manager.process_extraction_results(data)
                        
                        assert result['crafts_processed'] == 1
                        assert result['new_crafts_added'] == 1
                        assert result['crafts_rejected'] == 0
                        assert len(export_manager.existing_crafts) == 1
    
    def test_process_extraction_results_low_confidence_items(self, temp_exports_dir, mock_config_manager):
        """Test processing extraction results with low confidence items."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    low_confidence_item = {
                        'name': 'Low Confidence Item',
                        'confidence': 0.5  # Below 0.7 threshold
                    }
                    
                    # Mock _save_data to avoid file operations since no new items
                    with patch.object(export_manager, '_save_data'):
                        data = {'items_found': [low_confidence_item], 'crafts_found': []}
                        result = export_manager.process_extraction_results(data)
                        
                        assert result['items_processed'] == 1
                        assert result['new_items_added'] == 0
                        assert result['items_rejected'] == 1
                        assert len(export_manager.existing_items) == 0
    
    def test_process_extraction_results_duplicate_items(self, temp_exports_dir, mock_config_manager, sample_item):
        """Test processing extraction results with duplicate items."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            # Pre-populate with existing item
            item_hash = ExportManager._generate_item_hash(None, sample_item)
            existing_items = {item_hash: sample_item}
            
            with patch.object(ExportManager, '_load_existing_items', return_value=existing_items):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    # Mock _save_data to avoid file operations since no new items
                    with patch.object(export_manager, '_save_data'):
                        data = {'items_found': [sample_item], 'crafts_found': []}
                        result = export_manager.process_extraction_results(data)
                        
                        assert result['items_processed'] == 1
                        assert result['new_items_added'] == 0
                        assert len(export_manager.existing_items) == 1


@pytest.mark.unit
class TestExportManagerSaveData:
    """Test ExportManager save functionality."""
    
    def test_save_data_success(self, temp_exports_dir, mock_config_manager):
        """Test successfully saving data to files."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    # Add some test data
                    export_manager.existing_items['test_hash'] = {'name': 'Test Item', 'confidence': 0.8}
                    export_manager.existing_crafts['test_hash'] = {'name': 'Test Craft', 'confidence': 0.8}
                    
                    # Save data
                    export_manager._save_data()
                    
                    # Check files exist
                    assert (temp_exports_dir / "items.json").exists()
                    assert (temp_exports_dir / "crafts.json").exists()
                    
                    # Verify file content
                    with open(temp_exports_dir / "items.json", 'r') as f:
                        items_data = json.load(f)
                    
                    assert 'items' in items_data
                    assert 'metadata' in items_data
                    assert len(items_data['items']) == 1
                    assert items_data['items'][0]['name'] == 'Test Item'
    
    def test_save_data_file_error(self, temp_exports_dir, mock_config_manager):
        """Test handling file write error when saving data."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    # Mock file write to raise exception
                    with patch('builtins.open', side_effect=PermissionError("No permission")):
                        export_manager._save_data()
                        
                        # Should log error
                        mock_logger.error.assert_called()


@pytest.mark.unit
class TestExportManagerStatistics:
    """Test ExportManager statistics functionality."""
    
    def test_get_stats(self, temp_exports_dir, mock_config_manager):
        """Test getting export statistics."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_get_logger.return_value = Mock()
            
            existing_items = {
                'hash1': {'name': 'Item 1'},
                'hash2': {'name': 'Item 2'}
            }
            existing_crafts = {
                'hash1': {'name': 'Craft 1'}
            }
            
            with patch.object(ExportManager, '_load_existing_items', return_value=existing_items):
                with patch.object(ExportManager, '_load_existing_crafts', return_value=existing_crafts):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    stats = export_manager.get_stats()
                    
                    assert stats['total_items'] == 2
                    assert stats['total_crafts'] == 1
                    assert 'exports_dir' in stats
                    assert 'items_file' in stats
                    assert 'crafts_file' in stats


@pytest.mark.unit 
class TestExportManagerBitCraftyExport:
    """Test ExportManager BitCrafty export functionality."""
    
    def test_export_for_bitcrafty_success(self, temp_exports_dir, mock_config_manager):
        """Test successful BitCrafty format export."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            existing_items = {
                'item_hash': {
                    'id': 'item_hash',
                    'name': 'Test Item',
                    'description': 'Test Description',
                    'tier': 1,
                    'rarity': 'common'
                }
            }
            existing_crafts = {
                'craft_hash': {
                    'id': 'craft_hash',
                    'name': 'Test Craft',
                    'materials': [{'item': 'Material', 'qty': 1}],
                    'outputs': [{'item': 'Output', 'qty': 1}],
                    'requirements': {'profession': 'farming'}
                }
            }
            
            with patch.object(ExportManager, '_load_existing_items', return_value=existing_items):
                with patch.object(ExportManager, '_load_existing_crafts', return_value=existing_crafts):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    result = export_manager.export_for_bitcrafty()
                    
                    assert 'items_file' in result
                    assert 'crafts_file' in result
                    
                    # Check files exist
                    bitcrafty_items_file = temp_exports_dir / "bitcrafty_items.json"
                    bitcrafty_crafts_file = temp_exports_dir / "bitcrafty_crafts.json"
                    
                    assert bitcrafty_items_file.exists()
                    assert bitcrafty_crafts_file.exists()
                    
                    # Verify format transformation
                    with open(bitcrafty_items_file, 'r') as f:
                        items = json.load(f)
                    
                    assert len(items) == 1
                    assert items[0]['id'].startswith('item:extracted:')
                    assert items[0]['name'] == 'Test Item'
    
    def test_export_for_bitcrafty_file_error(self, temp_exports_dir, mock_config_manager):
        """Test handling file write error during BitCrafty export."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    # Mock file write to raise exception
                    with patch('builtins.open', side_effect=PermissionError("No permission")):
                        result = export_manager.export_for_bitcrafty()
                        
                        assert result == {}
                        mock_logger.error.assert_called()


@pytest.mark.unit
class TestExportManagerErrorHandling:
    """Test ExportManager error handling scenarios."""
    
    def test_process_extraction_results_with_invalid_data(self, temp_exports_dir, mock_config_manager):
        """Test processing extraction results with invalid data structure."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    # Try to process invalid data - use items that will fail validation
                    invalid_data = {
                        'items_found': [
                            {},    # Empty item (no name)
                            {'confidence': 0.8},  # Missing name
                            {'name': 'Low Conf Item', 'confidence': 0.3},  # Low confidence
                        ],
                        'crafts_found': []
                    }
                    
                    # Mock _save_data since no valid items will be added
                    with patch.object(export_manager, '_save_data'):
                        result = export_manager.process_extraction_results(invalid_data)
                        
                        # Should handle gracefully
                        assert isinstance(result, dict)
                        assert 'items_processed' in result
                        assert 'items_rejected' in result
                        assert result['items_processed'] == 3
                        assert result['items_rejected'] == 3  # All should be rejected
    
    def test_initialization_with_corrupted_files(self, temp_exports_dir):
        """Test initialization when existing files are corrupted."""
        # Create corrupted files
        (temp_exports_dir / "items.json").write_text("corrupted json")
        (temp_exports_dir / "crafts.json").write_text("corrupted json")
        
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            # Should initialize successfully with empty data
            export_manager = ExportManager(temp_exports_dir)
            
            assert export_manager.existing_items == {}
            assert export_manager.existing_crafts == {}
            
            # Should have logged errors
            assert mock_logger.error.call_count >= 2
    
    def test_process_extraction_results_missing_data_keys(self, temp_exports_dir, mock_config_manager):
        """Test processing extraction results with missing data keys."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    # Data missing expected keys
                    incomplete_data = {}  # No items_found or crafts_found
                    
                    # Mock _save_data since no items will be processed
                    with patch.object(export_manager, '_save_data'):
                        result = export_manager.process_extraction_results(incomplete_data)
                        
                        # Should handle gracefully with defaults
                        assert result['items_processed'] == 0
                        assert result['crafts_processed'] == 0
                        assert result['new_items_added'] == 0
                        assert result['new_crafts_added'] == 0
