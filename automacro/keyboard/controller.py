from pynput.keyboard import Controller


class KeyController:
    """
    A controller for character key presses.
    """

    def __init__(self):
        """
        Initialize the key controller.
        """

        self._controller = None

    def press(self, key: str) -> None:
        """
        Press a character key.

        Args:
            key (str): String representing the character key to press.
        """

        if not self._controller:
            self._controller = Controller()
        self._controller.press(key)

    def release(self, key: str) -> None:
        """
        Release a character key.

        Args:
            key (str): String representing the character key to release.
        """

        if not self._controller:
            self._controller = Controller()
        self._controller.release(key)

    def tap(self, key: str) -> None:
        """
        Tap a character key.

        Args:
            key (str): String representing the character key to tap.
        """

        if not self._controller:
            self._controller = Controller()
        self._controller.tap(key)

    def type(self, text: str) -> None:
        """
        Type a string of characters.

        Args:
            text (str): String representing the characters to type.
        """

        if not self._controller:
            self._controller = Controller()
        self._controller.type(text)
