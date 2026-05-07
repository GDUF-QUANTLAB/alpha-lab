import pytest

from factor.graph import get_execution_plan, group_by_level, topological_sort


class DummyFactor:
    def __init__(self, name, depends=None):
        self.name = name
        self._depends = depends or []


def test_topological_sort_empty():
    assert topological_sort() == []


def test_topological_sort_single():
    f = DummyFactor("a")
    assert topological_sort(f) == [f]


def test_topological_sort_chain():
    c = DummyFactor("c")
    b = DummyFactor("b", depends=[c])
    a = DummyFactor("a", depends=[b])
    result = topological_sort(a, b, c)
    # c should come first (no deps), then b, then a
    assert result.index(c) < result.index(b) < result.index(a)


def test_topological_sort_parallel():
    # a and b are independent, c depends on both
    a = DummyFactor("a")
    b = DummyFactor("b")
    c = DummyFactor("c", depends=[a, b])
    result = topological_sort(a, b, c)
    # c should come last
    assert result.index(c) > result.index(a)
    assert result.index(c) > result.index(b)


def test_topological_sort_circular_detection():
    a = DummyFactor("a", depends=[])
    b = DummyFactor("b", depends=[a])
    a._depends = [b]  # circular: a depends on b, b depends on a
    with pytest.raises(ValueError, match="Circular dependency"):
        topological_sort(a, b)


def test_group_by_level_empty():
    assert group_by_level() == []


def test_group_by_level_single():
    f = DummyFactor("a")
    assert group_by_level(f) == [[f]]


def test_group_by_level_chain():
    c = DummyFactor("c")
    b = DummyFactor("b", depends=[c])
    a = DummyFactor("a", depends=[b])
    levels = group_by_level(a, b, c)
    # Level 0: c, Level 1: b, Level 2: a
    assert len(levels) == 3
    assert levels[0] == [c]
    assert levels[1] == [b]
    assert levels[2] == [a]


def test_group_by_level_parallel():
    a = DummyFactor("a")
    b = DummyFactor("b")
    c = DummyFactor("c", depends=[a, b])
    levels = group_by_level(a, b, c)
    # Level 0: a, b (parallel), Level 1: c
    assert len(levels) == 2
    assert set(levels[0]) == {a, b}
    assert levels[1] == [c]


def test_get_execution_plan():
    a = DummyFactor("a")
    b = DummyFactor("b")
    c = DummyFactor("c", depends=[a, b])
    plan = get_execution_plan(a, b, c)
    assert plan["total_functions"] == 3
    assert plan["independent_functions"] == 2
    assert plan["max_parallelism"] == 2
