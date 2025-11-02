from typing import Callable

from automacro.workflow.task import WorkflowTask


class ConditionalTask(WorkflowTask):
    """
    A workflow task that jumps to other tasks based on a condition.
    """

    def __init__(
        self,
        task_name: str,
        condition: Callable[[], bool],
        then_task_idx: int,
        else_task_idx: int | None = None,
    ):
        """
        Initialize the conditional task.

        Args:
            task_name (str): The name of the task.
            condition (Callable[[], bool]): A function that returns a boolean.
            then_task_idx (int): The index of the task to jump to if the
            condition is true.
            else_task_idx (int | None): The index of the task to jump to if the
            condition is false. If None, the workflow proceeds to the next
            task in sequence.
        """

        super().__init__(task_name)
        self.condition = condition
        self.then_task_idx = then_task_idx
        self.else_task_idx = else_task_idx
        self.next_task_idx: int | None = None

    def step(self) -> None:
        """
        Evaluate the condition and set the next task index.
        """

        if self.condition():
            self.next_task_idx = self.then_task_idx
        else:
            self.next_task_idx = self.else_task_idx
        # Stop the task after one evaluation
        self.stop()


class WaitUntilTask(WorkflowTask):
    """
    A task that waits until a condition is met before completing.
    """

    def __init__(
        self,
        task_name: str,
        condition: Callable[[], bool],
        poll_interval: float = 0.1,
    ):
        """
        Args:
            task_name (str): The name of the task.
            condition (callable): A function that returns True when the waiting
            should stop.
            poll_interval (float): The time in seconds to wait between checks.
        """
        super().__init__(task_name)
        self._condition = condition
        self._poll_interval = poll_interval

    def step(self) -> None:
        if self._condition():
            self.stop()
        else:
            self.wait(self._poll_interval)
