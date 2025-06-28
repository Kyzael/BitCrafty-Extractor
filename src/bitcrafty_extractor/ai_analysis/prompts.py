"""Optimized prompts for AI vision analysis of BitCraft game interfaces.

Streamlined prompts focused on extracting game data efficiently with 
reduced token usage while maintaining high accuracy.
"""

from typing import Dict, Any, List
from enum import Enum
import json


class ExtractionType(Enum):
    """Types of data extraction available."""
    QUEUE_ANALYSIS = "queue_analysis"
    ITEM_TOOLTIP = "item_tooltip"
    CRAFT_RECIPE = "craft_recipe"
    SINGLE_ITEM_TEST = "single_item_test"


class PromptBuilder:
    """Builder for creating compact, efficient AI vision prompts."""
    
    def __init__(self):
        """Initialize prompt builder with optimized templates."""
        self.base_context = """Extract BitCraft game data from screenshots. Return ONLY valid JSON with exact item/recipe names and confidence scores (0.0-1.0)."""
    
    def build_queue_analysis_prompt(self, screenshot_count: int = 1, include_examples: bool = True) -> str:
        """Build optimized prompt for analyzing screenshots queue.
        
        Args:
            screenshot_count: Number of screenshots being analyzed
            include_examples: Whether to include example responses
            
        Returns:
            Compact formatted prompt string
        """
        schema = {
            "analysis_type": "queue_analysis",
            "screenshots_processed": screenshot_count,
            "items_found": [
                {
                    "name": "string - exact item name",
                    "description": "string - item description", 
                    "rarity": "string - common/uncommon/rare/epic/legendary",
                    "tier": "number or null",
                    "confidence": "number - 0.0-1.0"
                }
            ],
            "crafts_found": [
                {
                    "name": "string - recipe name", 
                    "requirements": {
                        "profession": "string - e.g. tailoring, farming, cooking",
                        "building": "string - building name or null",
                        "tool": "string - tool name or null"
                    },
                    "materials": [
                        {"item": "string - ingredient name", "qty": "number"}
                    ],
                    "outputs": [
                        {"item": "string - output name", "qty": "number or string for variable"}
                    ],
                    "confidence": "number - 0.0-1.0"
                }
            ],
            "total_confidence": "number - 0.0-1.0"
        }
        
        examples = ""
        if include_examples:
            examples = f"""
EXAMPLE:
{json.dumps({
    "analysis_type": "queue_analysis",
    "screenshots_processed": 2,
    "items_found": [
        {
            "name": "Rough Cloth Strip",
            "description": "Basic textile material woven from plant fibers",
            "rarity": "common",
            "tier": 1,
            "confidence": 0.95
        }
    ],
    "crafts_found": [
        {
            "name": "Weave Rough Cloth",
            "requirements": {
                "profession": "tailoring",
                "building": None,
                "tool": "basic-tools"
            },
            "materials": [
                {"item": "cloth-strip", "qty": 1},
                {"item": "wispweave-filament", "qty": 5}
            ],
            "outputs": [
                {"item": "cloth", "qty": 1}
            ],
            "confidence": 0.88
        }
    ],
    "total_confidence": 0.91
}, indent=2)}
"""
        
        craft_validation_rules = """
CRITICAL CRAFTING RECIPE VALIDATION RULES:
1. ONLY extract crafts_found if you see an ACTUAL CRAFTING INTERFACE with materials, tools, or profession requirements
2. Do NOT extract crafts for simple item tooltips or item information screens
3. A craft MUST have at least one of: materials list, profession requirement, tool requirement, or building requirement
4. If you only see an item description without crafting details, extract it as items_found ONLY
5. Crafts without materials[] AND without profession AND without tools are INVALID - exclude them
6. Item hover tooltips or information screens are NOT crafting recipes

VALID CRAFT INDICATORS:
- Clear materials list with quantities
- Profession requirements (tailoring, cooking, farming, etc.)
- Tool requirements (saw, hammer, loom, etc.)
- Building requirements (workstation, kiln, etc.)
- Recipe steps or crafting instructions

INVALID CRAFT INDICATORS (extract as items_found instead):
- Simple item tooltips or descriptions
- Item information screens without crafting details
- Just showing item name and description
- No materials, tools, professions, or buildings visible
"""
        
        return f"""{self.base_context}

TASK: Extract items and crafting recipes from {screenshot_count} screenshot(s).

{craft_validation_rules}

SCHEMA:
{json.dumps(schema, indent=2)}

{examples}

Return ONLY JSON following the schema above."""

    def build_item_tooltip_prompt(self, include_examples: bool = True) -> str:
        """Build compact prompt for item tooltip extraction.
        
        Args:
            include_examples: Whether to include example responses
            
        Returns:
            Compact formatted prompt string
        """
        schema = {
            "name": "string - exact item name",
            "description": "string - item description text",
            "rarity": "string - common/uncommon/rare/epic/legendary", 
            "tier": "number - 1-5 or null",
            "confidence": "number - 0.0-1.0"
        }
        
        examples = ""
        if include_examples:
            examples = f"""
EXAMPLE:
{json.dumps({
    "name": "Rough Spool of Thread",
    "description": "Basic thread crafted from plant fibers",
    "rarity": "common",
    "tier": 1,
    "confidence": 0.95
}, indent=2)}
"""
        
        return f"""{self.base_context}

TASK: Extract ITEM INFORMATION ONLY from this item tooltip or details screen.

CRITICAL: This is for ITEM DETAILS ONLY - do NOT extract crafting recipes or create craft entries.
Focus only on the item itself (name, description, rarity, tier).

SCHEMA:
{json.dumps(schema, indent=2)}

{examples}

Return ONLY JSON following the schema above."""

    def build_craft_recipe_prompt(self, include_examples: bool = True) -> str:
        """Build compact prompt for crafting recipe extraction.
        
        Args:
            include_examples: Whether to include example responses
            
        Returns:
            Compact formatted prompt string
        """
        schema = {
            "name": "string - recipe name",
            "requirements": {
                "profession": "string - crafting profession",
                "building": "string - building name or null", 
                "tool": "string - tool name or null"
            },
            "materials": [
                {"item": "string - ingredient name", "qty": "number or string"}
            ],
            "outputs": [
                {"item": "string - output name", "qty": "number or string"}
            ],
            "confidence": "number - 0.0-1.0"
        }
        
        examples = ""
        if include_examples:
            examples = f"""
EXAMPLE:
{json.dumps({
    "name": "Weave Rough Cloth",
    "requirements": {
        "profession": "tailoring",
        "building": None,
        "tool": "basic-tools"
    },
    "materials": [
        {"item": "cloth-strip", "qty": 1},
        {"item": "wispweave-filament", "qty": 5}
    ],
    "outputs": [
        {"item": "cloth", "qty": 1}
    ],
    "confidence": 0.90
}, indent=2)}
"""
        
        return f"""{self.base_context}

TASK: Extract crafting recipe data from an ACTIVE CRAFTING INTERFACE.

VALIDATION REQUIREMENTS:
- This prompt should ONLY be used for actual crafting interfaces/recipe screens
- Must show clear materials list with quantities
- Must show profession, tool, or building requirements
- Do NOT use this for simple item tooltips or information screens

SCHEMA: 
{json.dumps(schema, indent=2)}

{examples}

Return ONLY JSON following the schema above."""

    def build_single_item_test_prompt(self) -> str:
        """Build compact prompt for single item testing.
        
        Returns:
            Compact formatted prompt string for single item analysis
        """
        return f"""{self.base_context}

TASK: Identify items in this BitCraft screenshot.

Return JSON:
{{
    "items": [
        {{
            "name": "exact item name",
            "description": "item description if visible", 
            "rarity": "rarity if visible",
            "tier": "tier if visible",
            "confidence": 0.8
        }}
    ],
    "confidence": 0.8
}}

Common BitCraft items: Rough Spool of Thread, Rough Cloth Strip, Wispweave Seeds, Rough Wood Log, Raw Pelt, Breezy Fin Darter Fillet.
Be precise with names. Return empty array if no items visible."""

    def get_prompt(self, extraction_type: ExtractionType, **kwargs) -> str:
        """Get formatted prompt for specific extraction type.
        
        Args:
            extraction_type: Type of extraction to perform
            **kwargs: Additional parameters for prompt building
            
        Returns:
            Formatted prompt string
        """
        if extraction_type == ExtractionType.QUEUE_ANALYSIS:
            return self.build_queue_analysis_prompt(
                screenshot_count=kwargs.get('screenshot_count', 1),
                include_examples=kwargs.get('include_examples', True)
            )
        elif extraction_type == ExtractionType.ITEM_TOOLTIP:
            return self.build_item_tooltip_prompt(
                include_examples=kwargs.get('include_examples', True)
            )
        elif extraction_type == ExtractionType.CRAFT_RECIPE:
            return self.build_craft_recipe_prompt(
                include_examples=kwargs.get('include_examples', True)
            )
        elif extraction_type == ExtractionType.SINGLE_ITEM_TEST:
            return self.build_single_item_test_prompt()
        else:
            raise ValueError(f"Unknown extraction type: {extraction_type}")

    def get_compact_prompt(self, extraction_type: ExtractionType, **kwargs) -> str:
        """Get compact version of prompt (no examples) for cost optimization.
        
        Args:
            extraction_type: Type of extraction to perform
            **kwargs: Additional parameters for prompt building
            
        Returns:
            Compact prompt string
        """
        return self.get_prompt(extraction_type, include_examples=False, **kwargs)

    # Convenience methods for common use cases
    def get_queue_analysis_prompt(self, screenshot_count: int, include_examples: bool = True) -> str:
        """Get queue analysis prompt with screenshot count.
        
        Args:
            screenshot_count: Number of screenshots being analyzed
            include_examples: Whether to include examples
            
        Returns:
            Formatted prompt string
        """
        return self.get_prompt(
            ExtractionType.QUEUE_ANALYSIS,
            screenshot_count=screenshot_count,
            include_examples=include_examples
        )
    
    def get_compact_queue_prompt(self, screenshot_count: int) -> str:
        """Get compact queue analysis prompt for cost optimization.
        
        Args:
            screenshot_count: Number of screenshots being analyzed
            
        Returns:
            Compact prompt string
        """
        return self.get_compact_prompt(
            ExtractionType.QUEUE_ANALYSIS,
            screenshot_count=screenshot_count
        )
