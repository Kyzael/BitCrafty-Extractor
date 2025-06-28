#!/usr/bin/env python3
"""Manual validation tool for BitCrafty-Extractor screenshots."""
import argparse
import datetime
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

import cv2
import numpy as np
import structlog

from bitcrafty_extractor.core.config_manager import ConfigManager
from bitcrafty_extractor.core.window_monitor import WindowMonitor
from bitcrafty_extractor.core.ocr_engine import OCREngine
from bitcrafty_extractor.utils.logging_utils import setup_logging


def create_validation_directories() -> Dict[str, Path]:
    """Create directories for validation data."""
    base_dir = Path("validation")
    directories = {
        "screenshots": base_dir / "screenshots",
        "processed": base_dir / "processed", 
        "ocr_results": base_dir / "ocr_results",
        "annotations": base_dir / "annotations"
    }
    
    for dir_path in directories.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return directories


def capture_validation_screenshot(
    window_monitor: WindowMonitor,
    ocr_engine: OCREngine,
    logger: structlog.BoundLogger
) -> Optional[Dict[str, Any]]:
    """Capture a screenshot and extract text for manual validation."""
    
    # Capture screenshot
    screenshot = window_monitor.capture_window()
    if screenshot is None:
        logger.error("Failed to capture screenshot")
        return None
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create validation directories
    dirs = create_validation_directories()
    
    # Save original screenshot
    screenshot_path = dirs["screenshots"] / f"screenshot_{timestamp}.png"
    cv2.imwrite(str(screenshot_path), screenshot)
    logger.info("Screenshot saved", path=str(screenshot_path), shape=screenshot.shape)
    
    # Extract OCR text
    ocr_results = ocr_engine.extract_text(screenshot)
    
    # Convert OCR results to serializable format
    ocr_data_for_json = []
    for result in ocr_results:
        if hasattr(result, '__dict__'):
            # Convert OCRResult object to dictionary
            ocr_data_for_json.append(result.__dict__)
        else:
            # Already a dictionary
            ocr_data_for_json.append(result)
    
    # Save OCR results
    ocr_results_path = dirs["ocr_results"] / f"ocr_results_{timestamp}.json"
    ocr_data = {
        "timestamp": timestamp,
        "screenshot_path": str(screenshot_path),
        "text_blocks": ocr_data_for_json,
        "total_blocks": len(ocr_data_for_json),
        "screenshot_shape": [int(x) for x in screenshot.shape],  # Convert to list for JSON
        "window_info": window_monitor.get_window_info()
    }
    
    with open(ocr_results_path, 'w', encoding='utf-8') as f:
        json.dump(ocr_data, f, indent=2, ensure_ascii=False)
    
    logger.info("OCR results saved", path=str(ocr_results_path), text_blocks=len(ocr_data_for_json))
    
    # Create annotated image with OCR regions (if OCR available)
    if ocr_data_for_json:
        annotated_image = screenshot.copy()
        
        for i, result in enumerate(ocr_data_for_json):
            if 'bbox' in result and result['bbox']:
                # Draw bounding box
                x, y, w, h = result['bbox']
                cv2.rectangle(annotated_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # Add text label
                label = f"{i}: {result.get('confidence', 0):.1f}%"
                cv2.putText(annotated_image, label, (x, y - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Save annotated image
        annotated_path = dirs["processed"] / f"annotated_{timestamp}.png"
        cv2.imwrite(str(annotated_path), annotated_image)
        logger.info("Annotated image saved", path=str(annotated_path))
        ocr_data["annotated_image_path"] = str(annotated_path)
    
    # Create manual annotation template
    annotation_template = {
        "timestamp": timestamp,
        "screenshot_path": str(screenshot_path),
        "validation_status": "pending",  # pending, approved, rejected
        "manual_corrections": [],
        "notes": "",
        "reviewer": "",
        "review_date": "",
        "confidence_assessment": {
            "ocr_accuracy": "",  # poor, fair, good, excellent
            "ui_clarity": "",     # poor, fair, good, excellent
            "text_legibility": "", # poor, fair, good, excellent
            "overall_quality": ""  # poor, fair, good, excellent
        },
        "extracted_data": {
            "items": [],
            "crafts": [],
            "ui_elements": [],
            "other": []
        },
        "issues_found": []
    }
    
    annotation_path = dirs["annotations"] / f"annotation_{timestamp}.json"
    with open(annotation_path, 'w', encoding='utf-8') as f:
        json.dump(annotation_template, f, indent=2, ensure_ascii=False)
    
    logger.info("Annotation template created", path=str(annotation_path))
    
    # Print summary for user
    print(f"\n{'='*60}")
    print(f"VALIDATION CAPTURE COMPLETE")
    print(f"{'='*60}")
    print(f"Timestamp: {timestamp}")
    print(f"Screenshot: {screenshot_path}")
    print(f"OCR Results: {ocr_results_path}")
    print(f"Annotation Template: {annotation_path}")
    if ocr_results:
        print(f"Annotated Image: {annotated_path}")
    print(f"Text blocks found: {len(ocr_data_for_json)}")
    
    if window_monitor.get_window_info():
        window_title, window_rect = window_monitor.get_window_info()
        print(f"Window: {window_title}")
        print(f"Window size: {window_rect[2] - window_rect[0]}x{window_rect[3] - window_rect[1]}")
    
    print(f"\nTo manually validate:")
    print(f"1. Open the screenshot: {screenshot_path}")
    print(f"2. Review OCR results: {ocr_results_path}")
    print(f"3. Fill out annotation template: {annotation_path}")
    print(f"{'='*60}\n")
    
    return ocr_data


def list_validation_files() -> None:
    """List all available validation files."""
    validation_dir = Path("validation")
    
    if not validation_dir.exists():
        print("No validation directory found. Capture a screenshot first.")
        return
    
    screenshots = list((validation_dir / "screenshots").glob("*.png")) if (validation_dir / "screenshots").exists() else []
    annotations = list((validation_dir / "annotations").glob("*.json")) if (validation_dir / "annotations").exists() else []
    
    print(f"\n{'='*60}")
    print(f"VALIDATION FILES")
    print(f"{'='*60}")
    print(f"Screenshots: {len(screenshots)}")
    print(f"Annotations: {len(annotations)}")
    
    if screenshots:
        print(f"\nRecent screenshots:")
        for screenshot in sorted(screenshots, reverse=True)[:5]:
            print(f"  - {screenshot.name}")
    
    if annotations:
        print(f"\nAnnotations:")
        for annotation in sorted(annotations, reverse=True)[:5]:
            try:
                with open(annotation, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                status = data.get('validation_status', 'unknown')
                reviewer = data.get('reviewer', 'unassigned')
                print(f"  - {annotation.name} [{status}] ({reviewer})")
            except Exception:
                print(f"  - {annotation.name} [error reading file]")
    
    print(f"{'='*60}\n")


def main():
    """Main entry point for validation tool."""
    parser = argparse.ArgumentParser(description="Manual validation tool for BitCrafty-Extractor")
    parser.add_argument("--capture", action="store_true", help="Capture a new screenshot for validation")
    parser.add_argument("--list", action="store_true", help="List existing validation files")
    parser.add_argument("--config", default="config/default.yaml", help="Configuration file path")
    
    args = parser.parse_args()
    
    if args.list:
        list_validation_files()
        return
    
    if not args.capture:
        parser.print_help()
        return
    
    # Setup logging
    setup_logging(level="INFO", log_file=None)
    logger = structlog.get_logger()
    
    try:
        # Load configuration
        config_path = Path(args.config)
        config_manager = ConfigManager(config_path)
        config = config_manager.config
        
        logger.info("Starting manual validation capture", config_file=args.config)
        
        # Initialize components
        window_monitor = WindowMonitor(config.window, logger)
        ocr_engine = OCREngine(config.ocr, logger)
        
        # Find window
        if not window_monitor.find_window():
            logger.error("Could not find BitCraft window")
            print("Error: Could not find BitCraft window. Make sure the game is running and visible.")
            return
        
        # Capture and process
        result = capture_validation_screenshot(window_monitor, ocr_engine, logger)
        
        if result:
            logger.info("Validation capture completed successfully")
        else:
            logger.error("Validation capture failed")
            
    except Exception as e:
        logger.error("Validation capture failed", error=str(e))
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
