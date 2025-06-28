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
    
    def _generate_item_hash(self, item: Dict[str, Any]) -> str:
        """Generate a unique hash for an item based on key properties."""
        # Use name and description for hashing (core identifying features)
        name = item.get('name', '').lower().strip()
        description = item.get('description', '').lower().strip()
        
        # Create hash from name + description
        hash_string = f"{name}|{description}"
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
            Dict with processing statistics
        """
        if extracted_at is None:
            extracted_at = datetime.now()
            
        items = data.get('items_found', [])
        crafts = data.get('crafts_found', [])
        
        # Process items
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
            'min_confidence_threshold': self.min_confidence
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
            
            if item_hash not in self.existing_items:
                # New item found
                processed_item['id'] = item_hash
                self.existing_items[item_hash] = processed_item
                new_items.append(processed_item)
                
                self.logger.info("New item discovered", 
                               name=item.get('name'),
                               item_id=item_hash,
                               confidence=item.get('confidence'))
            else:
                # Item exists, optionally update confidence or other metadata
                existing = self.existing_items[item_hash]
                new_confidence = item.get('confidence', 0)
                existing_confidence = existing.get('confidence', 0)
                
                if new_confidence > existing_confidence:
                    existing['confidence'] = new_confidence
                    existing['last_seen'] = datetime.now().isoformat()
                    
                    self.logger.info("Updated item confidence", 
                                   name=item.get('name'),
                                   old_confidence=existing_confidence,
                                   new_confidence=new_confidence)
        
        if rejected_items > 0:
            self.logger.info("Items validation summary", 
                           processed=len(items),
                           accepted=len(items) - rejected_items,
                           rejected=rejected_items)
        
        return new_items
    
    def _process_crafts(self, crafts: List[Dict[str, Any]], extracted_at: datetime) -> List[Dict[str, Any]]:
        """Process crafts and add new ones to the store."""
        new_crafts = []
        rejected_crafts = 0
        
        for craft in crafts:
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
            
            if craft_hash not in self.existing_crafts:
                # New craft found
                processed_craft['id'] = craft_hash
                self.existing_crafts[craft_hash] = processed_craft
                new_crafts.append(processed_craft)
                
                self.logger.info("New craft discovered",
                               name=craft.get('name'),
                               craft_id=craft_hash,
                               confidence=craft.get('confidence'),
                               profession=craft.get('requirements', {}).get('profession'))
            else:
                # Craft exists, optionally update confidence
                existing = self.existing_crafts[craft_hash]
                new_confidence = craft.get('confidence', 0)
                existing_confidence = existing.get('confidence', 0)
                
                if new_confidence > existing_confidence:
                    existing['confidence'] = new_confidence
                    existing['last_seen'] = datetime.now().isoformat()
                    
                    self.logger.info("Updated craft confidence",
                                   name=craft.get('name'),
                                   old_confidence=existing_confidence,
                                   new_confidence=new_confidence)
        
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
