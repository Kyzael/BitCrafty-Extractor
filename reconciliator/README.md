# BitCrafty-Extractor Reconciliator

## Purpose

The Reconciliator bridges BitCrafty-Extractor’s `/exports/it### 🎯 Example ID Mapping

| Extracto## ✅ Completed & 🚀 Future Features

### Currently Implemented ✅
- ✅ **One-click reconciliation** for all entity types (items, crafts, requirements, metadata)
- ✅ **Interactive confirmation** with detailed change preview
- ✅ **Automatic backup system** with timestamped backups
- ✅ **Backup management** (list, restore, cleanup)
- ✅ **Post-change data integrity validation** using BitCrafty's CI validation logic
- ✅ **Colorful CLI interface** with ANSI colors for improved user experience
- ✅ **Strict adherence** to BitCrafty's ID and data standards

### Potential Future Enhancements 🚀

#### Enhanced Backup System
- **Backup Compression**: Compress old backups to save disk space
- **Selective Restore**: Restore individual files instead of full backup
- **Backup Verification**: Validate backup integrity and checksums
- **Remote Backup**: Support for cloud backup storage

#### Configuration Management
- **Config File Support**: YAML/JSON configuration for paths and settings
- **Environment Variables**: Support for different deployment environments
- **Multiple Profiles**: Switch between different BitCrafty installations

#### Advanced User Experience
- **Progress Tracking**: Progress bars for large dataset processing
- **Detailed Reporting**: Generate HTML/PDF reports of changes made
- **Batch Operations**: Process multiple extractor sessions at once
- **Dry Run Mode**: Enhanced preview mode without file system access

#### Integration Features
- **CI/CD Integration**: Automated reconciliation in build pipelines
- **API Mode**: REST API for programmatic access
- **Webhook Support**: Notifications when reconciliation completes
- **Git Integration**: Automatic commits of reconciliation changesut Name      | Profession   | BitCrafty ID                  |
|---------------------------|--------------|-------------------------------|
| "Rough Plank"             | carpentry    | item:carpentry:rough-plank    |
| "Cook Plain Mushroom Skewer"| cooking    | craft:cooking:plain-mushroom-skewer |
| "Tier 1 Saw" (tool)       | —            | tool:saw                      |
| "1/2 Craft Recipe"        | cooking      | craft:cooking:craft-recipe    |

---

## Current Implementation Status

### ✅ Completed Features
- **Full Data Reconciliation**: Items, crafts, requirements, and metadata processing
- **ID Transformation**: Converts extracted data to BitCrafty format (`[entity-type]:[profession]:[identifier]`)
- **Smart Conflict Resolution**: Handles craft name conflicts by adding input material context
- **Shared Requirements**: Extracts and manages reusable requirement objects across crafts
- **Metadata Generation**: Auto-creates new professions, tools, and buildings
- **Interactive Confirmation**: Detailed change preview with user confirmation
- **Reference Updates**: Updates all item references when IDs change
- **DeepDiff Integration**: Advanced comparison capabilities for data differences
- **Automatic Backup System**: Creates timestamped backups before applying changes
- **Backup Management**: List, restore, and clean up backups through interactive interface
- **Data Integrity Validation**: Pre and post-change validation using BitCrafty's test suite logic
- **Rollback Protection**: Prevents data corruption through comprehensive validation checks

### 🔧 Current Workflow

1. **Data Loading & Validation**
   - Loads extractor exports from `/exports/` directory
   - Loads canonical BitCrafty data from configurable path (`G:\SC\BitCrafty\data`)
   - Validates JSON structure and handles missing files gracefully

2. **Transform & Normalize**
   - Converts all extracted entities to BitCrafty ID format
   - Cleans AI-generated prefixes from craft names (e.g., "1/2 Recipe Name" → "Recipe Name")
   - Builds profession mappings from craft data
   - Resolves craft name conflicts by adding input material context

3. **Requirements Processing**
   - Extracts unique requirement combinations from crafts
   - Creates shared requirement objects for profession/tool/building combinations
   - Generates requirement IDs: `requirement:profession:tool:building`
   - Updates crafts to reference requirement IDs instead of inline requirements

4. **Comparison & Analysis**
   - Matches entities by name first, then by ID
   - Identifies new items, crafts, requirements, and metadata
   - Tracks ID updates needed for existing items with name matches
   - Updates craft references when item IDs change
   - Provides detailed change tracking with confidence scores

5. **Interactive Review**
   - Shows comprehensive summary of all changes
   - Provides detailed view with line-by-line changes
   - Allows user to review before applying changes
   - Supports cancellation at any point

6. **Data Application**
   - Runs pre-change validation to detect existing data issues
   - Creates automatic backup before applying any changes
   - Updates BitCrafty JSON files atomically
   - Maintains referential integrity across all files
   - Runs post-change validation to ensure data integrity
   - Provides detailed success/failure feedback with rollback guidance
   - Updates multiple files: items.json, crafts.json, requirements.json, buildings.json
   - Cleans up old backups automatically (keeps 10 most recent)

### 🏃‍♂️ Usage

---

```powershell
# Navigate to the reconciliator directory
cd G:\SC\BitCrafty-Extractor\reconciliator

# Run the reconciliation tool
python reconciliator.py
```

The tool will:
1. Load and analyze both extractor exports and BitCrafty data
2. Show a summary of all proposed changes
3. Allow you to view detailed changes with 'd' option
4. Require confirmation before applying any changes
5. Update all relevant BitCrafty data files

### 📊 Example Output
```
RECONCILIATION SUMMARY
================================================================================

ITEMS:
  New items to add: 2
  Items to update: 0
  Items needing ID updates: 3
  Identical items: 8

CRAFTS:
  New crafts to add: 4
  Crafts to update: 0
  Identical crafts: 12

REQUIREMENTS:
  New requirements to add: 4
  Requirements to update: 0
  Existing requirements: 2

METADATA:
  Buildings - New: 1, Existing: 3

Ready to apply 12 changes to BitCrafty data:
  • 3 item ID updates
  • 2 new items
  • 4 new crafts
  • 4 new requirements
  • 1 new buildings

Apply these changes? [y/N/d for details/b for backup management]:
```

### 🔄 Backup Management

The reconciliator includes a comprehensive backup system:

#### Automatic Backups
- **Pre-Change Backups**: Automatically creates timestamped backups before applying any changes
- **File Coverage**: Backs up all BitCrafty data files (items, crafts, requirements, metadata)
- **Manifest Tracking**: Each backup includes a manifest with timestamp and file list
- **Automatic Cleanup**: Keeps only the 10 most recent backups by default

#### Interactive Backup Management
Access backup management during confirmation with the 'b' option:

```
Backup actions: [l]ist files, [r]estore, [c]lean old, [v]alidate data, [q]uit backup management:

Found 3 backups:
  1. backup_20250629_143022 - 2025-06-29T14:30:22 (6 files)
  2. backup_20250629_142815 - 2025-06-29T14:28:15 (6 files)
  3. backup_20250629_141203 - 2025-06-29T14:12:03 (6 files)
```

#### Backup Features
- **List Files**: View what files are included in each backup
- **Restore**: Restore BitCrafty data from any backup (with confirmation)
- **Clean Up**: Remove old backups, keeping only recent ones
- **Data Validation**: Run integrity checks on current BitCrafty data
- **Safe Storage**: Backups stored in `G:\SC\BitCrafty\data\backups\` (git-ignored)

### 🔒 Data Integrity Protection

The reconciliator includes comprehensive data integrity validation based on BitCrafty's existing CI test suite:

#### Validation Checks
- **Entity ID Format**: Ensures all IDs follow `[type]:[profession]:[identifier]` format
- **Reference Integrity**: Validates all item, craft, and requirement references
- **Profession Categories**: Verifies profession references against metadata
- **Requirement Validation**: Checks tool, building, and profession references in requirements
- **Duplicate Detection**: Identifies duplicate entity IDs across all data files
- **Missing Data**: Detects entities with missing names or required fields
- **Orphaned Requirements**: Warns about unused requirement definitions

#### Validation Workflow
1. **Pre-Change Validation**: Optional check for existing data issues before reconciliation
2. **Post-Change Validation**: Automatic verification after applying changes
3. **Backup Validation**: Manual validation command in backup management
4. **Rollback Guidance**: Clear instructions if validation fails after changes

#### Example Validation Output
```
[VALIDATION] ✅ Data integrity verification PASSED
[VALIDATION] Validated 156 entities (42 items, 89 crafts, 25 requirements)
[VALIDATION] 2 warnings found
[VALIDATION]   - Requirement "requirement:cooking:basic" is not used by any craft
```

---

## Planned Features

- One-click reconciliation for all entity types (items, crafts, requirements, metadata).
- Batch diff/confirmation table for upserts.
- Dry run mode for safe review.
- Strict adherence to BitCrafty’s ID and data standards.

---

## 📁 Technical Implementation

### File Structure
```
reconciliator/
├── reconciliator.py        # Main reconciliation logic
├── __init__.py            # Package initialization
└── README.md              # This documentation
```

### Dependencies
- **Python 3.11+**: Core language requirements
- **deepdiff**: Advanced data comparison (automatically installed)
- **Standard Library**: json, os, copy, datetime, shutil for data manipulation and backup operations

### Data Flow
```
Extractor Exports → Normalization → Comparison → User Review → BitCrafty Updates
       ↓                  ↓             ↓           ↓              ↓
   items.json      ID Transform    DeepDiff   Interactive    File Updates
   crafts.json     Name Cleanup    Analysis   Confirmation   Reference Fix
```

### Key Functions
- `normalize_extractor_data()`: Transforms extracted data to BitCrafty format
- `extract_requirements_from_crafts()`: Creates shared requirement objects
- `compare_entities()`: Identifies differences and needed changes
- `resolve_craft_name_conflicts()`: Handles duplicate craft names intelligently
- `create_backup()`: Creates timestamped backups with manifest tracking
- `restore_from_backup()`: Restores BitCrafty data from specific backup
- `validate_data_integrity_post_change()`: Runs comprehensive data validation
- `DataIntegrityValidator`: Full validation suite based on BitCrafty's test logic
- `apply_changes()`: Safely updates BitCrafty data files with validation

---

## 🔧 Configuration

### Path Configuration
The tool uses a direct path configuration for easy setup:

```python
# Current configuration in reconciliator.py
BITCRAFTY_DATA_DIR = r'G:\SC\BitCrafty\data'
```

To use a different BitCrafty installation, simply update this path in the file.

---

**See BitCrafty/data/README.md for ID and data format standards.**
