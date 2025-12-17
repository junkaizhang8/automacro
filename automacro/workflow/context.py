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

    iteration: int = 0
    tasks_executed: int = 0


@dataclass
class WorkflowContext:
    """
    Workflow-owned context information of a workflow run.
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


class WorkflowRuntimeView:
    """
    A read-only view of the runtime information of a workflow run.
    """

    __slots__ = ("_ctx",)

    def __init__(self, ctx: WorkflowContext):
        self._ctx = ctx

    @property
    def iteration(self) -> int:
        return self._ctx.runtime.iteration

    @property
    def tasks_executed(self) -> int:
        return self._ctx.runtime.tasks_executed

    @property
    def is_first_iteration(self) -> bool:
        return self._ctx.runtime.iteration == 0


class TaskContext:
    """
    Context information for a workflow run exposed to tasks.
    """

    def __init__(self, ctx: WorkflowContext):
        """
        Initialize the TaskContext.

        Args:
            ctx (WorkflowContext): The underlying workflow context.
        """

        self._ctx = ctx
        self._runtime_view = WorkflowRuntimeView(ctx)

    @property
    def meta(self) -> WorkflowMeta:
        return self._ctx.meta

    @property
    def runtime(self) -> WorkflowRuntimeView:
        return self._runtime_view

    @property
    def persistent(self) -> MutableMapping[str, Any]:
        return self._ctx.persistent

    @property
    def transient(self) -> MutableMapping[str, Any]:
        return self._ctx.transient
