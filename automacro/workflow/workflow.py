from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum, auto

from automacro.workflow.base import Node, NodeChain
from automacro.workflow.context import ExecutionContext


class WorkflowState(Enum):
    """
    An enumeration of the different states that the workflow can be in during
    its execution.
    """

    NOT_RUNNING = auto()
    RUNNING = auto()


@dataclass
class _Frame:
    """
    A frame on the workflow's execution stack, representing a single node that
    is currently being executed.
    """

    node: Node


class Workflow:
    """
    A class representing a workflow, which manages the execution of a tree of
    nodes. The workflow is designed to be thread-safe, allowing for control
    from multiple threads while ensuring that the execution state is properly
    synchronized.
    """

    def __init__(self, node: Node) -> None:
        """
        Initialize a new `Workflow` with the given root node.

        Args:
            node (Node): The root node of the workflow to execute.
        """

        self._node = node
        self._ctx = ExecutionContext()

        self._stack: list[_Frame]

        self._init_stack()

        self._state = WorkflowState.NOT_RUNNING

        self._lock = threading.Lock()

    @property
    def status(self) -> WorkflowState:
        return self._state

    def _init_stack(self) -> None:
        self._stack = [_Frame(self._node)]

        if isinstance(self._node, NodeChain):
            child = self._node._step(self._ctx)
            if child is not None and child is not self._node:
                self._stack.append(_Frame(child))

    def _step(self) -> bool:
        """
        Perform a single step of execution. Returns True if execution is
        complete, or False if there are more steps to execute.

        This method does not perform any state checks, so it assumes that the
        workflow is currently running and that the caller has already acquired
        the necessary locks.

        Returns:
            bool: True if execution is complete, or False if there are more
            steps to execute.
        """

        while self._stack:
            frame = self._stack[-1]
            node = frame.node

            child = node._step(self._ctx)

            if child is None:
                self._stack.pop()
                continue
            else:
                if child is not frame.node:
                    self._stack.append(_Frame(child))
            break

        return not self._stack

    def run(self) -> None:
        """
        Run the workflow. This method will block until the workflow is complete
        or until it is stopped.

        Only one thread is allowed to run the workflow at a time, and any
        attempts to call run while the workflow is already running will be
        ignored.
        """

        with self._lock:
            if self._state != WorkflowState.NOT_RUNNING:
                return

            self._state = WorkflowState.RUNNING

        while True:
            with self._lock:
                if self._state == WorkflowState.NOT_RUNNING:
                    return

            done = self._step()
            if done:
                self.stop()
                return

    def stop(self) -> None:
        """
        Stop the workflow. This will cause the workflow to exit as soon as
        possible.
        """

        with self._lock:
            if self._state != WorkflowState.NOT_RUNNING:
                self._state = WorkflowState.NOT_RUNNING
