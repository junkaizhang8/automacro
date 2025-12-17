from typing import Sequence
import threading
from time import sleep, monotonic
import uuid

from automacro.utils import _get_logger
from automacro.workflow.conditional import ConditionalTask
from automacro.workflow.task import WorkflowTask
from automacro.workflow.context import WorkflowContext, TaskContext, WorkflowMeta


class Workflow:
    """
    Class to manage a workflow of tasks.
    """

    def __init__(
        self, tasks: Sequence[WorkflowTask], workflow_name: str, loop: bool = False
    ):
        """
        Initialize the workflow with a list of tasks.

        Args:
            tasks (Sequence[WorkflowTask]): Sequence of WorkflowTask objects.
            workflow_name (str): Name of the workflow.
            loop (bool): Flag to indicate if the workflow should loop after
            completion. Default is False.
        """

        self._logger = _get_logger(self.__class__)

        # Copy the tasks to avoid external modifications
        self._tasks = tuple(tasks)

        self._workflow_name = workflow_name
        self._loop = loop

        self._context = None

        self._current_task_idx = 0
        self._jump_requested = False
        self._locked = False
        self._running = False
        self._thread = None
        self._lock = threading.RLock()

    @property
    def workflow_name(self) -> str:
        return self._workflow_name

    @property
    def loop(self) -> bool:
        return self._loop

    def _get_context(self) -> WorkflowContext:
        """
        Guarded method to access the workflow context. Do not directly
        access the `_context` attribute directly in case it is not initialized.

        Raises:
            RuntimeError: If the workflow context is not initialized.

        Returns:
            WorkflowContext: The workflow context.
        """

        if self._context is None:
            raise RuntimeError("Workflow context is not initialized")
        return self._context

    def _get_run_id(self) -> str | None:
        """
        Get the current run ID of the workflow.

        Returns:
            str | None: The run ID if the workflow is running, None otherwise.
        """

        if self._context is None:
            return None
        return self._context.meta.run_id

    def _prefix_log(self, message: str) -> str:
        """
        Prefix log messages with the workflow name and the run ID
        (if available).

        Args:
            message (str): The log message.

        Returns:
            str: The prefixed log message.
        """

        run_id = self._get_run_id()
        if run_id is not None:
            return f"[{self._workflow_name}({run_id})] {message}"
        return f"[{self._workflow_name}] {message}"

    def _is_valid_task_index(self, index: int) -> bool:
        """
        Check if the given task index is valid.

        Args:
            index (int): The task index to check.

        Returns:
            bool: True if the index is valid, False otherwise.
        """

        return -len(self._tasks) <= index < len(self._tasks)

    def _init_context(self):
        """
        Initialize the workflow context.
        """

        if self._context is None:
            self._context = WorkflowContext(
                meta=WorkflowMeta(
                    workflow_name=self.workflow_name,
                    run_id=uuid.uuid4().hex[:8],
                    started_at=monotonic(),
                    loop=self.loop,
                )
            )

    def _init_run(self):
        """
        Initialize a workflow run.
        """

        with self._lock:
            # We don't want to modify the state if the workflow is currently
            # running by accidentally calling this method directly
            if self._running:
                return

            self._running = True
            self._current_task_idx = 0
            self._jump_requested = False
            self._locked = False

    def _cleanup_run(self):
        """
        Cleanup after a workflow run.
        """

        with self._lock:
            self._running = False
            self._current_task_idx = 0
            self._jump_requested = False
            self._locked = False

            self._logger.info(self._prefix_log("Workflow completed"))

            self._context = None

    def _run_workflow(self):
        """
        Internal method to run the workflow logic.
        """

        self._init_run()

        while True:
            with self._lock:
                # Exit if workflow is stopped or index is out of range
                if not self._running or self._current_task_idx >= len(self._tasks):
                    break

                # Skip execution if locked
                if self._locked:
                    # Jumps are allowed when locked
                    # So, we still have to reset the flag if a jump was requested
                    self._jump_requested = False
                    continue

                task = self._tasks[self._current_task_idx]
                idx = self._current_task_idx

            # Execute the current task outside the lock to prevent blocking other operations
            task.execute(TaskContext(self._get_context()))

            with self._lock:
                # If workflow was stopped externally
                if not self._running:
                    break

                self._get_context().runtime.tasks_executed += 1

                # If no jump requested and still on the same task
                if idx == self._current_task_idx and not self._jump_requested:
                    # If the task is a ConditionalTask, handle branching
                    if (
                        isinstance(task, ConditionalTask)
                        and task.next_task_idx is not None
                    ):
                        # If the next task index is invalid, stop the workflow
                        if not self._is_valid_task_index(task.next_task_idx):
                            self._logger.error(
                                self._prefix_log(
                                    f"Invalid task index from ConditionalTask ({task.task_name}): {task.next_task_idx}"
                                )
                            )
                            self.stop()
                            break
                        # Otherwise, jump to the specified task
                        self.jump_to(task.next_task_idx)
                    else:
                        self.next()

                # If a jump was requested, reset the flag
                self._jump_requested = False

            # Small delay to prevent tight loop
            sleep(0.01)

        self._cleanup_run()

    def execute(self, background: bool = False):
        """
        Execute the workflow.

        Args:
            background (bool): Flag to indicate if the workflow should run
            in a background thread. Default is False.
        """

        with self._lock:
            if self._running:
                self._logger.warning(self._prefix_log("Workflow is already running"))
                return

            self._init_context()

        if background:
            self._logger.info(
                self._prefix_log("Starting workflow in background thread")
            )

            self._thread = threading.Thread(target=self._run_workflow, daemon=True)
            self._thread.start()
        else:
            self._logger.info(self._prefix_log("Starting workflow"))
            self._run_workflow()

    def stop(self):
        """
        Signal to stop the workflow as soon as possible.
        """

        with self._lock:
            if not self._running:
                return

            self._logger.info(self._prefix_log("Stopping workflow"))
            self._running = False

            # Stop the current task
            if self._is_valid_task_index(self._current_task_idx):
                self._tasks[self._current_task_idx].stop()

    def next(self):
        """
        Signal to move to the next task in the workflow.
        """

        with self._lock:
            if not self._running:
                self._logger.warning(self._prefix_log("Workflow is not running"))
                return

            # Stop the current task
            if self._is_valid_task_index(self._current_task_idx):
                self._tasks[self._current_task_idx].stop()

            self._current_task_idx += 1

            if self.loop and self._current_task_idx >= len(self._tasks):
                # Loop back to the first task if the end is reached
                self._current_task_idx = 0

                self._get_context().runtime.iteration += 1
                # Reset the transient state for the new loop iteration
                self._get_context().reset_transient()

                self._logger.info(
                    self._prefix_log(
                        f"Starting iteration {self._get_context().runtime.iteration}"
                    )
                )

            if self._locked:
                self._logger.info(
                    self._prefix_log(
                        f"Currently paused at task: {self._tasks[self._current_task_idx].task_name}"
                    )
                )

    def jump_to(self, task_idx: int, *, reset_transient: bool = False):
        """
        Jump to a specific task in the workflow.

        Args:
            task_idx (int): Index of the task to jump to.
            reset_transient (bool): Whether to reset the transient context.
            Default is False.
        """

        with self._lock:
            if not self._running:
                self._logger.warning(self._prefix_log("Workflow is not running"))
                return

            # Invalid index
            if not self._is_valid_task_index(task_idx):
                self._logger.error(
                    self._prefix_log(f"Invalid task index for jump_to: {task_idx}")
                )
                return

            # Stop the current task
            if self._is_valid_task_index(self._current_task_idx):
                self._tasks[self._current_task_idx].stop()

            self._current_task_idx = task_idx
            self._jump_requested = True

            if reset_transient:
                self._get_context().reset_transient()

            if self._locked:
                self._logger.info(
                    self._prefix_log(
                        f"Currently paused at task: {self._tasks[self._current_task_idx].task_name}"
                    )
                )

    def lock(self):
        """
        Lock the workflow to prevent task execution. Jumps and next calls
        are allowed when locked, but the task will not be executed.
        """

        with self._lock:
            self._locked = True
            self._logger.info(self._prefix_log("Workflow locked"))

    def unlock(self):
        """
        Unlock the workflow to allow task execution.
        """

        with self._lock:
            self._locked = False
            self._logger.info(self._prefix_log("Workflow unlocked"))

    def toggle_lock(self):
        """
        Toggle the lock state of the workflow.
        """

        with self._lock:
            if self._locked:
                self.unlock()
            else:
                self.lock()

    def is_locked(self) -> bool:
        """
        Check if the workflow is locked.

        Returns:
            bool: True if the workflow is locked, False otherwise.
        """

        with self._lock:
            return self._locked

    def is_running(self) -> bool:
        """
        Check if the workflow is running.

        Returns:
            bool: True if the workflow is running, False otherwise.
        """

        with self._lock:
            return self._running

    def join(self):
        """
        Wait for the workflow thread to complete.
        """

        if self._thread and self._thread.is_alive():
            self._thread.join()
