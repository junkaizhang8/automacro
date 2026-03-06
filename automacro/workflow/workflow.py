from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum, auto

from automacro.workflow.base import Node, NodeChain
from automacro.workflow.context import ExecutionContext
from automacro.workflow.exceptions import InterruptException


class WorkflowState(Enum):
    """
    An enumeration of the different states that the workflow can be in during
    its execution.
    """

    NOT_RUNNING = auto()
    RUNNING = auto()
    PAUSED = auto()


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
    nodes.

    The workflow is designed to be thread-safe, allowing for control from
    multiple threads while ensuring that the execution state is properly
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

        self._cond = threading.Condition()

        self._thread = None

    @property
    def state(self) -> WorkflowState:
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

        This method does not handle `InterruptException`, so any interrupts
        that occur during the execution of this step will propagate up to
        the caller. The caller is responsible for catching `InterruptException`
        and pausing the workflow as necessary.

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
            elif child is not frame.node:
                self._stack.append(_Frame(child))
            break

        return not self._stack

    def _pause(self) -> None:
        """
        Internal method to pause the workflow.

        This method does not acquire any locks, so it assumes that the caller
        has already acquired the necessary locks before calling it.
        """

        if self._state == WorkflowState.RUNNING:
            self._ctx._pause()
            self._state = WorkflowState.PAUSED

    def _resume(self) -> None:
        """
        Internal method to resume the workflow.

        This method does not acquire any locks, so it assumes that the caller
        has already acquired the necessary locks before calling it.
        """

        if self._state == WorkflowState.PAUSED:
            self._ctx._resume()
            self._state = WorkflowState.RUNNING
            self._cond.notify_all()

    def run(self, *, start_paused: bool = False) -> None:
        """
        Run the workflow. This method will block until the workflow is complete
        or until it is stopped.

        Only one thread is allowed to run the workflow at a time, and any
        attempts to call run while the workflow is already running will be
        ignored.

        Args:
            start_paused (bool): If True, the workflow will start in a paused
            state. Otherwise, it will start running immediately. Default is
            False.
        """

        with self._cond:
            if self._state != WorkflowState.NOT_RUNNING:
                return

            self._state = (
                WorkflowState.PAUSED if start_paused else WorkflowState.RUNNING
            )

        while True:
            with self._cond:
                while self._state == WorkflowState.PAUSED:
                    self._cond.wait()

                if self._state == WorkflowState.NOT_RUNNING:
                    return

            try:
                done = self._step()
                if done:
                    self.stop()
                    return
            except InterruptException:
                with self._cond:
                    self._pause()

    def start(self, *, start_paused: bool = False) -> None:
        """
        Start the workflow in a new thread. This is a convenience method that
        enables running the workflow without blocking the current thread.

        Args:
            start_paused (bool): If True, the workflow will start in a paused
            state. Otherwise, it will start running immediately. Default is
            False.
        """

        if self._thread is not None and self._thread.is_alive():
            return

        self._thread = threading.Thread(
            target=self.run, kwargs={"start_paused": start_paused}
        )
        self._thread.start()

    def join(self, timeout: float | None = None) -> None:
        """
        Wait for the workflow to complete. This will block until the workflow
        has finished executing or until the specified timeout has elapsed.

        This method should only be called if the workflow was started using the
        `start` method, and it will have no effect otherwise.

        Args:
            timeout (float | None): The maximum amount of time to wait for the
            workflow to complete, in seconds. If None, this method will wait
            indefinitely until the workflow completes. Default is None.
        """

        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def stop(self) -> None:
        """
        Stop the workflow. This will cause the workflow to exit as soon as
        possible.
        """

        with self._cond:
            if self._state != WorkflowState.NOT_RUNNING:
                self._ctx._resume()
                self._state = WorkflowState.NOT_RUNNING
                self._cond.notify_all()

    def pause(self) -> None:
        """
        Pause the workflow. If the workflow is already paused or not running,
        this method will have no effect.
        """

        with self._cond:
            if self._state == WorkflowState.RUNNING:
                self._pause()

    def resume(self) -> None:
        """
        Resume the workflow if it is currently paused. If the workflow is not
        paused, this method will have no effect.
        """

        with self._cond:
            if self._state == WorkflowState.PAUSED:
                self._resume()
