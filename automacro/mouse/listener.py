from typing import Callable

from pynput.mouse import Button, Listener

from automacro.mouse.mouse_button import MouseButton


class MouseListener:
    """
    A listener for mouse events.
    """

    def __init__(
        self,
        on_move: Callable[[int, int], None] | None = None,
        on_click: Callable[[int, int, MouseButton, bool], None] | None = None,
        on_scroll: Callable[[int, int, int, int], None] | None = None,
    ):
        """
        Initialize the mouse listener.

        Args:
            on_move (Callable[[int, int], None] | None): Optional callback
            function for mouse move events. The function should accept two
            arguments: x and y. Default is None.
            on_click (Callable[[int, int, MouseButton, bool], None] | None):
            Optional callback function for mouse click events. The function
            should accept four arguments: x, y, button, and pressed. Default
            is None.
            on_scroll (Callable[[int, int, int, int], None] | None):
            Optional callback function for mouse scroll events. The function
            should accept four arguments: x, y, dx, and dy. Default is None.
        """

        self._click_callback = on_click

        self._listener = Listener(
            on_move=on_move,
            on_click=self._on_click,
            on_scroll=on_scroll,
        )

    def _on_click(self, x: int, y: int, button: Button, pressed: bool) -> None:
        """
        Callback function for mouse click event.

        Args:
            x (int): The x-coordinate of the mouse click.
            y (int): The y-coordinate of the mouse click.
            button (pynput.mouse.Button): The mouse button that was clicked.
            pressed (bool): True if the button was pressed, False if released.
        """

        if self._click_callback:
            mouse_button = MouseButton.from_pynput(button)
            if mouse_button:
                self._click_callback(x, y, mouse_button, pressed)

    def start(self) -> None:
        """
        Start the mouse listener thread.
        """

        if self._listener:
            self._listener.start()

    def stop(self) -> None:
        """
        Stop the mouse listener.
        """

        if self._listener:
            self._listener.stop()

    def join(self) -> None:
        """
        Wait for the mouse listener thread to complete.
        """

        if self._listener:
            self._listener.join()
