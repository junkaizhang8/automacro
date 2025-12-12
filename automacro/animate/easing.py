import math


def linear(t: float) -> float:
    return t


def ease_in_quad(t: float) -> float:
    return t * t


def ease_out_quad(t: float) -> float:
    return t * (2 - t)


def ease_in_out_quad(t: float) -> float:
    if t < 0.5:
        return 2 * t * t
    else:
        return -1 + (4 - 2 * t) * t


def ease_in_cubic(t: float) -> float:
    return t * t * t


def ease_out_cubic(t: float) -> float:
    t -= 1
    return t * t * t + 1


def ease_in_out_cubic(t: float) -> float:
    if t < 0.5:
        return 4 * t * t * t
    else:
        t -= 1
        return 1 + 4 * t * t * t


def ease_in_quart(t: float) -> float:
    return t * t * t * t


def ease_out_quart(t: float) -> float:
    t -= 1
    return 1 - t * t * t * t


def ease_in_out_quart(t: float) -> float:
    if t < 0.5:
        return 8 * t * t * t * t
    else:
        t -= 1
        return 1 - 8 * t * t * t * t


def ease_in_quint(t: float) -> float:
    return t * t * t * t * t


def ease_out_quint(t: float) -> float:
    t -= 1
    return 1 + t * t * t * t * t


def ease_in_out_quint(t: float) -> float:
    if t < 0.5:
        return 16 * t * t * t * t * t
    else:
        t -= 1
        return 1 + 16 * t * t * t * t * t


def ease_in_sine(t: float) -> float:
    return 1 - math.cos((t * math.pi) / 2)


def ease_out_sine(t: float) -> float:
    return math.sin((t * math.pi) / 2)


def ease_in_out_sine(t: float) -> float:
    return -(math.cos(math.pi * t) - 1) / 2


def ease_in_expo(t: float) -> float:
    return 0 if t == 0 else math.pow(2, 10 * (t - 1))


def ease_out_expo(t: float) -> float:
    return 1 if t == 1 else 1 - math.pow(2, -10 * t)


def ease_in_out_expo(t: float) -> float:
    if t == 0:
        return 0
    if t == 1:
        return 1
    if t < 0.5:
        return math.pow(2, 20 * t - 10) / 2
    else:
        return (2 - math.pow(2, -20 * t + 10)) / 2


def ease_in_circ(t: float) -> float:
    return 1 - math.sqrt(1 - t * t)


def ease_out_circ(t: float) -> float:
    t -= 1
    return math.sqrt(1 - t * t)


def ease_in_out_circ(t: float) -> float:
    if t < 0.5:
        return (1 - math.sqrt(1 - 4 * t * t)) / 2
    else:
        t = 2 * t - 1
        return (math.sqrt(1 - t * t) + 1) / 2
