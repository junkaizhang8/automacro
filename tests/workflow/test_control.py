import pytest

from automacro import (
    if_,
    while_,
)


def test_if_then_true_function_condition() -> None:
    results = []

    def cond() -> bool:
        return True

    def action() -> None:
        results.append(1)

    node = if_(cond).then_(action)
    node.run()

    assert results == [1]


def test_if_then_true_lambda_condition() -> None:
    results = []

    def action() -> None:
        results.append(1)

    node = if_(lambda: True).then_(action)
    node.run()

    assert results == [1]


def test_if_then_false_function_condition() -> None:
    results = []

    def condition() -> bool:
        return False

    def action() -> None:
        results.append(1)

    node = if_(condition).then_(action)
    node.run()

    assert results == []


def test_if_then_false_lambda_condition() -> None:
    results = []

    def action() -> None:
        results.append(1)

    node = if_(lambda: False).then_(action)
    node.run()

    assert results == []


def test_if_else_true_condition() -> None:
    results = []

    node = (
        if_(lambda: True)
        .then_(lambda: results.append("if"))
        .else_(lambda: results.append("else"))
    )

    node.run()
    assert results == ["if"]


def test_if_else_false_condition() -> None:
    results = []

    node = (
        if_(lambda: False)
        .then_(lambda: results.append("if"))
        .else_(lambda: results.append("else"))
    )

    node.run()
    assert results == ["else"]


def test_if_elif_else_first_true() -> None:
    results = []

    node = (
        if_(lambda: True)
        .then_(lambda: results.append("if"))
        .elif_(lambda: True)
        .then_(lambda: results.append("elif"))
        .else_(lambda: results.append("else"))
    )

    node.run()
    assert results == ["if"]


def test_if_elif_else_second_true() -> None:
    results = []

    node = (
        if_(lambda: False)
        .then_(lambda: results.append("if"))
        .elif_(lambda: True)
        .then_(lambda: results.append("elif"))
        .else_(lambda: results.append("else"))
    )

    node.run()
    assert results == ["elif"]


def test_if_elif_else_none_true() -> None:
    results = []

    node = (
        if_(lambda: False)
        .then_(lambda: results.append("if"))
        .elif_(lambda: False)
        .then_(lambda: results.append("elif"))
        .else_(lambda: results.append("else"))
    )

    node.run()
    assert results == ["else"]


def test_if_elif_else_multiple_elifs() -> None:
    results = []

    node = (
        if_(lambda: False)
        .then_(lambda: results.append("if"))
        .elif_(lambda: False)
        .then_(lambda: results.append("elif1"))
        .elif_(lambda: True)
        .then_(lambda: results.append("elif2"))
        .else_(lambda: results.append("else"))
    )

    node.run()
    assert results == ["elif2"]


def test_while_loop() -> None:
    results = []
    count = 0

    def cond() -> bool:
        nonlocal count
        return count < 3

    def action() -> None:
        nonlocal count
        results.append(count)
        count += 1

    node = while_(cond).do_(action)
    node.run()

    assert results == [0, 1, 2]
    assert count == 3


def test_while_loop_zero_iterations() -> None:
    results = []

    node = while_(lambda: False).do_(lambda: results.append("action"))
    node.run()

    assert results == []


def test_nested_control_flow() -> None:
    results = []
    i = 0

    """
    while i < 2:
      if i == 0:
        append "zero"
      else:
        append "one"
      i += 1
    """

    def cond_while() -> bool:
        return i < 2

    def cond_if() -> bool:
        return i == 0

    def incr() -> None:
        nonlocal i
        i += 1

    inner_if = (
        if_(cond_if)
        .then_(lambda: results.append("zero"))
        .else_(lambda: results.append("one"))
    )

    loop = while_(cond_while).do_(inner_if | incr)

    loop.run()

    assert results == ["zero", "one"]
    assert i == 2
