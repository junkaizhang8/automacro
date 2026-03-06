import pytest
import time
from typing_extensions import override

from automacro import (
    ExecutionContext,
    InterruptException,
    Task,
    Workflow,
    WorkflowState,
)


def test_execution_context_check_interrupt() -> None:
    ctx = ExecutionContext()
    assert not ctx._interrupt_event.is_set()
    # No interrupt, so this should not raise
    ctx.check_interrupt()

    ctx._pause()
    assert ctx._interrupt_event.is_set()
    # Interrupt is set, so this should raise an InterruptException
    with pytest.raises(InterruptException):
        ctx.check_interrupt()

    ctx._resume()
    assert not ctx._interrupt_event.is_set()
    # No interrupt, so this should not raise
    ctx.check_interrupt()


def test_check_interrupt_in_task() -> None:
    completed = False

    class InterruptingTask(Task):
        @override
        def step(self, ctx: ExecutionContext) -> bool:
            nonlocal completed

            time.sleep(0.2)
            ctx.check_interrupt()
            completed = True
            return True

    task = InterruptingTask()
    wf = Workflow(task)
    wf.start()

    # Let the task start and execute for a bit
    time.sleep(0.1)

    # Pause the workflow, which will set the interrupt event and cause the
    # task to raise an InterruptException when it calls check_interrupt()
    wf.pause()

    # Wait a moment to ensure the interrupt is processed
    time.sleep(0.2)

    assert wf.state == WorkflowState.PAUSED
    assert completed is False

    # Now resume it (which should restart the task) and let it complete
    wf.resume()

    # Give it a moment to start and execute the step
    time.sleep(0.3)

    wf.join()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert completed is True


def test_wait_in_task() -> None:
    completed = False

    class WaitingTask(Task):
        @override
        def step(self, ctx: ExecutionContext) -> bool:
            nonlocal completed

            ctx.wait(0.2)
            completed = True
            return True

    task = WaitingTask()
    wf = Workflow(task)
    wf.start()

    time.sleep(0.1)

    # Pause the workflow, which will set the interrupt event and cause the
    # task to raise an InterruptException during the wait
    wf.pause()

    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert completed is False

    wf.resume()

    time.sleep(0.3)

    wf.join()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert completed is True


def test_sleep_in_task() -> None:
    completed = False

    class SleepingTask(Task):
        @override
        def step(self, ctx: ExecutionContext) -> bool:
            nonlocal completed

            ctx.sleep(0.2)
            completed = True
            return True

    task = SleepingTask()
    wf = Workflow(task)
    wf.start()

    time.sleep(0.1)

    # Pause the workflow, which should have no effect on the sleep since
    # it is not interruptible
    wf.pause()

    time.sleep(0.2)

    wf.join()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert completed is True
