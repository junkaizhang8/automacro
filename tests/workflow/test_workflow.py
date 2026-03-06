import threading
import time

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


def test_workflow_single_task() -> None:
    task = MockTask(steps_to_complete=3)
    wf = Workflow(task)

    assert wf.state == WorkflowState.NOT_RUNNING
    wf.run()
    assert wf.state == WorkflowState.NOT_RUNNING
    assert task.steps_count == 3


def test_workflow_node_chain() -> None:
    results = []

    def step1() -> None:
        results.append(1)

    def step2() -> None:
        results.append(2)

    root = NodeChain(step1, step2)
    wf = Workflow(root)

    assert wf.state == WorkflowState.NOT_RUNNING
    wf.run()
    assert wf.state == WorkflowState.NOT_RUNNING
    assert results == [1, 2]


def test_workflow_nested_node_chain() -> None:
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


def test_workflow_start_already_running() -> None:
    # Test that calling start() while already running doesn't spawn extra threads
    def slow_task() -> None:
        time.sleep(0.3)

    wf = Workflow(NodeChain(slow_task))
    wf.start()

    original_thread = wf._thread

    # Call start again
    wf.start()
    assert wf._thread is original_thread

    wf.join()


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

    wf.start()
    wf.join()
    assert wf.state == WorkflowState.NOT_RUNNING
    assert task.executed is True


def test_workflow_pause_resume() -> None:
    results = []

    continue_event = threading.Event()

    def s1() -> None:
        continue_event.wait()
        results.append(1)

    def s2() -> None:
        results.append(2)

    root = NodeChain(s1, s2)
    wf = Workflow(root)

    wf.start()

    # Give it a moment to start
    time.sleep(0.1)

    assert wf.state == WorkflowState.RUNNING

    # Without checking for interrupts in s1, the workflow
    # only pauses after s1 completes
    wf.pause()

    # Allow the first step to complete
    continue_event.set()

    # Give it a moment to pause
    time.sleep(0.2)

    assert wf.state == WorkflowState.PAUSED
    assert results == [1]

    wf.resume()

    # Give it a moment to resume and finish
    time.sleep(0.2)

    assert wf.state == WorkflowState.NOT_RUNNING
    assert results == [1, 2]


def test_workflow_start_paused() -> None:
    def dummy() -> None:
        pass

    wf = Workflow(NodeChain(dummy))

    wf.start(start_paused=True)

    # Give it a moment to start
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED

    wf.stop()
    wf.join()
