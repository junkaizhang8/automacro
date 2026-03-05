from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, TypeAlias

from typing_extensions import override

from automacro.workflow.context import ExecutionContext


class Node(ABC):
    """
    Base class for all nodes in a workflow. Nodes represent individual steps or
    actions within a workflow, and can be composed together to build more
    complex workflows. Each node must implement the `_step` method (except for
    subclasses of `Task`, which itself implements the `_step` method), which
    defines the logic for executing that node within a given execution context.

    Nodes can be chained together using the '|' operator, which creates a
    `NodeChain` object that encapsulates the sequence of nodes to be executed
    in order.
    """

    def __init__(self, *, name: str | None = None) -> None:
        """
        Initialize a new `Node`.

        Args:
            name (str | None): An optional name for the node, used for
            identification and debugging purposes. If not provided, the
            class name of the node will be used as its name.
        """

        self._name = name or self.__class__.__name__

        self._running = False

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @abstractmethod
    def _step(self, ctx: ExecutionContext) -> Node | None:
        """
        Perform a single step of the node's logic within the given execution
        context, and return the next child node to execute, or None if this
        node has completed its work and should be popped off the execution
        stack.

        Args:
            ctx (ExecutionContext): The execution context for the workflow.

        Returns:
            Node | None: The next child node to execute, or None if this node
            has completed its work.
        """

    def on_enter(self) -> None:
        """
        Method called when the node is first entered (i.e., when it starts
        executing). Can be optionally overridden by subclasses to perform
        setup or initialization logic when the node is entered.
        """

        pass

    def on_exit(self) -> None:
        """
        Method called when the node is exited (i.e., when it has completed its
        work). Can be optionally overridden by subclasses to perform cleanup or
        finalization logic when the node is exited.
        """

        pass

    def run(self) -> None:
        """
        Run the node until it has completed its work. This method will repeatedly
        call the `_step` method until it returns None, indicating that the node
        has finished executing.
        """

        ctx = ExecutionContext()

        stack: list[Node] = [self]

        while stack:
            current = stack[-1]
            next_node = current._step(ctx)

            if next_node is None:
                stack.pop()
            elif next_node is not current:
                stack.append(next_node)

    def __or__(self, other: NodeLike) -> NodeChain:
        return NodeChain(self, other)

    def __ror__(self, other: NodeLike) -> NodeChain:
        return NodeChain(other, self)


class NodeChain(Node):
    """
    Represents a sequence of `NodeLike` objects chained together using the '|'
    operator. A `NodeLike` can be either a `Node` instance or a callable
    function that accepts no arguments. The `NodeChain` object will execute
    each node in order, moving to the next node only after the current node
    has completed its work.

    The '|' operator is only defined on `Node` (and `NodeChain`) objects.
    Plain callables (including lambdas) do not implement '|', so chaining
    multiple lambdas directly is not supported.

    This means that the following code will NOT work:

        ```python
        (lambda: print("hi")) | (lambda: print("bye"))
        ```

    Instead, at least one side of the chain must already be a `Node`
    (or `NodeChain`) so that the overloaded operator can be invoked.
    For example:

        ```python
        coerce_to_node(lambda: print("hi")) | (lambda: print("bye"))
        ```

    or:

        ```python
        NodeChain() | (lambda: print("hi")) | (lambda: print("bye"))
        ```

    Once the left-hand operand is a `Node`, subsequent callables will
    automatically be coerced into `Node` instances.
    """

    def __init__(
        self,
        *steps: NodeLike,
        name: str | None = None,
    ) -> None:
        """
        Initialize a new `NodeChain`.

        Args:
            steps (NodeLike): A variable number of `NodeLike` objects (either
            Node instances or callables) to be executed in sequence as part of
            this NodeChain.
            name (str | None): An optional name for the node chain, used for
            identification and debugging purposes. If not provided, the default
            name will be "NodeChain".
        """

        super().__init__(name=name)

        nodes: list[Node] = []

        for step in steps:
            if isinstance(step, NodeChain):
                nodes.extend(step.nodes)
            else:
                nodes.append(coerce_to_node(step))

        self._nodes = tuple(nodes)
        self._cursor = 0

    @property
    def nodes(self) -> tuple[Node, ...]:
        return self._nodes

    @override
    def _step(self, ctx: ExecutionContext) -> Node | None:
        if not self._running:
            self._running = True
            self.on_enter()

        if self._cursor >= len(self._nodes):
            self.on_exit()
            self._running = False
            return None

        node = self.nodes[self._cursor]
        self._cursor += 1

        return node

    @override
    def on_enter(self) -> None:
        print(f"Entering node chain: {self.name}")
        self._cursor = 0

    @override
    def __or__(self, other: NodeLike) -> NodeChain:
        if isinstance(other, NodeChain):
            return NodeChain(
                *self.nodes,
                *other.nodes,
                name=self.name or other.name,
            )
        return NodeChain(
            *self.nodes,
            other,
            name=self.name,
        )

    @override
    def __ror__(self, other: NodeLike) -> NodeChain:
        if isinstance(other, NodeChain):
            return NodeChain(
                *other.nodes,
                *self.nodes,
                name=other.name or self.name,
            )
        return NodeChain(
            other,
            *self.nodes,
            name=self.name,
        )


NodeLike: TypeAlias = Node | Callable[[], Any]


class Task(Node, ABC):
    """
    Base class representing a unit of work that can be executed as part of a
    workflow.
    """

    def __init__(self, *, name: str | None = None) -> None:
        super().__init__(name=name)

    @override
    def _step(self, ctx: ExecutionContext) -> Node | None:
        if not self._running:
            self._running = True
            self.on_enter()

        done = self.step(ctx)

        if done:
            self.on_exit()
            self._running = False
            return None
        return self

    @abstractmethod
    def step(self, ctx: ExecutionContext) -> bool:
        """
        Perform a single step of the task's logic within the given execution
        context, and return whether the task has completed its work.

        Args:
            ctx (ExecutionContext): The execution context for the workflow.

        Returns:
            bool: True if the task has completed its work and should be popped
            off the execution stack, or False if the task is still in progress
            and should remain on the stack for further steps.
        """


class TaskCallable(Task):
    """
    A simple `Task` implementation that wraps a no-argument callable function.

    The task is considered complete after the function is called once.
    This allows plain callables (including lambdas) to be easily integrated
    into a workflow as tasks without needing to define a custom `Task`
    subclass for each function.
    """

    def __init__(
        self,
        func: Callable[[], Any],
        *,
        name: str | None = None,
    ) -> None:
        """
        Initialize a new `TaskCallable`.

        Args:
            func (Callable[[], Any]): The function to be wrapped by this task.
            name (str | None): An optional name for the task, used for
            identification and debugging purposes. If not provided, the default
            name will be the name of the wrapped function.
        """

        super().__init__(name=name or func.__name__)
        self._func = func

    @override
    def step(self, ctx: ExecutionContext) -> bool:
        self._func()
        return True


def coerce_to_node(thing: NodeLike) -> Node:
    """
    Coerce a `NodeLike` object into a `Node`.

    Args:
        thing (NodeLike): The object to be coerced, which can be either a
        `Node` instance or a callable that takes no arguments.

    Returns:
        Node: The coerced `Node` instance. If the input was already a `Node`
        instance, it is returned as-is. If the input was a callable, it is
        wrapped in a `TaskCallable`.
    """

    if isinstance(thing, Node):
        return thing
    if callable(thing):
        return TaskCallable(thing)
