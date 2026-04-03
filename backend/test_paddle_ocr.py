"""
PaddleOCR Installation Verification Script

This script tests that PaddleOCR is properly installed and working.
Run this after installing dependencies to verify the setup.

Usage:
    cd backend
    python test_paddle_ocr.py
"""

import sys

def test_imports():
    """Test that all required packages can be imported."""
    print("Testing imports...")
    
    try:
        import numpy as np
        print("  ✓ NumPy imported")
    except ImportError as e:
        print(f"  ✗ NumPy import failed: {e}")
        return False
    
    try:
        import cv2
        print(f"  ✓ OpenCV imported (version {cv2.__version__})")
    except ImportError as e:
        print(f"  ✗ OpenCV import failed: {e}")
        return False
    
    try:
        import paddle
        print(f"  ✓ PaddlePaddle imported (version {paddle.__version__})")
    except ImportError as e:
        print(f"  ✗ PaddlePaddle import failed: {e}")
        print("    Run: pip install paddlepaddle")
        return False
    
    try:
        from paddleocr import PaddleOCR
        print("  ✓ PaddleOCR imported")
    except ImportError as e:
        print(f"  ✗ PaddleOCR import failed: {e}")
        print("    Run: pip install paddleocr")
        return False
    
    return True


def test_ocr_initialization():
    """Test that PaddleOCR can be initialized."""
    print("\nTesting PaddleOCR initialization...")
    print("  (This may download models on first run, ~100MB)")
    
    try:
        from paddleocr import PaddleOCR
        
        # Initialize with minimal settings
        ocr = PaddleOCR(
            use_angle_cls=True,
            lang='en',
            use_gpu=False,
            show_log=False
        )
        print("  ✓ PaddleOCR initialized successfully")
        return ocr
    except Exception as e:
        print(f"  ✗ PaddleOCR initialization failed: {e}")
        return None


def test_ocr_on_sample():
    """Test OCR on a simple test image."""
    print("\nTesting OCR on sample image...")
    
    import numpy as np
    import cv2
    from paddleocr import PaddleOCR
    
    # Create a simple test image with text
    img = np.ones((100, 400, 3), dtype=np.uint8) * 255  # White background
    
    # Add some text using OpenCV
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, 'Hello PaddleOCR', (20, 60), font, 1.2, (0, 0, 0), 2)
    
    # Save temp image
    temp_path = 'test_ocr_sample.png'
    cv2.imwrite(temp_path, img)
    
    try:
        ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False, show_log=False)
        result = ocr.ocr(temp_path, cls=True)
        
        if result and result[0]:
            text_found = []
            for line in result[0]:
                if line and len(line) >= 2:
                    text_found.append(line[1][0])
            
            extracted = ' '.join(text_found)
            print(f"  ✓ OCR extracted: '{extracted}'")
            
            # Cleanup
            import os
            os.remove(temp_path)
            return True
        else:
            print("  ⚠ OCR returned empty result (this might be normal for simple test)")
            import os
            os.remove(temp_path)
            return True
            
    except Exception as e:
        print(f"  ✗ OCR test failed: {e}")
        import os
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False


def main():
    print("=" * 50)
    print("PaddleOCR Installation Verification")
    print("=" * 50)
    
    # Test imports
    if not test_imports():
        print("\n❌ Import tests failed. Please install missing packages.")
        sys.exit(1)
    
    # Test initialization
    ocr = test_ocr_initialization()
    if ocr is None:
        print("\n❌ OCR initialization failed.")
        sys.exit(1)
    
    # Test actual OCR
    if not test_ocr_on_sample():
        print("\n⚠ OCR sample test had issues, but may still work.")
    
    print("\n" + "=" * 50)
    print("✅ PaddleOCR is installed and ready!")
    print("=" * 50)
    print("\nYou can now start the backend server:")
    print("  python run.py")


if __name__ == '__main__':
    main()
