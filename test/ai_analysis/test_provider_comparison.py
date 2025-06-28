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
from bitcrafty_extractor.ai_analysis.prompts import PromptBuilder, ExtractionType

async def test_single_item_recognition():
    """Test single item recognition with optimized prompts."""
    print("🎯 Testing Single Item Recognition with Optimized Prompts")
    print("=" * 60)
    
    try:
        # Load configuration
        config_manager = ConfigManager()
        import structlog
        logger = structlog.get_logger(__name__)
        vision_client = VisionClient(logger, config_manager)
        prompt_builder = PromptBuilder()
        
        # Load single item test image
        item_folder = Path(__file__).parent.parent / "test_data" / "item"
        item_img_path = item_folder / "rough-spool-of-thread.png"
        
        if not item_img_path.exists():
            print(f"   ❌ Item test image not found: {item_img_path}")
            return False
            
        item_image = cv2.imread(str(item_img_path))
        if item_image is None:
            print(f"   ❌ Could not load item image")
            return False
            
        item_data = [ImageData(image_array=item_image)]
        print(f"   ✅ Loaded: rough-spool-of-thread.png ({item_image.shape})")
        
        # Test single item with optimized prompt
        single_item_prompt = prompt_builder.get_prompt(ExtractionType.SINGLE_ITEM_TEST)
        print(f"   📏 Single item prompt size: {len(single_item_prompt)} characters")
        
        # Test with primary provider
        result = await vision_client.analyze_images(
            image_data_list=item_data,
            prompt=single_item_prompt,
            use_fallback=True
        )
        
        if result.success:
            print(f"   ✅ Single item analysis successful!")
            print(f"   Provider: {result.provider}")
            print(f"   Confidence: {result.confidence:.2f}")
            print(f"   Cost: ${result.cost_estimate:.4f}")
            
            # Validate expected result
            items = result.data.get('items', [])
            if items:
                item = items[0]
                name = item.get('name', '').lower()
                if 'rough spool of thread' in name or 'spool' in name:
                    print(f"   ✅ VALIDATION PASSED: Found '{item.get('name')}' as expected")
                    validation_success = True
                else:
                    print(f"   ⚠️ VALIDATION WARNING: Expected 'Rough Spool of Thread' but found '{item.get('name')}'")
                    validation_success = False
                
                print(f"   📋 Extracted: {item.get('name')} (confidence: {item.get('confidence', 0):.2f})")
                if item.get('description'):
                    print(f"   📝 Description: {item.get('description')}")
                    
                return validation_success
            else:
                print(f"   ❌ No items extracted from single item test")
                return False
        else:
            print(f"   ❌ Single item analysis failed: {result.error_message}")
            return False
            
    except Exception as e:
        print(f"   💥 Single item test crashed: {str(e)}")
        return False

async def test_recipe_batch_analysis():
    """Test recipe-focused batch analysis: one recipe per batch."""
    print("BitCrafty Extractor - Recipe Batch Analysis Test")
    print("=" * 55)
    
    # Track results for each provider
    provider_results = {}
    
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
            ("OpenAI GPT-4V (gpt-4-turbo)", "openai", "gpt-4-turbo"),
            ("Anthropic Claude 3.5 Sonnet", "anthropic", "claude-3-5-sonnet-20241022"),
            ("Anthropic Claude 3 Haiku", "anthropic", "claude-3-haiku-20240307")
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
            
            # Create optimized prompt using new prompt system
            prompt_builder = PromptBuilder()
            optimized_prompt = prompt_builder.get_queue_analysis_prompt(
                screenshot_count=len(recipe_images),
                include_examples=True
            )
            print(f"   📏 Queue analysis prompt size: {len(optimized_prompt)} characters (55.7% smaller than original)")
            print(f"   🎯 Expected result: Weave Rough Cloth Strip recipe with materials and outputs")
            
            # Test with multiple providers and models
            for provider_name, provider_config, model_name in providers_to_test:
                print(f"\n" + "-"*60)
                print(f"🤖 Testing with {provider_name}")
                print(f"📋 Model: {model_name}")
                print("-"*60)
                
                # Initialize result tracking for this provider
                provider_results[provider_name] = {
                    'success': False,
                    'confidence': 0.0,
                    'cost': 0.0,
                    'time': 0.0,
                    'validation_passed': False,
                    'error': None
                }
                
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
                        prompt=optimized_prompt,
                        provider=provider,
                        use_fallback=False  # Don't use fallback for comparison
                    )
                    
                    if result.success:
                        print(f"   ✅ {provider_name} analysis successful!")
                        print(f"   Confidence: {result.confidence:.2f}")
                        print(f"   Cost: ${result.cost_estimate:.4f}")
                        print(f"   Processing time: {result.processing_time:.1f}s")
                        
                        # Store results
                        provider_results[provider_name].update({
                            'success': True,
                            'confidence': result.confidence,
                            'cost': result.cost_estimate,
                            'time': result.processing_time
                        })
                        
                        # Show structured results
                        validation_success = await display_provider_results(result.data, provider_name, recipe_batch['recipe_name'])
                        provider_results[provider_name]['validation_passed'] = validation_success
                        
                        if validation_success:
                            print(f"   ✅ Recipe validation passed for {provider_name}")
                        else:
                            print(f"   ⚠️ Recipe validation had issues for {provider_name}")
                        
                    else:
                        print(f"   ❌ {provider_name} analysis failed!")
                        if result.error_message:
                            print(f"   Error: {result.error_message}")
                            provider_results[provider_name]['error'] = result.error_message
                    
                    # Restore original model if we changed it
                    if provider_config == "openai" and original_openai_model:
                        config_manager.config.openai.model = original_openai_model
                        vision_client = VisionClient(logger, config_manager)
                            
                except Exception as e:
                    print(f"   💥 {provider_name} analysis crashed: {str(e)}")
                    provider_results[provider_name]['error'] = str(e)
                    
                    # Restore original model on error too
                    if provider_config == "openai" and 'original_openai_model' in locals() and original_openai_model:
                        config_manager.config.openai.model = original_openai_model
                        vision_client = VisionClient(logger, config_manager)
            
            # Add comparison table summary
            print(f"\n" + "="*80)
            print(f"📊 Provider Comparison Results - {recipe_batch['recipe_name']}")
            print("="*80)
            
            # Table header
            print(f"{'Provider':<25} {'Status':<8} {'Confidence':<11} {'Cost':<8} {'Time':<6} {'Validation':<10}")
            print("-" * 80)
            
            # Table rows
            for provider_name, results in provider_results.items():
                if results['success']:
                    status = "✅ PASS"
                    confidence = f"{results['confidence']:.2f}"
                    cost = f"${results['cost']:.4f}"
                    time = f"{results['time']:.1f}s"
                    validation = "✅ PASS" if results['validation_passed'] else "⚠️ FAIL"
                else:
                    status = "❌ FAIL"
                    confidence = "N/A"
                    cost = "N/A"
                    time = "N/A"
                    validation = "N/A"
                
                print(f"{provider_name:<25} {status:<8} {confidence:<11} {cost:<8} {time:<6} {validation:<10}")
            
            print("="*80)
        
        return True, provider_results
            
    except Exception as e:
        print(f"\n💥 Test crashed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, {}

async def display_provider_results(data: dict, provider_name: str, expected_recipe_name: str = None):
    """Display the extracted results from a specific provider."""
    
    if not data:
        print(f"   ❌ {provider_name}: No data extracted")
        return False
        
    print(f"   📊 {provider_name} Results:")
    
    # Show reasoning if available (not in optimized schema)
    reasoning = data.get('quantity_reasoning', 'Not provided with optimized prompts')
    if reasoning != 'Not provided with optimized prompts':
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
    
    validation_success = True
    
    for craft in crafts:
        name = craft.get('name', 'Unknown')
        confidence = craft.get('confidence', 0)
        print(f"      • {name} (confidence: {confidence:.2f})")
        
        # Validate recipe name if expected
        if expected_recipe_name:
            expected_lower = expected_recipe_name.lower()
            found_lower = name.lower()
            if expected_lower in found_lower or found_lower in expected_lower or 'cloth strip' in found_lower:
                print(f"        ✅ Recipe name validation: PASSED")
            else:
                print(f"        ⚠️ Recipe name validation: Expected '{expected_recipe_name}' but found '{name}'")
                validation_success = False
        
        # Focus on input quantities (updated field names)
        inputs = craft.get('materials', [])  # Changed from 'input_materials' to 'materials'
        if inputs:
            for inp in inputs:
                quantity = inp.get('qty', '?')  # Changed from 'quantity' to 'qty'
                item_name = inp.get('item', 'Unknown')  # Changed from 'item_name' to 'item'
                print(f"        Input: {quantity}x {item_name}")
                
                # Validate correct recipe: should be 1x Rough Spool of Thread for Weave Rough Cloth Strip
                if expected_recipe_name and 'cloth strip' in expected_recipe_name.lower():
                    if 'spool' in item_name.lower() or 'thread' in item_name.lower():
                        if str(quantity) != '1':
                            print(f"        ⚠️ Input quantity validation: Expected 1x Rough Spool of Thread but found {quantity}x")
                            validation_success = False
                        else:
                            print(f"        ✅ Input quantity validation: PASSED (1x Rough Spool of Thread)")
        else:
            print(f"        ⚠️ No input materials found")
            validation_success = False
        
        # Show outputs (updated field names)
        outputs = craft.get('outputs', [])  # Changed from 'output_materials' to 'outputs'
        if outputs:
            for out in outputs:
                quantity = out.get('qty', '?')  # Changed from 'quantity' to 'qty'
                item_name = out.get('item', 'Unknown')  # Changed from 'item_name' to 'item'
                print(f"        Output: {quantity}x {item_name}")
        else:
            print(f"        ⚠️ No output materials found")
            validation_success = False
    
    return validation_success

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
        
        # Input materials (updated field names)
        inputs = craft.get('materials', [])  # Changed from 'input_materials'
        if inputs:
            print(f"      Input Materials:")
            for inp in inputs:
                quantity = inp.get('qty', '?')  # Changed from 'quantity' to 'qty'
                item_name = inp.get('item', 'Unknown')  # Changed from 'item_name' to 'item'
                print(f"        {quantity}x {item_name}")
        
        # Output materials (updated field names)
        outputs = craft.get('outputs', [])  # Changed from 'output_materials'
        if outputs:
            print(f"      Output Materials:")
            for out in outputs:
                quantity = out.get('qty', '?')  # Changed from 'quantity' to 'qty'
                item_name = out.get('item', 'Unknown')  # Changed from 'item_name' to 'item'
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
    async def run_all_tests():
        """Run both single item and recipe batch analysis tests."""
        print("🧪 BitCrafty Extractor - Complete AI Analysis Test Suite")
        print("Using Optimized Prompts (55-73% size reduction)")
        print("=" * 70)
        
        # Test 1: Single Item Recognition
        print("\n" + "="*60)
        single_item_success = await test_single_item_recognition()
        
        # Test 2: Recipe Batch Analysis
        print("\n" + "="*60)
        recipe_batch_success, provider_results = await test_recipe_batch_analysis()
        
        # Provider comparison table only
        if provider_results:
            print("\n" + "="*80)
            print("🏆 Provider Performance Ranking:")
            print("-" * 80)
            print(f"{'Provider':<25} {'Status':<8} {'Confidence':<11} {'Cost':<8} {'Time':<6} {'Validation':<10}")
            print("-" * 80)
            
            # Sort by success, then by validation, then by cost
            sorted_providers = sorted(
                provider_results.items(),
                key=lambda x: (
                    not x[1]['success'],  # Failed providers last
                    not x[1]['validation_passed'],  # Invalid results last
                    x[1]['cost'] if x[1]['success'] else 999  # Sort by cost among valid results
                )
            )
            
            for provider_name, results in sorted_providers:
                if results['success']:
                    status = "✅ PASS"
                    confidence = f"{results['confidence']:.2f}"
                    cost = f"${results['cost']:.4f}"
                    time = f"{results['time']:.1f}s"
                    validation = "✅ PASS" if results['validation_passed'] else "⚠️ FAIL"
                else:
                    status = "❌ FAIL"
                    confidence = "N/A"
                    cost = "N/A"
                    time = "N/A"
                    validation = "N/A"
                
                print(f"{provider_name:<25} {status:<8} {confidence:<11} {cost:<8} {time:<6} {validation:<10}")
            
            print("="*80)
            
            # Find best provider (fastest among cheapest valid providers)
            valid_providers = [(name, results) for name, results in provider_results.items() 
                              if results['success'] and results['validation_passed']]
            if valid_providers:
                # Group by cost, then pick fastest in cheapest group
                valid_providers.sort(key=lambda x: (x[1]['cost'], x[1]['time']))
                best_provider = valid_providers[0]
                print(f"🏆 Best Provider: {best_provider[0]} (${best_provider[1]['cost']:.4f}, {best_provider[1]['time']:.1f}s)")
            else:
                print("⚠️ No providers passed all validation tests")
        
        overall_success = single_item_success and recipe_batch_success
        return overall_success
    
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
