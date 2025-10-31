import platform
import subprocess


_SCALE = 1.0


def _retrieve_scale_factor() -> float:
    """
    Retrieve the display scale factor based on the operating system.
    """

    system = platform.system()

    # MacOS
    if system == "Darwin":
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True,
                text=True,
            )
            if "retina" in result.stdout.lower():
                return 2.0
        except Exception:
            pass
        return 1.0

    # TODO: Implement checks for Windows/Linux if needed

    # Return 1.0 for default
    return 1.0


_SCALE = _retrieve_scale_factor()


def get_scale_factor() -> float:
    """
    Return the current display scale factor.

    Returns:
        float: The display scale factor.
    """

    return _SCALE


def scale_point(x: int, y: int, inverse: bool = False) -> tuple[int, int]:
    """
    Convert coordinates between logical and physical spaces.

    Args:
        x (int): The x-coordinate.
        y (int): The y-coordinate.
        inverse (bool): If True, scale from physical to logical.
        Otherwise, scale from logical to physical.

    Returns:
        tuple[int, int]: The scaled (x, y) coordinates.
    """

    # Quick return if no scaling is needed
    if _SCALE == 1.0:
        return x, y

    if inverse:
        return int(x / _SCALE), int(y / _SCALE)
    else:
        return int(x * _SCALE), int(y * _SCALE)


def scale_value(value: int, inverse: bool = False) -> int:
    """
    Convert a single value between logical and physical spaces.

    Args:
        value (int): The value to scale.
        inverse (bool): If True, scale from physical to logical.
        Otherwise, scale from logical to physical.

    Returns:
        int: The scaled value.
    """

    # Quick return if no scaling is needed
    if _SCALE == 1.0:
        return value

    if inverse:
        return int(value / _SCALE)
    else:
        return int(value * _SCALE)


def scale_box(
    left: int, top: int, width: int, height: int, inverse: bool = False
) -> tuple[int, int, int, int]:
    """
    Convert a rectangular region between logical and physical spaces.

    Args:
        left (int): The left x-coordinate of the box.
        top (int): The top y-coordinate of the box.
        width (int): The width of the box.
        height (int): The height of the box.
        inverse (bool): If True, scale from physical to logical.
        Otherwise, scale from logical to physical.

    Returns:
        tuple[int, int, int, int]: The scaled (left, top, width, height) of the box.
    """

    scaled_left, scaled_top = scale_point(left, top, inverse=inverse)
    scaled_width, scaled_height = scale_point(width, height, inverse=inverse)

    return scaled_left, scaled_top, scaled_width, scaled_height


def center(left: int, top: int, width: int, height: int) -> tuple[int, int]:
    """
    Calculate the center point of a rectangular box.

    Args:
        left (int): The left x-coordinate of the box.
        top (int): The top y-coordinate of the box.
        width (int): The width of the box.
        height (int): The height of the box.

    Returns:
        tuple[int, int]: The (x, y) coordinates of the center point.
    """

    center_x = left + width // 2
    center_y = top + height // 2

    return center_x, center_y
