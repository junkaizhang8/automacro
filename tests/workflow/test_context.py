import threading

import pytest
from conftest import wait_until

from automacro import (
    ExecutionContext,
    InterruptException,
    Task,
    Workflow,
    WorkflowState,
)


def test_check_interrupt_raises_interrupt_exception() -> None:
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
    continue_event = threading.Event()

    class InterruptingTask(Task):
        def step(self, ctx: ExecutionContext) -> bool:
            nonlocal completed

            continue_event.wait()
            ctx.check_interrupt()
            completed = True
            return True

    task = InterruptingTask()
    wf = Workflow(task)
    wf.start()

    wait_until(lambda: wf.state == WorkflowState.RUNNING)

    # Pause the workflow and notify the workflow thread to continue, causing
    # the task to raise an InterruptException when it calls check_interrupt()
    wf.pause()
    continue_event.set()

    wait_until(lambda: wf.state == WorkflowState.PAUSED)
    assert completed is False

    # Now resume it (which should restart the task) and let it complete
    wf.resume()
    wf.join()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert completed is True


def test_wait_in_task() -> None:
    completed = False

    class WaitingTask(Task):
        def step(self, ctx: ExecutionContext) -> bool:
            nonlocal completed

            ctx.wait(0.2)
            completed = True
            return True

    task = WaitingTask()
    wf = Workflow(task)
    wf.start()

    wait_until(lambda: wf.state == WorkflowState.RUNNING)

    # Pause the workflow, which will set the interrupt event and cause the
    # task to raise an InterruptException during the wait
    wf.pause()

    wait_until(lambda: wf.state == WorkflowState.PAUSED)
    assert completed is False

    wf.resume()
    wf.join()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert completed is True


def test_sleep_in_task() -> None:
    completed = False

    class SleepingTask(Task):
        def step(self, ctx: ExecutionContext) -> bool:
            nonlocal completed

            ctx.sleep(0.2)
            completed = True
            return True

    task = SleepingTask()
    wf = Workflow(task)
    wf.start()

    wait_until(lambda: wf.state == WorkflowState.RUNNING)

    # Pause the workflow, which should have no effect on the sleep since
    # it is not interruptible
    wf.pause()
    wf.join()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert completed is True
