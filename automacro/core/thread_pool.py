from concurrent.futures import ThreadPoolExecutor, Future
import threading


class ThreadPool:
    def __init__(self, max_workers: int = 4):
        """
        Initialize the thread pool.

        Args:
            max_workers (int): The maximum number of worker threads.
            Default is 4.
        """

        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.Lock()

    def submit(self, fn, *args, **kwargs) -> Future:
        """
        Submit a task to the thread pool.

        Args:
            fn (Callable): The function to execute.
            *args, **kwargs: Arguments for the function.

        Returns:
            Future: A Future object representing the execution of the task.
        """

        with self._lock:
            return self._executor.submit(fn, *args, **kwargs)

    def shutdown(self, wait: bool = True):
        """
        Shutdown the thread pool.

        Args:
            wait (bool): If True, wait for all tasks to complete before
            shutting down. Default is True.
        """

        with self._lock:
            self._executor.shutdown(wait=wait)
