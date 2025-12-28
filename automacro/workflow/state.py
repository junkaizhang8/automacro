from enum import Enum, auto


class WorkflowState(Enum):
    """
    An enumeration representing the state of a workflow.
    """

    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPING = auto()
