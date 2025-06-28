#!/usr/bin/env python3
"""
Test AI provider comparison with unit test framework.

Usage:
    python test_provider_comparison.py           # Run as unit test (minimal output)
    python test_provider_comparison.py -verbose  # Run with detailed output
"""

import sys
import asyncio
import unittest
import argparse
import numpy as np
import cv2
import logging
from pathlib import Path

# Set up verbose mode detection early
VERBOSE_MODE = "-verbose" in sys.argv or "-v" in sys.argv

# Configure logging based on mode
if VERBOSE_MODE:
    # Verbose mode: Show all logs including debug and info from all components
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)-8s] %(name)s: %(message)s')
    print("🧪 BitCrafty-Extractor Provider Comparison Tests")
    print("=" * 55)
else:
    # Standard mode: Only show warnings, errors, and critical messages
    logging.basicConfig(level=logging.ERROR, format='%(asctime)s [%(levelname)-8s] %(message)s')
    # Disable info and debug logs completely
    logging.disable(logging.WARNING)

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from bitcrafty_extractor.config.config_manager import ConfigManager
from bitcrafty_extractor.ai_analysis.vision_client import VisionClient, ImageData, AIProvider
from bitcrafty_extractor.ai_analysis.prompts import PromptBuilder, ExtractionType

class TestProviderComparison(unittest.TestCase):
    """Test AI provider comparison with different models and configurations."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures for the entire class."""
        # Configure structlog to respect standard library logging levels
        import structlog
        
        if not VERBOSE_MODE:
            # Create a logger that respects the WARNING+ level we set
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.format_exc_info,
                    structlog.dev.ConsoleRenderer()
                ],
                wrapper_class=structlog.stdlib.BoundLogger,
                logger_factory=structlog.stdlib.LoggerFactory(),
                cache_logger_on_first_use=True,
            )
            # Set the root logger to WARNING level to suppress info/debug
            logging.getLogger().setLevel(logging.WARNING)
        
        # Now create components with suppressed logging
        cls.logger = structlog.get_logger(__name__)
        cls.config_manager = ConfigManager(logger=cls.logger)
        
        cls.vision_client = VisionClient(cls.logger, cls.config_manager)
        cls.prompt_builder = PromptBuilder()
        cls.provider_results = {}
        
        # Load test images
        cls.test_data_path = Path(__file__).parent.parent / "test_data"
        cls._load_test_images()
        
        if VERBOSE_MODE:
            print("🔧 Test setup complete")
    
    @classmethod
    def _load_test_images(cls):
        """Load test images for analysis."""
        cls.item_images = []
        cls.craft_images = []
        
        # Load single item test image
        item_folder = cls.test_data_path / "item"
        item_img_path = item_folder / "rough-spool-of-thread.png"
        
        if item_img_path.exists():
            image = cv2.imread(str(item_img_path))
            if image is not None:
                cls.item_images.append(ImageData(image_array=image))
                if VERBOSE_MODE:
                    print(f"   ✅ Loaded item: {item_img_path.name} ({image.shape})")
        
        # Load craft recipe images
        craft_folder = cls.test_data_path / "craft"
        craft_files = [
            "weave_rough_cloth_strip_input.png",
            "weave_rough_cloth_strip.png", 
            "weave_rough_cloth_output.png"
        ]
        
        for screenshot in craft_files:
            img_path = craft_folder / screenshot
            if img_path.exists():
                image = cv2.imread(str(img_path))
                if image is not None:
                    cls.craft_images.append(ImageData(image_array=image))
                    if VERBOSE_MODE:
                        print(f"   ✅ Loaded craft: {screenshot} ({image.shape})")
    
    def test_single_item_recognition(self):
        """Test single item recognition with optimized prompts."""
        if not VERBOSE_MODE:
            print("🎯 Testing Single Item Recognition... ", end="", flush=True)
        
        if VERBOSE_MODE:
            print("\n🎯 Testing Single Item Recognition")
            print("-" * 40)
        
        if not self.item_images:
            if not VERBOSE_MODE:
                print("SKIPPED (no test images)")
            self.skipTest("No item test images available")
        
        # Test single item prompt
        single_item_prompt = self.prompt_builder.get_prompt(ExtractionType.SINGLE_ITEM_TEST)
        
        # Run async test
        result = asyncio.run(self._analyze_with_provider(
            self.item_images,
            single_item_prompt,
            "single_item",
            expected_item="Rough Spool of Thread"
        ))
        
        self.assertTrue(result['success'], "Single item recognition should succeed")
        self.assertGreater(result['confidence'], 0.5, "Should have reasonable confidence")
        
        if not VERBOSE_MODE:
            print("PASSED")
        
        if VERBOSE_MODE:
            print(f"   ✅ Single item test passed (confidence: {result['confidence']:.2f})")
    
    def test_openai_gpt4o_analysis(self):
        """Test OpenAI GPT-4o analysis."""
        provider_name = "OpenAI GPT-4o"
        
        if not VERBOSE_MODE:
            print(f"🤖 Testing {provider_name}... ", end="", flush=True)
        
        if not self.craft_images:
            if not VERBOSE_MODE:
                print("SKIPPED (no test images)")
            self.skipTest("No craft test images available")
        
        result = asyncio.run(self._test_provider_analysis(
            provider_name, AIProvider.OPENAI_GPT4V, "gpt-4o"
        ))
        
        self.assertTrue(result['success'], f"{provider_name} should succeed")
        if result['success']:
            self.assertGreater(result['confidence'], 0.0, "Should have valid confidence")
            self.provider_results[provider_name] = result
        
        if not VERBOSE_MODE:
            status = "PASSED" if result['success'] else "FAILED"
            #print(status)
    
    def test_openai_gpt4_turbo_analysis(self):
        """Test OpenAI GPT-4 Turbo analysis."""
        provider_name = "OpenAI GPT-4 Turbo"
        
        if not VERBOSE_MODE:
            print(f"🤖 Testing {provider_name}... ", end="", flush=True)
        
        if not self.craft_images:
            if not VERBOSE_MODE:
                print("SKIPPED (no test images)")
            self.skipTest("No craft test images available")
        
        result = asyncio.run(self._test_provider_analysis(
            provider_name, AIProvider.OPENAI_GPT4V, "gpt-4-turbo"
        ))
        
        self.assertTrue(result['success'], f"{provider_name} should succeed")
        if result['success']:
            self.assertGreater(result['confidence'], 0.0, "Should have valid confidence")
            self.provider_results[provider_name] = result
        
        if not VERBOSE_MODE:
            status = "PASSED" if result['success'] else "FAILED"
            print(status)
    
    def test_anthropic_claude_sonnet_analysis(self):
        """Test Anthropic Claude 3.5 Sonnet analysis."""
        provider_name = "Anthropic Claude 3.5 Sonnet"
        
        if not VERBOSE_MODE:
            print(f"🤖 Testing {provider_name}... ", end="", flush=True)
        
        if not self.craft_images:
            if not VERBOSE_MODE:
                print("SKIPPED (no test images)")
            self.skipTest("No craft test images available")
        
        result = asyncio.run(self._test_provider_analysis(
            provider_name, AIProvider.ANTHROPIC_CLAUDE, "claude-3-5-sonnet-20241022"
        ))
        
        self.assertTrue(result['success'], f"{provider_name} should succeed")
        if result['success']:
            self.assertGreater(result['confidence'], 0.0, "Should have valid confidence")
            self.provider_results[provider_name] = result
        
        if not VERBOSE_MODE:
            status = "PASSED" if result['success'] else "FAILED"
            print(status)
    
    def test_anthropic_claude_haiku_analysis(self):
        """Test Anthropic Claude 3 Haiku analysis."""
        provider_name = "Anthropic Claude 3 Haiku"
        
        if not VERBOSE_MODE:
            print(f"🤖 Testing {provider_name}... ", end="", flush=True)
        
        if not self.craft_images:
            if not VERBOSE_MODE:
                print("SKIPPED (no test images)")
            self.skipTest("No craft test images available")
        
        result = asyncio.run(self._test_provider_analysis(
            provider_name, AIProvider.ANTHROPIC_CLAUDE, "claude-3-haiku-20240307"
        ))
        
        self.assertTrue(result['success'], f"{provider_name} should succeed")
        if result['success']:
            self.assertGreater(result['confidence'], 0.0, "Should have valid confidence")
            self.provider_results[provider_name] = result
        
        if not VERBOSE_MODE:
            status = "PASSED" if result['success'] else "FAILED"
            print(status)
    
    async def _test_provider_analysis(self, provider_name, provider_type, model_name):
        """Test analysis with a specific provider and model."""
        if VERBOSE_MODE:
            print(f"\n🤖 Testing {provider_name}")
            print(f"📋 Model: {model_name}")
        
        # Create optimized prompt
        prompt = self.prompt_builder.get_queue_analysis_prompt(
            screenshot_count=len(self.craft_images),
            include_examples=True
        )
        
        if VERBOSE_MODE:
            print(f"📏 Prompt size: {len(prompt)} characters")
        
        try:
            # Configure specific model
            original_model = None
            if provider_type == AIProvider.OPENAI_GPT4V and self.config_manager.config.openai:
                original_model = self.config_manager.config.openai.model
                self.config_manager.config.openai.model = model_name
                self.vision_client = VisionClient(self.logger, self.config_manager)
            elif provider_type == AIProvider.ANTHROPIC_CLAUDE and self.config_manager.config.anthropic:
                original_model = self.config_manager.config.anthropic.model
                self.config_manager.config.anthropic.model = model_name
                self.vision_client = VisionClient(self.logger, self.config_manager)
            
            # Run analysis
            result = await self.vision_client.analyze_images(
                image_data_list=self.craft_images,
                prompt=prompt,
                provider=provider_type,
                use_fallback=False
            )
            
            # Restore original model
            if original_model:
                if provider_type == AIProvider.OPENAI_GPT4V:
                    self.config_manager.config.openai.model = original_model
                else:
                    self.config_manager.config.anthropic.model = original_model
                self.vision_client = VisionClient(self.logger, self.config_manager)
            
            if result.success:
                validation_passed = self._validate_craft_result(
                    result.data, "Weave Rough Cloth Strip", provider_name
                )
                
                return {
                    'success': True,
                    'confidence': result.confidence,
                    'cost': result.cost_estimate,
                    'time': result.processing_time,
                    'validation_passed': validation_passed,
                    'error': None
                }
            else:
                if VERBOSE_MODE:
                    print(f"   ❌ Analysis failed: {result.error_message}")
                return {
                    'success': False,
                    'confidence': 0.0,
                    'cost': 0.0,
                    'time': 0.0,
                    'validation_passed': False,
                    'error': result.error_message
                }
                
        except Exception as e:
            if VERBOSE_MODE:
                print(f"   💥 Analysis crashed: {str(e)}")
            return {
                'success': False,
                'confidence': 0.0,
                'cost': 0.0,
                'time': 0.0,
                'validation_passed': False,
                'error': str(e)
            }
    
    def _validate_craft_result(self, data, expected_recipe_name, provider_name):
        """Validate the extracted craft result."""
        if not data:
            if VERBOSE_MODE:
                print(f"   ❌ No data extracted")
            return False
        
        crafts = data.get('crafts_found', [])
        if not crafts:
            if VERBOSE_MODE:
                print(f"   ❌ No crafts found")
            return False
        
        craft = crafts[0]
        name = craft.get('name', '')
        
        # Check recipe name
        expected_lower = expected_recipe_name.lower()
        found_lower = name.lower()
        name_valid = (expected_lower in found_lower or 
                     found_lower in expected_lower or 
                     'cloth strip' in found_lower)
        
        # Check materials
        materials = craft.get('materials', [])
        materials_valid = len(materials) > 0
        
        # Check outputs
        outputs = craft.get('outputs', [])
        outputs_valid = len(outputs) > 0
        
        validation_passed = name_valid and materials_valid and outputs_valid
        
        if VERBOSE_MODE:
            print(f"   📊 {provider_name} Results:")
            print(f"      Recipe: {name} ({'✅' if name_valid else '❌'})")
            print(f"      Materials: {len(materials)} ({'✅' if materials_valid else '❌'})")
            print(f"      Outputs: {len(outputs)} ({'✅' if outputs_valid else '❌'})")
            print(f"      Confidence: {craft.get('confidence', 0):.2f}")
            if validation_passed:
                print(f"   ✅ Validation passed")
            else:
                print(f"   ⚠️ Validation failed")
        
        return validation_passed
    
    async def _analyze_with_provider(self, images, prompt, test_type, expected_item=None):
        """Generic analysis method for different test types."""
        try:
            result = await self.vision_client.analyze_images(
                image_data_list=images,
                prompt=prompt,
                use_fallback=True
            )
            
            if result.success:
                validation_passed = True
                if test_type == "single_item" and expected_item:
                    items = result.data.get('items', [])
                    if items:
                        item_name = items[0].get('name', '').lower()
                        expected_lower = expected_item.lower()
                        validation_passed = expected_lower in item_name or 'spool' in item_name
                    else:
                        validation_passed = False
                
                if VERBOSE_MODE and not validation_passed:
                    print(f"   ⚠️ Validation failed for {test_type}")
                
                return {
                    'success': True,
                    'confidence': result.confidence,
                    'cost': result.cost_estimate,
                    'time': result.processing_time,
                    'validation_passed': validation_passed
                }
            else:
                return {'success': False, 'confidence': 0.0, 'validation_passed': False}
                
        except Exception as e:
            if VERBOSE_MODE:
                print(f"   � {test_type} test crashed: {str(e)}")
            return {'success': False, 'confidence': 0.0, 'validation_passed': False}
    
    @classmethod
    def tearDownClass(cls):
        """Display provider comparison results after all tests."""
        if cls.provider_results:
            print("\n" + "="*80)
            print("🏆 Provider Performance Ranking")
            print("="*80)
            print(f"{'Provider':<25} {'Status':<8} {'Confidence':<11} {'Cost':<8} {'Time':<6} {'Validation':<10}")
            print("-" * 80)
            
            # Sort by success, validation, then cost
            sorted_providers = sorted(
                cls.provider_results.items(),
                key=lambda x: (
                    not x[1]['success'],
                    not x[1]['validation_passed'],
                    x[1]['cost'] if x[1]['success'] else 999
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
            
            # Find best provider
            valid_providers = [(name, results) for name, results in cls.provider_results.items() 
                              if results['success'] and results['validation_passed']]
            if valid_providers:
                valid_providers.sort(key=lambda x: (x[1]['cost'], x[1]['time']))
                best_provider = valid_providers[0]
                print(f"🏆 Best Provider: {best_provider[0]} (${best_provider[1]['cost']:.4f}, {best_provider[1]['time']:.1f}s)")
            else:
                print("⚠️ No providers passed all validation tests")
            print()


def run_provider_comparison_tests():
    """Run provider comparison tests and display results."""
    # Configure logging early for non-verbose mode
    if not VERBOSE_MODE:
        # Suppress all logging below WARNING level
        logging.getLogger().setLevel(logging.WARNING)
        # Also suppress specific loggers that might be noisy
        logging.getLogger('bitcrafty_extractor').setLevel(logging.WARNING)
        logging.getLogger('anthropic').setLevel(logging.WARNING)
        logging.getLogger('openai').setLevel(logging.WARNING)
    
    if VERBOSE_MODE:
        print("🧪 BitCrafty-Extractor Provider Comparison Tests")
        print("=" * 55)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    test_suite.addTests(loader.loadTestsFromTestCase(TestProviderComparison))
    
    # Run tests
    verbosity = 2 if VERBOSE_MODE else 1
    runner = unittest.TextTestRunner(verbosity=verbosity, stream=sys.stdout)
    result = runner.run(test_suite)
    
    if not VERBOSE_MODE:
        # Show summary for non-verbose mode
        print(f"\n📊 Test Results Summary:")
        print(f"   Tests run: {result.testsRun}")
        print(f"   Failures: {len(result.failures)}")
        print(f"   Errors: {len(result.errors)}")
        
        if result.failures:
            print("\n❌ Failures:")
            for test, traceback in result.failures:
                print(f"   - {test}")
        
        if result.errors:
            print("\n💥 Errors:")
            for test, traceback in result.errors:
                print(f"   - {test}")
    
    success = result.wasSuccessful()
    if success:
        if VERBOSE_MODE:
            print("\n✅ All provider comparison tests passed!")
        return True
    else:
        if VERBOSE_MODE:
            print("\n❌ Some tests failed!")
        return False

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test AI provider comparison')
    parser.add_argument('-verbose', '--verbose', action='store_true', 
                       help='Show detailed output during tests')
    args = parser.parse_args()
    
    # Set global verbose flag
    VERBOSE_MODE = args.verbose
    
    # Configure logging early if not in verbose mode
    if not VERBOSE_MODE:
        logging.getLogger().setLevel(logging.WARNING)
        logging.getLogger('bitcrafty_extractor').setLevel(logging.WARNING)
    
    # Run tests
    success = run_provider_comparison_tests()
    sys.exit(0 if success else 1)
