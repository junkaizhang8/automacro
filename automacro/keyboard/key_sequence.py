from typing import Tuple

from pynput.keyboard import Key as PynputKey

from automacro.keyboard.key import Key, ModifierKey, stringify_modifiers
from automacro.keyboard.char import unshift_char


class KeySequence:
    """
    A sequence of key inputs.
    """

    def __init__(
        self,
        key: str | Key | None = None,
        modifiers: frozenset[ModifierKey] | set[ModifierKey] | None = None,
        *,
        repeat: bool = False,
        ignore_modifiers: bool = False,
    ):
        """
        Initialize the key input.

        Args:
            key (str | Key | None): The character key or Key object. Any
            string key must be a single character, and will be converted to
            its unshifted equivalent. Default is None.
            modifiers (frozenset[ModifierKey] | set[ModifierKey] | None):
            Optional set of modifier keys. Default is None.
            repeat (bool): Whether the key input should be treated as a repeat
            action. Default is False.
            ignore_modifiers (bool): Whether to ignore modifier keys. Mainly
            used for the key listener. If True, as long as the key sequence's
            modifiers are a subset of the currently pressed modifiers, it will
            trigger. If False, the modifiers must match exactly. Default is
            False.
        """

        old_key = key

        if isinstance(key, str):
            if len(key) != 1:
                raise ValueError(
                    f"KeyInput: string key must be a single character, got '{key}'"
                )
            key = unshift_char(key)

        self._key = key

        # If the provided key is a shifted character, ensure that SHIFT is
        # included in modifiers
        if old_key != key:
            modifiers = set(modifiers) if modifiers else set()
            modifiers.add(ModifierKey.SHIFT)

        self._modifiers = frozenset(modifiers or set())
        self._repeat = repeat
        self._ignore_modifiers = ignore_modifiers

    @property
    def key(self) -> str | Key | None:
        return self._key

    @property
    def modifiers(self) -> frozenset[ModifierKey]:
        return self._modifiers

    @property
    def repeat(self) -> bool:
        return self._repeat

    @property
    def ignore_modifiers(self) -> bool:
        return self._ignore_modifiers

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
        return (
            self.key == other.key
            and self.modifiers == other.modifiers
            and self.repeat == other.repeat
            and self.ignore_modifiers == other.ignore_modifiers
        )

    def __hash__(self):
        return hash((self.key, self.modifiers, self.repeat, self.ignore_modifiers))

    def __repr__(self):
        return f"<KeyInput {self.stringify_key()} repeat={self.repeat} ignore_modifiers={self.ignore_modifiers}>"

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
            # Angle brackets for special keys
            if isinstance(self.key, Key):
                return f"<{key_str}>"
            return f"{key_str}"
        if mod_str:
            return f"<{mod_str}>"
        # If no key is specified and no modifiers, return empty string
        return ""
