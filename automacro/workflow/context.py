from dataclasses import dataclass, field
from typing import Any, MutableMapping, TypeVar, Generic

from automacro.workflow.state import WorkflowState


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

    task_started_at: float | None = None


@dataclass
class WorkflowContext:
    """
    Workflow-owned context information of a workflow run.

    This class is intended for internal use within a workflow. It should not
    be used directly by tasks or hooks. Instead, tasks and hooks should use
    the `TaskContext` and `HookContext` classes, which provide a restricted
    view of the workflow context.
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


class _RuntimeView:
    """
    A generic, read-only view of the runtime state of a workflow run.
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
    def is_first_iteration(self) -> bool:
        return self._ctx.runtime.iteration == 0

    @property
    def tasks_executed(self) -> int:
        return self._ctx.runtime.tasks_executed


class TaskRuntimeView(_RuntimeView):
    """
    A read-only view of the runtime state of a workflow run,
    intended for use within TaskContext.
    """

    @property
    def task_started_at(self) -> float:
        start = self._ctx.runtime.task_started_at

        # Theoretically unreachable due to execution flow.
        # task_started_at should always be initialized for any hooks using
        # a TaskContext parameter
        if start is None:
            raise RuntimeError("task_started_at accessed when no task is running")

        return start


class HookRuntimeView(_RuntimeView):
    """
    A read-only view of the runtime state of a workflow run,
    intended for use within HookContext.
    """

    pass


RuntimeViewT = TypeVar("RuntimeViewT", bound=_RuntimeView, covariant=True)


class _ExecutionContextView(Generic[RuntimeViewT]):
    """
    A generic, highly restricted view of the workflow execution context.
    """

    __slots__ = ("_ctx", "_runtime_view", "_state")

    def __init__(
        self, ctx: WorkflowContext, state: WorkflowState, runtime_view: RuntimeViewT
    ):
        """
        Initialize the TaskContext.

        Args:
            ctx (WorkflowContext): The underlying workflow context.
            state (WorkflowState): The current workflow state.
            runtime_view (RuntimeViewT): The runtime view to expose.
        """

        self._ctx = ctx
        self._state = state
        self._runtime_view = runtime_view

    @property
    def meta(self) -> WorkflowMeta:
        return self._ctx.meta

    @property
    def runtime(self) -> RuntimeViewT:
        return self._runtime_view

    @property
    def persistent(self) -> MutableMapping[str, Any]:
        return self._ctx.persistent

    @property
    def transient(self) -> MutableMapping[str, Any]:
        return self._ctx.transient

    @property
    def state(self) -> WorkflowState:
        return self._state

    @property
    def is_paused(self) -> bool:
        return self._state == WorkflowState.PAUSED


class TaskContext(_ExecutionContextView[TaskRuntimeView]):
    """
    Context information exposed to each workflow task during execution.

    Tasks may observe workflow metadata and runtime state, and read/write
    persistent and transient data.
    """

    def __init__(self, ctx: WorkflowContext, state: WorkflowState):
        """
        Initialize the TaskContext.

        Args:
            ctx (WorkflowContext): The underlying workflow context.
            state (WorkflowState): The current workflow state.
        """

        super().__init__(ctx, state, TaskRuntimeView(ctx))


class HookContext(_ExecutionContextView[HookRuntimeView]):
    """
    Context information exposed to workflow hooks during execution.

    Hooks may observe workflow metadata and runtime state, and read/write
    persistent and transient data.
    """

    def __init__(self, ctx: WorkflowContext, state: WorkflowState):
        """
        Initialize the HookContext.

        Args:
            ctx (WorkflowContext): The underlying workflow context.
            state (WorkflowState): The current workflow state.
        """

        super().__init__(ctx, state, HookRuntimeView(ctx))
