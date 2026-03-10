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
    bp,
    coerce_to_node,
    if_,
    while_,
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

    def step1() -> None:
        continue_event.wait()
        results.append(1)

    def step2() -> None:
        results.append(2)

    root = NodeChain(step1, step2)
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


def test_workflow_restart() -> None:
    results = []

    def step1() -> None:
        results.append(1)

    def step2() -> None:
        results.append(2)

    chain = step1 | bp() | step2
    wf = Workflow(chain)

    wf.start()
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert results == [1]

    wf.restart()
    wf.resume()

    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert results == [1, 1]

    wf.resume()
    time.sleep(0.1)

    wf.join()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert results == [1, 1, 2]


def test_workflow_step_in_empty() -> None:
    wf = Workflow(NodeChain())

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED

    wf.step_in()

    assert wf.state == WorkflowState.NOT_RUNNING

    wf.join()


def test_workflow_step_in_lambda() -> None:
    results = []

    def step() -> None:
        results.append(1)

    wf = Workflow(coerce_to_node(step))

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert results == []

    wf.step_in()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert results == [1]

    wf.join()


def test_workflow_step_in_lambda_chain() -> None:
    results = []

    def step1() -> None:
        results.append(1)

    def step2() -> None:
        results.append(2)

    chain = coerce_to_node(step1) | step2
    wf = Workflow(chain)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert results == []

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert results == [1]

    wf.step_in()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert results == [1, 2]

    wf.join()


def test_workflow_step_in_task() -> None:
    task = MockTask(steps_to_complete=2)
    wf = Workflow(task)

    wf.start(start_paused=True)

    assert wf.state == WorkflowState.PAUSED
    assert task.steps_count == 0

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert task.steps_count == 1

    wf.step_in()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert task.steps_count == 2

    wf.join()


def test_workflow_step_in_task_chain() -> None:
    task1 = MockTask(steps_to_complete=2)
    task2 = MockTask(steps_to_complete=1)
    chain = task1 | task2
    wf = Workflow(chain)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert task1.steps_count == 0
    assert task2.steps_count == 0

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert task1.steps_count == 1
    assert task2.steps_count == 0

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert task1.steps_count == 2
    assert task2.steps_count == 0

    wf.step_in()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert task1.steps_count == 2
    assert task2.steps_count == 1

    wf.join()


def test_workflow_step_in_if_true() -> None:
    condition_called = False
    results = []

    def cond() -> bool:
        nonlocal condition_called
        condition_called = True
        return True

    def step1() -> None:
        results.append(1)

    def step2() -> None:
        results.append(2)

    node = if_(cond).then_(step1).else_(step2)
    wf = Workflow(node)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert condition_called is False
    assert results == []

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert condition_called is True
    assert results == []

    wf.step_in()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert condition_called is True
    assert results == [1]

    wf.join()


def test_workflow_step_in_if_false() -> None:
    condition_called = False
    results = []

    def cond() -> bool:
        nonlocal condition_called
        condition_called = True
        return False

    def step1() -> None:
        results.append(1)

    def step2() -> None:
        results.append(2)

    node = if_(cond).then_(step1).else_(step2)
    wf = Workflow(node)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert condition_called is False
    assert results == []

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert condition_called is True
    assert results == []

    wf.step_in()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert condition_called is True
    assert results == [2]

    wf.join()


def test_workflow_step_in_if_elif_else() -> None:
    condition1_called = False
    condition2_called = False
    results = []

    def cond1() -> bool:
        nonlocal condition1_called
        condition1_called = True
        return False

    def cond2() -> bool:
        nonlocal condition2_called
        condition2_called = True
        return True

    def step1() -> None:
        results.append(1)

    def step2() -> None:
        results.append(2)

    def step3() -> None:
        results.append(3)

    node = if_(cond1).then_(step1).elif_(cond2).then_(step2).else_(step3)
    wf = Workflow(node)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert condition1_called is False
    assert condition2_called is False
    assert results == []

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert condition1_called is True
    assert condition2_called is False
    assert results == []

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert condition1_called is True
    assert condition2_called is True
    assert results == []

    wf.step_in()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert condition1_called is True
    assert condition2_called is True
    assert results == [2]

    wf.join()


def test_workflow_step_in_while() -> None:
    condition_call_counter = 0
    i = 0

    def cond() -> bool:
        nonlocal condition_call_counter
        condition_call_counter += 1
        return i < 2

    def body() -> None:
        nonlocal i
        i += 1

    node = while_(cond).do_(body)
    wf = Workflow(node)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert condition_call_counter == 0
    assert i == 0

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert condition_call_counter == 1
    assert i == 0

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert condition_call_counter == 1
    assert i == 1

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert condition_call_counter == 2
    assert i == 1

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert condition_call_counter == 2
    assert i == 2

    wf.step_in()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert condition_call_counter == 3
    assert i == 2

    wf.join()


def test_workflow_step_in_while_zero_iterations() -> None:
    condition_call_counter = 0
    body_called = False

    def cond() -> bool:
        nonlocal condition_call_counter
        condition_call_counter += 1
        return False

    def body() -> None:
        nonlocal body_called
        body_called = True

    node = while_(cond).do_(body)
    wf = Workflow(node)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert condition_call_counter == 0
    assert body_called is False

    wf.step_in()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert condition_call_counter == 1
    assert body_called is False

    wf.join()


def test_workflow_step_in_nested_control_flow() -> None:
    results = []
    start_called = False
    end_called = False
    while_cond_counter = 0
    if_cond_counter = 0
    i = 0

    def start() -> None:
        nonlocal start_called
        start_called = True

    def end() -> None:
        nonlocal end_called
        end_called = True

    def cond_while() -> bool:
        nonlocal while_cond_counter
        while_cond_counter += 1
        return i < 2

    def cond_if() -> bool:
        nonlocal if_cond_counter
        if_cond_counter += 1
        return i == 0

    def incr() -> None:
        nonlocal i
        i += 1

    inner_if = (
        if_(cond_if).then_(lambda: results.append(0)).else_(lambda: results.append(1))
    )

    """
    start()
    while i < 2:
      if i == 0:
        append "zero"
      else:
        append "one"
      i += 1
    end()
    """

    chain = start | while_(cond_while).do_(inner_if | incr) | end
    wf = Workflow(chain)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert results == []
    assert start_called is False
    assert end_called is False
    assert while_cond_counter == 0
    assert if_cond_counter == 0
    assert i == 0

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert results == []
    assert start_called is True
    assert end_called is False
    assert while_cond_counter == 0
    assert if_cond_counter == 0
    assert i == 0

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert results == []
    assert start_called is True
    assert end_called is False
    assert while_cond_counter == 1
    assert if_cond_counter == 0
    assert i == 0

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert results == []
    assert start_called is True
    assert end_called is False
    assert while_cond_counter == 1
    assert if_cond_counter == 1
    assert i == 0

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert results == [0]
    assert start_called is True
    assert end_called is False
    assert while_cond_counter == 1
    assert if_cond_counter == 1
    assert i == 0

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert results == [0]
    assert start_called is True
    assert end_called is False
    assert while_cond_counter == 1
    assert if_cond_counter == 1
    assert i == 1

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert results == [0]
    assert start_called is True
    assert end_called is False
    assert while_cond_counter == 2
    assert if_cond_counter == 1
    assert i == 1

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert results == [0]
    assert start_called is True
    assert end_called is False
    assert while_cond_counter == 2
    assert if_cond_counter == 2
    assert i == 1

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert results == [0, 1]
    assert start_called is True
    assert end_called is False
    assert while_cond_counter == 2
    assert if_cond_counter == 2
    assert i == 1

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert results == [0, 1]
    assert while_cond_counter == 2
    assert start_called is True
    assert end_called is False
    assert if_cond_counter == 2
    assert i == 2

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert results == [0, 1]
    assert start_called is True
    assert end_called is False
    assert while_cond_counter == 3
    assert if_cond_counter == 2
    assert i == 2

    wf.step_in()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert results == [0, 1]
    assert start_called is True
    assert end_called is True
    assert while_cond_counter == 3
    assert if_cond_counter == 2
    assert i == 2

    wf.join()


def test_workflow_step_over_empty() -> None:
    wf = Workflow(NodeChain())

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED

    wf.step_over()

    assert wf.state == WorkflowState.NOT_RUNNING

    wf.join()


def test_workflow_step_over_lambda() -> None:
    results = []

    def step() -> None:
        results.append(1)

    wf = Workflow(coerce_to_node(step))

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert results == []

    wf.step_over()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert results == [1]

    wf.join()


def test_workflow_step_over_lambda_chain() -> None:
    results = []

    def step1() -> None:
        results.append(1)

    def step2() -> None:
        results.append(2)

    chain = coerce_to_node(step1) | step2
    wf = Workflow(chain)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert results == []

    wf.step_over()

    assert wf.state == WorkflowState.PAUSED
    assert results == [1]

    wf.step_over()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert results == [1, 2]

    wf.join()


def test_workflow_step_over_task() -> None:
    task = MockTask(steps_to_complete=2)
    wf = Workflow(task)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert task.steps_count == 0

    wf.step_over()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert task.steps_count == 2

    wf.join()


def test_workflow_step_over_task_chain() -> None:
    task1 = MockTask(steps_to_complete=2)
    task2 = MockTask(steps_to_complete=1)
    chain = task1 | task2
    wf = Workflow(chain)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert task1.steps_count == 0
    assert task2.steps_count == 0

    wf.step_over()

    assert wf.state == WorkflowState.PAUSED
    assert task1.steps_count == 2
    assert task2.steps_count == 0

    wf.step_over()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert task1.steps_count == 2
    assert task2.steps_count == 1

    wf.join()


def test_workflow_step_over_if_true() -> None:
    condition_called = False
    results = []

    def cond() -> bool:
        nonlocal condition_called
        condition_called = True
        return True

    def step1() -> None:
        results.append(1)

    def step2() -> None:
        results.append(2)

    node = if_(cond).then_(step1).else_(step2)
    wf = Workflow(node)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert condition_called is False
    assert results == []

    wf.step_over()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert condition_called is True
    assert results == [1]

    wf.join()


def test_workflow_step_over_if_false() -> None:
    condition_called = False
    results = []

    def cond() -> bool:
        nonlocal condition_called
        condition_called = True
        return False

    def step1() -> None:
        results.append(1)

    def step2() -> None:
        results.append(2)

    node = if_(cond).then_(step1).else_(step2)
    wf = Workflow(node)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert condition_called is False
    assert results == []

    wf.step_over()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert condition_called is True
    assert results == [2]

    wf.join()


def test_workflow_step_over_if_elif_else() -> None:
    condition1_called = False
    condition2_called = False
    results = []

    def cond1() -> bool:
        nonlocal condition1_called
        condition1_called = True
        return False

    def cond2() -> bool:
        nonlocal condition2_called
        condition2_called = True
        return True

    def step1() -> None:
        results.append(1)

    def step2() -> None:
        results.append(2)

    def step3() -> None:
        results.append(3)

    node = if_(cond1).then_(step1).elif_(cond2).then_(step2).else_(step3)
    wf = Workflow(node)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert condition1_called is False
    assert condition2_called is False
    assert results == []

    wf.step_over()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert condition1_called is True
    assert condition2_called is True
    assert results == [2]

    wf.join()


def test_workflow_step_over_while() -> None:
    condition_call_counter = 0
    i = 0

    def cond() -> bool:
        nonlocal condition_call_counter
        condition_call_counter += 1
        return i < 2

    def body() -> None:
        nonlocal i
        i += 1

    node = while_(cond).do_(body)
    wf = Workflow(node)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert condition_call_counter == 0
    assert i == 0

    wf.step_over()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert condition_call_counter == 3
    assert i == 2

    wf.join()


def test_workflow_step_over_while_zero_iterations() -> None:
    condition_call_counter = 0
    body_called = False

    def cond() -> bool:
        nonlocal condition_call_counter
        condition_call_counter += 1
        return False

    def body() -> None:
        nonlocal body_called
        body_called = True

    node = while_(cond).do_(body)
    wf = Workflow(node)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert condition_call_counter == 0
    assert body_called is False

    wf.step_over()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert condition_call_counter == 1
    assert body_called is False

    wf.join()


def test_workflow_step_over_nested_control_flow() -> None:
    results = []
    start_called = False
    end_called = False
    while_cond_counter = 0
    if_cond_counter = 0
    i = 0

    def start() -> None:
        nonlocal start_called
        start_called = True

    def end() -> None:
        nonlocal end_called
        end_called = True

    def cond_while() -> bool:
        nonlocal while_cond_counter
        while_cond_counter += 1
        return i < 2

    def cond_if() -> bool:
        nonlocal if_cond_counter
        if_cond_counter += 1
        return i == 0

    def incr() -> None:
        nonlocal i
        i += 1

    inner_if = (
        if_(cond_if).then_(lambda: results.append(0)).else_(lambda: results.append(1))
    )

    """
    start()
    while i < 2:
      if i == 0:
        append "zero"
      else:
        append "one"
      i += 1
    end()
    """

    chain = start | while_(cond_while).do_(inner_if | incr) | end
    wf = Workflow(chain)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert results == []
    assert start_called is False
    assert end_called is False
    assert while_cond_counter == 0
    assert if_cond_counter == 0
    assert i == 0

    wf.step_over()

    assert wf.state == WorkflowState.PAUSED
    assert results == []
    assert start_called is True
    assert end_called is False
    assert while_cond_counter == 0
    assert if_cond_counter == 0
    assert i == 0

    wf.step_over()

    assert wf.state == WorkflowState.PAUSED
    assert results == [0, 1]
    assert start_called is True
    assert end_called is False
    assert while_cond_counter == 3
    assert if_cond_counter == 2
    assert i == 2

    wf.step_over()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert results == [0, 1]
    assert start_called is True
    assert end_called is True
    assert while_cond_counter == 3
    assert if_cond_counter == 2
    assert i == 2

    wf.join()


def test_workflow_step_out_empty() -> None:
    wf = Workflow(NodeChain())

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED

    wf.step_out()

    assert wf.state == WorkflowState.NOT_RUNNING

    wf.join()


def test_workflow_step_out_lambda() -> None:
    results = []

    def step() -> None:
        results.append(1)

    wf = Workflow(coerce_to_node(step))

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert results == []

    wf.step_out()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert results == [1]

    wf.join()


def test_workflow_step_out_lambda_chain() -> None:
    results = []

    def step1() -> None:
        results.append(1)

    def step2() -> None:
        results.append(2)

    chain = coerce_to_node(step1) | step2
    wf = Workflow(chain)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert results == []

    wf.step_out()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert results == [1, 2]

    wf.join()


def test_workflow_step_out_task() -> None:
    task = MockTask(steps_to_complete=2)
    wf = Workflow(task)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert task.steps_count == 0

    wf.step_out()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert task.steps_count == 2

    wf.join()


def test_workflow_step_out_task_chain() -> None:
    task1 = MockTask(steps_to_complete=2)
    task2 = MockTask(steps_to_complete=1)
    chain = task1 | task2
    wf = Workflow(chain)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert task1.steps_count == 0
    assert task2.steps_count == 0

    wf.step_out()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert task1.steps_count == 2
    assert task2.steps_count == 1

    wf.join()


def test_workflow_step_out_if_true() -> None:
    condition_called = False
    results = []

    def cond() -> bool:
        nonlocal condition_called
        condition_called = True
        return True

    def step1() -> None:
        results.append(1)

    def step2() -> None:
        results.append(2)

    node = if_(cond).then_(step1).else_(step2)
    wf = Workflow(node)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert condition_called is False
    assert results == []

    wf.step_out()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert condition_called is True
    assert results == [1]

    wf.join()


def test_workflow_step_out_if_false() -> None:
    condition_called = False
    results = []

    def cond() -> bool:
        nonlocal condition_called
        condition_called = True
        return False

    def step1() -> None:
        results.append(1)

    def step2() -> None:
        results.append(2)

    node = if_(cond).then_(step1).else_(step2)
    wf = Workflow(node)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert condition_called is False
    assert results == []

    wf.step_out()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert condition_called is True
    assert results == [2]

    wf.join()


def test_workflow_step_out_if_elif_else() -> None:
    condition1_called = False
    condition2_called = False
    results = []

    def cond1() -> bool:
        nonlocal condition1_called
        condition1_called = True
        return False

    def cond2() -> bool:
        nonlocal condition2_called
        condition2_called = True
        return True

    def step1() -> None:
        results.append(1)

    def step2() -> None:
        results.append(2)

    def step3() -> None:
        results.append(3)

    node = if_(cond1).then_(step1).elif_(cond2).then_(step2).else_(step3)
    wf = Workflow(node)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert condition1_called is False
    assert condition2_called is False
    assert results == []

    wf.step_out()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert condition1_called is True
    assert condition2_called is True
    assert results == [2]

    wf.join()


def test_workflow_step_out_if_body() -> None:
    condition_called = False
    results = []

    def cond() -> bool:
        nonlocal condition_called
        condition_called = True
        return True

    def s1() -> None:
        results.append(1)

    def s2() -> None:
        results.append(2)

    def s3() -> None:
        results.append(3)

    def s4() -> None:
        results.append(4)

    node = if_(cond).then_(coerce_to_node(s1) | s2 | s3).else_(s4)
    wf = Workflow(node)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert condition_called is False
    assert results == []

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert condition_called is True
    assert results == []

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert condition_called is True
    assert results == [1]

    wf.step_out()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert condition_called is True
    assert results == [1, 2, 3]

    wf.join()


def test_workflow_step_out_while() -> None:
    condition_call_counter = 0
    i = 0

    def cond() -> bool:
        nonlocal condition_call_counter
        condition_call_counter += 1
        return i < 2

    def body() -> None:
        nonlocal i
        i += 1

    node = while_(cond).do_(body)
    wf = Workflow(node)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert condition_call_counter == 0
    assert i == 0

    wf.step_out()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert condition_call_counter == 3
    assert i == 2

    wf.join()


def test_workflow_step_out_while_zero_iterations() -> None:
    condition_call_counter = 0
    body_called = False

    def cond() -> bool:
        nonlocal condition_call_counter
        condition_call_counter += 1
        return False

    def body() -> None:
        nonlocal body_called
        body_called = True

    node = while_(cond).do_(body)
    wf = Workflow(node)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert condition_call_counter == 0
    assert body_called is False

    wf.step_out()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert condition_call_counter == 1
    assert body_called is False

    wf.join()


def test_workflow_step_out_while_body() -> None:
    condition_call_counter = 0
    i = 0

    def cond() -> bool:
        nonlocal condition_call_counter
        condition_call_counter += 1
        return i < 6

    def s1() -> None:
        nonlocal i
        i += 1

    node = while_(cond).do_(coerce_to_node(s1) | s1 | s1)
    wf = Workflow(node)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert condition_call_counter == 0
    assert i == 0

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert condition_call_counter == 1
    assert i == 0

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert condition_call_counter == 1
    assert i == 1

    wf.step_out()

    assert wf.state == WorkflowState.PAUSED
    assert condition_call_counter == 1
    assert i == 3

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert condition_call_counter == 2
    assert i == 3

    wf.step_in()

    assert wf.state == WorkflowState.PAUSED
    assert condition_call_counter == 2
    assert i == 4

    wf.step_out()

    assert wf.state == WorkflowState.PAUSED
    assert condition_call_counter == 2
    assert i == 6

    wf.step_in()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert condition_call_counter == 3
    assert i == 6

    wf.join()


def test_workflow_step_out_nested_control_flow() -> None:
    results = []
    start_called = False
    end_called = False
    while_cond_counter = 0
    if_cond_counter = 0
    i = 0

    def start() -> None:
        nonlocal start_called
        start_called = True

    def end() -> None:
        nonlocal end_called
        end_called = True

    def cond_while() -> bool:
        nonlocal while_cond_counter
        while_cond_counter += 1
        return i < 2

    def cond_if() -> bool:
        nonlocal if_cond_counter
        if_cond_counter += 1
        return i == 0

    def incr() -> None:
        nonlocal i
        i += 1

    inner_if = (
        if_(cond_if).then_(lambda: results.append(0)).else_(lambda: results.append(1))
    )

    """
    start()
    while i < 2:
      if i == 0:
        append "zero"
      else:
        append "one"
      i += 1
    end()
    """

    chain = start | while_(cond_while).do_(inner_if | incr) | end
    wf = Workflow(chain)

    wf.start(start_paused=True)
    time.sleep(0.1)

    assert wf.state == WorkflowState.PAUSED
    assert results == []
    assert start_called is False
    assert end_called is False
    assert while_cond_counter == 0
    assert if_cond_counter == 0
    assert i == 0

    wf.step_out()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert results == [0, 1]
    assert start_called is True
    assert end_called is True
    assert while_cond_counter == 3
    assert if_cond_counter == 2
    assert i == 2

    wf.join()
