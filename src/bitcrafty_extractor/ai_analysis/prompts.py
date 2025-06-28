"""Structured prompts for AI vision analysis of game interfaces.

This module contains optimized prompts for extracting different types of 
game data from screenshots with high accuracy and consistency using a
queue-based analysis approach.
"""

from typing import Dict, Any, List
from enum import Enum
import json


class ExtractionType(Enum):
    """Types of data extraction available."""
    QUEUE_ANALYSIS = "queue_analysis"


class PromptBuilder:
    """Builder for creating structured AI vision prompts."""
    
    def __init__(self):
        """Initialize prompt builder with base templates."""
        self.base_context = """
You are an expert at analyzing game interface screenshots from Bitcraft, 
a crafting and building game. Your task is to extract structured data 
from multiple screenshots with high accuracy.

IMPORTANT INSTRUCTIONS:
1. Return ONLY valid JSON - no additional text or explanations
2. If you cannot extract any data, return {"error": "reason"}
3. Be precise with spelling and formatting
4. Include confidence scores (0.0-1.0) for extracted data
5. Follow the exact JSON schema provided
6. Analyze ALL provided screenshots together
7. Automatically detect items and crafting recipes from any screenshots
8. Group similar data together (all items, all crafts)
"""
    
    def build_queue_analysis_prompt(self, include_examples: bool = True) -> str:
        """Build prompt for analyzing a queue of screenshots.
        
        Args:
            include_examples: Whether to include example responses
            
        Returns:
            Formatted prompt string
        """
        schema = {
            "analysis_type": "queue_analysis",
            "screenshots_processed": "number - how many screenshots were analyzed",
            "items_found": [
                {
                    "type": "item",
                    "name": "string - exact name of the item",
                    "tier": "number - item tier/level (1-5, or null if not visible)",
                    "rarity": "string - item rarity (common, uncommon, rare, epic, legendary)",
                    "description": "string - item description text",
                    "uses": "string - what the item is used for or its purpose",
                    "confidence": "number - confidence score 0.0-1.0"
                }
            ],
            "crafts_found": [
                {
                    "type": "craft_recipe",
                    "name": "string - name of the item being crafted",
                    "requirements": {
                        "profession": "string - crafting profession required (e.g., blacksmithing, farming)",
                        "tool": "string - tool required if any (e.g., Anvil, Workbench)",
                        "building": "string - building required if any (e.g., Blacksmith Shop)"
                    },
                    "input_materials": [
                        {
                            "item_name": "string - ingredient item name",
                            "quantity": "number - amount needed"
                        }
                    ],
                    "output_materials": [
                        {
                            "item_name": "string - output item name",
                            "quantity": "number - base amount produced",
                            "variable_quantity": "boolean - true if quantity can vary"
                        }
                    ],
                    "confidence": "number - confidence score 0.0-1.0"
                }
            ],
            "total_confidence": "number - overall confidence score 0.0-1.0"
        }
        
        examples = ""
        if include_examples:
            examples = f"""
EXAMPLE RESPONSE:
{json.dumps({
    "analysis_type": "queue_analysis",
    "screenshots_processed": 3,
    "items_found": [
        {
            "type": "item",
            "name": "Iron Sword",
            "tier": 2,
            "rarity": "common",
            "description": "A sturdy sword forged from iron ore",
            "uses": "Combat weapon for dealing damage to enemies",
            "confidence": 0.95
        },
        {
            "type": "item",
            "name": "Wheat Seeds",
            "tier": 1,
            "rarity": "common", 
            "description": "Seeds used to grow wheat crops",
            "uses": "Plant in farmland to grow wheat for food production",
            "confidence": 0.92
        }
    ],
    "crafts_found": [
        {
            "type": "craft_recipe",
            "name": "Iron Sword",
            "requirements": {
                "profession": "blacksmithing",
                "tool": "Anvil",
                "building": "Blacksmith Shop"
            },
            "input_materials": [
                {"item_name": "Iron Ingot", "quantity": 3},
                {"item_name": "Wood", "quantity": 1}
            ],
            "output_materials": [
                {"item_name": "Iron Sword", "quantity": 1, "variable_quantity": False}
            ],
            "confidence": 0.88
        }
    ],
    "total_confidence": 0.91
}, indent=2)}

ANOTHER EXAMPLE (No crafts found):
{json.dumps({
    "analysis_type": "queue_analysis", 
    "screenshots_processed": 2,
    "items_found": [
        {
            "type": "item",
            "name": "Health Potion",
            "tier": 3,
            "rarity": "uncommon",
            "description": "A magical potion that restores health when consumed",
            "uses": "Restore health points during combat or exploration",
            "confidence": 0.89
        }
    ],
    "crafts_found": [],
    "total_confidence": 0.89
}, indent=2)}
"""
        
        return f"""{self.base_context}

TASK: Analyze all provided screenshots and extract item and crafting recipe data.

ITEM EXTRACTION RULES:
- Extract items from tooltips, inventory views, or any UI showing item details
- Include name, tier (if visible), rarity, description, and uses
- Focus on what the item is used for or its purpose in the game

CRAFTING RECIPE EXTRACTION RULES:
- Extract recipes from crafting interfaces, recipe books, or recipe tooltips
- Include all requirements (profession, tool, building)
- List all input materials with quantities
- List all output materials with quantities and whether quantity can vary
- Look for any crafting-related UI elements

REQUIRED JSON SCHEMA:
{json.dumps(schema, indent=2)}

{examples}

Analyze ALL the provided screenshots together and extract all visible items and crafting recipes.
Return ONLY the JSON response following the exact schema above."""

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
