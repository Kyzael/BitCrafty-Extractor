# BitCrafty-Extractor Reconciliator

## Purpose

The Reconciliator transforms BitCrafty-Extractor's exported data into BitCrafty's canonical format. It handles ID mapping, profession assignment, and safely updates all data files with automatic backups and validation.

### 🎯 Quick Example

| Extractor Output          | BitCrafty Format              |
|---------------------------|-------------------------------|
| "Rough Plank"             | `item:carpentry:rough-plank`  |
| "1/2 Cook Mushroom Skewer"| `craft:cooking:mushroom-skewer` |
| "Tier 1 Saw"              | `tool:saw`                    |

---

## 🚀 Usage

```powershell
# Navigate to reconciliator directory
cd G:\SC\BitCrafty-Extractor\reconciliator

# Run the tool
python reconciliator.py
```

The tool will:
1. **Load** extractor exports and BitCrafty data
2. **Show** a summary of proposed changes
3. **Ask** for confirmation before applying changes
4. **Apply** changes in correct order with automatic backup

### Example Output
```
RECONCILIATION SUMMARY
================================================================================

Ready to apply 19 changes to BitCrafty data:
  • 7 item ID updates
  • 3 new items
  • 4 new crafts
  • 4 new requirements
  • 1 new building

Apply these changes? [Yes/No] or [Details/Backups]: y
```

---

## ✅ Key Features

- **Smart Profession Mapping** - Output items get craft profession, input materials keep original
- **Intelligent Building Detection** - Prevents duplicate buildings using requirement validation  
- **Automatic Backups** - Creates timestamped backups before any changes
- **Data Validation** - Comprehensive integrity checks before and after changes
- **Interactive Interface** - Review changes with detailed breakdowns and backup management
- **Reference Updates** - Automatically fixes all item/craft references when IDs change

---

## 🔄 Backup Management

Access during confirmation with **[B]ackups** option:

- **List** - View available backups and their contents
- **Restore** - Restore BitCrafty data from any backup  
- **Clean** - Remove old backups (keeps 10 most recent)
- **Validate** - Check current data integrity

Backups are stored in `G:\SC\BitCrafty\data\backups\` (git-ignored).

---

## 🔧 Configuration

Update the BitCrafty path if needed:

```python
# In reconciliator.py
BITCRAFTY_DATA_DIR = r'G:\SC\BitCrafty\data'
```

---

## 🎯 Recent Success

Latest reconciliation processed **19 changes** successfully:
- 7 item ID updates, 3 new items, 4 new crafts, 4 new requirements, 1 new building
- Complete data integrity validation passed on 121 total entities

**See BitCrafty/data/README.md for ID and data format standards.**
