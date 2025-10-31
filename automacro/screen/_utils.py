from automacro.core import (
    CoordinateSpace,
    get_coordinate_space,
    scale_point,
    scale_value,
    scale_box,
)


def _to_physical_point(x: int, y: int) -> tuple[int, int]:
    """
    Convert a point to physical coordinate space, if the current space is not
    physical.

    Args:
        x (int): The x-coordinate of the point.
        y (int): The y-coordinate of the point.

    Returns:
        tuple[int, int]: The (x, y) coordinates in physical space.
    """

    if get_coordinate_space() != CoordinateSpace.PHYSICAL:
        return scale_point(x, y, to=CoordinateSpace.PHYSICAL)
    return (x, y)


def _to_physical_value(value: int) -> int:
    """
    Convert a single value to physical coordinate space, if the current space is
    not physical.

    Args:
        value (int): The value to convert.

    Returns:
        int: The value in physical space.
    """

    if get_coordinate_space() != CoordinateSpace.PHYSICAL:
        return scale_value(value, to=CoordinateSpace.PHYSICAL)
    return value


def _to_physical_box(
    left: int, top: int, width: int, height: int
) -> tuple[int, int, int, int]:
    """
    Convert a rectangular region to physical coordinate space, if the current
    space is not physical.

    Args:
        left (int): The left x-coordinate of the box.
        top (int): The top y-coordinate of the box.
        width (int): The width of the box.
        height (int): The height of the box.

    Returns:
        tuple[int, int, int, int]: The (left, top, width, height) in physical
        space.
    """

    if get_coordinate_space() != CoordinateSpace.PHYSICAL:
        return scale_box(left, top, width, height, to=CoordinateSpace.PHYSICAL)
    return (left, top, width, height)
