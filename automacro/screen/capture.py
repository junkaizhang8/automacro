from PIL import Image
import pyautogui as pag


def capture(region: tuple[int, int, int, int] | None = None) -> Image.Image:
    """
    Capture a screenshot of the screen or a specific region.

    Args:
        region (tuple[int, int, int, int] | None): A region (left, top, width,
        height) to capture. If None, captures the entire screen.

    Returns:
        PIL.Image.Image: The captured screenshot image.
    """

    # pyautogui uses logical coordinates for screenshots; no scaling needed
    return pag.screenshot(region=region)
