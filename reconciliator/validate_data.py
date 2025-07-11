#!/usr/bin/env python3
"""
Data Integrity Validation Script
Runs the DataIntegrityValidator to find and suggest fixes for broken item references.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

# Import all functions and classes from reconciliator
from reconciliator import (
    load_json, DataIntegrityValidator,
    ITEMS_DATA_PATH, CRAFTS_DATA_PATH, REQUIREMENTS_DATA_PATH,
    PROFESSIONS_META_PATH, TOOLS_META_PATH, BUILDINGS_META_PATH
)

def main():
    print("="*80)
    print("BitCrafty Data Integrity Validator")
    print("="*80)
    
    print("\n1. Loading BitCrafty data files...")
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
        print(f"   ✅ Loaded {len(professions_meta or [])} professions")
        print(f"   ✅ Loaded {len(tools_meta or [])} tools")
        print(f"   ✅ Loaded {len(buildings_meta or [])} buildings")
        
    except Exception as e:
        print(f"   ❌ Error loading data files: {e}")
        return False
    
    print("\n2. Creating validator and running checks...")
    validator = DataIntegrityValidator(
        items_data, crafts_data, requirements_data,
        professions_meta, tools_meta, buildings_meta
    )
    
    print("   🔍 Validating craft item references...")
    print("   🔍 Validating entity profession categories...")
    print("   🔍 Validating craft requirements...")
    print("   🔍 Validating requirement metadata references...")
    print("   🔍 Validating data integrity...")
    
    is_valid = validator.run_all_validations()
    
    print("\n" + "="*80)
    print("VALIDATION RESULTS")
    print("="*80)
    
    if not is_valid:
        print("❌ VALIDATION FAILED - Issues found:")
        print("")
        validator.print_errors()
        
        print("\n" + "="*80)
        print("RECOMMENDATIONS")
        print("="*80)
        print("• Review broken item references above")
        print("• Use suggested fixes where provided")
        print("• Run this validator again after making fixes")
        print("• Consider running the reconciliator to auto-fix some issues")
        
        return False
    else:
        print("✅ VALIDATION PASSED - No issues found!")
        validator.print_summary()
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
