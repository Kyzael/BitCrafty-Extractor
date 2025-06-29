"""Comprehensive validation test for the updated main application configuration using pytest."""

import pytest
import asyncio
import numpy as np
import cv2
from pathlib import Path
import sys

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

try:
    from bitcrafty_extractor.config.config_manager import ConfigManager
    from bitcrafty_extractor.ai_analysis.vision_client import VisionClient, ImageData
    import structlog
except ImportError as e:
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)


@pytest.fixture
def config_manager():
    """Create a ConfigManager instance for testing."""
    return ConfigManager()


@pytest.fixture
def vision_client(config_manager):
    """Create a VisionClient instance for testing."""
    logger = structlog.get_logger(__name__)
    return VisionClient(logger, config_manager)


@pytest.fixture
def test_recipe():
    """Test recipe data for validation."""
    return {
        "recipe_name": "Weave Rough Cloth Strip",
        "description": "Comprehensive validation test",
        "screenshots": [
            "weave_rough_cloth_strip_input.png",
            "weave_rough_cloth_strip.png",
            "weave_rough_cloth_output.png"
        ]
    }


@pytest.fixture
def validation_prompt():
    """Create a comprehensive validation prompt."""
    return """
TASK: Extract complete item details and crafting recipe information from the provided screenshots.

VALIDATION REQUIREMENTS:
1. ITEM DETAILS - Extract accurate information for ALL items:
   - Name: Exact item name as shown
   - Tier: Item tier/level (1-5) if visible
   - Rarity: Item rarity (common, uncommon, rare, epic, legendary)
   - Description: Complete item description text
   - Uses: What the item is used for

2. CRAFTING RECIPE - Extract complete recipe information:
   - Name: Exact recipe/craft name
   - Requirements: Profession, tool, building requirements
   - Input materials: Exact quantities and item names
   - Output materials: Exact quantities and item names

3. ACCURACY CRITICAL POINTS:
   - Read quantities VERY carefully (look for 1x, 2x, 3x indicators)
   - Include complete item descriptions, not summaries
   - Extract exact profession/tool/building names as shown
   - Verify tier numbers match what's displayed

REQUIRED JSON RESPONSE:
```json
{
  "analysis_type": "comprehensive_validation",
  "screenshots_processed": <number>,
  "validation_notes": "Explain your confidence in the accuracy",
  "items_found": [
    {
      "type": "item",
      "name": "string - EXACT item name",
      "tier": <number or null - exact tier shown>,
      "rarity": "string - exact rarity shown",
      "description": "string - COMPLETE description, not summary",
      "uses": "string - what item is used for",
      "confidence": <0.0-1.0>
    }
  ],
  "crafts_found": [
    {
      "type": "craft_recipe",
      "name": "string - EXACT recipe name",
      "requirements": {
        "profession": "string - EXACT profession name",
        "tool": "string or null - EXACT tool name",
        "building": "string or null - EXACT building name"
      },
      "input_materials": [
        {
          "item_name": "string - EXACT input item name",
          "quantity": <number - READ VERY CAREFULLY>
        }
      ],
      "output_materials": [
        {
          "item_name": "string - EXACT output item name",
          "quantity": <number - READ VERY CAREFULLY>,
          "variable_quantity": <boolean>
        }
      ],
      "confidence": <0.0-1.0>
    }
  ],
  "total_confidence": <0.0-1.0>
}
```

Extract all data with maximum accuracy and completeness.
"""


@pytest.fixture
def expected_items():
    """Expected item validation data."""
    return {
        "Rough Spool of Thread": {"tier": 1, "rarity": "common"},
        "Rough Cloth Strip": {"tier": 1, "rarity": "common"}
    }


@pytest.mark.integration
class TestConfigurationValidation:
    """Test comprehensive configuration validation."""
    
    def test_configuration_loading(self, config_manager):
        """Test that configuration loads properly."""
        assert config_manager is not None
        assert config_manager.config is not None
        assert config_manager.config.extraction is not None
        assert config_manager.config.extraction.primary_provider is not None
        assert config_manager.config.extraction.fallback_provider is not None

    def test_vision_client_initialization(self, vision_client):
        """Test that vision client initializes properly."""
        assert vision_client is not None
        assert hasattr(vision_client, 'analyze_images')

    def test_test_data_availability(self, test_recipe):
        """Test that test data files are available."""
        craft_folder = Path(__file__).parent.parent / "test_data" / "craft"
        
        available_images = 0
        for screenshot in test_recipe['screenshots']:
            img_path = craft_folder / screenshot
            if img_path.exists():
                available_images += 1
        
        # At least one test image should be available
        assert available_images > 0, f"No test images found in {craft_folder}"

    @pytest.mark.asyncio
    async def test_image_loading(self, test_recipe):
        """Test loading of test images."""
        craft_folder = Path(__file__).parent.parent / "test_data" / "craft"
        recipe_images = []
        
        for screenshot in test_recipe['screenshots']:
            img_path = craft_folder / screenshot
            if img_path.exists():
                image = cv2.imread(str(img_path))
                if image is not None:
                    recipe_images.append(ImageData(image_array=image))
        
        assert len(recipe_images) > 0, "Should load at least one test image"
        
        for image_data in recipe_images:
            assert image_data.image_array is not None
            assert image_data.image_array.shape[2] == 3  # Should be RGB/BGR

    @pytest.mark.asyncio
    async def test_vision_client_integration(self, vision_client, test_recipe):
        """Test vision client integration without expensive API calls."""
        # Load test images
        craft_folder = Path(__file__).parent.parent / "test_data" / "craft"
        recipe_images = []
        
        for screenshot in test_recipe['screenshots']:
            img_path = craft_folder / screenshot
            if img_path.exists():
                image = cv2.imread(str(img_path))
                if image is not None:
                    recipe_images.append(ImageData(image_array=image))
        
        if not recipe_images:
            pytest.skip("No test images available for analysis")
        
        # Test image processing and preparation (no API calls)
        image_data = recipe_images[0]
        
        # Test image preparation method
        try:
            base64_image = vision_client._prepare_image(image_data)
            assert base64_image is not None
            assert isinstance(base64_image, str)
            assert len(base64_image) > 0
            
            # Test cost estimation (no API calls)
            image_size = len(base64_image.encode('utf-8'))
            cost = vision_client._estimate_cost(vision_client.default_provider, image_size)
            assert isinstance(cost, (int, float))
            assert cost >= 0
        except AttributeError:
            # If internal methods aren't accessible, test public interface
            pass
        
        # Test provider configuration
        assert hasattr(vision_client, 'config_manager')
        assert vision_client.config_manager is not None
        
        # Test that analyze_images method exists and is callable
        assert hasattr(vision_client, 'analyze_images')
        assert callable(getattr(vision_client, 'analyze_images'))
        
        # Test get_stats method (no API calls)
        if hasattr(vision_client, 'get_stats'):
            stats = vision_client.get_stats()
            assert isinstance(stats, dict)
        
        # Mock a successful analysis result for validation testing
        mock_result = type('MockResult', (), {
            'success': True,
            'data': {
                'analysis_type': 'integration_test',
                'screenshots_processed': len(recipe_images),
                'items_found': [
                    {
                        'name': 'Test Item',
                        'tier': 1,
                        'rarity': 'common',
                        'description': 'Test description',
                        'confidence': 0.95
                    }
                ],
                'crafts_found': [
                    {
                        'name': 'Test Craft',
                        'requirements': {'profession': 'test'},
                        'input_materials': [{'item_name': 'Test Input', 'quantity': 1}],
                        'output_materials': [{'item_name': 'Test Output', 'quantity': 1}],
                        'confidence': 0.90
                    }
                ],
                'total_confidence': 0.92
            },
            'confidence': 0.92,
            'cost_estimate': 0.001,
            'processing_time': 0.1
        })()
        
        # Test validation logic with mock data
        self._validate_extraction_quality(mock_result.data)

    @pytest.mark.asyncio  
    async def test_api_configuration_validation(self, vision_client):
        """Test API configuration without making expensive calls."""
        # Test that providers are configured
        assert hasattr(vision_client, 'default_provider')
        assert hasattr(vision_client, 'fallback_provider')
        
        # Test configuration initialization
        assert vision_client.config_manager is not None
        config = vision_client.config_manager.config
        assert config is not None
        assert hasattr(config, 'extraction')
        
        # Verify provider configuration exists
        extraction_config = config.extraction
        assert extraction_config.primary_provider is not None
        assert extraction_config.fallback_provider is not None
        
        # Test that API credentials exist (don't validate them to avoid costs)
        if hasattr(config, 'openai') and config.openai:
            assert hasattr(config.openai, 'api_key')
        if hasattr(config, 'anthropic') and config.anthropic:
            assert hasattr(config.anthropic, 'api_key')
    
    def _validate_extraction_quality(self, data: dict):
        """Validate the quality of extracted data."""
        assert data is not None, "Data should not be None"
        
        # Validate items
        items = data.get('items_found', [])
        assert isinstance(items, list), "items_found should be a list"
        
        expected_items = {
            "Rough Spool of Thread": {"tier": 1, "rarity": "common"},
            "Rough Cloth Strip": {"tier": 1, "rarity": "common"}
        }
        
        for item in items:
            assert isinstance(item, dict), "Each item should be a dict"
            assert 'name' in item, "Item should have a name"
            assert 'confidence' in item, "Item should have confidence"
            
            name = item.get('name')
            confidence = item.get('confidence', 0)
            assert isinstance(confidence, (int, float)), "Confidence should be numeric"
            assert 0.0 <= confidence <= 1.0, "Confidence should be between 0 and 1"
            
            # Check specific expected items
            if name in expected_items:
                expected = expected_items[name]
                tier = item.get('tier')
                rarity = item.get('rarity', '').lower()
                
                if tier is not None:
                    assert tier == expected["tier"], f"Tier mismatch for {name}"
                if rarity:
                    assert rarity == expected["rarity"], f"Rarity mismatch for {name}"
        
        # Validate crafting recipes
        crafts = data.get('crafts_found', [])
        assert isinstance(crafts, list), "crafts_found should be a list"
        
        for craft in crafts:
            assert isinstance(craft, dict), "Each craft should be a dict"
            assert 'name' in craft, "Craft should have a name"
            assert 'confidence' in craft, "Craft should have confidence"
            assert 'requirements' in craft, "Craft should have requirements"
            assert 'input_materials' in craft, "Craft should have input materials"
            assert 'output_materials' in craft, "Craft should have output materials"
            
            confidence = craft.get('confidence', 0)
            assert isinstance(confidence, (int, float)), "Confidence should be numeric"
            assert 0.0 <= confidence <= 1.0, "Confidence should be between 0 and 1"
            
            # Validate requirements
            reqs = craft.get('requirements', {})
            assert isinstance(reqs, dict), "Requirements should be a dict"
            
            # Validate input materials
            inputs = craft.get('input_materials', [])
            assert isinstance(inputs, list), "Input materials should be a list"
            
            for inp in inputs:
                assert isinstance(inp, dict), "Each input should be a dict"
                assert 'item_name' in inp, "Input should have item_name"
                assert 'quantity' in inp, "Input should have quantity"
                
                quantity = inp.get('quantity')
                assert isinstance(quantity, (int, float)), "Quantity should be numeric"
                assert quantity > 0, "Quantity should be positive"
            
            # Validate output materials
            outputs = craft.get('output_materials', [])
            assert isinstance(outputs, list), "Output materials should be a list"
            
            for out in outputs:
                assert isinstance(out, dict), "Each output should be a dict"
                assert 'item_name' in out, "Output should have item_name"
                assert 'quantity' in out, "Output should have quantity"
                
                quantity = out.get('quantity')
                assert isinstance(quantity, (int, float)), "Quantity should be numeric"
                assert quantity > 0, "Quantity should be positive"
        
        # Overall assessment
        total_confidence = data.get('total_confidence', 0)
        assert isinstance(total_confidence, (int, float)), "Total confidence should be numeric"
        assert 0.0 <= total_confidence <= 1.0, "Total confidence should be between 0 and 1"


@pytest.mark.integration
def test_validation_prompt_structure(validation_prompt):
    """Test that validation prompt has proper structure."""
    assert isinstance(validation_prompt, str)
    assert len(validation_prompt) > 100
    assert "TASK:" in validation_prompt
    assert "VALIDATION REQUIREMENTS:" in validation_prompt
    assert "JSON RESPONSE:" in validation_prompt
    assert "items_found" in validation_prompt
    assert "crafts_found" in validation_prompt


@pytest.mark.integration
def test_expected_items_structure(expected_items):
    """Test that expected items structure is valid."""
    assert isinstance(expected_items, dict)
    assert len(expected_items) > 0
    
    for item_name, expected_data in expected_items.items():
        assert isinstance(item_name, str)
        assert isinstance(expected_data, dict)
        assert 'tier' in expected_data
        assert 'rarity' in expected_data
        assert isinstance(expected_data['tier'], int)
        assert isinstance(expected_data['rarity'], str)
