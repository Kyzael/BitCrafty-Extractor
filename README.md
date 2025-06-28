# BitCrafty-Extractor

A real-time data extraction tool that monitors the Bitcraft game window to automatically discover and catalog items, crafts, buildings, and professions for the BitCrafty application.

## Overview

BitCrafty-Extractor is a background service that uses computer vision and OCR to read the Bitcraft game window, extract game data, and maintain an up-to-date dataset for BitCrafty. It operates as a passive observer, requiring no game modifications or API access.

## Architecture Design

### Technology Stack
- **Language**: Python 3.11+
- **Computer Vision**: OpenCV for window capture and image processing
- **OCR**: Tesseract with pytesseract for text recognition
- **UI Detection**: Template matching and contour detection
- **Data Processing**: pandas for data manipulation and validation
- **Configuration**: YAML for settings and templates
- **Logging**: structlog for detailed operation logs

### Core Components

#### 1. Window Monitor (`window_monitor.py`)
```
Responsibilities:
- Detect and attach to Bitcraft.exe window
- Capture screenshots at configurable intervals
- Handle window focus/unfocus events
- Manage capture regions (inventory, crafting, tooltips)
```

#### 2. Image Processor (`image_processor.py`)
```
Responsibilities:
- Preprocess screenshots for OCR optimization
- Apply filters (contrast, brightness, noise reduction)
- Segment UI regions using template matching
- Extract text regions and prepare for OCR
```

#### 3. OCR Engine (`ocr_engine.py`)
```
Responsibilities:
- Configure Tesseract for game UI text
- Process text extraction with confidence scoring
- Handle multiple text formats (tooltips, menus, lists)
- Filter and clean extracted text
```

#### 4. Data Extractor (`data_extractor.py`)
```
Responsibilities:
- Parse extracted text into structured data
- Identify item names, descriptions, and properties
- Extract craft recipes and material lists
- Detect profession and building information
```

#### 5. Data Validator (`data_validator.py`)
```
Responsibilities:
- Compare extracted data against existing BitCrafty dataset
- Validate data integrity and format compliance
- Detect new items, crafts, or changes to existing ones
- Generate confidence scores for extracted data
```

#### 6. Data Merger (`data_merger.py`)
```
Responsibilities:
- Merge validated new data with existing datasets
- Generate BitCrafty-compatible JSON files
- Create incremental update files
- Handle ID generation and profession assignment
```

### Data Extraction Targets

#### Items
```
Target UI Elements:
- Inventory tooltips
- Item detail panels
- Merchant listings
- Storage interfaces

Extracted Properties:
- Name (exact text)
- Tier (numeric or text indicators)
- Rank (Common, Rare, Epic, etc.)
- Profession association
- Description text
```

#### Crafts
```
Target UI Elements:
- Crafting interface recipes
- Workshop recipe lists
- Crafting queue displays
- Recipe tooltips

Extracted Properties:
- Recipe name
- Input materials and quantities
- Output items and quantities
- Required tools/buildings
- Profession requirements
```

#### Buildings & Tools
```
Target UI Elements:
- Building placement UI
- Tool tooltips
- Workshop interfaces
- Construction menus

Extracted Properties:
- Building/tool names
- Tier and profession requirements
- Functionality descriptions
```

### Configuration System

#### Template Definitions (`templates/`)
```
ui_templates.yaml:
- Inventory slot positions
- Tooltip boundaries
- Menu button locations
- Text region definitions

extraction_rules.yaml:
- OCR confidence thresholds
- Text parsing patterns
- Data validation rules
- ID generation rules
```

#### Settings (`config.yaml`)
```yaml
capture:
  interval_ms: 500
  window_name: "Bitcraft"
  regions:
    inventory: [100, 100, 400, 600]
    crafting: [500, 100, 900, 700]
    tooltips: [0, 0, 1920, 1080]

ocr:
  language: "eng"
  confidence_threshold: 80
  preprocessing:
    contrast: 1.2
    brightness: 10
    noise_reduction: true

data:
  output_dir: "../BitCrafty/data"
  backup_existing: true
  validation_threshold: 85
```

### Operation Modes

#### 1. Passive Monitoring Mode
- Continuously monitors game window
- Extracts data as player navigates UI
- Builds confidence over time through repeated observations
- Minimal performance impact

#### 2. Active Discovery Mode
- Triggered when new UI elements detected
- Intensive OCR processing for unknown regions
- Higher CPU usage but faster data extraction
- Used for discovering new content updates

#### 3. Validation Mode
- Compares extracted data against existing dataset
- Generates reports of discrepancies
- Suggests updates to existing data
- Quality assurance for dataset accuracy

### Data Flow

```
1. Window Capture
   ↓
2. Image Preprocessing
   ↓
3. UI Region Detection
   ↓
4. OCR Text Extraction
   ↓
5. Data Structure Parsing
   ↓
6. Validation Against Existing Data
   ↓
7. Confidence Scoring
   ↓
8. Data Merging/Storage
   ↓
9. BitCrafty Format Export
```

### Output Formats

#### Extracted Data Files
```
extracted/
├── items_raw.json          # Raw extracted item data
├── crafts_raw.json         # Raw extracted craft data
├── buildings_raw.json      # Raw extracted building data
├── confidence_scores.json  # Confidence metrics per item
└── extraction_log.json     # Detailed extraction history
```

#### BitCrafty Export Files
```
export/
├── items_update.json       # New/updated items in BitCrafty format
├── crafts_update.json      # New/updated crafts in BitCrafty format
├── metadata_update.json    # New/updated metadata
└── merge_report.md         # Human-readable merge summary
```

### Quality Assurance

#### Confidence Scoring
- OCR confidence (0-100)
- Template matching accuracy (0-100)
- Cross-reference validation (0-100)
- Historical consistency (0-100)
- Combined confidence score (0-100)

#### Manual Review System
- Flag low-confidence extractions for review
- Generate visual diff reports
- Provide manual correction interface
- Learn from corrections to improve future extractions

### Error Handling

#### Recovery Strategies
- Graceful handling of window loss/minimization
- OCR failure recovery with alternative processing
- Data corruption detection and rollback
- Network connectivity issues (if cloud OCR used)

#### Logging System
- Structured logging with configurable levels
- Performance metrics and timing data
- Error tracking with context
- Extraction statistics and success rates

## Installation & Setup

### Prerequisites
```bash
# Python 3.11+
# Tesseract OCR
# Visual C++ Redistributable (Windows)
```

### Installation
```bash
git clone https://github.com/Kyzael/BitCrafty-Extractor.git
cd BitCrafty-Extractor
pip install -r requirements.txt
```

### Configuration
```bash
# Copy default config
cp config/default.yaml config/config.yaml

# Edit configuration for your setup
# Set Bitcraft window name, screen resolution, etc.
```

### Usage
```bash
# Start passive monitoring
python extractor.py --mode passive

# Run discovery mode
python extractor.py --mode discovery --duration 30m

# Validate existing data
python extractor.py --mode validate --input ../BitCrafty/data

# Export to BitCrafty format
python extractor.py --export --output ../BitCrafty/data
```

## Development Roadmap

### Phase 1: Core Infrastructure
- [ ] Window detection and capture system
- [ ] Basic OCR integration
- [ ] Configuration system
- [ ] Logging framework

### Phase 2: Data Extraction
- [ ] Item tooltip extraction
- [ ] Craft recipe parsing
- [ ] UI template system
- [ ] Basic validation

### Phase 3: Integration
- [ ] BitCrafty format export
- [ ] Data merging system
- [ ] Confidence scoring
- [ ] Error handling

### Phase 4: Enhancement
- [ ] Machine learning for improved accuracy
- [ ] Advanced template matching
- [ ] Performance optimization
- [ ] User interface for manual review

## Contributing

See `.github/instructions/extractor_coding_standards.md` for coding guidelines and development practices.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
