"""Tests for factor user API integration behavior."""

import polars as pl

from factor.api import Factor
from factor.core import FIELD, Cubase
from factor.engine import get_value_online


def dep_fn(date):
    return pl.DataFrame({FIELD.ASSET: ["A"], "value": [1.0]})


def parent_fn(date, cb):
    assert cb.cubase.get_lag(0) == 2
    return pl.DataFrame({FIELD.ASSET: ["A"], "value": [1.0]})


def test_factor_call_preserves_cubase_config():
    dep = Factor(fn=dep_fn, name="dep", insert_time="15:00:00")
    cubase = Cubase([{"factor": dep, "lag": 2}])
    fac = Factor(cubase, fn=parent_fn, name="parent", insert_time="15:00:00")

    bound = fac(extra=1)

    assert bound._cubase.get_lag(0) == 2


def test_factor_version_includes_cubase_lag():
    dep = Factor(fn=dep_fn, name="dep", insert_time="15:00:00")

    lag_1 = Factor(
        Cubase([{"factor": dep, "lag": 1}]),
        fn=parent_fn,
        name="parent",
        insert_time="15:00:00",
    )
    lag_2 = Factor(
        Cubase([{"factor": dep, "lag": 2}]),
        fn=parent_fn,
        name="parent",
        insert_time="15:00:00",
    )

    assert lag_1.version != lag_2.version


def test_get_value_online_passes_factor_cubase_to_context():
    dep = Factor(fn=dep_fn, name="dep", insert_time="15:00:00")
    cubase = Cubase([{"factor": dep, "lag": 2}])
    fac = Factor(cubase, fn=parent_fn, name="parent", insert_time="15:00:00")

    result = get_value_online(fac, "2023-01-03")

    assert result[FIELD.FIELDNAMES].to_list() == ["value"]
