from pynput.keyboard import Controller

from automacro.keyboard.key_sequence import KeySequence


class KeyController:
    """
    A controller for character key presses.
    """

    def __init__(self):
        """
        Initialize the key controller.
        """

        self._controller = None

    def press(self, seq: KeySequence):
        """
        Press a key with modifiers.

        Args:
            seq (KeySequence): Key sequence to press.
        """

        if not self._controller:
            self._controller = Controller()

        key, modifiers = seq.to_pynput()

        for modifier in modifiers:
            self._controller.press(modifier)
        if key:
            self._controller.press(key)

    def release(self, seq: KeySequence):
        """
        Release a key with modifiers.

        Args:
            seq (KeySequence): Key sequence to release.
        """

        if not self._controller:
            self._controller = Controller()

        key, modifiers = seq.to_pynput()

        if key:
            self._controller.release(key)
        # The modifiers are released in reversed order
        for modifier in reversed(list(modifiers)):
            self._controller.release(modifier)

    def tap(self, seq: KeySequence):
        """
        Tap a key with modifiers.

        Args:
            seq (KeySequence): Key sequence to tap.
        """

        if not self._controller:
            self._controller = Controller()

        self.press(seq)
        self.release(seq)

    def type(self, text: str):
        """
        Type a string of characters.

        Args:
            text (str): String representing the characters to type.
        """

        if not self._controller:
            self._controller = Controller()
        self._controller.type(text)
