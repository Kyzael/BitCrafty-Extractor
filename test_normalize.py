#!/usr/bin/env python3

from reconciliator.reconciliator import normalize_name, transform_to_bitcrafty_id

print('Testing normalize_name function:')
test_cases = [
    "Miner's Pick",
    "Smith's Hammer", 
    "Worker's Tools",
    "Beast's Claw",
    "Giant's Strength",
    "Lord's Equipment",
    "Master Craftsman's Kit",
    "Tailor's Needle"
]

for test in test_cases:
    normalized = normalize_name(test)
    print(f'  "{test}" -> "{normalized}"')

print('\nTesting transform_to_bitcrafty_id function:')
print(f'  Item: {transform_to_bitcrafty_id("item", "Miner\'s Pick", "Mining")}')
print(f'  Item: {transform_to_bitcrafty_id("item", "Smith\'s Hammer", "Blacksmithing")}')
print(f'  Craft: {transform_to_bitcrafty_id("craft", "Tailor\'s Kit", "Tailoring")}')

print('\nTesting profession normalization:')
professions = ["Mining", "Blacksmithing", "Tailor's Guild", "Beast Master's Trade"]
for prof in professions:
    normalized = normalize_name(prof)
    print(f'  "{prof}" -> "{normalized}"')
