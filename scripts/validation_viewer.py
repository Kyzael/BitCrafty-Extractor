#!/usr/bin/env python3
"""Validation viewer for examining screenshots and OCR results."""
import argparse
import json
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import cv2
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.widgets import Button
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


def load_validation_data(timestamp: str) -> Optional[Dict[str, Any]]:
    """Load validation data for a specific timestamp."""
    validation_dir = Path("validation")
    
    # Load OCR results
    ocr_results_path = validation_dir / "ocr_results" / f"ocr_results_{timestamp}.json"
    if not ocr_results_path.exists():
        print(f"OCR results not found: {ocr_results_path}")
        return None
    
    with open(ocr_results_path, 'r', encoding='utf-8') as f:
        ocr_data = json.load(f)
    
    # Load annotation if it exists
    annotation_path = validation_dir / "annotations" / f"annotation_{timestamp}.json"
    annotation_data = None
    if annotation_path.exists():
        with open(annotation_path, 'r', encoding='utf-8') as f:
            annotation_data = json.load(f)
    
    return {
        "ocr_data": ocr_data,
        "annotation_data": annotation_data,
        "timestamp": timestamp
    }


def display_validation_results(validation_data: Dict[str, Any]) -> None:
    """Display validation results in a visual format."""
    if not CV2_AVAILABLE:
        print("OpenCV and matplotlib not available. Showing text summary only.")
        print_text_summary(validation_data)
        return
    
    ocr_data = validation_data["ocr_data"]
    screenshot_path = Path(ocr_data["screenshot_path"])
    
    if not screenshot_path.exists():
        print(f"Screenshot not found: {screenshot_path}")
        return
    
    # Load screenshot
    image = cv2.imread(str(screenshot_path))
    if image is None:
        print(f"Could not load image: {screenshot_path}")
        return
    
    # Convert BGR to RGB for matplotlib
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Create figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Display original image
    ax1.imshow(image_rgb)
    ax1.set_title(f"Original Screenshot\n{validation_data['timestamp']}")
    ax1.axis('off')
    
    # Display image with OCR annotations
    ax2.imshow(image_rgb)
    ax2.set_title(f"OCR Results ({len(ocr_data['text_blocks'])} blocks)")
    ax2.axis('off')
    
    # Add OCR bounding boxes
    for i, result in enumerate(ocr_data["text_blocks"]):
        if 'bbox' in result and result['bbox']:
            x, y, w, h = result['bbox']
            
            # Create rectangle
            rect = patches.Rectangle((x, y), w, h, linewidth=2, 
                                   edgecolor='lime', facecolor='none')
            ax2.add_patch(rect)
            
            # Add text label
            confidence = result.get('confidence', 0)
            text = result.get('text', '')[:20]  # Truncate long text
            label = f"{i}: {confidence:.1f}%\n{text}..."
            ax2.text(x, y - 5, label, fontsize=8, color='lime', 
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='black', alpha=0.7))
    
    plt.tight_layout()
    plt.show()
    
    # Print detailed OCR results
    print_text_summary(validation_data)


def print_text_summary(validation_data: Dict[str, Any]) -> None:
    """Print a text summary of the validation data."""
    ocr_data = validation_data["ocr_data"]
    annotation_data = validation_data.get("annotation_data")
    
    print(f"\n{'='*80}")
    print(f"VALIDATION SUMMARY - {validation_data['timestamp']}")
    print(f"{'='*80}")
    
    # Screenshot info
    print(f"Screenshot: {ocr_data['screenshot_path']}")
    print(f"Image size: {ocr_data['screenshot_shape'][1]}x{ocr_data['screenshot_shape'][0]}")
    
    # Window info
    if ocr_data.get('window_info'):
        window_title, window_rect = ocr_data['window_info']
        print(f"Window: {window_title}")
        print(f"Window rect: {window_rect}")
    
    # OCR Results
    print(f"\nOCR RESULTS ({len(ocr_data['text_blocks'])} text blocks):")
    print(f"{'-'*80}")
    
    for i, result in enumerate(ocr_data["text_blocks"]):
        text = result.get('text', '').strip()
        confidence = result.get('confidence', 0)
        bbox = result.get('bbox', [])
        
        print(f"Block {i:2d}: [{confidence:5.1f}%] {text}")
        if bbox:
            print(f"         Position: ({bbox[0]}, {bbox[1]}) Size: {bbox[2]}x{bbox[3]}")
        print()
    
    # Annotation info
    if annotation_data:
        print(f"\nANNOTATION STATUS:")
        print(f"{'-'*80}")
        print(f"Status: {annotation_data.get('validation_status', 'Unknown')}")
        print(f"Reviewer: {annotation_data.get('reviewer', 'Unassigned')}")
        print(f"Review Date: {annotation_data.get('review_date', 'Not reviewed')}")
        
        if annotation_data.get('notes'):
            print(f"Notes: {annotation_data['notes']}")
        
        confidence = annotation_data.get('confidence_assessment', {})
        if any(confidence.values()):
            print(f"\nConfidence Assessment:")
            for key, value in confidence.items():
                if value:
                    print(f"  {key.replace('_', ' ').title()}: {value}")
    else:
        print(f"\nNo annotation file found. Create one at:")
        print(f"validation/annotations/annotation_{validation_data['timestamp']}.json")
    
    print(f"{'='*80}\n")


def list_available_validations() -> None:
    """List all available validation timestamps."""
    validation_dir = Path("validation")
    
    if not validation_dir.exists():
        print("No validation directory found.")
        return
    
    ocr_dir = validation_dir / "ocr_results"
    if not ocr_dir.exists():
        print("No OCR results found.")
        return
    
    ocr_files = list(ocr_dir.glob("ocr_results_*.json"))
    
    if not ocr_files:
        print("No validation data found.")
        return
    
    print(f"\nAvailable validation data:")
    print(f"{'='*50}")
    
    for ocr_file in sorted(ocr_files, reverse=True):
        # Extract timestamp from filename
        timestamp = ocr_file.stem.replace("ocr_results_", "")
        
        # Check if annotation exists
        annotation_file = validation_dir / "annotations" / f"annotation_{timestamp}.json"
        annotation_status = "❌ No annotation"
        
        if annotation_file.exists():
            try:
                with open(annotation_file, 'r', encoding='utf-8') as f:
                    annotation = json.load(f)
                status = annotation.get('validation_status', 'pending')
                reviewer = annotation.get('reviewer', 'unassigned')
                annotation_status = f"✅ {status} ({reviewer})"
            except Exception:
                annotation_status = "⚠️ Error reading annotation"
        
        print(f"{timestamp} - {annotation_status}")
    
    print(f"{'='*50}\n")


def main():
    """Main entry point for validation viewer."""
    parser = argparse.ArgumentParser(description="View validation results for BitCrafty-Extractor")
    parser.add_argument("timestamp", nargs="?", help="Timestamp of validation to view (YYYYMMDD_HHMMSS)")
    parser.add_argument("--list", action="store_true", help="List available validations")
    parser.add_argument("--latest", action="store_true", help="View the latest validation")
    
    args = parser.parse_args()
    
    if args.list:
        list_available_validations()
        return
    
    if args.latest:
        # Find the latest validation
        validation_dir = Path("validation/ocr_results")
        if not validation_dir.exists():
            print("No validation data found.")
            return
        
        ocr_files = list(validation_dir.glob("ocr_results_*.json"))
        if not ocr_files:
            print("No validation data found.")
            return
        
        latest_file = max(ocr_files, key=lambda x: x.stat().st_mtime)
        timestamp = latest_file.stem.replace("ocr_results_", "")
        print(f"Viewing latest validation: {timestamp}")
    elif args.timestamp:
        timestamp = args.timestamp
    else:
        list_available_validations()
        return
    
    # Load and display validation data
    validation_data = load_validation_data(timestamp)
    if validation_data:
        display_validation_results(validation_data)
    else:
        print(f"Could not load validation data for timestamp: {timestamp}")


if __name__ == "__main__":
    main()
