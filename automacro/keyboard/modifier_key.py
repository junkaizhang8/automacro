from enum import Enum

from pynput.keyboard import Key


class ModifierKey(Enum):
    """
    An enumeration of modifier keys.
    """

    CTRL = 0
    ALT = 1
    CMD = 2
    SHIFT = 3


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


def get_modifier_key(key: Key) -> ModifierKey | None:
    """
    Get the ModifierKey enum corresponding to the given pynput Key.

    Args:
        key (PynputKey): The pynput Key to check.

    Returns:
        ModifierKey | None: The corresponding ModifierKey enum, or None if not
        a modifier key.
    """

    ctrl_keys = [Key.ctrl, Key.ctrl_l, Key.ctrl_r]
    alt_keys = [Key.alt, Key.alt_l, Key.alt_r]
    cmd_keys = [Key.cmd, Key.cmd_l, Key.cmd_r]
    shift_keys = [Key.shift, Key.shift_l, Key.shift_r]

    if key in ctrl_keys:
        return ModifierKey.CTRL
    if key in alt_keys:
        return ModifierKey.ALT
    if key in cmd_keys:
        return ModifierKey.CMD
    if key in shift_keys:
        return ModifierKey.SHIFT

    return None
