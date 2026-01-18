import re

import mss

from automacro.screen.types import RGB


def get_pixel(x: int, y: int) -> RGB:
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

    with mss.mss() as sct:
        monitor = {"left": x, "top": y, "width": 1, "height": 1}

        img = sct.grab(monitor)

        r, g, b = tuple(img.rgb[:3])

        return r, g, b


def is_pixel(x: int, y: int, expected: RGB, tolerance: int = 0) -> bool:
    """
    Check if the pixel at the specified (x, y) coordinates matches the expected
    RGB color within a given tolerance.

    Args:
        x (int): The x-coordinate of the pixel.
        y (int): The y-coordinate of the pixel.
        expected (tuple[int, int, int]): The expected RGB color as a tuple
        (R, G, B).
        tolerance (int): The tolerance for color matching. Default is 0.

    Returns:
        bool: True if the pixel color matches the expected color within the
        tolerance, False otherwise.
    """

    pixel = get_pixel(x, y)
    return all(abs(pixel[i] - expected[i]) <= tolerance for i in range(3))


def rgb_to_hex(rgb: RGB) -> str:
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

    return "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2]).upper()


def hex_to_rgb(hex_color: str) -> RGB:
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
