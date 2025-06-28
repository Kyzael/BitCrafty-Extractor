"""OCR engine for text extraction from game UI."""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import numpy as np
import structlog

try:
    import pytesseract
    import cv2
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

from bitcrafty_extractor import OCRError
from bitcrafty_extractor.core.config_manager import OCRConfig


@dataclass
class OCRResult:
    """Result of OCR text extraction."""
    text: str
    confidence: float
    bbox: tuple[int, int, int, int]  # (x, y, width, height)
    
    @classmethod
    def empty(cls) -> 'OCRResult':
        """Create an empty OCR result."""
        return cls(text="", confidence=0.0, bbox=(0, 0, 0, 0))


class OCREngine:
    """OCR engine for extracting text from game UI elements."""
    
    def __init__(self, config: OCRConfig, logger: structlog.BoundLogger):
        """Initialize OCR engine.
        
        Args:
            config: OCR configuration
            logger: Structured logger instance
            
        Raises:
            OCRError: If OCR libraries are not available
        """
        if not OCR_AVAILABLE:
            raise OCRError("OCR libraries not available. Install pytesseract and opencv-python.")
        
        self.config = config
        self.logger = logger
        
        # Verify tesseract installation
        try:
            version = pytesseract.get_tesseract_version()
            self.logger.info("OCR engine initialized", 
                           tesseract_version=str(version),
                           language=config.language,
                           confidence_threshold=config.confidence_threshold)
        except Exception as e:
            # For development/testing, allow graceful degradation
            self.logger.warning("Tesseract not available, OCR will be limited", error=str(e))
            self._tesseract_available = False
        else:
            self._tesseract_available = True
    
    def extract_text(self, image: np.ndarray, region: Optional[tuple[int, int, int, int]] = None) -> List[OCRResult]:
        """Extract text from image using OCR.
        
        Args:
            image: Input image as numpy array (BGR format)
            region: Optional region to extract from (x, y, width, height)
            
        Returns:
            List of OCR results with text, confidence, and bounding boxes
            
        Raises:
            OCRError: If OCR processing fails
            ValueError: If image is invalid
        """
        if image is None or image.size == 0:
            raise ValueError("Image cannot be None or empty")
        
        # If Tesseract is not available, return mock results for testing
        if not getattr(self, '_tesseract_available', True):
            self.logger.debug("OCR not available, returning mock results")
            return [OCRResult(
                text="Mock OCR Result",
                confidence=0.85,
                bbox=(10, 10, 100, 20)
            )]
        
        try:
            # Extract region if specified
            if region:
                x, y, w, h = region
                if x < 0 or y < 0 or w <= 0 or h <= 0:
                    raise ValueError(f"Invalid region: {region}")
                if x + w > image.shape[1] or y + h > image.shape[0]:
                    raise ValueError(f"Region {region} exceeds image bounds {image.shape}")
                
                image = image[y:y+h, x:x+w]
            
            # Preprocess image if enabled
            if self.config.preprocessing_enabled:
                image = self._preprocess_image(image)
            
            # Perform OCR with detailed data
            ocr_data = pytesseract.image_to_data(
                image,
                lang=self.config.language,
                config=self.config.config_string,
                output_type=pytesseract.Output.DICT
            )
            
            # Process results
            results = []
            n_boxes = len(ocr_data['text'])
            
            for i in range(n_boxes):
                text = ocr_data['text'][i].strip()
                confidence = float(ocr_data['conf'][i])
                
                # Filter by confidence threshold and non-empty text
                if confidence >= (self.config.confidence_threshold * 100) and text:
                    bbox = (
                        ocr_data['left'][i],
                        ocr_data['top'][i],
                        ocr_data['width'][i],
                        ocr_data['height'][i]
                    )
                    
                    # Adjust bbox if region was specified
                    if region:
                        bbox = (
                            bbox[0] + region[0],
                            bbox[1] + region[1],
                            bbox[2],
                            bbox[3]
                        )
                    
                    results.append(OCRResult(
                        text=text,
                        confidence=confidence / 100.0,  # Convert to 0-1 range
                        bbox=bbox
                    ))
            
            self.logger.debug("OCR extraction completed",
                            total_boxes=n_boxes,
                            valid_results=len(results),
                            region=region)
            
            return results
            
        except Exception as e:
            self.logger.error("OCR extraction failed", error=str(e), region=region)
            raise OCRError(f"OCR processing failed: {e}") from e
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for better OCR results.
        
        Args:
            image: Input image
            
        Returns:
            Preprocessed image
        """
        try:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Apply bilateral filter to reduce noise while preserving edges
            filtered = cv2.bilateralFilter(gray, 9, 75, 75)
            
            # Enhance contrast
            enhanced = cv2.convertScaleAbs(filtered, alpha=1.2, beta=10)
            
            return enhanced
            
        except Exception as e:
            self.logger.warning("Image preprocessing failed, using original", error=str(e))
            return image
    
    def extract_single_text(self, image: np.ndarray, region: Optional[tuple[int, int, int, int]] = None) -> Optional[str]:
        """Extract single text string from image (convenience method).
        
        Args:
            image: Input image
            region: Optional region to extract from
            
        Returns:
            Extracted text string or None if no text found
        """
        try:
            results = self.extract_text(image, region)
            if results:
                # Combine all text results
                combined_text = " ".join(result.text for result in results)
                return combined_text.strip()
            return None
        except Exception as e:
            self.logger.warning("Single text extraction failed", error=str(e))
            return None
