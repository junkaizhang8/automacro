from typing import Sequence
import threading
from time import sleep

from automacro import _logger
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

        self.tasks = tasks
        self.workflow_name = workflow_name
        self.current_task_idx = 0
        self.logger = _logger(self.__class__)
        self._jump_requested = False
        self._locked = False
        self._loop = loop
        self._running = False
        self._thread = None

    def _prefix_log(self, message: str) -> str:
        """
        Prefix log messages with the workflow name.

        Args:
            message (str): The log message.

        Returns:
            str: The prefixed log message.
        """

        return f"[Workflow:{self.workflow_name}] {message}"

    def _run_workflow(self) -> None:
        """
        Internal method to run the workflow logic.
        """

        # Reset the current task index
        self.current_task_idx = 0
        self._running = True
        while self._running and self.current_task_idx < len(self.tasks):
            # Only execute the task if not locked
            if not self._locked:
                task = self.tasks[self.current_task_idx]
                idx = self.current_task_idx
                task.execute()
                # Only move to the next task if neither next nor jump_to was called
                if (
                    self._running
                    and idx == self.current_task_idx
                    and not self._jump_requested
                ):
                    self.next()

            # If a jump was requested, reset the flag
            if self._jump_requested:
                self._jump_requested = False
            # Small delay to prevent tight loop
            sleep(0.01)
        self.stop()
        self.logger.info(self._prefix_log("Workflow completed"))

    def execute(self, background: bool = False) -> None:
        """
        Execute the workflow.

        Args:
            background (bool): Flag to indicate if the workflow should run
            in a background thread. Default is False.
        """

        if self._running:
            self.logger.warning(self._prefix_log("Workflow is already running"))

            return

        if background:
            self.logger.info(self._prefix_log("Starting workflow in background thread"))

            self._thread = threading.Thread(target=self._run_workflow, daemon=True)
            self._thread.start()
        else:
            self.logger.info(self._prefix_log("Starting workflow"))
            self._run_workflow()

    def stop(self) -> None:
        """
        Signal to stop the workflow as soon as possible.
        """

        # Stop the workflow
        if self._running:
            self.logger.info(self._prefix_log("Stopping workflow"))
            self._running = False
            # Stop the current task
            if self.current_task_idx < len(self.tasks):
                self.tasks[self.current_task_idx].stop()

    def next(self) -> None:
        """
        Signal to move to the next task in the workflow.
        """

        if not self._running:
            self.logger.warning(self._prefix_log("Workflow is not running"))

            return

        # Stop the current task
        self.tasks[self.current_task_idx].stop()
        self.current_task_idx += 1
        # Loop back to the first task if the end is reached
        if self._loop:
            self.current_task_idx %= len(self.tasks)

        if self._locked:
            self.logger.info(
                self._prefix_log(
                    f"Currently paused at task: {self.tasks[self.current_task_idx].task_name}"
                )
            )

    def jump_to(self, task_idx: int) -> None:
        """
        Jump to a specific task in the workflow.

        Args:
            task_idx (int): Index of the task to jump to.
        """

        if not self._running:
            self.logger.warning(self._prefix_log("Workflow is not running"))

            return

        # Invalid index
        if task_idx < 0 or task_idx >= len(self.tasks):
            self.logger.error(
                self._prefix_log(f"Invalid task index for jump_to: {task_idx}")
            )

            return

        # Stop the current task
        self.tasks[self.current_task_idx].stop()
        self.current_task_idx = task_idx
        self._jump_requested = True

        if self._locked:
            self.logger.info(
                self._prefix_log(
                    f"Currently paused at task: {self.tasks[self.current_task_idx].task_name}"
                )
            )

    def lock(self) -> None:
        """
        Lock the workflow to prevent task execution. Jumps and next calls
        are allowed when locked, but the task will not be executed.
        """

        self._locked = True
        self.logger.info(self._prefix_log("Workflow locked"))

    def unlock(self) -> None:
        """
        Unlock the workflow to allow task execution.
        """

        self._locked = False
        self.logger.info(self._prefix_log("Workflow unlocked"))

    def is_running(self) -> bool:
        """
        Check if the workflow is running.

        Returns:
            bool: True if the workflow is running, False otherwise.
        """

        return self._running

    def join(self) -> None:
        """
        Wait for the workflow thread to complete.
        """

        if self._thread and self._thread.is_alive():
            self._thread.join()
