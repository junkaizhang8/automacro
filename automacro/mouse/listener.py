from typing import Callable

from pynput.mouse import Listener


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
        self._listener = Listener(
            on_move=on_move, on_click=on_click, on_scroll=on_scroll
        )

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
