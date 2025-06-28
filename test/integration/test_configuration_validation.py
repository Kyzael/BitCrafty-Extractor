#!/usr/bin/env python3
"""
Comprehensive validation test for the updated main application configuration.
Tests accurate extraction of item details and crafting requirements.
"""

import sys
import asyncio
import numpy as np
import cv2
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from bitcrafty_extractor.config.config_manager import ConfigManager
from bitcrafty_extractor.ai_analysis.vision_client import VisionClient, ImageData

async def test_updated_configuration():
    """Test the updated configuration with Anthropic Claude as primary."""
    print("BitCrafty Extractor - Updated Configuration Validation")
    print("=" * 60)
    
    try:
        # Load configuration with new defaults
        print("🔧 Loading updated configuration...")
        config_manager = ConfigManager()
        
        print(f"✅ Configuration loaded:")
        print(f"   Primary provider: {config_manager.config.extraction.primary_provider}")
        print(f"   Fallback provider: {config_manager.config.extraction.fallback_provider}")
        
        if config_manager.config.openai:
            print(f"   OpenAI model: {config_manager.config.openai.model}")
        if config_manager.config.anthropic:
            print(f"   Anthropic model: {config_manager.config.anthropic.model}")
        
        # Initialize vision client
        print("\n🤖 Initializing AI vision client...")
        import structlog
        logger = structlog.get_logger(__name__)
        vision_client = VisionClient(logger, config_manager)
        
        # Test recipe batch
        test_recipe = {
            "recipe_name": "Weave Rough Cloth Strip",
            "description": "Comprehensive validation test",
            "screenshots": [
                "weave_rough_cloth_strip_input.png",
                "weave_rough_cloth_strip.png",
                "weave_rough_cloth_output.png"
            ]
        }
        
        print(f"\n🎯 Testing Recipe: {test_recipe['recipe_name']}")
        
        # Load screenshots
        craft_folder = Path(__file__).parent.parent / "test_data" / "craft"
        recipe_images = []
        
        for screenshot in test_recipe['screenshots']:
            img_path = craft_folder / screenshot
            if img_path.exists():
                image = cv2.imread(str(img_path))
                if image is not None:
                    recipe_images.append(ImageData(image_array=image))
                    print(f"   ✅ Loaded: {screenshot}")
                else:
                    print(f"   ❌ Could not load: {screenshot}")
            else:
                print(f"   ❌ Not found: {screenshot}")
        
        if not recipe_images:
            print("   💥 No images loaded!")
            return False
        
        # Create comprehensive validation prompt
        validation_prompt = create_validation_prompt()
        
        print(f"\n🔄 Analyzing with updated configuration...")
        print(f"   Using: {config_manager.config.extraction.primary_provider} (primary)")
        
        result = await vision_client.analyze_images(
            image_data_list=recipe_images,
            prompt=validation_prompt,
            use_fallback=True
        )
        
        if result.success:
            print(f"\n🎉 Analysis successful!")
            print(f"   Provider used: {result.provider}")
            print(f"   Confidence: {result.confidence:.2f}")
            print(f"   Cost: ${result.cost_estimate:.4f}")
            print(f"   Processing time: {result.processing_time:.1f}s")
            
            # Comprehensive validation
            await validate_extraction_quality(result.data)
            
            return True
        else:
            print(f"\n❌ Analysis failed!")
            if result.error_message:
                print(f"   Error: {result.error_message}")
            return False
            
    except Exception as e:
        print(f"\n💥 Test crashed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def create_validation_prompt() -> str:
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

async def validate_extraction_quality(data: dict):
    """Validate the quality of extracted data against expected standards."""
    
    print(f"\n📋 COMPREHENSIVE VALIDATION RESULTS")
    print("=" * 50)
    
    if not data:
        print("❌ No data extracted")
        return
    
    validation_notes = data.get('validation_notes', '')
    if validation_notes:
        print(f"🧠 AI Validation Notes: {validation_notes}")
    
    # Validate items
    items = data.get('items_found', [])
    print(f"\n📦 ITEM VALIDATION ({len(items)} items found):")
    
    expected_items = {
        "Rough Spool of Thread": {"tier": 1, "rarity": "common"},
        "Rough Cloth Strip": {"tier": 1, "rarity": "common"}
    }
    
    for item in items:
        name = item.get('name', 'Unknown')
        tier = item.get('tier')
        rarity = item.get('rarity', '').lower()
        description = item.get('description', '')
        uses = item.get('uses', '')
        confidence = item.get('confidence', 0)
        
        print(f"\n   🔍 {name}:")
        print(f"      Tier: {tier} {'✅' if tier is not None else '⚠️ Missing'}")
        print(f"      Rarity: {rarity} {'✅' if rarity else '⚠️ Missing'}")
        print(f"      Description: {'✅ Complete' if len(description) > 20 else '⚠️ Too short'} ({len(description)} chars)")
        print(f"      Uses: {'✅ Provided' if uses else '⚠️ Missing'}")
        print(f"      Confidence: {confidence:.2f}")
        
        # Check against expected values
        if name in expected_items:
            expected = expected_items[name]
            if tier == expected["tier"]:
                print(f"      ✅ Tier matches expected value")
            else:
                print(f"      ❌ Tier mismatch: expected {expected['tier']}, got {tier}")
            
            if rarity == expected["rarity"]:
                print(f"      ✅ Rarity matches expected value")
            else:
                print(f"      ❌ Rarity mismatch: expected {expected['rarity']}, got {rarity}")
    
    # Validate crafting recipe
    crafts = data.get('crafts_found', [])
    print(f"\n🔧 CRAFTING RECIPE VALIDATION ({len(crafts)} recipes found):")
    
    for craft in crafts:
        name = craft.get('name', 'Unknown')
        confidence = craft.get('confidence', 0)
        
        print(f"\n   🔍 {name} (Confidence: {confidence:.2f}):")
        
        # Validate requirements
        reqs = craft.get('requirements', {})
        profession = reqs.get('profession', '')
        tool = reqs.get('tool')
        building = reqs.get('building', '')
        
        print(f"      Requirements:")
        print(f"        Profession: '{profession}' {'✅' if profession else '❌ Missing'}")
        print(f"        Tool: '{tool}' {'✅' if tool is not None else '⚠️ None specified'}")
        print(f"        Building: '{building}' {'✅' if building else '❌ Missing'}")
        
        # Validate input materials
        inputs = craft.get('input_materials', [])
        print(f"      Input Materials:")
        if inputs:
            for inp in inputs:
                quantity = inp.get('quantity')
                item_name = inp.get('item_name', '')
                print(f"        {quantity}x {item_name}")
                
                # Critical validation: quantity should be 1 for this recipe
                if item_name == "Rough Spool of Thread":
                    if quantity == 1:
                        print(f"        ✅ CORRECT: Quantity is 1 (as expected)")
                    else:
                        print(f"        ❌ INCORRECT: Quantity is {quantity}, should be 1")
        else:
            print(f"        ❌ No input materials found")
        
        # Validate output materials
        outputs = craft.get('output_materials', [])
        print(f"      Output Materials:")
        if outputs:
            for out in outputs:
                quantity = out.get('quantity')
                item_name = out.get('item_name', '')
                variable = out.get('variable_quantity', False)
                print(f"        {quantity}x {item_name} {'(variable)' if variable else ''}")
                
                # Validation: should produce 1 Rough Cloth Strip
                if item_name == "Rough Cloth Strip" and quantity == 1:
                    print(f"        ✅ CORRECT: Output quantity and item")
        else:
            print(f"        ❌ No output materials found")
    
    # Overall assessment
    total_confidence = data.get('total_confidence', 0)
    print(f"\n📈 OVERALL ASSESSMENT:")
    print(f"   Total Confidence: {total_confidence:.2f}")
    
    if len(items) >= 2 and len(crafts) >= 1 and total_confidence >= 0.8:
        print(f"   🎉 VALIDATION PASSED: High-quality extraction achieved")
    else:
        print(f"   ⚠️ VALIDATION CONCERNS: Review extraction quality")

if __name__ == "__main__":
    success = asyncio.run(test_updated_configuration())
    sys.exit(0 if success else 1)
