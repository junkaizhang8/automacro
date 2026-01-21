from automacro.screen.ocr.base import OCRBackend


def create_backend(name: str, **kwargs) -> OCRBackend:
    """
    Factory function to create an OCR backend instance based on the given name.

    Do note that the backends do not come pre-installed, so you may need to
    install additional dependencies to use them.

    Available backends:
    - "tesseract": Uses Tesseract OCR engine.

    Args:
        name (str): The name of the OCR backend to create. It is
        case-insensitive.
        **kwargs: Additional keyword arguments to pass to the backend
        constructor.

    Returns:
        OCRBackend: An instance of the specified OCR backend.

    Raises:
        ValueError: If the specified backend name is not recognized.
    """

    name = name.lower()

    if name == "tesseract":
        from automacro.screen.ocr.tesseract import TesseractOCR

        return TesseractOCR(**kwargs)

    raise ValueError(f"Unknown OCR backend: {name}")
