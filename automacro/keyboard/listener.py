from typing import Callable

from pynput.keyboard import Listener

from automacro._utils import _get_logger
from automacro.keyboard.key_input import KeyInput
from automacro.keyboard.modifier_key import get_modifier_key


class KeyListener:
    """
    A listener for character key presses.
    """

    def __init__(
        self,
        callbacks: dict[KeyInput, Callable] | None = None,
    ):
        """
        Initialize the key listener.

        Args:
            callbacks (dict[KeyInput, Callable] | None): Optional dictionary
            mapping keys to callback functions. Default is None.
        """

        self._callbacks = callbacks.copy() if callbacks else {}
        self._repeat_actions = (
            {key_input: key_input.repeat for key_input in callbacks.keys()}
            if callbacks
            else {}
        )
        self._listener = Listener(on_press=self._on_press, on_release=self._on_release)
        self._modifiers = set()
        self._pressed_keys = set()
        self._logger = _get_logger(self.__class__)

    def _on_press(self, key):
        """
        Callback function for key press event.
        """

        if not self._callbacks:
            return

        modifier = get_modifier_key(key)
        if modifier:
            self._modifiers.add(modifier)

        if hasattr(key, "char") and key.char:
            k = KeyInput(key.char.lower(), self._modifiers)
            if k in self._callbacks:
                if k not in self._pressed_keys:
                    self._callbacks[k]()
                    self._pressed_keys.add(k)
                    return
                if k in self._repeat_actions and self._repeat_actions[k]:
                    self._callbacks[k]()

    def _on_release(self, key):
        """
        Callback function for key release event.
        """

        if not self._callbacks:
            return

        modifier = get_modifier_key(key)
        if modifier:
            for k in list(self._pressed_keys):
                if modifier in k.modifiers:
                    self._pressed_keys.discard(k)
            self._modifiers.discard(modifier)

        if hasattr(key, "char") and key.char:
            for k in list(self._pressed_keys):
                if k.key == key.char:
                    self._pressed_keys.discard(k)

    def start(self) -> None:
        """
        Start the key listener thread.
        """

        if self._listener:
            self._listener.start()

    def stop(self) -> None:
        """
        Stop the key listener.
        """

        if self._listener:
            self._listener.stop()

    def join(self) -> None:
        """
        Wait for the key listener thread to complete.
        """

        if self._listener:
            self._listener.join()
