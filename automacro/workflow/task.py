import threading

from automacro.utils import _get_logger
from automacro.workflow.context import TaskContext


class TaskInterrupted(Exception):
    """
    Exception raised to signal that a workflow task has been interrupted.
    """

    pass


class WorkflowTask:
    """
    A workflow task that runs on repeat until stopped.
    """

    def __init__(self, name: str):
        """
        Initialize the workflow task.

        Args:
            name (str): Name of the task.
        """

        self._logger = _get_logger(self.__class__)

        self._name = name

        self._workflow_name = None
        self._workflow_run_id = None

        self._stop_event = threading.Event()
        self._stop_event.set()

    @property
    def name(self) -> str:
        return self._name

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
            return f"[{self._name}] {message}"
        return (
            f"[{self._workflow_name}({self._workflow_run_id}):{self._name}] {message}"
        )

    def on_start(self, ctx: TaskContext):
        """
        Called exactly once when the task starts.

        Subclasses may override this method to define any setup behavior
        at the start of the task.

        Args:
            ctx (TaskContext): The task context.
        """

        pass

    def on_end(self, ctx: TaskContext):
        """
        Called exactly once when the task ends (not when `stop` is called).

        Subclasses may override this method to define any teardown behavior
        at the end of the task.

        Args:
            ctx (TaskContext): The task context.
        """

        pass

    def step(self, ctx: TaskContext):
        """
        Perform a single iteration of the task.

        Subclasses should override this method to define the behavior for
        each step of the task's execution loop.

        The task will call this method repeatedly until the task is stopped
        via the `stop` method.

        Args:
            ctx (TaskContext): The task context.
        """

        raise NotImplementedError

    def run(self, ctx: TaskContext):
        """
        Run the task repeatedly until stopped.

        Args:
            ctx (TaskContext): The task context.
        """

        if not self._stop_event.is_set():
            self._logger.warning(self._prefix_log("Task is already running"))
            return

        self._workflow_name = ctx.meta.workflow_name
        self._workflow_run_id = ctx.meta.run_id

        self._logger.info(self._prefix_log("Starting task"))
        self._stop_event.clear()

        try:
            self.on_start(ctx)
            while self.is_running():
                # We wrap step in a try-except to catch interruptions
                try:
                    self.step(ctx)
                except TaskInterrupted:
                    break
                self._stop_event.wait(0)
        finally:
            self.on_end(ctx)
            self._stop_event.set()
            self._workflow_name = None
            self._workflow_run_id = None

    def stop(self):
        """
        Signal to stop the task.
        """

        if self.is_running():
            self._logger.info(self._prefix_log("Stopping task"))
            self._stop_event.set()

    def is_running(self) -> bool:
        """
        Check if the workflow is running.

        Returns:
            bool: True if the workflow is running, False otherwise.
        """

        return not self._stop_event.is_set()

    def check_stopped(self):
        """
        Non-blocking check for whether the task has been stopped. If stopped,
        raises `TaskInterrupted` and immediately exits the current step.
        Only meant to be called inside `step`.

        Raises:
            TaskInterrupted: If the task has been stopped.
        """
        if not self.is_running():
            raise TaskInterrupted

    def wait(self, seconds: float):
        """
        Wait for a specified number of seconds or until the task is stopped
        (whichever comes first). If stopped, raises `TaskInterrupted` and
        immediately exits the current step. Only meant to be called inside
        `step`.

        Args:
            seconds (float): Number of seconds to wait.

        Raises:
            TaskInterrupted: If the task has been stopped during the wait.
        """

        interrupted = self._stop_event.wait(timeout=seconds)
        if interrupted:
            raise TaskInterrupted


class CheckpointTask(WorkflowTask):
    """
    A checkpoint workflow task that blocks the running thread until `stop` is
    called. Useful for creating pause points in a workflow.
    """

    def __init__(self, name: str = "Checkpoint Task"):
        """
        Initialize the checkpoint task.

        Args:
            name (str): The name of the task. Default is "Checkpoint Task".
        """

        super().__init__(name)

    def step(self, ctx: TaskContext):
        """
        Block until stopped.
        """

        # Block the thread until a stop is requested
        self._stop_event.wait()

        raise TaskInterrupted


class NoOpTask(WorkflowTask):
    """
    A no-operation workflow task that does nothing and immediately stops.
    """

    def __init__(self, name: str = "No-Op Task"):
        """
        Initialize the no-op task.

        Args:
            name (str): The name of the task. Default is "No-Op Task".
        """

        super().__init__(name)

    def step(self, ctx: TaskContext):
        """
        Do nothing.
        """

        raise TaskInterrupted
