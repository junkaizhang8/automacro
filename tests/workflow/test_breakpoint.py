import pytest
from conftest import wait_until

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
    wait_until(lambda: wf.state == WorkflowState.PAUSED)
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
    wait_until(lambda: wf.state == WorkflowState.PAUSED)
    wf.resume()

    # Wait for second breakpoint
    wait_until(lambda: wf.state == WorkflowState.PAUSED)
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
    wait_until(lambda: wf.state == WorkflowState.PAUSED)
    wf.resume()

    # Wait for second breakpoint
    wait_until(lambda: wf.state == WorkflowState.PAUSED)
    assert results == [1]

    wf.resume()
    wf.join()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert results == [1, 2]


def test_breakpoint_as_first_node_in_chain() -> None:
    results = []

    chain = bp() | (lambda: results.append(1)) | (lambda: results.append(2))

    wf = Workflow(chain)

    wf.start()

    # Wait for breakpoint
    wait_until(lambda: wf.state == WorkflowState.PAUSED)
    assert results == []

    wf.resume()
    wf.join()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert results == [1, 2]


def test_breakpoint_as_last_node_in_chain() -> None:
    results = []

    chain = (lambda: results.append(1)) | ((lambda: results.append(2)) | bp())

    wf = Workflow(chain)

    wf.start()

    # Wait for it to hit the breakpoint
    wait_until(lambda: wf.state == WorkflowState.PAUSED)
    assert results == [1, 2]

    wf.resume()
    wf.join()

    assert wf.state == WorkflowState.NOT_RUNNING
    assert results == [1, 2]


def test_breakpoint_as_only_node() -> None:
    wf = Workflow(bp())

    wf.start()

    wait_until(lambda: wf.state == WorkflowState.PAUSED)

    wf.resume()
    wf.join()

    assert wf.state == WorkflowState.NOT_RUNNING
