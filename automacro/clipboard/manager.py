import pyperclip


def copy(text: str):
    """
    Copy text to the clipboard.

    Args:
        text (str): The text to copy to the clipboard.
    """

    pyperclip.copy(text)


def paste() -> str:
    """
    Paste text from the clipboard.

    Returns:
        str: The text from the clipboard.
    """

    return pyperclip.paste()
