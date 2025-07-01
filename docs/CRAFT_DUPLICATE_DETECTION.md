# Craft Duplicate Detection Improvements

## Overview

The BitCrafty-Extractor has been enhanced to properly handle crafting recipes that share the same name but have different materials, outputs, or requirements. This addresses the issue where legitimate recipe variations (like different Basic Fertilizer recipes) were incorrectly flagged as duplicates.

## Problem Statement

In BitCraft, multiple crafting recipes can have similar or identical names while being genuinely different recipes. Examples include:

1. **Basic Fertilizer Variants:**
   - "Make Basic Fertilizer (Fish)" - uses fish as material
   - "Make Basic Fertilizer (Berry)" - uses berries as material  
   - "Make Basic Fertilizer" - uses farming station building

2. **Building-Specific Recipes:**
   - Same recipe name but different requirements based on the building used
   - Different material quantities based on building efficiency

## Solution

### Enhanced Hash Generation

The craft hash generation now includes **requirements** in addition to name, materials, and outputs:

```python
def _generate_craft_hash(self, craft: Dict[str, Any]) -> str:
    """Generate a unique hash for a craft based on key properties.
    
    For true duplicate detection, includes name, materials, outputs, AND requirements.
    This prevents flagging legitimate crafts with same name but different 
    requirements (like Basic Fertilizer variants) as duplicates.
    """
    # Hash components: name + materials + outputs + requirements
    hash_string = f"{name}|{materials_str}|{outputs_str}|{requirements_str}"
    return hashlib.md5(hash_string.encode('utf-8')).hexdigest()[:12]
```

### Improved Processing Logic

The craft processing logic now distinguishes between:

1. **Exact Duplicates:** Same name, materials, outputs, AND requirements
2. **Similar Crafts:** Same name but different materials/outputs/requirements  
3. **Very Similar Crafts:** Nearly identical crafts that might warrant updating

### Duplicate Detection Rules

A craft is considered a **true duplicate** only if it has identical:
- Name
- Materials (items and quantities)
- Outputs (items and quantities)
- Requirements (profession, building, tool, level)

## Test Coverage

Comprehensive tests verify the following scenarios:

### ✅ Different Recipes Should NOT Be Duplicates

1. **Different Requirements:**
   ```python
   # These are NOT duplicates (different tool vs building requirement)
   craft1 = {
       'name': 'Make Basic Fertilizer',
       'materials': [{'item': 'Basic Berry', 'qty': 1}],
       'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
       'requirements': {'profession': 'farming', 'tool': 'basic_tools'}
   }
   
   craft2 = {
       'name': 'Make Basic Fertilizer', 
       'materials': [{'item': 'Basic Berry', 'qty': 1}],
       'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
       'requirements': {'profession': 'farming', 'building': 'tier1_farming_station'}
   }
   ```

2. **Different Materials:**
   ```python
   # These are NOT duplicates (different input materials)
   fertilizer_fish = {
       'name': 'Make Basic Fertilizer (Fish)',
       'materials': [{'item': 'Breezy Fin Darter', 'qty': 2}],
       'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
       'requirements': {'profession': 'farming', 'tool': 'basic_tools'}
   }
   
   fertilizer_berry = {
       'name': 'Make Basic Fertilizer (Berry)',
       'materials': [{'item': 'Basic Berry', 'qty': 2}],
       'outputs': [{'item': 'Basic Fertilizer', 'qty': 1}],
       'requirements': {'profession': 'farming', 'tool': 'basic_tools'}
   }
   ```

3. **Different Quantities:**
   ```python
   # These are NOT duplicates (different material quantities)
   craft1 = {
       'name': 'Make Test Food',
       'materials': [{'item': 'Ingredient A', 'qty': 1}],
       'outputs': [{'item': 'Test Food', 'qty': 1}],
       'requirements': {'profession': 'cooking'}
   }
   
   craft2 = {
       'name': 'Make Test Food',
       'materials': [{'item': 'Ingredient A', 'qty': 2}],  # Different quantity
       'outputs': [{'item': 'Test Food', 'qty': 1}],
       'requirements': {'profession': 'cooking'}
   }
   ```

### ✅ Identical Recipes Should Be Duplicates

```python
# These ARE duplicates (completely identical)
craft1 = {
    'name': 'Make Test Item',
    'materials': [{'item': 'Material A', 'qty': 2}],
    'outputs': [{'item': 'Test Item', 'qty': 1}],
    'requirements': {'profession': 'farming', 'level': 1}
}

craft2 = craft1.copy()  # Identical
```

## Benefits

1. **Accurate Data Collection:** No longer loses legitimate recipe variations
2. **Better Game Representation:** Correctly represents the complexity of BitCraft's crafting system
3. **Improved User Experience:** BitCrafty app will show all available recipe options
4. **Data Integrity:** Maintains the completeness and accuracy of the crafting database

## Implementation Details

### Hash Algorithm
- Uses MD5 for consistency and speed
- 12-character truncated hash for manageable storage
- Case-insensitive name comparison
- Sorted materials/outputs for consistent ordering
- Non-empty requirements only

### Performance Impact
- Minimal overhead from additional requirement processing
- More accurate duplicate detection reduces false positives
- Better memory efficiency by avoiding unnecessary data loss

## Migration

Existing databases will automatically benefit from the improved logic:
- New extractions will correctly identify unique recipes
- Previous false duplicates can be re-extracted and will now be preserved
- No manual database cleanup required

## Future Enhancements

Potential future improvements:
1. **Similarity Scoring:** Quantify how similar crafts are for better update decisions
2. **Recipe Clustering:** Group related recipes for better UI organization
3. **Confidence Weighting:** Use AI confidence scores more intelligently in duplicate decisions
