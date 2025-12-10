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
    CTRL_L = 1
    CTRL_R = 2
    ALT = 3
    ALT_L = 4
    ALT_R = 5
    CMD = 6
    CMD_L = 7
    CMD_R = 8
    SHIFT = 9
    SHIFT_L = 10
    SHIFT_R = 11

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

        map = {
            PynputKey.ctrl: ModifierKey.CTRL,
            PynputKey.ctrl_l: ModifierKey.CTRL_L,
            PynputKey.ctrl_r: ModifierKey.CTRL_R,
            PynputKey.alt: ModifierKey.ALT,
            PynputKey.alt_l: ModifierKey.ALT_L,
            PynputKey.alt_r: ModifierKey.ALT_R,
            PynputKey.cmd: ModifierKey.CMD,
            PynputKey.cmd_l: ModifierKey.CMD_L,
            PynputKey.cmd_r: ModifierKey.CMD_R,
            PynputKey.shift: ModifierKey.SHIFT,
            PynputKey.shift_l: ModifierKey.SHIFT_L,
            PynputKey.shift_r: ModifierKey.SHIFT_R,
        }

        return map.get(key, None)

    def to_pynput(self) -> PynputKey:
        """
        Convert a ModifierKey to its corresponding pynput Key.

        Returns:
            pynput.keyboard.Key: The corresponding pynput Key.
        """

        mod_to_pynput = {
            ModifierKey.CTRL: PynputKey.ctrl,
            ModifierKey.CTRL_L: PynputKey.ctrl_l,
            ModifierKey.CTRL_R: PynputKey.ctrl_r,
            ModifierKey.ALT: PynputKey.alt,
            ModifierKey.ALT_L: PynputKey.alt_l,
            ModifierKey.ALT_R: PynputKey.alt_r,
            ModifierKey.CMD: PynputKey.cmd,
            ModifierKey.CMD_L: PynputKey.cmd_l,
            ModifierKey.CMD_R: PynputKey.cmd_r,
            ModifierKey.SHIFT: PynputKey.shift,
            ModifierKey.SHIFT_L: PynputKey.shift_l,
            ModifierKey.SHIFT_R: PynputKey.shift_r,
        }

        return mod_to_pynput[self]

    def is_general(self) -> bool:
        """
        Check if the ModifierKey is in its general form (not left/right).

        Returns:
            bool: True if the ModifierKey is general, False otherwise.
        """

        return self.value % 3 == 0

    def is_left(self) -> bool:
        """
        Check if the ModifierKey is a left side variant.

        Returns:
            bool: True if the ModifierKey is left side, False otherwise.
        """

        return self.name.endswith("_L")

    def is_right(self) -> bool:
        """
        Check if the ModifierKey is a right side variant.

        Returns:
            bool: True if the ModifierKey is right side, False otherwise.
        """

        return self.name.endswith("_R")

    def general(self) -> "ModifierKey":
        """
        Convert a specific ModifierKey (left/right) to its general form.
        If the ModifierKey is already general, it is returned as is.

        Returns:
            ModifierKey: The general form of the modifier key.
        """

        general_value = self.value - (self.value % 3)
        return ModifierKey(general_value)

    def left(self) -> "ModifierKey":
        """
        Get the left side variant of the modifier key.
        If the ModifierKey is already left or in general form, it is returned
        as is.

        Returns:
            ModifierKey: The left side variant of the modifier key.
        """

        if self.is_right():
            return ModifierKey[self.name.replace("_R", "_L")]
        if self.is_general():
            return ModifierKey[self.name + "_L"]
        return self

    def right(self) -> "ModifierKey":
        """
        Get the right side variant of the modifier key.
        If the ModifierKey is already right or in general form, it is returned
        as is.

        Returns:
            ModifierKey: The right side variant of the modifier key.
        """

        if self.is_left():
            return ModifierKey[self.name.replace("_L", "_R")]
        if self.is_general():
            return ModifierKey[self.name + "_R"]
        return self

    def opposite(self) -> "ModifierKey | None":
        """
        Get the opposite side variant of the modifier key.
        For example, if the key is CTRL_L, it returns CTRL_R.
        If the ModifierKey is in general form, it returns None.

        Returns:
            ModifierKey | None: The opposite side variant of the modifier key,
            or None if the key is in general form.
        """

        if self.is_left():
            return self.right()
        if self.is_right():
            return self.left()
        return None


def stringify_modifiers(modifiers: frozenset[ModifierKey]) -> str:
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
        modifiers (frozenset[ModifierKey]): Set of modifier keys.

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

    # Track which general modifiers are already in use, in case of
    # left/right variants. General modifiers take precedence
    # over left/right variants.
    mod_in_use = {
        ModifierKey.CTRL: False,
        ModifierKey.ALT: False,
        ModifierKey.CMD: False,
        ModifierKey.SHIFT: False,
    }

    for modifier in mods:
        general = modifier.general()

        if mod_in_use[general]:
            continue

        if general in mods:
            mod_in_use[general] = True

        if modifier.is_general():
            variant_suffix = ""
        elif modifier.is_left():
            variant_suffix = "l"
        else:
            variant_suffix = "r"

        mod_str += mod_to_str.get(general, "") + variant_suffix + "-"

    if mod_str.endswith("-"):
        mod_str = mod_str[:-1]

    return mod_str
