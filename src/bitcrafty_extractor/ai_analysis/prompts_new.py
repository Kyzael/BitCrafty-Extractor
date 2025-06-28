"""Structured prompts for AI vision analysis of game interfaces.

This module contains optimized prompts for extracting different types of 
game data from screenshots with high accuracy and consistency.
"""

from typing import Dict, Any, List
from enum import Enum
import json


class ExtractionType(Enum):
    """Types of data extraction available."""
    ITEM_TOOLTIP = "item_tooltip"
    CRAFT_RECIPE = "craft_recipe"


class PromptBuilder:
    """Builder for creating structured AI vision prompts."""
    
    def __init__(self):
        """Initialize prompt builder with base templates."""
        self.base_context = """
You are an expert at analyzing game interface screenshots from Bitcraft, 
a crafting and building game. Your task is to extract structured data 
from the game UI with high accuracy.

IMPORTANT INSTRUCTIONS:
1. Return ONLY valid JSON - no additional text or explanations
2. If you cannot extract the requested data, return {"error": "reason"}
3. Be precise with spelling and formatting
4. Include confidence scores (0.0-1.0) for extracted data
5. Follow the exact JSON schema provided
6. For complex recipes with multiple screenshots, analyze all provided images together
"""
    
    def build_item_tooltip_prompt(self, include_examples: bool = True) -> str:
        """Build prompt for extracting item tooltip information.
        
        Args:
            include_examples: Whether to include example responses
            
        Returns:
            Formatted prompt string
        """
        schema = {
            "type": "item_tooltip",
            "item_name": "string - exact name of the item",
            "description": "string - item description text",
            "profession": "string - associated profession (farming, mining, etc.)",
            "rarity": "string - item rarity if visible",
            "stack_size": "number - maximum stack size if shown",
            "value": "number - item value if displayed",
            "properties": "object - any additional properties (weight, durability, etc.)",
            "confidence": "number - confidence score 0.0-1.0"
        }
        
        examples = ""
        if include_examples:
            examples = f"""
EXAMPLE RESPONSE:
{json.dumps({
    "type": "item_tooltip",
    "item_name": "Iron Sword",
    "description": "A sturdy sword forged from iron ore",
    "profession": "blacksmithing",
    "rarity": "common",
    "stack_size": 1,
    "value": 25,
    "properties": {
        "durability": 100,
        "damage": 15
    },
    "confidence": 0.95
}, indent=2)}

ANOTHER EXAMPLE:
{json.dumps({
    "type": "item_tooltip",
    "item_name": "Wheat Seeds",
    "description": "Seeds used to grow wheat crops",
    "profession": "farming",
    "rarity": "common",
    "stack_size": 50,
    "value": 2,
    "properties": {
        "growth_time": "5 minutes"
    },
    "confidence": 0.92
}, indent=2)}
"""
        
        return f"""{self.base_context}

TASK: Extract item tooltip information from this game screenshot.

REQUIRED JSON SCHEMA:
{json.dumps(schema, indent=2)}

{examples}

Analyze the screenshot and extract the item tooltip data following the exact schema above.
Return ONLY the JSON response."""

    def build_craft_recipe_prompt(self, include_examples: bool = True) -> str:
        """Build prompt for extracting crafting recipe information.
        
        Args:
            include_examples: Whether to include example responses
            
        Returns:
            Formatted prompt string
        """
        schema = {
            "type": "craft_recipe",
            "recipe_name": "string - name of the item being crafted",
            "profession": "string - crafting profession required",
            "ingredients": [
                {
                    "item_name": "string - ingredient item name",
                    "quantity": "number - amount needed"
                }
            ],
            "outputs": [
                {
                    "item_name": "string - output item name", 
                    "quantity": "number - amount produced"
                }
            ],
            "requirements": {
                "level": "number - profession level required",
                "tool": "string - tool required if any",
                "building": "string - building required if any",
                "skill_points": "number - skill points required if any"
            },
            "craft_time": "string - time to craft if shown",
            "multi_screenshots": "number - how many screenshots were analyzed (1 for simple, 2+ for complex)",
            "confidence": "number - confidence score 0.0-1.0"
        }
        
        examples = ""
        if include_examples:
            examples = f"""
EXAMPLE RESPONSE:
{json.dumps({
    "type": "craft_recipe",
    "recipe_name": "Iron Sword",
    "profession": "blacksmithing",
    "ingredients": [
        {"item_name": "Iron Ingot", "quantity": 3},
        {"item_name": "Wood", "quantity": 1}
    ],
    "outputs": [
        {"item_name": "Iron Sword", "quantity": 1}
    ],
    "requirements": {
        "level": 15,
        "tool": "Anvil",
        "building": "Blacksmith Shop",
        "skill_points": 5
    },
    "craft_time": "30 seconds",
    "multi_screenshots": 1,
    "confidence": 0.88
}, indent=2)}
"""
        
        return f"""{self.base_context}

TASK: Extract crafting recipe information from this game screenshot(s).
If multiple screenshots are provided, analyze them together to extract complete recipe data.

REQUIRED JSON SCHEMA:
{json.dumps(schema, indent=2)}

{examples}

Analyze the screenshot(s) and extract the crafting recipe data following the exact schema above.
For multi-screenshot recipes, combine data from all images to provide complete ingredient/output lists.
Return ONLY the JSON response."""

    def get_prompt(self, extraction_type: ExtractionType, **kwargs) -> str:
        """Get formatted prompt for specific extraction type.
        
        Args:
            extraction_type: Type of extraction to perform
            **kwargs: Additional parameters for prompt building
            
        Returns:
            Formatted prompt string
        """
        if extraction_type == ExtractionType.ITEM_TOOLTIP:
            return self.build_item_tooltip_prompt(
                include_examples=kwargs.get('include_examples', True)
            )
        elif extraction_type == ExtractionType.CRAFT_RECIPE:
            return self.build_craft_recipe_prompt(
                include_examples=kwargs.get('include_examples', True)
            )
        else:
            raise ValueError(f"Unknown extraction type: {extraction_type}")

    def get_compact_prompt(self, extraction_type: ExtractionType) -> str:
        """Get compact version of prompt (no examples) for cost optimization.
        
        Args:
            extraction_type: Type of extraction to perform
            
        Returns:
            Compact prompt string
        """
        return self.get_prompt(extraction_type, include_examples=False)
