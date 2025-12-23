from automacro.workflow.task import WorkflowTask
from automacro.workflow.context import TaskContext, WorkflowHookContext


class WorkflowHooks:
    """
    Base class for workflow hooks.

    Subclasses may override any of the hook methods to implement custom
    behavior at various points in the workflow execution lifecycle.

    All hook methods are no-ops by default.
    """

    def on_workflow_start(self, ctx: WorkflowHookContext):
        """
        Called once when a workflow run starts.

        This hook is invoked after the workflow context has been initialized
        and before any tasks are executed.

        Args:
            ctx (WorkflowHookContext): The context of the workflow run.
        """

        pass

    def on_workflow_end(self, ctx: WorkflowHookContext):
        """
        Called once when a workflow run ends.

        This hook is invoked when the workflow terminates, either due to:
        - Normal completion of all tasks
        - An explicit stop request
        - An error or invalid state

        The workflow context is still valid when this hook is called.

        Args:
            ctx (WorkflowHookContext): The context of the workflow run.
        """

        pass

    def on_iteration_start(self, iteration: int, ctx: WorkflowHookContext):
        """
        Called at the start of each workflow loop iteration.

        An iteration represents when the workflow has looped back to the
        first task when looping is enabled. An iteration does not require
        every task to have been executed; it simply indicates that the
        task execution pointer has wrapped around.

        This hook is invoked before any tasks are executed in the current
        iteration.

        Args:
            iteration (int): The current iteration number (0-based).
            ctx (WorkflowHookContext): The context of the workflow run.
        """

        pass

    def on_iteration_end(self, iteration: int, ctx: WorkflowHookContext):
        """
        Called at the end of each workflow loop iteration.

        This hook is invoked after the last task has been executed in the
        workflow iteration and before the task execution pointer wraps around.

        Args:
            iteration (int): The current iteration number (0-based).
            ctx (WorkflowHookContext): The context of the workflow run.
        """

        pass

    def on_task_start(self, task: WorkflowTask, ctx: TaskContext):
        """
        Called before each task starts execution.

        This hook is invoked immediately before a task's `execute` method
        is called.

        Args:
            task (WorkflowTask): The task that is about to be executed.
            ctx (TaskContext): The context of the workflow run.
        """

        pass

    def on_task_end(self, task: WorkflowTask, ctx: TaskContext):
        """
        Called after each task completes execution.

        This hook is invoked immediately after a task's `execute` method
        terminates.

        Args:
            task (WorkflowTask): The task that has just completed execution.
            ctx (TaskContext): The context of the workflow run.
        """

        pass

    def on_lock(self, ctx: WorkflowHookContext):
        """
        Called when the workflow locks.

        This hook is invoked after the workflow enters a locked state.
        A workflow may enter a locked state using the `lock` method
        or the `toggle_lock` method.

        Args:
            ctx (WorkflowHookContext): The context of the workflow run.
        """

        pass

    def on_unlock(self, ctx: WorkflowHookContext):
        """
        Called when the workflow unlocks.

        This hook is invoked after the workflow exits a locked state.
        A workflow may exit a locked state using the `unlock` method
        or the `toggle_lock` method.

        Args:
            ctx (WorkflowHookContext): The context of the workflow run.
        """

        pass

    def on_current_task_change(
        self,
        prev: WorkflowTask | None,
        current: WorkflowTask | None,
        ctx: WorkflowHookContext,
    ):
        """
        Called when the current task changes.

        This hook is invoked whenever the workflow's current task
        pointer changes, regardless of whether the workflow is locked.
        This can occur when:
        - `next` method is called
        - `jump_to` method is called
        - Iteration wraps (looping enabled)
        - The workflow reaches the end (looping disabled)

        Args:
            prev (WorkflowTask | None): The previous current task, or None
            if there was no previous task.
            current (WorkflowTask | None): The current task, or None if the
            workflow is finished.
            ctx (WorkflowHookContext): The context of the workflow run.
        """

        pass
