from enum import Enum
import platform
import subprocess


class CoordinateSpace(Enum):
    """
    An enumeration to represent different coordinate spaces.
    """

    LOGICAL = "logical"
    PHYSICAL = "physical"

    def __repr__(self) -> str:
        return f"CoordinateSpace.{self.name}"


_CURRENT_SPACE: CoordinateSpace = CoordinateSpace.LOGICAL
_SCALE: float = 1.0


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


def get_coordinate_space() -> CoordinateSpace:
    """
    Return the current coordinate space.

    Returns:
        CoordinateSpace: The current coordinate space.
    """

    return _CURRENT_SPACE


def set_coordinate_space(space: CoordinateSpace) -> None:
    """
    Set the coordinate space for screen operations.

    Args:
        space (CoordinateSpace): The desired coordinate space.
    """

    global _CURRENT_SPACE

    try:
        _CURRENT_SPACE = space
    except Exception:
        raise ValueError("Invalid coordinate space specified.")


def scale_point(x: int, y: int, to: CoordinateSpace | None = None) -> tuple[int, int]:
    """
    Convert coordinates between logical and physical spaces.

    Args:
        x (int): The x-coordinate.
        y (int): The y-coordinate.
        to (CoordinateSpace | None): The target coordinate space.
        If None, use the current coordinate space.

    Returns:
        tuple[int, int]: The scaled (x, y) coordinates.
    """

    # Quick return if no scaling is needed
    if _SCALE == 1.0:
        return x, y

    target_space = to or _CURRENT_SPACE

    if target_space == CoordinateSpace.PHYSICAL:
        return int(x * _SCALE), int(y * _SCALE)
    elif target_space == CoordinateSpace.LOGICAL:
        return int(x / _SCALE), int(y / _SCALE)
    else:
        raise ValueError("Invalid coordinate space specified.")


def scale_value(value: int, to: CoordinateSpace | None = None) -> int:
    """
    Convert a single value between logical and physical spaces.

    Args:
        value (int): The value to scale.
        to (CoordinateSpace | None): The target coordinate space.
        If None, use the current coordinate space.

    Returns:
        int: The scaled value.
    """

    # Quick return if no scaling is needed
    if _SCALE == 1.0:
        return value

    target_space = to or _CURRENT_SPACE

    if target_space == CoordinateSpace.PHYSICAL:
        return int(value * _SCALE)
    elif target_space == CoordinateSpace.LOGICAL:
        return int(value / _SCALE)
    else:
        raise ValueError("Invalid coordinate space specified.")


def scale_box(
    left: int, top: int, width: int, height: int, to: CoordinateSpace | None = None
) -> tuple[int, int, int, int]:
    """
    Convert a rectangular region between logical and physical spaces.

    Args:
        left (int): The left x-coordinate of the box.
        top (int): The top y-coordinate of the box.
        width (int): The width of the box.
        height (int): The height of the box.
        to (CoordinateSpace | None): The target coordinate space.
        If None, use the current coordinate space.

    Returns:
        tuple[int, int, int, int]: The scaled (left, top, width, height) of the box.
    """

    scaled_left, scaled_top = scale_point(left, top, to)
    scaled_width = scale_value(width, to)
    scaled_height = scale_value(height, to)

    return scaled_left, scaled_top, scaled_width, scaled_height
