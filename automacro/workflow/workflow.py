from typing import Sequence, Callable
import threading
from time import monotonic
import uuid

from automacro.utils import _get_logger
from automacro.workflow.conditional import ConditionalTask
from automacro.workflow.task import WorkflowTask
from automacro.workflow.state import WorkflowState
from automacro.workflow.context import (
    WorkflowContext,
    TaskContext,
    WorkflowHookContext,
    WorkflowMeta,
)
from automacro.workflow.hooks import WorkflowHooks


class Workflow:
    """
    A runtime workflow engine that manages and executes a sequence of tasks.

    The workflow executes a sequence of `WorkflowTask` objects, allowing for
    advanced control flow such as jumping between tasks, looping, and
    attaching hooks for various lifecycle events.
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

        self._state = WorkflowState.IDLE
        self._current_task_idx = 0

        self._extern_req = False
        self._task_running = False
        self._in_hook = False

        self._thread = None
        self._cond = threading.Condition(threading.RLock())

    @property
    def name(self) -> str:
        return self._name

    @property
    def loop(self) -> bool:
        return self._loop

    def _is_running(self) -> bool:
        """
        Check if the workflow is running.

        This is an unsafe version that does not acquire the lock.
        Internal use only.

        Returns:
            bool: True if the workflow is running, False otherwise.
        """

        return self._state in (WorkflowState.RUNNING, WorkflowState.PAUSED)

    def _is_paused(self) -> bool:
        """
        Check if the workflow is paused.

        This is an unsafe version that does not acquire the lock.
        Internal use only.

        Returns:
            bool: True if the workflow is paused, False otherwise.
        """

        return self._state == WorkflowState.PAUSED

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

    def _check_in_hook(self, action: str) -> bool:
        """
        Check if the current call is inside a hook, and log an error if so.

        NOTE: This method must be called while holding the workflow lock.

        Args:
            action (str): The action being performed.

        Returns:
            bool: True if in a hook, False otherwise.
        """

        if not self._in_hook:
            return False

        self._logger.warning(
            self._prefix_log(
                f"Cannot call Workflow.{action}() from inside a hook. "
                "Hooks must not perform workflow control operations"
            )
        )
        return True

    def _run_hook(self, fn: Callable, *args, **kwargs):
        """
        Execute a workflow hook while guarding against workflow control calls.

        NOTE: This method must be called while holding the workflow lock.

        Args:
            fn (Callable): The hook function to execute.
            *args, **kwargs: Arguments to pass to the hook function.
        """

        self._in_hook = True
        try:
            fn(*args, **kwargs)
        finally:
            self._in_hook = False

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

    def _init_run(self) -> bool:
        """
        Initialize a workflow run, and return whether the initialization was
        successful.

        NOTE: This method must be called while holding the workflow lock.

        Returns:
            bool: True if the run was initialized, False otherwise.
        """

        # We don't want to modify the state if the workflow is currently
        # running by accidentally calling this method directly
        if self._is_running():
            return False

        # We also don't want to start a new run if the previous run was
        # stopped but cleanup is still pending
        if self._state == WorkflowState.STOPPING:
            self._logger.warning(
                self._prefix_log(
                    "Previous workflow run is still cleaning up. Cannot start a new run"
                )
            )
            return False

        self._current_task_idx = 0
        self._state = WorkflowState.RUNNING

        return True

    def _cleanup_run(self):
        """
        Cleanup after a workflow run.

        NOTE: This method must be called while holding the workflow lock.
        """

        if self._state != WorkflowState.STOPPING:
            return

        self._state = WorkflowState.IDLE
        self._current_task_idx = 0

        self._logger.info(self._prefix_log("Workflow completed"))

        self._context = None

    def _next(self):
        """
        Internal method to move to the next task in the workflow.

        NOTE: This method must be called while holding the workflow lock.
        """

        if not self._is_running():
            self._logger.warning(self._prefix_log("Workflow is not running"))
            return

        ctx = self._get_context()
        runtime = ctx.runtime
        hooks = self._hooks

        # Stop the current task
        self._stop_current_task()

        prev = (
            self._tasks[self._current_task_idx]
            if self._is_valid_task_index(self._current_task_idx)
            else None
        )

        prev_idx = self._current_task_idx
        next_idx = self._current_task_idx + 1

        # We are at the end of the task list
        if next_idx >= len(self._tasks) or prev_idx == -1:
            return self._on_iteration_end()

        # Otherwise, move to the next task
        runtime.prev_task_idx = prev_idx
        runtime.current_task_idx = next_idx
        self._current_task_idx = next_idx

        self._run_hook(
            hooks.on_current_task_change,
            prev,
            self._tasks[self._current_task_idx],
            WorkflowHookContext(ctx, self._state),
        )

        # Notify in case the workflow is waiting
        self._cond.notify_all()

    def _jump_to(self, task_idx: int, *, reset_transient: bool = False):
        """
        Internal method to jump to a specific task in the workflow.

        NOTE: This method must be called while holding the workflow lock.

        Args:
            task_idx (int): Index of the task to jump to.
            reset_transient (bool): Whether to reset the transient state in
            the workflow context. Default is False.
        """

        if not self._is_running():
            self._logger.warning(self._prefix_log("Workflow is not running"))
            return

        # Invalid index
        if not self._is_valid_task_index(task_idx):
            self._logger.error(
                self._prefix_log(f"Invalid task index for jump_to: {task_idx}")
            )
            return

        # Stop the current task
        self._stop_current_task()

        prev = (
            self._tasks[self._current_task_idx]
            if self._is_valid_task_index(self._current_task_idx)
            else None
        )

        runtime = self._get_context().runtime

        runtime.prev_task_idx = self._current_task_idx
        runtime.current_task_idx = task_idx
        self._current_task_idx = task_idx

        if reset_transient:
            self._get_context().reset_transient()

        if self._is_paused():
            self._logger.info(
                self._prefix_log(
                    f"Currently paused at task: {self._tasks[self._current_task_idx].name}"
                )
            )

        current = self._tasks[self._current_task_idx]

        self._run_hook(
            self._hooks.on_current_task_change,
            prev,
            current,
            WorkflowHookContext(self._get_context(), self._state),
        )

        # Notify in case the workflow is waiting
        self._cond.notify_all()

    def _run_impl(self):
        """
        Internal method for handling the workflow run loop.
        """

        with self._cond:
            if not self._init_run():
                return

            ctx = self._get_context()
            hooks = self._hooks
            self._logger.info(self._prefix_log("Starting iteration 0"))

            self._run_hook(
                hooks.on_workflow_start,
                WorkflowHookContext(self._get_context(), self._state),
            )
            self._run_hook(
                hooks.on_iteration_start,
                0,
                WorkflowHookContext(ctx, self._state),
            )

        try:
            while True:
                with self._cond:
                    while self._is_paused():
                        self._cond.wait()

                    if not self._is_running():
                        break

                    task = self._tasks[self._current_task_idx]

                    self._run_hook(
                        hooks.on_task_start,
                        task,
                        TaskContext(ctx, self._state),
                    )

                try:
                    # Execute the current task outside the lock to prevent
                    # blocking other operations
                    task.run(TaskContext(ctx, self._state))
                except Exception as e:
                    self._logger.exception(
                        self._prefix_log(f"Exception in task {task.name}: {e}")
                    )
                    with self._cond:
                        self._state = WorkflowState.STOPPING
                        self._cond.notify_all()
                    break

                with self._cond:
                    if not self._is_running():
                        break

                    ctx.runtime.tasks_executed += 1

                    # If an external control flow change was requested, skip
                    if self._extern_req:
                        self._extern_req = False
                        continue

                    # Otherwise, if the task is a ConditionalTask, handle branching
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
                        self._jump_to(task.next_task_idx)
                        continue

                    # Otherwise, move to the next task
                    self._next()
        finally:
            with self._cond:
                self._run_hook(
                    hooks.on_workflow_end,
                    WorkflowHookContext(ctx, self._state),
                )

                self._cleanup_run()

    def _stop_current_task(self):
        """
        Stop the current task if it is running.

        NOTE: This method must be called while holding the workflow lock.
        """

        if not self._is_running():
            return

        if not self._is_valid_task_index(self._current_task_idx):
            return

        task = self._tasks[self._current_task_idx]

        if not task.is_running():
            return

        task.stop()
        self._run_hook(
            self._hooks.on_task_end,
            task,
            TaskContext(self._get_context(), self._state),
        )

    def _on_iteration_end(self):
        """
        Handle the end of the current iteration. This also means the previous
        task must be stopped before calling this method.

        NOTE: This method must be called while holding the workflow lock. This
        is required to ensure thread safety. However, this also means that
        long-running hooks may block other operations on the workflow.
        """

        if not self._is_running():
            return

        ctx = self._get_context()
        runtime = ctx.runtime
        hooks = self._hooks

        self._run_hook(
            hooks.on_iteration_end,
            ctx.runtime.iteration,
            WorkflowHookContext(ctx, self._state),
        )

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

            self._run_hook(
                hooks.on_current_task_change,
                prev,
                None,
                WorkflowHookContext(ctx, self._state),
            )

            self._state = WorkflowState.STOPPING
            self._cond.notify_all()

            return

        # Loop back to the first task
        runtime.prev_task_idx = self._current_task_idx
        runtime.current_task_idx = 0
        self._current_task_idx = 0

        runtime.iteration += 1
        ctx.reset_transient()

        self._logger.info(
            self._prefix_log(f"Starting iteration {ctx.runtime.iteration}")
        )

        self._run_hook(
            hooks.on_iteration_start,
            runtime.iteration,
            WorkflowHookContext(ctx, self._state),
        )

        self._run_hook(
            hooks.on_current_task_change,
            prev,
            self._tasks[0],
            WorkflowHookContext(ctx, self._state),
        )

    def run(self):
        """
        Run the workflow in the current thread.
        """

        with self._cond:
            if self._check_in_hook("run"):
                return

            if self._is_running():
                self._logger.warning(self._prefix_log("Workflow is already running"))
                return

            if self._state == WorkflowState.STOPPING:
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

        with self._cond:
            if self._check_in_hook("start"):
                return

            if self._is_running():
                self._logger.warning(self._prefix_log("Workflow is already running"))
                return

            if self._state == WorkflowState.STOPPING:
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

        with self._cond:
            if self._check_in_hook("stop"):
                return

            if not self._is_running():
                return

            self._logger.info(self._prefix_log("Stopping workflow"))

            # Stop the current task
            self._stop_current_task()

            self._state = WorkflowState.STOPPING
            self._cond.notify_all()

    def next(self):
        """
        Signal to move to the next task in the workflow.
        """

        with self._cond:
            if self._check_in_hook("next"):
                return

            if not self._is_running():
                return

            self._extern_req = True
            self._next()

    def jump_to(self, task_idx: int, *, reset_transient: bool = False):
        """
        Jump to a specific task in the workflow.

        Args:
            task_idx (int): Index of the task to jump to.
            reset_transient (bool): Whether to reset the transient state in
            the workflow context. Default is False.
        """

        with self._cond:
            if self._check_in_hook("jump_to"):
                return

            if not self._is_running():
                return

            self._extern_req = True
            self._jump_to(task_idx, reset_transient=reset_transient)

    def end_iteration(self):
        """
        End the current iteration and, if looping is enabled, jump to the
        first task.
        """

        with self._cond:
            if self._check_in_hook("end_iteration"):
                return

            if not self._is_running():
                return

            self._extern_req = True
            # Stop the current task
            self._stop_current_task()

            self._on_iteration_end()

            # Notify in case the workflow is waiting
            self._cond.notify_all()

    def pause(self):
        """
        Pause the workflow to prevent task execution. Calls to `next` and
        `jump_to` are allowed when paused, but the task will not be executed.

        Some hooks may still be invoked while the workflow is paused. These
        hooks are:
        - `on_iteration_start`
        - `on_iteration_end`
        """

        with self._cond:
            if self._check_in_hook("pause"):
                return

            if self._state != WorkflowState.RUNNING:
                return

            ctx = self._get_context()

            self._state = WorkflowState.PAUSED
            self._logger.info(self._prefix_log("Workflow paused"))

            self._run_hook(
                self._hooks.on_pause,
                WorkflowHookContext(ctx, self._state),
            )

    def resume(self):
        """
        Resume the workflow to allow task execution.
        """

        with self._cond:
            if self._check_in_hook("resume"):
                return

            if self._state != WorkflowState.PAUSED:
                return

            ctx = self._get_context()

            self._state = WorkflowState.RUNNING

            self._logger.info(self._prefix_log("Workflow resumed"))

            self._run_hook(
                self._hooks.on_resume,
                WorkflowHookContext(ctx, self._state),
            )
            self._cond.notify_all()

    def toggle(self):
        """
        Toggle the workflow between paused and running states.
        """

        with self._cond:
            if self._check_in_hook("toggle"):
                return

            ctx = self._get_context()

            if self._state == WorkflowState.PAUSED:
                self._state = WorkflowState.RUNNING

                self._logger.info(self._prefix_log("Workflow resumed"))

                self._run_hook(
                    self._hooks.on_resume,
                    WorkflowHookContext(ctx, self._state),
                )
                self._cond.notify_all()
            elif self._state == WorkflowState.RUNNING:
                self._state = WorkflowState.PAUSED

                self._logger.info(self._prefix_log("Workflow paused"))

                self._run_hook(
                    self._hooks.on_pause,
                    WorkflowHookContext(ctx, self._state),
                )

    def is_running(self) -> bool:
        """
        Check if the workflow is running.

        Returns:
            bool: True if the workflow is running, False otherwise.
        """

        with self._cond:
            return self._is_running()

    def is_paused(self) -> bool:
        """
        Check if the workflow is paused.

        Returns:
            bool: True if the workflow is paused, False otherwise.
        """

        with self._cond:
            return self._is_paused()

    def join(self):
        """
        Wait for the workflow thread to complete.
        """

        if self._thread and self._thread.is_alive():
            self._thread.join()
