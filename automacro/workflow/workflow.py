from typing import Sequence
import threading
from time import sleep

from automacro.utils import _get_logger
from automacro.workflow.conditional import ConditionalTask
from automacro.workflow.task import WorkflowTask


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
            tasks (Sequence[WorkflowTask]): List of WorkflowTask objects.
            workflow_name (str): Name of the workflow.
            loop (bool): Flag to indicate if the workflow should loop after
            completion. Default is False.
        """

        self.workflow_name = workflow_name
        self._logger = _get_logger(self.__class__)
        self._tasks = tasks
        self._current_task_idx = 0
        self._jump_requested = False
        self._locked = False
        self._loop = loop
        self._running = False
        self._thread = None
        self._lock = threading.RLock()

    def _prefix_log(self, message: str) -> str:
        """
        Prefix log messages with the workflow name.

        Args:
            message (str): The log message.

        Returns:
            str: The prefixed log message.
        """

        return f"[Workflow:{self.workflow_name}] {message}"

    def _is_valid_task_index(self, index: int) -> bool:
        """
        Check if the given task index is valid.

        Args:
            index (int): The task index to check.

        Returns:
            bool: True if the index is valid, False otherwise.
        """

        return 0 <= index < len(self._tasks)

    def _run_workflow(self) -> None:
        """
        Internal method to run the workflow logic.
        """

        with self._lock:
            # Reset the current task index
            self._current_task_idx = 0
            self._running = True

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
            task.execute()

            with self._lock:
                # If workflow was stopped externally
                if not self._running:
                    break

                # If no jump requested and same task still current
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

        self.stop()
        self._logger.info(self._prefix_log("Workflow completed"))

    def execute(self, background: bool = False) -> None:
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

        if background:
            self._logger.info(
                self._prefix_log("Starting workflow in background thread")
            )

            self._thread = threading.Thread(target=self._run_workflow, daemon=True)
            self._thread.start()
        else:
            self._logger.info(self._prefix_log("Starting workflow"))
            self._run_workflow()

    def stop(self) -> None:
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

    def next(self) -> None:
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
            # Loop back to the first task if the end is reached
            if self._loop:
                self._current_task_idx %= len(self._tasks)

            if self._locked:
                self._logger.info(
                    self._prefix_log(
                        f"Currently paused at task: {self._tasks[self._current_task_idx].task_name}"
                    )
                )

    def jump_to(self, task_idx: int) -> None:
        """
        Jump to a specific task in the workflow.

        Args:
            task_idx (int): Index of the task to jump to.
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

            if self._locked:
                self._logger.info(
                    self._prefix_log(
                        f"Currently paused at task: {self._tasks[self._current_task_idx].task_name}"
                    )
                )

    def lock(self) -> None:
        """
        Lock the workflow to prevent task execution. Jumps and next calls
        are allowed when locked, but the task will not be executed.
        """

        with self._lock:
            self._locked = True
            self._logger.info(self._prefix_log("Workflow locked"))

    def unlock(self) -> None:
        """
        Unlock the workflow to allow task execution.
        """

        with self._lock:
            self._locked = False
            self._logger.info(self._prefix_log("Workflow unlocked"))

    def toggle_lock(self) -> None:
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

    def join(self) -> None:
        """
        Wait for the workflow thread to complete.
        """

        if self._thread and self._thread.is_alive():
            self._thread.join()
