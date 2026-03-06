from typing_extensions import override

from automacro.workflow.base import Node
from automacro.workflow.context import ExecutionContext


class Breakpoint(Node):
    """
    A node representing a breakpoint in a workflow. When the workflow
    execution reaches this node, it will pause and wait for user input to
    continue.
    """

    def __init__(self, name: str | None = None) -> None:
        super().__init__(name=name)

    @override
    def _step(self, ctx: ExecutionContext) -> Node | None:
        return None


def bp(name: str | None = None) -> Breakpoint:
    """
    Factory function to create a `Breakpoint` node.

    Args:
        name: Optional name for the breakpoint node. If not provided, it will
        default to the class name "Breakpoint". This name can be used for
        identification and debugging purposes when the workflow execution
        reaches this breakpoint.

    Returns:
        Breakpoint: An instance of the `Breakpoint` node, which can be included
        in a workflow to create a pause point where execution will wait for
        user input before continuing.
    """

    return Breakpoint(name=name)
