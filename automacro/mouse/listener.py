from typing import Callable

from pynput.mouse import Listener

from automacro.core import scale_point


class MouseListener:
    """
    A listener for mouse events.
    """

    def __init__(
        self,
        on_move: Callable | None = None,
        on_click: Callable | None = None,
        on_scroll: Callable | None = None,
    ):
        """
        Initialize the mouse listener.

        Args:
            on_move (Callable | None): Optional callback function for mouse
            move events. Default is None.
            on_click (Callable | None): Optional callback function for mouse
            click events. Default is None.
            on_scroll (Callable | None): Optional callback function for mouse
            scroll events. Default is None.
        """

        self._move_callback = on_move
        self._click_callback = on_click
        self._scroll_callback = on_scroll

        self._listener = Listener(
            on_move=self._on_move, on_click=self._on_click, on_scroll=self._on_scroll
        )

    def _on_move(self, x: int, y: int) -> None:
        """
        Callback function for mouse move event.
        """

        if self._move_callback:
            self._move_callback(*scale_point(x, y))

    def _on_click(self, x: int, y: int, button, pressed: bool) -> None:
        """
        Callback function for mouse click event.
        """

        if self._click_callback:
            self._click_callback(*scale_point(x, y), button, pressed)

    def _on_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        """
        Callback function for mouse scroll event.
        """

        if self._scroll_callback:
            self._scroll_callback(*scale_point(x, y), dx, dy)

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
