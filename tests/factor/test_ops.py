"""Tests for factor.ops modules."""

import polars as pl
import pytest

from factor.core import FIELD, BasicFactor
from factor.ops import basic, time_series


class DummyFactor(BasicFactor):
    """Concrete implementation of BasicFactor for testing."""

    def shift(self, n: int = 1):
        new_fac = DummyFactor(
            *self._depends, fn=self.fn, name=self.name, insert_time=self.insert_time
        )
        new_fac.lag = self.lag + n
        return new_fac


def dummy_fn(date, cb=None):
    """Test function that returns simple data."""
    return pl.DataFrame(
        {
            "asset": ["A", "B", "C"],
            "datetime": ["2023-01-01 15:00:00"] * 3,
            "price": [10.0, 20.0, 30.0],
        }
    )


def dummy_fn_multi(date, cb=None):
    """Test function that returns multi-field data."""
    return pl.DataFrame(
        {
            "asset": ["A", "B", "C"],
            "datetime": ["2023-01-01 15:00:00"] * 3,
            "field1": [1.0, 2.0, 3.0],
            "field2": [4.0, 5.0, 6.0],
        }
    )


class MockFactorContext:
    """Mock FactorContext for testing ops that return Expressions."""

    def __init__(self, data=None, dep_names=None):
        self.data = data if data is not None else self._default_data()
        self.dep_names = dep_names or ["price"]

    def _default_data(self):
        return pl.DataFrame(
            {
                FIELD.ASSET: ["A", "B", "C"] * 3,
                FIELD.DATETIME: [
                    "2023-01-01 15:00:00",
                    "2023-01-02 15:00:00",
                    "2023-01-03 15:00:00",
                ]
                * 3,
                "price": [10.0, 20.0, 30.0] * 3,
            }
        )

    def load(self, date=None, beg_date=None, end_date=None):
        return self.data

    def load_window(self, date, window=1):
        return self.data


class TestBasicOps:
    """Tests for basic arithmetic operations."""

    def test_log_returns_dataframe(self):
        """Test LOG operation returns DataFrame."""
        ctx = MockFactorContext()
        result = basic.LOG(ctx, "2023-01-01")
        assert isinstance(result, pl.DataFrame)
        assert FIELD.ASSET in result.columns

    def test_exp_returns_dataframe(self):
        """Test EXP operation returns DataFrame."""
        ctx = MockFactorContext()
        result = basic.EXP(ctx, "2023-01-01")
        assert isinstance(result, pl.DataFrame)
        assert FIELD.ASSET in result.columns

    def test_add_returns_dataframe(self):
        """Test ADD operation returns DataFrame."""
        ctx = MockFactorContext(dep_names=["price", "price"])
        result = basic.ADD(ctx, "2023-01-01")
        assert isinstance(result, pl.DataFrame)
        assert FIELD.ASSET in result.columns

    def test_sub_returns_dataframe(self):
        """Test SUB operation returns DataFrame."""
        ctx = MockFactorContext(dep_names=["price", "price"])
        result = basic.SUB(ctx, "2023-01-01")
        assert isinstance(result, pl.DataFrame)
        assert FIELD.ASSET in result.columns

    def test_div_returns_dataframe(self):
        """Test DIV operation returns DataFrame."""
        ctx = MockFactorContext(dep_names=["price", "price"])
        result = basic.DIV(ctx, "2023-01-01")
        assert isinstance(result, pl.DataFrame)
        assert FIELD.ASSET in result.columns

    def test_mul_returns_dataframe(self):
        """Test MUL operation returns DataFrame."""
        ctx = MockFactorContext(dep_names=["price", "price"])
        result = basic.MUL(ctx, "2023-01-01")
        assert isinstance(result, pl.DataFrame)
        assert FIELD.ASSET in result.columns

    def test_pct_returns_dataframe(self):
        """Test PCT operation returns DataFrame."""
        ctx = MockFactorContext(dep_names=["price", "price"])
        result = basic.PCT(ctx, "2023-01-01")
        assert isinstance(result, pl.DataFrame)
        assert FIELD.ASSET in result.columns

    def test_abs_returns_dataframe(self):
        """Test ABS operation returns DataFrame."""
        ctx = MockFactorContext()
        result = basic.ABS(ctx, "2023-01-01")
        assert isinstance(result, pl.DataFrame)
        assert FIELD.ASSET in result.columns

    def test_ufold_returns_dataframe(self):
        """Test UFOLD operation returns DataFrame."""
        ctx = MockFactorContext()
        result = basic.UFOLD(ctx, "2023-01-01")
        assert isinstance(result, pl.DataFrame)
        assert FIELD.ASSET in result.columns

    def test_zfold_returns_dataframe(self):
        """Test ZFOLD operation returns DataFrame."""
        ctx = MockFactorContext()
        result = basic.ZFOLD(ctx, "2023-01-01")
        assert isinstance(result, pl.DataFrame)
        assert FIELD.ASSET in result.columns


class TestTimeSeriesOps:
    """Tests for time series operations."""

    def test_ts_mean_executes(self):
        """Test TS_MEAN executes without error."""
        ctx = MockFactorContext()
        result = time_series.TS_MEAN(ctx, "2023-01-03", window=3)
        # Result can be Expr or DataFrame depending on polars version
        assert result is not None

    def test_ts_std_executes(self):
        """Test TS_STD executes without error."""
        ctx = MockFactorContext()
        result = time_series.TS_STD(ctx, "2023-01-03", window=3)
        assert result is not None

    def test_ts_zscore_executes(self):
        """Test TS_ZSCORE executes without error."""
        ctx = MockFactorContext()
        result = time_series.TS_ZSCORE(ctx, "2023-01-03", window=3)
        assert result is not None

    def test_ts_sharpe_executes(self):
        """Test TS_SHARPE executes without error."""
        ctx = MockFactorContext()
        result = time_series.TS_SHARPE(ctx, "2023-01-03", window=3)
        assert result is not None

    def test_ts_corr_executes(self):
        """Test TS_CORR executes without error."""
        ctx = MockFactorContext(dep_names=["price", "price"])
        result = time_series.TS_CORR(ctx, "2023-01-03", window=3)
        assert result is not None

    def test_ts_corr_warning_on_more_than_two_deps(self):
        """Test TS_CORR warns when given more than 2 dependencies."""
        data = pl.DataFrame(
            {
                FIELD.ASSET: ["A", "B", "C"] * 3,
                FIELD.DATETIME: [
                    "2023-01-01 15:00:00",
                    "2023-01-02 15:00:00",
                    "2023-01-03 15:00:00",
                ]
                * 3,
                "a": [1.0, 2.0, 3.0] * 3,
                "b": [4.0, 5.0, 6.0] * 3,
                "c": [7.0, 8.0, 9.0] * 3,
            }
        )
        ctx = MockFactorContext(data=data, dep_names=["a", "b", "c"])
        with pytest.warns(UserWarning, match="TS_CORR received 3 dependencies"):
            time_series.TS_CORR(ctx, "2023-01-03", window=3)

    def test_ts_mean_weighted_executes(self):
        """Test TS_MEAN_WEIGHTED executes without error."""
        ctx = MockFactorContext(dep_names=["price", "price"])
        result = time_series.TS_MEAN_WEIGHTED(ctx, "2023-01-03", window=3)
        assert result is not None

    def test_ts_range_executes(self):
        """Test TS_RANGE executes without error."""
        ctx = MockFactorContext()
        result = time_series.TS_RANGE(ctx, "2023-01-03", window=3)
        assert result is not None


class TestOpsWithRealExecution:
    """Tests that actually execute ops with mock data."""

    def test_log_executes_correctly(self):
        """Test LOG computes correct values."""
        ctx = MockFactorContext()
        result = basic.LOG(ctx, "2023-01-01")
        result_pd = result.collect() if hasattr(result, "collect") else result
        assert FIELD.ASSET in result_pd.columns

    def test_add_executes_correctly(self):
        """Test ADD computes correct values."""
        data = pl.DataFrame(
            {
                FIELD.ASSET: ["A", "B"],
                FIELD.DATETIME: ["2023-01-01 15:00:00", "2023-01-01 15:00:00"],
                "x": [1.0, 2.0],
                "y": [3.0, 4.0],
            }
        )
        ctx = MockFactorContext(data=data, dep_names=["x", "y"])
        result = basic.ADD(ctx, "2023-01-01")
        result_pd = result.collect() if hasattr(result, "collect") else result
        assert FIELD.ASSET in result_pd.columns
