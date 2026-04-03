"""
OCR Service using PaddleOCR for multi-language text extraction.
Supports English, Hindi, Tamil, Telugu, and other Indian languages.
"""
import numpy as np
from PIL import Image
from typing import Tuple, Optional, List, Dict, Any
from pathlib import Path
import io
import logging

_cv2_module = None
_cv2_import_error = None

# Suppress PaddleOCR's verbose logging
logging.getLogger('ppocr').setLevel(logging.WARNING)

# Initialize PaddleOCR lazily to avoid import issues
_ocr_engine = None


def _require_cv2():
    """Return OpenCV module or raise a user-friendly runtime error."""
    global _cv2_module, _cv2_import_error
    if _cv2_module is not None:
        return _cv2_module

    if _cv2_import_error is not None:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "OpenCV is unavailable. Install compatible versions of NumPy/OpenCV "
            f"for your Python runtime. Original error: {_cv2_import_error}"
        ) from _cv2_import_error

    try:
        import cv2 as cv2_mod  # type: ignore
    except Exception as exc:  # pragma: no cover - environment dependent
        _cv2_import_error = exc
        raise RuntimeError(
            "OpenCV is unavailable. Install compatible versions of NumPy/OpenCV "
            f"for your Python runtime. Original error: {_cv2_import_error}"
        ) from _cv2_import_error

    _cv2_module = cv2_mod
    return _cv2_module


def get_ocr_engine():
    """Lazy initialization of PaddleOCR engine."""
    global _ocr_engine
    _require_cv2()
    if _ocr_engine is None:
        try:
            from paddleocr import PaddleOCR
        except Exception as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "PaddleOCR is unavailable in this environment. Ensure PaddleOCR "
                "and PaddlePaddle are installed with versions compatible with "
                "your current Python version."
            ) from exc
        # Multi-language OCR: supports English + Indian languages
        # lang='en' for English, use 'devanagari' for Hindi, 'tamil', 'telugu' etc.
        # We use 'en' as default and 'multilingual' approach
        _ocr_engine = PaddleOCR(
            lang='en',
            device='gpu:0',
            text_det_box_thresh=0.5,
            text_recognition_batch_size=6,
            enable_mkldnn=False,
            enable_hpi=False,
            enable_cinn=False,
        )
    return _ocr_engine


class ImagePreprocessor:
    """
    Image preprocessing pipeline for OCR optimization.
    Uses OpenCV for image enhancement before text extraction.
    """
    
    def load_image(self, image_data: bytes) -> np.ndarray:
        """Load image from bytes."""
        cv2_mod = _require_cv2()
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2_mod.imdecode(nparr, cv2_mod.IMREAD_COLOR)
        return img
    
    def load_image_from_path(self, image_path: str) -> np.ndarray:
        """Load image from file path."""
        cv2_mod = _require_cv2()
        img = cv2_mod.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image from {image_path}")
        return img
    
    def resize_image(self, img: np.ndarray, max_width: int = 2000) -> np.ndarray:
        """
        Resize image if too large while maintaining aspect ratio.
        Larger images give better OCR but are slower.
        """
        height, width = img.shape[:2]
        
        if width > max_width:
            ratio = max_width / width
            new_height = int(height * ratio)
            cv2_mod = _require_cv2()
            img = cv2_mod.resize(img, (max_width, new_height), interpolation=cv2_mod.INTER_AREA)
        
        return img
    
    def convert_to_grayscale(self, img: np.ndarray) -> np.ndarray:
        """Convert image to grayscale."""
        if len(img.shape) == 3:
            cv2_mod = _require_cv2()
            return cv2_mod.cvtColor(img, cv2_mod.COLOR_BGR2GRAY)
        return img
    
    def apply_denoising(self, img: np.ndarray) -> np.ndarray:
        """Apply noise reduction."""
        cv2_mod = _require_cv2()
        if len(img.shape) == 2:  # Grayscale
            return cv2_mod.fastNlMeansDenoising(img, h=10)
        return cv2_mod.fastNlMeansDenoisingColored(img, h=10)
    
    def enhance_contrast(self, img: np.ndarray) -> np.ndarray:
        """Enhance contrast using CLAHE."""
        cv2_mod = _require_cv2()
        if len(img.shape) == 3:
            # Convert to LAB color space
            lab = cv2_mod.cvtColor(img, cv2_mod.COLOR_BGR2LAB)
            l, a, b = cv2_mod.split(lab)
            clahe = cv2_mod.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            lab = cv2_mod.merge([l, a, b])
            return cv2_mod.cvtColor(lab, cv2_mod.COLOR_LAB2BGR)
        else:
            clahe = cv2_mod.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            return clahe.apply(img)
    
    def sharpen_image(self, img: np.ndarray) -> np.ndarray:
        """Apply sharpening kernel."""
        cv2_mod = _require_cv2()
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]])
        return cv2_mod.filter2D(img, -1, kernel)
    
    def deskew_image(self, img: np.ndarray) -> np.ndarray:
        """
        Deskew image to correct rotation.
        Important for scanned menus.
        """
        cv2_mod = _require_cv2()
        gray = self.convert_to_grayscale(img) if len(img.shape) == 3 else img
        
        # Edge detection
        edges = cv2_mod.Canny(gray, 50, 150, apertureSize=3)
        
        # Detect lines
        lines = cv2_mod.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
        
        if lines is not None:
            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
                if abs(angle) < 45:  # Only consider near-horizontal lines
                    angles.append(angle)
            
            if angles:
                median_angle = np.median(angles)
                if abs(median_angle) > 0.5:  # Only deskew if significant rotation
                    (h, w) = img.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2_mod.getRotationMatrix2D(center, median_angle, 1.0)
                    img = cv2_mod.warpAffine(
                        img, M, (w, h),
                        flags=cv2_mod.INTER_CUBIC,
                        borderMode=cv2_mod.BORDER_REPLICATE
                    )
        
        return img
    
    def preprocess(self, img: np.ndarray, enhance: bool = True) -> np.ndarray:
        """
        Full preprocessing pipeline for PaddleOCR.
        
        Args:
            img: Input image (BGR)
            enhance: Whether to apply enhancement steps
            
        Returns:
            Preprocessed image ready for OCR (still in BGR for PaddleOCR)
        """
        # Resize if needed
        img = self.resize_image(img)
        
        if enhance:
            # Enhance contrast
            img = self.enhance_contrast(img)
            
            # Denoise
            img = self.apply_denoising(img)
            
            # Optional: Sharpen for blurry images
            # img = self.sharpen_image(img)
        
        return img
    
    def preprocess_for_ocr(self, image_data: bytes) -> Tuple[np.ndarray, np.ndarray]:
        """
        Preprocess image bytes for OCR.
        
        Returns:
            Tuple of (original_image, processed_image)
        """
        original = self.load_image(image_data)
        processed = self.preprocess(original)
        return original, processed


class OCREngine:
    """
    OCR engine using PaddleOCR for multi-language text extraction.
    Supports English, Hindi, Tamil, Telugu, and other Indian languages.
    """
    
    def __init__(self):
        """Initialize OCR engine."""
        self.preprocessor = ImagePreprocessor()
        self._ocr = None
    
    @property
    def ocr(self):
        """Lazy load OCR engine."""
        if self._ocr is None:
            self._ocr = get_ocr_engine()
        return self._ocr
    
    def _run_ocr(self, img: np.ndarray):
        """Run OCR with backward/forward compatibility across PaddleOCR versions."""
        try:
            import inspect
            ocr_sig = inspect.signature(self.ocr.ocr)
            if 'cls' in ocr_sig.parameters:
                return self.ocr.ocr(img, cls=True)
        except Exception:
            pass
        return self.ocr.ocr(img)

    def _parse_ocr_result(self, result):
        """Normalize OCR result to a standard format"""
        if not result or not result[0]:
            return []
        
        parsed = []
        if isinstance(result[0], dict):
            res_dict = result[0]
            texts = res_dict.get('rec_texts', [])
            scores = res_dict.get('rec_scores', [])
            polys = res_dict.get('rec_polys', [])
            for i in range(len(texts)):
                bbox = polys[i].tolist() if i < len(polys) and hasattr(polys[i], 'tolist') else []
                parsed.append({
                    'text': str(texts[i]),
                    'confidence': float(scores[i]) if i < len(scores) else 1.0,
                    'bbox': bbox
                })
        else:
            for line in result[0]:
                if isinstance(line, (list, tuple)) and len(line) >= 2:
                    bbox = line[0]
                    text = line[1][0]
                    confidence = line[1][1]
                    parsed.append({
                        'text': str(text),
                        'confidence': float(confidence),
                        'bbox': bbox
                    })
        return parsed

    def extract_text(self, img: np.ndarray) -> str:
        """
        Extract text from image using PaddleOCR.
        
        Args:
            img: Image array (BGR format)
            
        Returns:
            Extracted text as single string
        """
        result = self._run_ocr(img)
        parsed = self._parse_ocr_result(result)
        return "\n".join([item['text'] for item in parsed])
    
    def extract_with_confidence(self, img: np.ndarray) -> Dict[str, Any]:
        """
        Extract text with confidence scores and bounding boxes.
        
        Returns:
            Dictionary with text, confidence data, and bounding boxes
        """
        result = self._run_ocr(img)
        parsed = self._parse_ocr_result(result)
        
        if not parsed:
            return {
                'text': '',
                'average_confidence': 0,
                'word_count': 0,
                'lines': [],
                'raw_data': result
            }
        
        lines = parsed
        confidences = [item['confidence'] for item in parsed]
        full_text_parts = [item['text'] for item in parsed]
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            'text': '\n'.join(full_text_parts),
            'average_confidence': avg_confidence * 100,  # Convert to percentage
            'word_count': sum(len(line['text'].split()) for line in lines),
            'lines': lines,
            'raw_data': result
        }
    
    def extract_structured_data(self, img: np.ndarray) -> List[Dict[str, Any]]:
        """
        Extract structured text data with positions.
        Useful for understanding menu layout.
        
        Returns:
            List of text items with position and confidence
        """
        result = self._run_ocr(img)
        parsed = self._parse_ocr_result(result)
        
        items = []
        for item in parsed:
            bbox = item['bbox']
            if bbox and len(bbox) == 4:
                x_center = sum(p[0] for p in bbox) / 4
                y_center = sum(p[1] for p in bbox) / 4
            else:
                x_center, y_center = 0, 0
                
            items.append({
                'text': item['text'],
                'confidence': item['confidence'],
                'x': x_center,
                'y': y_center,
                'bbox': bbox
            })
        
        # Sort by vertical position (top to bottom)
        items.sort(key=lambda x: x['y'])
        
        return items
    
    def process_menu_image(self, image_data: bytes) -> Dict[str, Any]:
        """
        Full pipeline: preprocess image and extract menu text.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Dictionary with extracted text and metadata
        """
        # Preprocess
        original, processed = self.preprocessor.preprocess_for_ocr(image_data)
        
        # Try both original and processed
        result_processed = self.extract_with_confidence(processed)
        result_original = self.extract_with_confidence(original)
        
        # Use result with higher confidence
        if result_original['average_confidence'] > result_processed['average_confidence']:
            result = result_original
            result['preprocessing_used'] = False
        else:
            result = result_processed
            result['preprocessing_used'] = True
        
        # Also get structured data for better menu parsing
        result['structured_items'] = self.extract_structured_data(
            processed if result['preprocessing_used'] else original
        )
        
        return result


# Singleton instances
image_preprocessor = ImagePreprocessor()
ocr_engine = OCREngine()
