import pytest
from typing_extensions import override

from automacro import (
    ExecutionContext,
    NodeChain,
    Task,
    Workflow,
    WorkflowState,
)


class MockTask(Task):
    def __init__(self, steps_to_complete: int = 1, name: str | None = None) -> None:
        super().__init__(name=name)
        self.steps_to_complete = steps_to_complete
        self.steps_count = 0

    @override
    def step(self, ctx: ExecutionContext) -> bool:
        self.steps_count += 1
        return self.steps_count >= self.steps_to_complete


def test_workflow_execution() -> None:
    results = []

    def step1() -> None:
        results.append(1)

    def step2() -> None:
        results.append(2)

    root = NodeChain(step1, step2)
    wf = Workflow(root)

    assert wf.status == WorkflowState.NOT_RUNNING
    wf.run()
    assert wf.status == WorkflowState.NOT_RUNNING
    assert results == [1, 2]


def test_workflow_stop() -> None:
    class StopTask(Task):
        def __init__(self) -> None:
            super().__init__()
            self.wf: Workflow | None = None
            self.executed = False

        @override
        def step(self, ctx: ExecutionContext) -> bool:
            self.executed = True
            if self.wf:
                self.wf.stop()
            return False

    task = StopTask()
    wf = Workflow(task)
    task.wf = wf

    wf.run()
    assert wf.status == WorkflowState.NOT_RUNNING
    assert task.executed is True


def test_nested_node_chain() -> None:
    results = []

    def s1() -> None:
        results.append(1)

    def s2() -> None:
        results.append(2)

    def s3() -> None:
        results.append(3)

    chain1 = NodeChain(s1, s2)
    chain2 = NodeChain(chain1, s3)

    wf = Workflow(chain2)
    wf.run()

    assert results == [1, 2, 3]
