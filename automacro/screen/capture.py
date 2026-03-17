import mss
from PIL import Image

from automacro.screen.types import BBox

# Create a single mss instance to be reused for all captures.
# This is more efficient than creating a new instance for each capture.
_sct = mss.mss()


def capture(region: BBox | None = None) -> Image.Image:
    """
    Capture a screenshot of the screen or a specific region.

    Args:
        region (tuple[int, int, int, int] | None): A region (left, top, width,
        height) to capture. If None, captures the entire screen.

    Returns:
        PIL.Image.Image: The captured screenshot image.
    """

    monitor = (
        _sct.monitors[1]
        if region is None
        else {
            "left": region[0],
            "top": region[1],
            "width": region[2],
            "height": region[3],
        }
    )

    sct_img = _sct.grab(monitor)

    # Convert to PIL Image
    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

    return img
