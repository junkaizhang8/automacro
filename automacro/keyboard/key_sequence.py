from typing import Tuple

from pynput.keyboard import Key as PynputKey

from automacro.keyboard.key import Key, ModifierKey, stringify_modifiers


class KeySequence:
    """
    A sequence of key inputs.
    """

    def __init__(
        self,
        key: str | Key | None = None,
        modifiers: set[ModifierKey] | None = None,
        repeat: bool = False,
    ):
        """
        Initialize the key input.

        Args:
            key (str | Key | None): The character key or Key object. Default
            is None.
            modifiers (set[ModifierKey] | None): Optional set of modifier
            keys. Default is None.
            repeat (bool): Whether the key input should be treated as a repeat
            action. Default is False.
        """

        if isinstance(key, str):
            if len(key) != 1:
                raise ValueError(
                    f"KeyInput: string key must be a single character, got '{key}'"
                )
            key = key.lower()

        self.key = key
        self.modifiers = frozenset(modifiers or set())
        self.repeat = repeat

    def to_pynput(self) -> Tuple[str | PynputKey | None, set[PynputKey]]:
        """
        Returns the key and modifiers in pynput format.

        Returns:
            Tuple[str | PynputKey | None, set[PynputKey]]: A tuple containing
            the key and a set of modifier keys in pynput format.
        """

        modifiers = {mod.to_pynput() for mod in self.modifiers}

        if isinstance(self.key, Key):
            return self.key.to_pynput(), modifiers
        return self.key, modifiers

    def __eq__(self, other):
        if not isinstance(other, KeySequence):
            return NotImplemented
        return self.key == other.key and self.modifiers == other.modifiers

    def __hash__(self):
        return hash((self.key, self.modifiers))

    def __repr__(self):
        return f"<KeyInput {self.stringify_key()} repeat={self.repeat}>"

    def stringify_key(self) -> str:
        """
        Stringify the key and any modifiers into its string representation.

        Returns:
            str: Stringified representation of the KeyInput.
        """

        mod_str = stringify_modifiers(self.modifiers)
        if isinstance(self.key, Key):
            key_str = "".join(
                word.capitalize() for word in self.key.name.lower().split("_")
            )
        else:
            key_str = self.key or ""

        if mod_str and key_str:
            return f"<{mod_str}-{key_str}>"
        if key_str:
            return f"<{key_str}>"
        # If no key is specified, or only modifiers, return empty string
        return ""
