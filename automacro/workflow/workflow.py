from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum, auto

from automacro.workflow.base import Node, NodeChain
from automacro.workflow.breakpoint import Breakpoint
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


class _StepKind(Enum):
    """
    An enumeration of the different kinds of stepping actions that can be
    requested in the workflow.
    """

    IN = auto()
    OVER = auto()
    OUT = auto()


@dataclass
class _StepRequest:
    """
    A request to perform a stepping action in the workflow.
    """

    kind: _StepKind
    start_depth: int
    frame: _Frame | None = None
    steps_executed: int = 0
    done: threading.Event | None = None


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

        self._state = WorkflowState.NOT_RUNNING

        self._step_request: _StepRequest | None = None

        self._executing_node = False

        self._cond = threading.Condition()

        self._thread = None

    @property
    def state(self) -> WorkflowState:
        return self._state

    def _init_stack(self) -> None:
        """
        Initialize the execution stack with the root node of the workflow. This
        should be called at the beginning of the workflow's execution to set up
        the initial state of the stack.
        """

        self._stack = [_Frame(self._node)]

        if isinstance(self._node, NodeChain):
            child = self._node._step(self._ctx)
            if child is not None and child is not self._node:
                self._stack.append(_Frame(child))

                if isinstance(child, Breakpoint):
                    self._pause()
        elif isinstance(self._node, Breakpoint):
            self._pause()

    def _set_step_request(self, kind: _StepKind) -> threading.Event | None:
        """
        Create a new step request to be processed. This should be called by
        the stepping methods (step_in, step_over, step_out) to add new step
        requests to the queue.

        This method does not perform any state checks, so it assumes that the
        workflow is currently running and that the caller has already acquired
        the necessary locks.

        Args:
            kind (_StepKind): The kind of step request to enqueue (IN, OVER,
            or OUT).

        Returns:
            threading.Event | None: If block is True, this method returns a
            threading.Event that will be set when the step request is fulfilled.
            If block is False, this method returns None.
        """

        # We only allow one active step request at a time, since having
        # multiple active step requests would create ambiguity about which
        # request should be fulfilled when a step is executed
        if self._step_request is not None:
            return None

        current_frame = self._stack[-1] if self._stack else None
        event = threading.Event()

        self._step_request = _StepRequest(
            kind, len(self._stack), frame=current_frame, done=event
        )

        self._resume()

        return event

    def _step(self) -> bool:
        """
        Perform a single step of execution. Returns True if execution is
        complete, or False if there are more steps to execute.

        This method does not handle `InterruptException`, so any interrupts
        that occur during the execution of this step will propagate up to
        the caller. The caller is responsible for catching `InterruptException`
        and pausing the workflow as necessary.

        Returns:
            bool: True if execution is complete, or False if there are more
            steps to execute.
        """

        while True:
            with self._cond:
                if not self._stack:
                    return True

                frame = self._stack[-1]
                node = frame.node

            child = node._step(self._ctx)

            with self._cond:
                if not self._stack:
                    return True

                if (
                    child is not None
                    and not isinstance(child, NodeChain)
                    and self._step_request is not None
                ):
                    self._step_request.steps_executed += 1

                if child is None:
                    self._stack.pop()
                    self._check_step_request_with_depth()
                    continue

                if child is not frame.node:
                    self._stack.append(_Frame(child))
                    self._check_step_request_with_depth()

                if isinstance(child, Breakpoint):
                    self._pause()

            break

        return not self._stack

    def _check_step_request_with_depth(self) -> None:
        """
        Check if the active step request (OVER or OUT) has been fulfilled,
        and if so, clear it and pause the workflow if there are no more pending
        step requests.

        This method does not perform any state checks, so it assumes that the
        workflow is currently running and that the caller has already acquired
        the necessary locks.
        """

        req = self._step_request

        if req is None:
            return

        depth = len(self._stack)

        finished = False
        current_frame = self._stack[-1] if self._stack else None
        node = current_frame.node if current_frame else None

        if req.kind == _StepKind.OVER:
            # We treat NodeChains as transparent for stepping purposes
            finished = (
                req.steps_executed >= 1
                and depth <= req.start_depth
                and current_frame is not req.frame
                and not isinstance(node, NodeChain)
            )
        elif req.kind == _StepKind.OUT:
            finished = (
                depth < req.start_depth
                and current_frame is not req.frame
                and not isinstance(node, NodeChain)
            )

        if finished:
            if req.done is not None:
                req.done.set()

            self._step_request = None
            self._pause()

    def _check_step_in_request(self) -> None:
        """
        Check if the active step request (IN) has been fulfilled and if so,
        clear it and pause the workflow if there are no more pending step
        requests.

        This method does not perform any state checks, so it assumes that the
        workflow is currently running and that the caller has already acquired
        the necessary locks.
        """

        req = self._step_request

        if req is None or req.kind != _StepKind.IN:
            return

        if req.steps_executed >= 1:
            if req.done is not None:
                req.done.set()

            self._step_request = None
            self._pause()

    def _unwind_stack(self) -> None:
        """
        Internal method to unwind the execution stack. This is used when
        stopping or restarting the workflow to ensure that all nodes are
        properly exited and that the stack is cleared.

        This method does not acquire any locks, so it assumes that the caller
        has already acquired the necessary locks before calling it.
        """

        while self._stack:
            frame = self._stack.pop()
            frame.node.on_exit()
            frame.node._running = False

    def _pause(self) -> None:
        """
        Internal method to pause the workflow.

        This method does not acquire any locks, so it assumes that the caller
        has already acquired the necessary locks before calling it.
        """

        if self._state == WorkflowState.RUNNING:
            self._ctx._pause()
            self._state = WorkflowState.PAUSED
            self._cond.notify_all()

    def _resume(self) -> None:
        """
        Internal method to resume the workflow.

        This method does not acquire any locks, so it assumes that the caller
        has already acquired the necessary locks before calling it.
        """

        if self._state == WorkflowState.PAUSED:
            self._ctx._resume()
            self._state = WorkflowState.RUNNING
            self._executing_node = True
            self._cond.notify_all()

    def _on_enter(self, start_paused: bool) -> None:
        """
        Internal method to perform any necessary setup when the workflow starts
        running. This should be called at the beginning of the `run` method to
        ensure that any necessary initialization is performed before execution
        begins.

        Args:
            start_paused (bool): Whether the workflow should start in a paused
            state.
        """

        self._state = WorkflowState.PAUSED if start_paused else WorkflowState.RUNNING
        self._init_stack()
        self._step_request = None
        self._executing_node = not start_paused

    def _on_exit(self) -> None:
        """
        Internal method to perform cleanup when the workflow is stopped. This
        should be called at the end of the `run` method to ensure that any
        necessary cleanup is performed when the workflow finishes executing or is
        stopped.
        """

        # Notify any pending step request that execution is complete
        if self._step_request is not None and self._step_request.done is not None:
            self._step_request.done.set()

        # Unwind the stack to ensure that all nodes are properly exited
        self._unwind_stack()

        self._step_request = None
        self._state = WorkflowState.NOT_RUNNING

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

            self._on_enter(start_paused)

        while True:
            with self._cond:
                while self._state == WorkflowState.PAUSED:
                    self._executing_node = False
                    # Notify any waiting threads that we are paused, and then
                    # wait until we are resumed again
                    self._cond.notify_all()
                    self._cond.wait()

                if self._state == WorkflowState.NOT_RUNNING:
                    break

            try:
                done = self._step()
                if done:
                    self.stop()
                    break

                with self._cond:
                    self._check_step_in_request()
            except InterruptException:
                pass

        with self._cond:
            self._on_exit()

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

    def stop(self, block: bool = False) -> None:
        """
        Stop the workflow. This will cause the workflow to exit as soon as
        possible.

        Args:
            block (bool): Whether to block until the workflow has fully
            stopped. If True, will also join the workflow thread if it was
            started using the `start` method. Default is False.
        """

        with self._cond:
            if self._state != WorkflowState.NOT_RUNNING:
                self._ctx._resume()
                self._state = WorkflowState.NOT_RUNNING
                self._executing_node = False
                self._cond.notify_all()

        if block and self._thread is not None:
            self._thread.join()

    def pause(self, block: bool = False) -> None:
        """
        Pause the workflow. If the workflow is already paused or not running,
        this method will have no effect.

        Args:
            block (bool): Whether to block until the workflow has fully paused.
            Default is False.
        """

        with self._cond:
            if self._state == WorkflowState.RUNNING:
                self._pause()

                if block:
                    while self._executing_node:
                        self._cond.wait()

    def resume(self) -> None:
        """
        Resume the workflow if it is currently paused. If the workflow is not
        paused, this method will have no effect.
        """

        with self._cond:
            if self._state == WorkflowState.PAUSED:
                self._resume()

    def restart(self) -> None:
        """
        Restart the workflow from the beginning. This will reset the workflow's
        execution state and start it from the root node. If the workflow is not
        paused, this method will have no effect.

        Note that this method does not reset data within user-defined nodes
        unless those nodes explicitly handle resource cleanup and
        reinitialization via implementing `on_exit` and/or `on_enter` methods.
        """

        with self._cond:
            if self._state != WorkflowState.PAUSED:
                return

            self._unwind_stack()

            self._init_stack()
            self._step_request = None

    def step_in(self) -> None:
        """
        Request to step into the next node in the workflow. This will cause the
        workflow to execute the next step of the next `Task` node it
        encounters, and then pause again. If the workflow is not currently
        paused, this method will have no effect.

        Note that only one step request can be active at a time, so if there
        is already an active step request when this method is called, the new
        request will be ignored.
        """

        with self._cond:
            if self._state != WorkflowState.PAUSED:
                return

            event = self._set_step_request(_StepKind.IN)

        if event is not None:
            event.wait()

    def step_over(self) -> None:
        """
        Request to step over the next node in the workflow. This will cause the
        workflow to continue executing until the node has completed and has
        been popped off the stack, and then pause again. If the workflow is not
        currently paused, this method will have no effect.

        Note that only one step request can be active at a time, so if there
        is already an active step request when this method is called, the new
        request will be ignored.
        """

        with self._cond:
            if self._state != WorkflowState.PAUSED:
                return

            event = self._set_step_request(_StepKind.OVER)

        if event is not None:
            event.wait()

    def step_out(self) -> None:
        """
        Request to step out of the current node in the workflow. This will
        cause the workflow to continue executing until the current node has
        completed and has been popped off the stack, and then pause again. If
        the workflow is not currently paused, this method will have no effect.

        Note that only one step request can be active at a time, so if there
        is already an active step request when this method is called, the new
        request will be ignored.
        """

        with self._cond:
            if self._state != WorkflowState.PAUSED:
                return

            event = self._set_step_request(_StepKind.OUT)

        if event is not None:
            event.wait()
