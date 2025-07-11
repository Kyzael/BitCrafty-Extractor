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
                        'materials': [{'item': 'Material 1', 'qty': 1}],
                        'outputs': [{'item': 'Output 1', 'qty': 1}],
                        'requirements': {'profession': 'farming'}
                    }
                    
                    craft_hash = export_manager._generate_craft_hash(craft)
                    
                    assert isinstance(craft_hash, str)
                    assert len(craft_hash) == 12
    
    def test_generate_craft_hash_with_requirements_different(self, temp_exports_dir):
        """Test that crafts with same name/materials/outputs but different requirements generate different hashes."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_get_logger.return_value = Mock()
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir)
                    
                    # Craft with basic tools requirement
                    craft1 = {
                        'name': 'Make Basic Fertilizer',
                        'materials': [{'item': 'Basic Berry', 'qty': 1}],
                        'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                        'requirements': {'profession': 'farming', 'tool': 'basic_tools'}
                    }
                    
                    # Same craft but with farming station requirement
                    craft2 = {
                        'name': 'Make Basic Fertilizer',
                        'materials': [{'item': 'Basic Berry', 'qty': 1}],
                        'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                        'requirements': {'profession': 'farming', 'building': 'tier1_farming_station'}
                    }
                    
                    hash1 = export_manager._generate_craft_hash(craft1)
                    hash2 = export_manager._generate_craft_hash(craft2)
                    
                    # Should be different because requirements are different
                    assert hash1 != hash2
    
    def test_generate_craft_hash_fertilizer_variants(self, temp_exports_dir):
        """Test that different Basic Fertilizer recipes generate different hashes."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_get_logger.return_value = Mock()
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir)
                    
                    # Different fertilizer recipes should have different hashes
                    fertilizer_fish = {
                        'name': 'Make Basic Fertilizer (Fish)',
                        'materials': [{'item': 'Breezy Fin Darter', 'qty': 2}],
                        'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                        'requirements': {'profession': 'farming', 'tool': 'basic_tools'}
                    }
                    
                    fertilizer_berry = {
                        'name': 'Make Basic Fertilizer (Berry)',
                        'materials': [{'item': 'Basic Berry', 'qty': 2}],
                        'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                        'requirements': {'profession': 'farming', 'tool': 'basic_tools'}
                    }
                    
                    fertilizer_station = {
                        'name': 'Make Basic Fertilizer',
                        'materials': [{'item': 'Basic Berry', 'qty': 1}],
                        'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                        'requirements': {'profession': 'farming', 'building': 'tier1_farming_station'}
                    }
                    
                    hash_fish = export_manager._generate_craft_hash(fertilizer_fish)
                    hash_berry = export_manager._generate_craft_hash(fertilizer_berry)
                    hash_station = export_manager._generate_craft_hash(fertilizer_station)
                    
                    # All should be different
                    assert hash_fish != hash_berry
                    assert hash_fish != hash_station
                    assert hash_berry != hash_station
    
    def test_generate_craft_hash_identical_crafts_same_hash(self, temp_exports_dir):
        """Test that truly identical crafts generate the same hash."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_get_logger.return_value = Mock()
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir)
                    
                    craft1 = {
                        'name': 'Test Craft',
                        'materials': [{'item': 'Material A', 'qty': 2}],
                        'outputs': [{'item': 'Output X', 'qty': 1}],
                        'requirements': {'profession': 'farming', 'level': 1}
                    }
                    
                    # Identical craft
                    craft2 = {
                        'name': 'Test Craft',
                        'materials': [{'item': 'Material A', 'qty': 2}],
                        'outputs': [{'item': 'Output X', 'qty': 1}],
                        'requirements': {'profession': 'farming', 'level': 1}
                    }
                    
                    hash1 = export_manager._generate_craft_hash(craft1)
                    hash2 = export_manager._generate_craft_hash(craft2)
                    
                    # Should be identical
                    assert hash1 == hash2
    
    def test_generate_craft_hash_missing_requirements(self, temp_exports_dir):
        """Test craft hash generation when requirements are missing or empty."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_get_logger.return_value = Mock()
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir)
                    
                    craft_no_reqs = {
                        'name': 'Test Craft',
                        'materials': [{'item': 'Material A', 'qty': 1}],
                        'outputs': [{'item': 'Output X', 'qty': 1}]
                        # No requirements
                    }
                    
                    craft_empty_reqs = {
                        'name': 'Test Craft',
                        'materials': [{'item': 'Material A', 'qty': 1}],
                        'outputs': [{'item': 'Output X', 'qty': 1}],
                        'requirements': {}  # Empty requirements
                    }
                    
                    hash_no_reqs = export_manager._generate_craft_hash(craft_no_reqs)
                    hash_empty_reqs = export_manager._generate_craft_hash(craft_empty_reqs)
                    
                    # Should be the same since both have no meaningful requirements
                    assert hash_no_reqs == hash_empty_reqs


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
    
    def test_validate_craft_circular_recipe_detected(self, temp_exports_dir, mock_config_manager):
        """Test craft validation detects circular recipes (input = output)."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    # Test circular recipe where material and output are the same
                    craft = {
                        'name': 'Make Basic Fertilizer',
                        'confidence': 0.8,
                        'requirements': {'profession': 'farming'},
                        'materials': [{'item': 'Basic Fertilizer', 'qty': 1}],
                        'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}]
                    }
                    validation = export_manager._validate_craft(craft)
                    
                    assert validation['is_valid'] is False
                    assert any('Circular recipe detected' in reason for reason in validation['reasons'])
                    
    def test_validate_craft_valid_non_circular(self, temp_exports_dir, mock_config_manager):
        """Test that valid non-circular recipes pass validation."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_get_logger.return_value = Mock()
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    craft = {
                        'name': 'Make Basic Fertilizer',
                        'confidence': 0.8,
                        'requirements': {'profession': 'farming', 'tool': 'basic_tools'},
                        'materials': [{'item': 'Breezy Fin Darter', 'qty': 2}],  # Input is fish
                        'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}]      # Output is fertilizer
                    }
                    validation = export_manager._validate_craft(craft)
                    
                    assert validation['is_valid'] is True
                    assert len(validation['reasons']) == 0
                    
    def test_validate_craft_real_world_circular_example(self, temp_exports_dir, mock_config_manager):
        """Test the real-world circular recipe example from analysis log."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_get_logger.return_value = Mock()
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    # This is the invalid circular recipe from the analysis log
                    circular_craft = {
                        'name': 'Make Basic Fertilizer',
                        'confidence': 0.85,
                        'requirements': {'profession': 'farming', 'tool': 'basic_tools'},
                        'materials': [{'item': 'Basic Fertilizer', 'qty': 1}],  # Same as output!
                        'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}]
                    }
                    validation = export_manager._validate_craft(circular_craft)
                    
                    assert validation['is_valid'] is False
                    assert any('Circular recipe detected: basic fertilizer is both input and output' in reason for reason in validation['reasons'])
                    assert any('basic fertilizer is both input and output' in reason.lower() for reason in validation['reasons'])
    
    def test_validate_craft_valid_different_materials_outputs(self, temp_exports_dir, mock_config_manager):
        """Test craft validation passes when materials and outputs are different."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    # Test valid recipe with different materials and outputs
                    craft = {
                        'name': 'Make Basic Fertilizer',
                        'confidence': 0.8,
                        'requirements': {'profession': 'farming'},
                        'materials': [{'item': 'Basic Berry', 'qty': 1}],
                        'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}]
                    }
                    validation = export_manager._validate_craft(craft)
                    
                    assert validation['is_valid'] is True
                    assert len(validation['reasons']) == 0


@pytest.mark.unit
class TestExportManagerCraftDuplicateDetection:
    """Test ExportManager craft duplicate detection improvements."""
    
    def test_fertilizer_variants_not_duplicates(self, temp_exports_dir, mock_config_manager):
        """Test that different Basic Fertilizer recipes are not considered duplicates."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    # First add a fish-based fertilizer
                    fertilizer_fish = {
                        'name': 'Make Basic Fertilizer (Fish)',
                        'materials': [{'item': 'Breezy Fin Darter', 'qty': 2}],
                        'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                        'requirements': {'profession': 'farming', 'tool': 'basic_tools'},
                        'confidence': 0.85
                    }
                    
                    # Mock _save_data to avoid file operations
                    with patch.object(export_manager, '_save_data'):
                        data1 = {'items_found': [], 'crafts_found': [fertilizer_fish]}
                        result1 = export_manager.process_extraction_results(data1)
                        
                        assert result1['new_crafts_added'] == 1
                        assert len(export_manager.existing_crafts) == 1
                        
                        # Now add a berry-based fertilizer with similar name
                        fertilizer_berry = {
                            'name': 'Make Basic Fertilizer (Berry)',
                            'materials': [{'item': 'Basic Berry', 'qty': 2}],
                            'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                            'requirements': {'profession': 'farming', 'tool': 'basic_tools'},
                            'confidence': 0.88
                        }
                        
                        data2 = {'items_found': [], 'crafts_found': [fertilizer_berry]}
                        result2 = export_manager.process_extraction_results(data2)
                        
                        # Should be added as a new craft, not considered duplicate
                        assert result2['new_crafts_added'] == 1
                        assert len(export_manager.existing_crafts) == 2
                        assert result2['crafts_found_duplicates'] == 0
    
    def test_same_name_different_requirements_not_duplicates(self, temp_exports_dir, mock_config_manager):
        """Test that crafts with same name but different requirements are not duplicates."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    # Basic fertilizer made with basic tools
                    fertilizer_basic = {
                        'name': 'Make Basic Fertilizer',
                        'materials': [{'item': 'Basic Berry', 'qty': 1}],
                        'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                        'requirements': {'profession': 'farming', 'tool': 'basic_tools'},
                        'confidence': 0.85
                    }
                    
                    # Mock _save_data to avoid file operations
                    with patch.object(export_manager, '_save_data'):
                        data1 = {'items_found': [], 'crafts_found': [fertilizer_basic]}
                        result1 = export_manager.process_extraction_results(data1)
                        
                        assert result1['new_crafts_added'] == 1
                        
                        # Same name and materials but different building requirement
                        fertilizer_station = {
                            'name': 'Make Basic Fertilizer',
                            'materials': [{'item': 'Basic Berry', 'qty': 1}],
                            'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                            'requirements': {'profession': 'farming', 'building': 'tier1_farming_station'},
                            'confidence': 0.87
                        }
                        
                        data2 = {'items_found': [], 'crafts_found': [fertilizer_station]}
                        result2 = export_manager.process_extraction_results(data2)
                        
                        # Should be added as new, not duplicate
                        assert result2['new_crafts_added'] == 1
                        assert len(export_manager.existing_crafts) == 2
                        assert result2['crafts_found_duplicates'] == 0
    
    def test_identical_crafts_are_duplicates(self, temp_exports_dir, mock_config_manager):
        """Test that truly identical crafts are correctly identified as duplicates."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    craft = {
                        'name': 'Make Test Item',
                        'materials': [{'item': 'Material A', 'qty': 2}],
                        'outputs': [{'item': 'Test Item', 'qty': 1}],
                        'requirements': {'profession': 'farming', 'level': 1},
                        'confidence': 0.85
                    }
                    
                    # Mock _save_data to avoid file operations
                    with patch.object(export_manager, '_save_data'):
                        data1 = {'items_found': [], 'crafts_found': [craft]}
                        result1 = export_manager.process_extraction_results(data1)
                        
                        assert result1['new_crafts_added'] == 1
                        
                        # Add the exact same craft again
                        identical_craft = craft.copy()
                        data2 = {'items_found': [], 'crafts_found': [identical_craft]}
                        result2 = export_manager.process_extraction_results(data2)
                        
                        # Should be identified as duplicate
                        assert result2['new_crafts_added'] == 0
                        assert result2['crafts_found_duplicates'] == 1
                        assert len(export_manager.existing_crafts) == 1
    
    def test_different_materials_not_duplicates(self, temp_exports_dir, mock_config_manager):
        """Test that crafts with same name but different materials are not duplicates."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    craft1 = {
                        'name': 'Make Test Tool',
                        'materials': [{'item': 'Wood', 'qty': 2}, {'item': 'Stone', 'qty': 1}],
                        'outputs': [{'item': 'Test Tool', 'qty': 1}],
                        'requirements': {'profession': 'tool_making'},
                        'confidence': 0.85
                    }
                    
                    # Mock _save_data to avoid file operations
                    with patch.object(export_manager, '_save_data'):
                        data1 = {'items_found': [], 'crafts_found': [craft1]}
                        result1 = export_manager.process_extraction_results(data1)
                        
                        assert result1['new_crafts_added'] == 1
                        
                        # Same name and output but different materials
                        craft2 = {
                            'name': 'Make Test Tool',
                            'materials': [{'item': 'Metal', 'qty': 1}],  # Different materials
                            'outputs': [{'item': 'Test Tool', 'qty': 1}],
                            'requirements': {'profession': 'tool_making'},
                            'confidence': 0.87
                        }
                        
                        data2 = {'items_found': [], 'crafts_found': [craft2]}
                        result2 = export_manager.process_extraction_results(data2)
                        
                        # Should be different crafts
                        assert result2['new_crafts_added'] == 1
                        assert result2['crafts_found_duplicates'] == 0
                        assert len(export_manager.existing_crafts) == 2
    
    def test_different_quantities_update_behavior(self, temp_exports_dir, mock_config_manager):
        """Test that crafts with same materials but different quantities trigger updates when appropriate."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    craft1 = {
                        'name': 'Make Test Food',
                        'materials': [{'item': 'Ingredient A', 'qty': 1}],
                        'outputs': [{'item': 'Test Food', 'qty': 1}],
                        'requirements': {'profession': 'cooking'},
                        'confidence': 0.85
                    }
                    
                    # Mock _save_data to avoid file operations
                    with patch.object(export_manager, '_save_data'):
                        data1 = {'items_found': [], 'crafts_found': [craft1]}
                        result1 = export_manager.process_extraction_results(data1)
                        
                        assert result1['new_crafts_added'] == 1
                        
                        # Same craft but with higher confidence and different quantity
                        craft2 = {
                            'name': 'Make Test Food',
                            'materials': [{'item': 'Ingredient A', 'qty': 2}],  # Different quantity
                            'outputs': [{'item': 'Test Food', 'qty': 1}],
                            'requirements': {'profession': 'cooking'},
                            'confidence': 0.87  # Higher confidence
                        }
                        
                        data2 = {'items_found': [], 'crafts_found': [craft2]}
                        result2 = export_manager.process_extraction_results(data2)
                        
                        # With our new update logic, this should not create a new craft
                        # Updates might be counted differently or not increment standard counters
                        assert result2['new_crafts_added'] == 0
                        assert len(export_manager.existing_crafts) == 1
                        
                        # The existing craft should still exist (may have disambiguated name)
                        existing_craft = list(export_manager.existing_crafts.values())[0]
                        assert 'Make Test Food' in existing_craft['name']  # Name might be disambiguated
    
    def test_bitcrafty_fertilizer_scenario(self, temp_exports_dir, mock_config_manager):
        """Test the exact BitCrafty fertilizer scenario that prompted this improvement."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    # Simulate extracting all BitCrafty fertilizer recipes
                    fertilizer_recipes = [
                        {
                            'name': 'Make Basic Fertilizer (Fish)',
                            'materials': [{'item': 'Breezy Fin Darter', 'qty': 2}],
                            'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                            'requirements': {'profession': 'farming', 'tool': 'basic_tools'},
                            'confidence': 0.85
                        },
                        {
                            'name': 'Make Basic Fertilizer (Berry)',
                            'materials': [{'item': 'Basic Berry', 'qty': 2}],
                            'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                            'requirements': {'profession': 'farming', 'tool': 'basic_tools'},
                            'confidence': 0.88
                        },
                        {
                            'name': 'Make Basic Fertilizer (Flower)',
                            'materials': [{'item': 'Basic Flower', 'qty': 5}],
                            'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                            'requirements': {'profession': 'farming', 'tool': 'basic_tools'},
                            'confidence': 0.87
                        },
                        {
                            'name': 'Make Basic Fertilizer (Food Waste)',
                            'materials': [{'item': 'Food Waste', 'qty': 2}],
                            'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                            'requirements': {'profession': 'farming', 'tool': 'basic_tools'},
                            'confidence': 0.82
                        },
                        {
                            'name': 'Make Basic Fertilizer',
                            'materials': [{'item': 'Basic Berry', 'qty': 1}],
                            'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                            'requirements': {'profession': 'farming', 'building': 'tier1_farming_station'},
                            'confidence': 0.90
                        }
                    ]
                    
                    # Mock _save_data to avoid file operations
                    with patch.object(export_manager, '_save_data'):
                        # Process all fertilizer recipes in a single extraction
                        data = {'items_found': [], 'crafts_found': fertilizer_recipes}
                        result = export_manager.process_extraction_results(data)
                        
                        # All 5 recipes should be added as unique crafts
                        assert result['new_crafts_added'] == 5
                        assert result['crafts_found_duplicates'] == 0
                        assert len(export_manager.existing_crafts) == 5
                        
                        # Verify all recipes have different hashes
                        craft_hashes = set()
                        for craft in export_manager.existing_crafts.values():
                            craft_hashes.add(craft['id'])
                        assert len(craft_hashes) == 5  # All unique hashes
                        
                        # Verify names are handled correctly by disambiguation
                        craft_names = [craft['name'] for craft in export_manager.existing_crafts.values()]
                        
                        # The generic "Make Basic Fertilizer" should be disambiguated to include material
                        expected_names = {
                            'Make Basic Fertilizer (Fish)',
                            'Make Basic Fertilizer (Berry)', 
                            'Make Basic Fertilizer (Flower)',
                            'Make Basic Fertilizer (Food Waste)',
                            'Make Basic Fertilizer (Basic Berry)'  # Generic name disambiguated
                        }
                        
                        assert set(craft_names) == expected_names


@pytest.mark.unit
class TestExportManagerNameDisambiguation:
    """Test ExportManager craft name disambiguation functionality."""
    
    def test_disambiguate_generic_craft_name_with_existing(self, temp_exports_dir, mock_config_manager):
        """Test that generic craft names get disambiguated when they conflict with existing crafts."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            # Start with existing fertilizer craft using fish
            existing_fertilizer = {
                'name': 'Make Basic Fertilizer',
                'materials': [{'item': 'Breezy Fin Darter', 'qty': 2}],
                'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                'requirements': {'profession': 'farming', 'tool': 'basic_tools'},
                'confidence': 0.85,
                'id': 'existing_hash'
            }
            
            existing_crafts = {'existing_hash': existing_fertilizer}
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value=existing_crafts):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    # Add new generic fertilizer craft using berries
                    new_fertilizer = {
                        'name': 'Make Basic Fertilizer',  # Generic name from AI
                        'materials': [{'item': 'Basic Berry', 'qty': 2}],
                        'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                        'requirements': {'profession': 'farming', 'tool': 'basic_tools'},
                        'confidence': 0.88
                    }
                    
                    # Mock _save_data to avoid file operations
                    with patch.object(export_manager, '_save_data'):
                        data = {'items_found': [], 'crafts_found': [new_fertilizer]}
                        result = export_manager.process_extraction_results(data)
                        
                        # Should add new craft and disambiguate both names
                        assert result['new_crafts_added'] == 1
                        assert len(export_manager.existing_crafts) == 2
                        
                        # Check that names were disambiguated
                        craft_names = [craft['name'] for craft in export_manager.existing_crafts.values()]
                        
                        # Should have disambiguated names based on materials
                        expected_names = {
                            'Make Basic Fertilizer (Breezy Fin Darter)',
                            'Make Basic Fertilizer (Basic Berry)'
                        }
                        
                        assert set(craft_names) == expected_names
    
    def test_multiple_new_crafts_same_base_name_disambiguation(self, temp_exports_dir, mock_config_manager):
        """Test disambiguation when multiple new crafts have the same base name."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    # Add multiple fertilizer crafts with same base name but different materials
                    new_crafts = [
                        {
                            'name': 'Make Basic Fertilizer',
                            'materials': [{'item': 'Breezy Fin Darter', 'qty': 2}],
                            'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                            'requirements': {'profession': 'farming', 'tool': 'basic_tools'},
                            'confidence': 0.85
                        },
                        {
                            'name': 'Make Basic Fertilizer', 
                            'materials': [{'item': 'Basic Berry', 'qty': 2}],
                            'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                            'requirements': {'profession': 'farming', 'tool': 'basic_tools'},
                            'confidence': 0.88
                        },
                        {
                            'name': 'Make Basic Fertilizer',
                            'materials': [{'item': 'Basic Flower', 'qty': 5}],
                            'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                            'requirements': {'profession': 'farming', 'tool': 'basic_tools'},
                            'confidence': 0.82
                        }
                    ]
                    
                    # Mock _save_data to avoid file operations
                    with patch.object(export_manager, '_save_data'):
                        data = {'items_found': [], 'crafts_found': new_crafts}
                        result = export_manager.process_extraction_results(data)
                        
                        # Should add all crafts with disambiguated names
                        assert result['new_crafts_added'] == 3
                        assert len(export_manager.existing_crafts) == 3
                        
                        # Check that all names were disambiguated
                        craft_names = [craft['name'] for craft in export_manager.existing_crafts.values()]
                        
                        expected_names = {
                            'Make Basic Fertilizer (Breezy Fin Darter)',
                            'Make Basic Fertilizer (Basic Berry)',
                            'Make Basic Fertilizer (Basic Flower)'
                        }
                        
                        assert set(craft_names) == expected_names
    
    def test_no_disambiguation_needed_for_unique_names(self, temp_exports_dir, mock_config_manager):
        """Test that crafts with unique names don't get unnecessarily disambiguated."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    # Add crafts with unique names
                    new_crafts = [
                        {
                            'name': 'Craft Stone Axe',
                            'materials': [{'item': 'Stone', 'qty': 2}, {'item': 'Wood', 'qty': 1}],
                            'outputs': [{'item': 'Stone Axe', 'qty': 1}],
                            'requirements': {'profession': 'tool_making'},
                            'confidence': 0.85
                        },
                        {
                            'name': 'Weave Cloth Strip',
                            'materials': [{'item': 'Thread', 'qty': 1}],
                            'outputs': [{'item': 'Cloth Strip', 'qty': 1}],
                            'requirements': {'profession': 'tailoring'},
                            'confidence': 0.88
                        }
                    ]
                    
                    # Mock _save_data to avoid file operations
                    with patch.object(export_manager, '_save_data'):
                        data = {'items_found': [], 'crafts_found': new_crafts}
                        result = export_manager.process_extraction_results(data)
                        
                        # Should add all crafts without changing names
                        assert result['new_crafts_added'] == 2
                        assert len(export_manager.existing_crafts) == 2
                        
                        # Names should remain unchanged
                        craft_names = [craft['name'] for craft in export_manager.existing_crafts.values()]
                        
                        expected_names = {'Craft Stone Axe', 'Weave Cloth Strip'}
                        assert set(craft_names) == expected_names
    
    def test_already_disambiguated_names_preserved(self, temp_exports_dir, mock_config_manager):
        """Test that craft names already containing material disambiguation are preserved."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    # Add crafts where AI already extracted specific names
                    new_crafts = [
                        {
                            'name': 'Make Basic Fertilizer (Fish)',  # Already specific
                            'materials': [{'item': 'Breezy Fin Darter', 'qty': 2}],
                            'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                            'requirements': {'profession': 'farming', 'tool': 'basic_tools'},
                            'confidence': 0.85
                        },
                        {
                            'name': 'Make Basic Fertilizer (Berry)',  # Already specific
                            'materials': [{'item': 'Basic Berry', 'qty': 2}],
                            'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                            'requirements': {'profession': 'farming', 'tool': 'basic_tools'},
                            'confidence': 0.88
                        }
                    ]
                    
                    # Mock _save_data to avoid file operations
                    with patch.object(export_manager, '_save_data'):
                        data = {'items_found': [], 'crafts_found': new_crafts}
                        result = export_manager.process_extraction_results(data)
                        
                        # Should add both crafts without changing names
                        assert result['new_crafts_added'] == 2
                        assert len(export_manager.existing_crafts) == 2
                        
                        # Names should remain as extracted
                        craft_names = [craft['name'] for craft in export_manager.existing_crafts.values()]
                        expected_names = {
                            'Make Basic Fertilizer (Fish)',
                            'Make Basic Fertilizer (Berry)'
                        }
                        
                        assert set(craft_names) == expected_names
    
    def test_mixed_generic_and_specific_names(self, temp_exports_dir, mock_config_manager):
        """Test handling of mixed generic and already-specific craft names."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    # Mix of generic and specific names from AI
                    new_crafts = [
                        {
                            'name': 'Make Basic Fertilizer',  # Generic
                            'materials': [{'item': 'Breezy Fin Darter', 'qty': 2}],
                            'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                            'requirements': {'profession': 'farming', 'tool': 'basic_tools'},
                            'confidence': 0.85
                        },
                        {
                            'name': 'Make Basic Fertilizer (Berry)',  # Already specific
                            'materials': [{'item': 'Basic Berry', 'qty': 2}],
                            'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
                            'requirements': {'profession': 'farming', 'tool': 'basic_tools'},
                            'confidence': 0.88
                        }
                    ]
                    
                    # Mock _save_data to avoid file operations
                    with patch.object(export_manager, '_save_data'):
                        data = {'items_found': [], 'crafts_found': new_crafts}
                        result = export_manager.process_extraction_results(data)
                        
                        # Should add both crafts
                        assert result['new_crafts_added'] == 2
                        assert len(export_manager.existing_crafts) == 2
                        
                        # Generic name should be disambiguated, specific should remain
                        craft_names = [craft['name'] for craft in export_manager.existing_crafts.values()]
                        
                        # Should include both the original specific name and disambiguated generic
                        expected_names = {
                            'Make Basic Fertilizer (Breezy Fin Darter)',  # Disambiguated
                            'Make Basic Fertilizer (Berry)'               # Preserved
                        }
                        
                        assert set(craft_names) == expected_names


@pytest.mark.unit
class TestExportManagerCircularRecipeRejection:
    """Test ExportManager rejection of circular recipes during processing."""
    
    def test_process_extraction_rejects_circular_recipes(self, temp_exports_dir, mock_config_manager):
        """Test that circular recipes are rejected during processing with appropriate error reporting."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    # Mix of valid and circular recipes
                    extraction_data = {
                        'items_found': [],
                        'crafts_found': [
                            # Valid recipe
                            {
                                'name': 'Make Basic Fertilizer',
                                'confidence': 0.85,
                                'requirements': {'profession': 'farming', 'tool': 'basic_tools'},
                                'materials': [{'item': 'Breezy Fin Darter', 'qty': 2}],
                                'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}]
                            },
                            # Circular recipe (should be rejected)
                            {
                                'name': 'Make Basic Fertilizer (Circular)',
                                'confidence': 0.90,  # High confidence but still invalid
                                'requirements': {'profession': 'farming', 'tool': 'basic_tools'},
                                'materials': [{'item': 'Basic Fertilizer', 'qty': 1}],  # Same as output!
                                'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}]
                            },
                            # Another valid recipe
                            {
                                'name': 'Craft Stone Axe',
                                'confidence': 0.88,
                                'requirements': {'profession': 'tool_making'},
                                'materials': [{'item': 'Stone', 'qty': 2}, {'item': 'Wood', 'qty': 1}],
                                'outputs': [{'item': 'Stone Axe', 'qty': 1}]
                            }
                        ]
                    }
                    
                    # Mock _save_data to avoid file operations
                    with patch.object(export_manager, '_save_data'):
                        result = export_manager.process_extraction_results(extraction_data)
                        
                        # Should add 2 valid crafts and reject 1 circular recipe
                        assert result['new_crafts_added'] == 2
                        assert result['crafts_rejected'] == 1
                        assert result['crafts_processed'] == 3
                        
                        # Verify only valid crafts were added
                        craft_names = [craft['name'] for craft in export_manager.existing_crafts.values()]
                        
                        expected_valid_names = {
                            'Make Basic Fertilizer (Breezy Fin Darter)',  # Disambiguated 
                            'Craft Stone Axe'
                        }
                        
                        assert set(craft_names) == expected_valid_names
                        
                        # Verify circular recipe was not added
                        assert 'Make Basic Fertilizer (Circular)' not in craft_names
                        assert 'Make Basic Fertilizer (Basic Fertilizer)' not in craft_names
    
    def test_circular_recipe_error_logging(self, temp_exports_dir, mock_config_manager):
        """Test that circular recipes trigger appropriate error logging for user feedback."""
        with patch('structlog.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with patch.object(ExportManager, '_load_existing_items', return_value={}):
                with patch.object(ExportManager, '_load_existing_crafts', return_value={}):
                    export_manager = ExportManager(temp_exports_dir, mock_config_manager)
                    
                    circular_craft = {
                        'name': 'Make Basic Fertilizer',
                        'confidence': 0.85,
                        'requirements': {'profession': 'farming', 'tool': 'basic_tools'},
                        'materials': [{'item': 'Basic Fertilizer', 'qty': 1}],
                        'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}]
                    }
                    
                    # Call validation directly to test logging
                    validation = export_manager._validate_craft(circular_craft)
                    
                    # Should be invalid
                    assert validation['is_valid'] is False
                    assert any('Circular recipe detected' in reason for reason in validation['reasons'])
                    
                    # Check that warning was logged for user awareness
                    mock_logger.warning.assert_called()
                    warning_call = mock_logger.warning.call_args
                    assert 'Circular recipe detected' in warning_call[0][0]
                    assert warning_call[1]['craft_name'] == 'Make Basic Fertilizer'
                    assert 'basic fertilizer' in warning_call[1]['circular_items']


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
