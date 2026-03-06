from typing_extensions import override

from automacro.workflow.base import Node
from automacro.workflow.context import ExecutionContext


class Wait(Node):
    """
    A node that waits for a specified duration before completing.

    If the parent workflow is interrupted during the wait, it will raise an
    InterruptException and stop waiting immediately.
    """

    def __init__(
        self,
        duration: float,
        *,
        name: str | None = None,
    ) -> None:
        """
        Initialize the `Wait` node.

        Args:
            duration: The amount of time to wait, in seconds.
            name: Optional name for the node. If not provided, it will default
            to "Wait({duration}s)".
        """

        super().__init__(name=name or f"Wait({duration}s)")
        self._duration = duration

    @override
    def _step(self, ctx: ExecutionContext) -> Node | None:
        ctx.wait(self._duration)
        return None


class Sleep(Node):
    """
    A node that sleeps for a specified duration before completing.

    This is not interruptible, and will not raise `InterruptException` even if
    the parent workflow is interrupted during the sleep. Use `Wait` instead to
    have an interruptible sleep.
    """

    def __init__(
        self,
        duration: float,
        *,
        name: str | None = None,
    ) -> None:
        """
        Initialize the `Sleep` node.

        Args:
            duration: The amount of time to sleep, in seconds.
            name: Optional name for the node. If not provided, it will default
            to "Sleep({duration}s)".
        """

        super().__init__(name=name or f"Sleep({duration}s)")
        self._duration = duration

    @override
    def _step(self, ctx: ExecutionContext) -> Node | None:
        ctx.sleep(self._duration)
        return None
