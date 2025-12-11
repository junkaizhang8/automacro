from typing import Callable

from pynput.mouse import Button, Listener

from automacro.utils import _get_logger
from automacro.core import ThreadPool
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
        thread_pool: ThreadPool | None = None,
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
            thread_pool (ThreadPool | None): Optional shared thread pool for
            executing callbacks. If None, callbacks will be executed in a
            dedicated thread. Default is None.
        """

        self._move_callback = on_move
        self._click_callback = on_click
        self._scroll_callback = on_scroll

        self._listener = Listener(
            on_move=on_move,
            on_click=self._on_click,
            on_scroll=on_scroll,
        )

        self._owns_thread_pool = thread_pool is None
        self._thread_pool = thread_pool or ThreadPool(1)

        self._logger = _get_logger(self.__class__)

    def __del__(self):
        try:
            if self._owns_thread_pool and self._thread_pool:
                # We don't wait for tasks to complete to avoid blocking
                self._thread_pool.shutdown(wait=False)
        except Exception as e:
            self._logger.error(f"Error shutting down thread pool: {e}")

    def _on_move(self, x: int, y: int):
        """
        Callback function for mouse move event.

        Args:
            x (int): The x-coordinate of the mouse move.
            y (int): The y-coordinate of the mouse move.
        """

        if self._move_callback:
            self._thread_pool.submit(self._move_callback, x, y)

    def _on_click(self, x: int, y: int, button: Button, pressed: bool):
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
                self._thread_pool.submit(
                    self._click_callback, x, y, mouse_button, pressed
                )

    def _on_scroll(self, x: int, y: int, dx: int, dy: int):
        """
        Callback function for mouse scroll event.

        Args:
            x (int): The x-coordinate of the mouse scroll.
            y (int): The y-coordinate of the mouse scroll.
            dx (int): The horizontal scroll delta.
            dy (int): The vertical scroll delta.
        """

        if self._scroll_callback:
            self._thread_pool.submit(self._scroll_callback, x, y, dx, dy)

    def start(self):
        """
        Start the mouse listener thread.
        """

        if self._listener:
            self._listener.start()

    def stop(self):
        """
        Stop the mouse listener.
        """

        if self._listener:
            self._listener.stop()

        if self._owns_thread_pool and self._thread_pool:
            try:
                # We don't wait for tasks to complete to avoid blocking
                self._thread_pool.shutdown(wait=False)
            except Exception as e:
                self._logger.error(f"Error shutting down thread pool: {e}")

    def join(self):
        """
        Wait for the mouse listener thread to complete.
        """

        if self._listener:
            self._listener.join()
