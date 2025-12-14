def normalize_char(char: str) -> str:
    """
    Normalize a character by converting shifted characters to their
    non-shifted equivalents. If the character is not a shifted character,
    it is returned unchanged.

    Args:
        char (str): The character to normalize.

    Returns:
        str: The normalized character.
    """

    if len(char) != 1:
        raise ValueError(
            f"normalize_char: input must be a single character, got '{char}'"
        )

    shift_map = {
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

    char = char.lower()
    return shift_map.get(char, char)
