import pytest

from automacro import (
    ExecutionContext,
    Node,
    NodeChain,
    Task,
    TaskCallable,
    coerce_to_node,
)


class DummyTask(Task):
    def __init__(self, steps_to_complete: int = 1, name: str | None = None) -> None:
        super().__init__(name=name)
        self.steps_to_complete = steps_to_complete
        self.step_count = 0
        self.entered = False
        self.exited = False

    def step(self, ctx: ExecutionContext) -> bool:
        self.step_count += 1
        return self.step_count >= self.steps_to_complete

    def on_enter(self) -> None:
        self.entered = True

    def on_exit(self) -> None:
        self.exited = True


def test_coerce_to_node_with_node() -> None:
    class DummyNode(Node):
        def _step(self, ctx: ExecutionContext) -> Node | None:
            return None

    node = DummyNode()
    assert coerce_to_node(node) is node


def test_coerce_to_node_with_callable() -> None:
    def func() -> None:
        pass

    node = coerce_to_node(func)
    assert isinstance(node, TaskCallable)
    assert node.name == "func"


def test_coerce_to_node_with_lambda() -> None:
    node = coerce_to_node(lambda: None)
    assert isinstance(node, TaskCallable)
    assert node.name == "<lambda>"


def test_run_task_callable() -> None:
    results = []

    def action() -> None:
        results.append(1)

    node = TaskCallable(action)
    node.run()

    assert results == [1]


def test_task_lifecycle() -> None:
    task = DummyTask(steps_to_complete=2)

    assert task.entered is False
    assert task.step_count == 0
    assert task.exited is False

    task.run()

    assert task.entered is True
    assert task.step_count == 2
    assert task.exited is True


def test_node_can_run_twice() -> None:
    results = []

    def action():
        results.append(1)

    node = TaskCallable(action)

    node.run()
    node.run()

    assert results == [1, 1]


def test_empty_node_chain() -> None:
    chain = NodeChain()

    assert chain.nodes == ()

    chain.run()


def test_run_node_chain() -> None:
    results = []

    def task1():
        results.append(1)

    def task2():
        results.append(2)

    def task3():
        results.append(3)

    chain = NodeChain(task1, task2, task3)
    chain.run()

    assert results == [1, 2, 3]


def test_multistep_task_in_node_chain() -> None:
    results = []

    class MultiStep(Task):
        def __init__(self):
            super().__init__()
            self.count = 0

        def step(self, ctx: ExecutionContext) -> bool:
            results.append(self.count)
            self.count += 1
            return self.count >= 3

    chain = NodeChain(MultiStep(), lambda: results.append("done"))

    chain.run()

    assert results == [0, 1, 2, "done"]


def test_node_chain_operator() -> None:
    task1 = DummyTask(name="task1")
    task2 = DummyTask(name="task2")

    chain = task1 | task2

    assert isinstance(chain, NodeChain)
    assert len(chain.nodes) == 2
    assert chain.nodes[0] is task1
    assert chain.nodes[1] is task2


def test_node_chain_with_callable_operator() -> None:
    task1 = DummyTask(name="task1")

    def task2() -> None:
        pass

    chain = task1 | task2

    assert isinstance(chain, NodeChain)
    assert len(chain.nodes) == 2
    assert chain.nodes[0] is task1
    assert isinstance(chain.nodes[1], TaskCallable)


def test_node_chain_operator_associativity() -> None:
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
    def task1() -> None:
        pass

    task2 = DummyTask(name="task2")

    chain = task1 | task2
    assert isinstance(chain, NodeChain)
    assert len(chain.nodes) == 2
    assert isinstance(chain.nodes[0], TaskCallable)
    assert chain.nodes[1] is task2


def test_node_chain_flattening() -> None:
    task1 = DummyTask(name="task1")
    task2 = DummyTask(name="task2")
    task3 = DummyTask(name="task3")

    chain1 = task1 | task2
    chain2 = chain1 | task3

    assert len(chain2.nodes) == 3
    assert chain2.nodes[0] is task1
    assert chain2.nodes[1] is task2
    assert chain2.nodes[2] is task3

    chain3 = task1 | (task2 | task3)
    assert len(chain3.nodes) == 3
