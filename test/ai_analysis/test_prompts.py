#!/usr/bin/env python3
"""
Test the optimized prompts.py module for BitCraft AI analysis.

This test validates:
- All prompt types can be generated successfully
- Prompt size optimizations are working
- JSON schema validation
- Prompt content accuracy
- Performance improvements
"""

import sys
import json
import unittest
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from bitcrafty_extractor.ai_analysis.prompts import PromptBuilder, ExtractionType


class TestPromptBuilder(unittest.TestCase):
    """Test the PromptBuilder class and all extraction types."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.prompt_builder = PromptBuilder()
        
        # Expected prompt sizes (to ensure optimizations are maintained)
        self.expected_max_sizes = {
            "queue_full": 2100,     # ~2043 chars with examples
            "queue_compact": 1300,   # ~1228 chars without examples  
            "item_tooltip": 650,     # ~606 chars
            "craft_recipe": 1100,    # ~1054 chars
            "single_item": 700       # ~670 chars
        }
    
    def test_prompt_builder_initialization(self):
        """Test that PromptBuilder initializes correctly."""
        self.assertIsInstance(self.prompt_builder, PromptBuilder)
        self.assertIsNotNone(self.prompt_builder.base_context)
        self.assertIn("BitCraft", self.prompt_builder.base_context)
    
    def test_all_extraction_types_available(self):
        """Test that all expected extraction types are defined."""
        expected_types = {
            ExtractionType.QUEUE_ANALYSIS,
            ExtractionType.ITEM_TOOLTIP, 
            ExtractionType.CRAFT_RECIPE,
            ExtractionType.SINGLE_ITEM_TEST
        }
        
        available_types = set(ExtractionType)
        self.assertEqual(expected_types, available_types)
    
    def test_queue_analysis_prompt_generation(self):
        """Test queue analysis prompt generation with different parameters."""
        # Test with examples
        prompt_with_examples = self.prompt_builder.build_queue_analysis_prompt(
            screenshot_count=3, 
            include_examples=True
        )
        
        # Test without examples  
        prompt_without_examples = self.prompt_builder.build_queue_analysis_prompt(
            screenshot_count=3,
            include_examples=False
        )
        
        # Basic validations
        self.assertIsInstance(prompt_with_examples, str)
        self.assertIsInstance(prompt_without_examples, str)
        self.assertGreater(len(prompt_with_examples), len(prompt_without_examples))
        
        # Content validations
        self.assertIn("queue_analysis", prompt_with_examples)
        self.assertIn("screenshots_processed", prompt_with_examples)
        self.assertIn("items_found", prompt_with_examples)
        self.assertIn("crafts_found", prompt_with_examples)
        self.assertIn("EXAMPLE", prompt_with_examples)
        self.assertNotIn("EXAMPLE", prompt_without_examples)
        
        # Schema validations
        self.assertIn("materials", prompt_with_examples)
        self.assertIn("outputs", prompt_with_examples)
        self.assertIn("requirements", prompt_with_examples)
        self.assertIn("profession", prompt_with_examples)
        
        # Size optimization check
        self.assertLess(len(prompt_with_examples), self.expected_max_sizes["queue_full"])
        self.assertLess(len(prompt_without_examples), self.expected_max_sizes["queue_compact"])
    
    def test_item_tooltip_prompt_generation(self):
        """Test item tooltip prompt generation."""
        prompt_with_examples = self.prompt_builder.build_item_tooltip_prompt(include_examples=True)
        prompt_without_examples = self.prompt_builder.build_item_tooltip_prompt(include_examples=False)
        
        # Basic validations
        self.assertIsInstance(prompt_with_examples, str)
        self.assertIsInstance(prompt_without_examples, str)
        self.assertGreater(len(prompt_with_examples), len(prompt_without_examples))
        
        # Content validations
        self.assertIn("item tooltip", prompt_with_examples)
        self.assertIn("name", prompt_with_examples)
        self.assertIn("description", prompt_with_examples)
        self.assertIn("rarity", prompt_with_examples)
        self.assertIn("tier", prompt_with_examples)
        self.assertIn("EXAMPLE", prompt_with_examples)
        self.assertNotIn("EXAMPLE", prompt_without_examples)
        
        # Size optimization check
        self.assertLess(len(prompt_with_examples), self.expected_max_sizes["item_tooltip"])
    
    def test_craft_recipe_prompt_generation(self):
        """Test craft recipe prompt generation."""
        prompt_with_examples = self.prompt_builder.build_craft_recipe_prompt(include_examples=True)
        prompt_without_examples = self.prompt_builder.build_craft_recipe_prompt(include_examples=False)
        
        # Basic validations
        self.assertIsInstance(prompt_with_examples, str)
        self.assertIsInstance(prompt_without_examples, str)
        self.assertGreater(len(prompt_with_examples), len(prompt_without_examples))
        
        # Content validations
        self.assertIn("crafting recipe", prompt_with_examples)
        self.assertIn("materials", prompt_with_examples)
        self.assertIn("outputs", prompt_with_examples)
        self.assertIn("requirements", prompt_with_examples)
        self.assertIn("profession", prompt_with_examples)
        self.assertIn("EXAMPLE", prompt_with_examples)
        self.assertNotIn("EXAMPLE", prompt_without_examples)
        
        # Size optimization check
        self.assertLess(len(prompt_with_examples), self.expected_max_sizes["craft_recipe"])
    
    def test_single_item_test_prompt_generation(self):
        """Test single item test prompt generation."""
        prompt = self.prompt_builder.build_single_item_test_prompt()
        
        # Basic validations
        self.assertIsInstance(prompt, str)
        
        # Content validations
        self.assertIn("BitCraft", prompt)
        self.assertIn("items", prompt)
        self.assertIn("Rough Spool of Thread", prompt)
        self.assertIn("Rough Cloth Strip", prompt)
        
        # Size optimization check
        self.assertLess(len(prompt), self.expected_max_sizes["single_item"])
    
    def test_get_prompt_method(self):
        """Test the generic get_prompt method with all extraction types."""
        # Test queue analysis
        queue_prompt = self.prompt_builder.get_prompt(
            ExtractionType.QUEUE_ANALYSIS,
            screenshot_count=2,
            include_examples=True
        )
        self.assertIn("queue_analysis", queue_prompt)
        
        # Test item tooltip
        item_prompt = self.prompt_builder.get_prompt(
            ExtractionType.ITEM_TOOLTIP,
            include_examples=True
        )
        self.assertIn("item tooltip", item_prompt)
        
        # Test craft recipe
        craft_prompt = self.prompt_builder.get_prompt(
            ExtractionType.CRAFT_RECIPE,
            include_examples=True
        )
        self.assertIn("crafting recipe", craft_prompt)
        
        # Test single item test
        test_prompt = self.prompt_builder.get_prompt(ExtractionType.SINGLE_ITEM_TEST)
        self.assertIn("BitCraft", test_prompt)
        
        # Test invalid extraction type
        with self.assertRaises(ValueError):
            self.prompt_builder.get_prompt("invalid_type")
    
    def test_get_compact_prompt_method(self):
        """Test the get_compact_prompt method."""
        # Test queue analysis compact
        compact_queue = self.prompt_builder.get_compact_prompt(
            ExtractionType.QUEUE_ANALYSIS,
            screenshot_count=2
        )
        
        full_queue = self.prompt_builder.get_prompt(
            ExtractionType.QUEUE_ANALYSIS,
            screenshot_count=2,
            include_examples=True
        )
        
        self.assertLess(len(compact_queue), len(full_queue))
        self.assertNotIn("EXAMPLE", compact_queue)
        self.assertIn("EXAMPLE", full_queue)
    
    def test_convenience_methods(self):
        """Test the convenience methods."""
        # Test get_queue_analysis_prompt
        queue_prompt = self.prompt_builder.get_queue_analysis_prompt(
            screenshot_count=3,
            include_examples=True
        )
        self.assertIn("3 screenshot(s)", queue_prompt)
        self.assertIn("EXAMPLE", queue_prompt)
        
        # Test get_compact_queue_prompt
        compact_prompt = self.prompt_builder.get_compact_queue_prompt(screenshot_count=2)
        self.assertIn("2 screenshot(s)", compact_prompt)
        self.assertNotIn("EXAMPLE", compact_prompt)
    
    def test_json_schema_validity(self):
        """Test that example JSON in prompts is valid."""
        # Get queue analysis prompt with examples
        queue_prompt = self.prompt_builder.build_queue_analysis_prompt(
            screenshot_count=2,
            include_examples=True
        )
        
        # Extract JSON from example
        if "EXAMPLE:" in queue_prompt:
            example_start = queue_prompt.find("EXAMPLE:") + len("EXAMPLE:")
            example_end = queue_prompt.find("Return ONLY JSON")
            if example_end == -1:
                example_end = len(queue_prompt)
            
            example_text = queue_prompt[example_start:example_end].strip()
            
            # Find JSON block
            json_start = example_text.find("{")
            json_end = example_text.rfind("}") + 1
            
            if json_start != -1 and json_end > json_start:
                json_text = example_text[json_start:json_end]
                
                try:
                    parsed_json = json.loads(json_text)
                    self.assertIsInstance(parsed_json, dict)
                    
                    # Validate expected keys
                    self.assertIn("analysis_type", parsed_json)
                    self.assertIn("screenshots_processed", parsed_json)
                    self.assertIn("items_found", parsed_json)
                    self.assertIn("crafts_found", parsed_json)
                    self.assertIn("total_confidence", parsed_json)
                    
                except json.JSONDecodeError as e:
                    self.fail(f"Invalid JSON in example: {e}")
    
    def test_bitcraft_specific_content(self):
        """Test that prompts contain BitCraft-specific terminology."""
        all_prompts = [
            self.prompt_builder.get_queue_analysis_prompt(2),
            self.prompt_builder.get_prompt(ExtractionType.ITEM_TOOLTIP),
            self.prompt_builder.get_prompt(ExtractionType.CRAFT_RECIPE),
            self.prompt_builder.get_prompt(ExtractionType.SINGLE_ITEM_TEST)
        ]
        
        # Check for BitCraft-specific terms
        bitcraft_terms = [
            "BitCraft",
            "tailoring",
            "farming", 
            "cooking",
            "Rough Spool of Thread",
            "Rough Cloth Strip",
            "Wispweave"
        ]
        
        for prompt in all_prompts:
            has_bitcraft_content = any(term in prompt for term in bitcraft_terms)
            self.assertTrue(has_bitcraft_content, "Prompt should contain BitCraft-specific content")
    
    def test_data_format_alignment(self):
        """Test that prompts align with actual game data format."""
        queue_prompt = self.prompt_builder.get_queue_analysis_prompt(2)
        
        # Check for correct field names that match crafts.json
        self.assertIn('"item":', queue_prompt)  # Should use "item" not "item_name"
        self.assertIn('"qty":', queue_prompt)   # Should use "qty" not "quantity"
        self.assertIn("materials", queue_prompt)
        self.assertIn("outputs", queue_prompt)
        self.assertIn("requirements", queue_prompt)
        self.assertIn("profession", queue_prompt)
        self.assertIn("building", queue_prompt)
        self.assertIn("tool", queue_prompt)
    
    def test_size_optimizations(self):
        """Test that size optimizations are working as expected."""
        # Get actual sizes
        queue_full = len(self.prompt_builder.get_queue_analysis_prompt(3, True))
        queue_compact = len(self.prompt_builder.get_compact_queue_prompt(3))
        item_prompt = len(self.prompt_builder.get_prompt(ExtractionType.ITEM_TOOLTIP))
        craft_prompt = len(self.prompt_builder.get_prompt(ExtractionType.CRAFT_RECIPE))
        test_prompt = len(self.prompt_builder.get_prompt(ExtractionType.SINGLE_ITEM_TEST))
        
        # Validate size optimizations
        self.assertLess(queue_full, self.expected_max_sizes["queue_full"],
                       f"Queue full prompt too large: {queue_full} > {self.expected_max_sizes['queue_full']}")
        self.assertLess(queue_compact, self.expected_max_sizes["queue_compact"],
                       f"Queue compact prompt too large: {queue_compact} > {self.expected_max_sizes['queue_compact']}")
        self.assertLess(item_prompt, self.expected_max_sizes["item_tooltip"],
                       f"Item prompt too large: {item_prompt} > {self.expected_max_sizes['item_tooltip']}")
        self.assertLess(craft_prompt, self.expected_max_sizes["craft_recipe"],
                       f"Craft prompt too large: {craft_prompt} > {self.expected_max_sizes['craft_recipe']}")
        self.assertLess(test_prompt, self.expected_max_sizes["single_item"],
                       f"Test prompt too large: {test_prompt} > {self.expected_max_sizes['single_item']}")
        
        # Validate that compact is significantly smaller than full
        size_reduction = (queue_full - queue_compact) / queue_full
        self.assertGreater(size_reduction, 0.3, "Compact prompt should be at least 30% smaller")


class TestPromptPerformance(unittest.TestCase):
    """Test prompt generation performance."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.prompt_builder = PromptBuilder()
    
    def test_prompt_generation_speed(self):
        """Test that prompt generation is fast."""
        import time
        
        start_time = time.time()
        
        # Generate multiple prompts
        for i in range(100):
            self.prompt_builder.get_queue_analysis_prompt(i % 5 + 1)
            self.prompt_builder.get_prompt(ExtractionType.ITEM_TOOLTIP)
            self.prompt_builder.get_prompt(ExtractionType.CRAFT_RECIPE)
            self.prompt_builder.get_prompt(ExtractionType.SINGLE_ITEM_TEST)
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        # Should generate 400 prompts in under 1 second
        self.assertLess(generation_time, 1.0, f"Prompt generation too slow: {generation_time:.2f}s")


def run_prompt_validation_tests():
    """Run all prompt validation tests and display results."""
    print("🧪 BitCrafty-Extractor Prompt Validation Tests")
    print("=" * 55)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all test cases
    test_suite.addTest(unittest.makeSuite(TestPromptBuilder))
    test_suite.addTest(unittest.makeSuite(TestPromptPerformance))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(test_suite)
    
    # Display summary
    print("\n" + "=" * 55)
    print("📊 Test Results Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback}")
    
    if result.errors:
        print("\n💥 Errors:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n✅ All prompt validation tests passed!")
        
        # Display optimization metrics
        pb = PromptBuilder()
        print("\n📈 Prompt Size Metrics:")
        print(f"   Queue (full): {len(pb.get_queue_analysis_prompt(3, True))} chars")
        print(f"   Queue (compact): {len(pb.get_compact_queue_prompt(3))} chars")
        print(f"   Item tooltip: {len(pb.get_prompt(ExtractionType.ITEM_TOOLTIP))} chars")
        print(f"   Craft recipe: {len(pb.get_prompt(ExtractionType.CRAFT_RECIPE))} chars")
        print(f"   Single item: {len(pb.get_prompt(ExtractionType.SINGLE_ITEM_TEST))} chars")
        
        return True
    else:
        print("\n❌ Some tests failed!")
        return False


if __name__ == "__main__":
    success = run_prompt_validation_tests()
    sys.exit(0 if success else 1)
