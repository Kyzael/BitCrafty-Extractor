#!/usr/bin/env python3
"""
Auto-Fixing Data Integrity Validation Script
Runs validation and automatically fixes ID errors where possible.
"""

import sys
import os
import json
import re
from datetime import datetime
from copy import deepcopy

sys.path.append(os.path.dirname(__file__))

# Import all functions and classes from reconciliator
from reconciliator import (
    load_json, save_json, DataIntegrityValidator, Colors,
    ITEMS_DATA_PATH, CRAFTS_DATA_PATH, REQUIREMENTS_DATA_PATH,
    PROFESSIONS_META_PATH, TOOLS_META_PATH, BUILDINGS_META_PATH,
    BACKUPS_DIR, create_backup, normalize_name
)

class AutoFixValidator:
    """Enhanced validator that can automatically fix common ID issues"""
    
    def __init__(self, items_data, crafts_data, requirements_data, professions_meta, tools_meta, buildings_meta):
        self.items_data = items_data or []
        self.crafts_data = crafts_data or []
        self.requirements_data = requirements_data or []
        self.professions_meta = professions_meta or []
        self.tools_meta = tools_meta or []
        self.buildings_meta = buildings_meta or []
        
        # Track fixes applied
        self.fixes_applied = []
        self.items_created = []
        self.references_fixed = []
        
        # Create lookups for efficient searching
        self.item_lookup = {item.get('id'): item for item in self.items_data if item.get('id')}
        self.item_name_lookup = {item.get('name', '').lower(): item for item in self.items_data if item.get('name')}
        self.craft_lookup = {craft.get('id'): craft for craft in self.crafts_data if craft.get('id')}
        
    def suggest_item_id_fix(self, broken_ref):
        """Suggest a fix for a broken item reference"""
        if not broken_ref or ':' not in broken_ref:
            return None
            
        # Extract the item name from the broken ID
        parts = broken_ref.split(':')
        if len(parts) < 3:
            return None
            
        item_name_part = parts[-1].replace('-', ' ').title()
        
        # Look for fuzzy matches in existing items
        best_matches = []
        
        for existing_id, item in self.item_lookup.items():
            item_name = item.get('name', '')
            
            # Exact name match (case insensitive)
            if item_name.lower() == item_name_part.lower():
                return existing_id
                
            # Fuzzy name match (contains or similar)
            if (item_name_part.lower() in item_name.lower() or 
                item_name.lower() in item_name_part.lower()):
                best_matches.append((existing_id, item_name))
        
        # Try "Plain" prefix variations
        plain_name = f"Plain {item_name_part}"
        for existing_id, item in self.item_lookup.items():
            item_name = item.get('name', '')
            if item_name.lower() == plain_name.lower():
                return existing_id
        
        # Return best fuzzy match if found
        if best_matches:
            return best_matches[0][0]
            
        return None
    
    def create_missing_item(self, broken_ref, context="unknown"):
        """Create a missing item based on broken reference"""
        if not broken_ref or ':' not in broken_ref:
            return None
            
        parts = broken_ref.split(':')
        if len(parts) < 3:
            return None
            
        entity_type = parts[0]
        profession = parts[1]
        item_name_slug = parts[2]
        
        if entity_type != 'item':
            return None
        
        # Convert slug back to readable name
        item_name = item_name_slug.replace('-', ' ').title()
        
        # Create the new item
        new_item = {
            'id': broken_ref,
            'name': item_name,
            'description': f"Auto-created item (from {context})",
            'tier': 1,
            'rank': 'Common'
        }
        
        return new_item
    
    def fix_broken_item_references(self, dry_run=False):
        """Find and fix broken item references in crafts"""
        fixes = []
        
        print(f"\n{Colors.header('🔧 ANALYZING BROKEN ITEM REFERENCES')}")
        
        for craft in self.crafts_data:
            craft_id = craft.get('id', 'unknown')
            craft_name = craft.get('name', 'unknown')
            
            # Check materials
            if 'materials' in craft:
                for i, material in enumerate(craft['materials']):
                    item_ref = material.get('item', '')
                    if item_ref and item_ref not in self.item_lookup:
                        # Try to find a fix
                        suggested_fix = self.suggest_item_id_fix(item_ref)
                        
                        if suggested_fix:
                            fix_info = {
                                'type': 'reference_fix',
                                'craft_id': craft_id,
                                'craft_name': craft_name,
                                'section': 'materials',
                                'index': i,
                                'old_ref': item_ref,
                                'new_ref': suggested_fix,
                                'existing_item_name': self.item_lookup[suggested_fix].get('name', '')
                            }
                            fixes.append(fix_info)
                        else:
                            # Create missing item
                            new_item = self.create_missing_item(item_ref, f"craft {craft_name} material")
                            if new_item:
                                fix_info = {
                                    'type': 'create_item',
                                    'craft_id': craft_id,
                                    'craft_name': craft_name,
                                    'section': 'materials',
                                    'index': i,
                                    'broken_ref': item_ref,
                                    'new_item': new_item
                                }
                                fixes.append(fix_info)
            
            # Check outputs
            if 'outputs' in craft:
                for i, output in enumerate(craft['outputs']):
                    item_ref = output.get('item', '')
                    if item_ref and item_ref not in self.item_lookup:
                        # Try to find a fix
                        suggested_fix = self.suggest_item_id_fix(item_ref)
                        
                        if suggested_fix:
                            fix_info = {
                                'type': 'reference_fix',
                                'craft_id': craft_id,
                                'craft_name': craft_name,
                                'section': 'outputs',
                                'index': i,
                                'old_ref': item_ref,
                                'new_ref': suggested_fix,
                                'existing_item_name': self.item_lookup[suggested_fix].get('name', '')
                            }
                            fixes.append(fix_info)
                        else:
                            # Create missing item
                            new_item = self.create_missing_item(item_ref, f"craft {craft_name} output")
                            if new_item:
                                fix_info = {
                                    'type': 'create_item',
                                    'craft_id': craft_id,
                                    'craft_name': craft_name,
                                    'section': 'outputs',
                                    'index': i,
                                    'broken_ref': item_ref,
                                    'new_item': new_item
                                }
                                fixes.append(fix_info)
        
        if not fixes:
            print(f"   {Colors.success('✅ No broken item references found!')}")
            return []
        
        # Show what will be fixed
        reference_fixes = [f for f in fixes if f['type'] == 'reference_fix']
        create_fixes = [f for f in fixes if f['type'] == 'create_item']
        
        print(f"   {Colors.info(f'Found {len(fixes)} issues to fix:')}")
        print(f"   • {Colors.colorize(str(len(reference_fixes)), Colors.YELLOW)} reference corrections")
        print(f"   • {Colors.colorize(str(len(create_fixes)), Colors.GREEN)} items to create")
        
        if not dry_run:
            print(f"\n{Colors.header('APPLYING FIXES:')}")
            self._apply_fixes(fixes)
        else:
            print(f"\n{Colors.header('PREVIEW OF FIXES:')}")
            self._preview_fixes(fixes)
        
        return fixes
    
    def _preview_fixes(self, fixes):
        """Preview what fixes would be applied"""
        for fix in fixes:
            if fix['type'] == 'reference_fix':
                print(f"   {Colors.colorize('🔗', Colors.YELLOW)} {fix['craft_name']} ({fix['section']})")
                print(f"      {Colors.colorize(fix['old_ref'], Colors.RED)} → {Colors.colorize(fix['new_ref'], Colors.GREEN)}")
                print(f"      Reason: Found existing item '{fix['existing_item_name']}'")
            
            elif fix['type'] == 'create_item':
                new_item = fix['new_item']
                print(f"   {Colors.colorize('➕', Colors.GREEN)} Create missing item: {Colors.highlight(new_item['id'])}")
                print(f"      Name: {new_item['name']}")
                print(f"      Used by: {fix['craft_name']} ({fix['section']})")
    
    def _apply_fixes(self, fixes):
        """Actually apply the fixes to the data"""
        items_to_create = []
        
        for fix in fixes:
            if fix['type'] == 'reference_fix':
                # Update the craft reference
                craft = self.craft_lookup.get(fix['craft_id'])
                if craft and fix['section'] in craft:
                    craft[fix['section']][fix['index']]['item'] = fix['new_ref']
                    print(f"   {Colors.colorize('✓', Colors.GREEN)} Fixed reference in {fix['craft_name']}")
                    print(f"      {Colors.gray(f'{fix['old_ref']} → {fix['new_ref']}')}")
                    self.references_fixed.append(fix)
            
            elif fix['type'] == 'create_item':
                items_to_create.append(fix['new_item'])
                self.items_created.append(fix['new_item'])
        
        # Add new items to the items data
        if items_to_create:
            for new_item in items_to_create:
                self.items_data.append(new_item)
                self.item_lookup[new_item['id']] = new_item
                print(f"   {Colors.colorize('✓', Colors.GREEN)} Created item: {Colors.highlight(new_item['id'])}")
                print(f"      Name: {new_item['name']}")
        
        self.fixes_applied.extend(fixes)
    
    def fix_profession_inconsistencies(self, dry_run=False):
        """Fix items that have wrong profession in their ID"""
        fixes = []
        
        print(f"\n{Colors.header('🔧 ANALYZING PROFESSION INCONSISTENCIES')}")
        
        # Build profession mapping from crafts (what profession creates each item)
        item_to_creating_profession = {}
        
        for craft in self.crafts_data:
            craft_id = craft.get('id', '')
            if ':' in craft_id:
                craft_profession = craft_id.split(':')[1]
                
                # Map output items to this profession
                for output in craft.get('outputs', []):
                    item_ref = output.get('item', '')
                    if item_ref:
                        item_to_creating_profession[item_ref] = craft_profession
        
        # Check for profession mismatches
        for item in self.items_data:
            item_id = item.get('id', '')
            item_name = item.get('name', '')
            
            if ':' not in item_id:
                continue
                
            parts = item_id.split(':')
            if len(parts) < 3:
                continue
                
            current_profession = parts[1]
            creating_profession = item_to_creating_profession.get(item_id)
            
            if creating_profession and creating_profession != current_profession:
                # This item should be in a different profession
                correct_id = f"item:{creating_profession}:{parts[2]}"
                
                # Check if the correct ID already exists
                if correct_id not in self.item_lookup:
                    fix_info = {
                        'type': 'profession_fix',
                        'old_id': item_id,
                        'new_id': correct_id,
                        'item_name': item_name,
                        'old_profession': current_profession,
                        'new_profession': creating_profession,
                        'item': item
                    }
                    fixes.append(fix_info)
        
        if not fixes:
            print(f"   {Colors.success('✅ No profession inconsistencies found!')}")
            return []
        
        print(f"   {Colors.info(f'Found {len(fixes)} profession inconsistencies to fix')}")
        
        if not dry_run:
            print(f"\n{Colors.header('APPLYING PROFESSION FIXES:')}")
            self._apply_profession_fixes(fixes)
        else:
            print(f"\n{Colors.header('PREVIEW OF PROFESSION FIXES:')}")
            self._preview_profession_fixes(fixes)
        
        return fixes
    
    def _preview_profession_fixes(self, fixes):
        """Preview profession fixes"""
        for fix in fixes:
            print(f"   {Colors.colorize('🔄', Colors.CYAN)} {fix['item_name']}")
            print(f"      {Colors.colorize(fix['old_id'], Colors.RED)} → {Colors.colorize(fix['new_id'], Colors.GREEN)}")
            print(f"      Profession: {fix['old_profession']} → {fix['new_profession']}")
    
    def _apply_profession_fixes(self, fixes):
        """Apply profession fixes"""
        for fix in fixes:
            # Update the item ID
            old_item = fix['item']
            old_item['id'] = fix['new_id']
            
            # Update lookups
            if fix['old_id'] in self.item_lookup:
                del self.item_lookup[fix['old_id']]
            self.item_lookup[fix['new_id']] = old_item
            
            # Update all craft references to this item
            for craft in self.crafts_data:
                # Update materials
                for material in craft.get('materials', []):
                    if material.get('item') == fix['old_id']:
                        material['item'] = fix['new_id']
                
                # Update outputs
                for output in craft.get('outputs', []):
                    if output.get('item') == fix['old_id']:
                        output['item'] = fix['new_id']
            
            print(f"   {Colors.colorize('✓', Colors.GREEN)} Fixed profession for: {fix['item_name']}")
            print(f"      {Colors.gray(f'{fix['old_id']} → {fix['new_id']}')}")
            
            self.fixes_applied.append(fix)
    
    def save_fixes_to_files(self):
        """Save the fixed data back to files"""
        if not self.fixes_applied:
            print(f"\n{Colors.info('No fixes to save.')}")
            return False
        
        print(f"\n{Colors.header('💾 SAVING FIXES TO FILES')}")
        
        try:
            # Save items
            if any(f['type'] in ['create_item', 'profession_fix'] for f in self.fixes_applied):
                save_json(ITEMS_DATA_PATH, self.items_data)
                print(f"   {Colors.colorize('✓', Colors.GREEN)} Saved {Colors.highlight('items.json')}")
            
            # Save crafts
            if any(f['type'] == 'reference_fix' for f in self.fixes_applied):
                save_json(CRAFTS_DATA_PATH, self.crafts_data)
                print(f"   {Colors.colorize('✓', Colors.GREEN)} Saved {Colors.highlight('crafts.json')}")
            
            return True
            
        except Exception as e:
            print(f"   {Colors.error(f'Error saving files: {e}')}")
            return False
    
    def print_summary(self):
        """Print summary of all fixes applied"""
        print(f"\n{Colors.section_divider('AUTO-FIX SUMMARY', 60)}")
        
        reference_fixes = len([f for f in self.fixes_applied if f['type'] == 'reference_fix'])
        profession_fixes = len([f for f in self.fixes_applied if f['type'] == 'profession_fix'])
        items_created = len([f for f in self.fixes_applied if f['type'] == 'create_item'])
        
        print(f"  {Colors.highlight('Fixes Applied:')} {Colors.bold(str(len(self.fixes_applied)))}")
        print(f"  • {Colors.colorize(str(reference_fixes), Colors.YELLOW)} reference corrections")
        print(f"  • {Colors.colorize(str(profession_fixes), Colors.CYAN)} profession fixes")
        print(f"  • {Colors.colorize(str(items_created), Colors.GREEN)} items created")
        
        if self.items_created:
            print(f"\n  {Colors.colorize('New Items Created:', Colors.GREEN)}")
            for item in self.items_created[:5]:  # Show first 5
                print(f"    • {Colors.highlight(item['id'])}: {item['name']}")
            if len(self.items_created) > 5:
                remaining = len(self.items_created) - 5
                print(f"    {Colors.gray(f'... and {remaining} more')}")

def main():
    print("="*80)
    print("BitCrafty Auto-Fixing Data Integrity Validator")
    print("="*80)
    
    # Ask user for mode
    print("\nSelect mode:")
    print("1. Preview fixes only (dry run)")
    print("2. Apply fixes automatically")
    
    while True:
        choice = input("\nEnter choice [1/2]: ").strip()
        if choice in ['1', '2']:
            break
        print("Please enter 1 or 2")
    
    dry_run = (choice == '1')
    
    print(f"\n1. Loading BitCrafty data files...")
    try:
        items_data = load_json(ITEMS_DATA_PATH)
        crafts_data = load_json(CRAFTS_DATA_PATH) 
        requirements_data = load_json(REQUIREMENTS_DATA_PATH)
        professions_meta = load_json(PROFESSIONS_META_PATH)
        tools_meta = load_json(TOOLS_META_PATH)
        buildings_meta = load_json(BUILDINGS_META_PATH)
        
        print(f"   ✅ Loaded {len(items_data or [])} items")
        print(f"   ✅ Loaded {len(crafts_data or [])} crafts")
        print(f"   ✅ Loaded {len(requirements_data or [])} requirements")
        
    except Exception as e:
        print(f"   ❌ Error loading data files: {e}")
        return False
    
    # Create backup if applying fixes
    if not dry_run:
        print(f"\n2. Creating backup...")
        backup_path = create_backup()
        if backup_path:
            print(f"   ✅ Backup created: {Colors.highlight(backup_path)}")
        else:
            print(f"   ⚠️  Could not create backup - continuing anyway")
    
    print(f"\n3. Creating auto-fix validator...")
    validator = AutoFixValidator(
        items_data, crafts_data, requirements_data,
        professions_meta, tools_meta, buildings_meta
    )
    
    # Run fixes
    print(f"\n4. Running auto-fixes...")
    
    broken_ref_fixes = validator.fix_broken_item_references(dry_run)
    profession_fixes = validator.fix_profession_inconsistencies(dry_run)
    
    total_fixes = len(broken_ref_fixes) + len(profession_fixes)
    
    if total_fixes == 0:
        print(f"\n{Colors.success('✅ NO ISSUES FOUND - Data integrity is good!')}")
        return True
    
    if dry_run:
        print(f"\n{Colors.info('🔍 DRY RUN COMPLETE')}")
        print(f"Found {Colors.bold(str(total_fixes))} issues that can be auto-fixed")
        print(f"Run with mode 2 to apply these fixes")
        return True
    
    # Save fixes
    print(f"\n5. Saving fixes...")
    if validator.save_fixes_to_files():
        print(f"   {Colors.success('✅ All fixes saved successfully!')}")
        
        # Run final validation
        print(f"\n6. Running final validation...")
        final_validator = DataIntegrityValidator(
            validator.items_data, validator.crafts_data, requirements_data,
            professions_meta, tools_meta, buildings_meta
        )
        
        is_valid = final_validator.run_all_validations()
        
        if is_valid:
            print(f"   {Colors.success('✅ Final validation passed!')}")
        else:
            print(f"   {Colors.warning('⚠️  Some issues remain after auto-fixing')}")
            final_validator.print_errors()
        
        validator.print_summary()
        return True
    else:
        print(f"   {Colors.error('❌ Error saving fixes')}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
