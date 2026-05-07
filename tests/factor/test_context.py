import polars as pl

from factor.context import FactorContext


def test_factor_context_empty_dep_facs():
    """Test that load() returns empty DataFrame when dep_facs is empty."""
    ctx = FactorContext(loader_time="15:00:00")
    result = ctx.load(date="2023-01-03")
    assert isinstance(result, pl.DataFrame)
    assert result.is_empty()


def test_factor_context_dep_names():
    """Test that dep_names is correctly populated."""

    class DummyFactor:
        def __init__(self, name):
            self.name = name
            self.tb_name = f"factors/name={name}/version=1"

    fac1 = DummyFactor("fac1")
    ctx = FactorContext(fac1, loader_time="15:00:00")
    assert ctx.dep_names == ["fac1"]
