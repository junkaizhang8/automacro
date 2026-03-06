class InterruptException(Exception):
    """
    Exception raised when a workflow execution is interrupted. This is used to
    propagate an interrupt signal up the workflow chain, allowing the workflow
    to handle the interrupt and stop execution of the current node.
    """

    pass
