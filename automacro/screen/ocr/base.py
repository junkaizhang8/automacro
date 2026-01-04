from abc import ABC, abstractmethod
import re

from PIL import Image


class OCRBackend(ABC):
    """
    An abstract base class defining the interface for OCR backends.
    """

    @abstractmethod
    def read_text(self, image: Image.Image, **kwargs) -> str:
        """
        Extract text from the given image using OCR.

        Args:
            image (PIL.Image.Image): The image to perform OCR on.
            kwargs: Additional keyword arguments for OCR processing.
        """

        ...

    def contains_text(
        self,
        image: Image.Image,
        text: str,
        *,
        exact: bool = False,
        case_sensitive: bool = False,
        **kwargs,
    ) -> bool:
        """
        Check if the specified text is present in the OCR-extracted text from
        the image.

        Args:
            image (PIL.Image.Image): The image to perform OCR on.
            text (str): The text to search for.
            exact (bool): Whether to perform an exact match. If False, checks
            if the text is a substring of the extracted text. Default is False.
            case_sensitive (bool): Whether the text search should be
            case-sensitive. Default is False.
            kwargs: Additional keyword arguments for OCR processing.
        """

        extracted_text = self.read_text(image, **kwargs)

        if not case_sensitive:
            text = text.lower()
            extracted_text = extracted_text.lower()

        if exact:
            return text == extracted_text

        return text in extracted_text

    def matches_text(self, image: Image.Image, pattern: str, **kwargs) -> bool:
        """
        Check if the specified pattern matches any part of the OCR-extracted
        text from the image.

        Args:
            image (PIL.Image.Image): The image to perform OCR on.
            pattern (str): The regex pattern to search for.
            kwargs: Additional keyword arguments for OCR processing.
        """

        extracted_text = self.read_text(image, **kwargs)
        return re.search(pattern, extracted_text) is not None
