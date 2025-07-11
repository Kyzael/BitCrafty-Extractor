import os
import json
import re
import sys
from copy import deepcopy
from datetime import datetime
import shutil
try:
    from deepdiff import DeepDiff
except ImportError:
    DeepDiff = None  # Will warn if diffing is attempted without it

# Import ExportManager for intelligent craft comparison
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from bitcrafty_extractor.export.export_manager import ExportManager

# Color codes for CLI output
class Colors:
    """ANSI color codes for terminal output"""
    # Text colors
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    
    # Background colors
    BG_RED = '\033[101m'
    BG_GREEN = '\033[102m'
    BG_YELLOW = '\033[103m'
    BG_BLUE = '\033[104m'
    
    # Formatting
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    ITALIC = '\033[3m'
    
    # Reset
    RESET = '\033[0m'
    
    @staticmethod
    def colorize(text, color):
        """Apply color to text"""
        return f"{color}{text}{Colors.RESET}"
    
    @staticmethod
    def success(text):
        """Green success message"""
        return f"{Colors.GREEN}✅ {text}{Colors.RESET}"
    
    @staticmethod
    def error(text):
        """Red error message"""
        return f"{Colors.RED}❌ {text}{Colors.RESET}"
    
    @staticmethod
    def warning(text):
        """Yellow warning message"""
        return f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}"
    
    @staticmethod
    def info(text):
        """Blue info message"""
        return f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}"
    
    @staticmethod
    def highlight(text):
        """Cyan highlighted text"""
        return f"{Colors.CYAN}{text}{Colors.RESET}"
    
    @staticmethod
    def bold(text):
        """Bold text"""
        return f"{Colors.BOLD}{text}{Colors.RESET}"
    
    @staticmethod
    def header(text):
        """Bold cyan header"""
        return f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}"
    
    @staticmethod
    def gray(text):
        """Gray dimmed text"""
        return f"{Colors.GRAY}{text}{Colors.RESET}"
    
    @staticmethod
    def section_divider(title, width=80):
        """Create a colored section divider"""
        padding = (width - len(title) - 2) // 2
        divider = "=" * padding + f" {title} " + "=" * padding
        if len(divider) < width:
            divider += "="
        return Colors.colorize(divider, Colors.BOLD + Colors.MAGENTA)

    @staticmethod
    def get_tier_color(tier):
        """Get color for tier display"""
        tier_colors = {
            1: Colors.GRAY,
            2: Colors.GREEN,
            3: Colors.BLUE,
            4: Colors.MAGENTA,
            5: Colors.YELLOW,
            6: Colors.RED
        }
        return tier_colors.get(tier, Colors.WHITE)
    
    @staticmethod
    def get_rarity_color(rarity):
        """Get color for rarity display"""
        rarity_colors = {
            'common': Colors.GRAY,
            'uncommon': Colors.GREEN,
            'rare': Colors.BLUE,
            'epic': Colors.MAGENTA,
            'legendary': Colors.YELLOW,
            'mythic': Colors.RED
        }
        return rarity_colors.get(rarity, Colors.WHITE)

# Enhanced print functions with colors
def print_success(message):
    print(Colors.success(message))

def print_error(message):
    print(Colors.error(message))

def print_warning(message):
    print(Colors.warning(message))

def print_info(message):
    print(Colors.info(message))

def print_header(message):
    print(Colors.header(message))

def print_highlight(message):
    print(Colors.highlight(message))

# Paths for extractor exports
EXPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'exports'))
ITEMS_EXPORT_PATH = os.path.join(EXPORTS_DIR, 'items.json')
CRAFTS_EXPORT_PATH = os.path.join(EXPORTS_DIR, 'crafts.json')

# Paths for BitCrafty canonical data
BITCRAFTY_DATA_DIR = r'G:\SC\BitCrafty\data'
BACKUPS_DIR = os.path.join(BITCRAFTY_DATA_DIR, 'backups')
ITEMS_DATA_PATH = os.path.join(BITCRAFTY_DATA_DIR, 'items.json')
CRAFTS_DATA_PATH = os.path.join(BITCRAFTY_DATA_DIR, 'crafts.json')
REQUIREMENTS_DATA_PATH = os.path.join(BITCRAFTY_DATA_DIR, 'requirements.json')
PROFESSIONS_META_PATH = os.path.join(BITCRAFTY_DATA_DIR, 'metadata', 'professions.json')
TOOLS_META_PATH = os.path.join(BITCRAFTY_DATA_DIR, 'metadata', 'tools.json')
BUILDINGS_META_PATH = os.path.join(BITCRAFTY_DATA_DIR, 'metadata', 'buildings.json')


def load_json(path):
    """Load JSON data from a file, return None if not found."""
    if not os.path.exists(path):
        print(f"[WARN] File not found: {path}")
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path, data):
    """Save JSON data to a file."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def clean_craft_name(name):
    """Clean craft name by removing AI-generated prefixes like '1/2', '2/3', etc."""
    # Remove patterns like "1/2 ", "2/3 ", "1/4 " at the start of craft names
    cleaned = re.sub(r'^\d+/\d+\s+', '', name.strip())
    return cleaned


def normalize_name(name):
    """Normalize name to BitCrafty ID format: lowercase, hyphens, no spaces, no apostrophes."""
    import re
    # Convert to lowercase first
    normalized = name.lower()
    # Remove apostrophes and single quotes
    normalized = normalized.replace("'", "").replace("'", "").replace("`", "")
    # Replace spaces and underscores with hyphens
    normalized = normalized.replace(' ', '-').replace('_', '-')
    # Remove any other invalid characters, keeping only letters, numbers, and hyphens
    normalized = re.sub(r'[^a-z0-9-]', '', normalized)
    # Remove multiple consecutive hyphens
    normalized = re.sub(r'-+', '-', normalized)
    # Remove leading/trailing hyphens
    normalized = normalized.strip('-')
    return normalized


def extract_profession_from_crafts(crafts_export):
    """Build mapping of item names to professions from craft data.
    Only maps items that are OUTPUTS of crafts to the craft's profession.
    Input materials should keep their original profession from where they are produced.
    """
    item_to_profession = {}
    
    if not crafts_export or 'crafts' not in crafts_export:
        return item_to_profession
    
    for craft in crafts_export['crafts']:
        profession = craft.get('requirements', {}).get('profession')
        if not profession:
            continue
        
        # Normalize profession name (lowercase, no apostrophes)
        normalized_profession = normalize_name(profession)
            
        # ONLY map output items to this profession (items that this craft creates)
        # Do NOT map input materials - they belong to whatever profession creates them
        for output in craft.get('outputs', []):
            item_name = output.get('item')
            if item_name:
                item_to_profession[item_name] = normalized_profession
                print(f"[DEBUG] Mapped output item '{item_name}' to profession '{normalized_profession}'")
    
    return item_to_profession


def transform_to_bitcrafty_id(entity_type, name, profession=None):
    """Transform entity to BitCrafty ID format: [entity-type]:[profession]:[identifier]"""
    normalized_name = normalize_name(name)
    
    if entity_type in ['item', 'craft'] and profession:
        # Ensure profession is also normalized (lowercase, no apostrophes)
        normalized_profession = normalize_name(profession)
        return f"{entity_type}:{normalized_profession}:{normalized_name}"
    elif entity_type == 'tool':
        # Tools don't use profession, extract base name (e.g., "Tier 1 Saw" -> "tool:saw")
        base_name = normalized_name.replace('tier-1-', '').replace('tier-2-', '').replace('tier-3-', '')
        return f"tool:{base_name}"
    elif entity_type == 'building':
        # Buildings similar to tools
        base_name = normalized_name.replace('tier-1-', '').replace('tier-2-', '').replace('tier-3-', '')
        return f"building:{base_name}"
    else:
        return f"{entity_type}:{normalized_name}"


def normalize_extractor_data(items_export, crafts_export):
    """Normalize extractor data to BitCrafty format."""
    normalized_items = {}
    normalized_crafts = {}
    
    # Build profession mapping from crafts (only for OUTPUT items)
    item_to_profession = extract_profession_from_crafts(crafts_export)
    
    # Create item name to ID mapping
    item_name_to_id = {}
    
    # Load existing BitCrafty items to check for name matches
    existing_bitcrafty_items = load_json(ITEMS_DATA_PATH) or []
    existing_item_names = {}
    existing_item_fuzzy_names = {}  # For fuzzy matching
    for item in existing_bitcrafty_items:
        name = item.get('name', '').strip()
        item_id = item.get('id')
        if name and item_id:
            existing_item_names[name] = item_id
            
            # Also create fuzzy matching entries
            # Remove common prefixes for fuzzy matching
            fuzzy_name = name
            for prefix in ['Plain ', 'Basic ', 'Simple ', 'Rough ']:
                fuzzy_name = fuzzy_name.replace(prefix, '').strip()
            
            if fuzzy_name != name:
                existing_item_fuzzy_names[fuzzy_name] = item_id
    
    # Normalize items - match BitCrafty format exactly
    if items_export and 'items' in items_export:
        for item in items_export['items']:
            name = item.get('name')
            if not name:
                continue
                
            profession = item_to_profession.get(name)
            if not profession:
                # Item has no profession mapping (not produced by any craft in our data)
                # Try to infer profession from name or skip for now
                inferred_profession = infer_profession_from_item_name(name)
                if inferred_profession:
                    profession = inferred_profession
                    print(f"[INFO] Inferred profession '{profession}' for item: {name}")
                else:
                    print(f"[WARN] No profession found for item: {name} - skipping")
                    continue
                
            bitcrafty_id = transform_to_bitcrafty_id('item', name, profession)
            # Match BitCrafty items.json format exactly and include description
            normalized_items[bitcrafty_id] = {
                'id': bitcrafty_id,
                'name': name,
                'description': item.get('description', ''),  # Include description from extractor exports
                'tier': item.get('tier', 1),
                'rank': item.get('rarity', 'Common').title()  # Use 'rank' not 'rarity', capitalize
            }
            item_name_to_id[name] = bitcrafty_id
    
    # Normalize crafts - match BitCrafty format exactly
    if crafts_export and 'crafts' in crafts_export:
        for craft in crafts_export['crafts']:
            name = craft.get('name')
            profession = craft.get('requirements', {}).get('profession')
            if not name or not profession:
                continue
            
            # Normalize profession name (lowercase, no apostrophes)
            normalized_profession = normalize_name(profession)
            
            # Clean the craft name of AI-generated prefixes
            cleaned_name = clean_craft_name(name)
            print(f"[DEBUG] Craft name: '{name}' -> '{cleaned_name}', profession: '{profession}' -> '{normalized_profession}'")
                
            bitcrafty_id = transform_to_bitcrafty_id('craft', cleaned_name, normalized_profession)
            
            # Transform materials to use item IDs
            materials = []
            for material in craft.get('materials', []):
                item_name = material.get('item')
                if item_name in item_name_to_id:
                    materials.append({
                        'item': item_name_to_id[item_name],
                        'qty': material.get('qty', 1)
                    })
                else:
                    # Check if this item already exists in BitCrafty first
                    existing_item_id = existing_item_names.get(item_name)
                    
                    # If no exact match, try fuzzy matching
                    if not existing_item_id:
                        # Try without common prefixes
                        fuzzy_name = item_name
                        for prefix in ['Plain ', 'Basic ', 'Simple ', 'Rough ']:
                            fuzzy_name = fuzzy_name.replace(prefix, '').strip()
                        
                        existing_item_id = existing_item_fuzzy_names.get(fuzzy_name)
                        if existing_item_id:
                            print(f"[INFO] Fuzzy match found for material '{item_name}' -> existing item with full name")
                    
                    if existing_item_id:
                        # For materials, we should prefer using existing items even if profession differs
                        # since materials come from other crafts and should maintain their original profession
                        materials.append({
                            'item': existing_item_id,
                            'qty': material.get('qty', 1)
                        })
                        item_name_to_id[item_name] = existing_item_id
                        print(f"[INFO] Using existing BitCrafty material: {item_name} -> {existing_item_id}")
                    else:
                        # For input materials, try to find existing ID in BitCrafty data
                        # or infer profession, but DON'T use the current craft's profession
                        inferred_profession = infer_profession_from_item_name(item_name)
                        if inferred_profession:
                            normalized_inferred = normalize_name(inferred_profession)
                            item_id = transform_to_bitcrafty_id('item', item_name, normalized_inferred)
                        else:
                            # Fallback: use foraging for raw materials, current profession otherwise
                            fallback_profession = get_fallback_profession_for_material(item_name, normalized_profession)
                            normalized_fallback = normalize_name(fallback_profession)
                            item_id = transform_to_bitcrafty_id('item', item_name, normalized_fallback)
                            print(f"[WARN] Using fallback profession '{normalized_fallback}' for material: {item_name}")
                        
                        materials.append({
                            'item': item_id,
                            'qty': material.get('qty', 1)
                        })
                        # Also create the missing item entry
                        if item_id not in normalized_items:
                            normalized_items[item_id] = {
                                'id': item_id,
                                'name': item_name,
                                'description': '',  # Placeholder description for missing items
                                'tier': 1,
                                'rank': 'Common'
                            }
                            item_name_to_id[item_name] = item_id
                            print(f"[INFO] Created missing material item: {item_id}")
            
            # Transform outputs to use item IDs (these should already be mapped)
            outputs = []
            for output in craft.get('outputs', []):
                item_name = output.get('item')
                if item_name in item_name_to_id:
                    outputs.append({
                        'item': item_name_to_id[item_name],
                        'qty': output.get('qty', 1)
                    })
                else:
                    # Check if this item already exists in BitCrafty with a different profession
                    existing_item_id = existing_item_names.get(item_name)
                    
                    # If no exact match, try fuzzy matching
                    if not existing_item_id:
                        # Try without common prefixes
                        fuzzy_name = item_name
                        for prefix in ['Plain ', 'Basic ', 'Simple ', 'Rough ']:
                            fuzzy_name = fuzzy_name.replace(prefix, '').strip()
                        
                        existing_item_id = existing_item_fuzzy_names.get(fuzzy_name)
                        if existing_item_id:
                            print(f"[INFO] Fuzzy match found for '{item_name}' -> existing item with full name")
                    
                    if existing_item_id:
                        # Validate if the existing item matches what this craft should produce
                        existing_profession = existing_item_id.split(':')[1] if ':' in existing_item_id else None
                        expected_profession = normalized_profession
                        
                        if existing_profession == expected_profession:
                            # Perfect match - use existing item
                            outputs.append({
                                'item': existing_item_id,
                                'qty': output.get('qty', 1)
                            })
                            item_name_to_id[item_name] = existing_item_id
                            print(f"[INFO] Using existing BitCrafty item: {item_name} -> {existing_item_id}")
                        else:
                            # Profession mismatch - this craft should create a new item with correct profession
                            correct_item_id = transform_to_bitcrafty_id('item', item_name, normalized_profession)
                            outputs.append({
                                'item': correct_item_id,
                                'qty': output.get('qty', 1)
                            })
                            item_name_to_id[item_name] = correct_item_id
                            
                            print(f"[WARN] Profession mismatch for '{item_name}':")
                            print(f"  Existing: {existing_item_id} (profession: {existing_profession})")
                            print(f"  Expected: {correct_item_id} (profession: {expected_profession})")
                            print(f"  Creating new item with correct profession for craft output")
                            
                            # Create the new item entry with correct profession
                            if correct_item_id not in normalized_items:
                                normalized_items[correct_item_id] = {
                                    'id': correct_item_id,
                                    'name': item_name,
                                    'description': '',  # Placeholder description for new items
                                    'tier': 1,
                                    'rank': 'Common'
                                }
                                print(f"[INFO] Created new output item with correct profession: {correct_item_id}")
                    else:
                        # No existing item found - create new one with craft's profession
                        item_id = transform_to_bitcrafty_id('item', item_name, normalized_profession)
                        outputs.append({
                            'item': item_id,
                            'qty': output.get('qty', 1)
                        })
                        # Also create the missing item entry
                        if item_id not in normalized_items:
                            normalized_items[item_id] = {
                                'id': item_id,
                                'name': item_name,
                                'description': '',  # Placeholder description for missing items
                                'tier': 1,
                                'rank': 'Common'
                            }
                            item_name_to_id[item_name] = item_id
                            print(f"[INFO] Created missing output item: {item_id}")
            
            # Match BitCrafty crafts.json format exactly
            normalized_crafts[bitcrafty_id] = {
                'id': bitcrafty_id,
                'name': cleaned_name,
                'materials': materials,
                'outputs': outputs,
                'requirements': craft.get('requirements', {})  # Keep for now, will be replaced with requirement ID
            }
    
    return normalized_items, normalized_crafts


def infer_profession_from_item_name(item_name):
    """Infer profession from item name based on common patterns."""
    name_lower = item_name.lower()
    
    # Common patterns for different professions
    if any(word in name_lower for word in ['wood', 'log', 'trunk', 'stripped', 'plank']):
        return 'carpentry'
    elif any(word in name_lower for word in ['thread', 'spool', 'cloth', 'fabric']):
        return 'tailoring'  
    elif any(word in name_lower for word in ['mushroom', 'berry', 'fruit', 'vegetable']):
        return 'foraging'
    elif any(word in name_lower for word in ['clay', 'stone', 'ore', 'metal', 'pot', 'brick', 'glass']):
        return 'mining'  # Pottery items (pots) are often made from clay, so mining
    elif any(word in name_lower for word in ['sap', 'resin']):
        return 'forestry'
    elif any(word in name_lower for word in ['seed', 'fertilizer', 'grain']):
        return 'farming'
    
    return None


def get_fallback_profession_for_material(item_name, current_craft_profession):
    """Get fallback profession for materials that can't be inferred."""
    # Try to infer first
    inferred = infer_profession_from_item_name(item_name)
    if inferred:
        return inferred
    
    # Common fallbacks for raw materials
    name_lower = item_name.lower()
    if any(word in name_lower for word in ['basic', 'raw', 'rough']):
        return 'foraging'  # Most basic items come from foraging
    
    # If all else fails, use current craft profession
    return current_craft_profession


def load_bitcrafty_data(items_data, crafts_data):
    """Load and index BitCrafty data by ID."""
    bitcrafty_items = {}
    bitcrafty_crafts = {}
    
    # Load items
    if items_data:
        for item in items_data:
            item_id = item.get('id')
            if item_id:
                bitcrafty_items[item_id] = item
    
    # Load crafts
    if crafts_data:
        for craft in crafts_data:
            craft_id = craft.get('id')
            if craft_id:
                bitcrafty_crafts[craft_id] = craft
    
    return bitcrafty_items, bitcrafty_crafts


def resolve_craft_name_conflicts(normalized_crafts):
    """Resolve craft name conflicts by adding input materials to ID and name."""
    # Group crafts by base name
    name_groups = {}
    for craft_id, craft in normalized_crafts.items():
        base_name = craft['name']
        if base_name not in name_groups:
            name_groups[base_name] = []
        name_groups[base_name].append((craft_id, craft))
    
    # Update crafts with conflicts
    updated_crafts = {}
    for base_name, craft_list in name_groups.items():
        if len(craft_list) == 1:
            # No conflict, keep as is
            craft_id, craft = craft_list[0]
            updated_crafts[craft_id] = craft
        else:
            # Multiple crafts with same name, differentiate by main input
            print(f"[INFO] Resolving {len(craft_list)} craft name conflicts for: {base_name}")
            for craft_id, craft in craft_list:
                # Get main input material for differentiation
                main_input = ""
                if craft.get('inputs') and len(craft['inputs']) > 0:
                    main_material = craft['inputs'][0].get('item', '')
                    main_input = normalize_name(main_material.replace('item:', '').split(':')[-1])
                
                if main_input:
                    # Update craft name and ID
                    profession = craft_id.split(':')[1]  # Extract profession from existing ID
                    base_craft_name = normalize_name(base_name)
                    new_id = f"craft:{profession}:{base_craft_name}-{main_input}"
                    new_name = f"{base_name} ({main_material})"
                    
                    craft['id'] = new_id
                    craft['name'] = new_name
                    updated_crafts[new_id] = craft
                    
                    print(f"  Updated: {craft_id} -> {new_id}")
                    print(f"    Name: {base_name} -> {new_name}")
                else:
                    # Fallback: keep original if no main input found
                    updated_crafts[craft_id] = craft
                    print(f"  [WARN] No main input found for: {craft_id}")
    
    return updated_crafts


def find_items_needing_descriptions(bitcrafty_items, items_export):
    """Find existing BitCrafty items that are missing descriptions but have them in extractor exports."""
    items_needing_descriptions = {}
    
    if not items_export or 'items' not in items_export:
        return items_needing_descriptions
    
    # Create name-to-description mapping from extractor exports
    extractor_descriptions = {}
    for item in items_export['items']:
        name = item.get('name', '').strip()
        description = item.get('description', '') or ''  # Handle None case
        description = description.strip()
        if name and description:
            extractor_descriptions[name] = description
    
    # Find BitCrafty items missing descriptions
    for item_id, item in bitcrafty_items.items():
        item_name = item.get('name', '').strip()
        existing_description = item.get('description', '') or ''  # Handle None case
        existing_description = existing_description.strip()
        
        # If item has no description but extractor has one for this name
        if not existing_description and item_name in extractor_descriptions:
            items_needing_descriptions[item_id] = {
                'existing': item,
                'description': extractor_descriptions[item_name],
                'reason': f"Adding missing description for '{item_name}'"
            }
            print(f"[INFO] Found missing description for: {item_id} ({item_name})")
    
    return items_needing_descriptions


def intelligent_craft_comparison(normalized_craft, existing_craft, export_manager):
    """Use ExportManager's intelligent logic to determine if craft should be updated.
    
    Args:
        normalized_craft: Normalized extractor craft data
        existing_craft: Existing BitCrafty craft data  
        export_manager: ExportManager instance for comparison logic
        
    Returns:
        tuple: (should_update: bool, reason: str)
    """
    try:
        # Convert BitCrafty format back to extractor format for comparison
        extractor_format_existing = {
            'name': existing_craft.get('name', ''),
            'materials': existing_craft.get('materials', []),
            'outputs': existing_craft.get('outputs', []),
            'requirements': {
                'profession': 'unknown',  # Will be inferred from requirement
                'building': 'unknown',
                'tool': 'unknown'
            },
            'confidence': 0.95,  # Assume existing data is high confidence
            'id': existing_craft.get('id', '')
        }
        
        # Use ExportManager's intelligent comparison logic
        should_update = export_manager._should_update_existing_craft(
            normalized_craft, extractor_format_existing
        )
        
        if should_update:
            # Determine the reason for update
            reasons = []
            
            # Check quantity improvements
            if export_manager._has_better_quantities(normalized_craft, extractor_format_existing):
                reasons.append("better quantities")
                
            # Check materials/outputs differences
            new_materials = normalized_craft.get('materials', [])
            old_materials = existing_craft.get('materials', [])
            if len(new_materials) != len(old_materials):
                reasons.append("material count difference")
                
            new_outputs = normalized_craft.get('outputs', [])
            old_outputs = existing_craft.get('outputs', [])
            if len(new_outputs) != len(old_outputs):
                reasons.append("output count difference")
                
            reason = f"ExportManager logic: {', '.join(reasons) if reasons else 'general improvements'}"
        else:
            reason = "No improvements detected by ExportManager logic"
            
        return should_update, reason
        
    except Exception as e:
        print(f"[WARNING] Error in intelligent craft comparison: {e}")
        # Fallback to simple comparison
        return False, f"Error in intelligent comparison: {e}"


def intelligent_craft_merge(existing_craft, new_craft, export_manager):
    """Use ExportManager's intelligent merging to create updated craft.
    
    Args:
        existing_craft: Existing BitCrafty craft data
        new_craft: New normalized extractor craft data
        export_manager: ExportManager instance for merging logic
        
    Returns:
        dict: Merged craft data in BitCrafty format
    """
    try:
        # Convert BitCrafty format to extractor format for merging
        extractor_format_existing = {
            'name': existing_craft.get('name', ''),
            'materials': existing_craft.get('materials', []),
            'outputs': existing_craft.get('outputs', []),
            'requirements': {
                'profession': 'unknown',
                'building': 'unknown', 
                'tool': 'unknown'
            },
            'confidence': 0.95,
            'id': existing_craft.get('id', '')
        }
        
        # Use ExportManager's merge logic
        merged_craft = export_manager._merge_craft_data(extractor_format_existing, new_craft)
        
        # Convert back to BitCrafty format
        bitcrafty_format = {
            'id': existing_craft.get('id', ''),  # Keep original ID
            'name': merged_craft.get('name', ''),
            'materials': merged_craft.get('materials', []),
            'outputs': merged_craft.get('outputs', []),
            'requirement': existing_craft.get('requirement', '')  # Keep original requirement format
        }
        
        return bitcrafty_format
        
    except Exception as e:
        print(f"[WARNING] Error in intelligent craft merge: {e}")
        # Fallback to new craft data
        return clean_craft_for_bitcrafty(new_craft)


def compare_entities(normalized_items, normalized_crafts, bitcrafty_items, bitcrafty_crafts):
    """Compare normalized extractor data with BitCrafty data using intelligent logic."""
    
    # Create ExportManager instance for intelligent craft comparison
    try:
        export_manager = ExportManager()
        print_info("Using ExportManager for intelligent craft comparison...")
    except Exception as e:
        print(f"[WARNING] Could not create ExportManager: {e}")
        export_manager = None
    
    changes = {
        'items': {
            'new': {},
            'updated': {},
            'identical': {},
            'id_updates': {},  # Items that need ID changes due to name matches
            'description_updates': {}  # Items that need description updates
        },
        'crafts': {
            'new': {},
            'updated': {},
            'identical': {}
        }
    }
    
    # Create name-to-item mapping for BitCrafty items
    bitcrafty_by_name = {}
    for item_id, item in bitcrafty_items.items():
        name = item.get('name', '').strip()
        if name:
            bitcrafty_by_name[name] = (item_id, item)
    
    # Compare items by name first, then by ID
    for item_id, item in normalized_items.items():
        item_name = item.get('name', '').strip()
        
        # Check if an item with this name already exists in BitCrafty
        if item_name in bitcrafty_by_name:
            existing_id, existing_item = bitcrafty_by_name[item_name]
            
            if existing_id != item_id:
                # Same name, different ID - need to update BitCrafty to use our ID
                changes['items']['id_updates'][existing_id] = {
                    'old_id': existing_id,
                    'new_id': item_id,
                    'existing': existing_item,
                    'new': item,
                    'reason': f"Name match: '{item_name}'"
                }
                print(f"[INFO] ID update needed: {existing_id} -> {item_id} (name: {item_name})")
            else:
                # Same name and ID - check for other differences
                if (item.get('description') != existing_item.get('description') or 
                    item.get('tier') != existing_item.get('tier') or
                    item.get('rank') != existing_item.get('rank')):
                    changes['items']['updated'][item_id] = {
                        'existing': existing_item,
                        'new': item,
                        'changes': []
                    }
                else:
                    changes['items']['identical'][item_id] = item
        else:
            # Check by ID if not found by name
            if item_id in bitcrafty_items:
                existing = bitcrafty_items[item_id]
                if (item.get('name') != existing.get('name') or 
                    item.get('description') != existing.get('description') or
                    item.get('tier') != existing.get('tier') or
                    item.get('rank') != existing.get('rank')):
                    changes['items']['updated'][item_id] = {
                        'existing': existing,
                        'new': item,
                        'changes': []
                    }
                else:
                    changes['items']['identical'][item_id] = item
            else:
                # Completely new item
                changes['items']['new'][item_id] = item        # Compare crafts using intelligent logic
        for craft_id, craft in normalized_crafts.items():
            if craft_id in bitcrafty_crafts:
                existing = bitcrafty_crafts[craft_id]
                
                if export_manager:
                    # Use intelligent comparison
                    should_update, reason = intelligent_craft_comparison(craft, existing, export_manager)
                    if should_update:
                        changes['crafts']['updated'][craft_id] = {
                            'existing': existing,
                            'new': craft,
                            'changes': [reason]
                        }
                        print(f"[INFO] Craft update needed: {craft_id} - {reason}")
                    else:
                        changes['crafts']['identical'][craft_id] = craft
                        print(f"[DEBUG] Craft unchanged: {craft_id} - {reason}")
                else:
                    # Fallback to simple comparison
                    if (craft.get('name') != existing.get('name') or 
                        craft.get('materials') != existing.get('materials') or
                        craft.get('outputs') != existing.get('outputs') or
                        craft.get('requirement') != existing.get('requirement')):
                        changes['crafts']['updated'][craft_id] = {
                            'existing': existing,
                            'new': craft,
                            'changes': ['Simple field comparison']
                        }
                    else:
                        changes['crafts']['identical'][craft_id] = craft
            else:
                changes['crafts']['new'][craft_id] = craft
    
    return changes


def update_craft_item_references(normalized_crafts, id_updates):
    """Update craft item references to use updated item IDs."""
    old_to_new_id = {}
    for old_id, update_info in id_updates.items():
        old_to_new_id[old_id] = update_info['new_id']
    
    updated_crafts = {}
    for craft_id, craft in normalized_crafts.items():
        updated_craft = deepcopy(craft)
        
        # Update materials (BitCrafty uses 'materials' not 'inputs')
        if 'materials' in updated_craft:
            for material in updated_craft['materials']:
                item_ref = material.get('item', '')
                if item_ref in old_to_new_id:
                    old_ref = item_ref
                    new_ref = old_to_new_id[item_ref]
                    material['item'] = new_ref
                    print(f"[INFO] Updated craft material: {old_ref} -> {new_ref} in {craft_id}")
        
        # Update outputs
        if 'outputs' in updated_craft:
            for output in updated_craft['outputs']:
                item_ref = output.get('item', '')
                if item_ref in old_to_new_id:
                    old_ref = item_ref
                    new_ref = old_to_new_id[item_ref]
                    output['item'] = new_ref
                    print(f"[INFO] Updated craft output: {old_ref} -> {new_ref} in {craft_id}")
        
        updated_crafts[craft_id] = updated_craft
    
    return updated_crafts


def extract_metadata_from_crafts(normalized_crafts):
    """Extract tools, buildings, and professions from normalized crafts."""
    professions = set()
    tools = set()
    buildings = set()
    
    for craft_id, craft in normalized_crafts.items():
        requirements = craft.get('requirements', {})
        
        # Extract profession and normalize it
        profession = requirements.get('profession')
        if profession:
            normalized_profession = normalize_name(profession)
            professions.add(normalized_profession)
        
        # Extract tool
        tool = requirements.get('tool')
        if tool and tool != 'null' and tool is not None:
            # Clean tool name (remove "Tier 1", etc.)
            clean_tool = tool.lower().replace('tier 1 ', '').replace('tier 2 ', '').replace('tier 3 ', '')
            tools.add(clean_tool)
        
        # Extract building
        building = requirements.get('building')
        if building and building != 'null' and building is not None:
            # Clean building name and extract the actual building name
            clean_building = building.lower().replace('tier 1 ', '').replace('tier 2 ', '').replace('tier 3 ', '')
            
            # Extract building type (e.g., "carpentry station" -> "station", "kiln" -> "kiln")
            if 'station' in clean_building:
                buildings.add('station')  # Generic station
            elif 'kiln' in clean_building:
                buildings.add('kiln')
            elif 'well' in clean_building:
                buildings.add('well')
            elif 'loom' in clean_building:
                buildings.add('loom')
            else:
                # Use the whole building name if no special handling
                buildings.add(clean_building)
    
    return professions, tools, buildings


def compare_metadata(extracted_professions, extracted_tools, extracted_buildings, 
                    professions_meta, tools_meta, buildings_meta):
    """Compare extracted metadata with existing BitCrafty metadata."""
    
    metadata_changes = {
        'professions': {'new': [], 'existing': []},
        'tools': {'new': [], 'existing': []},
        'buildings': {'new': [], 'existing': []}
    }
    
    # Compare professions
    existing_professions = set()
    if professions_meta:
        for prof in professions_meta:
            prof_name = prof.get('name', '')
            if prof_name:
                # Use normalize_name for consistency
                existing_professions.add(normalize_name(prof_name))

    for profession in extracted_professions:
        normalized_profession = normalize_name(profession)
        if normalized_profession in existing_professions:
            metadata_changes['professions']['existing'].append(profession)
            print(f"[DEBUG] Profession already exists: {profession}")
        else:
            metadata_changes['professions']['new'].append(profession)
            print(f"[INFO] New profession found: {profession}")

    # Compare tools
    existing_tools = set()
    if tools_meta:
        for tool in tools_meta:
            existing_tools.add(tool.get('name', '').lower())

    for tool in extracted_tools:
        if tool.lower() in existing_tools:
            metadata_changes['tools']['existing'].append(tool)
            print(f"[DEBUG] Tool already exists: {tool}")
        else:
            metadata_changes['tools']['new'].append(tool)
            print(f"[INFO] New tool found: {tool}")

    # Compare buildings - check by building type and profession context
    existing_building_ids = set()
    if buildings_meta:
        for building in buildings_meta:
            existing_building_ids.add(building.get('id', ''))

    for building in extracted_buildings:
        building_exists = False
        
        if building == 'station':
            # For stations, check if profession-specific stations exist
            # We'll need to check this during requirements processing
            building_exists = False  # Will be checked per profession later
        elif building == 'kiln':
            # Check if any kiln exists (regardless of profession)
            kiln_exists = any('kiln' in bid for bid in existing_building_ids)
            building_exists = kiln_exists
        else:
            # For other buildings, check generically
            building_exists = any(building.lower() in bid.lower() for bid in existing_building_ids)
        
        if building_exists:
            metadata_changes['buildings']['existing'].append(building)
            print(f"[DEBUG] Building already exists: {building}")
        else:
            metadata_changes['buildings']['new'].append(building)
            print(f"[INFO] New building found: {building}")
    
    return metadata_changes


def create_new_metadata_entries(metadata_changes, normalized_crafts):
    """Create new metadata entries for professions, tools, and buildings."""
    
    new_metadata = {
        'professions': [],
        'tools': [],
        'buildings': []
    }
    
    # Create new profession entries with white color
    for profession in metadata_changes['professions']['new']:
        new_metadata['professions'].append({
            'name': profession,
            'color': '#FFFFFF',  # Default white color for new professions
            'description': f"Auto-generated profession: {profession.title()}"
        })
    
    # Create new tool entries
    for tool in metadata_changes['tools']['new']:
        tool_id = f"tool:{normalize_name(tool)}"
        new_metadata['tools'].append({
            'id': tool_id,
            'name': tool.title(),
            'description': f"Auto-generated tool: {tool.title()}"
        })
    
    # Create new building entries based on actual missing building IDs
    missing_building_ids = metadata_changes.get('missing_building_ids', [])
    for building_id in missing_building_ids:
        if ':' in building_id:
            building_name = building_id.split(':')[-1].replace('-', ' ').title()
            new_metadata['buildings'].append({
                'id': building_id,
                'name': building_name
            })
            print(f"[DEBUG] Will create building: {building_id} -> {building_name}")
    
    return new_metadata


def print_comparison_summary(changes, metadata_changes=None, new_metadata=None, requirement_changes=None):
    """Print a summary of the comparison results."""
    print("\n" + Colors.section_divider("RECONCILIATION SUMMARY"))
    
    # Items summary
    items = changes['items']
    print_header("\nITEMS:")
    print(f"  {Colors.highlight('New items to add:')} {Colors.bold(str(len(items['new'])))}")
    print(f"  {Colors.highlight('Items to update:')} {Colors.bold(str(len(items['updated'])))}")
    print(f"  {Colors.highlight('Items needing ID updates:')} {Colors.bold(str(len(items['id_updates'])))}")
    print(f"  {Colors.highlight('Items needing description updates:')} {Colors.bold(str(len(items.get('description_updates', {}))))}")
    print(f"  {Colors.highlight('Identical items:')} {Colors.gray(str(len(items['identical'])))}")
    
    if items['new']:
        print(f"\n  {Colors.colorize('New items:', Colors.GREEN)}")
        for item_id, item in list(items['new'].items())[:5]:  # Show first 5
            print(f"    {Colors.colorize('+', Colors.GREEN)} {Colors.highlight(item_id)}: {item.get('name')}")
        if len(items['new']) > 5:
            remaining = len(items['new']) - 5
            print(f"    {Colors.gray(f'... and {remaining} more')}")
    
    if items.get('description_updates'):
        print(f"\n  {Colors.colorize('Items needing description updates:', Colors.CYAN)}")
        for item_id, update_info in list(items['description_updates'].items())[:5]:  # Show first 5
            item_name = update_info['existing']['name']
            description_preview = update_info['description'][:50] + ('...' if len(update_info['description']) > 50 else '')
            print(f"    {Colors.colorize('📝', Colors.CYAN)} {Colors.highlight(item_id)}: {item_name}")
            print(f"      {Colors.gray(f'Description: {description_preview}')}")
        if len(items['description_updates']) > 5:
            remaining = len(items['description_updates']) - 5
            print(f"    {Colors.gray(f'... and {remaining} more')}")
    
    if items['id_updates']:
        print(f"\n  {Colors.colorize('Items needing ID updates:', Colors.YELLOW)}")
        for old_id, update_info in list(items['id_updates'].items())[:5]:
            print(f"    {Colors.colorize('~', Colors.YELLOW)} {Colors.highlight(old_id)} → {Colors.highlight(update_info['new_id'])}")
            print(f"      {Colors.gray(f'Reason: {update_info['reason']}')}")
        if len(items['id_updates']) > 5:
            remaining = len(items['id_updates']) - 5
            print(f"    {Colors.gray(f'... and {remaining} more')}")
    
    # Crafts summary
    crafts = changes['crafts']
    print_header("\nCRAFTS:")
    print(f"  {Colors.highlight('New crafts to add:')} {Colors.bold(str(len(crafts['new'])))}")
    print(f"  {Colors.highlight('Crafts to update:')} {Colors.bold(str(len(crafts['updated'])))}")
    print(f"  {Colors.highlight('Identical crafts:')} {Colors.gray(str(len(crafts['identical'])))}")
    
    if crafts['new']:
        print(f"\n  {Colors.colorize('New crafts:', Colors.GREEN)}")
        for craft_id, craft in list(crafts['new'].items())[:5]:  # Show first 5
            print(f"    {Colors.colorize('+', Colors.GREEN)} {Colors.highlight(craft_id)}: {craft.get('name')}")
        if len(crafts['new']) > 5:
            remaining = len(crafts['new']) - 5
            print(f"    {Colors.gray(f'... and {remaining} more')}")
    
    # Requirements summary
    if requirement_changes:
        print_header("\nREQUIREMENTS:")
        print(f"  {Colors.highlight('New requirements to add:')} {Colors.bold(str(len(requirement_changes['new'])))}")
        print(f"  {Colors.highlight('Requirements to update:')} {Colors.bold(str(len(requirement_changes['updated'])))}")
        print(f"  {Colors.highlight('Existing requirements:')} {Colors.gray(str(len(requirement_changes['existing'])))}")
        
        if requirement_changes['new']:
            print(f"\n  {Colors.colorize('New requirements:', Colors.GREEN)}")
            for req_id, req_data in list(requirement_changes['new'].items())[:5]:
                craft_count = len(req_data['crafts'])
                print(f"    {Colors.colorize('+', Colors.GREEN)} {Colors.highlight(req_id)}: {req_data['entry']['name']} {Colors.gray(f'(used by {craft_count} crafts)')}")
            if len(requirement_changes['new']) > 5:
                remaining = len(requirement_changes['new']) - 5
                print(f"    {Colors.gray(f'... and {remaining} more')}")
    
    # Metadata summary
    if metadata_changes and new_metadata:
        print_header("\nMETADATA:")
        
        # Professions
        new_profs = len(new_metadata['professions'])
        existing_profs = len(metadata_changes['professions']['existing'])
        print(f"  {Colors.highlight('Professions')} - New: {Colors.bold(str(new_profs))}, Existing: {Colors.gray(str(existing_profs))}")
        if new_metadata['professions']:
            print(f"    {Colors.colorize('New professions (white color):', Colors.GREEN)}")
            for prof in new_metadata['professions']:
                print(f"      {Colors.colorize('+', Colors.GREEN)} {Colors.highlight(prof['name'])}")
        
        # Tools
        new_tools = len(new_metadata['tools'])
        existing_tools = len(metadata_changes['tools']['existing'])
        print(f"  {Colors.highlight('Tools')} - New: {Colors.bold(str(new_tools))}, Existing: {Colors.gray(str(existing_tools))}")
        if new_metadata['tools']:
            print(f"    {Colors.colorize('New tools:', Colors.GREEN)}")
            for tool in new_metadata['tools']:
                print(f"      {Colors.colorize('+', Colors.GREEN)} {Colors.highlight(tool['id'])}: {tool['name']}")
        
        # Buildings
        new_buildings = len(new_metadata['buildings'])
        existing_buildings = len(metadata_changes['buildings']['existing'])
        print(f"  {Colors.highlight('Buildings')} - New: {Colors.bold(str(new_buildings))}, Existing: {Colors.gray(str(existing_buildings))}")
        if new_metadata['buildings']:
            print(f"    {Colors.colorize('New buildings:', Colors.GREEN)}")
            for building in new_metadata['buildings']:
                print(f"      {Colors.colorize('+', Colors.GREEN)} {Colors.highlight(building['id'])}: {building['name']}")


def check_building_requirements_exist(extracted_requirements, buildings_meta):
    """Check which building requirements are missing from BitCrafty metadata."""
    existing_building_ids = set()
    if buildings_meta:
        for building in buildings_meta:
            existing_building_ids.add(building.get('id', ''))
    
    missing_buildings = []
    
    for signature, req_data in extracted_requirements.items():
        req_entry = req_data['entry']
        building_ref = req_entry.get('building', {}).get('name')
        
        if building_ref and building_ref not in existing_building_ids:
            missing_buildings.append(building_ref)
            print(f"[INFO] Missing building: {building_ref}")
        else:
            print(f"[DEBUG] Building exists: {building_ref}")
    
    return missing_buildings


def main():
    # Load all relevant data
    print_info("Loading extractor exports and BitCrafty data...")
    items_export = load_json(ITEMS_EXPORT_PATH)
    crafts_export = load_json(CRAFTS_EXPORT_PATH)
    items_data = load_json(ITEMS_DATA_PATH)
    crafts_data = load_json(CRAFTS_DATA_PATH)
    requirements_data = load_json(REQUIREMENTS_DATA_PATH)
    professions_meta = load_json(PROFESSIONS_META_PATH)
    tools_meta = load_json(TOOLS_META_PATH)
    buildings_meta = load_json(BUILDINGS_META_PATH)

    print_success("Data loaded. Ready for normalization and comparison.")
    
    # Step 2: Transform & Normalize extractor data
    print_info("Normalizing extractor data to BitCrafty format...")
    normalized_items, normalized_crafts = normalize_extractor_data(items_export, crafts_export)
    
    print_success(f"Normalized {Colors.bold(str(len(normalized_items)))} items and {Colors.bold(str(len(normalized_crafts)))} crafts")
    for item_id in list(normalized_items.keys())[:3]:  # Show first 3 as examples
        print(f"  Item: {Colors.highlight(item_id)}")
    for craft_id in list(normalized_crafts.keys())[:3]:  # Show first 3 as examples
        print(f"  Craft: {Colors.highlight(craft_id)}")
    
    # Step 3: Resolve craft name conflicts
    print_info("Resolving craft name conflicts...")
    normalized_crafts = resolve_craft_name_conflicts(normalized_crafts)
    
    # Step 4: Load BitCrafty canonical data
    print_info("Loading BitCrafty canonical data...")
    bitcrafty_items, bitcrafty_crafts = load_bitcrafty_data(items_data, crafts_data)
    print_success(f"Loaded {Colors.bold(str(len(bitcrafty_items)))} BitCrafty items and {Colors.bold(str(len(bitcrafty_crafts)))} crafts")
    
    # Step 5: Compare and identify changes
    print_info("Comparing data and identifying changes...")
    changes = compare_entities(normalized_items, normalized_crafts, bitcrafty_items, bitcrafty_crafts)
    
    # Step 5.5: Find existing items needing descriptions
    print_info("Checking for existing items missing descriptions...")
    description_updates = find_items_needing_descriptions(bitcrafty_items, items_export)
    if description_updates:
        changes['items']['description_updates'] = description_updates
        print_success(f"Found {Colors.bold(str(len(description_updates)))} items needing description updates")
    else:
        print_info("No existing items need description updates")
    
    # Step 6: Update craft item references based on ID changes
    if changes['items']['id_updates']:
        print_info("Updating craft item references...")
        normalized_crafts = update_craft_item_references(normalized_crafts, changes['items']['id_updates'])
        # Re-run comparison for crafts after updating references
        updated_changes = compare_entities(normalized_items, normalized_crafts, bitcrafty_items, bitcrafty_crafts)
        # Preserve description_updates from the previous comparison
        if 'description_updates' in changes['items']:
            updated_changes['items']['description_updates'] = changes['items']['description_updates']
        changes = updated_changes
    
    # Step 7: Extract and compare metadata
    print("\n" + Colors.section_divider("METADATA & REQUIREMENTS PROCESSING", 60))
    print_info("Extracting metadata from crafts...")
    extracted_professions, extracted_tools, extracted_buildings = extract_metadata_from_crafts(normalized_crafts)
    print_success(f"Extracted {Colors.bold(str(len(extracted_professions)))} professions, {Colors.bold(str(len(extracted_tools)))} tools, {Colors.bold(str(len(extracted_buildings)))} buildings")
    
    print_info("Comparing metadata with BitCrafty data...")
    metadata_changes = compare_metadata(extracted_professions, extracted_tools, extracted_buildings,
                                       professions_meta, tools_meta, buildings_meta)
    
    # Step 8: Extract and compare requirements
    print_info("Extracting requirements from crafts...")
    extracted_requirements = extract_requirements_from_crafts(normalized_crafts)
    print_success(f"Extracted {Colors.bold(str(len(extracted_requirements)))} unique requirements")
    
    print_info("Comparing requirements with BitCrafty data...")
    requirement_changes = compare_requirements(extracted_requirements, requirements_data)
    
    # Check for missing buildings needed by requirements (more accurate than generic metadata comparison)
    print_info("Checking for missing buildings...")
    missing_buildings = check_building_requirements_exist(extracted_requirements, buildings_meta)
    
    # Update metadata changes to only include actually missing buildings
    metadata_changes['buildings']['new'] = []
    metadata_changes['missing_building_ids'] = missing_buildings  # Pass the actual IDs
    if missing_buildings:
        for building_id in missing_buildings:
            # Extract building name from ID for display
            if ':' in building_id:
                building_name = building_id.split(':')[-1].replace('-', ' ').title()
                metadata_changes['buildings']['new'].append(building_name)
                print(f"[INFO] Will create missing building: {building_id}")
    
    print_info("Creating new metadata entries...")
    new_metadata = create_new_metadata_entries(metadata_changes, normalized_crafts)
    
    # Step 9: Update crafts to use requirement references
    print_info("Updating crafts to use requirement references...")
    normalized_crafts = update_crafts_with_requirements(normalized_crafts, extracted_requirements)
    
    # Step 9.5: Ensure all item references in crafts exist
    print_info("Ensuring all craft item references exist...")
    normalized_items = ensure_item_references_exist(normalized_crafts, normalized_items)
    
    # Re-run craft comparison after requirement updates
    updated_changes = compare_entities(normalized_items, normalized_crafts, bitcrafty_items, bitcrafty_crafts)
    # Preserve description_updates from the previous comparison
    if 'description_updates' in changes['items']:
        updated_changes['items']['description_updates'] = changes['items']['description_updates']
    changes = updated_changes
    
    # Step 10: Print final summary with metadata and requirements
    print_comparison_summary(changes, metadata_changes, new_metadata, requirement_changes)
    
    # Step 11: Prompt for confirmation and apply changes
    if prompt_for_confirmation(changes, metadata_changes, new_metadata, requirement_changes):
        # Optional: Run pre-change validation to catch existing issues
        print_info("Running pre-change data integrity check...")
        pre_validation_passed = validate_data_integrity_post_change()
        
        if not pre_validation_passed:
            print_warning("Pre-existing data integrity issues detected!")
            response = input(f"{Colors.colorize('Continue with reconciliation anyway? [y/N]: ', Colors.YELLOW)}").strip().lower()
            if response != 'y' and response != 'yes':
                print_info("Reconciliation cancelled due to pre-existing data issues.")
                return
        
        # Create backup before applying changes
        print_info("Creating backup before applying changes...")
        backup_path = create_backup()
        
        if backup_path:
            print_success(f"Backup created successfully: {Colors.highlight(backup_path)}")
            
            # Clean up old backups (keep 10 most recent)
            cleanup_old_backups(keep_count=10)
            
            if apply_changes_in_correct_order(changes, metadata_changes, new_metadata, requirement_changes, normalized_crafts):
                print_success("Reconciliation completed successfully!")
                print_info(f"Backup available at: {Colors.highlight(backup_path)}")
            else:
                print_info(f"Backup available for rollback at: {Colors.highlight(backup_path)}")
        else:
            print_warning("Could not create backup. Do you want to continue anyway? [y/N]: ")
            response = input().strip().lower()
            if response == 'y' or response == 'yes':
                if apply_changes_in_correct_order(changes, metadata_changes, new_metadata, requirement_changes, normalized_crafts):
                    print_success("Reconciliation completed successfully!")
                else:
                    print_error("Reconciliation failed. No changes were applied.")
            else:
                print_info("Reconciliation cancelled due to backup failure.")
    else:
        print_info("Reconciliation cancelled. No changes were applied.")
    
def prompt_for_confirmation(changes, metadata_changes, new_metadata, requirement_changes):
    """Prompt user for confirmation before applying changes."""
    print("\n" + Colors.section_divider("CONFIRMATION REQUIRED"))
    
    total_changes = (
        len(changes['items']['new']) + len(changes['items']['updated']) + len(changes['items']['id_updates']) +
        len(changes['items'].get('description_updates', {})) +
        len(changes['crafts']['new']) + len(changes['crafts']['updated']) +
        len(metadata_changes['buildings']['new']) +
        len(requirement_changes['new']) + len(requirement_changes['updated'])
    )
    
    if total_changes == 0:
        print_info("No changes needed. Everything is up to date!")
        while True:
            prompt_text = f"\n{Colors.colorize('No reconciliation needed. Would you like to access', Colors.BOLD)} [{Colors.colorize('B', Colors.CYAN)}ackups] or [{Colors.colorize('Q', Colors.GRAY)}uit]? "
            response = input(prompt_text).strip().lower()
            
            if response in ['q', 'quit']:
                print_info("Exiting reconciliator.")
                return False
            elif response in ['b', 'backup', 'backups']:
                show_backup_management()
                continue
            else:
                print_warning("Please enter 'Backups' or 'Quit' (letters or full words).")
    
    print(f"\n{Colors.colorize('Ready to apply', Colors.BOLD)} {Colors.colorize(str(total_changes), Colors.BOLD + Colors.GREEN)} {Colors.colorize('changes to BitCrafty data:', Colors.BOLD)}")
    print(f"  • {Colors.colorize(str(len(changes['items']['id_updates'])), Colors.YELLOW)} item ID updates")
    print(f"  • {Colors.colorize(str(len(changes['items']['new'])), Colors.GREEN)} new items")
    print(f"  • {Colors.colorize(str(len(changes['items']['updated'])), Colors.CYAN)} item updates")
    print(f"  • {Colors.colorize(str(len(changes['items'].get('description_updates', {}))), Colors.CYAN)} description updates")
    print(f"  • {Colors.colorize(str(len(changes['crafts']['new'])), Colors.GREEN)} new crafts")
    print(f"  • {Colors.colorize(str(len(changes['crafts']['updated'])), Colors.CYAN)} craft updates")
    print(f"  • {Colors.colorize(str(len(requirement_changes['new'])), Colors.GREEN)} new requirements")
    print(f"  • {Colors.colorize(str(len(requirement_changes['updated'])), Colors.CYAN)} requirement updates")
    print(f"  • {Colors.colorize(str(len(metadata_changes['buildings']['new'])), Colors.GREEN)} new buildings")
    
    while True:
        prompt_text = f"\n{Colors.colorize('Apply these changes?', Colors.BOLD)} [{Colors.colorize('Y', Colors.GREEN)}es/{Colors.colorize('N', Colors.RED)}o] or [{Colors.colorize('D', Colors.BLUE)}etails/{Colors.colorize('B', Colors.CYAN)}ackups]: "
        response = input(prompt_text).strip().lower()
        
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no', '']:
            print_info("Changes cancelled.")
            return False
        elif response in ['d', 'details']:
            print_detailed_changes(changes, metadata_changes, new_metadata, requirement_changes)
            continue
        elif response in ['b', 'backup', 'backups']:
            show_backup_management()
            continue
        else:
            print_warning("Please enter 'Yes/No' or 'Details/Backups' (letters or full words).")


def show_backup_management():
    """Show backup management interface."""
    print("\n" + Colors.section_divider("BACKUP MANAGEMENT", 60))
    
    backups = list_available_backups()
    
    if not backups:
        print_warning("No backups found.")
        return
    
    print(f"\n{Colors.success(f'Found {len(backups)} backups:')}")
    for i, backup in enumerate(backups, 1):
        created_at = backup.get('created_at', 'Unknown')
        file_count = len(backup.get('files', []))
        print(f"  {Colors.colorize(str(i), Colors.BOLD)}. {Colors.highlight(backup['folder'])} - {Colors.gray(created_at)} {Colors.colorize(f'({file_count} files)', Colors.CYAN)}")
    
    while True:
        prompt_text = f"\n{Colors.colorize('Backup actions:', Colors.BOLD)} [{Colors.colorize('L', Colors.BLUE)}ist/{Colors.colorize('R', Colors.YELLOW)}estore/{Colors.colorize('C', Colors.RED)}lean/{Colors.colorize('V', Colors.GREEN)}alidate/{Colors.colorize('Q', Colors.GRAY)}uit]: "
        action = input(prompt_text).strip().lower()
        
        if action in ['q', 'quit']:
            break
        elif action in ['v', 'validate']:
            print_info("Running data integrity validation...")
            is_valid = validate_data_integrity_post_change()
            if is_valid:
                print_success("Data integrity validation passed!")
            else:
                print_error("Data integrity validation failed - see errors above")
        elif action in ['l', 'list']:
            try:
                backup_num = int(input(f"{Colors.colorize('Enter backup number to list files: ', Colors.CYAN)}")) - 1
                if 0 <= backup_num < len(backups):
                    backup = backups[backup_num]
                    print(f"\n{Colors.header(f'Files in backup {backup['folder']}:')}")
                    for file_name in backup.get('files', []):
                        print(f"  • {Colors.highlight(file_name)}")
                else:
                    print_error("Invalid backup number.")
            except ValueError:
                print_error("Please enter a valid number.")
        
        elif action in ['r', 'restore']:
            print(f"\n{Colors.colorize('⚠️  WARNING:', Colors.BOLD + Colors.RED)} This will overwrite current BitCrafty data!")
            confirm = input(f"{Colors.colorize('Are you sure you want to restore? [Y/N]: ', Colors.YELLOW)}").strip().lower()
            if confirm in ['y', 'yes']:
                try:
                    backup_num = int(input(f"{Colors.colorize('Enter backup number to restore: ', Colors.CYAN)}")) - 1
                    if 0 <= backup_num < len(backups):
                        backup = backups[backup_num]
                        if restore_from_backup(backup['path']):
                            print_success(f"Restored from backup: {backup['folder']}")
                        else:
                            print_error("Failed to restore backup.")
                    else:
                        print_error("Invalid backup number.")
                except ValueError:
                    print_error("Please enter a valid number.")
            else:
                print_info("Restore cancelled.")
        
        elif action in ['c', 'clean']:
            try:
                keep_count = int(input(f"{Colors.colorize('How many recent backups to keep? [default: 10]: ', Colors.CYAN)}") or "10")
                cleanup_old_backups(keep_count)
                # Refresh the backup list
                backups = list_available_backups()
                print_success(f"Now have {len(backups)} backups remaining.")
            except ValueError:
                print_error("Please enter a valid number.")
        
        else:
            print_warning("Invalid option. Use 'List/Restore/Clean/Validate/Quit' (letters or full words).")


def print_detailed_changes(changes, metadata_changes, new_metadata, requirement_changes):
    """Print detailed information about what will be changed."""
    print("\n" + Colors.section_divider("DETAILED CHANGES", 60))
    
    if changes['items']['id_updates']:
        print(f"\n{Colors.colorize('ITEM ID UPDATES:', Colors.BOLD + Colors.YELLOW)}")
        print(f"{Colors.gray('File:')} {Colors.highlight(ITEMS_DATA_PATH)}")
        
        for old_id, update_info in changes['items']['id_updates'].items():
            new_id = update_info['new_id']
            item_name = update_info['new']['name']
            print(f"  {Colors.colorize(old_id, Colors.RED)} → {Colors.colorize(new_id, Colors.GREEN)}")
            print(f"    {Colors.colorize('Name:', Colors.CYAN)} {item_name}")
            print(f"    {Colors.colorize('Reason:', Colors.CYAN)} {update_info['reason']}")
    
    if changes['items']['new']:
        print(f"\n{Colors.colorize('NEW ITEMS:', Colors.BOLD + Colors.GREEN)}")
        print(f"{Colors.gray('File:')} {Colors.highlight(ITEMS_DATA_PATH)}")
        for item_id, item in changes['items']['new'].items():
            tier_color = Colors.get_tier_color(item.get('tier'))
            tier_text = Colors.colorize(f"T{item.get('tier', '?')}", tier_color)
            print(f"  {Colors.colorize('✓', Colors.GREEN)} Added new item: {Colors.highlight(item_id)} {Colors.gray(f'({tier_text})')}")
    
    if changes['items'].get('description_updates'):
        print(f"\n{Colors.colorize('DESCRIPTION UPDATES:', Colors.BOLD + Colors.CYAN)}")
        print(f"{Colors.gray('File:')} {Colors.highlight(ITEMS_DATA_PATH)}")
        for item_id, update_info in changes['items']['description_updates'].items():
            item_name = update_info['existing']['name']
            description = update_info['description']
            print(f"  {Colors.colorize('📝', Colors.CYAN)} {Colors.highlight(item_id)}: {item_name}")
            print(f"    {Colors.colorize('Adding description:', Colors.CYAN)} {Colors.gray(description[:80] + ('...' if len(description) > 80 else ''))}")
    
    if changes['items']['updated']:
        print(f"\n{Colors.colorize('UPDATED ITEMS:', Colors.BOLD + Colors.YELLOW)}")
        print(f"{Colors.gray('File:')} {Colors.highlight(ITEMS_DATA_PATH)}")
        for item_id, updated_item in changes['items']['updated'].items():
            tier_color = Colors.get_tier_color(updated_item.get('tier'))
            tier_text = Colors.colorize(f"T{updated_item.get('tier', '?')}", tier_color)
            print(f"  {Colors.colorize('✓', Colors.GREEN)} Updated item: {Colors.highlight(item_id)} {Colors.gray(f'({tier_text})')}")
    
    if requirement_changes['new']:
        print(f"\n{Colors.colorize('NEW REQUIREMENTS:', Colors.BOLD + Colors.GREEN)}")
        print(f"{Colors.gray('File:')} {Colors.highlight(REQUIREMENTS_DATA_PATH)}")
        
        for req_id, req_data in requirement_changes['new'].items():
            req_entry = req_data['entry']
            craft_count = len(req_data['crafts'])
            print(f"  {Colors.colorize('+', Colors.GREEN)} {Colors.highlight(req_id)}: {req_entry['name']}")
            print(f"    {Colors.colorize('Used by', Colors.CYAN)} {Colors.colorize(str(craft_count), Colors.YELLOW)} {Colors.colorize('crafts:', Colors.CYAN)} {Colors.gray(', '.join(req_data['crafts'][:3]))}{Colors.gray('...' if craft_count > 3 else '')}")
            print(f"    {Colors.colorize('Profession:', Colors.CYAN)} {Colors.colorize(req_entry['profession']['name'], Colors.BLUE)}")
            if 'tool' in req_entry:
                print(f"    {Colors.colorize('Tool:', Colors.CYAN)} {req_entry['tool']['name']}")
            if 'building' in req_entry:
                print(f"    {Colors.colorize('Building:', Colors.CYAN)} {req_entry['building']['name']}")
    
    if changes['crafts']['new']:
        print(f"\n{Colors.colorize('NEW CRAFTS:', Colors.BOLD + Colors.GREEN)}")
        print(f"{Colors.gray('File:')} {Colors.highlight(CRAFTS_DATA_PATH)}")
        
        for craft_id, craft in changes['crafts']['new'].items():
            print(f"  {Colors.colorize('+', Colors.GREEN)} {Colors.highlight(craft_id)}: {craft['name']}")
            if craft.get('requirement'):
                print(f"    {Colors.colorize('Requirement:', Colors.CYAN)} {Colors.gray(craft['requirement'])}")
            if craft.get('inputs'):
                input_count = len(craft['inputs'])
                print(f"    {Colors.colorize('Inputs:', Colors.CYAN)} {Colors.colorize(str(input_count), Colors.YELLOW)} items")
            if craft.get('outputs'):
                output_count = len(craft['outputs'])
                print(f"    {Colors.colorize('Outputs:', Colors.CYAN)} {Colors.colorize(str(output_count), Colors.YELLOW)} items")
    
    if changes['crafts']['updated']:
        print(f"\n{Colors.colorize('UPDATED CRAFTS:', Colors.BOLD + Colors.YELLOW)}")
        print(f"{Colors.gray('File:')} {Colors.highlight(CRAFTS_DATA_PATH)}")
        for craft_id, updated_craft in changes['crafts']['updated'].items():
            print(f"  {Colors.colorize('✓', Colors.GREEN)} Updated craft: {Colors.highlight(craft_id)}")
    
    if metadata_changes['buildings']['new']:
        print(f"\n{Colors.colorize('NEW BUILDINGS:', Colors.BOLD + Colors.GREEN)}")
        print(f"{Colors.gray('File:')} {Colors.highlight(BUILDINGS_META_PATH)}")
        
        for building_data in new_metadata['buildings']:
            print(f"  {Colors.colorize('+', Colors.GREEN)} {Colors.highlight(building_data['id'])}: {building_data['name']}")


def apply_changes_in_correct_order(changes, metadata_changes, new_metadata, requirement_changes, normalized_crafts):
    """
    Apply changes to BitCrafty data files in the correct order:
    1. Metadata (professions, tools, buildings) 
    2. Items
    3. Requirements
    4. Crafts
    This ensures IDs are available for lookups in later steps.
    """
    print_info("Applying changes to BitCrafty data files in correct order...")
    
    try:
        # Load current BitCrafty data
        items_data = load_json(ITEMS_DATA_PATH)
        crafts_data = load_json(CRAFTS_DATA_PATH)
        requirements_data = load_json(REQUIREMENTS_DATA_PATH)
        buildings_data = load_json(BUILDINGS_META_PATH)
        professions_data = load_json(PROFESSIONS_META_PATH)
        tools_data = load_json(TOOLS_META_PATH)
        
        changes_applied = 0
        
        # STEP 1: Insert metadata first (buildings, tools, professions)
        print_header("\n1. INSERTING METADATA")
        
        # Add new buildings
        if metadata_changes['buildings']['new']:
            count = len(metadata_changes['buildings']['new'])
            print_info(f"Adding {Colors.colorize(str(count), Colors.YELLOW)} new buildings...")
            for building_data in new_metadata['buildings']:
                buildings_data.append(building_data)
                print(f"  {Colors.colorize('✓', Colors.GREEN)} Added building: {Colors.highlight(building_data['id'])}")
                changes_applied += 1
            
            # Handle profession-specific stations that need to be created based on craft requirements
            station_professions = set()
            for craft_id, craft in normalized_crafts.items():
                requirements = craft.get('requirements', {})
                profession = requirements.get('profession')
                building = requirements.get('building', '').lower()
                if profession and 'station' in building:
                    # Normalize profession name
                    normalized_profession = normalize_name(profession)
                    station_professions.add(normalized_profession)
            
            # Create missing station buildings
            for profession in station_professions:
                station_id = f"building:{profession}:station"
                if not any(b.get('id') == station_id for b in buildings_data):
                    buildings_data.append({
                        'id': station_id,
                        'name': f"{profession.title()} Station"
                    })
                    print(f"  {Colors.colorize('✓', Colors.GREEN)} Added profession station: {Colors.highlight(station_id)}")
                    changes_applied += 1
        
        # Add new tools
        if metadata_changes['tools']['new']:
            count = len(metadata_changes['tools']['new'])
            print_info(f"Adding {Colors.colorize(str(count), Colors.YELLOW)} new tools...")
            for tool_data in new_metadata['tools']:
                tools_data.append(tool_data)
                print(f"  {Colors.colorize('✓', Colors.GREEN)} Added tool: {Colors.highlight(tool_data['id'])}")
                changes_applied += 1
        
        # Add new professions
        if metadata_changes['professions']['new']:
            count = len(metadata_changes['professions']['new'])
            print_info(f"Adding {Colors.colorize(str(count), Colors.YELLOW)} new professions...")
            for prof_data in new_metadata['professions']:
                # Ensure profession name is normalized for ID creation
                normalized_prof_name = normalize_name(prof_data['name'])
                professions_data.append({
                    'id': f"profession:{normalized_prof_name}",
                    'name': prof_data['name'],  # Keep original name for display
                    'color': prof_data['color']
                })
                print(f"  {Colors.colorize('✓', Colors.GREEN)} Added profession: profession:{normalized_prof_name}")
                changes_applied += 1
        
        # STEP 2: Insert/Update Items
        print_header("\n2. INSERTING/UPDATING ITEMS")
        
        # Apply item ID updates first
        if changes['items']['id_updates']:
            count = len(changes['items']['id_updates'])
            print_info(f"Updating {Colors.colorize(str(count), Colors.YELLOW)} item IDs...")
            for old_id, update_info in changes['items']['id_updates'].items():
                new_id = update_info['new_id']
                # Find and update item
                for item in items_data:
                    if item['id'] == old_id:
                        item['id'] = new_id
                        print(f"  {Colors.colorize('✓', Colors.GREEN)} Updated item ID: {Colors.colorize(old_id, Colors.RED)} → {Colors.colorize(new_id, Colors.GREEN)}")
                        changes_applied += 1
                        break
                
                # Update references in crafts
                for craft in crafts_data:
                    # Update materials
                    if 'materials' in craft:
                        for material in craft['materials']:
                            if material.get('item') == old_id:
                                material['item'] = new_id
                                print(f"  {Colors.colorize('✓', Colors.GREEN)} Updated craft material reference: {Colors.gray(old_id)} → {Colors.gray(new_id)}")
                    
                    # Update outputs
                    if 'outputs' in craft:
                        for output in craft['outputs']:
                            if output.get('item') == old_id:
                                output['item'] = new_id
                                print(f"  {Colors.colorize('✓', Colors.GREEN)} Updated craft output reference: {Colors.gray(old_id)} → {Colors.gray(new_id)}")
        
        # Apply description updates to existing items
        if changes['items'].get('description_updates'):
            count = len(changes['items']['description_updates'])
            print_info(f"Adding descriptions to {Colors.colorize(str(count), Colors.YELLOW)} existing items...")
            for item_id, update_info in changes['items']['description_updates'].items():
                description = update_info['description']
                # Find and update item
                for item in items_data:
                    if item['id'] == item_id:
                        item['description'] = description
                        item_name = item['name']
                        description_preview = description[:50] + ('...' if len(description) > 50 else '')
                        print(f"  {Colors.colorize('📝', Colors.CYAN)} Updated description for: {Colors.highlight(item_id)} ({item_name})")
                        print(f"    {Colors.gray(description_preview)}")
                        changes_applied += 1
                        break
        
        # Update existing items
        if changes['items']['updated']:
            count = len(changes['items']['updated'])
            print_info(f"Updating {Colors.colorize(str(count), Colors.YELLOW)} existing items...")
            for item_id, update_info in changes['items']['updated'].items():
                new_item = clean_item_for_bitcrafty(update_info['new'])
                # Find and replace the existing item
                for i, item in enumerate(items_data):
                    if item['id'] == item_id:
                        items_data[i] = new_item
                        tier_color = Colors.get_tier_color(new_item.get('tier'))
                        tier_text = Colors.colorize(f"T{new_item.get('tier', '?')}", tier_color)
                        print(f"  {Colors.colorize('✓', Colors.GREEN)} Updated item: {Colors.highlight(item_id)} {Colors.gray(f'({tier_text})')}")
                        changes_applied += 1
                        break
        
        # Add new items
        if changes['items']['new']:
            count = len(changes['items']['new'])
            print_info(f"Adding {Colors.colorize(str(count), Colors.YELLOW)} new items...")
            for item_id, item in changes['items']['new'].items():
                clean_item = clean_item_for_bitcrafty(item)
                items_data.append(clean_item)
                tier_color = Colors.get_tier_color(clean_item.get('tier'))
                tier_text = Colors.colorize(f"T{clean_item.get('tier', '?')}", tier_color)
                print(f"  {Colors.colorize('✓', Colors.GREEN)} Added item: {Colors.highlight(item_id)} {Colors.gray(f'({tier_text})')}")
                changes_applied += 1
        
        # STEP 3: Insert Requirements
        print_header("\n3. INSERTING REQUIREMENTS")
        
        if requirement_changes['new']:
            count = len(requirement_changes['new'])
            print_info(f"Adding {Colors.colorize(str(count), Colors.YELLOW)} new requirements...")
            for req_id, req_data in requirement_changes['new'].items():
                requirements_data.append(req_data['entry'])
                print(f"  {Colors.colorize('✓', Colors.GREEN)} Added requirement: {Colors.highlight(req_id)}")
                changes_applied += 1
        
        # STEP 4: Insert/Update Crafts
        print_header("\n4. INSERTING/UPDATING CRAFTS")
        
        # Update existing crafts
        if changes['crafts']['updated']:
            count = len(changes['crafts']['updated'])
            print_info(f"Updating {Colors.colorize(str(count), Colors.YELLOW)} existing crafts...")
            
            # Create ExportManager for intelligent merging
            try:
                merge_manager = ExportManager()
            except Exception as e:
                print(f"[WARNING] Could not create ExportManager for merging: {e}")
                merge_manager = None
                
            for craft_id, update_info in changes['crafts']['updated'].items():
                if merge_manager:
                    # Use intelligent merging
                    merged_craft = intelligent_craft_merge(
                        update_info['existing'], 
                        update_info['new'], 
                        merge_manager
                    )
                else:
                    # Fallback to simple replacement
                    merged_craft = clean_craft_for_bitcrafty(update_info['new'])
                
                # Find and replace the existing craft
                for i, craft in enumerate(crafts_data):
                    if craft['id'] == craft_id:
                        crafts_data[i] = merged_craft
                        reason = ', '.join(update_info.get('changes', ['update']))
                        print(f"  {Colors.colorize('✓', Colors.GREEN)} Updated craft: {Colors.highlight(craft_id)} ({reason})")
                        changes_applied += 1
                        break
        
        # Add new crafts
        if changes['crafts']['new']:
            count = len(changes['crafts']['new'])
            print_info(f"Adding {Colors.colorize(str(count), Colors.YELLOW)} new crafts...")
            for craft_id, craft in changes['crafts']['new'].items():
                clean_craft = clean_craft_for_bitcrafty(craft)
                crafts_data.append(clean_craft)
                print(f"  {Colors.colorize('✓', Colors.GREEN)} Added craft: {Colors.highlight(craft_id)}: {craft['name']}")
                changes_applied += 1
        
        # Write all updated files
        print_header("\n5. SAVING FILES")
        write_json(items_data, ITEMS_DATA_PATH)
        write_json(crafts_data, CRAFTS_DATA_PATH)
        write_json(requirements_data, REQUIREMENTS_DATA_PATH)
        write_json(buildings_data, BUILDINGS_META_PATH)
        write_json(professions_data, PROFESSIONS_META_PATH)
        write_json(tools_data, TOOLS_META_PATH)
        
        print_success(f"Applied {Colors.colorize(str(changes_applied), Colors.BOLD)} changes successfully!")
        print_info("Updated files:")
        print(f"  • {Colors.highlight(ITEMS_DATA_PATH)}")
        print(f"  • {Colors.highlight(CRAFTS_DATA_PATH)}")
        print(f"  • {Colors.highlight(REQUIREMENTS_DATA_PATH)}")
        print(f"  • {Colors.highlight(BUILDINGS_META_PATH)}")
        print(f"  • {Colors.highlight(PROFESSIONS_META_PATH)}")
        print(f"  • {Colors.highlight(TOOLS_META_PATH)}")
        
        # Run post-change validation
        print_header("\n6. VALIDATION")
        print_info("Running post-change data integrity verification...")
        validation_passed = validate_data_integrity_post_change()
        
        if not validation_passed:
            print_error("Data integrity validation FAILED after applying changes!")
            print_warning("This indicates the reconciliation may have introduced data inconsistencies.")
            print_warning("Consider restoring from backup and reviewing the changes.")
            return False
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to apply changes: {e}")
        return False


def clean_item_for_bitcrafty(item):
    """Clean item data to match BitCrafty format exactly - remove extractor metadata."""
    return {
        'id': item['id'],
        'name': item['name'],
        'description': item.get('description', ''),  # Include description in BitCrafty format
        'tier': item.get('tier', 1),
        'rank': item.get('rank', 'Common')
    }


def ensure_item_references_exist(normalized_crafts, normalized_items):
    """
    Ensure all item references in crafts exist in normalized_items.
    If not, create placeholder items with basic information.
    """
    print_info("Verifying all craft item references exist...")
    
    # Get all item IDs referenced in crafts
    referenced_items = set()
    
    for craft_id, craft in normalized_crafts.items():
        # Check materials
        for material in craft.get('materials', []):
            item_ref = material.get('item')
            if item_ref:
                referenced_items.add(item_ref)
        
        # Check outputs
        for output in craft.get('outputs', []):
            item_ref = output.get('item')
            if item_ref:
                referenced_items.add(item_ref)
    
    # Check which items are missing
    missing_items = referenced_items - set(normalized_items.keys())
    
    if missing_items:
        print_warning(f"Found {len(missing_items)} item references without matching items. Creating placeholder items...")
        
        for item_id in missing_items:
            # Extract info from ID
            if ':' in item_id:
                parts = item_id.split(':')
                if len(parts) >= 3:
                    profession = parts[1]
                    name_part = parts[2].replace('-', ' ').title()
                    
                    # Create placeholder item
                    normalized_items[item_id] = {
                        'id': item_id,
                        'name': name_part,
                        'description': '',  # Placeholder description for missing items
                        'tier': 1,
                        'rank': 'Common'
                    }
                    print(f"  {Colors.colorize('✓', Colors.GREEN)} Created placeholder item: {Colors.highlight(item_id)} ({name_part})")
    
    return normalized_items


def clean_item_for_bitcrafty(item):
    """Clean item data to match BitCrafty format exactly - remove extractor metadata."""
    return {
        'id': item['id'],
        'name': item['name'],
        'description': item.get('description', ''),  # Include description in BitCrafty format
        'tier': item.get('tier', 1),
        'rank': item.get('rank', 'Common')
    }


def clean_craft_for_bitcrafty(craft):
    """Clean craft data to match BitCrafty format exactly - remove extractor metadata."""
    clean_craft = {
        'id': craft['id'],
        'name': craft['name'],
        'materials': craft.get('materials', []),
        'outputs': craft.get('outputs', [])
    }
    
    # Only add requirement if it exists
    if 'requirement' in craft:
        clean_craft['requirement'] = craft['requirement']
    
    return clean_craft


def write_json(data, file_path):
    """Write JSON data to file with proper formatting."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def create_backup():
    """Create a timestamped backup of all BitCrafty data files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_folder = os.path.join(BACKUPS_DIR, f"backup_{timestamp}")
    
    try:
        # Create backup directory if it doesn't exist
        os.makedirs(backup_folder, exist_ok=True)
        
        # List of files to backup
        files_to_backup = [
            ('items.json', ITEMS_DATA_PATH),
            ('crafts.json', CRAFTS_DATA_PATH),
            ('requirements.json', REQUIREMENTS_DATA_PATH),
            ('metadata/professions.json', PROFESSIONS_META_PATH),
            ('metadata/tools.json', TOOLS_META_PATH),
            ('metadata/buildings.json', BUILDINGS_META_PATH)
        ]
        
        backed_up_files = []
        
        for relative_path, source_path in files_to_backup:
            if os.path.exists(source_path):
                # Create subdirectories if needed
                backup_file_path = os.path.join(backup_folder, relative_path)
                backup_dir = os.path.dirname(backup_file_path)
                os.makedirs(backup_dir, exist_ok=True)
                
                # Copy the file
                shutil.copy2(source_path, backup_file_path)
                backed_up_files.append(relative_path)
                print(f"[BACKUP] Backed up: {relative_path}")
        
        # Create a backup manifest
        manifest = {
            'timestamp': timestamp,
            'created_at': datetime.now().isoformat(),
            'backed_up_files': backed_up_files,
            'backup_reason': 'Pre-reconciliation backup',
            'bitcrafty_data_dir': BITCRAFTY_DATA_DIR
        }
        
        manifest_path = os.path.join(backup_folder, 'backup_manifest.json')
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        print(f"[BACKUP] Created backup: {backup_folder}")
        print(f"[BACKUP] Backed up {len(backed_up_files)} files")
        return backup_folder
        
    except Exception as e:
        print(f"[ERROR] Failed to create backup: {e}")
        return None


def list_available_backups():
    """List all available backups sorted by date (newest first)."""
    if not os.path.exists(BACKUPS_DIR):
        return []
    
    backups = []
    for item in os.listdir(BACKUPS_DIR):
        backup_path = os.path.join(BACKUPS_DIR, item)
        if os.path.isdir(backup_path) and item.startswith('backup_'):
            manifest_path = os.path.join(backup_path, 'backup_manifest.json')
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                    backups.append({
                        'folder': item,
                        'path': backup_path,
                        'timestamp': manifest.get('timestamp'),
                        'created_at': manifest.get('created_at'),
                        'files': manifest.get('backed_up_files', [])
                    })
                except Exception as e:
                    print(f"[WARN] Could not read backup manifest: {manifest_path} - {e}")
    
    # Sort by timestamp (newest first)
    backups.sort(key=lambda x: x['timestamp'], reverse=True)
    return backups


def restore_from_backup(backup_path):
    """Restore BitCrafty data from a specific backup."""
    manifest_path = os.path.join(backup_path, 'backup_manifest.json')
    
    if not os.path.exists(manifest_path):
        print(f"[ERROR] Backup manifest not found: {manifest_path}")
        return False
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        print(f"[RESTORE] Restoring from backup created at: {manifest.get('created_at')}")
        
        # Restore each file
        restored_files = []
        for relative_path in manifest.get('backed_up_files', []):
            backup_file_path = os.path.join(backup_path, relative_path)
            
            # Determine target path
            if relative_path == 'items.json':
                target_path = ITEMS_DATA_PATH
            elif relative_path == 'crafts.json':
                target_path = CRAFTS_DATA_PATH
            elif relative_path == 'requirements.json':
                target_path = REQUIREMENTS_DATA_PATH
            elif relative_path == 'metadata/professions.json':
                target_path = PROFESSIONS_META_PATH
            elif relative_path == 'metadata/tools.json':
                target_path = TOOLS_META_PATH
            elif relative_path == 'metadata/buildings.json':
                target_path = BUILDINGS_META_PATH
            else:
                continue
            
            if os.path.exists(backup_file_path):
                # Create target directory if needed
                target_dir = os.path.dirname(target_path)
                os.makedirs(target_dir, exist_ok=True)
                
                # Copy the file
                shutil.copy2(backup_file_path, target_path)
                restored_files.append(relative_path)
                print(f"[RESTORE] Restored: {relative_path}")
        
        print(f"[RESTORE] Successfully restored {len(restored_files)} files")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to restore from backup: {e}")
        return False


def cleanup_old_backups(keep_count=10):
    """Clean up old backups, keeping only the most recent ones."""
    backups = list_available_backups()
    
    if len(backups) <= keep_count:
        return
    
    backups_to_delete = backups[keep_count:]
    
    print(f"[CLEANUP] Removing {len(backups_to_delete)} old backups (keeping {keep_count} most recent)")
    
    for backup in backups_to_delete:
        try:
            shutil.rmtree(backup['path'])
            print(f"[CLEANUP] Removed backup: {backup['folder']}")
        except Exception as e:
            print(f"[WARN] Could not remove backup {backup['folder']}: {e}")


def extract_requirements_from_crafts(normalized_crafts):
    """Extract unique requirements from normalized crafts and create requirement entries following BitCrafty convention."""
    
    requirements_by_signature = {}
    
    for craft_id, craft in normalized_crafts.items():
        requirements = craft.get('requirements', {})
        
        profession = requirements.get('profession')
        tool = requirements.get('tool')
        building = requirements.get('building')
        
        if not profession:
            continue
        
        # Normalize profession name (lowercase, no apostrophes)
        normalized_profession = normalize_name(profession)
            
        # Extract tier information and clean names dynamically
        tool_clean = None
        tool_tier = 1
        if tool and tool != 'null' and tool is not None:
            tool_clean = tool.lower()
            # Dynamic tier extraction using regex
            tier_match = re.search(r'tier\s*(\d+)', tool_clean)
            if tier_match:
                tool_tier = int(tier_match.group(1))
                tool_clean = re.sub(r'tier\s*\d+\s*', '', tool_clean).strip()
            
        building_clean = None
        building_tier = 1
        if building and building != 'null' and building is not None:
            building_clean = building.lower()
            # Dynamic tier extraction using regex
            tier_match = re.search(r'tier\s*(\d+)', building_clean)
            if tier_match:
                building_tier = int(tier_match.group(1))
                building_clean = re.sub(r'tier\s*\d+\s*', '', building_clean).strip()
        
        # Create requirement signature (includes tiers and normalized profession)
        signature = (normalized_profession, tool_clean, tool_tier, building_clean, building_tier)
        
        if signature not in requirements_by_signature:
            # Create requirement ID following BitCrafty convention with dynamic tiers
            if building_clean and tool_clean:
                # Tool + Building = "tier{N}-{building}" pattern
                max_tier = max(building_tier, tool_tier)
                identifier = f"tier{max_tier}-{normalize_name(building_clean)}"
                req_name = f"Tier {max_tier} {building_clean.title()} Requirements"
            elif building_clean:
                # Building-only requirements
                if building_clean == "station":
                    # Station gets special handling
                    identifier = f"tier{building_tier}-{normalized_profession}-station"
                    req_name = f"Tier {building_tier} {normalized_profession.title()} Station Requirements"
                else:
                    # Other buildings
                    identifier = f"tier{building_tier}-{normalize_name(building_clean)}"
                    req_name = f"Tier {building_tier} {building_clean.title()} Requirements"
                    
                # Special naming for certain buildings
                if building_clean == "well":
                    identifier = f"tier{building_tier}-well"
                    req_name = f"Tier {building_tier} Well Access"
            elif tool_clean:
                # Tool-only requirements
                identifier = f"tier{tool_tier}-{normalize_name(tool_clean)}-tools"
                req_name = f"Tier {tool_tier} {tool_clean.title()} Tools Requirements"
            else:
                # Fallback to basic tools
                identifier = "tier1-basic-tools"
                req_name = f"Tier 1 Basic {normalized_profession.title()} Tools Requirements"
            
            requirement_id = f"requirement:{normalized_profession}:{identifier}"
            
            # Create requirement entry
            requirement_entry = {
                'id': requirement_id,
                'name': req_name,
                'profession': {'name': f"profession:{normalized_profession}", 'level': 1}
            }
            
            if tool_clean:
                requirement_entry['tool'] = {'name': f"tool:{normalize_name(tool_clean)}", 'level': tool_tier}
                
            if building_clean:
                # Use proper building ID format
                if 'station' in building_clean:
                    # Handle "carpentry station" -> "building:carpentry:station"
                    building_id = f"building:{normalized_profession}:station"
                elif building_clean == 'kiln':
                    # Handle specific buildings like kiln
                    building_id = f"building:{normalized_profession}:kiln"
                elif building_clean == 'well':
                    # Handle specific buildings like well
                    building_id = f"building:{normalized_profession}:well"
                elif building_clean in ['loom', 'anvil', 'forge']:
                    # Handle other specific buildings
                    building_id = f"building:{normalized_profession}:{building_clean}"
                else:
                    # Fallback for unknown buildings
                    building_id = f"building:{normalized_profession}:{normalize_name(building_clean)}"
                    
                requirement_entry['building'] = {'name': building_id, 'level': building_tier}
            
            requirements_by_signature[signature] = {
                'id': requirement_id,
                'entry': requirement_entry,
                'crafts': []
            }
            
            print(f"[DEBUG] Created requirement: {requirement_id} -> {req_name}")
        
        # Track which crafts use this requirement
        requirements_by_signature[signature]['crafts'].append(craft_id)
    
    return requirements_by_signature


def compare_requirements(extracted_requirements, existing_requirements):
    """Compare extracted requirements with existing BitCrafty requirements."""
    requirement_changes = {
        'new': {},
        'existing': {},
        'updated': {}
    }
    
    # Index existing requirements by ID
    existing_by_id = {}
    if existing_requirements:
        for req in existing_requirements:
            req_id = req.get('id')
            if req_id:
                existing_by_id[req_id] = req
    
    # Compare extracted requirements
    for signature, req_data in extracted_requirements.items():
        req_id = req_data['id']
        req_entry = req_data['entry']
        
        if req_id in existing_by_id:
            existing_req = existing_by_id[req_id]
            # Check if requirement needs updating (simplified comparison)
            if (req_entry.get('name') != existing_req.get('name') or
                req_entry.get('profession') != existing_req.get('profession') or
                req_entry.get('tool') != existing_req.get('tool') or
                req_entry.get('building') != existing_req.get('building')):
                requirement_changes['updated'][req_id] = {
                    'existing': existing_req,
                    'new': req_entry,
                    'crafts': req_data['crafts']
                }
                print(f"[INFO] Requirement needs update: {req_id}")
            else:
                requirement_changes['existing'][req_id] = {
                    'entry': req_entry,
                    'crafts': req_data['crafts']
                }
                print(f"[DEBUG] Requirement already exists: {req_id}")
        else:
            requirement_changes['new'][req_id] = {
                'entry': req_entry,
                'crafts': req_data['crafts']
            }
            print(f"[INFO] New requirement needed: {req_id}")
    
    return requirement_changes


def update_crafts_with_requirements(normalized_crafts, extracted_requirements):
    """Update normalized crafts to reference requirement IDs instead of inline requirements."""
    
    updated_crafts = {}
    
    for craft_id, craft in normalized_crafts.items():
        updated_craft = deepcopy(craft)
        requirements = craft.get('requirements', {})
        
        profession = requirements.get('profession')
        tool = requirements.get('tool')
        building = requirements.get('building')
        
        if profession:
            # Normalize profession name (same as in extract_requirements_from_crafts)
            normalized_profession = normalize_name(profession)
            
            # Extract tier information and clean names (same logic as extract_requirements_from_crafts)
            tool_clean = None
            tool_tier = 1
            if tool and tool != 'null' and tool is not None:
                tool_clean = tool.lower()
                # Dynamic tier extraction using regex
                tier_match = re.search(r'tier\s*(\d+)', tool_clean)
                if tier_match:
                    tool_tier = int(tier_match.group(1))
                    tool_clean = re.sub(r'tier\s*\d+\s*', '', tool_clean).strip()
                
            building_clean = None
            building_tier = 1
            if building and building != 'null' and building is not None:
                building_clean = building.lower()
                # Dynamic tier extraction using regex
                tier_match = re.search(r'tier\s*(\d+)', building_clean)
                if tier_match:
                    building_tier = int(tier_match.group(1))
                    building_clean = re.sub(r'tier\s*\d+\s*', '', building_clean).strip()
            
            # Create signature to match with extracted requirements
            signature = (normalized_profession, tool_clean, tool_tier, building_clean, building_tier)
            
            # Find the requirement ID for this signature
            for sig, req_data in extracted_requirements.items():
                if sig == signature:
                    # Replace requirements object with requirement ID reference (BitCrafty format)
                    updated_craft['requirement'] = req_data['id']
                    # Remove the old requirements object
                    if 'requirements' in updated_craft:
                        del updated_craft['requirements']
                    print(f"[DEBUG] Updated craft {craft_id} to use requirement: {req_data['id']}")
                    break
        
        updated_crafts[craft_id] = updated_craft
    
    return updated_crafts

def validate_data_integrity_post_change():
    """
    Validate BitCrafty data integrity after applying changes.
    Uses similar validation logic to the CI data-validation.test.js
    """
    print("\n" + Colors.section_divider("DATA INTEGRITY VALIDATION", 60))
    
    try:
        # Reload all data files to get fresh state
        items_data = load_json(ITEMS_DATA_PATH)
        crafts_data = load_json(CRAFTS_DATA_PATH)
        requirements_data = load_json(REQUIREMENTS_DATA_PATH)
        professions_meta = load_json(PROFESSIONS_META_PATH)
        tools_meta = load_json(TOOLS_META_PATH)
        buildings_meta = load_json(BUILDINGS_META_PATH)
        
        if not all([items_data, crafts_data, requirements_data, professions_meta, tools_meta, buildings_meta]):
            print_error("Could not load all data files for validation")
            return False
        
        validator = DataIntegrityValidator(
            items_data, crafts_data, requirements_data,
            professions_meta, tools_meta, buildings_meta
        )
        
        # Run all validation checks
        is_valid = validator.run_all_validations()
        
        if is_valid:
            print(f"\n{Colors.colorize('✅ Data integrity verification PASSED', Colors.BOLD + Colors.GREEN)}")
            validator.print_summary()
            return True
        else:
            print(f"\n{Colors.colorize('❌ Data integrity verification FAILED', Colors.BOLD + Colors.RED)}")
            validator.print_errors()
            return False
            
    except Exception as e:
        print_error(f"ERROR during validation: {e}")
        return False


class DataIntegrityValidator:
    """
    Data integrity validator based on BitCrafty's data-validation.test.js
    Ensures all references are valid and data structure is consistent.
    """
    
    def __init__(self, items_data, crafts_data, requirements_data, professions_meta, tools_meta, buildings_meta):
        self.items = items_data or []
        self.crafts = crafts_data or []
        self.requirements = requirements_data or []
        self.professions = professions_meta or []
        self.tools = tools_meta or []
        self.buildings = buildings_meta or []
        
        self.errors = []
        self.warnings = []
        self.create_lookup_sets()
    
    def error(self, message):
        self.errors.append(message)
    
    def warning(self, message):
        self.warnings.append(message)
    
    def create_lookup_sets(self):
        """Create lookup sets for quick validation (like the JS version)"""
        self.item_ids = set(item.get('id') for item in self.items if item.get('id'))
        self.craft_ids = set(craft.get('id') for craft in self.crafts if craft.get('id'))
        self.requirement_ids = set(req.get('id') for req in self.requirements if req.get('id'))
        
        # Extract profession names from metadata
        self.profession_names = set()
        for prof in self.professions:
            prof_id = prof.get('id', prof.get('name', ''))
            if ':' in prof_id:
                profession_name = prof_id.split(':')[1]
                self.profession_names.add(profession_name)
            elif prof_id:
                # Use normalize_name for consistency
                normalized_prof = normalize_name(prof_id)
                self.profession_names.add(normalized_prof)
        
        self.tool_ids = set(tool.get('id') for tool in self.tools if tool.get('id'))
        self.building_ids = set(building.get('id') for building in self.buildings if building.get('id'))
        self.profession_ids = set(prof.get('id') for prof in self.professions if prof.get('id'))
    
    def extract_profession_from_id(self, entity_id):
        """Extract profession from entity ID (format: type:profession:identifier)"""
        if not entity_id or ':' not in entity_id:
            return None
        parts = entity_id.split(':')
        return parts[1] if len(parts) >= 2 else None
    
    def is_valid_entity_id_format(self, entity_id, expected_type):
        """Check if entity ID follows the correct format"""
        if not entity_id or ':' not in entity_id:
            return False
        parts = entity_id.split(':')
        return len(parts) == 3 and parts[0] == expected_type
    
    def validate_craft_item_references(self):
        """Validate all item IDs in crafts are valid"""
        for craft in self.crafts:
            craft_id = craft.get('id', 'unknown')
            
            # Check materials/inputs
            materials = craft.get('materials', craft.get('inputs', []))
            for material in materials:
                item_ref = material.get('item')
                if item_ref and item_ref not in self.item_ids:
                    self.error(f'Craft "{craft_id}" references non-existent item "{item_ref}" in materials')
                    
                    # Try to suggest a fix by finding similar item names
                    suggested_fix = self.suggest_item_fix(item_ref)
                    if suggested_fix:
                        self.error(f'  → Suggested fix: use "{suggested_fix}" instead')
            
            # Check outputs
            outputs = craft.get('outputs', [])
            for output in outputs:
                item_ref = output.get('item')
                if item_ref and item_ref not in self.item_ids:
                    self.error(f'Craft "{craft_id}" references non-existent item "{item_ref}" in outputs')
                    
                    # Try to suggest a fix by finding similar item names
                    suggested_fix = self.suggest_item_fix(item_ref)
                    if suggested_fix:
                        self.error(f'  → Suggested fix: use "{suggested_fix}" instead')
    
    def suggest_item_fix(self, broken_item_id):
        """Suggest a fix for a broken item reference by finding similar existing items"""
        if not broken_item_id or ':' not in broken_item_id:
            return None
        
        # Extract the broken item name part
        parts = broken_item_id.split(':')
        if len(parts) < 3:
            return None
        
        broken_profession = parts[1]
        broken_name_part = parts[2]
        
        # Look for items with similar names in the same profession
        for item_id in self.item_ids:
            if item_id.startswith(f"item:{broken_profession}:"):
                existing_name_part = item_id.split(':')[2]
                
                # Check for common patterns that might indicate a match
                if broken_name_part in existing_name_part or existing_name_part in broken_name_part:
                    return item_id
                
                # Check for "plain-" prefix pattern
                if broken_name_part.replace('-', '') == existing_name_part.replace('plain-', '').replace('-', ''):
                    return item_id
        
        return None
    
    def validate_entity_profession_categories(self):
        """Validate entity ID profession categories"""
        # Validate items
        for item in self.items:
            item_id = item.get('id')
            if not item_id:
                self.error(f'Item missing ID: {item}')
                continue
                
            if not self.is_valid_entity_id_format(item_id, 'item'):
                self.error(f'Item "{item_id}" has invalid ID format (expected: item:profession:identifier)')
                continue
            
            profession = self.extract_profession_from_id(item_id)
            if not profession:
                self.error(f'Item "{item_id}" has no profession in ID')
            elif profession not in self.profession_names:
                self.error(f'Item "{item_id}" has invalid profession "{profession}" (not found in professions metadata)')
        
        # Validate crafts
        for craft in self.crafts:
            craft_id = craft.get('id')
            if not craft_id:
                self.error(f'Craft missing ID: {craft}')
                continue
                
            if not self.is_valid_entity_id_format(craft_id, 'craft'):
                self.error(f'Craft "{craft_id}" has invalid ID format (expected: craft:profession:identifier)')
                continue
            
            profession = self.extract_profession_from_id(craft_id)
            if not profession:
                self.error(f'Craft "{craft_id}" has no profession in ID')
            elif profession not in self.profession_names:
                self.error(f'Craft "{craft_id}" has invalid profession "{profession}" (not found in professions metadata)')
    
    def validate_craft_requirements(self):
        """Validate all crafts have valid requirements"""
        for craft in self.crafts:
            craft_id = craft.get('id', 'unknown')
            requirement_ref = craft.get('requirement')
            
            if not requirement_ref:
                self.error(f'Craft "{craft_id}" is missing requirement field')
            elif requirement_ref not in self.requirement_ids:
                self.error(f'Craft "{craft_id}" references non-existent requirement "{requirement_ref}"')
    
    def validate_requirement_metadata_references(self):
        """Validate requirement entity IDs with metadata"""
        for req in self.requirements:
            req_id = req.get('id', 'unknown')
            
            # Validate requirement ID format
            if not self.is_valid_entity_id_format(req_id, 'requirement'):
                self.error(f'Requirement "{req_id}" has invalid ID format (expected: requirement:profession:identifier)')
            
            # Validate profession reference
            profession_ref = req.get('profession', {}).get('name')
            if profession_ref:
                if profession_ref not in self.profession_ids:
                    self.error(f'Requirement "{req_id}" references non-existent profession "{profession_ref}"')
            else:
                self.error(f'Requirement "{req_id}" is missing profession.name')
            
            # Validate tool reference (if present)
            tool_ref = req.get('tool', {}).get('name')
            if tool_ref and tool_ref not in self.tool_ids:
                self.error(f'Requirement "{req_id}" references non-existent tool "{tool_ref}"')
            
            # Validate building reference (if present)
            building_ref = req.get('building', {}).get('name')
            if building_ref and building_ref not in self.building_ids:
                self.error(f'Requirement "{req_id}" references non-existent building "{building_ref}"')
            
            # Validate level values
            prof_level = req.get('profession', {}).get('level')
            if prof_level is not None and (not isinstance(prof_level, int) or prof_level < 1):
                self.error(f'Requirement "{req_id}" has invalid profession level: {prof_level}')
            
            tool_level = req.get('tool', {}).get('level')
            if tool_level is not None and (not isinstance(tool_level, int) or tool_level < 1):
                self.error(f'Requirement "{req_id}" has invalid tool level: {tool_level}')
            
            building_level = req.get('building', {}).get('level')
            if building_level is not None and (not isinstance(building_level, int) or building_level < 1):
                self.error(f'Requirement "{req_id}" has invalid building level: {building_level}')
    
    def validate_data_integrity(self):
        """Additional data integrity checks"""
        # Check for duplicate IDs
        all_entities = []
        for item in self.items:
            if item.get('id'):
                all_entities.append(('item', item.get('id')))
        for craft in self.crafts:
            if craft.get('id'):
                all_entities.append(('craft', craft.get('id')))
        for req in self.requirements:
            if req.get('id'):
                all_entities.append(('requirement', req.get('id')))
        
        all_ids = [entity[1] for entity in all_entities]
        seen_ids = set()
        duplicate_ids = set()
        
        for entity_id in all_ids:
            if entity_id in seen_ids:
                duplicate_ids.add(entity_id)
            seen_ids.add(entity_id)
        
        for dup_id in duplicate_ids:
            self.error(f'Duplicate ID found: {dup_id}')
        
        # Check for missing names
        all_data_entities = self.items + self.crafts + self.requirements
        for entity in all_data_entities:
            entity_id = entity.get('id', 'unknown')
            name = entity.get('name', '').strip()
            if not name:
                self.error(f'Entity "{entity_id}" is missing name')
        
        # Check for orphaned requirements (requirements not used by any craft)
        used_requirements = set()
        for craft in self.crafts:
            requirement_ref = craft.get('requirement')
            if requirement_ref:
                used_requirements.add(requirement_ref)
        
        for req in self.requirements:
            req_id = req.get('id')
            if req_id and req_id not in used_requirements:

                self.warning(f'Requirement "{req_id}" is not used by any craft')
    
    def run_all_validations(self):
        """Run all validation checks and return True if no errors"""
        self.validate_craft_item_references()
        self.validate_entity_profession_categories()
        self.validate_craft_requirements()
        self.validate_requirement_metadata_references()
        self.validate_data_integrity()
        
        return len(self.errors) == 0
    
    def print_summary(self):
        """Print validation summary"""
        total_entities = len(self.items) + len(self.crafts) + len(self.requirements)
        print(f"\n{Colors.colorize('Validation Summary:', Colors.BOLD + Colors.CYAN)}")
        print(f"  Validated {Colors.colorize(str(total_entities), Colors.YELLOW)} entities:")
        print(f"    • {Colors.colorize(str(len(self.items)), Colors.GREEN)} items")
        print(f"    • {Colors.colorize(str(len(self.crafts)), Colors.GREEN)} crafts")
        print(f"    • {Colors.colorize(str(len(self.requirements)), Colors.GREEN)} requirements")
        
        if self.warnings:
            print(f"\n   {Colors.colorize(f'{len(self.warnings)} warnings found:', Colors.YELLOW)}")
            for warning in self.warnings[:3]:  # Show first 3 warnings
                print(f"    {Colors.colorize('⚠️', Colors.YELLOW)}  {Colors.gray(warning)}")
            if len(self.warnings) > 3:
                print(f"    {Colors.gray(f'... and {len(self.warnings) - 3} more warnings')}")
    
    def print_errors(self):
        """Print all validation errors"""
        print(f"\n{Colors.colorize(f'{len(self.errors)} errors found:', Colors.BOLD + Colors.RED)}")
        for error in self.errors:
            print(f"  {Colors.colorize('❌', Colors.RED)} {error}")
        
        if self.warnings:
            print(f"\n{Colors.colorize(f'{len(self.warnings)} warnings:', Colors.YELLOW)}")
            for warning in self.warnings:
                print(f"  {Colors.colorize('⚠️', Colors.YELLOW)}  {Colors.gray(warning)}")


if __name__ == "__main__":
    main()
