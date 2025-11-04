from enum import Enum

from pynput.mouse import Button


class MouseButton(Enum):
    """
    An enumeration representing mouse buttons.
    """

    LEFT = Button.left
    RIGHT = Button.right
    MIDDLE = Button.middle

    @classmethod
    def from_pynput(cls, button: Button) -> "MouseButton | None":
        """
        Convert a pynput Button to its corresponding MouseButton enum member.

        Args:
            button (pynput.mouse.Button): The pynput Button to convert.

        Returns:
            MouseButton | None: The corresponding MouseButton enum member, or
            None if not found.
        """

        if button == Button.left:
            return cls.LEFT
        if button == Button.right:
            return cls.RIGHT
        if button == Button.middle:
            return cls.MIDDLE
        return None

    def to_pynput(self) -> Button:
        """
        Convert a MouseButton enum member to its corresponding pynput Button.

        Returns:
            pynput.mouse.Button: The corresponding pynput Button.
        """

        return self.value
