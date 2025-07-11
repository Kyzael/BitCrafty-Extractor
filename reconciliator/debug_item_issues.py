#!/usr/bin/env python3
"""
Debug script to identify why reconciliator thinks it needs to create items that already exist
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from reconciliator import (
    load_json, normalize_extractor_data, compare_entities, load_bitcrafty_data,
    ITEMS_DATA_PATH, CRAFTS_DATA_PATH
)

def main():
    print("="*80)
    print("BitCrafty Item Creation Debug")
    print("="*80)
    
    # Load extractor exports
    print("\n1. Loading extractor exports...")
    items_export = load_json('../exports/items.json')
    crafts_export = load_json('../exports/crafts.json')
    
    # Load BitCrafty data
    print("2. Loading BitCrafty data...")
    items_data = load_json(ITEMS_DATA_PATH)
    crafts_data = load_json(CRAFTS_DATA_PATH)
    
    print("3. Normalizing extractor data...")
    normalized_items, normalized_crafts = normalize_extractor_data(items_export, crafts_export)
    
    print("4. Loading BitCrafty canonical data...")
    bitcrafty_items, bitcrafty_crafts = load_bitcrafty_data(items_data, crafts_data)
    
    print("5. Comparing entities...")
    changes = compare_entities(normalized_items, normalized_crafts, bitcrafty_items, bitcrafty_crafts)
    
    # Focus on the problematic items
    problem_items = [
        'item:farming:wispweave-plant',
        'item:farming:wispweave-seeds', 
        'item:masonry:foresters-pot'
    ]
    
    print("\n" + "="*80)
    print("PROBLEM ITEM ANALYSIS")
    print("="*80)
    
    for item_id in problem_items:
        print(f"\n🔍 Analyzing: {item_id}")
        
        # Check if it exists in normalized (extractor) data
        if item_id in normalized_items:
            extractor_item = normalized_items[item_id]
            print(f"  📤 Extractor normalized item:")
            print(f"     Name: '{extractor_item['name']}'")
            print(f"     ID: {extractor_item['id']}")
        else:
            print(f"  ❌ NOT found in extractor normalized data")
        
        # Check if it exists in BitCrafty data
        if item_id in bitcrafty_items:
            bitcrafty_item = bitcrafty_items[item_id]
            print(f"  📥 BitCrafty existing item:")
            print(f"     Name: '{bitcrafty_item['name']}'")
            print(f"     ID: {bitcrafty_item['id']}")
        else:
            print(f"  ❌ NOT found in BitCrafty existing data")
        
        # Check what the reconciliator thinks about this item
        if item_id in changes['items']['new']:
            print(f"  🆕 Reconciliator wants to CREATE this item:")
            new_item = changes['items']['new'][item_id]
            print(f"     Name: '{new_item['name']}'")
            print(f"     ID: {new_item['id']}")
        elif item_id in changes['items']['updated']:
            print(f"  🔄 Reconciliator wants to UPDATE this item")
        elif item_id in changes['items']['identical']:
            print(f"  ✅ Reconciliator considers this item IDENTICAL")
        else:
            print(f"  ❓ Reconciliator has no opinion on this item")
    
    # Now let's find items with similar names in BitCrafty
    print("\n" + "="*80)
    print("SIMILAR ITEMS IN BITCRAFTY")
    print("="*80)
    
    # Create name lookup for BitCrafty items
    bitcrafty_by_name = {}
    for item_id, item in bitcrafty_items.items():
        name = item.get('name', '').lower()
        if name:
            bitcrafty_by_name[name] = (item_id, item)
    
    search_terms = ['wispweave', 'forester', 'pot']
    for term in search_terms:
        print(f"\n🔍 BitCrafty items containing '{term}':")
        for name, (item_id, item) in bitcrafty_by_name.items():
            if term in name:
                print(f"  • {item_id}: '{item['name']}'")
    
    # Let's also check what items the extractor exports contain with these names
    print("\n" + "="*80)
    print("EXTRACTOR EXPORTED ITEMS")
    print("="*80)
    
    if items_export and 'items' in items_export:
        for term in search_terms:
            print(f"\n🔍 Extractor items containing '{term}':")
            for item in items_export['items']:
                name = item.get('name', '').lower()
                if term in name:
                    print(f"  • '{item['name']}'")
    
    # Check what crafts reference these items
    print("\n" + "="*80)
    print("CRAFT REFERENCES")
    print("="*80)
    
    if crafts_export and 'crafts' in crafts_export:
        for term in search_terms:
            print(f"\n🔍 Crafts referencing items with '{term}':")
            for craft in crafts_export['crafts']:
                craft_name = craft.get('name', '')
                
                # Check materials
                for material in craft.get('materials', []):
                    item_name = material.get('item', '').lower()
                    if term in item_name:
                        print(f"  • {craft_name} (material): '{material['item']}'")
                
                # Check outputs
                for output in craft.get('outputs', []):
                    item_name = output.get('item', '').lower()
                    if term in item_name:
                        print(f"  • {craft_name} (output): '{output['item']}'")

if __name__ == "__main__":
    main()
