from automacro.screen.capture import capture
from automacro.screen.ocr.base import OCRBackend
from automacro.screen.ocr.factory import create_backend

_backend: OCRBackend | None = None


def set_backend(backend: OCRBackend):
    """
    Set the OCR backend to be used for text extraction from the screen.

    The library contains some built-in backends, and you can also
    make your own by implementing the OCRBackend protocol. Do note
    that the built-in backends do not come pre-installed, so you may
    need to install additional dependencies to use them.

    Available backends:
    - "tesseract": Uses Tesseract OCR engine.

    Args:
        backend (OCRBackend): An instance of the OCR backend to set.
    """

    global _backend
    _backend = backend


def use(name: str, **kwargs):
    """
    Set the OCR backend by name using the factory function.

    The library contains some built-in backends, and you can also
    make your own by implementing the OCRBackend protocol. Do note
    that the built-in backends do not come pre-installed, so you may
    need to install additional dependencies to use them.

    Available backends:
    - "tesseract": Uses Tesseract OCR engine.

    Args:
        name (str): The name of the OCR backend to use.
        **kwargs: Additional keyword arguments to pass to the backend
        constructor.
    """

    backend = create_backend(name, **kwargs)
    set_backend(backend)


def read_text(region: tuple[int, int, int, int] | None = None) -> str:
    """
    Capture a screenshot of the specified region and extract text using OCR.

    Args:
        region (tuple[int, int, int, int] | None): A region (left, top, width,
        height) to capture. If None, captures the entire screen. Default
        is None.

    Returns:
        str: The extracted text from the captured image.
    """

    if _backend is None:
        raise RuntimeError(
            "OCR backend is not set. Please set it using set_backend() or use()"
        )

    image = capture(region=region)
    return _backend.read_text(image)


def contains_text(
    text: str,
    *,
    region: tuple[int, int, int, int] | None = None,
    exact: bool = False,
    case_sensitive: bool = False,
) -> bool:
    """
    Check if the specified text is present in the OCR-extracted text.

    Args:
        text (str): The text to search for.
        region (tuple[int, int, int, int]): A region (left, top, width,
        height) to capture. If None, captures the entire screen. Default
        is None.
        exact (bool): Whether to perform an exact match. If False, checks
        if the text is a substring of the extracted text. Default is False.
        case_sensitive (bool): Whether the text search should be
        case-sensitive. Default is False.

    Returns:
        bool: True if the text is found, False otherwise.
    """

    if _backend is None:
        raise RuntimeError(
            "OCR backend is not set. Please set it using set_backend() or use()"
        )

    image = capture(region=region)
    return _backend.contains_text(
        image, text, exact=exact, case_sensitive=case_sensitive
    )


def matches_text(
    pattern: str,
    *,
    region: tuple[int, int, int, int] | None = None,
) -> bool:
    """
    Check if the specified pattern matches any part of the OCR-extracted text.

    Args:
        pattern (str): The regex pattern to search for.
        region (tuple[int, int, int, int]): A region (left, top, width,
        height) to capture. If None, captures the entire screen. Default
        is None.
        case_sensitive (bool): Whether the pattern search should be
        case-sensitive. Default is False.

    Returns:
        bool: True if the pattern matches, False otherwise.
    """

    if _backend is None:
        raise RuntimeError(
            "OCR backend is not set. Please set it using set_backend() or use()"
        )

    image = capture(region=region)
    return _backend.matches_text(image, pattern)
