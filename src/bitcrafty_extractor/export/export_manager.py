"""Export manager for saving extracted items and crafts to JSON files."""

import json
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Any, Set
from datetime import datetime
import structlog


class ExportManager:
    """Manages exporting and deduplicating extracted items and crafts."""
    
    def __init__(self, exports_dir: Path = None, config_manager=None):
        """Initialize export manager.
        
        Args:
            exports_dir: Directory to save exports (defaults to ./exports)
            config_manager: Configuration manager for validation settings
        """
        self.logger = structlog.get_logger(__name__)
        self.exports_dir = exports_dir or Path("exports")
        self.exports_dir.mkdir(exist_ok=True)
        
        # Configuration for validation
        self.config_manager = config_manager
        if config_manager and config_manager.config.extraction:
            self.min_confidence = config_manager.config.extraction.min_confidence
        else:
            self.min_confidence = 0.7  # Default threshold
        
        # File paths
        self.items_file = self.exports_dir / "items.json"
        self.crafts_file = self.exports_dir / "crafts.json"
        
        # Load existing data
        self.existing_items: Dict[str, Dict] = self._load_existing_items()
        self.existing_crafts: Dict[str, Dict] = self._load_existing_crafts()
        
        # Session tracking for new discoveries
        self.session_new_items: List[Dict[str, Any]] = []
        self.session_new_crafts: List[Dict[str, Any]] = []
        
        self.logger.info("Export manager initialized", 
                        exports_dir=str(self.exports_dir),
                        existing_items=len(self.existing_items),
                        existing_crafts=len(self.existing_crafts),
                        min_confidence_threshold=self.min_confidence)
    
    def _load_existing_items(self) -> Dict[str, Dict]:
        """Load existing items from JSON file."""
        if not self.items_file.exists():
            self.logger.info("No existing items file found", file=str(self.items_file))
            return {}
        
        try:
            with open(self.items_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert list to dict keyed by item hash
            items_dict = {}
            for item in data.get('items', []):
                item_hash = self._generate_item_hash(item)
                items_dict[item_hash] = item
            
            self.logger.info("Loaded existing items", count=len(items_dict))
            return items_dict
            
        except Exception as e:
            self.logger.error("Failed to load existing items", error=str(e))
            return {}
    
    def _load_existing_crafts(self) -> Dict[str, Dict]:
        """Load existing crafts from JSON file."""
        if not self.crafts_file.exists():
            self.logger.info("No existing crafts file found", file=str(self.crafts_file))
            return {}
        
        try:
            with open(self.crafts_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert list to dict keyed by craft hash
            crafts_dict = {}
            for craft in data.get('crafts', []):
                craft_hash = self._generate_craft_hash(craft)
                crafts_dict[craft_hash] = craft
            
            self.logger.info("Loaded existing crafts", count=len(crafts_dict))
            return crafts_dict
            
        except Exception as e:
            self.logger.error("Failed to load existing crafts", error=str(e))
            return {}
    
    def _find_similar_items(self, new_item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find items with the same name but potentially different properties.
        
        This helps identify items that might be duplicates with minor variations.
        """
        new_name = new_item.get('name', '').lower().strip()
        similar_items = []
        
        for existing_item in self.existing_items.values():  # Use .values() to get the actual items
            # Handle non-dictionary items safely
            if not isinstance(existing_item, dict):
                self.logger.warning("Non-dict existing item in _find_similar_items", 
                                  item_type=type(existing_item).__name__, 
                                  item_value=str(existing_item)[:100])
                continue
                
            existing_name = existing_item.get('name', '').lower().strip()
            if new_name == existing_name:
                similar_items.append(existing_item)
        
        return similar_items
    
    def _should_update_existing_item(self, new_item: Dict[str, Any], existing_item: Dict[str, Any]) -> bool:
        """Determine if an existing item should be updated with new information.
        
        Returns True if the new item has better/more complete information.
        """
        # Check if new item has higher confidence
        new_confidence = new_item.get('confidence', 0)
        existing_confidence = existing_item.get('confidence', 0)
        
        if new_confidence > existing_confidence + 0.05:  # 5% threshold
            return True
        
        # Check if new item has more complete information
        new_desc = new_item.get('description', '')
        existing_desc = existing_item.get('description', '')
        
        # Prefer longer, more detailed descriptions
        if len(new_desc) > len(existing_desc) * 1.2:  # 20% longer
            return True
        
        # Check if new item has tier when existing doesn't
        if new_item.get('tier') is not None and existing_item.get('tier') is None:
            return True
        
        return False
    
    def _generate_item_hash(self, item: Dict[str, Any]) -> str:
        """Generate a unique hash for an item based on key properties.
        
        Uses primarily the item name for duplicate detection, as descriptions
        may have minor variations while referring to the same item.
        """
        # Handle non-dictionary items safely
        if not isinstance(item, dict):
            self.logger.warning("_generate_item_hash called with non-dict", 
                              item_type=type(item).__name__, 
                              item_value=str(item)[:100])
            # Generate hash from string representation
            return hashlib.md5(str(item).encode('utf-8')).hexdigest()[:12]
        
        # Use primarily name for hashing (core identifying feature)
        name = item.get('name', '').lower().strip()
        
        # Normalize common variations in name
        name = name.replace('  ', ' ')  # Double spaces to single
        name = name.replace('-', ' ')   # Dashes to spaces for consistency
        
        # For more robust duplicate detection, also consider tier and rarity if available
        tier = str(item.get('tier', '') or '').strip()
        rarity = str(item.get('rarity', '') or '').strip()
        
        # Create hash primarily from name, with tier/rarity as secondary factors
        hash_string = f"{name}|{tier}|{rarity}"
        return hashlib.md5(hash_string.encode('utf-8')).hexdigest()[:12]
    
    def _generate_craft_hash(self, craft: Dict[str, Any]) -> str:
        """Generate a unique hash for a craft based on key properties.
        
        For true duplicate detection, includes name, materials, outputs, AND requirements.
        This prevents flagging legitimate crafts with same name but different 
        requirements (like Basic Fertilizer variants) as duplicates.
        """
        # Handle non-dictionary crafts safely
        if not isinstance(craft, dict):
            self.logger.warning("_generate_craft_hash called with non-dict", 
                              craft_type=type(craft).__name__, 
                              craft_value=str(craft)[:100])
            # Generate hash from string representation
            return hashlib.md5(str(craft).encode('utf-8')).hexdigest()[:12]
        
        # Use name, materials, outputs, and requirements for comprehensive hashing
        name = craft.get('name', '').lower().strip()
        
        # Normalize materials and outputs
        materials = craft.get('materials', [])
        outputs = craft.get('outputs', [])
        requirements = craft.get('requirements', {})
        
        # Create sorted string representation for consistent hashing
        materials_str = "|".join(sorted([
            f"{m.get('item', '') if isinstance(m, dict) else str(m)}:{m.get('qty', 1) if isinstance(m, dict) else 1}" for m in materials
        ]))
        outputs_str = "|".join(sorted([
            f"{o.get('item', '') if isinstance(o, dict) else str(o)}:{o.get('qty', 1) if isinstance(o, dict) else 1}" for o in outputs
        ]))
        
        # Include requirements in hash to differentiate crafts with same name/materials/outputs
        # but different profession, building, tool requirements
        requirements_parts = []
        if isinstance(requirements, dict):
            # Sort requirements for consistent hashing
            for key in sorted(requirements.keys()):
                value = requirements[key]
                if value:  # Only include non-empty values
                    requirements_parts.append(f"{key}:{str(value).lower().strip()}")
        
        requirements_str = "|".join(requirements_parts)
        
        # Combine all components for comprehensive duplicate detection
        hash_string = f"{name}|{materials_str}|{outputs_str}|{requirements_str}"
        return hashlib.md5(hash_string.encode('utf-8')).hexdigest()[:12]
    
    def _analyze_items_for_duplicates(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze items to identify duplicates before processing.
        
        Args:
            items: List of items to analyze
            
        Returns:
            Dict with duplicate analysis results
        """
        duplicates = []
        duplicates_count = 0
        
        for item in items:
            # Skip non-dictionary items safely
            if not isinstance(item, dict):
                self.logger.warning("Non-dict item in duplicate analysis", 
                                  item_type=type(item).__name__, 
                                  item_value=str(item)[:100])
                continue
                
            item_hash = self._generate_item_hash(item)
            
            if item_hash in self.existing_items:
                duplicates_count += 1
                existing = self.existing_items[item_hash]
                duplicates.append({
                    'name': item.get('name', 'Unknown'),
                    'hash': item_hash,
                    'new_confidence': item.get('confidence', 0),
                    'existing_confidence': existing.get('confidence', 0),
                    'first_seen': existing.get('extracted_at', 'Unknown')
                })
                
                self.logger.debug("Item duplicate detected", 
                                name=item.get('name'),
                                hash=item_hash,
                                existing_confidence=existing.get('confidence', 0),
                                new_confidence=item.get('confidence', 0))
        
        return {
            'duplicates_count': duplicates_count,
            'duplicates': duplicates,
            'new_items_count': len(items) - duplicates_count
        }
    
    def _analyze_crafts_for_duplicates(self, crafts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze crafts to identify duplicates before processing.
        
        Args:
            crafts: List of crafts to analyze
            
        Returns:
            Dict with duplicate analysis results
        """
        duplicates = []
        duplicates_count = 0
        
        for craft in crafts:
            # Skip non-dictionary crafts safely
            if not isinstance(craft, dict):
                self.logger.warning("Non-dict craft in duplicate analysis", 
                                  craft_type=type(craft).__name__, 
                                  craft_value=str(craft)[:100])
                continue
                
            # Clean craft name first (same as in processing)
            craft_copy = craft.copy()
            craft_copy['name'] = self._clean_craft_name(craft.get('name', ''))
            
            craft_hash = self._generate_craft_hash(craft_copy)
            
            if craft_hash in self.existing_crafts:
                duplicates_count += 1
                existing = self.existing_crafts[craft_hash]
                duplicates.append({
                    'name': craft_copy.get('name', 'Unknown'),
                    'hash': craft_hash,
                    'new_confidence': craft.get('confidence', 0),
                    'existing_confidence': existing.get('confidence', 0),
                    'first_seen': existing.get('extracted_at', 'Unknown'),
                    'profession': craft.get('requirements', {}).get('profession', 'Unknown')
                })
                
                self.logger.debug("Craft duplicate detected", 
                                name=craft_copy.get('name'),
                                hash=craft_hash,
                                existing_confidence=existing.get('confidence', 0),
                                new_confidence=craft.get('confidence', 0))
        
        return {
            'duplicates_count': duplicates_count,
            'duplicates': duplicates,
            'new_crafts_count': len(crafts) - duplicates_count
        }
    
    def _validate_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Validate an item and return validation results.
        
        Args:
            item: Item data to validate
            
        Returns:
            Dict with validation results
        """
        # Handle non-dictionary items
        if not isinstance(item, dict):
            self.logger.warning("_validate_item called with non-dict", 
                              item_type=type(item).__name__, 
                              item_value=str(item)[:100])
            return {
                'is_valid': False,
                'reasons': [f"Item is not a dictionary: {type(item).__name__}"]
            }
        
        name = item.get('name', '').strip()
        confidence = item.get('confidence', 0)
        
        validation = {
            'is_valid': True,
            'reasons': []
        }
        
        # Check confidence threshold
        if confidence < self.min_confidence:
            validation['is_valid'] = False
            validation['reasons'].append(f"Confidence {confidence:.2f} below threshold {self.min_confidence}")
        
        # Check required fields
        if not name:
            validation['is_valid'] = False
            validation['reasons'].append("Missing or empty name")
        
        if validation['is_valid']:
            self.logger.debug("Item validation passed", name=name, confidence=confidence)
        else:
            self.logger.info("Item validation failed", 
                           name=name or "unnamed",
                           confidence=confidence,
                           reasons=validation['reasons'])
        
        return validation
    
    def _validate_craft(self, craft: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a craft and return validation results.
        
        Args:
            craft: Craft data to validate
            
        Returns:
            Dict with validation results
        """
        # Handle non-dictionary crafts
        if not isinstance(craft, dict):
            self.logger.warning("_validate_craft called with non-dict",
                              craft_type=type(craft).__name__,
                              craft_value=str(craft)[:100])
            return {
                'is_valid': False,
                'reasons': [f"Craft is not a dictionary: {type(craft).__name__}"]
            }
        
        name = craft.get('name', '').strip()
        confidence = craft.get('confidence', 0)
        requirements = craft.get('requirements', {})
        materials = craft.get('materials', [])
        outputs = craft.get('outputs', [])
        
        validation = {
            'is_valid': True,
            'reasons': []
        }
        
        # Check confidence threshold
        if confidence < self.min_confidence:
            validation['is_valid'] = False
            validation['reasons'].append(f"Confidence {confidence:.2f} below threshold {self.min_confidence}")
        
        # Check required fields
        if not name:
            validation['is_valid'] = False
            validation['reasons'].append("Missing or empty name")
        
        # Check for empty requirements - this is critical for preventing false crafts
        if not requirements or all(not v for v in requirements.values()):
            validation['is_valid'] = False
            validation['reasons'].append("Empty or missing requirements (profession, building, tool)")
        
        # Check that at least one requirement field is meaningful
        profession = str(requirements.get('profession', '') or '').strip()
        building = str(requirements.get('building', '') or '').strip()
        tool = str(requirements.get('tool', '') or '').strip()
        
        if not any([profession, building, tool]):
            validation['is_valid'] = False
            validation['reasons'].append("No meaningful profession, building, or tool requirements")
        
        # Check materials list
        if not materials:
            validation['is_valid'] = False
            validation['reasons'].append("Missing or empty materials list")
        
        # Check outputs list
        if not outputs:
            validation['is_valid'] = False
            validation['reasons'].append("Missing or empty outputs list")
        
        # Check for circular recipes (input = output)
        if materials and outputs:
            material_items = set()
            output_items = set()
            
            # Extract material item names
            for material in materials:
                if isinstance(material, dict) and 'item' in material:
                    material_items.add(material['item'].strip().lower())
            
            # Extract output item names
            for output in outputs:
                if isinstance(output, dict) and 'item' in output:
                    output_items.add(output['item'].strip().lower())
            
            # Check for overlap (circular recipes)
            circular_items = material_items & output_items
            if circular_items:
                validation['is_valid'] = False
                circular_list = list(circular_items)
                validation['reasons'].append(f"Circular recipe detected: {circular_list[0]} is both input and output")
                self.logger.warning("Circular recipe detected", 
                                  craft_name=name,
                                  circular_items=list(circular_items),
                                  materials=[m.get('item') if isinstance(m, dict) else m for m in materials],
                                  outputs=[o.get('item') if isinstance(o, dict) else o for o in outputs])
        
        if validation['is_valid']:
            self.logger.debug("Craft validation passed", 
                            name=name, 
                            confidence=confidence,
                            profession=profession,
                            materials_count=len(materials))
        else:
            self.logger.info("Craft validation failed", 
                           name=name or "unnamed",
                           confidence=confidence,
                           requirements=requirements,
                           reasons=validation['reasons'])
        
        return validation
    
    def process_extraction_results(self, data: Dict[str, Any], extracted_at: datetime = None) -> Dict[str, Any]:
        """Process extraction results and export new items/crafts.
        
        Args:
            data: Extraction results from AI analysis
            extracted_at: Timestamp of when screenshots were taken
            
        Returns:
            Dict with processing statistics including duplicate detection
        """
        if extracted_at is None:
            extracted_at = datetime.now()
            
        items = data.get('items_found', [])
        crafts = data.get('crafts_found', [])
        
        # Debug and validate items/crafts data types
        self.logger.debug("Processing extraction results", 
                         items_type=type(items).__name__, 
                         crafts_type=type(crafts).__name__,
                         items_count=len(items) if hasattr(items, '__len__') else 'no len',
                         crafts_count=len(crafts) if hasattr(crafts, '__len__') else 'no len')
        
        # Filter out any non-dictionary items/crafts and log them
        valid_items = []
        invalid_items = []
        for i, item in enumerate(items):
            if isinstance(item, dict):
                valid_items.append(item)
            else:
                invalid_items.append((i, type(item).__name__, str(item)[:100]))
                self.logger.warning("Invalid item type found", 
                                  index=i, 
                                  item_type=type(item).__name__, 
                                  item_value=str(item)[:100])
        
        valid_crafts = []
        invalid_crafts = []
        for i, craft in enumerate(crafts):
            if isinstance(craft, dict):
                valid_crafts.append(craft)
            else:
                invalid_crafts.append((i, type(craft).__name__, str(craft)[:100]))
                self.logger.warning("Invalid craft type found",
                                  index=i,
                                  craft_type=type(craft).__name__,
                                  craft_value=str(craft)[:100])
        
        # Use filtered lists for processing
        items = valid_items
        crafts = valid_crafts
        
        if invalid_items:
            self.logger.warning("Filtered out invalid items", count=len(invalid_items), details=invalid_items)
        if invalid_crafts:
            self.logger.warning("Filtered out invalid crafts", count=len(invalid_crafts), details=invalid_crafts)
        
        # Analyze duplicates before processing
        items_duplicate_analysis = self._analyze_items_for_duplicates(items)
        crafts_duplicate_analysis = self._analyze_crafts_for_duplicates(crafts)
        
        # Process items and crafts
        new_items = self._process_items(items, extracted_at)
        new_crafts = self._process_crafts(crafts, extracted_at)
        
        # Calculate validation statistics safely - items and crafts now only contain dicts
        valid_items_count = 0
        valid_crafts_count = 0
        
        # Count valid items
        for item in items:
            try:
                if isinstance(item, dict) and self._validate_item(item)['is_valid']:
                    valid_items_count += 1
            except Exception as e:
                self.logger.warning("Error validating item during stats calculation", 
                                  item_type=type(item).__name__, 
                                  error=str(e))
        
        # Count valid crafts
        for craft in crafts:
            try:
                if isinstance(craft, dict) and self._validate_craft(craft)['is_valid']:
                    valid_crafts_count += 1
            except Exception as e:
                self.logger.warning("Error validating craft during stats calculation", 
                                  craft_type=type(craft).__name__, 
                                  error=str(e))
        
        items_rejected = len(items) - valid_items_count
        crafts_rejected = len(crafts) - valid_crafts_count
        
        # Save if we have new data
        if new_items or new_crafts:
            self._save_data()
        
        stats = {
            'items_processed': len(items),
            'crafts_processed': len(crafts),
            'items_rejected': items_rejected,
            'crafts_rejected': crafts_rejected,
            'new_items_added': len(new_items),
            'new_crafts_added': len(new_crafts),
            'total_items': len(self.existing_items),
            'total_crafts': len(self.existing_crafts),
            'min_confidence_threshold': self.min_confidence,
            # Enhanced duplicate tracking
            'items_found_total': len(items),
            'items_found_new': len(new_items),
            'items_found_duplicates': items_duplicate_analysis['duplicates_count'],
            'crafts_found_total': len(crafts),
            'crafts_found_new': len(new_crafts),
            'crafts_found_duplicates': crafts_duplicate_analysis['duplicates_count'],
            'duplicate_items_details': items_duplicate_analysis['duplicates'],
            'duplicate_crafts_details': crafts_duplicate_analysis['duplicates'],
            # Include info about invalid data
            'invalid_items_filtered': len(invalid_items),
            'invalid_crafts_filtered': len(invalid_crafts)
        }
        
        self.logger.info("Processed extraction results", **stats)
        return stats
    
    def _process_items(self, items: List[Dict[str, Any]], extracted_at: datetime) -> List[Dict[str, Any]]:
        """Process items and add new ones to the store."""
        new_items = []
        rejected_items = 0
        
        for item in items:
            # Validate item first
            validation = self._validate_item(item)
            if not validation['is_valid']:
                rejected_items += 1
                self.logger.info("Rejected item", 
                               name=item.get('name', 'unnamed'),
                               reasons=validation['reasons'])
                continue
            
            # Add extraction metadata
            processed_item = {
                **item,
                'extracted_at': extracted_at.isoformat(),
                'extraction_source': 'bitcrafty-extractor'
            }
            
            item_hash = self._generate_item_hash(processed_item)
            
            # Check for exact duplicate first
            if item_hash in self.existing_items:
                self.logger.debug("Exact duplicate item found", name=item.get('name'), hash=item_hash)
                continue
            
            # Check for similar items (same name, different properties)
            similar_items = self._find_similar_items(processed_item)
            if similar_items:
                # Found items with same name - decide whether to update or skip
                best_existing = max(similar_items, key=lambda x: x.get('confidence', 0))
                
                if self._should_update_existing_item(processed_item, best_existing):
                    # Update the existing item with better information
                    old_hash = self._generate_item_hash(best_existing)
                    self.logger.info("Updating existing item with better information", 
                                   name=processed_item.get('name'),
                                   old_confidence=best_existing.get('confidence'),
                                   new_confidence=processed_item.get('confidence'))
                    
                    # Remove old item from existing items dict
                    if old_hash in self.existing_items:
                        del self.existing_items[old_hash]
                    
                    # Add the updated item
                    processed_item['id'] = item_hash
                    self.existing_items[item_hash] = processed_item
                    new_items.append(processed_item)
                    # Track updated items for session summary
                    self.session_new_items.append(processed_item)
                else:
                    # Keep existing item, skip new one
                    self.logger.debug("Similar item exists with better/equal info", name=processed_item.get('name'))
                continue
            
            # This is a genuinely new item
            processed_item['id'] = item_hash
            self.existing_items[item_hash] = processed_item
            new_items.append(processed_item)
            # Track new items for session summary
            self.session_new_items.append(processed_item)
            self.logger.info("New item discovered", 
                           name=processed_item.get('name'),
                           item_id=item_hash,
                           confidence=processed_item.get('confidence'))
        
        self.logger.info("Items processing complete", 
                       new_items=len(new_items),
                       rejected_items=rejected_items)
        return new_items
        
        if rejected_items > 0:
            self.logger.info("Items validation summary", 
                           processed=len(items),
                           accepted=len(items) - rejected_items,
                           rejected=rejected_items)
        
        return new_items
    
    def _normalize_item_name(self, item_name: str) -> str:
        """Normalize item names to match existing items in database.
        
        This helps ensure consistency between craft materials/outputs and actual item names.
        """
        if not item_name:
            return item_name
            
        # Convert from various formats to proper title case
        normalized = item_name.strip()
        
        # Handle kebab-case to Title Case (e.g., "knapped-flint" -> "Knapped Flint")
        if '-' in normalized:
            normalized = ' '.join(word.capitalize() for word in normalized.split('-'))
        
        # Handle snake_case to Title Case (e.g., "basic_mushroom" -> "Basic Mushroom")  
        if '_' in normalized:
            normalized = ' '.join(word.capitalize() for word in normalized.split('_'))
        
        # Handle simple lowercase to Title Case
        if normalized.islower():
            normalized = normalized.title()
            
        # Check if we have this exact item in our existing items
        for existing_item in self.existing_items.values():
            existing_name = existing_item.get('name', '')
            if existing_name.lower() == normalized.lower():
                return existing_name  # Return the exact existing name
        
        return normalized
    
    def _normalize_craft_materials_and_outputs(self, craft: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize item names in craft materials and outputs."""
        craft_copy = craft.copy()
        
        # Normalize materials
        if 'materials' in craft_copy:
            normalized_materials = []
            for material in craft_copy['materials']:
                normalized_material = material.copy()
                if 'item' in normalized_material:
                    normalized_material['item'] = self._normalize_item_name(normalized_material['item'])
                normalized_materials.append(normalized_material)
            craft_copy['materials'] = normalized_materials
        
        # Normalize outputs
        if 'outputs' in craft_copy:
            normalized_outputs = []
            for output in craft_copy['outputs']:
                normalized_output = output.copy()
                if 'item' in normalized_output:
                    normalized_output['item'] = self._normalize_item_name(normalized_output['item'])
                normalized_outputs.append(normalized_output)
            craft_copy['outputs'] = normalized_outputs
        
        return craft_copy
    
    def _find_similar_crafts(self, new_craft: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find crafts with the same name but potentially different properties.
        
        This helps identify crafts that might be variations of the same recipe
        but should not be considered exact duplicates if they have different
        materials, outputs, or requirements.
        """
        new_name = new_craft.get('name', '').lower().strip()
        similar_crafts = []
        
        for existing_craft in self.existing_crafts.values():
            # Handle non-dictionary crafts safely
            if not isinstance(existing_craft, dict):
                self.logger.warning("Non-dict existing craft in _find_similar_crafts", 
                                  craft_type=type(existing_craft).__name__, 
                                  craft_value=str(existing_craft)[:100])
                continue
                
            existing_name = existing_craft.get('name', '').lower().strip()
            
            # Only consider crafts with identical names as "similar"
            # The hash function will determine if they're truly duplicates
            if new_name == existing_name:
                similar_crafts.append(existing_craft)
        
        return similar_crafts
    
    def _are_crafts_very_similar(self, new_craft: Dict[str, Any], existing_craft: Dict[str, Any]) -> bool:
        """Check if two crafts are very similar (beyond just having the same name).
        
        Returns True only if the crafts have the same name, materials, outputs, AND requirements.
        This is used to identify crafts that are nearly identical and might warrant updating
        rather than being added as separate entries.
        """
        # Must have same name (case insensitive)
        new_name = new_craft.get('name', '').lower().strip()
        existing_name = existing_craft.get('name', '').lower().strip()
        if new_name != existing_name:
            return False
        
        # Compare materials
        new_materials = new_craft.get('materials', [])
        existing_materials = existing_craft.get('materials', [])
        if not self._materials_equal(new_materials, existing_materials):
            return False
        
        # Compare outputs  
        new_outputs = new_craft.get('outputs', [])
        existing_outputs = existing_craft.get('outputs', [])
        if not self._outputs_equal(new_outputs, existing_outputs):
            return False
        
        # Compare requirements
        new_reqs = new_craft.get('requirements', {})
        existing_reqs = existing_craft.get('requirements', {})
        if not self._requirements_equal(new_reqs, existing_reqs):
            return False
        
        # If we get here, they're very similar (essentially the same craft)
        return True
    
    def _materials_equal(self, materials1: List[Dict], materials2: List[Dict]) -> bool:
        """Check if two materials lists are equal."""
        if len(materials1) != len(materials2):
            return False
        
        # Sort materials by item name for comparison
        sorted_m1 = sorted(materials1, key=lambda x: x.get('item', '') if isinstance(x, dict) else str(x))
        sorted_m2 = sorted(materials2, key=lambda x: x.get('item', '') if isinstance(x, dict) else str(x))
        
        for m1, m2 in zip(sorted_m1, sorted_m2):
            if not isinstance(m1, dict) or not isinstance(m2, dict):
                continue
            if (m1.get('item', '') != m2.get('item', '') or 
                m1.get('qty', 1) != m2.get('qty', 1)):
                return False
        
        return True
    
    def _outputs_equal(self, outputs1: List[Dict], outputs2: List[Dict]) -> bool:
        """Check if two outputs lists are equal."""
        if len(outputs1) != len(outputs2):
            return False
        
        # Sort outputs by item name for comparison
        sorted_o1 = sorted(outputs1, key=lambda x: x.get('item', '') if isinstance(x, dict) else str(x))
        sorted_o2 = sorted(outputs2, key=lambda x: x.get('item', '') if isinstance(x, dict) else str(x))
        
        for o1, o2 in zip(sorted_o1, sorted_o2):
            if not isinstance(o1, dict) or not isinstance(o2, dict):
                continue
            if (o1.get('item', '') != o2.get('item', '') or 
                o1.get('qty', 1) != o2.get('qty', 1)):
                return False
        
        return True
    
    def _requirements_equal(self, reqs1: Dict, reqs2: Dict) -> bool:
        """Check if two requirements dictionaries are equal."""
        # Normalize requirements by removing empty values
        norm_reqs1 = {k: v for k, v in reqs1.items() if v and str(v).strip()}
        norm_reqs2 = {k: v for k, v in reqs2.items() if v and str(v).strip()}
        
        return norm_reqs1 == norm_reqs2
    
    def _should_update_existing_craft(self, new_craft: Dict[str, Any], existing_craft: Dict[str, Any]) -> bool:
        """Determine if an existing craft should be updated with new information.
        
        Only updates if the new craft has significantly better confidence or
        more complete information, ensuring we don't replace good data with worse data.
        """
        # Check if new craft has significantly higher confidence
        new_confidence = new_craft.get('confidence', 0)
        existing_confidence = existing_craft.get('confidence', 0)
        
        if new_confidence > existing_confidence + 0.1:  # 10% threshold for safety
            return True
        
        # Check if new craft has more complete requirements
        new_reqs = new_craft.get('requirements', {})
        existing_reqs = existing_craft.get('requirements', {})
        
        # Count non-empty requirement fields
        new_req_count = sum(1 for v in new_reqs.values() if v and str(v).strip())
        existing_req_count = sum(1 for v in existing_reqs.values() if v and str(v).strip())
        
        # Only update if significantly more complete requirements
        if new_req_count > existing_req_count + 1:
            return True
        
        # Check if new craft has more complete materials/outputs data
        new_materials = new_craft.get('materials', [])
        existing_materials = existing_craft.get('materials', [])
        new_outputs = new_craft.get('outputs', [])
        existing_outputs = existing_craft.get('outputs', [])
        
        # Prefer craft with more detailed material/output information
        if (len(new_materials) > len(existing_materials) or 
            len(new_outputs) > len(existing_outputs)):
            return True
        
        return False
    
    def _clean_craft_name(self, name: str) -> str:
        """Clean craft name by removing sequence prefixes like '1/2', '2/3', etc.
        
        Args:
            name: Original craft name
            
        Returns:
            Cleaned craft name
        """
        # Remove patterns like "1/2 ", "2/3 ", "1/4 " etc. at the start
        cleaned = re.sub(r'^\d+/\d+\s+', '', name.strip())
        return cleaned
    
    def _get_primary_material_name(self, materials: List[Dict[str, Any]]) -> str:
        """Extract the primary material name for name disambiguation.
        
        Args:
            materials: List of material dictionaries
            
        Returns:
            Name of the primary material (cleaned and capitalized)
        """
        if not materials or not isinstance(materials, list):
            return ""
        
        # Get the first material as primary (most recipes have one main ingredient)
        primary_material = materials[0]
        if not isinstance(primary_material, dict):
            return ""
        
        item_name = primary_material.get('item', '')
        if not item_name:
            return ""
        
        # Extract item name from BitCrafty ID format (item:profession:name)
        if ':' in item_name:
            item_parts = item_name.split(':')
            if len(item_parts) >= 3:
                item_name = item_parts[-1]  # Get the last part (actual item name)
        
        # Convert from kebab-case to Title Case
        if '-' in item_name:
            item_name = ' '.join(word.capitalize() for word in item_name.split('-'))
        elif '_' in item_name:
            item_name = ' '.join(word.capitalize() for word in item_name.split('_'))
        else:
            item_name = item_name.title()
        
        return item_name
    
    def _get_base_craft_name(self, name: str) -> str:
        """Extract base craft name by removing material disambiguation in parentheses.
        
        Args:
            name: Full craft name potentially with material disambiguation
            
        Returns:
            Base craft name without material specification
        """
        # Remove content in parentheses at the end
        base_name = re.sub(r'\s*\([^)]+\)\s*$', '', name.strip())
        return base_name
    
    def _disambiguate_craft_names(self, crafts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Disambiguate craft names by adding material specifications in parentheses.
        
        For crafts that share the same base name but have different materials,
        append the primary material name in parentheses to distinguish them.
        
        Args:
            crafts: List of craft dictionaries to process
            
        Returns:
            List of crafts with disambiguated names
        """
        if not crafts:
            return crafts
        
        # Group crafts by their base name
        name_groups = {}
        for i, craft in enumerate(crafts):
            if not isinstance(craft, dict):
                continue
                
            base_name = self._get_base_craft_name(craft.get('name', ''))
            if base_name not in name_groups:
                name_groups[base_name] = []
            name_groups[base_name].append((i, craft))
        
        # Process groups that have multiple crafts
        updated_crafts = list(crafts)  # Create a copy
        
        for base_name, craft_list in name_groups.items():
            if len(craft_list) <= 1:
                continue  # No disambiguation needed for single crafts
            
            # Check if crafts in this group have different materials
            materials_differ = False
            first_materials = None
            
            for _, craft in craft_list:
                materials = craft.get('materials', [])
                if first_materials is None:
                    first_materials = materials
                elif not self._materials_equal(materials, first_materials):
                    materials_differ = True
                    break
            
            if not materials_differ:
                continue  # No disambiguation needed if materials are the same
            
            # Disambiguate names by adding primary material
            for index, craft in craft_list:
                primary_material = self._get_primary_material_name(craft.get('materials', []))
                if primary_material:
                    # Check if name already has disambiguation
                    current_name = craft.get('name', '')
                    if not re.search(r'\([^)]+\)$', current_name):
                        # Add disambiguation
                        new_name = f"{base_name} ({primary_material})"
                        updated_crafts[index] = {**craft, 'name': new_name}
                        self.logger.info("Disambiguated craft name", 
                                       original=current_name,
                                       disambiguated=new_name,
                                       material=primary_material)
        
        return updated_crafts
    
    def _update_existing_craft_names(self):
        """Update existing crafts to add name disambiguation when needed.
        
        This ensures that if we have 'Make Basic Fertilizer' and then add
        'Make Basic Fertilizer (Fish)', we go back and update the first one
        to 'Make Basic Fertilizer (Berry)' or similar.
        """
        if not self.existing_crafts:
            return
        
        existing_crafts_list = list(self.existing_crafts.values())
        disambiguated_crafts = self._disambiguate_craft_names(existing_crafts_list)
        
        # Update the existing_crafts dict with new names
        updated_existing_crafts = {}
        for i, craft in enumerate(disambiguated_crafts):
            # Regenerate hash with new name if it changed
            original_craft = existing_crafts_list[i]
            if craft.get('name') != original_craft.get('name'):
                # Name changed, regenerate hash
                new_hash = self._generate_craft_hash(craft)
                craft['id'] = new_hash
                updated_existing_crafts[new_hash] = craft
                self.logger.info("Updated existing craft name with disambiguation",
                               original_name=original_craft.get('name'),
                               new_name=craft.get('name'),
                               new_hash=new_hash)
            else:
                # Name unchanged, keep original hash
                original_hash = self._generate_craft_hash(original_craft)
                updated_existing_crafts[original_hash] = craft
        
        self.existing_crafts = updated_existing_crafts
    
    def _disambiguate_new_craft_names(self, new_crafts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Disambiguate new craft names against existing crafts and each other.
        
        This handles the case where AI vision extracts generic names like "Make Basic Fertilizer"
        but the recipe actually uses specific materials like fish. We need to:
        1. Check if the base name conflicts with existing crafts with different materials
        2. Disambiguate by adding primary material in parentheses
        3. Also disambiguate within the current batch of new crafts
        
        Args:
            new_crafts: List of new craft dictionaries from AI extraction
            
        Returns:
            List of crafts with disambiguated names
        """
        if not new_crafts:
            return new_crafts
        
        # Combine existing and new crafts for comprehensive disambiguation
        all_crafts = []
        
        # Add existing crafts with their current names
        for existing_craft in self.existing_crafts.values():
            if isinstance(existing_craft, dict):
                all_crafts.append(existing_craft)
        
        # Add new crafts
        all_crafts.extend(new_crafts)
        
        # Group all crafts by base name
        name_groups = {}
        existing_indices = set()  # Track which indices are existing crafts
        new_craft_indices = {}    # Map new craft index to all_crafts index
        
        for i, craft in enumerate(all_crafts):
            if not isinstance(craft, dict):
                continue
                
            base_name = self._get_base_craft_name(craft.get('name', ''))
            if base_name not in name_groups:
                name_groups[base_name] = []
            name_groups[base_name].append((i, craft))
            
            # Track if this is an existing craft
            if i < len(self.existing_crafts):
                existing_indices.add(i)
            else:
                # This is a new craft
                new_craft_index = i - len(self.existing_crafts)
                new_craft_indices[new_craft_index] = i
        
        # Process groups that need disambiguation
        updated_new_crafts = list(new_crafts)  # Copy to modify
        crafts_to_update = []  # Track existing crafts that need name updates
        
        for base_name, craft_list in name_groups.items():
            if len(craft_list) <= 1:
                continue  # No disambiguation needed
            
            # Check if crafts have different materials
            unique_materials = set()
            for _, craft in craft_list:
                materials = craft.get('materials', [])
                materials_signature = self._get_materials_signature(materials)
                unique_materials.add(materials_signature)
            
            if len(unique_materials) <= 1:
                continue  # All crafts have same materials, no disambiguation needed
            
            # Need to disambiguate - add material names to all crafts in this group
            for index, craft in craft_list:
                primary_material = self._get_primary_material_name(craft.get('materials', []))
                if not primary_material:
                    continue  # Skip if we can't determine primary material
                
                current_name = craft.get('name', '')
                
                # Check if name already has disambiguation in parentheses
                if re.search(r'\([^)]+\)$', current_name):
                    continue  # Already disambiguated
                
                # Create disambiguated name
                new_name = f"{base_name} ({primary_material})"
                
                if index in existing_indices:
                    # This is an existing craft - mark for update
                    crafts_to_update.append((craft, new_name))
                    self.logger.info("Existing craft needs disambiguation", 
                                   original=current_name,
                                   disambiguated=new_name,
                                   reason="conflict_with_new_craft")
                else:
                    # This is a new craft - update directly
                    new_craft_index = index - len(self.existing_crafts)
                    if 0 <= new_craft_index < len(updated_new_crafts):
                        updated_new_crafts[new_craft_index] = {
                            **updated_new_crafts[new_craft_index], 
                            'name': new_name
                        }
                        self.logger.info("New craft name disambiguated", 
                                       original=current_name,
                                       disambiguated=new_name,
                                       material=primary_material)
        
        # Update existing crafts that need disambiguation
        for craft_to_update, new_name in crafts_to_update:
            # Find the craft in existing_crafts and update it
            for hash_key, existing_craft in self.existing_crafts.items():
                if existing_craft is craft_to_update:
                    # Update the name and regenerate hash
                    updated_craft = {**existing_craft, 'name': new_name}
                    new_hash = self._generate_craft_hash(updated_craft)
                    updated_craft['id'] = new_hash
                    
                    # Remove old entry and add updated one
                    del self.existing_crafts[hash_key]
                    self.existing_crafts[new_hash] = updated_craft
                    
                    self.logger.info("Updated existing craft with disambiguated name",
                                   old_name=existing_craft.get('name'),
                                   new_name=new_name,
                                   old_hash=hash_key,
                                   new_hash=new_hash)
                    break
        
        return updated_new_crafts
    
    def _get_materials_signature(self, materials: List[Dict[str, Any]]) -> str:
        """Create a signature string for materials list for comparison.
        
        Args:
            materials: List of material dictionaries
            
        Returns:
            String signature representing the materials
        """
        if not materials:
            return ""
        
        # Sort materials by item name and create signature
        sorted_materials = sorted(materials, key=lambda x: x.get('item', '') if isinstance(x, dict) else str(x))
        signature_parts = []
        
        for material in sorted_materials:
            if isinstance(material, dict):
                item = material.get('item', '')
                qty = material.get('qty', 1)
                signature_parts.append(f"{item}:{qty}")
            else:
                signature_parts.append(str(material))
        
        return "|".join(signature_parts)
    
    def _process_crafts(self, crafts: List[Dict[str, Any]], extracted_at: datetime) -> List[Dict[str, Any]]:
        """Process crafts and add new ones to the store."""
        new_crafts = []
        rejected_crafts = 0
        
        # First pass: clean and normalize craft names and materials
        processed_crafts = []
        for craft in crafts:
            # Clean the craft name first
            original_name = craft.get('name', '')
            cleaned_name = self._clean_craft_name(original_name)
            craft['name'] = cleaned_name
            
            if original_name != cleaned_name:
                self.logger.info("Cleaned craft name", 
                               original=original_name, 
                               cleaned=cleaned_name)
            
            # Normalize item names in materials and outputs
            craft = self._normalize_craft_materials_and_outputs(craft)
            processed_crafts.append(craft)
        
        # Second pass: disambiguate names by adding materials in parentheses where needed
        processed_crafts = self._disambiguate_new_craft_names(processed_crafts)
        
        # Third pass: process each craft for validation and storage
        for craft in processed_crafts:
            # Validate craft first
            validation = self._validate_craft(craft)
            if not validation['is_valid']:
                rejected_crafts += 1
                self.logger.info("Rejected craft", 
                               name=craft.get('name', 'unnamed'),
                               confidence=craft.get('confidence', 0),
                               requirements=craft.get('requirements', {}),
                               reasons=validation['reasons'])
                continue
            
            # Add extraction metadata
            processed_craft = {
                **craft,
                'extracted_at': extracted_at.isoformat(),
                'extraction_source': 'bitcrafty-extractor'
            }
            
            craft_hash = self._generate_craft_hash(processed_craft)
            
            # Check for exact duplicate first
            if craft_hash in self.existing_crafts:
                self.logger.debug("Exact duplicate craft found", name=craft.get('name'), hash=craft_hash)
                continue
            
            # For crafts with same name but different hash (different materials/requirements/outputs),
            # we should add them as separate crafts rather than trying to update existing ones.
            # Only update existing crafts if they have the same name AND very similar properties
            # but the new one has significantly better confidence or completeness.
            
            similar_crafts = self._find_similar_crafts(processed_craft)
            should_add_as_new = True
            
            if similar_crafts:
                # Check if any similar craft has nearly identical properties
                for existing_craft in similar_crafts:
                    existing_hash = self._generate_craft_hash(existing_craft)
                    
                    # If we find a very similar craft (not identical but close),
                    # check if we should update it
                    if self._are_crafts_very_similar(processed_craft, existing_craft):
                        if self._should_update_existing_craft(processed_craft, existing_craft):
                            # Update the existing craft with better information
                            self.logger.info("Updating existing similar craft with better information", 
                                           name=processed_craft.get('name'),
                                           old_confidence=existing_craft.get('confidence'),
                                           new_confidence=processed_craft.get('confidence'))
                            
                            # Remove old craft from existing crafts dict
                            if existing_hash in self.existing_crafts:
                                del self.existing_crafts[existing_hash]
                            
                            # Add the updated craft
                            processed_craft['id'] = craft_hash
                            self.existing_crafts[craft_hash] = processed_craft
                            new_crafts.append(processed_craft)
                            # Track updated crafts for session summary
                            self.session_new_crafts.append(processed_craft)
                            should_add_as_new = False
                            break
                        else:
                            # Don't update, but also don't add as new if very similar
                            self.logger.debug("Very similar craft exists with better/equal info", 
                                            name=processed_craft.get('name'))
                            should_add_as_new = False
                            break
            
            # Add as genuinely new craft if not similar enough to any existing craft
            if should_add_as_new:
                processed_craft['id'] = craft_hash
                self.existing_crafts[craft_hash] = processed_craft
                new_crafts.append(processed_craft)
                # Track new crafts for session summary
                self.session_new_crafts.append(processed_craft)
                
                self.logger.info("New craft discovered",
                               name=craft.get('name'),
                               craft_id=craft_hash,
                               confidence=craft.get('confidence'),
                               profession=craft.get('requirements', {}).get('profession'))
        
        # Fourth pass: After adding new crafts, update existing craft names for disambiguation
        if new_crafts:
            self._update_existing_craft_names()
        
        if rejected_crafts > 0:
            self.logger.info("Crafts validation summary", 
                           processed=len(crafts),
                           accepted=len(crafts) - rejected_crafts,
                           rejected=rejected_crafts)
        
        return new_crafts
    
    def _save_data(self):
        """Save current data to JSON files."""
        try:
            # Save items
            items_data = {
                'metadata': {
                    'version': '1.0',
                    'source': 'bitcrafty-extractor',
                    'last_updated': datetime.now().isoformat(),
                    'total_items': len(self.existing_items)
                },
                'items': list(self.existing_items.values())
            }
            
            with open(self.items_file, 'w', encoding='utf-8') as f:
                json.dump(items_data, f, indent=2, ensure_ascii=False)
            
            # Save crafts
            crafts_data = {
                'metadata': {
                    'version': '1.0',
                    'source': 'bitcrafty-extractor',
                    'last_updated': datetime.now().isoformat(),
                    'total_crafts': len(self.existing_crafts)
                },
                'crafts': list(self.existing_crafts.values())
            }
            
            with open(self.crafts_file, 'w', encoding='utf-8') as f:
                json.dump(crafts_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info("Saved data to exports",
                           items_file=str(self.items_file),
                           crafts_file=str(self.crafts_file),
                           items_count=len(self.existing_items),
                           crafts_count=len(self.existing_crafts))
            
        except Exception as e:
            self.logger.error("Failed to save export data", error=str(e))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current export statistics."""
        return {
            'total_items': len(self.existing_items),
            'total_crafts': len(self.existing_crafts),
            'items_file': str(self.items_file),
            'crafts_file': str(self.crafts_file),
            'exports_dir': str(self.exports_dir)
        }
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session-specific statistics for new discoveries."""
        # Safely extract item names with type checking
        item_names = []
        for item in self.session_new_items:
            if isinstance(item, dict):
                item_names.append(item.get('name', 'Unknown'))
            else:
                # Handle unexpected data types
                self.logger.warning("Unexpected item type in session", 
                                  item_type=type(item).__name__, 
                                  item_value=str(item)[:100])
                item_names.append(str(item) if item else 'Unknown')
        
        # Safely extract craft names with type checking  
        craft_names = []
        for craft in self.session_new_crafts:
            if isinstance(craft, dict):
                craft_names.append(craft.get('name', 'Unknown'))
            else:
                # Handle unexpected data types
                self.logger.warning("Unexpected craft type in session",
                                  craft_type=type(craft).__name__,
                                  craft_value=str(craft)[:100])
                craft_names.append(str(craft) if craft else 'Unknown')
        
        return {
            'session_new_items': self.session_new_items,
            'session_new_crafts': self.session_new_crafts,
            'session_new_items_count': len(self.session_new_items),
            'session_new_crafts_count': len(self.session_new_crafts),
            'session_new_item_names': item_names,
            'session_new_craft_names': craft_names
        }
    
    def reset_session_tracking(self):
        """Reset session tracking for a new session."""
        self.session_new_items = []
        self.session_new_crafts = []
        self.logger.info("Session tracking reset")
    
    def export_for_bitcrafty(self) -> Dict[str, str]:
        """Export data in BitCrafty-compatible format.
        
        Returns:
            Dict with paths to exported files
        """
        try:
            # Convert to BitCrafty format (items.json and crafts.json)
            bitcrafty_items_file = self.exports_dir / "bitcrafty_items.json"
            bitcrafty_crafts_file = self.exports_dir / "bitcrafty_crafts.json"
            
            # Transform items to BitCrafty format
            bitcrafty_items = []
            for item in self.existing_items.values():
                transformed = {
                    'id': f"item:extracted:{item['id']}",
                    'name': item.get('name', ''),
                    'description': item.get('description', ''),
                    'tier': item.get('tier'),
                    'rarity': item.get('rarity', 'common')
                }
                bitcrafty_items.append(transformed)
            
            # Transform crafts to BitCrafty format
            bitcrafty_crafts = []
            for craft in self.existing_crafts.values():
                transformed = {
                    'id': f"craft:extracted:{craft['id']}",
                    'name': craft.get('name', ''),
                    'materials': craft.get('materials', []),
                    'outputs': craft.get('outputs', []),
                    'requirements': craft.get('requirements', {})
                }
                bitcrafty_crafts.append(transformed)
            
            # Save in BitCrafty format
            with open(bitcrafty_items_file, 'w', encoding='utf-8') as f:
                json.dump(bitcrafty_items, f, indent=2, ensure_ascii=False)
            
            with open(bitcrafty_crafts_file, 'w', encoding='utf-8') as f:
                json.dump(bitcrafty_crafts, f, indent=2, ensure_ascii=False)
            
            self.logger.info("Exported BitCrafty-compatible files",
                           items_file=str(bitcrafty_items_file),
                           crafts_file=str(bitcrafty_crafts_file))
            
            return {
                'items_file': str(bitcrafty_items_file),
                'crafts_file': str(bitcrafty_crafts_file)
            }
            
        except Exception as e:
            self.logger.error("Failed to export BitCrafty format", error=str(e))
            return {}
