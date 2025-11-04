from enum import Enum

from pynput.keyboard import Key as PynputKey


class Key(Enum):
    """
    An enumeration of special keyboard keys.
    """

    BACKSPACE = PynputKey.backspace

    CAPS_LOCK = PynputKey.caps_lock

    DELETE = PynputKey.delete

    DOWN = PynputKey.down

    END = PynputKey.end

    ENTER = PynputKey.enter

    ESC = PynputKey.esc

    F1 = PynputKey.f1
    F2 = PynputKey.f2
    F3 = PynputKey.f3
    F4 = PynputKey.f4
    F5 = PynputKey.f5
    F6 = PynputKey.f6
    F7 = PynputKey.f7
    F8 = PynputKey.f8
    F9 = PynputKey.f9
    F10 = PynputKey.f10
    F11 = PynputKey.f11
    F12 = PynputKey.f12
    F13 = PynputKey.f13
    F14 = PynputKey.f14
    F15 = PynputKey.f15
    F16 = PynputKey.f16
    F17 = PynputKey.f17
    F18 = PynputKey.f18
    F19 = PynputKey.f19
    F20 = PynputKey.f20

    HOME = PynputKey.home

    LEFT = PynputKey.left

    PAGE_DOWN = PynputKey.page_down

    PAGE_UP = PynputKey.page_up

    RIGHT = PynputKey.right

    SPACE = PynputKey.space

    TAB = PynputKey.tab

    UP = PynputKey.up

    @classmethod
    def from_pynput(cls, key: PynputKey) -> "Key | None":
        """
        Convert a pynput Key to its corresponding Key enum member.

        Args:
            key (pynput.keyboard.Key): The pynput Key to convert.

        Returns:
            Key | None: The corresponding Key enum member, or None if not found.
        """

        for member in cls:
            if member.value == key:
                return member

        return None

    def to_pynput(self) -> PynputKey:
        """
        Convert a Key enum member to its corresponding pynput Key.

        Returns:
            pynput.keyboard.Key: The corresponding pynput Key.
        """

        return self.value


class ModifierKey(Enum):
    """
    An enumeration of modifier keys.
    """

    CTRL = 0
    ALT = 1
    CMD = 2
    SHIFT = 3

    @classmethod
    def from_pynput(cls, key: PynputKey) -> "ModifierKey | None":
        """
        Convert a pynput Key to its corresponding ModifierKey.

        Args:
            key (pynput.keyboard.Key): The pynput Key to convert.

        Returns:
            ModifierKey | None: The corresponding ModifierKey, or None if not
            a modifier key.
        """

        ctrl_keys = [PynputKey.ctrl, PynputKey.ctrl_l, PynputKey.ctrl_r]
        alt_keys = [PynputKey.alt, PynputKey.alt_l, PynputKey.alt_r]
        cmd_keys = [PynputKey.cmd, PynputKey.cmd_l, PynputKey.cmd_r]
        shift_keys = [PynputKey.shift, PynputKey.shift_l, PynputKey.shift_r]

        if key in ctrl_keys:
            return ModifierKey.CTRL
        if key in alt_keys:
            return ModifierKey.ALT
        if key in cmd_keys:
            return ModifierKey.CMD
        if key in shift_keys:
            return ModifierKey.SHIFT

        return None

    def to_pynput(self) -> PynputKey:
        """
        Convert a ModifierKey to its corresponding pynput Key.

        Returns:
            pynput.keyboard.Key: The corresponding pynput Key.
        """

        mod_to_pynput = {
            ModifierKey.CTRL: PynputKey.ctrl,
            ModifierKey.ALT: PynputKey.alt,
            ModifierKey.CMD: PynputKey.cmd,
            ModifierKey.SHIFT: PynputKey.shift,
        }

        return mod_to_pynput[self]


def stringify_modifiers(modifiers: set[ModifierKey] | frozenset[ModifierKey]) -> str:
    """
    Stringify a set of modifier keys into a string representation.

    Each modifier is represented by a unique uppercase letter, and
    are connected by hyphens. The modifiers are stringified (in the order
    listed) as follows:
    - CTRL -> C
    - ALT -> M
    - CMD -> D
    - SHIFT -> S

    Args:
        modifiers (set[ModifierKey] | frozenset[ModifierKey]): Set of
        modifier keys.

    Returns:
        str: Stringified representation of the modifier keys. If no modifiers,
        an empty string is returned.
    """

    mod_str = ""

    # We sort the modifiers to ensure they are ordered
    mods = sorted(modifiers, key=lambda m: m.value)

    mod_to_str = {
        ModifierKey.CTRL: "C",
        ModifierKey.ALT: "M",
        ModifierKey.CMD: "D",
        ModifierKey.SHIFT: "S",
    }

    for modifier in mods:
        mod_str += mod_to_str.get(modifier, "") + "-"

    if mod_str.endswith("-"):
        mod_str = mod_str[:-1]

    return mod_str
