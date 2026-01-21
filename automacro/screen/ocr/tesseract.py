from PIL import Image

from automacro.screen.ocr.base import OCRBackend

try:
    import pytesseract
except ImportError as e:
    raise RuntimeError(
        "pytesseract is required for TesseractOCR backend. "
        "Install with: pip install automacro[ocr-tesseract]"
    ) from e


class TesseractOCR(OCRBackend):
    """
    A Tesseract OCR backend implementation.
    """

    def read_text(self, image: Image.Image) -> str:
        return pytesseract.image_to_string(image)
