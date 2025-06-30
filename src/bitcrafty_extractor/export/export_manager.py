"""Export manager for saving extracted items and crafts to JSON files."""

import json
import hashlib
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
        
        for existing_item in self.existing_items:
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
        """Generate a unique hash for a craft based on key properties."""
        # Use name, materials, and outputs for hashing
        name = craft.get('name', '').lower().strip()
        
        # Normalize materials and outputs
        materials = craft.get('materials', [])
        outputs = craft.get('outputs', [])
        
        # Create sorted string representation for consistent hashing
        materials_str = "|".join(sorted([
            f"{m.get('item', '')}:{m.get('qty', 1)}" for m in materials
        ]))
        outputs_str = "|".join(sorted([
            f"{o.get('item', '')}:{o.get('qty', 1)}" for o in outputs
        ]))
        
        hash_string = f"{name}|{materials_str}|{outputs_str}"
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
        
        # Analyze duplicates before processing
        items_duplicate_analysis = self._analyze_items_for_duplicates(items)
        crafts_duplicate_analysis = self._analyze_crafts_for_duplicates(crafts)
        
        # Process items and crafts
        new_items = self._process_items(items, extracted_at)
        new_crafts = self._process_crafts(crafts, extracted_at)
        
        # Calculate validation statistics
        items_rejected = len(items) - len([i for i in items if self._validate_item(i)['is_valid']])
        crafts_rejected = len(crafts) - len([c for c in crafts if self._validate_craft(c)['is_valid']])
        
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
            'duplicate_crafts_details': crafts_duplicate_analysis['duplicates']
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
                else:
                    # Keep existing item, skip new one
                    self.logger.debug("Similar item exists with better/equal info", name=processed_item.get('name'))
                continue
            
            # This is a genuinely new item
            processed_item['id'] = item_hash
            self.existing_items[item_hash] = processed_item
            new_items.append(processed_item)
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
        """Find crafts with the same name but potentially different properties."""
        new_name = new_craft.get('name', '').lower().strip()
        similar_crafts = []
        
        for existing_craft in self.existing_crafts.values():
            existing_name = existing_craft.get('name', '').lower().strip()
            if new_name == existing_name:
                similar_crafts.append(existing_craft)
        
        return similar_crafts
    
    def _should_update_existing_craft(self, new_craft: Dict[str, Any], existing_craft: Dict[str, Any]) -> bool:
        """Determine if an existing craft should be updated with new information."""
        # Check if new craft has higher confidence
        new_confidence = new_craft.get('confidence', 0)
        existing_confidence = existing_craft.get('confidence', 0)
        
        if new_confidence > existing_confidence + 0.05:  # 5% threshold
            return True
        
        # Check if new craft has more complete requirements
        new_reqs = new_craft.get('requirements', {})
        existing_reqs = existing_craft.get('requirements', {})
        
        # Count non-empty requirement fields
        new_req_count = sum(1 for v in new_reqs.values() if v)
        existing_req_count = sum(1 for v in existing_reqs.values() if v)
        
        if new_req_count > existing_req_count:
            return True
        
        return False
        """Clean craft name by removing sequence prefixes like '1/2', '2/3', etc.
        
        Args:
            name: Original craft name
            
        Returns:
            Cleaned craft name
        """
        import re
        # Remove patterns like "1/2 ", "2/3 ", "1/4 " etc. at the start
        cleaned = re.sub(r'^\d+/\d+\s+', '', name.strip())
        return cleaned
    
    def _process_crafts(self, crafts: List[Dict[str, Any]], extracted_at: datetime) -> List[Dict[str, Any]]:
        """Process crafts and add new ones to the store."""
        new_crafts = []
        rejected_crafts = 0
        
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
            
            # Check for similar crafts (same name, different materials/outputs)
            similar_crafts = self._find_similar_crafts(processed_craft)
            if similar_crafts:
                # Found crafts with same name - decide whether to update or skip
                best_existing = max(similar_crafts, key=lambda x: x.get('confidence', 0))
                
                if self._should_update_existing_craft(processed_craft, best_existing):
                    # Update the existing craft with better information
                    old_hash = self._generate_craft_hash(best_existing)
                    self.logger.info("Updating existing craft with better information", 
                                   name=processed_craft.get('name'),
                                   old_confidence=best_existing.get('confidence'),
                                   new_confidence=processed_craft.get('confidence'))
                    
                    # Remove old craft from existing crafts dict
                    if old_hash in self.existing_crafts:
                        del self.existing_crafts[old_hash]
                    
                    # Add the updated craft
                    processed_craft['id'] = craft_hash
                    self.existing_crafts[craft_hash] = processed_craft
                    new_crafts.append(processed_craft)
                else:
                    # Keep existing craft, skip new one
                    self.logger.debug("Similar craft exists with better/equal info", name=processed_craft.get('name'))
                continue
            
            # This is a genuinely new craft
            processed_craft['id'] = craft_hash
            self.existing_crafts[craft_hash] = processed_craft
            new_crafts.append(processed_craft)
            
            self.logger.info("New craft discovered",
                           name=craft.get('name'),
                           craft_id=craft_hash,
                           confidence=craft.get('confidence'),
                           profession=craft.get('requirements', {}).get('profession'))
        
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
