from bidict import bidict

_SHIFT_MAP = bidict(
    {
        "~": "`",
        "!": "1",
        "@": "2",
        "#": "3",
        "$": "4",
        "%": "5",
        "^": "6",
        "&": "7",
        "*": "8",
        "(": "9",
        ")": "0",
        "_": "-",
        "+": "=",
        "{": "[",
        "}": "]",
        "|": "\\",
        ":": ";",
        '"': "'",
        "<": ",",
        ">": ".",
        "?": "/",
    }
)


def unshift_char(char: str) -> str:
    """
    Convert a shifted character to their non-shifted equivalent. If the
    character is an unshifted character, it is returned unchanged.

    Args:
        char (str): The character to unshift.

    Returns:
        str: The unshifted character.
    """

    if len(char) != 1:
        raise ValueError(
            f"unshift_char: input must be a single character, got '{char}'"
        )

    return _SHIFT_MAP.get(char, char.lower())


def shift_char(char: str) -> str:
    """
    Convert a non-shifted character to their shifted equivalent. If the
    character is a shifted character, it is returned unchanged.

    Args:
        char (str): The character to shift.

    Returns:
        str: The shifted character.
    """

    if len(char) != 1:
        raise ValueError(f"shift_char: input must be a single character, got '{char}'")

    return _SHIFT_MAP.inv.get(char, char.upper())
