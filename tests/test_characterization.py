"""Golden-master tests: the game maths must behave exactly as recorded.

A failure here means a change altered game balance or behavior. If that change
was intended, regenerate the reference with ``python -m tests.golden_cases --update <name>``
and review the JSON diff before committing.
"""

import pytest

from tests.golden_cases import SCENARIOS, load_golden, run_scenario


def first_difference(actual, expected, path='$'):
    """Return a readable description of the first mismatch, or None if equal."""
    if type(actual) is not type(expected):
        return f'{path}: type {type(actual).__name__} != {type(expected).__name__}'
    if isinstance(actual, dict):
        if actual.keys() != expected.keys():
            return f'{path}: keys {sorted(actual)} != {sorted(expected)}'
        for key in actual:
            diff = first_difference(actual[key], expected[key], f'{path}.{key}')
            if diff:
                return diff
        return None
    if isinstance(actual, list):
        for index, (a, e) in enumerate(zip(actual, expected, strict=False)):
            diff = first_difference(a, e, f'{path}[{index}]')
            if diff:
                return diff
        if len(actual) != len(expected):
            return f'{path}: length {len(actual)} != {len(expected)}'
        return None
    if actual != expected:
        return f'{path}: {actual!r} != {expected!r}'
    return None


@pytest.mark.parametrize('name', sorted(SCENARIOS))
def test_matches_golden(name):
    diff = first_difference(run_scenario(name), load_golden(name))
    assert diff is None, f'{name} differs from golden reference at {diff}'
