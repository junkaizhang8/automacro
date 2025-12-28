class WorkflowError(Exception):
    """
    Base class for workflow-related errors.
    """

    pass


class InvalidTaskJumpError(WorkflowError):
    """
    Raised when an invalid task jump is attempted in the workflow.
    """

    def __init__(self, idx: int):
        super().__init__(f"Invalid jump to task index {idx}")


class InvalidConditionalIndexError(WorkflowError):
    """
    Raised when an invalid task index is provided by a ConditionalTask
    instance upon execution.
    """

    def __init__(self, task_name: str, idx: int):
        super().__init__(
            f"Invalid task index from ConditionalTask ({task_name}): {idx}"
        )
