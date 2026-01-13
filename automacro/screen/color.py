import re

import pyautogui as pag

# PyAutoGUI uses physical coordinates for pixel operations, so we need to
# rescale coordinates accordingly.
from automacro.screen.coordinates import scale_point


def get_pixel_color(x: int, y: int) -> tuple[int, int, int]:
    """
    Get the RGB color of the pixel at the specified (x, y) coordinates on the
    screen.

    Args:
        x (int): The x-coordinate of the pixel.
        y (int): The y-coordinate of the pixel.

    Returns:
        tuple[int, int, int]: The RGB color of the pixel as a tuple (R, G, B),
        where each value ranges from 0 to 255.
    """

    return pag.pixel(*scale_point(x, y))


def is_pixel_color(
    x: int, y: int, expected_color: tuple[int, int, int], tolerance: int = 0
) -> bool:
    """
    Check if the pixel at the specified (x, y) coordinates matches the expected
    RGB color within a given tolerance.

    Args:
        x (int): The x-coordinate of the pixel.
        y (int): The y-coordinate of the pixel.
        expected_color (tuple[int, int, int]): The expected RGB color as a tuple
        (R, G, B).
        tolerance (int): The tolerance for color matching. Default is 0.

    Returns:
        bool: True if the pixel color matches the expected color within the
        tolerance, False otherwise.
    """

    return pag.pixelMatchesColor(*scale_point(x, y), expected_color, tolerance)


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    """
    Convert an RGB color tuple to a hexadecimal color string.

    Args:
        rgb (tuple[int, int, int]): The RGB color as a tuple (R, G, B).
        Each value must be in the range 0-255.

    Returns:
        str: The hexadecimal color string in the format '#RRGGBB'.
    """

    # Invalid RGB values check
    if any(not (0 <= value <= 255) for value in rgb):
        raise ValueError("RGB values must be in the range 0-255.")

    return "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """
    Convert a hexadecimal color string to an RGB color tuple.

    Args:
        hex_color (str): The hexadecimal color string in the format '#RRGGBB'.

    Returns:
        tuple[int, int, int]: The RGB color as a tuple (R, G, B).
    """

    hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")

    if not hex_pattern.match(hex_color):
        raise ValueError(
            "Hex color must be in the format '#RRGGBB' with valid hex digits."
        )

    # Remove the leading '#'
    hex_color = hex_color.lstrip("#")

    red = int(hex_color[0:2], 16)
    green = int(hex_color[2:4], 16)
    blue = int(hex_color[4:6], 16)

    return (red, green, blue)
