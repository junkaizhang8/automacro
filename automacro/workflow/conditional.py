from typing import Callable

from automacro.workflow.task import WorkflowTask
from automacro.workflow.context import TaskContext


class ConditionalTask(WorkflowTask):
    """
    A workflow task that jumps to other tasks based on a condition.
    """

    def __init__(
        self,
        name: str,
        condition: Callable[[TaskContext], bool],
        then_task_idx: int,
        else_task_idx: int | None = None,
    ):
        """
        Initialize the conditional task.

        Args:
            name (str): The name of the task.
            condition (Callable[[TaskContext], bool]): A function that
            accepts a TaskContext and returns True or False.
            then_task_idx (int): The index of the task to jump to if the
            condition is true.
            else_task_idx (int | None): The index of the task to jump to if the
            condition is false. If None, the workflow proceeds to the next
            task in sequence.
        """

        super().__init__(name)
        self._condition = condition
        self._then_task_idx = then_task_idx
        self._else_task_idx = else_task_idx
        self._next_task_idx: int | None = None

    @property
    def next_task_idx(self) -> int | None:
        """
        The index of the next task to jump to after evaluating the condition.
        It is set to None until the task is executed.
        """

        return self._next_task_idx

    def step(self, ctx: TaskContext):
        """
        Evaluate the condition and set the next task index.
        """

        if self._condition(ctx):
            self._next_task_idx = self._then_task_idx
        else:
            self._next_task_idx = self._else_task_idx
        # Stop the task after one evaluation
        self.stop()


class WaitUntilTask(WorkflowTask):
    """
    A task that waits until a condition is met before completing.
    """

    def __init__(
        self,
        name: str,
        condition: Callable[[TaskContext], bool],
        poll_interval: float = 0.1,
    ):
        """
        Args:
            name (str): The name of the task.
            condition (Callable[[TaskContext], bool]): A function that accepts
            a TaskContext and returns True when the wait should end.
            poll_interval (float): The time in seconds to wait between checks.
        """

        super().__init__(name)
        self._condition = condition
        self._poll_interval = poll_interval

    def step(self, ctx: TaskContext):
        """
        Evaluate the condition and wait if not met.
        """

        if self._condition(ctx):
            self.stop()
        else:
            self.wait(self._poll_interval)
