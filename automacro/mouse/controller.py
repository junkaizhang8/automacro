from enum import Enum

from pynput.mouse import Button, Controller

from automacro.core import CoordinateSpace, get_coordinate_space, scale_point


class MouseButton(Enum):
    """
    An enumeration representing mouse buttons.
    """

    LEFT = Button.left
    RIGHT = Button.right
    MIDDLE = Button.middle

    def __eq__(self, other):
        if isinstance(other, Button):
            return self.value == other
        return super().__eq__(other)


def _to_logical_point(x: int, y: int) -> tuple[int, int]:
    """
    Convert a point from the current coordinate space to logical space.

    Args:
        x (int): x-coordinate.
        y (int): y-coordinate.

    Returns:
        tuple[int, int]: The (x, y) coordinates in logical space.
    """

    if get_coordinate_space() != CoordinateSpace.LOGICAL:
        return scale_point(x, y, to=CoordinateSpace.LOGICAL)
    return (x, y)


class MouseController:
    """
    A controller for mouse actions.
    """

    def __init__(self):
        """
        Initialize the mouse controller.
        """

        self._controller = None

    def move(self, x: int, y: int) -> None:
        """
        Move the mouse to the specified (x, y) coordinates.

        Args:
            x (int): x-coordinate to move to.
            y (int): y-coordinate to move to.
        """

        if not self._controller:
            self._controller = Controller()
        self._controller.position = _to_logical_point(x, y)

    def click(self, button: MouseButton, count: int = 1) -> None:
        """
        Click the specified mouse button a given number of times.

        Args:
            button (MouseButton): Mouse button to click.
            count (int): Number of times to click the button. Default is 1.
        """

        if not self._controller:
            self._controller = Controller()
        self._controller.click(button.value, count)

    def scroll(self, dx: int, dy: int) -> None:
        """
        Scroll the mouse by the specified amounts in the x and y directions.
        """

        if not self._controller:
            self._controller = Controller()
        self._controller.scroll(*_to_logical_point(dx, dy))
