from typing import Sequence
import threading
from time import sleep, monotonic
import uuid

from automacro.utils import _get_logger
from automacro.workflow.conditional import ConditionalTask
from automacro.workflow.task import WorkflowTask
from automacro.workflow.context import (
    WorkflowContext,
    TaskContext,
    WorkflowHookContext,
    WorkflowMeta,
)
from automacro.workflow.hooks import WorkflowHooks


class Workflow:
    """
    Class to manage a workflow of tasks.
    """

    def __init__(
        self,
        tasks: Sequence[WorkflowTask],
        name: str,
        *,
        loop: bool = False,
        hooks: WorkflowHooks | None = None,
    ):
        """
        Initialize the workflow with a list of tasks.

        Args:
            tasks (Sequence[WorkflowTask]): Sequence of WorkflowTask objects.
            name (str): Name of the workflow.
            loop (bool): Flag to indicate if the workflow should loop after
            completion. Default is False.
            hooks (WorkflowHooks | None): Optional workflow hooks.
        """

        self._logger = _get_logger(self.__class__)

        # Copy the tasks to avoid external modifications
        self._tasks = tuple(tasks)

        self._name = name
        self._loop = loop
        self._hooks = hooks or WorkflowHooks()

        self._context = None

        self._current_task_idx = 0
        self._jump_requested = False
        self._locked = False
        self._running = False
        self._pending_cleanup = False

        self._thread = None
        self._lock = threading.RLock()

    @property
    def name(self) -> str:
        return self._name

    @property
    def loop(self) -> bool:
        return self._loop

    def _get_context(self) -> WorkflowContext:
        """
        Guarded method to access the workflow context. Do not directly
        access the `_context` attribute directly in case it is not initialized.

        NOTE: This method must be called while holding the workflow lock.

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

        NOTE: This method must be called while holding the workflow lock.

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

        NOTE: This method must be called while holding the workflow lock.

        Args:
            message (str): The log message.

        Returns:
            str: The prefixed log message.
        """

        run_id = self._get_run_id()
        if run_id is not None:
            return f"[{self._name}({run_id})] {message}"
        return f"[{self._name}] {message}"

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
                    workflow_name=self._name,
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

            # We also don't want to start a new run if the previous run was
            # stopped but cleanup is still pending
            if self._pending_cleanup:
                self._logger.warning(
                    self._prefix_log(
                        "Previous workflow run is still cleaning up. Cannot start a new run"
                    )
                )
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
            if not self._pending_cleanup:
                return

            self._running = False
            self._current_task_idx = 0
            self._jump_requested = False
            self._locked = False

            self._logger.info(self._prefix_log("Workflow completed"))

            self._context = None

    def _run_impl(self):
        """
        Internal method for handling the workflow run loop.
        """

        self._init_run()

        with self._lock:
            ctx = self._get_context()
            hooks = self._hooks
            self._logger.info(self._prefix_log("Starting iteration 0"))

        hooks.on_workflow_start(WorkflowHookContext(self._get_context()))
        hooks.on_iteration_start(0, WorkflowHookContext(ctx))

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

            # Execute the current task outside the lock to prevent blocking
            # other operations
            hooks.on_task_start(task, TaskContext(ctx))
            task.run(TaskContext(ctx))
            hooks.on_task_end(task, TaskContext(ctx))

            with self._lock:
                # If workflow was stopped externally
                if not self._running:
                    break

                ctx.runtime.tasks_executed += 1

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
                                    f"Invalid task index from ConditionalTask ({task.name}): {task.next_task_idx}"
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

        hooks.on_workflow_end(WorkflowHookContext(ctx))
        self._cleanup_run()

    def _on_iteration_end(self):
        """
        Handle the end of the current iteration. This also means the previous
        task must be stopped before calling this method.

        NOTE: This method must be called while holding the workflow lock. This
        is required to ensure thread safety. However, this also means that
        long-running hooks may block other operations on the workflow.
        """

        if not self._running:
            return

        ctx = self._get_context()
        runtime = ctx.runtime
        hooks = self._hooks

        hooks.on_iteration_end(ctx.runtime.iteration, WorkflowHookContext(ctx))

        prev = (
            self._tasks[self._current_task_idx]
            if self._is_valid_task_index(self._current_task_idx)
            else None
        )

        if not self._loop:
            runtime.prev_task_idx = self._current_task_idx
            runtime.current_task_idx = None
            # Set to an invalid index to indicate completion
            self._current_task_idx = len(self._tasks)

            hooks.on_current_task_change(prev, None, WorkflowHookContext(ctx))
            return

        # Loop back to the first task if the end is reached
        runtime.prev_task_idx = self._current_task_idx
        runtime.current_task_idx = 0
        self._current_task_idx = 0

        runtime.iteration += 1
        ctx.reset_transient()

        self._logger.info(
            self._prefix_log(f"Starting iteration {ctx.runtime.iteration}")
        )

        hooks.on_iteration_start(runtime.iteration, WorkflowHookContext(ctx))

        hooks.on_current_task_change(prev, self._tasks[0], WorkflowHookContext(ctx))

    def run(self):
        """
        Run the workflow in the current thread.
        """

        with self._lock:
            if self._running:
                self._logger.warning(self._prefix_log("Workflow is already running"))
                return

            if not self._running and self._pending_cleanup:
                self._logger.warning(
                    self._prefix_log(
                        "Previous workflow run is still cleaning up. Cannot start a new run"
                    )
                )
                return

            self._init_context()
            self._logger.info(self._prefix_log("Starting workflow"))

        self._run_impl()

    def start(self):
        """
        Run the workflow in a separate thread.
        """

        with self._lock:
            if self._running:
                self._logger.warning(self._prefix_log("Workflow is already running"))
                return

            if not self._running and self._pending_cleanup:
                self._logger.warning(
                    self._prefix_log(
                        "Previous workflow run is still cleaning up. Cannot start a new run"
                    )
                )
                return

            self._init_context()
            self._logger.info(
                self._prefix_log("Starting workflow in a separate thread")
            )

        self._thread = threading.Thread(target=self._run_impl)
        self._thread.start()

    def stop(self):
        """
        Signal to stop the workflow as soon as possible.
        """

        with self._lock:
            if not self._running:
                return

            self._logger.info(self._prefix_log("Stopping workflow"))
            self._running = False
            self._pending_cleanup = True

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

            ctx = self._get_context()
            runtime = ctx.runtime
            hooks = self._hooks

            prev = None

            # Stop the current task
            if self._is_valid_task_index(self._current_task_idx):
                prev = self._tasks[self._current_task_idx]
                prev.stop()

            prev_idx = self._current_task_idx
            next_idx = self._current_task_idx + 1

            # We are at the end of the task list
            if next_idx >= len(self._tasks) or prev_idx == -1:
                return self._on_iteration_end()

            # Otherwise, move to the next task
            runtime.prev_task_idx = prev_idx
            runtime.current_task_idx = next_idx
            self._current_task_idx = next_idx

            hooks.on_current_task_change(
                prev, self._tasks[self._current_task_idx], WorkflowHookContext(ctx)
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

            prev = None

            # Stop the current task
            if self._is_valid_task_index(self._current_task_idx):
                prev = self._tasks[self._current_task_idx]
                self._tasks[self._current_task_idx].stop()

            self._current_task_idx = task_idx
            self._jump_requested = True

            if reset_transient:
                self._get_context().reset_transient()

            if self._locked:
                self._logger.info(
                    self._prefix_log(
                        f"Currently paused at task: {self._tasks[self._current_task_idx].name}"
                    )
                )

            current = self._tasks[self._current_task_idx]

            self._hooks.on_current_task_change(
                prev, current, WorkflowHookContext(self._get_context())
            )

    def end_iteration(self):
        """
        End the current iteration and, if looping is enabled, jump to the
        first task.
        """

        with self._lock:
            if not self._running:
                return

            # Stop the current task
            if self._is_valid_task_index(self._current_task_idx):
                self._tasks[self._current_task_idx].stop()

            self._on_iteration_end()

    def lock(self):
        """
        Lock the workflow to prevent task execution. Calls to `next` and
        `jump_to` are allowed when locked, but the task will not be executed.

        Some hooks may still be invoked while the workflow is locked. These
        hooks are:
        - `on_iteration_start`
        - `on_iteration_end`
        """

        self._lock.acquire()

        if self._locked:
            return self._lock.release()

        ctx = self._get_context()

        self._locked = True
        ctx.runtime.is_locked = True
        self._logger.info(self._prefix_log("Workflow locked"))

        # We release the lock early to prevent other threads from waiting
        # too long while the hook is being executed
        self._lock.release()

        self._hooks.on_lock(WorkflowHookContext(ctx))

    def unlock(self):
        """
        Unlock the workflow to allow task execution.
        """

        self._lock.acquire()

        if not self._locked:
            return self._lock.release()

        ctx = self._get_context()

        self._locked = False
        ctx.runtime.is_locked = False
        self._logger.info(self._prefix_log("Workflow unlocked"))

        # We release the lock early to prevent other threads from waiting
        # too long while the hook is being executed
        self._lock.release()

        self._hooks.on_unlock(WorkflowHookContext(ctx))

    def toggle_lock(self):
        """
        Toggle the lock state of the workflow.
        """

        self._lock.acquire()

        ctx = self._get_context()

        if self._locked:
            self._locked = False
            ctx.runtime.is_locked = False
            self._logger.info(self._prefix_log("Workflow unlocked"))

            self._lock.release()

            self._hooks.on_unlock(WorkflowHookContext(ctx))
        else:
            self._locked = True
            ctx.runtime.is_locked = True
            self._logger.info(self._prefix_log("Workflow locked"))

            self._lock.release()

            self._hooks.on_lock(WorkflowHookContext(ctx))

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
