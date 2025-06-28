"""
Test simulation of the problematic "Basic Clay Crafting" false positive.

This demonstrates how our new validation would have prevented the issue.
"""

# Simulated AI response that created the false positive
problematic_craft = {
    "name": "Basic Clay Crafting",
    "requirements": {
        "profession": None,  # No profession requirement
        "building": None,    # No building requirement  
        "tool": None         # No tool requirement
    },
    "materials": [],  # No materials list
    "outputs": [],    # No outputs list
    "confidence": 0.85  # High confidence from AI
}

print("Problematic Craft Analysis:")
print("=" * 40)
print(f"Name: {problematic_craft['name']}")
print(f"Requirements: {problematic_craft['requirements']}")
print(f"Materials: {problematic_craft['materials']}")
print(f"Outputs: {problematic_craft['outputs']}")
print(f"Confidence: {problematic_craft['confidence']}")
print()

print("New Validation Results:")
print("=" * 40)

# Our validation logic (simplified)
requirements = problematic_craft.get('requirements', {})
confidence = problematic_craft.get('confidence', 0)
materials = problematic_craft.get('materials', [])
outputs = problematic_craft.get('outputs', [])

validation_failures = []

# Check confidence (would pass with 0.85 vs 0.7 threshold)
if confidence < 0.7:
    validation_failures.append(f"Confidence {confidence:.2f} below threshold 0.7")

# Check empty requirements
if not requirements or all(not v for v in requirements.values()):
    validation_failures.append("Empty or missing requirements (profession, building, tool)")

# Check meaningful requirements
profession = str(requirements.get('profession', '') or '').strip()
building = str(requirements.get('building', '') or '').strip()
tool = str(requirements.get('tool', '') or '').strip()

if not any([profession, building, tool]):
    validation_failures.append("No meaningful profession, building, or tool requirements")

# Check materials and outputs
if not materials:
    validation_failures.append("Missing or empty materials list")

if not outputs:
    validation_failures.append("Missing or empty outputs list")

is_valid = len(validation_failures) == 0

print(f"Valid: {is_valid}")
if not is_valid:
    print("Validation Failures:")
    for i, failure in enumerate(validation_failures, 1):
        print(f"  {i}. {failure}")
    print()
    print("Result: This craft would be REJECTED and not saved to crafts.json")
else:
    print("Result: This craft would be accepted")

print()
print("Conclusion:")
print("=" * 40)
print("The new validation system would have prevented the 'Basic Clay Crafting'")
print("false positive by detecting empty requirements and missing materials/outputs.")
