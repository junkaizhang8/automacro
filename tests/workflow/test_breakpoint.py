import time

import pytest

from automacro import (
    Workflow,
    WorkflowState,
    bp,
)


def test_breakpoint_pauses_workflow() -> None:
    results = []

    def s1() -> None:
        results.append(1)

    def s2() -> None:
        results.append(2)

    chain = s1 | bp() | s2

    wf = Workflow(chain)

    wf.start()

    # Wait for it to hit the breakpoint
    time.sleep(0.1)

    # It should be paused AFTER s1
    assert wf.state == WorkflowState.PAUSED
    assert results == [1]

    wf.resume()

    wf.join()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert results == [1, 2]


def test_multiple_breakpoints() -> None:
    results = []

    chain = (
        (lambda: results.append(1))
        | bp("bp1")
        | (lambda: results.append(2))
        | bp("bp2")
        | (lambda: results.append(3))
    )

    wf = Workflow(chain)

    wf.start()

    # Wait for first breakpoint
    time.sleep(0.1)
    assert wf.state == WorkflowState.PAUSED
    assert results == [1]

    wf.resume()

    # Wait for second breakpoint
    time.sleep(0.1)
    assert wf.state == WorkflowState.PAUSED
    assert results == [1, 2]

    wf.resume()
    wf.join()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert results == [1, 2, 3]


def test_multiple_consecutive_breakpoints() -> None:
    results = []

    chain = (
        (lambda: results.append(1))
        | bp("bp1")
        | bp("bp2")
        | (lambda: results.append(2))
    )

    wf = Workflow(chain)

    wf.start()

    # Wait for first breakpoint
    time.sleep(0.1)
    assert wf.state == WorkflowState.PAUSED
    assert results == [1]

    wf.resume()
    time.sleep(0.1)

    # Wait for second breakpoint
    assert wf.state == WorkflowState.PAUSED
    assert results == [1]

    wf.resume()
    wf.join()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert results == [1, 2]
