import threading
from time import sleep

from automacro.utils import _get_logger
from automacro.workflow.context import TaskContext


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

        Args:
            task_name (str): Name of the task.
        """

        self._logger = _get_logger(self.__class__)

        self._task_name = task_name

        self._workflow_name = None
        self._workflow_run_id = None

        self._running = False
        self._interrupt_event = threading.Event()

    @property
    def task_name(self) -> str:
        return self._task_name

    def _prefix_log(self, message: str) -> str:
        """
        Prefix log messages with the workflow name and run ID (if available)
        and task name.

        Args:
            message (str): The log message.

        Returns:
            str: The prefixed log message.
        """

        if self._workflow_name is None or self._workflow_run_id is None:
            return f"[{self.task_name}] {message}"
        return f"[{self._workflow_name}({self._workflow_run_id}):{self.task_name}] {message}"

    def step(self, ctx: TaskContext):
        """
        Perform a single iteration of the task.

        Subclasses should override this method to define the behavior executed
        on each cycle of the task's main loop.

        The task will call this method repeatedly until the task is stopped
        via the `stop` method.

        Args:
            ctx (TaskContext): The task context.
        """

        raise NotImplementedError

    def run(self, ctx: TaskContext):
        """
        Run the task repeatedly until stopped.

        Not thread-safe; should be called from a single thread.

        Args:
            ctx (TaskContext): The task context.
        """

        if self._running:
            self._logger.info(self._prefix_log("Task is already running"))
            return

        self._workflow_name = ctx.meta.workflow_name
        self._workflow_run_id = ctx.meta.run_id
        self._running = True

        self._logger.info(self._prefix_log("Starting task"))
        self._interrupt_event.clear()

        try:
            while self._running:
                # We wrap step in a try-except to catch interruptions
                try:
                    self.step(ctx)
                except _TaskInterrupted:
                    break
                # Small delay to prevent tight loop
                sleep(0.01)
        finally:
            self._running = False
            self._workflow_name = None
            self._workflow_run_id = None

    def stop(self):
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

    def wait(self, seconds: float):
        """
        Wait for a specified number of seconds or until the task is stopped
        (whichever comes first).

        Args:
            seconds (float): Number of seconds to wait.
        """

        interrupted = self._interrupt_event.wait(timeout=seconds)
        if interrupted or not self._running:
            raise _TaskInterrupted


class CheckpointTask(WorkflowTask):
    """
    A checkpoint workflow task that continuously loops without doing anything.
    Useful for creating pause points in a workflow.
    """

    def __init__(self, task_name: str = "Checkpoint Task"):
        super().__init__(task_name)

    def step(self, ctx: TaskContext):
        """
        Continuously loop without doing anything.
        """

        pass


class NoOpTask(WorkflowTask):
    """
    A no-operation workflow task that does nothing and immediately stops.
    """

    def __init__(self, task_name: str = "No-Op Task"):
        super().__init__(task_name)

    def step(self, ctx: TaskContext):
        """
        Do nothing.
        """

        self.stop()
