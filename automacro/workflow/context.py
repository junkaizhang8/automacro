import threading
import time

from automacro.workflow.exceptions import InterruptException


class ExecutionContext:
    """
    A context object that is passed to each node during the execution of a
    workflow. It provides methods for checking if the workflow has been
    interrupted, and for waiting or sleeping during the execution of a node.
    """

    def __init__(self) -> None:
        """
        Initialize the execution context.
        """

        self._interrupt_event = threading.Event()

    def _pause(self) -> None:
        """
        Internal method to pause the workflow execution.
        """

        self._interrupt_event.set()

    def _resume(self) -> None:
        """
        Internal method to resume the workflow execution.
        """

        self._interrupt_event.clear()

    def check_interrupt(self) -> None:
        """
        Check if the workflow has been interrupted, and raise an
        `InterruptException` if it has. This will stop the execution of the
        current node and propagate the interrupt up the workflow chain,
        allowing the workflow to handle the interrupt.

        Raises:
            InterruptException: If the workflow has been interrupted.
        """

        if self._interrupt_event.is_set():
            raise InterruptException()

    def wait(self, duration: float) -> None:
        """
        Wait for the specified duration, or until the workflow is interrupted.

        Args:
            duration: The amount of time to wait, in seconds.

        Raises:
            InterruptException: If the workflow is interrupted during the wait.
        """

        interrupted = self._interrupt_event.wait(duration)
        if interrupted:
            raise InterruptException()

    def sleep(self, duration: float) -> None:
        """
        Sleep for the specified duration.

        This is not interruptible, and will not raise `InterruptException` even
        if the workflow is interrupted during the sleep. Use `wait` instead to
        have an interruptible pause duration.
        """

        time.sleep(duration)
