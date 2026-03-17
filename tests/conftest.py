import time


def wait_until(condition, timeout=1.0, interval=0.01):
    """Wait until a condition is True or timeout."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if condition():
            return
        time.sleep(interval)
    raise TimeoutError("Condition not met within timeout")
