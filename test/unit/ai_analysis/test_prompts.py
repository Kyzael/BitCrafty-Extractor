"""Test the optimized prompts.py module for BitCraft AI analysis using pytest framework."""

import pytest
import json
import time
from pathlib import Path
import sys

# Add src to path
src_path = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

try:
    from bitcrafty_extractor.ai_analysis.prompts import PromptBuilder, ExtractionType
except ImportError as e:
    pytest.skip(f"Prompt modules not available: {e}", allow_module_level=True)


@pytest.fixture
def prompt_builder():
    """Create a PromptBuilder instance for testing."""
    return PromptBuilder()


@pytest.fixture
def expected_max_sizes():
    """Expected maximum prompt sizes (updated for quantity formatting improvements July 2025)."""
    return {
        "queue_full": 4500,     # ~4466 chars with quantity formatting rules and examples  
        "queue_compact": 3200,   # ~3000 chars without examples but with validation
        "item_tooltip": 900,     # ~816 chars with validation instructions
        "craft_recipe": 1500,    # ~1364 chars with validation requirements
        "single_item": 750       # ~670 chars (minimal changes)
    }


@pytest.mark.ai_analysis
@pytest.mark.unit
class TestPromptBuilder:
    """Test the PromptBuilder class and all extraction types."""

    def test_prompt_builder_initialization(self, prompt_builder):
        """Test that PromptBuilder initializes correctly."""
        assert isinstance(prompt_builder, PromptBuilder)
        assert prompt_builder.base_context is not None
        assert "BitCraft" in prompt_builder.base_context

    def test_all_extraction_types_available(self):
        """Test that all expected extraction types are defined."""
        expected_types = {
            ExtractionType.QUEUE_ANALYSIS,
            ExtractionType.ITEM_TOOLTIP, 
            ExtractionType.CRAFT_RECIPE,
            ExtractionType.SINGLE_ITEM_TEST
        }
        
        available_types = set(ExtractionType)
        assert expected_types == available_types

    def test_queue_analysis_prompt_generation(self, prompt_builder, expected_max_sizes):
        """Test queue analysis prompt generation with different parameters."""
        # Test with examples
        prompt_with_examples = prompt_builder.build_queue_analysis_prompt(
            screenshot_count=3, 
            include_examples=True
        )
        
        # Test without examples  
        prompt_without_examples = prompt_builder.build_queue_analysis_prompt(
            screenshot_count=3,
            include_examples=False
        )
        
        # Basic validations
        assert isinstance(prompt_with_examples, str)
        assert isinstance(prompt_without_examples, str)
        assert len(prompt_with_examples) > len(prompt_without_examples)
        
        # Content validations
        assert "queue_analysis" in prompt_with_examples
        assert "screenshots_processed" in prompt_with_examples
        assert "items_found" in prompt_with_examples
        assert "crafts_found" in prompt_with_examples
        assert "EXAMPLE" in prompt_with_examples
        assert "EXAMPLE" not in prompt_without_examples
        
        # Schema validations
        assert "materials" in prompt_with_examples
        assert "outputs" in prompt_with_examples
        assert "requirements" in prompt_with_examples
        assert "profession" in prompt_with_examples
        
        # Size optimization check
        assert len(prompt_with_examples) < expected_max_sizes["queue_full"]
        assert len(prompt_without_examples) < expected_max_sizes["queue_compact"]

    def test_item_tooltip_prompt_generation(self, prompt_builder, expected_max_sizes):
        """Test item tooltip prompt generation."""
        prompt_with_examples = prompt_builder.build_item_tooltip_prompt(include_examples=True)
        prompt_without_examples = prompt_builder.build_item_tooltip_prompt(include_examples=False)
        
        # Basic validations
        assert isinstance(prompt_with_examples, str)
        assert isinstance(prompt_without_examples, str)
        assert len(prompt_with_examples) > len(prompt_without_examples)
        
        # Content validations
        assert "item tooltip" in prompt_with_examples
        assert "name" in prompt_with_examples
        assert "description" in prompt_with_examples
        assert "rarity" in prompt_with_examples
        assert "tier" in prompt_with_examples
        assert "EXAMPLE" in prompt_with_examples
        assert "EXAMPLE" not in prompt_without_examples
        
        # Size optimization check
        assert len(prompt_with_examples) < expected_max_sizes["item_tooltip"]

    def test_craft_recipe_prompt_generation(self, prompt_builder, expected_max_sizes):
        """Test craft recipe prompt generation."""
        prompt_with_examples = prompt_builder.build_craft_recipe_prompt(include_examples=True)
        prompt_without_examples = prompt_builder.build_craft_recipe_prompt(include_examples=False)
        
        # Basic validations
        assert isinstance(prompt_with_examples, str)
        assert isinstance(prompt_without_examples, str)
        assert len(prompt_with_examples) > len(prompt_without_examples)
        
        # Content validations
        assert "crafting recipe" in prompt_with_examples
        assert "materials" in prompt_with_examples
        assert "outputs" in prompt_with_examples
        assert "requirements" in prompt_with_examples
        assert "profession" in prompt_with_examples
        assert "EXAMPLE" in prompt_with_examples
        assert "EXAMPLE" not in prompt_without_examples
        
        # Size optimization check
        assert len(prompt_with_examples) < expected_max_sizes["craft_recipe"]

    def test_single_item_test_prompt_generation(self, prompt_builder, expected_max_sizes):
        """Test single item test prompt generation."""
        prompt = prompt_builder.build_single_item_test_prompt()
        
        # Basic validations
        assert isinstance(prompt, str)
        
        # Content validations
        assert "BitCraft" in prompt
        assert "items" in prompt
        assert "Rough Spool of Thread" in prompt
        assert "Rough Cloth Strip" in prompt
        
        # Size optimization check
        assert len(prompt) < expected_max_sizes["single_item"]

    def test_get_prompt_method(self, prompt_builder):
        """Test the generic get_prompt method with all extraction types."""
        # Test queue analysis
        queue_prompt = prompt_builder.get_prompt(
            ExtractionType.QUEUE_ANALYSIS,
            screenshot_count=2,
            include_examples=True
        )
        assert "queue_analysis" in queue_prompt
        
        # Test item tooltip
        item_prompt = prompt_builder.get_prompt(
            ExtractionType.ITEM_TOOLTIP,
            include_examples=True
        )
        assert "item tooltip" in item_prompt
        
        # Test craft recipe
        craft_prompt = prompt_builder.get_prompt(
            ExtractionType.CRAFT_RECIPE,
            include_examples=True
        )
        assert "crafting recipe" in craft_prompt
        
        # Test single item test
        test_prompt = prompt_builder.get_prompt(ExtractionType.SINGLE_ITEM_TEST)
        assert "BitCraft" in test_prompt
        
        # Test invalid extraction type
        with pytest.raises(ValueError):
            prompt_builder.get_prompt("invalid_type")

    def test_get_compact_prompt_method(self, prompt_builder):
        """Test the get_compact_prompt method."""
        # Test queue analysis compact
        compact_queue = prompt_builder.get_compact_prompt(
            ExtractionType.QUEUE_ANALYSIS,
            screenshot_count=2
        )
        
        full_queue = prompt_builder.get_prompt(
            ExtractionType.QUEUE_ANALYSIS,
            screenshot_count=2,
            include_examples=True
        )
        
        assert len(compact_queue) < len(full_queue)
        assert "EXAMPLE" not in compact_queue
        assert "EXAMPLE" in full_queue

    def test_convenience_methods(self, prompt_builder):
        """Test the convenience methods."""
        # Test get_queue_analysis_prompt
        queue_prompt = prompt_builder.get_queue_analysis_prompt(
            screenshot_count=3,
            include_examples=True
        )
        assert "3 screenshot(s)" in queue_prompt
        assert "EXAMPLE" in queue_prompt
        
        # Test get_compact_queue_prompt
        compact_prompt = prompt_builder.get_compact_queue_prompt(screenshot_count=2)
        assert "2 screenshot(s)" in compact_prompt
        assert "EXAMPLE" not in compact_prompt

    def test_json_schema_validity(self, prompt_builder):
        """Test that example JSON in prompts is valid."""
        # Get queue analysis prompt with examples
        queue_prompt = prompt_builder.build_queue_analysis_prompt(
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
                    assert isinstance(parsed_json, dict)
                    
                    # Validate expected keys
                    assert "analysis_type" in parsed_json
                    assert "screenshots_processed" in parsed_json
                    assert "items_found" in parsed_json
                    assert "crafts_found" in parsed_json
                    assert "total_confidence" in parsed_json
                    
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON in example: {e}")

    def test_bitcraft_specific_content(self, prompt_builder):
        """Test that prompts contain BitCraft-specific terminology."""
        all_prompts = [
            prompt_builder.get_queue_analysis_prompt(2),
            prompt_builder.get_prompt(ExtractionType.ITEM_TOOLTIP),
            prompt_builder.get_prompt(ExtractionType.CRAFT_RECIPE),
            prompt_builder.get_prompt(ExtractionType.SINGLE_ITEM_TEST)
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
            assert has_bitcraft_content, "Prompt should contain BitCraft-specific content"

    def test_data_format_alignment(self, prompt_builder):
        """Test that prompts align with actual game data format."""
        queue_prompt = prompt_builder.get_queue_analysis_prompt(2)
        
        # Check for correct field names that match crafts.json
        assert '"item":' in queue_prompt  # Should use "item" not "item_name"
        assert '"qty":' in queue_prompt   # Should use "qty" not "quantity"
        assert "materials" in queue_prompt
        assert "outputs" in queue_prompt
        assert "requirements" in queue_prompt
        assert "profession" in queue_prompt
        assert "building" in queue_prompt
        assert "tool" in queue_prompt

    def test_size_optimizations(self, prompt_builder, expected_max_sizes):
        """Test that size optimizations are working as expected."""
        # Get actual sizes
        queue_full = len(prompt_builder.get_queue_analysis_prompt(3, True))
        queue_compact = len(prompt_builder.get_compact_queue_prompt(3))
        item_prompt = len(prompt_builder.get_prompt(ExtractionType.ITEM_TOOLTIP))
        craft_prompt = len(prompt_builder.get_prompt(ExtractionType.CRAFT_RECIPE))
        test_prompt = len(prompt_builder.get_prompt(ExtractionType.SINGLE_ITEM_TEST))
        
        # Validate size optimizations
        assert queue_full < expected_max_sizes["queue_full"], \
            f"Queue full prompt too large: {queue_full} > {expected_max_sizes['queue_full']}"
        assert queue_compact < expected_max_sizes["queue_compact"], \
            f"Queue compact prompt too large: {queue_compact} > {expected_max_sizes['queue_compact']}"
        assert item_prompt < expected_max_sizes["item_tooltip"], \
            f"Item prompt too large: {item_prompt} > {expected_max_sizes['item_tooltip']}"
        assert craft_prompt < expected_max_sizes["craft_recipe"], \
            f"Craft prompt too large: {craft_prompt} > {expected_max_sizes['craft_recipe']}"
        assert test_prompt < expected_max_sizes["single_item"], \
            f"Test prompt too large: {test_prompt} > {expected_max_sizes['single_item']}"
        
        # Validate that compact is significantly smaller than full
        size_reduction = (queue_full - queue_compact) / queue_full
        assert size_reduction > 0.2, "Compact prompt should be at least 20% smaller"

    def test_validation_rules_present(self, prompt_builder):
        """Test that our validation improvements are present in prompts."""
        # Queue analysis should have craft validation rules
        queue_prompt = prompt_builder.get_queue_analysis_prompt(2, True)
        
        # Check for validation rules
        assert "CRITICAL CRAFTING RECIPE VALIDATION RULES" in queue_prompt
        assert "ONLY extract crafts_found if you see an ACTUAL CRAFTING INTERFACE" in queue_prompt
        assert "Do NOT extract crafts for simple item tooltips" in queue_prompt
        assert "materials list, profession requirement" in queue_prompt
        assert "VALID CRAFT INDICATORS" in queue_prompt
        assert "INVALID CRAFT INDICATORS" in queue_prompt
        
        # Item tooltip should have explicit instructions against crafts
        item_prompt = prompt_builder.get_prompt(ExtractionType.ITEM_TOOLTIP)
        assert "ITEM INFORMATION ONLY" in item_prompt
        assert "do NOT extract crafting recipes" in item_prompt
        assert "Focus only on the item itself" in item_prompt
        
        # Craft recipe should have validation requirements
        craft_prompt = prompt_builder.get_prompt(ExtractionType.CRAFT_RECIPE)
        assert "ACTIVE CRAFTING INTERFACE" in craft_prompt
        assert "VALIDATION REQUIREMENTS" in craft_prompt
        assert "clear materials list with quantities" in craft_prompt
        assert "profession, tool, or building requirements" in craft_prompt


@pytest.mark.ai_analysis
@pytest.mark.unit
@pytest.mark.parametrize("extraction_type,expected_content", [
    (ExtractionType.QUEUE_ANALYSIS, "queue_analysis"),
    (ExtractionType.ITEM_TOOLTIP, "item tooltip"),
    (ExtractionType.CRAFT_RECIPE, "crafting recipe"),
    (ExtractionType.SINGLE_ITEM_TEST, "BitCraft"),
])
def test_extraction_type_content(prompt_builder, extraction_type, expected_content):
    """Test that each extraction type generates content with expected keywords."""
    prompt = prompt_builder.get_prompt(extraction_type)
    assert expected_content in prompt


@pytest.mark.ai_analysis
@pytest.mark.unit
@pytest.mark.parametrize("screenshot_count", [1, 2, 3, 5, 10])
def test_queue_analysis_screenshot_count(prompt_builder, screenshot_count):
    """Test queue analysis prompt with different screenshot counts."""
    prompt = prompt_builder.get_queue_analysis_prompt(screenshot_count)
    assert f"{screenshot_count} screenshot(s)" in prompt
    assert isinstance(prompt, str)
    assert len(prompt) > 0


@pytest.mark.ai_analysis
@pytest.mark.unit
class TestPromptPerformance:
    """Test prompt generation performance."""

    def test_prompt_generation_speed(self, prompt_builder):
        """Test that prompt generation is fast."""
        start_time = time.time()
        
        # Generate multiple prompts
        for i in range(100):
            prompt_builder.get_queue_analysis_prompt(i % 5 + 1)
            prompt_builder.get_prompt(ExtractionType.ITEM_TOOLTIP)
            prompt_builder.get_prompt(ExtractionType.CRAFT_RECIPE)
            prompt_builder.get_prompt(ExtractionType.SINGLE_ITEM_TEST)
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        # Should generate 400 prompts in under 1 second
        assert generation_time < 1.0, f"Prompt generation too slow: {generation_time:.2f}s"

    def test_prompt_size_consistency(self, prompt_builder):
        """Test that prompt sizes are consistent across multiple generations."""
        # Generate same prompt multiple times
        prompts = []
        for _ in range(10):
            prompt = prompt_builder.get_queue_analysis_prompt(3, True)
            prompts.append(prompt)
        
        # All prompts should be identical
        first_prompt = prompts[0]
        for prompt in prompts[1:]:
            assert prompt == first_prompt, "Prompt generation should be deterministic"

    def test_memory_usage(self, prompt_builder):
        """Test that prompt generation doesn't accumulate memory."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Generate many prompts
        for _ in range(1000):
            prompt_builder.get_queue_analysis_prompt(3, True)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be minimal (< 10MB)
        assert memory_increase < 10 * 1024 * 1024, f"Memory usage increased by {memory_increase / 1024 / 1024:.1f}MB"


@pytest.mark.ai_analysis
@pytest.mark.unit
def test_prompt_builder_methods_exist(prompt_builder):
    """Test that all required methods exist on PromptBuilder."""
    # Test that required methods exist
    assert hasattr(prompt_builder, 'build_queue_analysis_prompt')
    assert hasattr(prompt_builder, 'build_item_tooltip_prompt')
    assert hasattr(prompt_builder, 'build_craft_recipe_prompt')
    assert hasattr(prompt_builder, 'build_single_item_test_prompt')
    assert hasattr(prompt_builder, 'get_prompt')
    assert hasattr(prompt_builder, 'get_compact_prompt')
    assert hasattr(prompt_builder, 'get_queue_analysis_prompt')
    assert hasattr(prompt_builder, 'get_compact_queue_prompt')
    
    # Test that methods are callable
    assert callable(prompt_builder.build_queue_analysis_prompt)
    assert callable(prompt_builder.get_prompt)
    assert callable(prompt_builder.get_compact_prompt)


@pytest.mark.ai_analysis
@pytest.mark.unit
def test_extraction_type_enum():
    """Test ExtractionType enum values."""
    # Test that enum has expected values
    assert hasattr(ExtractionType, 'QUEUE_ANALYSIS')
    assert hasattr(ExtractionType, 'ITEM_TOOLTIP')
    assert hasattr(ExtractionType, 'CRAFT_RECIPE')
    assert hasattr(ExtractionType, 'SINGLE_ITEM_TEST')
    
    # Test that enum values are unique
    values = [e.value for e in ExtractionType]
    assert len(values) == len(set(values)), "ExtractionType values should be unique"
