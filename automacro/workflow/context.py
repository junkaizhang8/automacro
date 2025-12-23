from dataclasses import dataclass, field
from typing import Any, MutableMapping


@dataclass(frozen=True)
class WorkflowMeta:
    """
    Metadata for a workflow run.
    """

    workflow_name: str
    run_id: str
    started_at: float
    loop: bool


@dataclass
class WorkflowRuntime:
    """
    Runtime information of a workflow run.
    """

    current_task_idx: int | None = 0
    prev_task_idx: int | None = None
    iteration: int = 0
    tasks_executed: int = 0
    is_locked: bool = False


@dataclass
class WorkflowContext:
    """
    Workflow-owned context information of a workflow run.

    This class is intended for internal use within a workflow. It should not
    be used directly by tasks or hooks. Instead, tasks and hooks should use
    the `TaskContext` and `WorkflowHookContext` classes, which provide
    a restricted view of the workflow context.
    """

    # Metadata (read-only)
    meta: WorkflowMeta

    # Runtime information
    runtime: WorkflowRuntime = field(default_factory=WorkflowRuntime)

    # Persistent data across workflow loops
    persistent: dict[str, Any] = field(default_factory=dict)

    # Resettable data for each workflow loop iteration
    transient: dict[str, Any] = field(default_factory=dict)

    def reset_transient(self):
        """
        Reset the transient (loop-scoped) state.
        """

        self.transient.clear()

    def reset_all(self):
        """
        Reset all mutable context state.
        """

        self.runtime = WorkflowRuntime()
        self.persistent.clear()
        self.transient.clear()


class RuntimeView:
    """
    A read-only view of the runtime state of a workflow run.
    """

    __slots__ = ("_ctx",)

    def __init__(self, ctx: WorkflowContext):
        self._ctx = ctx

    @property
    def current_task_idx(self) -> int | None:
        return self._ctx.runtime.current_task_idx

    @property
    def prev_task_idx(self) -> int | None:
        return self._ctx.runtime.prev_task_idx

    @property
    def iteration(self) -> int:
        return self._ctx.runtime.iteration

    @property
    def tasks_executed(self) -> int:
        return self._ctx.runtime.tasks_executed

    @property
    def is_first_iteration(self) -> bool:
        return self._ctx.runtime.iteration == 0

    @property
    def is_locked(self) -> bool:
        return self._ctx.runtime.is_locked


class _ExecutionContextView:
    """
    Highly restricted view of the workflow execution context.

    An internal class not intended for public use.
    """

    __slots__ = ("_ctx", "_runtime_view")

    def __init__(self, ctx: WorkflowContext):
        """
        Initialize the TaskContext.

        Args:
            ctx (WorkflowContext): The underlying workflow context.
        """

        self._ctx = ctx
        self._runtime_view = RuntimeView(ctx)

    @property
    def meta(self) -> WorkflowMeta:
        return self._ctx.meta

    @property
    def runtime(self) -> RuntimeView:
        return self._runtime_view

    @property
    def persistent(self) -> MutableMapping[str, Any]:
        return self._ctx.persistent

    @property
    def transient(self) -> MutableMapping[str, Any]:
        return self._ctx.transient


class TaskContext(_ExecutionContextView):
    """
    Context information exposed to each workflow task during execution.

    Tasks may observe workflow metadata and runtime state, and read/write
    persistent and transient data.
    """

    pass


class WorkflowHookContext(_ExecutionContextView):
    """
    Context information exposed to workflow hooks during execution.

    Hooks may observe workflow metadata and runtime state, and read/write
    persistent and transient data.
    """

    pass
