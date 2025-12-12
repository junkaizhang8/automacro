from typing import Callable, Iterable


def interpolate(
    start: float,
    end: float,
    t: float,
    duration: float,
    easing_fn: Callable[[float], float],
) -> float:
    """
    Interpolate between start and end values based on current time t,
    duration, and easing function.

    Args:
        start (float): The starting value.
        end (float): The ending value.
        t (float): The current time (in seconds) elapsed. Must be between 0 and
        duration.
        duration (float): The total duration of the interpolation (in seconds).
        easing_fn (Callable[[float], float]): Easing function to apply.
    """

    if duration <= 0:
        return end

    # Normalize t to [0, 1]
    normalized_t = max(0.0, min(t / duration, 1.0))

    return start + (end - start) * easing_fn(normalized_t)


def interpolate_sequence(
    start: Iterable[float],
    end: Iterable[float],
    t: float,
    duration: float,
    easing_fn: Callable[[float], float],
) -> list[float]:
    """
    Interpolate between two sequences of values element-wise.

    If the sequences are of different lengths, the extra elements in the
    longer sequence are ignored.

    Args:
        start (Iterable[float]): The starting sequence of values.
        end (Iterable[float]): The ending sequence of values.
        t (float): The current time (in seconds) elapsed. Must be between 0 and
        duration.
        duration (float): The total duration of the interpolation (in seconds).
        easing_fn (Callable[[float], float]): Easing function to apply.

    Returns:
        list[float]: The interpolated sequence of values.
    """

    return [interpolate(s, e, t, duration, easing_fn) for s, e in zip(start, end)]
