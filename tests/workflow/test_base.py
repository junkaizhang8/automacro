import pytest
from typing_extensions import override

from automacro import (
    ExecutionContext,
    Node,
    NodeChain,
    Task,
    TaskCallable,
    coerce_to_node,
)


def test_coerce_to_node_with_node() -> None:
    class Dummy(Node):
        @override
        def _step(self, ctx: ExecutionContext) -> Node | None:
            return None

    node = Dummy()
    assert coerce_to_node(node) is node


def test_coerce_to_node_with_callable() -> None:
    def dummy_func() -> None:
        pass

    node = coerce_to_node(dummy_func)
    assert isinstance(node, TaskCallable)
    assert node.name == "dummy_func"


def test_task_callable_execution() -> None:
    called = False

    def dummy_func() -> None:
        nonlocal called
        called = True

    node = TaskCallable(dummy_func)
    ctx = ExecutionContext()

    # TaskCallable should complete in one step
    next_node = node._step(ctx)
    assert called is True
    assert next_node is None


class MockTask(Task):
    def __init__(self, steps_to_complete: int = 1, name: str | None = None) -> None:
        super().__init__(name=name)
        self.steps_to_complete = steps_to_complete
        self.steps_count = 0
        self.entered = False
        self.exited = False

    @override
    def step(self, ctx: ExecutionContext) -> bool:
        self.steps_count += 1
        return self.steps_count >= self.steps_to_complete

    @override
    def on_enter(self) -> None:
        self.entered = True

    @override
    def on_exit(self) -> None:
        self.exited = True


def test_task_lifecycle() -> None:
    task = MockTask(steps_to_complete=2)
    ctx = ExecutionContext()

    # First step
    next_node = task._step(ctx)
    assert next_node is task
    assert task.entered is True
    assert task.steps_count == 1
    assert task.exited is False

    # Second step (completes)
    next_node = task._step(ctx)
    assert next_node is None
    assert task.steps_count == 2
    assert task.exited is True


def test_node_chain_execution() -> None:
    task1 = MockTask(name="task1")
    task2 = MockTask(name="task2")
    chain = NodeChain(task1, task2)
    ctx = ExecutionContext()

    # First step of chain returns first node
    node1 = chain._step(ctx)
    assert node1 is task1

    # Second step of chain returns second node
    node2 = chain._step(ctx)
    assert node2 is task2

    # Third step of chain returns None
    node3 = chain._step(ctx)
    assert node3 is None


def test_node_chain_operator() -> None:
    task1 = MockTask(name="task1")
    task2 = MockTask(name="task2")

    chain = task1 | task2
    assert isinstance(chain, NodeChain)
    assert len(chain.nodes) == 2
    assert chain.nodes[0] is task1
    assert chain.nodes[1] is task2


def test_node_chain_with_callable_operator() -> None:
    task1 = MockTask(name="task1")

    def task2_func() -> None:
        pass

    chain = task1 | task2_func
    assert isinstance(chain, NodeChain)
    assert len(chain.nodes) == 2
    assert chain.nodes[0] is task1
    assert isinstance(chain.nodes[1], TaskCallable)


def test_node_chain_or_operator_associativity() -> None:
    def s1() -> None:
        pass

    def s2() -> None:
        pass

    def s3() -> None:
        pass

    # (s1 | s2) | s3
    chain = (coerce_to_node(s1) | s2) | s3
    assert len(chain.nodes) == 3

    # s1 | (s2 | s3)
    chain = s1 | (coerce_to_node(s2) | s3)
    assert len(chain.nodes) == 3


def test_node_chain_ror_operator() -> None:
    def task1_func() -> None:
        pass

    task2 = MockTask(name="task2")

    chain = task1_func | task2
    assert isinstance(chain, NodeChain)
    assert len(chain.nodes) == 2
    assert isinstance(chain.nodes[0], TaskCallable)
    assert chain.nodes[1] is task2


def test_node_chain_flattening() -> None:
    task1 = MockTask(name="task1")
    task2 = MockTask(name="task2")
    task3 = MockTask(name="task3")

    chain1 = task1 | task2
    chain2 = chain1 | task3

    assert len(chain2.nodes) == 3
    assert chain2.nodes[0] is task1
    assert chain2.nodes[1] is task2
    assert chain2.nodes[2] is task3

    chain3 = task1 | (task2 | task3)
    assert len(chain3.nodes) == 3


def test_node_run_with_single_node() -> None:
    called = False

    def func() -> None:
        nonlocal called
        called = True

    node = coerce_to_node(func)
    node.run()

    assert called is True


def test_node_run_with_node_chain() -> None:
    results = []

    def s1() -> None:
        results.append(1)

    def s2() -> None:
        results.append(2)

    chain = coerce_to_node(s1) | s2
    chain.run()

    assert results == [1, 2]
