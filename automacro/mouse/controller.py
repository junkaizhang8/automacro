from pynput.mouse import Controller

from automacro.core import get_screen_size
from automacro.mouse.mouse_button import MouseButton


def _clamp_to_screen_bounds(x: int, y: int) -> tuple[int, int]:
    """
    Clamp the given (x, y) coordinates to be within the screen bounds.

    Args:
        x (int): The x-coordinate.
        y (int): The y-coordinate.

    Returns:
        tuple[int, int]: The clamped (x, y) coordinates.
    """

    screen_width, screen_height = get_screen_size()
    clamped_x = max(0, min(x, screen_width - 1))
    clamped_y = max(0, min(y, screen_height - 1))
    return clamped_x, clamped_y


class MouseController:
    """
    A controller for mouse actions.
    """

    def __init__(self):
        """
        Initialize the mouse controller.
        """

        self._controller = None

    def get_position(self) -> tuple[int, int]:
        """
        Get the current position of the mouse.

        Returns:
            tuple[int, int]: The (x, y) coordinates of the mouse.
        """

        if not self._controller:
            self._controller = Controller()
        x, y = self._controller.position
        return int(x), int(y)

    def move_to(self, x: int, y: int):
        """
        Move the mouse to the specified (x, y) coordinates.

        If the coordinates are outside the screen bounds, they will be
        clamped to the nearest valid position.

        Args:
            x (int): x-coordinate to move to.
            y (int): y-coordinate to move to.
        """

        if not self._controller:
            self._controller = Controller()

        # Clamp coordinates to screen bounds
        pos = _clamp_to_screen_bounds(x, y)
        self._controller.position = pos

    def move_by(self, dx: int, dy: int):
        """
        Move the mouse by the specified offsets in the x and y directions.

        If the resulting position is outside the screen bounds, it will be
        clamped to the nearest valid position.

        Args:
            dx (int): Offset in the x direction.
            dy (int): Offset in the y direction.
        """

        if not self._controller:
            self._controller = Controller()

        current_x, current_y = self._controller.position

        # Clamp coordinates to screen bounds
        pos = _clamp_to_screen_bounds(current_x + dx, current_y + dy)
        self._controller.position = pos

    def press(self, button: MouseButton):
        """
        Hold down the specified mouse button.

        Args:
            button (MouseButton): Mouse button to hold down.
        """

        if not self._controller:
            self._controller = Controller()
        self._controller.press(button.to_pynput())

    def release(self, button: MouseButton):
        """
        Release the specified mouse button.

        Args:
            button (MouseButton): Mouse button to release.
        """

        if not self._controller:
            self._controller = Controller()
        self._controller.release(button.to_pynput())

    def click(self, button: MouseButton, count: int = 1):
        """
        Click the specified mouse button a given number of times.

        Args:
            button (MouseButton): Mouse button to click.
            count (int): Number of times to click the button. Default is 1.
        """

        if not self._controller:
            self._controller = Controller()
        self._controller.click(button.to_pynput(), count)

    def scroll(self, dx: int, dy: int):
        """
        Scroll the mouse by the specified amounts in the x and y directions.
        """

        if not self._controller:
            self._controller = Controller()
        self._controller.scroll(dx, dy)
