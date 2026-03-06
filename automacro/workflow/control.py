from __future__ import annotations

from typing import Callable, Sequence, TypeAlias

from typing_extensions import override

from automacro.workflow.base import ExecutionContext, Node, NodeLike, coerce_to_node

BooleanFunction: TypeAlias = Callable[[], bool]


class If(Node):
    """
    A node representing a conditional branch in a workflow. It evaluates a
    series of conditions in order, and executes the first branch whose
    condition evaluates to True. If no conditions are True, it does nothing
    and exits immediately.

    This node can be built using the `if_` factory function, which provides a
    fluent interface for defining the branches of the conditional.
    """

    def __init__(self, branches: Sequence[tuple[BooleanFunction, NodeLike]]) -> None:
        """
        Initialize the `If` node with a list of branches. The branches will be
        evaluated in the order they are provided.

        Args:
            branches (Sequence[tuple[BooleanFunction, NodeLike]]): A sequence
            of tuples, where each tuple contains a boolean function (a no-arg
            callable that returns a boolean) and a `NodeLike` object (either a
            Node instance or a callable that can be coerced to a Node). The
            first branch whose condition function returns True will have its
            corresponding node executed.
        """

        super().__init__(name="If")
        self._branches = [(c, coerce_to_node(n)) for c, n in branches]

        self._cursor = 0
        self._is_branching = True

    @override
    def _step(self, ctx: ExecutionContext) -> Node | None:
        ctx.check_interrupt()

        if not self._running:
            self._running = True
            self.on_enter()

        if self._is_branching:
            cond, node = self._branches[self._cursor]
            self._cursor += 1

            if cond():
                self._is_branching = False
                return node

            if self._cursor >= len(self._branches):
                self.on_exit()
                self._running = False
                return None

            return self

        self.on_exit()
        self._running = False
        return None

    @override
    def on_enter(self) -> None:
        self._cursor = 0
        self._is_branching = True

    def elif_(self, condition: BooleanFunction) -> _ConditionalBuilder:
        """
        Add an 'elif' branch to the conditional. This method can be called
        multiple times to add multiple 'elif' branches.

        Args:
            condition (BooleanFunction): A boolean function (a no-arg callable
            that returns a boolean) that will be evaluated as the condition for
            this branch.

        Returns:
            _ConditionalBuilder: A builder object which expects a `then_`
            method call to specify the node to execute if this condition is
            True.
        """

        return _ConditionalBuilder(condition, list(self._branches))

    def else_(self, node: NodeLike) -> IfAndElse:
        """
        Add an 'else' branch to the conditional. This method can only be called
        once, and it must be called after all 'if' and 'elif' branches have
        been defined.

        Args:
            node (NodeLike): A `NodeLike` object (either a Node instance or a
            callable that can be coerced to a Node) that will be executed if
            none of the 'if' or 'elif' conditions evaluate to True.

        Returns:
            IfAndElse: A new `IfAndElse` node that includes the defined
            branches and the specified 'else' branch. This node is the final,
            executable version of the conditional, and it does not have builder
            methods.
        """

        return IfAndElse(self._branches, else_branch=node)


class IfAndElse(Node):
    """
    A node representing a conditional branch with an 'else' case. This node is
    the final, executable version of a conditional that includes an 'else'
    branch. It evaluates a series of conditions in order, and executes the
    first branch whose condition evaluates to True. If no conditions are True,
    it executes the 'else' branch.

    This node does not have builder methods, and it is typically created
    through the `else_` method of the `If` builder.
    """

    def __init__(
        self,
        branches: Sequence[tuple[BooleanFunction, NodeLike]],
        else_branch: NodeLike,
    ) -> None:
        """
        Initialize the `IfAndElse` node with a list of branches and an else
        branch.

        Args:
            branches (Sequence[tuple[BooleanFunction, NodeLike]]): A sequence
            of tuples, where each tuple contains a boolean function (a no-arg
            callable that returns a boolean) and a `NodeLike` object (either a
            Node instance or a callable that can be coerced to a Node). The
            first branch whose condition function returns True will have its
            corresponding node executed.
            else_branch (NodeLike): A `NodeLike` object (either a Node instance
            or a callable that can be coerced to a Node) that will be executed
            if none of the conditions in the branches evaluate to True.
        """

        super().__init__(name="If and Else")
        self._branches = [(c, coerce_to_node(n)) for c, n in branches]
        self._else_branch = coerce_to_node(else_branch)

        self._cursor = 0
        self._is_branching = True

    @override
    def _step(self, ctx: ExecutionContext) -> Node | None:
        ctx.check_interrupt()

        if not self._running:
            self._running = True
            self.on_enter()

        if self._is_branching:
            cond, node = self._branches[self._cursor]
            self._cursor += 1

            if cond():
                self._is_branching = False
                return node

            if self._cursor >= len(self._branches):
                self._is_branching = False
                return self._else_branch

            return self

        self.on_exit()
        self._running = False
        return None

    @override
    def on_enter(self) -> None:
        self._cursor = 0
        self._is_branching = True


class _ConditionalBuilder:
    """
    A builder class for constructing an `If` node with multiple branches. This
    class is used to provide a fluent interface for defining the branches of a
    conditional. It enables chaining of `then_` calls to 'if' and 'elif'
    branches to define the nodes to execute for each condition.
    """

    def __init__(
        self,
        condition: BooleanFunction,
        accumulated_branches: list[tuple[BooleanFunction, NodeLike]],
    ) -> None:
        """
        Initialize the conditional builder.

        Args:
            condition (BooleanFunction): The condition for the current
            branch being defined.

            accumulated_branches (list[tuple[BooleanFunction, NodeLike]]): A
            list of branches that have been defined so far in the builder.
        """

        self._condition = condition
        self._accumulated_branches = accumulated_branches

    def then_(self, node: NodeLike) -> If:
        """
        Define the node to execute if the current condition evaluates to True,
        and return an `If` node that includes the defined branches so far.

        Args:
            node (NodeLike): A `NodeLike` object (either a Node instance or a
            callable that can be coerced to a Node) that will be executed if
            the current condition evaluates to True.

        Returns:
            If: A new `If` node that includes the defined branches so far,
            including the new branch added by this method.
        """

        self._accumulated_branches.append((self._condition, node))
        return If(self._accumulated_branches)


class While(Node):
    """
    A node representing a while loop in a workflow. It repeatedly evaluates a
    condition, and executes a body node as long as the condition evaluates to
    True. Once the condition evaluates to False, it exits the loop.

    This node can be built using the `while_` factory function, which provides
    a fluent interface for defining the condition and body of the loop.
    """

    def __init__(self, condition: BooleanFunction, body: NodeLike) -> None:
        """
        Initialize the `While` node with a condition and a body.

        Args:
            condition (BooleanFunction): A boolean function (a no-arg callable
            that returns a boolean) that will be evaluated before each
            iteration of the loop. The body will be executed as long as this
            condition returns True.
            body (NodeLike): A `NodeLike` object (either a Node instance or a
            callable that can be coerced to a Node) that represents the body of
            the loop. This node will be executed repeatedly as long as the
            condition evaluates to True.
        """

        super().__init__(name="While")
        self._condition = condition
        self._body = coerce_to_node(body)

        self._is_checking = True

    @override
    def _step(self, ctx: ExecutionContext) -> Node | None:
        ctx.check_interrupt()

        if not self._running:
            self._running = True
            self.on_enter()

        if self._is_checking:
            self._is_checking = False
            if not self._condition():
                self.on_exit()
                self._running = False
                return None
            return self._body

        self._is_checking = True
        return self

    @override
    def on_enter(self) -> None:
        self._is_checking = True


class _WhileBuilder:
    """
    A builder class for constructing a `While` node. This class is used to
    provide a fluent interface for defining the condition and body of a while
    loop. It enables chaining of the `do_` method to specify the body of the
    loop after defining the condition.
    """

    def __init__(self, condition: BooleanFunction) -> None:
        """
        Initialize the while builder.

        Args:
            condition (BooleanFunction): The condition for the while loop.
        """

        self._condition = condition

    def do_(self, node: NodeLike) -> While:
        """
        Define the body of the while loop, and return a `While` node that
        includes the defined condition and body.

        Args:
            node (NodeLike): A `NodeLike` object (either a Node instance or a
            callable that can be coerced to a Node) that represents the body
            of the loop. This node will be executed repeatedly as long as the
            condition evaluates to True.

        Returns:
            While: A new `While` node that includes the defined condition and
            body.
        """

        return While(self._condition, node)


def if_(condition: BooleanFunction) -> _ConditionalBuilder:
    """
    Factory function to start building an If node.

    Args:
        condition (BooleanFunction): A no-arg callable that returns a boolean,
        which will be evaluated as the condition for the 'if' branch.

    Returns:
        _ConditionalBuilder: A builder object which expects a `then_` method
        call to specify the node to execute if the condition is True, and which
        provides additional methods for defining 'elif' and 'else' branches.
    """
    return _ConditionalBuilder(condition, [])


def while_(condition: BooleanFunction) -> _WhileBuilder:
    """
    Factory function to start building a While node.

    Args:
        condition (BooleanFunction): A no-arg callable that returns a boolean,
        which will be evaluated as the condition for the while loop.

    Returns:
        _WhileBuilder: A builder object which expects a `do_` method call to
        specify the body of the loop, and which will return a `While` node
        when the body is defined.
    """
    return _WhileBuilder(condition)
