def _get_logger(cls):
    """
    Create a logger for the given class.

    Args:
        cls (type): The class for which to create the logger.

    Returns:
        logging.Logger: The logger instance.
    """
    import logging

    return logging.getLogger(cls.__module__ + "." + cls.__name__)
