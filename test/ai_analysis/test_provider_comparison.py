#!/usr/bin/env python3
"""
Test recipe-focused batch analysis.
Send all screenshots for ONE recipe together and extract both the item details and crafting recipe.
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
from bitcrafty_extractor.ai_analysis.prompts_queue import PromptBuilder, ExtractionType

async def test_recipe_batch_analysis():
    """Test recipe-focused batch analysis: one recipe per batch."""
    print("BitCrafty Extractor - Recipe Batch Analysis Test")
    print("=" * 55)
    
    try:
        # Load configuration
        print("🔧 Loading configuration...")
        config_manager = ConfigManager()
        
        # Initialize vision client
        print("🤖 Initializing AI vision client...")
        import structlog
        logger = structlog.get_logger(__name__)
        vision_client = VisionClient(logger, config_manager)
        
        # Define recipe batches - each recipe gets its own focused analysis
        recipe_batches = [
            {
                "recipe_name": "Weave Rough Cloth Strip",
                "description": "Complete crafting recipe for Rough Cloth Strip",
                "screenshots": [
                    "weave_rough_cloth_strip_input.png",   # Input materials view
                    "weave_rough_cloth_strip.png",         # Main recipe interface  
                    "weave_rough_cloth_output.png"         # Output materials view
                ]
            }
            # Future batches can be added here:
            # {
            #     "recipe_name": "Forge Iron Sword", 
            #     "screenshots": ["iron_sword_input.png", "iron_sword_recipe.png", "iron_sword_output.png"]
            # }
        ]
        
        # Process each recipe batch with multiple providers and models
        providers_to_test = [
            ("OpenAI GPT-4V (gpt-4o)", "openai", "gpt-4o"),
            ("OpenAI GPT-4V (gpt-4-vision-preview)", "openai", "gpt-4-vision-preview"), 
            ("OpenAI GPT-4V (gpt-4-turbo)", "openai", "gpt-4-turbo"),
            ("Anthropic Claude", "anthropic", "claude-3-5-sonnet-20241022")
        ]
        
        for batch_idx, recipe_batch in enumerate(recipe_batches, 1):
            print(f"\n" + "="*70)
            print(f"🎯 Recipe Batch {batch_idx}: {recipe_batch['recipe_name']}")
            print(f"📝 {recipe_batch['description']}")
            print("="*70)
            
            # Load all screenshots for this recipe
            craft_folder = Path(__file__).parent.parent / "test_data" / "craft"
            recipe_images = []
            
            for screenshot in recipe_batch['screenshots']:
                img_path = craft_folder / screenshot
                if img_path.exists():
                    image = cv2.imread(str(img_path))
                    if image is not None:
                        recipe_images.append(ImageData(image_array=image))
                        print(f"   ✅ Loaded: {screenshot} ({image.shape})")
                    else:
                        print(f"   ❌ Could not load: {screenshot}")
                else:
                    print(f"   ❌ Not found: {screenshot}")
            
            if not recipe_images:
                print(f"   💥 No images loaded for {recipe_batch['recipe_name']}")
                continue
                
            print(f"\n🔄 Testing with {len(recipe_images)} screenshots")
            
            # Create improved prompt 
            improved_prompt = create_recipe_focused_prompt()
            
            # Test with multiple providers and models
            for provider_name, provider_config, model_name in providers_to_test:
                print(f"\n" + "-"*60)
                print(f"🤖 Testing with {provider_name}")
                print(f"📋 Model: {model_name}")
                print("-"*60)
                
                try:
                    # Force specific provider and model
                    if provider_config == "openai":
                        from bitcrafty_extractor.ai_analysis.vision_client import AIProvider
                        provider = AIProvider.OPENAI_GPT4V
                        
                        # Temporarily override the model for this test
                        original_openai_model = None
                        if config_manager.config.openai:
                            original_openai_model = config_manager.config.openai.model
                            config_manager.config.openai.model = model_name
                            # Reinitialize the vision client with new model
                            vision_client = VisionClient(logger, config_manager)
                    else:
                        from bitcrafty_extractor.ai_analysis.vision_client import AIProvider
                        provider = AIProvider.ANTHROPIC_CLAUDE
                    
                    result = await vision_client.analyze_images(
                        image_data_list=recipe_images,
                        prompt=improved_prompt,
                        provider=provider,
                        use_fallback=False  # Don't use fallback for comparison
                    )
                    
                    if result.success:
                        print(f"   ✅ {provider_name} analysis successful!")
                        print(f"   Confidence: {result.confidence:.2f}")
                        print(f"   Cost: ${result.cost_estimate:.4f}")
                        print(f"   Processing time: {result.processing_time:.1f}s")
                        
                        # Show structured results
                        await display_provider_results(result.data, provider_name, recipe_batch['recipe_name'])
                        
                    else:
                        print(f"   ❌ {provider_name} analysis failed!")
                        if result.error_message:
                            print(f"   Error: {result.error_message}")
                    
                    # Restore original model if we changed it
                    if provider_config == "openai" and original_openai_model:
                        config_manager.config.openai.model = original_openai_model
                        vision_client = VisionClient(logger, config_manager)
                            
                except Exception as e:
                    print(f"   💥 {provider_name} analysis crashed: {str(e)}")
                    
                    # Restore original model on error too
                    if provider_config == "openai" and 'original_openai_model' in locals() and original_openai_model:
                        config_manager.config.openai.model = original_openai_model
                        vision_client = VisionClient(logger, config_manager)
            
            # Add comparison summary
            print(f"\n" + "="*50)
            print(f"📊 Provider Comparison Complete")
            print("="*50)
        
        return True
            
    except Exception as e:
        print(f"\n💥 Test crashed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def create_recipe_focused_prompt(recipe_name: str = None) -> str:
    """Create a focused prompt for analyzing recipe screenshots."""
    
    return f"""
TASK: Carefully review all provided screenshots and extract any items and their associated crafting recipes.

INSTRUCTIONS:
1. Look for item tooltips, descriptions, and details - extract all visible item information
2. Look for crafting interfaces, recipe views, or any UI showing how to make items
3. Pay EXTREMELY careful attention to quantities - count exactly what you see
4. If you see different quantities in different screenshots, choose the most clear and reliable view
5. Extract complete item details AND any crafting recipes shown

WHAT TO EXTRACT:

ITEMS:
- Extract details for ANY items shown (ingredients, outputs, tools, etc.)
- Include name, tier, rarity, description, and uses
- Look in tooltips, inventory views, item details, etc.

CRAFTING RECIPES:
- Extract ANY crafting recipes or processes shown
- Include exact requirements (profession, tool, building)
- Count input materials VERY carefully - look for quantity numbers, item stacks, etc.
- Count output materials VERY carefully - what is actually produced
- If unclear, state your reasoning

CRITICAL: READ QUANTITIES EXTREMELY CAREFULLY
- Look for numbers next to items (1x, 2x, 3x, etc.)
- Check item stack sizes or counts
- If multiple views show different quantities, explain what you see
- Double-check your quantity readings

REQUIRED JSON RESPONSE:
```json
{{
  "analysis_type": "recipe_analysis",
  "screenshots_processed": <number>,
  "quantity_reasoning": "Explain how you determined the quantities",
  "items_found": [
    {{
      "type": "item",
      "name": "string - exact item name",
      "tier": <number or null>,
      "rarity": "string",
      "description": "string - item description", 
      "uses": "string - what the item is used for",
      "confidence": <0.0-1.0>
    }}
  ],
  "crafts_found": [
    {{
      "type": "craft_recipe", 
      "name": "string - recipe name",
      "requirements": {{
        "profession": "string",
        "tool": "string or null",
        "building": "string or null"
      }},
      "input_materials": [
        {{
          "item_name": "string",
          "quantity": <number - COUNT VERY CAREFULLY>
        }}
      ],
      "output_materials": [
        {{
          "item_name": "string", 
          "quantity": <number - COUNT VERY CAREFULLY>,
          "variable_quantity": <boolean>
        }}
      ],
      "confidence": <0.0-1.0>
    }}
  ],
  "total_confidence": <0.0-1.0>
}}
```

Analyze all screenshots and extract complete item and recipe data with accurate quantities.
"""

async def display_provider_results(data: dict, provider_name: str, expected_recipe_name: str = None):
    """Display the extracted results from a specific provider."""
    
    if not data:
        print(f"   ❌ {provider_name}: No data extracted")
        return
        
    print(f"   📊 {provider_name} Results:")
    
    # Show reasoning if available
    reasoning = data.get('quantity_reasoning', '')
    if reasoning:
        print(f"   🧠 Quantity reasoning: {reasoning}")
    
    # Show items found
    items = data.get('items_found', [])
    print(f"   📦 Items found: {len(items)}")
    for item in items:
        name = item.get('name', 'Unknown')
        confidence = item.get('confidence', 0)
        print(f"      • {name} (confidence: {confidence:.2f})")
    
    # Show crafting recipes with focus on quantities
    crafts = data.get('crafts_found', [])
    print(f"   🔧 Recipes found: {len(crafts)}")
    for craft in crafts:
        name = craft.get('name', 'Unknown')
        confidence = craft.get('confidence', 0)
        print(f"      • {name} (confidence: {confidence:.2f})")
        
        # Focus on input quantities
        inputs = craft.get('input_materials', [])
        if inputs:
            for inp in inputs:
                quantity = inp.get('quantity', '?')
                item_name = inp.get('item_name', 'Unknown')
                print(f"        Input: {quantity}x {item_name}")
        
        # Show outputs
        outputs = craft.get('output_materials', [])
        if outputs:
            for out in outputs:
                quantity = out.get('quantity', '?')
                item_name = out.get('item_name', 'Unknown')
                print(f"        Output: {quantity}x {item_name}")

async def display_recipe_results(data: dict, expected_recipe_name: str):
    """Display the extracted recipe results in a clear format."""
    
    if not data:
        print("   ❌ No data extracted")
        return
        
    print(f"\n📊 Extracted Data Summary:")
    print(f"   Recipe analyzed: {expected_recipe_name}")
    print(f"   Screenshots processed: {data.get('screenshots_processed', 0)}")
    
    # Show items found
    items = data.get('items_found', [])
    print(f"\n📦 Items Found ({len(items)}):")
    for i, item in enumerate(items, 1):
        name = item.get('name', 'Unknown')
        tier = item.get('tier', 'Unknown')
        rarity = item.get('rarity', 'unknown')
        confidence = item.get('confidence', 0)
        description = item.get('description', 'No description')
        if description and len(description) > 80:
            description = description[:80]
        
        print(f"   {i}. {name}")
        print(f"      Tier: {tier} | Rarity: {rarity} | Confidence: {confidence:.2f}")
        print(f"      Description: {description}...")
    
    # Show crafting recipes  
    crafts = data.get('crafts_found', [])
    print(f"\n🔧 Crafting Recipes Found ({len(crafts)}):")
    for i, craft in enumerate(crafts, 1):
        name = craft.get('name', 'Unknown')
        confidence = craft.get('confidence', 0)
        
        print(f"   {i}. {name} (Confidence: {confidence:.2f})")
        
        # Requirements
        reqs = craft.get('requirements', {})
        if reqs:
            profession = reqs.get('profession', 'Unknown')
            tool = reqs.get('tool', 'None')
            building = reqs.get('building', 'None')
            print(f"      Requirements:")
            print(f"        Profession: {profession}")
            print(f"        Tool: {tool}")
            print(f"        Building: {building}")
        
        # Input materials
        inputs = craft.get('input_materials', [])
        if inputs:
            print(f"      Input Materials:")
            for inp in inputs:
                quantity = inp.get('quantity', '?')
                item_name = inp.get('item_name', 'Unknown')
                print(f"        {quantity}x {item_name}")
        
        # Output materials
        outputs = craft.get('output_materials', [])
        if outputs:
            print(f"      Output Materials:")
            for out in outputs:
                quantity = out.get('quantity', '?')
                item_name = out.get('item_name', 'Unknown')
                variable = out.get('variable_quantity', False)
                var_text = " (variable)" if variable else ""
                print(f"        {quantity}x {item_name}{var_text}")
    
    # Overall confidence
    total_confidence = data.get('total_confidence', 0)
    print(f"\n📈 Overall Analysis Confidence: {total_confidence:.2f}")
    
    # Validation
    if crafts:
        expected_lower = expected_recipe_name.lower()
        found_lower = crafts[0].get('name', '').lower()
        if expected_lower in found_lower or found_lower in expected_lower:
            print(f"✅ Recipe name validation: PASSED")
        else:
            print(f"⚠️ Recipe name validation: Expected '{expected_recipe_name}' but found '{crafts[0].get('name')}'")

if __name__ == "__main__":
    success = asyncio.run(test_recipe_batch_analysis())
    sys.exit(0 if success else 1)
