import threading
from time import sleep

from automacro import _logger


class _TaskInterrupted(Exception):
    """
    Internal exception raised when a task is interrupted while waiting.
    """

    pass


class WorkflowTask:
    """
    A workflow task that runs on repeat until stopped.
    """

    def __init__(self, task_name: str):
        """
        Initialize the workflow task.
        """

        self.task_name = task_name
        self._logger = _logger(self.__class__)
        self._running = False
        self._interrupt_event = threading.Event()

    def _prefix_log(self, message: str) -> str:
        """
        Prefix log messages with the task name.

        Args:
            message (str): The log message.

        Returns:
            str: The prefixed log message.
        """

        return f"[Task:{self.task_name}] {message}"

    def step(self) -> None:
        """
        Perform a single iteration of the task.

        Subclasses should override this method to define the behavior executed
        on each cycle of the task's main loop.
        """

        raise NotImplementedError

    def execute(self) -> None:
        """
        Run the task repeatedly until stopped.
        """

        if self._running:
            self._logger.info(self._prefix_log("Task is already running"))
            return

        self._logger.info(self._prefix_log("Starting task"))
        self._running = True
        self._interrupt_event.clear()

        try:
            while self._running:
                # We wrap step in a try-except to catch interruptions
                try:
                    self.step()
                except _TaskInterrupted:
                    break
                # Small delay to prevent tight loop
                sleep(0.01)
        finally:
            self._running = False

    def stop(self) -> None:
        """
        Signal to stop the task.
        """

        if self._running:
            self._logger.info(self._prefix_log("Stopping task"))
            self._running = False
            self._interrupt_event.set()

    def is_running(self) -> bool:
        """
        Check if the workflow is running.

        Returns:
            bool: True if the workflow is running, False otherwise.
        """

        return self._running

    def wait(self, seconds: float) -> None:
        """
        Wait for a specified number of seconds or until the task is stopped
        (whichever comes first).

        Args:
            seconds (float): Number of seconds to wait.
        """

        interrupted = self._interrupt_event.wait(timeout=seconds)
        if interrupted or not self._running:
            raise _TaskInterrupted


class NoOpTask(WorkflowTask):
    """
    A no-op workflow task that does nothing.
    Can be used as a checkpoint in a workflow.
    """

    def __init__(self, task_name: str = "No-Op Task"):
        super().__init__(task_name)

    def step(self) -> None:
        """
        Do nothing.
        """

        pass
