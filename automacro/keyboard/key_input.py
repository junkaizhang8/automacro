from automacro.keyboard.modifier_key import ModifierKey, stringify_modifiers


class KeyInput:
    """
    A simple structure to hold key input information.
    """

    def __init__(
        self, key: str, modifiers: set[ModifierKey] | None = None, repeat: bool = False
    ):
        """
        Initialize the key input.

        Args:
            key (str): The character key.
            modifiers (set[ModifierKey] | None): Optional set of modifier
            keys. Default is None.
            repeat (bool): Whether the key input should be treated as a repeat
            action. Default is False.
        """

        if not isinstance(key, str) or len(key) != 1:
            raise ValueError("Key must be a single character string.")

        self.key = key.lower()
        self.modifiers = frozenset(modifiers) if modifiers else frozenset()
        self.repeat = repeat

    def __eq__(self, other):
        if not isinstance(other, KeyInput):
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

        if mod_str:
            return f"<{mod_str}-{self.key}>"
        return self.key
